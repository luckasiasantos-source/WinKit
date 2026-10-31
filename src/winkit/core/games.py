"""Jogos sem baixar de novo (V2-13): bibliotecas da Steam e manifestos da Epic. Regras puras."""

from __future__ import annotations

import ntpath
from typing import Any

from winkit.core.vdf import VdfDict


def steam_libraries(data: VdfDict) -> list[tuple[str, int]]:
    """(caminho, número de jogos) de cada biblioteca do ``libraryfolders.vdf``."""
    root = data.get("libraryfolders")
    if not isinstance(root, dict):
        return []
    out = []
    for value in root.values():
        if isinstance(value, dict) and isinstance(value.get("path"), str):
            apps = value.get("apps")
            out.append((str(value["path"]), len(apps) if isinstance(apps, dict) else 0))
    return out


def _same(a: str, b: str) -> bool:
    return ntpath.normcase(ntpath.normpath(a)) == ntpath.normcase(ntpath.normpath(b))


def has_steam_library(data: VdfDict, path: str) -> bool:
    return any(_same(p, path) for p, _ in steam_libraries(data))


def add_steam_library(data: VdfDict, path: str) -> bool:
    """Acrescenta a biblioteca com o próximo número livre; False se já existe (nunca duplica)."""
    root = data.setdefault("libraryfolders", {})
    if not isinstance(root, dict):
        raise ValueError("libraryfolders.vdf inválido")
    if has_steam_library(data, path):
        return False
    numbers = [int(k) for k in root if k.isdigit()]
    root[str(max(numbers, default=-1) + 1)] = {
        "path": path,
        "label": "",
        "totalsize": "0",
        "apps": {},
    }
    return True


_EPIC_PATHS = ("InstallLocation", "ManifestLocation", "StagingLocation")


def rewrite_epic_manifest(item: dict[str, Any], new_install: str) -> dict[str, Any]:
    """Troca a pasta antiga do jogo pela nova (letra atual) nos campos de caminho."""
    old = str(item.get("InstallLocation") or "")
    out = dict(item)
    for field in _EPIC_PATHS:
        value = item.get(field)
        if not isinstance(value, str) or not value:
            continue
        if old and ntpath.normcase(value).startswith(ntpath.normcase(old)):
            out[field] = new_install + value[len(old) :]
    out["InstallLocation"] = new_install
    return out


def add_launcher_installed(data: dict[str, Any], item: dict[str, Any]) -> bool:
    """Acrescenta o jogo no ``LauncherInstalled.dat`` (por ``AppName``); False se já existe."""
    entries = data.setdefault("InstallationList", [])
    if not isinstance(entries, list):
        raise ValueError("LauncherInstalled.dat inválido")
    name = item.get("AppName")
    if any(isinstance(e, dict) and e.get("AppName") == name for e in entries):
        return False
    entries.append(
        {
            "InstallLocation": item.get("InstallLocation", ""),
            "NamespaceId": item.get("CatalogNamespace", ""),
            "ItemId": item.get("CatalogItemId", ""),
            "ArtifactId": name,
            "AppVersion": item.get("AppVersionString", ""),
            "AppName": name,
        }
    )
    return True
