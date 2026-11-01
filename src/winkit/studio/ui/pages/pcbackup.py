"""Backup do PC para outro disco e "Antes de formatar" (V3-09, V3-10, V3-15, V3-16)."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressBar

from winkit.collector.pc_backup import BackupStopped
from winkit.i18n import render, t, tn
from winkit.i18n.format import format_duration, format_size
from winkit.studio.ui.base import Page, show_error
from winkit.studio.ui.pages.common import toggle
from winkit.ui.widgets import Card, Row, button, label, section, symbol_icon

KIND_COLOR = {"nvme": "#30D158", "ssd": "#34C759", "hdd": "#FF9500", "usb": "#8E8E93"}


class PcBackupPage(Page):
    """V3-09/10: copiar arquivos para outro disco, conferir e trazer de volta."""

    title_key = "studio.pcbackup.title"
    subtitle_key = "studio.pcbackup.subtitle"

    def __init__(self, ctl: Any, tasks: Any) -> None:
        self._estimate: Any = None
        self._result: Any = None
        self._running = False
        self._stop = False
        self._bar = QProgressBar()
        self._status = label("", "Caption")
        super().__init__(ctl, tasks)

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        b = self.ctl.require_recipe().pc_backup
        dests = self.slow("destinations")
        chosen = b.destination.serial if b.destination else None
        where = Card()
        if dests is None:
            where.add_row(Row(t("studio.loading"), None))
        for d in dests if isinstance(dests, list) else []:
            current = d.serial == chosen
            pick = button(
                t("studio.path.chosen") if current else t("studio.path.choose"),
                None if current else "Primary",
                partial(self._dest, d),
            )
            pick.setEnabled(not current and not d.locked)
            sub = t(
                "studio.pcbackup.dest_detail",
                kind=t(f"pcbackup.kind_{d.kind}"),
                fs=d.file_system,
                free=format_size(d.free),
                model=d.model,
            )
            if d.system_disk:
                sub += "\n⚠ " + t("pcbackup.warn_same_disk")
            if d.locked:
                sub += "\n⚠ " + t("studio.pcbackup.locked")
            where.add_row(
                Row(
                    f"{d.letter}  {d.label}",
                    sub,
                    accessory=pick,
                    icon=symbol_icon("chip", KIND_COLOR.get(d.kind, "#8E8E93")),
                )
            )
        self.content.addWidget(section(t("studio.pcbackup.section_where"), where))

        what = Card()
        for literal in b.sources:
            what.add_row(
                Row(
                    literal,
                    None,
                    accessory=button(
                        t("studio.extra.remove"), None, partial(self._remove, literal)
                    ),
                    icon=symbol_icon("folder", "#34C759"),
                )
            )
        if not b.sources:
            what.add_row(Row(t("studio.pcbackup.no_sources"), None))
        self.content.addWidget(section(t("studio.pcbackup.section_what"), what))
        self.content.addLayout(
            self.toolbar(
                button(t("studio.pcbackup.user_folders"), None, self._defaults),
                button(t("studio.pcbackup.add_folder"), None, self._add),
            )
        )
        opts = Card()
        opts.add_row(
            Row(
                t("studio.pcbackup.zip"),
                t("studio.pcbackup.zip_hint"),
                accessory=toggle(b.zip, self._zip),
            )
        )
        opts.add_row(
            Row(
                t("studio.pcbackup.restore_after"),
                t("studio.pcbackup.restore_after_hint"),
                accessory=toggle(b.restore_after_install, self._restore_after),
            )
        )
        self.content.addWidget(section(t("studio.pcbackup.section_options"), opts))

        ready = b.destination is not None and bool(b.sources)
        go = button(
            t("studio.pcbackup.pause") if self._running else t("studio.pcbackup.start"),
            None if self._running else "Primary",
            self._pause if self._running else self._start,
        )
        go.setEnabled(ready)
        est = button(t("studio.pcbackup.estimate"), None, self._estimate_now)
        est.setEnabled(ready and not self._running)
        self.content.addLayout(self.toolbar(est, go))
        if self._estimate is not None:
            e = self._estimate
            card = Card()
            card.add_row(
                Row(
                    t("studio.pcbackup.estimate_title", size=format_size(e.total), n=e.files),
                    t(
                        "studio.pcbackup.estimate_detail",
                        time=format_duration(e.seconds),
                        speed=f"{e.speed:.0f}",
                    )
                    + ("" if e.measured else " " + t("studio.pcbackup.estimate_typical")),
                    icon=symbol_icon("refresh", "#007AFF"),
                )
            )
            for w in e.warnings:
                card.add_row(Row(render(w), None, icon=symbol_icon("!", "#FF9500")))
            self.content.addWidget(section("", card))
        self._bar = QProgressBar()
        self._bar.setRange(0, 1000)
        self._bar.setVisible(self._running)
        self.content.addWidget(self._bar)
        self._status = label(self._status.text() if self._running else "", "Caption")
        self.content.addWidget(self._status)
        if self._result is not None:
            m = self._result
            done = Card()
            done.add_row(
                Row(
                    t("studio.pcbackup.done", n=len(m.files), size=format_size(m.total_bytes)),
                    tn("studio.pcbackup.failed", len(m.failed))
                    if m.failed
                    else t("studio.pcbackup.all_ok"),
                    icon=symbol_icon(
                        "!" if m.failed else "check", "#FF9500" if m.failed else "#34C759"
                    ),
                )
            )
            for key, why in list(m.failed.items())[:10]:
                done.add_row(Row(key, why))
            self.content.addWidget(section(t("studio.pcbackup.section_result"), done))
        self._restore_section()

    def _restore_section(self) -> None:
        found = (
            self.ctl.pc_backups_found()
            if isinstance(self.ctl.cache.get("destinations"), list)
            else []
        )
        card = Card()
        for base, manifest in found:
            card.add_row(
                Row(
                    t("studio.pcbackup.found", pc=manifest.computer, n=len(manifest.files)),
                    t(
                        "studio.pcbackup.found_detail",
                        size=format_size(manifest.total_bytes),
                        path=str(base),
                    ),
                    accessory=button(
                        t("studio.pcbackup.restore"), None, partial(self._restore, base, manifest)
                    ),
                    icon=symbol_icon("folder", "#007AFF"),
                )
            )
        if not card.rows:
            card.add_row(Row(t("studio.pcbackup.none_found"), None))
        self.content.addWidget(
            section(
                t("studio.pcbackup.section_restore"),
                card,
                footer=t("studio.pcbackup.restore_footer"),
            )
        )

    # ---- ações
    def _dest(self, d: Any) -> None:
        self.ctl.set_pc_destination(d)
        self._estimate = None
        self.refresh()

    def _remove(self, literal: str) -> None:
        b = self.ctl.require_recipe().pc_backup
        self.ctl.set_pc_sources([x for x in b.sources if x != literal])
        self.refresh()

    def _defaults(self) -> None:
        b = self.ctl.require_recipe().pc_backup
        self.ctl.set_pc_sources([*b.sources, *self.ctl.default_pc_sources()])
        self.refresh()

    def _add(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, t("studio.pcbackup.add_folder"))
        if folder:
            b = self.ctl.require_recipe().pc_backup
            self.ctl.set_pc_sources([*b.sources, folder.replace("/", "\\")])
            self.refresh()

    def _zip(self, value: bool) -> None:
        self.ctl.require_recipe().pc_backup.zip = value
        self.save()

    def _restore_after(self, value: bool) -> None:
        self.ctl.require_recipe().pc_backup.restore_after_install = value
        self.save()

    def _estimate_now(self) -> None:
        def done(e: Any) -> None:
            self._estimate = e
            self.refresh()

        self.tasks.run(t("studio.pcbackup.estimating"), self.ctl.pc_estimate, done)

    def _start(self) -> None:
        self._running, self._stop, self._result = True, False, None
        self.refresh()
        self.tasks.with_progress(
            lambda report: self.ctl.run_pc_backup(report, lambda: self._stop),
            self._progress,
            self._finished,
        )

    def _pause(self) -> None:
        self._stop = True

    def _progress(self, p: Any) -> None:
        if p.total_bytes:
            self._bar.setValue(int(p.done_bytes * 1000 / p.total_bytes))
        self._status.setText(
            t(
                "studio.pcbackup.progress",
                files=p.done_files,
                total=p.total_files,
                done=format_size(p.done_bytes),
                size=format_size(p.total_bytes),
            )
        )

    def _finished(self, result: Any) -> None:
        self._running = False
        if isinstance(result, BackupStopped):
            self.refresh()
            return
        if isinstance(result, BaseException):
            self.refresh()
            show_error(self, result)
            return
        self._result = result
        self.refresh()
        QMessageBox.information(
            self,
            t("app.name"),
            t("studio.pcbackup.notify_done")
            if not result.failed
            else tn("studio.pcbackup.failed", len(result.failed)),
        )

    def _restore(self, base: Path, manifest: Any) -> None:
        def done(report: Any) -> None:
            if isinstance(report, BaseException):
                show_error(self, report)
                return
            QMessageBox.information(
                self,
                t("app.name"),
                t(
                    "studio.pcbackup.restored",
                    copied=report.copied,
                    kept=report.kept,
                    failed=len(report.failed),
                ),
            )

        self.tasks.with_progress(
            lambda report: self.ctl.restore_pc_backup(base, manifest, report), self._progress, done
        )


class HealthPage(Page):
    """V3-15/16: "pode formatar?" — backup conferido, BitLocker e chave, ativação, espaço."""

    title_key = "studio.health.title"
    subtitle_key = "studio.health.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        if self.needs_recipe():
            return
        h = self.slow("health")
        card = Card()
        found = (
            self.ctl.pc_backups_found()
            if isinstance(self.ctl.cache.get("destinations"), list)
            else []
        )
        verified = any(not m.failed and m.files for _, m in found)
        card.add_row(
            Row(
                t("health.backup_ok") if verified else t("health.backup_missing"),
                t("health.backup_hint"),
                icon=symbol_icon(
                    "check" if verified else "!", "#34C759" if verified else "#FF3B30"
                ),
            )
        )
        if h is None:
            card.add_row(Row(t("studio.loading"), None))
        elif not isinstance(h, Exception):
            if h.bitlocker_on:
                card.add_row(
                    Row(
                        t("health.bitlocker_on"),
                        tn("health.bitlocker_keys", h.recovery_keys),
                        accessory=button(t("health.export_key"), "Primary", self._export),
                        icon=symbol_icon("!", "#FF9500"),
                    )
                )
            else:
                card.add_row(
                    Row(t("health.bitlocker_off"), None, icon=symbol_icon("check", "#34C759"))
                )
            card.add_row(
                Row(
                    t("health.activated") if h.activated else t("health.not_activated"),
                    t("health.activation_hint"),
                    icon=symbol_icon(
                        "check" if h.activated else "!", "#34C759" if h.activated else "#FF9500"
                    ),
                )
            )
        ready = verified and (
            h is None
            or isinstance(h, Exception)
            or not h.bitlocker_on
            or h.recovery_keys == 0
            or self._exported
        )
        card.add_row(
            Row(
                t("health.ready") if ready else t("health.not_ready"),
                t("health.ready_hint"),
                icon=symbol_icon("check" if ready else "cross", "#34C759" if ready else "#FF3B30"),
            )
        )
        self.content.addWidget(section(t("health.section"), card))

    _exported = False

    def _export(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, t("health.export_where"))
        if not folder:
            return

        def done(path: Any) -> None:
            self._exported = True
            self.refresh()
            QMessageBox.information(self, t("app.name"), t("health.exported", path=str(path)))

        self.tasks.run(
            t("health.exporting"), lambda: self.ctl.export_recovery_keys(Path(folder)), done
        )
