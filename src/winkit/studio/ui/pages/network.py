"""Grupo "Rede": Wi-Fi, DNS e bloqueios, unidades de rede (M14)."""

from __future__ import annotations

from functools import partial

from PySide6.QtWidgets import QHBoxLayout, QInputDialog, QLineEdit, QMessageBox, QWidget

from winkit.core.recipe.models import WifiNetwork
from winkit.i18n import t, tn
from winkit.studio.ui.base import Page
from winkit.studio.ui.pages.common import choice_row, combo, empty, toggle
from winkit.ui.widgets import Card, Row, button, kind_icon, label, section, symbol_icon


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


class NetworkDrivesPage(Page):
    """V2-17: unidades de rede do PC atual (ex.: ``Z:`` → ``\\\\nas\\filmes``)."""

    title_key = "studio.drives.title"
    subtitle_key = "studio.drives.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        self.content.addLayout(
            self.toolbar(
                button(t("studio.drives.read"), "Primary", self._read),
                button(t("studio.drives.add"), "Secondary", self._add),
            )
        )
        card = Card()
        for d in sorted(r.network_drives, key=lambda x: x.letter):
            card.add_row(
                choice_row(
                    f"{d.letter}:  {d.remote_path}",
                    d.label,
                    icon_kind="network_drive",
                    selected=d.selected,
                    on_select=partial(self._set_selected, d.letter),
                )
            )
        self.content.addWidget(
            section(
                t("studio.on_pendrive"),
                card if card.rows else empty(t("studio.drives.none")),
                footer=t("studio.drives.footer"),
            )
        )

    def _set_selected(self, letter: str, value: bool) -> None:
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        for d in r.network_drives:
            if d.letter == letter:
                d.selected = value
        self.save()

    def _read(self) -> None:
        def done(added: list[object]) -> None:
            self.refresh()
            QMessageBox.information(self, t("app.name"), tn("studio.drives.read_done", len(added)))

        self.tasks.run(t("studio.drives.reading"), self.ctl.collect_drives, done)

    def _add(self) -> None:
        letter, ok = QInputDialog.getText(self, t("studio.drives.add"), t("studio.drives.letter"))
        if not ok or not letter.strip():
            return
        path, ok = QInputDialog.getText(self, t("studio.drives.add"), t("studio.drives.path"))
        if not ok or not path.strip():
            return
        try:
            self.ctl.add_drive(letter.strip(), path.strip())
        except ValueError:
            QMessageBox.warning(self, t("app.name"), t("studio.drives.invalid"))
            return
        self.refresh()


class BrowsersPage(Page):
    """V2-12: extensões, página inicial e buscador pelas políticas oficiais (D-038)."""

    title_key = "studio.browsers.title"
    subtitle_key = "studio.browsers.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        self.content.addLayout(
            self.toolbar(
                button(t("studio.browsers.read"), "Primary", self._read),
                *[
                    button(b.name, "Secondary", partial(self._add, b.id))
                    for b in self.ctl.catalogs.browsers
                    if not any(c.id == b.id for c in r.browsers)
                ],
            )
        )
        searches = [("", t("studio.browsers.search_keep"))]
        searches += [(s.id, s.name) for s in self.ctl.catalogs.search_providers]
        for cfg in r.browsers:
            entry = self.ctl.catalogs.browser(cfg.id)
            if entry is None:
                continue
            card = Card()
            card.add_row(
                Row(
                    t("studio.browsers.enabled"),
                    None,
                    accessory=toggle(cfg.selected, partial(self._set, cfg, "selected")),
                    icon=kind_icon("browser"),
                )
            )
            card.add_row(
                Row(
                    t("studio.browsers.mode"),
                    t("studio.browsers.mode_hint"),
                    accessory=combo(
                        [
                            ("suggest", t("studio.browsers.suggest")),
                            ("force", t("studio.browsers.force")),
                        ],
                        cfg.mode,
                        partial(self._set, cfg, "mode"),
                    ),
                )
            )
            home = QLineEdit(cfg.homepage or "")
            home.setPlaceholderText("https://")
            home.editingFinished.connect(partial(self._homepage, cfg, home))
            card.add_row(Row(t("studio.browsers.homepage"), None, accessory=home))
            card.add_row(
                Row(
                    t("studio.browsers.search"),
                    None,
                    accessory=combo(
                        searches,
                        cfg.search or "",
                        partial(self._search, cfg),
                    ),
                )
            )
            for ext in cfg.extensions:
                card.add_row(
                    choice_row(
                        ext.name or ext.id,
                        ext.id,
                        icon_kind="browser",
                        selected=ext.selected,
                        on_select=partial(self._set, ext, "selected"),
                    )
                )
            for store_id, name, _slug in self.ctl.suggested_extensions(cfg.id):
                if not any(e.id == store_id for e in cfg.extensions):
                    card.add_row(
                        Row(
                            name,
                            t("studio.browsers.suggested"),
                            accessory=button(
                                t("studio.browsers.add"),
                                "Secondary",
                                partial(self._add_ext, cfg.id, store_id),
                            ),
                        )
                    )
            self.content.addWidget(section(entry.name, card))
        warn = Card()
        warn.add_row(
            Row(
                t("studio.browsers.warning_title"),
                t("studio.browsers.warning"),
                icon=symbol_icon("!", "#FF9500"),
            )
        )
        self.content.addWidget(section("", warn))

    def _set(self, obj: object, name: str, value: object) -> None:
        setattr(obj, name, value)
        self.save()

    def _search(self, cfg: object, value: str) -> None:
        self._set(cfg, "search", value or None)

    def _homepage(self, cfg: object, edit: QLineEdit) -> None:
        text = edit.text().strip() or None
        try:
            self._set(cfg, "homepage", text)
        except ValueError:
            QMessageBox.warning(self, t("app.name"), t("studio.browsers.bad_url"))

    def _add(self, browser_id: str) -> None:
        self.ctl.add_browser(browser_id)
        self.refresh()

    def _add_ext(self, browser_id: str, store_id: str) -> None:
        self.ctl.add_browser_extension(browser_id, store_id)
        self.refresh()

    def _read(self) -> None:
        self.tasks.run(
            t("studio.browsers.reading"), self.ctl.collect_browsers, lambda _: self.refresh()
        )
