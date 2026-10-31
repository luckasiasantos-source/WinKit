"""Grupo "Sistema": apps pré-instalados, ajustes, energia e atualizações."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

from PySide6.QtWidgets import QSpinBox

from winkit.core.recipe.models import Recipe, TweakSelection
from winkit.i18n import t
from winkit.studio.ui.base import Page
from winkit.studio.ui.pages.common import choice_row, combo, toggle
from winkit.ui.widgets import Card, Row, SegmentedControl, kind_icon, section, symbol_icon


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
        }
    )
    CATEGORIES: tuple[str, ...] = ("privacy", "visual", "system")

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
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
