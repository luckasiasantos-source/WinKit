from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from winkit.agent import main as agent_main
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.progress import Choice
from winkit.agent.store import StateStore
from winkit.core.state import models as st
from winkit.platform.environment import single_instance
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.system import FakeAccounts, FakeScheduler


@pytest.fixture
def world(tmp_path: Path) -> World:
    return make_world(tmp_path)


def state(world: World) -> st.AgentState:
    s = StateStore(world.paths.state).load()
    assert s is not None
    return s


def test_phase1_then_phase2_end_to_end(world: World) -> None:
    sc = world.system / "Windows" / "Setup" / "Scripts" / "SetupComplete.cmd"
    sc.write_text(f'@echo off\r\n"{world.paths.agent_exe}" phase1\r\n', encoding="ascii")
    (world.system / "Windows" / "Panther" / "unattend.xml").write_text("<x/>")
    reg = world.services.registry
    assert isinstance(reg, FakeRegistry)
    reg.set(
        "HKLM",
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon",
        "DefaultPassword",
        "sz",
        "x",
    )

    assert run_phase1(world.runtime()) == 0
    s = state(world)
    assert s.phase1.status == "done"
    sched = world.services.scheduler
    assert isinstance(sched, FakeScheduler) and sched.task_exe == world.paths.agent_exe
    accounts = world.services.accounts
    assert isinstance(accounts, FakeAccounts) and "Samuel" in accounts.admins  # H11
    logs = list((world.pendrive / "WinKit" / "Logs").glob("PC-TESTE_*/agente.log"))
    assert logs and "Fase 1" in logs[0].read_text(encoding="utf-8")

    assert run_phase2(world.runtime()) == 0
    s = state(world)
    assert s.step("finalize:summary").status == "done"
    assert s.phase2.status == "done"
    # resumo e atalho
    html = world.paths.summary_html.read_text(encoding="utf-8")
    assert "Resumo do WinKit" in html and "PC-TESTE" in html
    shortcut = world.system / "Users" / "Samuel" / "Desktop" / "Resumo do WinKit.url"
    assert "resumo.html" in shortcut.read_text(encoding="utf-8")
    assert (
        json.loads(world.paths.summary_json.read_text(encoding="utf-8"))["computer"] == "PC-TESTE"
    )
    # limpeza
    assert not sc.exists()
    assert not (world.system / "Windows" / "Panther" / "unattend.xml").exists()
    assert not world.paths.recipe.exists()  # receita local pode ter senha
    assert (
        reg.get("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", "DefaultPassword")
        is None
    )
    assert sched.task_exe is None
    runonce = reg.get("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "WinKitLimpeza")
    assert runonce and "rmdir" in runonce
    assert ("notify", ("WinKit", "WinKit concluído — 1 aviso(s)")) in world.ui.events or any(
        e[0] == "notify" for e in world.ui.events
    )


def test_setupcomplete_with_other_lines_keeps_them(world: World) -> None:
    sc = world.system / "Windows" / "Setup" / "Scripts" / "SetupComplete.cmd"
    sc.write_text(
        f'@echo off\r\ncall oem.cmd\r\n"{world.paths.agent_exe}" phase1\r\n', encoding="ascii"
    )
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    text = sc.read_text(encoding="ascii")
    assert "oem.cmd" in text and "phase1" not in text


def test_phase2_without_phase1_uses_fallback(world: World) -> None:
    r = world.recipe()
    r.tweaks = []
    from tests.factories import tweak

    r.tweaks = [tweak("visual.dark_theme")]
    world.save_recipe(r)
    assert run_phase2(world.runtime()) == 0
    s = state(world)
    step = s.step("tweak:visual.dark_theme")
    assert step.phase_ran == 2  # rodou na Fase 2
    log = (world.paths.logs / "agente.log").read_text(encoding="utf-8")
    assert "fallback" in log


def test_postpone(world: World) -> None:
    world.ui.choice = Choice("postpone")
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    s = state(world)
    assert s.postponed and s.step("finalize:summary").status == "pending"
    world.ui.choice = Choice("start")
    run_phase2(world.runtime())
    assert state(world).step("finalize:summary").status == "done"


def test_second_instance_is_ignored(world: World) -> None:
    with single_instance("WinKitAgent", world.paths.locks) as only:
        assert only
        assert run_phase2(world.runtime()) == 0
    assert StateStore(world.paths.state).load() is None


def test_interrupted_step_is_resumed(world: World) -> None:
    run_phase1(world.runtime())
    s = state(world)
    step_id = next(k for k, v in s.steps.items() if v.status == "pending")
    st.mark_running(s, step_id, 2, s.created_at)
    StateStore(world.paths.state).save(s)
    run_phase2(world.runtime())
    log = (world.paths.logs / "agente.log").read_text(encoding="utf-8")
    assert "interrompidas retomadas" in log


def test_corrupted_state_starts_over(world: World) -> None:
    world.paths.state.parent.mkdir(parents=True, exist_ok=True)
    world.paths.state.write_text("{lixo", encoding="utf-8")
    assert run_phase1(world.runtime()) == 0
    assert state(world).phase1.status == "done"
    assert world.paths.state.with_suffix(".corrompido.json").exists()


def test_missing_recipe_falls_back_to_pendrive(world: World) -> None:
    world.paths.recipe.unlink()
    assert run_phase1(world.runtime()) == 0
    assert state(world).phase1.status == "done"


def test_no_recipe_anywhere(world: World) -> None:
    world.paths.recipe.unlink()
    world.paths.bootstrap.unlink()
    assert run_phase1(world.runtime()) == 0
    assert run_phase2(world.runtime()) == 1
    assert "receita não encontrada" in (world.paths.logs / "agente.log").read_text("utf-8")


def test_retry_resets_failures(world: World) -> None:
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    s = state(world)
    # simula uma falha antiga e pede "tentar de novo"
    any_id = next(k for k in s.steps if k != "finalize:summary")
    s.steps[any_id].status = "failed"
    s.steps[any_id].attempts = 3
    s.steps["finalize:summary"].status = "pending"
    StateStore(world.paths.state).save(s)
    world.bootstrap()
    run_phase2(world.runtime(), retry_failed=True)
    assert state(world).steps[any_id].status != "failed"


def test_nothing_to_do_after_completion(world: World) -> None:
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    world.bootstrap()
    events_before = len(world.ui.events)
    assert run_phase2(world.runtime()) == 0
    assert len(world.ui.events) == events_before  # não perguntou nada


def test_agent_main_never_fails_phase1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))

    def boom():
        raise RuntimeError("falha ao montar o runtime")

    monkeypatch.setattr(agent_main, "build_runtime", boom)
    assert agent_main.main(["phase1"]) == 0
    assert agent_main.main(["phase2"]) == 1
    crash = (tmp_path / "WinKit" / "Logs" / "agente-erro-fatal.log").read_text(encoding="utf-8")
    assert "falha ao montar o runtime" in crash


def test_agent_main_dispatch(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_main, "build_runtime", world.runtime)
    assert agent_main.main(["phase1"]) == 0
    assert agent_main.main(["phase2", "--first-logon"]) == 0
    assert agent_main.main(["retry"]) == 0
    assert agent_main.main(["summary"]) == 0
