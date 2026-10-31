"""Grupo "Preparar": pendrive e Windows/conta (R-36: sem lógica de negócio)."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog, QLineEdit, QMessageBox

from winkit.core.recipe.models import Recipe
from winkit.core.recipe.validation import username_problem, validate_computer_name
from winkit.i18n import t
from winkit.i18n.format import format_size
from winkit.studio.ui.base import Page
from winkit.studio.ui.pages.common import TIME_ZONES, combo, keyboards, toggle
from winkit.ui.widgets import Card, Row, SegmentedControl, button, label, section, symbol_icon


class PendrivePage(Page):
    title_key = "studio.pendrive.title"
    subtitle_key = "studio.pendrive.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        self.content.addLayout(
            self.toolbar(
                button(t("studio.pendrive.search"), None, self.refresh),
                button(t("studio.pendrive.use_folder"), None, self._choose_folder),
            )
        )
        found = Card()
        try:
            drives = self.ctl.pendrives()
        except Exception as exc:  # noqa: BLE001 — mostra o motivo na lista
            drives = []
            found.add_row(
                Row(t("studio.pendrive.list_failed"), str(exc), icon=symbol_icon("!", "#FF9500"))
            )
        for v in drives:
            current = self.ctl.target is not None and str(self.ctl.target.root) == v.root
            use = button(
                t("studio.pendrive.in_use") if current else t("studio.pendrive.use"),
                None if current else "Primary",
                partial(self._use, v),
            )
            use.setEnabled(not current)
            found.add_row(
                Row(
                    f"{v.data_letter}  {v.disk_name}",
                    t(f"pendrive.kind_{v.kind}")
                    + " · "
                    + t(
                        "studio.pendrive.free_of",
                        fs=v.file_system,
                        free=format_size(v.free),
                        size=format_size(v.size),
                    ),
                    accessory=use,
                    icon=symbol_icon("chip", "#8E8E93"),
                )
            )
        if not found.rows:
            found.add_row(
                Row(
                    t("studio.pendrive.none"),
                    t("studio.pendrive.none_hint"),
                    icon=symbol_icon("!", "#FF9500"),
                )
            )
        self.content.addWidget(section(t("studio.pendrive.section_found"), found))
        if self.ctl.target is not None:
            info = Card()
            info.add_row(
                Row(
                    t("studio.pendrive.selected"),
                    self.ctl.target.description,
                    icon=symbol_icon("check", "#34C759"),
                )
            )
            sizes = self.ctl.sizes()
            used = " · ".join(f"{t(f'size.{k}')} {format_size(v)}" for k, v in sizes.items())
            info.add_row(
                Row(
                    t("studio.pendrive.space"),
                    t(
                        "studio.pendrive.space_detail",
                        used=used,
                        free=format_size(self.ctl.free_bytes()),
                    ),
                    icon=symbol_icon("folder", "#007AFF"),
                )
            )
            read = button(t("studio.pendrive.read_isos"), None, self._read_isos)
            info.add_row(
                Row(
                    t("studio.pendrive.isos"),
                    t("studio.pendrive.isos_hint"),
                    accessory=read,
                    icon=symbol_icon("refresh", "#5856D6"),
                )
            )
            self.content.addWidget(section(t("studio.pendrive.section_this"), info))
        warning = Card()
        warning.add_row(
            Row(
                t("studio.disclaimer.title"),
                t("studio.disclaimer.text"),
                icon=symbol_icon("!", "#FF3B30"),
            )
        )
        self.content.addWidget(section(t("studio.disclaimer.section"), warning))

    def _use(self, v: Any) -> None:
        self.ctl.open_ventoy(v)
        self.window().on_target_changed()  # type: ignore[attr-defined]

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, t("studio.pendrive.folder_dialog"))
        if folder:
            self.ctl.open_folder(Path(folder))
            self.window().on_target_changed()  # type: ignore[attr-defined]

    def _read_isos(self) -> None:
        def done(isos: list[Any]) -> None:
            card = Card()
            for iso in isos:
                sub = (
                    t(
                        "studio.pendrive.iso_detail",
                        os=iso.os_major,
                        build=iso.build,
                        arch=iso.architecture,
                        langs=", ".join(iso.languages),
                    )
                    if iso.is_windows
                    else t("studio.pendrive.not_windows_iso")
                )
                card.add_row(
                    Row(
                        iso.name,
                        sub,
                        icon=symbol_icon("download" if iso.is_windows else "minus", "#5856D6"),
                    )
                )
            if not card.rows:
                card.add_row(Row(t("studio.pendrive.no_isos")))
            self.content.addWidget(section(t("studio.pendrive.section_isos"), card))

        self.tasks.run(t("studio.pendrive.reading_isos"), self.ctl.isos, done)


class AccountPage(Page):
    title_key = "studio.account.title"
    subtitle_key = "studio.account.subtitle"

    def refresh(self) -> None:
        self.clear_content()
        r = self.ctl.recipe
        if self.ctl.target is None:
            self.content.addWidget(label(t("studio.needs_pendrive"), "Secondary"))
            return
        if r is None:
            self._create_form()
            return
        w = r.windows
        acc = Card()
        user = QLineEdit(w.account.username)
        user.editingFinished.connect(lambda: self._set_user(user.text()))
        acc.add_row(
            Row(
                t("studio.account.username"),
                t("studio.account.username_hint"),
                accessory=user,
                icon=symbol_icon("pencil", "#AF52DE"),
            )
        )
        pc = QLineEdit(w.computer_name or "")
        pc.setPlaceholderText(t("studio.account.pc_placeholder"))
        pc.setMaxLength(15)
        pc.editingFinished.connect(lambda: self._set_pc(pc.text()))
        acc.add_row(
            Row(t("studio.account.pc"), None, accessory=pc, icon=symbol_icon("chip", "#8E8E93"))
        )
        acc.add_row(
            Row(
                t("studio.account.ask_pc"),
                None,
                accessory=toggle(
                    w.computer_name_decide_at_runtime,
                    lambda v: self._set(
                        lambda r: setattr(r.windows, "computer_name_decide_at_runtime", v)
                    ),
                ),
                icon=symbol_icon("pencil", "#AF52DE"),
            )
        )
        pw = SegmentedControl(
            [
                ("empty", t("studio.account.no_password")),
                ("stored", t("studio.account.set_password")),
            ],
            w.account.password_mode,
        )
        pw.changed.connect(self._set_password_mode)
        acc.add_row(
            Row(
                t("studio.account.password"),
                t("studio.account.password_hint"),
                accessory=pw,
                icon=symbol_icon("dot", "#FF9500"),
            )
        )
        if w.account.password_mode == "stored":  # noqa: S105 — modo, não senha
            field = QLineEdit(w.account.password or "")
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.editingFinished.connect(
                lambda: self._set(
                    lambda r: setattr(r.windows.account, "password", field.text() or None)
                )
            )
            acc.add_row(
                Row(
                    t("studio.account.password_field"),
                    t("studio.account.password_readable"),
                    accessory=field,
                    icon=symbol_icon("!", "#FF3B30"),
                )
            )
        self.content.addWidget(section(t("studio.account.section_account"), acc))

        win = Card()
        ed = combo(
            [(e.id, e.name) for e in self.ctl.catalogs.editions],
            w.edition,
            lambda v: self._set(lambda r: setattr(r.windows, "edition", v)),
        )
        win.add_row(
            Row(t("studio.account.edition"), None, accessory=ed, icon=symbol_icon("W", "#007AFF"))
        )
        kb = combo(
            keyboards(),
            w.input_locale,
            lambda v: self._set(lambda r: setattr(r.windows, "input_locale", v)),
        )
        win.add_row(
            Row(t("studio.account.keyboard"), None, accessory=kb, icon=symbol_icon("K", "#5856D6"))
        )
        tz = combo(
            TIME_ZONES,
            w.time_zone,
            lambda v: self._set(lambda r: setattr(r.windows, "time_zone", v)),
        )
        win.add_row(
            Row(
                t("studio.account.time_zone"),
                None,
                accessory=tz,
                icon=symbol_icon("refresh", "#FF9500"),
            )
        )
        lang = combo(
            [
                ("auto", t("studio.lang.auto_windows")),
                ("pt-BR", "Português (Brasil)"),
                ("en-US", "English"),
                ("es", "Español"),
            ],
            r.execution.language,
            lambda v: self._set(lambda r: setattr(r.execution, "language", v)),
        )
        win.add_row(
            Row(
                t("studio.account.agent_language"),
                t("studio.account.agent_language_hint"),
                accessory=lang,
                icon=symbol_icon("dot", "#32ADE6"),
            )
        )
        os_seg = SegmentedControl(
            [("11", "Windows 11"), ("10-11", t("studio.account.os_both"))],
            "10-11" if 10 in w.target_os else "11",
        )
        os_seg.changed.connect(
            lambda v: self._set(
                lambda r: setattr(r.windows, "target_os", [10, 11] if v == "10-11" else [11])
            )
        )
        win.add_row(
            Row(
                t("studio.account.target_os"),
                None,
                accessory=os_seg,
                icon=symbol_icon("download", "#34C759"),
            )
        )
        self.content.addWidget(section(t("studio.account.section_windows"), win))

        disk = Card()
        disk.add_row(
            Row(
                t("studio.account.no_encryption"),
                t("studio.account.no_encryption_hint"),
                accessory=toggle(
                    w.prevent_device_encryption,
                    lambda v: self._set(
                        lambda r: setattr(r.windows, "prevent_device_encryption", v)
                    ),
                ),
                icon=symbol_icon("chip", "#34C759"),
            )
        )
        self.content.addWidget(section(t("studio.account.section_disk"), disk))
        self.problems = label("", "Danger")
        self.content.addWidget(self.problems)
        self._show_problems()

    def _create_form(self) -> None:
        card = Card()
        self.new_user = QLineEdit()
        self.new_user.setPlaceholderText(t("studio.account.username_placeholder"))
        card.add_row(
            Row(
                t("studio.account.username"),
                None,
                accessory=self.new_user,
                icon=symbol_icon("pencil", "#AF52DE"),
            )
        )
        self.new_pc = QLineEdit()
        self.new_pc.setPlaceholderText(t("studio.account.optional"))
        self.new_pc.setMaxLength(15)
        card.add_row(
            Row(
                t("studio.account.pc"),
                None,
                accessory=self.new_pc,
                icon=symbol_icon("chip", "#8E8E93"),
            )
        )
        self.content.addWidget(
            section(
                t("studio.account.section_new"),
                card,
                footer=t("studio.account.new_footer"),
            )
        )
        self.content.addLayout(
            self.toolbar(button(t("studio.account.create"), "Primary", self._create))
        )

    def _create(self) -> None:
        name = self.new_user.text().strip()
        problem = username_problem(name) if name else t("studio.account.name_required")
        pc = self.new_pc.text().strip() or None
        if problem or (pc and not validate_computer_name(pc)):
            QMessageBox.warning(self, t("app.name"), problem or t("studio.account.pc_invalid"))
            return
        self.ctl.create_recipe(name, pc)
        self.window().on_target_changed()  # type: ignore[attr-defined]

    def _set(self, fn: Callable[[Recipe], None]) -> None:
        if self.ctl.recipe is None:
            return
        fn(self.ctl.recipe)
        self.save()
        self._show_problems()

    def _set_user(self, value: str) -> None:
        value = value.strip()
        if value and not username_problem(value):
            self._set(lambda r: setattr(r.windows.account, "username", value))
        self._show_problems()

    def _set_pc(self, value: str) -> None:
        value = value.strip()
        if not value or validate_computer_name(value):
            self._set(lambda r: setattr(r.windows, "computer_name", value or None))
        else:
            self._show_problems(extra=t("studio.account.pc_invalid"))

    def _set_password_mode(self, mode: str) -> None:
        self._set(lambda r: setattr(r.windows.account, "password_mode", mode))
        self.refresh()

    def _show_problems(self, extra: str | None = None) -> None:
        """Só os problemas desta página, calculados direto (nunca filtrando texto traduzido)."""
        r = self.ctl.recipe
        if not hasattr(self, "problems") or r is None:
            return
        msgs = [extra] if extra else []
        problem = username_problem(r.windows.account.username)
        if problem:
            msgs.append(problem)
        name = r.windows.computer_name
        if name and not validate_computer_name(name):
            msgs.append(t("studio.account.pc_invalid"))
        account = r.windows.account
        if account.password_mode == "stored" and not account.password:  # noqa: S105
            msgs.append(t("recipe.password_missing"))
        self.problems.setText("\n".join(msgs))
