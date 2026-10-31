"""Drivers de terceiros: listar, exportar e instalar (PLANO.md §7.2, M4).

Nunca interpreta o texto do ``pnputil`` (R-13): só o código de saída e o conteúdo da pasta.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from winkit.core.errors import PlatformError
from winkit.platform.powershell import PowerShell
from winkit.platform.runner import CommandRunner
from winkit.platform.system import system32

#: Códigos de saída do pnputil.
PNPUTIL_OK = 0
PNPUTIL_REBOOT = 3010
#: ERROR_NO_MORE_ITEMS: pacote adicionado ao repositório, mas nenhum dispositivo presente o usa.
PNPUTIL_NOTHING_INSTALLED = 259

_LIST = r"""
Get-WindowsDriver -Online | ForEach-Object {
    [pscustomobject]@{
        Driver = [string]$_.Driver
        OriginalFileName = [string]$_.OriginalFileName
        ClassName = [string]$_.ClassName
        ProviderName = [string]$_.ProviderName
        Version = [string]$_.Version
        Date = $(if ($_.Date) { $_.Date.ToString('yyyy-MM-dd') } else { $null })
        BootCritical = [bool]$_.BootCritical
    }
}
"""


@dataclass(frozen=True)
class InstalledDriver:
    published_name: str  # oemNN.inf
    original_inf: str
    class_name: str
    provider: str
    version: str
    date: str | None
    boot_critical: bool


@dataclass(frozen=True)
class DriverInstallResult:
    exit_code: int

    @property
    def ok(self) -> bool:
        return self.exit_code in (PNPUTIL_OK, PNPUTIL_REBOOT, PNPUTIL_NOTHING_INSTALLED)

    @property
    def reboot(self) -> bool:
        return self.exit_code == PNPUTIL_REBOOT


class DriverManager(Protocol):
    def list_third_party(self) -> list[InstalledDriver]: ...

    def export(self, published_name: str, dest: Path) -> None: ...

    def install(self, folder: Path, log: Path | None = None) -> DriverInstallResult: ...


def driver_from_json(item: dict[str, Any]) -> InstalledDriver:
    original = str(item.get("OriginalFileName") or "")
    return InstalledDriver(
        published_name=str(item["Driver"]),
        original_inf=original.replace("/", "\\").rsplit("\\", 1)[-1],
        class_name=str(item.get("ClassName") or ""),
        provider=str(item.get("ProviderName") or ""),
        version=str(item.get("Version") or ""),
        date=item.get("Date"),
        boot_critical=bool(item.get("BootCritical")),
    )


class WindowsDriverManager:
    def __init__(self, runner: CommandRunner, ps: PowerShell) -> None:
        self._runner = runner
        self._ps = ps

    def list_third_party(self) -> list[InstalledDriver]:
        return [driver_from_json(x) for x in self._ps.run_json(_LIST, timeout=600)]

    def export(self, published_name: str, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        res = self._runner.run(
            [str(system32("pnputil.exe")), "/export-driver", published_name, str(dest)],
            timeout=600,
        )
        if res.exit_code != 0 or not any(dest.rglob("*.inf")):
            raise PlatformError(
                f"falha ao exportar {published_name} (pnputil código {res.exit_code})"
            )

    def install(self, folder: Path, log: Path | None = None) -> DriverInstallResult:
        res = self._runner.run(
            [
                str(system32("pnputil.exe")),
                "/add-driver",
                str(folder / "*.inf"),
                "/subdirs",
                "/install",
            ],
            timeout=1800,
            log_to=log,
        )
        if res.timed_out:
            raise PlatformError("pnputil excedeu o tempo limite")
        return DriverInstallResult(res.exit_code)
