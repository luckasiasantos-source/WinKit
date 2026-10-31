# WinKit — Status da Implementação

> Documento vivo. Mostra **o que existe de verdade no código** neste momento, marco por marco.
> Atualizado no mesmo commit de toda mudança que começa, conclui ou bloqueia um item.
>
> Legenda: ⬜ não iniciado · 🟨 em andamento · ✅ concluído · ⛔ bloqueado · ➖ fora do escopo atual

**Última atualização:** 2026-10-31
**Versão do código:** nenhuma (ainda não há código)
**Fase do projeto:** Planejamento concluído — aguardando autorização para iniciar o M0

## Resumo

| Marco | Descrição | Estado | Validação em hardware |
|---|---|---|---|
| — | Planejamento e documentação | ✅ | — |
| M0 | Fundação | ⬜ | — |
| M1 | Núcleo puro | ⬜ | — |
| M2 | Construtor mínimo + primeira instalação real | ⬜ | ⬜ pendente |
| M3 | Esqueleto do Agente | ⬜ | ⬜ pendente |
| M4 | Drivers | ⬜ | ⬜ pendente |
| M5 | Aplicativos | ⬜ | ⬜ pendente |
| M6 | Backups | ⬜ | ⬜ pendente |
| M7 | Bloatware e ajustes | ⬜ | ⬜ pendente |
| M8 | Windows Update, resumo e notificações | ⬜ | ⬜ pendente |
| M9 | Interface do Agente | ⬜ | ⬜ pendente |
| M10 | WinKit Studio (GUI) | ⬜ | — |

## Detalhe por marco

### Planejamento ✅
- ✅ Análise da conversa anterior (PDF) e correções técnicas
- ✅ Decisões D-001 a D-019 (`ARQUITETURA.md`)
- ✅ `PLANO.md`, `ARQUITETURA.md`, `STATUS.md`, `DIVIDAS_TECNICAS.md`, `INCIDENTES.md`, `CHANGELOG.md`, `CLAUDE.md`

### M0 — Fundação ⬜
- ⬜ `pyproject.toml` + uv + `uv.lock`
- ⬜ ruff, mypy, pytest, import-linter configurados
- ⬜ CI GitHub Actions (Linux + Windows)
- ⬜ Estrutura de pastas (`PLANO.md` §18)
- ⬜ `core/errors.py`
- ⬜ `i18n/pt_br.py`
- ⬜ `platform/runner.py` + testes
- ⬜ `platform/powershell.py` + testes
- ⬜ Testes de proteção de camadas ativos

### M1 — Núcleo puro ⬜
- ⬜ Modelos da receita + validação + estrutura de migração
- ⬜ Moldes de caminho (tradução e resolução)
- ⬜ Esquemas dos catálogos + YAMLs iniciais
- ⬜ Planejador (R1–R15)
- ⬜ Modelo de estado e transições
- ⬜ Manifesto e diff incremental

### M2 — Construtor mínimo ⬜
- ⬜ Detecção do Ventoy
- ⬜ Leitura de ISOs
- ⬜ Gerador do `autounattend.xml`
- ⬜ Mesclagem do `ventoy.json`
- ⬜ `bootstrap.ps1` mínimo
- ⬜ CLI: `pendrive listar`, `construir --somente-xml`, `validar`
- ⬜ Roteiro `docs/validacao/M2.md`

### M3 — Esqueleto do Agente ⬜
- ⬜ Empacotamento PyInstaller onedir
- ⬜ Executor + estado + retomada + instância única
- ⬜ `SetupComplete.cmd`, tarefa agendada, fallback, limpeza
- ⬜ Localização e espera do pendrive
- ⬜ Logs no pendrive
- ⬜ Roteiro `docs/validacao/M3.md`

### M4 — Drivers ⬜
### M5 — Aplicativos ⬜
### M6 — Backups ⬜
### M7 — Bloatware e ajustes ⬜
### M8 — Windows Update, resumo e notificações ⬜
### M9 — Interface do Agente ⬜
### M10 — WinKit Studio ⬜

(Itens detalhados de M4–M10 em `PLANO.md` §20; são desdobrados aqui quando o marco começar.)

## Hipóteses técnicas

| # | Hipótese (resumo) | Estado | Onde foi validada |
|---|---|---|---|
| H1 | `auto_install` do Ventoy aplica todas as etapas do XML | ⬜ não validada | — |
| H2 | Pendrive visível com letra na etapa *specialize* e no `SetupComplete.cmd` | ⬜ | — |
| H3 | `SetupComplete.cmd` executa com chave genérica em PC com chave OEM | ⬜ | — |
| H4 | `SetupComplete.cmd` roda antes da criação do perfil a partir do Default | ⬜ | — |
| H5 | winget disponível em até ~10 min após o primeiro login | ⬜ | — |
| H6 | robocopy lê cópia de sombra via link simbólico | ⬜ | — |
| H7 | Agente PyInstaller roda como SYSTEM sem bloqueio do Defender | ⬜ | — |
| H8 | Desempenho aceitável de pasta crua em exFAT via USB | ⬜ | — |
| H9 | PowerShell funciona na etapa *specialize* | ⬜ | — |
| H10 | Instalador enxerga o SSD sem driver extra | ⬜ | — |
