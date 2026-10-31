"""Dublês de Appx e recursos do sistema."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from winkit.core.errors import PlatformError
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
    known: dict[str, bool] = field(default_factory=dict)  # nome → habilitado/instalado
    restart: bool = False
    renamed_to: str | None = None
    current_name: str = "PC-TESTE"
    #: (nome, fonte offline) de cada recurso ligado; ``None`` = pelo Windows Update.
    sources: list[tuple[str, Path | None]] = field(default_factory=list)
    #: Capacidades exigem internet: sem ela, a chamada falha como no Windows.
    online: bool = True

    def set_optional_feature(
        self, name: str, *, enabled: bool, source: Path | None = None
    ) -> FeatureResult:
        if name not in self.known:
            return "absent"
        if self.known[name] == enabled:
            return "same"
        self.known[name] = enabled
        if enabled:
            self.sources.append((name, source))
        return "restart" if self.restart else "changed"

    def set_capability(self, name: str, *, installed: bool) -> FeatureResult:
        if name not in self.known:
            return "absent"
        if self.known[name] == installed:
            return "same"
        if not self.online:
            raise PlatformError(f"{name}: sem acesso ao Windows Update")
        self.known[name] = installed
        return "changed"

    def states(self, features: list[str], capabilities: list[str]) -> dict[str, bool]:
        return {n: self.known[n] for n in [*features, *capabilities] if n in self.known}

    def rename_computer(self, name: str) -> bool:
        if name == self.current_name:
            return False
        self.renamed_to = name
        return True


@dataclass
class FakeIsoMounter:
    """Monta "ISOs" apontando para pastas de teste (``roots[nome da ISO]``)."""

    roots: dict[str, Path] = field(default_factory=dict)
    mounted: list[Path] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def mount(self, iso: Path) -> Path:
        root = self.roots.get(iso.name)
        if root is None:
            raise PlatformError(f"não montou: {iso}")
        self.mounted.append(iso)
        self.log.append(f"mount {iso.name}")
        return root

    def dismount(self, iso: Path) -> None:
        self.mounted.remove(iso)
        self.log.append(f"dismount {iso.name}")


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
