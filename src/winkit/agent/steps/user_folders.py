"""Etapa: pastas do usuário em outro disco (V2-14, R16).

Só aponta as pastas (``User Shell Folders``); nunca move nem apaga arquivos, nunca troca letra.
Sem o volume, pula com motivo e as pastas ficam no lugar padrão.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from winkit.agent.steps.base import StepBase, StepContext, StepResult, local_path
from winkit.core.errors import WinKitError
from winkit.core.user_folders import SHELL_FOLDERS_KEY, expand_user, registry_values
from winkit.core.volumes import VolumeInfo, resolve
from winkit.i18n import Msg, msg
from winkit.platform.registry import DEFAULT_HIVE_MOUNT, mounted_hive


@contextmanager
def _hive(ctx: StepContext) -> Iterator[tuple[str, str]]:
    if ctx.step.target == "default_profile":
        hive = Path(local_path(ctx.services.folders.default_profile_root())) / "NTUSER.DAT"
        with mounted_hive(ctx.services.registry, hive):
            yield "HKU", f"{DEFAULT_HIVE_MOUNT}\\{SHELL_FOLDERS_KEY}"
    else:
        yield "HKCU", SHELL_FOLDERS_KEY


def target_volume(ctx: StepContext) -> VolumeInfo | None:
    uf = ctx.recipe.user_folders
    if not uf.enabled or uf.volume is None:
        return None
    return resolve(uf.volume, ctx.services.volumes.volumes())


class UserFoldersStep(StepBase):
    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        if ctx.step.target == "default_profile":
            return False
        v = target_volume(ctx)
        if v is None or v.letter is None:
            return False
        values = registry_values(ctx.recipe.user_folders, v.letter)
        reg = ctx.services.registry
        return all(reg.get("HKCU", SHELL_FOLDERS_KEY, k) == val for k, val in values.items())

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        v = target_volume(ctx)
        if v is None or v.letter is None:
            return (msg("step.user_folders.no_volume", label=self._label(ctx)),)
        values = registry_values(ctx.recipe.user_folders, v.letter)
        return tuple(msg("preview.user_folder", path=p) for p in values.values())

    def _label(self, ctx: StepContext) -> str:
        ref = ctx.recipe.user_folders.volume
        return (ref.label or ref.serial) if ref else "?"

    def run(self, ctx: StepContext) -> StepResult:
        v = target_volume(ctx)
        if v is None or v.letter is None:
            return StepResult.skipped(msg("step.user_folders.no_volume", label=self._label(ctx)))
        uf = ctx.recipe.user_folders
        username = ctx.recipe.windows.account.username
        root = ctx.services.volumes.root(v.letter)
        try:
            for rel in uf.folders.values():  # para a conta principal; as outras, no login
                root.joinpath(*expand_user(rel, username).split("\\")).mkdir(
                    parents=True, exist_ok=True
                )
            with _hive(ctx) as (hive, key):
                for name, value in registry_values(uf, v.letter).items():
                    ctx.services.registry.set(hive, key, name, "expand_sz", value)
        except (WinKitError, OSError) as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        key = (
            "step.user_folders.live"
            if ctx.step.target == "user_profile"
            else "step.user_folders.done"
        )
        return StepResult.ok(msg(key, letter=v.letter, n=len(uf.folders)))
