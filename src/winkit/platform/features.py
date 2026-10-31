"""Recursos opcionais do Windows (ex.: Recall) e computador (renomear)."""

from __future__ import annotations

from typing import Literal, Protocol

from winkit.platform.powershell import PowerShell

FeatureResult = Literal["absent", "same", "changed", "restart"]

_FEATURE = r"""
$f = Get-WindowsOptionalFeature -Online -FeatureName $p.Name -ErrorAction SilentlyContinue
if (-not $f) { 'absent'; return }
$off = @('Disabled', 'DisabledWithPayloadRemoved')
if ($p.Enable) {
    if ($f.State -eq 'Enabled') { 'same'; return }
    $r = Enable-WindowsOptionalFeature -Online -FeatureName $p.Name -NoRestart
} else {
    if ($off -contains [string]$f.State) { 'same'; return }
    $r = Disable-WindowsOptionalFeature -Online -FeatureName $p.Name -NoRestart
}
if ($r.RestartNeeded) { 'restart' } else { 'changed' }
"""

_RENAME = r"""
if ($env:COMPUTERNAME -eq $p.Name) { 'same'; return }
Rename-Computer -NewName $p.Name -Force | Out-Null
'renamed'
"""


class SystemFeatures(Protocol):
    def set_optional_feature(self, name: str, *, enabled: bool) -> FeatureResult: ...

    def rename_computer(self, name: str) -> bool:
        """True se renomeou (exige reinício); False se já tinha esse nome."""
        ...


class WindowsSystemFeatures:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def set_optional_feature(self, name: str, *, enabled: bool) -> FeatureResult:
        out = self._ps.run_json(_FEATURE, {"Name": name, "Enable": enabled}, timeout=1800)
        value = str(out[0]) if out else "absent"
        return value if value in ("absent", "same", "changed", "restart") else "changed"  # type: ignore[return-value]

    def rename_computer(self, name: str) -> bool:
        return self._ps.run_json(_RENAME, {"Name": name}, timeout=300) == ["renamed"]
