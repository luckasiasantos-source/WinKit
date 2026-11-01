"""Grupo "Concluir": primeiro login e revisar/construir."""

from __future__ import annotations

from functools import partial
from typing import Any

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QSpinBox

from winkit.core.live import LivePreview
from winkit.i18n import render, t
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
        skipped: list[str] = getattr(self.window(), "skipped_titles", list)()
        if skipped:  # etapas puladas no modo em etapas (V3-05)
            check.add_row(
                Row(
                    t("studio.build.skipped"),
                    ", ".join(skipped),
                    icon=symbol_icon("!", "#8E8E93"),
                )
            )
        self.content.addWidget(section(t("studio.build.section_check"), check))
        r = self.ctl.recipe
        if r is not None:
            cmp_card = Card()
            cmp_card.add_row(
                Row(
                    t("studio.build.compare"),
                    t("studio.build.compare_hint"),
                    accessory=toggle(r.compare_after_install, self._set_compare),
                    icon=kind_icon("compare"),
                )
            )
            self.content.addWidget(section("", cmp_card))
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

    def _set_compare(self, value: bool) -> None:
        if self.ctl.recipe is not None:
            self.ctl.recipe.compare_after_install = value
            self.save()


_STATUS_ICON = {
    "already_done": ("check", "#34C759"),
    "will_change": ("refresh", "#007AFF"),
    "not_applicable": ("minus", "#8E8E93"),
}


class LivePage(Page):
    """V2-03: aplicar a receita neste Windows, com prévia e ponto de restauração (D-033)."""

    title_key = "studio.live.title"
    subtitle_key = "studio.live.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        self._kinds: dict[str, bool] = dict.fromkeys(self.ctl.live_kinds(), True)
        self._restore = True
        self._previewed = False
        warn = Card()
        warn.add_row(
            Row(
                t("studio.live.warning_title"),
                t("studio.live.warning"),
                icon=symbol_icon("!", "#FF9500"),
            )
        )
        self.content.addWidget(section("", warn))
        what = Card()
        for kind in self._kinds:
            what.add_row(
                Row(
                    t(f"studio.live.kind.{kind}"),
                    None,
                    accessory=toggle(True, partial(self._set_kind, kind)),
                    icon=kind_icon(kind),
                )
            )
        self.content.addWidget(section(t("studio.live.section_what"), what))
        safety = Card()
        self._restore_switch = toggle(True, self._set_restore)
        safety.add_row(
            Row(
                t("studio.live.restore"),
                t("studio.live.restore_hint"),
                accessory=self._restore_switch,
                icon=kind_icon("restore_point"),
            )
        )
        self.content.addWidget(section(t("studio.live.section_safety"), safety))
        self.apply_button = button(t("studio.live.apply"), "Primary", self._apply)
        self.apply_button.setEnabled(False)
        self.content.addLayout(
            self.toolbar(button(t("studio.live.preview"), None, self._preview), self.apply_button)
        )
        self.result = label(t("studio.live.preview_first"), "Secondary")
        self.content.addWidget(self.result)

    def _selected(self) -> frozenset[str]:
        return frozenset(k for k, on in self._kinds.items() if on)

    def _invalidate(self) -> None:
        self._previewed = False
        self.apply_button.setEnabled(False)
        self.result.setText(t("studio.live.preview_first"))

    def _set_kind(self, kind: str, value: bool) -> None:
        self._kinds[kind] = value
        self._invalidate()

    def _set_restore(self, value: bool) -> None:
        if not value:
            answer = QMessageBox.question(self, t("app.name"), t("studio.live.restore_off_confirm"))
            if answer != QMessageBox.StandardButton.Yes:
                self._restore_switch.setChecked(True)
                return
        self._restore = value
        self._invalidate()

    def _preview(self) -> None:
        def done(preview: LivePreview) -> None:
            card = Card()
            for item in preview.items:
                glyph, color = _STATUS_ICON[item.status]
                lines = [t(f"preview.status.{item.status}")]
                lines += [render(m) for m in (*item.changes, *item.warnings)]
                card.add_row(Row(item.title, "\n".join(lines), icon=symbol_icon(glyph, color)))
            if not card.rows:
                card.add_row(Row(t("studio.live.nothing")))
            counts = t(
                "studio.live.preview_counts",
                change=preview.count("will_change"),
                done=preview.count("already_done"),
            )
            self.content.addWidget(section(t("studio.live.section_preview"), card, footer=counts))
            self._previewed = True
            self.apply_button.setEnabled(preview.count("will_change") > 0)
            self.result.setText(t("studio.live.ready_to_apply"))

        kinds = self._selected()
        self.tasks.run(
            t("studio.live.previewing"),
            lambda: self.ctl.live_preview(kinds, self._restore),  # type: ignore[arg-type]
            done,
        )

    def _apply(self) -> None:
        if not self._previewed:
            return

        def done(result: Any) -> None:
            c = result.counts
            self.result.setText(
                t(
                    "studio.live.applied",
                    done=c.get("done", 0),
                    failed=c.get("failed", 0),
                    skipped=c.get("skipped", 0),
                )
            )
            self.apply_button.setEnabled(False)
            if result.summary_html is not None:
                self._summary = result.summary_html
                self.content.addLayout(
                    self.toolbar(button(t("ui.agent.open_summary"), None, self._open_summary))
                )

        kinds = self._selected()
        self.tasks.run(
            t("studio.live.applying"),
            lambda: self.ctl.live_apply(kinds, self._restore),  # type: ignore[arg-type]
            done,
        )

    def _open_summary(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._summary)))
