"""Nome da família de um arquivo de fonte (V2-07): tabela ``name`` do OpenType/TrueType/TTC.

Leitor puro, sem dependência nova. Usa ``nameID`` 1 (família) e 4 (nome completo), dando
preferência à plataforma Windows (3) em inglês dos EUA (``0x0409``).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

TRUETYPE = b"\x00\x01\x00\x00"
OPENTYPE_CFF = b"OTTO"
APPLE_TRUE = b"true"
COLLECTION = b"ttcf"
FONT_EXTENSIONS = (".ttf", ".otf", ".ttc")
FONTS_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
USER_FONTS_KEY = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"
INSTALL_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"


class FontError(ValueError):
    """Arquivo que não é uma fonte OpenType/TrueType legível."""


@dataclass(frozen=True)
class FontNames:
    family: str
    full_name: str
    #: ``OpenType`` para contornos CFF, ``TrueType`` para os outros (sufixo do registro).
    kind: str


def _u16(data: bytes, offset: int) -> int:
    return int(struct.unpack_from(">H", data, offset)[0])


def _u32(data: bytes, offset: int) -> int:
    return int(struct.unpack_from(">I", data, offset)[0])


def _name_table(data: bytes, base: int) -> tuple[int, int]:
    tag = data[base : base + 4]
    if tag not in (TRUETYPE, OPENTYPE_CFF, APPLE_TRUE):
        raise FontError("assinatura de fonte desconhecida")
    count = _u16(data, base + 4)
    for i in range(count):
        rec = base + 12 + 16 * i
        if data[rec : rec + 4] == b"name":
            return _u32(data, rec + 8), _u32(data, rec + 12)
    raise FontError("a fonte não tem a tabela 'name'")


def _decode(raw: bytes, platform: int) -> str:
    if platform in (0, 3):
        return raw.decode("utf-16-be", errors="replace")
    return raw.decode("latin-1")


def _pick(data: bytes, offset: int, length: int, name_id: int) -> str | None:
    if offset + 6 > len(data) or offset + length > len(data):
        raise FontError("tabela 'name' fora do arquivo")
    count = _u16(data, offset + 2)
    strings = offset + _u16(data, offset + 4)
    best: tuple[int, str] | None = None
    for i in range(count):
        rec = offset + 6 + 12 * i
        platform, _enc, lang, nid, size, off = struct.unpack_from(">HHHHHH", data, rec)
        if nid != name_id:
            continue
        rank = 0 if (platform, lang) == (3, 0x0409) else 1 if platform == 3 else 2
        if best is None or rank < best[0]:
            text = _decode(data[strings + off : strings + off + size], platform).strip()
            if text:
                best = (rank, text)
    return best[1] if best else None


def read_names(data: bytes) -> FontNames:
    """Nomes da primeira fonte do arquivo (numa coleção TTC, a primeira da lista)."""
    try:
        base = _u32(data, 12) if data[:4] == COLLECTION else 0
        offset, length = _name_table(data, base)
        family = _pick(data, offset, length, 1)
        full = _pick(data, offset, length, 4) or family
    except struct.error as exc:
        raise FontError(f"arquivo de fonte truncado: {exc}") from exc
    if not family or not full:
        raise FontError("a fonte não tem nome de família")
    kind = "OpenType" if data[base : base + 4] == OPENTYPE_CFF else "TrueType"
    return FontNames(family=family, full_name=full, kind=kind)


def registry_name(names: FontNames) -> str:
    """Nome do valor em ``...\\CurrentVersion\\Fonts`` (ex.: ``Inter Regular (TrueType)``)."""
    return f"{names.full_name} ({names.kind})"
