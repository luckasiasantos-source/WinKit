"""Etapa: ligar um recurso do Windows (V2-08, R19).

Nunca desliga nada. O .NET 3.5 usa, nesta ordem, a pasta ``sources\\sxs`` do pendrive comum,
a da ISO original montada **só para leitura** (Ventoy, D-002) ou, na Fase 2, o Windows Update.
"""

from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path

from winkit.agent.steps.base import StepBase, StepContext, StepResult
from winkit.core import layout
from winkit.core.catalog.models import FeatureEntry
from winkit.core.errors import WinKitError
from winkit.core.isos import IsoIndex, pick_iso
from winkit.i18n import Msg, msg
from winkit.platform.iso_mount import mounted_iso


def _entry(ctx: StepContext) -> FeatureEntry | None:
    return ctx.catalogs.feature(ctx.step.ref)


def _states(ctx: StepContext, entry: FeatureEntry) -> dict[str, bool]:
    features = [p.feature for p in entry.parts if p.feature]
    capabilities = [p.capability for p in entry.parts if p.capability]
    return ctx.services.features.states(features, capabilities)


def _language(ctx: StepContext) -> str | None:
    lang = ctx.recipe.windows.ui_language
    return None if lang == "auto" else lang


def offline_source(ctx: StepContext, entry: FeatureEntry, stack: ExitStack) -> Path | None:
    """Pasta com os arquivos do recurso, ou ``None``. Uma ISO montada fica em ``stack``."""
    rel = entry.offline_source
    root = ctx.pendrive
    if rel is None or root is None:
        return None
    direct = root / rel
    if direct.is_dir():  # pendrive comum (Rufus/Microsoft): a mídia já está aberta
        return direct
    iso = _matching_iso(ctx, root)
    if iso is None:
        return None
    try:
        mount = stack.enter_context(mounted_iso(ctx.services.iso, iso))
    except WinKitError as exc:
        ctx.log.warning(f"não foi possível montar {iso.name}: {exc}", step=ctx.step.id)
        return None
    ctx.log.info(f"ISO montada só para leitura: {iso.name}", step=ctx.step.id)
    source = mount / rel
    return source if source.is_dir() else None


def _matching_iso(ctx: StepContext, root: Path) -> Path | None:
    """A ISO do pendrive com o mesmo build do Windows em execução (``WinKit/isos.json``)."""
    index_file = root / layout.ISOS_INDEX
    try:
        index = IsoIndex.model_validate(json.loads(index_file.read_text(encoding="utf-8")))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        ctx.log.warning(f"isos.json ilegível: {exc}", step=ctx.step.id)
        return None
    chosen = pick_iso(
        index,
        build=ctx.services.env.windows_build(),
        architecture=ctx.recipe.windows.architecture,
        language=_language(ctx),
    )
    if chosen is None:
        ctx.log.info("nenhuma ISO do mesmo build no pendrive", step=ctx.step.id)
        return None
    iso = root / chosen.image.lstrip("/")
    return iso if iso.is_file() else None


class FeatureStep(StepBase):
    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        entry = _entry(ctx)
        if entry is None:
            return False
        states = _states(ctx, entry)
        return all(states.get(p.name, False) for p in entry.parts)

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        entry = _entry(ctx)
        if entry is None:
            return ()
        key = "preview.feature_restart" if entry.restart else "preview.feature"
        return (msg(key, name=entry.name),)

    def run(self, ctx: StepContext) -> StepResult:
        entry = _entry(ctx)
        if entry is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        before = _states(ctx, entry)
        missing = [p for p in entry.parts if not before.get(p.name, False)]
        reboot = False
        try:
            with ExitStack() as stack:
                source = offline_source(ctx, entry, stack) if missing else None
                if entry.needs_network and source is None:
                    if ctx.phase == 1 and ctx.mode == "install":
                        return StepResult.deferred(msg("step.feature.no_offline_source"))
                    if not ctx.services.env.has_internet():
                        return StepResult.deferred(msg("step.no_network"))
                for part in missing:
                    if part.capability:
                        result = ctx.services.features.set_capability(part.name, installed=True)
                    else:
                        result = ctx.services.features.set_optional_feature(
                            part.name,
                            enabled=True,
                            source=source if part.offline_source else None,
                        )
                    ctx.log.info(f"{part.name}: {result}", step=ctx.step.id)
                    if result == "absent":
                        return StepResult.skipped(msg("step.feature.absent", name=part.name))
                    reboot = reboot or result == "restart"
        except WinKitError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        key = "step.feature.enabled_offline" if source is not None else "step.feature.enabled"
        return StepResult.ok(msg(key, name=entry.name), reboot=reboot)
