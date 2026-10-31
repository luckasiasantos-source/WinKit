"""Resolver de volumes (D-035, R-52) e pastas do usuário em outro disco (V2-14)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.agent.helpers import World, make_world
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.phases import run_phase1
from winkit.agent.steps.base import StepContext
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.collector.user_folders import copy_now, detect, system_serial
from winkit.core.catalog.loader import default_catalogs
from winkit.core.planner.models import PlanContext
from winkit.core.planner.planner import plan
from winkit.core.recipe.models import UserFolders, VolumeRef
from winkit.core.user_folders import SHELL_FOLDERS_KEY, generalize_user, registry_values
from winkit.core.volumes import VolumeInfo, normalize_serial, resolve, split
from winkit.platform.copy import PythonCopier
from winkit.platform.fakes.backup import FakeOldPcFolders
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.services import fake_services
from winkit.platform.fakes.volumes import FakeVolumes
from winkit.platform.registry import DEFAULT_HIVE_MOUNT
from winkit.platform.volumes import parse_volumes

DATA = "1A2B3C4D"  # serial inventado (IN-009: nunca discos reais)


def test_resolve_by_serial_never_by_letter() -> None:
    vols = [
        VolumeInfo(serial="0000AAAA", letter="C", size=100, is_system=True),
        VolumeInfo(serial=DATA, letter="E", size=500),  # a letra mudou de D para E
    ]
    ref = VolumeRef(serial=DATA, letter_hint="D", size=500)
    found = resolve(ref, vols)
    assert found is not None and found.letter == "E"
    assert resolve(VolumeRef(serial="FFFFFFFF", letter_hint="E"), vols) is None
    assert split(r"E:\SteamLibrary", vols) == (vols[1], "SteamLibrary")
    assert split(r"\\nas\x", vols) is None
    assert normalize_serial(0x1A2B3C4D) == DATA and normalize_serial(-1) is None


def test_parse_cim_volumes() -> None:
    rows = [
        {
            "Serial": 0x1A2B3C4D,
            "Letter": "D:",
            "Label": "Dados",
            "Size": 10,
            "Free": 5,
            "System": False,
        },
        {"Serial": None, "Letter": "X:"},
        {"Serial": 1, "Letter": "", "Label": "", "System": False},
    ]
    vols = parse_volumes(rows)
    assert vols[0] == VolumeInfo(serial=DATA, letter="D", label="Dados", size=10, free=5)
    assert vols[1].letter is None and vols[1].serial == "00000001"


def test_recipe_rejects_drive_letters_in_volume_paths() -> None:
    """Teste de proteção da R-52: caminhos de volume nunca levam letra de unidade."""
    for bad in (r"D:\Usuarios", r"\Usuarios", "/x"):
        with pytest.raises(ValidationError):
            UserFolders(folders={"documents": bad})
    with pytest.raises(ValidationError):
        VolumeRef(serial=DATA, letter_hint="D:")
    uf = UserFolders(
        enabled=True,
        volume=VolumeRef(serial=DATA, letter_hint="D"),
        folders={"documents": r"Usuarios\%USERNAME%\Documentos"},
    )
    dumped = uf.model_dump_json()
    assert not re.search(r"[A-Z]:\\\\", dumped)  # só a dica de letra, sem caminho com letra


def test_registry_values_use_official_names() -> None:
    uf = UserFolders(
        enabled=True,
        volume=VolumeRef(serial=DATA),
        folders={"documents": r"U\%USERNAME%\Docs", "downloads": r"U\%USERNAME%\Down"},
    )
    assert registry_values(uf, "E") == {
        "Personal": r"E:\U\%USERNAME%\Docs",
        "{374DE290-123F-4565-9164-39C4925E467B}": r"E:\U\%USERNAME%\Down",
    }
    assert generalize_user(r"Usuarios\samuel\Docs", "Samuel") == r"Usuarios\%USERNAME%\Docs"


def test_detect_existing_redirection(tmp_path: Path) -> None:
    reg = FakeRegistry()
    reg.set("HKCU", SHELL_FOLDERS_KEY, "Personal", "expand_sz", r"D:\Usuarios\Samuel\Documentos")
    reg.set("HKCU", SHELL_FOLDERS_KEY, "My Music", "expand_sz", r"%USERPROFILE%\Music")
    vols = [
        VolumeInfo(serial="0000AAAA", letter="C", is_system=True),
        VolumeInfo(serial=DATA, letter="D", label="Dados"),
    ]
    found = detect(reg, vols, r"C:\Users\Samuel", "Samuel")
    assert found is not None and found.volume is not None
    assert found.volume.serial == DATA and found.volume.letter_hint == "D"
    assert found.folders == {"documents": r"Usuarios\%USERNAME%\Documentos"}
    assert system_serial(vols) == "0000AAAA"
    assert detect(FakeRegistry(), vols, r"C:\Users\Samuel", "Samuel") is None


def _world(tmp_path: Path) -> World:
    w = make_world(tmp_path)
    vols = w.services.volumes
    assert isinstance(vols, FakeVolumes)
    vols.add("0000AAAA", "C", w.system, system=True)
    vols.add(DATA, "E", tmp_path / "disco-E")  # era D: no PC antigo
    r = w.recipe()
    r.user_folders = UserFolders(
        enabled=True,
        volume=VolumeRef(serial=DATA, label="Dados", letter_hint="D", size=500 * 2**30),
        folders={
            "documents": r"Usuarios\%USERNAME%\Documentos",
            "downloads": r"Usuarios\%USERNAME%\Downloads",
        },
    )
    w.save_recipe(r)
    return w


def test_plan_before_backups_and_tweaks(tmp_path: Path) -> None:
    w = _world(tmp_path)
    p = plan(w.recipe(), default_catalogs(), PlanContext(os_major=11, build=26100))
    ids = [s.id for s in p.phase(1)]
    assert ids.index("user_folders:default") < min(
        i for i, s in enumerate(ids) if s.startswith(("tweak:", "backup:"))
    )


def test_phase1_points_default_profile_with_current_letter(tmp_path: Path) -> None:
    w = _world(tmp_path)
    run_phase1(w.runtime())
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    key = rf"{DEFAULT_HIVE_MOUNT}\{SHELL_FOLDERS_KEY}"
    assert reg.get("HKU", key, "Personal") == r"E:\Usuarios\%USERNAME%\Documentos"
    assert reg.get_type("HKU", key, "Personal") == "expand_sz"
    assert (tmp_path / "disco-E" / "Usuarios" / "Samuel" / "Documentos").is_dir()
    assert reg.mounted == {}


def test_missing_volume_is_skipped_never_failed(tmp_path: Path) -> None:
    w = _world(tmp_path)
    vols = w.services.volumes
    assert isinstance(vols, FakeVolumes)
    vols.items = [v for v in vols.items if v.serial != DATA]
    run_phase1(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None
    sst = state.step("user_folders:default")
    assert sst.status == "skipped" and sst.reason is not None
    assert sst.reason.key == "step.user_folders.no_volume"


def test_backups_follow_redirected_documents(tmp_path: Path) -> None:
    """R16: ``{DOCUMENTS}`` aponta para o outro disco depois da etapa."""
    w = _world(tmp_path)
    p = plan(w.recipe(), default_catalogs(), PlanContext(os_major=11, build=26100))
    step = p.step("user_folders:default")
    assert step is not None
    ctx = StepContext.__new__(StepContext)  # só os campos que folders() usa
    ctx.step, ctx.recipe, ctx.services = step, w.recipe(), w.services
    folders = ctx.folders()
    assert folders["DOCUMENTS"] == r"E:\Usuarios\Samuel\Documentos"


def test_live_points_hkcu_and_is_then_done(tmp_path: Path) -> None:
    w = _world(tmp_path)
    opts = {"root": w.pendrive, "restore_point": False, "only_kinds": frozenset({"user_folders"})}
    run_live(w.runtime(), LiveOptions(**opts))  # type: ignore[arg-type]
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    assert reg.get("HKCU", SHELL_FOLDERS_KEY, "Personal") == r"E:\Usuarios\%USERNAME%\Documentos"
    again = run_live(w.runtime(), LiveOptions(simulate=True, **opts))  # type: ignore[arg-type]
    assert again.preview is not None
    assert [i.status for i in again.preview.items] == ["already_done"]


def test_copy_now_is_merge_only(tmp_path: Path) -> None:
    w = _world(tmp_path)
    old = FakeOldPcFolders(tmp_path / "C-antigo")
    docs = tmp_path / "C-antigo" / "Users" / "Samuel" / "Documents"
    docs.mkdir(parents=True)
    (docs / "novo.txt").write_text("novo", encoding="utf-8")
    (docs / "existe.txt").write_text("do C", encoding="utf-8")
    dest = tmp_path / "disco-E" / "Usuarios" / "Samuel" / "Documentos"
    dest.mkdir(parents=True)
    (dest / "existe.txt").write_text("do disco", encoding="utf-8")
    report = copy_now(
        w.recipe(), w.services.volumes, PythonCopier(), old.current_user(), old.volume_root
    )
    assert report.copied == ["documents"] and report.missing == ["downloads"]
    assert (dest / "novo.txt").read_text(encoding="utf-8") == "novo"
    assert (dest / "existe.txt").read_text(
        encoding="utf-8"
    ) == "do disco"  # merge: nada substituído
    assert (docs / "novo.txt").exists()  # a origem fica intacta


def test_cli_folders(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    vols = FakeVolumes()
    vols.add("0000AAAA", "C", tmp_path / "C", system=True)
    vols.add(DATA, "D", tmp_path / "D")
    services = fake_services(volumes=vols)
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=services, out=out.append)

    assert run("pastas", "definir", "--volume", "D", "--pastas", "documentos,imagens") == 0
    uf = w.recipe().user_folders
    assert uf.enabled and uf.volume is not None and uf.volume.serial == DATA
    assert uf.folders == {
        "documents": r"Usuarios\%USERNAME%\Documentos",
        "pictures": r"Usuarios\%USERNAME%\Imagens",
    }
    assert w.recipe().meta.source_system_volume == "0000AAAA"
    assert any(r"D:\Usuarios\%USERNAME%\Documentos" in x for x in out)
    assert run("pastas", "definir", "--volume", "C") == 1  # o do sistema é recusado
    assert run("folders", "set", "--volume", "D", "--pastas", "nada") == 1
