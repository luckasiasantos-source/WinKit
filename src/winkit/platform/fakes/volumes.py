"""Dublê dos volumes: cada letra aponta para uma pasta temporária."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from winkit.core.volumes import VolumeInfo


@dataclass
class FakeVolumes:
    items: list[VolumeInfo] = field(default_factory=list)
    roots: dict[str, Path] = field(default_factory=dict)

    def volumes(self) -> list[VolumeInfo]:
        return list(self.items)

    def root(self, letter: str) -> Path:
        return self.roots[letter.upper()]

    def add(
        self, serial: str, letter: str, base: Path, *, label: str = "Dados", system: bool = False
    ) -> VolumeInfo:
        v = VolumeInfo(
            serial=serial,
            letter=letter,
            label=label,
            size=500 * 2**30,
            free=200 * 2**30,
            is_system=system,
        )
        self.items.append(v)
        self.roots[letter] = base
        base.mkdir(parents=True, exist_ok=True)
        return v
