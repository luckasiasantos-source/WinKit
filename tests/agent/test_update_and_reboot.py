from __future__ import annotations

from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.store import StateStore
from winkit.core.state.models import AgentState
from winkit.i18n import render
from winkit.platform.fakes.apps import FakeShortcuts
from winkit.platform.fakes.system_tweaks import FakeSession, FakeUpdater
from winkit.platform.windows_update import UpdateResult


def state(w: World) -> AgentState:
    s = StateStore(w.paths.state).load()
    assert s is not None
    return s


def updater(w: World) -> FakeUpdater:
    u = w.services.updater
    assert isinstance(u, FakeUpdater)
    return u


def session(w: World) -> FakeSession:
    s = w.services.session
    assert isinstance(s, FakeSession)
    return s


@pytest.fixture
def world(tmp_path: Path) -> World:
    return make_world(tmp_path)


def run_all(w: World) -> None:
    run_phase1(w.runtime())
    run_phase2(w.runtime())


@pytest.mark.parametrize(
    ("res", "status", "note"),
    [
        (UpdateResult(0, 2, False), "done", "nenhuma atualização"),
        (UpdateResult(3, 2, True, ("KB1",)), "done", "3 atualizações instaladas"),
        (UpdateResult(3, 3, False), "done", "algumas com erro"),
        (UpdateResult(3, 4, False), "failed", "código 4"),
    ],
)
def test_windows_update_results(world: World, res: UpdateResult, status: str, note: str) -> None:
    updater(world).result = res
    run_all(world)
    st = state(world).step("windows_update:all")
    assert st.status == status
    assert note in (render(st.reason) + render(st.error))


def test_windows_update_drivers_flag_and_disabled(world: World) -> None:
    r = world.recipe()
    r.updates.include_drivers_from_windows_update = True
    world.save_recipe(r)
    run_all(world)
    assert updater(world).calls == [True]
    (world.tmp / "b").mkdir()
    w2 = make_world(world.tmp / "b")
    r2 = w2.recipe()
    r2.updates.windows_update_after_install = False
    w2.save_recipe(r2)
    run_all(w2)
    assert updater(w2).calls == []


def test_reboot_ask_yes_and_no(world: World) -> None:
    world.ui.reboot_answer = True
    run_all(world)
    assert session(world).reboots and session(world).reboots[0][0] == 15
    (world.tmp / "b").mkdir()
    w2 = make_world(world.tmp / "b")
    run_all(w2)
    assert session(w2).reboots == []
    assert ("ask_reboot", None) in w2.ui.events


@pytest.mark.parametrize(("idle", "rebooted"), [(600.0, True), (10.0, False)])
def test_reboot_auto_if_idle(world: World, idle: float, rebooted: bool) -> None:
    r = world.recipe()
    r.execution.reboot_policy = "auto_if_idle"
    world.save_recipe(r)
    session(world).idle = idle
    run_all(world)
    assert bool(session(world).reboots) is rebooted
    assert any(e[0] == "notify" for e in world.ui.events)


def test_reboot_never(world: World) -> None:
    r = world.recipe()
    r.execution.reboot_policy = "never"
    world.save_recipe(r)
    run_all(world)
    assert session(world).reboots == []
    assert ("ask_reboot", None) not in world.ui.events


def test_failure_keeps_agent_and_creates_retry_shortcut(world: World) -> None:
    updater(world).result = UpdateResult(1, 4, False)
    for _ in range(3):  # esgota as tentativas da etapa que falha
        run_all(world)
    s = state(world)
    assert s.step("windows_update:all").status == "failed"
    assert s.step("finalize:summary").status == "done"
    sc = world.services.shortcuts
    assert isinstance(sc, FakeShortcuts)
    retry = [c for c in sc.created if c[2] == "retry"]
    assert retry and retry[0][1].endswith("winkit-agent.exe")
    from winkit.platform.fakes.registry import FakeRegistry

    reg = world.services.registry
    assert isinstance(reg, FakeRegistry)
    assert (
        reg.get("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "WinKitLimpeza")
        is None
    )  # Agente mantido para "tentar de novo"
    html = world.paths.summary_html.read_text(encoding="utf-8")
    assert "Falhas" in html and "Windows Update" in html
