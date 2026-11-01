"""Fábrica das implementações reais da plataforma (injeção de dependência simples)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from winkit.core.regional import RegionalDefaults
from winkit.platform.associations import AssociationsTool, DismAssociations
from winkit.platform.copy import Copier, RobocopyCopier
from winkit.platform.devices import DeviceInspector, WindowsDeviceInspector
from winkit.platform.disk_info import DiskInfo, WindowsDiskInfo
from winkit.platform.disks import DiskInspector, WindowsDiskInspector
from winkit.platform.drivers import DriverManager, WindowsDriverManager
from winkit.platform.features import SystemFeatures, WindowsSystemFeatures
from winkit.platform.image_tools import ImageTools, WindowsImageTools
from winkit.platform.inventory import AppInventory, WindowsAppInventory
from winkit.platform.iso_mount import IsoMounter, WindowsIsoMounter
from winkit.platform.known_folders import KnownFolders, WindowsKnownFolders
from winkit.platform.locale import read_regional
from winkit.platform.powershell import PowerShell
from winkit.platform.registry import Registry, WindowsRegistry
from winkit.platform.runner import CommandRunner, SubprocessRunner
from winkit.platform.scheduler import TaskScheduler, WindowsTaskScheduler
from winkit.platform.usb_writer import UsbWriter, WindowsUsbWriter
from winkit.platform.volumes import Volumes, WindowsVolumes
from winkit.platform.vss import ShadowCopies, WindowsShadowCopies
from winkit.platform.wifi import WifiManager, WindowsWifi
from winkit.platform.windows_download import FidoLinks, IsoLinks, tools_dir
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
    volumes: Volumes | None = None
    devices: DeviceInspector | None = None
    #: Link oficial da ISO do Windows (V3-08).
    iso_links: IsoLinks | None = None
    #: Discos de destino do backup e saúde do PC (V3-09, V3-15).
    disk_info: DiskInfo | None = None
    #: ISO personalizada (V3-11): imagens do Windows e ISO montada só para leitura.
    image_tools: ImageTools | None = None
    iso_mounter: IsoMounter | None = None
    #: V3-13: o único que apaga um disco — o pendrive confirmado (R-60).
    usb_writer: UsbWriter | None = None


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
        volumes=WindowsVolumes(ps),
        devices=WindowsDeviceInspector(ps),
        iso_links=FidoLinks(ps, tools_dir()),
        disk_info=WindowsDiskInfo(ps),
        image_tools=WindowsImageTools(ps),
        iso_mounter=WindowsIsoMounter(ps),
        usb_writer=WindowsUsbWriter(ps),
    )
