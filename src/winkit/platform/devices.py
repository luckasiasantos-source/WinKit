"""Dispositivos com problema pelo CIM ``Win32_PnPEntity`` (V2-09). Só JSON, nunca texto."""

from __future__ import annotations

from typing import Any, Protocol

from winkit.core.devices import ProblemDevice
from winkit.platform.powershell import PowerShell

_PROBLEMS = r"""
Get-CimInstance -ClassName Win32_PnPEntity -Filter 'ConfigManagerErrorCode <> 0' |
    ForEach-Object {
        [pscustomobject]@{
            Name = [string]$_.Name
            DeviceID = [string]$_.PNPDeviceID
            Code = [int]$_.ConfigManagerErrorCode
            HardwareID = @($_.HardwareID | ForEach-Object { [string]$_ })
        }
    }
"""


class DeviceInspector(Protocol):
    def problem_devices(self) -> list[ProblemDevice]: ...


def parse_devices(rows: list[Any]) -> list[ProblemDevice]:
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ids = row.get("HardwareID") or []
        if isinstance(ids, str):
            ids = [ids]
        out.append(
            ProblemDevice(
                name=str(row.get("Name") or row.get("DeviceID") or "?"),
                device_id=str(row.get("DeviceID") or ""),
                code=int(row.get("Code") or 0),
                hardware_ids=tuple(str(x) for x in ids if x),
            )
        )
    return [d for d in out if d.code != 0]


class WindowsDeviceInspector:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def problem_devices(self) -> list[ProblemDevice]:
        return parse_devices(self._ps.run_json(_PROBLEMS, {}, timeout=300))
