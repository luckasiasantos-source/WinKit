"""Imagens do Windows (``install.wim``, ``boot.wim``) pelo módulo DISM do PowerShell (V3-11, D-048).

Tudo em JSON e números, nunca texto do ``dism.exe`` (R-13). Imagem montada é sempre
desmontada (descartando, se algo falhou) — R-62; montagens órfãs do WinKit são limpas antes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from winkit.platform.powershell import PowerShell

LONG = 7200  # integrar atualizações pode levar mais de uma hora


@dataclass(frozen=True)
class ImageInfo:
    index: int
    name: str
    size: int


class ImageTools(Protocol):
    def images(self, wim: Path) -> list[ImageInfo]: ...

    def export(self, src: Path, index: int, dest: Path) -> None: ...

    def mount(self, wim: Path, index: int, folder: Path) -> None: ...

    def unmount(self, folder: Path, *, save: bool) -> None: ...

    def add_drivers(self, folder: Path, drivers: Path) -> None: ...

    def add_package(self, folder: Path, package: Path) -> None: ...

    def provisioned_apps(self, folder: Path) -> list[str]:
        """``DisplayName`` (ex.: ``Microsoft.BingNews``) → usado com o catálogo de bloatware."""
        ...

    def remove_app(self, folder: Path, display_name: str) -> None: ...

    def cleanup(self, under: Path) -> int:
        """Desmonta (descartando) imagens deixadas montadas dentro de ``under``."""
        ...

    def split(self, wim: Path, swm: Path, size_mb: int) -> None:
        """Divide em ``install.swm``, ``install2.swm``… (FAT32 aceita até 4 GB por arquivo)."""
        ...


class WindowsImageTools:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def images(self, wim: Path) -> list[ImageInfo]:
        out = self._ps.run_json(
            "Get-WindowsImage -ImagePath $Path | ForEach-Object { [pscustomobject]@{"
            " Index = [int]$_.ImageIndex; Name = [string]$_.ImageName; Size = [int64]$_.ImageSize } }",
            {"Path": str(wim)},
            timeout=600,
        )
        return [ImageInfo(int(x["Index"]), str(x["Name"]), int(x.get("Size") or 0)) for x in out]

    def export(self, src: Path, index: int, dest: Path) -> None:
        self._ps.run(
            "Export-WindowsImage -SourceImagePath $Src -SourceIndex $Index"
            " -DestinationImagePath $Dest -CompressionType max -CheckIntegrity | Out-Null",
            {"Src": str(src), "Index": index, "Dest": str(dest)},
            timeout=LONG,
        )

    def mount(self, wim: Path, index: int, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        self._ps.run(
            "Mount-WindowsImage -ImagePath $Path -Index $Index -Path $Dir | Out-Null",
            {"Path": str(wim), "Index": index, "Dir": str(folder)},
            timeout=LONG,
        )

    def unmount(self, folder: Path, *, save: bool) -> None:
        mode = "-Save" if save else "-Discard"
        self._ps.run(
            f"Dismount-WindowsImage -Path $Dir {mode} | Out-Null",
            {"Dir": str(folder)},
            timeout=LONG,
        )

    def add_drivers(self, folder: Path, drivers: Path) -> None:
        self._ps.run(
            "Add-WindowsDriver -Path $Dir -Driver $Drivers -Recurse | Out-Null",
            {"Dir": str(folder), "Drivers": str(drivers)},
            timeout=LONG,
        )

    def add_package(self, folder: Path, package: Path) -> None:
        self._ps.run(
            "Add-WindowsPackage -Path $Dir -PackagePath $Pkg | Out-Null",
            {"Dir": str(folder), "Pkg": str(package)},
            timeout=LONG,
        )

    def provisioned_apps(self, folder: Path) -> list[str]:
        out = self._ps.run_json(
            "Get-AppxProvisionedPackage -Path $Dir | ForEach-Object { [pscustomobject]@{"
            " Name = [string]$_.DisplayName; Package = [string]$_.PackageName } }",
            {"Dir": str(folder)},
            timeout=600,
        )
        return [str(x["Name"]) for x in out]

    def remove_app(self, folder: Path, display_name: str) -> None:
        self._ps.run(
            "Get-AppxProvisionedPackage -Path $Dir | Where-Object DisplayName -eq $Name |"
            " ForEach-Object { Remove-AppxProvisionedPackage -Path $Dir -PackageName $_.PackageName | Out-Null }",
            {"Dir": str(folder), "Name": display_name},
            timeout=600,
        )

    def cleanup(self, under: Path) -> int:
        out = self._ps.run_json(
            "Get-WindowsImage -Mounted | Where-Object { $_.Path -like ($Under + '*') } | ForEach-Object {"
            " Dismount-WindowsImage -Path $_.Path -Discard | Out-Null; [pscustomobject]@{ Path = $_.Path } }",
            {"Under": str(under)},
            timeout=LONG,
        )
        return len(out)

    def split(self, wim: Path, swm: Path, size_mb: int) -> None:
        self._ps.run(
            "Split-WindowsImage -ImagePath $Path -SplitImagePath $Swm -FileSize $Size -CheckIntegrity | Out-Null",
            {"Path": str(wim), "Swm": str(swm), "Size": size_mb},
            timeout=LONG,
        )
