"""Dublês de cópia de sombra (a "cópia de sombra" falsa é a própria pasta de origem)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from winkit.core.errors import VssError
from winkit.core.paths.templates import profile_folders
from winkit.platform.vss import Snapshot


@dataclass
class FakeShadowCopies:
    """``volume_roots`` mapeia "C:" → pasta real que faz o papel do volume nos testes."""

    volume_roots: dict[str, Path] = field(default_factory=dict)
    unsupported: set[str] = field(default_factory=set)
    fail_create: bool = False
    created: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)

    def supported(self, volume: str) -> bool:
        return volume not in self.unsupported

    def create(self, volume: str) -> Snapshot:
        if self.fail_create:
            raise VssError("serviço VSS parado")
        sid = f"{{snap-{len(self.created) + 1}}}"
        self.created.append(sid)
        return Snapshot(
            id=sid, device=f"\\\\?\\GLOBALROOT\\Device\\Shadow{len(self.created)}", volume=volume
        )

    def delete(self, snapshot_id: str) -> None:
        self.deleted.append(snapshot_id)

    def expose(self, snapshot: Snapshot, link: Path) -> Path:
        return self.volume_roots[snapshot.volume]

    def unexpose(self, link: Path) -> None:
        return None


@dataclass
class FakeOldPcFolders:
    """Pastas conhecidas do "PC antigo" como strings do Windows; ``base`` faz o papel do C:."""

    base: Path

    def machine(self) -> dict[str, str]:
        return {
            "PROGRAMDATA": r"C:\ProgramData",
            "PROGRAMFILES": r"C:\Program Files",
            "PROGRAMFILESX86": r"C:\Program Files (x86)",
            "PUBLIC": r"C:\Users\Public",
        }

    def current_user(self) -> dict[str, str]:
        return profile_folders(r"C:\Users\Samuel")

    def default_profile_root(self) -> str:
        return r"C:\Users\Default"

    def windows_dir(self) -> str:
        return r"C:\Windows"

    def volume_root(self, volume: str) -> Path:
        return self.base if volume.upper() == "C:" else self.base.parent / volume[0]
