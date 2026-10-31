"""Informações da sessão atual (privilégio, ociosidade)."""

from __future__ import annotations

import ctypes
import sys


def is_admin() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False
