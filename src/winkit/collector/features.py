"""Recursos do Windows ligados no PC atual (V2-08): sugestões para a receita."""

from __future__ import annotations

from winkit.core.catalog.models import Catalogs
from winkit.core.recipe.models import Recipe
from winkit.platform.features import SystemFeatures


def enabled_here(features: SystemFeatures, catalogs: Catalogs) -> list[str]:
    """Ids do catálogo cujas partes estão todas ligadas neste PC."""
    names = [p.feature for f in catalogs.features for p in f.parts if p.feature]
    caps = [p.capability for f in catalogs.features for p in f.parts if p.capability]
    states = features.states(sorted(set(names)), sorted(set(caps)))
    return [f.id for f in catalogs.features if all(states.get(p.name, False) for p in f.parts)]


def set_feature(recipe: Recipe, feature_id: str, enabled: bool) -> None:
    chosen = [x for x in recipe.windows.optional_features if x != feature_id]
    if enabled:
        chosen.append(feature_id)
    recipe.windows.optional_features = chosen


def add_enabled_here(features: SystemFeatures, catalogs: Catalogs, recipe: Recipe) -> list[str]:
    """Marca na receita os recursos ligados aqui; devolve só os que eram novos."""
    added = [
        i for i in enabled_here(features, catalogs) if i not in recipe.windows.optional_features
    ]
    for feature_id in added:
        set_feature(recipe, feature_id, enabled=True)
    return added
