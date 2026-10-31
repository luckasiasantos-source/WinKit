"""Manutenção (V2-18): especificação da tarefa, etapas, Sensor de Armazenamento e CLI."""

from __future__ import annotations

from pathlib import Path

from tests.agent.helpers import World, make_world
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.core.catalog.loader import default_catalogs
from winkit.core.maintenance import TASK_FOLDER, WINGET_TASK, winget_task
from winkit.core.planner.models import PlanContext
from winkit.core.planner.planner import TWEAK_STORAGE_SENSE, plan
from winkit.core.recipe.models import Maintenance
from winkit.platform.fakes.services import fake_services
from winkit.platform.fakes.system import FakeScheduler

WINGET = r"C:\Users\Samuel\AppData\Local\Microsoft\WindowsApps\winget.exe"


def test_task_spec_is_pure_and_complete() -> None:
    assert winget_task(Maintenance(), WINGET, "log") is None
    weekly = winget_task(
        Maintenance(winget_upgrade="weekly", winget_day="sat"), WINGET, r"C:\x.log"
    )
    assert weekly is not None
    assert (weekly.folder, weekly.name, weekly.day, weekly.time) == (
        TASK_FOLDER,
        WINGET_TASK,
        "Saturday",
        "12:00",
    )
    assert weekly.weeks_interval == 1 and weekly.execute == WINGET
    for flag in (
        "upgrade",
        "--all",
        "--silent",
        "--disable-interactivity",
        "--accept-source-agreements",
    ):
        assert flag in weekly.arguments
    assert '--log "C:\\x.log"' in weekly.arguments
    monthly = winget_task(Maintenance(winget_upgrade="monthly"), WINGET, "l")
    assert monthly is not None and monthly.weeks_interval == 4
    assert monthly.signature != weekly.signature
    assert (
        winget_task(Maintenance(winget_upgrade="weekly", winget_day="sat"), WINGET, r"C:\x.log")
        == weekly
    )


def test_plan_phases_and_storage_sense(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    r = w.recipe()
    r.maintenance = Maintenance(winget_upgrade="weekly", storage_sense=True)
    p = plan(r, default_catalogs(), PlanContext(os_major=11, build=26100))
    defrag = p.step("maintenance:defrag")
    winget = p.step("maintenance:winget")
    assert defrag is not None and defrag.phase == 1
    assert winget is not None and (winget.phase, winget.target) == (2, "user_profile")  # R27
    sense = p.step(f"tweak:{TWEAK_STORAGE_SENSE}")
    assert sense is not None and sense.target == "default_profile"


def _world(tmp_path: Path, m: Maintenance) -> World:
    w = make_world(tmp_path)
    r = w.recipe()
    r.maintenance = m
    w.save_recipe(r)
    winget = w.system / "Users" / "Samuel" / "AppData" / "Local" / "Microsoft" / "WindowsApps"
    winget.mkdir(parents=True)
    (winget / "winget.exe").write_bytes(b"MZ")
    return w


def test_install_creates_user_task_and_enables_defrag(tmp_path: Path) -> None:
    w = _world(tmp_path, Maintenance(winget_upgrade="monthly", winget_time="03:00"))
    run_phase1(w.runtime())
    sched = w.services.scheduler
    assert isinstance(sched, FakeScheduler)
    assert sched.builtin["ScheduledDefrag"] is True
    assert sched.user_tasks == {}
    run_phase2(w.runtime())
    (spec,) = sched.user_tasks.values()
    assert spec.weeks_interval == 4 and spec.time == "03:00"
    assert spec.execute.endswith("WindowsApps\\winget.exe")
    assert "ProgramData" in spec.arguments  # log fora do perfil
    state = StateStore(w.paths.state).load()
    assert state is not None
    assert state.step("maintenance:winget").status == "done"
    assert state.step("maintenance:defrag").status == "done"


def test_without_winget_the_task_is_skipped(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    r = w.recipe()
    r.maintenance = Maintenance(winget_upgrade="weekly")
    w.save_recipe(r)
    run_phase1(w.runtime())
    run_phase2(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("maintenance:winget").status == "skipped"


def test_live_preview_then_already_done(tmp_path: Path) -> None:
    w = _world(tmp_path, Maintenance(winget_upgrade="weekly"))
    kinds = frozenset({"maintenance"})
    opts = {"root": w.pendrive, "restore_point": False, "only_kinds": kinds}
    first = run_live(w.runtime(), LiveOptions(simulate=True, **opts))  # type: ignore[arg-type]
    assert first.preview is not None
    assert {i.status for i in first.preview.items} == {"will_change"}
    run_live(w.runtime(), LiveOptions(**opts))  # type: ignore[arg-type]
    again = run_live(w.runtime(), LiveOptions(simulate=True, **opts))  # type: ignore[arg-type]
    assert again.preview is not None
    assert {i.status for i in again.preview.items} == {"already_done"}


def test_cli_maintenance(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    sched = FakeScheduler()
    services = fake_services(scheduler=sched)
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=services, out=out.append)

    assert run("manutencao", "definir", "--winget", "semanal", "--dia", "fri", "--sensor") == 0
    m = w.recipe().maintenance
    assert (m.winget_upgrade, m.winget_day, m.storage_sense) == ("weekly", "fri", True)
    assert run("maintenance", "set", "--winget", "off", "--no-sensor", "--no-desfragmentar") == 0
    m = w.recipe().maintenance
    assert (m.winget_upgrade, m.storage_sense, m.ensure_defrag_schedule) == ("off", False, False)
    spec = winget_task(Maintenance(winget_upgrade="weekly"), WINGET, "l")
    assert spec is not None
    sched.ensure_user_task(spec)
    assert run("manutencao", "remover-do-pc") == 0
    assert sched.user_tasks == {}
