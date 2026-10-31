"""Perfis rápidos (V2-15): catálogo, mescla idempotente, nunca desmarca, prévia sem efeito."""

from __future__ import annotations

from pathlib import Path

from tests.agent.helpers import make_world
from winkit.cli import main as cli
from winkit.core.catalog.loader import default_catalogs
from winkit.core.presets import apply_preset, missing_ids, preset_tweaks, preview_preset
from winkit.core.recipe.models import Recipe, TweakSelection
from winkit.platform.fakes.services import fake_services


def _recipe(tmp_path: Path) -> Recipe:
    return make_world(tmp_path).recipe()


def test_every_preset_id_exists_and_gaming_tweaks_are_valid() -> None:
    c = default_catalogs()
    assert {"gamer", "privacy_max", "office", "developer"} <= {p.id for p in c.presets}
    for p in c.presets:
        assert missing_ids(p, c) == [], p.id
    gaming = [tw for tw in c.tweaks if tw.category == "gaming"]
    assert len(gaming) == 5 and all(tw.undo for tw in gaming)
    hags = c.tweak("gaming.hags")
    assert hags is not None and hags.risk == "caution"


def test_apply_is_a_merge_and_idempotent(tmp_path: Path) -> None:
    c = default_catalogs()
    gamer = c.preset("gamer")
    assert gamer is not None
    r = _recipe(tmp_path)
    r.tweaks.append(TweakSelection(id="visual.dark_theme"))
    r.power.scheme = "balanced"  # escolha do usuário: o perfil não troca
    r.bloatware.remove = ["Microsoft.XboxGamingOverlay", "Microsoft.BingNews"]
    result = apply_preset(gamer, r, c)
    enabled = {s.id for s in r.tweaks if s.enabled}
    assert set(preset_tweaks(gamer, c)) <= enabled
    assert "visual.dark_theme" in enabled  # nunca desmarca
    assert r.power.scheme == "balanced"
    assert r.bloatware.remove == ["Microsoft.BingNews"]  # o Game Bar fica
    assert [w.key for w in result.warnings] == ["preset.keep_bloat"]
    assert r.presets_applied == ["gamer"]
    again = apply_preset(gamer, r, c)
    assert again.changes == [] and r.presets_applied == ["gamer"]


def test_preview_does_not_touch_the_recipe(tmp_path: Path) -> None:
    c = default_catalogs()
    privacy = c.preset("privacy_max")
    assert privacy is not None
    r = _recipe(tmp_path)
    before = r.model_dump_json()
    preview = preview_preset(privacy, r, c)
    assert r.model_dump_json() == before
    keys = {m.key for m in preview.changes}
    assert {"preset.tweak", "preset.dns", "preset.blocklist"} <= keys
    apply_preset(privacy, r, c)
    assert r.dns.provider == "quad9" and r.dns.hosts_blocklists == ["trackers_basic"]


def test_developer_and_office(tmp_path: Path) -> None:
    c = default_catalogs()
    r = _recipe(tmp_path)
    dev, office = c.preset("developer"), c.preset("office")
    assert dev is not None and office is not None
    apply_preset(dev, r, c)
    apply_preset(office, r, c)
    assert {"wsl", "openssh_client"} <= set(r.windows.optional_features)
    assert r.maintenance.winget_upgrade == "weekly" and r.maintenance.storage_sense
    assert r.presets_applied == ["developer", "office"]


def test_cli_presets(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=fake_services(), out=out.append)

    assert run("perfil-rapido", "listar") == 0
    assert any(line.strip().startswith("gamer") for line in out)
    assert run("preset", "apply", "gamer", "--simular") == 0
    assert w.recipe().presets_applied == []
    assert run("perfil-rapido", "aplicar", "gamer") == 0
    assert w.recipe().presets_applied == ["gamer"]
    assert run("perfil-rapido", "aplicar", "nada") == 1
