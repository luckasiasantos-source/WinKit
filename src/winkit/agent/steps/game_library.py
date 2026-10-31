"""Etapa: jogos sem baixar de novo (V2-13, R22).

- Steam: acrescenta a biblioteca no ``libraryfolders.vdf`` (Steam fechada); a Steam acha os
  jogos pelos ``appmanifest_*.acf`` da pasta (H33).
- Epic: copia o manifesto ``.item`` com os caminhos na letra atual e acrescenta o jogo no
  ``LauncherInstalled.dat``.
Nunca mexe nos arquivos dos jogos. Sem o launcher instalado, pula com a instrução.
"""

from __future__ import annotations

import json
from pathlib import Path

from winkit.agent.steps.base import StepBase, StepContext, StepResult, local_path
from winkit.core.fsutil import atomic_write_text
from winkit.core.games import (
    add_launcher_installed,
    add_steam_library,
    has_steam_library,
    rewrite_epic_manifest,
)
from winkit.core.recipe.models import GameLibrary
from winkit.core.vdf import VdfError, dumps, loads
from winkit.core.volumes import VolumeInfo, on, resolve
from winkit.i18n import Msg, msg

STEAM_PROCESSES = ["steam.exe", "steamwebhelper.exe"]
EPIC_PROCESSES = ["EpicGamesLauncher.exe", "EpicWebHelper.exe"]


def _lib(ctx: StepContext) -> GameLibrary | None:
    return next((g for g in ctx.recipe.game_libraries if g.id == ctx.step.ref), None)


def _steam_vdf(ctx: StepContext) -> Path | None:
    raw = ctx.services.registry.get("HKCU", r"Software\Valve\Steam", "SteamPath")
    if isinstance(raw, str) and raw:
        steam = local_path(raw.replace("/", "\\"))
    else:
        steam = local_path(ctx.folders()["PROGRAMFILESX86"]) / "Steam"
    return steam / "steamapps" / "libraryfolders.vdf" if steam.is_dir() else None


def _epic_dirs(ctx: StepContext) -> tuple[Path, Path] | None:
    base = local_path(ctx.folders()["PROGRAMDATA"]) / "Epic"
    if not base.is_dir():
        return None
    return (
        base / "EpicGamesLauncher" / "Data" / "Manifests",
        base / "UnrealEngineLauncher" / "LauncherInstalled.dat",
    )


class GameLibraryStep(StepBase):
    live_safe = True

    def _volume(self, ctx: StepContext, lib: GameLibrary) -> VolumeInfo | None:
        v = resolve(lib.volume, ctx.services.volumes.volumes())
        return v if v is not None and v.letter else None

    def check(self, ctx: StepContext) -> bool:
        lib = _lib(ctx)
        if lib is None or lib.launcher != "steam":
            return False
        v = self._volume(ctx, lib)
        vdf = _steam_vdf(ctx)
        if v is None or vdf is None or not vdf.is_file():
            return False
        try:
            return has_steam_library(
                loads(vdf.read_text(encoding="utf-8")), on(v, lib.relative_path)
            )
        except (OSError, VdfError):
            return False

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        lib = _lib(ctx)
        return (msg("preview.game_library", name=lib.name),) if lib else ()

    def run(self, ctx: StepContext) -> StepResult:
        lib = _lib(ctx)
        if lib is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        v = self._volume(ctx, lib)
        if v is None:
            label = lib.volume.label or lib.volume.serial
            return StepResult.skipped(msg("step.game_library.no_volume", label=label))
        if (
            not ctx.services.volumes.root(str(v.letter))
            .joinpath(*lib.relative_path.split("\\"))
            .is_dir()
        ):
            return StepResult.skipped(
                msg("step.game_library.no_folder", path=on(v, lib.relative_path))
            )
        try:
            if lib.launcher == "steam":
                return self._steam(ctx, lib, v)
            return self._epic(ctx, lib, v)
        except (OSError, ValueError) as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))

    def _steam(self, ctx: StepContext, lib: GameLibrary, v: VolumeInfo) -> StepResult:
        vdf = _steam_vdf(ctx)
        if vdf is None:
            return StepResult.skipped(msg("step.game_library.no_launcher", launcher="Steam"))
        ctx.services.installers.kill(STEAM_PROCESSES)
        data = loads(vdf.read_text(encoding="utf-8")) if vdf.is_file() else {}
        if add_steam_library(data, on(v, lib.relative_path)):
            vdf.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(vdf, dumps(data))
        return StepResult.ok(msg("step.game_library.steam", path=on(v, lib.relative_path)))

    def _epic(self, ctx: StepContext, lib: GameLibrary, v: VolumeInfo) -> StepResult:
        dirs = _epic_dirs(ctx)
        if dirs is None or lib.manifest is None:
            return StepResult.skipped(msg("step.game_library.no_launcher", launcher="Epic Games"))
        manifests, installed = dirs
        ctx.services.installers.kill(EPIC_PROCESSES)
        src = ctx.payload(lib.manifest)
        item = rewrite_epic_manifest(
            json.loads(src.read_text(encoding="utf-8")), on(v, lib.relative_path)
        )
        manifests.mkdir(parents=True, exist_ok=True)
        atomic_write_text(manifests / src.name, json.dumps(item, indent=4))
        data = json.loads(installed.read_text(encoding="utf-8")) if installed.is_file() else {}
        if add_launcher_installed(data, item):
            installed.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(installed, json.dumps(data, indent=4))
        return StepResult.ok(msg("step.game_library.epic", name=lib.name))
