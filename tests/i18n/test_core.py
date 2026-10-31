from __future__ import annotations

import pytest

from winkit.i18n import Msg, current_language, legacy, msg, render, set_language, t, tn


def test_t_formats_in_current_language() -> None:
    assert t("paths.drive_missing", drive="D:") == "A unidade D: não existe neste PC."
    set_language("en-US")
    assert t("paths.drive_missing", drive="D:") == "Drive D: does not exist on this PC."
    set_language("es")
    assert t("paths.drive_missing", drive="D:") == "La unidad D: no existe en este PC."
    assert current_language() == "es"


def test_unknown_key_raises() -> None:
    with pytest.raises(KeyError):
        t("nao.existe")


def test_plural_forms() -> None:
    assert tn("ui.count.app", 1) == "1 app instalado"
    assert tn("ui.count.app", 3) == "3 apps instalados"
    set_language("en-US")
    assert tn("ui.count.app", 1) == "1 app installed"
    assert tn("ui.count.app", 0) == "0 apps installed"


def test_t_rejects_plural_and_tn_rejects_simple() -> None:
    with pytest.raises(TypeError):
        t("ui.count.app")
    with pytest.raises(TypeError):
        tn("app.name", 2)


def test_render_msg_follows_language() -> None:
    m = msg("step.exit_code", code=1603)
    assert render(m) == "o instalador retornou o código 1603"
    set_language("es")
    assert render(m) == "el instalador devolvió el código 1603"


def test_render_tolerates_unknown_key_and_none() -> None:
    assert render(Msg(key="chave.de.outra.versao")) == "chave.de.outra.versao"
    assert render(None) == ""
    assert render("texto pronto") == "texto pronto"
    assert render(legacy("antigo")) == "antigo"


def test_msg_roundtrip_json() -> None:
    m = msg("step.timeout", minutes=30)
    assert Msg.model_validate_json(m.model_dump_json()) == m
