"""Teste de proteção (R-60, D-045): o WinKit nunca apaga o disco errado."""

from __future__ import annotations

from dataclasses import replace

import pytest

from winkit.core.usb_safety import UsbDisk, boot_warnings, partition_style, refusal_reasons

PEN = UsbDisk(3, "AA11", "SanDisk", 32 * 1000**3, 7, False, False, ("E:",))


def test_pendrive_with_right_letter_passes() -> None:
    assert refusal_reasons(PEN, PEN, "e") == [] and refusal_reasons(PEN, PEN, "E:\\") == []


@pytest.mark.parametrize(
    ("current", "key"),
    [
        (None, "usb.refuse_gone"),
        (replace(PEN, bus_type=11), "usb.refuse_not_usb"),  # SATA interno
        (replace(PEN, is_system=True), "usb.refuse_system"),
        (replace(PEN, is_boot=True), "usb.refuse_system"),
        (replace(PEN, size=2 * 1000**4), "usb.refuse_size"),  # HD externo USB
        (replace(PEN, size=4 * 1000**3), "usb.refuse_size"),
        (replace(PEN, serial="BB22"), "usb.refuse_changed"),  # trocaram o pendrive
        (replace(PEN, number=4), "usb.refuse_changed"),
    ],
)
def test_every_lock_refuses(current: UsbDisk | None, key: str) -> None:
    assert key in [m.key for m in refusal_reasons(current, PEN, "E")]


def test_wrong_letter_refuses() -> None:
    assert [m.key for m in refusal_reasons(PEN, PEN, "C")] == ["usb.refuse_letter"]


def test_boot_modes() -> None:
    assert partition_style("uefi") == "GPT" and partition_style("uefi_bios") == "MBR"
    assert [m.key for m in boot_warnings("bios", "11", "x64")] == ["usb.warn_11_bios"]
    assert boot_warnings("uefi_bios", "10", "x64") == []
