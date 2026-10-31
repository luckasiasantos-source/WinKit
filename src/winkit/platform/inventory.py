"""Leitura dos apps instalados (registro de desinstalação + pacotes da Loja)."""

from __future__ import annotations

from typing import Protocol

from winkit.core.inventory import InstalledApp, app_from_appx, app_from_uninstall
from winkit.core.recipe.models import Scope
from winkit.platform.powershell import PowerShell
from winkit.platform.registry import Registry

UNINSTALL_KEYS: tuple[tuple[str, str, Scope], ...] = (
    ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", "machine"),
    ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", "machine"),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Uninstall", "user"),
)

_APPX = r"""
Get-AppxPackage | ForEach-Object {
    [pscustomobject]@{
        Name = [string]$_.Name
        Version = [string]$_.Version
        PublisherDisplayName = [string]$_.PublisherId
        IsFramework = [bool]$_.IsFramework
        NonRemovable = [bool]$_.NonRemovable
        SignatureKind = [string]$_.SignatureKind
        PackageFamilyName = [string]$_.PackageFamilyName
    }
}
"""


class AppInventory(Protocol):
    def installed(self, *, include_appx: bool = True) -> list[InstalledApp]: ...


class WindowsAppInventory:
    def __init__(self, registry: Registry, ps: PowerShell | None) -> None:
        self._registry = registry
        self._ps = ps

    def installed(self, *, include_appx: bool = True) -> list[InstalledApp]:
        seen: set[tuple[str, str]] = set()
        out: list[InstalledApp] = []
        for hive, key, scope in UNINSTALL_KEYS:
            for sub in self._registry.subkeys(hive, key):
                app = app_from_uninstall(self._registry.values(hive, f"{key}\\{sub}"), scope=scope)
                if app is None:
                    continue
                k = (app.name.casefold(), app.version)
                if k not in seen:
                    seen.add(k)
                    out.append(app)
        if include_appx and self._ps is not None:
            for item in self._ps.run_json(_APPX, timeout=300):
                app = app_from_appx(item)
                if app is not None:
                    out.append(app)
        return sorted(out, key=lambda a: a.name.casefold())
