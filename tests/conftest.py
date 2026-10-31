from __future__ import annotations

import ctypes
import os
import sys

import pytest


def _is_admin() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except OSError:
        return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    skip_win = pytest.mark.skip(reason="só roda no Windows")
    skip_admin = pytest.mark.skip(reason="exige administrador no Windows")
    admin = _is_admin()
    for item in items:
        if "windows" in item.keywords and sys.platform != "win32":
            item.add_marker(skip_win)
        if "admin" in item.keywords and not admin:
            item.add_marker(skip_admin)


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def _base_language(monkeypatch: pytest.MonkeyPatch) -> object:
    """Todo teste começa e termina em pt-BR (o idioma é estado do processo, D-030).

    ``WINKIT_LANG`` fixo: sem isso a CLI e o Studio detectam o idioma do Windows da máquina
    de teste (o runner do CI é em inglês — IN-014).
    """
    from winkit.i18n import set_language

    monkeypatch.setenv("WINKIT_LANG", "pt-BR")
    set_language("pt-BR")
    yield
    set_language("pt-BR")
