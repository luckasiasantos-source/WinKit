"""Montagem **somente leitura** de uma ISO (V2-08: fonte offline do .NET 3.5).

A ISO nunca é modificada (D-002): ``Mount-DiskImage -Access ReadOnly`` e desmontagem
sempre em ``finally``.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from winkit.core.errors import PlatformError
from winkit.platform.powershell import PowerShell

_MOUNT = r"""
$img = Mount-DiskImage -ImagePath $p.Path -Access ReadOnly -StorageType ISO -PassThru
$vol = $img | Get-Volume
[string]$vol.DriveLetter
"""

_DISMOUNT = r"""
Dismount-DiskImage -ImagePath $p.Path | Out-Null
'ok'
"""


class IsoMounter(Protocol):
    def mount(self, iso: Path) -> Path:
        """Monta como leitura e devolve a raiz da unidade (ex.: ``F:\\``)."""
        ...

    def dismount(self, iso: Path) -> None: ...


class WindowsIsoMounter:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def mount(self, iso: Path) -> Path:
        out = self._ps.run_json(_MOUNT, {"Path": str(iso)}, timeout=300)
        letter = str(out[0]).strip() if out else ""
        if len(letter) != 1 or not letter.isalpha():
            raise PlatformError(f"a ISO foi montada sem letra de unidade: {iso}")
        return Path(f"{letter}:\\")

    def dismount(self, iso: Path) -> None:
        self._ps.run_json(_DISMOUNT, {"Path": str(iso)}, timeout=300)


@contextlib.contextmanager
def mounted_iso(mounter: IsoMounter, iso: Path) -> Iterator[Path]:
    root = mounter.mount(iso)
    try:
        yield root
    finally:
        mounter.dismount(iso)
