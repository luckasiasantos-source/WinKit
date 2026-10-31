from __future__ import annotations

from pathlib import Path

import pytest

from tests.core.test_installer_detect import fake_pe
from winkit.core.errors import WinKitError
from winkit.platform.fakes.apps import FakeWinget
from winkit.platform.fakes.services import fake_services
from winkit.studio.controller import StudioController


@pytest.fixture
def ctl(tmp_path: Path) -> StudioController:
    old = tmp_path / "C"
    d = old / "Users" / "Samuel" / "AppData" / "Roaming" / "discord"
    d.mkdir(parents=True)
    (d / "settings.json").write_text("{}")
    (old / "Ferramentas" / "Port").mkdir(parents=True)
    (old / "Ferramentas" / "Port" / "p.exe").write_bytes(b"MZ")
    pen = tmp_path / "pen"
    pen.mkdir()
    (pen / "Windows11.iso").write_bytes(b"iso")
    c = StudioController(services=fake_services(old_pc=old))
    c.open_folder(pen)
    return c


def test_requires_target_and_recipe(tmp_path: Path) -> None:
    c = StudioController(services=fake_services(old_pc=tmp_path))
    with pytest.raises(WinKitError):
        _ = c.root
    with pytest.raises(WinKitError):
        c.require_recipe()


def test_full_flow(ctl: StudioController, tmp_path: Path) -> None:
    assert ctl.recipe is None
    ctl.create_recipe("Samuel", "PC-S")
    assert ctl.recipe is not None and ctl.recipe.windows.computer_name == "PC-S"
    assert [v.data_letter for v in ctl.pendrives()] == ["E:"]
    added = ctl.collect_apps()
    assert {"discord", "7zip"} <= {a.id for a in added}
    for a in ctl.recipe.apps:
        a.selected = a.id in ("discord", "7zip")
    winget = ctl.services.winget
    assert isinstance(winget, FakeWinget)
    winget.downloads["7zip.7zip"] = ("nullsoft", "machine", "/S")
    results = {r.app_id: r.ok for r in ctl.download_selected()}
    assert results == {"7zip": True, "discord": False}
    setup = tmp_path / "x.exe"
    setup.write_bytes(fake_pe([".text"], b"Nullsoft.NSIS"))
    assert ctl.add_installer(setup, "Meu App", None, "machine").installer is not None
    port = ctl.add_portable(r"C:\Ferramentas\Port", "Port", "p.exe")
    assert port.source == "portable"
    assert len(ctl.driver_candidates()) == 4
    assert ctl.export_drivers([c for c in ctl.driver_candidates() if c.recommended]) == 3
    sugs = ctl.backup_suggestions()
    rec = next(s for s in sugs if s.recommended and s.exists)
    item = ctl.add_suggestion(rec)
    extra, warn = ctl.add_backup(
        r"C:\Users\Samuel\AppData\Roaming\discord", "Discord", "merge", True
    )
    assert warn is None and extra.decide_at_runtime
    rep = ctl.capture()
    assert rep.ok and ctl.is_captured(item)
    ctl.remove_backup(extra.id)
    assert ctl.recipe.backup(extra.id) is None
    assert ctl.validation().ok
    assert ctl.plan().steps
    report = ctl.build()
    assert report.manifest_files > 0 and report.templates
    assert ctl.validate_pendrive().ok
    assert ctl.sizes()["Apps"] > 0
    assert [i.name for i in ctl.isos()] == ["Windows11.iso"]
    # reabrir o pendrive carrega a receita salva
    ctl.open_folder(ctl.root)
    assert ctl.recipe is not None and ctl.recipe.backup(item.id) is not None
