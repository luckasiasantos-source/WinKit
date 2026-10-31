from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.agent.helpers import make_world
from tests.factories import tweak
from tests.ui.conftest import wait
from winkit.agent.main import run_phase2_with_ui
from winkit.agent.phases import run_phase1
from winkit.agent.progress import Choice
from winkit.agent.store import StateStore
from winkit.agent.ui.qt import ChoosePage, QtAgentUi, RebootDialog
from winkit.core.planner.models import PlannedStep
from winkit.core.recipe.models import Execution
from winkit.core.summary import Summary

pytestmark = pytest.mark.ui


def step(i: str, kind: str = "app", choice: bool = False) -> PlannedStep:
    return PlannedStep(
        id=f"{kind}:{i}",
        kind=kind,
        ref=i,
        phase=2,
        title=f"Etapa {i}",  # type: ignore[arg-type]
        target="user_profile",
        user_choice=choice,
    )


def summary() -> Summary:
    return Summary(
        computer="PC",
        generated_at=datetime.now(UTC),
        phase1_seconds=1,
        phase2_seconds=1,
        done=3,
        failed=0,
        skipped=0,
        pending=0,
        items=(),
        warnings=(),
    )


def test_countdown_starts_by_itself(qapp) -> None:
    got: list[Choice] = []
    page = ChoosePage(
        [step("a"), step("b", choice=True)], {"app": 2}, countdown=1, default_name=None
    )
    page.decided.connect(got.append)
    wait(qapp, 1300)
    assert got and got[0].action == "start" and got[0].selected == frozenset({"app:b"})


def test_interaction_pauses_countdown_and_selection(qapp) -> None:
    got: list[Choice] = []
    page = ChoosePage(
        [
            step("b", choice=True),
            step("c", choice=True),
            step("pc", "rename_computer", choice=True),
        ],
        {},
        countdown=1,
        default_name="PC-X",
    )
    page.decided.connect(got.append)
    page._toggles["app:b"].click()  # desliga e pausa
    wait(qapp, 1300)
    assert got == []
    assert "pausada" in page.countdown_label.text()
    assert page._name_edit is not None
    page._name_edit.setText("PC-NOVO")
    page.start_btn.click()
    assert got[0].selected == frozenset({"app:c"})
    assert got[0].computer_name == "PC-NOVO"


def test_postpone(qapp) -> None:
    got: list[Choice] = []
    page = ChoosePage([step("a")], {}, countdown=None, default_name=None)
    page.decided.connect(got.append)
    page.postpone_btn.click()
    assert got == [Choice("postpone")]


def test_host_window_mode_round_trip(qapp, monkeypatch: pytest.MonkeyPatch) -> None:
    ui = QtAgentUi(Execution(mode="interactive"), auto_quit_ms=10)
    monkeypatch.setattr(RebootDialog, "exec", lambda self: 1)  # "Reiniciar agora"
    from PySide6.QtCore import QTimer

    def work() -> int:
        choice = ui.choose([step("a"), step("b", choice=True)], {"driver": 1})
        assert choice.action == "start"
        ui.progress(0, 1, "Etapa a")
        ui.step_result("app:a", "done", None)
        ui.waiting("network", True)
        ui.waiting("network", False)
        assert ui.ask_reboot() is True
        ui.finished(summary(), Path("resumo.html"))
        return 7

    def click_start() -> None:
        page = ui.gui.window.choose_page
        if page is None:
            QTimer.singleShot(50, click_start)
            return
        page.start_btn.click()
        QTimer.singleShot(300, ui.gui.window.done_page.close_requested.emit)

    QTimer.singleShot(100, click_start)
    assert ui.host(work) == 7
    assert ui.gui.window.done_page.title.text() == "Tudo pronto"


def test_host_silent_mode_never_shows_window(qapp) -> None:
    ui = QtAgentUi(Execution(mode="silent"), auto_quit_ms=10)

    def work() -> int:
        assert ui.choose([step("a")], {}) == Choice("start")
        ui.notify("WinKit", "olá")
        ui.finished(summary(), Path("r.html"))
        return 0

    assert ui.host(work) == 0
    assert not ui.gui.window.isVisible()


def test_host_propagates_errors(qapp) -> None:
    ui = QtAgentUi(Execution(mode="silent"), auto_quit_ms=10)

    def work() -> int:
        raise RuntimeError("falhou no trabalho")

    with pytest.raises(RuntimeError, match="falhou no trabalho"):
        ui.host(work)


def test_phase2_runs_inside_qt(qapp, tmp_path: Path) -> None:
    world = make_world(tmp_path)
    r = world.recipe()
    r.execution.mode = "countdown"
    r.execution.countdown_seconds = 5
    r.execution.reboot_policy = "never"  # a pergunta de reiniciar tem teste próprio (IN-019)
    r.tweaks = [tweak("visual.dark_theme", decide_at_runtime=True)]
    world.save_recipe(r)
    run_phase1(world.runtime())
    ui_holder: list[QtAgentUi] = []

    def factory(recipe):
        ui = QtAgentUi(recipe.execution, auto_quit_ms=10)
        ui_holder.append(ui)
        return ui

    from PySide6.QtCore import QTimer

    def close_when_done() -> None:
        ui = ui_holder[0] if ui_holder else None
        if ui is None or not ui.gui.finished_seen:
            QTimer.singleShot(100, close_when_done)
            return
        ui.gui.window.done_page.close_requested.emit()

    QTimer.singleShot(200, close_when_done)
    rt = world.runtime()
    rt.ui_factory = factory
    assert run_phase2_with_ui(rt) == 0
    state = StateStore(world.paths.state).load()
    assert state is not None and state.step("finalize:summary").status == "done"
    assert state.step("tweak:visual.dark_theme").status == "done"  # contagem começou sozinha


def test_closing_summary_before_reboot_question_still_asks(
    qapp, monkeypatch, tmp_path: Path
) -> None:
    """IN-019: fechar o resumo antes da pergunta de reiniciar só esconde a janela."""
    import time

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QDialog

    monkeypatch.setattr(RebootDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    ui = QtAgentUi(Execution(mode="countdown"), auto_quit_ms=10)
    html = tmp_path / "resumo.html"
    html.write_text("<html></html>", encoding="utf-8")

    def work() -> int:
        ui.finished(summary(), html)
        time.sleep(0.4)  # o usuário fecha a janela antes da pergunta
        return 1 if ui.ask_reboot() else 0

    def close_when_finished() -> None:
        if ui._gui is None or not ui.gui.finished_seen:
            QTimer.singleShot(50, close_when_finished)
            return
        ui.gui.window.done_page.close_requested.emit()

    QTimer.singleShot(50, close_when_finished)
    assert ui.host(work) == 1  # a pergunta apareceu e foi respondida


def test_pending_request_is_released_when_the_loop_ends(qapp, monkeypatch) -> None:
    """IN-019: a thread de trabalho nunca fica presa e nenhum pedido vaza para depois."""
    import threading

    from PySide6.QtCore import QTimer

    from winkit.agent.ui import qt

    asked = threading.Event()
    monkeypatch.setattr(qt._Gui, "_on_reboot", lambda self, req: asked.set())  # nunca responde
    ui = QtAgentUi(Execution(mode="silent"), auto_quit_ms=10)
    QTimer.singleShot(300, qapp.quit)
    assert ui.host(lambda: 1 if ui.ask_reboot() else 0) == 0  # resposta padrão: não reiniciar
    assert not [t for t in threading.enumerate() if t.name == "winkit-fase2" and t.is_alive()]
