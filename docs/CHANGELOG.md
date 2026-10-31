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

## 2026-10-31 — M16 — Resolver de volumes, pastas do usuário em outro disco (V2-14) e jogos (V2-13)
**Tipo:** implementação
**Resumo:** volumes passam a ser achados pelo número de série, nunca pela letra (D-035). Documentos, Downloads e as outras pastas podem ficar num outro disco, e o Windows novo já aponta para lá. Jogos da Steam e da Epic em outro disco aparecem instalados sem baixar de novo. A release 0.6.0 foi disparada antes deste commit.

### Adicionado
- `src/winkit/core/volumes.py`, `src/winkit/platform/volumes.py`, `src/winkit/platform/fakes/volumes.py`
- `src/winkit/core/user_folders.py`, `src/winkit/collector/user_folders.py`, `src/winkit/agent/steps/user_folders.py`
- `src/winkit/core/vdf.py`, `src/winkit/core/games.py`, `src/winkit/collector/games.py`, `src/winkit/agent/steps/game_library.py`
- Receita: `VolumeRef`, `meta.source_system_volume`, `user_folders`, `game_libraries` (aditivos); plano: `user_folders` (Fase 1, R16) e `game_library` (Fase 2, R22)
- Os moldes `{DOCUMENTS}` e afins seguem as pastas redirecionadas (R16)
- Studio: seções "Pastas do usuário" e "Jogos"; CLI: `pastas mostrar|definir|copiar-agora`, `coletar jogos`, `jogos listar|marcar|desmarcar`
- Testes: `tests/agent/test_user_folders.py` (inclui o de proteção da R-52), `tests/agent/test_games.py` e fixtures em `tests/fixtures/games/`

### Documentos vivos atualizados
- ARQUITETURA — módulos e verificação R-52; STATUS — M16 em andamento, H32, H33; PLANO_V2 — §5.1

## 2026-10-31 — Correção dos testes de fontes no Windows (IN-018)
**Tipo:** correção
**Resumo:** os testes das fontes dependiam de como o Linux trata a data dos arquivos e falharam no Windows. O id da fonte também saía com a extensão duplicada.

### Alterado
- `src/winkit/collector/fonts.py` — data de criação injetável; id sem a extensão
- `tests/agent/test_fonts.py` — datas controladas pelo teste

### Documentos vivos atualizados
- INCIDENTES — IN-018

## 2026-10-31 — M15 — Iniciar e barra de tarefas (V2-04) e fechamento do M15 (0.6.0)
**Tipo:** implementação
**Resumo:** os ícones fixados na barra e no Iniciar chegam ao Windows novo, no modo lista (entre versões) ou como cópia exata do Iniciar (mesma versão, experimental). Fecha o M15 com o roteiro de validação e a versão 0.6.0.

### Adicionado
- `src/winkit/core/start_layout.py`, `src/winkit/collector/start_layout.py`, `src/winkit/agent/steps/start_layout.py`
- Receita: `start_layout` (aditivo); plano: tipo `start_layout` no perfil Default (R20)
- Studio: seção "Iniciar e barra"; CLI: `coletar iniciar --modo list|exact`
- Testes: `tests/agent/test_start_layout.py` com snapshots em `tests/fixtures/start_layout/`
- `docs/validacao/M15.md`

### Alterado
- `src/winkit/__init__.py` — versão 0.6.0; `packaging/NOTAS_DA_VERSAO.md` — novidades do M15

### Documentos vivos atualizados
- ARQUITETURA — módulos e verificação R-42; STATUS — M15 ✅ código, H27, H28; DIVIDAS — DT-024

## 2026-10-31 — M15 — Navegadores prontos (V2-12)
**Tipo:** implementação
**Resumo:** Chrome, Edge, Brave e Firefox chegam com as extensões de sempre, página inicial e buscador, pelas políticas oficiais e no modo "sugerir" por padrão (D-038). Senhas, cookies e login nunca são lidos nem levados.

### Adicionado
- `src/winkit/data/browsers.yaml`, `extensions.yaml`, `search_providers.yaml`
- `src/winkit/core/browsers.py`, `src/winkit/collector/browsers.py`, `src/winkit/platform/browsers.py`, `src/winkit/agent/steps/browser.py`
- Receita: `browsers` (aditivo) e validação; plano: tipo `browser` na Fase 1 (R21)
- Studio: seção "Navegadores" (grupo Rede); CLI: `coletar navegadores`, `navegador listar|definir|remover-do-pc`
- Testes: `tests/agent/test_browsers.py` (tabela de casos por navegador e modo; perfis de exemplo sem dados pessoais)

### Documentos vivos atualizados
- ARQUITETURA — módulos; STATUS — V2-12, H30–H32; PLANO_V2 — §10.5

## 2026-10-31 — M15 — Aparência pessoal (V2-06)
**Tipo:** implementação
**Resumo:** papel de parede, cor de destaque, tema, mouse, ponteiro e repetição do teclado iguais aos do PC antigo. Só valores conhecidos e dentro do padrão do Windows são levados. A release 0.5.0 foi publicada.

### Adicionado
- `src/winkit/data/personal_settings.yaml` (+ traduções), `src/winkit/core/personal.py`, `src/winkit/collector/personal.py`, `src/winkit/platform/personal.py`, `src/winkit/agent/steps/personal.py`
- Receita: `personal` (aditivo); plano: tipo `personal` no perfil Default (R23)
- Studio: seção "Aparência" com miniatura do papel de parede; CLI: `coletar aparencia`, `aparencia listar|marcar|desmarcar`
- Testes: `tests/agent/test_personal.py`

### Documentos vivos atualizados
- ARQUITETURA — módulos; STATUS — V2-06, H26; DIVIDAS — DT-023; INCIDENTES — IN-017 (a 0.5.0 passou)

## 2026-10-31 — M15 — Apps padrão (V2-05)
**Tipo:** implementação
**Resumo:** navegador, leitor de PDF, players, visualizador e compactador padrão iguais aos do PC antigo, aplicados na instalação. O que o Windows não deixar (apps instalados depois do login) aparece no resumo para confirmar.

### Adicionado
- `src/winkit/data/file_associations.yaml` (+ traduções), `src/winkit/core/associations.py`, `src/winkit/platform/associations.py`, `src/winkit/platform/fakes/associations.py`, `src/winkit/collector/associations.py`, `src/winkit/agent/steps/default_apps.py`
- Receita: `default_apps` (aditivo); plano: `default_apps:import` (Fase 1) e `default_apps_verify:user` (Fase 2)
- Serviços do Studio: `associations`; Studio: seção "Apps padrão"; CLI: `coletar associacoes`, `associacoes listar|marcar|desmarcar`
- Testes: `tests/agent/test_default_apps.py` e a fixture `tests/fixtures/associations/exportado.xml`

### Documentos vivos atualizados
- ARQUITETURA — módulos; STATUS — V2-05, H25; PLANO_V2 — §5.1

## 2026-10-31 — M15 — Perfis rápidos (V2-15) e fontes (V2-07)
**Tipo:** implementação
**Resumo:** um clique aplica o perfil Gamer, Privacidade máxima, Escritório ou Programador, sempre somando à receita. As fontes instaladas no PC antigo vão para o Windows novo, para todos os usuários. A release 0.5.0 foi disparada antes deste commit.

### Adicionado
- `src/winkit/data/presets.yaml`, `src/winkit/core/presets.py`; 5 ajustes `gaming.*` em `tweaks.yaml` (categoria nova `gaming`) e traduções
- `src/winkit/core/fonts.py`, `src/winkit/collector/fonts.py`, `src/winkit/platform/fonts.py`, `src/winkit/agent/steps/font.py`
- Receita: `presets_applied`, `fonts` (aditivos); plano: tipo `font` na Fase 1
- Studio: cartão "Perfis rápidos" em Ajustes, categoria Jogos, seção "Fontes"; CLI: `perfil-rapido listar|aplicar`, `coletar fontes`, `fontes listar|marcar|desmarcar`
- Testes: `tests/core/test_presets.py`, `tests/agent/test_fonts.py` (fontes geradas no teste)

### Documentos vivos atualizados
- ARQUITETURA — módulos; STATUS — M15 em andamento; PLANO_V2 — §10.3 e §10.6; DIVIDAS — DT-022

## 2026-10-31 — Limite de tempo e diagnóstico nos testes da CI e da release (IN-017)
**Tipo:** correção (infraestrutura)
**Resumo:** a release 0.4.0 travou no passo de testes sem dizer onde. Agora um teste preso imprime a pilha e os passos de teste têm limite de tempo.

### Alterado
- `pyproject.toml` — `faulthandler_timeout = 300`
- `.github/workflows/ci.yml`, `.github/workflows/release.yml` — `timeout-minutes: 25` nos testes; a release fixa `QT_QPA_PLATFORM=offscreen`

### Documentos vivos atualizados
- INCIDENTES — IN-017

## 2026-10-31 — M14 — Variáveis de ambiente e PATH (V2-22) e fechamento do M14 (0.5.0)
**Tipo:** implementação
**Resumo:** quem programa leva as variáveis de ambiente e as pastas extras do PATH. Uma variável que já existe com outro valor nunca é trocada sem pedir, e o PATH só ganha entradas. Fecha o M14 com o roteiro de validação e a versão 0.5.0.

### Adicionado
- `src/winkit/data/protected_env.yaml`, `src/winkit/core/env.py`, `src/winkit/collector/env.py`, `src/winkit/agent/steps/env.py`
- `Environment.broadcast_env_change` (`WM_SETTINGCHANGE`)
- Receita: `environment` (`variables`, `path_entries`; aditivo); validação de nomes protegidos e repetidos; plano: tipo `env` (R26)
- Studio: seção "Variáveis de ambiente" (grupo Sistema); CLI: `coletar variaveis`, `variaveis listar|marcar|desmarcar|definir`
- `docs/validacao/M14.md`
- Testes: `tests/agent/test_env.py`

### Alterado
- `src/winkit/platform/fakes/registry.py` — o dublê devolve o nome do valor com a grafia gravada, como o Windows
- `src/winkit/__init__.py` — versão 0.5.0
- `packaging/NOTAS_DA_VERSAO.md` — novidades do M14 nos três idiomas
- `docs/PLANO_V2.md` — modelo do PATH com escopo e marca por pasta

### Documentos vivos atualizados
- STATUS — M14 ✅ código; PLANO_V2 — §5.1

## 2026-10-31 — M14 — Tarefas de manutenção (V2-18)
**Tipo:** implementação
**Resumo:** o Windows novo se mantém sozinho: uma tarefa do usuário atualiza os apps pelo winget, a otimização semanal do disco é garantida e o Sensor de Armazenamento pode ser ligado.

### Adicionado
- `src/winkit/core/maintenance.py` (especificação pura), `src/winkit/agent/steps/maintenance.py`
- `TaskScheduler`: `ensure_user_task`, `user_task_matches`, `builtin_task`, `remove_folder`
- Catálogo: ajuste `maintenance.storage_sense` (categoria nova `maintenance`)
- Receita: `maintenance` (aditivo); plano: `maintenance:defrag` na Fase 1 e `maintenance:winget` na Fase 2 (R27)
- Serviços do Studio: `scheduler`; Studio: seção "Manutenção" (grupo Sistema); CLI: `manutencao mostrar|definir|remover-do-pc`
- Testes: `tests/agent/test_maintenance.py`

### Alterado
- `tests/core/test_planner.py`, `tests/agent/test_live.py` — contam com a otimização do disco, ligada por padrão
- `docs/PLANO_V2.md` — "mensal" é a cada 4 semanas

### Documentos vivos atualizados
- ARQUITETURA — módulos; STATUS — V2-18; PLANO_V2 — §9.6

## 2026-10-31 — M14 — Unidades de rede mapeadas (V2-17)
**Tipo:** implementação
**Resumo:** as unidades de rede do PC antigo (ex.: `Z:` → `\\nas\filmes`) reaparecem no Windows novo. A senha do servidor nunca é levada; o Windows pede na primeira vez.

### Adicionado
- `src/winkit/platform/netdrives.py`, `src/winkit/collector/netdrives.py`, `src/winkit/agent/steps/network_drive.py`
- Receita: `network_drives` (aditivo); plano: tipo `network_drive` no perfil Default (R25)
- Serviços do Studio: `registry`
- Studio: seção "Unidades de rede" (grupo Rede); CLI: `coletar unidades`, `unidades listar|adicionar|remover`
- Testes: `tests/agent/test_network_drives.py`

### Documentos vivos atualizados
- ARQUITETURA — módulos; STATUS — V2-17, H24

## 2026-10-31 — M14 — DNS seguro e bloqueio pelo hosts (V2-16)
**Tipo:** implementação
**Resumo:** a receita troca o DNS do Windows novo por um serviço mais rápido e privado, com DNS criptografado no Windows 11, e pode bloquear anúncios e rastreadores pelo arquivo `hosts` num bloco marcado que dá para desfazer.

### Adicionado
- `src/winkit/data/dns_providers.yaml`, `src/winkit/data/hosts_blocklists.yaml` (+ traduções)
- `src/winkit/core/dns.py`, `src/winkit/platform/dns.py`, `src/winkit/platform/hosts.py`, `src/winkit/platform/fakes/dns.py`, `src/winkit/agent/steps/network_privacy.py`
- Receita: `dns` (aditivo), validação dos servidores e listas; validação dos ids de recursos do Windows
- Plano: tipos `dns` e `hosts` na Fase 1 depois do Wi-Fi (R18)
- Studio: seção "DNS e bloqueios" (grupo Rede) com desfazer; CLI: `dns mostrar|definir`, `dns bloqueios marcar|desmarcar|remover-do-pc`
- Testes: `tests/agent/test_network_privacy.py` (inclui o de proteção do `hosts`)

### Documentos vivos atualizados
- ARQUITETURA — módulos e verificação do `hosts`; STATUS — V2-16, H23; DIVIDAS — DT-021

## 2026-10-31 — Correção de lint do commit anterior (IN-016)
**Tipo:** correção
**Resumo:** o commit do diagnóstico de drivers entrou com dois erros de lint num teste porque um pipe escondeu a falha do `check.sh`. Corrigido e registrado.

### Alterado
- `tests/agent/test_driver_report.py` — importações no topo, linha longa quebrada

### Documentos vivos atualizados
- INCIDENTES — IN-016

## 2026-10-31 — M14 — Diagnóstico de drivers (V2-09)
**Tipo:** implementação
**Resumo:** no fim da instalação, o Agente lista os dispositivos que ficaram sem driver, procura no Windows Update só os drivers deles e mostra o que sobrou no resumo, com os ids de hardware para procurar no site do fabricante.

### Adicionado
- `src/winkit/core/devices.py` (tabela de códigos `ConfigManagerErrorCode`), `src/winkit/platform/devices.py`, `src/winkit/agent/steps/driver_report.py`
- `WindowsUpdater.install_drivers_for` (só drivers cujo `DriverHardwareID` casa)
- Receita: `updates.fix_missing_drivers` (ligado); estado: `devices`, `drivers_found` (aditivos); plano: tipo `driver_report` depois do Windows Update (R28)
- Resumo: seções "Drivers instalados pelo Windows Update" e "Dispositivos sem driver"
- Studio: chave na página Drivers; textos dos 21 códigos nos três idiomas
- Testes: `tests/agent/test_driver_report.py`

### Alterado
- `tests/core/test_planner.py`, `tests/agent/test_live.py` — contam com a etapa nova

### Documentos vivos atualizados
- ARQUITETURA — módulos; STATUS — V2-09

## 2026-10-31 — M14 — Recursos do Windows (V2-08)
**Tipo:** implementação
**Resumo:** a receita liga recursos do Windows já na instalação (WSL, Área Restrita, Hyper-V, .NET 3.5, OpenSSH, Telnet, TFTP, IIS). Os que não precisam de internet entram antes do login; o .NET 3.5 instala sem internet pela mídia de instalação, montando a ISO original só para leitura (D-043).

### Adicionado
- `src/winkit/data/features.yaml` (+ traduções em `i18n_en_us.yaml` e `i18n_es.yaml`)
- `src/winkit/platform/iso_mount.py`, `src/winkit/collector/features.py`, `src/winkit/agent/steps/feature.py`
- Catálogo: `FeatureEntry`, `FeaturePart`, `OsFilter.editions`; operações `capability_add`/`capability_remove` (R-34)
- Receita: `windows.optional_features`; plano: tipo `feature` e `PlannedStep.phase2_fallback`
- Construtor: `WinKit/isos.json` no modo Ventoy; `core/isos.py`: `IsoIndex`, `pick_iso`
- Studio: seção "Recursos do Windows" (grupo Sistema); CLI: `recursos listar|marcar|desmarcar`, `coletar recursos`
- Testes: `tests/agent/test_features.py`

### Alterado
- `src/winkit/platform/features.py` — recursos com fonte offline (`-Source -LimitAccess`), capacidades e consulta de estados por enum
- `src/winkit/agent/executor.py` — segunda chance na Fase 2 para etapas marcadas

### Documentos vivos atualizados
- ARQUITETURA — D-043, módulos, verificação D-002; STATUS — V2-08, H21, H22; DIVIDAS — DT-020

## 2026-10-31 — M14 — Wi-Fi e registro de segredos
**Tipo:** implementação + correção
**Resumo:** as redes Wi-Fi salvas no PC atual passam a ser conectadas no Windows novo antes do primeiro login, com opção de levar sem a senha (V2-02, D-036). Novo registro de segredos (R-53) mascarado em todo log. Corrige um efeito colateral global do ElementTree que alterava o `autounattend.xml` (IN-015). A release 0.4.0 foi publicada antes deste commit.

### Adicionado
- `src/winkit/core/secrets.py` — `SECRETS` (R-53)
- `src/winkit/core/wifi.py`, `src/winkit/collector/wifi.py`, `src/winkit/platform/wifi.py`, `src/winkit/platform/services_base.py`, `src/winkit/platform/fakes/wifi.py`, `src/winkit/agent/steps/wifi.py`
- Receita: `wifi.networks` (aditivo); planejador: tipo `wifi` na Fase 1 depois dos drivers (R17)
- Studio: grupo "Rede" com a página Wi-Fi; CLI: `coletar wifi`, `wifi listar|marcar|desmarcar [--sem-senha]`
- Testes: `tests/agent/test_wifi.py` (inclui o de proteção R-53), testes de arquitetura do IN-015; fixtures `tests/fixtures/wifi/*_doc.xml`

### Alterado
- `src/winkit/platform/runner.py`, `src/winkit/agent/eventlog.py` — mascaram o registro de segredos
- `src/winkit/core/unattend/generator.py` — reafirma os prefixos XML antes de serializar (IN-015)
- `tests/conftest.py` — limpa o registro de segredos entre testes

### Documentos vivos atualizados
- ARQUITETURA — módulos e verificações R-53/IN-015; STATUS — M14 em andamento; DIVIDAS — DT-019; INCIDENTES — IN-015

## 2026-10-31 — M13 — Pendrive comum: Rufus e ferramenta da Microsoft (0.4.0)
**Tipo:** implementação
**Resumo:** além do Ventoy, o WinKit prepara um pendrive de instalação gravado pelo Rufus ou pela Ferramenta de Criação de Mídia: grava só o `autounattend.xml` na raiz (com o idioma da imagem) e a pasta `WinKit\`, guarda as respostas do Rufus e nunca formata nada (V2-01, D-034). A release 0.3.0 foi publicada antes deste commit.

### Adicionado
- `src/winkit/core/media.py` — reconhecimento da mídia, `find_setup_targets`, marca de origem do XML
- `DiskInspector.read_setup_image` (+ dublê, `setup_rows`, `make_setup_folder`)
- `tests/builder/test_setup_media.py` — detecção, R-19 no modo comum, respostas do Rufus, idioma da imagem, validação
- `docs/RUFUS.md`, `docs/validacao/M13.md`

### Alterado
- `src/winkit/builder/target.py` — `Target.kind`, `list_targets`/`resolve_target` com os dois tipos, `from_drive`
- `src/winkit/builder/build.py` — `_build_setup_media`, cópia única das respostas existentes
- `src/winkit/builder/validate.py` — validação do modo comum; mensagem do bootstrap traduzida
- Studio e CLI mostram o tipo de cada pendrive; textos da página Pendrive
- Versão 0.4.0; notas da release

### Documentos vivos atualizados
- ARQUITETURA — R-19 (caminho do `$OEM$`) e módulos; STATUS — M13 e H16–H18

## 2026-10-31 — M11 — Correção: testes independentes do idioma do Windows
**Tipo:** correção (testes)
**Resumo:** os testes da CLI falhavam no runner do Windows (em inglês) porque a CLI detecta o idioma da máquina (IN-014).

### Alterado
- `tests/conftest.py` — `WINKIT_LANG=pt-BR` fixo em todo teste

### Documentos vivos atualizados
- INCIDENTES — IN-014

## 2026-10-31 — M12 — Aplicar neste PC e ponto de restauração (0.3.0)
**Tipo:** implementação
**Resumo:** a receita pode ser aplicada num Windows já instalado, com prévia que não muda nada, ponto de restauração antes e estado próprio por aplicação (V2-03, D-033). A instalação passa a terminar com um ponto de restauração "Windows pronto" (V2-10). A 0.2.0 (M11) não foi publicada à parte: o CI dela falhou (IN-014) e a release 0.3.0 leva o M11 e o M12 juntos.

### Adicionado
- `src/winkit/agent/live.py` — `run_live`, `LiveOptions`, `FixedLocator`, prévia e aplicação
- `src/winkit/agent/steps/restore.py`, `src/winkit/platform/restore.py`, `src/winkit/platform/fakes/restore.py` — ponto de restauração por CIM
- `src/winkit/core/live.py` — `PreviewItem`, `LivePreview`
- Receita: `restore_point` (`enabled`, `max_disk_percent`; aditivo, D-039)
- Agente: `winkit-agent apply`; CLI: `winkit aplicar` (`apply`)
- Studio: seção "Aplicar neste PC" e cartão "Ponto de restauração"
- Testes: `tests/agent/test_live.py` (inclui o de proteção R-54), `tests/core/test_planner_live.py`, página do Studio, regional tolerante
- `docs/validacao/M12.md`

### Alterado
- Planejador: `PlanContext.mode/only_kinds/restore_before`, R30/R31, tipo `restore_point`
- Contrato de etapa: `StepBase` com `live_safe` e `preview()`; prévia real do backup; `StepContext.mode`; `finalize` sem limpeza no modo ao vivo
- `src/winkit/agent/executor.py` — `context()`, modo; `Locator` como protocolo
- `src/winkit/platform/locale.py` — leitura regional nunca impede a receita nova (achado no teste com o executável)
- `packaging/smoke.ps1` — `aplicar --simular` e `winkit-agent apply --simular`
- Versão 0.3.0; notas da release com as novidades

### Documentos vivos atualizados
- ARQUITETURA — contrato de etapa (§4.1), módulos, R-54 na §5.12; PLANO_V2 — Studio roda o motor no próprio processo; DIVIDAS — DT-018; STATUS — M12 e H12–H15

## 2026-10-31 — M11 — Documentação trilíngue, capturas e versão 0.2.0
**Tipo:** documentação + versão
**Resumo:** fecha o M11. README em inglês e espanhol, `NOTICE` com a seção em espanhol, LEIA-ME do pacote nos três idiomas, notas da release trilíngues com as novidades, capturas novas do Studio e roteiro de validação. Links atualizados para o repositório renomeado (`WinKit`). Versão 0.2.0.

### Adicionado
- `README.en.md`, `README.es.md`
- `packaging/README.txt`, `packaging/LEAME.txt` (copiados pelo `build.ps1`)
- `docs/imagens/en/`, `docs/imagens/es/` e capturas novas em `docs/imagens/`
- `docs/validacao/M11.md`

### Alterado
- `README.md` — seletor de idioma, três idiomas, barra lateral agrupada, apelidos da CLI, links do repositório `WinKit`
- `NOTICE`, `CONTRIBUTING.md`, `packaging/LEIA-ME.txt`, `packaging/NOTAS_DA_VERSAO.md`, `packaging/build.ps1`
- `src/winkit/__init__.py` — versão 0.2.0
- `docs/PLANO.md` — nome do repositório

### Documentos vivos atualizados
- STATUS — M11 ✅ código, validação pendente

## 2026-10-31 — M11 — Catálogos traduzidos e padrões regionais do PC atual
**Tipo:** implementação + dados
**Resumo:** ajustes, apps pré-instalados, classes de driver e avisos de DPAPI ganham tradução em inglês e espanhol, carregada conforme o idioma (no Studio e no Agente). A receita nova passa a nascer com formatos, teclado e fuso do PC atual. A descrição da conta local no XML sai no idioma escolhido.

### Adicionado
- `src/winkit/data/i18n_en_us.yaml`, `src/winkit/data/i18n_es.yaml` — traduções dos catálogos
- `src/winkit/core/catalog/localize.py` — `localize`, `missing_translations`, `orphan_translations`
- `src/winkit/core/regional.py` — `RegionalDefaults`, conversão do layout de teclado para o formato do XML
- `platform/locale.read_regional` — formatos, teclado e fuso pelo registro
- Testes: `tests/core/test_catalog_localize.py`, `tests/core/test_regional.py`, descrição da conta por idioma

### Alterado
- `src/winkit/core/catalog/loader.py` — `default_catalogs()` no idioma atual (cache por idioma), `load_translation`
- `src/winkit/studio/controller.py` — catálogos sempre no idioma atual (`catalogs_override` para testes)
- `src/winkit/agent/phases.py`, `src/winkit/agent/main.py` — catálogos recarregados no idioma da receita
- `src/winkit/core/recipe/io.py` — `new_recipe(regional=...)`; Studio e CLI passam os valores do PC
- `src/winkit/platform/services.py` — `Services.regional`
- `src/winkit/core/unattend/generator.py` — descrição da conta por chave

### Documentos vivos atualizados
- PLANO — §9.5; PLANO_V2 — onde ficaram as traduções dos catálogos; STATUS — itens do M11

## 2026-10-31 — M11 — Agente, CLI e mensagens do motor em três idiomas
**Tipo:** implementação + testes
**Resumo:** o Agente passa a falar o idioma da receita (`auto` = idioma do Windows novo); a CLI ganha `--idioma`, `WINKIT_LANG` e apelidos em inglês (`build`, `recipe new`…); os avisos do Construtor, da validação e do Coletor saem traduzidos. Dois testes de proteção garantem que nenhuma chave falta, nenhuma sobra e nenhum texto de interface fica solto no código.

### Adicionado
- `tests/i18n/test_usage.py` — R-51 (uso das chaves) e R-55 (AST: nada de texto solto em interface, ajuda e saída)
- `tests/agent/test_language.py` — Agente em inglês (automático) e em espanhol (explícito)
- `tests/cli/test_cli.py` — `--idioma`, apelidos em inglês e `WINKIT_LANG`
- ~120 chaves `cli.*`, `validate.*`, `builder.*`, `collect.*`, `recipe.*`

### Alterado
- `src/winkit/agent/phases.py`, `src/winkit/agent/main.py` — `apply_language` com o idioma da receita
- `src/winkit/cli/main.py` — textos por chave, `choose_language`, `--idioma`, apelidos
- `src/winkit/builder/{build,validate}.py`, `src/winkit/collector/{apps,backups}.py`, `src/winkit/core/recipe/validation.py` — mensagens por chave
- `src/winkit/agent/ui/qt.py` — exemplo de nome de PC traduzido

### Removido
- 15 chaves que não eram mais usadas, nas três tabelas

### Documentos vivos atualizados
- ARQUITETURA — §5.12 com R-51, R-55 e IN-013; STATUS — itens do M11; PLANO_V2 — nota sobre a CLI

## 2026-10-31 — M11 — Studio em três idiomas, com grupos, busca e preferências
**Tipo:** implementação + refatoração
**Resumo:** todos os textos do Studio passam a vir das tabelas de tradução. As páginas saem de um arquivo único e viram um pacote por grupo. A barra lateral ganha grupos (Preparar, O que levar, Sistema, Concluir), busca por título e palavras-chave, e um botão de Preferências para idioma e tema que reconstrói a janela sem reiniciar (D-042).

### Adicionado
- `src/winkit/studio/ui/pages/{common,prepare,bring,system,finish}.py` — páginas por grupo
- `src/winkit/studio/preferences.py` — idioma e tema salvos (`studio.json`)
- `src/winkit/platform/locale.py` — idioma de exibição do Windows
- Campo `execution.language` na receita (idioma do primeiro login; aditivo, D-039)
- ~230 chaves `studio.*`, `size.*` e `pendrive.folder_description` nos três idiomas
- Lista maior de teclados (inclui espanhol e inglês do Reino Unido) e de fusos

### Alterado
- `src/winkit/studio/ui/window.py` — `GROUPS`/`Section`, busca, Preferências, `apply_preferences`, `go_to(id)`
- `src/winkit/studio/ui/base.py` — `title_key`/`subtitle_key`, `needs_recipe()`, widgets limpos somem na hora
- `src/winkit/studio/main.py` — idioma e tema na abertura; fumaça percorre as seções nos três idiomas
- `src/winkit/ui/theme.py` — tema forçado claro ou escuro
- `src/winkit/builder/build.py` — `payload_sizes` com ids (`agent`, `apps`…) traduzidos na borda
- `src/winkit/builder/target.py` — descrição do destino montada no idioma atual
- Página "Windows e conta": problemas calculados direto, sem filtrar texto traduzido
- `tests/ui/test_studio_ui.py` — todas as páginas nos três idiomas, troca de idioma, busca, preferências, aviso traduzido

### Removido
- `src/winkit/studio/ui/pages.py` — virou o pacote `pages/`

### Documentos vivos atualizados
- ARQUITETURA — módulos do Studio; STATUS — item do M11

## 2026-10-31 — M11 — Correção: tabelas de tradução no executável
**Tipo:** correção
**Resumo:** o executável empacotado não tinha as tabelas de tradução (importação dinâmica invisível ao PyInstaller, IN-013).

### Alterado
- `src/winkit/i18n/core.py` — importações explícitas das tabelas

### Adicionado
- `tests/test_architecture.py` — proíbe importação dinâmica no pacote

### Documentos vivos atualizados
- INCIDENTES — IN-013

## 2026-10-31 — M11 — Mensagens estruturadas no estado, nas etapas e no resumo
**Tipo:** implementação
**Resumo:** motivos e erros das etapas, avisos do Agente e itens do resumo passam a ser guardados como `Msg` (chave + parâmetros) e só viram texto na hora de mostrar, no idioma atual (D-031). O `estado.json` sobe para a versão 2, com migração da v1.

### Adicionado
- `src/winkit/core/state/migrations.py` — migração v1 → v2 (texto antigo vira `legacy.text`)
- `tests/core/test_state_migration.py`, `tests/core/test_summary.py` — migração e resumo nos três idiomas
- ~40 chaves novas (`step.*`, `summary.*`, `agent.recipe_changed`) nos três idiomas

### Alterado
- `src/winkit/agent/steps/*.py`, `src/winkit/agent/executor.py`, `src/winkit/agent/phases.py` — `StepResult` e motivos com `Msg`
- `src/winkit/core/state/models.py` — `error`, `reason` e `warnings` com `Msg`; `schema_version: 2`
- `src/winkit/core/summary.py` — `Msg` nos itens e avisos; HTML com `lang`, rótulos de status e data por idioma
- `src/winkit/i18n/core.py` — `render` escolhe o plural pelo parâmetro `n`
- Testes do Agente e do estado comparam o texto montado (`render`)

### Documentos vivos atualizados
- STATUS — item do M11 concluído

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
