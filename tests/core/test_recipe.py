from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from tests.factories import FIXED_NOW, app, backup, recipe
from winkit.core.errors import RecipeError
from winkit.core.recipe import io
from winkit.core.recipe.io import dump_recipe, load_recipe, recipe_hash
from winkit.core.recipe.models import Recipe


def test_defaults_match_the_plan() -> None:
    r = recipe()
    assert r.schema_version == 1
    assert r.execution.mode == "countdown"
    assert r.execution.countdown_seconds == 30
    assert r.windows.prevent_device_encryption is True  # D-020
    assert r.windows.account.password_mode == "empty"
    assert r.windows.target_os == [11]
    assert r.windows.input_locale == "0416:00010416"
    assert r.updates.block_wu_driver_replacement is True
    assert r.bloatware.block_reinstall is True
    assert r.meta.profile_id == "padrao"


def test_roundtrip_is_lossless() -> None:
    r = recipe(apps=[app("7zip")], backups=[backup("discord", "{APPDATA}\\discord")])
    text = dump_recipe(r)
    assert load_recipe(text) == r
    assert '"class"' not in text  # sem drivers
    assert text.endswith("\n")


def test_driver_class_alias_roundtrip() -> None:
    from tests.factories import driver

    r = recipe(drivers=[driver("net1")])
    text = dump_recipe(r)
    assert '"class": "Net"' in text
    assert load_recipe(text).drivers[0].class_name == "Net"


def test_unknown_fields_are_rejected() -> None:
    data = json.loads(dump_recipe(recipe()))
    data["windows"]["typo_field"] = 1
    with pytest.raises(RecipeError, match="typo_field"):
        io.recipe_from_dict(data)


def test_invalid_json_and_non_object() -> None:
    with pytest.raises(RecipeError):
        load_recipe("{nao json")
    with pytest.raises(RecipeError):
        load_recipe("[]")


def test_future_schema_version_is_refused() -> None:
    data = json.loads(dump_recipe(recipe()))
    data["schema_version"] = 99
    with pytest.raises(RecipeError, match="mais nova"):
        io.recipe_from_dict(data)


def test_invalid_schema_version() -> None:
    with pytest.raises(RecipeError):
        io.migrate({"schema_version": 0})


def test_migration_chain_is_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(io, "SCHEMA_VERSION", 2)
    monkeypatch.setitem(io.MIGRATIONS, 1, lambda d: {**d, "migrated": True})
    out = io.migrate({"schema_version": 1})
    assert out == {"schema_version": 2, "migrated": True}


def test_hash_ignores_updated_at_but_not_content() -> None:
    a = recipe()
    b = recipe()
    b.meta.updated_at = FIXED_NOW.replace(year=2030)
    assert recipe_hash(a) == recipe_hash(b)
    b.execution.mode = "silent"
    assert recipe_hash(a) != recipe_hash(b)


def test_item_id_pattern() -> None:
    with pytest.raises(ValidationError):
        app("Com Espaço")
    with pytest.raises(ValidationError):
        app("../fuga")


def test_queries() -> None:
    r = recipe(
        apps=[app("a"), app("b", selected=False)],
        backups=[backup("x"), backup("y", selected=False)],
    )
    assert [a.id for a in r.selected_apps()] == ["a"]
    assert [b.id for b in r.selected_backups()] == ["x"]
    assert r.app("b") is not None and r.app("zzz") is None
    assert r.backup("y") is not None and r.backup("zzz") is None


def test_assignment_is_validated() -> None:
    r = recipe()
    with pytest.raises(ValidationError):
        r.execution.mode = "barulhento"  # type: ignore[assignment]


def test_password_is_not_in_repr() -> None:
    r = recipe()
    r.windows.account.password = "segredo"
    assert "segredo" not in repr(r.windows.account)


def test_model_is_the_public_type() -> None:
    assert isinstance(recipe(), Recipe)
