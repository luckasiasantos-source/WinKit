"""Barra de título, contorno e cantos da janela no tema do app (Windows 11, DWM; V3-03).

O Windows desenha a moldura; sem isto a barra segue o tema do sistema e destoa do app
(ex.: barra preta sobre conteúdo claro). O Windows 10 recusa os atributos novos e mantém
a moldura padrão, sem erro.
"""

from __future__ import annotations

import ctypes
import sys

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
DWMWCP_ROUND = 2


def colorref(hex_color: str) -> int:
    """``"#RRGGBB"`` → ``COLORREF`` (0x00BBGGRR)."""
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return r | g << 8 | b << 16


def style_window(hwnd: int, *, dark: bool, caption: str, border: str, text: str) -> bool:
    """Aplica os atributos; ``False`` fora do Windows ou se o DWM recusar o modo escuro."""
    if sys.platform != "win32":
        return False
    dwm = ctypes.windll.dwmapi  # type: ignore[attr-defined,unused-ignore]

    def set_attr(attr: int, value: int) -> bool:
        v = ctypes.c_int(value)
        return bool(
            dwm.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd), attr, ctypes.byref(v), ctypes.sizeof(v)
            )
            == 0
        )

    ok = set_attr(DWMWA_USE_IMMERSIVE_DARK_MODE, int(dark))
    set_attr(DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND)
    set_attr(DWMWA_BORDER_COLOR, colorref(border))
    set_attr(DWMWA_CAPTION_COLOR, colorref(caption))
    set_attr(DWMWA_TEXT_COLOR, colorref(text))
    return ok
