"""Valida os catálogos empacotados (PLANO.md §19.1, "Dados")."""

from __future__ import annotations

from pathlib import Path
from typing import get_args

import pytest

from winkit.core.catalog.loader import FILES, load_catalogs
from winkit.core.catalog.models import OsFilter, TweakOp
from winkit.core.errors import CatalogError
from winkit.core.paths import templates
from winkit.core.recipe.models import Edition

CAT = load_catalogs()


def test_every_tweak_has_source_and_undo() -> None:  # R-33
    for tw in CAT.tweaks:
        assert tw.source.startswith("https://"), tw.id
        assert tw.undo, tw.id


def test_tweak_ids_prefix_matches_category() -> None:
    for tw in CAT.tweaks:
        assert tw.id.split(".")[0] == tw.category, tw.id


def test_tweak_ops_hives() -> None:
    for tw in CAT.tweaks:
        for op in [*tw.apply, *tw.undo]:
            if op.reg_set and tw.scope == "machine":
                assert op.reg_set.key.upper().startswith(("SOFTWARE", "SYSTEM")), tw.id


def test_device_encryption_is_specialize_and_recommended() -> None:  # D-020
    tw = CAT.tweak("system.prevent_device_encryption")
    assert tw and tw.stage == "specialize" and tw.recommended
    assert tw.apply[0].reg_set and tw.apply[0].reg_set.value == "PreventDeviceEncryption"


def test_editions_cover_recipe_literal() -> None:
    assert {e.id for e in CAT.editions} == set(get_args(Edition))


def test_bloatware_rules() -> None:
    blocked = {b.id for b in CAT.bloatware if b.risk == "blocked"}
    assert "Microsoft.DesktopAppInstaller" in blocked  # é o winget
    assert "Microsoft.WindowsStore" in blocked
    for b in CAT.bloatware:
        assert b.family_name.startswith(b.id + "_")


def test_app_catalog_templates_parse_and_warnings_exist() -> None:
    dpapi = {d.id for d in CAT.dpapi_patterns}
    for entry in CAT.apps:
        for cp in entry.config_paths:
            templates.parse(cp.template)
            if cp.warning:
                assert cp.warning in dpapi, (entry.id, cp.warning)


def test_driver_classes() -> None:
    net = CAT.driver_class("net")
    assert net and net.priority == 0 and net.recommended
    fw = CAT.driver_class("Firmware")
    assert fw and not fw.recommended


def test_signatures_order_burn_before_inno_before_nsis() -> None:
    types = [s.type for s in CAT.installer_signatures]
    assert types.index("wix_burn") < types.index("inno") < types.index("nsis")


def test_lookup_helpers() -> None:
    assert CAT.app("discord") is not None and CAT.app("zzz") is None
    assert CAT.edition("pro") is not None


def test_os_filter() -> None:
    f = OsFilter(os=[11], min_build=22000, max_build=26200)
    assert f.applies(11, 26100)
    assert not f.applies(10, 19045)
    assert not f.applies(11, 21000)
    assert not f.applies(11, 27000)
    assert f.applies(None, None)
    assert f.applies(11, None)


def test_tweak_op_exactly_one() -> None:
    with pytest.raises(ValueError):
        TweakOp()
    with pytest.raises(ValueError):
        TweakOp.model_validate(
            {
                "reg_delete_key": {"key": "a"},
                "appx_remove": {"package": "b"},
            }
        )
    op = TweakOp.model_validate({"appx_remove": {"package": "b"}})
    assert op.kind == "appx_remove"


@pytest.mark.parametrize(
    ("op", "msg"),
    [
        ({"reg_set": {"key": "k", "value": "v", "type": "dword", "data": "x"}}, "número"),
        ({"reg_set": {"key": "k", "value": "v", "type": "multi_sz", "data": "x"}}, "lista"),
        ({"reg_set": {"key": "k", "value": "v", "type": "sz", "data": 1}}, "texto"),
        ({"powercfg": {"args": ["/delete", "x"]}}, "powercfg"),
    ],
)
def test_tweak_op_validation(op: dict[str, object], msg: str) -> None:
    with pytest.raises(ValueError, match=msg):
        TweakOp.model_validate(op)


def _copy_data(tmp: Path) -> Path:
    src = Path(__file__).resolve().parents[2] / "src" / "winkit" / "data"
    for name in FILES.values():
        (tmp / name).write_text((src / name).read_text(encoding="utf-8"), encoding="utf-8")
    return tmp


def test_loader_errors(tmp_path: Path) -> None:
    d = _copy_data(tmp_path)
    (d / "editions.yaml").write_text("- {id: pro, name: Pro, generic_key: X}\n", encoding="utf-8")
    with pytest.raises(CatalogError, match="inválido"):
        load_catalogs(d)
    (d / "editions.yaml").write_text("[: quebrado", encoding="utf-8")
    with pytest.raises(CatalogError, match="YAML"):
        load_catalogs(d)
    (d / "editions.yaml").unlink()
    with pytest.raises(CatalogError, match="ausente"):
        load_catalogs(d)


def test_loader_detects_duplicates(tmp_path: Path) -> None:
    d = _copy_data(tmp_path)
    text = (d / "editions.yaml").read_text(encoding="utf-8")
    (d / "editions.yaml").write_text(text + text.splitlines()[-1] + "\n", encoding="utf-8")
    with pytest.raises(CatalogError, match="repetidos"):
        load_catalogs(d)


def test_blocked_requires_reason(tmp_path: Path) -> None:
    d = _copy_data(tmp_path)
    (d / "bloatware.yaml").write_text("- {id: A.B, name: x, risk: blocked}\n", encoding="utf-8")
    with pytest.raises(CatalogError):
        load_catalogs(d)


def test_catalogs_roundtrip_through_dump() -> None:
    from winkit.core.catalog.models import Catalogs

    assert Catalogs.model_validate(CAT.model_dump()) == CAT
