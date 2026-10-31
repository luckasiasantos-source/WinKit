"""Validação do pendrive sem alterar nada (PLANO.md §8.6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from winkit import __version__
from winkit.builder.build import load_profile_recipe
from winkit.core import layout, media
from winkit.core.catalog.models import Catalogs
from winkit.core.errors import IntegrityError, UnattendError, VentoyConfigError, WinKitError
from winkit.core.manifest.manifest import load_manifest, verify_tree
from winkit.core.recipe.validation import validate_recipe
from winkit.core.unattend.generator import check_safety
from winkit.core.ventoy.config import winkit_entries
from winkit.i18n import t

FAT32_LIMIT = 4 * 1024**3 - 1


@dataclass
class PendriveReport:
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def validate_pendrive(
    root: Path,
    catalogs: Catalogs,
    *,
    profile_id: str = "padrao",
    file_system: str = "exFAT",
    kind: str | None = None,
) -> PendriveReport:
    rep = PendriveReport()
    try:
        marker = layout.read_marker(root)
    except WinKitError as exc:
        rep.problems.append(str(exc))
        return rep
    if marker is None:
        rep.problems.append(t("validate.no_marker"))
        return rep

    _check_recipe(root, catalogs, profile_id, marker.pendrive_id, rep)
    setup = kind == "setup" if kind else media.has_setup_files(root)
    if setup:
        _check_setup_media(root, rep)
    else:
        _check_ventoy(root, rep)
    _check_agent(root, rep)
    _check_manifest(root, rep)
    if file_system.upper() in ("FAT32", "FAT"):
        for path in (root / layout.WINKIT).rglob("*"):
            if path.is_file() and path.stat().st_size > FAT32_LIMIT:
                rep.problems.append(t("pendrive.fat32_big_file", path=path))
    return rep


def _check_recipe(
    root: Path, catalogs: Catalogs, profile_id: str, pendrive_id: str, rep: PendriveReport
) -> None:
    try:
        recipe = load_profile_recipe(root, profile_id)
    except WinKitError as exc:
        rep.problems.append(str(exc))
        return
    result = validate_recipe(recipe, catalogs)
    rep.problems.extend(result.errors)
    rep.warnings.extend(result.warnings)
    if recipe.meta.pendrive_id != pendrive_id:
        rep.warnings.append(t("validate.other_pendrive"))
    for d in recipe.selected_drivers():
        if not layout.payload(root, d.path).exists():
            rep.problems.append(t("validate.driver_missing", id=d.id, path=d.path))
    for a in recipe.selected_apps():
        if a.installer and a.installer.path and not layout.payload(root, a.installer.path).exists():
            rep.problems.append(t("validate.installer_missing", id=a.id, path=a.installer.path))
    for b in recipe.selected_backups():
        if not layout.payload(root, b.data_path).exists():
            rep.problems.append(t("validate.backup_missing", id=b.id, path=b.data_path))


def _check_ventoy(root: Path, rep: PendriveReport) -> None:
    path = root / layout.VENTOY_JSON
    if not path.is_file():
        rep.problems.append(t("validate.no_ventoy_json"))
        return
    try:
        entries = winkit_entries(path.read_text(encoding="utf-8-sig"))
    except VentoyConfigError as exc:
        rep.problems.append(t("validate.ventoy_json_invalid", detail=exc))
        return
    if not entries:
        rep.warnings.append(t("validate.no_iso_entries"))
    for e in entries:
        iso = root / e.image.lstrip("/")
        xml = root / e.template.lstrip("/")
        if not iso.is_file():
            rep.warnings.append(t("validate.iso_missing", image=e.image))
        if not xml.is_file():
            rep.problems.append(t("validate.template_missing", name=e.template))
            continue
        try:
            check_safety(xml.read_bytes())
        except UnattendError as exc:
            rep.problems.append(f"{e.template}: {exc}")


def _check_setup_media(root: Path, rep: PendriveReport) -> None:
    """Pendrive comum (D-034): o ``autounattend.xml`` da raiz tem que ser o do WinKit."""
    path = root / media.UNATTEND
    if not path.is_file():
        rep.problems.append(t("validate.no_unattend"))
        return
    data = path.read_bytes()
    if not media.is_winkit_unattend(data):
        rep.problems.append(t("validate.unattend_not_winkit"))
    try:
        check_safety(data)
    except UnattendError as exc:
        rep.problems.append(f"{media.UNATTEND}: {exc}")
    oem = root / media.OEM_UNATTEND
    if oem.is_file() and not media.is_winkit_unattend(oem.read_bytes()):
        rep.warnings.append(t("validate.oem_unattend_present"))


def _check_agent(root: Path, rep: PendriveReport) -> None:
    if not (root / layout.BOOTSTRAP).is_file():
        rep.problems.append(t("validate.no_bootstrap"))
    version_file = root / layout.AGENT_VERSION
    if version_file.is_file():
        version = version_file.read_text(encoding="utf-8").strip()
        if version != __version__:
            rep.warnings.append(t("validate.agent_version", agent=version, studio=__version__))
    if not (root / layout.AGENT_BIN_DIR / layout.AGENT_EXE_NAME).is_file():
        rep.warnings.append(t("validate.no_agent_exe"))


def _check_manifest(root: Path, rep: PendriveReport) -> None:
    path = root / layout.MANIFEST
    if not path.is_file():
        return
    try:
        manifest = load_manifest(path.read_text(encoding="utf-8"))
        for sub in layout.MANIFEST_SUBDIRS:
            verify_tree(root, sub + "/", manifest)
    except IntegrityError as exc:
        rep.problems.append(str(exc))
