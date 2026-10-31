"""Comparação de versões tolerante (V2-21): ``1.2.3.4``, ``2024.10``, ``1.0.0-beta``, ``24.08``.

Partes numéricas comparam como números; uma versão com sufixo (``-beta``, ``rc1``) é **menor**
que a mesma sem sufixo. Pastas antigas gravadas com hífen (``1-2-3``) também funcionam.
"""

from __future__ import annotations

import re

_SPLIT = re.compile(r"[.\-_+ ]+")
_NUM_ALPHA = re.compile(r"^(\d+)([a-z].*)?$")


def _key(version: str) -> tuple[tuple[int, ...], int, str]:
    nums: list[int] = []
    suffix = ""
    for part in _SPLIT.split(version.strip().lower().lstrip("v")):
        if not part:
            continue
        m = _NUM_ALPHA.match(part)
        if m and not suffix:
            nums.append(int(m.group(1)))
            if m.group(2):
                suffix = m.group(2)
        else:
            suffix = (suffix + "." + part).strip(".")
    while len(nums) > 1 and nums[-1] == 0:  # 1.2 == 1.2.0
        nums.pop()
    return tuple(nums), 0 if suffix else 1, suffix


def compare(a: str, b: str) -> int:
    """-1 se ``a < b``, 0 se iguais, 1 se ``a > b``."""
    ka, kb = _key(a), _key(b)
    return (ka > kb) - (ka < kb)
