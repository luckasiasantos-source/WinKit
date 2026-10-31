"""``dism`` para exportar e importar os apps padrão (V2-05). Só código de saída e arquivos."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from winkit.platform.runner import CommandRunner
from winkit.platform.system import system32


class AssociationsTool(Protocol):
    def export(self, dest: Path) -> int: ...

    def import_file(self, xml: Path) -> int:
        """Vale para os perfis criados depois (por isso só na Fase 1)."""
        ...


class DismAssociations:
    def __init__(self, runner: CommandRunner) -> None:
        self._runner = runner

    def _dism(self, arg: str) -> int:
        cmd = [str(system32("dism.exe")), "/Online", arg]
        return self._runner.run(cmd, timeout=300).exit_code

    def export(self, dest: Path) -> int:
        dest.parent.mkdir(parents=True, exist_ok=True)
        return self._dism(f"/Export-DefaultAppAssociations:{dest}")

    def import_file(self, xml: Path) -> int:
        return self._dism(f"/Import-DefaultAppAssociations:{xml}")
