# PyInstaller — linha de comando do Studio (onedir, com console). Sem Qt.
#   uv run --group package pyinstaller packaging/winkit.spec --noconfirm
import os

SRC = os.path.join(SPECPATH, "..", "src", "winkit")
ICON = os.path.join(SPECPATH, "winkit.ico")
datas = [
    (os.path.join(SRC, "data", "*.yaml"), os.path.join("winkit", "data")),
    (os.path.join(SRC, "builder", "assets", "bootstrap.ps1"), os.path.join("winkit", "builder", "assets")),
]

a = Analysis(
    [os.path.join(SPECPATH, "entry_cli.py")],
    datas=datas,
    excludes=["tkinter", "pytest", "PySide6", "shiboken6"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="winkit", console=True, upx=False,
          icon=ICON if os.path.exists(ICON) else None)
coll = COLLECT(exe, a.binaries, a.datas, name="winkit", upx=False)
