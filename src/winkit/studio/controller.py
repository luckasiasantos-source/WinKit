"""Fachada do WinKit Studio sem Qt (R-36): a GUI só chama estes métodos.

Usa exatamente os mesmos serviços e funções da linha de comando.
"""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from winkit import __version__
from winkit.agent.live import LiveOptions, LiveResult, run_live
from winkit.agent.phases import Runtime
from winkit.builder import target as targets
from winkit.builder.build import (
    BuildOptions,
    BuildReport,
    build,
    ensure_marker,
    load_profile_recipe,
    payload_sizes,
    save_profile_recipe,
)
from winkit.builder.isos import scan_isos
from winkit.builder.validate import PendriveReport, validate_pendrive
from winkit.collector import apps as app_collector
from winkit.collector import associations as assoc_collector
from winkit.collector import backups as backup_collector
from winkit.collector import browsers as browser_collector
from winkit.collector import drivers as driver_collector
from winkit.collector import env as env_collector
from winkit.collector import features as feature_collector
from winkit.collector import fonts as font_collector
from winkit.collector import games as games_collector
from winkit.collector import netdrives as netdrive_collector
from winkit.collector import personal as personal_collector
from winkit.collector import start_layout as start_collector
from winkit.collector import user_folders as folders_collector
from winkit.collector import wifi as wifi_collector
from winkit.core import layout
from winkit.core.browsers import suggested
from winkit.core.catalog.loader import default_catalogs
from winkit.core.catalog.models import AssociationGroup, Catalogs
from winkit.core.errors import RecipeError, WinKitError
from winkit.core.isos import IsoInfo
from winkit.core.live import LivePreview
from winkit.core.planner.models import Plan, PlanContext, StepKind
from winkit.core.planner.planner import plan
from winkit.core.presets import PresetResult, apply_preset, preview_preset
from winkit.core.recipe.io import new_recipe
from winkit.core.recipe.models import (
    AppItem,
    BackupItem,
    BrowserConfig,
    BrowserExtension,
    ConflictPolicy,
    EnvPathEntry,
    EnvVar,
    ExtraAccount,
    FontItem,
    NetworkDrive,
    Recipe,
    Scope,
    WifiNetwork,
)
from winkit.core.recipe.validation import ValidationReport, username_problem, validate_recipe
from winkit.core.user_folders import ORDER, default_folders
from winkit.core.volumes import VolumeInfo
from winkit.core.volumes import ref_for as volume_ref
from winkit.core.volumes import resolve as resolve_volume
from winkit.core.winget_manifest import split_args
from winkit.i18n import current_language, t
from winkit.i18n.format import format_size
from winkit.platform import hosts
from winkit.platform.environment import WindowsEnvironment
from winkit.platform.services import Services
from winkit.platform.vss import PendingSnapshots


def windows_build() -> int | None:
    return WindowsEnvironment().windows_build()


def _studio_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".cache") / "WinKit"


def default_agent_source() -> Path | None:
    if getattr(sys, "frozen", False):
        candidate = Path(sys.executable).resolve().parent.parent / "winkit-agent"
        if (candidate / layout.AGENT_EXE_NAME).is_file():
            return candidate
    return None


def _real_agent_runtime() -> Runtime:  # pragma: no cover — só no Windows
    from winkit.agent.main import build_runtime  # noqa: PLC0415

    return build_runtime()


@dataclass
class StudioController:
    services: Services
    #: Catálogos fixos (testes); ``None`` = os empacotados, no idioma atual (D-030).
    catalogs_override: Catalogs | None = None
    clock: Callable[[], datetime] = field(default=lambda: datetime.now(UTC))
    profile_id: str = "padrao"
    target: targets.Target | None = None
    recipe: Recipe | None = None
    agent_source: Path | None = field(default_factory=default_agent_source)
    #: Monta o Agente para "aplicar neste PC" (os testes passam um com dublês).
    agent_runtime: Callable[[], Runtime] = field(default=_real_agent_runtime)

    # ------------------------------------------------------------------ pendrive
    @property
    def catalogs(self) -> Catalogs:
        return self.catalogs_override or default_catalogs()

    def pendrives(self) -> list[targets.AnyDrive]:
        return targets.list_targets(self.services.disks, self.services.volume_root)

    def open_ventoy(self, v: targets.AnyDrive) -> None:
        self._open(targets.from_drive(v))

    def open_folder(self, folder: Path) -> None:
        self._open(targets.from_folder(folder))

    def _open(self, tgt: targets.Target) -> None:
        self.target = tgt
        try:
            self.recipe = load_profile_recipe(tgt.root, self.profile_id)
        except RecipeError:
            self.recipe = None

    @property
    def root(self) -> Path:
        if self.target is None:
            raise WinKitError("nenhum pendrive selecionado")
        return self.target.root

    def require_recipe(self) -> Recipe:
        if self.recipe is None:
            raise WinKitError("crie a receita primeiro (página Windows e conta)")
        return self.recipe

    def create_recipe(self, username: str, computer_name: str | None) -> Recipe:
        marker = ensure_marker(self.root, self.clock())
        recipe = new_recipe(
            pendrive_id=marker.pendrive_id,
            username=username,
            profile_id=self.profile_id,
            source_pc=os.environ.get("COMPUTERNAME"),
            now=self.clock(),
            regional=self.services.regional(),
        )
        recipe.windows.computer_name = computer_name or None
        self.recipe = recipe
        self.save()
        return recipe

    def save(self) -> None:
        recipe = self.require_recipe()
        recipe.meta.updated_at = self.clock()
        save_profile_recipe(self.root, recipe)

    def isos(self) -> list[IsoInfo]:
        infos, _ = scan_isos(self.root, self.services.disks, _studio_dir() / "iso-cache.json")
        return infos

    def free_bytes(self) -> int:
        return targets.from_folder(self.root).free if self.target else 0

    def sizes(self) -> dict[str, int]:
        return payload_sizes(self.root, self.profile_id)

    # ------------------------------------------------------------------ apps
    def collect_apps(self, *, include_redist: bool = False) -> list[AppItem]:
        recipe = self.require_recipe()
        apps = app_collector.collect_inventory(
            self.services.inventory, self.services.winget, self.catalogs
        )
        added = app_collector.add_inventory(
            recipe, apps, self.catalogs, include_redist=include_redist
        )
        self.save()
        return added

    def download_selected(self) -> list[app_collector.DownloadResult]:
        recipe = self.require_recipe()
        out = []
        for item in recipe.selected_apps():
            if item.source == "winget_online" and item.winget_source == "winget":
                out.append(
                    app_collector.download_app(
                        self.services.winget,
                        self.root,
                        item,
                        self.catalogs,
                        free_bytes=self.free_bytes(),
                    )
                )
        self.save()
        return out

    def add_installer(self, file: Path, name: str, args: str | None, scope: Scope) -> AppItem:
        item = app_collector.add_local_installer(
            self.root,
            self.require_recipe(),
            file,
            name=name,
            catalogs=self.catalogs,
            args=split_args(args) if args else None,
            scope=scope,
        )
        self.save()
        return item

    def add_portable(self, folder: str, name: str, exe: str) -> AppItem:
        app, _ = backup_collector.add_portable_app(
            self.require_recipe(),
            self.catalogs,
            literal_folder=folder,
            old_folders=self.old_folders(),
            name=name,
            exe=exe,
            windows_dir=self.services.folders.windows_dir(),
        )
        self.save()
        return app

    # ------------------------------------------------------------------ drivers
    def driver_candidates(self) -> list[driver_collector.DriverCandidate]:
        return driver_collector.list_candidates(self.services.drivers, self.catalogs)

    def export_drivers(self, chosen: list[driver_collector.DriverCandidate]) -> int:
        added = driver_collector.export_drivers(
            self.services.drivers, chosen, root=self.root, recipe=self.require_recipe()
        )
        self.save()
        return len(added)

    # ------------------------------------------------------------------ backups
    def old_folders(self) -> dict[str, str]:
        f = self.services.folders
        return {**f.machine(), **f.current_user()}

    def backup_suggestions(self) -> list[backup_collector.Suggestion]:
        return backup_collector.suggest(
            self.require_recipe(), self.catalogs, self.old_folders(), self.services.volume_root
        )

    def add_suggestion(self, s: backup_collector.Suggestion) -> BackupItem:
        item = backup_collector.add_suggestion(self.require_recipe(), self.catalogs, s)
        self.save()
        return item

    def add_backup(
        self, literal: str, name: str, conflict: ConflictPolicy, decide: bool
    ) -> tuple[BackupItem, str | None]:
        local = backup_collector.local_source(
            self.services.volume_root(literal[:2].upper()), literal
        )
        item, warning = backup_collector.add_backup(
            self.require_recipe(),
            self.catalogs,
            name=name,
            literal=literal,
            old_folders=self.old_folders(),
            windows_dir=self.services.folders.windows_dir(),
            kind="file" if local.is_file() else "folder",
            on_conflict=conflict,
            decide_at_runtime=decide,
        )
        self.save()
        return item, warning

    def remove_backup(self, backup_id: str) -> None:
        recipe = self.require_recipe()
        item = recipe.backup(backup_id)
        recipe.backups = [b for b in recipe.backups if b.id != backup_id]
        if item is not None:
            folder = layout.payload(self.root, item.data_path).parent
            if folder.is_dir() and folder.parent.name == "Backups":
                shutil.rmtree(folder)
        self.save()

    def is_captured(self, item: BackupItem) -> bool:
        return layout.payload(self.root, item.data_path).exists()

    def capture(
        self, only: set[str] | None = None, *, use_vss: bool = True
    ) -> backup_collector.CaptureReport:
        studio = _studio_dir()
        report = backup_collector.capture(
            self.root,
            self.require_recipe(),
            self.catalogs,
            copier=self.services.copier,
            vss=self.services.vss,
            pending=PendingSnapshots(studio / "vss-pendentes.json"),
            old_folders=self.old_folders(),
            link_base=studio,
            free_bytes=self.free_bytes(),
            use_vss=use_vss,
            only=only,
            volume_root=self.services.volume_root,
            now=self.clock,
        )
        self.save()
        return report

    # ------------------------------------------------------------------ construir
    def validation(self) -> ValidationReport:
        return validate_recipe(self.require_recipe(), self.catalogs)

    def plan(self, os_major: int = 11) -> Plan:
        return plan(self.require_recipe(), self.catalogs, PlanContext(os_major=os_major))

    # ------------------------------------------------------------------ Wi-Fi (V2-02)
    def collect_wifi(self) -> list[WifiNetwork]:
        recipe = self.require_recipe()
        if self.services.wifi is None:
            return []
        added = wifi_collector.collect_wifi(self.services.wifi, self.root, recipe)
        self.save()
        return added

    def read_features(self) -> list[str]:
        """Marca os recursos do Windows ligados neste PC (V2-08); devolve os novos."""
        recipe = self.require_recipe()
        if self.services.features is None:
            return []
        added = feature_collector.add_enabled_here(self.services.features, self.catalogs, recipe)
        if added:
            self.save()
        return added

    def set_feature(self, feature_id: str, enabled: bool) -> None:
        feature_collector.set_feature(self.require_recipe(), feature_id, enabled)
        self.save()

    def collect_drives(self) -> list[NetworkDrive]:
        """Unidades de rede mapeadas neste PC (V2-17); devolve as novas."""
        recipe = self.require_recipe()
        if self.services.registry is None:
            return []
        added = netdrive_collector.collect_drives(self.services.registry, recipe)
        if added:
            self.save()
        return added

    def add_drive(self, letter: str, path: str) -> NetworkDrive:
        """``ValueError`` (do pydantic) se a letra ou o caminho forem inválidos."""
        drive = netdrive_collector.add_drive(self.require_recipe(), letter, path)
        self.save()
        return drive

    def collect_env(self) -> tuple[list[EnvVar], list[EnvPathEntry]]:
        """Variáveis e pastas do PATH deste PC que não são padrão do Windows (V2-22)."""
        recipe = self.require_recipe()
        if self.services.registry is None:
            return [], []
        f = self.services.folders
        found = env_collector.collect_env(
            self.services.registry,
            recipe,
            self.catalogs.protected_env,
            {**f.machine(), **f.current_user()},
            f.windows_dir(),
        )
        if found[0] or found[1]:
            self.save()
        return found

    def collect_fonts(self) -> tuple[list[FontItem], list[str]]:
        """Fontes instaladas neste PC (V2-07), desmarcadas; nada é copiado ainda."""
        recipe = self.require_recipe()
        if self.services.registry is None:
            return [], []
        found = font_collector.collect_fonts(
            self.services.registry,
            self.services.folders.windows_dir(),
            self.services.volume_root,
            recipe,
        )
        if found[0]:
            self.save()
        return found

    def select_font(self, font_id: str, selected: bool) -> None:
        """Ao marcar, copia o arquivo da fonte para o pendrive."""
        font_collector.select_font(
            self.root, self.require_recipe(), font_id, selected, self.services.volume_root
        )
        self.save()

    def collect_default_apps(self) -> int:
        """Exporta os apps padrão deste PC (V2-05); devolve quantas associações leu."""
        recipe = self.require_recipe()
        if self.services.associations is None:
            return 0
        items = assoc_collector.collect_associations(
            self.services.associations, self.root, recipe, self.catalogs
        )
        self.save()
        return len(items)

    def default_app_rows(self) -> list[tuple[AssociationGroup, str | None]]:
        return assoc_collector.group_rows(self.root, self.require_recipe(), self.catalogs)

    def set_default_app_group(self, group_id: str, selected: bool) -> None:
        assoc_collector.set_group(self.require_recipe(), group_id, selected)
        self.save()

    def collect_personal(self) -> personal_collector.PersonalReport:
        """Aparência deste PC (V2-06): valores validados e papel de parede."""
        recipe = self.require_recipe()
        if self.services.registry is None:
            return personal_collector.PersonalReport()
        report = personal_collector.collect_personal(
            self.services.registry,
            self.root,
            recipe,
            self.catalogs,
            appdata=self.services.folders.current_user()["APPDATA"],
            volume_root=self.services.volume_root,
        )
        self.save()
        return report

    def wallpaper_path(self) -> Path | None:
        rel = self.require_recipe().personal.wallpaper_file
        path = layout.payload(self.root, rel) if rel else None
        return path if path is not None and path.is_file() else None

    def set_personal_group(self, group_id: str, selected: bool) -> None:
        personal_collector.set_group(self.require_recipe(), group_id, selected)
        self.save()

    def collect_browsers(self) -> list[BrowserConfig]:
        """Navegadores e extensões deste PC (V2-12). Senhas e cookies nunca são lidos."""
        f = self.services.folders
        found = browser_collector.collect_browsers(
            self.require_recipe(),
            self.catalogs,
            {**f.machine(), **f.current_user()},
            self.services.volume_root,
        )
        self.save()
        return found

    def add_browser(self, browser_id: str) -> None:
        recipe = self.require_recipe()
        if not any(b.id == browser_id for b in recipe.browsers):
            recipe.browsers = [*recipe.browsers, BrowserConfig(id=browser_id)]
            self.save()

    def suggested_extensions(self, browser_id: str) -> list[tuple[str, str, str | None]]:
        entry = self.catalogs.browser(browser_id)
        return suggested(entry, self.catalogs) if entry else []

    def add_browser_extension(self, browser_id: str, store_id: str) -> None:
        cfg = next(b for b in self.require_recipe().browsers if b.id == browser_id)
        for sid, name, slug in self.suggested_extensions(browser_id):
            if sid == store_id and not any(e.id == sid for e in cfg.extensions):
                cfg.extensions = [*cfg.extensions, BrowserExtension(id=sid, name=name, slug=slug)]
        self.save()

    def collect_start_layout(self) -> tuple[int, list[str]]:
        """Fixados do Iniciar e da barra deste PC (V2-04)."""
        f = self.services.folders
        result = start_collector.collect_start_layout(
            self.require_recipe(),
            self.root,
            {**f.machine(), **f.current_user()},
            self.services.volume_root,
            build=windows_build(),
        )
        self.save()
        return result

    # ---- contas extras (V2-11)
    def add_extra_account(self, username: str, *, admin: bool, password_mode: str) -> str | None:
        """Devolve o problema (texto) ou ``None`` se a conta entrou na receita."""
        recipe = self.require_recipe()
        problem = username_problem(username)
        taken = {recipe.windows.account.username.casefold()}
        taken |= {a.username.casefold() for a in recipe.windows.extra_accounts}
        if problem is None and username.casefold() in taken:
            problem = t("recipe.account_duplicate", name=username)
        if problem:
            return problem
        account = ExtraAccount(
            username=username,
            group="administrators" if admin else "users",
            password_mode=password_mode,
        )
        recipe.windows.extra_accounts = [*recipe.windows.extra_accounts, account]
        self.save()
        return None

    def remove_extra_account(self, username: str) -> None:
        recipe = self.require_recipe()
        recipe.windows.extra_accounts = [
            a for a in recipe.windows.extra_accounts if a.username != username
        ]
        self.save()

    def collect_games(self) -> games_collector.GamesReport:
        """Bibliotecas da Steam e jogos da Epic em outros discos (V2-13)."""
        recipe = self.require_recipe()
        if self.services.registry is None:
            return games_collector.GamesReport()
        vols = self.all_volumes()
        recipe.meta.source_system_volume = folders_collector.system_serial(vols)
        report = games_collector.collect_games(
            self.services.registry,
            self.root,
            recipe,
            vols,
            machine=self.services.folders.machine(),
            volume_root=self.services.volume_root,
        )
        self.save()
        return report

    # ---- pastas do usuário em outro disco (V2-14)
    def all_volumes(self) -> list[VolumeInfo]:
        return self.services.volumes.volumes() if self.services.volumes else []

    def data_volumes(self) -> list[VolumeInfo]:
        """Volumes que não são o do sistema (o C: será formatado)."""
        return [v for v in self.all_volumes() if not v.is_system and v.letter]

    @staticmethod
    def volume_label(v: VolumeInfo) -> str:
        name = v.label or t("studio.folders.no_label")
        free = t("studio.folders.free", size=format_size(v.free))
        return f"{name} ({v.letter}:) · {format_size(v.size)} · {free}"

    def user_folders_base(self) -> str:
        uf = self.require_recipe().user_folders
        first = next(iter(uf.folders.values()), None)
        return (
            first.rsplit("\\", 1)[0]
            if first and "\\" in first
            else t("studio.folders.default_base")
        )

    def user_folder_rows(self) -> list[tuple[str, str]]:
        uf = self.require_recipe().user_folders
        base = self.user_folders_base()
        names = {f: t(f"folder.{f}") for f in ORDER}
        defaults = default_folders(base, names, list(ORDER))
        v = resolve_volume(uf.volume, self.all_volumes()) if uf.volume else None
        letter = v.letter if v and v.letter else (uf.volume.letter_hint if uf.volume else "?")
        return [(f, f"{letter}:\\{uf.folders.get(f, defaults[f])}") for f in ORDER]

    def detect_user_folders(self) -> bool:
        recipe = self.require_recipe()
        vols = self.all_volumes()
        recipe.meta.source_system_volume = folders_collector.system_serial(vols)
        if self.services.registry is None:
            return False
        user = self.services.folders.current_user()
        found = folders_collector.detect(
            self.services.registry, vols, user["USERPROFILE"], recipe.windows.account.username
        )
        if found is not None:
            recipe.user_folders = found
        self.save()
        return found is not None

    def set_user_folders(
        self,
        *,
        enabled: bool | None = None,
        serial: str | None = None,
        base: str | None = None,
        folder: tuple[str, bool] | None = None,
    ) -> None:
        recipe = self.require_recipe()
        uf = recipe.user_folders
        if enabled is not None:
            uf.enabled = enabled
        if serial is not None or (uf.volume is None and self.data_volumes()):
            chosen = next((v for v in self.data_volumes() if v.serial == serial), None)
            chosen = chosen or self.data_volumes()[0]
            uf.volume = volume_ref(chosen)
        names = {f: t(f"folder.{f}") for f in ORDER}
        if base is not None:
            uf.folders = default_folders(base, names, list(uf.folders))
        if folder is not None:
            folder_id, on = folder
            current = default_folders(self.user_folders_base(), names, [*uf.folders, folder_id])
            chosen_ids = [f for f in current if f in uf.folders or (on and f == folder_id)]
            if not on:
                chosen_ids = [f for f in chosen_ids if f != folder_id]
            uf.folders = {f: uf.folders.get(f, current[f]) for f in chosen_ids}
        self.save()

    def copy_user_folders_now(self) -> folders_collector.CopyReport:
        if self.services.volumes is None:
            return folders_collector.CopyReport()
        return folders_collector.copy_now(
            self.require_recipe(),
            self.services.volumes,
            self.services.copier,
            self.services.folders.current_user(),
            self.services.volume_root,
        )

    def preset_preview(self, preset_id: str) -> PresetResult:
        preset = self.catalogs.preset(preset_id)
        if preset is None:
            return PresetResult()
        return preview_preset(preset, self.require_recipe(), self.catalogs)

    def apply_preset(self, preset_id: str) -> PresetResult:
        """Mescla o perfil rápido com a receita (V2-15, D-040) e salva."""
        preset = self.catalogs.preset(preset_id)
        if preset is None:
            return PresetResult()
        result = apply_preset(preset, self.require_recipe(), self.catalogs)
        self.save()
        return result

    def remove_hosts_block(self) -> bool:
        """Desfazer (V2-16): tira o bloco do WinKit do ``hosts`` deste PC."""
        return hosts.remove_block(hosts.hosts_file(self.services.folders.windows_dir()))

    def set_wifi_include_key(self, network_id: str, include: bool) -> bool:
        ok = wifi_collector.set_include_key(self.root, self.require_recipe(), network_id, include)
        self.save()
        return ok

    # ------------------------------------------------------------------ aplicar neste PC (V2-03)
    def live_kinds(self) -> list[StepKind]:
        """Tipos de etapa que a receita teria no modo ao vivo (para "o que aplicar")."""
        ctx = PlanContext(os_major=11, phase1_ran=False, mode="live", restore_before=False)
        p = plan(self.require_recipe(), self.catalogs, ctx)
        kinds = dict.fromkeys(s.kind for s in p.steps if s.kind not in ("finalize",))
        return list(kinds)

    def _live_options(
        self, kinds: frozenset[StepKind], restore_point: bool, *, simulate: bool
    ) -> LiveOptions:
        self.save()
        return LiveOptions(
            root=self.root,
            profile_id=self.profile_id,
            simulate=simulate,
            only_kinds=kinds,
            restore_point=restore_point,
            language=current_language(),
        )

    def live_preview(self, kinds: frozenset[StepKind], restore_point: bool) -> LivePreview:
        result = run_live(
            self.agent_runtime(), self._live_options(kinds, restore_point, simulate=True)
        )
        return result.preview or LivePreview()

    def live_apply(self, kinds: frozenset[StepKind], restore_point: bool) -> LiveResult:
        return run_live(
            self.agent_runtime(), self._live_options(kinds, restore_point, simulate=False)
        )

    def build(self) -> BuildReport:
        self.save()
        report = build(
            self.target or targets.from_folder(self.root),
            self.services.disks,
            self.catalogs,
            BuildOptions(
                profile_id=self.profile_id,
                agent_source=self.agent_source,
                iso_cache=_studio_dir() / "iso-cache.json",
            ),
            now=self.clock(),
        )
        self._open(self.target or targets.from_folder(self.root))  # recarrega (id realinhado)
        return report

    def validate_pendrive(self) -> PendriveReport:
        fs = self.target.file_system if self.target else "exFAT"
        return validate_pendrive(
            self.root,
            self.catalogs,
            profile_id=self.profile_id,
            file_system=fs,
            kind=self.target.kind if self.target else None,
        )

    @staticmethod
    def version() -> str:
        return __version__
