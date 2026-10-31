# Regras obrigatórias do projeto WinKit

Este arquivo vale para qualquer pessoa ou agente de IA que for trabalhar neste repositório.

## Antes de mexer em qualquer coisa

Leia, nesta ordem:

1. `docs/PLANO.md` — o que o produto é e como foi desenhado.
2. `docs/ARQUITETURA.md` — arquitetura e **regras do código** (obrigatórias).
3. `docs/STATUS.md` — o que já está implementado e o que está em andamento.
4. `docs/DIVIDAS_TECNICAS.md` — o que sabemos que está incompleto ou feito de um jeito provisório.
5. `docs/INCIDENTES.md` — o que já deu errado, para não repetir.
6. `docs/CHANGELOG.md` — o mapa de todas as mudanças e implementações já feitas.

## Documentos vivos (obrigatório)

Toda mudança de código vem **no mesmo commit** com a atualização dos documentos afetados:

| Aconteceu isto | Atualize |
|---|---|
| Mudou a arquitetura, uma camada, uma dependência ou uma regra | `docs/ARQUITETURA.md` (incluindo o Registro de Decisões) |
| Começou, terminou ou bloqueou um item de um marco | `docs/STATUS.md` |
| Fez algo provisório, pulou um caso, deixou um TODO | `docs/DIVIDAS_TECNICAS.md` |
| Algo quebrou, uma hipótese se provou falsa, um teste real falhou | `docs/INCIDENTES.md` |
| Mudou escopo ou comportamento do produto | `docs/PLANO.md` |
| **Qualquer commit** | `docs/CHANGELOG.md` — sempre, sem exceção |

`TODO` no código sem uma entrada correspondente em `DIVIDAS_TECNICAS.md` não é permitido.

## Regras inegociáveis (resumo — detalhes em ARQUITETURA.md)

- **A ISO do Windows nunca é modificada.** Tudo vai para a pasta `WinKit/` no pendrive Ventoy.
- **Nada pesado vai para dentro da ISO**, nem backup, nem instalador, nem driver.
- **Nunca particionar, formatar ou apagar discos.** O `autounattend.xml` nunca contém `DiskConfiguration`.
- **Restauração é aditiva por padrão** (mesclar sem sobrescrever). Sobrescrever só com escolha explícita na receita.
- `winkit/core` não importa `winkit/platform`, Qt, `winreg`, `subprocess` nem nada específico de Windows.
- Nenhum `subprocess` com `shell=True`. Todo comando externo passa por `winkit.platform.runner`.
- **Nunca interpretar texto de saída localizado** (o Windows do usuário é pt-BR). Use JSON, CIM, registro ou códigos de saída.
- Identificadores de código em inglês; textos para o usuário, documentação e mensagens de commit em português (pt-BR).
