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

## 2026-10-31 — M1 — Núcleo puro + catálogos + criptografia desligada por padrão
**Tipo:** implementação + correção + documentação
**Resumo:** toda a lógica de decisão testável no Linux: receita, validação, moldes de caminho, catálogos de dados, planejador de fases, estado do Agente e manifesto. Corrige a falha de CI do M0 (IN-001) e registra o pedido do usuário de deixar a criptografia automática desligada por padrão (D-020).

### Adicionado
- `src/winkit/core/recipe/models.py` — `Recipe` e submodelos (`Meta`, `Execution`, `WindowsSettings`, `Account`, `Updates`, `DriverItem`, `InstallerSpec`, `AfterInstall`, `AppItem`, `BackupItem`, `Bloatware`, `TweakSelection`, `Power`); `prevent_device_encryption=True` por padrão
- `src/winkit/core/recipe/io.py` — `load_recipe`, `dump_recipe`, `recipe_hash`, `new_recipe`, `migrate`
- `src/winkit/core/recipe/validation.py` — `validate_recipe`, `ensure_valid`, `find_cycle`, `payload_path_problem`, `username_problem`, `validate_computer_name`
- `src/winkit/core/paths/templates.py` — `to_template`, `parse`, `resolve`, `profile_folders`, `retarget`, `normalize`
- `src/winkit/core/catalog/models.py` — modelos de ajuste (8 operações tipadas), bloatware, app, edição, assinatura de instalador, padrão DPAPI, classe de driver
- `src/winkit/core/catalog/loader.py` — `load_catalogs`, `default_catalogs`
- `src/winkit/data/` — `tweaks.yaml`, `bloatware.yaml`, `app_catalog.yaml`, `editions.yaml`, `installer_signatures.yaml`, `dpapi_patterns.yaml`, `default_excludes.yaml`, `driver_classes.yaml`
- `src/winkit/core/planner/models.py`, `planner.py` — `Plan`, `PlannedStep`, `PlanContext`, `ExcludedItem`, `plan()`
- `src/winkit/core/state/models.py` — `AgentState`, transições, `recover_interrupted`, `reset_for_retry`, `phase_complete`
- `src/winkit/core/manifest/manifest.py` — `scan`, `diff`, `verify`, `verify_tree`
- `src/winkit/core/fsutil.py` — `atomic_write_text`, `atomic_write_bytes`
- `src/winkit/i18n/pt_br.py` — títulos de etapas e motivos de exclusão
- Testes: `tests/factories.py`, `tests/core/test_recipe.py`, `test_validation.py`, `test_templates.py`, `test_planner.py`, `test_state.py`, `test_manifest.py`, `tests/data/test_catalogs.py`

### Alterado
- `pyproject.toml` — removido `force-include` de `data/` (IN-001); `A005` ignorado nos testes
- `data/` → `src/winkit/data/` (D-021); referências atualizadas no PLANO e na ARQUITETURA

### Documentos vivos atualizados
- STATUS — M1 concluído
- PLANO — D-020 na receita e no §14.2; notas de implementação no §6.1 e no §11.2
- ARQUITETURA — D-020, D-021, D-022; tabela de módulos
- DIVIDAS — DT-010 (catálogos não validados em Windows real), DT-011 (valores protegidos por UCPD)
- INCIDENTES — IN-001

### Decisões
- D-020 (criptografia automática desligada por padrão — pedido do usuário)
- D-021 (catálogos dentro do pacote)
- D-022 (`core` pode ler/gravar arquivos comuns)

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
