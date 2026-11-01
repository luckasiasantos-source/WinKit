"""Gera ``docs/ESTRUTURA.md``: a árvore do projeto com a descrição de cada arquivo de código.

A descrição de cada módulo vem da primeira linha da docstring dele; a de cada catálogo, da
primeira linha de comentário do YAML. Para mudar um texto, mude a docstring, não o .md.

Uso (na raiz do repositório): uv run python scripts/gen_estrutura.py [--check]
O teste ``tests/test_docs_sync.py`` falha se o arquivo ficar desatualizado.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "winkit"
OUT = ROOT / "docs" / "ESTRUTURA.md"

TOP = [
    ("CLAUDE.md", "regras obrigatórias para quem mexe no código (pessoas e agentes de IA)"),
    (".claude/skills/", "skills obrigatórias do Claude Code neste projeto (Ponytail, R-58)"),
    ("README.md", "apresentação em português, com a versão em inglês logo abaixo"),
    ("README.en.md, README.es.md", "a apresentação em inglês e em espanhol"),
    ("CONTRIBUTING.md", "como contribuir"),
    ("LICENSE, NOTICE", "licença Apache 2.0 e aviso de isenção"),
    ("pyproject.toml, uv.lock", "dependências e configuração de ruff, mypy, pytest e import-linter"),
    (".github/workflows/", "CI (lint, tipos, testes em Linux e Windows, pacote) e release"),
    ("docs/", "plano, arquitetura, status, dívidas, incidentes, changelog e roteiros de validação"),
    ("docs/validacao/", "roteiros de teste em VM ou PC real, um por marco"),
    ("docs/imagens/", "capturas de tela usadas nos READMEs"),
    ("packaging/", "specs do PyInstaller, build.ps1, smoke.ps1, make_icon.py (gera o .ico) e notas da versão"),
    ("scripts/", "check.sh (verificação antes de cada commit) e geradores de documentação"),
    ("src/winkit/", "o código (detalhado abaixo)"),
    ("tests/", "testes automáticos, espelhando as pastas de src/winkit"),
]

#: Ordem das camadas (ARQUITETURA.md): da mais pura para a interface.
PACKAGES = [
    ("core", "lógica pura: receita, planejador, moldes, XML, estado; sem Windows, Qt nem subprocess"),
    ("i18n", "textos em pt-BR, en-US e es, e a tradução na borda (D-031)"),
    ("platform", "tudo que toca o Windows, atrás de interfaces; `fakes/` tem as versões de teste"),
    ("collector", "casos de uso no PC atual: ler apps, drivers, backups e o resto da receita"),
    ("builder", "montar e validar o pendrive"),
    ("agent", "o Agente que roda na instalação: fases, executor e etapas (`steps/`)"),
    ("cli", "a linha de comando `winkit`"),
    ("ui", "componentes visuais compartilhados (tema, widgets)"),
    ("studio", "o WinKit Studio: controlador e páginas"),
    ("data", "catálogos versionados (YAML) e modelos de receita"),
]


def first_line(path: Path) -> str:
    doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
    return doc.strip().split("\n")[0].strip()


def yaml_line(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            return line.lstrip("# ").strip()
        if line.strip():
            break
    return ""


def render() -> str:
    out = [
        "# WinKit — Estrutura do projeto",
        "",
        "> **Gerado** por `scripts/gen_estrutura.py`; não edite à mão. Para mudar uma descrição, "
        "mude a docstring do módulo (ou o primeiro comentário do YAML) e rode o script. "
        "As regras de cada camada estão em [`ARQUITETURA.md`](ARQUITETURA.md).",
        "",
        "## Raiz",
        "",
        "| Caminho | O que tem |",
        "|---|---|",
        *[f"| `{p}` | {d} |" for p, d in TOP],
        "",
        "## `src/winkit/` por camada",
    ]
    for pkg, desc in PACKAGES:
        base = SRC / pkg
        out += ["", f"### `{pkg}/` — {desc}", ""]
        if pkg == "data":
            out += ["| Arquivo | O que tem |", "|---|---|"]
            for f in sorted(base.glob("*.yaml")):
                out.append(f"| `{f.name}` | {yaml_line(f)} |")
            n = len(list((base / "templates").glob("*.json")))
            out.append(f"| `templates/` | {n} modelos de receita prontos (`.winkit.json`) |")
            continue
        out += ["| Arquivo | O que faz |", "|---|---|"]
        for f in sorted(base.rglob("*.py")):
            if "__pycache__" in f.parts:
                continue
            rel = f.relative_to(base).as_posix()
            out.append(f"| `{rel}` | {first_line(f).replace('|', '\\|')} |")
    tests = sorted(d.name for d in (ROOT / "tests").iterdir() if d.is_dir() and d.name not in {"__pycache__"})
    out += [
        "",
        "## `tests/`",
        "",
        "Uma pasta por camada (" + ", ".join(f"`{t}/`" for t in tests) + "). "
        "`fixtures/` guarda as amostras fixas (XML de referência, layouts do Iniciar); "
        "`test_architecture.py` confere as regras do código; `factories.py` monta receitas de teste.",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    text = render()
    if "--check" in sys.argv:
        return 0 if OUT.exists() and OUT.read_text(encoding="utf-8") == text else 1
    OUT.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
