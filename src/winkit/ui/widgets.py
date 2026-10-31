"""Componentes no estilo macOS: chave liga/desliga, grupos arredondados, linhas, ícones (D-026)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from winkit.i18n import t
from winkit.ui import theme


class ToggleSwitch(QAbstractButton):
    """Chave estilo iOS/macOS com animação suave."""

    toggledByUser = Signal(bool)  # noqa: N815 — convenção de nomes do Qt

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._offset = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)
        self.clicked.connect(lambda: self.toggledByUser.emit(self.isChecked()))

    def sizeHint(self) -> QSize:
        return QSize(42, 24)

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, event: object) -> None:
        p = theme.current()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        off, on = QColor(p.switch_off), QColor(p.accent if self.isEnabled() else p.tertiary)
        t = self._offset
        track = QColor(
            int(off.red() + (on.red() - off.red()) * t),
            int(off.green() + (on.green() - off.green()) * t),
            int(off.blue() + (on.blue() - off.blue()) * t),
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 4
        x = r.left() + 2 + (r.width() - d - 4) * t
        painter.setBrush(QColor(0, 0, 0, 40))
        painter.drawEllipse(QRectF(x, r.top() + 2.6, d, d))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRectF(x, r.top() + 2, d, d))


class Card(QFrame):
    """Grupo arredondado com linhas separadas por um traço fino (lista "inset")."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 2, 0, 2)
        self._layout.setSpacing(0)
        self._rows: list[QWidget] = []

    def add_row(self, row: QWidget) -> QWidget:
        if self._rows:
            sep = QFrame()
            sep.setObjectName("Separator")
            wrap = QHBoxLayout()
            wrap.setContentsMargins(14, 0, 0, 0)
            wrap.addWidget(sep)
            self._layout.addLayout(wrap)
        self._layout.addWidget(row)
        self._rows.append(row)
        return row

    def clear(self) -> None:
        _empty_layout(self._layout)
        self._rows.clear()

    @property
    def rows(self) -> list[QWidget]:
        return list(self._rows)


def _empty_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            break
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
            continue
        inner = item.layout()
        if inner is not None:
            _empty_layout(inner)


class Row(QWidget):
    """Linha: ícone opcional, título, subtítulo e um acessório à direita."""

    def __init__(
        self,
        title: str,
        subtitle: str | None = None,
        *,
        accessory: QWidget | None = None,
        icon: QIcon | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(44)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(12)
        self.icon_label: QLabel | None = None
        if icon is not None:
            self.icon_label = QLabel()
            self.icon_label.setPixmap(icon.pixmap(22, 22))
            self.icon_label.setFixedSize(24, 24)
            lay.addWidget(self.icon_label)
        texts = QVBoxLayout()
        texts.setSpacing(1)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("Body")
        self.title_label.setWordWrap(True)
        texts.addWidget(self.title_label)
        self.subtitle_label = QLabel(subtitle or "")
        self.subtitle_label.setObjectName("Caption")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))
        texts.addWidget(self.subtitle_label)
        lay.addLayout(texts, 1)
        self.accessory = accessory
        if accessory is not None:
            lay.addWidget(accessory, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_icon(self, icon: QIcon) -> None:
        if self.icon_label is not None:
            self.icon_label.setPixmap(icon.pixmap(22, 22))

    def set_subtitle(self, text: str | None) -> None:
        self.subtitle_label.setText(text or "")
        self.subtitle_label.setVisible(bool(text))


class SegmentedControl(QWidget):
    """Seletor em pílula (NSSegmentedControl)."""

    changed = Signal(str)

    def __init__(
        self, options: list[tuple[str, str]], value: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Segmented")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(0)
        self.buttons: dict[str, QPushButton] = {}
        for key, text in options:
            b = QPushButton(text)
            b.setObjectName("Segment")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.set_value(k, emit=True))
            lay.addWidget(b)
            self.buttons[key] = b
        self._value = value
        self.set_value(value)

    def value(self) -> str:
        return self._value

    def set_value(self, key: str, *, emit: bool = False) -> None:
        self._value = key
        for k, b in self.buttons.items():
            b.setChecked(k == key)
        if emit:
            self.changed.emit(key)


def ask_pill(checked: bool) -> QPushButton:
    """Botão pequeno "Perguntar" (decidir na hora, item 35)."""
    b = QPushButton(t("ui.ask"))
    b.setObjectName("Pill")
    b.setCheckable(True)
    b.setChecked(checked)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setToolTip(t("ui.ask_tip"))
    return b


def section(title: str, card: Card, *, footer: str | None = None) -> QWidget:
    """Cabeçalho cinza em maiúsculas + cartão + rodapé opcional (como no Mac)."""
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    if title:
        h = QLabel(title)
        h.setObjectName("SectionHeader")
        lay.addWidget(h)
    lay.addWidget(card)
    if footer:
        f = QLabel(footer)
        f.setObjectName("Caption")
        f.setWordWrap(True)
        f.setContentsMargins(14, 0, 14, 0)
        lay.addWidget(f)
    return box


def label(text: str, kind: str = "Body", *, wrap: bool = True) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName(kind)
    lbl.setWordWrap(wrap)
    return lbl


def button(
    text: str, kind: str | None = None, on_click: Callable[[], None] | None = None
) -> QPushButton:
    b = QPushButton(text)
    if kind:
        b.setObjectName(kind)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click is not None:
        b.clicked.connect(on_click)
    return b


def expanding() -> QWidget:
    w = QWidget()
    w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return w


# ------------------------------------------------------------------ ícones desenhados
def _canvas(size: int) -> tuple[QPixmap, QPainter]:
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    return pm, painter


def symbol_icon(kind: str, color: str, size: int = 22) -> QIcon:
    """Ícone "símbolo" num quadrado arredondado colorido, como nos Ajustes do Mac."""
    pm, painter = _canvas(size)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.24, size * 0.24)
    pen = QPen(
        QColor("#FFFFFF"),
        size * 0.09,
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin,
    )
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    s = size
    if kind == "check":
        path = QPainterPath(QPointF(s * 0.28, s * 0.52))
        path.lineTo(s * 0.44, s * 0.68)
        path.lineTo(s * 0.73, s * 0.34)
        painter.drawPath(path)
    elif kind == "cross":
        painter.drawLine(QPointF(s * 0.32, s * 0.32), QPointF(s * 0.68, s * 0.68))
        painter.drawLine(QPointF(s * 0.68, s * 0.32), QPointF(s * 0.32, s * 0.68))
    elif kind == "dot":
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(QPointF(s / 2, s / 2), s * 0.12, s * 0.12)
    elif kind == "minus":
        painter.drawLine(QPointF(s * 0.3, s / 2), QPointF(s * 0.7, s / 2))
    elif _glyph(painter, kind, s):
        pass
    else:  # letra
        font = QFont()
        font.setBold(True)
        font.setPixelSize(int(s * 0.55))
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, s, s), Qt.AlignmentFlag.AlignCenter, kind[:1].upper())
    painter.end()
    icon = QIcon(pm)
    icon.addPixmap(pm, QIcon.Mode.Selected)  # sem o escurecimento padrão ao selecionar
    return icon


def app_icon(size: int = 64) -> QIcon:
    """Ícone do WinKit: quadrado arredondado com degradê azul e um "W"."""

    pm, painter = _canvas(size)
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0, QColor("#4FA3FF"))
    grad.setColorAt(1, QColor("#0063E0"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(grad))
    painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.23, size * 0.23)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(int(size * 0.55))
    painter.setFont(font)
    painter.setPen(QColor("#FFFFFF"))
    painter.drawText(QRectF(0, 0, size, size * 0.98), Qt.AlignmentFlag.AlignCenter, "W")
    painter.end()
    return QIcon(pm)


#: Cor e símbolo por tipo de etapa (ícones da lista, como nos Ajustes do Mac).
KIND_STYLE: dict[str, tuple[str, str]] = {
    "driver": ("chip", "#8E8E93"),
    "bloat": ("trash", "#FF3B30"),
    "tweak": ("sliders", "#5856D6"),
    "power": ("bolt", "#FF9500"),
    "backup": ("folder", "#34C759"),
    "app": ("download", "#007AFF"),
    "shortcut": ("arrow", "#32ADE6"),
    "rename_computer": ("pencil", "#AF52DE"),
    "windows_update": ("refresh", "#0A84FF"),
    "finalize": ("check", "#34C759"),
}


def _glyph(painter: QPainter, kind: str, s: float) -> bool:
    """Desenha um símbolo simples em branco. Devolve False se não conhecer o símbolo."""

    def line(x1: float, y1: float, x2: float, y2: float) -> None:
        painter.drawLine(QPointF(s * x1, s * y1), QPointF(s * x2, s * y2))

    if kind == "download":
        line(0.5, 0.24, 0.5, 0.6)
        line(0.36, 0.47, 0.5, 0.61)
        line(0.64, 0.47, 0.5, 0.61)
        line(0.28, 0.74, 0.72, 0.74)
    elif kind == "folder":
        path = QPainterPath(QPointF(s * 0.24, s * 0.32))
        path.lineTo(s * 0.42, s * 0.32)
        path.lineTo(s * 0.48, s * 0.39)
        path.lineTo(s * 0.76, s * 0.39)
        path.lineTo(s * 0.76, s * 0.72)
        path.lineTo(s * 0.24, s * 0.72)
        path.closeSubpath()
        painter.drawPath(path)
    elif kind == "sliders":
        for y, knob in ((0.36, 0.38), (0.64, 0.62)):
            line(0.24, y, 0.76, y)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(QPointF(s * knob, s * y), s * 0.07, s * 0.07)
            painter.setBrush(Qt.BrushStyle.NoBrush)
    elif kind == "chip":
        painter.drawRoundedRect(QRectF(s * 0.32, s * 0.32, s * 0.36, s * 0.36), s * 0.05, s * 0.05)
        for k in (0.42, 0.58):
            line(k, 0.2, k, 0.3)
            line(k, 0.7, k, 0.8)
            line(0.2, k, 0.3, k)
            line(0.7, k, 0.8, k)
    elif kind == "trash":
        line(0.26, 0.32, 0.74, 0.32)
        line(0.42, 0.24, 0.58, 0.24)
        path = QPainterPath(QPointF(s * 0.32, s * 0.36))
        path.lineTo(s * 0.36, s * 0.76)
        path.lineTo(s * 0.64, s * 0.76)
        path.lineTo(s * 0.68, s * 0.36)
        painter.drawPath(path)
    elif kind == "bolt":
        path = QPainterPath(QPointF(s * 0.56, s * 0.2))
        path.lineTo(s * 0.32, s * 0.54)
        path.lineTo(s * 0.5, s * 0.54)
        path.lineTo(s * 0.44, s * 0.8)
        path.lineTo(s * 0.68, s * 0.44)
        path.lineTo(s * 0.5, s * 0.44)
        path.closeSubpath()
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawPath(path)
    elif kind == "refresh":
        painter.drawArc(QRectF(s * 0.26, s * 0.26, s * 0.48, s * 0.48), 40 * 16, 280 * 16)
        line(0.66, 0.24, 0.7, 0.36)
        line(0.7, 0.36, 0.58, 0.38)
    elif kind == "arrow":
        line(0.3, 0.7, 0.7, 0.3)
        line(0.46, 0.3, 0.7, 0.3)
        line(0.7, 0.3, 0.7, 0.54)
    elif kind == "pencil":
        line(0.3, 0.7, 0.66, 0.34)
        line(0.6, 0.28, 0.72, 0.4)
        line(0.26, 0.74, 0.34, 0.72)
    else:
        return False
    return True


def kind_icon(kind: str) -> QIcon:
    glyph, color = KIND_STYLE.get(kind, ("dot", "#8E8E93"))
    return symbol_icon(glyph, color)
