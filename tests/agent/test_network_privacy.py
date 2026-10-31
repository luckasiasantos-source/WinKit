"""DNS seguro e bloqueio pelo hosts (V2-16): catálogos, regras do hosts, etapas e CLI."""

from __future__ import annotations

import codecs
import ipaddress
from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.phases import run_phase1
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.core import dns as rules
from winkit.core.catalog.loader import default_catalogs
from winkit.core.planner.models import PlanContext
from winkit.core.planner.planner import plan
from winkit.core.recipe.models import Dns
from winkit.core.recipe.validation import validate_recipe
from winkit.platform.dns import DOH_POLICY_KEY, DOH_POLICY_VALUE, DOH_REQUIRE, AdapterDns
from winkit.platform.fakes.dns import FakeDns
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.services import fake_services
from winkit.platform.hosts import hosts_file, remove_block

#: Sufixos da Microsoft que nunca podem entrar numa lista (o Defender trata como sequestro).
MICROSOFT = (
    "microsoft.com",
    "windows.com",
    "windows.net",
    "windowsupdate.com",
    "msftconnecttest.com",
    "live.com",
    "msn.com",
    "bing.com",
    "office.com",
    "office.net",
    "xbox.com",
    "azure.com",
    "azureedge.net",
    "skype.com",
    "outlook.com",
    "msedge.net",
    "visualstudio.com",
    "github.com",
    "linkedin.com",
)

USER_HOSTS = b"# hosts do usuario\r\n127.0.0.1 meu-servidor.local\r\n10.0.0.2\tnas # caixa\r\n"


# ------------------------------------------------------------------ catálogos
def test_catalogs_are_safe() -> None:
    c = default_catalogs()
    assert {"cloudflare", "quad9", "google", "adguard", "nextdns"} <= {
        p.id for p in c.dns_providers
    }
    for p in c.dns_providers:
        assert p.doh_template.startswith("https://")
        for ip in [*p.ipv4, *p.ipv6]:
            ipaddress.ip_address(ip)
    for b in c.hosts_blocklists:
        assert b.source and b.license
        for d in b.domains:
            assert not any(d == s or d.endswith("." + s) for s in MICROSOFT), d


# ------------------------------------------------------------------ hosts
@pytest.mark.parametrize(
    "original",
    [
        b"",
        USER_HOSTS,
        USER_HOSTS.replace(b"\r\n", b"\n"),
        codecs.BOM_UTF8 + USER_HOSTS,
        b"127.0.0.1 caf\xe9.local",  # Latin-1 e sem quebra de linha no fim
    ],
)
def test_hosts_block_roundtrip_keeps_user_bytes(original: bytes) -> None:
    domains = ["a.example", "b.example"]
    added = rules.with_block(original, domains)
    assert added.startswith(original)
    assert rules.has_block(added, domains)
    assert not rules.has_block(added, ["outro.example"])
    again = rules.with_block(added, domains)
    assert again == added  # idempotente: troca o bloco, não duplica
    removed, had = rules.without_block(added)
    assert had
    newline = b"\r\n" if b"\r\n" in original or not original else b"\n"
    expected = original if original.endswith((b"\n", b"\r")) or not original else original + newline
    assert removed == expected
    if original.startswith(codecs.BOM_UTF8):
        assert removed.startswith(codecs.BOM_UTF8)
    if b"\r\n" in original:
        assert b"\r\n0.0.0.0 a.example\r\n" in added


def test_hosts_broken_block_is_left_alone() -> None:
    data = USER_HOSTS + b"# >>> WinKit abc\r\n0.0.0.0 x.example\r\n"  # sem o fim
    assert rules.without_block(data) == (data, False)


# ------------------------------------------------------------------ planejador e validação
def test_plan_and_validation(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    r = w.recipe()
    c = default_catalogs()
    assert not {"dns:servers", "hosts:block"} & set(plan(r, c).ids())
    r.dns = Dns(provider="quad9", hosts_blocklists=["ads_basic"])
    p = plan(r, c, PlanContext(os_major=11, build=26100))
    ids = [s.id for s in p.phase(1)]
    assert ids.index("dns:servers") < ids.index("hosts:block")  # R18
    r.dns = Dns(provider="nextdns")
    assert any("NextDNS" in e for e in validate_recipe(r, c).errors)
    r.dns = Dns(provider="custom", custom_servers=["1.1.1.1", "não-é-ip"])
    assert any("não-é-ip" in e for e in validate_recipe(r, c).errors)
    r.dns = Dns(hosts_blocklists=["nada"])
    assert any("nada" in e for e in validate_recipe(r, c).errors)
    r.dns = Dns(provider="nextdns", provider_id="abc123")
    target = rules.resolve(r.dns, c)
    assert target is not None and target.doh_template == "https://dns.nextdns.io/abc123"


# ------------------------------------------------------------------ etapas
def _world(tmp_path: Path, dns: Dns) -> World:
    w = make_world(tmp_path)
    r = w.recipe()
    r.dns = dns
    w.save_recipe(r)
    hosts = w.system / "Windows" / "System32" / "drivers" / "etc" / "hosts"
    hosts.parent.mkdir(parents=True)
    hosts.write_bytes(USER_HOSTS)
    return w


def test_dns_and_hosts_before_login(tmp_path: Path) -> None:
    w = _world(
        tmp_path, Dns(provider="cloudflare", require_doh=True, hosts_blocklists=["ads_basic"])
    )
    run_phase1(w.runtime())
    fake = w.services.dns
    assert isinstance(fake, FakeDns)
    assert all(a.ipv4 == ("1.1.1.1", "1.0.0.1") for a in fake.adapter_list)
    assert all(len(a.ipv6) == 2 for a in fake.adapter_list)
    assert set(fake.doh_servers.values()) == {"https://cloudflare-dns.com/dns-query"}
    assert all(fake.require_flags.values())
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    assert reg.get("HKLM", DOH_POLICY_KEY, DOH_POLICY_VALUE) == DOH_REQUIRE
    hosts = w.system / "Windows" / "System32" / "drivers" / "etc" / "hosts"
    data = hosts.read_bytes()
    assert data.startswith(USER_HOSTS) and b"0.0.0.0 doubleclick.net\r\n" in data
    state = StateStore(w.paths.state).load()
    assert state is not None
    assert state.step("dns:servers").status == "done"
    assert state.step("hosts:block").status == "done"


def test_windows_10_without_doh_sets_only_servers(tmp_path: Path) -> None:
    w = _world(tmp_path, Dns(provider="quad9"))
    fake = w.services.dns
    assert isinstance(fake, FakeDns)
    fake.doh_available = False
    run_phase1(w.runtime())
    assert fake.adapter_list[0].ipv4 == ("9.9.9.9", "149.112.112.112")
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("dns:servers").status == "done"
    assert state.step("dns:servers").reason is not None
    assert state.step("dns:servers").reason.key == "step.dns.done"  # type: ignore[union-attr]


def test_no_adapter_is_skipped(tmp_path: Path) -> None:
    w = _world(tmp_path, Dns(provider="google"))
    w.services.dns = FakeDns(adapter_list=[])
    run_phase1(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("dns:servers").status == "skipped"


def test_live_preview_then_already_done(tmp_path: Path) -> None:
    w = _world(tmp_path, Dns(provider="adguard", hosts_blocklists=["trackers_basic"]))
    kinds = frozenset({"dns", "hosts"})
    first = run_live(
        w.runtime(),
        LiveOptions(root=w.pendrive, simulate=True, restore_point=False, only_kinds=kinds),  # type: ignore[arg-type]
    )
    assert first.preview is not None
    assert {i.step_id: i.status for i in first.preview.items} == {
        "dns:servers": "will_change",
        "hosts:block": "will_change",
    }
    run_live(w.runtime(), LiveOptions(root=w.pendrive, restore_point=False, only_kinds=kinds))  # type: ignore[arg-type]
    again = run_live(
        w.runtime(),
        LiveOptions(root=w.pendrive, simulate=True, restore_point=False, only_kinds=kinds),  # type: ignore[arg-type]
    )
    assert again.preview is not None
    assert {i.status for i in again.preview.items} == {"already_done"}


def test_undo_removes_only_the_block(tmp_path: Path) -> None:
    hosts = hosts_file(str(tmp_path / "Windows"))
    hosts.parent.mkdir(parents=True)
    hosts.write_bytes(rules.with_block(USER_HOSTS, ["x.example"]))
    assert remove_block(hosts)
    assert hosts.read_bytes() == USER_HOSTS
    assert not remove_block(hosts)


# ------------------------------------------------------------------ CLI
def test_cli_dns(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    services = fake_services()
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=services, out=out.append)

    assert run("dns", "definir", "cloudflare", "--exigir-criptografia") == 0
    assert w.recipe().dns.provider == "cloudflare" and w.recipe().dns.require_doh
    assert run("dns", "set", "custom", "--servidores", "1.1.1.1,9.9.9.9") == 0
    assert w.recipe().dns.custom_servers == ["1.1.1.1", "9.9.9.9"]
    assert run("dns", "definir", "custom", "--servidores", "lixo") == 1
    assert w.recipe().dns.custom_servers == ["1.1.1.1", "9.9.9.9"]  # nada salvo
    assert run("dns", "bloqueios", "marcar", "ads_basic") == 0
    assert w.recipe().dns.hosts_blocklists == ["ads_basic"]
    assert any("[x] ads_basic" in x for x in out)
    assert run("dns", "blocklists", "deselect", "ads_basic") == 0
    assert w.recipe().dns.hosts_blocklists == []


def test_adapter_parsing() -> None:
    from winkit.platform.dns import parse_adapters

    rows = [
        {"Index": 4, "Name": "Wi-Fi", "IPv4": "1.1.1.1", "IPv6": None},
        {"Index": 7, "Name": "Ethernet", "IPv4": ["8.8.8.8", "8.8.4.4"], "IPv6": []},
        {"Name": "sem índice"},
    ]
    assert parse_adapters(rows) == [
        AdapterDns(4, "Wi-Fi", ("1.1.1.1",), ()),
        AdapterDns(7, "Ethernet", ("8.8.8.8", "8.8.4.4"), ()),
    ]
