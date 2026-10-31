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

## 2026-10-31 — M5 — Aplicativos
**Tipo:** implementação + correção + testes + documentação
**Resumo:** lê os apps instalados no PC atual, sugere a fonte de cada um (winget, instalador offline), baixa instaladores para o pendrive e instala no Windows novo (offline na Fase 1, winget na Fase 2), com pós-instalação silenciosa.

### Adicionado
- `src/winkit/core/inventory.py`, `core/winget_manifest.py`, `core/installers/detect.py`
- `src/winkit/platform/inventory.py`, `winget.py`, `installers.py`, `shortcuts.py`, `fakes/apps.py`
- `src/winkit/collector/apps.py`
- `src/winkit/agent/steps/app.py` — `AppStep`, `ShortcutStep`, `after_install`, `create_shortcuts`
- CLI: `coletar apps`, `apps listar|marcar|desmarcar|baixar|adicionar`
- Testes: `tests/core/test_inventory.py`, `test_winget_manifest.py`, `test_installer_detect.py`, `tests/collector/test_apps.py`, `tests/agent/test_app_step.py`, caso de ponta a ponta em `tests/cli/test_cli.py`
- `docs/validacao/M5.md`

### Alterado
- `src/winkit/agent/steps/base.py` — `StepContext.wait` e `winget_wait_seconds`
- `src/winkit/agent/executor.py` — `Waits.winget_seconds`; repassa a espera às etapas
- `src/winkit/agent/services.py`, `platform/services.py`, fakes — inventário, winget, instaladores, atalhos
- `src/winkit/core/recipe/validation.py` — exigências de instalação só para apps marcados (IN-006)
- `src/winkit/cli/main.py` — parser dividido em funções

### Documentos vivos atualizados
- STATUS — M5; ARQUITETURA — módulos; DIVIDAS — DT-013, DT-014; INCIDENTES — IN-006, IN-007

---

## 2026-10-31 — M4 — Drivers
**Tipo:** implementação + testes + documentação
**Resumo:** coleta e exportação de drivers de terceiros no PC atual, instalação com `pnputil` na Fase 1 com verificação de integridade, e manifesto do pendrive gravado pelo `construir`.

### Adicionado
- `src/winkit/platform/drivers.py` — `WindowsDriverManager`, `InstalledDriver`, `DriverInstallResult`
- `src/winkit/platform/fakes/drivers.py`, `platform/fakes/services.py` (`fake_services`)
- `src/winkit/collector/drivers.py` — `list_candidates`, `export_drivers`, `DriverCandidate`
- `src/winkit/agent/integrity.py` — `verify_payload`
- `src/winkit/agent/steps/driver.py` — `DriverStep`
- `src/winkit/agent/fakes.py` — `fake_agent_services`
- `src/winkit/core/text.py` — `slugify`, `human_size`
- `src/winkit/core/fsutil.py` — `write_if_changed`
- Registro: `subkeys` e `values` (real e falso)
- CLI: `winkit coletar drivers`
- Testes: `tests/collector/test_drivers.py`, `tests/agent/test_driver_step.py`, novo caso em `tests/cli/test_cli.py`
- `docs/validacao/M4.md`

### Alterado
- `src/winkit/builder/build.py` — manifesto (fora do `--somente-xml`), tamanhos por categoria, gravação só quando o conteúdo muda
- `src/winkit/agent/services.py`, `platform/services.py` — campo `drivers`
- `src/winkit/agent/steps/registry.py` — `driver` deixa de ser "não implementada"

### Documentos vivos atualizados
- STATUS — M4; ARQUITETURA — tabela de módulos

---

## 2026-10-31 — M3 — Correções vindas do CI Windows
**Tipo:** correção
**Resumo:** o CI Windows revelou dois problemas reais no `bootstrap.ps1` (codificação e erro silencioso) e um de quebras de linha no snapshot. Corrigidos com testes.

### Adicionado
- `.gitattributes` — LF em todos os arquivos de texto
- `tests/builder/test_bootstrap_ps1.py` — `test_script_has_utf8_bom`, `test_builder_copies_script_byte_for_byte`

### Alterado
- `src/winkit/builder/assets/bootstrap.ps1` — UTF-8 com BOM; `ErrorActionPreference = 'Stop'` no bloco principal; `catch` protegido
- `tests/builder/test_build.py` — leitura do script com `utf-8-sig`

### Documentos vivos atualizados
- INCIDENTES — IN-004, IN-005

---

## 2026-10-31 — M3 — Agente: fases, executor, resumo, limpeza e empacotamento
**Tipo:** implementação + infraestrutura + testes + documentação
**Resumo:** o Agente roda de ponta a ponta (Fase 1 antes do login, Fase 2 depois), retoma após reinício, cai no fallback se a Fase 1 não rodar, gera o resumo e limpa tudo. Os executáveis `winkit.exe` e `winkit-agent.exe` são gerados e testados no CI Windows.

### Adicionado
- `src/winkit/platform/registry.py`, `scheduler.py`, `accounts.py`, `environment.py`, `known_folders.py`
- `src/winkit/platform/fakes/registry.py`, `fakes/system.py`
- `src/winkit/core/summary.py` — `Summary`, `build_summary`, `render_html`, `format_duration`
- `src/winkit/core/state/models.py` — `mark_deferred`
- `src/winkit/agent/paths.py`, `eventlog.py`, `pendrive.py`, `progress.py` (`AgentUi`, `NullUi`, `Choice`), `services.py`, `store.py`, `executor.py`, `phases.py`, `cleanup.py`, `ui_select.py`, `main.py`
- `src/winkit/agent/steps/base.py` (`StepContext`, `StepResult`, `StepHandler`, `local_path`), `steps/registry.py`, `steps/finalize.py`
- `packaging/entry_agent.py`, `entry_cli.py`, `winkit-agent.spec`, `winkit.spec`, `build.ps1`, `LEIA-ME.txt`
- `.github/workflows/ci.yml` — job "Empacotar executáveis (Windows)" com teste de fumaça e artefato `WinKit-windows`
- Testes: `tests/agent/helpers.py`, `test_executor.py`, `test_phases.py`
- `docs/validacao/M3.md`

### Alterado
- `src/winkit/cli/main.py` — usa o Agente do pacote automaticamente (`default_agent_source`)
- `pyproject.toml` — `E501` liberado nos módulos de plataforma (scripts PowerShell embutidos)

### Documentos vivos atualizados
- STATUS — M3 com código concluído
- ARQUITETURA — D-024, D-025; tabela de módulos
- DIVIDAS — DT-012 (Fase 2 sem janela até o M9)

### Decisões
- D-024 (resumo HTML estático; remoção condicional do Agente)
- D-025 (pacote em duas pastas onedir)

---

## 2026-10-31 — M2 — Correção de lint e script de verificação
**Tipo:** correção + infraestrutura
**Resumo:** corrige os avisos de lint enviados no commit do M2 e cria o `scripts/check.sh`, obrigatório antes de cada commit.

### Adicionado
- `scripts/check.sh` — ruff, formatação, mypy, import-linter e pytest, parando no primeiro erro

### Alterado
- `pyproject.toml` — `S314` (parse de XML) liberado nos testes, que leem XML gerado pelo próprio WinKit
- `tests/builder/test_bootstrap_ps1.py`, `tests/builder/test_build.py` — avisos do ruff
- `CLAUDE.md` — seção "Antes de cada commit"

### Documentos vivos atualizados
- INCIDENTES — IN-003

---

## 2026-10-31 — M2 — Construtor mínimo (XML, Ventoy, bootstrap, CLI)
**Tipo:** implementação + testes + documentação
**Resumo:** o WinKit já prepara um pendrive Ventoy de verdade: lê as ISOs sem alterá-las, gera um `autounattend.xml` por idioma/arquitetura, mescla o `ventoy.json` com segurança, grava o `bootstrap.ps1` e valida o resultado. Primeira versão utilizável da linha de comando.

### Adicionado
- `src/winkit/core/isos.py` — `IsoInfo`, `IsoEdition`, conversões de versão/arquitetura/idioma
- `src/winkit/core/layout.py` — caminhos do pendrive, `Marker` (`pendrive_id`)
- `src/winkit/core/ventoy/detect.py` — `PartitionRow`, `VentoyTarget`, `find_ventoy_targets`
- `src/winkit/core/ventoy/config.py` — `merge_auto_install`, `winkit_entries`, `parse_config`
- `src/winkit/core/unattend/commands.py` — `bootstrap_command`, `first_logon_command`, `reg_add_command`, `labconfig_commands` (limite de 259 caracteres)
- `src/winkit/core/unattend/generator.py` — `generate_unattend`, `check_safety`, `encode_password`, `template_name`
- `src/winkit/platform/disks.py` — `WindowsDiskInspector` (partições, leitura de ISO) + conversões JSON
- `src/winkit/platform/fakes/disks.py` — `FakeDiskInspector`, `ventoy_rows`, `windows_iso`
- `src/winkit/platform/session.py` — `is_admin`
- `src/winkit/platform/services.py` — `Services`, `real_services`
- `src/winkit/builder/target.py`, `isos.py`, `build.py`, `validate.py`
- `src/winkit/builder/assets/bootstrap.ps1`
- `src/winkit/cli/main.py` — comandos `pendrive listar`, `receita nova`, `plano`, `construir`, `validar`
- Testes: `tests/core/test_unattend.py` (inclui snapshot `tests/fixtures/unattend_default.xml`), `test_ventoy.py`, `test_isos.py`, `tests/platform/test_disks.py`, `tests/builder/test_build.py`, `tests/builder/test_bootstrap_ps1.py` (Windows), `tests/cli/test_cli.py`
- `docs/validacao/AMBIENTE_VM.md`, `docs/validacao/M2.md`

### Alterado
- `pyproject.toml` — `T20` liberado só na CLI

### Documentos vivos atualizados
- STATUS — M2 com código concluído e validação na VM pendente; H11
- PLANO — §9.2 (forma real do comando de bootstrap), §10.1/§10.3 (caminho do Agente, SID, FirstLogonCommands), H11
- ARQUITETURA — D-023
- INCIDENTES — IN-002 (backup do `ventoy.json`)

### Decisões
- D-023 (três caminhos para iniciar o Agente)

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
