"""Unidades de rede do PC atual (V2-17)."""

from __future__ import annotations

from winkit.core.recipe.models import NetworkDrive, Recipe
from winkit.platform.netdrives import read_mapped
from winkit.platform.registry import Registry


def collect_drives(registry: Registry, recipe: Recipe) -> list[NetworkDrive]:
    """Acrescenta à receita as unidades mapeadas aqui (nunca troca as que já estão lá)."""
    known = {d.letter for d in recipe.network_drives}
    added = [
        NetworkDrive(letter=letter, remote_path=path)
        for letter, path in sorted(read_mapped(registry).items())
        if letter not in known and letter >= "D"
    ]
    recipe.network_drives = [*recipe.network_drives, *added]
    return added


def add_drive(recipe: Recipe, letter: str, path: str) -> NetworkDrive:
    drive = NetworkDrive(letter=letter.upper().rstrip(":"), remote_path=path)
    recipe.network_drives = [d for d in recipe.network_drives if d.letter != drive.letter]
    recipe.network_drives.append(drive)
    return drive


def remove_drive(recipe: Recipe, letter: str) -> bool:
    before = len(recipe.network_drives)
    letter = letter.upper().rstrip(":")
    recipe.network_drives = [d for d in recipe.network_drives if d.letter != letter]
    return len(recipe.network_drives) != before
