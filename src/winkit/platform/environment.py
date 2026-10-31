"""Unidades, rede, versão do Windows e trava de instância única."""

from __future__ import annotations

import contextlib
import ctypes
import os
import socket
import string
import sys
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from winkit.core.errors import PlatformError

NCSI_URL = "http://www.msftconnecttest.com/connecttest.txt"
NCSI_TEXT = b"Microsoft Connect Test"


class Environment(Protocol):
    def drive_roots(self) -> list[Path]: ...

    def has_internet(self) -> bool: ...

    def windows_build(self) -> int | None: ...

    def computer_name(self) -> str: ...


class WindowsEnvironment:
    def drive_roots(self) -> list[Path]:
        roots = []
        for letter in string.ascii_uppercase[2:]:  # A: e B: são disquetes históricos
            root = Path(f"{letter}:\\")
            with contextlib.suppress(OSError):
                if root.exists():
                    roots.append(root)
        return roots

    def has_internet(self) -> bool:
        """Mesmo teste que o Windows usa (NCSI): responde um texto fixo da Microsoft."""
        try:
            with urllib.request.urlopen(NCSI_URL, timeout=5) as resp:
                return bool(resp.read(64).startswith(NCSI_TEXT))
        except (TimeoutError, OSError):
            return False

    def windows_build(self) -> int | None:
        if sys.platform != "win32":
            return None
        build: int = getattr(sys, "getwindowsversion")().build  # noqa: B009 — só existe no Windows
        return build

    def computer_name(self) -> str:
        return os.environ.get("COMPUTERNAME") or socket.gethostname()


@contextlib.contextmanager
def single_instance(name: str, lock_dir: Path) -> Iterator[bool]:
    """Devolve ``True`` se esta é a única instância; ``False`` se já há outra rodando."""
    if sys.platform == "win32":  # pragma: no cover — CI Windows
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, f"Global\\{name}")
        already = kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
        try:
            yield not already
        finally:
            if handle:
                kernel32.CloseHandle(handle)
        return
    import fcntl  # noqa: PLC0415 — só existe fora do Windows

    lock_dir.mkdir(parents=True, exist_ok=True)
    path = lock_dir / f"{name}.lock"
    with path.open("w") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def require_windows() -> None:
    if sys.platform != "win32":
        raise PlatformError("esta operação só funciona no Windows")
