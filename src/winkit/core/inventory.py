"""Inventário de apps instalados e classificação para a receita (PLANO.md §7.1, item 8).

Puro: recebe valores do registro / JSON já lidos pela plataforma.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from winkit.core.catalog.models import AppCatalogEntry, Catalogs
from winkit.core.recipe.models import AfterInstall, AppItem, InstallerSpec, Recipe, Scope
from winkit.core.text import slugify

_REDIST = re.compile(
    r"(Microsoft Visual C\+\+ \d{4}.*Redistributable|Microsoft \.NET (Runtime|Desktop Runtime|"
    r"Framework|Core)|Windows Desktop Runtime|Microsoft Windows Desktop Runtime|DirectX|"
    r"Microsoft Edge WebView2 Runtime|Microsoft Update Health Tools|Windows SDK|"
    r"vs_|Microsoft ASP\.NET)",
    re.IGNORECASE,
)
_SKIP_RELEASE_TYPES = {"update", "hotfix", "security update", "service pack"}


class InstalledApp(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    version: str = ""
    publisher: str = ""
    scope: Scope
    origin: Literal["registry", "appx"] = "registry"
    install_location: str = ""
    redistributable: bool = False
    winget_id: str | None = None
    winget_source: Literal["winget", "msstore"] = "winget"
    catalog_id: str | None = None

    @property
    def item_id(self) -> str:
        return self.catalog_id or slugify(self.name)


def app_from_uninstall(values: Mapping[str, Any], *, scope: Scope) -> InstalledApp | None:
    """Aplica os filtros do §7.1.2. ``None`` = ruído (atualização, componente de sistema...)."""
    name = str(values.get("DisplayName") or "").strip()
    if not name:
        return None
    if int(values.get("SystemComponent") or 0) == 1:
        return None
    if values.get("ParentKeyName"):
        return None
    if str(values.get("ReleaseType") or "").strip().lower() in _SKIP_RELEASE_TYPES:
        return None
    location = str(values.get("InstallLocation") or "")
    effective_scope: Scope = scope
    if scope == "machine" and "\\appdata\\local\\" in location.lower():
        effective_scope = "user"
    return InstalledApp(
        name=name,
        version=str(values.get("DisplayVersion") or ""),
        publisher=str(values.get("Publisher") or ""),
        scope=effective_scope,
        install_location=location,
        redistributable=bool(_REDIST.search(name)),
    )


def app_from_appx(item: Mapping[str, Any]) -> InstalledApp | None:
    if item.get("IsFramework") or str(item.get("SignatureKind") or "").lower() == "system":
        return None
    if item.get("NonRemovable"):
        return None
    name = str(item.get("Name") or "")
    if not name:
        return None
    return InstalledApp(
        name=name,
        version=str(item.get("Version") or ""),
        publisher=str(item.get("PublisherDisplayName") or ""),
        scope="user",
        origin="appx",
        winget_source="msstore",
    )


def parse_winget_export(text: str) -> list[tuple[str, str]]:
    """``winget export`` → [(PackageIdentifier, nome da fonte)]."""
    data = json.loads(text)
    out: list[tuple[str, str]] = []
    for source in data.get("Sources") or []:
        src_name = str((source.get("SourceDetails") or {}).get("Name") or "winget")
        for pkg in source.get("Packages") or []:
            pid = pkg.get("PackageIdentifier")
            if pid:
                out.append((str(pid), src_name))
    return out


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _catalog_entry(app: InstalledApp, catalogs: Catalogs) -> AppCatalogEntry | None:
    for entry in catalogs.apps:
        rx = entry.match.display_name_regex
        if rx and re.search(rx, app.name):
            return entry
    return None


def _heuristic_id(app: InstalledApp, ids: Iterable[str]) -> str | None:
    """Casa "Discord" com "Discord.Discord", "7-Zip 24.08" com "7zip.7zip" etc."""
    name = _norm(app.name)
    first_word = _norm(app.name.split()[0]) if app.name.split() else ""
    best: str | None = None
    for pid in ids:
        parts = [_norm(p) for p in pid.split(".") if p]
        if not parts:
            continue
        last = parts[-1]
        matches = bool(last) and (name == last or name.startswith(last) or first_word == last)
        if matches and (best is None or len(pid) < len(best)):
            best = pid
    return best


def match_inventory(
    apps: list[InstalledApp],
    export: list[tuple[str, str]],
    catalogs: Catalogs,
) -> list[InstalledApp]:
    """Completa ``winget_id`` e ``catalog_id``. Ordem: catálogo, depois heurística."""
    community = [pid for pid, src in export if src.lower() != "msstore"]
    available = set(community)
    out = []
    for app in apps:
        entry = _catalog_entry(app, catalogs)
        winget_id = None
        if entry is not None:
            winget_id = next((w for w in entry.match.winget_ids if w in available), None)
            winget_id = winget_id or (entry.match.winget_ids[0] if entry.match.winget_ids else None)
        if winget_id is None and app.origin == "registry":
            winget_id = _heuristic_id(app, community)
        out.append(
            app.model_copy(
                update={"winget_id": winget_id, "catalog_id": entry.id if entry else None}
            )
        )
    return out


def to_app_item(app: InstalledApp, catalogs: Catalogs) -> AppItem:
    """Sugestão inicial (desmarcada) para a receita (§7.1.3)."""
    entry = catalogs.app(app.catalog_id) if app.catalog_id else None
    scope: Scope = entry.scope if entry else app.scope
    after = entry.after_install if entry else AfterInstall()
    installer = None
    if entry and entry.installer:
        installer = InstallerSpec(
            type=entry.installer.type,
            args=list(entry.installer.args),
            success_codes=list(entry.installer.success_codes),
            timeout_minutes=entry.installer.timeout_minutes,
        )
    source: Literal["offline", "winget_online", "portable"] = (
        "winget_online" if app.winget_id else "offline"
    )
    return AppItem(
        id=app.item_id,
        name=entry.name if entry else app.name,
        selected=False,
        source=source,
        scope=scope,
        installer=installer,
        winget_id=app.winget_id,
        winget_source=app.winget_source,
        requires_non_elevated=bool(entry and entry.requires_non_elevated),
        after_install=after,
    )


def merge_into_recipe(recipe: Recipe, items: list[AppItem]) -> list[AppItem]:
    """Acrescenta apps novos sem tocar nos já existentes (preserva escolhas). Devolve os novos."""
    existing = {a.id for a in recipe.apps}
    added = []
    for item in items:
        if item.id in existing:
            continue
        recipe.apps.append(item)
        existing.add(item.id)
        added.append(item)
    return added
