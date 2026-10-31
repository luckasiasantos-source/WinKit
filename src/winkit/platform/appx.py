"""Pacotes Appx/MSIX: remoção para todos os usuários (PLANO.md §13.5, item 11)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from winkit.platform.powershell import PowerShell

DEPROVISIONED = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Appx\AppxAllUserStore\Deprovisioned"

_REMOVE = r"""
$prov = @(Get-AppxProvisionedPackage -Online | Where-Object { $_.DisplayName -eq $p.Name })
foreach ($x in $prov) { Remove-AppxProvisionedPackage -Online -PackageName $x.PackageName | Out-Null }
$inst = @(Get-AppxPackage -AllUsers -Name $p.Name)
foreach ($x in $inst) { Remove-AppxPackage -Package $x.PackageFullName -AllUsers -ErrorAction Continue }
$family = $null
if ($inst.Count -gt 0) { $family = [string]$inst[0].PackageFamilyName }
[pscustomobject]@{ Provisioned = $prov.Count; Installed = $inst.Count; Family = $family }
"""

_PRESENT = r"""
$prov = @(Get-AppxProvisionedPackage -Online | Where-Object { $_.DisplayName -eq $p.Name }).Count
$inst = @(Get-AppxPackage -AllUsers -Name $p.Name).Count
[pscustomobject]@{ Present = ($prov + $inst) -gt 0 }
"""


@dataclass(frozen=True)
class AppxRemoval:
    provisioned: int
    installed: int
    family: str | None


class AppxManager(Protocol):
    def remove(self, name: str) -> AppxRemoval: ...

    def is_present(self, name: str) -> bool: ...


class WindowsAppxManager:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def remove(self, name: str) -> AppxRemoval:
        out = self._ps.run_json(_REMOVE, {"Name": name}, timeout=900)
        data = out[0] if out else {}
        return AppxRemoval(
            provisioned=int(data.get("Provisioned") or 0),
            installed=int(data.get("Installed") or 0),
            family=data.get("Family") or None,
        )

    def is_present(self, name: str) -> bool:
        out = self._ps.run_json(_PRESENT, {"Name": name}, timeout=300)
        return bool(out and out[0].get("Present"))
