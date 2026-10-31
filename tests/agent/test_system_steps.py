from __future__ import annotations

from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from tests.factories import tweak
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.progress import Choice
from winkit.agent.store import StateStore
from winkit.core.catalog.loader import default_catalogs
from winkit.core.state.models import AgentState
from winkit.platform.appx import DEPROVISIONED
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.runner import FakeRunner, result
from winkit.platform.fakes.system_tweaks import FakeAppx, FakeFeatures

CAT = default_catalogs()
ADV = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"


def state(w: World) -> AgentState:
    s = StateStore(w.paths.state).load()
    assert s is not None
    return s


def reg(w: World) -> FakeRegistry:
    r = w.services.registry
    assert isinstance(r, FakeRegistry)
    return r


@pytest.fixture
def world(tmp_path: Path) -> World:
    return make_world(tmp_path)


def test_user_tweak_goes_to_default_hive_in_phase1(world: World) -> None:
    r = world.recipe()
    r.tweaks = [tweak("visual.show_extensions"), tweak("privacy.activity_history")]
    world.save_recipe(r)
    run_phase1(world.runtime())
    rg = reg(world)
    assert rg.get("HKU", rf"WinKitDefault\{ADV}", "HideFileExt") == 0
    assert rg.get("HKCU", ADV, "HideFileExt") is None
    assert rg.mounted == {}  # o hive foi desmontado (R-17)
    assert rg.get("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System", "EnableActivityFeed") == 0
    assert state(world).step("tweak:visual.show_extensions").status == "done"


def test_consumer_content_mixes_hklm_and_default(world: World) -> None:
    run_phase1(world.runtime())
    rg = reg(world)
    assert (
        rg.get(
            "HKLM",
            r"SOFTWARE\Policies\Microsoft\Windows\CloudContent",
            "DisableWindowsConsumerFeatures",
        )
        == 1
    )
    assert (
        rg.get(
            "HKU",
            r"WinKitDefault\Software\Microsoft\Windows\CurrentVersion"
            r"\ContentDeliveryManager",
            "SilentInstalledAppsEnabled",
        )
        == 0
    )
    assert (
        rg.get(
            "HKLM",
            r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate",
            "ExcludeWUDriversInQualityUpdate",
        )
        == 1
    )


def test_decide_at_runtime_tweak_goes_to_hkcu(world: World) -> None:
    r = world.recipe()
    r.tweaks = [tweak("visual.dark_theme", decide_at_runtime=True)]
    world.save_recipe(r)
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    assert (
        reg(world).get(
            "HKCU",
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            "AppsUseLightTheme",
        )
        == 0
    )


def test_already_applied_is_checked(world: World) -> None:
    rg = reg(world)
    rg.set(
        "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", "dword", 1
    )
    r = world.recipe()
    r.tweaks = [tweak("privacy.telemetry_minimum")]
    world.save_recipe(r)
    run_phase1(world.runtime())
    assert state(world).step("tweak:privacy.telemetry_minimum").reason == "já estava feito"


def test_optional_feature_and_failure(world: World) -> None:
    feats = world.services.features
    assert isinstance(feats, FakeFeatures)
    feats.states["Recall"] = True
    feats.restart = True
    r = world.recipe()
    r.tweaks = [tweak("privacy.recall"), tweak("visual.dark_theme")]
    world.save_recipe(r)
    reg(world).fail_on.add("Themes")
    run_phase1(world.runtime())
    s = state(world)
    assert feats.states["Recall"] is False
    assert s.step("tweak:privacy.recall").reboot_required
    assert s.step("tweak:visual.dark_theme").status == "failed"
    assert reg(world).mounted == {}  # desmontado mesmo com erro


def test_bloat_removed_and_deprovisioned(world: World) -> None:
    appx = world.services.appx
    assert isinstance(appx, FakeAppx)
    appx.present = {"Microsoft.BingNews"}
    appx.families = {"Microsoft.BingNews": "Microsoft.BingNews_8wekyb3d8bbwe"}
    r = world.recipe()
    r.bloatware.remove = ["Microsoft.BingNews", "Clipchamp.Clipchamp"]
    world.save_recipe(r)
    run_phase1(world.runtime())
    rg = reg(world)
    assert rg.key_exists("HKLM", rf"{DEPROVISIONED}\Microsoft.BingNews_8wekyb3d8bbwe")
    assert rg.key_exists("HKLM", rf"{DEPROVISIONED}\Clipchamp.Clipchamp_yxz26nhyzhsrt")
    s = state(world)
    assert s.step("bloat:Clipchamp.Clipchamp").reason == "já estava feito" or "não estava" in (
        s.step("bloat:Clipchamp.Clipchamp").reason or ""
    )
    assert "removido" in (s.step("bloat:Microsoft.BingNews").reason or "")


def test_bloat_without_block_reinstall(world: World) -> None:
    r = world.recipe()
    r.bloatware.remove = ["Microsoft.BingNews"]
    r.bloatware.block_reinstall = False
    world.save_recipe(r)
    run_phase1(world.runtime())
    assert not reg(world).key_exists("HKLM", DEPROVISIONED)


def test_power_with_hidden_scheme(world: World) -> None:
    runner = (
        FakeRunner()
        .when(
            lambda a: a[-2:] == ("/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"),
            result(exit_code=1),
        )
        .when(
            lambda a: a[-2:] == ("/setactive", "6f9c2f0a-3e1b-4a4e-9d55-8f2d1c7b5a01"),
            lambda a: result(
                exit_code=0 if any("/duplicatescheme" in c.args for c in runner.calls) else 1
            ),
        )
    )
    world.services.runner = runner
    r = world.recipe()
    r.power.scheme = "high_performance"
    r.power.hibernate = False
    r.power.fast_startup = False
    world.save_recipe(r)
    run_phase1(world.runtime())
    assert state(world).step("power:settings").status == "done"
    calls = [c.args[1:] for c in runner.calls if c.args[0].lower().endswith("powercfg.exe")]
    assert (
        "/duplicatescheme",
        "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "6f9c2f0a-3e1b-4a4e-9d55-8f2d1c7b5a01",
    ) in calls
    assert ("/hibernate", "off") in calls
    assert (
        reg(world).get(
            "HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Power", "HiberbootEnabled"
        )
        == 0
    )


def test_power_failure(world: World) -> None:
    world.services.runner = FakeRunner().when_contains("powercfg", result(exit_code=1))
    r = world.recipe()
    r.power.scheme = "balanced"
    world.save_recipe(r)
    run_phase1(world.runtime())
    assert "balanced" in (state(world).step("power:settings").error or "")


def test_rename_computer_decided_at_runtime(world: World) -> None:
    r = world.recipe()
    r.windows.computer_name_decide_at_runtime = True
    world.save_recipe(r)
    world.ui.choice = Choice("start", computer_name="PC-NOVO")
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    feats = world.services.features
    assert isinstance(feats, FakeFeatures) and feats.renamed_to == "PC-NOVO"
    s = state(world)
    assert s.step("rename_computer:computer").reboot_required


def test_rename_invalid_name(world: World) -> None:
    r = world.recipe()
    r.windows.computer_name_decide_at_runtime = True
    world.save_recipe(r)
    world.ui.choice = Choice("start", computer_name="nome inválido!")
    run_phase1(world.runtime())
    run_phase2(world.runtime())
    assert state(world).step("rename_computer:computer").status == "failed"


@pytest.mark.parametrize("target", ["machine", "default_profile", "user_profile"])
def test_every_catalog_tweak_applies_cleanly(world: World, target: str) -> None:
    """Teste de dados: todo ajuste do catálogo executa sem erro em qualquer alvo válido."""
    from winkit.agent.eventlog import EventLog
    from winkit.agent.phases import open_session
    from winkit.agent.steps.base import StepContext
    from winkit.agent.steps.tweak import TweakStep

    feats = world.services.features
    assert isinstance(feats, FakeFeatures)
    feats.states["Recall"] = True
    rt = world.runtime()
    s = open_session(rt, EventLog(rt.paths.logs, rt.clock), phase=1)
    assert s is not None
    base = s.plan.steps[0]
    for tw in CAT.tweaks:
        if tw.stage != "agent":
            continue
        if tw.scope == "machine" and target != "machine":
            continue
        if tw.scope == "user" and target == "machine":
            continue
        step = base.model_copy(
            update={"id": f"tweak:{tw.id}", "kind": "tweak", "ref": tw.id, "target": target}
        )
        ctx = StepContext(
            step=step,
            plan=s.plan,
            state=s.state,
            recipe=s.recipe,
            catalogs=CAT,
            services=world.services,
            paths=world.paths,
            log=s.log,
            ui=world.ui,
            pendrive=world.pendrive,
            phase=1,
            clock=rt.clock,
        )
        res = TweakStep().run(ctx)
        assert res.outcome == "done", (tw.id, target, res.message)
    assert reg(world).mounted == {}
