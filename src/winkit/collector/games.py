"""Jogos instalados em outro disco (V2-13): bibliotecas da Steam e jogos da Epic.

Bibliotecas no volume do sistema (que será formatado) não entram na receita: o Studio mostra
e explica como mover pela própria loja.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from winkit.collector.backups import local_source
from winkit.core import layout
from winkit.core.fsutil import atomic_write_bytes
from winkit.core.games import steam_libraries
from winkit.core.recipe.models import GameLibrary, Recipe
from winkit.core.vdf import VdfError, loads
from winkit.core.volumes import VolumeInfo, ref_for, split
from winkit.platform.registry import Registry

VolumeRoot = Callable[[str], Path]
STEAM_KEY = r"Software\Valve\Steam"
EPIC_MANIFESTS = r"Epic\EpicGamesLauncher\Data\Manifests"


@dataclass
class GamesReport:
    added: list[GameLibrary] = field(default_factory=list)
    #: Bibliotecas/jogos no disco do sistema (não podem ser levados).
    on_system: list[str] = field(default_factory=list)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "jogo"


def _steam(registry: Registry, volume_root: VolumeRoot) -> list[tuple[str, int]]:
    raw = registry.get("HKCU", STEAM_KEY, "SteamPath")
    if not isinstance(raw, str) or len(raw) < 3:
        return []
    steam = raw.replace("/", "\\")
    vdf = local_source(volume_root(steam[:2].upper()), steam) / "steamapps" / "libraryfolders.vdf"
    try:
        return steam_libraries(loads(vdf.read_text(encoding="utf-8")))
    except (OSError, VdfError):
        return []


def collect_games(
    registry: Registry,
    root: Path,
    recipe: Recipe,
    volumes: list[VolumeInfo],
    *,
    machine: Mapping[str, str],
    volume_root: VolumeRoot,
) -> GamesReport:
    report = GamesReport()
    known = {g.id for g in recipe.game_libraries}

    def add(lib: GameLibrary) -> None:
        if lib.id not in known:
            known.add(lib.id)
            report.added.append(lib)

    for path, games in _steam(registry, volume_root):
        hit = split(path, volumes)
        if hit is None or hit[0].is_system or not hit[1]:
            report.on_system.append(path)
            continue
        v, rel = hit
        add(
            GameLibrary(
                id=f"steam-{v.serial.lower()}-{_slug(rel)}",
                launcher="steam",
                name=f"Steam — {path}",
                volume=ref_for(v),
                relative_path=rel,
                games=games,
            )
        )
    programdata = machine.get("PROGRAMDATA")
    manifests = (
        local_source(volume_root(programdata[:2].upper()), f"{programdata}\\{EPIC_MANIFESTS}")
        if programdata
        else None
    )
    for item_file in sorted(manifests.glob("*.item")) if manifests and manifests.is_dir() else []:
        try:
            item = json.loads(item_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        install = str(item.get("InstallLocation") or "")
        hit = split(install, volumes)
        name = str(item.get("DisplayName") or item.get("AppName") or item_file.stem)
        if hit is None or hit[0].is_system or not hit[1]:
            report.on_system.append(name)
            continue
        v, rel = hit
        game_id = f"epic-{_slug(str(item.get('AppName') or name))}"
        rel_file = f"{layout.games_dir(recipe.meta.profile_id)}/{game_id}/{item_file.name}"
        atomic_write_bytes(root / rel_file, item_file.read_bytes())
        add(
            GameLibrary(
                id=game_id,
                launcher="epic",
                name=name,
                volume=ref_for(v),
                relative_path=rel,
                games=1,
                manifest=rel_file.removeprefix(f"{layout.WINKIT}/"),
            )
        )
    recipe.game_libraries = [*recipe.game_libraries, *report.added]
    return report


def select(recipe: Recipe, ids: list[str], *, selected: bool) -> list[str]:
    missing = []
    for game_id in ids:
        lib = next((g for g in recipe.game_libraries if g.id == game_id), None)
        if lib is None:
            missing.append(game_id)
        else:
            lib.selected = selected
    return missing
