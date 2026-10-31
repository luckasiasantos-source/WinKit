"""Discos, partições e leitura de ISO (somente leitura — D-002). Exige administrador."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from winkit.core.isos import DISM_ARCH, IsoEdition, IsoInfo, build_from_version, language_code
from winkit.core.isos import os_major_from_build as _os_major
from winkit.core.ventoy.detect import PartitionRow
from winkit.platform.powershell import PowerShell

_LIST_PARTITIONS = r"""
foreach ($d in @(Get-Disk)) {
    foreach ($p in @(Get-Partition -DiskNumber $d.Number -ErrorAction SilentlyContinue)) {
        $v = $null
        try { $v = $p | Get-Volume -ErrorAction Stop } catch { }
        $letter = $null
        if ($p.DriveLetter -and [int][char]$p.DriveLetter -ne 0) {
            $letter = [string]$p.DriveLetter
        }
        [pscustomobject]@{
            DiskNumber = [int]$d.Number
            DiskName = [string]$d.FriendlyName
            BusType = [string]$d.BusType
            PartitionNumber = [int]$p.PartitionNumber
            Size = [int64]$p.Size
            DriveLetter = $letter
            Label = $(if ($v) { [string]$v.FileSystemLabel } else { $null })
            FileSystem = $(if ($v) { [string]$v.FileSystem } else { $null })
            SizeRemaining = $(if ($v) { [int64]$v.SizeRemaining } else { $null })
        }
    }
}
"""

_READ_ISO = r"""
$img = Mount-DiskImage -ImagePath $p.Path -Access ReadOnly -StorageType ISO -PassThru
try {
    $letter = $null
    for ($i = 0; $i -lt 20 -and -not $letter; $i++) {
        $letter = ($img | Get-Volume -ErrorAction SilentlyContinue).DriveLetter
        if (-not $letter) { Start-Sleep -Milliseconds 250 }
    }
    if (-not $letter) { throw 'a ISO foi montada, mas não recebeu letra de unidade' }
    $wim = "$($letter):\sources\install.wim"
    if (-not (Test-Path -LiteralPath $wim)) { $wim = "$($letter):\sources\install.esd" }
    if (-not (Test-Path -LiteralPath $wim)) {
        [pscustomobject]@{ Windows = $false }
    } else {
        $images = @(Get-WindowsImage -ImagePath $wim)
        $first = Get-WindowsImage -ImagePath $wim -Index $images[0].ImageIndex
        [pscustomobject]@{
            Windows = $true
            Version = [string]$first.Version
            Architecture = [int]$first.Architecture
            Languages = @($first.Languages | ForEach-Object { [string]$_ })
            DefaultLanguageIndex = [int]$first.DefaultLanguageIndex
            Editions = @($images | ForEach-Object {
                [pscustomobject]@{ Index = [int]$_.ImageIndex; Name = [string]$_.ImageName } })
        }
    }
} finally {
    Dismount-DiskImage -ImagePath $p.Path | Out-Null
}
"""


#: Pendrive comum (D-034): a imagem já está aberta no pendrive; só lê os metadados (H16).
_READ_SETUP_IMAGE = r"""
$images = @(Get-WindowsImage -ImagePath $p.Path)
$first = Get-WindowsImage -ImagePath $p.Path -Index $images[0].ImageIndex
[pscustomobject]@{
    Windows = $true
    Version = [string]$first.Version
    Architecture = [int]$first.Architecture
    Languages = @($first.Languages | ForEach-Object { [string]$_ })
    DefaultLanguageIndex = [int]$first.DefaultLanguageIndex
    Editions = @($images | ForEach-Object {
        [pscustomobject]@{ Index = [int]$_.ImageIndex; Name = [string]$_.ImageName } })
}
"""


class DiskInspector(Protocol):
    def list_partitions(self) -> list[PartitionRow]: ...

    def read_iso(self, iso_path: Path, image: str) -> IsoInfo: ...

    def read_setup_image(self, image_path: Path) -> IsoInfo:
        """Metadados de ``sources\\install.wim|esd|swm`` de um pendrive comum (só leitura)."""
        ...


def partition_from_json(item: dict[str, Any]) -> PartitionRow:
    return PartitionRow(
        disk_number=int(item["DiskNumber"]),
        disk_name=str(item.get("DiskName") or ""),
        bus_type=str(item.get("BusType") or ""),
        partition_number=int(item["PartitionNumber"]),
        size=int(item.get("Size") or 0),
        drive_letter=item.get("DriveLetter") or None,
        label=item.get("Label") or None,
        file_system=item.get("FileSystem") or None,
        size_remaining=item.get("SizeRemaining"),
    )


def iso_from_json(item: dict[str, Any], *, image: str, size: int, mtime_ns: int) -> IsoInfo:
    if not item.get("Windows"):
        return IsoInfo(image=image, size=size, mtime_ns=mtime_ns, is_windows=False)
    build = build_from_version(str(item.get("Version") or ""))
    langs = tuple(c for c in (language_code(x) for x in item.get("Languages") or []) if c)
    raw_langs = list(item.get("Languages") or [])
    default_idx = int(item.get("DefaultLanguageIndex") or 0)
    default = language_code(raw_langs[default_idx]) if 0 <= default_idx < len(raw_langs) else None
    return IsoInfo(
        image=image,
        size=size,
        mtime_ns=mtime_ns,
        is_windows=True,
        os_major=_os_major(build),
        build=build,
        architecture=DISM_ARCH.get(int(item.get("Architecture", -1)), "unknown"),
        languages=langs,
        default_language=default or (langs[0] if langs else None),
        editions=tuple(
            IsoEdition(index=int(e["Index"]), name=str(e["Name"]))
            for e in item.get("Editions") or []
        ),
    )


class WindowsDiskInspector:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def list_partitions(self) -> list[PartitionRow]:
        return [partition_from_json(x) for x in self._ps.run_json(_LIST_PARTITIONS, timeout=120)]

    def read_iso(self, iso_path: Path, image: str) -> IsoInfo:
        stat = iso_path.stat()
        out = self._ps.run_json(_READ_ISO, {"Path": str(iso_path)}, timeout=600)
        item = out[0] if out else {"Windows": False}
        return iso_from_json(item, image=image, size=stat.st_size, mtime_ns=stat.st_mtime_ns)

    def read_setup_image(self, image_path: Path) -> IsoInfo:
        stat = image_path.stat()
        out = self._ps.run_json(_READ_SETUP_IMAGE, {"Path": str(image_path)}, timeout=600)
        item = out[0] if out else {"Windows": False}
        return iso_from_json(
            item, image="/" + image_path.name, size=stat.st_size, mtime_ns=stat.st_mtime_ns
        )
