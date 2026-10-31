"""Serviços de plataforma usados pelo Agente (injeção de dependência)."""

from __future__ import annotations

from dataclasses import dataclass

from winkit.platform.accounts import Accounts, WindowsAccounts
from winkit.platform.environment import Environment, WindowsEnvironment
from winkit.platform.known_folders import KnownFolders, WindowsKnownFolders
from winkit.platform.powershell import PowerShell
from winkit.platform.registry import Registry, WindowsRegistry
from winkit.platform.runner import CommandRunner, SubprocessRunner
from winkit.platform.scheduler import TaskScheduler, WindowsTaskScheduler


@dataclass
class AgentServices:
    runner: CommandRunner
    ps: PowerShell
    registry: Registry
    scheduler: TaskScheduler
    accounts: Accounts
    env: Environment
    folders: KnownFolders


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
    )
