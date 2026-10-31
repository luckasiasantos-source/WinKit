"""``Services`` do Studio montado só com dublês (um lugar para acrescentar campos novos)."""

from __future__ import annotations

from typing import Any

from winkit.platform.fakes.disks import FakeDiskInspector, windows_iso
from winkit.platform.fakes.drivers import FakeDriverManager
from winkit.platform.fakes.runner import FakeRunner
from winkit.platform.services import Services


def fake_services(**overrides: Any) -> Services:
    values: dict[str, Any] = {
        "runner": FakeRunner(),
        "disks": FakeDiskInspector(isos={"Windows11.iso": windows_iso()}),
        "drivers": FakeDriverManager(),
    }
    values.update(overrides)
    return Services(**values)
