"""Dublês de Appx e recursos do sistema."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from winkit.core.devices import ProblemDevice
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

    #: Ids de hardware que o "Windows Update" conhece (V2-09).
    driver_catalog: set[str] = field(default_factory=set)
    driver_searches: list[list[str]] = field(default_factory=list)
    #: Chamado com os ids instalados (o teste "conserta" os dispositivos).
    on_driver_install: Callable[[list[str]], None] | None = None

    def install_all(self, *, include_drivers: bool, log: Path | None) -> UpdateResult:
        self.calls.append(include_drivers)
        return self.result

    def install_drivers_for(self, hardware_ids: list[str], *, log: Path | None) -> UpdateResult:
        self.driver_searches.append(list(hardware_ids))
        hits = [
            h for h in hardware_ids if h.casefold() in {x.casefold() for x in self.driver_catalog}
        ]
        if hits and self.on_driver_install is not None:
            self.on_driver_install(hits)
        return UpdateResult(len(hits), 2, False, tuple(f"driver {h}" for h in hits))


@dataclass
class FakeDevices:
    devices: list[ProblemDevice] = field(default_factory=list)

    def problem_devices(self) -> list[ProblemDevice]:
        return list(self.devices)

    def fix(self, hardware_ids: list[str]) -> None:
        ids = {h.casefold() for h in hardware_ids}
        self.devices = [d for d in self.devices if not ids & {h.casefold() for h in d.hardware_ids}]


@dataclass
class FakeSession:
    idle: float = 0.0
    reboots: list[tuple[int, str]] = field(default_factory=list)

    def idle_seconds(self) -> float:
        return self.idle

    def reboot(self, *, delay_seconds: int, message: str) -> None:
        self.reboots.append((delay_seconds, message))


@dataclass
class FakeDriveMapper:
    online: set[str] = field(default_factory=set)  # caminhos de servidores "no ar"
    mapped: dict[str, str] = field(default_factory=dict)

    def map_now(self, letter: str, path: str) -> bool:
        if path not in self.online:
            return False
        self.mapped[letter] = path
        return True


@dataclass
class FakeFontLoader:
    loaded: list[Path] = field(default_factory=list)

    def load(self, path: Path) -> bool:
        self.loaded.append(path)
        return True
