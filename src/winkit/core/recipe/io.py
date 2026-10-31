"""Leitura, gravação, criação e migração da receita."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from winkit import __version__
from winkit.core.errors import RecipeError
from winkit.core.recipe.models import SCHEMA_VERSION, Account, Meta, Recipe, WindowsSettings
from winkit.i18n import t

Migration = Callable[[dict[str, Any]], dict[str, Any]]

#: ``MIGRATIONS[n]`` converte um dicionário da versão ``n`` para a ``n + 1``.
MIGRATIONS: dict[int, Migration] = {}


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    version = data.get("schema_version", 1)
    if not isinstance(version, int) or version < 1:
        raise RecipeError(f"schema_version inválido: {version!r}")
    if version > SCHEMA_VERSION:
        raise RecipeError(
            t("recipe.migration_unsupported", found=version, supported=SCHEMA_VERSION)
        )
    while version < SCHEMA_VERSION:
        data = MIGRATIONS[version](dict(data))
        version += 1
        data["schema_version"] = version
    return data


def recipe_from_dict(data: dict[str, Any]) -> Recipe:
    try:
        return Recipe.model_validate(migrate(data))
    except ValidationError as exc:
        problems = [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in exc.errors()]
        raise RecipeError(t("recipe.invalid", problems="\n".join(problems))) from exc


def load_recipe(text: str) -> Recipe:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RecipeError(f"receita não é JSON válido: {exc}") from exc
    if not isinstance(data, dict):
        raise RecipeError("receita deve ser um objeto JSON")
    return recipe_from_dict(data)


def dump_recipe(recipe: Recipe) -> str:
    data = recipe.model_dump(mode="json", by_alias=True)
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def recipe_hash(recipe: Recipe) -> str:
    """Hash estável do conteúdo (ignora datas de atualização)."""
    data = recipe.model_dump(mode="json", by_alias=True)
    data["meta"].pop("updated_at", None)
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def new_recipe(
    *,
    pendrive_id: str,
    username: str,
    profile_id: str = "padrao",
    source_pc: str | None = None,
    now: datetime | None = None,
) -> Recipe:
    stamp = now or datetime.now(UTC)
    return Recipe(
        meta=Meta(
            profile_id=profile_id,
            pendrive_id=pendrive_id,
            created_at=stamp,
            updated_at=stamp,
            winkit_version=__version__,
            source_pc=source_pc,
        ),
        windows=WindowsSettings(account=Account(username=username)),
    )
