"""Persistência atômica do ``estado.json`` (R-16, R-30)."""

from __future__ import annotations

from pathlib import Path

from winkit.core.errors import StateError
from winkit.core.fsutil import atomic_write_text
from winkit.core.state.models import AgentState, dump_state, load_state


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> AgentState | None:
        if not self.path.is_file():
            return None
        try:
            return load_state(self.path.read_text(encoding="utf-8"))
        except StateError:
            corrupt = self.path.with_suffix(".corrompido.json")
            self.path.replace(corrupt)
            raise

    def save(self, state: AgentState) -> None:
        atomic_write_text(self.path, dump_state(state))
