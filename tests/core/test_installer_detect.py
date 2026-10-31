from __future__ import annotations

import struct
from pathlib import Path

import pytest

from winkit.core.catalog.loader import default_catalogs
from winkit.core.installers.detect import (
    OLE_MAGIC,
    default_args,
    detect_type,
    pe_section_names,
    read_head,
)

SIGS = default_catalogs().installer_signatures


def fake_pe(sections: list[str], extra: bytes = b"") -> bytes:
    pe_off = 0x80
    opt_size = 0xF0
    data = bytearray(b"MZ" + b"\0" * (pe_off - 2))
    struct.pack_into("<I", data, 0x3C, pe_off)
    coff = bytearray(24)
    coff[0:4] = b"PE\0\0"
    struct.pack_into("<H", coff, 6, len(sections))
    struct.pack_into("<H", coff, 20, opt_size)
    data += coff + b"\0" * opt_size
    for name in sections:
        entry = bytearray(40)
        entry[0:8] = name.encode().ljust(8, b"\0")
        data += entry
    return bytes(data) + extra


def test_pe_sections() -> None:
    assert pe_section_names(fake_pe([".text", ".wixburn"])) == [".text", ".wixburn"]
    assert pe_section_names(b"nao-pe") == []
    assert pe_section_names(b"MZ" + b"\0" * 100) == []


@pytest.mark.parametrize(
    ("head", "name", "kind"),
    [
        (fake_pe([".text", ".wixburn"]), "x.exe", "wix_burn"),
        (fake_pe([".text"], b"...Inno Setup Setup Data (6.2.0)..."), "x.exe", "inno"),
        (fake_pe([".text"], b"...Nullsoft.NSIS.exehead..."), "x.exe", "nsis"),
        (fake_pe([".text"], b"SquirrelSetup"), "DiscordSetup.exe", "squirrel"),
        (fake_pe([".text"], b"InstallShield"), "s.exe", "installshield"),
        (OLE_MAGIC + b"\0" * 64, "pacote.MSI", "msi"),
        (b"PK\x03\x04" + b"\0" * 64, "app.msixbundle", "msix"),
        (b"nao-ole", "falso.msi", "unknown"),
        (fake_pe([".text"]), "qualquer.exe", "unknown"),
        (b"#!/bin/sh Inno Setup", "script.sh", "unknown"),
    ],
)
def test_detect(head: bytes, name: str, kind: str) -> None:
    assert detect_type(head, name, SIGS) == kind


def test_default_args() -> None:
    assert default_args("nsis", SIGS) == ["/S"]
    assert default_args("inno", SIGS)[0] == "/VERYSILENT"
    assert default_args("exe_custom", SIGS) == []


def test_read_head(tmp_path: Path) -> None:
    f = tmp_path / "a.bin"
    f.write_bytes(b"x" * 10)
    assert read_head(f, 4) == b"xxxx"
