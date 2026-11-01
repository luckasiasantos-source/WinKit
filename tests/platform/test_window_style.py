"""Moldura da janela (V3-03): conversão de cor e nada acontece fora do Windows."""

from __future__ import annotations

import sys

from winkit.platform.window_style import colorref, style_window


def test_colorref_is_bgr() -> None:
    assert colorref("#112233") == 0x332211
    assert colorref("#FFFFFF") == 0xFFFFFF


def test_noop_outside_windows() -> None:
    if sys.platform == "win32":  # no Windows, só confere que não levanta erro com janela inválida
        style_window(0, dark=True, caption="#000000", border="#000000", text="#FFFFFF")
    else:
        assert (
            style_window(0, dark=True, caption="#000000", border="#000000", text="#FFFFFF") is False
        )
