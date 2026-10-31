"""Grupo "Sistema": apps pré-instalados, ajustes, energia e atualizações."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QMessageBox, QSpinBox, QWidget

from winkit.core.maintenance import DAYS
from winkit.core.recipe.models import Recipe, TweakSelection
from winkit.i18n import render, t, tn
from winkit.studio.ui.base import Page
from winkit.studio.ui.pages.common import choice_row, combo, empty, toggle
from winkit.ui.widgets import (
    Card,
    Row,
    SegmentedControl,
    button,
    kind_icon,
    label,
    section,
    symbol_icon,
)

DAY_IDS = tuple(DAYS)


class BloatPage(Page):
    title_key = "studio.bloat.title"
    subtitle_key = "studio.bloat.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        opts = Card()
        opts.add_row(
            Row(
                t("studio.bloat.block_reinstall"),
                None,
                accessory=toggle(
                    r.bloatware.block_reinstall, lambda v: self._opt("block_reinstall", v)
                ),
                icon=symbol_icon("minus", "#FF3B30"),
            )
        )
        opts.add_row(
            Row(
                t("studio.bloat.consumer_content"),
                None,
                accessory=toggle(
                    r.bloatware.disable_consumer_content,
                    lambda v: self._opt("disable_consumer_content", v),
                ),
                icon=symbol_icon("minus", "#FF9500"),
            )
        )
        self.content.addWidget(section("", opts))
        chosen = set(r.bloatware.remove)
        for risk, footer in (
            ("safe", None),
            ("caution", t("studio.bloat.caution_footer")),
            ("blocked", None),
        ):
            card = Card()
            for b in self.ctl.catalogs.bloatware:
                if b.risk != risk or not any(o in r.windows.target_os for o in b.windows.os):
                    continue
                card.add_row(
                    choice_row(
                        b.name,
                        b.side_effect or b.reason,
                        icon_kind="bloat",
                        selected=b.id in chosen,
                        enabled=risk != "blocked",
                        on_select=partial(self._toggle, b.id),
                    )
                )
            self.content.addWidget(section(t(f"studio.bloat.risk_{risk}"), card, footer=footer))

    def _opt(self, name: str, value: bool) -> None:
        assert self.ctl.recipe is not None  # noqa: S101
        setattr(self.ctl.recipe.bloatware, name, value)
        self.save()

    def _toggle(self, pkg: str, value: bool) -> None:
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        items = [x for x in r.bloatware.remove if x != pkg]
        if value:
            items.append(pkg)
        r.bloatware.remove = items
        self.save()


class TweaksPage(Page):
    title_key = "studio.tweaks.title"
    subtitle_key = "studio.tweaks.subtitle"
    HIDDEN: frozenset[str] = frozenset(
        {
            "system.prevent_device_encryption",
            "system.wu_no_driver_replacement",
            "system.consumer_content",
            "maintenance.storage_sense",
        }
    )
    CATEGORIES: tuple[str, ...] = ("privacy", "visual", "gaming", "system")

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        presets = Card()
        for p in self.ctl.catalogs.presets:
            applied = p.id in r.presets_applied
            presets.add_row(
                Row(
                    p.name + (" ✓" if applied else ""),
                    p.description,
                    accessory=button(
                        t("studio.presets.apply"), "Secondary", partial(self._preset, p.id)
                    ),
                    icon=symbol_icon("sliders", "#AF52DE"),
                )
            )
        self.content.addWidget(
            section(t("studio.presets.title"), presets, footer=t("studio.presets.footer"))
        )
        selected = {sel.id: sel for sel in r.tweaks}
        for cat in self.CATEGORIES:
            card = Card()
            for tw in self.ctl.catalogs.tweaks:
                if tw.category != cat or tw.id in self.HIDDEN:
                    continue
                sel = selected.get(tw.id)
                card.add_row(
                    choice_row(
                        tw.title + (" ⚠" if tw.risk == "caution" else ""),
                        tw.description,
                        icon_kind="tweak",
                        selected=bool(sel and sel.enabled),
                        on_select=partial(self._set_enabled, tw.id),
                        ask=bool(sel and sel.decide_at_runtime),
                        on_ask=partial(self._set_tweak_ask, tw.id),
                    )
                )
            if card.rows:
                self.content.addWidget(section(t(f"studio.tweaks.cat_{cat}"), card))

    def _preset(self, preset_id: str) -> None:
        preview = self.ctl.preset_preview(preset_id)
        lines = [render(m) for m in preview.changes] or [t("studio.presets.nothing")]
        lines += ["⚠ " + render(m) for m in preview.warnings]
        answer = QMessageBox.question(
            self,
            t("studio.presets.confirm_title"),
            t("studio.presets.confirm") + "\n\n• " + "\n• ".join(lines),
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.ctl.apply_preset(preset_id)
            self.refresh()

    def _set_enabled(self, tweak_id: str, value: bool) -> None:
        self._set(tweak_id, enabled=value)

    def _set_tweak_ask(self, tweak_id: str, value: bool) -> None:
        self._set(tweak_id, decide_at_runtime=value)

    def _set(self, tweak_id: str, **changes: bool) -> None:
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        sel = next((x for x in r.tweaks if x.id == tweak_id), None)
        if sel is None:
            sel = TweakSelection(id=tweak_id, enabled=False)
            r.tweaks.append(sel)
        for k, v in changes.items():
            setattr(sel, k, v)
        self.save()


class EnergyPage(Page):
    title_key = "studio.energy.title"
    subtitle_key = "studio.energy.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        tri = [
            ("keep", t("studio.energy.keep")),
            ("on", t("studio.energy.on")),
            ("off", t("studio.energy.off")),
        ]

        def tri_value(v: bool | None) -> str:
            return "keep" if v is None else ("on" if v else "off")

        def from_tri(v: str) -> bool | None:
            return None if v == "keep" else v == "on"

        pw = Card()
        pw.add_row(
            Row(
                t("studio.energy.plan"),
                None,
                accessory=combo(
                    [
                        ("unchanged", t("studio.energy.keep")),
                        ("balanced", t("studio.energy.balanced")),
                        ("high_performance", t("studio.energy.high")),
                        ("ultimate", t("studio.energy.ultimate")),
                    ],
                    r.power.scheme,
                    lambda v: self._set(lambda r: setattr(r.power, "scheme", v)),
                ),
                icon=symbol_icon("bolt", "#FF9500"),
            )
        )
        hib = SegmentedControl(tri, tri_value(r.power.hibernate))
        hib.changed.connect(
            lambda v: self._set(lambda r: setattr(r.power, "hibernate", from_tri(v)))
        )
        pw.add_row(
            Row(
                t("studio.energy.hibernate"),
                None,
                accessory=hib,
                icon=symbol_icon("bolt", "#FF9500"),
            )
        )
        fs = SegmentedControl(tri, tri_value(r.power.fast_startup))
        fs.changed.connect(
            lambda v: self._set(lambda r: setattr(r.power, "fast_startup", from_tri(v)))
        )
        pw.add_row(
            Row(
                t("studio.energy.fast_startup"),
                None,
                accessory=fs,
                icon=symbol_icon("bolt", "#FF9500"),
            )
        )
        self.content.addWidget(section(t("studio.energy.section_power"), pw))

        up = Card()
        u = r.updates
        for attr, has_sub in (
            ("windows_update_after_install", True),
            ("during_setup", True),
            ("include_drivers_from_windows_update", False),
            ("block_wu_driver_replacement", False),
        ):
            up.add_row(
                Row(
                    t(f"studio.updates.{attr}"),
                    t(f"studio.updates.{attr}_hint") if has_sub else None,
                    accessory=toggle(getattr(u, attr), partial(self._set_update, attr)),
                    icon=kind_icon("windows_update"),
                )
            )
        self.content.addWidget(section(t("studio.energy.section_updates"), up))

        rp = Card()
        rp.add_row(
            Row(
                t("studio.restore.enabled"),
                t("studio.restore.enabled_hint"),
                accessory=toggle(
                    r.restore_point.enabled,
                    lambda v: self._set(lambda r: setattr(r.restore_point, "enabled", v)),
                ),
                icon=kind_icon("restore_point"),
            )
        )
        spin = QSpinBox()
        spin.setRange(1, 50)
        spin.setSuffix(" %")
        spin.setValue(r.restore_point.max_disk_percent)
        spin.valueChanged.connect(
            lambda v: self._set(lambda r: setattr(r.restore_point, "max_disk_percent", int(v)))
        )
        rp.add_row(Row(t("studio.restore.space"), t("studio.restore.space_hint"), accessory=spin))
        self.content.addWidget(section(t("studio.restore.section"), rp))

    def _set(self, fn: Callable[[Recipe], None]) -> None:
        if self.ctl.recipe is not None:
            fn(self.ctl.recipe)
            self.save()

    def _set_update(self, attr: str, value: bool) -> None:
        if self.ctl.recipe is not None:
            setattr(self.ctl.recipe.updates, attr, value)
            self.save()


class FeaturesPage(Page):
    """V2-08: recursos do Windows ligados já na instalação (nunca desliga nada)."""

    title_key = "studio.features.title"
    subtitle_key = "studio.features.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        self.content.addLayout(
            self.toolbar(button(t("studio.features.read"), "Secondary", self._read))
        )
        chosen = set(r.windows.optional_features)
        card = Card()
        for f in self.ctl.catalogs.features:
            if not any(o in r.windows.target_os for o in f.windows.os):
                continue
            allowed = f.windows.allows_edition(r.windows.edition)
            badges = []
            if f.needs_network:
                key = "studio.features.offline" if f.offline_source else "studio.features.network"
                badges.append(t(key))
            if f.restart:
                badges.append(t("studio.features.restart"))
            if not allowed:
                badges.append(t("studio.features.needs_pro"))
            detail = f.description + ("\n" + " · ".join(badges) if badges else "")
            card.add_row(
                choice_row(
                    f.name,
                    detail,
                    icon_kind="feature",
                    selected=allowed and f.id in chosen,
                    enabled=allowed,
                    on_select=partial(self.ctl.set_feature, f.id),
                )
            )
        self.content.addWidget(section("", card, footer=t("studio.features.footer")))

    def _read(self) -> None:
        def done(added: list[str]) -> None:
            self.refresh()
            QMessageBox.information(
                self, t("app.name"), tn("studio.features.read_done", len(added))
            )

        self.tasks.run(t("studio.features.reading"), self.ctl.read_features, done)


class MaintenancePage(Page):
    """V2-18: atualizar apps, Sensor de Armazenamento e otimização do disco."""

    title_key = "studio.maintenance.title"
    subtitle_key = "studio.maintenance.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        m = r.maintenance
        card = Card()
        card.add_row(
            Row(
                t("studio.maintenance.winget"),
                t("studio.maintenance.winget_hint"),
                accessory=combo(
                    [
                        ("off", t("studio.maintenance.off")),
                        ("weekly", t("studio.maintenance.weekly")),
                        ("monthly", t("studio.maintenance.monthly")),
                    ],
                    m.winget_upgrade,
                    lambda v: self._set("winget_upgrade", v, refresh=True),
                ),
                icon=kind_icon("maintenance"),
            )
        )
        if m.winget_upgrade != "off":
            days = [(d, t(f"studio.maintenance.day.{d}")) for d in DAY_IDS]
            card.add_row(
                Row(
                    t("studio.maintenance.day"),
                    None,
                    accessory=combo(days, m.winget_day, lambda v: self._set("winget_day", v)),
                )
            )
            hours = [(f"{h:02d}:00", f"{h:02d}:00") for h in range(24)]
            card.add_row(
                Row(
                    t("studio.maintenance.time"),
                    None,
                    accessory=combo(hours, m.winget_time, lambda v: self._set("winget_time", v)),
                )
            )
        card.add_row(
            Row(
                t("studio.maintenance.storage_sense"),
                t("studio.maintenance.storage_sense_hint"),
                accessory=toggle(m.storage_sense, lambda v: self._set("storage_sense", v)),
                icon=symbol_icon("trash", "#34C759"),
            )
        )
        card.add_row(
            Row(
                t("studio.maintenance.defrag"),
                t("studio.maintenance.defrag_hint"),
                accessory=toggle(
                    m.ensure_defrag_schedule, lambda v: self._set("ensure_defrag_schedule", v)
                ),
                icon=symbol_icon("bolt", "#34C759"),
            )
        )
        self.content.addWidget(section("", card, footer=t("studio.maintenance.footer")))

    def _set(self, name: str, value: object, *, refresh: bool = False) -> None:
        if self.ctl.recipe is not None:
            setattr(self.ctl.recipe.maintenance, name, value)
            self.save()
            if refresh:
                self.refresh()


class EnvPage(Page):
    """V2-22: variáveis de ambiente e pastas do PATH (nunca sobrescreve sem você pedir)."""

    title_key = "studio.env.title"
    subtitle_key = "studio.env.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        self.content.addLayout(self.toolbar(button(t("studio.env.read"), "Primary", self._read)))
        env = r.environment
        for scope in ("user", "machine"):
            card = Card()
            for v in env.variables:
                if v.scope != scope:
                    continue
                edit = QLineEdit(v.value)
                edit.setMinimumWidth(260)
                edit.editingFinished.connect(partial(self._set_value, v, edit))
                acc = QWidget()
                lay = QHBoxLayout(acc)
                lay.setContentsMargins(0, 0, 0, 0)
                lay.setSpacing(8)
                lay.addWidget(edit)
                lay.addWidget(label(t("studio.env.replace"), "Caption", wrap=False))
                lay.addWidget(toggle(v.on_conflict == "replace", partial(self._set_replace, v)))
                lay.addWidget(toggle(v.selected, partial(self._set_selected, v)))
                card.add_row(Row(v.name, None, accessory=acc, icon=kind_icon("env")))
            for p in env.path_entries:
                if p.scope != scope:
                    continue
                card.add_row(
                    choice_row(
                        p.value,
                        t("studio.env.path_entry"),
                        icon_kind="env",
                        selected=p.selected,
                        on_select=partial(self._set_selected, p),
                    )
                )
            self.content.addWidget(
                section(
                    t(f"studio.env.scope_{scope}"),
                    card if card.rows else empty(t("studio.env.none")),
                )
            )
        foot = Card()
        foot.add_row(Row(t("studio.env.rules_title"), t("studio.env.rules")))
        self.content.addWidget(section("", foot))

    def _set_value(self, v: Any, edit: QLineEdit) -> None:
        if edit.text() != v.value:
            v.value = edit.text()
            self.save()

    def _set_replace(self, v: Any, value: bool) -> None:
        v.on_conflict = "replace" if value else "skip"
        self.save()

    def _set_selected(self, v: Any, value: bool) -> None:
        v.selected = value
        self.save()

    def _read(self) -> None:
        def done(found: tuple[list[Any], list[Any]]) -> None:
            self.refresh()
            n = len(found[0]) + len(found[1])
            QMessageBox.information(self, t("app.name"), tn("studio.env.read_done", n))

        self.tasks.run(t("studio.env.reading"), self.ctl.collect_env, done)


class UserFoldersPage(Page):
    """V2-14: Documentos, Downloads… num outro disco, para a próxima formatação não apagar nada."""

    title_key = "studio.folders.title"
    subtitle_key = "studio.folders.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        uf = r.user_folders
        self.content.addLayout(
            self.toolbar(
                button(t("studio.folders.read"), "Secondary", self._read),
                button(t("studio.folders.copy_now"), "Secondary", self._copy_now),
            )
        )
        volumes = self.ctl.data_volumes()
        card = Card()
        card.add_row(
            Row(
                t("studio.folders.enabled"),
                None,
                accessory=toggle(uf.enabled, self._enabled),
                icon=kind_icon("user_folders"),
            )
        )
        options = [(v.serial, self.ctl.volume_label(v)) for v in volumes]
        current = uf.volume.serial if uf.volume else ""
        if not options:
            card.add_row(Row(t("studio.folders.no_volumes"), None))
        else:
            card.add_row(
                Row(
                    t("studio.folders.volume"),
                    None,
                    accessory=combo(options, current or options[0][0], self._volume),
                )
            )
        base = QLineEdit(self.ctl.user_folders_base())
        base.editingFinished.connect(lambda: self._base(base.text()))
        card.add_row(Row(t("studio.folders.base"), t("studio.folders.base_hint"), accessory=base))
        self.content.addWidget(section("", card))
        folders = Card()
        for folder_id, path in self.ctl.user_folder_rows():
            folders.add_row(
                choice_row(
                    t(f"folder.{folder_id}"),
                    path,
                    icon_kind="user_folders",
                    selected=folder_id in uf.folders,
                    on_select=partial(self._folder, folder_id),
                )
            )
        self.content.addWidget(section(t("studio.folders.which"), folders))
        warn = Card()
        warn.add_row(
            Row(
                t("studio.folders.warning_title"),
                t("studio.folders.warning"),
                icon=symbol_icon("!", "#FF9500"),
            )
        )
        self.content.addWidget(section("", warn))

    def _enabled(self, value: bool) -> None:
        self.ctl.set_user_folders(enabled=value)
        self.refresh()

    def _volume(self, serial: str) -> None:
        self.ctl.set_user_folders(serial=serial)
        self.refresh()

    def _base(self, text: str) -> None:
        self.ctl.set_user_folders(base=text.strip())
        self.refresh()

    def _folder(self, folder_id: str, value: bool) -> None:
        self.ctl.set_user_folders(folder=(folder_id, value))
        self.refresh()

    def _read(self) -> None:
        def done(found: bool) -> None:
            self.refresh()
            key = "studio.folders.read_done" if found else "studio.folders.read_none"
            QMessageBox.information(self, t("app.name"), t(key))

        self.tasks.run(t("studio.folders.reading"), self.ctl.detect_user_folders, done)

    def _copy_now(self) -> None:
        answer = QMessageBox.question(
            self, t("studio.folders.copy_now"), t("studio.folders.copy_confirm")
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        def done(report: Any) -> None:
            QMessageBox.information(
                self, t("app.name"), tn("studio.folders.copied", len(report.copied))
            )

        self.tasks.run(t("studio.folders.copying"), self.ctl.copy_user_folders_now, done)
