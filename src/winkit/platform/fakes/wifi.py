"""Dublê do Wi-Fi: perfis em memória e exportação a partir de XMLs de exemplo."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from winkit.core.wifi import parse_profile


@dataclass
class FakeWifi:
    wlan: bool = True
    #: Arquivos que ``export_profiles`` "exporta" (XMLs de exemplo).
    exportable: list[Path] = field(default_factory=list)
    installed: dict[str, bytes] = field(default_factory=dict)
    add_code: int = 0

    def has_wlan(self) -> bool:
        return self.wlan

    def export_profiles(self, dest: Path) -> list[Path]:
        dest.mkdir(parents=True, exist_ok=True)
        out = []
        for i, src in enumerate(self.exportable):
            target = dest / f"Wi-Fi-{i}.xml"
            shutil.copy2(src, target)
            out.append(target)
        return out

    def add_profile(self, xml_path: Path) -> int:
        if self.add_code == 0:
            data = xml_path.read_bytes()
            self.installed[parse_profile(data).name] = data
        return self.add_code

    def profile_exists(self, name: str) -> bool:
        return name in self.installed
