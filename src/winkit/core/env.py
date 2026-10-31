"""Variáveis de ambiente e PATH (V2-22): regras puras.

- Valores com pastas do perfil viram moldes ``%USERPROFILE%\\go`` (tipo ``expand_sz``).
- O PATH só **ganha** entradas, no fim, sem duplicar (sem maiúsculas e sem a barra final).
"""

from __future__ import annotations

import ntpath
from collections.abc import Mapping

#: Pasta conhecida (nome de ``core/paths/templates``) → variável de ambiente equivalente.
ENV_FOR_FOLDER: Mapping[str, str] = {
    "USERPROFILE": "USERPROFILE",
    "APPDATA": "APPDATA",
    "LOCALAPPDATA": "LOCALAPPDATA",
    "PROGRAMDATA": "ProgramData",
    "PROGRAMFILES": "ProgramFiles",
    "PROGRAMFILESX86": "ProgramFiles(x86)",
}
MACHINE_ENV_KEY = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
USER_ENV_KEY = "Environment"


def norm_entry(entry: str) -> str:
    return entry.strip().rstrip("\\").casefold()


def split_path(value: str | None) -> list[str]:
    return [e for e in (value or "").split(";") if e.strip()]


def merge_path(current: str | None, additions: list[str]) -> tuple[str, list[str]]:
    """Acrescenta no fim o que falta; devolve (novo valor, entradas acrescentadas)."""
    entries = split_path(current)
    seen = {norm_entry(e) for e in entries}
    added = []
    for entry in additions:
        key = norm_entry(entry)
        if key and key not in seen:
            seen.add(key)
            added.append(entry.strip())
    if not added:
        return current or "", []
    base = (current or "").rstrip(";")
    return (base + ";" if base else "") + ";".join(added), added


def to_env_template(
    value: str, folders: Mapping[str, str], *, windows_dir: str | None = None
) -> tuple[str, bool]:
    """Troca o começo de cada caminho pela variável mais específica. (valor, mudou?)."""
    roots = [(ENV_FOR_FOLDER[k], v) for k, v in folders.items() if k in ENV_FOR_FOLDER and v]
    if windows_dir:
        roots.append(("SystemRoot", windows_dir))
    roots.sort(key=lambda kv: len(kv[1]), reverse=True)
    changed = False
    parts = []
    for part in value.split(";"):
        new = part
        low = ntpath.normpath(part).casefold() if part else ""
        for var, root in roots:
            r = ntpath.normpath(root).casefold()
            if low == r or low.startswith(r + "\\"):
                new = f"%{var}%" + ntpath.normpath(part)[len(r) :]
                changed = True
                break
        parts.append(new)
    return ";".join(parts), changed


def is_default_path_entry(entry: str, defaults: list[str]) -> bool:
    key = norm_entry(entry)
    return any(key == norm_entry(d) for d in defaults)
