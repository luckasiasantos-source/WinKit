"""Dublê do dism de apps padrão."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FakeAssociations:
    exported: bytes = b""
    code: int = 0
    imported: list[bytes] = field(default_factory=list)

    def export(self, dest: Path) -> int:
        if self.code == 0:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(self.exported)
        return self.code

    def import_file(self, xml: Path) -> int:
        if self.code == 0:
            self.imported.append(xml.read_bytes())
        return self.code
