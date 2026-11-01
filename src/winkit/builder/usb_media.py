"""O WinKit grava a ISO num pendrive, sem Ventoy nem Rufus (V3-13, D-045, D-049).

Apaga **só** o pendrive confirmado (as travas ficam em ``platform.usb_writer``), cria uma
partição FAT32 (MBR para UEFI e BIOS, GPT só para UEFI), copia a ISO montada só para leitura,
divide o ``install.wim`` acima de 4 GB em ``install.swm`` e, para BIOS, grava o setor de boot.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from winkit.core.errors import WinKitError
from winkit.core.pc_backup import FAT32_MAX
from winkit.core.usb_safety import BootMode, UsbDisk, partition_style
from winkit.platform.image_tools import ImageTools
from winkit.platform.iso_mount import IsoMounter, mounted_iso
from winkit.platform.runner import CommandRunner
from winkit.platform.usb_writer import UsbWriter

SPLIT_MB = 3800


def write_usb(
    iso: Path,
    shown: UsbDisk,
    typed_letter: str,
    boot: BootMode,
    *,
    writer: UsbWriter,
    tools: ImageTools,
    mounter: IsoMounter,
    runner: CommandRunner,
    volume_root: Callable[[str], Path],
    progress: Callable[[str, float], None] = lambda step, frac: None,
) -> str:
    letter = writer.prepare(shown, typed_letter, style=partition_style(boot), label="WINKIT")
    dest = volume_root(letter)
    progress("format", 1.0)
    with mounted_iso(mounter, iso) as src:
        files = [p for p in src.rglob("*") if p.is_file()]
        total = sum(p.stat().st_size for p in files) or 1
        done = 0
        for p in files:
            rel = p.relative_to(src)
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            size = p.stat().st_size
            if size > FAT32_MAX:
                if p.name.lower() != "install.wim":
                    raise WinKitError(
                        f"{rel} passa de 4 GB e não cabe em FAT32; use a ISO personalizada"
                    )
                tools.split(p, out.with_name("install.swm"), SPLIT_MB)
            else:
                shutil.copyfile(p, out)
                if out.stat().st_size != size:
                    raise WinKitError(f"a cópia de {rel} não confere; tente outro pendrive")
            done += size
            progress("copy", done / total)
        if boot != "uefi":
            bootsect = src / "boot" / "bootsect.exe"
            if not bootsect.is_file():
                raise WinKitError("a ISO não tem boot\\bootsect.exe para o boot em BIOS")
            runner.run([bootsect, "/nt60", letter, "/mbr"], timeout=300).check()
    progress("boot", 1.0)
    return letter
