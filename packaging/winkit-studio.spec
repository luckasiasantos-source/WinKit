# PyInstaller — WinKit Studio (onedir, janela, pede administrador). Gere o ícone antes:
#   uv run python packaging/make_icon.py
#   uv run --group package pyinstaller packaging/winkit-studio.spec --noconfirm
import os

SRC = os.path.join(SPECPATH, "..", "src", "winkit")
ICON = os.path.join(SPECPATH, "winkit.ico")
datas = [
    (os.path.join(SRC, "data", "*.yaml"), os.path.join("winkit", "data")),
    (os.path.join(SRC, "builder", "assets", "bootstrap.ps1"), os.path.join("winkit", "builder", "assets")),
]

a = Analysis(
    [os.path.join(SPECPATH, "entry_studio.py")],
    datas=datas,
    excludes=["tkinter", "pytest", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
              "PySide6.Qt3DCore", "PySide6.QtQuick", "PySide6.QtQml"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="winkit-studio",
    console=False, upx=False, uac_admin=True,
    icon=ICON if os.path.exists(ICON) else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="winkit-studio", upx=False)
