"""ISO personalizada (V3-11/12, D-044, D-048): cópia com boot BIOS+UEFI, original intacta (R-64)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pycdlib
import pytest

from tests.agent.helpers import make_world
from winkit.builder.custom_iso import CustomIsoOptions, build_custom_iso
from winkit.core.catalog.loader import default_catalogs
from winkit.platform.fakes.disks import FakeDiskInspector
from winkit.platform.fakes.images import FakeImageTools, FakeIsoMounter

NOW = datetime(2026, 11, 1, tzinfo=UTC)


def _media(root: Path) -> Path:
    for rel, data in {
        "boot/etfsboot.com": b"B" * 4096,
        "efi/microsoft/boot/efisys.bin": b"E" * 2048,
        "sources/install.esd": b"esd",
        "sources/boot.wim": b"boot",
        "setup.exe": b"MZ",
    }.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return root


def _run(tmp: Path, tools: FakeImageTools, **kw: object) -> tuple[CustomIsoOptions, str]:
    original = tmp / "Win11.iso"
    original.write_bytes(b"ISO original")
    sha = hashlib.sha256(original.read_bytes()).hexdigest()
    drivers = tmp / "drivers"
    drivers.mkdir()
    update = tmp / "kb.msu"
    update.write_bytes(b"msu")
    opts = CustomIsoOptions(
        original=original,
        output=tmp / "saida" / "Win11-winkit.iso",
        work_dir=tmp / "trabalho",
        editions=[6],
        drivers=[drivers],
        updates=[update],
        remove_apps=["Microsoft.BingNews"],
        **kw,  # type: ignore[arg-type]
    )
    build_custom_iso(
        opts,
        tools=tools,
        mounter=FakeIsoMounter(_media(tmp / "unidade")),
        inspector=FakeDiskInspector(),
        catalogs=default_catalogs(),
        now=NOW,
    )
    return opts, sha


def test_custom_iso_is_bootable_copy(tmp_path: Path) -> None:
    tools = FakeImageTools()
    opts, sha = _run(tmp_path, tools)
    assert hashlib.sha256(opts.original.read_bytes()).hexdigest() == sha  # R-64
    assert ("export", "install.esd", "6") in tools.log
    assert ("remove", "Microsoft.BingNews") in tools.log
    assert ("remove", "Microsoft.WindowsCalculator") not in tools.log
    assert ("package", "kb.msu") in tools.log
    mounts = [op for op in tools.log if op[0] == "mount"]
    assert mounts == [
        ("mount", "install.wim", "1"),
        ("mount", "boot.wim", "1"),
        ("mount", "boot.wim", "2"),
    ]
    assert tools.log.count(("unmount", "save")) == 3 and not tools.mounted
    assert not (tmp_path / "trabalho" / "winkit-iso").exists()
    iso = pycdlib.PyCdlib()
    iso.open(str(opts.output))
    try:
        names = [c.file_identifier() for c in iso.list_children(udf_path="/sources")]
        assert b"install.wim" in names and b"install.esd" not in names
        assert len(iso.eltorito_boot_catalog.sections) == 1  # BIOS + uma seção UEFI
        assert iso.eltorito_boot_catalog.sections[0].platform_id == 0xEF
    finally:
        iso.close()


def test_failure_discards_and_keeps_nothing(tmp_path: Path) -> None:
    tools = FakeImageTools(fail_on="package")
    with pytest.raises(OSError):
        _run(tmp_path, tools)
    assert ("unmount", "discard") in tools.log and not tools.mounted
    assert not (tmp_path / "saida" / "Win11-winkit.iso").exists()
    assert not (tmp_path / "trabalho" / "winkit-iso").exists()


def test_self_contained_has_winkit_inside(tmp_path: Path) -> None:
    (tmp_path / "w").mkdir()
    world = make_world(tmp_path / "w")
    opts, _ = _run(tmp_path, FakeImageTools(), self_contained_from=world.pendrive)
    iso = pycdlib.PyCdlib()
    iso.open(str(opts.output))
    try:
        root = [c.file_identifier() for c in iso.list_children(udf_path="/")]
        assert b"autounattend.xml" in root and b"WinKit" in root
    finally:
        iso.close()
