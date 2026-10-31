"""Janela principal do WinKit Studio: barra lateral + páginas (estilo "Ajustes do Sistema")."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from winkit.studio.controller import StudioController
from winkit.studio.ui import pages
from winkit.studio.ui.base import Page, TaskRunner
from winkit.ui.widgets import app_icon, label, symbol_icon

SECTIONS: list[tuple[str, str, str, type[Page]]] = [
    ("Pendrive", "chip", "#8E8E93", pages.PendrivePage),
    ("Windows e conta", "pencil", "#AF52DE", pages.AccountPage),
    ("Aplicativos", "download", "#007AFF", pages.AppsPage),
    ("Configurações dos apps", "folder", "#34C759", pages.BackupsPage),
    ("Drivers", "chip", "#636366", pages.DriversPage),
    ("Apps pré-instalados", "trash", "#FF3B30", pages.BloatPage),
    ("Ajustes", "sliders", "#5856D6", pages.TweaksPage),
    ("Energia e atualizações", "bolt", "#FF9500", pages.EnergyPage),
    ("Primeiro login", "dot", "#32ADE6", pages.ExecutionPage),
    ("Revisar e construir", "check", "#34C759", pages.BuildPage),
]


class StudioWindow(QWidget):
    def __init__(self, ctl: StudioController, *, synchronous_tasks: bool = False) -> None:
        super().__init__()
        self.ctl = ctl
        self.setObjectName("Root")
        self.setWindowTitle("WinKit Studio")
        self.setWindowIcon(app_icon())
        self.resize(1080, 720)
        self.tasks = TaskRunner(self, synchronous=synchronous_tasks)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sidebar.setFixedWidth(250)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 18, 0, 12)
        side.setSpacing(10)
        head = QHBoxLayout()
        head.setContentsMargins(18, 0, 18, 6)
        icon = QLabel()
        icon.setPixmap(app_icon(36).pixmap(36, 36))
        head.addWidget(icon)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label("WinKit Studio", "SidebarTitle", wrap=False))
        names.addWidget(label(f"versão {ctl.version()}", "Caption", wrap=False))
        head.addLayout(names, 1)
        side.addLayout(head)

        self.nav = QListWidget()
        self.nav.setObjectName("SidebarList")
        self.nav.setIconSize(QSize(22, 22))
        self.nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        side.addWidget(self.nav, 1)
        self.status = label("", "Caption")
        self.status.setContentsMargins(18, 0, 18, 0)
        side.addWidget(self.status)
        root.addWidget(sidebar)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.pages: list[Page] = []
        for title, glyph, color, cls in SECTIONS:
            QListWidgetItem(symbol_icon(glyph, color), title, self.nav)
            page = cls(ctl, self.tasks)
            self.pages.append(page)
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self._go)
        self.nav.setCurrentRow(0)
        self._update_status()

    def _go(self, index: int) -> None:
        if 0 <= index < len(self.pages):
            self.pages[index].refresh()
            self.stack.setCurrentIndex(index)

    def go_to(self, title: str) -> Page:
        index = next(i for i, s in enumerate(SECTIONS) if s[0] == title)
        self.nav.setCurrentRow(index)
        return self.pages[index]

    def on_target_changed(self) -> None:
        self._update_status()
        self.pages[self.stack.currentIndex()].refresh()

    def _update_status(self) -> None:
        if self.ctl.target is None:
            self.status.setText("Nenhum pendrive selecionado")
        elif self.ctl.recipe is None:
            self.status.setText(f"{self.ctl.target.description}\nsem receita")
        else:
            r = self.ctl.recipe
            self.status.setText(
                f"{self.ctl.target.description}\n"
                f"{len(r.selected_apps())} apps · {len(r.selected_backups())} "
                f"configurações · {len(r.bloatware.remove)} removidos"
            )
