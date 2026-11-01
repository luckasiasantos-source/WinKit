"""Comandos da v3 na CLI (PLANO_V3 §5.5): backup do PC, gravar pendrive e ISO personalizada."""

from __future__ import annotations

from pathlib import Path

from tests.agent.helpers import make_world
from winkit.cli import main as cli
from winkit.core.usb_safety import UsbDisk
from winkit.platform.fakes.images import FakeIsoMounter, FakeUsbWriter
from winkit.platform.fakes.services import fake_services


def test_backup_pc_and_restore(tmp_path: Path) -> None:
    old = tmp_path / "C"
    docs = old / "Users" / "Samuel" / "Documents"
    docs.mkdir(parents=True)
    (docs / "a.txt").write_text("a")
    services = fake_services(old_pc=old)
    out: list[str] = []
    assert (
        cli.main(
            ["backup-pc", "fazer", "--destino", "D:", "--simular"],
            services=services,
            out=out.append,
        )
        == 0
    )
    assert (
        cli.main(["backup-pc", "fazer", "--destino", "D:"], services=services, out=out.append) == 0
    )
    assert (tmp_path / "D" / "WinKit-backup").is_dir()
    (docs / "a.txt").unlink()
    assert (
        cli.main(["pc-backup", "restore", "--origem", "D:"], services=services, out=out.append) == 0
    )
    assert (docs / "a.txt").read_text() == "a"


def test_pendrive_write_refuses_wrong_letter_and_simulates(tmp_path: Path) -> None:
    pen = UsbDisk(2, "AA", "Kingston", 16 * 1000**3, 7, False, False, ("F:",))
    writer = FakeUsbWriter(disks=[pen], roots={"F:": tmp_path / "F"})
    services = fake_services(old_pc=tmp_path / "C", usb_writer=writer)
    out: list[str] = []
    base = ["pendrive", "gravar", "--iso", "x.iso", "--disco", "2"]
    assert cli.main([*base, "--confirmar", "C"], services=services, out=out.append) == 1
    assert (
        cli.main([*base, "--confirmar", "F", "--simular"], services=services, out=out.append) == 0
    )
    assert writer.prepared == []


def test_iso_customize(tmp_path: Path) -> None:
    media = tmp_path / "iso"
    for rel in ("boot/etfsboot.com", "efi/microsoft/boot/efisys.bin", "sources/install.wim"):
        (media / rel).parent.mkdir(parents=True, exist_ok=True)
        (media / rel).write_bytes(b"x" * 2048)
    original = tmp_path / "Win11.iso"
    original.write_bytes(b"ISO")
    services = fake_services(old_pc=tmp_path / "C", iso_mounter=FakeIsoMounter(media))
    (tmp_path / "w").mkdir()
    world = make_world(tmp_path / "w")
    args = ["iso", "personalizar", "--original", str(original), "--saida", str(tmp_path / "n.iso")]
    args += ["--edicao", "6", "--autossuficiente", "--raiz", str(world.pendrive)]
    assert cli.main(args, services=services, out=lambda s: None) == 0
    assert (tmp_path / "n.iso").is_file() and original.read_bytes() == b"ISO"
