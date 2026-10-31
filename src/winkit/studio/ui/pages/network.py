"""Grupo "Rede": Wi-Fi, DNS e bloqueios, unidades de rede (M14)."""

from __future__ import annotations

from functools import partial

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QMessageBox, QWidget

from winkit.core.recipe.models import WifiNetwork
from winkit.i18n import t, tn
from winkit.studio.ui.base import Page
from winkit.studio.ui.pages.common import choice_row, combo, empty, toggle
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


class DnsPage(Page):
    """V2-16: DNS mais rápido e privado, com DoH, e bloqueio pelo ``hosts``."""

    title_key = "studio.dns.title"
    subtitle_key = "studio.dns.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        d = r.dns
        providers = self.ctl.catalogs.dns_providers
        options = [("unchanged", t("studio.dns.unchanged"))]
        options += [(p.id, p.name) for p in providers]
        options.append(("custom", t("studio.dns.custom")))
        card = Card()
        card.add_row(
            Row(
                t("studio.dns.server"),
                None,
                accessory=combo(options, d.provider, self._set_provider),
                icon=symbol_icon("dot", "#32ADE6"),
            )
        )
        chosen = self.ctl.catalogs.dns_provider(d.provider)
        if chosen is not None and chosen.needs_id:
            pid = QLineEdit(d.provider_id or "")
            pid.setPlaceholderText("abc123")
            pid.editingFinished.connect(
                lambda: self._set("provider_id", pid.text().strip() or None)
            )
            card.add_row(
                Row(t("studio.dns.provider_id"), t("studio.dns.provider_id_hint"), accessory=pid)
            )
        if d.provider == "custom":
            servers = QLineEdit(", ".join(d.custom_servers))
            servers.setPlaceholderText("1.1.1.1, 2606:4700:4700::1111")
            servers.editingFinished.connect(
                lambda: self._set(
                    "custom_servers", [s.strip() for s in servers.text().split(",") if s.strip()]
                )
            )
            card.add_row(Row(t("studio.dns.custom_servers"), None, accessory=servers))
            doh = QLineEdit(d.custom_doh_template or "")
            doh.setPlaceholderText("https://…/dns-query")
            doh.editingFinished.connect(
                lambda: self._set("custom_doh_template", doh.text().strip() or None)
            )
            card.add_row(Row(t("studio.dns.custom_doh"), None, accessory=doh))
        if d.provider != "unchanged":
            card.add_row(
                Row(
                    t("studio.dns.require_doh"),
                    t("studio.dns.require_doh_hint"),
                    accessory=toggle(d.require_doh, lambda v: self._set("require_doh", v)),
                )
            )
        self.content.addWidget(section("", card, footer=t("studio.dns.footer")))

        lists = Card()
        for b in self.ctl.catalogs.hosts_blocklists:
            lists.add_row(
                choice_row(
                    b.name,
                    b.description + " · " + tn("studio.dns.domains", len(b.domains)),
                    icon_kind="hosts",
                    selected=b.id in d.hosts_blocklists,
                    on_select=partial(self._toggle_list, b.id),
                )
            )
        self.content.addWidget(section(t("studio.dns.blocklists"), lists))
        warn = Card()
        warn.add_row(
            Row(
                t("studio.dns.warning_title"),
                t("studio.dns.warning"),
                accessory=button(t("studio.dns.remove_here"), "Secondary", self._remove_here),
                icon=symbol_icon("!", "#FF9500"),
            )
        )
        self.content.addWidget(section("", warn))

    def _set(self, name: str, value: object) -> None:
        if self.ctl.recipe is not None:
            setattr(self.ctl.recipe.dns, name, value)
            self.save()

    def _set_provider(self, value: str) -> None:
        self._set("provider", value)
        self.refresh()

    def _toggle_list(self, list_id: str, value: bool) -> None:
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        chosen = [x for x in r.dns.hosts_blocklists if x != list_id]
        if value:
            chosen.append(list_id)
        self._set("hosts_blocklists", chosen)

    def _remove_here(self) -> None:
        try:
            removed = self.ctl.remove_hosts_block()
        except OSError as exc:
            QMessageBox.warning(self, t("app.name"), t("studio.dns.remove_failed", detail=str(exc)))
            return
        key = "studio.dns.removed" if removed else "studio.dns.nothing_to_remove"
        QMessageBox.information(self, t("app.name"), t(key))
