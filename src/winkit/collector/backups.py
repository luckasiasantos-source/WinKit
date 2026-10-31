"""Backups de pastas e arquivos de configuração (PLANO.md §7.3, §7.4; itens 12, 16, 28, 30)."""

from __future__ import annotations

import contextlib
import fnmatch
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from winkit.core import layout
from winkit.core.catalog.models import Catalogs
from winkit.core.errors import PathTemplateError, VssError, WinKitError
from winkit.core.fsutil import atomic_write_text
from winkit.core.paths import templates
from winkit.core.recipe.models import (
    AfterInstall,
    AppItem,
    BackupItem,
    BackupKind,
    ConflictPolicy,
    Recipe,
    ShortcutSpec,
)
from winkit.core.text import human_size, slugify
from winkit.i18n import t, tn
from winkit.platform.copy import Copier, tree_stats
from winkit.platform.vss import PendingSnapshots, ShadowCopies, Snapshot

MANY_FILES = 5000
MARGIN_BYTES = 500 * 1024**2

#: Converte a letra de um volume ("C:") na pasta local que dá acesso a ele.
VolumeRoot = Callable[[str], Path]


def windows_volume_root(volume: str) -> Path:
    return Path(volume + "\\")


def local_source(root: Path, literal: str) -> Path:
    """Caminho literal do Windows → caminho local, a partir da raiz do volume."""
    rest = literal[3:] if len(literal) > 2 and literal[1] == ":" else literal
    return root.joinpath(*[p for p in rest.split("\\") if p])


# ------------------------------------------------------------------ sugestões (item 28)
@dataclass(frozen=True)
class Suggestion:
    app_id: str
    app_name: str
    template: str
    kind: BackupKind
    recommended: bool
    exists: bool
    files: int
    size: int
    warning: str | None
    exclude: tuple[str, ...]


def suggest(
    recipe: Recipe,
    catalogs: Catalogs,
    old_folders: Mapping[str, str],
    volume_root: VolumeRoot = windows_volume_root,
) -> list[Suggestion]:
    out: list[Suggestion] = []
    dpapi = {d.id: d.what for d in catalogs.dpapi_patterns}
    for app in recipe.selected_apps():
        entry = catalogs.app(app.id)
        if entry is None:
            continue
        for cp in entry.config_paths:
            try:
                literal = templates.resolve(cp.template, old_folders)
            except PathTemplateError:
                continue
            src = local_source(volume_root(literal[:2].upper()), literal)
            excludes = [*catalogs.default_excludes, *cp.exclude]
            exists = src.exists()
            stats = tree_stats(src, excludes) if exists else None
            out.append(
                Suggestion(
                    app_id=app.id,
                    app_name=app.name,
                    template=cp.template,
                    kind=cp.kind,
                    recommended=cp.recommended,
                    exists=exists,
                    files=stats.files if stats else 0,
                    size=stats.bytes if stats else 0,
                    warning=dpapi.get(cp.warning) if cp.warning else None,
                    exclude=tuple(cp.exclude),
                )
            )
    return out


# ------------------------------------------------------------------ adicionar
def _unique_id(recipe: Recipe, base: str) -> str:
    existing = {b.id for b in recipe.backups}
    candidate, n = base, 2
    while candidate in existing:
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def add_backup(
    recipe: Recipe,
    catalogs: Catalogs,
    *,
    name: str,
    template: str | None = None,
    literal: str | None = None,
    old_folders: Mapping[str, str] | None = None,
    windows_dir: str | None = None,
    kind: BackupKind = "folder",
    on_conflict: ConflictPolicy = "merge",
    decide_at_runtime: bool = False,
    related_app: str | None = None,
    extra_excludes: list[str] | None = None,
) -> tuple[BackupItem, str | None]:
    """Cria o item na receita. Devolve (item, aviso de caminho absoluto, se houver)."""
    warning = None
    if template is None:
        if literal is None or old_folders is None:
            raise WinKitError("informe o caminho")
        result = templates.to_template(literal, old_folders, windows_dir=windows_dir)
        template, warning = result.template, result.warning
    templates.parse(template)
    # mesmo molde já na receita: devolve o existente
    for b in recipe.backups:
        if b.template.casefold() == template.casefold():
            return b, warning
    backup_id = _unique_id(recipe, slugify(name, max_length=40))
    item = BackupItem(
        id=backup_id,
        name=name,
        selected=True,
        kind=kind,
        template=template,
        data_path=f"Perfis/{recipe.meta.profile_id}/Backups/{backup_id}/dados",
        exclude=[*catalogs.default_excludes, *(extra_excludes or [])] if kind == "folder" else [],
        on_conflict=on_conflict,
        related_app=related_app,
        decide_at_runtime=decide_at_runtime,
    )
    recipe.backups.append(item)
    return item, warning


def add_suggestion(recipe: Recipe, catalogs: Catalogs, s: Suggestion) -> BackupItem:
    name = f"{s.app_name} — {Path(s.template.replace(chr(92), '/')).name or 'configurações'}"
    item, _ = add_backup(
        recipe,
        catalogs,
        name=name,
        template=s.template,
        kind=s.kind,
        related_app=s.app_id,
        extra_excludes=list(s.exclude),
    )
    entry = catalogs.app(s.app_id)
    app = recipe.app(s.app_id)
    if (
        entry
        and entry.installer_wipes_config
        and app
        and item.id not in app.restore_backups_after_install
    ):
        app.restore_backups_after_install.append(item.id)
    return item


def add_portable_app(
    recipe: Recipe,
    catalogs: Catalogs,
    *,
    literal_folder: str,
    old_folders: Mapping[str, str],
    name: str,
    exe: str,
    windows_dir: str | None = None,
) -> tuple[AppItem, BackupItem]:
    """App portátil = backup da pasta + atalho no menu Iniciar (R12)."""
    item, _ = add_backup(
        recipe,
        catalogs,
        name=t("collect.portable_name", name=name),
        literal=literal_folder,
        old_folders=old_folders,
        windows_dir=windows_dir,
    )
    app_id = slugify(name, max_length=40)
    target = f"{item.template}\\{exe.lstrip(chr(92))}"
    app = AppItem(
        id=app_id,
        name=name,
        selected=True,
        source="portable",
        portable_backup=item.id,
        after_install=AfterInstall(shortcuts=[ShortcutSpec(name=name, target=target)]),
    )
    recipe.apps = [a for a in recipe.apps if a.id != app_id] + [app]
    item.related_app = app_id
    return app, item


# ------------------------------------------------------------------ captura
@dataclass
class CaptureItemReport:
    backup_id: str
    ok: bool
    files: int = 0
    size: int = 0
    used_vss: bool = False
    warnings: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class CaptureReport:
    items: list[CaptureItemReport] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(i.ok for i in self.items)


def dpapi_warnings(folder: Path, catalogs: Catalogs) -> list[str]:
    found: list[str] = []
    rels = [p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()]
    for pattern in catalogs.dpapi_patterns:
        glob = pattern.glob.replace("\\", "/")
        bare = glob.removeprefix("**/")
        hit = next((r for r in rels if fnmatch.fnmatch(r, glob) or fnmatch.fnmatch(r, bare)), None)
        if hit is not None:
            found.append(t("collect.dpapi_warning", path=hit, what=pattern.what))
    return found


class _Snapshots:
    """Uma cópia de sombra por volume; sempre apagadas no fim (R-17)."""

    def __init__(
        self, vss: ShadowCopies, pending: PendingSnapshots, link_base: Path, notes: list[str]
    ) -> None:
        self.vss, self.pending, self.link_base, self.notes = vss, pending, link_base, notes
        self.active: dict[str, tuple[Snapshot, Path, Path]] = {}
        self.failed: set[str] = set()

    def root(self, volume: str) -> Path | None:
        if volume in self.active:
            return self.active[volume][2]
        if volume in self.failed:
            return None
        if not self.vss.supported(volume):
            self.failed.add(volume)
            self.notes.append(t("collect.vss_not_ntfs", volume=volume))
            return None
        try:
            snap = self.vss.create(volume)
        except VssError as exc:
            self.failed.add(volume)
            self.notes.append(t("collect.vss_unavailable", volume=volume, detail=str(exc)))
            return None
        self.pending.add(snap.id)
        link = self.link_base / f"snap-{volume[0].lower()}"
        exposed = self.vss.expose(snap, link)
        self.active[volume] = (snap, link, exposed)
        return exposed

    def close(self) -> None:
        for snap, link, _ in self.active.values():
            with contextlib.suppress(Exception):
                self.vss.unexpose(link)
            try:
                self.vss.delete(snap.id)
                self.pending.remove(snap.id)
            except Exception as exc:  # noqa: BLE001 — fica pendente para a próxima execução
                self.notes.append(t("collect.vss_not_deleted", id=snap.id, detail=exc))
        self.active.clear()


def cleanup_orphan_snapshots(vss: ShadowCopies, pending: PendingSnapshots) -> int:
    removed = 0
    for sid in pending.load():
        try:
            vss.delete(sid)
            pending.remove(sid)
            removed += 1
        except Exception:  # noqa: BLE001, S112 — continua pendente; nova tentativa na próxima vez
            continue
    return removed


def capture(
    root: Path,
    recipe: Recipe,
    catalogs: Catalogs,
    *,
    copier: Copier,
    vss: ShadowCopies,
    pending: PendingSnapshots,
    old_folders: Mapping[str, str],
    link_base: Path,
    free_bytes: int,
    use_vss: bool = True,
    only: set[str] | None = None,
    volume_root: VolumeRoot = windows_volume_root,
    now: Callable[[], datetime] = datetime.now,
) -> CaptureReport:
    report = CaptureReport()
    cleanup_orphan_snapshots(vss, pending)
    items = [b for b in recipe.selected_backups() if only is None or b.id in only]

    # estimativa de espaço antes de copiar qualquer coisa (item 25)
    plan: list[tuple[BackupItem, str]] = []
    needed = 0
    for b in items:
        try:
            literal = templates.resolve(b.template, old_folders)
        except PathTemplateError as exc:
            report.items.append(CaptureItemReport(b.id, False, message=str(exc)))
            continue
        src = local_source(volume_root(literal[:2].upper()), literal)
        if not src.exists():
            report.items.append(
                CaptureItemReport(b.id, False, message=t("collect.source_missing", path=literal))
            )
            continue
        needed += tree_stats(src, b.exclude).bytes
        plan.append((b, literal))
    if needed > free_bytes - MARGIN_BYTES:
        raise WinKitError(
            t(
                "pendrive.no_space",
                needed=human_size(needed),
                free=human_size(free_bytes),
                margin=human_size(MARGIN_BYTES),
            )
        )

    snaps = _Snapshots(vss, pending, link_base, report.notes)
    try:
        for b, literal in plan:
            report.items.append(
                _capture_one(
                    root,
                    b,
                    literal,
                    catalogs,
                    copier=copier,
                    snaps=snaps if use_vss else None,
                    volume_root=volume_root,
                    now=now,
                )
            )
    finally:
        snaps.close()
    return report


def _capture_one(
    root: Path,
    b: BackupItem,
    literal: str,
    catalogs: Catalogs,
    *,
    copier: Copier,
    snaps: _Snapshots | None,
    volume_root: VolumeRoot,
    now: Callable[[], datetime],
) -> CaptureItemReport:
    volume = literal[:2].upper()
    vss_root = snaps.root(volume) if snaps is not None else None
    src = local_source(vss_root or volume_root(volume), literal)
    dst = layout.payload(root, b.data_path)
    log = dst.parent / "copia.log"  # fora de "dados", que o espelho recria
    try:
        copier.mirror(src, dst, excludes=b.exclude, log=log)
    except WinKitError as exc:
        return CaptureItemReport(b.id, False, message=str(exc))
    stats = tree_stats(dst, [])
    warnings = dpapi_warnings(dst, catalogs) if dst.is_dir() else []
    if stats.files > MANY_FILES:
        warnings.append(t("collect.many_files", path=literal, count=stats.files))
    b.warnings = sorted(set(b.warnings) | set(warnings))
    info = {
        "id": b.id,
        "template": b.template,
        "kind": b.kind,
        "captured_at": now().astimezone().isoformat(),
        "source_literal": literal,
        "file_count": stats.files,
        "size_bytes": stats.bytes,
        "used_vss": vss_root is not None,
        "exclude": b.exclude,
        "warnings": b.warnings,
    }
    atomic_write_text(
        dst.parent / "item.json", json.dumps(info, ensure_ascii=False, indent=2) + "\n"
    )
    return CaptureItemReport(
        b.id,
        True,
        files=stats.files,
        size=stats.bytes,
        used_vss=vss_root is not None,
        warnings=warnings,
        message=tn("collect.captured", stats.files, size=human_size(stats.bytes)),
    )
