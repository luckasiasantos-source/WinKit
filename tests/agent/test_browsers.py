"""Navegadores prontos (V2-12): catálogos, geração das políticas, leitura das extensões, etapa."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.phases import run_phase1
from winkit.cli import main as cli
from winkit.collector.browsers import collect_browsers
from winkit.core.browsers import CHROME_STORE, operations, undo_operations
from winkit.core.catalog.loader import default_catalogs
from winkit.core.catalog.models import CHROMIUM_ID, FIREFOX_ID
from winkit.core.recipe.models import BrowserConfig, BrowserExtension
from winkit.platform import browsers as policies
from winkit.platform.fakes.backup import FakeOldPcFolders
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.services import fake_services

UBO_LITE = "ddkjiahejlhfcafbddmgiahcphecmpfh"
BITWARDEN = "nngceckbapebfimnlniiiahkandclblb"


def test_catalogs_have_valid_ids_and_https() -> None:
    c = default_catalogs()
    assert {b.id for b in c.browsers} == {"chrome", "edge", "brave", "firefox"}
    for e in c.extensions:
        assert e.chromium_id is None or re.fullmatch(CHROMIUM_ID, e.chromium_id)
        assert e.firefox_id is None or re.fullmatch(FIREFOX_ID, e.firefox_id)
    assert all(s.search_url.startswith("https://") for s in c.search_providers)


def cfg(browser: str, mode: str = "suggest", **kw: object) -> BrowserConfig:
    exts = [BrowserExtension(id=UBO_LITE, name="uBO Lite"), BrowserExtension(id=BITWARDEN)]
    if browser == "firefox":
        exts = [BrowserExtension(id="uBOLite@raymondhill.net", slug="ublock-origin-lite")]
    return BrowserConfig(
        id=browser,
        extensions=exts,
        homepage="https://example.org",
        search="duckduckgo",
        mode=mode,  # type: ignore[arg-type]
        **kw,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(
    ("browser", "mode", "expected"),
    [
        (
            "chrome",
            "suggest",
            {
                (r"SOFTWARE\WOW6432Node\Google\Chrome\Extensions" + "\\" + UBO_LITE, "update_url"),
                (r"SOFTWARE\Policies\Google\Chrome\Recommended", "HomepageLocation"),
                (r"SOFTWARE\Policies\Google\Chrome\Recommended", "DefaultSearchProviderSearchURL"),
            },
        ),
        (
            "edge",
            "force",
            {
                (r"SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist", "1"),
                (r"SOFTWARE\Policies\Microsoft\Edge", "HomepageLocation"),
            },
        ),
        (
            "firefox",
            "suggest",
            {
                (r"SOFTWARE\Policies\Mozilla\Firefox", "ExtensionSettings"),
                (r"SOFTWARE\Policies\Mozilla\Firefox\Homepage", "URL"),
                (r"SOFTWARE\Policies\Mozilla\Firefox\SearchEngines", "Default"),
            },
        ),
    ],
)
def test_operations_per_browser_and_mode(
    browser: str, mode: str, expected: set[tuple[str, str]]
) -> None:
    ops = operations(cfg(browser, mode), default_catalogs())
    keys = {(o.key, o.value) for o in ops}
    assert expected <= keys
    if browser != "firefox" and mode == "suggest":
        assert not any("ExtensionInstallForcelist" in o.key for o in ops)  # D-038
        assert all(o.data == CHROME_STORE for o in ops if o.value == "update_url")
    if browser == "edge":
        forced = [o for o in ops if "Forcelist" in o.key]
        assert forced[0].data == f"{UBO_LITE};{CHROME_STORE}"


def test_firefox_extension_settings_json() -> None:
    (settings,) = [
        o for o in operations(cfg("firefox"), default_catalogs()) if o.value == "ExtensionSettings"
    ]
    data = json.loads(str(settings.data))
    assert data["uBOLite@raymondhill.net"] == {
        "installation_mode": "normal_installed",
        "install_url": "https://addons.mozilla.org/firefox/downloads/latest/ublock-origin-lite/latest.xpi",
    }
    forced = operations(cfg("firefox", "force"), default_catalogs())
    locked = next(o for o in forced if o.value == "Locked")
    assert locked.data == 1


def test_unselected_extension_is_left_out() -> None:
    c = cfg("chrome")
    c.extensions[1].selected = False
    ops = operations(c, default_catalogs())
    assert not any(BITWARDEN in o.key for o in ops)


# ------------------------------------------------------------------ leitura do PC antigo
def old_pc(tmp_path: Path) -> FakeOldPcFolders:
    folders = FakeOldPcFolders(tmp_path / "C")
    user = tmp_path / "C" / "Users" / "Samuel" / "AppData"
    chrome = user / "Local" / "Google" / "Chrome" / "User Data" / "Default"
    chrome.mkdir(parents=True)
    prefs = {
        "extensions": {
            "settings": {
                UBO_LITE: {"location": 1, "manifest": {"name": "uBlock Origin Lite"}},
                "mhjfbmdgcfjbbpaeojofohoefgiehjai": {"location": 5, "manifest": {"name": "PDF"}},
                BITWARDEN: {"location": 1, "manifest": {"name": "__MSG_extName__"}},
            }
        }
    }
    (chrome / "Preferences").write_text(json.dumps(prefs), encoding="utf-8")
    loc = chrome / "Extensions" / BITWARDEN / "2025.1.0" / "_locales" / "en"
    loc.mkdir(parents=True)
    (loc.parent.parent / "manifest.json").write_text('{"default_locale": "en"}', encoding="utf-8")
    (loc / "messages.json").write_text('{"extName": {"message": "Bitwarden"}}', encoding="utf-8")
    ff = user / "Roaming" / "Mozilla" / "Firefox"
    profile = ff / "Profiles" / "abcd.default-release"
    profile.mkdir(parents=True)
    (ff / "profiles.ini").write_text(
        "[Install308046B0AF4A39CB]\nDefault=Profiles/abcd.default-release\n", encoding="utf-8"
    )
    addons = {
        "addons": [
            {
                "id": "addon@darkreader.org",
                "type": "extension",
                "location": "app-profile",
                "defaultLocale": {"name": "Dark Reader"},
            },
            {"id": "formautofill@mozilla.org", "type": "extension", "location": "app-builtin"},
            {
                "id": "pt-BR@dictionaries.addons.mozilla.org",
                "type": "dictionary",
                "location": "app-profile",
            },
        ]
    }
    (profile / "extensions.json").write_text(json.dumps(addons), encoding="utf-8")
    return folders


def test_collect_reads_only_user_extensions(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    folders = old_pc(tmp_path)
    r = w.recipe()
    found = collect_browsers(
        r, default_catalogs(), {**folders.machine(), **folders.current_user()}, folders.volume_root
    )
    by_id = {b.id: b for b in found}
    assert set(by_id) == {"chrome", "firefox"}
    assert [(e.id, e.name) for e in by_id["chrome"].extensions] == [
        (BITWARDEN, "Bitwarden"),
        (UBO_LITE, "uBlock Origin Lite"),
    ]
    (dark,) = by_id["firefox"].extensions
    assert (dark.id, dark.name, dark.slug) == ("addon@darkreader.org", "Dark Reader", "darkreader")
    again = collect_browsers(
        r, default_catalogs(), {**folders.machine(), **folders.current_user()}, folders.volume_root
    )
    assert len(again[0].extensions) == 2  # não duplica


# ------------------------------------------------------------------ etapa e desfazer
def _world(tmp_path: Path) -> World:
    w = make_world(tmp_path)
    r = w.recipe()
    r.browsers = [cfg("chrome"), cfg("firefox")]
    w.save_recipe(r)
    return w


def test_phase1_writes_policies_and_live_is_then_done(tmp_path: Path) -> None:
    w = _world(tmp_path)
    run_phase1(w.runtime())
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    assert (
        reg.get("HKLM", r"SOFTWARE\Policies\Google\Chrome\Recommended", "HomepageLocation")
        == "https://example.org"
    )
    assert (
        reg.get("HKLM", r"SOFTWARE\Policies\Mozilla\Firefox\SearchEngines", "Default")
        == "DuckDuckGo"
    )
    opts = {"root": w.pendrive, "restore_point": False, "only_kinds": frozenset({"browser"})}
    again = run_live(w.runtime(), LiveOptions(simulate=True, **opts))  # type: ignore[arg-type]
    assert again.preview is not None
    assert {i.status for i in again.preview.items} == {"already_done"}


def test_undo_removes_only_winkit_values(tmp_path: Path) -> None:
    reg = FakeRegistry()
    reg.set("HKLM", r"SOFTWARE\Policies\Google\Chrome", "OutraPolitica", "dword", 1)
    c = cfg("chrome")
    policies.apply(reg, operations(c, default_catalogs()))
    assert policies.undo(reg, undo_operations(c, default_catalogs())) > 0
    assert not policies.applied(reg, operations(c, default_catalogs()))
    assert reg.get("HKLM", r"SOFTWARE\Policies\Google\Chrome", "OutraPolitica") == 1


def test_cli_browsers(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    folders = old_pc(tmp_path)
    services = fake_services(old_pc=folders.base)
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=services, out=out.append)

    assert run("coletar", "navegadores") == 0
    assert (
        run(
            "navegador",
            "definir",
            "chrome",
            "--extensoes",
            "dark_reader",
            "--busca",
            "startpage",
            "--pagina",
            "https://a.org",
            "--forcar",
        )
        == 0
    )
    chrome = next(b for b in w.recipe().browsers if b.id == "chrome")
    assert (
        chrome.mode == "force"
        and chrome.search == "startpage"
        and chrome.homepage == "https://a.org"
    )
    assert any(e.name == "Dark Reader" for e in chrome.extensions)
    assert run("browser", "set", "chrome", "--pagina", "ftp://x") == 1
    assert run("navegador", "definir", "chrome", "--busca", "nada") == 1
    assert run("navegador", "definir", "opera") == 1
