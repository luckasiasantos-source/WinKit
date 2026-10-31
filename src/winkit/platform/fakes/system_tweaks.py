"""Dublês de Appx e recursos do sistema."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from winkit.platform.appx import AppxRemoval
from winkit.platform.features import FeatureResult
from winkit.platform.windows_update import UpdateResult


@dataclass
class FakeAppx:
    present: set[str] = field(default_factory=set)
    removed: list[str] = field(default_factory=list)
    families: dict[str, str] = field(default_factory=dict)

    def remove(self, name: str) -> AppxRemoval:
        was = name in self.present
        self.present.discard(name)
        self.removed.append(name)
        return AppxRemoval(
            provisioned=int(was),
            installed=int(was),
            family=self.families.get(name) if was else None,
        )

    def is_present(self, name: str) -> bool:
        return name in self.present


@dataclass
class FakeFeatures:
    states: dict[str, bool] = field(default_factory=dict)  # nome → habilitado
    restart: bool = False
    renamed_to: str | None = None
    current_name: str = "PC-TESTE"

    def set_optional_feature(self, name: str, *, enabled: bool) -> FeatureResult:
        if name not in self.states:
            return "absent"
        if self.states[name] == enabled:
            return "same"
        self.states[name] = enabled
        return "restart" if self.restart else "changed"

    def rename_computer(self, name: str) -> bool:
        if name == self.current_name:
            return False
        self.renamed_to = name
        return True


@dataclass
class FakeUpdater:
    result: UpdateResult = field(default_factory=lambda: UpdateResult(2, 2, True, ("KB1", "KB2")))
    calls: list[bool] = field(default_factory=list)

    def install_all(self, *, include_drivers: bool, log: Path | None) -> UpdateResult:
        self.calls.append(include_drivers)
        return self.result


@dataclass
class FakeSession:
    idle: float = 0.0
    reboots: list[tuple[int, str]] = field(default_factory=list)

    def idle_seconds(self) -> float:
        return self.idle

    def reboot(self, *, delay_seconds: int, message: str) -> None:
        self.reboots.append((delay_seconds, message))
