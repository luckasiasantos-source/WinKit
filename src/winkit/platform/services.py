"""Fábrica das implementações reais da plataforma (injeção de dependência simples)."""

from __future__ import annotations

from dataclasses import dataclass

from winkit.platform.disks import DiskInspector, WindowsDiskInspector
from winkit.platform.drivers import DriverManager, WindowsDriverManager
from winkit.platform.inventory import AppInventory, WindowsAppInventory
from winkit.platform.powershell import PowerShell
from winkit.platform.registry import WindowsRegistry
from winkit.platform.runner import CommandRunner, SubprocessRunner
from winkit.platform.winget import WindowsWinget, Winget


@dataclass
class Services:
    runner: CommandRunner
    disks: DiskInspector
    drivers: DriverManager
    inventory: AppInventory
    winget: Winget


def real_services() -> Services:
    runner = SubprocessRunner()
    ps = PowerShell(runner)
    return Services(
        runner=runner,
        disks=WindowsDiskInspector(ps),
        drivers=WindowsDriverManager(runner, ps),
        inventory=WindowsAppInventory(WindowsRegistry(runner), ps),
        winget=WindowsWinget(runner, ps),
    )
