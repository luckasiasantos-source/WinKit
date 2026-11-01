"""ISO personalizada (V3-11/12): uma cópia da ISO; a original nunca é modificada (D-044)."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressBar

from winkit.builder.custom_iso import CustomIsoOptions
from winkit.core import layout
from winkit.i18n import t, tn
from winkit.i18n.format import format_size
from winkit.studio.ui.base import Page, show_error
from winkit.studio.ui.pages.common import toggle
from winkit.ui.widgets import Card, Row, button, label, section, symbol_icon


class CustomIsoPage(Page):
    title_key = "studio.customiso.title"
    subtitle_key = "studio.customiso.subtitle"

    def __init__(self, ctl: Any, tasks: Any) -> None:
        self._iso: Path | None = None
        self._editions: list[Any] = []
        self._keep: set[int] = set()
        self._drivers = True
        self._extra: Path | None = None
        self._updates: list[Path] = []
        self._remove_apps = True
        self._rollup = True
        self._self_contained = False
        self._output: Path | None = None
        self._work: Path | None = None
        self._running = False
        self._done: Path | None = None
        self._bar = QProgressBar()
        self._status = label("", "Caption")
        super().__init__(ctl, tasks)

    def refresh(self) -> None:
        self.clear_content()
        self._source_section()
        self._what_section()
        where = Card()
        where.add_row(
            Row(
                t("studio.customiso.output"),
                str(self._output_path()),
                accessory=button(t("studio.download.change"), None, self._choose_output),
            )
        )
        where.add_row(
            Row(
                t("studio.customiso.work"),
                str(self._work_dir()),
                accessory=button(t("studio.download.change"), None, self._choose_work),
            )
        )
        self.content.addWidget(section(t("studio.customiso.section_where"), where))
        go = button(t("studio.customiso.start"), "Primary", self._start)
        go.setEnabled(self._iso is not None and not self._running)
        self.content.addLayout(self.toolbar(go))
        self._bar = QProgressBar()
        self._bar.setRange(0, 1000)
        self._bar.setVisible(self._running)
        self.content.addWidget(self._bar)
        self._status = label(self._status.text() if self._running else "", "Caption")
        self.content.addWidget(self._status)
        if self._done is not None:
            ok = Card()
            ok.add_row(
                Row(
                    t("studio.customiso.done"),
                    str(self._done),
                    icon=symbol_icon("check", "#34C759"),
                )
            )
            self.content.addWidget(section("", ok))

    def _source_section(self) -> None:
        src = Card()
        src.add_row(
            Row(
                t("studio.customiso.original"),
                str(self._iso) if self._iso else t("studio.customiso.none"),
                accessory=button(t("studio.download.change"), None, self._choose_iso),
                icon=symbol_icon("download", "#007AFF"),
            )
        )
        for ed in self._editions:
            src.add_row(
                Row(
                    ed.name,
                    format_size(ed.size),
                    accessory=toggle(ed.index in self._keep, partial(self._edition, ed.index)),
                )
            )
        self.content.addWidget(
            section(t("studio.customiso.section_source"), src, footer=t("studio.customiso.footer"))
        )

    def _what_section(self) -> None:
        what = Card()
        what.add_row(
            Row(
                t("studio.customiso.drivers"),
                t("studio.customiso.drivers_hint"),
                accessory=toggle(self._drivers, partial(setattr, self, "_drivers")),
            )
        )
        what.add_row(
            Row(
                t("studio.customiso.extra_drivers"),
                str(self._extra) if self._extra else t("studio.customiso.none"),
                accessory=button(t("studio.download.change"), None, self._choose_extra),
            )
        )
        what.add_row(
            Row(
                t("studio.customiso.updates"),
                ", ".join(u.name for u in self._updates) or t("studio.customiso.none"),
                accessory=button(t("studio.customiso.add_update"), None, self._add_update),
            )
        )
        if self.ctl.target_windows.version == "7":
            what.add_row(
                Row(
                    t("studio.customiso.rollup"),
                    t("studio.customiso.rollup_hint"),
                    accessory=toggle(self._rollup, partial(setattr, self, "_rollup")),
                )
            )
        n_apps = len(self.ctl.recipe.bloatware.remove) if self.ctl.recipe else 0
        what.add_row(
            Row(
                t("studio.customiso.remove_apps"),
                tn("studio.customiso.remove_apps_hint", n_apps),
                accessory=toggle(self._remove_apps, partial(setattr, self, "_remove_apps")),
            )
        )
        has_pendrive = self.ctl.target is not None and self.ctl.recipe is not None
        whole = toggle(
            self._self_contained and has_pendrive, partial(setattr, self, "_self_contained")
        )
        whole.setEnabled(has_pendrive)
        what.add_row(
            Row(
                t("studio.customiso.self_contained"),
                t("studio.customiso.self_contained_hint"),
                accessory=whole,
            )
        )
        self.content.addWidget(section(t("studio.customiso.section_what"), what))

    def _output_path(self) -> Path:
        if self._output:
            return self._output
        if self._iso:
            return self._iso.with_name(self._iso.stem + "-winkit.iso")
        return Path.home() / "Downloads" / "Windows-winkit.iso"

    def _work_dir(self) -> Path:
        return self._work or self._output_path().parent

    def options(self) -> CustomIsoOptions:
        if self._iso is None:
            raise ValueError("ISO original não escolhida")
        drivers = []
        if (
            self._drivers
            and self.ctl.target is not None
            and (self.ctl.root / layout.DRIVERS).is_dir()
        ):
            drivers.append(self.ctl.root / layout.DRIVERS)
        if self._extra:
            drivers.append(self._extra)
        remove = (
            list(self.ctl.recipe.bloatware.remove) if self._remove_apps and self.ctl.recipe else []
        )
        whole = self._self_contained and self.ctl.target is not None
        return CustomIsoOptions(
            original=self._iso,
            output=self._output_path(),
            work_dir=self._work_dir(),
            editions=sorted(self._keep),
            drivers=drivers,
            updates=list(self._updates),
            remove_apps=remove,
            self_contained_from=self.ctl.root if whole else None,
            profile_id=self.ctl.profile_id,
            agent_source=self.ctl.agent_source,
        )

    def _choose_iso(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, t("studio.customiso.original"), "", t("studio.path.iso_filter")
        )
        if name:
            self.load_iso(Path(name))

    def load_iso(self, iso: Path) -> None:
        def done(editions: list[Any]) -> None:
            self._iso, self._editions = iso, editions
            self._keep = {e.index for e in editions}
            self.refresh()

        self.tasks.run(t("studio.customiso.reading"), lambda: self.ctl.iso_editions(iso), done)

    def _edition(self, index: int, value: bool) -> None:
        if value:
            self._keep.add(index)
        else:
            self._keep.discard(index)

    def _choose_extra(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, t("studio.customiso.extra_drivers"))
        self._extra = Path(folder) if folder else None
        self.refresh()

    def _add_update(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(
            self, t("studio.customiso.add_update"), "", t("studio.customiso.update_filter")
        )
        self._updates += [Path(n) for n in names]
        self.refresh()

    def _choose_output(self) -> None:
        name, _ = QFileDialog.getSaveFileName(
            self,
            t("studio.customiso.output"),
            str(self._output_path()),
            t("studio.path.iso_filter"),
        )
        if name:
            self._output = Path(name)
            self.refresh()

    def _choose_work(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, t("studio.customiso.work"))
        if folder:
            self._work = Path(folder)
            self.refresh()

    def _start(self) -> None:
        if not self._keep:
            QMessageBox.warning(self, t("app.name"), t("studio.customiso.no_edition"))
            return
        opts = self.options()
        rollup = self._rollup and self.ctl.target_windows.version == "7"
        self._running, self._done = True, None
        self.refresh()

        def job(report: Any) -> Path:
            if rollup:  # Windows 7 "SP2" (V3-14)
                opts.updates = [*opts.updates, *self.ctl.win7_rollup()]
            return self.ctl.make_custom_iso(opts, report)

        self.tasks.with_progress(job, self._progress, self._finished)

    def _progress(self, step_frac: Any) -> None:
        step, frac = step_frac
        self._bar.setValue(int(frac * 1000))
        self._status.setText(t(f"studio.customiso.step_{step}", percent=int(frac * 100)))

    def _finished(self, result: Any) -> None:
        self._running = False
        if isinstance(result, BaseException):
            self.refresh()
            show_error(self, result)
            return
        self._done = result
        self.refresh()
