"""Perfis rápidos (V2-15): aplicar é **mesclar** com a receita e nunca desmarca nada (D-040).

A mesma função serve para a prévia (numa cópia) e para aplicar, então a tela mostra
exatamente o que vai mudar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from winkit.core.catalog.models import Catalogs, Preset
from winkit.core.recipe.models import Recipe, TweakSelection
from winkit.core.text import Msg, msg


@dataclass
class PresetResult:
    changes: list[Msg] = field(default_factory=list)
    warnings: list[Msg] = field(default_factory=list)


def preset_tweaks(preset: Preset, catalogs: Catalogs) -> list[str]:
    ids = list(preset.tweaks)
    for tw in catalogs.tweaks:
        if tw.category in preset.all_in_category and tw.risk == "safe" and tw.id not in ids:
            ids.append(tw.id)
    return ids


def missing_ids(preset: Preset, catalogs: Catalogs) -> list[str]:
    """Ids do perfil que não existem nos catálogos (o teste de catálogo exige lista vazia)."""
    out = [f"tweak:{i}" for i in preset.tweaks if catalogs.tweak(i) is None]
    out += [f"feature:{i}" for i in preset.features if catalogs.feature(i) is None]
    out += [f"bloat:{i}" for i in preset.bloatware_keep if catalogs.bloat(i) is None]
    out += [f"blocklist:{i}" for i in preset.blocklists if catalogs.blocklist(i) is None]
    if preset.dns_provider and catalogs.dns_provider(preset.dns_provider) is None:
        out.append(f"dns:{preset.dns_provider}")
    return out


def preview_preset(preset: Preset, recipe: Recipe, catalogs: Catalogs) -> PresetResult:
    return apply_preset(preset, recipe.model_copy(deep=True), catalogs)


def apply_preset(preset: Preset, recipe: Recipe, catalogs: Catalogs) -> PresetResult:  # noqa: PLR0912 — uma regra de mescla por campo
    res = PresetResult()
    selections = {s.id: s for s in recipe.tweaks}
    for tweak_id in preset_tweaks(preset, catalogs):
        tweak = catalogs.tweak(tweak_id)
        if tweak is None or not any(o in recipe.windows.target_os for o in tweak.windows.os):
            continue
        sel = selections.get(tweak_id)
        if sel is not None and sel.enabled:
            continue
        if sel is None:
            recipe.tweaks.append(TweakSelection(id=tweak_id))
        else:
            sel.enabled = True
        res.changes.append(msg("preset.tweak", name=tweak.title))
    if preset.power_scheme and recipe.power.scheme == "unchanged":
        recipe.power.scheme = preset.power_scheme
        res.changes.append(msg(f"preset.power.{preset.power_scheme}"))
    for feature_id in preset.features:
        entry = catalogs.feature(feature_id)
        if entry is not None and feature_id not in recipe.windows.optional_features:
            recipe.windows.optional_features = [*recipe.windows.optional_features, feature_id]
            res.changes.append(msg("preset.feature", name=entry.name))
    for pkg in preset.bloatware_keep:
        if pkg in recipe.bloatware.remove:
            recipe.bloatware.remove = [x for x in recipe.bloatware.remove if x != pkg]
            bloat = catalogs.bloat(pkg)
            res.warnings.append(msg("preset.keep_bloat", name=bloat.name if bloat else pkg))
    if preset.dns_provider and recipe.dns.provider == "unchanged":
        provider = catalogs.dns_provider(preset.dns_provider)
        if provider is not None:
            recipe.dns.provider = provider.id
            res.changes.append(msg("preset.dns", name=provider.name))
    for list_id in preset.blocklists:
        blocklist = catalogs.blocklist(list_id)
        if blocklist is not None and list_id not in recipe.dns.hosts_blocklists:
            recipe.dns.hosts_blocklists = [*recipe.dns.hosts_blocklists, list_id]
            res.changes.append(msg("preset.blocklist", name=blocklist.name))
    if preset.storage_sense and not recipe.maintenance.storage_sense:
        recipe.maintenance.storage_sense = True
        res.changes.append(msg("preset.storage_sense"))
    if preset.winget_weekly and recipe.maintenance.winget_upgrade == "off":
        recipe.maintenance.winget_upgrade = "weekly"
        res.changes.append(msg("preset.winget_weekly"))
    if preset.id not in recipe.presets_applied:
        recipe.presets_applied = [*recipe.presets_applied, preset.id]
    return res
