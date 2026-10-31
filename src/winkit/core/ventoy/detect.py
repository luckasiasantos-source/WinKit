"""Detecção do pendrive Ventoy a partir da lista de partições (PLANO.md §8.1)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

VTOYEFI_LABEL = "VTOYEFI"


@dataclass(frozen=True)
class PartitionRow:
    disk_number: int
    disk_name: str
    bus_type: str
    partition_number: int
    size: int
    drive_letter: str | None
    label: str | None
    file_system: str | None
    size_remaining: int | None


@dataclass(frozen=True)
class VentoyTarget:
    disk_number: int
    disk_name: str
    bus_type: str
    data_letter: str  # "E:"
    data_label: str | None
    file_system: str  # "exFAT", "NTFS", "FAT32"...
    size: int
    free: int
    kind: str = "ventoy"

    @property
    def root(self) -> str:
        return self.data_letter + "\\"

    @property
    def is_fat32(self) -> bool:
        return self.file_system.upper() in ("FAT32", "FAT")


def find_ventoy_targets(rows: list[PartitionRow]) -> list[VentoyTarget]:
    """Um disco é Ventoy se tiver uma partição ``VTOYEFI`` e outra de dados com letra."""
    by_disk: dict[int, list[PartitionRow]] = defaultdict(list)
    for row in rows:
        by_disk[row.disk_number].append(row)
    targets: list[VentoyTarget] = []
    for disk, parts in sorted(by_disk.items()):
        if not any((p.label or "").upper() == VTOYEFI_LABEL for p in parts):
            continue
        candidates: list[tuple[PartitionRow, str, str]] = []
        for p in parts:
            if (p.label or "").upper() == VTOYEFI_LABEL or not p.drive_letter or not p.file_system:
                continue
            candidates.append((p, p.drive_letter, p.file_system))
        if not candidates:
            continue
        main, letter, fs = max(candidates, key=lambda c: c[0].size)
        targets.append(
            VentoyTarget(
                disk_number=disk,
                disk_name=main.disk_name,
                bus_type=main.bus_type,
                data_letter=letter.rstrip(":").upper() + ":",
                data_label=main.label,
                file_system=fs,
                size=main.size,
                free=main.size_remaining or 0,
            )
        )
    return targets
