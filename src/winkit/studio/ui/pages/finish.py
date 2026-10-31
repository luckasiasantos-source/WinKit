"""Grupo "Concluir": primeiro login e revisar/construir."""

from __future__ import annotations

from functools import partial
from typing import Any

from PySide6.QtWidgets import QSpinBox

from winkit.i18n import t
from winkit.studio.ui.base import Page
from winkit.studio.ui.pages.common import combo, toggle
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


class ExecutionPage(Page):
    title_key = "studio.execution.title"
    subtitle_key = "studio.execution.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        ex = r.execution
        card = Card()
        mode = SegmentedControl(
            [(m, t(f"studio.execution.mode_{m}")) for m in ("silent", "countdown", "interactive")],
            ex.mode,
        )
        mode.changed.connect(lambda v: self._set("mode", v))
        card.add_row(
            Row(
                t("studio.execution.on_start"),
                t(f"studio.execution.mode_{ex.mode}_hint"),
                accessory=mode,
                icon=symbol_icon("dot", "#007AFF"),
            )
        )
        spin = QSpinBox()
        spin.setRange(5, 600)
        spin.setSuffix(" s")
        spin.setValue(ex.countdown_seconds)
        spin.valueChanged.connect(lambda v: self._set("countdown_seconds", int(v), refresh=False))
        spin.setEnabled(ex.mode == "countdown")
        card.add_row(
            Row(
                t("studio.execution.countdown"),
                None,
                accessory=spin,
                icon=symbol_icon("refresh", "#007AFF"),
            )
        )
        for attr in ("show_tray_icon", "notify_on_finish", "desktop_summary_shortcut"):
            card.add_row(
                Row(
                    t(f"studio.execution.{attr}"),
                    None,
                    accessory=toggle(getattr(ex, attr), partial(self._set_flag, attr)),
                    icon=symbol_icon("check", "#34C759"),
                )
            )
        card.add_row(
            Row(
                t("studio.execution.reboot"),
                None,
                accessory=combo(
                    [
                        (p, t(f"studio.execution.reboot_{p}"))
                        for p in ("ask", "auto_if_idle", "never")
                    ],
                    ex.reboot_policy,
                    lambda v: self._set("reboot_policy", v, refresh=False),
                ),
                icon=symbol_icon("refresh", "#FF9500"),
            )
        )
        self.content.addWidget(section("", card))

    def _set(self, attr: str, value: Any, *, refresh: bool = True) -> None:
        if self.ctl.recipe is not None:
            setattr(self.ctl.recipe.execution, attr, value)
            self.save()
            if refresh:
                self.refresh()

    def _set_flag(self, attr: str, value: bool) -> None:
        self._set(attr, value, refresh=False)


class BuildPage(Page):
    title_key = "studio.build.title"
    subtitle_key = "studio.build.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        rep = self.ctl.validation()
        check = Card()
        if rep.ok and not rep.warnings:
            check.add_row(Row(t("studio.build.no_problems"), icon=symbol_icon("check", "#34C759")))
        for e in rep.errors:
            check.add_row(Row(e, icon=symbol_icon("cross", "#FF3B30")))
        for w in rep.warnings:
            check.add_row(Row(w, icon=symbol_icon("!", "#FF9500")))
        self.content.addWidget(section(t("studio.build.section_check"), check))
        if rep.ok:
            plan = self.ctl.plan()
            for phase in (1, 2):
                card = Card()
                for s in plan.phase(phase):
                    extras = []
                    if s.user_choice:
                        extras.append(t("studio.build.ask"))
                    if s.needs_network:
                        extras.append(t("studio.build.internet"))
                    card.add_row(Row(s.title, " · ".join(extras) or None, icon=kind_icon(s.kind)))
                title = t(f"studio.build.phase{phase}", n=len(plan.phase(phase)))
                self.content.addWidget(section(title, card))
        build = button(t("studio.build.build"), "Primary", self._build)
        build.setEnabled(rep.ok)
        self.content.addLayout(
            self.toolbar(build, button(t("studio.build.validate"), None, self._validate))
        )
        self.result = label("", "Secondary")
        self.content.addWidget(self.result)

    def _build(self) -> None:
        def done(rep: Any) -> None:
            lines = [
                t(
                    "studio.build.report",
                    templates=len(rep.templates),
                    isos=len(rep.isos),
                    files=rep.manifest_files,
                )
            ]
            lines += [f"⚠ {w}" for w in rep.warnings]
            self.refresh()
            self.result.setText(t("studio.build.ready") + "\n" + "\n".join(lines))

        self.tasks.run(t("studio.build.building"), self.ctl.build, done)

    def _validate(self) -> None:
        def done(rep: Any) -> None:
            if rep.ok:
                text = t("studio.build.all_good")
            else:
                text = t("studio.build.problems") + "\n" + "\n".join(rep.problems)
            if rep.warnings:
                text += "\n" + t("studio.build.warnings") + "\n" + "\n".join(rep.warnings)
            self.result.setText(text)

        self.tasks.run(t("studio.build.checking"), self.ctl.validate_pendrive, done)
