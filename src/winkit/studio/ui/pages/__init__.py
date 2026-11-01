"""Páginas do WinKit Studio, uma por seção da barra lateral (D-042)."""

from winkit.studio.ui.pages.bring import (
    AppearancePage,
    AppsPage,
    BackupsPage,
    DefaultAppsPage,
    DriversPage,
    FontsPage,
    GamesPage,
    StartLayoutPage,
    SuggestionsPage,
)
from winkit.studio.ui.pages.customiso import CustomIsoPage
from winkit.studio.ui.pages.finish import BuildPage, ExecutionPage, LivePage
from winkit.studio.ui.pages.network import BrowsersPage, DnsPage, NetworkDrivesPage, WifiPage
from winkit.studio.ui.pages.pcbackup import HealthPage, PcBackupPage
from winkit.studio.ui.pages.prepare import (
    AccountPage,
    DownloadPage,
    PathPage,
    PendrivePage,
    TemplatesPage,
)
from winkit.studio.ui.pages.system import (
    BloatPage,
    EnergyPage,
    EnvPage,
    FeaturesPage,
    MaintenancePage,
    TweaksPage,
    UserFoldersPage,
)
from winkit.studio.ui.pages.writeusb import WriteUsbPage

__all__ = [
    "AccountPage",
    "AppearancePage",
    "AppsPage",
    "BackupsPage",
    "BloatPage",
    "BrowsersPage",
    "BuildPage",
    "CustomIsoPage",
    "DefaultAppsPage",
    "DnsPage",
    "DownloadPage",
    "DriversPage",
    "EnergyPage",
    "EnvPage",
    "ExecutionPage",
    "FeaturesPage",
    "FontsPage",
    "GamesPage",
    "HealthPage",
    "LivePage",
    "MaintenancePage",
    "NetworkDrivesPage",
    "PathPage",
    "PcBackupPage",
    "PendrivePage",
    "StartLayoutPage",
    "SuggestionsPage",
    "TemplatesPage",
    "TweaksPage",
    "UserFoldersPage",
    "WifiPage",
    "WriteUsbPage",
]
