"""Fachada do WinKit Studio sem Qt (R-36): a GUI só chama estes métodos.

Usa exatamente os mesmos serviços e funções da linha de comando.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
from winkit.builder.custom_iso import CustomIsoOptions, build_custom_iso, needed_space
from winkit.builder.isos import scan_isos
from winkit.builder.usb_media import write_usb
from winkit.builder.validate import PendriveReport, validate_pendrive
from winkit.collector import app_updates, pc_backup, snapshot
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
from winkit.collector import suggest as suggest_collector
from winkit.collector import user_folders as folders_collector
from winkit.collector import wifi as wifi_collector
from winkit.core import layout, media, rufus, share
from winkit.core import pc_backup as core_pc
from winkit.core.browsers import suggested
from winkit.core.catalog.loader import default_catalogs
from winkit.core.catalog.models import AssociationGroup, Catalogs, DownloadSource
from winkit.core.devices import hardware_ids
from winkit.core.errors import RecipeError, WinKitError
from winkit.core.fsutil import atomic_write_text
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
    Media,
    NetworkDrive,
    Recipe,
    Scope,
    TargetWindows,
    VolumeRef,
    WifiNetwork,
)
from winkit.core.recipe.validation import ValidationReport, username_problem, validate_recipe
from winkit.core.share import ShareableRecipe
from winkit.core.suggest import Suggestion
from winkit.core.usb_safety import UsbDisk
from winkit.core.user_folders import ORDER, default_folders
from winkit.core.volumes import VolumeInfo
from winkit.core.volumes import ref_for as volume_ref
from winkit.core.volumes import resolve as resolve_volume
from winkit.core.winget_manifest import split_args
from winkit.i18n import current_language, t
from winkit.i18n.format import format_size
from winkit.i18n.msg import Msg
from winkit.platform import download as dl
from winkit.platform import external_tools, hosts
from winkit.platform.disk_info import Destination, Health
from winkit.platform.environment import WindowsEnvironment
from winkit.platform.image_tools import ImageInfo
from winkit.platform.iso_mount import mounted_iso
from winkit.platform.runner import launch
from winkit.platform.services import Services
from winkit.platform.vss import PendingSnapshots

log = logging.getLogger(__name__)


def windows_build() -> int | None:
    return WindowsEnvironment().windows_build()


def _studio_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".cache") / "WinKit"


@dataclass(frozen=True)
class PcEstimate:
    files: int
    total: int
    seconds: float
    speed: float  # MB/s
    measured: bool
    warnings: list[Msg]


def fetch_tool(source: DownloadSource) -> Path:  # pragma: no cover — rede real
    """Baixa a última release oficial (R-61) e devolve o executável."""
    release = external_tools.latest_release(source)
    return external_tools.fetch(source, _studio_dir() / "ferramentas", release=release)


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
    #: Dados lentos do sistema já lidos (pendrives, tamanhos, volumes); a interface lê daqui (R-59).
    cache: dict[str, Any] = field(default_factory=dict)
    #: Baixa Ventoy/Rufus (V3-07) e abre programas; os testes passam dublês.
    tool_fetcher: Callable[[DownloadSource], Path] = field(default=fetch_tool)
    launcher: Callable[[list[str]], None] = field(default=launch)
    iso_downloader: Callable[..., Path] = field(default=dl.download)
    #: Escolhas da primeira etapa (V3-06); vão para a receita quando ela existir.
    media: Media = field(default_factory=Media)
    target_windows: TargetWindows = field(default_factory=TargetWindows)

    # ------------------------------------------------------------------ pendrive
    @property
    def catalogs(self) -> Catalogs:
        return self.catalogs_override or default_catalogs()

    def pendrives(self) -> list[targets.AnyDrive]:
        return targets.list_targets(self.services.disks, self.services.volume_root)

    def load_slow(self, key: str) -> Any:
        """Lê um dado lento (fora da thread da interface) e guarda no cache. Erro vira o valor."""
        readers: dict[str, Callable[[], Any]] = {
            "pendrives": self.pendrives,
            "sizes": lambda: (self.sizes(), self.free_bytes()),
            "volumes": self.data_volumes,
            "destinations": self.pc_destinations,
            "health": self.pc_health,
            "usbdisks": self.usb_disks,
            "devices": lambda: (
                hardware_ids(self.services.devices.all_devices()) if self.services.devices else []
            ),
        }
        try:
            value = readers[key]()
        except Exception as exc:  # noqa: BLE001 — a página mostra o motivo
            value = exc
        self.cache[key] = value
        return value

    # ------------------------------------------------------------------ caminho (V3-06/07)
    def set_media_path(self, path: str) -> None:
        """Vale antes de existir receita (a primeira etapa vem antes do pendrive)."""
        self.media = Media.model_validate({"path": path})
        if self.recipe is not None:
            self.recipe.media = self.media
            self.save()

    def set_target_windows(self, version: str, arch: str) -> None:
        if version == "11":
            arch = "x64"  # o Windows 11 só existe em 64 bits
        self.target_windows = TargetWindows.model_validate({"version": version, "arch": arch})
        if self.recipe is not None:
            self.recipe.target_windows = self.target_windows
            # o XML usa a arquitetura da receita (32 bits = "x86")
            if arch == "x86":
                self.recipe.windows.architecture = "x86"
            elif self.recipe.windows.architecture == "x86":
                self.recipe.windows.architecture = "amd64"
            self.save()

    def open_tool(self, tool_id: str, iso: Path | None = None) -> Path:
        """Baixa (se preciso), confere e abre o Ventoy2Disk ou o Rufus para a pessoa usar."""
        source = self.catalogs.download(tool_id)
        if source is None:
            raise WinKitError(f"ferramenta desconhecida: {tool_id}")
        exe = self.tool_fetcher(source)
        args = [str(exe)]
        if tool_id == "rufus" and iso is not None:
            args += ["-i", str(iso)]  # já abre com a ISO escolhida
        self.launcher(args)
        self.cache.pop("pendrives", None)  # o pendrive vai mudar
        return exe

    def download_windows(
        self,
        dest: Path,
        language: str,
        progress: Callable[[dl.Progress], None],
        should_stop: Callable[[], bool],
    ) -> IsoInfo:
        """Baixa a ISO oficial do Windows alvo (V3-08) e confere que é mesmo do Windows."""
        if self.services.iso_links is None:
            raise WinKitError("download da ISO indisponível neste sistema")
        tw = self.target_windows
        if tw.version == "7":
            raise WinKitError(t("studio.download.no_win7"))
        url = self.services.iso_links.url(tw.version, tw.arch, language)
        path = self.iso_downloader(url, dest, progress=progress, should_stop=should_stop)
        info = self.services.disks.read_iso(path, path.name)
        if not info.is_windows:
            raise WinKitError(f"o arquivo baixado não é uma ISO do Windows: {path}")
        return info

    def copy_iso_to_pendrive(self, iso: Path) -> Path:
        """Ventoy: a ISO vai para a raiz do pendrive (V3-08)."""
        dest = self.root / iso.name
        if not dest.is_file() or dest.stat().st_size != iso.stat().st_size:
            part = dest.with_name(dest.name + ".part")
            shutil.copyfile(iso, part)
            part.replace(dest)
        self.cache.pop("sizes", None)
        return dest

    # ------------------------------------------------------------------ backup do PC (V3-09/10)
    def pc_destinations(self) -> list[Destination]:
        return self.services.disk_info.destinations() if self.services.disk_info else []

    def pc_destination(self) -> Destination | None:
        ref = self.require_recipe().pc_backup.destination
        dests = self.cache.get("destinations")
        if ref is None or not isinstance(dests, list):
            return None
        return next((d for d in dests if d.serial == ref.serial), None)

    def set_pc_destination(self, d: Destination) -> None:
        self.require_recipe().pc_backup.destination = VolumeRef(
            serial=d.serial, label=d.label or None, letter_hint=d.letter[:1] or None, size=d.size
        )
        self.save()

    def set_pc_sources(self, literals: list[str]) -> None:
        self.require_recipe().pc_backup.sources = list(dict.fromkeys(literals))
        self.save()

    def default_pc_sources(self) -> list[str]:
        return pc_backup.default_literals(self.old_folders())

    def _source_root(self, literal: str) -> Path:
        return backup_collector.local_source(
            self.services.volume_root(literal[:2].upper()), literal
        )

    def pc_estimate(self) -> PcEstimate:
        """Tamanho, avisos e tempo medido no destino de verdade (V3-09)."""
        b = self.require_recipe().pc_backup
        dest = self.pc_destination()
        if dest is None:
            raise WinKitError("escolha o disco de destino primeiro")
        files = [f for lit in b.sources for f in pc_backup.scan(self._source_root(lit))]
        total = sum(f.size for f in files)
        root = self.services.volume_root(dest.letter)
        try:
            speed, per_file = pc_backup.measure_speed(root / core_pc.BACKUP_DIR)
            measured = True
        except OSError:
            speed, per_file = core_pc.TYPICAL[dest.kind]
            measured = False
        return PcEstimate(
            files=len(files),
            total=total,
            seconds=core_pc.estimate_seconds(total, len(files), speed, per_file),
            speed=speed,
            measured=measured,
            warnings=core_pc.warnings(
                files,
                total=total,
                free=dest.free,
                file_system=dest.file_system,
                same_disk=dest.system_disk,
            ),
        )

    def run_pc_backup(
        self,
        progress: Callable[[core_pc.BackupProgress], None],
        should_stop: Callable[[], bool],
    ) -> core_pc.PcBackupManifest:
        b = self.require_recipe().pc_backup
        dest = self.pc_destination()
        if dest is None:
            raise WinKitError("escolha o disco de destino primeiro")
        studio = _studio_dir()
        notes: list[str] = []
        snaps = backup_collector._Snapshots(
            self.services.vss, PendingSnapshots(studio / "vss-pendentes.json"), studio, notes
        )
        try:
            manifest = pc_backup.run_backup(
                pc_backup.make_sources(b.sources, self.old_folders()),
                self.services.volume_root(dest.letter),
                computer=os.environ.get("COMPUTERNAME")
                or self.require_recipe().meta.source_pc
                or "pc",
                now=self.clock(),
                zip_mode=b.zip,
                source_root=self._source_root,
                snapshot_root=snaps.root,
                progress=progress,
                should_stop=should_stop,
            )
        finally:
            snaps.close()
        self.cache.pop("destinations", None)  # espaço livre mudou
        return manifest

    def pc_backups_found(self) -> list[tuple[Path, core_pc.PcBackupManifest]]:
        dests = self.cache.get("destinations")
        roots = (
            [self.services.volume_root(d.letter) for d in dests] if isinstance(dests, list) else []
        )
        return core_pc.find_backups(roots)

    def restore_pc_backup(
        self,
        base: Path,
        manifest: core_pc.PcBackupManifest,
        progress: Callable[[core_pc.BackupProgress], None],
    ) -> core_pc.RestoreReport:
        targets = core_pc.restore_targets(manifest, self.old_folders())
        return core_pc.restore(
            base, manifest, targets, target_root=self._source_root, progress=progress
        )

    # ---------------------------------------------------------- antes de formatar (V3-15/16)
    def pc_health(self) -> Health | None:
        return self.services.disk_info.health() if self.services.disk_info else None

    def export_recovery_keys(self, folder: Path) -> Path:
        """Chave de recuperação do BitLocker do C: num arquivo de texto (V3-16)."""
        if self.services.disk_info is None:
            raise WinKitError("indisponível neste sistema")
        keys = self.services.disk_info.recovery_keys()
        if not keys:
            raise WinKitError("o C: não tem chave de recuperação do BitLocker")
        lines = [t("health.key_file_header"), ""]
        lines += [
            f"{t('health.key_id')}: {kid}\n{t('health.key_value')}: {key}\n" for kid, key in keys
        ]
        path = folder / "WinKit-chave-bitlocker.txt"
        atomic_write_text(path, "\n".join(lines))
        return path

    # ---------------------------------------------------------- ISO personalizada (V3-11/12)
    def iso_editions(self, iso: Path) -> list[ImageInfo]:
        tools, mounter = self.services.image_tools, self.services.iso_mounter
        if tools is None or mounter is None:
            raise WinKitError("ISO personalizada indisponível neste sistema")
        with mounted_iso(mounter, iso) as drive:
            sources = drive / "sources"
            wim = next(
                (sources / n for n in ("install.wim", "install.esd") if (sources / n).is_file()),
                None,
            )
            if wim is None:
                raise WinKitError("a ISO não tem sources\\install.wim nem install.esd")
            return tools.images(wim)

    def custom_iso_space(self, opts: CustomIsoOptions) -> tuple[int, int]:
        """(precisa, livre) na pasta de trabalho."""
        extra = 0
        if opts.self_contained_from is not None:
            extra = sum(self.sizes().values())
        opts.work_dir.mkdir(parents=True, exist_ok=True)
        return needed_space(opts.original, extra), shutil.disk_usage(opts.work_dir).free

    def win7_rollup(self) -> list[Path]:
        """Windows 7 "SP2": pré-requisito e Convenience Rollup, baixados e conferidos (V3-14)."""
        arch = self.target_windows.arch
        out = []
        for kb in ("kb3020369", "kb3125574"):
            source = self.catalogs.download(f"win7_{kb}_{arch}")
            if source is None:
                raise WinKitError(f"atualização {kb} ausente do catálogo")
            out.append(external_tools.fetch_direct(source, _studio_dir() / "atualizacoes"))
        return out

    def make_custom_iso(self, opts: CustomIsoOptions, progress: Callable[[object], None]) -> Path:
        tools, mounter = self.services.image_tools, self.services.iso_mounter
        if tools is None or mounter is None:
            raise WinKitError("ISO personalizada indisponível neste sistema")
        need, free = self.custom_iso_space(opts)
        if free < need:
            raise WinKitError(
                t("studio.customiso.no_space", need=format_size(need), free=format_size(free))
            )
        return build_custom_iso(
            opts,
            tools=tools,
            mounter=mounter,
            inspector=self.services.disks,
            catalogs=self.catalogs,
            now=self.clock(),
            progress=lambda step, frac: progress((step, frac)),
        )

    # ------------------------------------------------------------ o WinKit grava o pendrive (V3-13)
    def usb_disks(self) -> list[UsbDisk]:
        return self.services.usb_writer.usb_disks() if self.services.usb_writer else []

    def set_boot(self, boot: str) -> None:
        self.media = self.media.model_copy(update={"boot": boot})
        if self.recipe is not None:
            self.recipe.media = self.media
            self.save()

    def write_usb(
        self, iso: Path, shown: UsbDisk, typed_letter: str, progress: Callable[[object], None]
    ) -> str:
        s = self.services
        if s.usb_writer is None or s.image_tools is None or s.iso_mounter is None:
            raise WinKitError("gravar pendrive indisponível neste sistema")
        letter = write_usb(
            iso,
            shown,
            typed_letter,
            self.media.boot,
            writer=s.usb_writer,
            tools=s.image_tools,
            mounter=s.iso_mounter,
            runner=s.runner,
            volume_root=s.volume_root,
            progress=lambda step, frac: progress((step, frac)),
        )
        self.cache.pop("pendrives", None)
        self.cache.pop("usbdisks", None)
        self.open_folder(s.volume_root(letter))  # segue como pendrive comum (D-034)
        return letter

    def rufus_options(self) -> list[rufus.RufusOption]:
        """O que o Rufus gravou neste pendrive (os originais guardados também contam)."""
        if self.target is None or self.recipe is None:
            return []
        texts = []
        for rel in (
            media.UNATTEND,
            media.UNATTEND_BACKUP,
            media.OEM_UNATTEND,
            media.OEM_UNATTEND + ".winkit-bak",
        ):
            path = self.root / rel
            if path.is_file() and not media.is_winkit_unattend(path.read_bytes()):
                texts.append(path.read_text(encoding="utf-8", errors="replace"))
        return rufus.compare(rufus.detect(texts), self.recipe)

    def open_ventoy(self, v: targets.AnyDrive) -> None:
        self._open(targets.from_drive(v))

    def open_folder(self, folder: Path) -> None:
        self._open(targets.from_folder(folder))

    def _open(self, tgt: targets.Target) -> None:
        self.target = tgt
        self.cache.pop("sizes", None)
        try:
            self.recipe = load_profile_recipe(tgt.root, self.profile_id)
        except RecipeError:
            self.recipe = None
        if self.recipe is not None:
            self.media, self.target_windows = self.recipe.media, self.recipe.target_windows

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
        recipe.media, recipe.target_windows = self.media, self.target_windows
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

    # ------------------------------------------------------------------ sugestões (V2-20)
    def suggestions(self) -> list[Suggestion]:
        """Analisa este PC (local, nada sai daqui) e sugere o que levar."""
        return suggest_collector.analyze(
            self.require_recipe(),
            self.catalogs,
            inventory=self.services.inventory,
            registry=self.services.registry,
            folders=self.old_folders(),
            volume_root=self.services.volume_root,
            now=self.clock(),
        )

    def accept_suggestion(self, s: Suggestion) -> bool:
        ok = suggest_collector.accept(self.require_recipe(), self.catalogs, s, self.old_folders())
        if ok:
            self.save()
        return ok

    def dismiss_suggestion(self, suggestion_id: str) -> None:
        suggest_collector.dismiss(self.require_recipe(), suggestion_id)
        self.save()

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

    # ---- atualizar os instaladores do pendrive (V2-21)
    def apps_need_update_check(self) -> bool:
        return app_updates.needs_check(self.require_recipe(), datetime.now(UTC))

    def _refresh(self, *, apply: bool, ids: list[str] | None) -> list[app_updates.UpdateCheck]:
        return app_updates.refresh_apps(
            self.services.winget,
            self.root,
            self.require_recipe(),
            self.catalogs,
            apply=apply,
            ids=ids,
            save=self.save,
            now=datetime.now(UTC),
        )

    def check_app_updates(self) -> list[app_updates.UpdateCheck]:
        return self._refresh(apply=False, ids=None)

    def update_apps(self, ids: list[str]) -> list[app_updates.UpdateCheck]:
        return self._refresh(apply=True, ids=ids)

    # ---- modelos e receitas compartilháveis (V2-23)
    def templates(self) -> list[tuple[str, ShareableRecipe]]:
        return [(i, share.load_template(i)) for i in share.TEMPLATE_IDS]

    @staticmethod
    def share_load(path: Path) -> ShareableRecipe:
        return share.loads(path.read_text(encoding="utf-8"))

    def share_preview(self, data: ShareableRecipe) -> share.ImportResult:
        return share.preview_import(data, self.require_recipe(), self.catalogs)

    def share_apply(self, data: ShareableRecipe) -> share.ImportResult:
        result = share.import_recipe(data, self.require_recipe(), self.catalogs)
        self.save()
        return result

    def share_export(self, path: Path, title: str) -> None:
        data = share.export_recipe(
            self.require_recipe(), title=title, description="", version=self.version()
        )
        atomic_write_text(path, share.dumps(data))

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

    def write_snapshot(self) -> None:
        """V2-19: o inventário "antes" vai para o pendrive junto com a construção."""
        recipe = self.require_recipe()
        if not recipe.compare_after_install:
            return
        snap = snapshot.take_snapshot(
            self.services.inventory,
            self.services.devices,
            self.services.features,
            self.catalogs,
            build=windows_build(),
        )
        snapshot.write_before(self.root, recipe, snap)

    def build(self) -> BuildReport:
        self.save()
        try:
            self.write_snapshot()
        except WinKitError as exc:  # o relatório é opcional; a construção continua
            log.warning("inventário para a comparação não gravado: %s", exc)
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
