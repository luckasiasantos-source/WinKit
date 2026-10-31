"""Fábricas de objetos para testes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from winkit.core.recipe.io import new_recipe
from winkit.core.recipe.models import (
    AppItem,
    BackupItem,
    DriverItem,
    InstallerSpec,
    Recipe,
    TweakSelection,
)

FIXED_NOW = datetime(2026, 11, 2, 14, 0, tzinfo=UTC)


def recipe(**overrides: Any) -> Recipe:
    r = new_recipe(
        pendrive_id="11111111-2222-3333-4444-555555555555",
        username="Samuel",
        source_pc="PC-ANTIGO",
        now=FIXED_NOW,
    )
    for key, value in overrides.items():
        setattr(r, key, value)
    return r


def app(app_id: str, **kw: Any) -> AppItem:
    data: dict[str, Any] = {
        "id": app_id,
        "name": app_id.title(),
        "source": "offline",
        "scope": "machine",
    }
    data.update(kw)
    if data["source"] == "offline" and "installer" not in data:
        data["installer"] = InstallerSpec(
            path=f"Apps/{app_id}/1.0/setup.exe", type="nsis", args=["/S"]
        )
    if data["source"] == "winget_online" and "winget_id" not in data:
        data["winget_id"] = f"Vendor.{app_id}"
    return AppItem(**data)


def backup(backup_id: str, template: str = "{APPDATA}\\X", **kw: Any) -> BackupItem:
    data: dict[str, Any] = {
        "id": backup_id,
        "name": backup_id,
        "template": template,
        "data_path": f"Perfis/padrao/Backups/{backup_id}/dados",
    }
    data.update(kw)
    return BackupItem(**data)


def driver(driver_id: str, priority: int = 5, cls: str = "Net") -> DriverItem:
    return DriverItem.model_validate(
        {
            "id": driver_id,
            "path": f"Drivers/{cls}/{driver_id}",
            "class": cls,
            "provider": "Acme",
            "priority": priority,
        }
    )


def tweak(tweak_id: str, **kw: Any) -> TweakSelection:
    return TweakSelection(id=tweak_id, **kw)
