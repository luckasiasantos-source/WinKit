"""Uso de programas (``UserAssist``) pelo registro do usuário atual (V2-20)."""

from __future__ import annotations

from winkit.core.userassist import EXECUTABLES_GUID, SHORTCUTS_GUID, UsageEntry, parse_entry
from winkit.platform.registry import Registry

USERASSIST_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist"


def read_usage(registry: Registry) -> list[UsageEntry]:
    out = []
    for guid in (EXECUTABLES_GUID, SHORTCUTS_GUID):
        for name, data in registry.values("HKCU", f"{USERASSIST_KEY}\\{guid}\\Count").items():
            if isinstance(data, bytes | bytearray):
                entry = parse_entry(name, bytes(data))
                if entry is not None:
                    out.append(entry)
    return out
