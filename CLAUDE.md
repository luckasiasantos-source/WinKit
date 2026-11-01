# Regras obrigatórias do projeto WinKit

Este arquivo vale para qualquer pessoa ou agente de IA que for trabalhar neste repositório.

## Antes de mexer em qualquer coisa

Leia, nesta ordem:

1. `docs/PLANO.md` — o que o produto é e como foi desenhado.
   - `docs/PLANO_V2.md` — plano da v2 (M11–M18): funções novas, decisões D-030+ e regras R-51+.
   - `docs/PLANO_V3.md` — plano da v3 (M19–M26): funções novas, decisões D-044+ e regras R-59+. Suas decisões e regras entram no `ARQUITETURA.md` no marco que as usa.
2. `docs/ARQUITETURA.md` — arquitetura e **regras do código** (obrigatórias).
3. `docs/STATUS.md` — o que já está implementado e o que está em andamento.
4. `docs/DIVIDAS_TECNICAS.md` — o que sabemos que está incompleto ou feito de um jeito provisório.
5. `docs/INCIDENTES.md` — o que já deu errado, para não repetir.
6. `docs/CHANGELOG.md` — o mapa de todas as mudanças e implementações já feitas.
7. `docs/ESTRUTURA.md` — a árvore do projeto, com o que cada arquivo de código faz.

## Skill obrigatória: Ponytail

Em **toda tarefa de código** neste repositório (escrever, corrigir, refatorar, revisar, escolher dependência), use a skill `ponytail` (nível `full`), em `.claude/skills/ponytail/`: a menor mudança que resolve o problema por inteiro, sem abstração nem opção que ninguém pediu, e uma resposta que diz o que ficou de fora e o risco. Para revisar uma mudança grande antes do commit, use `ponytail-review`; para o repositório inteiro, `ponytail-audit`; para listar os atalhos deixados, `ponytail-debt` (R-58).

Quando a skill e estas regras divergirem, **estas regras vencem**:
- os documentos vivos, o README e o `ESTRUTURA.md` fazem parte da "mudança completa", não são extra;
- respostas, relatórios de revisão, documentos e commits continuam em pt-BR;
- todo comentário `shortcut:` tem uma entrada correspondente em `docs/DIVIDAS_TECNICAS.md`, como um `TODO`;
- a cobertura mínima da R-38 continua valendo, além do "um teste onde a lógica precisa".

## Antes de cada commit (obrigatório)

```bash
scripts/check.sh
```

Roda lint, formatação, tipos, contratos de arquitetura e testes, e **para no primeiro erro**. Não commite se ele não terminar com `== OK` (IN-003).

## Documentos vivos (obrigatório)

Toda mudança de código vem **no mesmo commit** com a atualização dos documentos afetados:

| Aconteceu isto | Atualize |
|---|---|
| Mudou a arquitetura, uma camada, uma dependência ou uma regra | `docs/ARQUITETURA.md` (incluindo o Registro de Decisões) |
| Começou, terminou ou bloqueou um item de um marco | `docs/STATUS.md` |
| Fez algo provisório, pulou um caso, deixou um TODO | `docs/DIVIDAS_TECNICAS.md` |
| Algo quebrou, uma hipótese se provou falsa, um teste real falhou | `docs/INCIDENTES.md` |
| Mudou escopo ou comportamento do produto | `docs/PLANO.md` (v1) ou `docs/PLANO_V2.md` (v2) |
| Mudou algo que o README descreve (funções, requisitos, comandos, estado, aviso) | `README.md`, `README.en.md` e `README.es.md`; depois rode `uv run python scripts/sync_readme.py` (copia o inglês para baixo do português no `README.md`) — R-56 |
| Criou, moveu ou removeu um arquivo de código, ou mudou a docstring de um módulo | rode `uv run python scripts/gen_estrutura.py` para regerar `docs/ESTRUTURA.md` — R-57 |
| **Qualquer commit** | `docs/CHANGELOG.md` — sempre, sem exceção |

`TODO` ou `shortcut:` no código sem uma entrada correspondente em `DIVIDAS_TECNICAS.md` não é permitido.

Todo módulo Python começa com uma docstring cuja primeira linha diz o que ele faz: é dela que sai a descrição em `docs/ESTRUTURA.md`. O teste `tests/test_docs_sync.py` falha se o README ou a estrutura ficarem desatualizados.

## Regras inegociáveis (resumo — detalhes em ARQUITETURA.md)

- **A ISO original do Windows nunca é modificada.** Tudo vai para a pasta `WinKit/` no pendrive. A ISO personalizada (D-044) é sempre uma **cópia** num arquivo novo.
- **Nada pesado vai para dentro da ISO**, nem backup, nem instalador, nem driver — exceto na cópia autossuficiente que a pessoa pede (D-044).
- **Nunca particionar, formatar ou apagar discos.** Única exceção: o pendrive USB que a pessoa escolheu e confirmou digitando a letra, só por `platform/usb_writer.py` e com as travas da D-045 (R-60). O `autounattend.xml` nunca contém `DiskConfiguration`.
- **Restauração é aditiva por padrão** (mesclar sem sobrescrever). Sobrescrever só com escolha explícita na receita.
- `winkit/core` não importa `winkit/platform`, Qt, `winreg`, `subprocess` nem nada específico de Windows.
- Nenhum `subprocess` com `shell=True`. Todo comando externo passa por `winkit.platform.runner`.
- **Nunca interpretar texto de saída localizado** (o Windows do usuário é pt-BR). Use JSON, CIM, registro ou códigos de saída.
- Identificadores de código em inglês; textos para o usuário, documentação e mensagens de commit em português (pt-BR).
