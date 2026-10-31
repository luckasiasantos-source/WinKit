"""Leitura das ISOs do pendrive, com cache (PLANO.md §8.2)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from winkit.core.errors import WinKitError
from winkit.core.fsutil import atomic_write_text
from winkit.core.isos import IsoInfo
from winkit.core.layout import VENTOY_DIR, WINKIT
from winkit.platform.disks import DiskInspector

log = logging.getLogger(__name__)
_CACHE = TypeAdapter(dict[str, IsoInfo])
_SKIP_DIRS = {WINKIT.casefold(), VENTOY_DIR.casefold()}


def find_iso_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0].casefold() in _SKIP_DIRS:
            continue
        if path.is_file() and path.suffix.casefold() == ".iso":
            found.append(path)
    return sorted(found, key=lambda p: p.relative_to(root).as_posix().casefold())


def image_path(root: Path, iso: Path) -> str:
    """Caminho no formato do ``ventoy.json``: ``/pasta/arquivo.iso``."""
    return "/" + iso.relative_to(root).as_posix()


def _load_cache(path: Path | None) -> dict[str, IsoInfo]:
    if path is None or not path.is_file():
        return {}
    try:
        return _CACHE.validate_python(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, ValidationError):
        log.warning("cache de ISOs inválido; ignorando %s", path)
        return {}


def scan_isos(
    root: Path, inspector: DiskInspector, cache_path: Path | None = None
) -> tuple[list[IsoInfo], list[tuple[str, str]]]:
    """Devolve (ISOs lidas, [(imagem, erro)]). Uma ISO ilegível não interrompe as outras."""
    cache = _load_cache(cache_path)
    infos: list[IsoInfo] = []
    errors: list[tuple[str, str]] = []
    new_cache: dict[str, IsoInfo] = {}
    for iso in find_iso_files(root):
        image = image_path(root, iso)
        stat = iso.stat()
        key = f"{iso.resolve()}"
        cached = cache.get(key)
        if cached and cached.size == stat.st_size and cached.mtime_ns == stat.st_mtime_ns:
            info = cached.model_copy(update={"image": image})
        else:
            try:
                info = inspector.read_iso(iso, image)
            except (WinKitError, OSError) as exc:
                errors.append((image, str(exc)))
                continue
        new_cache[key] = info
        infos.append(info)
    if cache_path is not None:
        cache.update(new_cache)
        atomic_write_text(cache_path, _CACHE.dump_json(cache, indent=1).decode("utf-8") + "\n")
    return infos, errors
