"""Tema claro/escuro inspirado no macOS ("Ajustes do Sistema"), D-026.

Tokens de cor em um lugar só; a folha de estilo é gerada a partir deles.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication

FONT_STACK = ["Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue", "Arial"]


@dataclass(frozen=True)
class Palette:
    name: str
    window: str  # fundo da janela
    sidebar: str  # barra lateral (levemente diferente, como no Mac)
    card: str  # grupos arredondados
    card_border: str
    separator: str
    text: str
    secondary: str  # texto cinza
    tertiary: str
    accent: str  # azul do sistema
    accent_pressed: str
    accent_text: str
    success: str
    warning: str
    danger: str
    control: str  # fundo de botão secundário / campo
    control_hover: str
    switch_off: str
    selection: str  # linha selecionada na barra lateral


LIGHT = Palette(
    name="light",
    window="#F5F5F7",
    sidebar="#ECECEE",
    card="#FFFFFF",
    card_border="#E3E3E6",
    separator="#E6E6E9",
    text="#1D1D1F",
    secondary="#6E6E73",
    tertiary="#A1A1A6",
    accent="#007AFF",
    accent_pressed="#0062CC",
    accent_text="#FFFFFF",
    success="#34C759",
    warning="#FF9500",
    danger="#FF3B30",
    control="#E9E9EB",
    control_hover="#DEDEE1",
    switch_off="#E3E3E8",
    selection="#DCDCE0",
)

DARK = Palette(
    name="dark",
    window="#1E1E1E",
    sidebar="#262628",
    card="#2C2C2E",
    card_border="#3A3A3C",
    separator="#3A3A3C",
    text="#F5F5F7",
    secondary="#98989D",
    tertiary="#636366",
    accent="#0A84FF",
    accent_pressed="#0070E0",
    accent_text="#FFFFFF",
    success="#30D158",
    warning="#FF9F0A",
    danger="#FF453A",
    control="#3A3A3C",
    control_hover="#48484A",
    switch_off="#39393D",
    selection="#3A3A3C",
)


def system_is_dark() -> bool:
    hints = QGuiApplication.styleHints()
    try:
        return hints.colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:  # Qt < 6.5
        return QGuiApplication.palette().color(QPalette.ColorRole.Window).lightness() < 128


def current(mode: str = "auto") -> Palette:
    """``auto`` segue o Windows; ``light``/``dark`` forçam (Preferências do Studio)."""
    if mode == "light":
        return LIGHT
    if mode == "dark":
        return DARK
    return DARK if system_is_dark() else LIGHT


def chevron_file(p: Palette) -> str:
    """Seta "para baixo" desenhada em PNG (QSS não desenha triângulos de forma confiável)."""
    path = Path(tempfile.gettempdir()) / f"winkit-chevron-{p.name}.png"
    if not path.exists():
        pm = QPixmap(20, 20)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(
            QPen(
                QColor(p.secondary),
                2.4,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        line = QPainterPath(QPointF(5, 8))
        line.lineTo(10, 13)
        line.lineTo(15, 8)
        painter.drawPath(line)
        painter.end()
        pm.save(str(path))
    return path.as_posix()


def stylesheet(p: Palette) -> str:
    chevron = chevron_file(p)
    return f"""
* {{ font-family: {", ".join(f'"{f}"' for f in FONT_STACK)}; color: {p.text}; }}
QWidget#Root, QMainWindow, QDialog {{ background: {p.window}; }}
QWidget#Sidebar {{ background: {p.sidebar}; border-right: 1px solid {p.separator}; }}
QLabel#LargeTitle {{ font-size: 26px; font-weight: 700; }}
QLabel#Title {{ font-size: 20px; font-weight: 650; }}
QLabel#Headline {{ font-size: 15px; font-weight: 600; }}
QLabel#Body {{ font-size: 13px; }}
QLabel#Secondary, QLabel#Caption {{ color: {p.secondary}; font-size: 12px; }}
QLabel#SectionHeader {{ color: {p.secondary}; font-size: 12px; font-weight: 600;
    text-transform: uppercase; padding: 0 0 2px 14px; }}
QLabel#Danger {{ color: {p.danger}; }}
QLabel#Warning {{ color: {p.warning}; }}
QFrame#Card {{ background: {p.card}; border: 1px solid {p.card_border}; border-radius: 12px; }}
QFrame#Separator {{ background: {p.separator}; max-height: 1px; min-height: 1px; border: none; }}
QPushButton {{ background: {p.control}; border: none; border-radius: 8px; padding: 7px 16px;
    font-size: 13px; font-weight: 500; }}
QPushButton:hover {{ background: {p.control_hover}; }}
QPushButton:disabled {{ color: {p.tertiary}; }}
QPushButton#Primary {{ background: {p.accent}; color: {p.accent_text}; font-weight: 600; }}
QPushButton#Primary:hover {{ background: {p.accent_pressed}; }}
QPushButton#Primary:disabled {{ background: {p.control}; color: {p.tertiary}; }}
QPushButton#Destructive {{ color: {p.danger}; }}
QPushButton#Link {{ background: transparent; color: {p.accent}; padding: 2px 4px; }}
QLineEdit, QComboBox, QSpinBox {{ background: {p.card}; border: 1px solid {p.card_border};
    border-radius: 7px; padding: 6px 9px; font-size: 13px; selection-background-color: {p.accent}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 2px solid {p.accent}; padding: 5px 8px; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: url("{chevron}"); width: 10px; height: 10px; margin-right: 8px; }}
QComboBox QAbstractItemView {{ background: {p.card}; border: 1px solid {p.card_border};
    border-radius: 8px; padding: 4px; selection-background-color: {p.accent};
    selection-color: {p.accent_text}; outline: none; }}
QListWidget#SidebarList {{ background: transparent; border: none; outline: none; font-size: 13px; }}
QListWidget#SidebarList::item {{ padding: 7px 10px; border-radius: 7px; margin: 1px 8px; }}
QListWidget#SidebarList::item:selected {{ background: {p.selection}; color: {p.text}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px 1px; }}
QScrollBar::handle:vertical {{ background: {p.separator}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {p.tertiary}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QProgressBar {{ background: {p.switch_off}; border: none; border-radius: 3px; max-height: 6px;
    min-height: 6px; text-align: center; }}
QProgressBar::chunk {{ background: {p.accent}; border-radius: 3px; }}
QWidget#Segmented {{ background: {p.control}; border-radius: 8px; }}
QPushButton#Segment {{ background: transparent; border-radius: 6px; padding: 5px 14px; margin: 2px;
    font-weight: 500; }}
QPushButton#Segment:checked {{ background: {p.card}; color: {p.text}; font-weight: 600;
    border: 1px solid {p.card_border}; }}
QPushButton#Pill {{ background: transparent; border: 1px solid {p.card_border}; border-radius: 10px;
    padding: 2px 10px; font-size: 11px; color: {p.secondary}; }}
QPushButton#Pill:checked {{ background: {p.accent}; border-color: {p.accent}; color: {p.accent_text}; }}
QLabel#Badge {{ background: {p.control}; border-radius: 9px; padding: 1px 8px; font-size: 11px;
    color: {p.secondary}; }}
QLabel#SidebarTitle {{ font-size: 15px; font-weight: 700; }}
QToolTip {{ background: {p.card}; color: {p.text}; border: 1px solid {p.card_border};
    border-radius: 6px; padding: 4px 8px; }}
"""


def apply(app: QApplication, mode: str = "auto") -> Palette:
    p = current(mode)
    font = QFont()
    font.setFamilies(FONT_STACK)
    font.setPointSizeF(10)
    app.setFont(font)
    app.setStyle("Fusion")  # base neutra; o visual vem da folha de estilo
    app.setStyleSheet(stylesheet(p))
    return p
