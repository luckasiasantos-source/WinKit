from __future__ import annotations

from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from tests.core.test_installer_detect import fake_pe
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.store import StateStore
from winkit.builder import target as targets
from winkit.builder.build import BuildOptions, build
from winkit.collector.apps import add_local_installer
from winkit.core.catalog.loader import default_catalogs
from winkit.core.inventory import InstalledApp
from winkit.core.recipe.models import AfterInstall, AppItem, AutostartEntry, ShortcutSpec
from winkit.core.state.models import AgentState
from winkit.i18n import render
from winkit.platform.fakes.apps import FakeInstallerRunner, FakeInventory, FakeShortcuts, FakeWinget
from winkit.platform.fakes.disks import FakeDiskInspector, windows_iso
from winkit.platform.fakes.registry import FakeRegistry

CAT = default_catalogs()
RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"


def rebuild(world: World) -> None:
    build(
        targets.from_folder(world.pendrive),
        FakeDiskInspector(isos={"Windows11.iso": windows_iso()}),
        CAT,
        BuildOptions(),
        now=world.recipe().meta.created_at,
    )
    world.bootstrap()


def state(world: World) -> AgentState:
    s = StateStore(world.paths.state).load()
    assert s is not None
    return s


@pytest.fixture
def world(tmp_path: Path) -> World:
    w = make_world(tmp_path)
    src = tmp_path / "setup.exe"
    src.write_bytes(fake_pe([".text"], b"Nullsoft.NSIS"))
    r = w.recipe()
    item = add_local_installer(w.pendrive, r, src, name="Ferramenta", catalogs=CAT)
    item.after_install = AfterInstall(
        kill_processes=["ferramenta.exe"],
        disable_autostart=[AutostartEntry(hive="HKCU", value="Ferramenta")],
    )
    r.apps.append(
        AppItem(
            id="discord",
            name="Discord",
            source="winget_online",
            scope="user",
            winget_id="Discord.Discord",
        )
    )
    w.save_recipe(r)
    rebuild(w)
    return w


def installers(w: World) -> FakeInstallerRunner:
    x = w.services.installers
    assert isinstance(x, FakeInstallerRunner)
    return x


def winget(w: World) -> FakeWinget:
    x = w.services.winget
    assert isinstance(x, FakeWinget)
    return x


def test_offline_app_in_phase1_and_winget_in_phase2(world: World) -> None:
    reg = world.services.registry
    assert isinstance(reg, FakeRegistry)
    reg.set("HKLM", RUN, "Ferramenta", "sz", "x.exe")
    run_phase1(world.runtime())
    assert installers(world).ran == [("setup.exe", ("/S",), "machine")]
    assert installers(world).killed == ["ferramenta.exe"]
    assert reg.get("HKLM", RUN, "Ferramenta") is None
    assert state(world).step("app:ferramenta").status == "done"
    assert not (world.paths.base / "cache").exists() or not any(
        (world.paths.base / "cache").iterdir()
    )
    run_phase2(world.runtime())
    assert ("install", "Discord.Discord", "user", "winget") in winget(world).calls
    assert state(world).step("app:discord").status == "done"


def test_installer_exit_codes(world: World) -> None:
    installers(world).exit_code = 3010
    run_phase1(world.runtime())
    s = state(world)
    assert s.step("app:ferramenta").status == "done" and s.reboot_pending


def test_installer_failure_hint(world: World) -> None:
    installers(world).exit_code = 1603
    run_phase1(world.runtime())
    err = render(state(world).step("app:ferramenta").error)
    assert "1603" in err and "Instale manualmente" in err


def test_installer_timeout(world: World) -> None:
    installers(world).timed_out = True
    run_phase1(world.runtime())
    assert "tempo limite" in render(state(world).step("app:ferramenta").error)


def test_tampered_installer(world: World) -> None:
    next(world.pendrive.glob("WinKit/Apps/ferramenta/local/*.exe")).write_bytes(b"virus")
    run_phase1(world.runtime())
    st = state(world).step("app:ferramenta")
    assert st.status == "failed" and not st.recoverable
    assert installers(world).ran == []


def test_already_installed_is_detected(world: World) -> None:
    inv = world.services.inventory
    assert isinstance(inv, FakeInventory)
    inv.apps = [InstalledApp(name="Ferramenta", scope="machine")]
    run_phase1(world.runtime())
    assert installers(world).ran == []
    assert render(state(world).step("app:ferramenta").reason) == "já estava feito"


def test_winget_registers_and_waits(world: World) -> None:
    w = winget(world)
    w.is_available = False
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    assert w.registered == 1
    assert state(world).step("app:discord").status == "done"


def test_winget_never_available_defers(world: World) -> None:
    w = winget(world)
    w.is_available = False
    w.become_available_after_register = False
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    st = state(world).step("app:discord")
    assert st.status == "pending" and "winget" in render(st.reason)
    assert ("waiting", ("winget", True)) in world.ui.events


def test_winget_failure_code(world: World) -> None:
    winget(world).install_code = 0x8A150011
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    assert "0x8A150011" in render(state(world).step("app:discord").error)


def test_winget_already_installed_check(world: World) -> None:
    winget(world).installed_ids.add("Discord.Discord")
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    assert not [c for c in winget(world).calls if c[0] == "install"]


def test_portable_shortcuts(world: World) -> None:
    from tests.factories import backup

    r = world.recipe()
    r.backups.append(backup("port", "{ABS:Q:\\Portateis\\Tool}"))
    r.apps.append(
        AppItem(
            id="tool",
            name="Tool",
            source="portable",
            portable_backup="port",
            after_install=AfterInstall(
                shortcuts=[
                    ShortcutSpec(name="Tool", target="{ABS:Q:\\Portateis\\Tool}\\tool.exe"),
                    ShortcutSpec(
                        name="Tool",
                        target="{ABS:Q:\\Portateis\\Tool}\\tool.exe",
                        location="desktop",
                    ),
                ]
            ),
        )
    )
    (world.pendrive / "WinKit" / "Perfis" / "padrao" / "Backups" / "port" / "dados").mkdir(
        parents=True
    )
    world.save_recipe(r)
    rebuild(world)
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    sc = world.services.shortcuts
    assert isinstance(sc, FakeShortcuts)
    # Q: não existe: o backup é pulado e o atalho também (dependência), sem tocar em disco real
    assert state(world).step("backup:port").status == "skipped"
    assert state(world).step("shortcut:tool").status == "skipped"
    assert sc.created == []


def test_portable_shortcuts_created(world: World) -> None:
    from tests.factories import backup

    r = world.recipe()
    r.backups.append(backup("port2", "{LOCALAPPDATA}\\Programs\\Tool"))
    r.apps.append(
        AppItem(
            id="tool2",
            name="Tool",
            source="portable",
            portable_backup="port2",
            after_install=AfterInstall(
                shortcuts=[
                    ShortcutSpec(name="Tool", target="{LOCALAPPDATA}\\Programs\\Tool\\tool.exe"),
                    ShortcutSpec(
                        name="Tool",
                        target="{LOCALAPPDATA}\\Programs\\Tool\\tool.exe",
                        location="desktop",
                    ),
                ]
            ),
        )
    )
    (world.pendrive / "WinKit" / "Perfis" / "padrao" / "Backups" / "port2" / "dados").mkdir(
        parents=True
    )
    world.save_recipe(r)
    rebuild(world)
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    sc = world.services.shortcuts
    assert isinstance(sc, FakeShortcuts)
    assert state(world).step("shortcut:tool2").status == "done"
    names = sorted(p.parent.name for p, _, _ in sc.created)
    assert names == ["Desktop", "Programs"]
    assert all(t.endswith("tool.exe") and "Programs" in t for _, t, _ in sc.created)
