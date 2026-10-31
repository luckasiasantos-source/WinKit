"""Orquestra a construção do pendrive (PLANO.md §8.4).

M2: marcador, receita, leitura das ISOs, geração dos XMLs, mesclagem do ``ventoy.json`` e
cópia do bootstrap/Agente. A cópia de instaladores, drivers e backups entra nos marcos
seguintes, sempre por este mesmo orquestrador.
"""

from __future__ import annotations

import logging
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from importlib import resources
from pathlib import Path

from winkit import __version__
from winkit.builder.isos import scan_isos
from winkit.builder.target import Target
from winkit.core import layout, media
from winkit.core.catalog.models import Catalogs
from winkit.core.errors import PendriveError, RecipeError, WinKitError
from winkit.core.fsutil import atomic_write_text, write_if_changed
from winkit.core.isos import IsoInfo, iso_index
from winkit.core.manifest.manifest import Manifest, diff, dump_manifest, load_manifest, scan
from winkit.core.recipe.io import dump_recipe, load_recipe
from winkit.core.recipe.models import Recipe
from winkit.core.recipe.validation import ensure_valid
from winkit.core.unattend.generator import UnattendTarget, generate_unattend, template_name
from winkit.core.ventoy.config import AutoInstallEntry, merge_auto_install, parse_config
from winkit.i18n import t
from winkit.platform.disks import DiskInspector

log = logging.getLogger(__name__)

FALLBACK_LANGUAGE = "pt-BR"


@dataclass
class BuildOptions:
    profile_id: str = "padrao"
    xml_only: bool = False
    #: Pasta "winkit-agent" (PyInstaller onedir) a copiar para o pendrive.
    agent_source: Path | None = None
    iso_cache: Path | None = None


@dataclass
class BuildReport:
    root: Path
    pendrive_id: str = ""
    isos: list[IsoInfo] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    templates: list[str] = field(default_factory=list)
    removed_templates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    agent_copied: bool = False
    manifest_files: int = 0
    manifest_changes: tuple[int, int, int] = (0, 0, 0)  # adicionados, alterados, removidos
    sizes: dict[str, int] = field(default_factory=dict)


def ensure_marker(root: Path, now: datetime) -> layout.Marker:
    marker = layout.read_marker(root)
    if marker is None:
        marker = layout.new_marker(__version__, now)
        atomic_write_text(root / layout.MARKER, layout.dump_marker(marker))
        log.info("marcador criado: %s", marker.pendrive_id)
    return marker


def load_profile_recipe(root: Path, profile_id: str) -> Recipe:
    path = root / layout.recipe_file(profile_id)
    if not path.is_file():
        raise RecipeError(t("builder.recipe_missing", path=path))
    return load_recipe(path.read_text(encoding="utf-8-sig"))


def save_profile_recipe(root: Path, recipe: Recipe) -> Path:
    path = root / layout.recipe_file(recipe.meta.profile_id)
    atomic_write_text(path, dump_recipe(recipe))
    return path


def _group_isos(
    recipe: Recipe, isos: list[IsoInfo], report: BuildReport
) -> dict[tuple[str, str], list[IsoInfo]]:
    groups: dict[tuple[str, str], list[IsoInfo]] = defaultdict(list)
    for iso in isos:
        if not iso.is_windows:
            report.skipped.append((iso.image, t("builder.iso_skipped", name=iso.name)))
            continue
        if iso.architecture != recipe.windows.architecture:
            report.warnings.append(
                t(
                    "builder.arch_mismatch",
                    name=iso.name,
                    iso_arch=iso.architecture,
                    recipe_arch=recipe.windows.architecture,
                )
            )
            report.skipped.append((iso.image, t("builder.skip_arch")))
            continue
        if iso.os_major is not None and iso.os_major not in recipe.windows.target_os:
            report.skipped.append((iso.image, t("builder.skip_os", os=iso.os_major)))
            continue
        lang = iso.default_language or FALLBACK_LANGUAGE
        groups[(lang, iso.architecture)].append(iso)
    return groups


def _write_templates(
    root: Path,
    *,
    recipe: Recipe,
    catalogs: Catalogs,
    groups: dict[tuple[str, str], list[IsoInfo]],
    pendrive_id: str,
    report: BuildReport,
) -> list[AutoInstallEntry]:
    script_dir = root / layout.SCRIPT_DIR
    entries: list[AutoInstallEntry] = []
    written: set[str] = set()
    for (lang, arch), members in sorted(groups.items()):
        os_major = 10 if all(m.os_major == 10 for m in members) else None
        xml = generate_unattend(
            recipe,
            catalogs,
            UnattendTarget(ui_language=lang, architecture=arch, os_major=os_major),
            pendrive_id=pendrive_id,
        )
        name = template_name(recipe.meta.profile_id, lang, arch)
        write_if_changed(script_dir / name, xml)
        written.add(name)
        report.templates.append(f"/{layout.SCRIPT_DIR}/{name}")
        for iso in members:
            entries.append(AutoInstallEntry(iso.image, f"/{layout.SCRIPT_DIR}/{name}"))
            report.isos.append(iso)
    # remove modelos antigos deste perfil (só arquivos com o nosso prefixo — R-19)
    prefix = f"winkit-{recipe.meta.profile_id}-"
    if script_dir.is_dir():
        for old in sorted(script_dir.glob(f"{prefix}*.xml")):
            if old.name not in written:
                old.unlink()
                report.removed_templates.append(old.name)
    return entries


def _update_ventoy_json(root: Path, recipe: Recipe, entries: list[AutoInstallEntry]) -> None:
    path = root / layout.VENTOY_JSON
    existing = path.read_text(encoding="utf-8-sig") if path.is_file() else None
    parse_config(existing)  # falha antes de qualquer escrita se o arquivo estiver inválido
    backup = root / layout.VENTOY_BACKUP
    if not backup.exists():
        # Estado anterior à primeira alteração do WinKit. Se não havia ventoy.json, o backup
        # é "{}" (configuração vazia, equivalente a não ter o arquivo).
        if existing is not None:
            shutil.copy2(path, backup)
        else:
            atomic_write_text(backup, "{}\n")
    silent = recipe.execution.mode == "silent"
    text = merge_auto_install(
        existing,
        entries,
        autosel=1,
        timeout=5 if silent else 15,
        profile_id=recipe.meta.profile_id,
    )
    atomic_write_text(path, text)


def _keep_original(path: Path, backup: Path, report: BuildReport, key: str) -> None:
    """Guarda uma vez o arquivo de respostas que não é do WinKit (D-034)."""
    if not path.is_file() or media.is_winkit_unattend(path.read_bytes()):
        return
    if backup.exists():
        n = 2
        while backup.with_name(f"{backup.name}{n}").exists():
            n += 1
        backup = backup.with_name(f"{backup.name}{n}")
    shutil.copy2(path, backup)
    report.warnings.append(t(key, name=backup.name))


def _build_setup_media(  # noqa: PLR0917 — mesma assinatura das outras etapas da construção
    root: Path,
    recipe: Recipe,
    catalogs: Catalogs,
    inspector: DiskInspector,
    pendrive_id: str,
    report: BuildReport,
) -> None:
    """Pendrive comum (Rufus/Microsoft): só ``\\autounattend.xml`` na raiz (R-19)."""
    image = media.image_file(root)
    lang, arch, os_major = FALLBACK_LANGUAGE, recipe.windows.architecture, None
    if image is not None:
        try:
            info = inspector.read_setup_image(image)
        except (WinKitError, OSError) as exc:
            report.warnings.append(t("builder.setup_image_unreadable", detail=str(exc)))
        else:
            report.isos.append(info)
            if info.architecture not in ("unknown", recipe.windows.architecture):
                report.warnings.append(
                    t(
                        "builder.arch_mismatch",
                        name=info.name,
                        iso_arch=info.architecture,
                        recipe_arch=recipe.windows.architecture,
                    )
                )
            lang = info.default_language or FALLBACK_LANGUAGE
            os_major = 10 if info.os_major == 10 else None
    xml = generate_unattend(
        recipe,
        catalogs,
        UnattendTarget(ui_language=lang, architecture=arch, os_major=os_major),
        pendrive_id=pendrive_id,
    )
    path = root / media.UNATTEND
    _keep_original(path, root / media.UNATTEND_BACKUP, report, "builder.rufus_unattend_kept")
    write_if_changed(path, media.stamp_unattend(xml, __version__, pendrive_id))
    report.templates.append("/" + media.UNATTEND)
    oem = root / media.OEM_UNATTEND
    if oem.is_file() and not media.is_winkit_unattend(oem.read_bytes()):
        # seria aplicado depois do nosso e poderia desfazer a conta local (H17)
        _keep_original(
            oem, oem.with_name(oem.name + ".winkit-bak"), report, "builder.oem_unattend_kept"
        )
        oem.unlink()


def _copy_agent(root: Path, options: BuildOptions, report: BuildReport) -> None:
    bootstrap = resources.files("winkit.builder").joinpath("assets/bootstrap.ps1").read_bytes()
    write_if_changed(root / layout.BOOTSTRAP, bootstrap)
    write_if_changed(root / layout.AGENT_VERSION, (__version__ + "\n").encode("utf-8"))
    if options.agent_source is None:
        return
    exe = options.agent_source / layout.AGENT_EXE_NAME
    if not exe.is_file():
        raise PendriveError(t("builder.agent_missing", path=options.agent_source))
    dest = root / layout.AGENT_BIN_DIR
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(options.agent_source, dest)
    report.agent_copied = True


def build(
    target: Target,
    inspector: DiskInspector,
    catalogs: Catalogs,
    options: BuildOptions,
    *,
    now: datetime,
) -> BuildReport:
    root = target.root
    report = BuildReport(root=root)
    marker = ensure_marker(root, now)
    report.pendrive_id = marker.pendrive_id

    recipe = load_profile_recipe(root, options.profile_id)
    if recipe.meta.pendrive_id != marker.pendrive_id:
        report.warnings.append(t("builder.pendrive_id_updated"))
        recipe.meta.pendrive_id = marker.pendrive_id
        recipe.meta.updated_at = now
        save_profile_recipe(root, recipe)
    validation = ensure_valid(recipe, catalogs)
    report.warnings.extend(validation.warnings)

    if target.kind == "setup":
        _build_setup_media(root, recipe, catalogs, inspector, marker.pendrive_id, report)
    else:
        isos, errors = scan_isos(root, inspector, options.iso_cache)
        report.skipped.extend(errors)
        groups = _group_isos(recipe, isos, report)
        if not groups:
            report.warnings.append(t("builder.no_isos"))
        entries = _write_templates(
            root,
            recipe=recipe,
            catalogs=catalogs,
            groups=groups,
            pendrive_id=marker.pendrive_id,
            report=report,
        )
        _update_ventoy_json(root, recipe, entries)
        index = iso_index(isos)
        atomic_write_text(root / layout.ISOS_INDEX, index.model_dump_json(indent=2) + "\n")
    _copy_agent(root, options, report)
    if not options.xml_only:
        _write_manifest(root, report)
    report.sizes = payload_sizes(root, recipe.meta.profile_id)
    return report


def _write_manifest(root: Path, report: BuildReport) -> None:
    path = root / layout.MANIFEST
    previous: Manifest | None = None
    if path.is_file():
        try:
            previous = load_manifest(path.read_text(encoding="utf-8"))
        except WinKitError:
            previous = None
    manifest = scan(root, layout.MANIFEST_SUBDIRS, previous)
    d = diff(previous or Manifest(), manifest)
    report.manifest_files = len(manifest.files)
    report.manifest_changes = (len(d.added), len(d.changed), len(d.removed))
    atomic_write_text(path, dump_manifest(manifest))


def _tree_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def payload_sizes(root: Path, profile_id: str) -> dict[str, int]:
    """Espaço ocupado por categoria no pendrive (item 25)."""
    return {
        "agent": _tree_size(root / layout.AGENT_DIR),
        "apps": _tree_size(root / layout.APPS),
        "drivers": _tree_size(root / layout.DRIVERS),
        "backups": _tree_size(root / layout.backups_dir(profile_id)),
    }
