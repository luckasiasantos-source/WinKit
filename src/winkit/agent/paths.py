"""Caminhos locais do Agente no Windows novo (D-013)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from winkit.core import layout


@dataclass(frozen=True)
class AgentPaths:
    base: Path  # C:\ProgramData\WinKit

    @property
    def recipe(self) -> Path:
        return self.base / "receita.json"

    @property
    def state(self) -> Path:
        return self.base / "estado.json"

    @property
    def bootstrap(self) -> Path:
        return self.base / "bootstrap.json"

    @property
    def logs(self) -> Path:
        return self.base / "Logs"

    @property
    def agent_dir(self) -> Path:
        return self.base / "Agent" / "winkit-agent"

    @property
    def agent_exe(self) -> Path:
        return self.agent_dir / layout.AGENT_EXE_NAME

    @property
    def summary_json(self) -> Path:
        return self.base / "resumo.json"

    @property
    def summary_html(self) -> Path:
        return self.base / "resumo.html"

    @property
    def locks(self) -> Path:
        return self.base / "locks"
