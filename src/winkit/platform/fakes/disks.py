"""``DiskInspector`` falso: partições e ISOs programadas."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from winkit.core.errors import PlatformError
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
    #: Pendrive comum: o que ``Get-WindowsImage`` devolveria (``None`` = falha na leitura).
    setup_image: IsoInfo | None = field(default_factory=lambda: windows_iso("/install.wim"))

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

    def read_setup_image(self, image_path: Path) -> IsoInfo:
        self.reads.append(image_path.name)
        if self.setup_image is None:
            raise PlatformError("Get-WindowsImage falhou")
        return self.setup_image.model_copy(update={"image": "/" + image_path.name})


def setup_rows(letter: str = "F", fs: str = "NTFS") -> list[PartitionRow]:
    """Pendrive gravado pelo Rufus (NTFS + partição UEFI_NTFS) ao lado do disco interno."""
    return [
        PartitionRow(0, "Samsung SSD", "NVMe", 1, 500 * 2**30, "C", "Windows", "NTFS", 100 * 2**30),
        PartitionRow(
            3, "Kingston DataTraveler", "USB", 1, 32 * 2**30, letter, "CCCOMA", fs, 20 * 2**30
        ),
        PartitionRow(3, "Kingston DataTraveler", "USB", 2, 1 * 2**20, "G", "UEFI_NTFS", "FAT", 0),
    ]


def make_setup_folder(root: Path, image: str = "install.wim") -> Path:
    """Simula os arquivos de um pendrive de instalação do Windows."""
    (root / "sources").mkdir(parents=True, exist_ok=True)
    (root / "efi" / "boot").mkdir(parents=True, exist_ok=True)
    (root / "setup.exe").write_bytes(b"MZ")
    (root / "bootmgr").write_bytes(b"x")
    (root / "sources" / "boot.wim").write_bytes(b"wim")
    (root / "sources" / image).write_bytes(b"wim")
    (root / "efi" / "boot" / "bootx64.efi").write_bytes(b"efi")
    return root


@dataclass
class FakeIsoLinks:
    """Link da ISO (V3-08): devolve ``url`` e registra os pedidos."""

    url_value: str = "https://software.download.prss.microsoft.com/Win11_Portuguese_x64.iso"
    calls: list[tuple[str, str, str]] = field(default_factory=list)

    def url(self, version: str, arch: str, language: str) -> str:
        self.calls.append((version, arch, language))
        return self.url_value


@dataclass
class FakeDiskInfo:
    """Discos de destino e saúde do PC (V3-09/15/16)."""

    dests: list[Any] = field(default_factory=list)
    health_value: Any = None
    keys: list[tuple[str, str]] = field(default_factory=list)

    def destinations(self) -> list[Any]:
        return list(self.dests)

    def health(self) -> Any:
        from winkit.platform.disk_info import Health  # noqa: PLC0415

        return self.health_value or Health(
            bitlocker_on=False, recovery_keys=0, activated=True, free_system=50 * 1024**3
        )

    def recovery_keys(self) -> list[tuple[str, str]]:
        return list(self.keys)
