"""Atualizar instaladores do pendrive (V2-21): versões, troca segura, falha não perde nada."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from tests.agent.helpers import START, make_world
from winkit.cli import main as cli
from winkit.collector.app_updates import needs_check, refresh_apps
from winkit.collector.apps import download_app
from winkit.core.catalog.loader import default_catalogs
from winkit.core.recipe.models import AppItem, Recipe
from winkit.core.versions import compare
from winkit.platform.fakes.apps import FakeWinget
from winkit.platform.fakes.services import fake_services

GB = 10 * 2**30


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("1.2.3", "1.2.10", -1),
        ("2024.10", "2024.9", 1),
        ("1.0.0-beta", "1.0.0", -1),
        ("1.2", "1.2.0", 0),
        ("1-2-3", "1.2.3", 0),  # pastas antigas gravadas com hífen
        ("v3.1", "3.0.9", 1),
        ("24.08", "24.07.1", 1),
        ("1.0rc1", "1.0", -1),
        ("119.0.6045.160", "119.0.6045.123", 1),
    ],
)
def test_compare_versions(a: str, b: str, expected: int) -> None:
    assert compare(a, b) == expected
    assert compare(b, a) == -expected


def _setup(tmp_path: Path) -> tuple[Path, Recipe, FakeWinget, list[int]]:
    w = make_world(tmp_path)
    winget = FakeWinget(
        downloads={"Mozilla.Firefox": ("exe", "machine", "/S")}, versions={"Mozilla.Firefox": "1.0"}
    )
    r = w.recipe()
    item = AppItem(
        id="firefox", name="Firefox", source="winget_online", winget_id="Mozilla.Firefox"
    )
    r.apps = [item, AppItem(id="meu", name="Meu", source="offline")]
    assert download_app(winget, w.pendrive, item, default_catalogs(), free_bytes=GB).ok
    saves: list[int] = []
    return w.pendrive, r, winget, saves


def test_check_only_changes_nothing(tmp_path: Path) -> None:
    root, r, winget, saves = _setup(tmp_path)
    before = r.apps[0].installer
    winget.versions["Mozilla.Firefox"] = "2.0"
    results = refresh_apps(
        winget,
        root,
        r,
        default_catalogs(),
        apply=False,
        ids=None,
        save=lambda: saves.append(1),
        now=START,
    )
    statuses = {x.app_id: x.status for x in results}
    assert statuses == {"firefox": "newer", "meu": "manual"}
    assert r.apps[0].installer == before
    assert not (root / "WinKit" / "Apps" / "firefox" / ".verificando").exists()
    assert r.meta.last_update_check == START


def test_update_swaps_then_deletes_old(tmp_path: Path) -> None:
    root, r, winget, _saves = _setup(tmp_path)
    old_dir = root / "WinKit" / "Apps" / "firefox" / "1-0"
    assert old_dir.is_dir() and r.apps[0].installer_version == "1.0"
    winget.versions["Mozilla.Firefox"] = "2.0.1"
    order: list[str] = []

    def save() -> None:
        order.append("save:" + ("velha" if old_dir.exists() else "sem-velha"))

    (result,) = list(
        refresh_apps(
            winget, root, r, default_catalogs(), apply=True, ids=["firefox"], save=save, now=START
        )
    )
    assert result.status == "updated" and (result.current, result.available) == ("1.0", "2.0.1")
    item = r.apps[0]
    assert item.installer is not None and item.installer.path.startswith("Apps/firefox/2-0-1/")
    assert item.installer_version == "2.0.1"
    assert (root / "WinKit" / item.installer.path).is_file()
    assert not old_dir.exists()
    assert order[0] == "save:velha"  # a receita aponta para a nova ANTES de apagar a velha


def test_failure_in_the_middle_keeps_old_version(tmp_path: Path) -> None:
    """Teste de proteção (V2-21): falha no download não perde a versão antiga."""
    root, r, winget, _saves = _setup(tmp_path)
    before = r.apps[0].installer
    winget.downloads.clear()  # o próximo download falha
    (result,) = refresh_apps(
        winget,
        root,
        r,
        default_catalogs(),
        apply=True,
        ids=["firefox"],
        save=lambda: None,
        now=START,
    )
    assert result.status == "failed"
    assert r.apps[0].installer == before
    assert before is not None and (root / "WinKit" / str(before.path)).is_file()


def test_older_on_winget_is_never_installed(tmp_path: Path) -> None:
    root, r, winget, _ = _setup(tmp_path)
    winget.versions["Mozilla.Firefox"] = "0.9"
    (result,) = refresh_apps(
        winget,
        root,
        r,
        default_catalogs(),
        apply=True,
        ids=["firefox"],
        save=lambda: None,
        now=START,
    )
    assert result.status == "older" and r.apps[0].installer_version == "1.0"


def test_needs_check_after_30_days(tmp_path: Path) -> None:
    _, r, _, _ = _setup(tmp_path)
    r.apps[0].source = "offline"
    r.meta.last_update_check = START
    assert not needs_check(r, START + timedelta(days=29))
    assert needs_check(r, START + timedelta(days=31))


def test_cli_apps_update(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    winget = FakeWinget(downloads={"Mozilla.Firefox": ("exe", "machine", "/S")})
    r = w.recipe()
    item = AppItem(
        id="firefox", name="Firefox", source="winget_online", winget_id="Mozilla.Firefox"
    )
    r.apps = [item]
    download_app(winget, w.pendrive, item, default_catalogs(), free_bytes=GB)
    from winkit.builder.build import save_profile_recipe

    save_profile_recipe(w.pendrive, r)
    winget.versions["Mozilla.Firefox"] = "3.0"
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]
    services = fake_services(winget=winget)
    assert (
        cli.main(["apps", "atualizar", "--verificar", *raiz], services=services, out=out.append)
        == 0
    )
    assert any("1.0 → 3.0" in line for line in out)
    assert w.recipe().apps[0].installer_version == "1.0"
    assert cli.main(["apps", "update", "firefox", *raiz], services=services, out=out.append) == 0
    assert w.recipe().apps[0].installer_version == "3.0"
