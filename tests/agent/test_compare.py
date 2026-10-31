"""Relatório antes/depois (V2-19): comparação pura, inventário e seção do resumo."""

from __future__ import annotations

from pathlib import Path

from tests.agent.helpers import World, make_world
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.store import StateStore
from winkit.collector.snapshot import take_snapshot, write_before
from winkit.core.catalog.loader import default_catalogs
from winkit.core.compare import compare, normalize_name
from winkit.core.devices import ProblemDevice
from winkit.core.inventory import InstalledApp
from winkit.core.inventory_snapshot import SnapApp, SnapDevice, Snapshot
from winkit.platform.fakes.apps import FakeInventory
from winkit.platform.fakes.system_tweaks import FakeDevices, FakeFeatures

NAMES = {"wsl": "WSL"}


def test_normalize_names() -> None:
    assert normalize_name("7-Zip 24.08 (x64)") == normalize_name("7-Zip 23.01")
    assert normalize_name("Mozilla Firefox (x64 pt-BR)") != normalize_name("Mozilla Thunderbird")


def snap(apps: list[SnapApp], devices: list[SnapDevice], features: list[str]) -> Snapshot:
    return Snapshot(apps=apps, devices=devices, features=features)


WIFI = SnapDevice(name="Wi-Fi", hardware_ids=("PCI\\VEN_8086&DEV_2725",), code=0)
GPU = SnapDevice(name="Placa de vídeo", hardware_ids=("PCI\\VEN_10DE&DEV_2484",), code=0)


def test_compare_same_hardware() -> None:
    before = snap(
        [
            SnapApp(name="Firefox", winget_id="Mozilla.Firefox"),
            SnapApp(name="7-Zip 23.01"),
            SnapApp(name="OBS Studio"),
        ],
        [WIFI, GPU],
        ["wsl"],
    )
    after = snap(
        [
            SnapApp(name="Mozilla Firefox (x64 pt-BR)", winget_id="Mozilla.Firefox"),
            SnapApp(name="7-Zip 24.08 (x64)"),
        ],
        [WIFI, GPU.model_copy(update={"code": 28})],
        [],
    )
    c = compare(before, after, NAMES)
    assert c.missing_apps == ["OBS Studio"]  # o Firefox casa pelo id, o 7-Zip pelo nome
    assert c.driverless == ["Placa de vídeo"]
    assert c.missing_features == ["WSL"]
    assert c.same_hardware and not c.empty


def test_other_hardware_skips_drivers() -> None:
    other = SnapDevice(name="Outro", hardware_ids=("PCI\\VEN_1022&DEV_1234",), code=28)
    c = compare(snap([], [WIFI, GPU], []), snap([], [other], []), NAMES)
    assert not c.same_hardware and c.driverless == []
    assert compare(snap([], [], []), snap([], [], []), NAMES).empty


def _world(tmp_path: Path) -> World:
    w = make_world(tmp_path)
    before = take_snapshot(
        FakeInventory(
            apps=[
                InstalledApp(name="Firefox", scope="machine", winget_id="Mozilla.Firefox"),
                InstalledApp(name="OBS Studio", scope="machine"),
                InstalledApp(name="VC++ 2015", scope="machine", redistributable=True),
            ]
        ),
        FakeDevices(
            working=[
                ProblemDevice(name="Wi-Fi", device_id="x", code=0, hardware_ids=WIFI.hardware_ids)
            ]
        ),
        FakeFeatures(
            known={"Microsoft-Windows-Subsystem-Linux": True, "VirtualMachinePlatform": True}
        ),
        default_catalogs(),
        build=26100,
    )
    assert [a.name for a in before.apps] == ["Firefox", "OBS Studio"]  # sem redistribuíveis
    assert "wsl" in before.features
    write_before(w.pendrive, w.recipe(), before)
    w.services.inventory = FakeInventory(
        apps=[InstalledApp(name="Firefox", scope="machine", winget_id="Mozilla.Firefox")]
    )
    w.services.devices = FakeDevices(
        devices=[
            ProblemDevice(name="Wi-Fi", device_id="x", code=28, hardware_ids=WIFI.hardware_ids)
        ]
    )
    return w


def test_phase2_compares_and_summary_shows(tmp_path: Path) -> None:
    w = _world(tmp_path)
    run_phase1(w.runtime())
    run_phase2(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None and state.comparison is not None
    assert state.comparison.missing_apps == ["OBS Studio"]
    assert state.comparison.driverless == ["Wi-Fi"]
    assert "Subsistema do Windows para Linux (WSL)" in state.comparison.missing_features
    html = w.paths.summary_html.read_text(encoding="utf-8")
    assert "Comparação com o PC antigo" in html and "OBS Studio" in html


def test_without_before_file_is_skipped_and_option_off_removes(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    run_phase1(w.runtime())
    run_phase2(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("compare:after").status == "skipped"
    (tmp_path / "off").mkdir()
    w2 = make_world(tmp_path / "off")
    r = w2.recipe()
    r.compare_after_install = False
    w2.save_recipe(r)
    run_phase1(w2.runtime())
    state = StateStore(w2.paths.state).load()
    assert state is not None and "compare:after" not in state.steps
