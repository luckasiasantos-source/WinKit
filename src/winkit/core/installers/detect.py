"""Detecção do tipo de instalador pelo conteúdo (PLANO.md §13.3). Puro."""

from __future__ import annotations

import struct
from collections.abc import Sequence
from pathlib import Path

from winkit.core.catalog.models import InstallerSignature
from winkit.core.recipe.models import InstallerType

OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
ZIP_MAGIC = b"PK\x03\x04"
#: Quanto do arquivo é lido para procurar marcadores (os instaladores comuns gravam a
#: assinatura nos primeiros megabytes).
SCAN_BYTES = 8 * 1024 * 1024


def pe_section_names(data: bytes) -> list[str]:
    """Nomes das seções de um executável PE (para achar ``.wixburn``)."""
    if len(data) < 0x40 or data[:2] != b"MZ":
        return []
    (pe_offset,) = struct.unpack_from("<I", data, 0x3C)
    if pe_offset + 24 > len(data) or data[pe_offset : pe_offset + 4] != b"PE\0\0":
        return []
    (num_sections,) = struct.unpack_from("<H", data, pe_offset + 6)
    (opt_size,) = struct.unpack_from("<H", data, pe_offset + 20)
    table = pe_offset + 24 + opt_size
    names = []
    for i in range(min(num_sections, 96)):
        start = table + i * 40
        if start + 8 > len(data):
            break
        names.append(data[start : start + 8].rstrip(b"\0").decode("ascii", errors="replace"))
    return names


def detect_type(
    head: bytes, filename: str, signatures: Sequence[InstallerSignature]
) -> InstallerType:
    suffix = Path(filename).suffix.lower()
    sections = pe_section_names(head)
    for sig in signatures:
        if sig.extensions and suffix in sig.extensions:
            if sig.type == "msi" and not head.startswith(OLE_MAGIC):
                continue
            if sig.type == "msix" and not head.startswith(ZIP_MAGIC):
                continue
            return sig.type
        if sig.pe_section and sig.pe_section in sections:
            return sig.type
        if sig.markers and head[:2] == b"MZ" and any(m.encode() in head for m in sig.markers):
            return sig.type
    return "unknown"


def default_args(kind: InstallerType, signatures: Sequence[InstallerSignature]) -> list[str]:
    sig = next((s for s in signatures if s.type == kind), None)
    return list(sig.args) if sig else []


def read_head(path: Path, size: int = SCAN_BYTES) -> bytes:
    with path.open("rb") as fh:
        return fh.read(size)
