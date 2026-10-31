"""Jogos sem baixar de novo (V2-13): VDF, manifestos da Epic, coleta e etapa."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.collector.games import STEAM_KEY, collect_games
from winkit.core.catalog.loader import default_catalogs
from winkit.core.games import (
    add_launcher_installed,
    add_steam_library,
    rewrite_epic_manifest,
    steam_libraries,
)
from winkit.core.planner.models import PlanContext
from winkit.core.planner.planner import plan
from winkit.core.recipe.models import AppItem
from winkit.core.vdf import VdfError, dumps, loads
from winkit.platform.fakes.apps import FakeInstallerRunner
from winkit.platform.fakes.backup import FakeOldPcFolders
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.services import fake_services
from winkit.platform.fakes.volumes import FakeVolumes

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "games"
DATA = "5E6F7A8B"


def test_vdf_roundtrip_and_escapes() -> None:
    text = (FIX / "libraryfolders.vdf").read_text(encoding="utf-8")
    data = loads(text)
    assert dumps(data) == text  # ida e volta sem mudar nada
    assert steam_libraries(data) == [(r"C:\Program Files (x86)\Steam", 1), (r"D:\SteamLibrary", 2)]
    tricky = {"a": {"b": 'aspas " e \\ barra', "c": {}}}
    assert loads(dumps(tricky)) == tricky
    assert loads('// comentário\n"x" { "y" "1" }') == {"x": {"y": "1"}}
    with pytest.raises(VdfError):
        loads('"x" { "y" "1"')
    with pytest.raises(VdfError):
        loads('"x" "sem fechar')


def test_add_library_never_duplicates() -> None:
    data = loads((FIX / "libraryfolders.vdf").read_text(encoding="utf-8"))
    assert not add_steam_library(data, r"d:\steamlibrary\\")  # mesma pasta
    assert add_steam_library(data, r"E:\SteamLibrary")
    assert steam_libraries(data)[-1] == (r"E:\SteamLibrary", 0)
    assert list(data["libraryfolders"]) == ["0", "1", "2"]  # type: ignore[arg-type]
    empty: dict = {}
    assert add_steam_library(empty, r"E:\Jogos") and steam_libraries(empty) == [(r"E:\Jogos", 0)]


def test_epic_manifest_rewrite_and_launcher_installed() -> None:
    item = json.loads((FIX / "jogo.item").read_text(encoding="utf-8"))
    new = rewrite_epic_manifest(item, r"E:\Epic Games\JogoDeExemplo")
    assert new["InstallLocation"] == r"E:\Epic Games\JogoDeExemplo"
    assert new["ManifestLocation"] == r"E:\Epic Games\JogoDeExemplo/.egstore"
    assert new["StagingLocation"].startswith("E:")
    data: dict = {}
    assert add_launcher_installed(data, new)
    assert not add_launcher_installed(data, new)
    assert data["InstallationList"][0]["AppName"] == "ExemploApp"


def old_pc(tmp_path: Path) -> tuple[FakeRegistry, FakeOldPcFolders, FakeVolumes]:
    folders = FakeOldPcFolders(tmp_path / "C")
    steam = tmp_path / "C" / "Program Files (x86)" / "Steam" / "steamapps"
    steam.mkdir(parents=True)
    (steam / "libraryfolders.vdf").write_bytes((FIX / "libraryfolders.vdf").read_bytes())
    manifests = tmp_path / "C" / "ProgramData" / "Epic" / "EpicGamesLauncher" / "Data" / "Manifests"
    manifests.mkdir(parents=True)
    (manifests / "ABC.item").write_bytes((FIX / "jogo.item").read_bytes())
    reg = FakeRegistry()
    reg.set("HKCU", STEAM_KEY, "SteamPath", "sz", "C:/Program Files (x86)/Steam")
    vols = FakeVolumes()
    vols.add("0000AAAA", "C", tmp_path / "C", system=True)
    vols.add(DATA, "D", tmp_path / "D")
    return reg, folders, vols


def test_collect_skips_system_disk(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    reg, folders, vols = old_pc(tmp_path)
    r = w.recipe()
    report = collect_games(
        reg,
        w.pendrive,
        r,
        vols.volumes(),
        machine=folders.machine(),
        volume_root=folders.volume_root,
    )
    assert report.on_system == [r"C:\Program Files (x86)\Steam"]
    steam, epic = report.added
    assert (steam.launcher, steam.relative_path, steam.games, steam.volume.serial) == (
        "steam",
        "SteamLibrary",
        2,
        DATA,
    )
    assert (epic.launcher, epic.relative_path, epic.name) == (
        "epic",
        r"Epic Games\JogoDeExemplo",
        "Jogo de Exemplo",
    )
    assert epic.manifest is not None and (w.pendrive / "WinKit" / epic.manifest).is_file()
    again = collect_games(
        reg,
        w.pendrive,
        r,
        vols.volumes(),
        machine=folders.machine(),
        volume_root=folders.volume_root,
    )
    assert again.added == []


def _world(tmp_path: Path) -> World:
    w = make_world(tmp_path)
    reg, folders, old_vols = old_pc(tmp_path / "antigo")
    r = w.recipe()
    collect_games(
        reg,
        w.pendrive,
        r,
        old_vols.volumes(),
        machine=folders.machine(),
        volume_root=folders.volume_root,
    )
    r.apps.append(
        AppItem(id="steam", name="Steam", source="winget_online", winget_id="Valve.Steam")
    )
    w.save_recipe(r)
    vols = w.services.volumes
    assert isinstance(vols, FakeVolumes)
    vols.add("0000AAAA", "C", w.system, system=True)
    disk = tmp_path / "disco-E"
    vols.add(DATA, "E", disk)  # a letra mudou de D para E
    (disk / "SteamLibrary" / "steamapps").mkdir(parents=True)
    (disk / "Epic Games" / "JogoDeExemplo").mkdir(parents=True)
    (w.system / "Program Files (x86)" / "Steam" / "steamapps").mkdir(parents=True)
    (w.system / "ProgramData" / "Epic").mkdir(parents=True)
    return w


def test_plan_waits_for_launcher_app(tmp_path: Path) -> None:
    w = _world(tmp_path)
    p = plan(w.recipe(), default_catalogs(), PlanContext(os_major=11, build=26100))
    steam = next(s for s in p.steps if s.kind == "game_library" and "steam" in s.ref)
    assert steam.phase == 2 and steam.depends_on == ("app:steam",)


def test_phase2_links_steam_and_epic_with_current_letter(tmp_path: Path) -> None:
    w = _world(tmp_path)
    run_phase1(w.runtime())
    run_phase2(w.runtime())
    vdf = w.system / "Program Files (x86)" / "Steam" / "steamapps" / "libraryfolders.vdf"
    assert steam_libraries(loads(vdf.read_text(encoding="utf-8"))) == [(r"E:\SteamLibrary", 0)]
    manifest = (
        w.system / "ProgramData" / "Epic" / "EpicGamesLauncher" / "Data" / "Manifests" / "ABC.item"
    )
    assert (
        json.loads(manifest.read_text(encoding="utf-8"))["InstallLocation"]
        == r"E:\Epic Games\JogoDeExemplo"
    )
    installed = w.system / "ProgramData" / "Epic" / "UnrealEngineLauncher" / "LauncherInstalled.dat"
    assert (
        json.loads(installed.read_text(encoding="utf-8"))["InstallationList"][0]["AppName"]
        == "ExemploApp"
    )
    killer = w.services.installers
    assert isinstance(killer, FakeInstallerRunner)
    state = StateStore(w.paths.state).load()
    assert state is not None
    assert all(state.step(k).status == "done" for k in state.steps if k.startswith("game_library:"))


def test_missing_disk_or_launcher_is_skipped(tmp_path: Path) -> None:
    w = _world(tmp_path)
    vols = w.services.volumes
    assert isinstance(vols, FakeVolumes)
    vols.items = [v for v in vols.items if v.serial != DATA]
    run_phase1(w.runtime())
    run_phase2(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None
    reasons = {state.step(k).reason.key for k in state.steps if k.startswith("game_library:")}  # type: ignore[union-attr]
    assert reasons == {"step.game_library.no_volume"}


def test_cli_games(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    reg, folders, vols = old_pc(tmp_path / "antigo")
    services = fake_services(old_pc=folders.base, registry=reg, volumes=vols)
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=services, out=out.append)

    assert run("coletar", "jogos") == 0
    ids = [g.id for g in w.recipe().game_libraries]
    assert len(ids) == 2 and any("Program Files" in line for line in out)
    assert run("jogos", "desmarcar", ids[0]) == 0
    assert [g.selected for g in w.recipe().game_libraries] == [False, True]
    assert run("games", "select", "nada") == 1
