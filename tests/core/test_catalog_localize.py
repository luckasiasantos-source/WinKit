"""Catálogos traduzidos: completos, sem órfãos e válidos (D-030, R-51)."""

from __future__ import annotations

import pytest

from winkit.core.catalog.loader import (
    TRANSLATION_FILES,
    catalogs_for,
    default_catalogs,
    load_catalogs,
    load_translation,
)
from winkit.core.catalog.localize import missing_translations, orphan_translations
from winkit.i18n import set_language

BASE = load_catalogs()


@pytest.mark.parametrize("lang", sorted(TRANSLATION_FILES))
def test_translation_is_complete_and_has_no_orphans(lang: str) -> None:
    tr = load_translation(lang)
    assert missing_translations(BASE, tr) == []
    assert orphan_translations(BASE, tr) == []


@pytest.mark.parametrize("lang", sorted(TRANSLATION_FILES))
def test_translated_catalogs_keep_ids_and_rules(lang: str) -> None:
    c = catalogs_for(lang)  # type: ignore[arg-type]
    assert [t.id for t in c.tweaks] == [t.id for t in BASE.tweaks]
    assert [t.apply for t in c.tweaks] == [t.apply for t in BASE.tweaks]
    assert [b.risk for b in c.bloatware] == [b.risk for b in BASE.bloatware]
    # todo item "cuidado" continua com efeito colateral e todo bloqueado com motivo
    assert all(b.side_effect for b in c.bloatware if b.risk == "caution")
    assert all(b.reason for b in c.bloatware if b.risk == "blocked")


def test_default_catalogs_follow_the_language() -> None:
    assert default_catalogs().tweak("visual.dark_theme").title == "Tema escuro"  # type: ignore[union-attr]
    set_language("en-US")
    assert default_catalogs().tweak("visual.dark_theme").title == "Dark theme"  # type: ignore[union-attr]
    assert default_catalogs().bloat("Microsoft.BingNews").name == "News"  # type: ignore[union-attr]
    set_language("es")
    assert default_catalogs().driver_class("Net").label == "Red (Ethernet/Wi-Fi)"  # type: ignore[union-attr]
