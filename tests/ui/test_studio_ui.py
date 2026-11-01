from __future__ import annotations

from pathlib import Path

import pytest

from tests.ui.conftest import wait
from winkit.i18n import SUPPORTED, current_language, t
from winkit.platform.fakes.services import fake_services
from winkit.studio import preferences
from winkit.studio.controller import StudioController
from winkit.studio.ui.window import GROUPS, StudioWindow, all_sections
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
    w = StudioWindow(
        ctl,
        synchronous_tasks=True,
        prefs_path=tmp_path / "studio.json",
        detect_language=lambda: "es-MX",
    )
    w.show()
    return w


def _visit_all(window: StudioWindow, qapp) -> None:  # type: ignore[no-untyped-def]
    for s in all_sections():
        window.go_to(s.id)
        wait(qapp, 5)
        assert window.current_section() == s.id


def test_every_page_renders_without_and_with_recipe(window: StudioWindow, qapp) -> None:
    _visit_all(window, qapp)
    page = window.go_to("account")
    page.new_user.setText("Samuel")  # type: ignore[attr-defined]
    page._create()  # type: ignore[attr-defined]
    assert window.ctl.recipe is not None
    _visit_all(window, qapp)
    assert t("studio.status.no_recipe") not in window.status.text()


@pytest.mark.parametrize("lang", SUPPORTED)
def test_every_page_renders_in_every_language(window: StudioWindow, qapp, lang: str) -> None:
    window.ctl.create_recipe("Samuel", None)
    window.apply_preferences(preferences.Preferences(language=lang))  # type: ignore[arg-type]
    assert current_language() == lang
    _visit_all(window, qapp)
    assert window.windowTitle() == "WinKit Studio"
    page = window.go_to("apps")
    assert any(
        t("studio.apps.read") == b.text() for b in page.findChildren(type(window.prefs_button))
    )


def test_auto_language_follows_windows(window: StudioWindow, qapp) -> None:
    window.apply_preferences(preferences.Preferences(language="auto"))
    assert current_language() == "es"  # detect_language devolve es-MX
    page = window.go_to("pendrive")
    assert "Memoria USB" in [lbl.text() for lbl in page.findChildren(type(window.status))]


def test_language_switch_keeps_current_section(window: StudioWindow, qapp) -> None:
    window.go_to("tweaks")
    window.apply_preferences(preferences.Preferences(language="en-US"))
    assert window.current_section() == "tweaks"
    titles = [window.nav.item(i).text() for i in range(window.nav.count())]
    assert "Tweaks" in titles and "PREPARE" in titles


def test_search_filters_sections_and_headers(window: StudioWindow, qapp) -> None:
    window.search.setText("bitlocker")  # palavra-chave da seção "Windows e conta"
    visible = [
        window.nav.item(i).text()
        for i in range(window.nav.count())
        if not window.nav.item(i).isHidden()
    ]
    assert visible == [GROUPS[0].title.upper(), t("studio.account.title")]
    window.search.setText("")
    assert all(not window.nav.item(i).isHidden() for i in range(window.nav.count()))


def test_preferences_are_saved(tmp_path: Path) -> None:
    path = tmp_path / "p.json"
    assert preferences.load(path) == preferences.Preferences()
    preferences.save(preferences.Preferences(language="en-US", theme="dark"), path)
    assert preferences.load(path).language == "en-US"
    path.write_text("{lixo", encoding="utf-8")
    assert preferences.load(path) == preferences.Preferences()


def test_apps_toggle_saves_recipe(window: StudioWindow, qapp) -> None:
    window.ctl.create_recipe("Samuel", None)
    page = window.go_to("apps")
    page._collect()  # type: ignore[attr-defined]
    switches = page.findChildren(ToggleSwitch)
    assert switches
    switches[0].click()
    wait(qapp, 10)
    saved = window.ctl.root / "WinKit" / "Perfis" / "padrao" / "receita.json"
    assert '"selected": true' in saved.read_text(encoding="utf-8")


def test_build_page_builds(window: StudioWindow, qapp) -> None:
    window.ctl.create_recipe("Samuel", None)
    page = window.go_to("build")
    page._build()  # type: ignore[attr-defined]
    assert "Pendrive pronto" in page.result.text()  # type: ignore[attr-defined]
    page._validate()  # type: ignore[attr-defined]
    assert "Tudo certo" in page.result.text()  # type: ignore[attr-defined]


def test_tweaks_and_bloat_pages_change_recipe(window: StudioWindow, qapp) -> None:
    window.ctl.create_recipe("Samuel", None)
    tw = window.go_to("tweaks")
    tw._set_enabled("visual.dark_theme", True)  # type: ignore[attr-defined]
    tw._set_tweak_ask("visual.dark_theme", True)  # type: ignore[attr-defined]
    bl = window.go_to("bloat")
    bl._toggle("Microsoft.BingNews", True)  # type: ignore[attr-defined]
    r = window.ctl.recipe
    assert r is not None
    assert any(x.id == "visual.dark_theme" and x.decide_at_runtime for x in r.tweaks)
    assert r.bloatware.remove == ["Microsoft.BingNews"]
    ex = window.go_to("execution")
    ex._set("mode", "silent")  # type: ignore[attr-defined]
    assert r.execution.mode == "silent"


def test_account_problems_do_not_depend_on_language(window: StudioWindow, qapp) -> None:
    window.ctl.create_recipe("Samuel", None)
    window.apply_preferences(preferences.Preferences(language="en-US"))
    page = window.go_to("account")
    page._set_pc("nome inválido com espaço")  # type: ignore[attr-defined]
    assert "Invalid computer name" in page.problems.text()  # type: ignore[attr-defined]


@pytest.mark.parametrize("lang", SUPPORTED)
def test_first_page_shows_disclaimer(window: StudioWindow, qapp, lang: str) -> None:
    window.apply_preferences(preferences.Preferences(language=lang))  # type: ignore[arg-type]
    page = window.go_to("pendrive")
    wait(qapp, 10)
    text = t("studio.disclaimer.text")
    assert text in [r.subtitle_label.text() for r in page.findChildren(Row)]
    assert {"pt-BR": "vibe-codado", "en-US": "vibe-coded", "es": "vibe coding"}[lang] in text
    assert {"pt-BR": "pré-alpha", "en-US": "Pre-alpha", "es": "pre-alfa"}[lang] in text


def test_live_page_preview_then_apply(qapp, tmp_path: Path) -> None:
    """V2-03 no Studio: prévia obrigatória antes de aplicar; aplicar usa o Agente."""
    from tests.agent.helpers import make_world
    from tests.factories import backup

    (tmp_path / "w").mkdir()
    world = make_world(tmp_path / "w")
    r = world.recipe()
    r.backups = [backup("discord", "{APPDATA}\\discord")]
    world.save_recipe(r)
    dados = world.pendrive / "WinKit" / "Perfis" / "padrao" / "Backups" / "discord" / "dados"
    dados.mkdir(parents=True)
    (dados / "settings.json").write_text("x")
    ctl = StudioController(services=fake_services(), agent_runtime=world.runtime)
    ctl.open_folder(world.pendrive)
    w = StudioWindow(ctl, synchronous_tasks=True, prefs_path=tmp_path / "p.json")
    w.show()
    page = w.go_to("live")
    assert "backup" in page._kinds  # type: ignore[attr-defined]
    assert not page.apply_button.isEnabled()  # type: ignore[attr-defined]
    page._preview()  # type: ignore[attr-defined]
    assert page.apply_button.isEnabled()  # type: ignore[attr-defined]
    page._set_kind("tweak", False)  # type: ignore[attr-defined]
    assert not page.apply_button.isEnabled()  # mudou a escolha: refazer a prévia  # type: ignore[attr-defined]
    page._preview()  # type: ignore[attr-defined]
    page._apply()  # type: ignore[attr-defined]
    assert page.result.text().startswith("Aplicado:")  # type: ignore[attr-defined]
    restored = (
        world.system / "Users" / "Samuel" / "AppData" / "Roaming" / "discord" / "settings.json"
    )
    assert restored.read_text() == "x"


def test_suggestions_page_adds_and_ignores(window: StudioWindow, qapp, tmp_path: Path) -> None:
    roaming = tmp_path / "C" / "Users" / "Samuel" / "AppData" / "Roaming"
    for save in (roaming / ".minecraft" / "saves" / "Mundo", roaming / "StardewValley" / "Saves"):
        save.mkdir(parents=True)
        (save / "jogo.sav").write_bytes(b"x")
    window.ctl.create_recipe("Samuel", None)
    page = window.go_to("suggest")
    page._analyze()  # type: ignore[attr-defined]
    titles = [r.title_label.text() for r in page.findChildren(Row)]
    assert "Minecraft" in titles and "Stardew Valley" in titles
    items = {s.title: s for s in page._items}  # type: ignore[attr-defined]
    page._accept(items["Minecraft"])  # type: ignore[attr-defined]
    page._dismiss(items["Stardew Valley"])  # type: ignore[attr-defined]
    wait(qapp, 5)
    assert page._items == []  # type: ignore[attr-defined]
    r = window.ctl.recipe
    assert r is not None
    assert [b.template for b in r.backups] == [r"{APPDATA}\.minecraft\saves"]
    assert r.meta.dismissed_suggestions == ["save:stardew_valley"]


def test_wizard_steps_and_path_page(window: StudioWindow, qapp) -> None:
    """V3-05/06: Avançar, Pular e Voltar; a escolha do caminho vale antes da receita."""
    page = window.go_to("path")
    assert window.wizard_steps()[0] == "path" and "live" not in window.wizard_steps()
    page._choose("rufus")  # type: ignore[attr-defined]
    page._target("10", "x86")  # type: ignore[attr-defined]
    assert window.ctl.media.path == "rufus" and window.ctl.target_windows.arch == "x86"
    window.step_skip()
    assert window.current_section() == "pendrive"
    window.step_next()
    assert window.current_section() == "account"
    window.step_back()
    assert window.current_section() == "pendrive"
    window.ctl.create_recipe("Samuel", None)
    r = window.ctl.recipe
    assert r is not None and (r.media.path, r.target_windows.version) == ("rufus", "10")
    page._target("11", "x86")  # type: ignore[attr-defined]
    assert r.target_windows.arch == "x64"  # o 11 só tem 64 bits
    build = window.go_to("build")
    rows = [w.subtitle_label.text() for w in build.findChildren(Row)]
    assert any(t("studio.path.title") in text for text in rows)  # "Começar" foi pulada


def test_open_tool_downloads_and_launches(tmp_path: Path) -> None:
    launched: list[list[str]] = []
    ctl = StudioController(
        services=fake_services(old_pc=tmp_path / "C"),
        tool_fetcher=lambda source: tmp_path / f"{source.id}.exe",
        launcher=launched.append,
    )
    ctl.open_tool("rufus", tmp_path / "win.iso")
    ctl.open_tool("ventoy")
    assert launched == [
        [str(tmp_path / "rufus.exe"), "-i", str(tmp_path / "win.iso")],
        [str(tmp_path / "ventoy.exe")],
    ]
