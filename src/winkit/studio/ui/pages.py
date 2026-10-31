"""Páginas do WinKit Studio (M10). Sem lógica de negócio: tudo passa pelo controlador (R-36)."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QWidget,
)

from winkit.core.recipe.models import AppItem, Recipe, TweakSelection
from winkit.core.recipe.validation import username_problem, validate_computer_name
from winkit.core.text import human_size
from winkit.studio.ui.base import Page
from winkit.ui.widgets import (
    Card,
    Row,
    SegmentedControl,
    ToggleSwitch,
    ask_pill,
    button,
    kind_icon,
    label,
    section,
    symbol_icon,
)

TIME_ZONES = [
    ("E. South America Standard Time", "Brasília (UTC−3)"),
    ("SA Western Standard Time", "Manaus (UTC−4)"),
    ("SA Pacific Standard Time", "Rio Branco (UTC−5)"),
    ("UTC-02", "Fernando de Noronha (UTC−2)"),
    ("GMT Standard Time", "Lisboa"),
    ("Eastern Standard Time", "Nova York"),
]
KEYBOARDS = [
    ("0416:00010416", "Português (Brasil ABNT2)"),
    ("0409:00020409", "Inglês EUA — Internacional"),
    ("0409:00000409", "Inglês EUA"),
    ("0816:00000816", "Português (Portugal)"),
]


def combo(
    options: list[tuple[str, str]], value: str, on_change: Callable[[str], None]
) -> QComboBox:
    c = QComboBox()
    for key, text in options:
        c.addItem(text, key)
    idx = c.findData(value)
    if idx < 0:
        c.addItem(value, value)
        idx = c.count() - 1
    c.setCurrentIndex(idx)
    c.currentIndexChanged.connect(lambda _: on_change(str(c.currentData())))
    c.setMinimumWidth(220)
    return c


def toggle(value: bool, on_change: Callable[[bool], None]) -> ToggleSwitch:
    sw = ToggleSwitch(value)
    sw.toggledByUser.connect(on_change)
    return sw


def choice_row(
    title: str,
    subtitle: str | None,
    *,
    icon_kind: str,
    selected: bool,
    on_select: Callable[[bool], None],
    ask: bool | None = None,
    on_ask: Callable[[bool], None] | None = None,
    enabled: bool = True,
) -> Row:
    acc = QWidget()
    lay = QHBoxLayout(acc)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)
    if ask is not None and on_ask is not None:
        pill = ask_pill(ask)
        pill.toggled.connect(on_ask)
        pill.setVisible(selected)
        lay.addWidget(pill)

        def both(value: bool) -> None:
            on_select(value)
            pill.setVisible(value)

        sw = toggle(selected, both)
    else:
        sw = toggle(selected, on_select)
    sw.setEnabled(enabled)
    lay.addWidget(sw)
    return Row(title, subtitle, accessory=acc, icon=kind_icon(icon_kind))


# ------------------------------------------------------------------ 1. Pendrive
class PendrivePage(Page):
    title_text = "Pendrive"
    subtitle_text = "Onde o WinKit guarda tudo. A ISO do Windows nunca é modificada."

    def refresh(self) -> None:
        self.clear_content()
        self.content.addLayout(
            self.toolbar(
                button("Procurar pendrives", None, self.refresh),
                button("Usar uma pasta…", None, self._choose_folder),
            )
        )
        found = Card()
        try:
            drives = self.ctl.pendrives()
        except Exception as exc:  # noqa: BLE001 — mostra o motivo na lista
            drives = []
            found.add_row(
                Row("Não foi possível listar os discos", str(exc), icon=symbol_icon("!", "#FF9500"))
            )
        for v in drives:
            current = self.ctl.target is not None and str(self.ctl.target.root) == v.root
            use = button(
                "Em uso" if current else "Usar",
                None if current else "Primary",
                partial(self._use, v),
            )
            use.setEnabled(not current)
            found.add_row(
                Row(
                    f"{v.data_letter}  {v.disk_name}",
                    f"{v.file_system} · {human_size(v.free)} livres de {human_size(v.size)}",
                    accessory=use,
                    icon=symbol_icon("chip", "#8E8E93"),
                )
            )
        if not found.rows:
            found.add_row(
                Row(
                    "Nenhum pendrive Ventoy encontrado",
                    "Conecte o pendrive (com o Ventoy instalado) e clique em Procurar.",
                    icon=symbol_icon("!", "#FF9500"),
                )
            )
        self.content.addWidget(section("Pendrives Ventoy", found))
        if self.ctl.target is not None:
            info = Card()
            info.add_row(
                Row(
                    "Selecionado", self.ctl.target.description, icon=symbol_icon("check", "#34C759")
                )
            )
            sizes = self.ctl.sizes()
            used = " · ".join(f"{k} {human_size(v)}" for k, v in sizes.items())
            info.add_row(
                Row(
                    "Espaço",
                    f"{used} — livre: {human_size(self.ctl.free_bytes())}",
                    icon=symbol_icon("folder", "#007AFF"),
                )
            )
            read = button("Ler ISOs", None, self._read_isos)
            info.add_row(
                Row(
                    "ISOs do Windows",
                    "Detecta versão, idioma e edições (só leitura).",
                    accessory=read,
                    icon=symbol_icon("refresh", "#5856D6"),
                )
            )
            self.content.addWidget(section("Este pendrive", info))

    def _use(self, v: Any) -> None:
        self.ctl.open_ventoy(v)
        self.window().on_target_changed()  # type: ignore[attr-defined]

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Pasta que fará o papel do pendrive")
        if folder:
            self.ctl.open_folder(Path(folder))
            self.window().on_target_changed()  # type: ignore[attr-defined]

    def _read_isos(self) -> None:
        def done(isos: list[Any]) -> None:
            card = Card()
            for iso in isos:
                sub = (
                    f"Windows {iso.os_major} · build {iso.build} · {iso.architecture} · "
                    f"{', '.join(iso.languages)}"
                    if iso.is_windows
                    else "não é uma ISO do Windows"
                )
                card.add_row(
                    Row(
                        iso.name,
                        sub,
                        icon=symbol_icon("download" if iso.is_windows else "minus", "#5856D6"),
                    )
                )
            if not card.rows:
                card.add_row(Row("Nenhuma ISO encontrada"))
            self.content.addWidget(section("ISOs", card))

        self.tasks.run("Lendo as ISOs…", self.ctl.isos, done)


# ------------------------------------------------------------------ 2. Windows e conta
class AccountPage(Page):
    title_text = "Windows e conta"
    subtitle_text = "Conta local sem conta Microsoft, idioma, edição e privacidade do disco."

    def refresh(self) -> None:
        self.clear_content()
        r = self.ctl.recipe
        if self.ctl.target is None:
            self.content.addWidget(label("Escolha o pendrive primeiro.", "Secondary"))
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
                "Nome de usuário",
                "Conta local, administradora.",
                accessory=user,
                icon=symbol_icon("pencil", "#AF52DE"),
            )
        )
        pc = QLineEdit(w.computer_name or "")
        pc.setPlaceholderText("gerado pelo Windows")
        pc.setMaxLength(15)
        pc.editingFinished.connect(lambda: self._set_pc(pc.text()))
        acc.add_row(
            Row("Nome do computador", None, accessory=pc, icon=symbol_icon("chip", "#8E8E93"))
        )
        acc.add_row(
            Row(
                "Perguntar o nome no primeiro login",
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
            [("empty", "Sem senha"), ("stored", "Definir senha")], w.account.password_mode
        )
        pw.changed.connect(self._set_password_mode)
        acc.add_row(
            Row(
                "Senha",
                "Sem senha é o recomendado; defina depois em Configurações.",
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
                    "Senha da conta",
                    "Atenção: fica legível no pendrive (DT-006).",
                    accessory=field,
                    icon=symbol_icon("!", "#FF3B30"),
                )
            )
        self.content.addWidget(section("Conta", acc))

        win = Card()
        ed = combo(
            [(e.id, e.name) for e in self.ctl.catalogs.editions],
            w.edition,
            lambda v: self._set(lambda r: setattr(r.windows, "edition", v)),
        )
        win.add_row(Row("Edição", None, accessory=ed, icon=symbol_icon("W", "#007AFF")))
        kb = combo(
            KEYBOARDS,
            w.input_locale,
            lambda v: self._set(lambda r: setattr(r.windows, "input_locale", v)),
        )
        win.add_row(Row("Teclado", None, accessory=kb, icon=symbol_icon("K", "#5856D6")))
        tz = combo(
            TIME_ZONES,
            w.time_zone,
            lambda v: self._set(lambda r: setattr(r.windows, "time_zone", v)),
        )
        win.add_row(Row("Fuso horário", None, accessory=tz, icon=symbol_icon("refresh", "#FF9500")))
        os_seg = SegmentedControl(
            [("11", "Windows 11"), ("10-11", "10 e 11")], "10-11" if 10 in w.target_os else "11"
        )
        os_seg.changed.connect(
            lambda v: self._set(
                lambda r: setattr(r.windows, "target_os", [10, 11] if v == "10-11" else [11])
            )
        )
        win.add_row(
            Row("ISOs atendidas", None, accessory=os_seg, icon=symbol_icon("download", "#34C759"))
        )
        self.content.addWidget(section("Windows", win))

        disk = Card()
        disk.add_row(
            Row(
                "Não criptografar o disco automaticamente",
                "O Windows não liga a criptografia sozinho, nem depois de entrar com "
                "conta Microsoft. O BitLocker manual continua disponível.",
                accessory=toggle(
                    w.prevent_device_encryption,
                    lambda v: self._set(
                        lambda r: setattr(r.windows, "prevent_device_encryption", v)
                    ),
                ),
                icon=symbol_icon("chip", "#34C759"),
            )
        )
        self.content.addWidget(section("Disco", disk))
        self.problems = label("", "Danger")
        self.content.addWidget(self.problems)
        self._show_problems()

    def _create_form(self) -> None:
        card = Card()
        self.new_user = QLineEdit()
        self.new_user.setPlaceholderText("ex.: Samuel")
        card.add_row(
            Row(
                "Nome de usuário",
                None,
                accessory=self.new_user,
                icon=symbol_icon("pencil", "#AF52DE"),
            )
        )
        self.new_pc = QLineEdit()
        self.new_pc.setPlaceholderText("opcional")
        self.new_pc.setMaxLength(15)
        card.add_row(
            Row(
                "Nome do computador",
                None,
                accessory=self.new_pc,
                icon=symbol_icon("chip", "#8E8E93"),
            )
        )
        self.content.addWidget(
            section(
                "Nova receita",
                card,
                footer="A receita fica no pendrive e guarda todas as escolhas.",
            )
        )
        self.content.addLayout(self.toolbar(button("Criar receita", "Primary", self._create)))

    def _create(self) -> None:
        name = self.new_user.text().strip()
        problem = username_problem(name) if name else "Informe um nome."
        pc = self.new_pc.text().strip() or None
        if problem or (pc and not validate_computer_name(pc)):
            QMessageBox.warning(self, "WinKit", problem or "Nome de computador inválido.")
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
        self._show_problems(extra=username_problem(value) if value else "Informe um nome.")

    def _set_pc(self, value: str) -> None:
        value = value.strip()
        if not value or validate_computer_name(value):
            self._set(lambda r: setattr(r.windows, "computer_name", value or None))
        else:
            self._show_problems(extra="Nome de computador inválido (até 15 letras, números e -).")

    def _set_password_mode(self, mode: str) -> None:
        self._set(lambda r: setattr(r.windows.account, "password_mode", mode))
        self.refresh()

    def _show_problems(self, extra: str | None = None) -> None:
        if not hasattr(self, "problems") or self.ctl.recipe is None:
            return
        rep = self.ctl.validation()
        msgs = [
            m
            for m in rep.errors
            if "senha" in m or "usuário" in m.lower() or "computador" in m.lower()
        ]
        if extra:
            msgs.insert(0, extra)
        self.problems.setText("\n".join(msgs))


# ------------------------------------------------------------------ 3. Apps
def _app_subtitle(a: AppItem) -> str:
    where = "por usuário" if a.scope == "user" else "para todos"
    if a.source == "winget_online":
        src = f"winget online ({a.winget_id})"
    elif a.source == "portable":
        src = "portátil (pasta copiada)"
    elif a.installer and a.installer.path:
        src = f"instalador offline · {a.installer.type}"
    else:
        src = "sem instalador — adicione um ou baixe pelo winget"
    return f"{src} · {where}"


class AppsPage(Page):
    title_text = "Aplicativos"
    subtitle_text = "Escolha o que instalar no Windows novo. Baixar deixa a instalação offline."

    def refresh(self) -> None:
        self.clear_content()
        r = self.ctl.recipe
        if r is None:
            self.content.addWidget(label("Crie a receita primeiro (Windows e conta).", "Secondary"))
            return
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        self.content.addLayout(
            self.toolbar(
                button("Ler apps deste PC", None, self._collect),
                button("Baixar marcados", "Primary", self._download),
                button("Adicionar instalador…", None, self._add_installer),
                button("App portátil…", None, self._add_portable),
            )
        )
        self.content.addWidget(self.search)
        self._rows: list[tuple[Row, AppItem]] = []
        chosen, others = Card(), Card()
        for a in sorted(r.apps, key=lambda x: (x.order, x.name.casefold())):
            row = choice_row(
                a.name,
                _app_subtitle(a),
                icon_kind="app",
                selected=a.selected,
                on_select=partial(self._set_selected, a),
                ask=a.decide_at_runtime,
                on_ask=partial(self._set_ask, a),
            )
            (chosen if a.selected else others).add_row(row)
            self._rows.append((row, a))
        n = len(r.selected_apps())
        self.content.addWidget(
            section(
                f"Marcados ({n})", chosen if chosen.rows else _empty("Nenhum app marcado ainda.")
            )
        )
        self.content.addWidget(
            section(
                "Outros apps deste PC",
                others if others.rows else _empty('Clique em "Ler apps deste PC".'),
            )
        )

    def _filter(self, text: str) -> None:
        needle = text.casefold()
        for row, a in self._rows:
            row.setVisible(not needle or needle in a.name.casefold() or needle in a.id)

    def _set_selected(self, a: AppItem, value: bool) -> None:
        a.selected = value
        self.save()

    def _set_ask(self, a: AppItem, value: bool) -> None:
        a.decide_at_runtime = value
        self.save()

    def _collect(self) -> None:
        self.tasks.run(
            "Lendo os apps instalados…", self.ctl.collect_apps, lambda added: self.refresh()
        )

    def _download(self) -> None:
        def done(results: list[Any]) -> None:
            bad = [f"• {r.app_id}: {r.message}" for r in results if not r.ok]
            ok = sum(1 for r in results if r.ok)
            QMessageBox.information(
                self,
                "WinKit",
                f"{ok} app(s) prontos para instalar offline."
                + ("\n\nNão baixados:\n" + "\n".join(bad) if bad else ""),
            )
            self.refresh()

        self.tasks.run("Baixando instaladores com o winget…", self.ctl.download_selected, done)

    def _add_installer(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Instalador", "", "Instaladores (*.exe *.msi *.msix *.msixbundle)"
        )
        if not path:
            return
        name, ok = QInputDialog.getText(self, "WinKit", "Nome do app:", text=Path(path).stem)
        if not ok or not name.strip():
            return
        item = self.ctl.add_installer(Path(path), name.strip(), None, "machine")
        if item.installer is not None and item.installer.type == "unknown":
            args, ok = QInputDialog.getText(
                self,
                "WinKit",
                "Tipo de instalador desconhecido. Argumentos para instalar em silêncio:",
            )
            if ok and args.strip():
                self.ctl.add_installer(Path(path), name.strip(), args.strip(), "machine")
        self.refresh()

    def _add_portable(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Pasta do programa portátil")
        if not folder:
            return
        exe, _ = QFileDialog.getOpenFileName(self, "Executável do programa", folder, "*.exe")
        if not exe:
            return
        name, ok = QInputDialog.getText(self, "WinKit", "Nome do app:", text=Path(exe).stem)
        if ok and name.strip():
            rel = str(Path(exe).relative_to(folder))
            self.ctl.add_portable(str(Path(folder)).replace("/", "\\"), name.strip(), rel)
            self.refresh()


def _empty(text: str) -> Card:
    c = Card()
    c.add_row(Row(text))
    return c


# ------------------------------------------------------------------ 4. Drivers
class DriversPage(Page):
    title_text = "Drivers"
    subtitle_text = "Drivers deste PC para o Windows novo (rede primeiro, para o winget funcionar)."

    def refresh(self) -> None:
        self.clear_content()
        r = self.ctl.recipe
        if r is None:
            self.content.addWidget(label("Crie a receita primeiro.", "Secondary"))
            return
        self.content.addLayout(self.toolbar(button("Ler drivers deste PC", "Primary", self._read)))
        card = Card()
        for d in sorted(r.drivers, key=lambda x: (x.priority, x.class_name)):
            card.add_row(
                choice_row(
                    f"{d.class_name} — {d.provider}",
                    f"{d.version} · {d.path}",
                    icon_kind="driver",
                    selected=d.selected,
                    on_select=partial(self._set_driver, d),
                )
            )
        self.content.addWidget(
            section("No pendrive", card if card.rows else _empty("Nenhum driver exportado ainda."))
        )

    def _set_driver(self, d: Any, value: bool) -> None:
        d.selected = value
        self.save()

    def _choose(self, cand: Any, value: bool) -> None:
        self._chosen[id(cand)] = value

    def _read(self) -> None:
        def done(cands: list[Any]) -> None:
            self._candidates = cands
            self._chosen = {id(c): c.recommended for c in cands}
            card = Card()
            for c in cands:
                card.add_row(
                    choice_row(
                        c.label,
                        f"{c.driver.provider} · {c.driver.version} · {c.driver.published_name}",
                        icon_kind="driver",
                        selected=c.recommended,
                        on_select=partial(self._choose, c),
                    )
                )
            self.content.addWidget(
                section(
                    "Neste PC",
                    card,
                    footer="Impressoras e componentes de software vêm desmarcados.",
                )
            )
            self.content.addLayout(
                self.toolbar(button("Exportar marcados para o pendrive", "Primary", self._export))
            )

        self.tasks.run("Lendo os drivers…", self.ctl.driver_candidates, done)

    def _export(self) -> None:
        chosen = [c for c in self._candidates if self._chosen.get(id(c))]
        self.tasks.run(
            "Exportando drivers…", lambda: self.ctl.export_drivers(chosen), lambda n: self.refresh()
        )


# ------------------------------------------------------------------ 5. Backups
class BackupsPage(Page):
    title_text = "Configurações dos apps"
    subtitle_text = (
        "Pastas e arquivos copiados para o pendrive e restaurados no lugar certo do "
        "Windows novo, antes do primeiro uso."
    )

    def refresh(self) -> None:
        self.clear_content()
        r = self.ctl.recipe
        if r is None:
            self.content.addWidget(label("Crie a receita primeiro.", "Secondary"))
            return
        self.content.addLayout(
            self.toolbar(
                button("Sugerir pelos apps marcados", None, self._suggest),
                button("Adicionar pasta…", None, lambda: self._add(folder=True)),
                button("Adicionar arquivo…", None, lambda: self._add(folder=False)),
                button("Capturar agora", "Primary", self._capture),
            )
        )
        card = Card()
        for b in r.backups:
            status = "capturado" if self.ctl.is_captured(b) else "ainda não capturado"
            conflict = {"merge": "mesclar", "overwrite": "sobrescrever", "skip": "pular"}[
                b.on_conflict
            ]
            sub = f"{b.template} · {conflict} · {status}"
            if b.warnings:
                sub += f"\n⚠ {b.warnings[0]}"
            row = choice_row(
                b.name,
                sub,
                icon_kind="backup",
                selected=b.selected,
                on_select=partial(self._set_flag, b, "selected"),
                ask=b.decide_at_runtime,
                on_ask=partial(self._set_flag, b, "decide_at_runtime"),
            )
            card.add_row(row)
        self.content.addWidget(
            section(
                "No pendrive",
                card if card.rows else _empty("Nenhuma pasta escolhida ainda."),
                footer="Senhas, cookies e logins (DPAPI) não "
                "funcionam em outro PC — o WinKit avisa quando encontra.",
            )
        )

    def _set_flag(self, item: Any, attr: str, value: bool) -> None:
        setattr(item, attr, value)
        self.save()

    def _add_suggestion(self, s: Any) -> None:
        self.ctl.add_suggestion(s)
        self.refresh()

    def _suggest(self) -> None:
        sugs = self.ctl.backup_suggestions()
        card = Card()
        for s in sugs:
            size = human_size(s.size) if s.exists else "não existe neste PC"
            add = button("Adicionar", None, partial(self._add_suggestion, s))
            add.setEnabled(s.exists)
            sub = f"{s.template} · {size}" + (f"\n⚠ {s.warning}" if s.warning else "")
            card.add_row(
                Row(
                    f"{s.app_name}{' (recomendado)' if s.recommended else ''}",
                    sub,
                    accessory=add,
                    icon=kind_icon("backup"),
                )
            )
        self.content.addWidget(
            section(
                "Sugestões",
                card
                if card.rows
                else _empty("Marque apps conhecidos (Discord, VS Code…) para ver sugestões."),
            )
        )

    def _add(self, *, folder: bool) -> None:
        if folder:
            path = QFileDialog.getExistingDirectory(self, "Pasta de configuração")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Arquivo de configuração")
        if not path:
            return
        literal = str(Path(path)).replace("/", "\\")
        _, warning = self.ctl.add_backup(literal, Path(path).name, "merge", False)
        if warning:
            QMessageBox.information(self, "WinKit", warning)
        self.refresh()

    def _capture(self) -> None:
        def done(rep: Any) -> None:
            lines = [f"{'✓' if i.ok else '✗'} {i.backup_id}: {i.message}" for i in rep.items]
            QMessageBox.information(
                self, "WinKit", "\n".join([*rep.notes, *lines]) or "Nada a capturar."
            )
            self.refresh()

        self.tasks.run("Copiando para o pendrive (com cópia de sombra)…", self.ctl.capture, done)


# ------------------------------------------------------------------ 6. Bloatware
class BloatPage(Page):
    title_text = "Apps pré-instalados"
    subtitle_text = "Remova o que não usa. Os itens bloqueados quebrariam o Windows ou o winget."

    def refresh(self) -> None:
        self.clear_content()
        r = self.ctl.recipe
        if r is None:
            self.content.addWidget(label("Crie a receita primeiro.", "Secondary"))
            return
        opts = Card()
        opts.add_row(
            Row(
                "Impedir que voltem com atualizações",
                None,
                accessory=toggle(
                    r.bloatware.block_reinstall, lambda v: self._opt("block_reinstall", v)
                ),
                icon=symbol_icon("minus", "#FF3B30"),
            )
        )
        opts.add_row(
            Row(
                "Bloquear apps sugeridos (Candy Crush, TikTok…)",
                None,
                accessory=toggle(
                    r.bloatware.disable_consumer_content,
                    lambda v: self._opt("disable_consumer_content", v),
                ),
                icon=symbol_icon("minus", "#FF9500"),
            )
        )
        self.content.addWidget(section("", opts))
        chosen = set(r.bloatware.remove)
        for risk, title, footer in (
            ("safe", "Seguros", None),
            ("caution", "Com cuidado", "Cada item mostra o que deixa de funcionar."),
            ("blocked", "Bloqueados", None),
        ):
            card = Card()
            for b in self.ctl.catalogs.bloatware:
                if b.risk != risk or not any(o in r.windows.target_os for o in b.windows.os):
                    continue
                sub = b.side_effect or b.reason
                card.add_row(
                    choice_row(
                        b.name,
                        sub,
                        icon_kind="bloat",
                        selected=b.id in chosen,
                        enabled=risk != "blocked",
                        on_select=partial(self._toggle, b.id),
                    )
                )
            self.content.addWidget(section(title, card, footer=footer))

    def _opt(self, name: str, value: bool) -> None:
        assert self.ctl.recipe is not None  # noqa: S101
        setattr(self.ctl.recipe.bloatware, name, value)
        self.save()

    def _toggle(self, pkg: str, value: bool) -> None:
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        items = [x for x in r.bloatware.remove if x != pkg]
        if value:
            items.append(pkg)
        r.bloatware.remove = items
        self.save()


# ------------------------------------------------------------------ 7. Ajustes
class TweaksPage(Page):
    title_text = "Ajustes"
    subtitle_text = "Aplicados no perfil padrão: sua conta já nasce configurada."
    HIDDEN: frozenset[str] = frozenset(
        {
            "system.prevent_device_encryption",
            "system.wu_no_driver_replacement",
            "system.consumer_content",
        }
    )

    def refresh(self) -> None:
        self.clear_content()
        r = self.ctl.recipe
        if r is None:
            self.content.addWidget(label("Crie a receita primeiro.", "Secondary"))
            return
        selected = {t.id: t for t in r.tweaks}
        for cat, title in (
            ("privacy", "Privacidade"),
            ("visual", "Aparência"),
            ("system", "Sistema"),
        ):
            card = Card()
            for tw in self.ctl.catalogs.tweaks:
                if tw.category != cat or tw.id in self.HIDDEN:
                    continue
                sel = selected.get(tw.id)
                card.add_row(
                    choice_row(
                        tw.title + (" ⚠" if tw.risk == "caution" else ""),
                        tw.description,
                        icon_kind="tweak",
                        selected=bool(sel and sel.enabled),
                        on_select=partial(self._set_enabled, tw.id),
                        ask=bool(sel and sel.decide_at_runtime),
                        on_ask=partial(self._set_tweak_ask, tw.id),
                    )
                )
            self.content.addWidget(section(title, card))

    def _set_enabled(self, tweak_id: str, value: bool) -> None:
        self._set(tweak_id, enabled=value)

    def _set_tweak_ask(self, tweak_id: str, value: bool) -> None:
        self._set(tweak_id, decide_at_runtime=value)

    def _set(self, tweak_id: str, **changes: bool) -> None:
        r = self.ctl.recipe
        assert r is not None  # noqa: S101
        sel = next((t for t in r.tweaks if t.id == tweak_id), None)
        if sel is None:
            sel = TweakSelection(id=tweak_id, enabled=False)
            r.tweaks.append(sel)
        for k, v in changes.items():
            setattr(sel, k, v)
        self.save()


# ------------------------------------------------------------------ 8. Energia e atualizações
class EnergyPage(Page):
    title_text = "Energia e atualizações"

    def refresh(self) -> None:
        self.clear_content()
        r = self.ctl.recipe
        if r is None:
            self.content.addWidget(label("Crie a receita primeiro.", "Secondary"))
            return
        tri = [("keep", "Não mexer"), ("on", "Ligada"), ("off", "Desligada")]

        def tri_value(v: bool | None) -> str:
            return "keep" if v is None else ("on" if v else "off")

        def from_tri(v: str) -> bool | None:
            return None if v == "keep" else v == "on"

        pw = Card()
        pw.add_row(
            Row(
                "Plano de energia",
                None,
                accessory=combo(
                    [
                        ("unchanged", "Não mexer"),
                        ("balanced", "Equilibrado"),
                        ("high_performance", "Alto desempenho"),
                        ("ultimate", "Desempenho máximo"),
                    ],
                    r.power.scheme,
                    lambda v: self._set(lambda r: setattr(r.power, "scheme", v)),
                ),
                icon=symbol_icon("bolt", "#FF9500"),
            )
        )
        hib = SegmentedControl(tri, tri_value(r.power.hibernate))
        hib.changed.connect(
            lambda v: self._set(lambda r: setattr(r.power, "hibernate", from_tri(v)))
        )
        pw.add_row(Row("Hibernação", None, accessory=hib, icon=symbol_icon("bolt", "#FF9500")))
        fs = SegmentedControl(tri, tri_value(r.power.fast_startup))
        fs.changed.connect(
            lambda v: self._set(lambda r: setattr(r.power, "fast_startup", from_tri(v)))
        )
        pw.add_row(
            Row("Inicialização rápida", None, accessory=fs, icon=symbol_icon("bolt", "#FF9500"))
        )
        self.content.addWidget(section("Energia", pw))

        up = Card()
        u = r.updates
        for attr, title, sub in (
            (
                "windows_update_after_install",
                "Rodar o Windows Update no fim",
                "Última etapa da configuração.",
            ),
            ("during_setup", "Atualizar durante a instalação", "Deixa a instalação mais lenta."),
            ("include_drivers_from_windows_update", "Incluir drivers do Windows Update", None),
            (
                "block_wu_driver_replacement",
                "Não deixar o Windows Update trocar seus drivers",
                None,
            ),
        ):
            up.add_row(
                Row(
                    title,
                    sub,
                    accessory=toggle(
                        getattr(u, attr),
                        partial(self._set_update, attr),
                    ),
                    icon=kind_icon("windows_update"),
                )
            )
        self.content.addWidget(section("Atualizações", up))

    def _set(self, fn: Callable[[Recipe], None]) -> None:
        if self.ctl.recipe is not None:
            fn(self.ctl.recipe)
            self.save()

    def _set_update(self, attr: str, value: bool) -> None:
        if self.ctl.recipe is not None:
            setattr(self.ctl.recipe.updates, attr, value)
            self.save()


# ------------------------------------------------------------------ 9. Execução
class ExecutionPage(Page):
    title_text = "Primeiro login"
    subtitle_text = "Como o WinKit termina a configuração depois que o Windows inicia."

    def refresh(self) -> None:
        self.clear_content()
        r = self.ctl.recipe
        if r is None:
            self.content.addWidget(label("Crie a receita primeiro.", "Secondary"))
            return
        ex = r.execution
        card = Card()
        mode = SegmentedControl(
            [("silent", "Silencioso"), ("countdown", "Contagem"), ("interactive", "Interativo")],
            ex.mode,
        )
        mode.changed.connect(lambda v: self._set("mode", v))
        card.add_row(
            Row(
                "Ao iniciar",
                {
                    "silent": "Sem janelas: tudo em segundo plano, aviso no final.",
                    "countdown": "Mostra o que vai fazer e começa sozinho após a contagem.",
                    "interactive": "Mostra o que vai fazer e espera você clicar em Iniciar.",
                }[ex.mode],
                accessory=mode,
                icon=symbol_icon("dot", "#007AFF"),
            )
        )
        spin = QSpinBox()
        spin.setRange(5, 600)
        spin.setSuffix(" s")
        spin.setValue(ex.countdown_seconds)
        spin.valueChanged.connect(lambda v: self._set("countdown_seconds", int(v), refresh=False))
        spin.setEnabled(ex.mode == "countdown")
        card.add_row(
            Row("Contagem regressiva", None, accessory=spin, icon=symbol_icon("refresh", "#007AFF"))
        )
        for attr, title in (
            ("show_tray_icon", "Ícone de progresso na bandeja"),
            ("notify_on_finish", "Notificar ao terminar"),
            ("desktop_summary_shortcut", "Atalho do resumo na área de trabalho"),
        ):
            card.add_row(
                Row(
                    title,
                    None,
                    accessory=toggle(getattr(ex, attr), partial(self._set_flag, attr)),
                    icon=symbol_icon("check", "#34C759"),
                )
            )
        card.add_row(
            Row(
                "Quando precisar reiniciar",
                None,
                accessory=combo(
                    [
                        ("ask", "Perguntar"),
                        ("auto_if_idle", "Reiniciar se eu estiver ausente"),
                        ("never", "Nunca — eu reinicio"),
                    ],
                    ex.reboot_policy,
                    lambda v: self._set("reboot_policy", v, refresh=False),
                ),
                icon=symbol_icon("refresh", "#FF9500"),
            )
        )
        self.content.addWidget(section("", card))

    def _set(self, attr: str, value: Any, *, refresh: bool = True) -> None:
        if self.ctl.recipe is not None:
            setattr(self.ctl.recipe.execution, attr, value)
            self.save()
            if refresh:
                self.refresh()

    def _set_flag(self, attr: str, value: bool) -> None:
        self._set(attr, value, refresh=False)


# ------------------------------------------------------------------ 10. Construir
class BuildPage(Page):
    title_text = "Revisar e construir"
    subtitle_text = "Confira o plano e prepare o pendrive."

    def refresh(self) -> None:
        self.clear_content()
        r = self.ctl.recipe
        if r is None:
            self.content.addWidget(label("Crie a receita primeiro.", "Secondary"))
            return
        rep = self.ctl.validation()
        check = Card()
        if rep.ok and not rep.warnings:
            check.add_row(Row("Receita sem problemas", icon=symbol_icon("check", "#34C759")))
        for e in rep.errors:
            check.add_row(Row(e, icon=symbol_icon("cross", "#FF3B30")))
        for w in rep.warnings:
            check.add_row(Row(w, icon=symbol_icon("!", "#FF9500")))
        self.content.addWidget(section("Verificação", check))
        if rep.ok:
            plan = self.ctl.plan()
            for phase, title in ((1, "Antes do login"), (2, "Depois do login")):
                card = Card()
                for s in plan.phase(phase):
                    extra = " · perguntar" if s.user_choice else ""
                    extra += " · internet" if s.needs_network else ""
                    card.add_row(Row(s.title, extra.strip(" ·") or None, icon=kind_icon(s.kind)))
                self.content.addWidget(section(f"{title} ({len(plan.phase(phase))})", card))
        build = button("Construir pendrive", "Primary", self._build)
        build.setEnabled(rep.ok)
        self.content.addLayout(
            self.toolbar(build, button("Validar pendrive", None, self._validate))
        )
        self.result = label("", "Secondary")
        self.content.addWidget(self.result)

    def _build(self) -> None:
        def done(rep: Any) -> None:
            lines = [
                f"Modelos: {len(rep.templates)} · ISOs: {len(rep.isos)} · arquivos no "
                f"manifesto: {rep.manifest_files}"
            ]
            lines += [f"⚠ {w}" for w in rep.warnings]
            self.refresh()
            self.result.setText("Pendrive pronto.\n" + "\n".join(lines))

        self.tasks.run("Preparando o pendrive…", self.ctl.build, done)

    def _validate(self) -> None:
        def done(rep: Any) -> None:
            text = "Tudo certo." if rep.ok else "Problemas:\n" + "\n".join(rep.problems)
            if rep.warnings:
                text += "\nAvisos:\n" + "\n".join(rep.warnings)
            self.result.setText(text)

        self.tasks.run("Conferindo o pendrive…", self.ctl.validate_pendrive, done)
