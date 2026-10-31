"""Carrega e valida os catálogos YAML empacotados em ``winkit/data`` (D-021)."""

from __future__ import annotations

import functools
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from winkit.core.catalog.localize import CatalogTranslation, localize
from winkit.core.catalog.models import Catalogs
from winkit.core.errors import CatalogError
from winkit.i18n import Language, current_language

FILES: dict[str, str] = {
    "apps": "app_catalog.yaml",
    "tweaks": "tweaks.yaml",
    "bloatware": "bloatware.yaml",
    "editions": "editions.yaml",
    "installer_signatures": "installer_signatures.yaml",
    "dpapi_patterns": "dpapi_patterns.yaml",
    "default_excludes": "default_excludes.yaml",
    "driver_classes": "driver_classes.yaml",
    "features": "features.yaml",
}


def _read_text(name: str, directory: Path | None) -> str:
    if directory is not None:
        return (directory / name).read_text(encoding="utf-8")
    return resources.files("winkit.data").joinpath(name).read_text(encoding="utf-8")


def _parse(name: str, text: str) -> Any:
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise CatalogError(f"{name}: YAML inválido: {exc}") from exc


def load_catalogs(directory: Path | None = None) -> Catalogs:
    """Lê todos os catálogos. ``directory`` permite testar com arquivos alternativos."""
    raw: dict[str, Any] = {}
    for field, name in FILES.items():
        try:
            text = _read_text(name, directory)
        except FileNotFoundError as exc:
            raise CatalogError(f"catálogo ausente: {name}") from exc
        raw[field] = _parse(name, text) or []
    try:
        catalogs = Catalogs.model_validate(raw)
    except ValidationError as exc:
        raise CatalogError(f"catálogo inválido: {exc}") from exc
    _check_unique(catalogs)
    return catalogs


def _check_unique(c: Catalogs) -> None:
    groups: dict[str, list[str]] = {
        "app_catalog.yaml": [a.id for a in c.apps],
        "tweaks.yaml": [x.id for x in c.tweaks],
        "bloatware.yaml": [b.id for b in c.bloatware],
        "editions.yaml": [e.id for e in c.editions],
        "dpapi_patterns.yaml": [d.id for d in c.dpapi_patterns],
        "driver_classes.yaml": [d.name.casefold() for d in c.driver_classes],
        "features.yaml": [f.id for f in c.features],
    }
    for name, ids in groups.items():
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise CatalogError(f"{name}: identificadores repetidos {dupes}")


#: Arquivo de tradução dos catálogos por idioma (pt-BR é a base, D-030).
TRANSLATION_FILES: dict[str, str] = {"en-US": "i18n_en_us.yaml", "es": "i18n_es.yaml"}


def load_translation(lang: str, directory: Path | None = None) -> CatalogTranslation:
    name = TRANSLATION_FILES[lang]
    try:
        data = _parse(name, _read_text(name, directory)) or {}
        return CatalogTranslation.model_validate(data)
    except FileNotFoundError as exc:
        raise CatalogError(f"tradução ausente: {name}") from exc
    except ValidationError as exc:
        raise CatalogError(f"tradução inválida em {name}: {exc}") from exc


@functools.cache
def _base_catalogs() -> Catalogs:
    return load_catalogs()


@functools.cache
def catalogs_for(lang: Language) -> Catalogs:
    base = _base_catalogs()
    if lang not in TRANSLATION_FILES:
        return base
    return localize(base, load_translation(lang))


def default_catalogs() -> Catalogs:
    """Catálogos empacotados no idioma atual, carregados uma vez por idioma."""
    return catalogs_for(current_language())
