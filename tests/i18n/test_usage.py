"""R-51 (uso das chaves) e R-55 (nenhum texto de interface solto no código)."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from winkit.i18n import messages_for

SRC = Path("src/winkit")
BASE = messages_for("pt-BR")
KEY = re.compile(r"^[a-z][a-z0-9_]*(\.[A-Za-z0-9_.\-]+)+$")
CALLS = {"t", "tn", "msg"}


def _trees() -> list[tuple[Path, ast.AST]]:
    return [
        (p, ast.parse(p.read_text(encoding="utf-8")))
        for p in SRC.rglob("*.py")
        if "i18n" not in p.parts
    ]


def _call_name(node: ast.Call) -> str:
    f = node.func
    return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""


def test_every_key_used_in_code_exists() -> None:
    missing = []
    for path, tree in _trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _call_name(node) in CALLS and node.args:
                first = node.args[0]
                is_text = isinstance(first, ast.Constant) and isinstance(first.value, str)
                if is_text and first.value not in BASE:  # type: ignore[attr-defined]
                    missing.append(f"{path}:{node.lineno} {first.value}")  # type: ignore[attr-defined]
    assert missing == []


def test_every_key_is_used() -> None:
    literals: set[str] = set()
    prefixes: set[str] = set()
    for _, tree in _trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if KEY.match(node.value):
                    literals.add(node.value)
            elif isinstance(node, ast.JoinedStr) and node.values:
                head = node.values[0]
                is_text = isinstance(head, ast.Constant) and isinstance(head.value, str)
                if is_text and re.match(r"^[a-z][a-z0-9_]*\.", head.value):  # type: ignore[attr-defined]
                    prefixes.add(head.value)  # type: ignore[attr-defined]
    unused = [
        k
        for k in BASE
        if k not in literals and not any(k.startswith(p) for p in prefixes) and k != "legacy.text"
    ]
    assert unused == []


# ------------------------------------------------------------------ R-55
UI_DIRS = [SRC / "studio", SRC / "agent" / "ui", SRC / "ui", SRC / "cli"]
#: Função → posições dos argumentos que são texto para o usuário.
UI_FUNCS: dict[str, tuple[int, ...]] = {
    "label": (0,),
    "button": (0,),
    "Row": (0, 1),
    "section": (0,),
    "setText": (0,),
    "setWindowTitle": (0,),
    "setToolTip": (0,),
    "setPlaceholderText": (0,),
    "information": (1, 2),
    "warning": (1, 2),
    "critical": (1, 2),
    "question": (1, 2),
    "showMessage": (0, 1),
    "out": (0,),
    "print": (0,),
    "QLabel": (0,),
    "QPushButton": (0,),
    "addItem": (0,),
    "getText": (1, 2),
    "getExistingDirectory": (1,),
    "getOpenFileName": (1,),
}
UI_KEYWORDS = {"help", "description", "footer"}
#: Nomes próprios que não se traduzem.
ALLOWED = {
    "WinKit",
    "WinKit Studio",
    "Windows 11",
    "Português (Brasil)",
    "English",
    "Español",
    "abc123",  # exemplo de id pessoal do NextDNS
    "https://…/dns-query",  # exemplo de modelo DoH
}


def _has_text(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value not in ALLOWED and bool(re.search(r"[A-Za-zÀ-ÿ]{2,}", node.value))
    if isinstance(node, ast.JoinedStr):
        return any(
            isinstance(v, ast.Constant) and isinstance(v.value, str) and _has_text(v)
            for v in node.values
        )
    return False


def test_no_loose_ui_strings() -> None:
    found = []
    for folder in UI_DIRS:
        for path in folder.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = _call_name(node)
                positions = UI_FUNCS.get(name, ())
                candidates = [node.args[i] for i in positions if i < len(node.args)]
                candidates += [k.value for k in node.keywords if k.arg in UI_KEYWORDS]
                for arg in candidates:
                    if _has_text(arg):
                        found.append(f"{path}:{node.lineno} {ast.unparse(arg)[:60]}")
    assert found == []
