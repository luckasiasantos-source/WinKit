"""Uso de programas pelo ``UserAssist`` do Explorer (V2-20). Leitor puro, sem Windows.

- O nome do valor vem em ROT13 (``P:\\Cebtenz Svyrf\\...`` = ``C:\\Program Files\\...``).
- O dado tem 72 bytes (Windows 7 em diante, H34): contador em ``+4``, tempo em foco (ms) em
  ``+12`` e último uso (FILETIME) em ``+60``.
"""

from __future__ import annotations

import codecs
import struct
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

EXECUTABLES_GUID = "{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}"
SHORTCUTS_GUID = "{F4E57C4B-2036-45F0-A9AB-443BCFE33D9F}"
RECORD_SIZE = 72
_FILETIME_EPOCH = datetime(1601, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class UsageEntry:
    path: str
    count: int
    focus_ms: int
    last_used: datetime | None


def decode_name(name: str) -> str:
    return codecs.decode(name, "rot13")


def filetime(value: int) -> datetime | None:
    if value <= 0:
        return None
    try:
        return _FILETIME_EPOCH + timedelta(microseconds=value // 10)
    except OverflowError:
        return None


def parse_entry(name: str, data: bytes) -> UsageEntry | None:
    """``None`` para registros fora do formato (os de controle, ex.: ``UEME_CTLSESSION``)."""
    if len(data) != RECORD_SIZE:
        return None
    count, focus = struct.unpack_from("<I", data, 4)[0], struct.unpack_from("<I", data, 12)[0]
    last = struct.unpack_from("<Q", data, 60)[0]
    path = decode_name(name)
    if path.startswith("UEME_"):
        return None
    return UsageEntry(path=path, count=count, focus_ms=focus, last_used=filetime(last))


def make_entry(count: int, focus_ms: int, last_used: datetime | None) -> bytes:
    """Monta um registro no formato do Windows (usado pelos testes)."""
    data = bytearray(RECORD_SIZE)
    struct.pack_into("<I", data, 4, count)
    struct.pack_into("<I", data, 12, focus_ms)
    if last_used is not None:
        ticks = int((last_used - _FILETIME_EPOCH).total_seconds() * 10_000_000)
        struct.pack_into("<Q", data, 60, ticks)
    return bytes(data)
