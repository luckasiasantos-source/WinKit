"""Regras de validação da receita (PLANO.md §6.2).

``validate_recipe`` não lança exceção: devolve um relatório com erros (impedem construir)
e avisos (o usuário decide). ``ensure_valid`` lança ``RecipeValidationError`` se houver erro.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from winkit.core.catalog.models import Catalogs
from winkit.core.dns import problems as dns_problems
from winkit.core.errors import PathTemplateError, RecipeValidationError
from winkit.core.paths import templates
from winkit.core.recipe.models import AppItem, Recipe
from winkit.i18n import render, t

RESERVED_USERNAMES = frozenset(
    name.casefold()
    for name in (
        "Administrator",
        "Administrador",
        "Guest",
        "Convidado",
        "DefaultAccount",
        "WDAGUtilityAccount",
        "SYSTEM",
        "LocalService",
        "NetworkService",
        "Default",
        "Public",
        "Todos",
        "Everyone",
        "Users",
        "Usuários",
        "Administrators",
        "Administradores",
        "defaultuser0",
        "None",
        "Nenhum",
    )
)
_USERNAME_FORBIDDEN = set('\\/[]:;|=,+*?<>"@')
_COMPUTER_NAME_RE = re.compile(r"^[A-Za-z0-9-]{1,15}$")
_ALLOWED_PAYLOAD_ROOTS = ("Apps/", "Drivers/", "Perfis/")


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_computer_name(name: str) -> bool:
    return bool(_COMPUTER_NAME_RE.match(name)) and not name.isdigit()


def username_problem(name: str) -> str | None:
    if not name.strip() or name != name.strip() or name.endswith("."):
        return t("recipe.username_chars")
    if name.casefold() in RESERVED_USERNAMES:
        return t("recipe.username_reserved")
    if any(ch in _USERNAME_FORBIDDEN for ch in name):
        return t("recipe.username_chars")
    return None


def payload_path_problem(path: str, profile_id: str) -> str | None:
    """Caminhos dentro do pendrive: relativos, com '/', sem '..', em pastas permitidas."""
    if "\\" in path or path.startswith("/") or ":" in path:
        return t("recipe.path_relative", path=repr(path))
    if any(part in ("..", ".") or not part for part in path.split("/")):
        return t("recipe.path_invalid", path=repr(path))
    if path.startswith("Perfis/") and not path.startswith(f"Perfis/{profile_id}/"):
        return t("recipe.path_other_profile", path=repr(path))
    if not path.startswith(_ALLOWED_PAYLOAD_ROOTS):
        return t("recipe.path_outside", path=repr(path))
    return None


def _duplicates(ids: Iterable[str]) -> list[str]:
    return sorted(i for i, n in Counter(ids).items() if n > 1)


def find_cycle(edges: dict[str, list[str]]) -> list[str] | None:
    """Devolve os nós de um ciclo no grafo de dependências, se houver."""
    white, gray, black = 0, 1, 2
    color = dict.fromkeys(edges, white)
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        color[node] = gray
        stack.append(node)
        for dep in edges.get(node, []):
            if dep not in color:
                continue
            if color[dep] == gray:
                return stack[stack.index(dep) :]
            if color[dep] == white:
                found = visit(dep)
                if found:
                    return found
        stack.pop()
        color[node] = black
        return None

    for node in sorted(edges):
        if color[node] == white:
            found = visit(node)
            if found:
                return found
    return None


def validate_recipe(recipe: Recipe, catalogs: Catalogs | None = None) -> ValidationReport:
    report = ValidationReport()
    err, warn = report.errors.append, report.warnings.append
    _validate_windows(recipe, catalogs, err, warn)
    _validate_ids_and_paths(recipe, err)
    backup_ids = {b.id for b in recipe.backups}
    app_ids = {a.id for a in recipe.apps}
    for b in recipe.backups:
        try:
            templates.parse(b.template)
        except PathTemplateError as exc:
            err(f"backup {b.id}: {exc}")
        if b.related_app and b.related_app not in app_ids:
            warn(t("recipe.related_app_missing", id=b.id, app=b.related_app))
    for a in recipe.apps:
        _validate_app(a, backup_ids, app_ids, err, warn)
    cycle = find_cycle({a.id: list(a.depends_on) for a in recipe.apps})
    if cycle:
        err(t("recipe.dependency_cycle", ids=" → ".join([*cycle, cycle[0]])))
    if catalogs is not None:
        _validate_catalog_refs(recipe, catalogs, err)
    _validate_silent(recipe, warn)
    return report


Sink = Callable[[str], None]


def _validate_windows(recipe: Recipe, catalogs: Catalogs | None, err: Sink, warn: Sink) -> None:
    win = recipe.windows
    if win.computer_name is not None and not validate_computer_name(win.computer_name):
        err(t("recipe.computer_name_invalid", name=win.computer_name))
    problem = username_problem(win.account.username)
    if problem:
        err(t("recipe.username_invalid", name=win.account.username, reason=problem))
    if win.account.password_mode == "stored":  # noqa: S105 — modo, não senha
        if not win.account.password:
            err(t("recipe.password_missing"))
        warn(t("recipe.password_stored_warning"))
    if catalogs is not None and catalogs.edition(win.edition) is None:
        err(t("recipe.unknown_edition", edition=win.edition))


def _validate_ids_and_paths(recipe: Recipe, err: Sink) -> None:
    profile = recipe.meta.profile_id
    for section, ids in (
        ("drivers", [d.id for d in recipe.drivers]),
        ("apps", [a.id for a in recipe.apps]),
        ("backups", [b.id for b in recipe.backups]),
        ("tweaks", [x.id for x in recipe.tweaks]),
    ):
        for dup in _duplicates(ids):
            err(t("recipe.duplicate_id", id=dup, section=section))
    checks: list[tuple[str, str]] = [(f"driver {d.id}", d.path) for d in recipe.drivers]
    checks += [(f"backup {b.id}", b.data_path) for b in recipe.backups]
    checks += [
        (f"app {a.id}", a.installer.path)
        for a in recipe.apps
        if a.installer is not None and a.installer.path
    ]
    for label, path in checks:
        if (problem := payload_path_problem(path, profile)) is not None:
            err(f"{label}: {problem}")


def _validate_catalog_refs(recipe: Recipe, catalogs: Catalogs, err: Sink) -> None:
    for problem in dns_problems(recipe.dns, catalogs):
        err(render(problem))
    seen_vars: set[tuple[str, str]] = set()
    for var in recipe.environment.variables:
        key = (var.scope, var.name.casefold())
        if catalogs.protected_env.is_protected(var.name):
            err(t("recipe.env_protected", name=var.name))
        elif key in seen_vars:
            err(t("recipe.env_duplicate", name=var.name))
        seen_vars.add(key)
    for feature_id in recipe.windows.optional_features:
        if catalogs.feature(feature_id) is None:
            err(t("recipe.unknown_feature", id=feature_id))
    for sel in recipe.tweaks:
        if catalogs.tweak(sel.id) is None:
            err(t("recipe.unknown_tweak", id=sel.id))
    for pkg in recipe.bloatware.remove:
        entry = catalogs.bloat(pkg)
        if entry is None:
            err(t("recipe.unknown_bloat", id=pkg))
        elif entry.risk == "blocked":
            err(t("recipe.blocked_bloat", id=pkg, reason=entry.reason))


def _validate_silent(recipe: Recipe, warn: Sink) -> None:
    if recipe.execution.mode != "silent":
        return
    asking = [a.id for a in recipe.apps if a.decide_at_runtime]
    asking += [b.id for b in recipe.backups if b.decide_at_runtime]
    asking += [x.id for x in recipe.tweaks if x.decide_at_runtime]
    if recipe.windows.computer_name_decide_at_runtime:
        asking.append("computer_name")
    if asking:
        warn(t("recipe.silent_asks", ids=", ".join(asking)))


def _validate_app(
    a: AppItem,
    backup_ids: set[str],
    app_ids: set[str],
    err: Sink,
    warn: Sink,
) -> None:
    for dep in a.depends_on:
        if dep not in app_ids:
            err(t("recipe.unknown_dependency", id=a.id, dep=dep))
    for ref in a.restore_backups_after_install:
        if ref not in backup_ids:
            err(t("recipe.unknown_backup_ref", app=a.id, backup=ref))
    if not a.selected:
        return  # apps desmarcados ficam na receita só como inventário (IN-006)
    if a.source == "offline":
        if a.installer is None or not a.installer.path:
            err(t("recipe.missing_installer", id=a.id))
        elif a.installer.type == "unknown" and not a.installer.args:
            err(t("recipe.unknown_installer_type", id=a.id))
    elif a.source == "winget_online":
        if not a.winget_id:
            err(t("recipe.missing_winget_id", id=a.id))
    elif a.source == "portable" and (not a.portable_backup or a.portable_backup not in backup_ids):
        err(t("recipe.portable_needs_backup", id=a.id))
    if a.winget_source == "msstore" and a.source == "offline":
        warn(t("recipe.store_offline", id=a.id))


def ensure_valid(recipe: Recipe, catalogs: Catalogs | None = None) -> ValidationReport:
    report = validate_recipe(recipe, catalogs)
    if report.errors:
        raise RecipeValidationError(report.errors)
    return report
