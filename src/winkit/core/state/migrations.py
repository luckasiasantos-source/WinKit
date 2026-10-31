"""Migrações do ``estado.json`` (R-47).

v1 → v2 (D-031): ``error``, ``reason`` e ``warnings`` deixam de ser texto pronto e viram
``Msg``. Textos antigos são preservados como ``legacy.text``.
"""

from __future__ import annotations

from typing import Any

from winkit.core.errors import StateError
from winkit.core.text import legacy

CURRENT = 2


def _as_msg(value: Any) -> Any:
    if isinstance(value, str):
        return legacy(value).model_dump()
    return value


def migrate_state(data: Any) -> Any:
    """Leva um estado de qualquer versão conhecida para a atual."""
    if not isinstance(data, dict):
        return data
    version = data.get("schema_version", 1)
    if version == CURRENT:
        return data
    if version != 1:
        raise StateError(f"formato de estado desconhecido: {version}")
    out = dict(data)
    steps = {}
    for key, raw in (data.get("steps") or {}).items():
        step = dict(raw)
        for name in ("error", "reason"):
            if name in step:
                step[name] = _as_msg(step[name])
        steps[key] = step
    out["steps"] = steps
    out["warnings"] = [_as_msg(w) for w in data.get("warnings") or []]
    out["schema_version"] = CURRENT
    return out
