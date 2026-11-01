# WinKit — Estrutura do projeto

> **Gerado** por `scripts/gen_estrutura.py`; não edite à mão. Para mudar uma descrição, mude a docstring do módulo (ou o primeiro comentário do YAML) e rode o script. As regras de cada camada estão em [`ARQUITETURA.md`](ARQUITETURA.md).

## Raiz

| Caminho | O que tem |
|---|---|
| `CLAUDE.md` | regras obrigatórias para quem mexe no código (pessoas e agentes de IA) |
| `.claude/skills/` | skills obrigatórias do Claude Code neste projeto (Ponytail, R-58) |
| `README.md` | apresentação em português, com a versão em inglês logo abaixo |
| `README.en.md, README.es.md` | a apresentação em inglês e em espanhol |
| `CONTRIBUTING.md` | como contribuir |
| `LICENSE, NOTICE` | licença Apache 2.0 e aviso de isenção |
| `pyproject.toml, uv.lock` | dependências e configuração de ruff, mypy, pytest e import-linter |
| `.github/workflows/` | CI (lint, tipos, testes em Linux e Windows, pacote) e release |
| `docs/` | plano, arquitetura, status, dívidas, incidentes, changelog e roteiros de validação |
| `docs/validacao/` | roteiros de teste em VM ou PC real, um por marco |
| `docs/imagens/` | capturas de tela usadas nos READMEs |
| `packaging/` | specs do PyInstaller, build.ps1, smoke.ps1, make_icon.py (gera o .ico) e notas da versão |
| `scripts/` | check.sh (verificação antes de cada commit), geradores de documentação e `vm/` (VM de testes no Hyper-V) |
| `src/winkit/` | o código (detalhado abaixo) |
| `tests/` | testes automáticos, espelhando as pastas de src/winkit |

## `src/winkit/` por camada

### `core/` — lógica pura: receita, planejador, moldes, XML, estado; sem Windows, Qt nem subprocess

| Arquivo | O que faz |
|---|---|
| `__init__.py` | Núcleo puro: lógica de decisão sem efeitos colaterais e sem dependência de Windows. |
| `associations.py` | Apps padrão (V2-05): ler e filtrar o XML do ``dism /Export-DefaultAppAssociations``. |
| `browsers.py` | Navegadores prontos (V2-12): receita → operações tipadas de registro (R-34). Função pura. |
| `catalog/__init__.py` | Pacote. |
| `catalog/loader.py` | Carrega e valida os catálogos YAML empacotados em ``winkit/data`` (D-021). |
| `catalog/localize.py` | Tradução dos textos dos catálogos (D-030): a base fica em pt-BR, as outras línguas por cima. |
| `catalog/models.py` | Modelos dos catálogos em ``winkit/data`` (PLANO.md §15, R-32 a R-34). |
| `compare.py` | Relatório antes/depois (V2-19): o que o PC antigo tinha e o Windows novo não tem. Puro. |
| `devices.py` | Dispositivos com problema no Gerenciador de Dispositivos (V2-09). |
| `dns.py` | DNS seguro e bloqueio pelo ``hosts`` (V2-16): regras puras, sem Windows. |
| `env.py` | Variáveis de ambiente e PATH (V2-22): regras puras. |
| `errors.py` | Hierarquia de exceções do WinKit (ARQUITETURA.md, R-25). |
| `fonts.py` | Nome da família de um arquivo de fonte (V2-07): tabela ``name`` do OpenType/TrueType/TTC. |
| `fsutil.py` | Utilidades de arquivo portáveis usadas pelo ``core`` (D-022). |
| `games.py` | Jogos sem baixar de novo (V2-13): bibliotecas da Steam e manifestos da Epic. Regras puras. |
| `installers/__init__.py` | Pacote. |
| `installers/detect.py` | Detecção do tipo de instalador pelo conteúdo (PLANO.md §13.3). Puro. |
| `inventory.py` | Inventário de apps instalados e classificação para a receita (PLANO.md §7.1, item 8). |
| `inventory_snapshot.py` | Inventário de um PC para o relatório antes/depois (V2-19). Só o que é preciso comparar. |
| `isos.py` | Informações lidas de uma ISO do Windows (somente leitura — D-002). |
| `layout.py` | Layout fixo do pendrive (PLANO.md §5) e o arquivo marcador. |
| `live.py` | Prévia do modo "aplicar neste PC" (D-033, R-54): o que cada etapa faria, sem fazer nada. |
| `maintenance.py` | Especificação das tarefas de manutenção (V2-18). Função pura: o mesmo pedido, a mesma tarefa. |
| `manifest/__init__.py` | Pacote. |
| `manifest/manifest.py` | Manifesto de arquivos do pendrive (PLANO.md §8.5, R-22). |
| `media.py` | Pendrive de instalação comum, gravado pelo Rufus ou pela Ferramenta de Criação de Mídia |
| `paths/__init__.py` | Pacote. |
| `paths/templates.py` | Moldes de caminho portáveis entre máquinas (PLANO.md §6.3). |
| `pc_backup.py` | Backup do PC para outro disco (V3-09/10, D-051): regras puras, sem Windows. |
| `personal.py` | Aparência pessoal (V2-06, D-037): regras puras de captura e validação. |
| `planner/__init__.py` | Pacote. |
| `planner/models.py` | Modelos do plano de execução do Agente (PLANO.md §11). |
| `planner/planner.py` | Planejador de fases (PLANO.md §11.2, regras R1–R15). |
| `presets.py` | Perfis rápidos (V2-15): aplicar é **mesclar** com a receita e nunca desmarca nada (D-040). |
| `recipe/__init__.py` | Pacote. |
| `recipe/io.py` | Leitura, gravação, criação e migração da receita. |
| `recipe/models.py` | Modelo da receita (PLANO.md §6). |
| `recipe/validation.py` | Regras de validação da receita (PLANO.md §6.2). |
| `regional.py` | Padrões regionais do PC atual para a receita nova (D-030): formatos, teclado e fuso. |
| `rufus.py` | Opções que o Rufus gravou no pendrive (V3-07, H39). Leitor puro, sem Windows. |
| `secrets.py` | Registro único de segredos do processo (R-53, D-036). |
| `share.py` | Receitas compartilháveis e modelos prontos (V2-23, D-040). |
| `start_layout.py` | Iniciar e barra de tarefas (V2-04): arquivos que o Windows 11 lê no perfil Default. |
| `state/__init__.py` | Estado do Agente. |
| `state/migrations.py` | Migrações do ``estado.json`` (R-47). |
| `state/models.py` | Estado persistido do Agente e transições válidas (PLANO.md §11.4, R-29, R-30). |
| `suggest.py` | Assistente "o que levar" (V2-20): pontuação e ordenação puras e determinísticas. |
| `summary.py` | Resumo da execução do Agente (PLANO.md §12.4, item 36). |
| `text.py` | Utilidades de texto puras. |
| `unattend/__init__.py` | Pacote. |
| `unattend/commands.py` | Linhas de comando embutidas no ``autounattend.xml`` (PLANO.md §9.2). |
| `unattend/generator.py` | Geração do ``autounattend.xml`` (PLANO.md §9). |
| `usb_safety.py` | Travas para o WinKit gravar um pendrive (V3-13, D-045, R-60). Regras puras. |
| `user_folders.py` | Pastas do usuário em outro disco (V2-14): regras puras. |
| `userassist.py` | Uso de programas pelo ``UserAssist`` do Explorer (V2-20). Leitor puro, sem Windows. |
| `vdf.py` | Formato texto ``KeyValues`` da Valve (``libraryfolders.vdf``) — leitor e gravador puros. |
| `ventoy/__init__.py` | Pacote. |
| `ventoy/config.py` | Mesclagem do ``ventoy.json`` (PLANO.md §8.3). |
| `ventoy/detect.py` | Detecção do pendrive Ventoy a partir da lista de partições (PLANO.md §8.1). |
| `versions.py` | Comparação de versões tolerante (V2-21): ``1.2.3.4``, ``2024.10``, ``1.0.0-beta``, ``24.08``. |
| `volumes.py` | Resolver de volumes (D-035, R-52): achar pelo número de série, usar a letra **atual**. |
| `wifi.py` | Perfis de Wi-Fi exportados pelo Windows (V2-02, D-036). |
| `winget_manifest.py` | Leitura do manifesto YAML gravado pelo ``winget download`` (PLANO.md §7.1.4). |

### `i18n/` — textos em pt-BR, en-US e es, e a tradução na borda (D-031)

| Arquivo | O que faz |
|---|---|
| `__init__.py` | Textos exibidos ao usuário em pt-BR, en-US e es (R-03, D-030). |
| `core.py` | Tradução: ``t``, ``tn`` e ``render`` no idioma atual do processo (R-03, D-030). |
| `format.py` | Números, tamanhos, datas e durações por idioma, sem o módulo ``locale`` (D-030). |
| `languages.py` | Idiomas suportados e normalização de etiquetas BCP-47 (D-030). |
| `messages/__init__.py` | Tabelas de mensagens, uma por idioma, com as mesmas chaves (R-51). |
| `messages/en_us.py` | English (United States) texts. Same keys and placeholders as ``pt_br`` (R-51). |
| `messages/es.py` | Textos en español neutro (tú). Mismas claves y marcadores que ``pt_br`` (R-51). |
| `messages/pt_br.py` | Textos em português do Brasil: a base de todas as traduções (R-03, R-51). |
| `msg.py` | Mensagem estruturada: chave + parâmetros, traduzida só na borda (D-031). |

### `platform/` — tudo que toca o Windows, atrás de interfaces; `fakes/` tem as versões de teste

| Arquivo | O que faz |
|---|---|
| `__init__.py` | Camada de plataforma: único lugar com efeitos colaterais no Windows. |
| `accounts.py` | Contas locais (rede de segurança da hipótese H11). |
| `appx.py` | Pacotes Appx/MSIX: remoção para todos os usuários (PLANO.md §13.5, item 11). |
| `associations.py` | ``dism`` para exportar e importar os apps padrão (V2-05). Só código de saída e arquivos. |
| `browsers.py` | Gravar e desfazer as políticas de navegador (V2-12) no ``HKLM``. |
| `copy.py` | Cópia de pastas e arquivos para captura e restauração de backups (PLANO.md §13.1, D-014). |
| `devices.py` | Dispositivos com problema pelo CIM ``Win32_PnPEntity`` (V2-09). Só JSON, nunca texto. |
| `disk_info.py` | Discos de destino do backup e saúde do PC antes de formatar (V3-09, V3-15, V3-16). |
| `disks.py` | Discos, partições e leitura de ISO (somente leitura — D-002). Exige administrador. |
| `dns.py` | Servidores DNS e DNS criptografado (DoH) pelo módulo ``DnsClient`` (V2-16). |
| `download.py` | Download HTTP com progresso, pausa, retomada e conferência de SHA-256 (V3-07, V3-08; R-61). |
| `drivers.py` | Drivers de terceiros: listar, exportar e instalar (PLANO.md §7.2, M4). |
| `environment.py` | Unidades, rede, versão do Windows e trava de instância única. |
| `external_tools.py` | Ventoy e Rufus: baixar da release oficial, conferir e abrir para a pessoa usar (V3-07, D-046). |
| `fakes/__init__.py` | Implementações falsas das interfaces de ``winkit.platform`` para testes (R-40). |
| `fakes/apps.py` | Dublês de inventário, winget, instaladores e atalhos. |
| `fakes/associations.py` | Dublê do dism de apps padrão. |
| `fakes/backup.py` | Dublês de cópia de sombra (a "cópia de sombra" falsa é a própria pasta de origem). |
| `fakes/disks.py` | ``DiskInspector`` falso: partições e ISOs programadas. |
| `fakes/dns.py` | Dublê do cliente DNS: adaptadores e DoH em memória. |
| `fakes/drivers.py` | ``DriverManager`` falso. |
| `fakes/images.py` | Dublê das imagens do Windows e do montador de ISO (V3-11). |
| `fakes/powershell.py` | ``PowerShell`` falso: casa o corpo do script por trecho e devolve objetos prontos. |
| `fakes/registry.py` | Registro falso em memória (chaves sem diferenciar maiúsculas, como no Windows). |
| `fakes/restore.py` | Dublê dos pontos de restauração. |
| `fakes/runner.py` | ``CommandRunner`` falso: grava as chamadas e devolve respostas programadas. |
| `fakes/services.py` | ``Services`` do Studio montado só com dublês (um lugar para acrescentar campos novos). |
| `fakes/system.py` | Dublês de agendador, contas, ambiente e pastas conhecidas. |
| `fakes/system_tweaks.py` | Dublês de Appx e recursos do sistema. |
| `fakes/volumes.py` | Dublê dos volumes: cada letra aponta para uma pasta temporária. |
| `fakes/wifi.py` | Dublê do Wi-Fi: perfis em memória e exportação a partir de XMLs de exemplo. |
| `features.py` | Recursos opcionais e capacidades do Windows (Recall, WSL, OpenSSH…) e nome do computador. |
| `fonts.py` | Carregar uma fonte na sessão atual sem sair dela (V2-07, modo ao vivo). |
| `hosts.py` | O arquivo ``hosts`` do Windows (V2-16). As regras do bloco ficam em ``core/dns.py``. |
| `image_tools.py` | Imagens do Windows (``install.wim``, ``boot.wim``) pelo módulo DISM do PowerShell (V3-11, D-048). |
| `installers.py` | Execução de instaladores (PLANO.md §13.3): argumentos em lista, tempo limite, sem janela. |
| `inventory.py` | Leitura dos apps instalados (registro de desinstalação + pacotes da Loja). |
| `iso_mount.py` | Montagem **somente leitura** de uma ISO (V2-08: fonte offline do .NET 3.5). |
| `iso_writer.py` | Grava uma pasta de instalação do Windows como ISO de boot (V3-11, D-048, H36). |
| `known_folders.py` | Pastas conhecidas do Windows (``SHGetKnownFolderPath``) — PLANO.md §6.3. |
| `locale.py` | Idioma e padrões regionais do Windows atual, por API e registro (R-13, D-030). |
| `netdrives.py` | Unidades de rede (V2-17): registro ``Network`` e ``WScript.Network`` para o modo ao vivo. |
| `personal.py` | Aplicar a aparência na sessão atual (V2-06, modo ao vivo). |
| `power.py` | Ociosidade da sessão e reinicialização (PLANO.md §11.5). |
| `powershell.py` | Execução de PowerShell com UTF-8 e resultado em JSON (ARQUITETURA.md, R-13, R-14). |
| `registry.py` | Registro do Windows via ``winreg`` (PLANO.md §13.2). |
| `restore.py` | Pontos de restauração do sistema (V2-10, D-033), por CIM — nunca por texto (R-13). |
| `runner.py` | Único ponto de execução de processos externos (ARQUITETURA.md, R-11). |
| `scheduler.py` | Tarefa agendada da Fase 2 (D-012, D-023). |
| `services.py` | Fábrica das implementações reais da plataforma (injeção de dependência simples). |
| `services_base.py` | Consultas de serviços do Windows por código de saída (R-13). |
| `session.py` | Informações da sessão atual (privilégio, ociosidade). |
| `shortcuts.py` | Atalhos .lnk via WScript.Shell (PowerShell). |
| `snapshot.py` | Inventário do PC para o relatório antes/depois (V2-19), usado pelo Studio e pelo Agente. |
| `system.py` | Informações básicas do sistema e caminhos de ferramentas nativas (R-12). |
| `usage.py` | Uso de programas (``UserAssist``) pelo registro do usuário atual (V2-20). |
| `usb_writer.py` | O único lugar que apaga e formata um disco: o pendrive escolhido (V3-13, D-045, R-60). |
| `volumes.py` | Volumes do PC pelo CIM ``Win32_Volume`` (D-035). Só JSON e números (R-13). |
| `vss.py` | Cópias de sombra (VSS) para capturar arquivos em uso (PLANO.md §7.4.2, D-006). |
| `wifi.py` | Perfis de Wi-Fi pelo ``netsh wlan`` (V2-02). |
| `window_style.py` | Barra de título, contorno e cantos da janela no tema do app (Windows 11, DWM; V3-03). |
| `windows_download.py` | Link oficial da ISO do Windows, obtido pelo Fido (V3-08, D-047, H37). |
| `windows_update.py` | Windows Update pela API COM ``Microsoft.Update.Session`` (PLANO.md §20, M8; D-011). |
| `winget.py` | winget: export, download, install (PLANO.md §7.1.4, §13.4). |

### `collector/` — casos de uso no PC atual: ler apps, drivers, backups e o resto da receita

| Arquivo | O que faz |
|---|---|
| `__init__.py` | Pacote. |
| `app_updates.py` | Atualizar os instaladores do pendrive (V2-21, D-041). |
| `apps.py` | Coleta de aplicativos do PC atual (PLANO.md §7.1, itens 8 e 9). |
| `associations.py` | Apps padrão do PC atual (V2-05): exporta pelo ``dism`` e guarda o XML inteiro no pendrive. |
| `backups.py` | Backups de pastas e arquivos de configuração (PLANO.md §7.3, §7.4; itens 12, 16, 28, 30). |
| `browsers.py` | Navegadores e extensões instaladas neste PC (V2-12). |
| `drivers.py` | Coleta de drivers do PC atual (PLANO.md §7.2, item 7). |
| `env.py` | Variáveis de ambiente do PC atual (V2-22): só o que **não** é padrão do Windows. |
| `features.py` | Recursos do Windows ligados no PC atual (V2-08): sugestões para a receita. |
| `fonts.py` | Fontes instaladas no PC atual (V2-07). |
| `games.py` | Jogos instalados em outro disco (V2-13): bibliotecas da Steam e jogos da Epic. |
| `netdrives.py` | Unidades de rede do PC atual (V2-17). |
| `pc_backup.py` | Backup do PC para outro disco: copiar, conferir e trazer de volta (V3-09/10, D-051). |
| `personal.py` | Aparência deste PC (V2-06): valores do HKCU validados e o papel de parede. |
| `snapshot.py` | Inventário "antes" (V2-19): gravado no pendrive ao construir. |
| `start_layout.py` | Iniciar e barra de tarefas deste PC (V2-04). |
| `suggest.py` | Assistente "o que levar" (V2-20): analisa este PC e sugere, explicando o porquê. |
| `user_folders.py` | Pastas do usuário (V2-14): detectar as que já estão em outro disco e "Copiar agora". |
| `wifi.py` | Coleta das redes Wi-Fi salvas no PC atual (V2-02, D-036). |

### `builder/` — montar e validar o pendrive

| Arquivo | O que faz |
|---|---|
| `__init__.py` | Pacote. |
| `build.py` | Orquestra a construção do pendrive (PLANO.md §8.4). |
| `custom_iso.py` | ISO personalizada: uma **cópia** da ISO original com drivers, atualizações, edições e apps |
| `isos.py` | Leitura das ISOs do pendrive, com cache (PLANO.md §8.2). |
| `target.py` | Escolha do pendrive de destino (PLANO.md §8.1, D-034). |
| `usb_media.py` | O WinKit grava a ISO num pendrive, sem Ventoy nem Rufus (V3-13, D-045, D-049). |
| `validate.py` | Validação do pendrive sem alterar nada (PLANO.md §8.6). |

### `agent/` — o Agente que roda na instalação: fases, executor e etapas (`steps/`)

| Arquivo | O que faz |
|---|---|
| `__init__.py` | Pacote. |
| `cleanup.py` | Limpeza ao final (PLANO.md §10.4, D-024). |
| `eventlog.py` | Log do Agente: texto legível (pt-BR) + eventos JSONL (PLANO.md §11.7). |
| `executor.py` | Executa as etapas de uma fase do plano (ARQUITETURA.md §4.2). |
| `fakes.py` | ``AgentServices`` montado só com dublês (testes e simulação). |
| `integrity.py` | Verificação de integridade do conteúdo do pendrive antes de executar (R-22). |
| `live.py` | Modo "aplicar neste PC" (V2-03, D-033): a receita num Windows já instalado. |
| `main.py` | Ponto de entrada do Agente: ``winkit-agent.exe phase1 \| phase2 \| retry \| summary``. |
| `paths.py` | Caminhos locais do Agente no Windows novo (D-013). |
| `pendrive.py` | Localiza o pendrive pelo marcador — nunca pela letra (R-31). |
| `phases.py` | Orquestração das fases do Agente (PLANO.md §11, D-009, D-012, D-023). |
| `progress.py` | Interface entre o Agente e a apresentação (sem Qt — R-35). |
| `reboot.py` | Política de reinicialização da Fase 2 (PLANO.md §11.5). |
| `services.py` | Serviços de plataforma usados pelo Agente (injeção de dependência). |
| `steps/__init__.py` | Pacote. |
| `steps/account.py` | Etapa: conta extra (V2-11, R24). |
| `steps/app.py` | Etapas de aplicativos (M5): instalador offline, winget online e atalhos de portáteis. |
| `steps/backup.py` | Etapa: restaurar uma pasta ou arquivo de configuração (M6, itens 13, 14, 30). |
| `steps/base.py` | Contrato das etapas do Agente (ARQUITETURA.md §4.1, R-29). |
| `steps/browser.py` | Etapa: navegador pronto (V2-12, R21). As políticas no ``HKLM`` valem quando o navegador for |
| `steps/compare.py` | Etapa: relatório antes/depois (V2-19, R29). Compara o Windows novo com o inventário do PC |
| `steps/default_apps.py` | Etapas: apps padrão (V2-05, R20). |
| `steps/driver.py` | Etapa: instalar um pacote de drivers do pendrive com ``pnputil`` (M4). |
| `steps/driver_report.py` | Etapa: dispositivos sem driver e busca dirigida no Windows Update (V2-09, R28). |
| `steps/env.py` | Etapa: variáveis de ambiente e PATH (V2-22, R26). |
| `steps/feature.py` | Etapa: ligar um recurso do Windows (V2-08, R19). |
| `steps/finalize.py` | Etapa final: resumo (item 36), atalho na área de trabalho e limpeza. |
| `steps/font.py` | Etapa: instalar uma fonte para todos os usuários (V2-07). |
| `steps/game_library.py` | Etapa: jogos sem baixar de novo (V2-13, R22). |
| `steps/maintenance.py` | Etapas de manutenção (V2-18, R27). |
| `steps/network_drive.py` | Etapa: unidade de rede mapeada (V2-17, R25). |
| `steps/network_privacy.py` | Etapas: servidores DNS / DoH e bloqueio pelo ``hosts`` (V2-16, R18). |
| `steps/pc_restore.py` | Etapa: trazer o backup do PC de volta depois de instalar (V3-10, D-051). |
| `steps/personal.py` | Etapa: aparência pessoal (V2-06, R23). |
| `steps/registry.py` | Mapa tipo de etapa → implementação. |
| `steps/restore.py` | Etapa: ponto de restauração "Windows pronto" ou "antes de aplicar" (V2-10, D-033). |
| `steps/start_layout.py` | Etapa: Iniciar e barra de tarefas no perfil Default (V2-04, R20). |
| `steps/system.py` | Etapas de sistema: bloatware (item 11, 37), energia (item 34), nome do computador (item 33). |
| `steps/tweak.py` | Etapa: aplicar um ajuste do catálogo (M7, itens 31, 32; R-34). |
| `steps/user_folders.py` | Etapa: pastas do usuário em outro disco (V2-14, R16). |
| `steps/wifi.py` | Etapa: adicionar uma rede Wi-Fi antes do login (V2-02, R17, D-036). |
| `steps/windows_update.py` | Etapa: Windows Update depois da instalação (item 21, versão leve — D-011). |
| `store.py` | Persistência atômica do ``estado.json`` (R-16, R-30). |
| `ui/__init__.py` | Interface Qt do Agente (Fase 2). Único lugar do Agente que importa PySide6 (R-35). |
| `ui/qt.py` | Janela, bandeja e diálogos da Fase 2 (PLANO.md §12, D-008, D-026). |
| `ui_select.py` | Escolhe a apresentação da Fase 2 conforme o modo da receita (D-008). |

### `cli/` — a linha de comando `winkit`

| Arquivo | O que faz |
|---|---|
| `__init__.py` | Pacote. |
| `main.py` | Linha de comando do WinKit Studio (D-004). |

### `ui/` — componentes visuais compartilhados (tema, widgets)

| Arquivo | O que faz |
|---|---|
| `__init__.py` | Kit visual compartilhado (PySide6) — estilo inspirado no macOS (D-026). |
| `theme.py` | Tema claro/escuro inspirado no macOS ("Ajustes do Sistema"), D-026. |
| `widgets.py` | Componentes no estilo macOS: chave liga/desliga, grupos arredondados, linhas, ícones (D-026). |

### `studio/` — o WinKit Studio: controlador e páginas

| Arquivo | O que faz |
|---|---|
| `__init__.py` | Pacote. |
| `controller.py` | Fachada do WinKit Studio sem Qt (R-36): a GUI só chama estes métodos. |
| `main.py` | Ponto de entrada do WinKit Studio (GUI). |
| `preferences.py` | Preferências do Studio (idioma e tema), em ``%APPDATA%\WinKit\studio.json`` (D-030, D-042). |
| `ui/__init__.py` | Pacote. |
| `ui/base.py` | Base das páginas do Studio e execução de tarefas demoradas fora da thread da interface (R-37). |
| `ui/pages/__init__.py` | Páginas do WinKit Studio, uma por seção da barra lateral (D-042). |
| `ui/pages/bring.py` | Grupo "O que levar": aplicativos, configurações dos apps e drivers. |
| `ui/pages/common.py` | Peças comuns às páginas do Studio. Todo texto vem do ``i18n`` (R-03, R-55). |
| `ui/pages/customiso.py` | ISO personalizada (V3-11/12): uma cópia da ISO; a original nunca é modificada (D-044). |
| `ui/pages/finish.py` | Grupo "Concluir": primeiro login e revisar/construir. |
| `ui/pages/network.py` | Grupo "Rede": Wi-Fi, DNS e bloqueios, unidades de rede (M14). |
| `ui/pages/pcbackup.py` | Backup do PC para outro disco e "Antes de formatar" (V3-09, V3-10, V3-15, V3-16). |
| `ui/pages/prepare.py` | Grupo "Preparar": pendrive e Windows/conta (R-36: sem lógica de negócio). |
| `ui/pages/system.py` | Grupo "Sistema": apps pré-instalados, ajustes, energia e atualizações. |
| `ui/pages/writeusb.py` | O WinKit grava o pendrive (V3-13, D-045): escolher a ISO, o pendrive e o tipo de PC. |
| `ui/window.py` | Janela principal do WinKit Studio: barra lateral agrupada + páginas (D-042). |

### `data/` — catálogos versionados (YAML) e modelos de receita

| Arquivo | O que tem |
|---|---|
| `app_catalog.yaml` | Apps conhecidos (PLANO.md §15.1): como reconhecer no inventário, como instalar em |
| `bloatware.yaml` | Apps pré-instalados do Windows (PLANO.md §14.1). |
| `browsers.yaml` | Navegadores que o WinKit configura por política oficial (V2-12, M15; D-038). |
| `default_excludes.yaml` | Exclusões padrão de todo backup (PLANO.md §7.4.4). Nome de pasta ou padrão de arquivo, |
| `dns_providers.yaml` | Servidores DNS públicos que o WinKit sabe configurar (V2-16, M14). |
| `downloads.yaml` | Fontes oficiais de programas que o WinKit baixa (R-61, V3-07). Só releases dos próprios autores. |
| `dpapi_patterns.yaml` | Dados protegidos por DPAPI ou presos à conta/máquina (PLANO.md §7.4.6). Geram AVISO na |
| `driver_classes.yaml` | Classes de driver (ClassName do Windows). `priority` menor instala antes: rede e |
| `editions.yaml` | Chaves GENÉRICAS de instalação publicadas pela Microsoft (D-016). Não ativam o Windows: |
| `extensions.yaml` | Extensões sugeridas (V2-12). Ids das lojas oficiais; `firefox_slug` é o nome curto no AMO. |
| `features.yaml` | Recursos do Windows que o WinKit sabe ligar (V2-08, M14). |
| `file_associations.yaml` | Grupos de apps padrão (V2-05, M15). Cada grupo junta as extensões e protocolos que o |
| `game_saves.yaml` | Saves de jogos conhecidos (V2-20, M17): subconjunto curado à mão. Os moldes usam as mesmas |
| `hosts_blocklists.yaml` | Listas de bloqueio pelo arquivo hosts (V2-16, M14). |
| `i18n_en_us.yaml` | Traduções dos catálogos (inglês) — D-030, R-51. |
| `i18n_es.yaml` | Traduções dos catálogos (espanhol) — D-030, R-51. |
| `installer_signatures.yaml` | Detecção do tipo de instalador por conteúdo (PLANO.md §13.3). A ORDEM importa: a primeira |
| `personal_settings.yaml` | Aparência pessoal (V2-06, M15; D-037). Só estes valores do HKCU são levados, e cada um é |
| `presets.yaml` | Perfis rápidos (V2-15, M15): um clique marca um conjunto coerente de itens que já existem |
| `protected_env.yaml` | Variáveis de ambiente que o WinKit nunca leva nem grava (V2-22, M14): são do próprio |
| `search_providers.yaml` | Buscadores (V2-12). `{searchTerms}` é trocado pelo texto buscado (formato das políticas). |
| `tweaks.yaml` | Ajustes do sistema (PLANO.md §14.2). Cada item tem `source` e `undo` (R-33) e só usa |
| `templates/` | 5 modelos de receita prontos (`.winkit.json`) |

## `tests/`

Uma pasta por camada (`agent/`, `builder/`, `cli/`, `collector/`, `core/`, `data/`, `fixtures/`, `i18n/`, `platform/`, `studio/`, `ui/`). `fixtures/` guarda as amostras fixas (XML de referência, layouts do Iniciar); `test_architecture.py` confere as regras do código; `factories.py` monta receitas de teste.
