"""``Services`` do Studio montado só com dublês (um lugar para acrescentar campos novos)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from winkit.platform.copy import PythonCopier
from winkit.platform.fakes.apps import FakeInventory, FakeWinget
from winkit.platform.fakes.associations import FakeAssociations
from winkit.platform.fakes.backup import FakeOldPcFolders, FakeShadowCopies
from winkit.platform.fakes.disks import FakeDiskInspector, windows_iso
from winkit.platform.fakes.drivers import FakeDriverManager
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.runner import FakeRunner
from winkit.platform.fakes.system import FakeScheduler
from winkit.platform.fakes.volumes import FakeVolumes
from winkit.platform.fakes.wifi import FakeWifi
from winkit.platform.services import Services


def fake_services(*, old_pc: Path | None = None, **overrides: Any) -> Services:
    base = old_pc or Path(tempfile.mkdtemp(prefix="winkit-oldpc-"))
    folders = FakeOldPcFolders(base)
    values: dict[str, Any] = {
        "runner": FakeRunner(),
        "disks": FakeDiskInspector(isos={"Windows11.iso": windows_iso()}),
        "drivers": FakeDriverManager(),
        "inventory": FakeInventory(),
        "winget": FakeWinget(),
        "copier": PythonCopier(),
        "vss": FakeShadowCopies(volume_roots={"C:": base}),
        "folders": folders,
        "volume_root": folders.volume_root,
        "wifi": FakeWifi(),
        "registry": FakeRegistry(),
        "scheduler": FakeScheduler(),
        "associations": FakeAssociations(),
        "volumes": FakeVolumes(),
    }
    values.update(overrides)
    return Services(**values)
