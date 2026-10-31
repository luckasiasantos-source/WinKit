"""Grupo "O que levar": aplicativos, configurações dos apps e drivers."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog, QInputDialog, QLineEdit, QMessageBox

from winkit.core.recipe.models import AppItem
from winkit.i18n import t, tn
from winkit.i18n.format import format_size
from winkit.studio.ui.base import Page
from winkit.studio.ui.pages.common import choice_row, empty, toggle
from winkit.ui.widgets import Card, Row, button, kind_icon, section, symbol_icon


def app_subtitle(a: AppItem) -> str:
    where = t("studio.apps.per_user") if a.scope == "user" else t("studio.apps.for_all")
    if a.source == "winget_online":
        src = t("studio.apps.src_winget", id=a.winget_id or "")
    elif a.source == "portable":
        src = t("studio.apps.src_portable")
    elif a.installer and a.installer.path:
        src = t("studio.apps.src_offline", type=a.installer.type)
    else:
        src = t("studio.apps.src_missing")
    return f"{src} · {where}"


class AppsPage(Page):
    title_key = "studio.apps.title"
    subtitle_key = "studio.apps.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        self.search = QLineEdit()
        self.search.setPlaceholderText(t("studio.search"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        self.content.addLayout(
            self.toolbar(
                button(t("studio.apps.read"), None, self._collect),
                button(t("studio.apps.download"), "Primary", self._download),
                button(t("studio.apps.add_installer"), None, self._add_installer),
                button(t("studio.apps.add_portable"), None, self._add_portable),
            )
        )
        self.content.addWidget(self.search)
        self._rows: list[tuple[Row, AppItem]] = []
        chosen, others = Card(), Card()
        for a in sorted(r.apps, key=lambda x: (x.order, x.name.casefold())):
            row = choice_row(
                a.name,
                app_subtitle(a),
                icon_kind="app",
                selected=a.selected,
                on_select=partial(self._set_selected, a),
                ask=a.decide_at_runtime,
                on_ask=partial(self._set_ask, a),
            )
            (chosen if a.selected else others).add_row(row)
            self._rows.append((row, a))
        n = len(r.selected_apps())
        self.content.addWidget(
            section(
                t("studio.apps.section_selected", n=n),
                chosen if chosen.rows else empty(t("studio.apps.none_selected")),
            )
        )
        self.content.addWidget(
            section(
                t("studio.apps.section_others"),
                others if others.rows else empty(t("studio.apps.read_hint")),
            )
        )

    def _filter(self, text: str) -> None:
        needle = text.casefold()
        for row, a in self._rows:
            row.setVisible(not needle or needle in a.name.casefold() or needle in a.id)

    def _set_selected(self, a: AppItem, value: bool) -> None:
        a.selected = value
        self.save()

    def _set_ask(self, a: AppItem, value: bool) -> None:
        a.decide_at_runtime = value
        self.save()

    def _collect(self) -> None:
        self.tasks.run(
            t("studio.apps.reading"), self.ctl.collect_apps, lambda added: self.refresh()
        )

    def _download(self) -> None:
        def done(results: list[Any]) -> None:
            bad = [f"• {r.app_id}: {r.message}" for r in results if not r.ok]
            ok = sum(1 for r in results if r.ok)
            text = tn("studio.apps.download_done", ok)
            if bad:
                text += "\n\n" + t("studio.apps.not_downloaded") + "\n" + "\n".join(bad)
            QMessageBox.information(self, t("app.name"), text)
            self.refresh()

        self.tasks.run(t("studio.apps.downloading"), self.ctl.download_selected, done)

    def _add_installer(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("studio.apps.installer_dialog"),
            "",
            t("studio.apps.installer_filter") + " (*.exe *.msi *.msix *.msixbundle)",
        )
        if not path:
            return
        name, ok = QInputDialog.getText(
            self, t("app.name"), t("studio.apps.name_prompt"), text=Path(path).stem
        )
        if not ok or not name.strip():
            return
        item = self.ctl.add_installer(Path(path), name.strip(), None, "machine")
        if item.installer is not None and item.installer.type == "unknown":
            args, ok = QInputDialog.getText(self, t("app.name"), t("studio.apps.args_prompt"))
            if ok and args.strip():
                self.ctl.add_installer(Path(path), name.strip(), args.strip(), "machine")
        self.refresh()

    def _add_portable(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, t("studio.apps.portable_dialog"))
        if not folder:
            return
        exe, _ = QFileDialog.getOpenFileName(self, t("studio.apps.exe_dialog"), folder, "*.exe")
        if not exe:
            return
        name, ok = QInputDialog.getText(
            self, t("app.name"), t("studio.apps.name_prompt"), text=Path(exe).stem
        )
        if ok and name.strip():
            rel = str(Path(exe).relative_to(folder))
            self.ctl.add_portable(str(Path(folder)).replace("/", "\\"), name.strip(), rel)
            self.refresh()


class DriversPage(Page):
    title_key = "studio.drivers.title"
    subtitle_key = "studio.drivers.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        self.content.addLayout(
            self.toolbar(button(t("studio.drivers.read"), "Primary", self._read))
        )
        card = Card()
        for d in sorted(r.drivers, key=lambda x: (x.priority, x.class_name)):
            card.add_row(
                choice_row(
                    f"{d.class_name} — {d.provider}",
                    f"{d.version} · {d.path}",
                    icon_kind="driver",
                    selected=d.selected,
                    on_select=partial(self._set_driver, d),
                )
            )
        self.content.addWidget(
            section(
                t("studio.on_pendrive"),
                card if card.rows else empty(t("studio.drivers.none")),
            )
        )
        fix = Card()
        fix.add_row(
            Row(
                t("studio.drivers.fix_missing"),
                t("studio.drivers.fix_missing_hint"),
                accessory=toggle(r.updates.fix_missing_drivers, self._set_fix),
                icon=kind_icon("driver_report"),
            )
        )
        self.content.addWidget(section("", fix))

    def _set_fix(self, value: bool) -> None:
        if self.ctl.recipe is not None:
            self.ctl.recipe.updates.fix_missing_drivers = value
            self.save()

    def _set_driver(self, d: Any, value: bool) -> None:
        d.selected = value
        self.save()

    def _choose(self, cand: Any, value: bool) -> None:
        self._chosen[id(cand)] = value

    def _read(self) -> None:
        def done(cands: list[Any]) -> None:
            self._candidates = cands
            self._chosen = {id(c): c.recommended for c in cands}
            card = Card()
            for c in cands:
                card.add_row(
                    choice_row(
                        c.label,
                        f"{c.driver.provider} · {c.driver.version} · {c.driver.published_name}",
                        icon_kind="driver",
                        selected=c.recommended,
                        on_select=partial(self._choose, c),
                    )
                )
            self.content.addWidget(
                section(t("studio.drivers.on_pc"), card, footer=t("studio.drivers.footer"))
            )
            self.content.addLayout(
                self.toolbar(button(t("studio.drivers.export"), "Primary", self._export))
            )

        self.tasks.run(t("studio.drivers.reading"), self.ctl.driver_candidates, done)

    def _export(self) -> None:
        chosen = [c for c in self._candidates if self._chosen.get(id(c))]
        self.tasks.run(
            t("studio.drivers.exporting"),
            lambda: self.ctl.export_drivers(chosen),
            lambda n: self.refresh(),
        )


class BackupsPage(Page):
    title_key = "studio.backups.title"
    subtitle_key = "studio.backups.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        self.content.addLayout(
            self.toolbar(
                button(t("studio.backups.suggest"), None, self._suggest),
                button(t("studio.backups.add_folder"), None, lambda: self._add(folder=True)),
                button(t("studio.backups.add_file"), None, lambda: self._add(folder=False)),
                button(t("studio.backups.capture"), "Primary", self._capture),
            )
        )
        card = Card()
        for b in r.backups:
            status = (
                t("studio.backups.captured")
                if self.ctl.is_captured(b)
                else t("studio.backups.not_captured")
            )
            conflict = t(f"studio.conflict.{b.on_conflict}")
            sub = f"{b.template} · {conflict} · {status}"
            if b.warnings:
                sub += f"\n⚠ {b.warnings[0]}"
            row = choice_row(
                b.name,
                sub,
                icon_kind="backup",
                selected=b.selected,
                on_select=partial(self._set_flag, b, "selected"),
                ask=b.decide_at_runtime,
                on_ask=partial(self._set_flag, b, "decide_at_runtime"),
            )
            card.add_row(row)
        self.content.addWidget(
            section(
                t("studio.on_pendrive"),
                card if card.rows else empty(t("studio.backups.none")),
                footer=t("studio.backups.footer"),
            )
        )

    def _set_flag(self, item: Any, attr: str, value: bool) -> None:
        setattr(item, attr, value)
        self.save()

    def _add_suggestion(self, s: Any) -> None:
        self.ctl.add_suggestion(s)
        self.refresh()

    def _suggest(self) -> None:
        sugs = self.ctl.backup_suggestions()
        card = Card()
        for s in sugs:
            size = format_size(s.size) if s.exists else t("studio.backups.missing_here")
            add = button(t("studio.add"), None, partial(self._add_suggestion, s))
            add.setEnabled(s.exists)
            sub = f"{s.template} · {size}" + (f"\n⚠ {s.warning}" if s.warning else "")
            title = (
                t("studio.backups.recommended", name=s.app_name) if s.recommended else s.app_name
            )
            card.add_row(Row(title, sub, accessory=add, icon=kind_icon("backup")))
        self.content.addWidget(
            section(
                t("studio.backups.section_suggestions"),
                card if card.rows else empty(t("studio.backups.suggest_hint")),
            )
        )

    def _add(self, *, folder: bool) -> None:
        if folder:
            path = QFileDialog.getExistingDirectory(self, t("studio.backups.folder_dialog"))
        else:
            path, _ = QFileDialog.getOpenFileName(self, t("studio.backups.file_dialog"))
        if not path:
            return
        literal = str(Path(path)).replace("/", "\\")
        _, warning = self.ctl.add_backup(literal, Path(path).name, "merge", False)
        if warning:
            QMessageBox.information(self, t("app.name"), warning)
        self.refresh()

    def _capture(self) -> None:
        def done(rep: Any) -> None:
            lines = [f"{'✓' if i.ok else '✗'} {i.backup_id}: {i.message}" for i in rep.items]
            text = "\n".join([*rep.notes, *lines]) or t("studio.backups.nothing")
            QMessageBox.information(self, t("app.name"), text)
            self.refresh()

        self.tasks.run(t("studio.backups.capturing"), self.ctl.capture, done)


class FontsPage(Page):
    """V2-07: fontes instaladas neste PC; o arquivo só vai para o pendrive ao marcar."""

    title_key = "studio.fonts.title"
    subtitle_key = "studio.fonts.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        self.content.addLayout(self.toolbar(button(t("studio.fonts.read"), "Primary", self._read)))
        card = Card()
        for f in sorted(r.fonts, key=lambda x: x.family.casefold()):
            origin = t(f"studio.fonts.origin_{f.origin}")
            card.add_row(
                choice_row(
                    f.full_name,
                    f"{f.family} · {format_size(f.size)} · {origin}",
                    icon_kind="font",
                    selected=f.selected,
                    on_select=partial(self._select, f.id),
                )
            )
        self.content.addWidget(
            section(
                t("studio.fonts.section"),
                card if card.rows else empty(t("studio.fonts.none")),
                footer=t("studio.fonts.license"),
            )
        )

    def _select(self, font_id: str, value: bool) -> None:
        try:
            self.ctl.select_font(font_id, value)
        except OSError as exc:
            QMessageBox.warning(self, t("app.name"), t("studio.fonts.copy_failed", detail=str(exc)))
            self.refresh()

    def _read(self) -> None:
        def done(found: tuple[list[Any], list[str]]) -> None:
            self.refresh()
            QMessageBox.information(
                self, t("app.name"), tn("studio.fonts.read_done", len(found[0]))
            )

        self.tasks.run(t("studio.fonts.reading"), self.ctl.collect_fonts, done)


class DefaultAppsPage(Page):
    """V2-05: navegador, PDF, vídeo… padrão iguais aos do PC antigo."""

    title_key = "studio.defaults.title"
    subtitle_key = "studio.defaults.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        self.content.addLayout(
            self.toolbar(button(t("studio.defaults.read"), "Primary", self._read))
        )
        card = Card()
        if r.default_apps.associations_file:
            for group, app in self.ctl.default_app_rows():
                card.add_row(
                    choice_row(
                        group.name,
                        app or t("studio.defaults.no_app"),
                        icon_kind="default_apps",
                        selected=group.id in r.default_apps.groups,
                        enabled=app is not None,
                        on_select=partial(self._set, group.id),
                    )
                )
        self.content.addWidget(section("", card if card.rows else empty(t("studio.defaults.none"))))
        warn = Card()
        warn.add_row(
            Row(
                t("studio.defaults.warning_title"),
                t("studio.defaults.warning"),
                icon=symbol_icon("!", "#FF9500"),
            )
        )
        self.content.addWidget(section("", warn))

    def _set(self, group_id: str, value: bool) -> None:
        self.ctl.set_default_app_group(group_id, value)

    def _read(self) -> None:
        self.tasks.run(
            t("studio.defaults.reading"), self.ctl.collect_default_apps, lambda _: self.refresh()
        )
