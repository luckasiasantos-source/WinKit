"""Base das páginas do Studio e execução de tarefas demoradas fora da thread da interface (R-37)."""

from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from winkit.core.errors import WinKitError
from winkit.studio.controller import StudioController
from winkit.ui.widgets import app_icon, label


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(object)


class _Job(QRunnable):
    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self.fn = fn
        self.signals = _Signals()

    def run(self) -> None:
        try:
            result = self.fn()
        except Exception as exc:  # noqa: BLE001 — repassado para a interface
            self.signals.failed.emit(exc)
        else:
            self.signals.done.emit(result)


class WorkingSheet(QDialog):
    """Folha modal "Trabalhando…" com barra indeterminada."""

    def __init__(self, text: str, parent: QWidget | None) -> None:
        super().__init__(parent)
        self.setWindowTitle("WinKit")
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(12)
        lay.addWidget(label(text, "Headline"))
        bar = QProgressBar()
        bar.setRange(0, 0)
        lay.addWidget(bar)
        lay.addWidget(label("Isso pode levar alguns minutos.", "Caption"))


class TaskRunner:
    """Roda funções demoradas numa thread; ``synchronous`` executa na hora (testes)."""

    def __init__(self, parent: QWidget, *, synchronous: bool = False) -> None:
        self.parent = parent
        self.synchronous = synchronous
        self._jobs: list[_Job] = []

    def run(self, text: str, fn: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        if self.synchronous:
            try:
                result = fn()
            except Exception as exc:  # noqa: BLE001
                show_error(self.parent, exc)
                return
            on_done(result)
            return
        sheet = WorkingSheet(text, self.parent)
        job = _Job(fn)
        self._jobs.append(job)

        def finish() -> None:
            sheet.accept()
            if job in self._jobs:
                self._jobs.remove(job)

        def ok(result: object) -> None:
            finish()
            on_done(result)

        def bad(exc: object) -> None:
            finish()
            show_error(self.parent, exc if isinstance(exc, BaseException) else Exception(exc))

        job.signals.done.connect(ok)
        job.signals.failed.connect(bad)
        QThreadPool.globalInstance().start(job)
        sheet.exec()


def show_error(parent: QWidget | None, exc: BaseException) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle("WinKit")
    box.setIconPixmap(app_icon(48).pixmap(48, 48))
    box.setText("Não foi possível concluir.")
    box.setInformativeText(
        str(exc)
        if isinstance(exc, WinKitError)
        else f"{exc}\n\n{''.join(traceback.format_exception_only(exc)).strip()}"
    )
    box.exec()


class Page(QWidget):
    """Página com título grande, subtítulo e conteúdo rolável."""

    title_text = ""
    subtitle_text = ""

    def __init__(self, ctl: StudioController, tasks: TaskRunner) -> None:
        super().__init__()
        self.ctl = ctl
        self.tasks = tasks
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        holder = QWidget()
        scroll.setWidget(holder)
        self.body = QVBoxLayout(holder)
        self.body.setContentsMargins(36, 28, 44, 28)  # folga para a barra de rolagem
        self.body.setSpacing(18)
        head = QVBoxLayout()
        head.setSpacing(4)
        head.addWidget(label(self.title_text, "Title"))
        if self.subtitle_text:
            head.addWidget(label(self.subtitle_text, "Secondary"))
        self.body.addLayout(head)
        self.content = QVBoxLayout()
        self.content.setSpacing(18)
        self.body.addLayout(self.content)
        self.body.addStretch(1)

    def toolbar(self, *widgets: QWidget) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(8)
        for w in widgets:
            bar.addWidget(w)
        bar.addStretch(1)
        return bar

    def clear_content(self) -> None:
        while self.content.count():
            item = self.content.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                _drop_layout(item.layout())

    def refresh(self) -> None:
        """Reconstrói o conteúdo a partir do controlador."""

    def save(self) -> None:
        if self.ctl.recipe is not None:
            self.ctl.save()


def _drop_layout(layout: Any) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
        elif item.layout() is not None:
            _drop_layout(item.layout())
