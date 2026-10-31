"""Janela principal do WinKit Studio: barra lateral agrupada + páginas (D-042)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from winkit.i18n import normalize, set_language, t, tn
from winkit.studio import preferences
from winkit.studio.controller import StudioController
from winkit.studio.ui import pages
from winkit.studio.ui.base import Page, TaskRunner
from winkit.studio.ui.pages.common import combo
from winkit.ui import theme
from winkit.ui.widgets import app_icon, button, label, symbol_icon

_SECTION_ROLE = Qt.ItemDataRole.UserRole


@dataclass(frozen=True)
class Section:
    id: str
    glyph: str
    color: str
    page: type[Page]

    @property
    def title(self) -> str:
        return t(self.page.title_key)

    def keywords(self) -> str:
        return t(f"studio.keywords.{self.id}")


@dataclass(frozen=True)
class SectionGroup:
    id: str
    sections: tuple[Section, ...]

    @property
    def title(self) -> str:
        return t(f"studio.group.{self.id}")


GROUPS: tuple[SectionGroup, ...] = (
    SectionGroup(
        "prepare",
        (
            Section("pendrive", "chip", "#8E8E93", pages.PendrivePage),
            Section("account", "pencil", "#AF52DE", pages.AccountPage),
        ),
    ),
    SectionGroup(
        "bring",
        (
            Section("apps", "download", "#007AFF", pages.AppsPage),
            Section("backups", "folder", "#34C759", pages.BackupsPage),
            Section("drivers", "chip", "#636366", pages.DriversPage),
            Section("fonts", "pencil", "#FF2D55", pages.FontsPage),
            Section("defaults", "check", "#007AFF", pages.DefaultAppsPage),
        ),
    ),
    SectionGroup(
        "system",
        (
            Section("bloat", "trash", "#FF3B30", pages.BloatPage),
            Section("tweaks", "sliders", "#5856D6", pages.TweaksPage),
            Section("energy", "bolt", "#FF9500", pages.EnergyPage),
            Section("features", "chip", "#5AC8FA", pages.FeaturesPage),
            Section("maintenance", "refresh", "#34C759", pages.MaintenancePage),
            Section("env", "sliders", "#8E8E93", pages.EnvPage),
        ),
    ),
    SectionGroup(
        "network",
        (
            Section("wifi", "dot", "#32ADE6", pages.WifiPage),
            Section("dns", "check", "#30B0C7", pages.DnsPage),
            Section("drives", "folder", "#5856D6", pages.NetworkDrivesPage),
        ),
    ),
    SectionGroup(
        "finish",
        (
            Section("execution", "dot", "#32ADE6", pages.ExecutionPage),
            Section("build", "check", "#34C759", pages.BuildPage),
            Section("live", "refresh", "#FF9500", pages.LivePage),
        ),
    ),
)


def all_sections() -> list[Section]:
    return [s for g in GROUPS for s in g.sections]


class PreferencesDialog(QDialog):
    """Idioma e tema (D-042). Aplicado ao confirmar."""

    def __init__(self, prefs: preferences.Preferences, parent: QWidget | None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("studio.prefs.title"))
        self.result_prefs = prefs
        form = QFormLayout(self)
        form.setContentsMargins(24, 20, 24, 20)
        form.setSpacing(12)
        self._lang = prefs.language
        self._theme = prefs.theme
        form.addRow(
            t("studio.prefs.language"),
            combo(
                [
                    ("auto", t("studio.lang.auto_windows")),
                    ("pt-BR", "Português (Brasil)"),
                    ("en-US", "English"),
                    ("es", "Español"),
                ],
                prefs.language,
                lambda v: setattr(self, "_lang", v),
            ),
        )
        form.addRow(
            t("studio.prefs.theme"),
            combo(
                [(m, t(f"studio.prefs.theme_{m}")) for m in ("auto", "light", "dark")],
                prefs.theme,
                lambda v: setattr(self, "_theme", v),
            ),
        )
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._ok)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _ok(self) -> None:
        self.result_prefs = preferences.Preferences.model_validate(
            {"language": self._lang, "theme": self._theme}
        )
        self.accept()


def resolve_language(choice: str, detect: Callable[[], str]) -> str:
    return normalize(detect()) if choice == "auto" else choice


class StudioWindow(QWidget):
    def __init__(
        self,
        ctl: StudioController,
        *,
        synchronous_tasks: bool = False,
        prefs_path: Path | None = None,
        detect_language: Callable[[], str] | None = None,
    ) -> None:
        super().__init__()
        self.ctl = ctl
        self.prefs_path = prefs_path
        self.detect_language = detect_language or (lambda: "pt-BR")
        self.theme_mode = "auto"
        self.setObjectName("Root")
        self.setWindowIcon(app_icon())
        self.resize(1120, 740)
        self.tasks = TaskRunner(self, synchronous=synchronous_tasks)
        self.sections = all_sections()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sidebar.setFixedWidth(260)
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
        self.version_label = label("", "Caption", wrap=False)
        names.addWidget(self.version_label)
        head.addLayout(names, 1)
        side.addLayout(head)

        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        search_box = QHBoxLayout()
        search_box.setContentsMargins(14, 0, 14, 0)
        search_box.addWidget(self.search)
        side.addLayout(search_box)

        self.nav = QListWidget()
        self.nav.setObjectName("SidebarList")
        self.nav.setIconSize(QSize(22, 22))
        self.nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setTextElideMode(Qt.TextElideMode.ElideRight)
        side.addWidget(self.nav, 1)
        self.status = label("", "Caption")
        self.status.setContentsMargins(18, 0, 18, 0)
        side.addWidget(self.status)
        foot = QHBoxLayout()
        foot.setContentsMargins(14, 0, 14, 0)
        self.prefs_button = button("", None, self.open_preferences)
        foot.addWidget(self.prefs_button)
        foot.addStretch(1)
        side.addLayout(foot)
        root.addWidget(sidebar)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.pages: list[Page] = []
        self.nav.currentRowChanged.connect(self._go)
        self._build()

    # ------------------------------------------------------------------ montagem
    def _build(self, current: str | None = None) -> None:
        """(Re)cria barra lateral e páginas no idioma atual (troca de idioma sem reiniciar)."""
        self.setWindowTitle(t("studio.window_title"))
        self.version_label.setText(t("studio.version", version=self.ctl.version()))
        self.search.setPlaceholderText(t("studio.search"))
        self.prefs_button.setText(t("studio.prefs.button"))
        self.nav.blockSignals(True)
        self.nav.clear()
        for page in self.pages:
            self.stack.removeWidget(page)
            page.hide()
            page.setParent(None)  # sai da janela já, sem esperar o deleteLater
            page.deleteLater()
        self.pages = []
        for group in GROUPS:
            header = QListWidgetItem(group.title.upper(), self.nav)
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            font = header.font()
            font.setPointSizeF(8.5)
            font.setBold(True)
            header.setFont(font)
            header.setForeground(QColor(theme.current(self.theme_mode).secondary))
            for s in group.sections:
                item = QListWidgetItem(symbol_icon(s.glyph, s.color), s.title, self.nav)
                item.setData(_SECTION_ROLE, len(self.pages))
                page = s.page(self.ctl, self.tasks)
                self.pages.append(page)
                self.stack.addWidget(page)
        self.nav.blockSignals(False)
        self._select(current or self.sections[0].id)
        self._update_status()

    def _row_of(self, index: int) -> int:
        for row in range(self.nav.count()):
            if self.nav.item(row).data(_SECTION_ROLE) == index:
                return row
        return -1

    def _select(self, section_id: str) -> None:
        index = next(i for i, s in enumerate(self.sections) if s.id == section_id)
        self.nav.setCurrentRow(self._row_of(index))
        self._go(self.nav.currentRow())

    def _go(self, row: int) -> None:
        item = self.nav.item(row) if row >= 0 else None
        index = item.data(_SECTION_ROLE) if item is not None else None
        if isinstance(index, int) and 0 <= index < len(self.pages):
            self.pages[index].refresh()
            self.stack.setCurrentIndex(index)

    def _filter(self, text: str) -> None:
        needle = text.casefold().strip()
        header: QListWidgetItem | None = None
        header_has_match = False
        for row in range(self.nav.count()):
            item = self.nav.item(row)
            index = item.data(_SECTION_ROLE)
            if not isinstance(index, int):
                if header is not None:
                    header.setHidden(not header_has_match)
                header, header_has_match = item, False
                continue
            s = self.sections[index]
            match = not needle or needle in s.title.casefold() or needle in s.keywords().casefold()
            item.setHidden(not match)
            header_has_match = header_has_match or match
        if header is not None:
            header.setHidden(not header_has_match)

    # ------------------------------------------------------------ API das páginas e dos testes
    def current_section(self) -> str:
        return self.sections[self.stack.currentIndex()].id

    def go_to(self, section_id: str) -> Page:
        self._select(section_id)
        return self.pages[self.stack.currentIndex()]

    def on_target_changed(self) -> None:
        self._update_status()
        self.pages[self.stack.currentIndex()].refresh()

    def apply_preferences(self, prefs: preferences.Preferences) -> None:
        set_language(resolve_language(prefs.language, self.detect_language))  # type: ignore[arg-type]
        app = QApplication.instance()
        self.theme_mode = prefs.theme
        if isinstance(app, QApplication):
            theme.apply(app, prefs.theme)
        self._build(self.current_section() if self.pages else None)

    def open_preferences(self) -> None:
        dialog = PreferencesDialog(preferences.load(self.prefs_path), self)
        if dialog.exec():
            preferences.save(dialog.result_prefs, self.prefs_path)
            self.apply_preferences(dialog.result_prefs)

    def _update_status(self) -> None:
        if self.ctl.target is None:
            self.status.setText(t("studio.status.no_pendrive"))
        elif self.ctl.recipe is None:
            self.status.setText(f"{self.ctl.target.description}\n{t('studio.status.no_recipe')}")
        else:
            r = self.ctl.recipe
            parts = [
                tn("studio.status.apps", len(r.selected_apps())),
                tn("studio.status.backups", len(r.selected_backups())),
                tn("studio.status.removed", len(r.bloatware.remove)),
            ]
            self.status.setText(f"{self.ctl.target.description}\n" + " · ".join(parts))
