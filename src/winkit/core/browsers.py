"""Navegadores prontos (V2-12): receita → operações tipadas de registro (R-34). Função pura.

- Chromium (Chrome, Edge, Brave): no modo **sugerir** (padrão, D-038) as extensões entram como
  "externas" (o navegador pergunta e o usuário pode remover) e página inicial e buscador vão em
  ``Recommended``; no modo **forçar**, ``ExtensionInstallForcelist`` e políticas obrigatórias.
- Firefox: ``ExtensionSettings`` (JSON), ``Homepage`` e ``SearchEngines`` (``Locked`` só ao forçar).
Senhas, cookies e login nunca são tocados.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from winkit.core.catalog.models import CHROMIUM_ID, FIREFOX_ID, BrowserEntry, Catalogs
from winkit.core.recipe.models import BrowserConfig

CHROME_STORE = "https://clients2.google.com/service/update2/crx"
AMO_LATEST = "https://addons.mozilla.org/firefox/downloads/latest/{slug}/latest.xpi"
RESTORE_URLS = 4  # RestoreOnStartup: abrir uma lista de páginas


@dataclass(frozen=True)
class RegWrite:
    key: str  # sempre HKLM
    value: str
    type: str  # "sz" | "dword"
    data: int | str


@dataclass(frozen=True)
class RegUndo:
    key: str
    value: str | None  # None = apagar a chave inteira (só as que o WinKit cria)


def _search(cfg: BrowserConfig, catalogs: Catalogs) -> tuple[str, str] | None:
    provider = catalogs.search_provider(cfg.search) if cfg.search else None
    return (provider.name, provider.search_url) if provider else None


def _chromium(entry: BrowserEntry, cfg: BrowserConfig, catalogs: Catalogs) -> list[RegWrite]:
    ops: list[RegWrite] = []
    exts = [e for e in cfg.extensions if e.selected and re.fullmatch(CHROMIUM_ID, e.id)]
    if cfg.mode == "suggest" and entry.extensions_key:
        ops += [
            RegWrite(f"{entry.extensions_key}\\{e.id}", "update_url", "sz", CHROME_STORE)
            for e in exts
        ]
        base = f"{entry.policy_key}\\Recommended"
    else:
        ops += [
            RegWrite(
                f"{entry.policy_key}\\ExtensionInstallForcelist",
                str(i),
                "sz",
                f"{e.id};{CHROME_STORE}",
            )
            for i, e in enumerate(exts, 1)
        ]
        base = entry.policy_key
    if cfg.homepage:
        ops += [
            RegWrite(base, "HomepageLocation", "sz", cfg.homepage),
            RegWrite(base, "HomepageIsNewTabPage", "dword", 0),
            RegWrite(base, "RestoreOnStartup", "dword", RESTORE_URLS),
            RegWrite(f"{base}\\RestoreOnStartupURLs", "1", "sz", cfg.homepage),
        ]
    search = _search(cfg, catalogs)
    if search:
        ops += [
            RegWrite(base, "DefaultSearchProviderEnabled", "dword", 1),
            RegWrite(base, "DefaultSearchProviderName", "sz", search[0]),
            RegWrite(base, "DefaultSearchProviderSearchURL", "sz", search[1]),
        ]
    return ops


def _firefox(entry: BrowserEntry, cfg: BrowserConfig, catalogs: Catalogs) -> list[RegWrite]:
    ops: list[RegWrite] = []
    key = entry.policy_key
    exts = [e for e in cfg.extensions if e.selected and re.fullmatch(FIREFOX_ID, e.id)]
    if exts:
        mode = "normal_installed" if cfg.mode == "suggest" else "force_installed"
        settings = {
            e.id: {"installation_mode": mode, "install_url": AMO_LATEST.format(slug=e.slug or e.id)}
            for e in exts
        }
        ops.append(RegWrite(key, "ExtensionSettings", "sz", json.dumps(settings, sort_keys=True)))
    locked = 1 if cfg.mode == "force" else 0
    if cfg.homepage:
        ops += [
            RegWrite(f"{key}\\Homepage", "URL", "sz", cfg.homepage),
            RegWrite(f"{key}\\Homepage", "StartPage", "sz", "homepage"),
            RegWrite(f"{key}\\Homepage", "Locked", "dword", locked),
        ]
    search = _search(cfg, catalogs)
    if search:
        add = f"{key}\\SearchEngines\\Add\\1"
        ops += [
            RegWrite(add, "Name", "sz", search[0]),
            RegWrite(add, "URLTemplate", "sz", search[1]),
            RegWrite(add, "Method", "sz", "GET"),
            RegWrite(f"{key}\\SearchEngines", "Default", "sz", search[0]),
        ]
    return ops


def operations(cfg: BrowserConfig, catalogs: Catalogs) -> list[RegWrite]:
    entry = catalogs.browser(cfg.id)
    if entry is None:
        return []
    if entry.engine == "firefox":
        return _firefox(entry, cfg, catalogs)
    return _chromium(entry, cfg, catalogs)


def undo_operations(cfg: BrowserConfig, catalogs: Catalogs) -> list[RegUndo]:
    """Desfazer: só o que ``operations`` gravaria (com qualquer modo), nunca outras políticas."""
    out: list[RegUndo] = []
    seen: set[tuple[str, str | None]] = set()
    for mode in ("suggest", "force"):
        for op in operations(cfg.model_copy(update={"mode": mode}), catalogs):
            entry = catalogs.browser(cfg.id)
            ext_key = entry.extensions_key if entry else None
            undo = (
                RegUndo(op.key, None)
                if ext_key and op.key.startswith(ext_key + "\\")
                else RegUndo(op.key, op.value)
            )
            if (undo.key, undo.value) not in seen:
                seen.add((undo.key, undo.value))
                out.append(undo)
    return out


def suggested(entry: BrowserEntry, catalogs: Catalogs) -> list[tuple[str, str, str | None]]:
    """(id na loja, nome, slug) das extensões do catálogo que existem para este navegador."""
    out = []
    for ext in catalogs.extensions:
        if entry.engine == "firefox" and ext.firefox_id:
            out.append((ext.firefox_id, ext.name, ext.firefox_slug))
        elif entry.engine == "chromium" and ext.chromium_id:
            out.append((ext.chromium_id, ext.name, None))
    return out
