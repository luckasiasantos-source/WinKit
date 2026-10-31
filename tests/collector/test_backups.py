from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.factories import FIXED_NOW, app, recipe
from winkit.collector import backups as bk
from winkit.core import layout
from winkit.core.catalog.loader import default_catalogs
from winkit.core.errors import WinKitError
from winkit.core.recipe.models import Recipe
from winkit.platform.copy import PythonCopier
from winkit.platform.fakes.backup import FakeOldPcFolders, FakeShadowCopies
from winkit.platform.vss import PendingSnapshots

CAT = default_catalogs()
GB = 1024**3


@pytest.fixture
def oldpc(tmp_path: Path) -> FakeOldPcFolders:
    c = tmp_path / "C"
    d = c / "Users" / "Samuel" / "AppData" / "Roaming" / "discord"
    (d / "Cache").mkdir(parents=True)
    (d / "Local Storage" / "leveldb").mkdir(parents=True)
    (d / "settings.json").write_text('{"tema": "escuro"}')
    (d / "Cache" / "x.bin").write_bytes(b"x" * 100)
    (d / "Local Storage" / "leveldb" / "000003.log").write_text("token")
    (d / "Local Storage" / "leveldb" / "000005.ldb").write_text("token")
    code = c / "Users" / "Samuel" / "AppData" / "Roaming" / "Code" / "User"
    code.mkdir(parents=True)
    (code / "settings.json").write_text("{}")
    winrar = c / "Program Files" / "WinRAR"
    winrar.mkdir(parents=True)
    (winrar / "rarreg.key").write_text("licença")
    return FakeOldPcFolders(c)


def folders(old: FakeOldPcFolders) -> dict[str, str]:
    return {**old.machine(), **old.current_user()}


def capture(
    r: Recipe, old: FakeOldPcFolders, pen: Path, vss: FakeShadowCopies | None = None, **kw: object
) -> bk.CaptureReport:
    return bk.capture(
        pen,
        r,
        CAT,
        copier=PythonCopier(),
        vss=vss or FakeShadowCopies({"C:": old.base}),
        pending=PendingSnapshots(pen.parent / "pend.json"),
        old_folders=folders(old),
        link_base=pen.parent / "links",
        free_bytes=kw.pop("free", 50 * GB),  # type: ignore[arg-type]
        volume_root=old.volume_root,
        now=lambda: FIXED_NOW,
        **kw,  # type: ignore[arg-type]
    )


def test_suggestions_for_selected_apps(oldpc: FakeOldPcFolders) -> None:
    r = recipe(apps=[app("discord"), app("vscode"), app("winrar"), app("steam", selected=False)])
    sugs = bk.suggest(r, CAT, folders(oldpc), oldpc.volume_root)
    by_tpl = {s.template: s for s in sugs}
    settings = by_tpl[r"{APPDATA}\discord\settings.json"]
    assert settings.recommended and settings.exists and settings.kind == "file"
    storage = by_tpl[r"{APPDATA}\discord\Local Storage"]
    assert not storage.recommended and storage.warning and "token" in storage.warning
    assert by_tpl[r"{APPDATA}\Code\User"].exists
    assert not by_tpl[r"{USERPROFILE}\.vscode\extensions"].exists
    assert by_tpl[r"{PROGRAMFILES}\WinRAR\rarreg.key"].exists
    assert not any(s.app_id == "steam" for s in sugs)


def test_add_backup_translates_and_dedupes(oldpc: FakeOldPcFolders) -> None:
    r = recipe()
    item, warn = bk.add_backup(
        r,
        CAT,
        name="Discord",
        old_folders=folders(oldpc),
        literal=r"C:\Users\Samuel\AppData\Roaming\discord",
    )
    assert item.template == r"{APPDATA}\discord" and warn is None
    assert item.data_path == "Perfis/padrao/Backups/discord/dados"
    assert "Cache" in item.exclude
    again, _ = bk.add_backup(
        r,
        CAT,
        name="Outro",
        old_folders=folders(oldpc),
        literal=r"c:\users\samuel\appdata\roaming\DISCORD",
    )
    assert again is item and len(r.backups) == 1
    abs_item, warn = bk.add_backup(
        r, CAT, name="Jogo", old_folders=folders(oldpc), literal=r"D:\Jogos\Save"
    )
    assert abs_item.template == r"{ABS:D:\Jogos\Save}" and warn and "D:" in warn
    dup, _ = bk.add_backup(r, CAT, name="Discord", template=r"{APPDATA}\outro")
    assert dup.id == "discord-2"
    with pytest.raises(WinKitError):
        bk.add_backup(r, CAT, name="x")


def test_capture_with_vss(oldpc: FakeOldPcFolders, tmp_path: Path) -> None:
    pen = tmp_path / "pen"
    r = recipe(apps=[app("discord")])
    for s in bk.suggest(r, CAT, folders(oldpc), oldpc.volume_root):
        if s.recommended:
            bk.add_suggestion(r, CAT, s)
    bk.add_backup(
        r,
        CAT,
        name="Discord tudo",
        literal=r"C:\Users\Samuel\AppData\Roaming\discord",
        old_folders=folders(oldpc),
    )
    vss = FakeShadowCopies({"C:": oldpc.base})
    rep = capture(r, oldpc, pen, vss)
    assert rep.ok, [i.message for i in rep.items]
    assert vss.created == ["{snap-1}"] and vss.deleted == ["{snap-1}"]  # uma por volume, apagada
    settings = r.backups[0]
    assert settings.kind == "file"
    assert (layout.payload(pen, settings.data_path) / "settings.json").is_file()
    full = r.backups[1]
    dados = layout.payload(pen, full.data_path)
    assert (dados / "settings.json").exists()
    assert not (dados / "Cache").exists()  # exclusão padrão
    assert any("token" in w for w in full.warnings)  # item 16
    info = json.loads((dados.parent / "item.json").read_text(encoding="utf-8"))
    assert info["used_vss"] and info["source_literal"].endswith("discord")
    assert info["template"] == r"{APPDATA}\discord"


def test_capture_without_vss_support(oldpc: FakeOldPcFolders, tmp_path: Path) -> None:
    r = recipe()
    bk.add_backup(
        r,
        CAT,
        name="d",
        literal=r"C:\Users\Samuel\AppData\Roaming\discord",
        old_folders=folders(oldpc),
    )
    vss = FakeShadowCopies({"C:": oldpc.base}, unsupported={"C:"})
    rep = capture(r, oldpc, tmp_path / "pen", vss)
    assert rep.ok and not rep.items[0].used_vss
    assert any("NTFS" in n for n in rep.notes)
    vss2 = FakeShadowCopies({"C:": oldpc.base}, fail_create=True)
    rep2 = capture(r, oldpc, tmp_path / "pen2", vss2)
    assert rep2.ok and any("VSS" in n for n in rep2.notes)
    rep3 = capture(r, oldpc, tmp_path / "pen3", use_vss=False)
    assert rep3.ok and not rep3.notes


def test_capture_missing_source_and_space(oldpc: FakeOldPcFolders, tmp_path: Path) -> None:
    r = recipe()
    bk.add_backup(r, CAT, name="x", template=r"{APPDATA}\nao-existe")
    rep = capture(r, oldpc, tmp_path / "pen")
    assert not rep.ok and "não existe" in rep.items[0].message
    r2 = recipe()
    bk.add_backup(
        r2,
        CAT,
        name="d",
        literal=r"C:\Users\Samuel\AppData\Roaming\discord",
        old_folders=folders(oldpc),
    )
    with pytest.raises(WinKitError, match="Espaço insuficiente"):
        capture(r2, oldpc, tmp_path / "pen", free=10)


def test_capture_only_some_and_orphans(oldpc: FakeOldPcFolders, tmp_path: Path) -> None:
    r = recipe()
    a, _ = bk.add_backup(r, CAT, name="a", template=r"{APPDATA}\discord")
    bk.add_backup(r, CAT, name="b", template=r"{APPDATA}\Code\User")
    pend = PendingSnapshots(tmp_path / "pend.json")
    pend.add("{orfa}")
    vss = FakeShadowCopies({"C:": oldpc.base})
    rep = capture(r, oldpc, tmp_path / "pen", vss, only={a.id})
    assert [i.backup_id for i in rep.items] == [a.id]
    assert "{orfa}" in vss.deleted and pend.load() == []


def test_portable_app(oldpc: FakeOldPcFolders) -> None:
    r = recipe()
    app_item, b = bk.add_portable_app(
        r,
        CAT,
        literal_folder=r"C:\Program Files\WinRAR",
        old_folders=folders(oldpc),
        name="Rar Portátil",
        exe="rar.exe",
    )
    assert app_item.source == "portable" and app_item.portable_backup == b.id
    assert app_item.after_install.shortcuts[0].target == r"{PROGRAMFILES}\WinRAR\rar.exe"
    assert b.related_app == app_item.id


def test_installer_wipes_config_links_backup(monkeypatch: pytest.MonkeyPatch) -> None:
    from winkit.core.catalog.models import Catalogs

    data = CAT.model_dump()
    for a in data["apps"]:
        if a["id"] == "vlc":
            a["installer_wipes_config"] = True
    cat = Catalogs.model_validate(data)
    r = recipe(apps=[app("vlc")])
    s = bk.Suggestion("vlc", "VLC", r"{APPDATA}\vlc", "folder", True, True, 1, 1, None, ())
    item = bk.add_suggestion(r, cat, s)
    assert r.app("vlc").restore_backups_after_install == [item.id]  # type: ignore[union-attr]


def test_dpapi_scan(tmp_path: Path) -> None:
    (tmp_path / "Default" / "Network").mkdir(parents=True)
    (tmp_path / "Default" / "Network" / "Cookies").write_text("x")
    (tmp_path / "Login Data").write_text("x")
    warnings = bk.dpapi_warnings(tmp_path, CAT)
    assert any("Cookies" in w for w in warnings) and any("Login Data" in w for w in warnings)
