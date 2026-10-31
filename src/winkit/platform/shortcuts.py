"""Atalhos .lnk via WScript.Shell (PowerShell)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from winkit.platform.powershell import PowerShell

_CREATE = r"""
$dir = Split-Path -Parent $p.Path
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($p.Path)
$s.TargetPath = $p.Target
$s.Arguments = $p.Arguments
$s.WorkingDirectory = Split-Path -Parent $p.Target
$s.Save()
"""


class Shortcuts(Protocol):
    def create(self, path: Path, target: str, arguments: str = "") -> None: ...


class WindowsShortcuts:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def create(self, path: Path, target: str, arguments: str = "") -> None:
        self._ps.run(
            _CREATE, {"Path": str(path), "Target": target, "Arguments": arguments}, timeout=120
        )
