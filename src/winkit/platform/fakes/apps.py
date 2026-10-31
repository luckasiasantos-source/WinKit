"""Dublês de inventário, winget, instaladores e atalhos."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from winkit.core.inventory import InstalledApp
from winkit.core.recipe.models import InstallerSpec, Scope
from winkit.platform.installers import InstallOutcome


def sample_inventory() -> list[InstalledApp]:
    return [
        InstalledApp(name="Discord", version="1.0.9170", publisher="Discord Inc.", scope="user"),
        InstalledApp(
            name="7-Zip 24.08 (x64)", version="24.08", publisher="Igor Pavlov", scope="machine"
        ),
        InstalledApp(name="Programa Obscuro", version="2.0", publisher="Ninguém", scope="machine"),
        InstalledApp(
            name="Microsoft Visual C++ 2015-2022 Redistributable (x64)",
            version="14.40",
            publisher="Microsoft",
            scope="machine",
            redistributable=True,
        ),
        InstalledApp(
            name="Microsoft.WhatsApp", scope="user", origin="appx", winget_source="msstore"
        ),
    ]


SAMPLE_EXPORT = {
    "Sources": [
        {
            "Packages": [
                {"PackageIdentifier": "Discord.Discord"},
                {"PackageIdentifier": "7zip.7zip"},
            ],
            "SourceDetails": {"Name": "winget"},
        },
        {"Packages": [{"PackageIdentifier": "9NKSQGP7F2NH"}], "SourceDetails": {"Name": "msstore"}},
    ]
}


@dataclass
class FakeInventory:
    apps: list[InstalledApp] = field(default_factory=sample_inventory)

    def installed(self, *, include_appx: bool = True) -> list[InstalledApp]:
        return [a for a in self.apps if include_appx or a.origin != "appx"]


@dataclass
class FakeWinget:
    is_available: bool = True
    become_available_after_register: bool = True
    registered: int = 0
    installed_ids: set[str] = field(default_factory=set)
    install_code: int = 0
    calls: list[tuple[str, ...]] = field(default_factory=list)
    #: id → (tipo winget, escopo, switches) para simular "winget download"
    downloads: dict[str, tuple[str, str, str]] = field(default_factory=dict)
    #: id → versão que o "winget download" baixa (padrão 1.0)
    versions: dict[str, str] = field(default_factory=dict)

    def available(self) -> bool:
        return self.is_available

    def register(self) -> None:
        self.registered += 1
        if self.become_available_after_register:
            self.is_available = True

    def export(self, dest: Path) -> bool:
        dest.write_text(json.dumps(SAMPLE_EXPORT), encoding="utf-8")
        return True

    def download(self, package_id: str, dest: Path, *, source: str = "winget") -> int:
        self.calls.append(("download", package_id))
        if package_id not in self.downloads:
            return 0x8A150014
        kind, scope, switches = self.downloads[package_id]
        version = self.versions.get(package_id, "1.0")
        dest.mkdir(parents=True, exist_ok=True)
        (dest / f"{package_id}_{version}_{kind}.exe").write_bytes(b"MZ" + version.encode())
        (dest / f"{package_id}_{version}.yaml").write_text(
            f"PackageIdentifier: {package_id}\nPackageVersion: {version}\nInstallerType: {kind}\n"
            f"Scope: {scope}\nInstallerSwitches:\n  Silent: {switches}\n",
            encoding="utf-8",
        )
        return 0

    def install(
        self, package_id: str, *, scope: str, source: str = "winget", log: Path | None = None
    ) -> int:
        self.calls.append(("install", package_id, scope, source))
        if self.install_code == 0:
            self.installed_ids.add(package_id)
        return self.install_code

    def is_installed(self, package_id: str) -> bool:
        return package_id in self.installed_ids


@dataclass
class FakeInstallerRunner:
    exit_code: int = 0
    timed_out: bool = False
    ran: list[tuple[str, tuple[str, ...], Scope]] = field(default_factory=list)
    killed: list[str] = field(default_factory=list)

    def run(self, file: Path, spec: InstallerSpec, *, scope: Scope, log: Path) -> InstallOutcome:
        self.ran.append((file.name, tuple(spec.args), scope))
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"instalado {file.name}\n", encoding="utf-8")
        return InstallOutcome(self.exit_code, self.timed_out)

    def kill(self, process_names: list[str]) -> None:
        self.killed.extend(process_names)


@dataclass
class FakeShortcuts:
    created: list[tuple[Path, str, str]] = field(default_factory=list)

    def create(self, path: Path, target: str, arguments: str = "") -> None:
        self.created.append((path, target, arguments))
