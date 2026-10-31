"""Pontos de restauração do sistema (V2-10, D-033), por CIM — nunca por texto (R-13).

``SystemRestore`` (``root\\default``): ``Enable``, ``CreateRestorePoint`` e a lista de pontos.
``Win32_ShadowStorage``: espaço máximo reservado. O limite de um ponto a cada 24 h é
contornado com ``SystemRestorePointCreationFrequency = 0`` e restaurado depois.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from winkit.platform.powershell import PowerShell

SR_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore"
SR_POLICY_KEY = r"SOFTWARE\Policies\Microsoft\Windows NT\SystemRestore"
FREQUENCY_VALUE = "SystemRestorePointCreationFrequency"
MODIFY_SETTINGS = 12
BEGIN_SYSTEM_CHANGE = 100


@dataclass(frozen=True)
class RestorePointInfo:
    sequence: int
    description: str


class RestorePoints(Protocol):
    def enable(self, drive: str) -> None:
        """Liga a proteção do sistema no volume (``C:\\``)."""
        ...

    def ensure_max_percent(self, drive: str, percent: int) -> None:
        """Garante pelo menos ``percent``% do volume reservado (nunca reduz)."""
        ...

    def create(self, description: str) -> int:
        """Cria o ponto; devolve o código de retorno do CIM (0 = ok)."""
        ...

    def list(self) -> list[RestorePointInfo]: ...


_ENABLE = r"""
Invoke-CimMethod -Namespace root/default -ClassName SystemRestore -MethodName Enable `
    -Arguments @{ Drive = $p.Drive } | Select-Object -ExpandProperty ReturnValue
"""

_MAX = r"""
$vol = Get-CimInstance Win32_Volume | Where-Object { $_.DriveLetter -eq $p.Letter }
if (-not $vol) { 'no_volume'; return }
$want = [uint64]($vol.Capacity * $p.Percent / 100)
$st = Get-CimInstance Win32_ShadowStorage | Where-Object { $_.Volume.DeviceID -eq $vol.DeviceID }
if (-not $st) { 'no_storage'; return }
if ($st.MaxSpace -ge $want) { 'same'; return }
Set-CimInstance -InputObject $st -Property @{ MaxSpace = $want }
'changed'
"""

_CREATE = r"""
Invoke-CimMethod -Namespace root/default -ClassName SystemRestore -MethodName CreateRestorePoint `
    -Arguments @{ Description = $p.Description; RestorePointType = [uint32]$p.Type; EventType = [uint32]$p.Event } |
    Select-Object -ExpandProperty ReturnValue
"""

_LIST = r"""
Get-CimInstance -Namespace root/default -ClassName SystemRestore -ErrorAction SilentlyContinue |
    ForEach-Object { [pscustomobject]@{ sequence = [int]$_.SequenceNumber; description = [string]$_.Description } }
"""


class WindowsRestorePoints:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def enable(self, drive: str) -> None:
        self._ps.run_json(_ENABLE, {"Drive": drive}, timeout=300)

    def ensure_max_percent(self, drive: str, percent: int) -> None:
        self._ps.run_json(_MAX, {"Letter": drive.rstrip("\\"), "Percent": percent}, timeout=300)

    def create(self, description: str) -> int:
        out = self._ps.run_json(
            _CREATE,
            {"Description": description, "Type": MODIFY_SETTINGS, "Event": BEGIN_SYSTEM_CHANGE},
            timeout=900,
        )
        return int(out[0]) if out else -1

    def list(self) -> list[RestorePointInfo]:
        out: list[Any] = self._ps.run_json(_LIST, {}, timeout=300)
        return [
            RestorePointInfo(int(i["sequence"]), str(i["description"]))
            for i in out
            if isinstance(i, dict)
        ]
