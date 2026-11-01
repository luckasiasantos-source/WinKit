"""Grava uma pasta de instalação do Windows como ISO de boot (V3-11, D-048, H36).

Arquivos vão em UDF 2.60 (o instalador lê por aí; aceita arquivos grandes); só os dois arquivos de
boot entram também no ISO9660, para o El Torito: ``boot/etfsboot.com`` (BIOS) e
``efi/microsoft/boot/efisys.bin`` (UEFI) — os **da própria ISO original**, nunca trocados.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pycdlib

from winkit.core.errors import WinKitError

BIOS_BOOT = "boot/etfsboot.com"
UEFI_BOOT = "efi/microsoft/boot/efisys.bin"


def _iso9660(rel: str) -> str:
    return "/" + rel.upper() + ";1"


def write_iso(
    folder: Path,
    output: Path,
    *,
    label: str = "WINKIT",
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    """Grava ``folder`` em ``output`` (via ``.part``). Exige os dois arquivos de boot."""
    for needed in (BIOS_BOOT, UEFI_BOOT):
        if not (folder / needed).is_file():
            raise WinKitError(f"arquivo de boot ausente na pasta da ISO: {needed}")
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    total = sum(p.stat().st_size for p in files)
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, vol_ident=label[:32], udf="2.60")
    for name in ("BOOT", "EFI", "EFI/MICROSOFT", "EFI/MICROSOFT/BOOT"):
        iso.add_directory("/" + name, udf_path="/" + name.lower())
    for sub in sorted(p for p in folder.rglob("*") if p.is_dir()):
        rel = sub.relative_to(folder).as_posix()
        if rel.lower() not in ("boot", "efi", "efi/microsoft", "efi/microsoft/boot"):
            iso.add_directory(udf_path="/" + rel)
    for p in files:
        rel = p.relative_to(folder).as_posix()
        is_boot = rel.lower() in (BIOS_BOOT, UEFI_BOOT)
        iso.add_file(str(p), _iso9660(rel) if is_boot else None, udf_path="/" + rel)
    iso.add_eltorito(
        _iso9660(BIOS_BOOT),
        bootcatfile="/BOOT.CAT;1",
        boot_load_size=8,
        udf_bootcatfile="/boot.cat",
    )
    iso.add_eltorito(_iso9660(UEFI_BOOT), efi=True, boot_load_size=1)
    part = output.with_name(output.name + ".part")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        iso.write(
            str(part),
            progress_cb=(lambda done, all_, _o: progress(done, all_)) if progress else None,
        )
    finally:
        iso.close()
    part.replace(output)
    if progress is not None:
        progress(total, total)
    return output
