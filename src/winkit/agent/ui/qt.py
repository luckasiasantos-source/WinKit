"""Janela, bandeja e diálogos da Fase 2 (PLANO.md §12, D-008, D-026).

O trabalho do Agente roda numa thread; o Qt roda na thread principal. Os métodos do
protocolo ``AgentUi`` são chamados pela thread de trabalho e repassados à interface por
sinais (thread-safe). ``choose`` e ``ask_reboot`` esperam a resposta do usuário.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QScrollArea,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from winkit.agent.progress import Choice
from winkit.core.planner.models import PlannedStep
from winkit.core.recipe.models import Execution
from winkit.core.summary import Summary
from winkit.i18n import t
from winkit.ui import theme
from winkit.ui.widgets import (
    Card,
    Row,
    ToggleSwitch,
    app_icon,
    button,
    expanding,
    kind_icon,
    label,
    section,
    symbol_icon,
)

KIND_COUNT_KEYS = {
    "driver": "ui.count.driver",
    "bloat": "ui.count.bloat",
    "tweak": "ui.count.tweak",
    "power": "ui.count.power",
    "backup": "ui.count.backup",
    "app": "ui.count.app",
}


@dataclass
class _Request:
    event: threading.Event = field(default_factory=threading.Event)
    value: Any = None


# ------------------------------------------------------------------ páginas
class ChoosePage(QWidget):
    """Antes de começar: o que já foi feito, o que será feito, escolhas e contagem."""

    decided = Signal(object)  # Choice

    def __init__(
        self,
        pending: list[PlannedStep],
        done_before: dict[str, int],
        *,
        countdown: int | None,
        default_name: str | None,
    ) -> None:
        super().__init__()
        self._toggles: dict[str, ToggleSwitch] = {}
        self._name_edit: QLineEdit | None = None
        self._remaining = countdown
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 20)
        root.setSpacing(18)

        head = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(app_icon(56).pixmap(56, 56))
        head.addWidget(icon)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(label(t("ui.agent.title"), "LargeTitle"))
        titles.addWidget(label(t("ui.agent.subtitle"), "Secondary"))
        head.addLayout(titles, 1)
        root.addLayout(head)

        content = QWidget()
        col = QVBoxLayout(content)
        col.setContentsMargins(0, 0, 12, 0)  # folga para a barra de rolagem
        col.setSpacing(18)

        done_card = Card()
        if done_before:
            order = list(KIND_COUNT_KEYS)
            for kind, count in sorted(
                done_before.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99
            ):
                key = KIND_COUNT_KEYS.get(kind)
                if key and count:
                    done_card.add_row(
                        Row(t(key, count=count), icon=symbol_icon("check", "#34C759"))
                    )
        if not done_card.rows:
            done_card.add_row(Row(t("ui.agent.nothing_before")))
        col.addWidget(section(t("agent.done_before_login"), done_card))

        todo = Card()
        for step in pending:
            if step.kind == "finalize":
                continue
            accessory: QWidget
            if step.kind == "rename_computer" and step.user_choice:
                self._name_edit = QLineEdit(default_name or "")
                self._name_edit.setPlaceholderText("PC-NOVO")
                self._name_edit.setMaxLength(15)
                self._name_edit.setFixedWidth(180)
                self._name_edit.textEdited.connect(self.pause_countdown)
                accessory = self._name_edit
            elif step.user_choice:
                sw = ToggleSwitch(True)
                sw.toggledByUser.connect(self.pause_countdown)
                self._toggles[step.id] = sw
                accessory = sw
            else:
                accessory = label(t("ui.agent.included"), "Caption", wrap=False)
            todo.add_row(Row(step.title, None, accessory=accessory, icon=kind_icon(step.kind)))
        if not todo.rows:
            todo.add_row(Row(t("ui.agent.only_summary")))
        col.addWidget(
            section(
                t("agent.todo_now"),
                todo,
                footer=t("ui.agent.todo_footer") if self._toggles else None,
            )
        )
        col.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        bar = QHBoxLayout()
        self.countdown_label = label("", "Secondary", wrap=False)
        bar.addWidget(self.countdown_label)
        bar.addWidget(expanding())
        self.postpone_btn = button(t("agent.postpone"), None, self._postpone)
        self.start_btn = button(t("agent.start"), "Primary", self._start)
        self.start_btn.setDefault(True)
        bar.addWidget(self.postpone_btn)
        bar.addWidget(self.start_btn)
        root.addLayout(bar)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        if countdown:
            self._update_countdown()
            self._timer.start()

    # ---- contagem regressiva
    def _update_countdown(self) -> None:
        if self._remaining is not None:
            self.countdown_label.setText(t("agent.starting_in", seconds=self._remaining))

    def _tick(self) -> None:
        if self._remaining is None:
            return
        self._remaining -= 1
        if self._remaining <= 0:
            self._timer.stop()
            self._start()
        else:
            self._update_countdown()

    def pause_countdown(self, *_: object) -> None:
        if self._remaining is not None:
            self._timer.stop()
            self._remaining = None
            self.countdown_label.setText(t("ui.agent.countdown_paused"))

    def mousePressEvent(self, event: Any) -> None:
        self.pause_countdown()
        super().mousePressEvent(event)

    # ---- decisão
    def selection(self) -> frozenset[str]:
        return frozenset(k for k, sw in self._toggles.items() if sw.isChecked())

    def _start(self) -> None:
        self._timer.stop()
        name = self._name_edit.text().strip() if self._name_edit else None
        self.decided.emit(Choice("start", selected=self.selection(), computer_name=name or None))

    def _postpone(self) -> None:
        self._timer.stop()
        self.decided.emit(Choice("postpone"))


class ProgressPage(QWidget):
    minimize_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._rows: dict[str, Row] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 20)
        root.setSpacing(14)
        root.addWidget(label(t("ui.agent.progress_title"), "LargeTitle"))
        self.current = label("", "Secondary")
        root.addWidget(self.current)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        root.addWidget(self.bar)
        self.notice = label("", "Warning")
        self.notice.setVisible(False)
        root.addWidget(self.notice)
        self.card = Card()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(0, 0, 12, 0)
        hl.addWidget(self.card)
        hl.addStretch(1)
        scroll.setWidget(holder)
        root.addWidget(scroll, 1)
        bar = QHBoxLayout()
        bar.addWidget(expanding())
        bar.addWidget(button(t("ui.agent.minimize"), None, self.minimize_requested.emit))
        root.addLayout(bar)

    def set_steps(self, steps: list[PlannedStep]) -> None:
        self.card.clear()
        self._rows.clear()
        for s in steps:
            row = Row(s.title, None, icon=symbol_icon("dot", "#C7C7CC"))
            self._rows[s.id] = row
            self.card.add_row(row)

    def progress(self, done: int, total: int, current: str) -> None:
        self.bar.setMaximum(max(total, 1))
        self.bar.setValue(done)
        self.current.setText(
            t("agent.progress", done=done, total=total, current=current) if current else ""
        )

    def step_result(self, step_id: str, status: str, message: str | None) -> None:
        row = self._rows.get(step_id)
        if row is None:
            return
        icon = {
            "done": symbol_icon("check", "#34C759"),
            "failed": symbol_icon("cross", "#FF3B30"),
            "skipped": symbol_icon("minus", "#8E8E93"),
        }.get(status, symbol_icon("dot", "#FF9500"))
        row.set_icon(icon)
        row.set_subtitle(message if status != "done" else (message or None))

    def waiting(self, reason: str, active: bool) -> None:
        texts = {
            "pendrive": t("agent.reconnect_pendrive"),
            "network": t("agent.waiting_network"),
            "winget": t("agent.waiting_winget"),
        }
        self.notice.setText(texts.get(reason, ""))
        self.notice.setVisible(active)


class DonePage(QWidget):
    close_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._html: Path | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 48, 32, 24)
        root.setSpacing(12)
        root.addStretch(1)
        self.icon = QLabel()
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.icon)
        self.title = label("", "LargeTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.title)
        self.counts = label("", "Secondary")
        self.counts.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.counts)
        root.addStretch(2)
        bar = QHBoxLayout()
        bar.addWidget(expanding())
        bar.addWidget(button(t("ui.agent.open_summary"), None, self.open_summary))
        bar.addWidget(button(t("ui.agent.close"), "Primary", self.close_requested.emit))
        root.addLayout(bar)

    def show_summary(self, summary: Summary, html: Path) -> None:
        self._html = html
        ok = summary.failed == 0
        self.icon.setPixmap(
            symbol_icon("check" if ok else "!", "#34C759" if ok else "#FF9500", 72).pixmap(72, 72)
        )
        self.title.setText(t("ui.agent.all_done") if ok else t("ui.agent.done_with_failures"))
        self.counts.setText(
            t("summary.counts", done=summary.done, failed=summary.failed, skipped=summary.skipped)
        )

    def open_summary(self) -> None:
        if self._html is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._html)))


class RebootDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("app.name"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumWidth(380)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 18)
        lay.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(app_icon(48).pixmap(48, 48))
        lay.addWidget(ic, 0, Qt.AlignmentFlag.AlignHCenter)
        title = label(t("ui.agent.reboot_title"), "Headline")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        body = label(t("agent.reboot_needed"), "Secondary")
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(body)
        bar = QHBoxLayout()
        bar.addWidget(button(t("agent.reboot_later"), None, self.reject))
        now = button(t("agent.reboot_now"), "Primary", self.accept)
        bar.addWidget(now)
        lay.addLayout(bar)


class AgentWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Root")
        self.setWindowTitle(t("agent.title"))
        self.setWindowIcon(app_icon())
        self.resize(720, 620)
        self.stack = QStackedWidget(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.stack)
        self.progress_page = ProgressPage()
        self.done_page = DonePage()
        self.stack.addWidget(self.progress_page)
        self.stack.addWidget(self.done_page)
        self.choose_page: ChoosePage | None = None

    def show_choose(self, page: ChoosePage) -> None:
        if self.choose_page is not None:
            self.stack.removeWidget(self.choose_page)
        self.choose_page = page
        self.stack.insertWidget(0, page)
        self.stack.setCurrentWidget(page)


# ------------------------------------------------------------------ ponte entre threads
class _Gui(QObject):
    sig_choose = Signal(object, object, object)
    sig_progress = Signal(int, int, str)
    sig_step = Signal(str, str, object)
    sig_waiting = Signal(str, bool)
    sig_notify = Signal(str, str)
    sig_reboot = Signal(object)
    sig_finished = Signal(object, object)
    sig_work_done = Signal()

    def __init__(self, execution: Execution, *, auto_quit_ms: int) -> None:
        super().__init__()
        self.execution = execution
        self.window_mode = execution.mode != "silent"
        self.auto_quit_ms = auto_quit_ms
        self.window = AgentWindow()
        self.finished_seen = False
        self.tray: QSystemTrayIcon | None = None
        if QSystemTrayIcon.isSystemTrayAvailable() and (
            execution.show_tray_icon or execution.notify_on_finish or self.window_mode
        ):
            self._make_tray()
        self.sig_choose.connect(self._on_choose)
        self.sig_progress.connect(self._on_progress)
        self.sig_step.connect(self.window.progress_page.step_result)
        self.sig_waiting.connect(self.window.progress_page.waiting)
        self.sig_notify.connect(self._on_notify)
        self.sig_reboot.connect(self._on_reboot)
        self.sig_finished.connect(self._on_finished)
        self.sig_work_done.connect(self._on_work_done)
        self.window.progress_page.minimize_requested.connect(self.window.hide)
        self.window.done_page.close_requested.connect(self._quit)

    def _make_tray(self) -> None:
        self.tray = QSystemTrayIcon(app_icon(32))
        self.tray.setToolTip(t("app.name"))
        menu = QMenu()
        show = QAction(t("ui.agent.show_progress"), menu)
        show.triggered.connect(self._show_window)
        menu.addAction(show)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda *_: self._show_window())
        self.tray.show()

    def _show_window(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _on_choose(self, pending: list[PlannedStep], done: dict[str, int], req: _Request) -> None:
        self.window.progress_page.set_steps([s for s in pending if s.kind != "finalize"])
        if not self.window_mode:
            req.value = Choice("start")
            req.event.set()
            return
        countdown = self.execution.countdown_seconds if self.execution.mode == "countdown" else None
        rename = next((s for s in pending if s.kind == "rename_computer"), None)
        page = ChoosePage(
            pending, done, countdown=countdown, default_name=None if rename is None else ""
        )

        def decided(choice: Choice) -> None:
            req.value = choice
            req.event.set()
            if choice.action == "start":
                self.window.stack.setCurrentWidget(self.window.progress_page)
            else:
                self._quit()

        page.decided.connect(decided)
        self.window.show_choose(page)
        self._show_window()

    def _on_progress(self, done: int, total: int, current: str) -> None:
        self.window.progress_page.progress(done, total, current)
        if self.tray is not None and current:
            self.tray.setToolTip(t("agent.tray_tip", done=done, total=total, current=current))

    def _on_notify(self, title: str, message: str) -> None:
        if self.tray is not None:
            self.tray.showMessage(title, message, app_icon(64), 8000)

    def _on_reboot(self, req: _Request) -> None:
        dlg = RebootDialog(self.window if self.window.isVisible() else None)
        req.value = dlg.exec() == QDialog.DialogCode.Accepted
        req.event.set()

    def _on_finished(self, summary: Summary, html: Path) -> None:
        self.finished_seen = True
        self.window.done_page.show_summary(summary, html)
        self.window.stack.setCurrentWidget(self.window.done_page)

    def _on_work_done(self) -> None:
        if self.window_mode and self.window.isVisible() and self.finished_seen:
            return  # o usuário fecha a janela
        QTimer.singleShot(self.auto_quit_ms if self.tray is not None else 0, self._quit)

    def _quit(self) -> None:
        if self.tray is not None:
            self.tray.hide()
        self.window.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()


class QtAgentUi:
    """Implementa ``AgentUi`` com janela (contagem/interativo) ou só bandeja (silencioso)."""

    def __init__(self, execution: Execution, *, auto_quit_ms: int = 9000) -> None:
        self.execution = execution
        self.auto_quit_ms = auto_quit_ms
        self._gui: _Gui | None = None

    @property
    def gui(self) -> _Gui:
        assert self._gui is not None  # noqa: S101 — só depois de host()
        return self._gui

    def host(self, work: Callable[[], int]) -> int:
        app = QApplication.instance() or QApplication([])
        assert isinstance(app, QApplication)  # noqa: S101
        app.setQuitOnLastWindowClosed(False)
        theme.apply(app)
        self._gui = _Gui(self.execution, auto_quit_ms=self.auto_quit_ms)
        result: dict[str, Any] = {}

        def runner() -> None:
            try:
                result["code"] = work()
            except BaseException as exc:  # noqa: BLE001 — repassado depois do loop do Qt
                result["error"] = exc
            finally:
                self.gui.sig_work_done.emit()

        thread = threading.Thread(target=runner, name="winkit-fase2", daemon=True)
        thread.start()
        app.exec()
        thread.join(timeout=10)
        if "error" in result:
            raise result["error"]
        return int(result.get("code", 0))

    # ---- protocolo AgentUi (chamado pela thread de trabalho)
    def choose(self, pending: list[PlannedStep], done_before_login: dict[str, int]) -> Choice:
        req = _Request()
        self.gui.sig_choose.emit(pending, done_before_login, req)
        req.event.wait()
        value: Choice = req.value
        return value

    def progress(self, done: int, total: int, current: str) -> None:
        self.gui.sig_progress.emit(done, total, current)

    def step_result(self, step_id: str, status: str, message: str | None) -> None:
        self.gui.sig_step.emit(step_id, status, message)

    def waiting(self, reason: Literal["pendrive", "network", "winget"], active: bool) -> None:
        self.gui.sig_waiting.emit(reason, active)
        if active:
            self.notify(
                t("app.name"),
                {
                    "pendrive": t("agent.reconnect_pendrive"),
                    "network": t("agent.waiting_network"),
                    "winget": t("agent.waiting_winget"),
                }[reason],
            )

    def notify(self, title: str, message: str) -> None:
        self.gui.sig_notify.emit(title, message)

    def ask_reboot(self) -> bool:
        req = _Request()
        self.gui.sig_reboot.emit(req)
        req.event.wait()
        return bool(req.value)

    def finished(self, summary: Summary, html: Path) -> None:
        self.gui.sig_finished.emit(summary, html)
