"""Gera packaging/winkit.ico a partir do ícone desenhado em winkit.ui.widgets.app_icon."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from winkit.ui.widgets import app_icon  # noqa: E402

app = QApplication(sys.argv)
out = Path(__file__).with_name("winkit.ico")
pixmap = app_icon(256).pixmap(256, 256)
if not pixmap.save(str(out), "ICO"):
    pixmap.save(str(out.with_suffix(".png")), "PNG")
    print("Aviso: plugin ICO indisponível; gerado PNG")
print(out)
