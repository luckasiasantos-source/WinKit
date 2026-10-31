"""Dublês de agendador, contas, ambiente e pastas conhecidas."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from winkit.core.paths.templates import profile_folders


@dataclass
class FakeScheduler:
    task_exe: Path | None = None
    removed: int = 0

    def ensure_phase2_task(self, exe: Path) -> bool:
        created = self.task_exe != exe
        self.task_exe = exe
        return created

    def remove_phase2_task(self) -> bool:
        existed = self.task_exe is not None
        self.task_exe = None
        self.removed += 1
        return existed


@dataclass
class FakeAccounts:
    admins: set[str] = field(default_factory=set)
    users: set[str] = field(default_factory=lambda: {"Samuel"})

    def ensure_administrator(self, username: str) -> str:
        if username not in self.users:
            return "no_user"
        if username in self.admins:
            return "already"
        self.admins.add(username)
        return "added"


@dataclass
class FakeEnvironment:
    roots: list[Path] = field(default_factory=list)
    internet: bool = True
    build: int | None = 26100
    name: str = "PC-TESTE"

    def drive_roots(self) -> list[Path]:
        return [r for r in self.roots if r.exists()]

    def has_internet(self) -> bool:
        return self.internet

    def windows_build(self) -> int | None:
        return self.build

    def computer_name(self) -> str:
        return self.name


@dataclass
class FakeKnownFolders:
    base: Path

    def machine(self) -> dict[str, str]:
        b = self.base
        return {
            "PROGRAMDATA": str(b / "ProgramData"),
            "PROGRAMFILES": str(b / "Program Files"),
            "PROGRAMFILESX86": str(b / "Program Files (x86)"),
            "PUBLIC": str(b / "Users" / "Public"),
        }

    def current_user(self) -> dict[str, str]:
        return profile_folders(str(self.base / "Users" / "Samuel"))

    def default_profile_root(self) -> str:
        return str(self.base / "Users" / "Default")

    def windows_dir(self) -> str:
        return str(self.base / "Windows")
