"""O Agente fala o idioma da receita; em ``auto``, o do Windows novo (D-030)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from winkit.agent.phases import run_phase1, run_phase2
from winkit.core.recipe.io import dump_recipe, load_recipe
from winkit.i18n import current_language


@pytest.fixture
def world(tmp_path: Path) -> World:
    return make_world(tmp_path)


def _set_language(world: World, value: str) -> None:
    for path in (
        world.paths.recipe,
        world.pendrive / "WinKit" / "Perfis" / "padrao" / "receita.json",
    ):
        if path.is_file():
            recipe = load_recipe(path.read_text(encoding="utf-8"))
            recipe.execution.language = value  # type: ignore[assignment]
            path.write_text(dump_recipe(recipe), encoding="utf-8")


def test_auto_follows_new_windows_language(world: World) -> None:
    assert run_phase1(world.runtime(detect_language=lambda: "en-GB")) == 0
    assert current_language() == "en-US"
    assert run_phase2(world.runtime(detect_language=lambda: "en-GB")) == 0
    html = world.paths.summary_html.read_text(encoding="utf-8")
    assert 'lang="en-US"' in html and "WinKit summary" in html


def test_explicit_language_wins_over_windows(world: World) -> None:
    _set_language(world, "es")
    assert run_phase1(world.runtime(detect_language=lambda: "pt-BR")) == 0
    assert run_phase2(world.runtime(detect_language=lambda: "pt-BR")) == 0
    html = world.paths.summary_html.read_text(encoding="utf-8")
    assert 'lang="es"' in html and "Resumen de WinKit" in html
