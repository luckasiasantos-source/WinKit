# Como contribuir com o WinKit

Obrigado pelo interesse! Este guia resume o que você precisa saber antes de abrir um PR. As regras completas estão em [`CLAUDE.md`](CLAUDE.md) e em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md), e valem igualmente para pessoas e agentes de IA.

## Preparar o ambiente

```bash
git clone https://github.com/luckasiasantos-source/Iso-Modify-Win11
cd Iso-Modify-Win11
uv sync
scripts/check.sh
```

O `scripts/check.sh` roda lint, formatação, tipos (Linux e Windows), contratos de arquitetura e testes, e para no primeiro erro. **Só abra o PR se ele terminar com `== OK`.**

A maior parte do código roda e é testada no Linux, com versões falsas de tudo que toca o Windows (`src/winkit/platform/fakes/`). O CI roda os mesmos testes no Windows e gera os executáveis.

## Regras inegociáveis

- **A ISO do Windows nunca é modificada.** Tudo vai para a pasta `WinKit/` do pendrive.
- **Nunca particionar, formatar ou apagar discos.** O `autounattend.xml` nunca tem `DiskConfiguration`.
- **Restaurar sem sobrescrever** por padrão. Sobrescrever só com escolha explícita na receita.
- `winkit/core` não importa nada do Windows, do Qt nem de `winkit/platform`.
- Comandos externos só por `winkit.platform.runner`, nunca com `shell=True`.
- **Nunca interpretar texto de saída localizado.** Use JSON, CIM, registro ou códigos de saída.
- Identificadores em inglês; textos para o usuário, documentação e mensagens de commit em português (pt-BR).

## Documentos vivos

Toda mudança de código vem **no mesmo commit** com os documentos afetados:

| Aconteceu isto | Atualize |
|---|---|
| Mudou arquitetura, camada, dependência ou regra | `docs/ARQUITETURA.md` |
| Começou, terminou ou bloqueou um item | `docs/STATUS.md` |
| Fez algo provisório ou deixou um `TODO` | `docs/DIVIDAS_TECNICAS.md` |
| Algo quebrou ou uma hipótese se provou falsa | `docs/INCIDENTES.md` |
| Mudou o comportamento do produto | `docs/PLANO.md` |
| **Qualquer commit** | `docs/CHANGELOG.md` |

## Contribuições que mais ajudam

- **Catálogo de apps** (`src/winkit/data/app_catalog.yaml`): pastas de configuração de apps populares, parâmetros silenciosos e o que excluir dos backups (caches, logs).
- **Ajustes e bloatware** (`src/winkit/data/tweaks.yaml`, `bloatware.yaml`): valores confirmados numa versão específica do Windows, com a fonte.
- **Testes em VM ou PC real**: siga um roteiro de [`docs/validacao/`](docs/validacao/) e abra uma issue com a versão do Windows (`winver`), o roteiro, o resultado de cada passo e os logs de `WinKit\Logs\` do pendrive.

## Abrindo o PR

1. Um assunto por PR, com testes do comportamento novo (o resultado exato, não "feito ou pulado").
2. Mensagem de commit em português explicando o porquê.
3. Entrada no `docs/CHANGELOG.md`.
