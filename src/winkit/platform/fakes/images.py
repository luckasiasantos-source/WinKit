"""Dublê das imagens do Windows e do montador de ISO (V3-11)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from winkit.platform.image_tools import ImageInfo


@dataclass
class FakeImageTools:
    editions: list[ImageInfo] = field(
        default_factory=lambda: [
            ImageInfo(1, "Windows 11 Home", 10**9),
            ImageInfo(6, "Windows 11 Pro", 10**9),
        ]
    )
    apps: list[str] = field(
        default_factory=lambda: ["Microsoft.BingNews", "Microsoft.WindowsCalculator"]
    )
    log: list[tuple[str, ...]] = field(default_factory=list)
    mounted: set[str] = field(default_factory=set)
    fail_on: str | None = None  # operação que falha (para testar o descarte)

    def _do(self, *op: str) -> None:
        if self.fail_on == op[0]:
            raise OSError(f"falhou: {op[0]}")
        self.log.append(op)

    def images(self, wim: Path) -> list[ImageInfo]:
        return list(self.editions)

    def export(self, src: Path, index: int, dest: Path) -> None:
        self._do("export", src.name, str(index))
        with dest.open("ab") as f:
            f.write(f"img{index}".encode())

    def mount(self, wim: Path, index: int, folder: Path) -> None:
        self._do("mount", wim.name, str(index))
        self.mounted.add(str(folder))

    def unmount(self, folder: Path, *, save: bool) -> None:
        self.log.append(("unmount", "save" if save else "discard"))
        self.mounted.discard(str(folder))

    def add_drivers(self, folder: Path, drivers: Path) -> None:
        self._do("drivers", drivers.name)

    def add_package(self, folder: Path, package: Path) -> None:
        self._do("package", package.name)

    def provisioned_apps(self, folder: Path) -> list[str]:
        return list(self.apps)

    def remove_app(self, folder: Path, display_name: str) -> None:
        self._do("remove", display_name)

    def cleanup(self, under: Path) -> int:
        n = len(self.mounted)
        self.mounted.clear()
        return n


@dataclass
class FakeIsoMounter:
    """``mount`` devolve uma pasta que faz o papel da unidade da ISO montada."""

    contents: Path
    mounts: list[str] = field(default_factory=list)

    def mount(self, iso: Path) -> Path:
        self.mounts.append(iso.name)
        return self.contents

    def dismount(self, iso: Path) -> None:
        self.mounts.append("dismount")
