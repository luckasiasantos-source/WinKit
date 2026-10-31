"""Inventário do PC para o relatório antes/depois (V2-19), usado pelo Studio e pelo Agente."""

from __future__ import annotations

from winkit.core.catalog.models import Catalogs
from winkit.core.inventory_snapshot import SnapApp, SnapDevice, Snapshot
from winkit.platform.devices import DeviceInspector
from winkit.platform.features import SystemFeatures
from winkit.platform.inventory import AppInventory


def take_snapshot(
    inventory: AppInventory,
    devices: DeviceInspector | None,
    features: SystemFeatures | None,
    catalogs: Catalogs,
    *,
    build: int | None,
) -> Snapshot:
    apps = [
        SnapApp(name=a.name, version=a.version, publisher=a.publisher, winget_id=a.winget_id)
        for a in inventory.installed(include_appx=False)
        if not a.redistributable
    ]
    devs = [
        SnapDevice(name=d.name, hardware_ids=d.hardware_ids[:3], code=d.code)
        for d in (devices.all_devices() if devices else [])
    ]
    enabled: list[str] = []
    if features is not None:
        names = sorted({p.feature for f in catalogs.features for p in f.parts if p.feature})
        caps = sorted({p.capability for f in catalogs.features for p in f.parts if p.capability})
        states = features.states(names, caps)
        enabled = [
            f.id for f in catalogs.features if all(states.get(p.name, False) for p in f.parts)
        ]
    return Snapshot(windows_build=build, apps=apps, devices=devs, features=enabled)
