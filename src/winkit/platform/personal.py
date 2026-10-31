"""Aplicar a aparência na sessão atual (V2-06, modo ao vivo)."""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from typing import Protocol

SPI_SETDESKWALLPAPER = 0x0014
SPI_SETCURSORS = 0x0057
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02


class LiveAppearance(Protocol):
    def set_wallpaper(self, path: Path) -> bool: ...

    def reload_cursors(self) -> bool: ...


class WindowsLiveAppearance:
    def _spi(self, action: int, param: object) -> bool:
        if sys.platform != "win32":
            return False
        flags = SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        fn = ctypes.windll.user32.SystemParametersInfoW  # type: ignore[attr-defined,unused-ignore]
        return bool(fn(action, 0, param, flags))

    def set_wallpaper(self, path: Path) -> bool:
        return self._spi(SPI_SETDESKWALLPAPER, str(path))

    def reload_cursors(self) -> bool:
        return self._spi(SPI_SETCURSORS, None)
