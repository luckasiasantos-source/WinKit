"""Coleta de drivers do PC atual (PLANO.md §7.2, item 7)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from winkit.core import layout
from winkit.core.catalog.models import Catalogs
from winkit.core.recipe.models import DriverItem, Recipe
from winkit.core.text import slugify
from winkit.platform.drivers import DriverManager, InstalledDriver


@dataclass(frozen=True)
class DriverCandidate:
    driver: InstalledDriver
    label: str
    priority: int
    recommended: bool

    @property
    def item_id(self) -> str:
        d = self.driver
        return slugify(f"{d.class_name}-{d.provider}-{d.published_name.removesuffix('.inf')}")

    @property
    def payload_path(self) -> str:
        d = self.driver
        folder = slugify(f"{d.provider}_{d.published_name.removesuffix('.inf')}_{d.version}")
        return f"Drivers/{slugify(d.class_name)}/{folder}"


def list_candidates(manager: DriverManager, catalogs: Catalogs) -> list[DriverCandidate]:
    out = []
    for d in manager.list_third_party():
        cls = catalogs.driver_class(d.class_name)
        out.append(
            DriverCandidate(
                driver=d,
                label=cls.label if cls else d.class_name,
                priority=cls.priority if cls else 5,
                recommended=bool(cls and cls.recommended),
            )
        )
    return sorted(out, key=lambda c: (c.priority, c.driver.class_name, c.driver.provider))


def export_drivers(
    manager: DriverManager,
    candidates: list[DriverCandidate],
    *,
    root: Path,
    recipe: Recipe,
) -> list[DriverItem]:
    """Exporta para o pendrive e acrescenta/atualiza os itens na receita."""
    added: list[DriverItem] = []
    by_id = {d.id: i for i, d in enumerate(recipe.drivers)}
    for cand in candidates:
        dest = layout.payload(root, cand.payload_path)
        if not any(dest.rglob("*.inf")):
            manager.export(cand.driver.published_name, dest)
        item = DriverItem.model_validate(
            {
                "id": cand.item_id,
                "selected": True,
                "path": cand.payload_path,
                "class": cand.driver.class_name,
                "provider": cand.driver.provider,
                "version": cand.driver.version,
                "original_inf": cand.driver.original_inf,
                "priority": cand.priority,
            }
        )
        if item.id in by_id:
            recipe.drivers[by_id[item.id]] = item
        else:
            by_id[item.id] = len(recipe.drivers)
            recipe.drivers.append(item)
        added.append(item)
    return added
