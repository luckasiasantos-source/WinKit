"""``DiskInspector`` falso: partições e ISOs programadas."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from winkit.core.isos import IsoArch, IsoEdition, IsoInfo
from winkit.core.ventoy.detect import PartitionRow


def ventoy_rows(letter: str = "E", fs: str = "exFAT", free: int = 50 * 2**30) -> list[PartitionRow]:
    return [
        PartitionRow(0, "Samsung SSD", "NVMe", 1, 500 * 2**30, "C", "Windows", "NTFS", 100 * 2**30),
        PartitionRow(2, "SanDisk Ultra", "USB", 1, 100 * 2**30, letter, "Ventoy", fs, free),
        PartitionRow(2, "SanDisk Ultra", "USB", 2, 32 * 2**20, None, "VTOYEFI", "FAT", 0),
    ]


def windows_iso(
    image: str = "/Windows11.iso",
    *,
    lang: str = "pt-BR",
    arch: IsoArch = "amd64",
    build: int = 26100,
) -> IsoInfo:
    return IsoInfo(
        image=image,
        size=6 * 2**30,
        mtime_ns=1,
        is_windows=True,
        os_major=11 if build >= 22000 else 10,
        build=build,
        architecture=arch,
        languages=(lang,),
        default_language=lang,
        editions=(
            IsoEdition(index=1, name="Windows 11 Home"),
            IsoEdition(index=6, name="Windows 11 Pro"),
        ),
    )


@dataclass
class FakeDiskInspector:
    rows: list[PartitionRow] = field(default_factory=ventoy_rows)
    #: nome do arquivo (ex.: "Windows11.iso") → informação; ausente = não é Windows
    isos: dict[str, IsoInfo] = field(default_factory=dict)
    reads: list[str] = field(default_factory=list)

    def list_partitions(self) -> list[PartitionRow]:
        return list(self.rows)

    def read_iso(self, iso_path: Path, image: str) -> IsoInfo:
        self.reads.append(image)
        stat = iso_path.stat()
        info = self.isos.get(iso_path.name)
        if info is None:
            return IsoInfo(
                image=image, size=stat.st_size, mtime_ns=stat.st_mtime_ns, is_windows=False
            )
        return info.model_copy(
            update={"image": image, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        )
