"""Gera packaging/winkit.ico (16 a 256 px, PNG dentro) e docs/imagens/logo.png a partir do logo vetorial.

Uso (na raiz do repositório): uv run python packaging/make_icon.py
O desenho fica em ``winkit.ui.widgets.paint_logo``; este script só o exporta.
"""

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from winkit.ui.widgets import paint_logo  # noqa: E402

ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
ROOT = Path(__file__).resolve().parents[1]


def png(size: int) -> bytes:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(0)
    painter = QPainter(img)
    paint_logo(painter, size)
    painter.end()
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(data.data())


def ico(images: list[tuple[int, bytes]]) -> bytes:
    """Formato ICO com entradas PNG (aceito desde o Windows Vista)."""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for size, blob in images:
        dim = 0 if size >= 256 else size  # 0 = 256 no formato ICO
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        blobs += blob
        offset += len(blob)
    return header + entries + blobs


app = QApplication(sys.argv)
(ROOT / "packaging" / "winkit.ico").write_bytes(ico([(s, png(s)) for s in ICO_SIZES]))
(ROOT / "docs" / "imagens" / "logo.png").write_bytes(png(512))
print("winkit.ico e logo.png gerados")
