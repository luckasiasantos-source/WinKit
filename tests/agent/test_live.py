"""Modo "aplicar neste PC" (V2-03, D-033) e ponto de restauração (V2-10)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.agent.helpers import World, make_world
from tests.factories import backup, tweak
from winkit.agent import main as agent_main
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.core import layout
from winkit.i18n import render
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.restore import FakeRestorePoints
from winkit.platform.fakes.services import fake_services
from winkit.platform.restore import FREQUENCY_VALUE, SR_KEY, SR_POLICY_KEY

DARK = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"


def put(w: World, backup_id: str, files: dict[str, str]) -> None:
    dados = layout.payload(w.pendrive, f"Perfis/padrao/Backups/{backup_id}/dados")
    for rel, content in files.items():
        (dados / rel).parent.mkdir(parents=True, exist_ok=True)
        (dados / rel).write_text(content)


@pytest.fixture
def world(tmp_path: Path) -> World:
    w = make_world(tmp_path)
    r = w.recipe()
    r.backups = [backup("discord", "{APPDATA}\\discord")]
    r.tweaks = [tweak("visual.dark_theme")]
    r.updates.windows_update_after_install = False
    w.save_recipe(r)
    put(w, "discord", {"settings.json": "do backup", "sub/x.txt": "x"})
    mine = w.system / "Users" / "Samuel" / "AppData" / "Roaming" / "discord"
    mine.mkdir(parents=True)
    (mine / "settings.json").write_text("meu")  # já existe no Windows em uso
    return w


def restore(w: World) -> FakeRestorePoints:
    r = w.services.restore
    assert isinstance(r, FakeRestorePoints)
    return r


def reg(w: World) -> FakeRegistry:
    r = w.services.registry
    assert isinstance(r, FakeRegistry)
    return r


def _forbid_writes(w: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """R-54: na prévia, qualquer escrita é erro."""

    def boom(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("a prévia tentou mudar algo")

    s = w.services
    for obj, names in (
        (s.registry, ["set", "delete_value", "delete_key", "create_key", "load_hive"]),
        (s.copier, ["restore_tree", "copy_file"]),
        (s.appx, ["remove"]),
        (s.installers, ["run"]),
        (s.winget, ["install", "register"]),
        (s.drivers, ["install"]),
        (s.restore, ["enable", "ensure_max_percent", "create"]),
        (s.runner, ["run"]),
        (s.features, ["rename_computer", "set_optional_feature"]),
        (s.updater, ["install_all"]),
    ):
        for name in names:
            if hasattr(obj, name):
                monkeypatch.setattr(obj, name, boom)


def test_preview_never_writes(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_writes(world, monkeypatch)
    res = run_live(world.runtime(), LiveOptions(root=world.pendrive, simulate=True))
    assert res.code == 0 and res.preview is not None
    by_id = {i.step_id: i for i in res.preview.items}
    assert by_id["restore_point:before"].status == "will_change"
    copy = by_id["backup:discord"]
    assert copy.status == "will_change"
    text = render(copy.changes[0])
    assert "copiar 1 arquivo(s)" in text and "1 já existem" in text
    assert by_id["tweak:visual.dark_theme"].status == "will_change"
    assert res.run_dir is not None and (res.run_dir / "previa.json").is_file()
    assert not (res.run_dir / "estado.json").exists()
    mine = world.system / "Users" / "Samuel" / "AppData" / "Roaming" / "discord"
    assert not (mine / "sub").exists()


def test_apply_creates_restore_point_first_and_merges(world: World) -> None:
    res = run_live(world.runtime(), LiveOptions(root=world.pendrive))
    assert res.code == 0, res.counts
    assert [
        p.description.startswith("WinKit — antes de aplicar") for p in restore(world).points
    ] == [True]
    mine = world.system / "Users" / "Samuel" / "AppData" / "Roaming" / "discord"
    assert (mine / "settings.json").read_text() == "meu"  # merge: nunca sobrescreve (R-21)
    assert (mine / "sub" / "x.txt").read_text() == "x"
    assert reg(world).get("HKCU", DARK, "AppsUseLightTheme") == 0  # no usuário atual
    assert res.summary_html is not None and res.summary_html.is_file()
    assert res.run_dir is not None and res.run_dir.parent.name == "Aplicacoes"
    state = StateStore(res.run_dir / "estado.json").load()
    assert state is not None and state.step("restore_point:before").status == "done"
    # nada de instalação: sem atalho do resumo, sem tarefa da Fase 2
    assert not list((world.system / "Users" / "Samuel" / "Desktop").glob("*"))
    assert world.services.scheduler.task_exe is None  # type: ignore[attr-defined]
    assert list((world.pendrive / "WinKit" / "Logs").glob("*_aplicar"))


def test_second_preview_says_already_done(world: World) -> None:
    run_live(world.runtime(), LiveOptions(root=world.pendrive))
    again = run_live(
        world.runtime(), LiveOptions(root=world.pendrive, simulate=True, restore_point=False)
    )
    assert again.preview is not None
    assert {i.step_id: i.status for i in again.preview.items} == {
        "backup:discord": "already_done",
        "tweak:visual.dark_theme": "already_done",
        "tweak:system.wu_no_driver_replacement": "already_done",
        "tweak:system.consumer_content": "already_done",
    }


def test_only_kinds_and_without_restore_point(world: World) -> None:
    res = run_live(
        world.runtime(),
        LiveOptions(root=world.pendrive, only_kinds=frozenset({"backup"}), restore_point=False),
    )
    assert res.code == 0
    assert restore(world).points == []
    assert reg(world).get("HKCU", DARK, "AppsUseLightTheme") is None


def test_restore_point_policy_failure_and_frequency_restored(world: World) -> None:
    reg(world).set("HKLM", SR_KEY, FREQUENCY_VALUE, "dword", 1440)
    restore(world).create_code = 7
    res = run_live(world.runtime(), LiveOptions(root=world.pendrive, only_kinds=frozenset()))
    state = StateStore(res.run_dir / "estado.json").load()  # type: ignore[operator]
    assert state is not None
    st = state.step("restore_point:before")
    assert st.status == "failed" and "código 7" in render(st.error)
    assert reg(world).get("HKLM", SR_KEY, FREQUENCY_VALUE) == 1440  # valor original de volta
    reg(world).set("HKLM", SR_POLICY_KEY, "DisableSR", "dword", 1)
    res = run_live(world.runtime(), LiveOptions(root=world.pendrive, only_kinds=frozenset()))
    state = StateStore(res.run_dir / "estado.json").load()  # type: ignore[operator]
    assert state is not None and state.step("restore_point:before").status == "skipped"


def test_ready_restore_point_at_the_end_of_install(world: World) -> None:
    from winkit.agent.phases import run_phase1, run_phase2

    run_phase1(world.runtime())
    run_phase2(world.runtime())
    points = restore(world).points
    assert len(points) == 1 and points[0].description.startswith("WinKit — Windows pronto")
    assert reg(world).get("HKLM", SR_KEY, FREQUENCY_VALUE) is None  # não deixa rastro


def test_agent_apply_command(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_main, "build_runtime", world.runtime)
    opened: list[Path] = []
    monkeypatch.setattr(agent_main, "open_file", opened.append)
    assert agent_main.main(["apply", "--root", str(world.pendrive), "--simular"]) == 0
    assert opened == []
    assert agent_main.main(["apply", "--root", str(world.pendrive), "--somente", "backup"]) == 0
    assert opened and opened[0].name == "resumo.html"


def test_cli_aplicar(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "AGENT_RUNTIME", world.runtime)
    out: list[str] = []
    raiz = ["--raiz", str(world.pendrive)]
    assert cli.main(["aplicar", *raiz, "--simular"], services=fake_services(), out=out.append) == 0
    assert any("[vai mudar]" in line for line in out)
    out.clear()
    code = cli.main(
        ["aplicar", *raiz, "--sem-ponto-de-restauracao"], services=fake_services(), out=out.append
    )
    assert code == 2 and "--sei-o-que-estou-fazendo" in out[0]
    out.clear()
    assert cli.main(["apply", *raiz], services=fake_services(), out=out.append) == 0
    assert out[0].startswith("Aplicado:")


def test_caller_language_wins_over_recipe(world: World) -> None:
    res = run_live(world.runtime(), LiveOptions(root=world.pendrive, simulate=True, language="es"))
    assert res.preview is not None
    assert res.preview.items[0].title == "Punto de restauración antes de aplicar"
