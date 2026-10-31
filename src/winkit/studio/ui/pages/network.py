"""Grupo "Rede": Wi-Fi, DNS e bloqueios, unidades de rede (M14)."""

from __future__ import annotations

from functools import partial

from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QWidget

from winkit.core.recipe.models import WifiNetwork
from winkit.i18n import t
from winkit.studio.ui.base import Page
from winkit.studio.ui.pages.common import empty, toggle
from winkit.ui.widgets import Card, Row, button, label, section, symbol_icon


class WifiPage(Page):
    """V2-02: redes Wi-Fi do PC atual, conectadas antes do primeiro login."""

    title_key = "studio.wifi.title"
    subtitle_key = "studio.wifi.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        self.content.addLayout(self.toolbar(button(t("studio.wifi.read"), "Primary", self._read)))
        card = Card()
        for n in r.wifi.networks:
            card.add_row(self._row(n))
        self.content.addWidget(
            section(
                t("studio.on_pendrive"),
                card if card.rows else empty(t("studio.wifi.none")),
                footer=t("studio.wifi.footer"),
            )
        )
        warn = Card()
        warn.add_row(
            Row(
                t("studio.wifi.warning_title"),
                t("studio.wifi.warning"),
                icon=symbol_icon("!", "#FF9500"),
            )
        )
        self.content.addWidget(section("", warn))

    def _row(self, n: WifiNetwork) -> Row:
        sub = t(f"studio.wifi.security.{n.security}")
        if n.security == "enterprise":
            return Row(
                n.ssid,
                sub + " · " + t("studio.wifi.enterprise"),
                icon=symbol_icon("dot", "#8E8E93"),
            )
        if not n.include_key:
            sub += " · " + t("studio.wifi.no_key")
        acc = QWidget()
        lay = QHBoxLayout(acc)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(label(t("studio.wifi.include_key"), "Caption", wrap=False))
        lay.addWidget(toggle(n.include_key, partial(self._set_key, n.id)))
        lay.addSpacing(12)
        lay.addWidget(toggle(n.selected, partial(self._set_selected, n)))
        return Row(n.ssid, sub, accessory=acc, icon=symbol_icon("dot", "#32ADE6"))

    def _set_selected(self, n: WifiNetwork, value: bool) -> None:
        n.selected = value
        self.save()

    def _set_key(self, network_id: str, value: bool) -> None:
        if not self.ctl.set_wifi_include_key(network_id, value):
            QMessageBox.information(self, t("app.name"), t("studio.wifi.read_again"))
        self.refresh()

    def _read(self) -> None:
        self.tasks.run(
            t("studio.wifi.reading"), self.ctl.collect_wifi, lambda added: self.refresh()
        )
