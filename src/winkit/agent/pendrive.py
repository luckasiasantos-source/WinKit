"""Localiza o pendrive pelo marcador — nunca pela letra (R-31)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from winkit.core.errors import PendriveError
from winkit.core.layout import read_marker
from winkit.platform.environment import Environment


class Locator(Protocol):
    def find(self) -> Path | None: ...


class PendriveLocator:
    def __init__(self, env: Environment, pendrive_id: str) -> None:
        self._env = env
        self.pendrive_id = pendrive_id

    def find(self) -> Path | None:
        for root in self._env.drive_roots():
            try:
                marker = read_marker(root)
            except (PendriveError, OSError):
                continue
            if marker is not None and marker.pendrive_id == self.pendrive_id:
                return root
        return None
