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
