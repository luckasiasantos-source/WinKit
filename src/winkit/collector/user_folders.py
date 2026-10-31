"""Pastas do usuário (V2-14): detectar as que já estão em outro disco e "Copiar agora".

"Copiar agora" usa só a política ``merge`` (D-007): nunca move, nunca espelha, nunca apaga.
"""

from __future__ import annotations

import ntpath
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from winkit.collector.backups import local_source
from winkit.core.recipe.models import Recipe, UserFolderId, UserFolders
from winkit.core.user_folders import (
    ORDER,
    SHELL_FOLDERS_KEY,
    TEMPLATE_VARS,
    VALUE_NAMES,
    expand_user,
    generalize_user,
)
from winkit.core.volumes import VolumeInfo, ref_for, resolve, split
from winkit.platform.copy import Copier
from winkit.platform.registry import Registry
from winkit.platform.volumes import Volumes

VolumeRoot = Callable[[str], Path]


def _expand(value: str, env: Mapping[str, str]) -> str:
    for var, path in env.items():
        value = value.replace(f"%{var}%", path).replace(f"%{var.lower()}%", path)
    return value


def detect(
    registry: Registry, volumes: list[VolumeInfo], profile: str, username: str
) -> UserFolders | None:
    """As pastas que já apontam para um disco que não é o do sistema (o mais usado ganha)."""
    env = {"USERPROFILE": profile, "USERNAME": username}
    found: dict[str, list[tuple[UserFolderId, str]]] = {}
    for folder in ORDER:
        raw = registry.get("HKCU", SHELL_FOLDERS_KEY, VALUE_NAMES[folder])
        if not isinstance(raw, str):
            continue
        hit = split(_expand(raw, env), volumes)
        if hit is None or hit[0].is_system or not hit[1]:
            continue
        found.setdefault(hit[0].serial, []).append((folder, generalize_user(hit[1], username)))
    if not found:
        return None
    serial, items = max(found.items(), key=lambda kv: len(kv[1]))
    volume = next(v for v in volumes if v.serial == serial)
    return UserFolders(enabled=True, volume=ref_for(volume), folders=dict(items))


def system_serial(volumes: list[VolumeInfo]) -> str | None:
    return next((v.serial for v in volumes if v.is_system), None)


@dataclass
class CopyReport:
    copied: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def copy_now(
    recipe: Recipe,
    volumes: Volumes,
    copier: Copier,
    current_user: Mapping[str, str],
    volume_root: VolumeRoot,
) -> CopyReport:
    """Copia as pastas do C: para o destino (merge). A origem fica intacta."""
    uf = recipe.user_folders
    report = CopyReport()
    target = resolve(uf.volume, volumes.volumes()) if uf.volume else None
    if target is None or target.letter is None:
        raise FileNotFoundError("volume das pastas do usuário não encontrado")
    username = recipe.windows.account.username
    for folder, rel in uf.folders.items():
        src_win = current_user.get(TEMPLATE_VARS[folder])
        if not src_win:
            continue
        src = local_source(volume_root(src_win[:2].upper()), src_win)
        if not src.is_dir():
            report.missing.append(folder)
            continue
        dest = volumes.root(target.letter).joinpath(*expand_user(rel, username).split("\\"))
        if ntpath.normcase(str(src)) == ntpath.normcase(str(dest)):
            continue
        copier.restore_tree(src, dest, policy="merge", log=None)
        report.copied.append(folder)
    return report
