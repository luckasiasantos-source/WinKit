"""O WinKit grava o pendrive (V3-13): travas, cópia, divisão do install.wim e boot em BIOS."""

from __future__ import annotations

from pathlib import Path

import pytest

from winkit.builder.usb_media import write_usb
from winkit.core.errors import WinKitError
from winkit.core.usb_safety import UsbDisk
from winkit.platform.fakes.images import FakeImageTools, FakeIsoMounter, FakeUsbWriter
from winkit.platform.fakes.runner import FakeRunner

PEN = UsbDisk(3, "AA11", "SanDisk", 32 * 1000**3, 7, False, False, ("E:",))


def _media(root: Path) -> Path:
    for rel in ("boot/bootsect.exe", "efi/boot/bootx64.efi", "sources/boot.wim", "setup.exe"):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * 100)
    with (root / "sources" / "install.wim").open("wb") as f:
        f.truncate(5 * 1024**3)  # esparso: maior que 4 GB sem ocupar disco
    return root


def _write(
    tmp: Path, boot: str = "uefi_bios", letter: str = "E"
) -> tuple[FakeUsbWriter, FakeImageTools, FakeRunner, Path]:
    pen = tmp / "pendrive"
    pen.mkdir()
    (pen / "foto-antiga.jpg").write_bytes(b"x")
    writer = FakeUsbWriter(disks=[PEN], roots={"E:": pen})
    tools, runner = FakeImageTools(), FakeRunner()
    write_usb(
        tmp / "Win11.iso",
        PEN,
        letter,
        boot,  # type: ignore[arg-type]
        writer=writer,
        tools=tools,
        mounter=FakeIsoMounter(_media(tmp / "iso")),
        runner=runner,
        volume_root=lambda v: writer.roots[v],
    )
    return writer, tools, runner, pen


def test_writes_splits_and_makes_bios_bootable(tmp_path: Path) -> None:
    writer, tools, runner, pen = _write(tmp_path)
    assert writer.prepared == [(3, "MBR")]
    assert not (pen / "foto-antiga.jpg").exists()  # o pendrive confirmado foi apagado
    assert (pen / "setup.exe").is_file() and (pen / "efi" / "boot" / "bootx64.efi").is_file()
    assert not (pen / "sources" / "install.wim").exists()
    assert (pen / "sources" / "install.swm").is_file() and ("split", "install.wim") in tools.log
    assert any("bootsect.exe" in str(c.args[0]) and "/nt60" in c.args for c in runner.calls)


def test_uefi_only_uses_gpt_without_bootsect(tmp_path: Path) -> None:
    writer, _, runner, _ = _write(tmp_path, boot="uefi")
    assert writer.prepared == [(3, "GPT")] and not runner.calls


def test_wrong_letter_erases_nothing(tmp_path: Path) -> None:
    with pytest.raises(WinKitError):
        _write(tmp_path, letter="C")
    assert (tmp_path / "pendrive" / "foto-antiga.jpg").is_file()
