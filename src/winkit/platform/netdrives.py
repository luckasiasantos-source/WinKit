"""Unidades de rede (V2-17): registro ``Network`` e ``WScript.Network`` para o modo ao vivo.

O nome do provedor (``ProviderName``) é **lido do próprio Windows**, nunca escrito por nós:
ele muda com o idioma ("Microsoft Windows Network" / "Rede Microsoft Windows") — R-13.
"""

from __future__ import annotations

from typing import Protocol

from winkit.platform.powershell import PowerShell
from winkit.platform.registry import Registry

NETWORK_KEY = "Network"
PROVIDER_KEY = r"SYSTEM\CurrentControlSet\Services\LanmanWorkstation\NetworkProvider"
#: Valores gravados pelo próprio Windows para uma unidade SMB persistente.
CONNECTION_TYPE = 1  # disco
PROVIDER_TYPE = 0x20000  # WNNC_NET_LANMAN
DEFER_FLAGS = 4  # reconecta só quando a unidade é usada

_MAP = r"""
try {
    $n = New-Object -ComObject WScript.Network
    $n.MapNetworkDrive("$($p.Letter):", $p.Path, $true)
    'ok'
} catch { 'fail' }
"""


def read_mapped(registry: Registry, hive: str = "HKCU", prefix: str = "") -> dict[str, str]:
    """Letra → caminho (``RemotePath``); ``UserName`` e o resto são ignorados de propósito."""
    base = f"{prefix}\\{NETWORK_KEY}" if prefix else NETWORK_KEY
    out = {}
    for letter in registry.subkeys(hive, base):
        path = registry.get(hive, f"{base}\\{letter}", "RemotePath")
        if isinstance(path, str) and len(letter) == 1 and letter.isalpha():
            out[letter.upper()] = path
    return out


def provider_name(registry: Registry) -> str | None:
    value = registry.get("HKLM", PROVIDER_KEY, "Name")
    return value if isinstance(value, str) and value else None


def write_mapping(
    registry: Registry, hive: str, prefix: str, letter: str, path: str, *, provider: str | None
) -> None:
    key = f"{prefix}\\{NETWORK_KEY}\\{letter}" if prefix else f"{NETWORK_KEY}\\{letter}"
    registry.set(hive, key, "RemotePath", "sz", path)
    registry.set(hive, key, "ConnectionType", "dword", CONNECTION_TYPE)
    registry.set(hive, key, "ProviderType", "dword", PROVIDER_TYPE)
    registry.set(hive, key, "DeferFlags", "dword", DEFER_FLAGS)
    if provider:
        registry.set(hive, key, "ProviderName", "sz", provider)


class DriveMapper(Protocol):
    def map_now(self, letter: str, path: str) -> bool:
        """Mapeia na sessão atual e guarda como persistente; False se o servidor não respondeu."""
        ...


class WindowsDriveMapper:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def map_now(self, letter: str, path: str) -> bool:
        out = self._ps.run_json(_MAP, {"Letter": letter, "Path": path}, timeout=120)
        return out == ["ok"]
