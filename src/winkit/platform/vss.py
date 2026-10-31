"""Cópias de sombra (VSS) para capturar arquivos em uso (PLANO.md §7.4.2, D-006)."""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from winkit.core.errors import VssError
from winkit.core.fsutil import atomic_write_text
from winkit.platform.powershell import PowerShell

_CREATE = r"""
$r = Invoke-CimMethod -ClassName Win32_ShadowCopy -MethodName Create -Arguments @{ Volume = $p.Volume; Context = 'ClientAccessible' }
if ($r.ReturnValue -ne 0) { throw "Win32_ShadowCopy.Create retornou $($r.ReturnValue)" }
$s = Get-CimInstance Win32_ShadowCopy -Filter "ID='$($r.ShadowID)'"
[pscustomobject]@{ Id = [string]$r.ShadowID; Device = [string]$s.DeviceObject }
"""

_DELETE = r"""
$s = Get-CimInstance Win32_ShadowCopy -Filter "ID='$($p.Id)'"
if ($s) { Remove-CimInstance -InputObject $s; 'removed' } else { 'absent' }
"""

_VOLUME_INFO = r"""
$v = Get-Volume -DriveLetter $p.Letter -ErrorAction Stop
$part = Get-Partition -DriveLetter $p.Letter -ErrorAction SilentlyContinue
$disk = if ($part) { Get-Disk -Number $part.DiskNumber -ErrorAction SilentlyContinue } else { $null }
[pscustomobject]@{ FileSystem = [string]$v.FileSystem; BusType = $(if ($disk) { [string]$disk.BusType } else { '' }) }
"""


@dataclass(frozen=True)
class Snapshot:
    id: str
    device: str  # \\?\GLOBALROOT\Device\HarddiskVolumeShadowCopyN
    volume: str  # "C:"


class ShadowCopies(Protocol):
    def supported(self, volume: str) -> bool: ...

    def create(self, volume: str) -> Snapshot: ...

    def delete(self, snapshot_id: str) -> None: ...

    def expose(self, snapshot: Snapshot, link: Path) -> Path:
        """Cria um link de diretório para a cópia de sombra e devolve a raiz acessível."""
        ...

    def unexpose(self, link: Path) -> None: ...


class PendingSnapshots:
    """Lista em disco de cópias de sombra ainda não apagadas (limpeza na próxima execução)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[str]:
        if not self.path.is_file():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return [str(x) for x in data] if isinstance(data, list) else []
        except ValueError:
            return []

    def add(self, snapshot_id: str) -> None:
        ids = self.load()
        if snapshot_id not in ids:
            ids.append(snapshot_id)
        atomic_write_text(self.path, json.dumps(ids))

    def remove(self, snapshot_id: str) -> None:
        ids = [x for x in self.load() if x != snapshot_id]
        atomic_write_text(self.path, json.dumps(ids))


class WindowsShadowCopies:  # pragma: no cover — CI Windows / PC real
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def supported(self, volume: str) -> bool:
        try:
            info = self._ps.run_json(_VOLUME_INFO, {"Letter": volume[0]}, timeout=120)
        except Exception:  # noqa: BLE001 — sem informação = sem VSS
            return False
        if not info:
            return False
        fs = str(info[0].get("FileSystem") or "").upper()
        bus = str(info[0].get("BusType") or "").upper()
        return fs in ("NTFS", "REFS") and bus not in ("USB", "SD", "MMC")

    def create(self, volume: str) -> Snapshot:
        try:
            out = self._ps.run_json(_CREATE, {"Volume": volume.rstrip("\\") + "\\"}, timeout=600)
        except Exception as exc:
            raise VssError(f"não foi possível criar a cópia de sombra de {volume}: {exc}") from exc
        if not out:
            raise VssError("Win32_ShadowCopy não devolveu dados")
        return Snapshot(id=str(out[0]["Id"]), device=str(out[0]["Device"]), volume=volume)

    def delete(self, snapshot_id: str) -> None:
        self._ps.run_json(_DELETE, {"Id": snapshot_id}, timeout=300)

    def expose(self, snapshot: Snapshot, link: Path) -> Path:
        link.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(FileNotFoundError):
            link.rmdir()
        # A barra final no alvo é obrigatória para links de cópia de sombra (H6).
        link.symlink_to(snapshot.device + "\\", target_is_directory=True)
        return link

    def unexpose(self, link: Path) -> None:
        with contextlib.suppress(FileNotFoundError):
            link.rmdir()
