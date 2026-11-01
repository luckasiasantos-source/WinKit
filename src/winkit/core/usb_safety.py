"""Travas para o WinKit gravar um pendrive (V3-13, D-045, R-60). Regras puras.

Só um pendrive USB escolhido pela pessoa pode ser apagado, e só se **todas** as travas passarem,
conferidas de novo imediatamente antes de apagar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from winkit.i18n.msg import Msg, msg

BootMode = Literal["uefi_bios", "uefi", "bios"]
BUS_USB = 7
MIN_SIZE = 8 * 1000**3
MAX_SIZE = 512 * 1000**3


@dataclass(frozen=True)
class UsbDisk:
    number: int
    serial: str
    model: str
    size: int
    bus_type: int
    is_system: bool
    is_boot: bool
    letters: tuple[str, ...]  # letras das partições hoje ("E:")


def refusal_reasons(current: UsbDisk | None, shown: UsbDisk, typed_letter: str) -> list[Msg]:
    """Motivos para **não** apagar. Vazio = pode. ``current`` é o disco relido agora."""
    if current is None:
        return [msg("usb.refuse_gone")]
    out: list[Msg] = []
    if current.bus_type != BUS_USB:
        out.append(msg("usb.refuse_not_usb"))
    if current.is_system or current.is_boot:
        out.append(msg("usb.refuse_system"))
    if not MIN_SIZE <= current.size <= MAX_SIZE:
        out.append(msg("usb.refuse_size"))
    if (current.number, current.serial) != (shown.number, shown.serial):
        out.append(msg("usb.refuse_changed"))
    letter = typed_letter.strip().upper().rstrip(":\\") + ":"
    if letter not in current.letters:
        out.append(msg("usb.refuse_letter"))
    return out


def boot_warnings(boot: BootMode, version: str, arch: str) -> list[Msg]:
    """Avisos do tipo de PC para o Windows alvo (o tipo continua escolha da pessoa)."""
    out: list[Msg] = []
    if version == "11" and boot == "bios":
        out.append(msg("usb.warn_11_bios"))
    if version == "7" and boot != "bios":
        out.append(msg("usb.warn_7_uefi"))
    if arch == "x86" and boot != "bios":
        out.append(msg("usb.warn_x86_uefi"))
    return out


def partition_style(boot: BootMode) -> Literal["MBR", "GPT"]:
    """MBR serve aos dois firmwares; GPT só ao UEFI."""
    return "GPT" if boot == "uefi" else "MBR"
