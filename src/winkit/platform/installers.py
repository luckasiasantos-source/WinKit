"""Execução de instaladores (PLANO.md §13.3): argumentos em lista, tempo limite, sem janela."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from winkit.core.recipe.models import InstallerSpec, Scope
from winkit.platform.powershell import PowerShell
from winkit.platform.runner import CommandRunner
from winkit.platform.system import system32
from winkit.platform.winget import normalize_code

_MSIX_MACHINE = "Add-AppxProvisionedPackage -Online -PackagePath $p.Path -SkipLicense | Out-Null"
_MSIX_USER = "Add-AppxPackage -Path $p.Path"


@dataclass(frozen=True)
class InstallOutcome:
    exit_code: int
    timed_out: bool = False


class InstallerRunner(Protocol):
    def run(
        self, file: Path, spec: InstallerSpec, *, scope: Scope, log: Path
    ) -> InstallOutcome: ...

    def kill(self, process_names: list[str]) -> None: ...


def build_argv(file: Path, spec: InstallerSpec, log: Path) -> list[str]:
    if spec.type == "msi":
        return [str(system32("msiexec.exe")), "/i", str(file), *spec.args, "/l*v", str(log)]
    return [str(file), *spec.args]


class WindowsInstallerRunner:
    def __init__(self, runner: CommandRunner, ps: PowerShell) -> None:
        self._runner = runner
        self._ps = ps

    def run(self, file: Path, spec: InstallerSpec, *, scope: Scope, log: Path) -> InstallOutcome:
        timeout = spec.timeout_minutes * 60
        if spec.type == "msix":
            body = _MSIX_MACHINE if scope == "machine" else _MSIX_USER
            try:
                self._ps.run(body, {"Path": str(file)}, timeout=timeout, log_to=log)
            except Exception:  # noqa: BLE001 — falha vira código 1; detalhe fica no log
                return InstallOutcome(1)
            return InstallOutcome(0)
        res = self._runner.run(
            build_argv(file, spec, log), timeout=timeout, log_to=log, cwd=file.parent
        )
        return InstallOutcome(normalize_code(res.exit_code), res.timed_out)

    def kill(self, process_names: list[str]) -> None:
        for name in process_names:
            self._runner.run([str(system32("taskkill.exe")), "/IM", name, "/F", "/T"], timeout=60)
