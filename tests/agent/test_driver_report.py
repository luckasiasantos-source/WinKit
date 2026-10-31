"""Diagnóstico de drivers (V2-09): CIM, busca dirigida no Windows Update e resumo."""

from __future__ import annotations

from pathlib import Path

from tests.agent.helpers import World, make_world
from winkit.agent.eventlog import EventLog
from winkit.agent.phases import open_session, run_phase1, run_phase2
from winkit.agent.store import StateStore
from winkit.core.devices import PROBLEM_CODES, ProblemDevice, hardware_ids, problem_text
from winkit.core.summary import build_summary, render_html
from winkit.i18n import render, set_language
from winkit.i18n.messages import en_us, es, pt_br
from winkit.platform.devices import parse_devices
from winkit.platform.fakes.system_tweaks import FakeDevices, FakeUpdater

WIFI = ProblemDevice(
    name="Controlador de rede",
    device_id=r"PCI\VEN_8086&DEV_2725\4&1",
    code=28,
    hardware_ids=(r"PCI\VEN_8086&DEV_2725&SUBSYS_00248086", r"PCI\VEN_8086&DEV_2725"),
)
SENSOR = ProblemDevice(
    name="Dispositivo desconhecido",
    device_id=r"ACPI\INT33D3\0",
    code=1,
    hardware_ids=(r"ACPI\INT33D3",),
)
UNPLUGGED = ProblemDevice(name="Celular", device_id=r"USB\VID_1", code=45, hardware_ids=())


def test_parse_cim_json() -> None:
    rows = [
        {"Name": "Controlador de rede", "DeviceID": "PCI\\X", "Code": 28, "HardwareID": ["A", "B"]},
        {"Name": None, "DeviceID": "ACPI\\Y", "Code": 1, "HardwareID": "C"},
        {"Name": "ok", "DeviceID": "Z", "Code": 0, "HardwareID": []},
        "lixo",
    ]
    devices = parse_devices(rows)
    assert [(d.name, d.code, d.hardware_ids) for d in devices] == [
        ("Controlador de rede", 28, ("A", "B")),
        ("ACPI\\Y", 1, ("C",)),
    ]


def test_problem_codes_table_is_translated() -> None:
    for code in PROBLEM_CODES:
        key = f"device.problem.{code}"
        assert key in pt_br.MESSAGES and key in en_us.MESSAGES and key in es.MESSAGES
    assert "999" in render(problem_text(999))
    assert hardware_ids([WIFI, WIFI, SENSOR]) == [*WIFI.hardware_ids, *SENSOR.hardware_ids]


def _world(tmp_path: Path, devices: list[ProblemDevice], catalog: set[str]) -> World:
    w = make_world(tmp_path)
    fake = FakeDevices(devices=list(devices))
    w.services.devices = fake
    updater = w.services.updater
    assert isinstance(updater, FakeUpdater)
    updater.driver_catalog = catalog
    updater.on_driver_install = fake.fix
    return w


def test_searches_only_problem_devices_and_reports_the_rest(tmp_path: Path) -> None:
    w = _world(tmp_path, [WIFI, SENSOR, UNPLUGGED], {WIFI.hardware_ids[1]})
    run_phase1(w.runtime())
    run_phase2(w.runtime())
    updater = w.services.updater
    assert isinstance(updater, FakeUpdater)
    searched = updater.driver_searches[0]
    assert set(searched) == {*WIFI.hardware_ids, *SENSOR.hardware_ids}  # o desconectado não
    state = StateStore(w.paths.state).load()
    assert state is not None
    assert [d.device_id for d in state.devices] == [SENSOR.device_id]
    assert state.drivers_found == [f"driver {WIFI.hardware_ids[1]}"]
    sst = state.step("driver_report:devices")
    assert sst.status == "done" and sst.reason is not None
    assert sst.reason.key == "step.driver_report.remaining"
    html = w.paths.summary_html.read_text(encoding="utf-8")
    assert "Dispositivos sem driver" in html and "Dispositivo desconhecido" in html
    assert "ACPI\\INT33D3" in html
    assert "Controlador de rede" not in html.split("Dispositivos sem driver")[1]


def test_without_internet_only_reports(tmp_path: Path) -> None:
    w = _world(tmp_path, [WIFI], {WIFI.hardware_ids[0]})
    w.env.internet = False
    r = w.recipe()
    r.updates.windows_update_after_install = False  # senão a etapa do WU espera a internet
    w.save_recipe(r)
    run_phase1(w.runtime())
    run_phase2(w.runtime())
    updater = w.services.updater
    assert isinstance(updater, FakeUpdater)
    assert updater.driver_searches == []
    state = StateStore(w.paths.state).load()
    assert state is not None and [d.code for d in state.devices] == [28]


def test_option_off_removes_the_step(tmp_path: Path) -> None:
    w = _world(tmp_path, [WIFI], set())
    r = w.recipe()
    r.updates.fix_missing_drivers = False
    w.save_recipe(r)
    run_phase1(w.runtime())
    run_phase2(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None and "driver_report:devices" not in state.steps


def test_summary_section_in_every_language(tmp_path: Path) -> None:
    w = _world(tmp_path, [SENSOR], set())
    run_phase1(w.runtime())
    run_phase2(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None
    rt = w.runtime()
    s = open_session(rt, EventLog(w.tmp / "logs", rt.clock), phase=2)
    assert s is not None
    summary = build_summary(s.plan, state, s.recipe, computer="PC", now=rt.clock())
    titles = (("en-US", "Devices without drivers"), ("es", "Dispositivos sin controlador"))
    for lang, title in titles:
        set_language(lang)  # type: ignore[arg-type]
        assert title in render_html(summary, log_path="x")
