"""Unidades de rede (V2-17): coleta, perfil Default, modo ao vivo, colisão de letra e CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.agent.helpers import START, World, make_world
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.phases import run_phase1
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.collector.netdrives import add_drive, collect_drives
from winkit.core.recipe.io import new_recipe
from winkit.core.recipe.models import NetworkDrive, Recipe
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.services import fake_services
from winkit.platform.fakes.system_tweaks import FakeDriveMapper
from winkit.platform.netdrives import PROVIDER_KEY, read_mapped
from winkit.platform.registry import DEFAULT_HIVE_MOUNT

NAS = r"\\nas\filmes"
#: Nome do provedor como o Windows em português grava (lido, nunca escrito por nós).
PROVIDER = "Rede Microsoft Windows"


def old_pc_registry() -> FakeRegistry:
    reg = FakeRegistry()
    reg.set("HKCU", r"Network\Z", "RemotePath", "sz", NAS)
    reg.set("HKCU", r"Network\Z", "UserName", "sz", r"NAS\samuel")
    reg.set("HKCU", r"Network\Y", "RemotePath", "sz", r"\\192.168.0.10\backup")
    return reg


def test_collect_ignores_username() -> None:
    reg = old_pc_registry()
    assert read_mapped(reg) == {"Z": NAS, "Y": r"\\192.168.0.10\backup"}
    w_recipe = fake_recipe()
    added = collect_drives(reg, w_recipe)
    assert [(d.letter, d.remote_path) for d in added] == [
        ("Y", r"\\192.168.0.10\backup"),
        ("Z", NAS),
    ]
    assert "samuel" not in w_recipe.model_dump_json()
    assert collect_drives(reg, w_recipe) == []  # não duplica


def fake_recipe() -> Recipe:
    return new_recipe(pendrive_id="x" * 36, username="Samuel", now=START)


def test_invalid_drive_is_rejected() -> None:
    r = fake_recipe()
    with pytest.raises(ValidationError):
        add_drive(r, "C", NAS)
    with pytest.raises(ValidationError):
        add_drive(r, "Z", r"C:\pasta")
    assert add_drive(r, "z:", NAS).letter == "Z"


def _world(tmp_path: Path) -> World:
    w = make_world(tmp_path)
    r = w.recipe()
    r.network_drives = [NetworkDrive(letter="Z", remote_path=NAS)]
    w.save_recipe(r)
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    reg.set("HKLM", PROVIDER_KEY, "Name", "sz", PROVIDER)
    return w


def test_phase1_writes_default_profile(tmp_path: Path) -> None:
    w = _world(tmp_path)
    run_phase1(w.runtime())
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    key = rf"{DEFAULT_HIVE_MOUNT}\Network\Z"
    assert reg.get("HKU", key, "RemotePath") == NAS
    assert reg.get("HKU", key, "ProviderName") == PROVIDER  # copiado do Windows novo (R-13)
    assert reg.get("HKU", key, "ProviderType") == 0x20000
    assert reg.mounted == {}  # hive desmontada
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("network_drive:Z").status == "done"


def test_default_profile_letter_taken_is_skipped(tmp_path: Path) -> None:
    w = _world(tmp_path)
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    reg.set("HKU", rf"{DEFAULT_HIVE_MOUNT}\Network\Z", "RemotePath", "sz", r"\\outro\x")
    run_phase1(w.runtime())
    assert reg.get("HKU", rf"{DEFAULT_HIVE_MOUNT}\Network\Z", "RemotePath") == r"\\outro\x"
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("network_drive:Z").status == "skipped"


def test_live_maps_now_or_falls_back_to_registry(tmp_path: Path) -> None:
    w = _world(tmp_path)
    kinds = frozenset({"network_drive"})
    mapper = FakeDriveMapper(online={NAS})
    w.services.drive_mapper = mapper
    run_live(w.runtime(), LiveOptions(root=w.pendrive, restore_point=False, only_kinds=kinds))  # type: ignore[arg-type]
    assert mapper.mapped == {"Z": NAS}

    (tmp_path / "offline").mkdir()
    w2 = _world(tmp_path / "offline")
    run_live(w2.runtime(), LiveOptions(root=w2.pendrive, restore_point=False, only_kinds=kinds))  # type: ignore[arg-type]
    reg = w2.services.registry
    assert isinstance(reg, FakeRegistry)
    assert reg.get("HKCU", r"Network\Z", "RemotePath") == NAS  # servidor fora: grava e reconecta
    again = run_live(
        w2.runtime(),
        LiveOptions(root=w2.pendrive, simulate=True, restore_point=False, only_kinds=kinds),  # type: ignore[arg-type]
    )
    assert again.preview is not None
    assert [i.status for i in again.preview.items] == ["already_done"]


def test_live_letter_used_by_local_disk(tmp_path: Path) -> None:
    w = _world(tmp_path)
    w.env.drive_roots = lambda: [Path("C:\\"), Path("Z:\\")]  # type: ignore[method-assign]
    mapper = FakeDriveMapper(online={NAS})
    w.services.drive_mapper = mapper
    kinds = frozenset({"network_drive"})
    result = run_live(
        w.runtime(),
        LiveOptions(root=w.pendrive, restore_point=False, only_kinds=kinds),  # type: ignore[arg-type]
    )
    assert mapper.mapped == {}  # nunca substitui o disco local
    assert result.run_dir is not None
    state = StateStore(result.run_dir / "estado.json").load()
    assert state is not None
    sst = state.step("network_drive:Z")
    assert sst.status == "skipped" and sst.reason is not None
    assert sst.reason.key == "step.network_drive.letter_taken"


def test_cli_drives(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    services = fake_services(registry=old_pc_registry())
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=services, out=out.append)

    assert run("coletar", "unidades") == 0
    assert {d.letter for d in w.recipe().network_drives} == {"Y", "Z"}
    assert run("unidades", "adicionar", "X", r"\\pc\musicas") == 0
    assert run("unidades", "adicionar", "B", r"\\pc\x") == 1
    assert run("drives", "remove", "Y") == 0
    assert [d.letter for d in w.recipe().network_drives] == ["Z", "X"]
    assert any(r"X:  \\pc\musicas" in x for x in out)
