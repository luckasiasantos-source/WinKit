"""Tarefa agendada da Fase 2 (D-012, D-023)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol

from winkit.core.maintenance import TaskSpec
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


_USER_TASK = r"""
$t = Get-ScheduledTask -TaskPath $p.Folder -TaskName $p.Name -ErrorAction SilentlyContinue
if ($t -and $t.Description -eq $p.Signature) { 'same'; return }
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute $p.Execute -Argument $p.Arguments
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $p.Day -At $p.Time -WeeksInterval $p.Weeks
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskPath $p.Folder -TaskName $p.Name -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Description $p.Signature -Force | Out-Null
'created'
"""

_USER_TASK_SAME = r"""
$t = Get-ScheduledTask -TaskPath $p.Folder -TaskName $p.Name -ErrorAction SilentlyContinue
if ($t -and $t.Description -eq $p.Signature) { 'same' } else { 'different' }
"""

_BUILTIN = r"""
$t = Get-ScheduledTask -TaskPath $p.Folder -TaskName $p.Name -ErrorAction SilentlyContinue
if (-not $t) { 'absent'; return }
if ([string]$t.State -ne 'Disabled') { 'enabled'; return }
if ($p.Enable) { Enable-ScheduledTask -TaskPath $p.Folder -TaskName $p.Name | Out-Null; 'changed' }
else { 'disabled' }
"""

_REMOVE_FOLDER = r"""
$ts = @(Get-ScheduledTask -TaskPath $p.Folder -ErrorAction SilentlyContinue)
foreach ($t in $ts) { Unregister-ScheduledTask -TaskPath $t.TaskPath -TaskName $t.TaskName -Confirm:$false }
[int]$ts.Count
"""

BuiltinState = Literal["absent", "enabled", "disabled", "changed"]


class TaskScheduler(Protocol):
    def ensure_phase2_task(self, exe: Path) -> bool:
        """Garante a tarefa; devolve True se precisou criar."""
        ...

    def remove_phase2_task(self) -> bool: ...

    def ensure_user_task(self, spec: TaskSpec) -> bool:
        """Tarefa do usuário atual (V2-18); True se criou ou recriou."""
        ...

    def user_task_matches(self, spec: TaskSpec) -> bool: ...

    def builtin_task(self, folder: str, name: str, *, enable: bool) -> BuiltinState:
        """Estado de uma tarefa do próprio Windows; com ``enable``, habilita se estiver desligada."""
        ...

    def remove_folder(self, folder: str) -> int:
        """Desfazer: remove as tarefas da pasta; devolve quantas eram."""
        ...


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

    @staticmethod
    def _spec(spec: TaskSpec) -> dict[str, object]:
        return {
            "Folder": spec.folder,
            "Name": spec.name,
            "Execute": spec.execute,
            "Arguments": spec.arguments,
            "Day": spec.day,
            "Time": spec.time,
            "Weeks": spec.weeks_interval,
            "Signature": spec.signature,
        }

    def ensure_user_task(self, spec: TaskSpec) -> bool:
        return self._ps.run_json(_USER_TASK, self._spec(spec), timeout=120) == ["created"]

    def user_task_matches(self, spec: TaskSpec) -> bool:
        return self._ps.run_json(_USER_TASK_SAME, self._spec(spec), timeout=120) == ["same"]

    def builtin_task(self, folder: str, name: str, *, enable: bool) -> BuiltinState:
        out = self._ps.run_json(_BUILTIN, {"Folder": folder, "Name": name, "Enable": enable})
        value = str(out[0]) if out else "absent"
        return value if value in ("absent", "enabled", "disabled", "changed") else "absent"  # type: ignore[return-value]

    def remove_folder(self, folder: str) -> int:
        out = self._ps.run_json(_REMOVE_FOLDER, {"Folder": folder}, timeout=120)
        return int(out[0]) if out else 0
