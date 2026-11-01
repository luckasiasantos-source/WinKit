"""Backup do PC para outro disco (V3-09/10, D-051): regras puras, sem Windows.

Cópia simples e aditiva: nunca apaga nada, sem versões antigas, sem senha. O manifesto guarda
o tamanho e o SHA-256 de cada arquivo conferido; refazer o backup copia só o que mudou.
"""

from __future__ import annotations

import hashlib
import re
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from winkit.core.errors import PathTemplateError, WinKitError
from winkit.core.paths import templates
from winkit.i18n.msg import Msg, msg

CHUNK = 4 * 1024 * 1024

MediaKind = Literal["nvme", "ssd", "hdd", "usb", "unknown"]
#: Escrita sequencial típica (MB/s) e custo por arquivo pequeno (ms), antes de medir.
TYPICAL: dict[str, tuple[float, float]] = {
    "nvme": (1500, 0.3),
    "ssd": (450, 0.6),
    "hdd": (110, 6.0),
    "usb": (30, 15.0),
    "unknown": (60, 8.0),
}
FAT32_MAX = 4 * 1024**3 - 1
LONG_PATH = 250
_INVALID = re.compile(r'[<>:"|?*\x00-\x1f]')
MARKER = "WinKit-backup/winkit-backup.json"
BACKUP_DIR = "WinKit-backup"
MANIFEST = "manifesto.json"


def classify(media_type: int, bus_type: int, spindle: int) -> MediaKind:
    """CIM ``MSFT_PhysicalDisk`` → tipo. Gaveta USB costuma esconder o tipo: ``usb``, sem chute."""
    if bus_type == 17:  # NVMe
        return "nvme"
    if bus_type == 7 and media_type == 0:
        return "usb"
    if media_type == 4 or (media_type == 0 and spindle == 0 and bus_type != 7):
        return "ssd"
    if media_type == 3 or spindle not in (0, -1, 0xFFFFFFFF):
        return "hdd"
    return "usb" if bus_type == 7 else "unknown"


def estimate_seconds(total_bytes: int, files: int, mb_per_s: float, ms_per_file: float) -> float:
    return total_bytes / (mb_per_s * 1024**2) + files * ms_per_file / 1000


class SourceFile(BaseModel):
    model_config = ConfigDict(frozen=True)
    rel: str  # caminho relativo dentro da origem, com "/"
    size: int


def warnings(
    files: list[SourceFile], *, total: int, free: int, file_system: str, same_disk: bool
) -> list[Msg]:
    out: list[Msg] = []
    if same_disk:
        out.append(msg("pcbackup.warn_same_disk"))
    if total > free:
        out.append(msg("pcbackup.warn_space", need=total, free=free))
    fs = file_system.upper()
    if fs == "FAT32":
        big = [f.rel for f in files if f.size > FAT32_MAX]
        if big:
            out.append(msg("pcbackup.warn_fat32_big", n=len(big), first=big[0]))
    if fs in ("FAT32", "EXFAT"):
        out.append(msg("pcbackup.warn_no_permissions"))
        bad = [f.rel for f in files if _INVALID.search(f.rel.replace("/", ""))]
        if bad:
            out.append(msg("pcbackup.warn_names", n=len(bad), first=bad[0]))
    long = [f.rel for f in files if len(f.rel) > LONG_PATH]
    if long:
        out.append(msg("pcbackup.warn_long", n=len(long), first=long[0]))
    return out


class BackupSource(BaseModel):
    label: str  # pasta dentro do backup
    literal: str  # caminho original no PC antigo
    #: Molde (``{DOCUMENTS}\\...``) para restaurar no usuário novo; ``None`` = mesmo caminho.
    template: str | None = None


class ManifestFile(BaseModel):
    size: int
    mtime_ns: int
    sha256: str


class PcBackupManifest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    schema_version: int = 1
    backup_id: str
    computer: str
    updated_at: datetime
    zip: bool = False
    sources: list[BackupSource] = Field(default_factory=list)
    #: "<label>/<rel>" → arquivo conferido.
    files: dict[str, ManifestFile] = Field(default_factory=dict)
    failed: dict[str, str] = Field(default_factory=dict)

    @property
    def total_bytes(self) -> int:
        return sum(f.size for f in self.files.values())


# ------------------------------------------------------------------ trazer de volta (V3-10)
@dataclass
class BackupProgress:
    done_bytes: int = 0
    total_bytes: int = 0
    done_files: int = 0
    total_files: int = 0
    current: str = ""


@dataclass
class RestoreReport:
    copied: int = 0
    kept: int = 0  # já existiam no destino: nunca sobrescritos
    failed: dict[str, str] = field(default_factory=dict)


def sha_copy(read: Callable[[], bytes], dst: Path) -> str:
    h = hashlib.sha256()
    part = dst.with_name(dst.name + ".part")
    dst.parent.mkdir(parents=True, exist_ok=True)
    with part.open("wb") as out:
        while block := read():
            out.write(block)
            h.update(block)
    part.replace(dst)
    return h.hexdigest()


def load_manifest(base: Path) -> PcBackupManifest | None:
    path = base / MANIFEST
    if not path.is_file():
        return None
    return PcBackupManifest.model_validate_json(path.read_text(encoding="utf-8"))


def find_backups(roots: list[Path]) -> list[tuple[Path, PcBackupManifest]]:
    found = []
    for root in roots:
        folder = root / BACKUP_DIR
        if not folder.is_dir():
            continue
        for base in sorted(p for p in folder.iterdir() if p.is_dir()):
            manifest = load_manifest(base)
            if manifest is not None:
                found.append((base, manifest))
    return found


def restore_targets(manifest: PcBackupManifest, folders: Mapping[str, str]) -> dict[str, str]:
    """Rótulo → pasta de destino no PC atual (molde do usuário novo, ou o caminho original)."""
    out = {}
    for s in manifest.sources:
        try:
            out[s.label] = templates.resolve(s.template, folders) if s.template else s.literal
        except PathTemplateError:
            out[s.label] = s.literal
    return out


def restore(
    base: Path,
    manifest: PcBackupManifest,
    targets: Mapping[str, str],
    *,
    target_root: Callable[[str], Path] = Path,
    progress: Callable[[BackupProgress], None] | None = None,
) -> RestoreReport:
    """Soma ao que existe: arquivo que já existe no destino nunca é sobrescrito (D-007)."""
    report = RestoreReport()
    state = BackupProgress(total_bytes=manifest.total_bytes, total_files=len(manifest.files))
    archive = zipfile.ZipFile(base / "backup.zip") if manifest.zip else None
    try:
        for key, entry in manifest.files.items():
            label, rel = key.split("/", 1)
            dst = target_root(targets[label]) / rel
            state.current = key
            try:
                if dst.exists():
                    report.kept += 1
                else:
                    if archive is not None:
                        with archive.open(key) as src:
                            sha = sha_copy(lambda s=src: s.read(CHUNK), dst)  # type: ignore[misc]
                    else:
                        with (base / key).open("rb") as src2:
                            sha = sha_copy(lambda s=src2: s.read(CHUNK), dst)  # type: ignore[misc]
                    if sha != entry.sha256:
                        dst.unlink()
                        raise WinKitError("o arquivo do backup não confere")
                    report.copied += 1
            except (OSError, WinKitError, KeyError) as exc:
                report.failed[key] = str(exc)
            state.done_bytes += entry.size
            state.done_files += 1
            if progress is not None:
                progress(state)
    finally:
        if archive is not None:
            archive.close()
    return report
