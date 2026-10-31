"""Serviços de plataforma usados pelo Agente (injeção de dependência)."""

from __future__ import annotations

from dataclasses import dataclass

from winkit.platform.accounts import Accounts, WindowsAccounts
from winkit.platform.appx import AppxManager, WindowsAppxManager
from winkit.platform.associations import AssociationsTool, DismAssociations
from winkit.platform.copy import Copier, RobocopyCopier
from winkit.platform.devices import DeviceInspector, WindowsDeviceInspector
from winkit.platform.dns import DnsClient, WindowsDnsClient
from winkit.platform.drivers import DriverManager, WindowsDriverManager
from winkit.platform.environment import Environment, WindowsEnvironment
from winkit.platform.features import SystemFeatures, WindowsSystemFeatures
from winkit.platform.fonts import FontLoader, WindowsFontLoader
from winkit.platform.installers import InstallerRunner, WindowsInstallerRunner
from winkit.platform.inventory import AppInventory, WindowsAppInventory
from winkit.platform.iso_mount import IsoMounter, WindowsIsoMounter
from winkit.platform.known_folders import KnownFolders, WindowsKnownFolders
from winkit.platform.netdrives import DriveMapper, WindowsDriveMapper
from winkit.platform.personal import LiveAppearance, WindowsLiveAppearance
from winkit.platform.power import SessionControl, WindowsSessionControl
from winkit.platform.powershell import PowerShell
from winkit.platform.registry import Registry, WindowsRegistry
from winkit.platform.restore import RestorePoints, WindowsRestorePoints
from winkit.platform.runner import CommandRunner, SubprocessRunner
from winkit.platform.scheduler import TaskScheduler, WindowsTaskScheduler
from winkit.platform.shortcuts import Shortcuts, WindowsShortcuts
from winkit.platform.wifi import WifiManager, WindowsWifi
from winkit.platform.windows_update import ComWindowsUpdater, WindowsUpdater
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
    updater: WindowsUpdater
    session: SessionControl
    restore: RestorePoints
    wifi: WifiManager
    iso: IsoMounter
    devices: DeviceInspector
    dns: DnsClient
    drive_mapper: DriveMapper
    font_loader: FontLoader
    associations: AssociationsTool
    appearance: LiveAppearance


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
        updater=ComWindowsUpdater(ps),
        session=WindowsSessionControl(runner),
        restore=WindowsRestorePoints(ps),
        wifi=WindowsWifi(runner),
        iso=WindowsIsoMounter(ps),
        devices=WindowsDeviceInspector(ps),
        dns=WindowsDnsClient(ps),
        drive_mapper=WindowsDriveMapper(ps),
        font_loader=WindowsFontLoader(),
        associations=DismAssociations(runner),
        appearance=WindowsLiveAppearance(),
    )
