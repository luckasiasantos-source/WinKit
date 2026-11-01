"""Backup do PC para outro disco: copiar, conferir e trazer de volta (V3-09/10, D-051).

Cópia aditiva arquivo a arquivo (para ter progresso e conferência): nunca apaga nada, nem na
origem nem no destino. Cada arquivo é relido no destino e comparado pelo SHA-256; o manifesto
diz o que já foi conferido, então refazer ou retomar copia só o que mudou ou faltou.
"""

from __future__ import annotations

import hashlib
import os
import time
import uuid
import zipfile
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path

from winkit.collector.backups import local_source
from winkit.core.errors import PathTemplateError, WinKitError
from winkit.core.fsutil import atomic_write_text
from winkit.core.paths import templates
from winkit.core.pc_backup import (  # noqa: F401 — reexporta o que a CLI e o Studio usam
    BACKUP_DIR,
    CHUNK,
    MANIFEST,
    BackupProgress,
    BackupSource,
    ManifestFile,
    PcBackupManifest,
    RestoreReport,
    SourceFile,
    find_backups,
    load_manifest,
    restore,
    restore_targets,
    sha_copy,
)
from winkit.core.text import slugify

DEFAULT_FOLDERS = ("DESKTOP", "DOCUMENTS", "PICTURES", "VIDEOS", "MUSIC", "DOWNLOADS")
SnapshotRoot = Callable[[str], Path | None]


class BackupStopped(WinKitError):  # noqa: N818 — estado, não erro
    """Parado a pedido; o manifesto guarda o que já foi conferido."""


def make_sources(literals: list[str], folders: Mapping[str, str]) -> list[BackupSource]:
    """Pastas escolhidas → origens com rótulo único e molde para o usuário novo."""
    out: list[BackupSource] = []
    used: set[str] = set()
    for literal in literals:
        base = slugify(Path(literal.replace("\\", "/")).name or "disco") or "pasta"
        label, n = base, 2
        while label in used:
            label, n = f"{base}-{n}", n + 1
        used.add(label)
        try:
            template: str | None = templates.to_template(literal, folders).template
        except PathTemplateError:
            template = None
        out.append(BackupSource(label=label, literal=literal, template=template))
    return out


def default_literals(folders: Mapping[str, str]) -> list[str]:
    return [folders[k] for k in DEFAULT_FOLDERS if k in folders]


def scan(root: Path) -> list[SourceFile]:
    files: list[SourceFile] = []
    for dirpath, dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        dirnames[:] = [
            d for d in dirnames if not (base / d).is_symlink() and not _is_junction(base / d)
        ]
        for name in filenames:
            p = base / name
            try:
                size = p.stat().st_size
            except OSError:
                continue
            files.append(SourceFile(rel=p.relative_to(root).as_posix(), size=size))
    return files


def _is_junction(p: Path) -> bool:
    try:
        return p.is_junction()
    except OSError:
        return False


def measure_speed(
    folder: Path, clock: Callable[[], float] = time.perf_counter
) -> tuple[float, float]:
    """Mede o destino de verdade: (MB/s em arquivo grande, ms por arquivo pequeno)."""
    probe = folder / ".winkit-medida"
    probe.mkdir(parents=True, exist_ok=True)
    try:
        block = os.urandom(1024 * 1024)
        start = clock()
        with (probe / "grande.bin").open("wb") as f:
            for _ in range(32):
                f.write(block)
            f.flush()
            os.fsync(f.fileno())
        big = max(clock() - start, 1e-6)
        start = clock()
        for i in range(100):
            with (probe / f"p{i}.bin").open("wb") as f:
                f.write(block[:4096])
        small = max(clock() - start, 1e-6)
        return 32 / big, small * 1000 / 100
    finally:
        for p in probe.iterdir():
            p.unlink(missing_ok=True)
        probe.rmdir()


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(CHUNK):
            h.update(block)
    return h.hexdigest()


def backup_base(dest_root: Path, computer: str) -> Path:
    return dest_root / BACKUP_DIR / (slugify(computer) or "pc")


def run_backup(
    sources: list[BackupSource],
    dest_root: Path,
    *,
    computer: str,
    now: datetime,
    zip_mode: bool = False,
    source_root: Callable[[str], Path] = Path,
    snapshot_root: SnapshotRoot | None = None,
    progress: Callable[[BackupProgress], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> PcBackupManifest:
    base = backup_base(dest_root, computer)
    base.mkdir(parents=True, exist_ok=True)
    marker = dest_root / BACKUP_DIR / "winkit-backup.json"
    if not marker.is_file():
        atomic_write_text(marker, f'{{"winkit_backup": "{uuid.uuid4()}"}}\n')
    manifest = load_manifest(base) or PcBackupManifest(
        backup_id=str(uuid.uuid4()), computer=computer, updated_at=now, zip=zip_mode
    )
    known = {s.label: s for s in manifest.sources}
    for s in sources:
        known[s.label] = s
    manifest.sources = list(known.values())
    manifest.failed = {}
    plan = [(s, f) for s in sources for f in scan(source_root(s.literal))]
    state = BackupProgress(total_bytes=sum(f.size for _, f in plan), total_files=len(plan))
    archive = (
        zipfile.ZipFile(base / "backup.zip", "a", zipfile.ZIP_DEFLATED, allowZip64=True)
        if zip_mode
        else None
    )

    def save() -> None:
        manifest.updated_at = now
        atomic_write_text(base / MANIFEST, manifest.model_dump_json(indent=2))

    try:
        for i, (source, f) in enumerate(plan):
            key = f"{source.label}/{f.rel}"
            src = source_root(source.literal) / f.rel
            state.current = key
            try:
                st = src.stat()
                old = manifest.files.get(key)
                if not (old and old.size == st.st_size and old.mtime_ns == st.st_mtime_ns):
                    sha = _copy_one(
                        src,
                        source,
                        rel=f.rel,
                        base=base,
                        key=key,
                        archive=archive,
                        snapshot_root=snapshot_root,
                    )
                    manifest.files[key] = ManifestFile(
                        size=st.st_size, mtime_ns=st.st_mtime_ns, sha256=sha
                    )
            except (OSError, WinKitError) as exc:
                manifest.failed[key] = str(exc)
            state.done_bytes += f.size
            state.done_files += 1
            if progress is not None:
                progress(state)
            if i % 200 == 199:
                save()
            if should_stop is not None and should_stop():
                save()
                raise BackupStopped(str(base))
    finally:
        if archive is not None:
            archive.close()
    save()
    return manifest


def _copy_one(
    src: Path,
    source: BackupSource,
    *,
    rel: str,
    base: Path,
    key: str,
    archive: zipfile.ZipFile | None,
    snapshot_root: SnapshotRoot | None,
) -> str:
    try:
        handle = src.open("rb")
    except PermissionError:
        # arquivo aberto (ex.: Outlook): lê da cópia de sombra do volume (M6)
        root = snapshot_root(source.literal[:2].upper()) if snapshot_root else None
        if root is None:
            raise
        handle = local_source(root, str(Path(source.literal) / rel).replace("/", "\\")).open("rb")
    with handle:
        if archive is not None:
            h = hashlib.sha256()
            with archive.open(key, "w", force_zip64=True) as out:
                while block := handle.read(CHUNK):
                    out.write(block)
                    h.update(block)
            sha = h.hexdigest()
            with archive.open(key) as back:  # conferência: relê do .zip
                check = hashlib.sha256()
                while block := back.read(CHUNK):
                    check.update(block)
            if check.hexdigest() != sha:
                raise WinKitError("a cópia no .zip não confere")
            return sha
        dst = base / key
        sha = sha_copy(lambda: handle.read(CHUNK), dst)
    if _sha_file(dst) != sha:  # conferência: relê do destino
        raise WinKitError("a cópia não confere com o original")
    return sha
