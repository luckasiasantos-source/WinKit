"""Páginas do WinKit Studio, uma por seção da barra lateral (D-042)."""

from winkit.studio.ui.pages.bring import (
    AppearancePage,
    AppsPage,
    BackupsPage,
    DefaultAppsPage,
    DriversPage,
    FontsPage,
)
from winkit.studio.ui.pages.finish import BuildPage, ExecutionPage, LivePage
from winkit.studio.ui.pages.network import DnsPage, NetworkDrivesPage, WifiPage
from winkit.studio.ui.pages.prepare import AccountPage, PendrivePage
from winkit.studio.ui.pages.system import (
    BloatPage,
    EnergyPage,
    EnvPage,
    FeaturesPage,
    MaintenancePage,
    TweaksPage,
)

__all__ = [
    "AccountPage",
    "AppearancePage",
    "AppsPage",
    "BackupsPage",
    "BloatPage",
    "BuildPage",
    "DefaultAppsPage",
    "DnsPage",
    "DriversPage",
    "EnergyPage",
    "EnvPage",
    "ExecutionPage",
    "FeaturesPage",
    "FontsPage",
    "LivePage",
    "MaintenancePage",
    "NetworkDrivesPage",
    "PendrivePage",
    "TweaksPage",
    "WifiPage",
]
