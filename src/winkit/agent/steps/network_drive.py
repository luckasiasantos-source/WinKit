"""Etapa: unidade de rede mapeada (V2-17, R25).

- Fase 1: grava no perfil Default (``HKU\\WinKitDefault\\Network\\<letra>``); o usuário novo
  reconecta no primeiro login.
- Fase 2 / ao vivo: mapeia na hora; com o servidor fora do ar, grava no ``HKCU`` e o Windows
  reconecta no próximo login.
- Letra já usada por outra coisa: pula com motivo (nunca substitui).
"""

from __future__ import annotations

from pathlib import Path

from winkit.agent.steps.base import StepBase, StepContext, StepResult, local_path
from winkit.core.errors import WinKitError
from winkit.core.recipe.models import NetworkDrive
from winkit.i18n import Msg, msg
from winkit.platform.netdrives import provider_name, read_mapped, write_mapping
from winkit.platform.registry import DEFAULT_HIVE_MOUNT, mounted_hive


def _item(ctx: StepContext) -> NetworkDrive | None:
    return next((d for d in ctx.recipe.network_drives if d.letter == ctx.step.ref), None)


def _same(a: str, b: str) -> bool:
    return a.rstrip("\\").casefold() == b.rstrip("\\").casefold()


def _letter_busy(ctx: StepContext, letter: str) -> bool:
    """A letra é de um disco local (ou pendrive) agora?"""
    return any(str(r).upper().startswith(f"{letter}:") for r in ctx.services.env.drive_roots())


class NetworkDriveStep(StepBase):
    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        item = _item(ctx)
        if item is None or ctx.step.target == "default_profile":
            return False  # o perfil Default só é lido com a hive montada; gravar de novo é seguro
        current = read_mapped(ctx.services.registry).get(item.letter)
        return current is not None and _same(current, item.remote_path)

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        item = _item(ctx)
        if item is None:
            return ()
        return (msg("preview.network_drive", letter=item.letter, path=item.remote_path),)

    def run(self, ctx: StepContext) -> StepResult:
        item = _item(ctx)
        if item is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        try:
            if ctx.step.target == "default_profile":
                return self._default_profile(ctx, item)
            return self._current_user(ctx, item)
        except WinKitError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))

    def _default_profile(self, ctx: StepContext, item: NetworkDrive) -> StepResult:
        reg = ctx.services.registry
        provider = provider_name(reg)
        hive = Path(local_path(ctx.services.folders.default_profile_root())) / "NTUSER.DAT"
        with mounted_hive(reg, hive):
            current = read_mapped(reg, "HKU", DEFAULT_HIVE_MOUNT).get(item.letter)
            if current is not None and not _same(current, item.remote_path):
                return StepResult.skipped(
                    msg("step.network_drive.letter_taken", letter=item.letter)
                )
            write_mapping(
                reg, "HKU", DEFAULT_HIVE_MOUNT, item.letter, item.remote_path, provider=provider
            )
        return StepResult.ok(msg("step.network_drive.saved", letter=item.letter))

    def _current_user(self, ctx: StepContext, item: NetworkDrive) -> StepResult:
        reg = ctx.services.registry
        current = read_mapped(reg).get(item.letter)
        if (current is not None and not _same(current, item.remote_path)) or (
            current is None and _letter_busy(ctx, item.letter)
        ):
            return StepResult.skipped(msg("step.network_drive.letter_taken", letter=item.letter))
        if ctx.services.drive_mapper.map_now(item.letter, item.remote_path):
            return StepResult.ok(msg("step.network_drive.mapped", letter=item.letter))
        write_mapping(reg, "HKCU", "", item.letter, item.remote_path, provider=provider_name(reg))
        return StepResult.ok(msg("step.network_drive.saved", letter=item.letter))
