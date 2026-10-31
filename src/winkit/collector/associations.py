"""Apps padrão do PC atual (V2-05): exporta pelo ``dism`` e guarda o XML inteiro no pendrive."""

from __future__ import annotations

import tempfile
from pathlib import Path

from winkit.core import layout
from winkit.core.associations import Association, parse, summary
from winkit.core.catalog.models import AssociationGroup, Catalogs
from winkit.core.errors import WinKitError
from winkit.core.fsutil import atomic_write_bytes
from winkit.core.recipe.models import Recipe
from winkit.platform.associations import AssociationsTool


def collect_associations(
    tool: AssociationsTool, root: Path, recipe: Recipe, catalogs: Catalogs
) -> list[Association]:
    with tempfile.TemporaryDirectory(prefix="winkit-assoc-") as tmp:
        dest = Path(tmp) / "assoc.xml"
        code = tool.export(dest)
        if code != 0 or not dest.is_file():
            raise WinKitError(f"dism /Export-DefaultAppAssociations retornou {code}")
        data = dest.read_bytes()
    items = parse(data)
    rel = layout.associations_file(recipe.meta.profile_id)
    atomic_write_bytes(root / rel, data)
    d = recipe.default_apps
    d.associations_file = rel.removeprefix(f"{layout.WINKIT}/")
    if not d.groups:  # primeira leitura: marca os grupos que têm um app escolhido
        d.groups = [g.id for g in catalogs.association_groups if summary(items, g)]
    d.enabled = True
    return items


def read_saved(root: Path, recipe: Recipe) -> list[Association]:
    f = recipe.default_apps.associations_file
    if not f:
        return []
    path = layout.payload(root, f)
    return parse(path.read_bytes()) if path.is_file() else []


def group_rows(
    root: Path, recipe: Recipe, catalogs: Catalogs
) -> list[tuple[AssociationGroup, str | None]]:
    items = read_saved(root, recipe)
    return [(g, summary(items, g)) for g in catalogs.association_groups]


def set_group(recipe: Recipe, group_id: str, selected: bool) -> None:
    groups = [g for g in recipe.default_apps.groups if g != group_id]
    if selected:
        groups.append(group_id)
    recipe.default_apps.groups = groups
