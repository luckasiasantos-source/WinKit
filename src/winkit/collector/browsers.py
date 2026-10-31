"""Navegadores e extensões instaladas neste PC (V2-12).

Só **ids e nomes** de extensões. Página inicial e buscador não são lidos (ficam em arquivos
protegidos ou sincronizados pela conta); senhas, cookies e login nunca são abertos.
"""

from __future__ import annotations

import configparser
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from winkit.collector.backups import local_source
from winkit.core.browsers import suggested
from winkit.core.catalog.models import BrowserEntry, Catalogs
from winkit.core.recipe.models import BrowserConfig, BrowserExtension, Recipe

VolumeRoot = Callable[[str], Path]
#: Chromium ``location``: 5 = componente, 10 = componente externo (do próprio navegador).
_SKIP_LOCATIONS = {5, 10}


def _data_dir(
    entry: BrowserEntry, folders: Mapping[str, str], volume_root: VolumeRoot
) -> Path | None:
    var, _, rest = entry.user_data.partition("\\")
    base = folders.get(var)
    if not base:
        return None
    full = f"{base}\\{rest}"
    return local_source(volume_root(full[:2].upper()), full)


def _json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_msg(ext_dir: Path, name: str) -> str | None:
    """``__MSG_appName__`` → texto do ``_locales`` (padrão da extensão, depois inglês)."""
    key = name.removeprefix("__MSG_").removesuffix("__")
    for version in sorted(ext_dir.glob("*"), reverse=True):
        manifest = _json(version / "manifest.json")
        for locale in (manifest.get("default_locale"), "en", "en_US"):
            if not locale:
                continue
            msgs = _json(version / "_locales" / str(locale) / "messages.json")
            for k, v in msgs.items():
                if k.lower() == key.lower() and isinstance(v, dict) and v.get("message"):
                    return str(v["message"])
    return None


def chromium_extensions(user_data: Path) -> list[BrowserExtension]:
    found: dict[str, BrowserExtension] = {}
    profiles = [p for p in user_data.glob("*") if (p / "Preferences").is_file()]
    for profile in profiles:
        settings: dict[str, Any] = {}
        for name in ("Preferences", "Secure Preferences"):
            settings.update(_json(profile / name).get("extensions", {}).get("settings", {}))
        for ext_id, info in settings.items():
            if not isinstance(info, dict) or info.get("location") in _SKIP_LOCATIONS:
                continue
            if info.get("was_installed_by_default") or ext_id in found:
                continue
            name = str((info.get("manifest") or {}).get("name") or "")
            if name.startswith("__MSG_"):
                name = _resolve_msg(profile / "Extensions" / ext_id, name) or ""
            found[ext_id] = BrowserExtension(id=ext_id, name=name or ext_id)
    return sorted(found.values(), key=lambda e: e.name.casefold())


def firefox_extensions(data_dir: Path) -> list[BrowserExtension]:
    ini = configparser.ConfigParser()
    try:
        ini.read(data_dir / "profiles.ini", encoding="utf-8")
    except configparser.Error:
        return []
    profile = None
    for section in ini.sections():  # [Install…] Default= aponta o perfil em uso
        if section.startswith("Install") and ini.has_option(section, "Default"):
            profile = data_dir / ini.get(section, "Default")
            break
    if profile is None:
        for section in ini.sections():
            if ini.get(section, "Default", fallback="0") == "1" and ini.has_option(section, "Path"):
                path = ini.get(section, "Path")
                relative = ini.get(section, "IsRelative", fallback="1") == "1"
                profile = data_dir / path if relative else Path(path)
                break
    if profile is None:
        return []
    addons = _json(profile / "extensions.json").get("addons", [])
    out = []
    for a in addons:
        if not isinstance(a, dict) or a.get("type") != "extension":
            continue
        if a.get("location") != "app-profile":
            continue
        name = str((a.get("defaultLocale") or {}).get("name") or a.get("id"))
        out.append(BrowserExtension(id=str(a["id"]), name=name))
    return sorted(out, key=lambda e: e.name.casefold())


def collect_browsers(
    recipe: Recipe, catalogs: Catalogs, folders: Mapping[str, str], volume_root: VolumeRoot
) -> list[BrowserConfig]:
    """Navegadores achados neste PC, com as extensões instaladas (soma às que já estão)."""
    found: list[BrowserConfig] = []
    for entry in catalogs.browsers:
        data_dir = _data_dir(entry, folders, volume_root)
        if data_dir is None or not data_dir.is_dir():
            continue
        exts = (
            firefox_extensions(data_dir)
            if entry.engine == "firefox"
            else chromium_extensions(data_dir)
        )
        slugs = {i: s for i, _, s in suggested(entry, catalogs)}
        exts = [e.model_copy(update={"slug": slugs.get(e.id)}) for e in exts]
        cfg = next((b for b in recipe.browsers if b.id == entry.id), None)
        if cfg is None:
            cfg = BrowserConfig(id=entry.id, extensions=exts)
            recipe.browsers = [*recipe.browsers, cfg]
        else:
            known = {e.id for e in cfg.extensions}
            cfg.extensions = [*cfg.extensions, *[e for e in exts if e.id not in known]]
        found.append(cfg)
    return found


def add_suggested(cfg: BrowserConfig, catalogs: Catalogs, ext_ids: list[str]) -> list[str]:
    """Acrescenta extensões do catálogo (ids de ``extensions.yaml``); devolve as desconhecidas."""
    entry = catalogs.browser(cfg.id)
    if entry is None:
        return ext_ids
    missing = []
    known = {e.id for e in cfg.extensions}
    for ext_id in ext_ids:
        ext = catalogs.extension(ext_id)
        store_id = (
            (ext.firefox_id if entry.engine == "firefox" else ext.chromium_id) if ext else None
        )
        if ext is None or store_id is None:
            missing.append(ext_id)
            continue
        if store_id not in known:
            slug = ext.firefox_slug if entry.engine == "firefox" else None
            cfg.extensions = [
                *cfg.extensions,
                BrowserExtension(id=store_id, name=ext.name, slug=slug),
            ]
            known.add(store_id)
    return missing
