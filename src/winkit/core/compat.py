"""Quais etapas servem para cada Windows alvo (V3-14, R-63) e drivers que o 7 não tem."""

from __future__ import annotations

#: Seções do Studio que **não** funcionam no modo limitado (7 e 8.1, agente legado, D-050).
LEGACY_UNSUPPORTED = frozenset(
    {
        "bloat",  # Appx
        "start",
        "defaults",
        "appearance",
        "browsers",
        "dns",
        "drives",
        "maintenance",
        "env",
        "fonts",
        "folders",
        "games",
        "live",  # "Aplicar neste PC" usa o Agente de verdade
        "suggest",
    }
)
#: Classe PCI → tipo de controlador que o Windows 7 não tem nativamente (H41).
WIN7_MISSING = {"CC_0C0330": "usb3", "CC_010802": "nvme"}


def supported(section_id: str, version: str) -> bool:
    return version not in ("7", "8.1") or section_id not in LEGACY_UNSUPPORTED


def missing_native_drivers(version: str, hardware_ids: list[str]) -> list[str]:
    """Controladores deste PC que o Windows alvo não reconhece sozinho (ex.: USB 3.0 no 7)."""
    if version != "7":
        return []
    found = set()
    for hid in hardware_ids:
        for code, kind in WIN7_MISSING.items():
            if code in hid.upper():
                found.add(kind)
    return sorted(found)
