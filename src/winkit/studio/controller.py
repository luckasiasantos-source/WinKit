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
from winkit.collector import backups as backup_collector
from winkit.collector import drivers as driver_collector
from winkit.core import layout
from winkit.core.catalog.loader import default_catalogs
from winkit.core.catalog.models import Catalogs
from winkit.core.errors import RecipeError, WinKitError
from winkit.core.isos import IsoInfo
from winkit.core.planner.models import Plan, PlanContext
from winkit.core.planner.planner import plan
from winkit.core.recipe.io import new_recipe
from winkit.core.recipe.models import AppItem, BackupItem, ConflictPolicy, Recipe, Scope
from winkit.core.recipe.validation import ValidationReport, validate_recipe
from winkit.core.ventoy.detect import VentoyTarget
from winkit.core.winget_manifest import split_args
from winkit.platform.services import Services
from winkit.platform.vss import PendingSnapshots


def _studio_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".cache") / "WinKit"


def default_agent_source() -> Path | None:
    if getattr(sys, "frozen", False):
        candidate = Path(sys.executable).resolve().parent.parent / "winkit-agent"
        if (candidate / layout.AGENT_EXE_NAME).is_file():
            return candidate
    return None


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

    # ------------------------------------------------------------------ pendrive
    @property
    def catalogs(self) -> Catalogs:
        return self.catalogs_override or default_catalogs()

    def pendrives(self) -> list[VentoyTarget]:
        return targets.list_targets(self.services.disks)

    def open_ventoy(self, v: VentoyTarget) -> None:
        self._open(targets.from_ventoy(v))

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
            self.root, self.catalogs, profile_id=self.profile_id, file_system=fs
        )

    @staticmethod
    def version() -> str:
        return __version__
