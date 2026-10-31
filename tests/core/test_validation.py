from __future__ import annotations

import pytest

from tests.factories import app, backup, driver, recipe, tweak
from winkit.core.catalog.loader import default_catalogs
from winkit.core.errors import RecipeValidationError
from winkit.core.recipe.models import InstallerSpec
from winkit.core.recipe.validation import (
    ensure_valid,
    find_cycle,
    payload_path_problem,
    username_problem,
    validate_computer_name,
    validate_recipe,
)

CAT = default_catalogs()


def errors(r: object) -> list[str]:
    return validate_recipe(r, CAT).errors  # type: ignore[arg-type]


def test_default_recipe_is_valid() -> None:
    report = ensure_valid(recipe(), CAT)
    assert report.ok and report.warnings == []


@pytest.mark.parametrize(
    ("name", "ok"),
    [
        ("PC-SAMUEL", True),
        ("A", True),
        ("123456", False),
        ("x" * 16, False),
        ("PC SAM", False),
        ("PC_SAM", False),
        ("pc-1", True),
        ("", False),
    ],
)
def test_computer_name(name: str, ok: bool) -> None:
    assert validate_computer_name(name) is ok


def test_invalid_computer_name_is_error() -> None:
    r = recipe()
    r.windows.computer_name = "nome com espaço"
    assert any("Nome de computador" in e for e in errors(r))


@pytest.mark.parametrize(
    ("name", "bad"),
    [
        ("Samuel", False),
        ("Administrator", True),
        ("administrador", True),
        ("Guest", True),
        ("a/b", True),
        ("a@b", True),
        (" lead", True),
        ("dot.", True),
        ("Lucas Santos", False),
    ],
)
def test_username(name: str, bad: bool) -> None:
    assert (username_problem(name) is not None) is bad


def test_stored_password_requires_value_and_warns() -> None:
    r = recipe()
    r.windows.account.password_mode = "stored"
    report = validate_recipe(r, CAT)
    assert any("senha" in e for e in report.errors)
    assert any("legível" in w for w in report.warnings)
    r.windows.account.password = "x"
    report = validate_recipe(r, CAT)
    assert report.ok and report.warnings


@pytest.mark.parametrize(
    ("path", "ok"),
    [
        ("Apps/7zip/1.0/setup.exe", True),
        ("Drivers/Net/x", True),
        ("Perfis/padrao/Backups/a/dados", True),
        ("Perfis/outro/Backups/a/dados", False),
        ("Apps\\7zip\\setup.exe", False),
        ("/Apps/x", False),
        ("C:/Apps/x", False),
        ("Apps/../ventoy/ventoy.json", False),
        ("Apps//x", False),
        ("ventoy/ventoy.json", False),
    ],
)
def test_payload_paths(path: str, ok: bool) -> None:
    assert (payload_path_problem(path, "padrao") is None) is ok


def test_bad_payload_path_is_error() -> None:
    r = recipe(apps=[app("x", installer=InstallerSpec(path="../fora.exe", type="nsis"))])
    assert any("app x" in e for e in errors(r))


def test_duplicate_ids() -> None:
    r = recipe(apps=[app("a"), app("a")], drivers=[driver("d"), driver("d")])
    errs = errors(r)
    assert any("apps" in e for e in errs) and any("drivers" in e for e in errs)


def test_dependencies() -> None:
    r = recipe(apps=[app("a", depends_on=["zz"])])
    assert any("zz" in e for e in errors(r))
    r = recipe(apps=[app("a", depends_on=["b"]), app("b", depends_on=["a"])])
    assert any("ciclo" in e for e in errors(r))


def test_find_cycle() -> None:
    assert find_cycle({"a": ["b"], "b": []}) is None
    cycle = find_cycle({"a": ["b"], "b": ["c"], "c": ["a"]})
    assert cycle is not None and set(cycle) == {"a", "b", "c"}
    assert find_cycle({"a": ["a"]}) == ["a"]
    assert find_cycle({"a": ["fora"]}) is None


def test_post_install_backup_must_exist() -> None:
    r = recipe(apps=[app("a", restore_backups_after_install=["nope"])])
    assert any("nope" in e for e in errors(r))


def test_app_source_requirements() -> None:
    assert any("instalador" in e for e in errors(recipe(apps=[app("a", installer=None)])))
    r = recipe(apps=[app("a", installer=InstallerSpec(path="Apps/a/s.exe", type="unknown"))])
    assert any("desconhecido" in e for e in errors(r))
    r = recipe(apps=[app("a", source="winget_online", winget_id=None)])
    assert any("winget_id" in e for e in errors(r))
    r = recipe(apps=[app("a", source="portable", installer=None)])
    assert any("portátil" in e for e in errors(r))
    r = recipe(
        apps=[app("a", source="portable", installer=None, portable_backup="pa")],
        backups=[backup("pa", "{ABS:D:\\Apps\\A}")],
    )
    assert errors(r) == []


def test_msstore_offline_warns() -> None:
    r = recipe(apps=[app("a", winget_source="msstore")])
    assert any("Store" in w for w in validate_recipe(r, CAT).warnings)


def test_backup_template_and_related_app() -> None:
    r = recipe(backups=[backup("b", "{NAOEXISTE}\\x", related_app="fantasma")])
    report = validate_recipe(r, CAT)
    assert any("desconhecida" in e for e in report.errors)
    assert any("fantasma" in w for w in report.warnings)


def test_catalog_references() -> None:
    r = recipe(tweaks=[tweak("visual.nao_existe")])
    r.bloatware.remove = ["Microsoft.WindowsStore", "Pacote.Inexistente", "Microsoft.BingNews"]
    errs = errors(r)
    assert any("visual.nao_existe" in e for e in errs)
    assert any("Microsoft.WindowsStore" in e and "Store" in e for e in errs)
    assert any("Pacote.Inexistente" in e for e in errs)
    assert not any("BingNews" in e for e in errs)


def test_unknown_edition_without_catalog_is_not_checked() -> None:
    assert validate_recipe(recipe(), None).ok


def test_silent_mode_warns_about_decide_at_runtime() -> None:
    r = recipe(
        apps=[app("a", decide_at_runtime=True)],
        tweaks=[tweak("visual.dark_theme", decide_at_runtime=True)],
    )
    r.execution.mode = "silent"
    r.windows.computer_name_decide_at_runtime = True
    report = validate_recipe(r, CAT)
    assert report.ok
    assert any("visual.dark_theme" in w and "computer_name" in w for w in report.warnings)


def test_ensure_valid_raises_with_all_problems() -> None:
    r = recipe(apps=[app("a", installer=None)])
    r.windows.computer_name = "!!"
    with pytest.raises(RecipeValidationError) as exc:
        ensure_valid(r, CAT)
    assert len(exc.value.problems) == 2


def test_unselected_apps_do_not_need_installer() -> None:  # IN-006
    r = recipe(
        apps=[
            app("a", installer=None, selected=False),
            app("w", source="winget_online", winget_id=None, selected=False),
        ]
    )
    assert errors(r) == []
