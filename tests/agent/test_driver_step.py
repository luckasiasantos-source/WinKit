from __future__ import annotations

from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from winkit.agent.phases import run_phase1
from winkit.agent.store import StateStore
from winkit.builder import target as targets
from winkit.builder.build import BuildOptions, build
from winkit.collector.drivers import export_drivers, list_candidates
from winkit.core.catalog.loader import default_catalogs
from winkit.platform.fakes.disks import FakeDiskInspector, windows_iso
from winkit.platform.fakes.drivers import FakeDriverManager


def _with_drivers(world: World) -> FakeDriverManager:
    mgr = FakeDriverManager()
    r = world.recipe()
    cands = [c for c in list_candidates(mgr, default_catalogs()) if c.recommended]
    export_drivers(mgr, cands, root=world.pendrive, recipe=r)
    world.save_recipe(r)
    build(
        targets.from_folder(world.pendrive),
        FakeDiskInspector(isos={"Windows11.iso": windows_iso()}),
        default_catalogs(),
        BuildOptions(),
        now=world.recipe().meta.created_at,
    )
    world.bootstrap()
    return mgr


@pytest.fixture
def world(tmp_path: Path) -> World:
    return make_world(tmp_path)


def test_drivers_installed_in_priority_order(world: World) -> None:
    _with_drivers(world)
    run_phase1(world.runtime())
    mgr = world.services.drivers
    assert isinstance(mgr, FakeDriverManager)
    names = [p.name for p in mgr.installed]
    assert names[0].startswith("realtek")  # rede primeiro (prioridade 0)
    state = StateStore(world.paths.state).load()
    assert state is not None
    assert all(v.status == "done" for k, v in state.steps.items() if k.startswith("driver:"))


def test_tampered_driver_is_not_installed(world: World) -> None:
    _with_drivers(world)
    inf = next(world.pendrive.glob("WinKit/Drivers/net/*/*.inf"))
    inf.write_text("adulterado")
    run_phase1(world.runtime())
    state = StateStore(world.paths.state).load()
    assert state is not None
    net = next(v for k, v in state.steps.items() if k.startswith("driver:net"))
    assert net.status == "failed" and not net.recoverable
    mgr = world.services.drivers
    assert isinstance(mgr, FakeDriverManager)
    assert not any(p.name.startswith("realtek") for p in mgr.installed)


def test_pnputil_failure_and_reboot(world: World) -> None:
    _with_drivers(world)
    mgr = world.services.drivers
    assert isinstance(mgr, FakeDriverManager)
    mgr.exit_code = 3010
    run_phase1(world.runtime())
    state = StateStore(world.paths.state).load()
    assert state is not None and state.reboot_pending

    (world.tmp / "w2").mkdir()
    world2 = make_world(world.tmp / "w2")
    _with_drivers(world2)
    mgr2 = world2.services.drivers
    assert isinstance(mgr2, FakeDriverManager)
    mgr2.exit_code = 5
    run_phase1(world2.runtime())
    s2 = StateStore(world2.paths.state).load()
    assert s2 is not None
    assert any(
        v.status == "failed" and "código 5" in (v.error or "")
        for k, v in s2.steps.items()
        if k.startswith("driver:")
    )


def test_missing_manifest_fails_closed(world: World) -> None:
    _with_drivers(world)
    (world.pendrive / "WinKit" / "manifesto.json").unlink()
    run_phase1(world.runtime())
    state = StateStore(world.paths.state).load()
    assert state is not None
    assert all(v.status == "failed" for k, v in state.steps.items() if k.startswith("driver:"))
