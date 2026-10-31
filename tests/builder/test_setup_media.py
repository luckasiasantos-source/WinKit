"""Pendrive comum gravado pelo Rufus ou pela ferramenta da Microsoft (V2-01, D-034)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from winkit.builder import target as targets
from winkit.builder.build import BuildOptions, build, ensure_marker, save_profile_recipe
from winkit.builder.validate import validate_pendrive
from winkit.core import media
from winkit.core.catalog.loader import default_catalogs
from winkit.core.recipe.io import new_recipe
from winkit.platform.fakes.disks import (
    FakeDiskInspector,
    make_setup_folder,
    setup_rows,
    ventoy_rows,
    windows_iso,
)

NOW = datetime(2026, 10, 31, tzinfo=UTC)
RUFUS_XML = b'<?xml version="1.0"?>\n<unattend xmlns="urn:schemas-microsoft-com:unattend"/>\n'


def _files(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and not p.relative_to(root).as_posix().startswith("WinKit/")
    }


@pytest.fixture
def pen(tmp_path: Path) -> Path:
    root = make_setup_folder(tmp_path / "rufus")
    marker = ensure_marker(root, NOW)
    save_profile_recipe(root, new_recipe(pendrive_id=marker.pendrive_id, username="Ana", now=NOW))
    return root


def _build(root: Path, inspector: FakeDiskInspector | None = None) -> object:
    return build(
        targets.from_folder(root),
        inspector or FakeDiskInspector(),
        default_catalogs(),
        BuildOptions(),
        now=NOW,
    )


def test_folder_with_setup_files_is_setup_kind(pen: Path, tmp_path: Path) -> None:
    assert targets.from_folder(pen).kind == "setup"
    assert targets.from_folder(tmp_path / "vazio").kind == "ventoy"


def test_detection_lists_rufus_drive_but_never_internal_disks(tmp_path: Path) -> None:
    roots = {"F:": make_setup_folder(tmp_path / "F"), "G:": tmp_path / "G"}
    (tmp_path / "G").mkdir()
    internal = make_setup_folder(tmp_path / "C")  # disco interno com arquivos de instalação
    roots["C:"] = internal
    rows = setup_rows() + ventoy_rows()
    found = targets.list_targets(
        FakeDiskInspector(rows=rows), lambda letter: roots.get(letter, tmp_path / "x")
    )
    kinds = {(d.data_letter, d.kind) for d in found}
    assert kinds == {("E:", "ventoy"), ("F:", "setup")}
    t = targets.resolve_target(
        FakeDiskInspector(rows=setup_rows()), "f", lambda letter: roots[letter]
    )
    assert t.kind == "setup" and t.root == Path("F:\\")


def test_build_writes_only_root_unattend_outside_winkit(pen: Path) -> None:
    before = _files(pen)
    report = _build(pen)
    after = _files(pen)
    changed = {k for k in after if before.get(k) != after[k]}
    assert changed == {media.UNATTEND}  # R-19: nada além do autounattend.xml fora de WinKit\
    assert not (pen / "ventoy").exists()
    data = (pen / media.UNATTEND).read_bytes()
    assert media.is_winkit_unattend(data) and b"DiskConfiguration" not in data
    assert report.templates == ["/autounattend.xml"]  # type: ignore[attr-defined]


def test_rufus_answers_are_kept_once_and_oem_removed(pen: Path) -> None:
    (pen / media.UNATTEND).write_bytes(RUFUS_XML)
    oem = pen / media.OEM_UNATTEND
    oem.parent.mkdir(parents=True)
    oem.write_bytes(RUFUS_XML)
    report = _build(pen)
    assert (pen / media.UNATTEND_BACKUP).read_bytes() == RUFUS_XML
    assert not oem.exists() and oem.with_name("unattend.xml.winkit-bak").read_bytes() == RUFUS_XML
    assert len(report.warnings) >= 2  # type: ignore[attr-defined]
    _build(pen)  # reconstruir não copia o próprio arquivo do WinKit (lição do IN-002)
    assert (pen / media.UNATTEND_BACKUP).read_bytes() == RUFUS_XML
    assert not (pen / (media.UNATTEND_BACKUP + "2")).exists()
    changed = set(_files(pen)) - {media.UNATTEND, media.UNATTEND_BACKUP}
    assert changed <= set(_files(pen)) and "ventoy/ventoy.json" not in changed


def test_language_comes_from_the_install_image(pen: Path) -> None:
    _build(pen, FakeDiskInspector(setup_image=windows_iso("/install.wim", lang="es-ES")))
    assert b"<UILanguage>es-ES</UILanguage>" in (pen / media.UNATTEND).read_bytes()
    report = _build(pen, FakeDiskInspector(setup_image=None))  # leitura falhou: segue com aviso
    assert any("pt-BR" in w for w in report.warnings)  # type: ignore[attr-defined]


def test_validate_setup_media(pen: Path) -> None:
    rep = validate_pendrive(pen, default_catalogs(), kind="setup")
    assert any("autounattend" in p for p in rep.problems)
    _build(pen)
    rep = validate_pendrive(pen, default_catalogs())  # tipo detectado pelos arquivos
    assert rep.ok, rep.problems
    (pen / media.UNATTEND).write_bytes(RUFUS_XML)
    assert not validate_pendrive(pen, default_catalogs()).ok
    oem = pen / media.OEM_UNATTEND
    oem.parent.mkdir(parents=True)
    oem.write_bytes(RUFUS_XML)
    _build(pen)
    oem.write_bytes(RUFUS_XML)
    assert any("$OEM$" in w for w in validate_pendrive(pen, default_catalogs()).warnings)


def test_detect_ignores_ventoy_disks_and_fixed_buses() -> None:
    from winkit.core.ventoy.detect import PartitionRow

    rows = [
        PartitionRow(1, "HD externo", "SATA", 1, 10, "H", "Dados", "NTFS", 5),
        PartitionRow(2, "Pendrive", "USB", 1, 10, "U", "X", "NTFS", 5),
        PartitionRow(2, "Pendrive", "USB", 2, 1, None, "VTOYEFI", "FAT", 0),
    ]
    assert media.find_setup_targets(rows, lambda letter: True) == []
