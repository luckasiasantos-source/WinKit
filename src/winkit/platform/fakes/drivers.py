"""``DriverManager`` falso."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from winkit.platform.drivers import DriverInstallResult, InstalledDriver


def sample_drivers() -> list[InstalledDriver]:
    return [
        InstalledDriver(
            "oem12.inf", "rt25cx21x64.inf", "Net", "Realtek", "10.68.815.2024", "2024-08-15", False
        ),
        InstalledDriver(
            "oem3.inf", "nvlddmkm.inf", "Display", "NVIDIA", "32.0.15.6094", "2024-10-01", False
        ),
        InstalledDriver("oem7.inf", "hpprinter.inf", "Printer", "HP", "1.0", None, False),
        InstalledDriver(
            "oem9.inf",
            "amdgpio2.inf",
            "System",
            "Advanced Micro Devices",
            "2.2.0.130",
            "2023-01-01",
            True,
        ),
    ]


@dataclass
class FakeDriverManager:
    drivers: list[InstalledDriver] = field(default_factory=sample_drivers)
    installed: list[Path] = field(default_factory=list)
    exit_code: int = 0

    def list_third_party(self) -> list[InstalledDriver]:
        return list(self.drivers)

    def export(self, published_name: str, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        drv = next(d for d in self.drivers if d.published_name == published_name)
        (dest / drv.original_inf).write_text("[Version]\nSignature=$WINDOWS NT$\n")
        (dest / (drv.original_inf[:-4] + ".sys")).write_bytes(b"MZ-driver")

    def install(self, folder: Path, log: Path | None = None) -> DriverInstallResult:
        self.installed.append(folder)
        return DriverInstallResult(self.exit_code)
