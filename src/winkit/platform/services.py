"""Fábrica das implementações reais da plataforma (injeção de dependência simples)."""

from __future__ import annotations

from dataclasses import dataclass

from winkit.platform.disks import DiskInspector, WindowsDiskInspector
from winkit.platform.powershell import PowerShell
from winkit.platform.runner import CommandRunner, SubprocessRunner


@dataclass
class Services:
    runner: CommandRunner
    disks: DiskInspector


def real_services() -> Services:
    runner = SubprocessRunner()
    ps = PowerShell(runner)
    return Services(runner=runner, disks=WindowsDiskInspector(ps))
