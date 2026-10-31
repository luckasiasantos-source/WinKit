"""Limpeza ao final (PLANO.md §10.4, D-024).

Remove tudo que possa conter senha ou disparar o Agente de novo. O próprio executável não
pode se apagar enquanto roda: a remoção da pasta do Agente é agendada em ``RunOnce`` e só
acontece se nada falhou (para permitir "tentar de novo").
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from pathlib import Path

from winkit.agent.paths import AgentPaths
from winkit.agent.services import AgentServices
from winkit.agent.steps.base import local_path

WINLOGON = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
RUNONCE = r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
RUNONCE_VALUE = "WinKitLimpeza"


@dataclass
class CleanupReport:
    removed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _unlink(path: Path, report: CleanupReport) -> None:
    try:
        if path.is_file():
            path.unlink()
            report.removed.append(str(path))
    except OSError as exc:
        report.errors.append(f"{path}: {exc}")


def remove_setupcomplete_line(windows_dir: Path, agent_exe: Path, report: CleanupReport) -> None:
    sc = windows_dir / "Setup" / "Scripts" / "SetupComplete.cmd"
    if not sc.is_file():
        return
    lines = sc.read_text(encoding="ascii", errors="replace").splitlines()
    kept = [ln for ln in lines if str(agent_exe).lower() not in ln.lower()]
    if [ln for ln in kept if ln.strip() and ln.strip().lower() != "@echo off"]:
        sc.write_text("\r\n".join(kept) + "\r\n", encoding="ascii")
        report.removed.append(f"{sc} (linha do WinKit)")
    else:
        _unlink(sc, report)


def cleanup(services: AgentServices, paths: AgentPaths, *, remove_agent: bool) -> CleanupReport:
    report = CleanupReport()
    windows_dir = local_path(services.folders.windows_dir())

    # tarefa agendada
    try:
        if services.scheduler.remove_phase2_task():
            report.removed.append("tarefa \\WinKit\\Fase2")
    except Exception as exc:  # noqa: BLE001 — limpeza é melhor esforço
        report.errors.append(f"tarefa: {exc}")

    # SetupComplete.cmd e cópias do arquivo de respostas (podem conter senha)
    remove_setupcomplete_line(windows_dir, paths.agent_exe, report)
    panther = windows_dir / "Panther"
    for pattern in ("unattend*.xml", "Unattend/unattend*.xml", "autounattend*.xml"):
        for f in sorted(panther.glob(pattern)) if panther.is_dir() else []:
            _unlink(f, report)

    # logon automático: o Windows remove com LogonCount=1; aqui só conferimos
    reg = services.registry
    with contextlib.suppress(Exception):
        if reg.delete_value("HKLM", WINLOGON, "DefaultPassword"):
            report.removed.append("Winlogon\\DefaultPassword")
        count = reg.get("HKLM", WINLOGON, "AutoLogonCount")
        if not count:
            reg.set("HKLM", WINLOGON, "AutoAdminLogon", "sz", "0")

    # cópia local da receita (pode ter senha) — o estado e os logs ficam
    _unlink(paths.recipe, report)

    if remove_agent:
        cmd = f'cmd.exe /c rmdir /s /q "{paths.agent_dir}"'
        try:
            reg.set("HKLM", RUNONCE, RUNONCE_VALUE, "sz", cmd)
            report.removed.append(f"{paths.agent_dir} (agendado para o próximo login)")
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"agendar remoção do Agente: {exc}")
    return report
