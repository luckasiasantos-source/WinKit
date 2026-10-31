from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from tests.factories import app, backup
from winkit.agent.eventlog import EventLog
from winkit.agent.phases import open_session
from winkit.agent.steps.base import StepContext, StepResult
from winkit.i18n import legacy, render


@dataclass
class Scripted:
    """Etapa falsa: devolve resultados por id e registra execuções."""

    results: dict[str, StepResult | Exception] = field(default_factory=dict)
    already: set[str] = field(default_factory=set)
    ran: list[str] = field(default_factory=list)

    def check(self, ctx: StepContext) -> bool:
        return ctx.step.id in self.already

    def run(self, ctx: StepContext) -> StepResult:
        self.ran.append(ctx.step.id)
        res = self.results.get(ctx.step.id, StepResult.ok())
        if isinstance(res, Exception):
            raise res
        return res


@pytest.fixture
def world(tmp_path: Path) -> World:
    w = make_world(tmp_path)
    r = w.recipe()
    r.apps = [app("a"), app("b", depends_on=["a"]), app("c"), app("w", source="winget_online")]
    r.backups = [backup("bk")]
    r.updates.windows_update_after_install = False
    r.updates.block_wu_driver_replacement = False
    r.bloatware.disable_consumer_content = False
    w.save_recipe(r)
    return w


def session(world: World, scripted: Scripted, phase: int = 1):
    rt = world.runtime()
    for kind in ("app", "backup", "driver", "tweak"):
        rt.handlers[kind] = scripted  # type: ignore[index]
    log = EventLog(rt.paths.logs, rt.clock)
    s = open_session(rt, log, phase=phase)
    assert s is not None
    return s


def test_failure_is_isolated_and_dependents_skipped(world: World) -> None:
    scripted = Scripted(results={"app:a": RuntimeError("boom")})
    s = session(world, scripted)
    s.executor(world.ui).run_phase(1)
    states = {k: v.status for k, v in s.state.steps.items()}
    assert states["app:a"] == "failed"
    assert "boom" in render(s.state.step("app:a").error)
    assert states["app:c"] == "done"  # seguiu adiante (P4)
    assert states["backup:bk"] == "done"
    # b depende de a; a falhou mas ainda pode ser tentado de novo → b espera
    assert states["app:b"] == "pending"


def test_dependency_with_final_failure_skips(world: World) -> None:
    scripted = Scripted(results={"app:a": StepResult.failed(legacy("hash"), recoverable=False)})
    s = session(world, scripted)
    s.executor(world.ui).run_phase(1)
    assert s.state.step("app:b").status == "skipped"
    assert "app:a" in render(s.state.step("app:b").reason)


def test_check_marks_done_without_running(world: World) -> None:
    scripted = Scripted(already={"app:c"})
    s = session(world, scripted)
    s.executor(world.ui).run_phase(1)
    assert "app:c" not in scripted.ran
    assert s.state.step("app:c").status == "done"
    assert render(s.state.step("app:c").reason) == "já estava feito"


def test_missing_pendrive_defers_without_spending_attempts(world: World) -> None:
    world.env.roots = []
    scripted = Scripted()
    s = session(world, scripted)
    s.executor(world.ui).run_phase(1)
    st_a = s.state.step("app:a")
    assert st_a.status == "pending" and st_a.attempts == 0
    assert "pendrive" in render(st_a.reason).lower()
    assert world.sleeps  # esperou antes de desistir
    assert ("waiting", ("pendrive", True)) in world.ui.events
    assert scripted.ran == []


def test_pendrive_coming_back_during_wait(world: World) -> None:
    roots = world.env.roots
    world.env.roots = []

    def sleep(seconds: float) -> None:
        world.sleeps.append(seconds)
        world.env.roots = roots

    rt = world.runtime()
    rt.sleep = sleep
    rt.handlers["app"] = rt.handlers["backup"] = Scripted()  # type: ignore[index]
    s = open_session(rt, EventLog(rt.paths.logs, rt.clock), phase=1)
    assert s is not None
    s.executor(world.ui).run_phase(1)
    assert s.state.step("app:a").status == "done"


def test_no_network_defers_winget(world: World) -> None:
    world.env.internet = False
    scripted = Scripted()
    s = session(world, scripted, phase=2)
    s.executor(world.ui).run_phase(2)
    assert s.state.step("app:w").status == "pending"
    assert "internet" in render(s.state.step("app:w").reason)


def test_deferred_result_returns_to_pending(world: World) -> None:
    scripted = Scripted(results={"app:c": StepResult.deferred(legacy("esperando"))})
    s = session(world, scripted)
    out = s.executor(world.ui).run_phase(1)
    assert out.deferred >= 1
    assert s.state.step("app:c").status == "pending"
    assert s.state.step("app:c").attempts == 0


def test_reboot_flag(world: World) -> None:
    scripted = Scripted(results={"app:c": StepResult.ok(reboot=True)})
    s = session(world, scripted)
    assert s.executor(world.ui).run_phase(1).reboot_required


def test_unselected_user_choice_is_skipped(world: World) -> None:
    r = world.recipe()
    r.apps[2].decide_at_runtime = True  # c
    world.save_recipe(r)
    scripted = Scripted()
    s = session(world, scripted, phase=2)
    s.executor(world.ui).run_phase(2, selection=frozenset())
    assert s.state.step("app:c").status == "skipped"
    assert render(s.state.step("app:c").reason) == "desmarcado na janela"


def test_state_is_persisted_after_each_step(world: World) -> None:
    scripted = Scripted()
    s = session(world, scripted)
    s.executor(world.ui).run_phase(1)
    saved = s.store.load()
    assert saved is not None and saved.step("app:a").status == "done"


def test_progress_events(world: World) -> None:
    s = session(world, Scripted())
    s.executor(world.ui).run_phase(1)
    progress = [e for e in world.ui.events if e[0] == "progress"]
    assert progress[0][1][0] == 0 and progress[-1][1][0] == progress[-1][1][1]
