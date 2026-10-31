"""Variáveis de ambiente do PC atual (V2-22): só o que **não** é padrão do Windows."""

from __future__ import annotations

from collections.abc import Mapping

from winkit.core.catalog.models import ProtectedEnv
from winkit.core.env import (
    MACHINE_ENV_KEY,
    USER_ENV_KEY,
    is_default_path_entry,
    split_path,
    to_env_template,
)
from winkit.core.recipe.models import EnvPathEntry, EnvScope, EnvVar, Recipe
from winkit.platform.registry import Registry

_KEYS: dict[EnvScope, tuple[str, str]] = {
    "user": ("HKCU", USER_ENV_KEY),
    "machine": ("HKLM", MACHINE_ENV_KEY),
}


def collect_env(
    registry: Registry,
    recipe: Recipe,
    protected: ProtectedEnv,
    folders: Mapping[str, str],
    windows_dir: str | None,
) -> tuple[list[EnvVar], list[EnvPathEntry]]:
    """Acrescenta à receita o que falta. Os itens novos vêm **desmarcados**: o usuário escolhe."""
    env = recipe.environment
    known_vars = {(v.scope, v.name.casefold()) for v in env.variables}
    known_paths = {(p.scope, p.value.casefold()) for p in env.path_entries}
    new_vars: list[EnvVar] = []
    new_paths: list[EnvPathEntry] = []
    for scope, (hive, key) in _KEYS.items():
        for name, raw in sorted(registry.values(hive, key).items()):
            if not isinstance(raw, str):
                continue
            value, templated = to_env_template(raw, folders, windows_dir=windows_dir)
            if name.casefold() == "path":
                for entry in split_path(value):
                    if is_default_path_entry(entry, protected.default_path_entries):
                        continue
                    if (scope, entry.casefold()) not in known_paths:
                        known_paths.add((scope, entry.casefold()))
                        new_paths.append(EnvPathEntry(value=entry, scope=scope, selected=False))
                continue
            if protected.is_protected(name) or (scope, name.casefold()) in known_vars:
                continue
            kind = "expand_sz" if templated or "%" in raw else "sz"
            new_vars.append(EnvVar(name=name, value=value, scope=scope, kind=kind, selected=False))
    env.variables = [*env.variables, *new_vars]
    env.path_entries = [*env.path_entries, *new_paths]
    return new_vars, new_paths


def set_variable(recipe: Recipe, var: EnvVar) -> None:
    env = recipe.environment
    env.variables = [
        v
        for v in env.variables
        if not (v.scope == var.scope and v.name.casefold() == var.name.casefold())
    ]
    env.variables.append(var)


def add_path(recipe: Recipe, value: str, scope: EnvScope) -> EnvPathEntry:
    env = recipe.environment
    env.path_entries = [
        p
        for p in env.path_entries
        if not (p.scope == scope and p.value.casefold() == value.casefold())
    ]
    entry = EnvPathEntry(value=value, scope=scope)
    env.path_entries.append(entry)
    return entry


def select(recipe: Recipe, names: list[str], *, selected: bool) -> list[str]:
    """Marca variáveis (por nome) ou pastas do PATH (pelo valor); devolve o que não achou."""
    wanted = {n.casefold() for n in names}
    found: set[str] = set()
    for v in recipe.environment.variables:
        if v.name.casefold() in wanted:
            v.selected = selected
            found.add(v.name.casefold())
    for p in recipe.environment.path_entries:
        if p.value.casefold() in wanted:
            p.selected = selected
            found.add(p.value.casefold())
    return [n for n in names if n.casefold() not in found]
