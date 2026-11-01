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
from winkit.i18n import t
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
        self.setWindowTitle(t("app.name"))
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
        lay.addWidget(label(t("studio.working.hint"), "Caption"))


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

    def background(self, fn: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        """Roda sem folha modal; a interface continua livre (R-59). Erros vêm em ``on_done``."""
        job = _Job(fn)
        self._jobs.append(job)

        def finish(result: object) -> None:
            if job in self._jobs:
                self._jobs.remove(job)
            on_done(result)

        job.signals.done.connect(finish)
        job.signals.failed.connect(finish)
        QThreadPool.globalInstance().start(job)


def show_error(parent: QWidget | None, exc: BaseException) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle(t("app.name"))
    box.setIconPixmap(app_icon(48).pixmap(48, 48))
    box.setText(t("studio.error.title"))
    box.setInformativeText(
        str(exc)
        if isinstance(exc, WinKitError)
        else f"{exc}\n\n{''.join(traceback.format_exception_only(exc)).strip()}"
    )
    box.exec()


class Page(QWidget):
    """Página com título grande, subtítulo e conteúdo rolável. Textos por chave (R-55)."""

    title_key = ""
    subtitle_key = ""

    def __init__(self, ctl: StudioController, tasks: TaskRunner) -> None:
        super().__init__()
        self.ctl = ctl
        self.tasks = tasks
        self._loading: set[str] = set()
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
        head.addWidget(label(t(self.title_key), "Title"))
        if self.subtitle_key:
            head.addWidget(label(t(self.subtitle_key), "Secondary"))
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
                widget.hide()  # some na hora; o deleteLater só roda no próximo ciclo
                widget.deleteLater()
            elif item.layout() is not None:
                _drop_layout(item.layout())

    def refresh(self) -> None:
        """Reconstrói o conteúdo a partir do controlador."""

    def slow(self, key: str) -> Any:
        """Dado lento do sistema (R-59): o cache, ou ``None`` enquanto carrega em segundo plano."""
        if key in self.ctl.cache:
            return self.ctl.cache[key]
        if self.tasks.synchronous:
            return self.ctl.load_slow(key)
        if key not in self._loading:
            self._loading.add(key)

            def loaded(_: object) -> None:
                self._loading.discard(key)
                if self.isVisible():
                    self.refresh()

            self.tasks.background(lambda: self.ctl.load_slow(key), loaded)
        return None

    def needs_recipe(self) -> bool:
        """Mostra o aviso e devolve ``True`` quando ainda não há receita."""
        if self.ctl.recipe is not None:
            return False
        self.content.addWidget(label(t("studio.needs_recipe"), "Secondary"))
        return True

    def save(self) -> None:
        if self.ctl.recipe is not None:
            self.ctl.save()


def _drop_layout(layout: Any) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().hide()
            item.widget().deleteLater()
        elif item.layout() is not None:
            _drop_layout(item.layout())
