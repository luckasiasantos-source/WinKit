"""Recursos opcionais e capacidades do Windows (Recall, WSL, OpenSSH…) e nome do computador.

Os estados vêm dos enums do DISM convertidos em texto (``Enabled``, ``Installed``), que não
são traduzidos — nunca a saída formatada do PowerShell (R-13).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Protocol

from winkit.platform.powershell import PowerShell

FeatureResult = Literal["absent", "same", "changed", "restart"]
_RESULTS = ("absent", "same", "changed", "restart")

_FEATURE = r"""
$f = Get-WindowsOptionalFeature -Online -FeatureName $p.Name -ErrorAction SilentlyContinue
if (-not $f) { 'absent'; return }
$off = @('Disabled', 'DisabledWithPayloadRemoved')
if ($p.Enable) {
    if ([string]$f.State -eq 'Enabled') { 'same'; return }
    $args = @{ Online = $true; FeatureName = $p.Name; All = $true; NoRestart = $true }
    if ($p.Source) { $args.Source = $p.Source; $args.LimitAccess = $true }
    $r = Enable-WindowsOptionalFeature @args
} else {
    if ($off -contains [string]$f.State) { 'same'; return }
    $r = Disable-WindowsOptionalFeature -Online -FeatureName $p.Name -NoRestart
}
if ($r.RestartNeeded) { 'restart' } else { 'changed' }
"""

_CAPABILITY = r"""
$c = Get-WindowsCapability -Online -Name $p.Name -ErrorAction SilentlyContinue
if (-not $c) { 'absent'; return }
if ($p.Install) {
    if ([string]$c.State -eq 'Installed') { 'same'; return }
    $r = Add-WindowsCapability -Online -Name $p.Name
} else {
    if ([string]$c.State -ne 'Installed') { 'same'; return }
    $r = Remove-WindowsCapability -Online -Name $p.Name
}
if ($r.RestartNeeded) { 'restart' } else { 'changed' }
"""

_STATES = r"""
$out = @{}
foreach ($n in @($p.Features)) {
    $f = Get-WindowsOptionalFeature -Online -FeatureName $n -ErrorAction SilentlyContinue
    if ($f) { $out[$n] = ([string]$f.State -eq 'Enabled') }
}
foreach ($n in @($p.Capabilities)) {
    $c = Get-WindowsCapability -Online -Name $n -ErrorAction SilentlyContinue
    if ($c) { $out[$n] = ([string]$c.State -eq 'Installed') }
}
[pscustomobject]$out
"""

_RENAME = r"""
if ($env:COMPUTERNAME -eq $p.Name) { 'same'; return }
Rename-Computer -NewName $p.Name -Force | Out-Null
'renamed'
"""


class SystemFeatures(Protocol):
    def set_optional_feature(
        self, name: str, *, enabled: bool, source: Path | None = None
    ) -> FeatureResult:
        """Liga/desliga um *optional feature*. ``source`` = pasta ``sxs`` (sem internet)."""
        ...

    def set_capability(self, name: str, *, installed: bool) -> FeatureResult: ...

    def states(self, features: list[str], capabilities: list[str]) -> dict[str, bool]:
        """Nome → ligado/instalado. Nomes que o Windows não conhece ficam de fora."""
        ...

    def rename_computer(self, name: str) -> bool:
        """True se renomeou (exige reinício); False se já tinha esse nome."""
        ...


def _result(out: list[Any]) -> FeatureResult:
    value = str(out[0]) if out else "absent"
    return value if value in _RESULTS else "changed"  # type: ignore[return-value]


class WindowsSystemFeatures:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def set_optional_feature(
        self, name: str, *, enabled: bool, source: Path | None = None
    ) -> FeatureResult:
        params = {"Name": name, "Enable": enabled, "Source": str(source) if source else ""}
        return _result(self._ps.run_json(_FEATURE, params, timeout=1800))

    def set_capability(self, name: str, *, installed: bool) -> FeatureResult:
        params = {"Name": name, "Install": installed}
        return _result(self._ps.run_json(_CAPABILITY, params, timeout=3600))

    def states(self, features: list[str], capabilities: list[str]) -> dict[str, bool]:
        params = {"Features": features, "Capabilities": capabilities}
        out = self._ps.run_json(_STATES, params, timeout=600)
        data = out[0] if out and isinstance(out[0], dict) else {}
        return {str(k): bool(v) for k, v in data.items()}

    def rename_computer(self, name: str) -> bool:
        return self._ps.run_json(_RENAME, {"Name": name}, timeout=300) == ["renamed"]
