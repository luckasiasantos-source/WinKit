"""Regras puras do backup do PC (V3-09): tipo de disco, estimativa e avisos."""

from __future__ import annotations

import pytest

from winkit.core import pc_backup as pb


@pytest.mark.parametrize(
    ("media", "bus", "spindle", "kind"),
    [
        (4, 17, 0, "nvme"),
        (4, 11, 0, "ssd"),
        (3, 11, 7200, "hdd"),
        (0, 7, -1, "usb"),  # gaveta USB que esconde o tipo
        (4, 7, 0, "ssd"),  # SSD externo que informa o tipo
        (0, 11, 5400, "hdd"),
        (0, 0, -1, "unknown"),
    ],
)
def test_classify(media: int, bus: int, spindle: int, kind: str) -> None:
    assert pb.classify(media, bus, spindle) == kind


def test_estimate_counts_small_files() -> None:
    few_big = pb.estimate_seconds(1024**3, 10, 110, 6)
    many_small = pb.estimate_seconds(1024**3, 100_000, 110, 6)
    assert many_small > few_big * 5


def test_warnings() -> None:
    files = [
        pb.SourceFile(rel="Videos/filme.mkv", size=5 * 1024**3),
        pb.SourceFile(rel="Docs/a?b.txt", size=1),
        pb.SourceFile(rel="x/" * 130 + "f.txt", size=1),
    ]
    keys = [
        m.key for m in pb.warnings(files, total=10, free=5, file_system="FAT32", same_disk=True)
    ]
    assert keys == [
        "pcbackup.warn_same_disk",
        "pcbackup.warn_space",
        "pcbackup.warn_fat32_big",
        "pcbackup.warn_no_permissions",
        "pcbackup.warn_names",
        "pcbackup.warn_long",
    ]
    assert pb.warnings(files[:1], total=1, free=9, file_system="NTFS", same_disk=False) == []
