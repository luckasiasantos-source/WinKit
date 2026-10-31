"""Assistente "o que levar" (V2-20): UserAssist, pontuação, sugestões e ignorar/adicionar."""

from __future__ import annotations

import codecs
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.factories import app, recipe
from winkit.collector import suggest as sg
from winkit.core.catalog.loader import default_catalogs
from winkit.core.inventory import InstalledApp
from winkit.core.suggest import rank, size_score, usage_score
from winkit.core.userassist import EXECUTABLES_GUID, make_entry, parse_entry
from winkit.platform.fakes.apps import FakeInventory
from winkit.platform.fakes.backup import FakeOldPcFolders
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.usage import USERASSIST_KEY

CAT = default_catalogs()
NOW = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)


def test_userassist_record_roundtrip() -> None:
    last = NOW - timedelta(days=2)
    name = codecs.encode(r"C:\Program Files\Mozilla Firefox\firefox.exe", "rot13")
    entry = parse_entry(name, make_entry(42, 1000, last))
    assert entry is not None and entry.count == 42 and entry.focus_ms == 1000
    assert entry.path.endswith("firefox.exe")
    assert entry.last_used is not None and abs(entry.last_used - last) < timedelta(seconds=1)
    assert parse_entry("HRZR_PGYFRFFVBA", make_entry(1, 0, None)) is None  # UEME_CTLSESSION
    assert parse_entry(name, b"\x00" * 16) is None  # formato antigo / curto


def test_scores_prefer_frequent_and_recent() -> None:
    assert usage_score(100, NOW, NOW) > usage_score(100, NOW - timedelta(days=60), NOW)
    assert usage_score(150, None, NOW) > usage_score(5, None, NOW)
    assert usage_score(10_000, NOW, NOW) == 100  # com teto
    assert size_score(100 * 1024**3) == 50


def _pc(tmp_path: Path) -> tuple[FakeOldPcFolders, Path]:
    c = tmp_path / "C"
    user = c / "Users" / "Samuel"
    (user / "AppData" / "Roaming" / ".minecraft" / "saves" / "Mundo").mkdir(parents=True)
    (user / "AppData" / "Roaming" / ".minecraft" / "saves" / "Mundo" / "level.dat").write_bytes(
        b"x" * 10
    )
    (user / "AppData" / "Roaming" / "StardewValley" / "Saves").mkdir(parents=True)  # vazia
    code = user / "AppData" / "Roaming" / "Code" / "User"
    code.mkdir(parents=True)
    (code / "settings.json").write_text("{}")
    (c / "Windows").mkdir()
    (c / "Fotos-antigas").mkdir()
    with (c / "Fotos-antigas" / "album.zip").open("wb") as f:
        f.truncate(300 * 1024**2)  # arquivo esparso: grande no tamanho, sem ocupar disco
    (c / "Pequena").mkdir()
    (c / "Pequena" / "a.txt").write_text("a")
    return FakeOldPcFolders(c), c


def _registry() -> FakeRegistry:
    reg = FakeRegistry()
    key = f"{USERASSIST_KEY}\\{EXECUTABLES_GUID}\\Count"
    for path, count, days in (
        (r"C:\Program Files\Mozilla Firefox\firefox.exe", 120, 0),
        (r"C:\Program Files\OBS Studio\bin\64bit\obs64.exe", 30, 1),
        (r"C:\Program Files\Raro\raro.exe", 1, 100),
        (r"C:\Program Files\7-Zip\7zFM.exe", 9, 5),
    ):
        reg.set(
            "HKCU",
            key,
            codecs.encode(path, "rot13"),
            "binary",
            make_entry(count, 0, NOW - timedelta(days=days)),
        )
    return reg


def _inventory() -> FakeInventory:
    return FakeInventory(
        apps=[
            InstalledApp(
                name="Mozilla Firefox (x64 pt-BR)",
                scope="machine",
                winget_id="Mozilla.Firefox",
                install_location=r"C:\Program Files\Mozilla Firefox",
            ),
            InstalledApp(name="OBS Studio", scope="machine", winget_id="OBSProject.OBSStudio"),
            InstalledApp(name="Raro", scope="machine", winget_id="Raro.Raro"),
            InstalledApp(name="7-Zip 24.08 (x64)", scope="machine", winget_id="7zip.7zip"),
            InstalledApp(name="VC++ 2015", scope="machine", redistributable=True),
        ]
    )


def _analyze(r, old: FakeOldPcFolders, c: Path, **kw):  # type: ignore[no-untyped-def]
    return sg.analyze(
        r,
        CAT,
        inventory=_inventory(),
        registry=_registry(),
        folders={**old.machine(), **old.current_user()},
        volume_root=lambda v: c,
        now=NOW,
        **kw,
    )


def test_analyze_suggests_each_kind_with_reason(tmp_path: Path) -> None:
    old, c = _pc(tmp_path)
    r = recipe()
    r.apps = [app("7zip", name="7-Zip", winget_id="7zip.7zip"), app("vscode", name="VS Code")]
    items = _analyze(r, old, c)
    ids = [s.id for s in items]
    # apps usados e fora da receita, o mais usado primeiro; o raro e o 7-Zip (já na receita) não
    assert [i for i in ids if i.startswith("app:")] == [
        "app:Mozilla.Firefox",
        "app:OBSProject.OBSStudio",
    ]
    assert items[0].reason.key == "suggest.app_used_today"
    assert items[1].reason.key == "suggest.app_used_yesterday"
    assert any(i.startswith("config:vscode:") for i in ids)
    assert "save:minecraft" in ids and "save:stardew_valley" not in ids  # pasta vazia
    assert "folder:fotos-antigas" in ids
    assert "folder:pequena" not in ids and "folder:windows" not in ids
    kinds = [s.kind for s in items]
    assert kinds == sorted(kinds, key=["app", "config", "save", "folder", "other"].index)


def test_dismissed_never_come_back_and_accept_adds(tmp_path: Path) -> None:
    old, c = _pc(tmp_path)
    r = recipe()
    r.apps = [app("vscode", name="VS Code")]
    folders = {**old.machine(), **old.current_user()}
    items = {s.id: s for s in _analyze(r, old, c)}
    sg.dismiss(r, "app:OBSProject.OBSStudio")
    sg.dismiss(r, "app:OBSProject.OBSStudio")
    assert r.meta.dismissed_suggestions == ["app:OBSProject.OBSStudio"]
    again = {s.id for s in _analyze(r, old, c)}
    assert "app:OBSProject.OBSStudio" not in again
    assert sg.accept(r, CAT, items["app:Mozilla.Firefox"], folders)
    assert r.apps[-1].winget_id == "Mozilla.Firefox" and r.apps[-1].source == "winget_online"
    assert sg.accept(r, CAT, items["save:minecraft"], folders)
    assert sg.accept(r, CAT, items["folder:fotos-antigas"], folders)
    config = next(s for k, s in items.items() if k.startswith("config:vscode:"))
    assert sg.accept(r, CAT, config, folders)
    templates = {b.template for b in r.backups}
    assert r"{APPDATA}\.minecraft\saves" in templates
    assert any("Fotos-antigas" in t for t in templates)
    # depois de aceitar, as sugestões somem sozinhas (já estão na receita)
    left = {s.id for s in _analyze(r, old, c)}
    assert not left & {"app:Mozilla.Firefox", "save:minecraft", config.id}


def test_folder_scan_respects_time_limit(tmp_path: Path) -> None:
    old, c = _pc(tmp_path)
    ticks = iter(range(10_000))
    items = _analyze(recipe(), old, c, budget_s=0, clock=lambda: float(next(ticks)))
    assert not [s for s in items if s.kind == "folder"]


def test_without_registry_still_suggests_files(tmp_path: Path) -> None:
    old, c = _pc(tmp_path)
    items = sg.analyze(
        recipe(),
        CAT,
        inventory=_inventory(),
        registry=None,
        folders={**old.machine(), **old.current_user()},
        volume_root=lambda v: c,
        now=NOW,
    )
    assert not [s for s in items if s.kind == "app"]
    assert "save:minecraft" in {s.id for s in items}


@pytest.mark.parametrize("dismissed", [[], ["x"]])
def test_rank_is_stable(dismissed: list[str]) -> None:
    assert rank([], dismissed) == []


def test_cli_suggestions(tmp_path: Path) -> None:
    import json

    from tests.agent.helpers import make_world
    from winkit.cli import main as cli
    from winkit.platform.fakes.services import fake_services

    (tmp_path / "w").mkdir()
    w = make_world(tmp_path / "w")
    _old, c = _pc(tmp_path)
    services = fake_services(old_pc=c, inventory=_inventory(), registry=_registry())
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=services, out=out.append)

    assert run("sugestoes", "listar", "--json") == 0
    data = json.loads("\n".join(out))
    assert data[0]["id"] == "app:Mozilla.Firefox" and data[0]["reason"]
    assert run("suggestions", "add", "app:Mozilla.Firefox", "save:minecraft") == 0
    assert run("sugestoes", "ignorar", "app:OBSProject.OBSStudio") == 0
    r = w.recipe()
    assert [a.winget_id for a in r.apps] == ["Mozilla.Firefox"]
    assert r.meta.dismissed_suggestions == ["app:OBSProject.OBSStudio"]
    assert run("sugestoes", "adicionar", "nao:existe") == 1
