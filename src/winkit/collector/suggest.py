"""Assistente "o que levar" (V2-20): analisa este PC e sugere, explicando o porquê.

Tudo é local; nada sai do PC. Nada é adicionado sozinho: cada sugestão tem "Adicionar" e
"Ignorar", e as ignoradas não voltam (``meta.dismissed_suggestions``).
"""

from __future__ import annotations

import ntpath
import os
import time
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path

from winkit.collector import backups as backup_collector
from winkit.collector.backups import local_source
from winkit.core.catalog.models import Catalogs
from winkit.core.compare import normalize_name
from winkit.core.errors import PathTemplateError, WinKitError
from winkit.core.paths import templates
from winkit.core.recipe.models import AppItem, Recipe
from winkit.core.suggest import Suggestion, rank, size_score, usage_score
from winkit.core.text import slugify
from winkit.core.userassist import UsageEntry
from winkit.i18n.format import format_size
from winkit.i18n.msg import msg
from winkit.platform.copy import tree_stats
from winkit.platform.inventory import AppInventory
from winkit.platform.registry import Registry
from winkit.platform.usage import read_usage

VolumeRoot = Callable[[str], Path]
MIN_USES = 3
#: Pastas da raiz do disco do sistema que são do Windows ou de programas.
SYSTEM_ROOT_DIRS = {
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "users",
    "recovery",
    "perflogs",
    "intel",
    "amd",
    "nvidia",
    "drivers",
    "msocache",
    "onedrivetemp",
    "winkit",
}
MIN_FOLDER_BYTES = 100 * 1024**2


def _segments(path: str) -> set[str]:
    parts = [p for p in path.replace("/", "\\").split("\\") if p]
    if parts:
        parts[-1] = ntpath.splitext(parts[-1])[0]
    return {n for n in (normalize_name(p) for p in parts) if n}


def _matches(keys: set[str], segments: set[str]) -> bool:
    """Casa pelo nome do programa ou da pasta dele (``Mozilla Firefox`` ↔ ``firefox.exe``)."""
    return any(
        k == s or (min(len(k), len(s)) >= 4 and (k.startswith(s) or s.startswith(k)))
        for k in keys
        for s in segments
    )


def bounded_size(folder: Path, deadline: float, clock: Callable[[], float]) -> tuple[int, bool]:
    """Tamanho da pasta até o prazo. Devolve (bytes, completo?). Não segue links."""
    total, stack = 0, [folder]
    while stack:
        if clock() > deadline:
            return total, False
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            stack.append(Path(e.path))
                        elif e.is_file(follow_symlinks=False):
                            total += e.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total, True


def _app_suggestions(
    inventory: AppInventory, usage: list[UsageEntry], recipe: Recipe, now: datetime
) -> list[Suggestion]:
    in_recipe = {a.winget_id.casefold() for a in recipe.apps if a.winget_id}
    in_recipe |= {normalize_name(a.name) for a in recipe.apps}
    out: list[Suggestion] = []
    for app in inventory.installed(include_appx=False):
        key = normalize_name(app.name)
        if app.redistributable or not key or key in in_recipe:
            continue
        if app.winget_id and app.winget_id.casefold() in in_recipe:
            continue
        keys = {key}
        if app.install_location:
            keys.add(normalize_name(ntpath.basename(app.install_location.rstrip("\\"))))
        keys.discard("")
        uses = [u for u in usage if _matches(keys, _segments(u.path))]
        count = sum(u.count for u in uses)
        if count < MIN_USES:
            continue
        last = max((u.last_used for u in uses if u.last_used), default=None)
        if last is None:
            reason = msg("suggest.app_used_count", n=count)
        elif (now - last).days < 1:
            reason = msg("suggest.app_used_today", n=count)
        elif (now - last).days == 1:
            reason = msg("suggest.app_used_yesterday", n=count)
        else:
            reason = msg("suggest.app_used", n=count, days=(now - last).days)
        out.append(
            Suggestion(
                id=f"app:{app.winget_id or key}",
                kind="app",
                title=app.name,
                reason=reason,
                score=usage_score(count, last, now),
                payload={"winget_id": app.winget_id or "", "name": app.name, "scope": app.scope},
            )
        )
    return out


def _config_suggestions(
    recipe: Recipe, catalogs: Catalogs, folders: Mapping[str, str], volume_root: VolumeRoot
) -> list[Suggestion]:
    have = {b.template.casefold() for b in recipe.backups}
    out = []
    for s in backup_collector.suggest(recipe, catalogs, folders, volume_root):
        if s.recommended and s.exists and s.template.casefold() not in have:
            out.append(
                Suggestion(
                    id=f"config:{s.app_id}:{slugify(s.template)}",
                    kind="config",
                    title=f"{s.app_name}: {s.template}",
                    reason=msg("suggest.config", app=s.app_name),
                    score=50 + size_score(s.size),
                    payload={"app_id": s.app_id, "template": s.template},
                )
            )
    return out


def _save_suggestions(
    recipe: Recipe, catalogs: Catalogs, folders: Mapping[str, str], volume_root: VolumeRoot
) -> list[Suggestion]:
    have = {b.template.casefold() for b in recipe.backups}
    out = []
    for g in catalogs.game_saves:
        if g.template.casefold() in have:
            continue
        try:
            literal = templates.resolve(g.template, folders)
        except PathTemplateError:
            continue
        src = local_source(volume_root(literal[:2].upper()), literal)
        if not src.is_dir():
            continue
        stats = tree_stats(src, [])
        if stats.files == 0:  # pasta vazia: nada a levar
            continue
        out.append(
            Suggestion(
                id=f"save:{g.id}",
                kind="save",
                title=g.name,
                reason=msg("suggest.save", size=format_size(stats.bytes)),
                score=40 + size_score(stats.bytes),
                payload={"template": g.template, "name": g.name},
            )
        )
    return out


def _folder_suggestions(
    system_root: Path, budget_s: float, clock: Callable[[], float]
) -> list[Suggestion]:
    out: list[Suggestion] = []
    deadline = clock() + budget_s
    try:
        entries = sorted(p for p in system_root.iterdir() if p.is_dir())
    except OSError:
        return out
    for folder in entries:
        name = folder.name
        if name.casefold() in SYSTEM_ROOT_DIRS or name.startswith(("$", ".")):
            continue
        # varredura com limite de tempo: o que passar do prazo entra com o tamanho parcial
        size, complete = bounded_size(folder, deadline, clock)
        if size < MIN_FOLDER_BYTES:
            continue
        key = "suggest.folder" if complete else "suggest.folder_partial"
        out.append(
            Suggestion(
                id=f"folder:{name.casefold()}",
                kind="folder",
                title=f"C:\\{name}",
                reason=msg(key, size=format_size(size)),
                score=size_score(size),
                payload={"literal": f"C:\\{name}", "name": name},
            )
        )
    return out


def analyze(
    recipe: Recipe,
    catalogs: Catalogs,
    *,
    inventory: AppInventory,
    registry: Registry | None,
    folders: Mapping[str, str],
    volume_root: VolumeRoot,
    now: datetime,
    budget_s: float = 20.0,
    clock: Callable[[], float] = time.monotonic,
) -> list[Suggestion]:
    usage = read_usage(registry) if registry is not None else []
    items = [
        *_app_suggestions(inventory, usage, recipe, now),
        *_config_suggestions(recipe, catalogs, folders, volume_root),
        *_save_suggestions(recipe, catalogs, folders, volume_root),
        *_folder_suggestions(volume_root("C:"), budget_s, clock),
    ]
    return rank(items, recipe.meta.dismissed_suggestions)


def dismiss(recipe: Recipe, suggestion_id: str) -> None:
    if suggestion_id not in recipe.meta.dismissed_suggestions:
        recipe.meta.dismissed_suggestions = [*recipe.meta.dismissed_suggestions, suggestion_id]


def accept(recipe: Recipe, catalogs: Catalogs, s: Suggestion, folders: Mapping[str, str]) -> bool:
    """Acrescenta à receita o que a sugestão propõe. False se não há o que fazer."""
    p = s.payload
    if s.kind == "app":
        if not p.get("winget_id"):
            return False
        ids = {a.id for a in recipe.apps}
        base = slugify(p["name"])
        app_id, n = base, 2
        while app_id in ids:
            app_id, n = f"{base}-{n}", n + 1
        scope = "user" if p.get("scope") == "user" else "machine"
        recipe.apps.append(
            AppItem(
                id=app_id,
                name=p["name"],
                source="winget_online",
                winget_id=p["winget_id"],
                scope=scope,
            )
        )
        return True
    try:
        if s.kind == "config":
            item = next(
                x
                for x in backup_collector.suggest(recipe, catalogs, folders)
                if x.app_id == p["app_id"] and x.template == p["template"]
            )
            backup_collector.add_suggestion(recipe, catalogs, item)
        elif s.kind == "save":
            backup_collector.add_backup(recipe, catalogs, name=p["name"], template=p["template"])
        elif s.kind == "folder":
            backup_collector.add_backup(
                recipe, catalogs, name=p["name"], literal=p["literal"], old_folders=folders
            )
        else:
            return False
    except (StopIteration, WinKitError, PathTemplateError):
        return False
    return True
