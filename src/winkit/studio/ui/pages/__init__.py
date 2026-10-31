"""Páginas do WinKit Studio, uma por seção da barra lateral (D-042)."""

from winkit.studio.ui.pages.bring import AppsPage, BackupsPage, DriversPage
from winkit.studio.ui.pages.finish import BuildPage, ExecutionPage, LivePage
from winkit.studio.ui.pages.network import DnsPage, NetworkDrivesPage, WifiPage
from winkit.studio.ui.pages.prepare import AccountPage, PendrivePage
from winkit.studio.ui.pages.system import BloatPage, EnergyPage, FeaturesPage, TweaksPage

__all__ = [
    "AccountPage",
    "AppsPage",
    "BackupsPage",
    "BloatPage",
    "BuildPage",
    "DnsPage",
    "DriversPage",
    "EnergyPage",
    "ExecutionPage",
    "FeaturesPage",
    "LivePage",
    "NetworkDrivesPage",
    "PendrivePage",
    "TweaksPage",
    "WifiPage",
]
