"""Ociosidade da sessão e reinicialização (PLANO.md §11.5)."""

from __future__ import annotations

import ctypes
import sys
from typing import Protocol

from winkit.platform.runner import CommandRunner
from winkit.platform.system import system32


class SessionControl(Protocol):
    def idle_seconds(self) -> float: ...

    def reboot(self, *, delay_seconds: int, message: str) -> None: ...


class _LastInputInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


class WindowsSessionControl:
    def __init__(self, runner: CommandRunner) -> None:
        self._runner = runner

    def idle_seconds(self) -> float:  # pragma: no cover — CI Windows
        if sys.platform != "win32":
            return 0.0
        info = _LastInputInfo()
        info.cbSize = ctypes.sizeof(_LastInputInfo)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        now = int(ctypes.windll.kernel32.GetTickCount())
        elapsed_ms = (now - int(info.dwTime)) & 0xFFFFFFFF
        return max(0.0, elapsed_ms / 1000.0)

    def reboot(self, *, delay_seconds: int, message: str) -> None:
        self._runner.run(
            [str(system32("shutdown.exe")), "/r", "/t", str(delay_seconds), "/c", message[:500]],
            timeout=60,
        )
