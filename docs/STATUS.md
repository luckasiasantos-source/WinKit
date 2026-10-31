# WinKit — Status da Implementação

> Documento vivo. Mostra **o que existe de verdade no código** neste momento, marco por marco.
> Atualizado no mesmo commit de toda mudança que começa, conclui ou bloqueia um item.
>
> Legenda: ⬜ não iniciado · 🟨 em andamento · ✅ concluído · ⛔ bloqueado · ➖ fora do escopo atual

**Última atualização:** 2026-10-31
**Versão do código:** 0.1.0 (em desenvolvimento)
**Fase do projeto:** implementação em andamento (autorizada pelo usuário para seguir de ponta a ponta de forma autônoma)

## Resumo

| Marco | Descrição | Estado | Validação em hardware |
|---|---|---|---|
| — | Planejamento e documentação | ✅ | — |
| M0 | Fundação | ✅ | — |
| M1 | Núcleo puro | ✅ | — |
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

### M0 — Fundação ✅
- ✅ `pyproject.toml` (hatchling, src layout) + uv + `uv.lock`
- ✅ ruff, mypy (`--strict` em `core`), pytest, import-linter configurados
- ✅ CI GitHub Actions (`.github/workflows/ci.yml`): Linux + Windows, lint, tipos, contratos, testes, cobertura
- ✅ Estrutura de pastas (`PLANO.md` §18)
- ✅ `core/errors.py` — hierarquia completa (R-25)
- ✅ `i18n/pt_br.py` — catálogo de textos + `t()`; teste valida todos os formatos
- ✅ `platform/system.py` — caminhos de ferramentas nativas (R-12)
- ✅ `platform/runner.py` — `SubprocessRunner` (lista de args, timeout com encerramento da árvore, sem janela de console, máscara de segredos, log)
- ✅ `platform/powershell.py` — parâmetros via JSON/Base64, `-EncodedCommand`, saída JSON
- ✅ `platform/fakes/` — `FakeRunner`, `FakePowerShell`
- ✅ Testes de proteção: contratos do import-linter, imports tardios no `core`, `subprocess` só no runner, `shell=` proibido, `TODO` exige `DT-nnn`, Fase 1 sem Qt (ativado no M3)

**Testes:** 130 passando no Linux, 4 pulados (3 exigem Windows real — rodam no CI Windows; 1 aguarda o Agente).

### M1 — Núcleo puro ✅
- ✅ `core/recipe/models.py` — receita completa (Pydantic, `extra=forbid`, validação na atribuição)
- ✅ `core/recipe/io.py` — carregar/gravar, hash estável, criação, cadeia de migrações
- ✅ `core/recipe/validation.py` — regras do §6.2 + caminhos do pendrive (sem `..`, só `Apps/`, `Drivers/`, `Perfis/<perfil>/`) + referências aos catálogos
- ✅ `core/paths/templates.py` — tradução por prefixo mais longo, resolução, perfil Default, redirecionamento
- ✅ `core/catalog/` — modelos + carregador com checagem de ids repetidos
- ✅ `winkit/data/*.yaml` — 13 apps, 26 ajustes (todos com `source` e `undo`), 54 pacotes de bloatware, 7 edições, 7 assinaturas de instalador, 10 padrões DPAPI, 19 exclusões, 24 classes de driver
- ✅ `core/planner/` — planejador R1–R15 com fallback, ordem topológica determinística, itens excluídos com motivo
- ✅ `core/state/` — estado, transições, retomada, limite de tentativas, tentar de novo
- ✅ `core/manifest/` — varredura com reaproveitamento de hash, diff, verificação de integridade
- ✅ `core/fsutil.py` — escrita atômica (R-16)

**Testes:** 300 passando; cobertura do `core` = 98%.

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
