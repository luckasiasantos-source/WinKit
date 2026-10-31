"""Recursos do Windows (V2-08): catálogo, planejador (R19), etapa e .NET 3.5 offline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.collector.features import add_enabled_here, enabled_here
from winkit.core import layout
from winkit.core.catalog.loader import default_catalogs
from winkit.core.isos import IsoIndex, IsoIndexEntry, pick_iso
from winkit.core.planner.models import PlanContext
from winkit.core.planner.planner import plan
from winkit.platform.fakes.services import fake_services
from winkit.platform.fakes.system_tweaks import FakeFeatures, FakeIsoMounter

ALL_PARTS = {
    "Microsoft-Windows-Subsystem-Linux": False,
    "VirtualMachinePlatform": False,
    "Containers-DisposableClientVM": False,
    "NetFx3": False,
    "OpenSSH.Server~~~~0.0.1.0": False,
    "TelnetClient": True,
}


def _features(w: World) -> FakeFeatures:
    feats = w.services.features
    assert isinstance(feats, FakeFeatures)
    return feats


def _world(tmp_path: Path, *ids: str, edition: str = "pro") -> World:
    w = make_world(tmp_path)
    _features(w).known.update(ALL_PARTS)
    r = w.recipe()
    r.windows.optional_features = list(ids)
    r.windows.edition = edition  # type: ignore[assignment]
    w.save_recipe(r)
    return w


# ------------------------------------------------------------------ catálogo
def test_catalog_entries_are_consistent() -> None:
    c = default_catalogs()
    assert {"wsl", "sandbox", "netfx3", "openssh_server"} <= {f.id for f in c.features}
    for f in c.features:
        assert f.source.startswith("https://")
        if any(p.capability for p in f.parts):
            assert f.needs_network  # capacidades sempre vêm do Windows Update
    sandbox = c.feature("sandbox")
    assert sandbox is not None
    assert not sandbox.windows.allows_edition("home")
    assert sandbox.windows.allows_edition("pro")
    netfx = c.feature("netfx3")
    assert netfx is not None and netfx.offline_source == "sources/sxs"


# ------------------------------------------------------------------ planejador
def test_plan_phases_and_edition_filter(tmp_path: Path) -> None:
    w = _world(tmp_path, "wsl", "sandbox", "netfx3", "openssh_server", "nao_existe")
    r = w.recipe()
    p = plan(r, default_catalogs(), PlanContext(os_major=11, build=26100))
    by_id = {s.id: s for s in p.steps}
    assert by_id["feature:wsl"].phase == 1 and not by_id["feature:wsl"].needs_network
    netfx = by_id["feature:netfx3"]
    assert (netfx.phase, netfx.needs_pendrive, netfx.phase2_fallback) == (1, True, True)
    ssh = by_id["feature:openssh_server"]
    assert (ssh.phase, ssh.needs_network) == (2, True)  # R19
    assert any(x.ref == "nao_existe" for x in p.excluded)

    r.windows.edition = "home"
    p = plan(r, default_catalogs(), PlanContext(os_major=11, build=26100))
    assert "feature:sandbox" not in p.ids()
    assert any(x.ref == "sandbox" for x in p.excluded)


def test_pick_iso_by_build_and_language() -> None:
    index = IsoIndex(
        isos=(
            IsoIndexEntry(image="/a.iso", build=22631, architecture="amd64", languages=("pt-BR",)),
            IsoIndexEntry(image="/b.iso", build=26100, architecture="amd64", languages=("en-US",)),
            IsoIndexEntry(image="/c.iso", build=26100, architecture="amd64", languages=("pt-BR",)),
            IsoIndexEntry(image="/d.iso", build=26100, architecture="arm64", languages=("pt-BR",)),
        )
    )
    chosen = pick_iso(index, build=26100, architecture="amd64", language="pt-BR")
    assert chosen is not None and chosen.image == "/c.iso"
    chosen = pick_iso(index, build=26100, architecture="amd64", language=None)
    assert chosen is not None and chosen.image == "/b.iso"
    assert pick_iso(index, build=19045, architecture="amd64", language=None) is None
    assert pick_iso(index, build=None, architecture="amd64", language=None) is None


# ------------------------------------------------------------------ etapa
def test_features_on_before_login_and_capability_after(tmp_path: Path) -> None:
    w = _world(tmp_path, "wsl", "telnet_client", "openssh_server")
    _features(w).restart = True
    run_phase1(w.runtime())
    feats = _features(w)
    assert (
        feats.known["Microsoft-Windows-Subsystem-Linux"] and feats.known["VirtualMachinePlatform"]
    )
    assert not feats.known["OpenSSH.Server~~~~0.0.1.0"]  # Fase 2, precisa de internet
    state = StateStore(w.paths.state).load()
    assert state is not None
    assert state.step("feature:wsl").status == "done"
    assert state.step("feature:telnet_client").status == "done"  # já estava ligado
    assert state.reboot_pending
    run_phase2(w.runtime())
    assert feats.known["OpenSSH.Server~~~~0.0.1.0"]


def test_netfx3_offline_from_ventoy_iso(tmp_path: Path) -> None:
    w = _world(tmp_path, "netfx3")
    index = json.loads((w.pendrive / layout.ISOS_INDEX).read_text(encoding="utf-8"))
    assert index["isos"][0]["image"] == "/Windows11.iso" and index["isos"][0]["build"] == 26100
    mounted = tmp_path / "iso-montada"
    (mounted / "sources" / "sxs").mkdir(parents=True)
    mounter = FakeIsoMounter(roots={"Windows11.iso": mounted})
    w.services.iso = mounter
    w.env.internet = False
    run_phase1(w.runtime())
    feats = _features(w)
    assert feats.sources == [("NetFx3", mounted / "sources" / "sxs")]
    assert mounter.log == ["mount Windows11.iso", "dismount Windows11.iso"]  # sempre desmonta
    assert mounter.mounted == []


def test_netfx3_offline_from_setup_media(tmp_path: Path) -> None:
    w = _world(tmp_path, "netfx3")
    (w.pendrive / "sources" / "sxs").mkdir(parents=True)
    run_phase1(w.runtime())
    assert _features(w).sources == [("NetFx3", w.pendrive / "sources" / "sxs")]


def test_iso_is_dismounted_even_when_enabling_fails(tmp_path: Path) -> None:
    w = _world(tmp_path, "netfx3")
    mounted = tmp_path / "iso-montada"
    (mounted / "sources" / "sxs").mkdir(parents=True)
    mounter = FakeIsoMounter(roots={"Windows11.iso": mounted})
    w.services.iso = mounter

    def boom(name: str, *, enabled: bool, source: Path | None = None) -> str:
        raise RuntimeError("DISM falhou")

    _features(w).set_optional_feature = boom  # type: ignore[method-assign,assignment]
    run_phase1(w.runtime())
    assert mounter.mounted == []
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("feature:netfx3").status == "failed"


def test_netfx3_without_source_waits_for_phase2_online(tmp_path: Path) -> None:
    w = _world(tmp_path, "netfx3")
    (w.pendrive / layout.ISOS_INDEX).unlink()
    run_phase1(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None
    sst = state.step("feature:netfx3")
    assert sst.status == "pending" and sst.reason is not None
    assert sst.reason.key == "step.feature.no_offline_source"
    w.env.internet = False
    run_phase2(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("feature:netfx3").status == "pending"
    w.env.internet = True
    run_phase2(w.runtime())
    assert _features(w).sources == [("NetFx3", None)]  # pelo Windows Update
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("feature:netfx3").status == "done"


def test_capability_tweak_ops() -> None:
    from winkit.core.catalog.models import TweakOp

    op = TweakOp.model_validate({"capability_add": {"name": "OpenSSH.Client~~~~0.0.1.0"}})
    assert op.kind == "capability_add"
    with pytest.raises(ValueError):
        TweakOp.model_validate(
            {"capability_add": {"name": "x"}, "capability_remove": {"name": "x"}}
        )


# ------------------------------------------------------------------ coleta e CLI
def test_collect_enabled_here(tmp_path: Path) -> None:
    w = _world(tmp_path)
    feats = FakeFeatures(known={**ALL_PARTS, "VirtualMachinePlatform": True})
    assert enabled_here(feats, default_catalogs()) == ["vm_platform", "telnet_client"]
    r = w.recipe()
    assert add_enabled_here(feats, default_catalogs(), r) == ["vm_platform", "telnet_client"]
    assert add_enabled_here(feats, default_catalogs(), r) == []


def test_cli_features(tmp_path: Path) -> None:
    w = _world(tmp_path)
    services = fake_services(features=FakeFeatures(known={**ALL_PARTS}))
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=services, out=out.append)

    assert run("recursos", "marcar", "wsl", "netfx3") == 0
    assert w.recipe().windows.optional_features == ["wsl", "netfx3"]
    assert any("[x] wsl" in x for x in out)
    assert run("features", "deselect", "wsl") == 0
    assert w.recipe().windows.optional_features == ["netfx3"]
    assert run("recursos", "marcar", "nada") == 1
    assert run("coletar", "recursos") == 0
    assert w.recipe().windows.optional_features == ["netfx3", "telnet_client"]
