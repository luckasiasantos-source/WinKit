"""Inventário "antes" (V2-19): gravado no pendrive ao construir."""

from __future__ import annotations

from pathlib import Path

from winkit.core import layout
from winkit.core.fsutil import atomic_write_text
from winkit.core.inventory_snapshot import Snapshot
from winkit.core.recipe.models import Recipe
from winkit.platform.snapshot import take_snapshot

__all__ = ["take_snapshot", "write_before"]


def write_before(root: Path, recipe: Recipe, snapshot: Snapshot) -> Path:
    path = root / layout.snapshot_file(recipe.meta.profile_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, snapshot.model_dump_json(indent=1) + "\n")
    return path
