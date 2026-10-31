"""Dublê dos pontos de restauração."""

from __future__ import annotations

from dataclasses import dataclass, field

from winkit.platform.restore import RestorePointInfo


@dataclass
class FakeRestorePoints:
    points: list[RestorePointInfo] = field(default_factory=list)
    enabled_drives: list[str] = field(default_factory=list)
    max_percent: dict[str, int] = field(default_factory=dict)
    create_code: int = 0

    def enable(self, drive: str) -> None:
        self.enabled_drives.append(drive)

    def ensure_max_percent(self, drive: str, percent: int) -> None:
        self.max_percent[drive] = max(percent, self.max_percent.get(drive, 0))

    def create(self, description: str) -> int:
        if self.create_code == 0:
            self.points.append(RestorePointInfo(len(self.points) + 1, description))
        return self.create_code

    def list(self) -> list[RestorePointInfo]:
        return list(self.points)
