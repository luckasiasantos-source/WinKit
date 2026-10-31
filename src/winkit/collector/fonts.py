"""Fontes instaladas no PC atual (V2-07).

- Do usuário: ``HKCU\\...\\Fonts`` (caminho completo, normalmente em ``%LOCALAPPDATA%``).
- Da máquina: ``HKLM\\...\\Fonts`` cujo arquivo foi criado **depois da instalação do Windows**
  (``InstallDate``, um número). Atualizações também instalam fontes: DT-022.
O arquivo só é copiado para o pendrive quando a fonte é marcada.
"""

from __future__ import annotations

import hashlib
import ntpath
import re
import shutil
from collections.abc import Callable
from pathlib import Path

from winkit.collector.backups import local_source
from winkit.core import layout
from winkit.core.fonts import (
    FONT_EXTENSIONS,
    FONTS_KEY,
    INSTALL_KEY,
    USER_FONTS_KEY,
    FontError,
    read_names,
)
from winkit.core.recipe.models import FontItem, Recipe, Scope
from winkit.platform.registry import Registry

VolumeRoot = Callable[[str], Path]


def file_created(path: Path) -> float:
    """Data de criação (no Windows); onde não existe, a de modificação."""
    st = path.stat()
    return float(getattr(st, "st_birthtime", st.st_mtime))


Created = Callable[[Path], float]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", name.lower()).strip("-.")[:70] or "fonte"


def _sources(registry: Registry, windows_dir: str) -> list[tuple[str, Scope]]:
    out: list[tuple[str, Scope]] = []
    for value in registry.values("HKCU", USER_FONTS_KEY).values():
        if isinstance(value, str):
            out.append((value, "user"))
    fonts_dir = ntpath.join(windows_dir, "Fonts")
    for value in registry.values("HKLM", FONTS_KEY).values():
        if isinstance(value, str):
            full = value if ntpath.isabs(value) else ntpath.join(fonts_dir, value)
            out.append((full, "machine"))
    return out


def font_candidates(
    registry: Registry, windows_dir: str, volume_root: VolumeRoot, created: Created = file_created
) -> tuple[list[FontItem], list[str]]:
    """(fontes que dá para levar, arquivos ilegíveis). Nada é copiado aqui."""
    install = registry.get("HKLM", INSTALL_KEY, "InstallDate")
    installed_at = float(install) if isinstance(install, int) else None
    items: list[FontItem] = []
    errors: list[str] = []
    used: set[str] = set()
    for source, origin in _sources(registry, windows_dir):
        if not source.lower().endswith(FONT_EXTENSIONS):
            continue
        local = local_source(volume_root(source[:2].upper()), source)
        try:
            if origin == "machine" and (installed_at is None or created(local) <= installed_at):
                continue  # veio com o Windows (ou não dá para saber): não leva
            names = read_names(local.read_bytes())
            size = local.stat().st_size
        except (OSError, FontError):
            errors.append(source)
            continue
        base = _slug(ntpath.splitext(ntpath.basename(source))[0])
        font_id, n = base, 2
        while font_id in used:
            font_id, n = f"{base}-{n}", n + 1
        used.add(font_id)
        items.append(
            FontItem(
                id=font_id,
                family=names.family,
                full_name=names.full_name,
                source=source,
                origin=origin,
                size=size,
            )
        )
    return items, errors


def collect_fonts(
    registry: Registry,
    windows_dir: str,
    volume_root: VolumeRoot,
    recipe: Recipe,
    created: Created = file_created,
) -> tuple[list[FontItem], list[str]]:
    """Acrescenta à receita as fontes novas (desmarcadas). Devolve (novas, ilegíveis)."""
    found, errors = font_candidates(registry, windows_dir, volume_root, created)
    known = {f.source.casefold() for f in recipe.fonts}
    ids = {f.id for f in recipe.fonts}
    added = []
    for item in found:
        if item.source.casefold() in known:
            continue
        font_id, n = item.id, 2
        while font_id in ids:
            font_id, n = f"{item.id}-{n}", n + 1
        ids.add(font_id)
        added.append(item.model_copy(update={"id": font_id}))
    recipe.fonts = [*recipe.fonts, *added]
    return added, errors


def select_font(
    root: Path, recipe: Recipe, font_id: str, selected: bool, volume_root: VolumeRoot
) -> bool:
    """Marca/desmarca. Ao marcar, copia o arquivo para ``Perfis/<p>/Fontes`` (se ainda não)."""
    item = next((f for f in recipe.fonts if f.id == font_id), None)
    if item is None:
        return False
    if selected and not item.file:
        name = f"{item.id}{ntpath.splitext(item.source)[1].lower()}"
        rel = f"{layout.fonts_dir(recipe.meta.profile_id)}/{name}"
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_source(volume_root(item.source[:2].upper()), item.source), dest)
        item.file = rel.removeprefix(f"{layout.WINKIT}/")
        item.sha256 = hashlib.sha256(dest.read_bytes()).hexdigest()
    item.selected = selected
    return True
