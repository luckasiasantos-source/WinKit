# WinKit — Status da Implementação

> Documento vivo. Mostra **o que existe de verdade no código** neste momento, marco por marco.
> Atualizado no mesmo commit de toda mudança que começa, conclui ou bloqueia um item.
>
> Legenda: ⬜ não iniciado · 🟨 em andamento · ✅ concluído · ⛔ bloqueado · ➖ fora do escopo atual

**Última atualização:** 2026-10-31
**Versão do código:** 0.1.0 (pré-alpha, projeto pessoal)
**Fase do projeto:** v1 implementada (M0–M10); falta a validação em VM/PC real pelos roteiros de `docs/validacao/`. v2 (M11–M18) aprovada e em implementação (`PLANO_V2.md`)

## Resumo

| Marco | Descrição | Estado | Validação em hardware |
|---|---|---|---|
| — | Planejamento e documentação | ✅ | — |
| M0 | Fundação | ✅ | — |
| M1 | Núcleo puro | ✅ | — |
| M2 | Construtor mínimo + primeira instalação real | ✅ código | ⬜ roteiro pronto (`docs/validacao/M2.md`), aguardando execução na VM |
| M3 | Esqueleto do Agente | ✅ código | ⬜ roteiro pronto (`docs/validacao/M3.md`) |
| M4 | Drivers | ✅ código | ⬜ roteiro pronto (`docs/validacao/M4.md`) |
| M5 | Aplicativos | ✅ código | ⬜ roteiro pronto (`docs/validacao/M5.md`) |
| M6 | Backups | ✅ código | ⬜ roteiro pronto (`docs/validacao/M6.md`) |
| M7 | Bloatware e ajustes | ✅ código | ⬜ roteiro pronto (`docs/validacao/M7.md`) |
| M8 | Windows Update, resumo e notificações | ✅ código | ⬜ roteiro pronto (`docs/validacao/M8.md`) |
| M9 | Interface do Agente | ✅ código | ⬜ roteiro pronto (`docs/validacao/M9.md`) |
| M10 | WinKit Studio (GUI) | ✅ código | ⬜ roteiro pronto (`docs/validacao/M10.md`) |
| M11 | Inglês e espanhol (V2-00) | 🟨 em andamento | — |
| M12 | Aplicar neste PC + ponto de restauração (V2-03, V2-10) | ⬜ planejado | — |
| M13 | Pendrive comum: Rufus/Microsoft (V2-01) | ⬜ planejado | — |
| M14 | Rede e sistema (V2-02, 08, 09, 16, 17, 18, 22) | ⬜ planejado | — |
| M15 | Personalização (V2-04, 05, 06, 07, 12, 15) | ⬜ planejado | — |
| M16 | Contas, pastas e jogos (V2-11, 13, 14) | ⬜ planejado | — |
| M17 | Inteligência do pendrive (V2-19, 20, 21, 23) | ⬜ planejado | — |
| M18 | Fechamento da v2 | ⬜ planejado | — |

## Detalhe por marco

### Planejamento ✅
- ✅ Análise da conversa anterior (PDF) e correções técnicas
- ✅ Decisões D-001 a D-019 (`ARQUITETURA.md`)
- ✅ `PLANO.md`, `ARQUITETURA.md`, `STATUS.md`, `DIVIDAS_TECNICAS.md`, `INCIDENTES.md`, `CHANGELOG.md`, `CLAUDE.md`
- ✅ `README.md` e `CONTRIBUTING.md` para código aberto
- ✅ Licença Apache-2.0 (`LICENSE`, `NOTICE`) e aviso "100% vibe-codado, uso por conta e risco" no README, no pacote e no Studio (D-028)
- ⬜ Tornar o repositório público (feito pelo dono nas configurações do GitHub)
- ✅ Release por tag (`release.yml`, D-029); versões saem como pré-lançamento até a validação em VM

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

### M2 — Construtor mínimo ✅ (código) · validação na VM pendente
- ✅ `core/ventoy/detect.py` — detecção do Ventoy pela partição `VTOYEFI`
- ✅ `core/ventoy/config.py` — mesclagem do `ventoy.json` (preserva plugins e entradas de terceiros, remove entradas obsoletas só deste perfil)
- ✅ `core/isos.py` + `platform/disks.py` — partições e leitura de ISO somente leitura (`Mount-DiskImage -Access ReadOnly` + `Get-WindowsImage`), com cache
- ✅ `core/unattend/` — gerador do XML (windowsPE/specialize/oobeSystem), linhas de comando com limite de 259 caracteres, salvaguarda contra elementos de disco
- ✅ `core/layout.py` — layout do pendrive e marcador com `pendrive_id`
- ✅ `builder/` — alvo, leitura de ISOs, construção (XML por idioma/arquitetura, `ventoy.json`, bootstrap, cópia do Agente), validação do pendrive
- ✅ `builder/assets/bootstrap.ps1` — versão completa (cópia do Agente, receita, `SetupComplete.cmd`, tarefa pelo SID, log no pendrive, nunca falha a instalação)
- ✅ CLI: `pendrive listar`, `receita nova`, `plano`, `construir [--somente-xml] [--agente]`, `validar`, opção `--raiz` para simular o pendrive numa pasta
- ✅ Roteiros: `docs/validacao/AMBIENTE_VM.md` (Hyper-V) e `docs/validacao/M2.md`

**Testes:** 392 passando no Linux; testes reais do `bootstrap.ps1` e da listagem de partições rodam no CI Windows.

### M3 — Esqueleto do Agente ✅ (código) · validação na VM pendente
- ✅ Plataforma: `registry.py` (winreg + montagem de hive), `scheduler.py` (tarefa pelo SID), `accounts.py` (rede de segurança H11), `environment.py` (unidades, internet via NCSI, build, trava de instância única), `known_folders.py` (`SHGetKnownFolderPath`) + fakes
- ✅ `agent/executor.py` — contrato §4.2: falha isolada, dependências, espera de pendrive/internet sem gastar tentativa, desmarcado na janela, estado gravado antes/depois
- ✅ `agent/phases.py` — Fase 1 e Fase 2, fallback (D-012), retomada, receita local ou do pendrive, adiar, tentar de novo
- ✅ `agent/steps/finalize.py` + `agent/cleanup.py` — resumo JSON/HTML, atalho `.url` na área de trabalho, limpeza (tarefa, `SetupComplete.cmd`, Panther, Winlogon, receita local, remoção do Agente via `RunOnce`)
- ✅ `core/summary.py` — resumo e HTML autocontido com escape
- ✅ `agent/main.py` — `phase1 | phase2 [--first-logon] | retry | summary`; a Fase 1 sempre sai com 0; erro fatal vai para `agente-erro-fatal.log`
- ✅ Empacotamento: `packaging/*.spec`, `packaging/build.ps1`, job de CI "Empacotar" com teste de fumaça usando os executáveis prontos; artefato **WinKit-windows**
- ✅ Etapas de drivers/apps/backups/ajustes ainda como "não implementada" (preenchidas em M4–M8)
- ✅ Roteiro `docs/validacao/M3.md`

**Testes:** 417 passando; teste de proteção "Fase 1 não carrega Qt" agora ativo; CLI congelada testada localmente.

### M4 — Drivers ✅ (código) · validação na VM pendente
- ✅ `platform/drivers.py` — `Get-WindowsDriver -Online` (JSON), `pnputil /export-driver`, `pnputil /add-driver /subdirs /install` (só código de saída: 0, 3010, 259)
- ✅ `collector/drivers.py` — classificação pelo catálogo (recomendados, prioridade), exportação idempotente para `WinKit/Drivers/<classe>/...`, itens na receita
- ✅ `agent/steps/driver.py` + `agent/integrity.py` — verificação SHA-256 da pasta contra o manifesto antes de instalar (falha definitiva se adulterado ou sem manifesto)
- ✅ `construir` grava `WinKit/manifesto.json` (reaproveita hashes) e mostra espaço por categoria (item 25)
- ✅ `construir` agora é idempotente também no manifesto (`write_if_changed`)
- ✅ CLI: `winkit coletar drivers [--listar] [--todos] [--classe X]`
- ✅ Roteiro `docs/validacao/M4.md`
### M5 — Aplicativos ✅ (código) · validação na VM pendente
- ✅ `core/inventory.py` — filtros de ruído (§7.1.2), escopo por usuário, redistribuíveis, correspondência com o catálogo e com o `winget export` (heurística), sugestão de item para a receita, mescla que preserva escolhas
- ✅ `core/winget_manifest.py` — leitura do manifesto do `winget download`, tipos do winget → tipos do WinKit, divisão de argumentos no estilo Windows
- ✅ `core/installers/detect.py` — detecção por conteúdo (MSI/OLE, MSIX/ZIP, seção PE `.wixburn`, marcadores Inno/NSIS/Squirrel/InstallShield)
- ✅ Plataforma: `inventory.py` (registro + `Get-AppxPackage`), `winget.py` (export, download, install, list, registro do App Installer), `installers.py` (msiexec, MSIX via PowerShell, exe; `taskkill`), `shortcuts.py` (.lnk via WScript.Shell)
- ✅ `agent/steps/app.py` — instalador offline (hash, cópia local, códigos de sucesso/reinício, dica para instalar manualmente), winget online (registro + espera, adiamento), pós-instalação (encerrar processos, remover inicialização automática, atalhos), atalhos de apps portáteis
- ✅ `collector/apps.py` + CLI: `coletar apps`, `apps listar|marcar|desmarcar|baixar|adicionar` (com `--ordem` e `--decidir-na-hora`)
- ✅ Roteiro `docs/validacao/M5.md`
### M6 — Backups ✅ (código) · validação na VM pendente
- ✅ `platform/copy.py` — `RobocopyCopier` (espelho com exclusões, mesclar `/XC /XN /XO`, sobrescrever, pular, caminhos longos, código ≥ 8 = falha) e `PythonCopier` com a mesma semântica; salvaguarda R-20 (espelho só em `Backups/<id>/dados`)
- ✅ `platform/vss.py` — criar/apagar cópia de sombra via CIM, verificar se o volume suporta (NTFS interno), expor por link de diretório, lista de pendentes para limpar órfãs
- ✅ `collector/backups.py` — sugestões a partir do catálogo para os apps marcados (item 28), adicionar pasta/arquivo com tradução para molde (item 30), captura com uma cópia de sombra por volume sempre apagada no fim, estimativa de espaço antes de copiar (item 25), avisos DPAPI (item 16), `item.json`, apps portáteis
- ✅ `agent/steps/backup.py` — restauração no perfil Default (Fase 1) ou no perfil real (Fase 2/fallback), `{ABS}` com unidade ausente vira "pulado", arquivos soltos, políticas merge/overwrite/skip
- ✅ CLI: `coletar backups [--adicionar-recomendados]`, `backup adicionar|listar|capturar|remover`, `apps portatil`, `sincronizar` (item 27)
- ✅ `TweakOp` aceita catálogo exportado e lido de novo (contagem por campos preenchidos)
- ✅ Roteiro `docs/validacao/M6.md`
### M7 — Bloatware e ajustes ✅ (código) · validação na VM pendente
- ✅ `platform/appx.py` — remoção de pacote provisionado e instalado para todos os usuários; presença
- ✅ `platform/features.py` — recursos opcionais (ativar/desativar, reinício necessário) e renomear o computador
- ✅ Registro: `create_key` (chave `Deprovisioned`, item 37)
- ✅ `agent/steps/tweak.py` — motor de operações tipadas: registro (perfil Default montado e sempre desmontado, HKCU, HKLM), tipo de início de serviço via registro, recursos opcionais, powercfg, appx; conferência "já aplicado"
- ✅ `agent/steps/system.py` — bloatware + bloqueio de reinstalação; plano de energia com duplicação de planos ocultos (Modern Standby), hibernação, inicialização rápida; renomear o computador (decidir na hora)
- ✅ Teste de dados: todos os ajustes do catálogo aplicam em todos os alvos
- ✅ Roteiro `docs/validacao/M7.md`
### M8 — Windows Update, resumo e notificações ✅ (código) · validação na VM pendente
- ✅ `platform/windows_update.py` — API COM `Microsoft.Update.Session`: procurar, aceitar EULA, baixar, instalar; com ou sem drivers
- ✅ `platform/power.py` — ociosidade (`GetLastInputInfo`) e reinício agendado (`shutdown /r /t`)
- ✅ `agent/steps/windows_update.py` — resultados 2/3/4, reinício necessário, títulos no log
- ✅ `agent/reboot.py` — políticas `ask`, `auto_if_idle` (5 min ocioso, aviso de 60 s), `never`
- ✅ Atalho "Tentar de novo os que falharam (WinKit)" quando há falha (o Agente fica instalado — D-024)
- ✅ Resumo HTML e notificação final (M3) agora com todos os tipos de etapa reais
- ✅ Roteiro `docs/validacao/M8.md`
### M9 — Interface do Agente ✅ (código) · validação na VM pendente
- ✅ `winkit/ui/` — kit visual no estilo macOS (D-026): tema claro/escuro com tokens, chave liga/desliga animada, grupos arredondados, linhas, ícones desenhados por tipo de etapa, ícone do app
- ✅ `agent/ui/qt.py` — janela com páginas Início (já feito / a fazer, chaves "decidir na hora", nome do PC, contagem regressiva que pausa ao interagir), Progresso (status por etapa, avisos de espera), Concluído; diálogo de reinício; bandeja com progresso e notificações; ponte segura entre a thread de trabalho e o Qt
- ✅ `agent/ui_select.py` — janela para `countdown`/`interactive`, só bandeja para `silent`, nada se tudo desligado; Qt importado só ali (R-35)
- ✅ `agent/main.py` — a Fase 2 roda dentro da interface (`run_phase2_with_ui`)
- ✅ Protocolo `AgentUi.step_result` (status real de cada etapa na lista)
- ✅ Capturas em `docs/imagens/`
- ✅ Roteiro `docs/validacao/M9.md`
### M10 — WinKit Studio ✅ (código) · validação no PC pendente
- ✅ `studio/controller.py` — fachada sem Qt sobre os mesmos serviços da CLI (R-36), testada à parte
- ✅ `studio/ui/` — janela no estilo "Ajustes do Sistema" (D-026): barra lateral com 10 seções (Pendrive, Windows e conta, Aplicativos, Configurações dos apps, Drivers, Apps pré-instalados, Ajustes, Energia e atualizações, Primeiro login, Revisar e construir), tarefas demoradas fora da thread da interface com folha "Trabalhando…" (R-37)
- ✅ Kit visual: controle segmentado, botão "Perguntar" (decidir na hora), seta das listas, ícones sem escurecer na seleção
- ✅ Empacotamento: `packaging/winkit-studio.spec` (janela, pede administrador), ícone gerado (`make_icon.py`), CI abre o Studio pronto no modo `--teste-fumaca`
- ✅ Registro do Windows carregado só no primeiro uso (o app não cai fora do Windows)
- ✅ Capturas em `docs/imagens/studio-*.png`
- ✅ Roteiro `docs/validacao/M10.md`

(Itens detalhados de M4–M10 em `PLANO.md` §20; são desdobrados aqui quando o marco começar.)

### M11 — Inglês e espanhol 🟨
- ✅ Decisões D-030 a D-042 e regras R-51 a R-55 no `ARQUITETURA.md`
- ✅ `winkit/i18n`: idiomas, `t`/`tn` com plural, `Msg`, formatação por idioma, tabelas pt-BR/en-US/es com paridade testada (R-51); contrato de pureza no import-linter
- ✅ `Msg` no estado (schema 2, com migração da v1), nas etapas, no executor e no resumo (HTML com `lang` e datas por idioma)
- ⬜ Extração dos textos do Studio, da janela do Agente e da CLI; teste AST (R-55)
- ⬜ Catálogos traduzidos, detecção do idioma, troca no Studio, idioma do Agente pela receita
- ⬜ README, NOTICE, LEIA-ME e notas da release trilíngues; capturas; roteiro `M11.md`

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
| H11 | Grupo `Administrators` funciona em Windows pt-BR | ⬜ | — |
