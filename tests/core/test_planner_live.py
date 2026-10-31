"""Modo ao vivo e ponto de restauração no planejador (R30, R31, D-033)."""

from __future__ import annotations

from tests.factories import app, backup, recipe, tweak
from winkit.core.catalog.loader import default_catalogs
from winkit.core.planner.models import PlanContext
from winkit.core.planner.planner import plan

LIVE = PlanContext(os_major=11, build=26100, phase1_ran=False, mode="live")


def _recipe():  # type: ignore[no-untyped-def]
    return recipe(
        apps=[app("a"), app("w", source="winget_online")],
        backups=[backup("b")],
        tweaks=[tweak("visual.dark_theme")],
    )


def test_install_mode_ends_with_ready_restore_point() -> None:
    p = plan(_recipe(), default_catalogs())
    kinds = [s.kind for s in p.phase(2)]
    assert kinds[-2:] == ["restore_point", "finalize"]
    assert p.step("restore_point:ready") is not None
    r = _recipe()
    r.restore_point.enabled = False
    assert plan(r, default_catalogs()).step("restore_point:ready") is None


def test_live_mode_starts_with_restore_point_and_has_one_phase() -> None:
    p = plan(_recipe(), default_catalogs(), LIVE)
    assert p.phase(1) == []
    assert p.phase(2)[0].id == "restore_point:before"
    assert p.step("restore_point:ready") is None
    assert all(s.target != "default_profile" for s in p.steps)  # R31


def test_live_mode_without_restore_point() -> None:
    ctx = LIVE.model_copy(update={"restore_before": False})
    p = plan(_recipe(), default_catalogs(), ctx)
    assert all(s.kind != "restore_point" for s in p.steps)


def test_only_kinds_filters_but_keeps_restore_and_finalize() -> None:
    ctx = LIVE.model_copy(update={"only_kinds": frozenset({"backup"})})
    p = plan(_recipe(), default_catalogs(), ctx)
    assert {s.kind for s in p.steps} == {"restore_point", "backup", "finalize"}
    assert {e.ref for e in p.excluded if e.kind == "app"} == {"a", "w"}


def test_live_mode_renames_when_recipe_has_a_name() -> None:
    r = _recipe()
    r.windows.computer_name = "PC-NOVO"
    assert plan(r, default_catalogs(), LIVE).step("rename_computer:computer") is not None
    assert plan(r, default_catalogs()).step("rename_computer:computer") is None  # vai no XML


def test_live_plan_is_deterministic() -> None:
    assert plan(_recipe(), default_catalogs(), LIVE) == plan(_recipe(), default_catalogs(), LIVE)
