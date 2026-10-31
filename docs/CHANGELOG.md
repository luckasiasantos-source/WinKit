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

## 2026-10-31 — M11 — Base da tradução (pt-BR, en-US, es)
**Tipo:** implementação + documentação
**Resumo:** plano da v2 aprovado. Decisões e regras novas registradas; o módulo de tradução passa a ter três idiomas, plural, mensagens estruturadas e formatação por idioma.

### Adicionado
- `src/winkit/i18n/{core,languages,msg,format}.py` — `t`, `tn`, `Plural`, `render`, `set_language`, `normalize`, `Msg`, `format_size/duration/datetime`
- `src/winkit/i18n/messages/{en_us,es}.py` — traduções de todas as chaves existentes
- `tests/i18n/` — paridade de chaves, marcadores e plurais (R-51), núcleo, idiomas e formatação
- Contrato do import-linter: `winkit.i18n` é puro

### Alterado
- `src/winkit/i18n/pt_br.py` → `src/winkit/i18n/messages/pt_br.py`; contagens viram plurais de verdade (`tn`)
- `src/winkit/core/text.py` — reexporta `Msg`
- `tests/conftest.py` — todo teste começa e termina em pt-BR

### Removido
- `tests/test_i18n.py` — substituído por `tests/i18n/`

### Documentos vivos atualizados
- ARQUITETURA — D-030 a D-042, R-03/R-04/R-19 alteradas, D-018 alterada, R-51 a R-55
- STATUS — v2 aprovada; M11 em andamento; DIVIDAS — DT-016, DT-017
- PLANO_V2 e PLANO — plano marcado como aprovado

### Decisões
- D-030 a D-042 (novas); D-018 (alterada)

## 2026-10-31 — Planejamento v2 — Plano detalhado M11 a M18
**Tipo:** documentação
**Resumo:** plano minucioso da v2, aguardando aprovação: tradução para inglês e espanhol e 23 funções novas, em 8 marcos, com decisões, regras, hipóteses, riscos, testes e checklists.

### Adicionado
- `docs/PLANO_V2.md` — escopo (V2-00 a V2-23), decisões propostas D-030 a D-042, mudanças de regra (R-03, R-04, R-19) e regras novas R-51 a R-55, arquitetura transversal (receita, catálogos, layout, planejador R16–R33, contrato de etapa, plataforma, volumes, segredos, Studio, CLI), detalhamento de cada função por marco, hipóteses H12–H34, riscos, dívidas previstas, estratégia de testes, ordem e versões, rastreabilidade e checklists

### Alterado
- `CLAUDE.md` — `PLANO_V2.md` na ordem de leitura e na tabela de documentos vivos
- `docs/PLANO.md` — §20 aponta para o plano da v2

### Documentos vivos atualizados
- STATUS — M11 a M18 como "planejado, aguardando aprovação"

## 2026-10-31 — Fechamento — Correção: workflow de release
**Tipo:** correção
**Resumo:** a primeira release falhou porque o código 1 esperado do `gh release view` encerrava o passo (IN-012).

### Alterado
- `.github/workflows/release.yml` — zera `$LASTEXITCODE` depois de conferir que a release não existe

### Documentos vivos atualizados
- INCIDENTES — IN-012

## 2026-10-31 — Fechamento — Licença Apache-2.0, aviso de uso por conta e risco e releases
**Tipo:** documentação + implementação + infraestrutura
**Resumo:** o projeto passa a ser código aberto sob a Apache-2.0, com aviso em destaque de que é um pré-alpha pessoal (quem usa é testador), 100% vibe-codado e de que toda a responsabilidade é de quem usa. Versões prontas para baixar passam a ser publicadas na página de Releases a cada tag `vX.Y.Z`.

### Adicionado
- `LICENSE` — texto da Apache License 2.0
- `NOTICE` — direitos autorais e aviso de isenção (pt-BR e inglês)
- `tests/ui/test_studio_ui.py` — teste de que a primeira página do Studio mostra o aviso
- `.github/workflows/release.yml` — tag `vX.Y.Z` ou disparo manual → testes, pacote, fumaça, `.zip` + SHA-256, release (pré-lançamento)
- `packaging/smoke.ps1` — teste de fumaça dos executáveis, extraído do CI para ser usado também na release
- `packaging/NOTAS_DA_VERSAO.md` — texto da página da release, com o aviso

### Alterado
- `README.md` — aviso em destaque no topo, selos de licença e "vibe-codado", seções Aviso e Licença
- `src/winkit/studio/ui/pages.py` — `DISCLAIMER` e seção "Aviso" na página Pendrive
- `packaging/LEIA-ME.txt`, `packaging/build.ps1` — aviso no LEIA-ME; o pacote leva `LICENSE` e `NOTICE`
- `pyproject.toml` — `license = "Apache-2.0"`
- `CONTRIBUTING.md` — licença das contribuições e como publicar uma versão
- `.github/workflows/ci.yml` — o teste de fumaça chama `packaging/smoke.ps1`
- `README.md` — o download passa a ser pela página de Releases

### Documentos vivos atualizados
- ARQUITETURA — D-028, D-029; PLANO — §18 (arquivos novos) e §22 (risco do código escrito por IA); DIVIDAS — DT-015 quitada; STATUS — licença e aviso, repositório público pendente

### Decisões
- D-028, D-029 (novas)

## 2026-10-31 — Fechamento — README e guia de contribuição
**Tipo:** documentação
**Resumo:** README completo para código aberto (o que é, recursos, capturas, como funciona, uso pelo Studio e pela CLI, compilação, arquitetura) e guia de contribuição. Revisão final dos documentos vivos.

### Adicionado
- `CONTRIBUTING.md` — como preparar o ambiente, regras do código, documentos vivos, o que é bem-vindo e como relatar testes em VM

### Alterado
- `README.md` — reescrito para código aberto, com capturas de `docs/imagens/`

### Documentos vivos atualizados
- DIVIDAS — DT-013 e DT-014 voltam a "aberta" (IN-011); DT-015 nova (licença não definida)
- INCIDENTES — IN-011
- STATUS — README e guia de contribuição no item de planejamento

## 2026-10-31 — M10 — Correção: mypy no modo Windows
**Tipo:** correção + infraestrutura
**Resumo:** corrige um erro de tipo que só o mypy no Windows enxergava e passa a rodar o mypy também em `--platform win32`, localmente e no CI (IN-010).

### Alterado
- `src/winkit/platform/power.py` — conversão explícita do contador do Windows
- `scripts/check.sh`, `.github/workflows/ci.yml` — `mypy --platform win32`

### Documentos vivos atualizados
- INCIDENTES — IN-010; ARQUITETURA — §5.12

---

## 2026-10-31 — M10 — WinKit Studio (GUI estilo macOS)
**Tipo:** implementação + infraestrutura + testes + documentação
**Resumo:** o aplicativo gráfico para o PC atual, com o visual pedido pelo usuário (estilo "Ajustes do Sistema" do Mac): todas as escolhas da receita sem editar arquivos, e "Construir pendrive" com um clique.

### Adicionado
- `src/winkit/studio/controller.py` — `StudioController`
- `src/winkit/studio/ui/base.py` — `Page`, `TaskRunner`, `WorkingSheet`, `show_error`
- `src/winkit/studio/ui/pages.py` — 10 páginas
- `src/winkit/studio/ui/window.py` — `StudioWindow`, `SECTIONS`
- `src/winkit/studio/main.py` — entrada da GUI (`--teste-fumaca`)
- `src/winkit/ui/widgets.py` — `SegmentedControl`, `ask_pill`
- `packaging/entry_studio.py`, `winkit-studio.spec`, `make_icon.py`
- Testes: `tests/studio/test_controller.py`, `tests/ui/test_studio_ui.py`
- `docs/imagens/studio-*.png`, `docs/validacao/M10.md`

### Alterado
- `src/winkit/ui/theme.py` — controle segmentado, botões "Perguntar", seta desenhada das listas, títulos da barra lateral
- `src/winkit/platform/registry.py` — `winreg` carregado no primeiro uso
- `packaging/*.spec`, `build.ps1`, `LEIA-ME.txt` — ícone, Studio no pacote
- `.github/workflows/ci.yml` — fumaça do Studio empacotado
- `.gitignore` — ícone gerado

### Documentos vivos atualizados
- STATUS — M10 e fase do projeto; ARQUITETURA — D-027, módulos

### Decisões
- D-027 (Studio como executável próprio, com elevação)

---

## 2026-10-31 — M9 — Janela do Agente (estilo macOS)
**Tipo:** implementação + testes + documentação
**Resumo:** a Fase 2 ganha a interface pedida: janela no estilo macOS com contagem regressiva, modo interativo, escolhas na hora e progresso por etapa; modo silencioso só com bandeja e notificação.

### Adicionado
- `src/winkit/ui/__init__.py`, `ui/theme.py`, `ui/widgets.py` — kit visual (D-026)
- `src/winkit/agent/ui/qt.py` — `QtAgentUi`, `AgentWindow`, `ChoosePage`, `ProgressPage`, `DonePage`, `RebootDialog`
- `docs/imagens/agente-*.png` — capturas (claro e escuro)
- Testes: `tests/ui/conftest.py`, `tests/ui/test_agent_ui.py` (offscreen)
- `docs/validacao/M9.md`

### Alterado
- `src/winkit/agent/ui_select.py` — escolhe janela/bandeja/nada conforme o modo
- `src/winkit/agent/main.py` — `run_phase2_with_ui`
- `src/winkit/agent/phases.py` — `load_agent_recipe` público
- `src/winkit/agent/progress.py`, `executor.py` — `step_result`
- `src/winkit/i18n/pt_br.py` — textos da interface
- `pyproject.toml` — contratos do import-linter para o kit visual; regras de lint para código de interface
- `.gitattributes` — PNG como binário

### Documentos vivos atualizados
- STATUS — M9; ARQUITETURA — D-026, módulos; DIVIDAS — DT-012 quitada

### Decisões
- D-026 (interface estilo macOS)

---

## 2026-10-31 — M8 — Correção: atalho de app portátil e isolamento dos testes
**Tipo:** correção
**Resumo:** corrige o molde `{ABS:pasta}\arquivo` usado pelos atalhos de apps portáteis e isola os testes de discos e do navegador reais (IN-009).

### Alterado
- `src/winkit/core/paths/templates.py` — `{ABS:...}` aceita sufixo (caminho dentro da pasta)
- `src/winkit/agent/main.py` — `open_file` substituível
- `tests/agent/test_app_step.py` — unidade `Q:` + novo teste do caminho de sucesso dos atalhos
- `tests/agent/test_phases.py` — `summary` sem abrir navegador
- `tests/core/test_templates.py` — `test_abs_with_suffix_is_a_path_inside_the_folder`

### Documentos vivos atualizados
- INCIDENTES — IN-009

---

## 2026-10-31 — M8 — Windows Update, política de reinício e "tentar de novo"
**Tipo:** implementação + testes + documentação
**Resumo:** última etapa da Fase 2: Windows Update pela API oficial; reinício conforme a política da receita; atalho para tentar de novo o que falhou. Com isso, todos os tipos de etapa do Agente estão implementados.

### Adicionado
- `src/winkit/platform/windows_update.py` — `ComWindowsUpdater`, `UpdateResult`
- `src/winkit/platform/power.py` — `WindowsSessionControl`
- `src/winkit/agent/steps/windows_update.py` — `WindowsUpdateStep`
- `src/winkit/agent/reboot.py` — `handle_reboot`
- `FakeUpdater`, `FakeSession`
- Testes: `tests/agent/test_update_and_reboot.py`
- `docs/validacao/M8.md`

### Alterado
- `src/winkit/agent/steps/finalize.py` — atalho "tentar de novo" quando há falha
- `src/winkit/agent/phases.py` — aplica a política de reinício; limpa o sinal de reinício a cada nova sessão
- `src/winkit/agent/steps/registry.py` — nenhum tipo de etapa pendente de implementação
- `src/winkit/agent/services.py`, `agent/fakes.py` — `updater`, `session`

### Documentos vivos atualizados
- STATUS — M8; ARQUITETURA — módulos

---

## 2026-10-31 — M7 — Bloatware, ajustes, energia e nome do computador
**Tipo:** implementação + testes + documentação
**Resumo:** o Agente remove os apps escolhidos e impede que voltem, aplica os ajustes de privacidade/visual/sistema no perfil Default (a conta já nasce configurada), ajusta energia e renomeia o computador quando decidido na hora.

### Adicionado
- `src/winkit/platform/appx.py`, `features.py`, `fakes/system_tweaks.py`
- `src/winkit/agent/steps/tweak.py` — `TweakStep`, `locate`, `apply_op`, `registry_scope`
- `src/winkit/agent/steps/system.py` — `BloatStep`, `PowerStep`, `RenameComputerStep`
- Registro: `create_key`
- `AgentState.computer_name_choice`
- Testes: `tests/agent/test_system_steps.py` (inclui todos os ajustes do catálogo em todos os alvos)
- `docs/validacao/M7.md`

### Alterado
- `src/winkit/agent/services.py`, `agent/fakes.py` — `appx`, `features`
- `src/winkit/agent/steps/registry.py` — só `windows_update` segue pendente de implementação
- `src/winkit/agent/phases.py` — guarda o nome do PC escolhido na janela

### Documentos vivos atualizados
- STATUS — M7; ARQUITETURA — módulos

---

## 2026-10-31 — M6 — Backups de configuração
**Tipo:** implementação + testes + documentação
**Resumo:** o pedido central do usuário: escolher pastas (ou arquivos) de configuração no PC atual, guardar em pasta crua no pendrive com cópia de sombra e restaurar no lugar certo do Windows novo antes do primeiro uso do app.

### Adicionado
- `src/winkit/platform/copy.py` — `RobocopyCopier`, `PythonCopier`, `split_excludes`, `is_excluded`, `tree_stats`, `ensure_mirror_target`
- `src/winkit/platform/vss.py` — `WindowsShadowCopies`, `Snapshot`, `PendingSnapshots`
- `src/winkit/platform/fakes/backup.py` — `FakeShadowCopies`, `FakeOldPcFolders`
- `src/winkit/collector/backups.py` — `suggest`, `add_backup`, `add_suggestion`, `add_portable_app`, `capture`, `dpapi_warnings`, `cleanup_orphan_snapshots`
- `src/winkit/agent/steps/backup.py` — `BackupStep`
- CLI: `coletar backups`, `backup adicionar|listar|capturar|remover`, `apps portatil`, `sincronizar`
- Testes: `tests/platform/test_copy.py` (inclui robocopy real com caminho > 260 no Windows), `tests/collector/test_backups.py`, `tests/agent/test_backup_step.py`, fluxo completo em `tests/cli/test_cli.py`, `test_catalogs_roundtrip_through_dump`
- `docs/validacao/M6.md`

### Alterado
- `src/winkit/platform/services.py` — `copier`, `vss`, `folders`, `volume_root`
- `src/winkit/agent/services.py`, `agent/fakes.py` — `copier`
- `src/winkit/core/catalog/models.py` — validação de `TweakOp` por campos preenchidos

### Documentos vivos atualizados
- STATUS — M6; ARQUITETURA — módulos

---

## 2026-10-31 — M5 — Correção: arquivo inválido no repositório quebrava o CI Windows
**Tipo:** correção
**Resumo:** remove um log criado por engano com o nome literal `C:\ProgramData\...` (inválido no Windows), impede que isso se repita e adiciona testes de proteção.

### Removido
- `C:\ProgramData/WinKit/Logs/agente-erro-fatal.log` — lixo de teste (IN-008)

### Alterado
- `src/winkit/platform/system.py` — `program_data()` nunca devolve caminho relativo
- `.gitignore` — bloqueia nomes com letra de unidade
- `tests/test_architecture.py` — `test_no_windows_drive_paths_tracked`, `test_program_data_is_never_relative`

### Documentos vivos atualizados
- INCIDENTES — IN-008

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
