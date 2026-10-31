from __future__ import annotations

from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from tests.factories import backup
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.store import StateStore
from winkit.core import layout
from winkit.core.state.models import AgentState


def state(w: World) -> AgentState:
    s = StateStore(w.paths.state).load()
    assert s is not None
    return s


def put(w: World, backup_id: str, files: dict[str, str]) -> None:
    dados = layout.payload(w.pendrive, f"Perfis/padrao/Backups/{backup_id}/dados")
    for rel, content in files.items():
        (dados / rel).parent.mkdir(parents=True, exist_ok=True)
        (dados / rel).write_text(content)


@pytest.fixture
def world(tmp_path: Path) -> World:
    w = make_world(tmp_path)
    r = w.recipe()
    r.backups = [
        backup("discord", "{APPDATA}\\discord"),
        backup("rarreg", "{PROGRAMFILES}\\WinRAR\\rarreg.key", kind="file"),
        backup("jogo", "{ABS:Z:\\Jogos\\Save}"),
        backup("cfg", "{LOCALAPPDATA}\\App\\cfg", on_conflict="overwrite"),
    ]
    w.save_recipe(r)
    put(w, "discord", {"settings.json": "novo", "sub/x.txt": "x"})
    put(w, "rarreg", {"rarreg.key": "licença"})
    put(w, "jogo", {"save.dat": "s"})
    put(w, "cfg", {"a.ini": "do backup"})
    return w


def test_phase1_restores_into_default_profile(world: World) -> None:
    run_phase1(world.runtime())
    default = world.system / "Users" / "Default"
    assert (default / "AppData" / "Roaming" / "discord" / "settings.json").read_text() == "novo"
    assert (default / "AppData" / "Roaming" / "discord" / "sub" / "x.txt").exists()
    assert (world.system / "Program Files" / "WinRAR" / "rarreg.key").read_text() == "licença"
    s = state(world)
    assert s.step("backup:discord").phase_ran == 1
    assert s.step("backup:rarreg").status == "done"
    assert s.step("backup:jogo").status == "pending"  # {ABS} fica para a Fase 2


def test_absolute_path_with_missing_drive_is_skipped(world: World) -> None:
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    st = state(world).step("backup:jogo")
    assert st.status == "skipped" and "Z:" in (st.reason or "")


def test_merge_keeps_existing_and_overwrite_replaces(world: World) -> None:
    default = world.system / "Users" / "Default" / "AppData"
    (default / "Roaming" / "discord").mkdir(parents=True)
    (default / "Roaming" / "discord" / "settings.json").write_text("já existia")
    (default / "Local" / "App" / "cfg").mkdir(parents=True)
    (default / "Local" / "App" / "cfg" / "a.ini").write_text("antigo")
    run_phase1(world.runtime())
    assert (default / "Roaming" / "discord" / "settings.json").read_text() == "já existia"
    assert (default / "Roaming" / "discord" / "sub" / "x.txt").exists()
    assert (default / "Local" / "App" / "cfg" / "a.ini").read_text() == "do backup"


def test_fallback_restores_into_user_profile(world: World) -> None:
    run_phase2(world.runtime())
    user = world.system / "Users" / "Samuel" / "AppData" / "Roaming" / "discord"
    assert (user / "settings.json").read_text() == "novo"


def test_skip_policy_and_missing_backup(world: World) -> None:
    r = world.recipe()
    r.backups[0].on_conflict = "skip"
    r.backups.append(backup("sumiu", "{APPDATA}\\Sumiu"))
    world.save_recipe(r)
    default = world.system / "Users" / "Default" / "AppData" / "Roaming" / "discord"
    default.mkdir(parents=True)
    run_phase1(world.runtime())
    s = state(world)
    assert s.step("backup:discord").reason == "já estava feito"
    assert not (default / "settings.json").exists()
    assert s.step("backup:sumiu").status == "failed"
