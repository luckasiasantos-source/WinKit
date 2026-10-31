"""Testes de proteção da arquitetura (PLANO.md §19.2). Não podem ser removidos (R-41)."""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "winkit"


def test_import_contracts() -> None:
    exe = shutil.which("lint-imports")
    if exe is None:
        pytest.skip("import-linter não instalado")
    proc = subprocess.run([exe], cwd=ROOT, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_core_has_no_forbidden_imports_even_lazily() -> None:
    """import-linter não vê imports dentro de funções; este teste vê."""
    forbidden = ("winkit.platform", "PySide6", "winreg", "subprocess", "ctypes", "msvcrt")
    for path in (SRC / "core").rglob("*.py"):
        bad = {m for m in _imports(path) if m.startswith(forbidden)}
        assert not bad, f"{path.relative_to(ROOT)} importa {bad}"


def test_subprocess_only_in_runner() -> None:
    allowed = {SRC / "platform" / "runner.py"}
    for path in SRC.rglob("*.py"):
        if path in allowed:
            continue
        assert "subprocess" not in _imports(path), f"{path.relative_to(ROOT)} usa subprocess"


def test_no_shell_true_anywhere() -> None:
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "shell":
                value = node.value
                assert isinstance(value, ast.Constant) and value.value is False, (
                    f"{path.relative_to(ROOT)}:{node.value.lineno} usa shell="
                )


def test_todo_requires_debt_entry() -> None:
    """Todo TODO no código precisa citar uma dívida técnica: TODO(DT-nnn)."""
    debts = (ROOT / "docs" / "DIVIDAS_TECNICAS.md").read_text(encoding="utf-8")
    for path in SRC.rglob("*.py"):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "TODO" in line:
                assert "TODO(DT-" in line, f"{path}:{lineno} TODO sem referência a DT"
                ref = line.split("TODO(")[1].split(")")[0]
                assert f"### {ref} " in debts, f"{path}:{lineno} {ref} não existe"


def test_phase1_does_not_import_qt() -> None:
    """A Fase 1 roda como SYSTEM sem sessão gráfica: não pode carregar Qt (R-35)."""
    code = (
        "import sys\n"
        "import winkit.agent.main as m\n"
        "m.import_phase1_modules()\n"
        "bad = [k for k in sys.modules if k.startswith('PySide6')]\n"
        "assert not bad, bad\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    if "import_phase1_modules" in proc.stderr and "has no attribute" in proc.stderr:
        pytest.skip("agente ainda não implementado")
    if "No module named 'winkit.agent.main'" in proc.stderr:
        pytest.skip("agente ainda não implementado")
    assert proc.returncode == 0, proc.stderr


def test_no_windows_drive_paths_tracked() -> None:
    """Arquivo com "C:\\" no nome quebra o checkout no Windows (IN-008)."""
    proc = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        pytest.skip("git indisponível")
    bad = [f for f in proc.stdout.splitlines() if ":" in f or "\\" in f]
    assert not bad, bad


def test_program_data_is_never_relative() -> None:
    from winkit.platform.system import program_data

    assert program_data().is_absolute()


def test_no_dynamic_imports_in_package() -> None:
    """IN-013: o PyInstaller não enxerga ``importlib.import_module``; módulo some do executável."""
    import ast
    from pathlib import Path

    offenders = []
    for path in Path("src/winkit").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "import_module":
                offenders.append(str(path))
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__":
                offenders.append(str(path))
    assert offenders == []
