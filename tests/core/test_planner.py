from __future__ import annotations

import pytest

from tests.factories import app, backup, driver, recipe, tweak
from winkit.core.catalog.loader import default_catalogs
from winkit.core.errors import PlanError
from winkit.core.planner.models import PlanContext
from winkit.core.planner.planner import TWEAK_CONSUMER_CONTENT, TWEAK_WU_DRIVERS, plan
from winkit.core.recipe.models import Recipe

CAT = default_catalogs()
WIN11 = PlanContext(os_major=11, build=26100)


def P(r: Recipe, ctx: PlanContext = WIN11):  # noqa: N802
    return plan(r, CAT, ctx)


def phases(p) -> dict[str, int]:
    return {s.id: s.phase for s in p.steps}


def test_empty_recipe_has_implicit_steps() -> None:
    p = P(recipe())
    ids = p.ids()
    assert f"tweak:{TWEAK_WU_DRIVERS}" in ids
    assert f"tweak:{TWEAK_CONSUMER_CONTENT}" in ids
    assert ids[-1] == "finalize:summary"
    assert "windows_update:all" in ids


def test_implicit_tweaks_can_be_turned_off() -> None:
    r = recipe()
    r.updates.block_wu_driver_replacement = False
    r.bloatware.disable_consumer_content = False
    r.updates.windows_update_after_install = False
    r.restore_point.enabled = False
    r.updates.fix_missing_drivers = False
    assert P(r).ids() == ["finalize:summary"]


def test_drivers_phase1_by_priority() -> None:  # R3
    r = recipe(drivers=[driver("z-audio", 5, "MEDIA"), driver("a-net", 0), driver("b-chip", 1)])
    p = P(r)
    drivers = [s for s in p.steps if s.kind == "driver"]
    assert [s.ref for s in drivers] == ["a-net", "b-chip", "z-audio"]
    assert all(s.phase == 1 and s.needs_pendrive and s.target == "machine" for s in drivers)


def test_unselected_items_are_ignored() -> None:
    r = recipe(
        drivers=[driver("d")],
        apps=[app("a", selected=False)],
        backups=[backup("b", selected=False)],
    )
    r.drivers[0].selected = False
    assert not [s for s in P(r).steps if s.kind in ("driver", "app", "backup")]


def test_bloat_phase1_and_os_filter() -> None:  # R4
    r = recipe()
    r.bloatware.remove = ["Microsoft.BingNews", "Microsoft.People", "Microsoft.WindowsStore", "X.Y"]
    p = P(r)
    assert phases(p)["bloat:Microsoft.BingNews"] == 1
    excluded = {e.ref: e.reason for e in p.excluded}
    assert "Microsoft.People" in excluded  # só Windows 10
    assert "Microsoft.WindowsStore" in excluded  # bloqueado
    assert "X.Y" in excluded


def test_tweaks_targets() -> None:  # R5, R6
    r = recipe(tweaks=[tweak("visual.dark_theme"), tweak("privacy.activity_history")])
    p = P(r)
    dark = p.step("tweak:visual.dark_theme")
    hist = p.step("tweak:privacy.activity_history")
    assert dark and dark.phase == 1 and dark.target == "default_profile"
    assert hist and hist.phase == 1 and hist.target == "machine"


def test_tweak_decide_at_runtime_goes_to_phase2_hkcu() -> None:  # R2
    r = recipe(tweaks=[tweak("visual.dark_theme", decide_at_runtime=True)])
    s = P(r).step("tweak:visual.dark_theme")
    assert s and s.phase == 2 and s.target == "user_profile" and s.user_choice


def test_silent_mode_ignores_decide_at_runtime() -> None:  # R1
    r = recipe(
        tweaks=[tweak("visual.dark_theme", decide_at_runtime=True)],
        apps=[app("a", decide_at_runtime=True)],
    )
    r.execution.mode = "silent"
    p = P(r)
    assert phases(p)["tweak:visual.dark_theme"] == 1
    assert phases(p)["app:a"] == 1
    assert not any(s.user_choice for s in p.steps)


def test_specialize_and_unknown_and_os_tweaks_excluded() -> None:
    r = recipe(
        tweaks=[
            tweak("system.prevent_device_encryption"),
            tweak("visual.nope"),
            tweak("visual.taskbar_left"),
        ]
    )
    p = P(r, PlanContext(os_major=10, build=19045))
    reasons = {e.ref: e.reason for e in p.excluded}
    assert "durante a instalação" in reasons["system.prevent_device_encryption"]
    assert "visual.nope" in reasons
    assert "versão" in reasons["visual.taskbar_left"]


def test_disabled_tweak_is_not_planned() -> None:
    r = recipe(tweaks=[tweak("visual.dark_theme", enabled=False)])
    assert P(r).step("tweak:visual.dark_theme") is None


def test_backups_by_template() -> None:  # R7, R8
    r = recipe(
        backups=[
            backup("perfil", "{APPDATA}\\x"),
            backup("maquina", "{PROGRAMDATA}\\x"),
            backup("abs", "{ABS:D:\\Jogos}"),
            backup("ask", "{APPDATA}\\y", decide_at_runtime=True),
        ]
    )
    p = P(r)
    s = {x.ref: x for x in p.steps if x.kind == "backup"}
    assert (s["perfil"].phase, s["perfil"].target) == (1, "default_profile")
    assert (s["maquina"].phase, s["maquina"].target) == (1, "machine")
    assert (s["abs"].phase, s["abs"].target) == (2, "machine")
    assert (s["ask"].phase, s["ask"].target, s["ask"].user_choice) == (2, "user_profile", True)


def test_apps_by_source_and_scope() -> None:  # R9, R10, R11
    r = recipe(
        apps=[
            app("offline-machine"),
            app("winget", source="winget_online"),
            app("user-scope", scope="user"),
        ]
    )
    ph = phases(P(r))
    assert ph["app:offline-machine"] == 1
    assert ph["app:winget"] == 2
    assert ph["app:user-scope"] == 2
    w = P(r).step("app:winget")
    assert w and w.needs_network and not w.needs_pendrive


def test_dependency_in_phase2_pulls_dependent() -> None:
    r = recipe(
        apps=[
            app("base", source="winget_online"),
            app("plugin", depends_on=["base"]),
            app("plugin2", depends_on=["plugin"]),
        ]
    )
    ph = phases(P(r))
    assert ph["app:plugin"] == 2 and ph["app:plugin2"] == 2
    order = [s.ref for s in P(r).steps if s.kind == "app"]
    assert order.index("base") < order.index("plugin") < order.index("plugin2")


def test_app_order_and_dependencies_topological() -> None:
    r = recipe(apps=[app("c", order=1, depends_on=["a"]), app("a", order=50), app("b", order=10)])
    order = [s.ref for s in P(r).steps if s.kind == "app"]
    assert order == ["b", "a", "c"]
    c = P(r).step("app:c")
    assert c and c.depends_on == ("app:a",)


def test_dependency_on_unselected_app_is_dropped() -> None:
    r = recipe(apps=[app("a", depends_on=["b"]), app("b", selected=False)])
    s = P(r).step("app:a")
    assert s and s.depends_on == ()


def test_cycle_raises() -> None:
    r = recipe(apps=[app("a", depends_on=["b"]), app("b", depends_on=["a"])])
    with pytest.raises(PlanError):
        P(r)


def test_post_install_backup_follows_app() -> None:  # R13
    r = recipe(
        apps=[app("steam", restore_backups_after_install=["steam-cfg"])],
        backups=[backup("steam-cfg", "{PROGRAMFILESX86}\\Steam\\config"), backup("other")],
    )
    p = P(r)
    ids = p.ids()
    assert ids.index("app:steam") + 1 == ids.index("backup:steam-cfg")
    s = p.step("backup:steam-cfg")
    assert s and s.depends_on == ("app:steam",) and s.phase == 1


def test_post_install_backup_in_phase2_user_profile() -> None:
    r = recipe(
        apps=[app("d", scope="user", restore_backups_after_install=["d-cfg"])],
        backups=[backup("d-cfg", "{APPDATA}\\d")],
    )
    s = P(r).step("backup:d-cfg")
    assert s and s.phase == 2 and s.target == "user_profile"


def test_backups_before_apps_in_same_phase() -> None:
    r = recipe(apps=[app("a")], backups=[backup("b")])
    ids = P(r).ids()
    assert ids.index("backup:b") < ids.index("app:a")


def test_portable_app_becomes_shortcut_after_backup() -> None:  # R12
    r = recipe(
        apps=[app("port", source="portable", installer=None, portable_backup="port-dir")],
        backups=[backup("port-dir", "{ABS:D:\\Portable\\X}")],
    )
    p = P(r)
    s = p.step("shortcut:port")
    assert s and s.phase == 2 and s.depends_on == ("backup:port-dir",)
    assert p.step("app:port") is None


def test_rename_and_update_and_finalize_order() -> None:
    r = recipe()
    r.windows.computer_name_decide_at_runtime = True
    ids = P(r).phase(2)
    tail = [s.kind for s in ids][-5:]
    assert tail == [
        "rename_computer",
        "windows_update",
        "driver_report",  # R28: depois do Windows Update
        "restore_point",  # R30
        "finalize",
    ]


def test_fallback_moves_phase1_to_phase2_first() -> None:  # D-012
    r = recipe(
        drivers=[driver("n", 0)],
        backups=[backup("b")],
        apps=[app("a"), app("w", source="winget_online")],
        tweaks=[tweak("visual.dark_theme")],
    )
    p = P(r, PlanContext(os_major=11, build=26100, phase1_ran=False))
    assert p.phase(1) == []
    steps = p.phase(2)
    moved = [s for s in steps if s.moved_from_phase1]
    assert moved and steps[: len(moved)] == moved  # todas no começo
    assert all(s.target != "default_profile" for s in steps)
    assert moved[0].kind == "driver"
    assert p.step("tweak:visual.dark_theme").target == "user_profile"  # type: ignore[union-attr]


def test_power_step() -> None:
    r = recipe()
    assert P(r).step("power:settings") is None
    r.power.scheme = "high_performance"
    s = P(r).step("power:settings")
    assert s and s.phase == 1


def test_plan_is_deterministic() -> None:
    r = recipe(
        drivers=[driver("b"), driver("a")],
        apps=[app("y"), app("x")],
        backups=[backup("q"), backup("p")],
        tweaks=[tweak("visual.dark_theme")],
    )
    assert P(r) == P(r)
    assert P(r).ids() == P(r.model_copy(deep=True)).ids()


def test_phase1_group_order() -> None:
    r = recipe(
        drivers=[driver("d")],
        apps=[app("a")],
        backups=[backup("b")],
        tweaks=[tweak("visual.dark_theme")],
    )
    r.bloatware.remove = ["Microsoft.BingNews"]
    r.power.hibernate = False
    kinds = [s.kind for s in P(r).phase(1)]
    order = ["driver", "power", "bloat", "tweak", "backup", "app"]
    firsts = [kinds.index(k) for k in order]
    assert firsts == sorted(firsts)


def test_unknown_os_applies_everything() -> None:
    r = recipe()
    r.bloatware.remove = ["Microsoft.People"]
    assert P(r, PlanContext()).step("bloat:Microsoft.People") is not None
