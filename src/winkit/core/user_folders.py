"""Pastas do usuário em outro disco (V2-14): regras puras.

Os valores de ``User Shell Folders`` usam os nomes oficiais do Windows. ``%USERNAME%`` fica no
valor (``REG_EXPAND_SZ``), então o perfil Default serve a todas as contas (H32).
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping

from winkit.core.recipe.models import UserFolderId, UserFolders

SHELL_FOLDERS_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
VALUE_NAMES: Mapping[str, str] = {
    "desktop": "Desktop",
    "documents": "Personal",
    "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
    "pictures": "My Pictures",
    "videos": "My Video",
    "music": "My Music",
}
#: Pasta → nome usado nos moldes de caminho (``{DOCUMENTS}``…).
TEMPLATE_VARS: Mapping[str, str] = {
    "desktop": "DESKTOP",
    "documents": "DOCUMENTS",
    "downloads": "DOWNLOADS",
    "pictures": "PICTURES",
    "videos": "VIDEOS",
    "music": "MUSIC",
}
ORDER: tuple[UserFolderId, ...] = (
    "desktop",
    "documents",
    "downloads",
    "pictures",
    "videos",
    "music",
)
_USERNAME = re.compile(re.escape("%USERNAME%"), re.IGNORECASE)


def expand_user(relative: str, username: str) -> str:
    return _USERNAME.sub(lambda _: username, relative)


def generalize_user(relative: str, username: str) -> str:
    """``Usuarios\\Samuel\\Docs`` → ``Usuarios\\%USERNAME%\\Docs`` (só segmentos inteiros)."""
    parts = relative.split("\\")
    return "\\".join("%USERNAME%" if p.casefold() == username.casefold() else p for p in parts)


def default_folders(
    base: str, names: Mapping[UserFolderId, str], chosen: Collection[str]
) -> dict[UserFolderId, str]:
    base = base.strip("\\")
    return {f: f"{base}\\{names[f]}" if base else names[f] for f in ORDER if f in chosen}


def registry_values(uf: UserFolders, letter: str) -> dict[str, str]:
    """Nome do valor → caminho com a letra **atual** do volume."""
    return {VALUE_NAMES[f]: f"{letter}:\\{rel.strip(chr(92))}" for f, rel in uf.folders.items()}


def redirected(uf: UserFolders, letter: str, username: str) -> dict[str, str]:
    """Moldes de caminho que passam a apontar para o volume (R16): ``DOCUMENTS`` → ``D:\\…``."""
    return {
        TEMPLATE_VARS[f]: f"{letter}:\\{expand_user(rel, username).strip(chr(92))}"
        for f, rel in uf.folders.items()
    }
