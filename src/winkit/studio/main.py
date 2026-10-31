"""Ponto de entrada do WinKit Studio (GUI)."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from winkit.platform.services import real_services
from winkit.platform.session import is_admin
from winkit.platform.system import is_windows
from winkit.studio.controller import StudioController
from winkit.studio.ui.window import SECTIONS, StudioWindow
from winkit.ui import theme


def main() -> int:
    smoke = "--teste-fumaca" in sys.argv  # CI: abre e fecha a janela sem interação
    app = QApplication(sys.argv)
    app.setApplicationName("WinKit Studio")
    theme.apply(app)
    if not is_windows() and not smoke:
        QMessageBox.critical(None, "WinKit Studio", "O WinKit Studio funciona no Windows.")
        return 1
    ctl = StudioController(services=real_services())
    try:
        drives = ctl.pendrives()
        if len(drives) == 1:
            ctl.open_ventoy(drives[0])
    except Exception:  # noqa: BLE001, S110 — a página Pendrive mostra o erro
        pass
    window = StudioWindow(ctl)
    window.show()
    if smoke:
        for title, *_ in SECTIONS:
            window.go_to(title)
            app.processEvents()
        return 0
    if is_windows() and not is_admin():
        QMessageBox.warning(
            window,
            "WinKit Studio",
            "Abra o WinKit Studio como administrador: ler ISOs, drivers e "
            "copiar arquivos em uso exige isso.",
        )
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
