"""Serviços de plataforma usados pelo Agente (injeção de dependência)."""

from __future__ import annotations

from dataclasses import dataclass

from winkit.platform.accounts import Accounts, WindowsAccounts
from winkit.platform.appx import AppxManager, WindowsAppxManager
from winkit.platform.copy import Copier, RobocopyCopier
from winkit.platform.drivers import DriverManager, WindowsDriverManager
from winkit.platform.environment import Environment, WindowsEnvironment
from winkit.platform.features import SystemFeatures, WindowsSystemFeatures
from winkit.platform.installers import InstallerRunner, WindowsInstallerRunner
from winkit.platform.inventory import AppInventory, WindowsAppInventory
from winkit.platform.known_folders import KnownFolders, WindowsKnownFolders
from winkit.platform.powershell import PowerShell
from winkit.platform.registry import Registry, WindowsRegistry
from winkit.platform.runner import CommandRunner, SubprocessRunner
from winkit.platform.scheduler import TaskScheduler, WindowsTaskScheduler
from winkit.platform.shortcuts import Shortcuts, WindowsShortcuts
from winkit.platform.winget import WindowsWinget, Winget


@dataclass
class AgentServices:
    runner: CommandRunner
    ps: PowerShell
    registry: Registry
    scheduler: TaskScheduler
    accounts: Accounts
    env: Environment
    folders: KnownFolders
    drivers: DriverManager
    inventory: AppInventory
    winget: Winget
    installers: InstallerRunner
    shortcuts: Shortcuts
    copier: Copier
    appx: AppxManager
    features: SystemFeatures


def real_agent_services() -> AgentServices:  # pragma: no cover — só no Windows
    runner = SubprocessRunner()
    ps = PowerShell(runner)
    registry = WindowsRegistry(runner)
    return AgentServices(
        runner=runner,
        ps=ps,
        registry=registry,
        scheduler=WindowsTaskScheduler(ps),
        accounts=WindowsAccounts(ps),
        env=WindowsEnvironment(),
        folders=WindowsKnownFolders(registry),
        drivers=WindowsDriverManager(runner, ps),
        inventory=WindowsAppInventory(registry, None),
        winget=WindowsWinget(runner, ps),
        installers=WindowsInstallerRunner(runner, ps),
        shortcuts=WindowsShortcuts(ps),
        copier=RobocopyCopier(runner),
        appx=WindowsAppxManager(ps),
        features=WindowsSystemFeatures(ps),
    )
