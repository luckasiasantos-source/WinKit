"""Copia o README em inglês para o fim do README.md (seção "English version").

Uso (na raiz do repositório): uv run python scripts/sync_readme.py
O teste ``tests/test_readme.py`` falha se o README.md ficar diferente do que este script gera.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- english:start (gerado por scripts/sync_readme.py a partir de README.en.md) -->"
END = "<!-- english:end -->"


def english_block(en_text: str) -> str:
    body = en_text[en_text.index("> [!CAUTION]") :].strip()
    return f'{START}\n\n<a id="english"></a>\n\n# WinKit — English version\n\n{body}\n\n{END}'


def render(pt_text: str, en_text: str) -> str:
    block = english_block(en_text)
    if START in pt_text:
        head = pt_text[: pt_text.index(START)]
        tail = pt_text[pt_text.index(END) + len(END) :]
        return head + block + tail
    return pt_text.rstrip() + "\n\n---\n\n" + block + "\n"


def main() -> int:
    pt, en = ROOT / "README.md", ROOT / "README.en.md"
    new = render(pt.read_text(encoding="utf-8"), en.read_text(encoding="utf-8"))
    if "--check" in sys.argv:
        return 0 if new == pt.read_text(encoding="utf-8") else 1
    pt.write_text(new, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
