from __future__ import annotations

import json

from tests.factories import app as make_app
from tests.factories import recipe
from winkit.core.catalog.loader import default_catalogs
from winkit.core.inventory import (
    InstalledApp,
    app_from_appx,
    app_from_uninstall,
    match_inventory,
    merge_into_recipe,
    parse_winget_export,
    to_app_item,
)
from winkit.platform.fakes.apps import SAMPLE_EXPORT

CAT = default_catalogs()


def test_uninstall_filters() -> None:
    base = {"DisplayName": "App", "DisplayVersion": "1.0", "Publisher": "X"}
    assert app_from_uninstall(base, scope="machine") is not None
    assert app_from_uninstall({**base, "SystemComponent": 1}, scope="machine") is None
    assert app_from_uninstall({**base, "ParentKeyName": "Office"}, scope="machine") is None
    assert app_from_uninstall({**base, "ReleaseType": "Security Update"}, scope="machine") is None
    assert app_from_uninstall({"DisplayName": "  "}, scope="machine") is None


def test_uninstall_scope_and_redist() -> None:
    a = app_from_uninstall(
        {"DisplayName": "X", "InstallLocation": r"C:\Users\S\AppData\Local\X"}, scope="machine"
    )
    assert a is not None and a.scope == "user"
    vc = app_from_uninstall(
        {"DisplayName": "Microsoft Visual C++ 2015-2022 Redistributable (x64) - 14.40"},
        scope="machine",
    )
    assert vc is not None and vc.redistributable
    net = app_from_uninstall(
        {"DisplayName": "Microsoft .NET Runtime - 8.0.10 (x64)"}, scope="machine"
    )
    assert net is not None and net.redistributable


def test_appx_filters() -> None:
    assert app_from_appx({"Name": "Microsoft.VCLibs", "IsFramework": True}) is None
    assert app_from_appx({"Name": "Microsoft.Windows.Shell", "SignatureKind": "System"}) is None
    assert app_from_appx({"Name": "X", "NonRemovable": True}) is None
    a = app_from_appx({"Name": "5319275A.WhatsAppDesktop", "SignatureKind": "Store"})
    assert a is not None and a.origin == "appx" and a.winget_source == "msstore"


def test_parse_winget_export() -> None:
    assert parse_winget_export(json.dumps(SAMPLE_EXPORT)) == [
        ("Discord.Discord", "winget"),
        ("7zip.7zip", "winget"),
        ("9NKSQGP7F2NH", "msstore"),
    ]
    assert parse_winget_export("{}") == []


def test_match_by_catalog_and_heuristic() -> None:
    apps = [
        InstalledApp(name="Discord", scope="user"),
        InstalledApp(name="7-Zip 24.08 (x64)", scope="machine"),
        InstalledApp(name="Obsidian", scope="user"),
        InstalledApp(name="Programa Obscuro", scope="machine"),
    ]
    export = [
        ("Discord.Discord", "winget"),
        ("Obsidian.Obsidian", "winget"),
        ("Obscure.Tool", "winget"),
    ]
    out = {a.name: a for a in match_inventory(apps, export, CAT)}
    assert out["Discord"].catalog_id == "discord" and out["Discord"].winget_id == "Discord.Discord"
    # 7-Zip está no catálogo: usa o id do catálogo mesmo sem aparecer no export
    assert out["7-Zip 24.08 (x64)"].winget_id == "7zip.7zip"
    assert out["Obsidian"].winget_id == "Obsidian.Obsidian" and out["Obsidian"].catalog_id is None
    assert out["Programa Obscuro"].winget_id is None


def test_to_app_item_uses_catalog() -> None:
    discord = InstalledApp(
        name="Discord", scope="user", winget_id="Discord.Discord", catalog_id="discord"
    )
    item = to_app_item(discord, CAT)
    assert item.id == "discord" and not item.selected
    assert item.source == "winget_online" and item.scope == "user"
    assert "Discord.exe" in item.after_install.kill_processes
    spotify = to_app_item(
        InstalledApp(
            name="Spotify", scope="user", winget_id="Spotify.Spotify", catalog_id="spotify"
        ),
        CAT,
    )
    assert spotify.requires_non_elevated
    unknown = to_app_item(InstalledApp(name="Meu Programa 2", scope="machine"), CAT)
    assert (
        unknown.id == "meu-programa-2" and unknown.source == "offline" and unknown.installer is None
    )


def test_merge_preserves_existing_choices() -> None:
    r = recipe(apps=[make_app("discord", selected=True, order=5)])
    items = [
        to_app_item(InstalledApp(name="Discord", scope="user", catalog_id="discord"), CAT),
        to_app_item(InstalledApp(name="Novo", scope="machine"), CAT),
    ]
    added = merge_into_recipe(r, items)
    assert [a.id for a in added] == ["novo"]
    assert r.app("discord").selected and r.app("discord").order == 5  # type: ignore[union-attr]
