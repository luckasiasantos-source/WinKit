"""Ponto de entrada do WinKit Studio (GUI)."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from winkit.i18n import SUPPORTED, set_language, t
from winkit.platform.locale import detect_language
from winkit.platform.services import real_services
from winkit.platform.session import is_admin
from winkit.platform.system import is_windows
from winkit.studio import preferences
from winkit.studio.controller import StudioController
from winkit.studio.ui.window import StudioWindow, all_sections, resolve_language
from winkit.ui import theme


def main() -> int:
    smoke = "--teste-fumaca" in sys.argv  # CI: abre e fecha a janela sem interação
    prefs = preferences.load()
    set_language(resolve_language(prefs.language, detect_language))  # type: ignore[arg-type]
    app = QApplication(sys.argv)
    app.setApplicationName("WinKit Studio")
    theme.apply(app, prefs.theme)
    if not is_windows() and not smoke:
        QMessageBox.critical(None, "WinKit Studio", t("studio.windows_only"))
        return 1
    ctl = StudioController(services=real_services())
    try:
        drives = ctl.pendrives()
        if len(drives) == 1:
            ctl.open_ventoy(drives[0])
    except Exception:  # noqa: BLE001, S110 — a página Pendrive mostra o erro
        pass
    window = StudioWindow(ctl, detect_language=detect_language)
    window.show()
    if smoke:
        for lang in SUPPORTED:  # toda seção abre em todos os idiomas
            window.apply_preferences(preferences.Preferences(language=lang))
            for s in all_sections():
                window.go_to(s.id)
                app.processEvents()
        return 0
    if is_windows() and not is_admin():
        QMessageBox.warning(window, "WinKit Studio", t("studio.needs_admin"))
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
