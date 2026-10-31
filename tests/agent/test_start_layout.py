"""Iniciar e barra (V2-04): XML/JSON com snapshot (R-42), leitura dos fixados e etapa."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from tests.agent.helpers import World, make_world
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.collector.start_layout import collect_start_layout
from winkit.core.recipe.models import PinRef
from winkit.core.start_layout import NS, START2_DIR, start_json, taskbar_xml
from winkit.platform.fakes.backup import FakeOldPcFolders
from winkit.platform.fakes.services import fake_services

SNAP = Path(__file__).resolve().parents[1] / "fixtures" / "start_layout"
PINS = [
    PinRef(
        kind="desktop_link",
        value=r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Firefox.lnk",
        name="Firefox",
    ),
    PinRef(
        kind="packaged_app",
        value="Microsoft.WindowsCalculator_8wekyb3d8bbwe!App",
        name="Calculadora",
    ),
    PinRef(
        kind="desktop_link", value=r"%ALLUSERSPROFILE%\x & <y>.lnk", name="Escapado", selected=True
    ),
    PinRef(kind="desktop_link", value=r"%APPDATA%\nao.lnk", name="Desmarcado", selected=False),
]


def _snapshot(name: str, data: bytes) -> None:
    path = SNAP / name
    if not path.exists():  # pragma: no cover — primeira geração
        path.write_bytes(data)
    assert data == path.read_bytes()


def test_taskbar_xml_snapshot_and_namespaces() -> None:
    data = taskbar_xml(PINS)
    _snapshot("LayoutModification.xml", data)
    root = ET.fromstring(data)  # o XML continua válido e com os namespaces da Microsoft
    tb = "{" + NS["xmlns:taskbar"] + "}"
    assert root.tag == "{" + NS["xmlns"] + "}LayoutModificationTemplate"
    pins = list(root.iter(f"{tb}DesktopApp")) + list(root.iter(f"{tb}UWA"))
    assert len(pins) == 3  # o desmarcado fica de fora
    assert any(
        p.get("DesktopApplicationLinkPath") == r"%ALLUSERSPROFILE%\x & <y>.lnk" for p in pins
    )
    assert b"ns0:" not in data and b"register" not in data


def test_start_json_snapshot() -> None:
    data = start_json(PINS)
    _snapshot("LayoutModification.json", data)
    pinned = json.loads(data)["pinnedList"]
    assert pinned[1] == {"packagedAppId": "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"}
    assert len(pinned) == 3


def old_pc(tmp_path: Path) -> FakeOldPcFolders:
    folders = FakeOldPcFolders(tmp_path / "C")
    roaming = tmp_path / "C" / "Users" / "Samuel" / "AppData" / "Roaming" / "Microsoft"
    user_menu = roaming / "Windows" / "Start Menu" / "Programs"
    (user_menu / "Mozilla").mkdir(parents=True)
    (user_menu / "Mozilla" / "Firefox.lnk").write_bytes(b"L")
    (user_menu / "Desinstalar X.lnk").write_bytes(b"L")
    (user_menu / "Uninstall Y.lnk").write_bytes(b"L")
    machine_menu = (
        tmp_path / "C" / "ProgramData" / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    )
    machine_menu.mkdir(parents=True)
    (machine_menu / "Visual Studio Code.lnk").write_bytes(b"L")
    taskbar = roaming / "Internet Explorer" / "Quick Launch" / "User Pinned" / "TaskBar"
    taskbar.mkdir(parents=True)
    for name in ("Firefox", "Visual Studio Code", "File Explorer"):
        (taskbar / f"{name}.lnk").write_bytes(b"L")
    local = tmp_path / "C" / "Users" / "Samuel" / "AppData" / "Local"
    start2 = local.joinpath(*START2_DIR[2:])
    start2.mkdir(parents=True)
    (start2 / "start2.bin").write_bytes(b"\x00start")
    return folders


def test_collect_links_taskbar_to_start_menu(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    folders = old_pc(tmp_path)
    r = w.recipe()
    pinned, orphans = collect_start_layout(
        r,
        w.pendrive,
        {**folders.machine(), **folders.current_user()},
        folders.volume_root,
        build=26100,
    )
    s = r.start_layout
    assert pinned == 2 and orphans == ["File Explorer"]
    assert [p.value for p in s.taskbar_pins] == [
        r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Mozilla\Firefox.lnk",
        r"%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\Visual Studio Code.lnk",
    ]
    names = {p.name for p in s.start_pins}
    assert names == {"Firefox", "Visual Studio Code", "Desinstalar X", "Uninstall Y"}
    assert not any(p.selected for p in s.start_pins)  # o usuário escolhe
    assert s.start_file and s.source_build == 26100 and s.mode == "list"


def _world(tmp_path: Path, mode: str = "list", build: int = 26100) -> World:
    w = make_world(tmp_path)
    folders = old_pc(tmp_path)
    r = w.recipe()
    collect_start_layout(
        r,
        w.pendrive,
        {**folders.machine(), **folders.current_user()},
        folders.volume_root,
        build=build,
    )
    r.start_layout.mode = mode  # type: ignore[assignment]
    r.start_layout.start_pins[0].selected = True
    w.save_recipe(r)
    return w


def test_phase1_writes_default_profile_files(tmp_path: Path) -> None:
    w = _world(tmp_path)
    run_phase1(w.runtime())
    shell = w.system / "Users" / "Default" / "AppData" / "Local" / "Microsoft" / "Windows" / "Shell"
    assert b"Firefox.lnk" in (shell / "LayoutModification.xml").read_bytes()
    assert json.loads((shell / "LayoutModification.json").read_text(encoding="utf-8"))["pinnedList"]


def test_exact_copy_only_on_same_build(tmp_path: Path) -> None:
    w = _world(tmp_path, "exact")
    run_phase1(w.runtime())
    profile = w.system / "Users" / "Default"
    assert profile.joinpath(*START2_DIR, "start2.bin").read_bytes() == b"\x00start"

    (tmp_path / "outro").mkdir()
    w2 = _world(tmp_path / "outro", "exact", build=22631)
    run_phase1(w2.runtime())
    assert not (w2.system / "Users" / "Default").joinpath(*START2_DIR, "start2.bin").exists()
    state = StateStore(w2.paths.state).load()
    assert state is not None
    assert any(m.key == "summary.start_exact_other_build" for m in state.warnings)


def test_not_live_and_skipped_in_fallback(tmp_path: Path) -> None:
    w = _world(tmp_path)
    preview = run_live(
        w.runtime(), LiveOptions(root=w.pendrive, simulate=True, restore_point=False)
    )
    assert preview.preview is not None and "start_layout:default" in preview.preview.not_live_safe
    run_phase2(w.runtime())  # a Fase 1 não rodou
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("start_layout:default").status == "skipped"


def test_cli_start(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    folders = old_pc(tmp_path)
    out: list[str] = []
    services = fake_services(old_pc=folders.base)
    code = cli.main(
        ["coletar", "iniciar", "--modo", "exact", "--raiz", str(w.pendrive)],
        services=services,
        out=out.append,
    )
    assert code == 0
    assert w.recipe().start_layout.mode == "exact"
    assert any("File Explorer" in line for line in out)
