from __future__ import annotations

from pathlib import Path

from tests.core.test_installer_detect import fake_pe
from tests.factories import recipe
from winkit.collector import apps as col
from winkit.core import layout
from winkit.core.catalog.loader import default_catalogs
from winkit.core.manifest.manifest import hash_file
from winkit.core.recipe.models import AppItem
from winkit.platform.fakes.apps import FakeInventory, FakeWinget

CAT = default_catalogs()
GB = 1024**3


def test_collect_and_add_inventory() -> None:
    apps = col.collect_inventory(FakeInventory(), FakeWinget(), CAT)
    by_name = {a.name: a for a in apps}
    assert by_name["Discord"].winget_id == "Discord.Discord"
    assert by_name["7-Zip 24.08 (x64)"].catalog_id == "7zip"
    r = recipe()
    added = col.add_inventory(r, apps, CAT)
    ids = [a.id for a in added]
    assert "discord" in ids and "7zip" in ids and "programa-obscuro" in ids
    assert not any("visual" in i for i in ids)  # redistribuível fora por padrão
    assert all(not a.selected for a in added)
    assert len(col.add_inventory(r, apps, CAT, include_redist=True)) == 1


def test_collect_without_winget() -> None:
    apps = col.collect_inventory(FakeInventory(), FakeWinget(is_available=False), CAT)
    disc = next(a for a in apps if a.name == "Discord")
    assert disc.winget_id == "Discord.Discord"  # vem do catálogo


def _item(app_id: str = "7zip", winget_id: str | None = "7zip.7zip") -> AppItem:
    return AppItem(id=app_id, name=app_id, source="winget_online", winget_id=winget_id)


def test_download_makes_app_offline(tmp_path: Path) -> None:
    w = FakeWinget(downloads={"7zip.7zip": ("nullsoft", "machine", "/S")})
    item = _item()
    res = col.download_app(w, tmp_path, item, CAT, free_bytes=50 * GB)
    assert res.ok, res.message
    assert item.source == "offline" and item.installer is not None
    assert item.installer.type == "nsis" and item.installer.args == ["/S"]
    assert item.installer.path == "Apps/7zip/1-0/7zip.7zip_1.0_nullsoft.exe"
    installer = layout.payload(tmp_path, item.installer.path)
    assert item.installer.sha256 == hash_file(installer)
    assert not layout.payload(tmp_path, "Apps/7zip/.baixando").exists()


def test_download_uses_default_switches_and_scope(tmp_path: Path) -> None:
    w = FakeWinget(downloads={"Code.Code": ("inno", "user", "''")})
    item = _item("vscode", "Code.Code")
    assert col.download_app(w, tmp_path, item, CAT, free_bytes=50 * GB).ok
    assert item.installer is not None and item.installer.args[0] == "/VERYSILENT"
    assert item.scope == "user"


def test_download_failures(tmp_path: Path) -> None:
    w = FakeWinget(downloads={"Z.Zip": ("zip", "machine", "''"), "E.Exe": ("exe", "machine", "''")})
    for item, msg in [
        (_item("z", "Z.Zip"), "não instala offline"),
        (_item("e", "E.Exe"), "silencioso"),
        (_item("n", "Nao.Existe"), "0x8A150014"),
        (_item("s", None), "sem ID"),
    ]:
        res = col.download_app(w, tmp_path, item, CAT, free_bytes=50 * GB)
        assert not res.ok and msg in res.message, (item.id, res.message)
        assert item.source == "winget_online"
    res = col.download_app(w, tmp_path, _item("z", "Z.Zip"), CAT, free_bytes=GB)
    assert "2 GB" in res.message
    store = AppItem(
        id="w", name="w", source="winget_online", winget_id="9NKS", winget_source="msstore"
    )
    assert "Loja" in col.download_app(w, tmp_path, store, CAT, free_bytes=50 * GB).message


def test_add_local_installer(tmp_path: Path) -> None:
    src = tmp_path / "Meu Setup.exe"
    src.write_bytes(fake_pe([".text"], b"Inno Setup Setup Data"))
    pen = tmp_path / "pen"
    r = recipe()
    item = col.add_local_installer(pen, r, src, name="Meu App", catalogs=CAT)
    assert item.id == "meu-app" and item.selected
    assert item.installer is not None and item.installer.type == "inno"
    assert item.installer.path == "Apps/meu-app/local/meu-setup.exe"
    assert layout.payload(pen, item.installer.path).is_file()
    again = col.add_local_installer(pen, r, src, name="Meu App", catalogs=CAT, args=["/X"])
    assert len(r.apps) == 1 and again.installer is not None and again.installer.args == ["/X"]
    squirrel = tmp_path / "s.exe"
    squirrel.write_bytes(fake_pe([".text"], b"SquirrelSetup"))
    assert col.add_local_installer(pen, r, squirrel, name="S", catalogs=CAT).scope == "user"
