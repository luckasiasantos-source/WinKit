"""O WinKit grava o pendrive (V3-13, D-045): escolher a ISO, o pendrive e o tipo de PC."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog, QInputDialog, QProgressBar

from winkit.core.usb_safety import boot_warnings
from winkit.i18n import render, t
from winkit.i18n.format import format_size
from winkit.studio.ui.base import Page, show_error
from winkit.studio.ui.pages.common import combo
from winkit.ui.widgets import Card, Row, button, label, section, symbol_icon

BOOT_MODES = ("uefi_bios", "uefi", "bios")


class WriteUsbPage(Page):
    title_key = "studio.writeusb.title"
    subtitle_key = "studio.writeusb.subtitle"

    def __init__(self, ctl: Any, tasks: Any) -> None:
        self._iso: Path | None = None
        self._disk: Any = None
        self._running = False
        self._done: str | None = None
        self._bar = QProgressBar()
        self._status = label("", "Caption")
        super().__init__(ctl, tasks)

    def refresh(self) -> None:
        self.clear_content()
        src = Card()
        src.add_row(
            Row(
                t("studio.customiso.original"),
                str(self._iso) if self._iso else t("studio.customiso.none"),
                accessory=button(t("studio.download.change"), None, self._choose_iso),
                icon=symbol_icon("download", "#007AFF"),
            )
        )
        tw = self.ctl.target_windows
        boot = combo(
            [(m, t(f"studio.writeusb.boot_{m}")) for m in BOOT_MODES],
            self.ctl.media.boot,
            self._boot,
        )
        src.add_row(Row(t("studio.writeusb.boot"), t("studio.writeusb.boot_hint"), accessory=boot))
        for w in boot_warnings(self.ctl.media.boot, tw.version, tw.arch):
            src.add_row(Row(render(w), None, icon=symbol_icon("!", "#FF9500")))
        self.content.addWidget(section(t("studio.writeusb.section_what"), src))

        disks = self.slow("usbdisks")
        card = Card()
        if disks is None:
            card.add_row(Row(t("studio.loading"), None))
        for d in disks if isinstance(disks, list) else []:
            current = self._disk is not None and d.number == self._disk.number
            pick = button(
                t("studio.path.chosen") if current else t("studio.path.choose"),
                None if current else "Primary",
                partial(self._pick, d),
            )
            pick.setEnabled(not current)
            card.add_row(
                Row(
                    f"{', '.join(d.letters) or '—'}  {d.model}",
                    t("studio.writeusb.disk_detail", size=format_size(d.size), serial=d.serial),
                    accessory=pick,
                    icon=symbol_icon("chip", "#8E8E93"),
                )
            )
        if isinstance(disks, list) and not disks:
            card.add_row(Row(t("studio.writeusb.no_disks"), None))
        self.content.addWidget(
            section(t("studio.writeusb.section_disk"), card, footer=t("studio.writeusb.footer"))
        )
        refresh = button(t("studio.pendrive.search"), None, self._search)
        go = button(t("studio.writeusb.start"), "Destructive", self._start)
        go.setEnabled(self._iso is not None and self._disk is not None and not self._running)
        self.content.addLayout(self.toolbar(refresh, go))
        self._bar = QProgressBar()
        self._bar.setRange(0, 1000)
        self._bar.setVisible(self._running)
        self.content.addWidget(self._bar)
        self._status = label(self._status.text() if self._running else "", "Caption")
        self.content.addWidget(self._status)
        if self._done:
            ok = Card()
            ok.add_row(
                Row(
                    t("studio.writeusb.done", letter=self._done),
                    t("studio.writeusb.done_hint"),
                    icon=symbol_icon("check", "#34C759"),
                )
            )
            self.content.addWidget(section("", ok))

    def _choose_iso(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, t("studio.customiso.original"), "", t("studio.path.iso_filter")
        )
        if name:
            self._iso = Path(name)
            self.refresh()

    def _boot(self, mode: str) -> None:
        self.ctl.set_boot(mode)
        self.refresh()

    def _pick(self, disk: Any) -> None:
        self._disk = disk
        self.refresh()

    def _search(self) -> None:
        self.ctl.cache.pop("usbdisks", None)
        self.refresh()

    def ask_letter(self) -> str | None:
        d = self._disk
        text, ok = QInputDialog.getText(
            self,
            t("studio.writeusb.confirm_title"),
            t(
                "studio.writeusb.confirm",
                model=d.model,
                size=format_size(d.size),
                letters=", ".join(d.letters) or "—",
            ),
        )
        return text if ok and text.strip() else None

    def _start(self) -> None:
        typed = self.ask_letter()
        if typed is None or self._iso is None:
            return
        iso, disk = self._iso, self._disk
        self._running, self._done = True, None
        self.refresh()
        self.tasks.with_progress(
            lambda report: self.ctl.write_usb(iso, disk, typed, report),
            self._progress,
            self._finished,
        )

    def _progress(self, step_frac: Any) -> None:
        step, frac = step_frac
        self._bar.setValue(int(frac * 1000))
        self._status.setText(t(f"studio.writeusb.step_{step}", percent=int(frac * 100)))

    def _finished(self, result: Any) -> None:
        self._running = False
        if isinstance(result, BaseException):
            self.refresh()
            show_error(self, result)
            return
        self._done = result
        self.refresh()
        self.window().on_target_changed()  # type: ignore[attr-defined]
