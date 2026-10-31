"""Gravar e desfazer as políticas de navegador (V2-12) no ``HKLM``."""

from __future__ import annotations

from winkit.core.browsers import RegUndo, RegWrite
from winkit.platform.registry import Registry


def apply(registry: Registry, ops: list[RegWrite]) -> None:
    for op in ops:
        registry.set("HKLM", op.key, op.value, op.type, op.data)  # type: ignore[arg-type]


def applied(registry: Registry, ops: list[RegWrite]) -> bool:
    return all(registry.get("HKLM", op.key, op.value) == op.data for op in ops)


def undo(registry: Registry, ops: list[RegUndo]) -> int:
    removed = 0
    for op in ops:
        if op.value is None:
            removed += int(registry.delete_key("HKLM", op.key))
        else:
            removed += int(registry.delete_value("HKLM", op.key, op.value))
    return removed
