"""Carregar uma fonte na sessão atual sem sair dela (V2-07, modo ao vivo)."""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from typing import Protocol

HWND_BROADCAST = 0xFFFF
WM_FONTCHANGE = 0x001D
SMTO_ABORTIFHUNG = 0x0002


class FontLoader(Protocol):
    def load(self, path: Path) -> bool:
        """``AddFontResourceW`` + ``WM_FONTCHANGE``; False se o Windows recusou."""
        ...


class WindowsFontLoader:
    def load(self, path: Path) -> bool:
        if sys.platform != "win32":
            return False
        added = ctypes.windll.gdi32.AddFontResourceW(str(path))  # type: ignore[attr-defined,unused-ignore]
        result = ctypes.c_ulong()
        ctypes.windll.user32.SendMessageTimeoutW(  # type: ignore[attr-defined,unused-ignore]
            HWND_BROADCAST, WM_FONTCHANGE, 0, 0, SMTO_ABORTIFHUNG, 5000, ctypes.byref(result)
        )
        return bool(added)
