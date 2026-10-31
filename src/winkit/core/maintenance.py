"""Especificação das tarefas de manutenção (V2-18). Função pura: o mesmo pedido, a mesma tarefa."""

from __future__ import annotations

from dataclasses import dataclass

from winkit.core.recipe.models import Maintenance

TASK_FOLDER = "\\WinKit\\Manutencao\\"
WINGET_TASK = "AtualizarApps"
DEFRAG_FOLDER = "\\Microsoft\\Windows\\Defrag\\"
DEFRAG_TASK = "ScheduledDefrag"
WINGET_ARGS = (
    "upgrade",
    "--all",
    "--silent",
    "--accept-package-agreements",
    "--accept-source-agreements",
    "--disable-interactivity",
)
DAYS = {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
}


@dataclass(frozen=True)
class TaskSpec:
    folder: str
    name: str
    execute: str
    arguments: str
    day: str  # nome do dia em inglês, como o ``New-ScheduledTaskTrigger`` espera
    time: str  # "HH:MM"
    weeks_interval: int

    @property
    def signature(self) -> str:
        """Identidade da tarefa: se mudar, a tarefa é recriada."""
        return f"{self.execute}|{self.arguments}|{self.day}|{self.time}|{self.weeks_interval}"


def winget_task(m: Maintenance, winget_exe: str, log_file: str) -> TaskSpec | None:
    if m.winget_upgrade == "off":
        return None
    args = " ".join([*WINGET_ARGS, "--log", f'"{log_file}"'])
    return TaskSpec(
        folder=TASK_FOLDER,
        name=WINGET_TASK,
        execute=winget_exe,
        arguments=args,
        day=DAYS[m.winget_day],
        time=m.winget_time,
        weeks_interval=1 if m.winget_upgrade == "weekly" else 4,
    )
