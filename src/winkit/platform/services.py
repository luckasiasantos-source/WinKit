"""Fábrica das implementações reais da plataforma (injeção de dependência simples)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from winkit.core.regional import RegionalDefaults
from winkit.platform.associations import AssociationsTool, DismAssociations
from winkit.platform.copy import Copier, RobocopyCopier
from winkit.platform.disks import DiskInspector, WindowsDiskInspector
from winkit.platform.drivers import DriverManager, WindowsDriverManager
from winkit.platform.features import SystemFeatures, WindowsSystemFeatures
from winkit.platform.inventory import AppInventory, WindowsAppInventory
from winkit.platform.known_folders import KnownFolders, WindowsKnownFolders
from winkit.platform.locale import read_regional
from winkit.platform.powershell import PowerShell
from winkit.platform.registry import Registry, WindowsRegistry
from winkit.platform.runner import CommandRunner, SubprocessRunner
from winkit.platform.scheduler import TaskScheduler, WindowsTaskScheduler
from winkit.platform.vss import ShadowCopies, WindowsShadowCopies
from winkit.platform.wifi import WifiManager, WindowsWifi
from winkit.platform.winget import WindowsWinget, Winget


@dataclass
class Services:
    runner: CommandRunner
    disks: DiskInspector
    drivers: DriverManager
    inventory: AppInventory
    winget: Winget
    copier: Copier
    vss: ShadowCopies
    folders: KnownFolders
    #: Letra de volume → pasta que dá acesso a ele (nos testes, uma pasta temporária).
    volume_root: Callable[[str], Path] = field(default=lambda v: Path(v + "\\"))
    #: Formatos, teclado e fuso do PC atual para a receita nova (D-030).
    regional: Callable[[], RegionalDefaults] = field(default=RegionalDefaults)
    wifi: WifiManager | None = None
    features: SystemFeatures | None = None
    #: Registro do PC atual (unidades de rede, variáveis de ambiente).
    registry: Registry | None = None
    scheduler: TaskScheduler | None = None
    associations: AssociationsTool | None = None


def real_services() -> Services:
    runner = SubprocessRunner()
    ps = PowerShell(runner)
    registry = WindowsRegistry(runner)
    return Services(
        runner=runner,
        disks=WindowsDiskInspector(ps),
        drivers=WindowsDriverManager(runner, ps),
        inventory=WindowsAppInventory(registry, ps),
        winget=WindowsWinget(runner, ps),
        copier=RobocopyCopier(runner),
        vss=WindowsShadowCopies(ps),
        folders=WindowsKnownFolders(registry),
        regional=lambda: read_regional(registry),
        wifi=WindowsWifi(runner),
        features=WindowsSystemFeatures(ps),
        registry=registry,
        scheduler=WindowsTaskScheduler(ps),
        associations=DismAssociations(runner),
    )
