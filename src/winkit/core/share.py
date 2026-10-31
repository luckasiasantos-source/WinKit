"""Receitas compartilháveis e modelos prontos (V2-23, D-040).

O formato ``ShareableRecipe`` **não tem** campos para dados pessoais (conta, nomes, senhas,
drivers, backups, Wi-Fi, volumes, variáveis, fontes, instaladores offline…): com
``extra="forbid"``, um arquivo com eles é recusado. Importar sempre **mescla** e nunca desmarca.
Só há ids de catálogo e do winget; nenhum campo executa nada (R-34).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from winkit.core.catalog.models import Catalogs
from winkit.core.recipe.models import (
    AppItem,
    BrowserConfig,
    BrowserExtension,
    PowerScheme,
    Recipe,
    Scope,
    TweakSelection,
)
from winkit.core.text import Msg, msg, slugify

SHARE_SCHEMA_VERSION: Literal[1] = 1
EXTENSION = ".winkit.json"


class _Share(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShareApp(_Share):
    winget_id: Annotated[str, Field(min_length=3, max_length=120)]
    name: str
    scope: Scope = "machine"
    order: int = 100


class ShareBrowser(_Share):
    id: str
    extensions: list[BrowserExtension] = Field(default_factory=list)
    search: str | None = None
    mode: Literal["suggest", "force"] = "suggest"


class ShareableRecipe(_Share):
    share_schema_version: Literal[1] = SHARE_SCHEMA_VERSION
    winkit_version: str
    title: str
    description: str = ""
    language: str | None = None
    apps: list[ShareApp] = Field(default_factory=list)
    bloatware: list[str] = Field(default_factory=list)
    tweaks: list[str] = Field(default_factory=list)
    power_scheme: PowerScheme = "unchanged"
    optional_features: list[str] = Field(default_factory=list)
    winget_upgrade: Literal["off", "weekly", "monthly"] = "off"
    storage_sense: bool = False
    dns_provider: str = "unchanged"
    require_doh: bool = False
    hosts_blocklists: list[str] = Field(default_factory=list)
    browsers: list[ShareBrowser] = Field(default_factory=list)
    personal_groups: list[str] = Field(default_factory=list)
    presets_applied: list[str] = Field(default_factory=list)


class ShareError(ValueError):
    pass


def export_recipe(recipe: Recipe, *, title: str, description: str, version: str) -> ShareableRecipe:
    dns_provider = recipe.dns.provider
    if dns_provider == "custom" or recipe.dns.provider_id:  # servidores próprios e ids pessoais
        dns_provider = "unchanged"
    return ShareableRecipe(
        winkit_version=version,
        title=title,
        description=description,
        apps=[
            ShareApp(winget_id=a.winget_id, name=a.name, scope=a.scope, order=a.order)
            for a in recipe.selected_apps()
            if a.winget_id and a.source != "portable"
        ],
        bloatware=sorted(recipe.bloatware.remove),
        tweaks=[s.id for s in recipe.enabled_tweaks()],
        power_scheme=recipe.power.scheme,
        optional_features=list(recipe.windows.optional_features),
        winget_upgrade=recipe.maintenance.winget_upgrade,
        storage_sense=recipe.maintenance.storage_sense,
        dns_provider=dns_provider,
        require_doh=recipe.dns.require_doh if dns_provider != "unchanged" else False,
        hosts_blocklists=list(recipe.dns.hosts_blocklists),
        browsers=[  # sem página inicial (pode ser pessoal)
            ShareBrowser(id=b.id, extensions=b.extensions, search=b.search, mode=b.mode)
            for b in recipe.browsers
            if b.selected
        ],
        personal_groups=list(recipe.personal.groups),
        presets_applied=list(recipe.presets_applied),
    )


def dumps(share: ShareableRecipe) -> str:
    return share.model_dump_json(indent=2, exclude_none=True) + "\n"


def loads(text: str) -> ShareableRecipe:
    try:
        return ShareableRecipe.model_validate(json.loads(text))
    except (ValueError, ValidationError) as exc:
        raise ShareError(str(exc)) from exc


@dataclass
class ImportResult:
    changes: list[Msg] = field(default_factory=list)
    ignored: list[Msg] = field(default_factory=list)


def _unique_id(name: str, taken: set[str]) -> str:
    base = slugify(name)
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f"{base}-{n}", n + 1
    taken.add(candidate)
    return candidate


def preview_import(share: ShareableRecipe, recipe: Recipe, catalogs: Catalogs) -> ImportResult:
    return import_recipe(share, recipe.model_copy(deep=True), catalogs)


def import_recipe(share: ShareableRecipe, recipe: Recipe, catalogs: Catalogs) -> ImportResult:
    res = ImportResult()
    _merge_apps(share, recipe, res)
    _merge_system(share, recipe, catalogs, res)
    _merge_network(share, recipe, catalogs, res)
    for b in share.browsers:
        _merge_browser(b, recipe, catalogs, res)
    for group_id in share.personal_groups:
        if catalogs.personal_group(group_id) and group_id not in recipe.personal.groups:
            recipe.personal.groups = [*recipe.personal.groups, group_id]
    for preset_id in share.presets_applied:
        if catalogs.preset(preset_id) and preset_id not in recipe.presets_applied:
            recipe.presets_applied = [*recipe.presets_applied, preset_id]
    return res


def _merge_apps(share: ShareableRecipe, recipe: Recipe, res: ImportResult) -> None:
    have = {a.winget_id.casefold() for a in recipe.apps if a.winget_id}
    ids = {a.id for a in recipe.apps}
    for app in share.apps:
        if app.winget_id.casefold() in have:
            continue
        recipe.apps.append(
            AppItem(
                id=_unique_id(app.name, ids),
                name=app.name,
                source="winget_online",
                scope=app.scope,
                winget_id=app.winget_id,
                order=app.order,
            )
        )
        have.add(app.winget_id.casefold())
        res.changes.append(msg("share.app", name=app.name, id=app.winget_id))


def _merge_system(  # noqa: PLR0912 — uma regra de mescla por seção
    share: ShareableRecipe, recipe: Recipe, catalogs: Catalogs, res: ImportResult
) -> None:
    for pkg in share.bloatware:
        entry = catalogs.bloat(pkg)
        if entry is None or entry.risk == "blocked":
            res.ignored.append(msg("share.ignored_bloat", id=pkg))
        elif pkg not in recipe.bloatware.remove:
            recipe.bloatware.remove = [*recipe.bloatware.remove, pkg]
            res.changes.append(msg("share.bloat", name=entry.name))
    selections = {s.id: s for s in recipe.tweaks}
    for tweak_id in share.tweaks:
        tweak = catalogs.tweak(tweak_id)
        sel = selections.get(tweak_id)
        if tweak is None:
            res.ignored.append(msg("share.ignored_tweak", id=tweak_id))
        elif sel is None or not sel.enabled:
            if sel is None:
                recipe.tweaks.append(TweakSelection(id=tweak_id))
            else:
                sel.enabled = True
            res.changes.append(msg("preset.tweak", name=tweak.title))
    if share.power_scheme != "unchanged" and recipe.power.scheme == "unchanged":
        recipe.power.scheme = share.power_scheme
        res.changes.append(msg(f"preset.power.{share.power_scheme}"))
    for feature_id in share.optional_features:
        feature = catalogs.feature(feature_id)
        if feature is None:
            res.ignored.append(msg("share.ignored_feature", id=feature_id))
        elif feature_id not in recipe.windows.optional_features:
            recipe.windows.optional_features = [*recipe.windows.optional_features, feature_id]
            res.changes.append(msg("preset.feature", name=feature.name))
    if share.winget_upgrade != "off" and recipe.maintenance.winget_upgrade == "off":
        recipe.maintenance.winget_upgrade = share.winget_upgrade
        res.changes.append(msg("preset.winget_weekly"))
    if share.storage_sense and not recipe.maintenance.storage_sense:
        recipe.maintenance.storage_sense = True
        res.changes.append(msg("preset.storage_sense"))


def _merge_network(
    share: ShareableRecipe, recipe: Recipe, catalogs: Catalogs, res: ImportResult
) -> None:
    if share.dns_provider != "unchanged" and recipe.dns.provider == "unchanged":
        provider = catalogs.dns_provider(share.dns_provider)
        if provider is None or provider.needs_id:
            res.ignored.append(msg("share.ignored_dns", id=share.dns_provider))
        else:
            recipe.dns.provider = provider.id
            recipe.dns.require_doh = share.require_doh
            res.changes.append(msg("preset.dns", name=provider.name))
    for list_id in share.hosts_blocklists:
        blocklist = catalogs.blocklist(list_id)
        if blocklist is None:
            res.ignored.append(msg("share.ignored_blocklist", id=list_id))
        elif list_id not in recipe.dns.hosts_blocklists:
            recipe.dns.hosts_blocklists = [*recipe.dns.hosts_blocklists, list_id]
            res.changes.append(msg("preset.blocklist", name=blocklist.name))


def _merge_browser(b: ShareBrowser, recipe: Recipe, catalogs: Catalogs, res: ImportResult) -> None:
    entry = catalogs.browser(b.id)
    if entry is None:
        res.ignored.append(msg("share.ignored_browser", id=b.id))
        return
    cfg = next((x for x in recipe.browsers if x.id == b.id), None)
    if cfg is None:
        cfg = BrowserConfig(id=b.id, mode=b.mode)
        recipe.browsers = [*recipe.browsers, cfg]
    known = {e.id for e in cfg.extensions}
    new = [e for e in b.extensions if e.id not in known]
    if new:
        cfg.extensions = [*cfg.extensions, *new]
    search_set = bool(b.search and cfg.search is None and catalogs.search_provider(b.search))
    if search_set:
        cfg.search = b.search
    if new or search_set:
        res.changes.append(msg("share.browser", name=entry.name, n=len(new)))


TEMPLATE_IDS = ("minimo", "escritorio", "programador", "gamer", "privacidade")


def load_template(template_id: str) -> ShareableRecipe:
    """Modelo pronto do pacote (``winkit/data/templates``)."""
    if template_id not in TEMPLATE_IDS:
        raise ShareError(f"modelo desconhecido: {template_id}")
    # pelo pacote ``winkit.data`` (já importado), para valer também no executável (IN-013)
    text = resources.files("winkit.data").joinpath("templates", template_id + EXTENSION)
    return loads(text.read_text(encoding="utf-8"))
