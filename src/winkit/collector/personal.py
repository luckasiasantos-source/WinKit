"""Aparência deste PC (V2-06): valores do HKCU validados e o papel de parede."""

from __future__ import annotations

import ntpath
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from winkit.collector.backups import local_source
from winkit.core import layout
from winkit.core.catalog.models import Catalogs
from winkit.core.fsutil import atomic_write_bytes
from winkit.core.personal import WALLPAPER_KEY, WALLPAPER_VALUE, capture, image_kind
from winkit.core.recipe.models import Recipe
from winkit.platform.registry import Registry

VolumeRoot = Callable[[str], Path]


@dataclass
class PersonalReport:
    values: int = 0
    dropped: list[str] = field(default_factory=list)
    wallpaper: str | None = None
    #: Apresentação de slides ou Destaque do Windows: não são levados.
    wallpaper_skipped: bool = False


def _wallpaper(
    registry: Registry, appdata: str, volume_root: VolumeRoot
) -> tuple[bytes | None, str | None]:
    candidates = []
    current = registry.get("HKCU", WALLPAPER_KEY, WALLPAPER_VALUE)
    if isinstance(current, str) and current:
        candidates.append(current)
    candidates.append(ntpath.join(appdata, "Microsoft", "Windows", "Themes", "TranscodedWallpaper"))
    for path in candidates:
        if len(path) < 3 or path[1] != ":":
            continue
        local = local_source(volume_root(path[:2].upper()), path)
        try:
            data = local.read_bytes()
        except OSError:
            continue
        kind = image_kind(data)
        if kind:
            return data, kind
    return None, None


def collect_personal(
    registry: Registry,
    root: Path,
    recipe: Recipe,
    catalogs: Catalogs,
    *,
    appdata: str,
    volume_root: VolumeRoot,
) -> PersonalReport:
    report = PersonalReport()
    values, dropped = capture(catalogs.personal_groups, lambda k, v: registry.get("HKCU", k, v))
    p = recipe.personal
    p.values = values
    report.values, report.dropped = len(values), dropped
    data, kind = _wallpaper(registry, appdata, volume_root)
    if data is not None and kind is not None:
        rel = f"{layout.appearance_dir(recipe.meta.profile_id)}/papel-de-parede.{kind}"
        atomic_write_bytes(root / rel, data)
        p.wallpaper_file = rel.removeprefix(f"{layout.WINKIT}/")
        report.wallpaper = p.wallpaper_file
    else:
        p.wallpaper_file = None
        report.wallpaper_skipped = True
    if not p.groups:
        p.groups = [
            g.id
            for g in catalogs.personal_groups
            if (g.file and p.wallpaper_file)
            or any(f"{s.key}\\{s.value}" in values for s in g.values)
        ]
    return report


def set_group(recipe: Recipe, group_id: str, selected: bool) -> None:
    groups = [g for g in recipe.personal.groups if g != group_id]
    if selected:
        groups.append(group_id)
    recipe.personal.groups = groups
