"""Consultas de serviços do Windows por código de saída (R-13)."""

from __future__ import annotations

from winkit.platform.runner import CommandRunner
from winkit.platform.system import system32

#: ``sc.exe query`` devolve 1060 quando o serviço não existe.
SERVICE_DOES_NOT_EXIST = 1060


def service_exists(runner: CommandRunner, name: str) -> bool:
    result = runner.run([str(system32("sc.exe")), "query", name], timeout=60)
    return result.exit_code != SERVICE_DOES_NOT_EXIST


def service_running(runner: CommandRunner, name: str) -> bool:
    """Existe (o Windows inicia o ``WlanSvc`` sob demanda; não exigimos "em execução")."""
    return service_exists(runner, name)
