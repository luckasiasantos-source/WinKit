"""Manifesto de arquivos do pendrive (PLANO.md §8.5, R-22).

Guarda tamanho, data de modificação e SHA-256 de ``Agent/``, ``Apps/`` e ``Drivers/``.
Serve para a sincronização incremental (só copia o que mudou) e para verificar
integridade antes de executar um instalador.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from winkit.core.errors import IntegrityError

MANIFEST_SCHEMA_VERSION = 1
_CHUNK = 1024 * 1024


class FileEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    size: int
    mtime_ns: int
    sha256: str


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = MANIFEST_SCHEMA_VERSION
    files: dict[str, FileEntry] = Field(default_factory=dict)

    def total_size(self, prefix: str = "") -> int:
        return sum(e.size for k, e in self.files.items() if k.startswith(prefix))


@dataclass(frozen=True)
class ManifestDiff:
    added: tuple[str, ...]
    changed: tuple[str, ...]
    removed: tuple[str, ...]

    @property
    def empty(self) -> bool:
        return not (self.added or self.changed or self.removed)


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def scan(root: Path, subdirs: Iterable[str], previous: Manifest | None = None) -> Manifest:
    """Lê os arquivos de ``root/<subdir>`` e monta o manifesto.

    Se um arquivo tem o mesmo tamanho e data do manifesto anterior, o hash é reaproveitado
    (evita reler gigabytes de instaladores a cada sincronização).
    """
    files: dict[str, FileEntry] = {}
    for sub in subdirs:
        base = root / sub
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            rel = path.relative_to(root).as_posix()
            stat = path.stat()
            old = previous.files.get(rel) if previous else None
            if old and old.size == stat.st_size and old.mtime_ns == stat.st_mtime_ns:
                files[rel] = old
            else:
                files[rel] = FileEntry(
                    size=stat.st_size, mtime_ns=stat.st_mtime_ns, sha256=hash_file(path)
                )
    return Manifest(files=files)


def diff(old: Manifest, new: Manifest) -> ManifestDiff:
    added = sorted(set(new.files) - set(old.files))
    removed = sorted(set(old.files) - set(new.files))
    changed = sorted(
        k
        for k in set(old.files) & set(new.files)
        if old.files[k].sha256 != new.files[k].sha256 or old.files[k].size != new.files[k].size
    )
    return ManifestDiff(tuple(added), tuple(changed), tuple(removed))


def verify(root: Path, rel: str, manifest: Manifest) -> None:
    """Lança ``IntegrityError`` se o arquivo não existir ou não bater com o manifesto."""
    entry = manifest.files.get(rel)
    if entry is None:
        raise IntegrityError(f"arquivo fora do manifesto: {rel}")
    path = root / rel
    if not path.is_file():
        raise IntegrityError(f"arquivo ausente: {rel}")
    if path.stat().st_size != entry.size or hash_file(path) != entry.sha256:
        raise IntegrityError(f"arquivo alterado ou corrompido: {rel}")


def verify_tree(root: Path, prefix: str, manifest: Manifest) -> None:
    """Verifica todos os arquivos do manifesto que começam com ``prefix``."""
    for rel in sorted(k for k in manifest.files if k.startswith(prefix)):
        verify(root, rel, manifest)


def dump_manifest(manifest: Manifest) -> str:
    return manifest.model_dump_json(indent=1) + "\n"


def load_manifest(text: str) -> Manifest:
    try:
        return Manifest.model_validate(json.loads(text))
    except (ValueError, ValidationError) as exc:
        raise IntegrityError(f"manifesto corrompido: {exc}") from exc
