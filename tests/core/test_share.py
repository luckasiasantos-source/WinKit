"""Receitas compartilháveis e modelos (V2-23): proteção de dados pessoais, ida e volta, mescla."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.agent.helpers import make_world
from winkit.cli import main as cli
from winkit.core import share
from winkit.core.catalog.loader import default_catalogs
from winkit.core.recipe.models import (
    AppItem,
    BackupItem,
    BrowserConfig,
    BrowserExtension,
    Dns,
    EnvVar,
    ExtraAccount,
    NetworkDrive,
    TweakSelection,
    UserFolders,
    VolumeRef,
    WifiNetwork,
)
from winkit.platform.fakes.services import fake_services

#: Valores pessoais da receita de fixture: nenhum pode aparecer no arquivo exportado.
PERSONAL = [
    "Samuel",
    "PC-DO-SAMUEL",
    "senha-super-secreta",
    "Ana",
    "CasaWifi5G",
    "\\\\nas\\filmes",
    "JAVA_HOME",
    "D:\\meu-instalador.exe",
    "minha-pagina.example",
    "abc123nextdns",
    "1A2B3C4D",
]


def full_recipe(tmp_path: Path):  # type: ignore[no-untyped-def]
    r = make_world(tmp_path).recipe()
    r.windows.computer_name = "PC-DO-SAMUEL"
    r.windows.account.password_mode = "stored"
    r.windows.account.password = "senha-super-secreta"
    r.windows.extra_accounts = [ExtraAccount(username="Ana")]
    r.apps = [
        AppItem(id="firefox", name="Firefox", source="winget_online", winget_id="Mozilla.Firefox"),
        AppItem(id="meu", name="Meu App", source="offline", winget_id=None),
        AppItem(id="porta", name="Portátil", source="portable", portable_backup=None),
    ]
    r.apps[1].installer = None
    r.backups = [
        BackupItem(
            id="b", name="B", template=r"{APPDATA}\X", data_path="Perfis/padrao/Backups/b/dados"
        )
    ]
    r.wifi.networks = [
        WifiNetwork(id="casa", ssid="CasaWifi5G", file="Perfis/padrao/Wifi/casa.xml")
    ]
    r.network_drives = [NetworkDrive(letter="Z", remote_path="\\\\nas\\filmes")]
    r.environment.variables = [EnvVar(name="JAVA_HOME", value="D:\\meu-instalador.exe")]
    r.user_folders = UserFolders(
        enabled=True, volume=VolumeRef(serial="1A2B3C4D"), folders={"documents": "U\\D"}
    )
    r.tweaks = [TweakSelection(id="visual.dark_theme")]
    r.dns = Dns(provider="nextdns", provider_id="abc123nextdns", hosts_blocklists=["ads_basic"])
    r.browsers = [
        BrowserConfig(
            id="firefox",
            homepage="https://minha-pagina.example",
            search="duckduckgo",
            extensions=[BrowserExtension(id="addon@darkreader.org", name="Dark Reader")],
        )
    ]
    return r


def test_export_never_contains_personal_data(tmp_path: Path) -> None:
    """Teste de proteção (V2-23): conta, senha, Wi-Fi, caminhos, volumes nunca saem."""
    data = share.export_recipe(
        full_recipe(tmp_path), title="Meu setup", description="", version="0.8.0"
    )
    text = share.dumps(data)
    for value in PERSONAL:
        assert value not in text, value
    assert [a.winget_id for a in data.apps] == ["Mozilla.Firefox"]  # sem instaladores próprios
    assert data.dns_provider == "unchanged"  # o NextDNS exige id pessoal
    assert data.browsers[0].search == "duckduckgo" and "homepage" not in text


def test_personal_fields_are_rejected_on_import() -> None:
    base = json.loads(share.dumps(share.ShareableRecipe(winkit_version="1", title="x")))
    for field, value in (
        ("windows", {"account": {"username": "x"}}),
        ("wifi", {}),
        ("backups", []),
    ):
        with pytest.raises(share.ShareError):
            share.loads(json.dumps({**base, field: value}))
    with pytest.raises(share.ShareError):
        share.loads("não é json")


def test_roundtrip_and_idempotent_merge(tmp_path: Path) -> None:
    c = default_catalogs()
    exported = share.loads(
        share.dumps(
            share.export_recipe(full_recipe(tmp_path), title="t", description="", version="1")
        )
    )
    (tmp_path / "outro").mkdir()
    target = make_world(tmp_path / "outro").recipe()
    target.tweaks = [TweakSelection(id="privacy.copilot")]
    before = target.model_dump_json()
    preview = share.preview_import(exported, target, c)
    assert target.model_dump_json() == before  # a prévia não muda nada
    first = share.import_recipe(exported, target, c)
    assert {m.key for m in first.changes} >= {
        "share.app",
        "preset.tweak",
        "preset.blocklist",
        "share.browser",
    }
    assert preview.changes == first.changes
    assert {s.id for s in target.tweaks} == {
        "privacy.copilot",
        "visual.dark_theme",
    }  # nunca desmarca
    assert target.windows.account.username == "Samuel"  # a conta é sempre a sua
    second = share.import_recipe(exported, target, c)
    assert second.changes == []


def test_unknown_ids_are_ignored_with_reason(tmp_path: Path) -> None:
    data = share.ShareableRecipe(
        winkit_version="9.9",
        title="futuro",
        tweaks=["futuro.ajuste"],
        optional_features=["recurso_novo"],
        hosts_blocklists=["lista_nova"],
        bloatware=["Microsoft.WindowsStore"],
        dns_provider="nextdns",
    )
    r = make_world(tmp_path).recipe()
    res = share.import_recipe(data, r, default_catalogs())
    assert {m.key for m in res.ignored} == {
        "share.ignored_tweak",
        "share.ignored_feature",
        "share.ignored_blocklist",
        "share.ignored_bloat",
        "share.ignored_dns",
    }
    assert res.changes == []


def test_bundled_templates_are_valid(tmp_path: Path) -> None:
    c = default_catalogs()
    for template_id in share.TEMPLATE_IDS:
        data = share.load_template(template_id)
        (tmp_path / template_id).mkdir()
        r = make_world(tmp_path / template_id).recipe()
        res = share.import_recipe(data, r, c)
        assert res.ignored == [], template_id
        assert res.changes, template_id


def test_cli_share(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=fake_services(), out=out.append)

    assert run("receita", "modelo") == 0
    assert any("programador" in line for line in out)
    assert run("receita", "modelo", "gamer") == 0  # só prévia
    assert w.recipe().apps == []
    assert run("recipe", "template", "gamer", "--aplicar") == 0
    assert {a.winget_id for a in w.recipe().apps} == {
        "Valve.Steam",
        "EpicGames.EpicGamesLauncher",
        "Discord.Discord",
    }
    path = tmp_path / "meu.winkit.json"
    assert run("receita", "exportar", str(path), "--titulo", "Meu") == 0
    assert "Samuel" not in path.read_text(encoding="utf-8")
    assert run("receita", "importar", str(path), "--aplicar") == 0
    (tmp_path / "ruim.winkit.json").write_text('{"x": 1}', encoding="utf-8")
    assert run("receita", "importar", str(tmp_path / "ruim.winkit.json")) == 1
