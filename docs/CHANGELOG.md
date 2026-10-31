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

## 2026-10-31 — M0 — Fundação do projeto
**Tipo:** infraestrutura + implementação
**Resumo:** projeto Python configurado (uv, ruff, mypy, pytest, import-linter), CI Linux + Windows, e os primeiros módulos de base: erros, textos pt-BR, executor de comandos e PowerShell.

### Adicionado
- `pyproject.toml` — metadados, dependências (pydantic, PyYAML, PySide6), grupos `dev` e `package`, configuração de ruff/mypy/pytest/coverage e 5 contratos do import-linter
- `uv.lock` — versões travadas (R-45)
- `.gitignore`
- `.github/workflows/ci.yml` — matriz `ubuntu-latest` + `windows-latest`: ruff, mypy, import-linter, pytest com cobertura, artefatos de resultado
- `src/winkit/__init__.py` — versão 0.1.0 (R-46)
- Pacotes vazios da estrutura do `PLANO.md` §18 (`core/*`, `platform`, `collector`, `builder`, `agent`, `studio`, `cli`)
- `src/winkit/core/errors.py` — `WinKitError` e subclasses (receita, catálogo, caminhos, plano, estado, Ventoy, XML, plataforma, comando, PowerShell, registro, VSS, pendrive, operação insegura, integridade, etapa)
- `src/winkit/i18n/pt_br.py` — todos os textos ao usuário + `t(chave, **campos)`
- `src/winkit/platform/system.py` — `system32()`, `powershell_exe()`, `winkit_program_data()`, `CREATE_NO_WINDOW`
- `src/winkit/platform/runner.py` — `CommandResult`, protocolo `CommandRunner`, `SubprocessRunner`, máscara de segredos, decodificação de saída só para log
- `src/winkit/platform/powershell.py` — `PowerShell.run_json()` / `run()`; parâmetros nunca interpolados (JSON→Base64→`$p`), script por `-EncodedCommand`
- `src/winkit/platform/fakes/runner.py`, `fakes/powershell.py` — dublês para testes
- `tests/conftest.py` — marcadores `windows`/`admin` pulados fora do Windows/sem administrador
- `tests/platform/test_runner.py`, `tests/platform/test_powershell.py`, `tests/test_i18n.py`
- `tests/test_architecture.py` — testes de proteção (§19.2 do plano)

### Documentos vivos atualizados
- STATUS — M0 concluído
- ARQUITETURA — R-50 (formato `TODO(DT-nnn)`) e §5.12 (como cada regra é verificada)

### Decisões
- nenhuma nova

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
