"""Validação do pendrive sem alterar nada (PLANO.md §8.6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from winkit import __version__
from winkit.builder.build import load_profile_recipe
from winkit.core import layout
from winkit.core.catalog.models import Catalogs
from winkit.core.errors import IntegrityError, UnattendError, VentoyConfigError, WinKitError
from winkit.core.manifest.manifest import load_manifest, verify_tree
from winkit.core.recipe.validation import validate_recipe
from winkit.core.unattend.generator import check_safety
from winkit.core.ventoy.config import winkit_entries

FAT32_LIMIT = 4 * 1024**3 - 1


@dataclass
class PendriveReport:
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def validate_pendrive(
    root: Path, catalogs: Catalogs, *, profile_id: str = "padrao", file_system: str = "exFAT"
) -> PendriveReport:
    rep = PendriveReport()
    try:
        marker = layout.read_marker(root)
    except WinKitError as exc:
        rep.problems.append(str(exc))
        return rep
    if marker is None:
        rep.problems.append("pendrive sem WinKit\\winkit.marker (rode 'winkit construir')")
        return rep

    _check_recipe(root, catalogs, profile_id, marker.pendrive_id, rep)
    _check_ventoy(root, rep)
    _check_agent(root, rep)
    _check_manifest(root, rep)
    if file_system.upper() in ("FAT32", "FAT"):
        for path in (root / layout.WINKIT).rglob("*"):
            if path.is_file() and path.stat().st_size > FAT32_LIMIT:
                rep.problems.append(f"arquivo acima de 4 GB em FAT32: {path}")
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
        rep.warnings.append("a receita tem o identificador de outro pendrive (rode 'construir')")
    for d in recipe.selected_drivers():
        if not layout.payload(root, d.path).exists():
            rep.problems.append(f"driver {d.id}: pasta ausente ({d.path})")
    for a in recipe.selected_apps():
        if a.installer and a.installer.path and not layout.payload(root, a.installer.path).exists():
            rep.problems.append(f"app {a.id}: instalador ausente ({a.installer.path})")
    for b in recipe.selected_backups():
        if not layout.payload(root, b.data_path).exists():
            rep.problems.append(f"backup {b.id}: pasta ausente ({b.data_path})")


def _check_ventoy(root: Path, rep: PendriveReport) -> None:
    path = root / layout.VENTOY_JSON
    if not path.is_file():
        rep.problems.append("ventoy/ventoy.json não existe")
        return
    try:
        entries = winkit_entries(path.read_text(encoding="utf-8-sig"))
    except VentoyConfigError as exc:
        rep.problems.append(f"ventoy.json inválido: {exc}")
        return
    if not entries:
        rep.warnings.append("nenhuma ISO associada a um modelo do WinKit no ventoy.json")
    for e in entries:
        iso = root / e.image.lstrip("/")
        xml = root / e.template.lstrip("/")
        if not iso.is_file():
            rep.warnings.append(f"ventoy.json cita uma ISO que não existe: {e.image}")
        if not xml.is_file():
            rep.problems.append(f"modelo ausente: {e.template}")
            continue
        try:
            check_safety(xml.read_bytes())
        except UnattendError as exc:
            rep.problems.append(f"{e.template}: {exc}")


def _check_agent(root: Path, rep: PendriveReport) -> None:
    if not (root / layout.BOOTSTRAP).is_file():
        rep.problems.append("WinKit\\Agent\\bootstrap.ps1 ausente")
    version_file = root / layout.AGENT_VERSION
    if version_file.is_file():
        version = version_file.read_text(encoding="utf-8").strip()
        if version != __version__:
            rep.warnings.append(
                f"Agente no pendrive é a versão {version}; o Studio é {__version__}"
            )
    if not (root / layout.AGENT_BIN_DIR / layout.AGENT_EXE_NAME).is_file():
        rep.warnings.append(
            "o executável do Agente não está no pendrive: a instalação só fará a parte do XML"
        )


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
