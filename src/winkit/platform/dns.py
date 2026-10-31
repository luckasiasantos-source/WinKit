"""Servidores DNS e DNS criptografado (DoH) pelo módulo ``DnsClient`` (V2-16).

Só JSON e enums; nada de texto formatado (R-13). Sem os cmdlets de DoH (Windows 10), só os
servidores são configurados.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from winkit.platform.powershell import PowerShell

#: Política de DNS criptografado (``HKLM``), documentada pela Microsoft.
DOH_POLICY_KEY = r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient"
DOH_POLICY_VALUE = "DoHPolicy"
DOH_ALLOW = 2
DOH_REQUIRE = 3

_ADAPTERS = r"""
Get-NetAdapter -Physical -ErrorAction SilentlyContinue | ForEach-Object {
    $i = $_.ifIndex
    $v4 = @(Get-DnsClientServerAddress -InterfaceIndex $i -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        ForEach-Object { $_.ServerAddresses } | ForEach-Object { [string]$_ })
    $v6 = @(Get-DnsClientServerAddress -InterfaceIndex $i -AddressFamily IPv6 -ErrorAction SilentlyContinue |
        ForEach-Object { $_.ServerAddresses } | ForEach-Object { [string]$_ })
    [pscustomobject]@{ Index = [int]$i; Name = [string]$_.Name; IPv4 = $v4; IPv6 = $v6 }
}
"""

_SET = r"""
Set-DnsClientServerAddress -InterfaceIndex $p.Index -ServerAddresses @($p.Servers)
'ok'
"""

_DOH_LIST = r"""
if (-not (Get-Command Get-DnsClientDohServerAddress -ErrorAction SilentlyContinue)) {
    [pscustomobject]@{ Available = $false; Servers = @() }
    return
}
$s = @(Get-DnsClientDohServerAddress -ErrorAction SilentlyContinue | ForEach-Object {
    [pscustomobject]@{ Server = [string]$_.ServerAddress; Template = [string]$_.DohTemplate }
})
[pscustomobject]@{ Available = $true; Servers = $s }
"""

_DOH_SET = r"""
$fallback = -not $p.Require
$e = Get-DnsClientDohServerAddress -ServerAddress $p.Server -ErrorAction SilentlyContinue
if ($e) {
    Set-DnsClientDohServerAddress -ServerAddress $p.Server -DohTemplate $p.Template `
        -AllowFallbackToUdp $fallback -AutoUpgrade $true | Out-Null
} else {
    Add-DnsClientDohServerAddress -ServerAddress $p.Server -DohTemplate $p.Template `
        -AllowFallbackToUdp $fallback -AutoUpgrade $true | Out-Null
}
'ok'
"""


@dataclass(frozen=True)
class AdapterDns:
    index: int
    name: str
    ipv4: tuple[str, ...]
    ipv6: tuple[str, ...]


@dataclass(frozen=True)
class DohState:
    available: bool
    servers: dict[str, str]  # servidor → modelo


class DnsClient(Protocol):
    def adapters(self) -> list[AdapterDns]:
        """Adaptadores físicos (Wi-Fi e Ethernet) e os servidores atuais de cada um."""
        ...

    def set_servers(self, index: int, servers: list[str]) -> None: ...

    def doh(self) -> DohState: ...

    def set_doh(self, server: str, template: str, *, require: bool) -> None: ...


def _strs(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(x) for x in value if x)


def parse_adapters(rows: list[Any]) -> list[AdapterDns]:
    return [
        AdapterDns(
            int(r["Index"]), str(r.get("Name") or ""), _strs(r.get("IPv4")), _strs(r.get("IPv6"))
        )
        for r in rows
        if isinstance(r, dict) and r.get("Index") is not None
    ]


class WindowsDnsClient:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def adapters(self) -> list[AdapterDns]:
        return parse_adapters(self._ps.run_json(_ADAPTERS, {}, timeout=120))

    def set_servers(self, index: int, servers: list[str]) -> None:
        self._ps.run_json(_SET, {"Index": index, "Servers": servers}, timeout=120)

    def doh(self) -> DohState:
        out = self._ps.run_json(_DOH_LIST, {}, timeout=120)
        data = out[0] if out and isinstance(out[0], dict) else {}
        servers = {
            str(s["Server"]): str(s.get("Template") or "")
            for s in data.get("Servers") or []
            if isinstance(s, dict) and s.get("Server")
        }
        return DohState(bool(data.get("Available")), servers)

    def set_doh(self, server: str, template: str, *, require: bool) -> None:
        params = {"Server": server, "Template": template, "Require": require}
        self._ps.run_json(_DOH_SET, params, timeout=120)
