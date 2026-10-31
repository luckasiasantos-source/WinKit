"""Volumes do PC pelo CIM ``Win32_Volume`` (D-035). Só JSON e números (R-13)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Protocol

from winkit.core.volumes import VolumeInfo, normalize_serial
from winkit.platform.powershell import PowerShell

_VOLUMES = r"""
Get-CimInstance -ClassName Win32_Volume -Filter 'DriveType = 3' | ForEach-Object {
    [pscustomobject]@{
        Serial = $_.SerialNumber
        Letter = [string]$_.DriveLetter
        Label = [string]$_.Label
        Size = [uint64]$_.Capacity
        Free = [uint64]$_.FreeSpace
        System = [bool]($_.DriveLetter -eq $env:SystemDrive)
    }
}
"""


class Volumes(Protocol):
    def volumes(self) -> list[VolumeInfo]:
        """Discos fixos (internos e externos), com o número de série."""
        ...

    def root(self, letter: str) -> Path:
        """Pasta local da raiz do volume (nos testes, uma pasta temporária)."""
        ...


def parse_volumes(rows: list[Any]) -> list[VolumeInfo]:
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        serial = normalize_serial(r.get("Serial"))
        if serial is None:
            continue
        letter = str(r.get("Letter") or "").rstrip(":\\").upper() or None
        out.append(
            VolumeInfo(
                serial=serial,
                letter=letter if letter and len(letter) == 1 else None,
                label=str(r.get("Label") or "") or None,
                size=int(r.get("Size") or 0),
                free=int(r.get("Free") or 0),
                is_system=bool(r.get("System")),
            )
        )
    return out


class WindowsVolumes:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def volumes(self) -> list[VolumeInfo]:
        return parse_volumes(self._ps.run_json(_VOLUMES, {}, timeout=120))

    def root(self, letter: str) -> Path:
        if sys.platform != "win32":
            return Path("/") / letter
        return Path(f"{letter}:\\")
