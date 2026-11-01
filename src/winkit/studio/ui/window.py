"""Janela principal do WinKit Studio: barra lateral agrupada + páginas (D-042)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QShowEvent
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
from winkit.platform import window_style
from winkit.studio import preferences
from winkit.studio.controller import StudioController
from winkit.studio.ui import pages
from winkit.studio.ui.base import Page, TaskRunner
from winkit.studio.ui.pages.common import combo
from winkit.ui import theme
from winkit.ui.widgets import app_icon, button, label, symbol_icon

_SECTION_ROLE = Qt.ItemDataRole.UserRole
#: Seções fora do modo em etapas.
WIZARD_EXCLUDED = {"live"}


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
            Section("path", "arrow", "#FF9500", pages.PathPage),
            Section("pendrive", "chip", "#8E8E93", pages.PendrivePage),
            Section("account", "pencil", "#AF52DE", pages.AccountPage),
            Section("templates", "sliders", "#AF52DE", pages.TemplatesPage),
        ),
    ),
    SectionGroup(
        "bring",
        (
            Section("suggest", "check", "#FF9F0A", pages.SuggestionsPage),
            Section("apps", "download", "#007AFF", pages.AppsPage),
            Section("backups", "folder", "#34C759", pages.BackupsPage),
            Section("drivers", "chip", "#636366", pages.DriversPage),
            Section("fonts", "pencil", "#FF2D55", pages.FontsPage),
            Section("defaults", "check", "#007AFF", pages.DefaultAppsPage),
            Section("appearance", "pencil", "#5856D6", pages.AppearancePage),
            Section("start", "sliders", "#0A84FF", pages.StartLayoutPage),
            Section("games", "download", "#30D158", pages.GamesPage),
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
            Section("folders", "folder", "#FF9F0A", pages.UserFoldersPage),
        ),
    ),
    SectionGroup(
        "network",
        (
            Section("wifi", "dot", "#32ADE6", pages.WifiPage),
            Section("dns", "check", "#30B0C7", pages.DnsPage),
            Section("drives", "folder", "#5856D6", pages.NetworkDrivesPage),
            Section("browsers", "dot", "#FF9500", pages.BrowsersPage),
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

        main = QVBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        self.stack = QStackedWidget()
        main.addWidget(self.stack, 1)
        # modo em etapas (V3-05): convive com a barra lateral
        bar = QWidget()
        bar.setObjectName("WizardBar")
        bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        steps = QHBoxLayout(bar)
        steps.setContentsMargins(36, 10, 44, 12)
        self.back_button = button("", None, self.step_back)
        self.skip_button = button("", None, self.step_skip)
        self.next_button = button("", "Primary", self.step_next)
        self.step_label = label("", "Caption", wrap=False)
        steps.addWidget(self.back_button)
        steps.addWidget(self.skip_button)
        steps.addStretch(1)
        steps.addWidget(self.step_label)
        steps.addStretch(1)
        steps.addWidget(self.next_button)
        main.addWidget(bar)
        root.addLayout(main, 1)
        #: Etapas puladas no modo em etapas; a revisão lista (V3-05).
        self.skipped: set[str] = set()
        #: Páginas já abertas; cada uma só é criada na primeira visita (V3-01).
        self.pages: dict[int, Page] = {}
        self._current = 0
        self.nav.currentRowChanged.connect(self._go)
        self._build()

    # ------------------------------------------------------------------ montagem
    def _build(self, current: str | None = None) -> None:
        """(Re)cria barra lateral e páginas no idioma atual (troca de idioma sem reiniciar)."""
        self.setWindowTitle(t("studio.window_title"))
        self.version_label.setText(t("studio.version", version=self.ctl.version()))
        self.search.setPlaceholderText(t("studio.search"))
        self.prefs_button.setText(t("studio.prefs.button"))
        self.back_button.setText(t("studio.wizard.back"))
        self.skip_button.setText(t("studio.wizard.skip"))
        self.next_button.setText(t("studio.wizard.next"))
        self.nav.blockSignals(True)
        self.nav.clear()
        for page in self.pages.values():
            self.stack.removeWidget(page)
            page.hide()
            page.setParent(None)  # sai da janela já, sem esperar o deleteLater
            page.deleteLater()
        self.pages = {}
        index = 0
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
                item.setData(_SECTION_ROLE, index)
                index += 1
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
        if isinstance(index, int) and 0 <= index < len(self.sections):
            page = self._page(index)
            self._current = index
            page.refresh()
            self.stack.setCurrentWidget(page)
            self._update_steps()

    def _page(self, index: int) -> Page:
        if index not in self.pages:
            page = self.sections[index].page(self.ctl, self.tasks)
            self.pages[index] = page
            self.stack.addWidget(page)
        return self.pages[index]

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

    # ------------------------------------------------------------------ modo em etapas (V3-05)
    def wizard_steps(self) -> list[str]:
        """Ordem das etapas: as seções da barra lateral, menos "Aplicar neste PC" (outro fluxo)."""
        return [s.id for s in self.sections if s.id not in WIZARD_EXCLUDED]

    def _update_steps(self) -> None:
        steps = self.wizard_steps()
        current = self.current_section()
        if current not in steps:
            self.step_label.setText("")
            for b in (self.back_button, self.skip_button, self.next_button):
                b.setEnabled(False)
            return
        n = steps.index(current)
        self.step_label.setText(
            t(
                "studio.wizard.step",
                n=n + 1,
                total=len(steps),
                title=self.sections[self._current].title,
            )
        )
        self.back_button.setEnabled(n > 0)
        self.skip_button.setEnabled(n < len(steps) - 1)
        self.next_button.setEnabled(n < len(steps) - 1)

    def _move(self, delta: int) -> None:
        steps = self.wizard_steps()
        current = self.current_section()
        if current in steps:
            n = min(max(steps.index(current) + delta, 0), len(steps) - 1)
            self.go_to(steps[n])

    def step_back(self) -> None:
        self._move(-1)

    def step_skip(self) -> None:
        self.skipped.add(self.current_section())
        self._move(1)

    def step_next(self) -> None:
        self.skipped.discard(self.current_section())
        self._move(1)

    def skipped_titles(self) -> list[str]:
        return [s.title for s in self.sections if s.id in self.skipped]

    # ------------------------------------------------------------ API das páginas e dos testes
    def current_section(self) -> str:
        return self.sections[self._current].id

    def go_to(self, section_id: str) -> Page:
        self._select(section_id)
        return self.pages[self._current]

    def on_target_changed(self) -> None:
        self._update_status()
        self.pages[self._current].refresh()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._style_frame()

    def _style_frame(self) -> None:
        """Barra de título e contorno no tema do app, não no do sistema (V3-03)."""
        p = theme.current(self.theme_mode)
        window_style.style_window(
            int(self.winId()),
            dark=p.name == "dark",
            caption=p.window,
            border=p.card_border,
            text=p.text,
        )

    def apply_preferences(self, prefs: preferences.Preferences) -> None:
        set_language(resolve_language(prefs.language, self.detect_language))  # type: ignore[arg-type]
        app = QApplication.instance()
        self.theme_mode = prefs.theme
        if isinstance(app, QApplication):
            theme.apply(app, prefs.theme)
        self._build(self.current_section() if self.pages else None)
        self._style_frame()

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
