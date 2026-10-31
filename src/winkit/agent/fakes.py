"""``AgentServices`` montado só com dublês (testes e simulação)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from winkit.agent.services import AgentServices
from winkit.platform.copy import PythonCopier
from winkit.platform.fakes.apps import (
    FakeInstallerRunner,
    FakeInventory,
    FakeShortcuts,
    FakeWinget,
)
from winkit.platform.fakes.drivers import FakeDriverManager
from winkit.platform.fakes.powershell import FakePowerShell
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.restore import FakeRestorePoints
from winkit.platform.fakes.runner import FakeRunner
from winkit.platform.fakes.system import (
    FakeAccounts,
    FakeEnvironment,
    FakeKnownFolders,
    FakeScheduler,
)
from winkit.platform.fakes.system_tweaks import (
    FakeAppx,
    FakeFeatures,
    FakeIsoMounter,
    FakeSession,
    FakeUpdater,
)
from winkit.platform.fakes.wifi import FakeWifi


def fake_agent_services(*, pendrive: Path, system: Path, **overrides: Any) -> AgentServices:
    values: dict[str, Any] = {
        "runner": FakeRunner(),
        "ps": FakePowerShell(),
        "registry": FakeRegistry(),
        "scheduler": FakeScheduler(),
        "accounts": FakeAccounts(),
        "env": FakeEnvironment(roots=[pendrive]),
        "folders": FakeKnownFolders(system),
        "drivers": FakeDriverManager(),
        "inventory": FakeInventory(apps=[]),
        "winget": FakeWinget(),
        "installers": FakeInstallerRunner(),
        "shortcuts": FakeShortcuts(),
        "copier": PythonCopier(),
        "appx": FakeAppx(),
        "features": FakeFeatures(),
        "updater": FakeUpdater(),
        "session": FakeSession(),
        "restore": FakeRestorePoints(),
        "wifi": FakeWifi(),
        "iso": FakeIsoMounter(),
    }
    values.update(overrides)
    return AgentServices(**values)
