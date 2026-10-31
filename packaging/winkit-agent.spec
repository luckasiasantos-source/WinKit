# PyInstaller — Agente (onedir, sem console: D-015). Rode a partir da raiz do repositório:
#   uv run --group package pyinstaller packaging/winkit-agent.spec --noconfirm
import os

SRC = os.path.join(SPECPATH, "..", "src", "winkit")
ICON = os.path.join(SPECPATH, "winkit.ico")
datas = [
    (os.path.join(SRC, "data", "*.yaml"), os.path.join("winkit", "data")),
    (os.path.join(SRC, "builder", "assets", "bootstrap.ps1"), os.path.join("winkit", "builder", "assets")),
]

a = Analysis(
    [os.path.join(SPECPATH, "entry_agent.py")],
    datas=datas,
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="winkit-agent",
    console=False, upx=False, version=None,
    icon=ICON if os.path.exists(ICON) else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="winkit-agent", upx=False)
