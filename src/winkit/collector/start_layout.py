"""Iniciar e barra de tarefas deste PC (V2-04).

Os fixados da barra são os atalhos de ``User Pinned\\TaskBar``; cada um é ligado ao atalho de
mesmo nome no menu Iniciar (o Windows 11 só aceita fixar atalhos que estão lá). Apps da Store
fixados na barra não deixam atalho nessa pasta e ficam de fora (DT-024).
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Mapping
from pathlib import Path

from winkit.collector.backups import local_source
from winkit.core import layout
from winkit.core.recipe.models import PinRef, Recipe
from winkit.core.start_layout import START2_DIR, START_MENU, TASKBAR_PINNED

VolumeRoot = Callable[[str], Path]
#: (pasta conhecida, variável usada no molde do Windows).
_ROOTS = (("APPDATA", "%APPDATA%"), ("PROGRAMDATA", "%ALLUSERSPROFILE%"))


def _local(path: str, volume_root: VolumeRoot) -> Path:
    return local_source(volume_root(path[:2].upper()), path)


def start_menu_links(folders: Mapping[str, str], volume_root: VolumeRoot) -> list[PinRef]:
    out: dict[str, PinRef] = {}
    for var, env in _ROOTS:
        base = folders.get(var)
        if not base:
            continue
        root = _local(f"{base}\\{START_MENU}", volume_root)
        for lnk in sorted(root.rglob("*.lnk")):
            rel = "\\".join(lnk.relative_to(root).parts)
            name = lnk.stem
            if name.casefold() in out:
                continue
            out[name.casefold()] = PinRef(
                kind="desktop_link",
                value=f"{env}\\{START_MENU}\\{rel}",
                name=name,
                selected=False,
            )
    return sorted(out.values(), key=lambda p: p.name.casefold())


def collect_start_layout(
    recipe: Recipe,
    root: Path,
    folders: Mapping[str, str],
    volume_root: VolumeRoot,
    *,
    build: int | None,
) -> tuple[int, list[str]]:
    """Lê fixados e o ``start2.bin``. Devolve (fixados da barra achados, os sem atalho)."""
    links = start_menu_links(folders, volume_root)
    by_name = {p.name.casefold(): p for p in links}
    pinned_dir = _local(f"{folders['APPDATA']}\\{TASKBAR_PINNED}", volume_root)
    taskbar: list[PinRef] = []
    orphans: list[str] = []
    for lnk in sorted(pinned_dir.glob("*.lnk")) if pinned_dir.is_dir() else []:
        match = by_name.get(lnk.stem.casefold())
        if match is None:
            orphans.append(lnk.stem)
        else:
            taskbar.append(match.model_copy(update={"selected": True}))
    s = recipe.start_layout
    s.taskbar_pins = taskbar
    s.start_pins = links
    start2 = _local(f"{folders['LOCALAPPDATA']}\\" + "\\".join(START2_DIR[2:]), volume_root)
    start2 = start2 / "start2.bin"
    if start2.is_file():
        rel = f"{layout.start_dir(recipe.meta.profile_id)}/start2.bin"
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(start2, root / rel)
        s.start_file = rel.removeprefix(f"{layout.WINKIT}/")
        s.source_build = build
    if s.mode == "off":
        s.mode = "list"
    return len(taskbar), orphans
