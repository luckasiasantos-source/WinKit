"""O único lugar que apaga e formata um disco: o pendrive escolhido (V3-13, D-045, R-60).

Antes de apagar, o disco é relido e passa por ``core.usb_safety.refusal_reasons`` de novo.
Tudo por CIM e cmdlets de armazenamento, em JSON (R-13).
"""

from __future__ import annotations

from typing import Any, Protocol

from winkit.core.errors import WinKitError
from winkit.core.usb_safety import UsbDisk, refusal_reasons
from winkit.i18n import render
from winkit.platform.powershell import PowerShell

#: FAT32 pelo Windows vai só até 32 GB; o instalador cabe com folga.
FAT32_PARTITION = 32 * 1024**3

_LIST = r"""
Get-Disk | Where-Object { $_.BusType -eq 'USB' -or [int]$_.BusType -eq 7 } | ForEach-Object {
  $d = $_
  $letters = @(Get-Partition -DiskNumber $d.Number -ErrorAction SilentlyContinue |
    Where-Object DriveLetter | ForEach-Object { "$($_.DriveLetter):" })
  [pscustomobject]@{
    Number = [int]$d.Number; Serial = [string]$d.SerialNumber; Model = [string]$d.FriendlyName
    Size = [int64]$d.Size; Bus = [int]$d.BusType; System = [bool]$d.IsSystem; Boot = [bool]$d.IsBoot
    Letters = $letters
  }
}
"""

_PREPARE = r"""
Clear-Disk -Number $Number -RemoveData -RemoveOEM -Confirm:$false
Initialize-Disk -Number $Number -PartitionStyle $Style -ErrorAction SilentlyContinue
Set-Disk -Number $Number -PartitionStyle $Style -ErrorAction SilentlyContinue
$size = [Math]::Min($Max, (Get-Disk -Number $Number).LargestFreeExtent)
$p = if ($Style -eq 'MBR') { New-Partition -DiskNumber $Number -Size $size -IsActive -AssignDriveLetter }
     else { New-Partition -DiskNumber $Number -Size $size -AssignDriveLetter }
Format-Volume -Partition $p -FileSystem FAT32 -NewFileSystemLabel $Label -Confirm:$false | Out-Null
[pscustomobject]@{ Letter = "$((Get-Partition -DiskNumber $Number -PartitionNumber $p.PartitionNumber).DriveLetter):" }
"""


def _disk(x: dict[str, Any]) -> UsbDisk:
    letters = x.get("Letters") or []
    return UsbDisk(
        number=int(x["Number"]),
        serial=str(x.get("Serial") or "").strip(),
        model=str(x.get("Model") or ""),
        size=int(x.get("Size") or 0),
        bus_type=int(x.get("Bus") or 0),
        is_system=bool(x.get("System")),
        is_boot=bool(x.get("Boot")),
        letters=tuple(letters if isinstance(letters, list) else [letters]),
    )


class UsbWriter(Protocol):
    def usb_disks(self) -> list[UsbDisk]: ...

    def prepare(self, shown: UsbDisk, typed_letter: str, *, style: str, label: str) -> str:
        """Confere as travas, apaga, particiona e formata; devolve a letra nova ("E:")."""
        ...


class WindowsUsbWriter:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def usb_disks(self) -> list[UsbDisk]:
        return [_disk(x) for x in self._ps.run_json(_LIST, timeout=120)]

    def prepare(self, shown: UsbDisk, typed_letter: str, *, style: str, label: str) -> str:
        current = next((d for d in self.usb_disks() if d.number == shown.number), None)
        reasons = refusal_reasons(current, shown, typed_letter)
        if reasons:
            raise WinKitError("; ".join(render(r) for r in reasons))
        out = self._ps.run_json(
            _PREPARE,
            {"Number": shown.number, "Style": style, "Label": label[:11], "Max": FAT32_PARTITION},
            timeout=1800,
        )
        letter = str(out[0].get("Letter", "")) if out else ""
        if len(letter) != 2:
            raise WinKitError(
                "o pendrive foi formatado, mas não recebeu letra; tire e coloque de novo"
            )
        return letter
