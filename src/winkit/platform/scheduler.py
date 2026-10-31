"""Tarefa agendada da Fase 2 (D-012, D-023)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from winkit.platform.powershell import PowerShell

TASK_PATH = "\\WinKit\\"
TASK_NAME = "Fase2"
ADMINISTRATORS_SID = "S-1-5-32-544"

_ENSURE = r"""
$existing = Get-ScheduledTask -TaskPath $p.TaskPath -TaskName $p.TaskName -ErrorAction SilentlyContinue
if ($existing -and $existing.Actions[0].Execute -eq $p.Exe) { 'exists'; return }
$action = New-ScheduledTaskAction -Execute $p.Exe -Argument 'phase2'
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -GroupId $p.Sid -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 12)
Register-ScheduledTask -TaskPath $p.TaskPath -TaskName $p.TaskName -Action $action `
    -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
'created'
"""

_REMOVE = r"""
$t = Get-ScheduledTask -TaskPath $p.TaskPath -TaskName $p.TaskName -ErrorAction SilentlyContinue
if ($t) { Unregister-ScheduledTask -TaskPath $p.TaskPath -TaskName $p.TaskName -Confirm:$false; 'removed' }
else { 'absent' }
"""


class TaskScheduler(Protocol):
    def ensure_phase2_task(self, exe: Path) -> bool:
        """Garante a tarefa; devolve True se precisou criar."""
        ...

    def remove_phase2_task(self) -> bool: ...


class WindowsTaskScheduler:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def _params(self) -> dict[str, str]:
        return {"TaskPath": TASK_PATH, "TaskName": TASK_NAME, "Sid": ADMINISTRATORS_SID}

    def ensure_phase2_task(self, exe: Path) -> bool:
        out = self._ps.run_json(_ENSURE, {**self._params(), "Exe": str(exe)}, timeout=120)
        return out == ["created"]

    def remove_phase2_task(self) -> bool:
        return self._ps.run_json(_REMOVE, self._params(), timeout=120) == ["removed"]
