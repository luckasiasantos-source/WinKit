"""Resolver de volumes (D-035, R-52): achar pelo número de série, usar a letra **atual**.

Função pura. Nunca troca letra de unidade; se o volume não for achado, quem chama pula a etapa
com motivo claro.
"""

from __future__ import annotations

import ntpath
from dataclasses import dataclass

from winkit.core.recipe.models import VolumeRef


@dataclass(frozen=True)
class VolumeInfo:
    serial: str  # 8 dígitos hexadecimais, maiúsculos
    letter: str | None  # "D" (sem dois-pontos); None = sem letra
    label: str | None = None
    size: int = 0
    free: int = 0
    is_system: bool = False


def normalize_serial(value: object) -> str | None:
    """``Win32_Volume.SerialNumber`` (inteiro) → ``"1A2B3C4D"``."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return f"{value & 0xFFFFFFFF:08X}"


def ref_for(v: VolumeInfo) -> VolumeRef:
    return VolumeRef(serial=v.serial, label=v.label, letter_hint=v.letter, size=v.size)


def resolve(ref: VolumeRef, volumes: list[VolumeInfo]) -> VolumeInfo | None:
    """O volume com o mesmo serial (com letra); empate pelo tamanho mais próximo."""
    same = [v for v in volumes if v.serial == ref.serial and v.letter]
    if not same:
        return None
    return min(same, key=lambda v: abs(v.size - ref.size))


def by_letter(letter: str, volumes: list[VolumeInfo]) -> VolumeInfo | None:
    key = letter.rstrip(":\\").upper()
    return next((v for v in volumes if v.letter == key), None)


def split(path: str, volumes: list[VolumeInfo]) -> tuple[VolumeInfo, str] | None:
    """``D:\\SteamLibrary`` → (volume D, ``SteamLibrary``); None se o volume não é conhecido."""
    drive, rest = ntpath.splitdrive(path)
    if len(drive) != 2 or drive[1] != ":":
        return None
    v = by_letter(drive[0], volumes)
    return (v, rest.strip("\\")) if v else None


def on(v: VolumeInfo, relative: str) -> str:
    """Caminho do Windows no volume, com a letra atual."""
    rel = relative.strip("\\")
    return f"{v.letter}:\\{rel}" if rel else f"{v.letter}:\\"
