"""Discos de destino do backup e saúde do PC antes de formatar (V3-09, V3-15, V3-16).

Tudo por CIM, em JSON e números (R-13): tipo e barramento do disco, BitLocker, ativação.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from winkit.core.pc_backup import MediaKind, classify
from winkit.platform.powershell import PowerShell


@dataclass(frozen=True)
class Destination:
    letter: str  # "D:"
    label: str
    file_system: str
    size: int
    free: int
    serial: str
    kind: MediaKind
    model: str
    system_disk: bool  # mesmo disco físico do Windows em uso
    locked: bool  # BitLocker bloqueado


@dataclass(frozen=True)
class Health:
    bitlocker_on: bool  # o C: está criptografado
    recovery_keys: int  # quantas chaves de recuperação existem no C:
    activated: bool
    free_system: int


_DESTINATIONS = r"""
$sysDisk = (Get-Partition -DriveLetter ($env:SystemDrive.Substring(0,1))).DiskNumber
$enc = @{}
try {
  Get-CimInstance -Namespace root/cimv2/Security/MicrosoftVolumeEncryption -ClassName Win32_EncryptableVolume |
    ForEach-Object { $enc[$_.DriveLetter] = $_ }
} catch {}
Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -in 'Fixed','Removable' } | ForEach-Object {
  $v = $_
  $part = Get-Partition -DriveLetter $v.DriveLetter -ErrorAction SilentlyContinue
  $disk = if ($part) { Get-Disk -Number $part.DiskNumber -ErrorAction SilentlyContinue }
  $phys = if ($disk) { Get-PhysicalDisk | Where-Object { $_.DeviceId -eq [string]$disk.Number } | Select-Object -First 1 }
  $cimv = Get-CimInstance Win32_Volume -Filter ("DriveLetter='" + $v.DriveLetter + ":'")
  $e = $enc["$($v.DriveLetter):"]
  [pscustomobject]@{
    Letter = "$($v.DriveLetter):"
    Label = [string]$v.FileSystemLabel
    FileSystem = [string]$v.FileSystem
    Size = [int64]$v.Size
    Free = [int64]$v.SizeRemaining
    Serial = if ($cimv.SerialNumber) { '{0:X8}' -f [uint32]$cimv.SerialNumber } else { '' }
    MediaType = if ($phys) { [int]$phys.MediaType } else { 0 }
    BusType = if ($phys) { [int]$phys.BusType } elseif ($disk) { [int]$disk.BusType } else { 0 }
    Spindle = if ($phys) { [int64]$phys.SpindleSpeed } else { -1 }
    Model = if ($disk) { [string]$disk.FriendlyName } else { '' }
    SystemDisk = [bool]($part -and $part.DiskNumber -eq $sysDisk)
    Locked = [bool]($e -and $e.GetLockStatus().LockStatus -eq 1)
  }
}
"""

_HEALTH = r"""
$c = $env:SystemDrive
$e = $null; $keys = 0
try {
  $e = Get-CimInstance -Namespace root/cimv2/Security/MicrosoftVolumeEncryption -ClassName Win32_EncryptableVolume -Filter "DriveLetter='$c'"
  if ($e) { $keys = @($e.GetKeyProtectors(3).VolumeKeyProtectorID).Count }
} catch {}
$lic = Get-CimInstance SoftwareLicensingProduct -Filter "PartialProductKey IS NOT NULL AND ApplicationID='55c92734-d682-4d71-983e-d6ec3f16059f'" |
  Where-Object { $_.LicenseStatus -eq 1 } | Select-Object -First 1
[pscustomobject]@{
  BitLockerOn = [bool]($e -and $e.ProtectionStatus -eq 1)
  RecoveryKeys = [int]$keys
  Activated = [bool]$lic
  FreeSystem = [int64](Get-Volume -DriveLetter $c.Substring(0,1)).SizeRemaining
}
"""

_RECOVERY_KEYS = r"""
$c = $env:SystemDrive
$e = Get-CimInstance -Namespace root/cimv2/Security/MicrosoftVolumeEncryption -ClassName Win32_EncryptableVolume -Filter "DriveLetter='$c'"
foreach ($id in @($e.GetKeyProtectors(3).VolumeKeyProtectorID)) {
  [pscustomobject]@{ Id = [string]$id; Password = [string]$e.GetKeyProtectorNumericalPassword($id).NumericalPassword }
}
"""


def _destination(item: dict[str, Any]) -> Destination:
    return Destination(
        letter=str(item["Letter"]),
        label=str(item.get("Label") or ""),
        file_system=str(item.get("FileSystem") or ""),
        size=int(item.get("Size") or 0),
        free=int(item.get("Free") or 0),
        serial=str(item.get("Serial") or ""),
        kind=classify(
            int(item.get("MediaType") or 0),
            int(item.get("BusType") or 0),
            int(item.get("Spindle") or -1),
        ),
        model=str(item.get("Model") or ""),
        system_disk=bool(item.get("SystemDisk")),
        locked=bool(item.get("Locked")),
    )


class DiskInfo(Protocol):
    def destinations(self) -> list[Destination]: ...

    def health(self) -> Health: ...

    def recovery_keys(self) -> list[tuple[str, str]]: ...


class WindowsDiskInfo:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def destinations(self) -> list[Destination]:
        return [_destination(x) for x in self._ps.run_json(_DESTINATIONS, timeout=120)]

    def health(self) -> Health:
        out = self._ps.run_json(_HEALTH, timeout=120)
        x = out[0] if out else {}
        return Health(
            bitlocker_on=bool(x.get("BitLockerOn")),
            recovery_keys=int(x.get("RecoveryKeys") or 0),
            activated=bool(x.get("Activated")),
            free_system=int(x.get("FreeSystem") or 0),
        )

    def recovery_keys(self) -> list[tuple[str, str]]:
        """(id, chave de 48 dígitos). Segredo: nunca vai para log (R-53)."""
        return [
            (str(x["Id"]), str(x["Password"]))
            for x in self._ps.run_json(_RECOVERY_KEYS, timeout=120)
        ]
