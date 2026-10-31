# WinKit — Mapa de Mudanças

> Documento vivo. **Todo commit adiciona uma entrada aqui** (ver `CLAUDE.md`, R-49).
> Entradas mais recentes no topo. Cada entrada lista o que mudou, em que arquivos, e se mexeu em comportamento, documentos ou decisões.

## Formato

```
## AAAA-MM-DD — Marco — título
**Tipo:** implementação | correção | refatoração | documentação | testes | infraestrutura
**Resumo:** uma ou duas frases.

### Adicionado
- `caminho/arquivo` — o que faz

### Alterado
- `caminho/arquivo` — o que mudou e por quê

### Removido
- `caminho/arquivo` — por quê

### Documentos vivos atualizados
- STATUS / DIVIDAS / INCIDENTES / ARQUITETURA / PLANO — o que mudou em cada

### Decisões
- D-nnn (nova/alterada), se houver
```

---

## 2026-10-31 — Planejamento — documentação inicial do projeto
**Tipo:** documentação
**Resumo:** plano completo do produto, arquitetura, regras do código e documentos vivos. Nenhum código ainda.

### Adicionado
- `CLAUDE.md` — regras obrigatórias para quem mexe no repositório e tabela de quais documentos atualizar em cada tipo de mudança
- `README.md` — apresentação curta do projeto e índice da documentação
- `docs/PLANO.md` — produto, decisões, escopo (v1/depois/fora), arquitetura, layout do pendrive, receita, Coletor, Construtor, `autounattend.xml`, Agente (bootstrap, fases, planejador, estado, modos, interface), motores, bloatware e ajustes, catálogos, segurança, stack, estrutura do repositório, testes, marcos M0–M10, hipóteses H1–H10, riscos, rastreabilidade
- `docs/ARQUITETURA.md` — camadas e regra de dependência, módulos, contratos, regras R-01 a R-49, decisões D-001 a D-019
- `docs/STATUS.md` — estado por marco e das hipóteses
- `docs/DIVIDAS_TECNICAS.md` — dívidas de desenho DT-001 a DT-009
- `docs/INCIDENTES.md` — formato e lições L-001 a L-007 da fase de desenho
- `docs/CHANGELOG.md` — este arquivo
- `docs/validacao/README.md` — modelo dos roteiros de validação em hardware real

### Decisões
- D-001 a D-019 (todas novas)
