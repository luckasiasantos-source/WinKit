"""Leitura do manifesto YAML gravado pelo ``winget download`` (PLANO.md §7.1.4)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from winkit.core.errors import WinKitError
from winkit.core.recipe.models import InstallerType, Scope

#: InstallerType do winget → tipo do WinKit. ``None`` = não instalável offline pelo WinKit.
WINGET_TYPES: dict[str, InstallerType | None] = {
    "msi": "msi",
    "wix": "msi",
    "msix": "msix",
    "appx": "msix",
    "inno": "inno",
    "nullsoft": "nsis",
    "burn": "wix_burn",
    "exe": "exe_custom",
    "zip": None,
    "portable": None,
    "pwa": None,
}


@dataclass(frozen=True)
class DownloadedPackage:
    package_id: str
    version: str
    installer: Path
    installer_type: InstallerType | None
    raw_type: str
    scope: Scope | None
    silent_args: tuple[str, ...]


def split_args(text: str) -> list[str]:
    """Divide argumentos no estilo do Windows (aspas duplas agrupam; sem escapes POSIX)."""
    out: list[str] = []
    cur: list[str] = []
    quoted = False
    for ch in text.strip():
        if ch == '"':
            quoted = not quoted
            cur.append(ch)
        elif ch.isspace() and not quoted:
            if cur:
                out.append("".join(cur))
                cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur))
    return out


def _installer_section(data: dict[str, Any]) -> dict[str, Any]:
    merged = dict(data)
    installers = data.get("Installers")
    if isinstance(installers, list) and installers and isinstance(installers[0], dict):
        merged.update(installers[0])
    return merged


def parse_download_dir(folder: Path) -> DownloadedPackage:
    manifests = sorted(folder.glob("*.yaml")) + sorted(folder.glob("*.yml"))
    if not manifests:
        raise WinKitError(f"manifesto do winget não encontrado em {folder}")
    data = yaml.safe_load(manifests[0].read_text(encoding="utf-8-sig")) or {}
    if not isinstance(data, dict):
        raise WinKitError(f"manifesto do winget inválido: {manifests[0]}")
    inst = _installer_section(data)
    raw_type = str(inst.get("InstallerType") or "").lower()
    switches = inst.get("InstallerSwitches") or {}
    silent = str(switches.get("Silent") or switches.get("SilentWithProgress") or "")
    custom = str(switches.get("Custom") or "")
    scope_raw = str(inst.get("Scope") or "").lower()
    scope: Scope | None = (
        "machine" if scope_raw == "machine" else "user" if scope_raw == "user" else None
    )
    files = [
        p for p in folder.iterdir() if p.is_file() and p.suffix.lower() not in (".yaml", ".yml")
    ]
    if not files:
        raise WinKitError(f"instalador não encontrado em {folder}")
    return DownloadedPackage(
        package_id=str(data.get("PackageIdentifier") or ""),
        version=str(data.get("PackageVersion") or ""),
        installer=max(files, key=lambda p: p.stat().st_size),
        installer_type=WINGET_TYPES.get(raw_type),
        raw_type=raw_type,
        scope=scope,
        silent_args=tuple(split_args(silent) + split_args(custom)),
    )
