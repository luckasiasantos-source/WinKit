"""Peças comuns às páginas do Studio. Todo texto vem do ``i18n`` (R-03, R-55)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QWidget

from winkit.i18n import t
from winkit.ui.widgets import Card, Row, ToggleSwitch, ask_pill, kind_icon

#: Fusos mais comuns (id do Windows → nome próprio, igual em todos os idiomas).
TIME_ZONES: list[tuple[str, str]] = [
    ("E. South America Standard Time", "(UTC−03:00) Brasília"),
    ("Argentina Standard Time", "(UTC−03:00) Buenos Aires"),
    ("Pacific SA Standard Time", "(UTC−04:00) Santiago"),
    ("SA Western Standard Time", "(UTC−04:00) Manaus, La Paz"),
    ("SA Pacific Standard Time", "(UTC−05:00) Bogotá, Lima, Rio Branco"),
    ("Central Standard Time (Mexico)", "(UTC−06:00) Ciudad de México"),
    ("Eastern Standard Time", "(UTC−05:00) New York"),
    ("Central Standard Time", "(UTC−06:00) Chicago"),
    ("Pacific Standard Time", "(UTC−08:00) Los Angeles"),
    ("UTC-02", "(UTC−02:00) Fernando de Noronha"),
    ("GMT Standard Time", "(UTC+00:00) Lisboa, London"),
    ("Romance Standard Time", "(UTC+01:00) Madrid, Paris"),
]
#: Teclados (formato do autounattend → chave de texto).
KEYBOARDS: list[tuple[str, str]] = [
    ("0416:00010416", "studio.kb.pt_br_abnt2"),
    ("0816:00000816", "studio.kb.pt_pt"),
    ("0409:00000409", "studio.kb.en_us"),
    ("0409:00020409", "studio.kb.en_us_intl"),
    ("0809:00000809", "studio.kb.en_gb"),
    ("040A:0000040A", "studio.kb.es_es"),
    ("080A:0000080A", "studio.kb.es_latam"),
]


def keyboards() -> list[tuple[str, str]]:
    return [(code, t(key)) for code, key in KEYBOARDS]


def combo(
    options: list[tuple[str, str]], value: str, on_change: Callable[[str], None]
) -> QComboBox:
    c = QComboBox()
    for key, text in options:
        c.addItem(text, key)
    idx = c.findData(value)
    if idx < 0:
        c.addItem(value, value)
        idx = c.count() - 1
    c.setCurrentIndex(idx)
    c.currentIndexChanged.connect(lambda _: on_change(str(c.currentData())))
    c.setMinimumWidth(220)
    return c


def toggle(value: bool, on_change: Callable[[bool], None]) -> ToggleSwitch:
    sw = ToggleSwitch(value)
    sw.toggledByUser.connect(on_change)
    return sw


def choice_row(
    title: str,
    subtitle: str | None,
    *,
    icon_kind: str,
    selected: bool,
    on_select: Callable[[bool], None],
    ask: bool | None = None,
    on_ask: Callable[[bool], None] | None = None,
    enabled: bool = True,
) -> Row:
    acc = QWidget()
    lay = QHBoxLayout(acc)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)
    if ask is not None and on_ask is not None:
        pill = ask_pill(ask)
        pill.toggled.connect(on_ask)
        pill.setVisible(selected)
        lay.addWidget(pill)

        def both(value: bool) -> None:
            on_select(value)
            pill.setVisible(value)

        sw = toggle(selected, both)
    else:
        sw = toggle(selected, on_select)
    sw.setEnabled(enabled)
    lay.addWidget(sw)
    return Row(title, subtitle, accessory=acc, icon=kind_icon(icon_kind))


def empty(text: str) -> Card:
    c = Card()
    c.add_row(Row(text))
    return c
