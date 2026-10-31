"""winget: export, download, install (PLANO.md §7.1.4, §13.4).

Só códigos de saída são interpretados (R-13). No Windows o código de saída é um inteiro
sem sinal de 32 bits; os códigos do winget começam com 0x8A15.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from winkit.platform.powershell import PowerShell
from winkit.platform.runner import CommandRunner

OK = 0
ALREADY_INSTALLED = 0x8A150061
UPDATE_NOT_APPLICABLE = 0x8A15002B
NO_APPLICATIONS_FOUND = 0x8A150014
#: Instalado, mas precisa reiniciar (APPINSTALLER_CLI_ERROR_INSTALL_REBOOT_REQUIRED_*) — DT-013.
REBOOT_CODES = frozenset({0x8A150109, 0x8A15010A, 3010, 1641})
SUCCESS_CODES = frozenset({OK, ALREADY_INSTALLED, UPDATE_NOT_APPLICABLE})
APP_INSTALLER_FAMILY = "Microsoft.DesktopAppInstaller_8wekyb3d8bbwe"

_COMMON = ["--accept-source-agreements", "--disable-interactivity"]


def normalize_code(code: int) -> int:
    return code & 0xFFFFFFFF


class Winget(Protocol):
    def available(self) -> bool: ...

    def register(self) -> None: ...

    def export(self, dest: Path) -> bool: ...

    def download(self, package_id: str, dest: Path, *, source: str = "winget") -> int: ...

    def install(
        self, package_id: str, *, scope: str, source: str = "winget", log: Path | None = None
    ) -> int: ...

    def is_installed(self, package_id: str) -> bool: ...


def find_winget() -> Path | None:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        alias = Path(local) / "Microsoft" / "WindowsApps" / "winget.exe"
        if alias.exists():
            return alias
    program_files = Path(os.environ.get("PROGRAMFILES") or r"C:\Program Files")
    try:
        candidates = sorted(
            (program_files / "WindowsApps").glob(
                "Microsoft.DesktopAppInstaller_*_x64__8wekyb3d8bbwe"
            ),
            reverse=True,
        )
    except OSError:
        return None
    for folder in candidates:
        exe = folder / "winget.exe"
        if exe.exists():
            return exe
    return None


class WindowsWinget:
    def __init__(self, runner: CommandRunner, ps: PowerShell) -> None:
        self._runner = runner
        self._ps = ps

    def _exe(self) -> Path | None:
        return find_winget()

    def available(self) -> bool:
        exe = self._exe()
        if exe is None:
            return False
        return self._runner.run([str(exe), "--version"], timeout=60).exit_code == 0

    def register(self) -> None:
        self._ps.run(
            "Add-AppxPackage -RegisterByFamilyName -MainPackage $p.Family",
            {"Family": APP_INSTALLER_FAMILY},
            timeout=600,
        )

    def export(self, dest: Path) -> bool:
        exe = self._exe()
        if exe is None:
            return False
        res = self._runner.run(
            [str(exe), "export", "-o", str(dest), "--include-versions", *_COMMON], timeout=600
        )
        return dest.is_file() and normalize_code(res.exit_code) in SUCCESS_CODES

    def download(self, package_id: str, dest: Path, *, source: str = "winget") -> int:
        exe = self._exe()
        if exe is None:
            return -1
        dest.mkdir(parents=True, exist_ok=True)
        res = self._runner.run(
            [
                str(exe),
                "download",
                "--id",
                package_id,
                "--exact",
                "--source",
                source,
                "--download-directory",
                str(dest),
                "--accept-package-agreements",
                *_COMMON,
            ],
            timeout=3600,
        )
        return normalize_code(res.exit_code)

    def install(
        self, package_id: str, *, scope: str, source: str = "winget", log: Path | None = None
    ) -> int:
        exe = self._exe()
        if exe is None:
            return -1
        args = [
            str(exe),
            "install",
            "--id",
            package_id,
            "--exact",
            "--silent",
            "--source",
            source,
            "--accept-package-agreements",
            *_COMMON,
        ]
        if source != "msstore":
            args += ["--scope", scope]
        res = self._runner.run(args, timeout=3600, log_to=log)
        if res.timed_out:
            return -2
        return normalize_code(res.exit_code)

    def is_installed(self, package_id: str) -> bool:
        exe = self._exe()
        if exe is None:
            return False
        res = self._runner.run(
            [str(exe), "list", "--id", package_id, "--exact", *_COMMON], timeout=300
        )
        return normalize_code(res.exit_code) == OK
