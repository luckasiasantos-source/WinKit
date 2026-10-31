"""Escolha do pendrive de destino (PLANO.md §8.1, D-034).

Dois tipos: **Ventoy** (várias ISOs, XML injetado pelo plugin ``auto_install``) e **pendrive
de instalação comum** (Rufus ou Ferramenta de Criação de Mídia: ``autounattend.xml`` na raiz).
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from winkit.core.errors import PendriveError
from winkit.core.media import SetupTarget, find_setup_targets, has_setup_files
from winkit.core.ventoy.detect import VentoyTarget, find_ventoy_targets
from winkit.i18n import t
from winkit.platform.disks import DiskInspector

TargetKind = Literal["ventoy", "setup"]
AnyDrive = VentoyTarget | SetupTarget


@dataclass(frozen=True)
class Target:
    root: Path
    file_system: str
    free: int
    #: Rótulo do disco; ``None`` = pasta comum usada como pendrive.
    disk_label: str | None = None
    kind: TargetKind = "ventoy"

    @property
    def description(self) -> str:
        """Montado na hora, no idioma atual (troca de idioma no Studio)."""
        if self.disk_label is None:
            return t("pendrive.folder_description", path=str(self.root))
        return self.disk_label

    @property
    def is_fat32(self) -> bool:
        return self.file_system.upper() in ("FAT32", "FAT")


def _default_root(letter: str) -> Path:
    return Path(letter + "\\")


def list_targets(
    inspector: DiskInspector, volume_root: Callable[[str], Path] = _default_root
) -> list[AnyDrive]:
    """Pendrives Ventoy e pendrives de instalação comuns conectados."""
    rows = inspector.list_partitions()
    setup = find_setup_targets(rows, lambda letter: has_setup_files(volume_root(letter)))
    return [*find_ventoy_targets(rows), *setup]


def from_drive(v: AnyDrive) -> Target:
    return Target(
        root=Path(v.root),
        file_system=v.file_system,
        free=v.free,
        disk_label=f"{v.data_letter} {v.disk_name} ({v.bus_type}, {v.file_system})",
        kind="setup" if v.kind == "setup" else "ventoy",
    )


#: Nome antigo, mantido para quem só usa Ventoy.
from_ventoy = from_drive


def from_folder(folder: Path, file_system: str = "exFAT") -> Target:
    """Usa uma pasta como se fosse o pendrive (testes e simulação). Com os arquivos do
    instalador do Windows, ela vale como pendrive comum."""
    folder.mkdir(parents=True, exist_ok=True)
    return Target(
        root=folder,
        file_system=file_system,
        free=shutil.disk_usage(folder).free,
        kind="setup" if has_setup_files(folder) else "ventoy",
    )


def resolve_target(
    inspector: DiskInspector,
    letter: str | None,
    volume_root: Callable[[str], Path] = _default_root,
) -> Target:
    drives = list_targets(inspector, volume_root)
    if letter:
        wanted = letter.strip().rstrip(":\\/").upper() + ":"
        for v in drives:
            if v.data_letter == wanted:
                return from_drive(v)
        raise PendriveError(t("pendrive.not_found_letter", letter=wanted))
    if not drives:
        raise PendriveError(t("pendrive.none"))
    if len(drives) > 1:
        raise PendriveError(t("pendrive.many"))
    return from_drive(drives[0])
