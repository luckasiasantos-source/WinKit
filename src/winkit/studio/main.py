"""Ponto de entrada do WinKit Studio (GUI)."""

from __future__ import annotations

import sys

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen

from winkit.i18n import SUPPORTED, set_language, t
from winkit.platform.locale import detect_language
from winkit.platform.system import is_windows
from winkit.studio import preferences
from winkit.ui import theme
from winkit.ui.widgets import logo_pixmap


def main() -> int:
    smoke = "--teste-fumaca" in sys.argv  # CI: abre e fecha a janela sem interação
    app = QApplication(sys.argv)
    app.setApplicationName("WinKit Studio")
    splash = QSplashScreen(logo_pixmap(160))  # aparece antes de carregar o resto (V3-01)
    splash.show()
    app.processEvents()
    # importações pesadas (catálogos, serviços, páginas) só depois da tela de abertura
    from winkit.platform.services import real_services  # noqa: PLC0415
    from winkit.platform.session import is_admin  # noqa: PLC0415
    from winkit.studio.controller import StudioController  # noqa: PLC0415
    from winkit.studio.ui.window import StudioWindow, all_sections, resolve_language  # noqa: PLC0415

    prefs = preferences.load()
    set_language(resolve_language(prefs.language, detect_language))  # type: ignore[arg-type]
    theme.apply(app, prefs.theme)
    if not is_windows() and not smoke:
        splash.close()
        QMessageBox.critical(None, "WinKit Studio", t("studio.windows_only"))
        return 1
    # a lista de pendrives carrega em segundo plano na página Pendrive (R-59)
    ctl = StudioController(services=real_services())
    window = StudioWindow(ctl, detect_language=detect_language)
    window.show()
    splash.finish(window)
    if smoke:
        for lang in SUPPORTED:  # toda seção abre em todos os idiomas
            window.apply_preferences(preferences.Preferences(language=lang))
            for s in all_sections():
                window.go_to(s.id)
                app.processEvents()
        QThreadPool.globalInstance().waitForDone(120_000)  # leituras em segundo plano
        app.processEvents()
        return 0
    if is_windows() and not is_admin():
        QMessageBox.warning(window, "WinKit Studio", t("studio.needs_admin"))
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
