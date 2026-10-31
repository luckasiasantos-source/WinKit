from __future__ import annotations

from pathlib import Path

import pytest

from tests.ui.conftest import wait
from winkit.platform.fakes.services import fake_services
from winkit.studio.controller import StudioController
from winkit.studio.ui.pages import DISCLAIMER
from winkit.studio.ui.window import SECTIONS, StudioWindow
from winkit.ui.widgets import Row, ToggleSwitch

pytestmark = pytest.mark.ui


@pytest.fixture
def window(qapp, tmp_path: Path) -> StudioWindow:
    old = tmp_path / "C"
    d = old / "Users" / "Samuel" / "AppData" / "Roaming" / "discord"
    d.mkdir(parents=True)
    (d / "settings.json").write_text("{}")
    pen = tmp_path / "pen"
    pen.mkdir()
    (pen / "Windows11.iso").write_bytes(b"iso")
    ctl = StudioController(services=fake_services(old_pc=old))
    ctl.open_folder(pen)
    w = StudioWindow(ctl, synchronous_tasks=True)
    w.show()
    return w


def test_every_page_renders_without_and_with_recipe(window: StudioWindow, qapp) -> None:
    for title, *_ in SECTIONS:
        window.go_to(title)
        wait(qapp, 10)
    page = window.go_to("Windows e conta")
    page.new_user.setText("Samuel")  # type: ignore[attr-defined]
    page._create()  # type: ignore[attr-defined]
    assert window.ctl.recipe is not None
    for title, *_ in SECTIONS:
        window.go_to(title)
        wait(qapp, 10)
    assert "sem receita" not in window.status.text()


def test_apps_toggle_saves_recipe(window: StudioWindow, qapp) -> None:
    window.ctl.create_recipe("Samuel", None)
    page = window.go_to("Aplicativos")
    page._collect()  # type: ignore[attr-defined]
    switches = page.findChildren(ToggleSwitch)
    assert switches
    switches[0].click()
    wait(qapp, 10)
    saved = window.ctl.root / "WinKit" / "Perfis" / "padrao" / "receita.json"
    assert '"selected": true' in saved.read_text(encoding="utf-8")


def test_build_page_builds(window: StudioWindow, qapp) -> None:
    window.ctl.create_recipe("Samuel", None)
    page = window.go_to("Revisar e construir")
    page._build()  # type: ignore[attr-defined]
    assert "Pendrive pronto" in page.result.text()  # type: ignore[attr-defined]
    page._validate()  # type: ignore[attr-defined]
    assert "Tudo certo" in page.result.text()  # type: ignore[attr-defined]


def test_tweaks_and_bloat_pages_change_recipe(window: StudioWindow, qapp) -> None:
    window.ctl.create_recipe("Samuel", None)
    tw = window.go_to("Ajustes")
    tw._set_enabled("visual.dark_theme", True)  # type: ignore[attr-defined]
    tw._set_tweak_ask("visual.dark_theme", True)  # type: ignore[attr-defined]
    bl = window.go_to("Apps pré-instalados")
    bl._toggle("Microsoft.BingNews", True)  # type: ignore[attr-defined]
    r = window.ctl.recipe
    assert r is not None
    assert any(t.id == "visual.dark_theme" and t.decide_at_runtime for t in r.tweaks)
    assert r.bloatware.remove == ["Microsoft.BingNews"]
    ex = window.go_to("Primeiro login")
    ex._set("mode", "silent")  # type: ignore[attr-defined]
    assert r.execution.mode == "silent"


def test_first_page_shows_disclaimer(window: StudioWindow, qapp) -> None:
    page = window.go_to("Pendrive")
    wait(qapp, 10)
    assert DISCLAIMER in [r.subtitle_label.text() for r in page.findChildren(Row)]
    assert "vibe-codado" in DISCLAIMER
