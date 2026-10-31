"""Documentos gerados continuam em dia (R-56, R-57): README bilíngue e ESTRUTURA.md."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def _script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_readme_has_english_version_in_sync() -> None:
    """R-56: o README.md traz a versão em inglês igual ao README.en.md."""
    sync = _script("sync_readme")
    pt = (ROOT / "README.md").read_text(encoding="utf-8")
    en = (ROOT / "README.en.md").read_text(encoding="utf-8")
    assert "(#english)" in pt[:2000], "falta o aviso da versão em inglês no começo"
    assert sync.render(pt, en) == pt, "rode: uv run python scripts/sync_readme.py"


def test_structure_doc_is_up_to_date() -> None:
    """R-57: docs/ESTRUTURA.md descreve todos os arquivos de código atuais."""
    gen = _script("gen_estrutura")
    current = (ROOT / "docs" / "ESTRUTURA.md").read_text(encoding="utf-8")
    assert gen.render() == current, "rode: uv run python scripts/gen_estrutura.py"
