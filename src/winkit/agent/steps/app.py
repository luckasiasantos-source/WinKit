"""Etapas de aplicativos (M5): instalador offline, winget online e atalhos de portáteis."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from winkit.agent.integrity import verify_payload
from winkit.agent.steps.base import StepBase, StepContext, StepResult, local_path
from winkit.core.errors import IntegrityError, PathTemplateError, WinKitError
from winkit.core.paths import templates
from winkit.core.recipe.models import AppItem, ShortcutSpec
from winkit.i18n import msg
from winkit.platform import winget as wg

START_MENU = r"Microsoft\Windows\Start Menu\Programs"


def _item(ctx: StepContext) -> AppItem | None:
    return ctx.recipe.app(ctx.step.ref)


def _installed_by_name(ctx: StepContext, item: AppItem) -> bool:
    entry = ctx.catalogs.app(item.id)
    pattern = entry.match.display_name_regex if entry else None
    for app in ctx.services.inventory.installed(include_appx=False):
        if pattern and re.search(pattern, app.name):
            return True
        if app.name.casefold() == item.name.casefold():
            return True
    return False


def after_install(ctx: StepContext, item: AppItem) -> None:
    ai = item.after_install
    if ai.kill_processes:
        ctx.services.installers.kill(ai.kill_processes)
    for entry in ai.disable_autostart:
        for hive in {entry.hive, "HKLM"}:
            try:
                if ctx.services.registry.delete_value(hive, entry.key, entry.value):
                    ctx.log.info(
                        f"inicialização automática removida: {hive}\\{entry.value}",
                        step=ctx.step.id,
                    )
            except WinKitError as exc:
                ctx.log.warning(f"não foi possível remover {entry.value}: {exc}", step=ctx.step.id)
    if ai.shortcuts:
        create_shortcuts(ctx, ai.shortcuts)


def shortcut_path(ctx: StepContext, spec: ShortcutSpec) -> Path:
    folders = ctx.folders()
    base = (
        folders["DESKTOP"] if spec.location == "desktop" else f"{folders['APPDATA']}\\{START_MENU}"
    )
    return local_path(f"{base}\\{spec.name}.lnk")


def create_shortcuts(ctx: StepContext, specs: list[ShortcutSpec]) -> None:
    folders = ctx.folders()
    for spec in specs:
        target = templates.resolve(spec.target, folders)
        ctx.services.shortcuts.create(shortcut_path(ctx, spec), target, spec.arguments)


class AppStep(StepBase):
    def check(self, ctx: StepContext) -> bool:
        item = _item(ctx)
        if item is None:
            return False
        if item.source == "winget_online" and item.winget_id:
            w = ctx.services.winget
            return w.available() and w.is_installed(item.winget_id)
        if item.source == "offline":
            return _installed_by_name(ctx, item)
        return False

    def run(self, ctx: StepContext) -> StepResult:
        item = _item(ctx)
        if item is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        if item.requires_non_elevated:
            ctx.log.warning("este instalador prefere rodar sem elevação (DT-002)", step=ctx.step.id)
        if item.source == "winget_online":
            return self._winget(ctx, item)
        if item.source == "offline":
            return self._offline(ctx, item)
        return StepResult.skipped(msg("step.portable_by_shortcut"))

    # ------------------------------------------------------------------ offline
    def _offline(self, ctx: StepContext, item: AppItem) -> StepResult:
        spec = item.installer
        if spec is None or not spec.path or ctx.pendrive is None:
            return StepResult.failed(msg("recipe.missing_installer", id=item.id), recoverable=False)
        try:
            verify_payload(ctx.pendrive, spec.path, tree=False)
        except IntegrityError as exc:
            return StepResult.failed(msg("step.hash_mismatch", path=str(exc)), recoverable=False)
        source = ctx.payload(spec.path)
        cache = ctx.paths.base / "cache" / item.id
        try:
            if cache.exists():
                shutil.rmtree(cache)
            shutil.copytree(source.parent, cache)
            outcome = ctx.services.installers.run(
                cache / source.name, spec, scope=item.scope, log=ctx.log.step_log(ctx.step.id)
            )
        finally:
            shutil.rmtree(cache, ignore_errors=True)
        if outcome.timed_out:
            return StepResult.failed(msg("step.timeout", minutes=spec.timeout_minutes))
        code = outcome.exit_code
        if code in spec.success_codes or code in spec.reboot_codes:
            after_install(ctx, item)
            return StepResult.ok(reboot=code in spec.reboot_codes)
        return StepResult.failed(
            msg("step.installer_failed", code=code, path=f"WinKit\\{spec.path}")
        )

    # ------------------------------------------------------------------ winget
    def _winget(self, ctx: StepContext, item: AppItem) -> StepResult:
        w = ctx.services.winget
        if not item.winget_id:
            return StepResult.failed(msg("recipe.missing_winget_id", id=item.id), recoverable=False)
        if not w.available():
            try:
                w.register()
            except WinKitError as exc:
                ctx.log.warning(f"registro do App Installer falhou: {exc}", step=ctx.step.id)
            if not ctx.wait(w.available, ctx.winget_wait_seconds, "winget"):
                return StepResult.deferred(msg("step.winget_unavailable"))
        code = w.install(
            item.winget_id,
            scope=item.scope,
            source=item.winget_source,
            log=ctx.log.step_log(ctx.step.id),
        )
        if code == -1:
            return StepResult.deferred(msg("step.winget_unavailable"))
        if code == -2:
            return StepResult.failed(msg("step.timeout", minutes=60))
        if code in wg.SUCCESS_CODES or code in wg.REBOOT_CODES:
            after_install(ctx, item)
            return StepResult.ok(reboot=code in wg.REBOOT_CODES)
        return StepResult.failed(msg("step.winget_code", code=f"0x{code:08X}"))


class ShortcutStep(StepBase):
    """Apps portáteis (R12): a pasta já foi restaurada; aqui só os atalhos."""

    def check(self, ctx: StepContext) -> bool:
        item = _item(ctx)
        if item is None or not item.after_install.shortcuts:
            return False
        return all(shortcut_path(ctx, s).exists() for s in item.after_install.shortcuts)

    def run(self, ctx: StepContext) -> StepResult:
        item = _item(ctx)
        if item is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        if not item.after_install.shortcuts:
            return StepResult.skipped(msg("step.no_shortcuts"))
        try:
            create_shortcuts(ctx, item.after_install.shortcuts)
        except (PathTemplateError, WinKitError) as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        return StepResult.ok()
