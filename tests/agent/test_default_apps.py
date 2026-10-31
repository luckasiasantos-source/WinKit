"""Apps padrão (V2-05): XML do dism, filtro por grupo, Fase 1, conferência e CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.collector.associations import collect_associations, group_rows
from winkit.core.associations import (
    AssociationsError,
    filtered_xml,
    identifiers,
    parse,
    user_choice_key,
)
from winkit.core.catalog.loader import default_catalogs
from winkit.core.planner.models import PlanContext
from winkit.core.planner.planner import plan
from winkit.platform.fakes.associations import FakeAssociations
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.services import fake_services

XML = (
    Path(__file__).resolve().parents[1] / "fixtures" / "associations" / "exportado.xml"
).read_bytes()


def test_parse_and_filter() -> None:
    items = parse(XML)
    assert {a.identifier for a in items} == {
        ".htm",
        ".html",
        ".pdf",
        ".mp4",
        ".mkv",
        ".txt",
        "http",
        "https",
    }
    groups = default_catalogs().association_groups
    keep = identifiers(groups, ["browser", "pdf"])
    out = parse(filtered_xml(items, keep))
    assert {a.identifier for a in out} == {".htm", ".html", ".pdf", "http", "https"}
    with pytest.raises(AssociationsError):
        parse(b"<outra/>")
    with pytest.raises(AssociationsError):
        parse(b"nao e xml")
    assert user_choice_key(".pdf").endswith(r"FileExts\.pdf\UserChoice")
    assert user_choice_key("http").endswith(r"UrlAssociations\http\UserChoice")


def _world(tmp_path: Path, groups: list[str] | None = None) -> World:
    w = make_world(tmp_path)
    r = w.recipe()
    collect_associations(FakeAssociations(exported=XML), w.pendrive, r, default_catalogs())
    if groups is not None:
        r.default_apps.groups = groups
    w.save_recipe(r)
    return w


def test_collect_selects_groups_with_an_app(tmp_path: Path) -> None:
    w = _world(tmp_path)
    r = w.recipe()
    assert r.default_apps.enabled
    assert set(r.default_apps.groups) == {"browser", "pdf", "video", "text"}  # sem e-mail
    rows = {g.id: app for g, app in group_rows(w.pendrive, r, default_catalogs())}
    assert rows["browser"] == "Firefox" and rows["video"] == "VLC media player"
    assert rows["email"] is None


def test_plan_phase1_import_and_phase2_verify(tmp_path: Path) -> None:
    w = _world(tmp_path)
    p = plan(w.recipe(), default_catalogs(), PlanContext(os_major=11, build=26100))
    imp, ver = p.step("default_apps:import"), p.step("default_apps_verify:user")
    assert imp is not None and imp.phase == 1
    assert ver is not None and ver.phase == 2 and ver.depends_on == ("default_apps:import",)
    live = plan(w.recipe(), default_catalogs(), PlanContext(mode="live", phase1_ran=False))
    assert live.step("default_apps_verify:user") is None


def test_import_filtered_and_verify_reports_pending(tmp_path: Path) -> None:
    w = _world(tmp_path, ["browser", "pdf"])
    run_phase1(w.runtime())
    fake = w.services.associations
    assert isinstance(fake, FakeAssociations)
    (imported,) = fake.imported
    assert {a.identifier for a in parse(imported)} == {".htm", ".html", ".pdf", "http", "https"}
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    for ident, prog in (
        (".htm", "FirefoxHTML-308046B0AF4A39CB"),
        (".html", "FirefoxHTML-308046B0AF4A39CB"),
        ("http", "FirefoxURL-308046B0AF4A39CB"),
        ("https", "FirefoxURL-308046B0AF4A39CB"),
    ):
        reg.set("HKCU", user_choice_key(ident), "ProgId", "sz", prog)
    run_phase2(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None
    assert state.step("default_apps:import").status == "done"
    assert state.step("default_apps_verify:user").status == "done"
    pending = [m for m in state.warnings if m.key == "summary.default_apps_pending"]
    assert pending and pending[0].params["ids"] == ".pdf"


def test_fallback_and_live_never_force(tmp_path: Path) -> None:
    w = _world(tmp_path, ["pdf"])
    result = run_live(w.runtime(), LiveOptions(root=w.pendrive, simulate=True, restore_point=False))
    assert result.preview is not None
    assert "default_apps:import" in result.preview.not_live_safe
    run_phase2(w.runtime())  # a Fase 1 não rodou (fallback D-012)
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("default_apps:import").status == "skipped"
    fake = w.services.associations
    assert isinstance(fake, FakeAssociations) and fake.imported == []


def test_cli_default_apps(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    services = fake_services(associations=FakeAssociations(exported=XML))
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=services, out=out.append)

    assert run("coletar", "associacoes") == 0
    assert any("[x] pdf" in x and "SumatraPDF" in x for x in out)
    assert run("associacoes", "desmarcar", "video", "text") == 0
    assert set(w.recipe().default_apps.groups) == {"browser", "pdf"}
    assert run("defaults", "select", "nada") == 1
