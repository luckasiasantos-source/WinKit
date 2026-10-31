"""Wi-Fi (V2-02): leitura dos perfis, coleta, etapa e senha fora dos logs (D-036, R-53)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.collector.wifi import collect_wifi, set_include_key
from winkit.core import layout
from winkit.core.wifi import key_material, parse_profile, strip_key
from winkit.platform.fakes.services import fake_services
from winkit.platform.fakes.wifi import FakeWifi

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "wifi"
SECRET = "senha-de-teste-123"


def test_parse_profiles() -> None:
    casa = parse_profile((FIX / "casa_wpa2_doc.xml").read_bytes())
    assert (casa.name, casa.ssid, casa.security, casa.has_key) == (
        "Casa 5G",
        "Casa 5G",
        "wpa2_personal",
        True,
    )
    cafe = parse_profile((FIX / "cafe_aberta_doc.xml").read_bytes())
    assert (cafe.ssid, cafe.security, cafe.has_key) == ("Café", "open", False)  # SSID em hex
    assert parse_profile((FIX / "empresa_eap_doc.xml").read_bytes()).security == "enterprise"
    with pytest.raises(ValueError):
        parse_profile(b"<?xml version='1.0'?><outra/>")


def test_strip_key_keeps_the_rest() -> None:
    data = (FIX / "casa_wpa2_doc.xml").read_bytes()
    stripped = strip_key(data)
    assert key_material(stripped) is None and SECRET.encode() not in stripped
    assert parse_profile(stripped).name == "Casa 5G"


def _world_with_wifi(tmp_path: Path) -> World:
    w = make_world(tmp_path)
    exportable = [
        FIX / "casa_wpa2_doc.xml",
        FIX / "cafe_aberta_doc.xml",
        FIX / "empresa_eap_doc.xml",
    ]
    r = w.recipe()
    added = collect_wifi(FakeWifi(exportable=exportable), w.pendrive, r)
    assert {n.security for n in added} == {"wpa2_personal", "open", "enterprise"}
    assert [n.selected for n in added if n.security == "enterprise"] == [False]
    w.save_recipe(r)
    return w


def test_collect_and_install_before_login(tmp_path: Path) -> None:
    w = _world_with_wifi(tmp_path)
    assert run_phase1(w.runtime()) == 0
    wifi = w.services.wifi
    assert isinstance(wifi, FakeWifi)
    assert set(wifi.installed) == {"Casa 5G", "Cafe"}  # a corporativa nunca entra no plano
    state = StateStore(w.paths.state).load()
    assert state is not None
    ids = [k for k in state.steps if k.startswith("wifi:")]
    assert len(ids) == 2 and all(state.step(i).phase_ran == 1 for i in ids)
    assert not any((w.paths.base / "tmp" / "wifi").glob("*"))  # cópia com senha apagada


def test_wifi_password_never_logged(tmp_path: Path) -> None:
    """Teste de proteção (R-53): a senha da fixture não aparece em log, estado nem resumo."""
    w = _world_with_wifi(tmp_path)
    run_phase1(w.runtime())
    run_phase2(w.runtime())
    places = [w.paths.base, w.pendrive / "WinKit" / "Logs"]
    for base in places:
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in (".log", ".jsonl", ".json", ".html"):
                assert SECRET not in path.read_text(encoding="utf-8", errors="ignore"), path


def test_without_key_and_no_adapter(tmp_path: Path) -> None:
    w = _world_with_wifi(tmp_path)
    r = w.recipe()
    casa = next(n for n in r.wifi.networks if n.ssid == "Casa 5G")
    assert set_include_key(w.pendrive, r, casa.id, include=False)
    assert SECRET.encode() not in layout.payload(w.pendrive, casa.file).read_bytes()
    assert not set_include_key(w.pendrive, r, casa.id, include=True)  # precisa ler de novo
    w.save_recipe(r)
    wifi = w.services.wifi
    assert isinstance(wifi, FakeWifi)
    wifi.wlan = False
    run_phase1(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step(f"wifi:{casa.id}").status == "skipped"


def test_cli_collect_and_list(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    services = fake_services(wifi=FakeWifi(exportable=[FIX / "casa_wpa2_doc.xml"]))
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]
    assert cli.main(["coletar", "wifi", *raiz], services=services, out=out.append) == 0
    assert any("Casa 5G" in line and "com senha" in line for line in out)
    nid = w.recipe().wifi.networks[0].id
    out.clear()
    assert (
        cli.main(["wifi", "marcar", nid, "--sem-senha", *raiz], services=services, out=out.append)
        == 0
    )
    assert any("sem senha" in line for line in out)


def test_strip_key_does_not_change_other_xml() -> None:
    """IN-015: tirar a senha não pode alterar o XML gerado depois (registro global do ET)."""
    from tests.factories import recipe
    from winkit.core.catalog.loader import default_catalogs
    from winkit.core.unattend.generator import UnattendTarget, generate_unattend

    def xml() -> bytes:
        return generate_unattend(
            recipe(),
            default_catalogs(),
            UnattendTarget("pt-BR", "amd64", None),
            pendrive_id="x" * 8,
        )

    before = xml()
    strip_key((FIX / "casa_wpa2_doc.xml").read_bytes())
    assert xml() == before
    assert b"ns0:" not in xml()
