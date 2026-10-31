"""Etapa: aparência pessoal (V2-06, R23).

Fase 1 no perfil Default; ao vivo (ou no fallback) no ``HKCU``, aplicando na hora. O papel de
parede vai para ``%SystemRoot%\\Web\\Wallpaper\\WinKit``, pasta da máquina que sobrevive à
limpeza do Agente.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from winkit.agent.steps.base import StepBase, StepContext, StepResult, local_path
from winkit.core.catalog.models import PersonalGroup
from winkit.core.errors import WinKitError
from winkit.core.personal import WALLPAPER_KEY, WALLPAPER_VALUE, same, value_id
from winkit.i18n import Msg, msg
from winkit.platform.registry import DEFAULT_HIVE_MOUNT, mounted_hive

WALLPAPER_DIR = ("Web", "Wallpaper", "WinKit")


@contextmanager
def _hive(ctx: StepContext) -> Iterator[tuple[str, str]]:
    """(hive, prefixo) do perfil de destino."""
    if ctx.step.target == "default_profile":
        hive = Path(local_path(ctx.services.folders.default_profile_root())) / "NTUSER.DAT"
        with mounted_hive(ctx.services.registry, hive):
            yield "HKU", DEFAULT_HIVE_MOUNT + "\\"
    else:
        yield "HKCU", ""


def _group(ctx: StepContext) -> PersonalGroup | None:
    return ctx.catalogs.personal_group(ctx.step.ref)


def _wallpaper_target(ctx: StepContext) -> tuple[Path, str] | None:
    """(arquivo local, caminho do Windows gravado no registro)."""
    rel = ctx.recipe.personal.wallpaper_file
    if not rel:
        return None
    name = "papel-de-parede" + Path(rel).suffix
    windows = ctx.services.folders.windows_dir()
    return (
        local_path(windows).joinpath(*WALLPAPER_DIR, name),
        "\\".join([windows, *WALLPAPER_DIR, name]),
    )


class PersonalStep(StepBase):
    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        group = _group(ctx)
        if group is None or ctx.step.target == "default_profile":
            return False  # o perfil Default só é lido com a hive montada; gravar de novo é seguro
        reg = ctx.services.registry
        values = ctx.recipe.personal.values
        for spec in group.values:
            wanted = values.get(value_id(spec))
            if wanted is not None and not same(reg.get("HKCU", spec.key, spec.value), wanted):
                return False
        if group.file:
            target = _wallpaper_target(ctx)
            if target is None or not target[0].is_file():
                return False
            return bool(reg.get("HKCU", WALLPAPER_KEY, WALLPAPER_VALUE) == target[1])
        return True

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        group = _group(ctx)
        return (msg("preview.personal", name=group.name),) if group else ()

    def run(self, ctx: StepContext) -> StepResult:
        group = _group(ctx)
        if group is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        values = ctx.recipe.personal.values
        written = 0
        try:
            target = self._copy_wallpaper(ctx) if group.file else None
            with _hive(ctx) as (hive, prefix):
                reg = ctx.services.registry
                for spec in group.values:
                    wanted = values.get(value_id(spec))
                    if wanted is not None:
                        reg.set(hive, prefix + spec.key, spec.value, wanted.type, wanted.data)
                        written += 1
                if target is not None:
                    reg.set(hive, prefix + WALLPAPER_KEY, WALLPAPER_VALUE, "sz", target[1])
                    written += 1
        except (WinKitError, OSError) as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        if written == 0:
            return StepResult.skipped(msg("step.personal.nothing"))
        if ctx.step.target == "user_profile":
            live = ctx.services.appearance
            if target is not None:
                live.set_wallpaper(target[0])
            if group.id == "cursor":
                live.reload_cursors()
        return StepResult.ok(msg("step.personal.applied", name=group.name))

    def _copy_wallpaper(self, ctx: StepContext) -> tuple[Path, str] | None:
        target = _wallpaper_target(ctx)
        rel = ctx.recipe.personal.wallpaper_file
        if target is None or rel is None:
            return None
        target[0].parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ctx.payload(rel), target[0])
        return target
