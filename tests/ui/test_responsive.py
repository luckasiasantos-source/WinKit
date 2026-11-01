"""R-59: nenhuma tela trava esperando o Windows; leituras lentas vão para segundo plano (V3-01)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from PySide6.QtCore import QThreadPool

from tests.ui.conftest import wait
from winkit.platform.fakes.services import fake_services
from winkit.studio.controller import StudioController
from winkit.studio.ui.window import StudioWindow, all_sections
from winkit.ui.widgets import Row

pytestmark = pytest.mark.ui
SLOW = 2.0


def test_every_page_opens_fast_even_with_slow_system(qapp, tmp_path: Path) -> None:
    pen = tmp_path / "pen"
    pen.mkdir()
    ctl = StudioController(services=fake_services(old_pc=tmp_path / "C"))
    ctl.open_folder(pen)
    ctl.create_recipe("Samuel", None)
    real = ctl.pendrives

    def slow(fn):  # type: ignore[no-untyped-def]
        def wrapper():  # type: ignore[no-untyped-def]
            time.sleep(SLOW)
            return fn()

        return wrapper

    ctl.pendrives = slow(real)  # type: ignore[method-assign]
    ctl.sizes = slow(ctl.sizes)  # type: ignore[method-assign]
    ctl.data_volumes = slow(ctl.data_volumes)  # type: ignore[method-assign]
    window = StudioWindow(ctl, prefs_path=tmp_path / "p.json")
    window.show()
    for s in all_sections():
        start = time.perf_counter()
        window.go_to(s.id)
        qapp.processEvents()
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"{s.id} levou {elapsed:.2f}s"  # folga para CI lento; meta 0,2 s
    page = window.go_to("pendrive")
    QThreadPool.globalInstance().waitForDone(10_000)
    wait(qapp, 50)
    assert "pendrives" in ctl.cache and "sizes" in ctl.cache
    titles = [r.title_label.text() for r in page.findChildren(Row) if r.isVisible()]
    assert titles  # a página recarregou com os dados lidos
