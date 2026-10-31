"""Pendrive de instalação comum, gravado pelo Rufus ou pela Ferramenta de Criação de Mídia
(V2-01, D-034).

Reconhecido pelos arquivos do instalador; o WinKit grava só ``autounattend.xml`` na raiz e a
pasta ``WinKit``. Nunca formata, nunca toca em ``sources``, ``boot`` ou ``efi`` (R-19).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from winkit.core.ventoy.detect import VTOYEFI_LABEL, PartitionRow

UNATTEND = "autounattend.xml"
UNATTEND_BACKUP = "autounattend.xml.winkit-bak"
#: O Rufus pode gravar respostas aqui também (H17); seriam aplicadas depois das nossas.
OEM_UNATTEND = "sources/$OEM$/$$/Panther/unattend.xml"
IMAGE_NAMES = ("install.wim", "install.esd", "install.swm")
#: Só discos removíveis: nunca escrever num disco interno por engano.
REMOVABLE_BUSES = frozenset({"USB", "SD", "MMC"})
MARK = "WinKit"


def image_file(root: Path) -> Path | None:
    for name in IMAGE_NAMES:
        path = root / "sources" / name
        if path.is_file():
            return path
    return None


def has_setup_files(root: Path) -> bool:
    """``setup.exe`` + ``sources\\boot.wim`` + uma imagem de instalação na raiz."""
    try:
        return (
            (root / "setup.exe").is_file()
            and (root / "sources" / "boot.wim").is_file()
            and image_file(root) is not None
        )
    except OSError:
        return False


@dataclass(frozen=True)
class SetupTarget:
    disk_number: int
    disk_name: str
    bus_type: str
    data_letter: str  # "F:"
    data_label: str | None
    file_system: str
    size: int
    free: int
    kind: str = "setup"

    @property
    def root(self) -> str:
        return self.data_letter + "\\"


def find_setup_targets(
    rows: list[PartitionRow], is_setup: Callable[[str], bool]
) -> list[SetupTarget]:
    """Partições de discos removíveis, sem ``VTOYEFI``, com os arquivos do instalador.

    O layout "UEFI:NTFS" do Rufus (partição NTFS + uma pequena ``UEFI_NTFS``) dá certo
    sozinho: só a partição grande tem os arquivos do instalador.
    """
    disks_with_ventoy = {r.disk_number for r in rows if (r.label or "").upper() == VTOYEFI_LABEL}
    targets: list[SetupTarget] = []
    for r in sorted(rows, key=lambda x: (x.disk_number, x.partition_number)):
        if r.disk_number in disks_with_ventoy or r.bus_type.upper() not in REMOVABLE_BUSES:
            continue
        if not r.drive_letter or not r.file_system:
            continue
        letter = r.drive_letter.rstrip(":").upper() + ":"
        if not is_setup(letter):
            continue
        targets.append(
            SetupTarget(
                disk_number=r.disk_number,
                disk_name=r.disk_name,
                bus_type=r.bus_type,
                data_letter=letter,
                data_label=r.label,
                file_system=r.file_system,
                size=r.size,
                free=r.size_remaining or 0,
            )
        )
    return targets


def marker_comment(version: str, pendrive_id: str) -> bytes:
    return f"<!-- {MARK} {version} {pendrive_id} -->\n".encode()


def stamp_unattend(xml: bytes, version: str, pendrive_id: str) -> bytes:
    """Põe o comentário de origem logo depois da declaração XML."""
    head, sep, rest = xml.partition(b"?>\n")
    if not sep:
        return marker_comment(version, pendrive_id) + xml
    return head + sep + marker_comment(version, pendrive_id) + rest


def is_winkit_unattend(data: bytes) -> bool:
    """O arquivo foi gravado pelo WinKit (para não fazer cópia de segurança dele mesmo)."""
    return f"<!-- {MARK} ".encode() in data[:400]
