"""Escolha do pendrive de destino (PLANO.md §8.1)."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from winkit.core.errors import PendriveError
from winkit.core.ventoy.detect import VentoyTarget, find_ventoy_targets
from winkit.i18n import t
from winkit.platform.disks import DiskInspector


@dataclass(frozen=True)
class Target:
    root: Path
    file_system: str
    free: int
    description: str

    @property
    def is_fat32(self) -> bool:
        return self.file_system.upper() in ("FAT32", "FAT")


def list_targets(inspector: DiskInspector) -> list[VentoyTarget]:
    return find_ventoy_targets(inspector.list_partitions())


def from_ventoy(v: VentoyTarget) -> Target:
    return Target(
        root=Path(v.root),
        file_system=v.file_system,
        free=v.free,
        description=f"{v.data_letter} {v.disk_name} ({v.bus_type}, {v.file_system})",
    )


def from_folder(folder: Path, file_system: str = "exFAT") -> Target:
    """Usa uma pasta comum como se fosse o pendrive (testes e simulação)."""
    folder.mkdir(parents=True, exist_ok=True)
    return Target(
        root=folder,
        file_system=file_system,
        free=shutil.disk_usage(folder).free,
        description=f"pasta {folder}",
    )


def resolve_target(inspector: DiskInspector, letter: str | None) -> Target:
    targets = list_targets(inspector)
    if letter:
        wanted = letter.strip().rstrip(":\\/").upper() + ":"
        for v in targets:
            if v.data_letter == wanted:
                return from_ventoy(v)
        raise PendriveError(t("pendrive.not_found_letter", letter=wanted))
    if not targets:
        raise PendriveError(t("pendrive.none"))
    if len(targets) > 1:
        raise PendriveError(t("pendrive.many"))
    return from_ventoy(targets[0])
