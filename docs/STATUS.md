# WinKit — Status da Implementação

> Documento vivo. Mostra **o que existe de verdade no código** neste momento, marco por marco.
> Atualizado no mesmo commit de toda mudança que começa, conclui ou bloqueia um item.
>
> Legenda: ⬜ não iniciado · 🟨 em andamento · ✅ concluído · ⛔ bloqueado · ➖ fora do escopo atual

**Última atualização:** 2026-10-31
**Versão do código:** 0.4.0 (pré-alpha, projeto pessoal)
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
| M11 | Inglês e espanhol (V2-00) | ✅ código | ⬜ roteiro pronto (`docs/validacao/M11.md`) |
| M12 | Aplicar neste PC + ponto de restauração (V2-03, V2-10) | ✅ código | ⬜ roteiro pronto (`docs/validacao/M12.md`) |
| M13 | Pendrive comum: Rufus/Microsoft (V2-01) | ✅ código | ⬜ roteiro pronto (`docs/validacao/M13.md`) |
| M14 | Rede e sistema (V2-02, 08, 09, 16, 17, 18, 22) | ✅ código | ⬜ roteiro pronto (`docs/validacao/M14.md`) |
| M15 | Personalização (V2-04, 05, 06, 07, 12, 15) | ✅ código | ⬜ roteiro pronto (`docs/validacao/M15.md`) |
| M16 | Contas, pastas e jogos (V2-11, 13, 14) | ✅ código | ⬜ roteiro pronto (`docs/validacao/M16.md`) |
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

### M11 — Inglês e espanhol ✅ (código) · validação na VM pendente
- ✅ Decisões D-030 a D-042 e regras R-51 a R-55 no `ARQUITETURA.md`
- ✅ `winkit/i18n`: idiomas, `t`/`tn` com plural, `Msg`, formatação por idioma, tabelas pt-BR/en-US/es com paridade testada (R-51); contrato de pureza no import-linter
- ✅ `Msg` no estado (schema 2, com migração da v1), nas etapas, no executor e no resumo (HTML com `lang` e datas por idioma)
- ✅ Studio: textos por chave nos três idiomas; páginas divididas em `studio/ui/pages/`; barra lateral agrupada com busca; Preferências (idioma e tema) com troca sem reiniciar (D-042)
- ✅ Janela do Agente, resumo e notificações no idioma da receita (`execution.language`; `auto` = idioma do Windows novo)
- ✅ CLI: textos por chave, `--idioma`, `WINKIT_LANG`, apelidos em inglês (D-032); avisos do Construtor, da validação e do Coletor traduzidos
- ✅ Testes de proteção: uso das chaves (R-51) e nenhum texto de interface solto (R-55)
- ✅ Catálogos traduzidos (`data/i18n_*.yaml`, completude e órfãos testados), carregados por idioma
- ✅ Detecção do idioma do Windows, troca no Studio, idioma do Agente pela receita
- ✅ Receita nova com formatos, teclado e fuso do PC atual; descrição da conta no XML traduzida
- ✅ README em três idiomas (`README.en.md`, `README.es.md`), `NOTICE`, LEIA-ME do pacote (`README.txt`, `LEAME.txt`) e notas da release trilíngues; links para o repositório `WinKit`
- ✅ Capturas do Studio em pt/en/es (`docs/imagens/`, `docs/imagens/en/`, `docs/imagens/es/`); roteiro `docs/validacao/M11.md`; versão 0.2.0

### M12 — Aplicar neste PC e ponto de restauração ✅ (código) · validação na VM pendente
- ✅ V2-10: ponto de restauração "Windows pronto" no fim da instalação (`restore_point:ready`, R30), com espaço máximo configurável; frequência de 24 h contornada e restaurada; política que desliga a Restauração do Sistema respeitada
- ✅ V2-03: `agent/live.py` — plano ao vivo (perfil do usuário atual, R31), filtro "o que aplicar", ponto de restauração **antes** (D-033), prévia sem escrita (R-54, teste de proteção), estado/resumo por aplicação, logs no pendrive
- ✅ Contrato de etapa com `live_safe` e `preview()`; prévia real dos backups (novos × mantidos)
- ✅ `winkit-agent apply`, `winkit aplicar` (`--simular`, `--somente`, `--sem-ponto-de-restauracao` com confirmação extra)
- ✅ Studio: seção "Aplicar neste PC" (escolher → prévia → aplicar) e cartão do ponto de restauração em "Energia e atualizações"
- ✅ Teste de fumaça do pacote com `aplicar --simular` e `winkit-agent apply --simular`
- ⬜ DT-018: progresso por etapa e processo separado

### M13 — Pendrive comum (Rufus/Microsoft) ✅ (código) · validação na VM pendente
- ✅ `core/media.py`: reconhece o pendrive de instalação (setup.exe + boot.wim + install.wim/esd/swm), só em discos USB/SD sem `VTOYEFI`; layout UEFI:NTFS do Rufus
- ✅ Construtor: `\autounattend.xml` na raiz com o idioma da imagem; respostas do Rufus guardadas uma vez (`.winkit-bak`); `$OEM$` movido; teste de proteção da R-19 no modo comum
- ✅ Validação do modo comum; Studio e CLI mostram o tipo de cada pendrive
- ✅ `docs/RUFUS.md` com as configurações recomendadas

### M14 — Rede e sistema ✅ (código) · validação na VM pendente
- ✅ R-53: registro de segredos (`core/secrets.py`) mascarado pelo `runner` e pelo `EventLog`
- ✅ V2-02 Wi-Fi: coleta (`netsh wlan export key=clear`, só arquivos), opção sem senha, etapa antes do login logo após os drivers (R17), cópia temporária apagada, teste de proteção da senha; Studio (grupo Rede) e CLI (`coletar wifi`, `wifi listar|marcar|desmarcar --sem-senha`)
- ✅ V2-08 Recursos do Windows: catálogo `features.yaml` (WSL, Sandbox, Hyper-V, .NET 3.5, OpenSSH, Telnet, TFTP, IIS) com filtro de edição; sem internet antes do login, com internet depois (R19); .NET 3.5 sem internet pela mídia de instalação (`sources\sxs` ou ISO montada só para leitura, D-043); operações `capability_add`/`capability_remove` para os ajustes; Studio (grupo Sistema) e CLI (`recursos listar|marcar|desmarcar`, `coletar recursos`)
- ✅ V2-09 Diagnóstico de drivers: lista os dispositivos com problema (CIM, código traduzido por tabela), procura no Windows Update só os drivers deles (`DriverHardwareID`), seção "Dispositivos sem driver" no resumo com os ids de hardware; chave no Studio (Drivers), ligada por padrão; a prévia do modo ao vivo só consulta
- ✅ V2-16 DNS e bloqueios: Cloudflare, Cloudflare para Famílias, Quad9, Google, AdGuard, NextDNS (id pessoal) ou personalizado; DoH com política `DoHPolicy` no Windows 11 (só servidores no 10); bloqueio de anúncios e rastreadores por listas curadas no `hosts`, num bloco marcado, sem domínios da Microsoft; desfazer pelo Studio e pela CLI (`dns bloqueios remover-do-pc`)
- ✅ V2-17 Unidades de rede: coleta do `HKCU\Network` (sem o usuário do servidor), gravação no perfil Default na Fase 1 com o `ProviderName` lido do Windows novo; ao vivo mapeia na hora ou grava para reconectar; letra ocupada nunca é substituída; Studio (grupo Rede) e CLI (`coletar unidades`, `unidades listar|adicionar|remover`)
- ✅ V2-18 Manutenção: tarefa do usuário que roda `winget upgrade --all` toda semana ou a cada 4 semanas (dia e hora escolhidos, log em `ProgramData\WinKit\Manutencao`); otimização semanal nativa do disco garantida (ligada por padrão); Sensor de Armazenamento como ajuste `maintenance.storage_sense` com desfazer; Studio (grupo Sistema) e CLI (`manutencao mostrar|definir|remover-do-pc`)
- ✅ V2-22 Variáveis de ambiente e PATH: coleta só do que não é padrão (`protected_env.yaml`), valores com pastas do perfil viram moldes `%USERPROFILE%\…`, itens lidos chegam desmarcados; máquina no `HKLM` e usuário no perfil Default na Fase 1, `HKCU` + aviso aos programas ao vivo; nunca sobrescreve sem "substituir" (R-21); o PATH só ganha entradas no fim, sem duplicar; Studio (grupo Sistema) e CLI (`coletar variaveis`, `variaveis listar|marcar|desmarcar|definir`)
- ✅ Versão 0.5.0 e roteiro `docs/validacao/M14.md`

### M15 — Personalização ✅ (código) · validação na VM pendente
- ✅ V2-15 Perfis rápidos: Gamer, Privacidade máxima, Escritório e Programador (`presets.yaml`); 5 ajustes novos na categoria Jogos; aplicar mescla e nunca desmarca, com prévia; o Gamer mantém o Xbox Game Bar; Studio (cartão no topo de Ajustes) e CLI (`perfil-rapido listar|aplicar [--simular]`)
- ✅ V2-07 Fontes: leitor da tabela `name` (TTF, OTF, TTC) sem dependência nova; coleta das fontes do usuário e das da máquina instaladas depois do Windows; o arquivo só vai para o pendrive ao marcar; instalação para todos os usuários sem sobrescrever (`_winkit`); ao vivo carrega na sessão; Studio (grupo O que levar) e CLI (`coletar fontes`, `fontes listar|marcar|desmarcar`)
- ✅ V2-05 Apps padrão: `dism /Export-DefaultAppAssociations` (só código de saída e XML), grupos do catálogo (navegador, PDF, vídeo, música, imagens, compactados, e-mail, texto) com o app atual; importação na Fase 1 depois dos apps offline (R20); conferência do `UserChoice` na Fase 2 com aviso no resumo do que não pegou; fora da Fase 1 e ao vivo, só a instrução manual; Studio (O que levar) e CLI (`coletar associacoes`, `associacoes listar|marcar|desmarcar`)
- ✅ V2-06 Aparência: papel de parede (tipo pelos bytes; `TranscodedWallpaper` quando o original sumiu), cor de destaque, tema e transparência, mouse, ponteiro (só cursores de `%SystemRoot%\cursors`) e repetição do teclado; cada valor validado pelo catálogo e descartado se fora do padrão; perfil Default na Fase 1, `HKCU` + aplicação na hora ao vivo; Studio (O que levar, com miniatura) e CLI (`coletar aparencia`, `aparencia listar|marcar|desmarcar`)
- ✅ V2-12 Navegadores: Chrome, Edge, Brave e Firefox; leitura das extensões instaladas (Chromium: `Preferences`/`Secure Preferences`, resolvendo `__MSG_…__`; Firefox: `profiles.ini` + `extensions.json`), sem tocar em senhas ou cookies; extensões sugeridas do catálogo; página inicial e buscador; modo Sugerir (externas + `Recommended`) ou Forçar; desfazer só das políticas do WinKit; Studio (grupo Rede) e CLI (`coletar navegadores`, `navegador listar|definir|remover-do-pc`)
- ✅ V2-04 Iniciar e barra: fixados da barra ligados aos atalhos do menu Iniciar (`LayoutModification.xml`, `Replace`); Iniciar no modo lista (`LayoutModification.json`, formato `ConfigureStartPins`) ou cópia exata do `start2.bin` só no mesmo build (com aviso e volta para a lista); só na Fase 1, no perfil Default; Studio (O que levar) e CLI (`coletar iniciar --modo list|exact`)
- ✅ Roteiro `docs/validacao/M15.md` e versão 0.6.0

### M16 — Contas, pastas e jogos ✅ (código) · validação na VM pendente
- ✅ Resolver de volumes (D-035, R-52): `VolumeRef` pelo serial do CIM; a letra antiga é só dica; volume ausente = etapa pulada com motivo; teste de proteção da R-52; `meta.source_system_volume`
- ✅ V2-14 Pastas do usuário em outro disco: detecta as que já estão fora do C:; escolha do disco (nunca o do sistema), pasta base com `%USERNAME%` e pastas; `User Shell Folders` no perfil Default (Fase 1, antes de backups e ajustes, R16) ou no `HKCU` ao vivo; os moldes `{DOCUMENTS}` e afins passam a apontar para lá; "Copiar agora" em `merge` (origem intacta); Studio (grupo Sistema) e CLI (`pastas mostrar|definir|copiar-agora`)
- ✅ V2-13 Jogos: leitor/gravador VDF (ida e volta idêntica); bibliotecas da Steam e jogos da Epic fora do C:; na Fase 2, depois do app do launcher (R22), a biblioteca entra no `libraryfolders.vdf` e o manifesto da Epic é reescrito com a letra atual; nunca toca nos arquivos dos jogos; Studio (O que levar) e CLI (`coletar jogos`, `jogos listar|marcar|desmarcar`)
- ✅ V2-11 Contas extras: administrador ou padrão; senha "trocar no primeiro acesso" (padrão), "sem senha" ou "definida agora" (registrada como segredo, R-53); `LocalAccount` no XML (snapshot com duas contas); na Fase 1 o grupo é conferido pelo SID e a conta padrão sai de Administradores; backups "só a conta principal" vão para a Fase 2 no perfil dela; nunca ao vivo; Studio (Windows e conta) e CLI (`contas listar|adicionar|remover`, `backup-para-quem`)
- ✅ Roteiro `docs/validacao/M16.md` e versão 0.7.0

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
| H12 | Idioma de exibição lido como SYSTEM na Fase 1 | ⬜ | — |
| H13 | `CreateRestorePoint` funciona na Fase 2, logo após o Windows Update | ⬜ | — |
| H14 | `pnputil` num Windows em uso não força reinício sem aviso | ⬜ | — |
| H15 | Remover Appx com o usuário logado não exige sair da sessão | ⬜ | — |
| H16 | `Get-WindowsImage` lê metadados de `.swm` pelo primeiro arquivo | ⬜ | — |
| H17 | O Rufus grava respostas também em `sources\$OEM$\$$\Panther\unattend.xml` | ⬜ | — |
| H18 | O instalador usa o `autounattend.xml` do pendrive de boot mesmo com outra mídia removível | ⬜ | — |
| H21 | `Mount-DiskImage -Access ReadOnly` de uma ISO na partição exFAT do Ventoy funciona na Fase 1, como SYSTEM | ⬜ | — |
| H22 | `Enable-WindowsOptionalFeature` funciona na Fase 1 sem o serviço Windows Update ativo | ⬜ | — |
| H25 | `/Import-DefaultAppAssociations` na Fase 1 vale para a conta criada no primeiro login, para apps já instalados | ⬜ | — |
| H26 | O Windows 11 mantém o papel de parede e a cor gravados no perfil Default no primeiro login | ⬜ | — |
| H30 | Extensões externas por registro continuam aceitas no Chrome e no Edge estáveis para usuários não gerenciados | ⬜ | — |
| H31 | O Brave aceita as políticas do Chromium em `HKLM\SOFTWARE\Policies\BraveSoftware\Brave` | ⬜ | — |
| H32 | O endereço `addons.mozilla.org/.../latest/<id>/latest.xpi` aceita o id da extensão quando não há nome curto | ⬜ | — |
| H27 | Copiar `start2.bin` para o perfil Default reproduz o Iniciar na conta nova (mesma versão) | ⬜ | — |
| H28 | `LayoutModification.json` no perfil Default é respeitado pelo Windows 11 atual | ⬜ | — |
| H32 | `REG_EXPAND_SZ` com `%USERNAME%` em `User Shell Folders` do perfil Default é expandido no primeiro login de cada conta | ⬜ | — |
| H33 | Acrescentar a biblioteca no `libraryfolders.vdf` com a Steam fechada basta para ela reconhecer os jogos | ⬜ | — |
| H24 | Valores em `HKCU\Network` gravados no perfil Default são reconectados no primeiro login do usuário novo | ⬜ | — |
| H23 | `Set-DnsClientServerAddress` funciona na Fase 1 para adaptadores cujo driver acabou de ser instalado pelo `pnputil` | ⬜ | — |
