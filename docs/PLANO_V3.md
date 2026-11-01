# WinKit v3 — Plano de implementação (M19 a M26)

> **Estado deste documento:** **aprovado pelo dono do projeto em 2026-11-01**, com as sugestões do §14 e os pontos assumidos do §1.2; em implementação (ver `STATUS.md`).
> Quando aprovado, vira documento vivo como o `PLANO.md` e o `PLANO_V2.md`: muda no mesmo commit que mudar o código (`CLAUDE.md`).
>
> **Relação com os outros documentos:** a v1 (`PLANO.md`, M0–M10) e a v2 (`PLANO_V2.md`, M11–M18) estão implementadas. Este arquivo descreve **só o que é novo**. Onde a v3 muda algo antigo, a seção diz "muda o PLANO.md §x" ou "muda a D-nnn". As decisões propostas (D-044 em diante) e as regras novas (R-59 em diante) só entram no `ARQUITETURA.md` no primeiro commit do marco que as usa, depois da aprovação.
>
> **Origem:** a conversa de 2026-10-31 a 2026-11-01 com o dono, e duas pesquisas (ferramentas que personalizam a mídia de instalação; ferramentas de backup). As respostas do dono estão citadas como **[dono]**.
>
> **Aviso que continua valendo:** pré-alpha, pessoal e 100% vibe-codado (D-028). Cada marco termina com um roteiro de validação em VM. A v3 mexe em coisas **destrutivas** (gravar pendrive) e **pesadas** (montar imagens do Windows): por isso cada uma tem testes de proteção próprios.

## Sumário

0. [Como ler](#0-como-ler)
1. [Escopo: os itens da v3](#1-escopo-os-itens-da-v3)
2. [O que muda nos princípios](#2-o-que-muda-nos-princípios)
3. [Decisões propostas (D-044 a D-054)](#3-decisões-propostas-d-044-a-d-054)
4. [Regras novas do código (R-59 a R-64)](#4-regras-novas-do-código-r-59-a-r-64)
5. [Arquitetura transversal](#5-arquitetura-transversal)
6. [M19 — Correções: velocidade, nitidez e janela; testes na VM](#6-m19--correções-velocidade-nitidez-e-janela-testes-na-vm)
7. [M20 — Modo em etapas e escolha do caminho](#7-m20--modo-em-etapas-e-escolha-do-caminho)
8. [M21 — Baixar a ISO oficial](#8-m21--baixar-a-iso-oficial)
9. [M22 — Backup para HD secundário](#9-m22--backup-para-hd-secundário)
10. [M23 — ISO personalizada](#10-m23--iso-personalizada)
11. [M24 — O WinKit grava o pendrive](#11-m24--o-winkit-grava-o-pendrive)
12. [M25 — Windows 7 e 8.1 em modo limitado](#12-m25--windows-7-e-81-em-modo-limitado)
13. [M26 — Fechamento da v3](#13-m26--fechamento-da-v3)
14. [Sugestões aguardando aprovação](#14-sugestões-aguardando-aprovação)
15. [Hipóteses novas (H36 a H48)](#15-hipóteses-novas-h36-a-h48)
16. [Riscos novos](#16-riscos-novos)
17. [Dívidas já previstas](#17-dívidas-já-previstas)
18. [Estratégia de testes da v3](#18-estratégia-de-testes-da-v3)
19. [Ordem, dependências e versões](#19-ordem-dependências-e-versões)
20. [O que depende do dono do projeto](#20-o-que-depende-do-dono-do-projeto)

---

## 0. Como ler

- Cada função nova tem um código **V3-nn**. As funções seguem os mesmos blocos do `PLANO_V2.md` §0 (objetivo, como se usa, dados, plataforma, segurança, testes, validação, arquivos, pronto quando), resumidos quando não há novidade.
- A skill `ponytail` é obrigatória na implementação (R-58): a menor mudança que resolve por inteiro. Este plano descreve **o que** cada função faz e **os limites**; o tamanho do código fica para a implementação.
- "Caminho" é a forma de levar o Windows ao PC: **Ventoy**, **Rufus**, **ferramenta da Microsoft**, **o WinKit grava o pendrive** ou **ISO personalizada** (§7.2).
- "Windows alvo" é o Windows que vai ser instalado (11, 10, 8.1 ou 7). O Studio continua rodando só no Windows 10 e 11.

## 1. Escopo: os itens da v3

| Código | Função | Marco |
|---|---|---|
| V3-01 | **Velocidade do Studio**: nenhuma tela trava esperando o Windows | M19 |
| V3-02 | **Nitidez em telas de alta resolução** (4K, escalas 150%–300%) | M19 |
| V3-03 | **Janela**: barra de título no tema do app, contorno fino, barra de rolagem discreta | M19 |
| V3-04 | **Testes na VM do dono**: guia para ligar o PC à sessão e scripts de VM | M19 |
| V3-05 | **Modo em etapas** (Voltar / Pular / Avançar), convivendo com a barra lateral **[dono]** | M20 |
| V3-06 | **Escolha do caminho** no início: Ventoy, Rufus, Microsoft, WinKit grava, ISO personalizada **[dono]** | M20 |
| V3-07 | **Ventoy e Rufus**: baixar do site oficial, abrir para a pessoa usar e detectar o resultado, inclusive as opções do Rufus **[dono]** | M20 |
| V3-08 | **Baixar a ISO oficial** com velocidade, porcentagem, conferência e pausa **[dono]** | M21 |
| V3-09 | **Backup para HD secundário** (seção própria e etapa do fluxo) **[dono]** | M22 |
| V3-10 | **Trazer o backup de volta**, à mão ou na instalação **[dono]** | M22 |
| V3-11 | **ISO personalizada**: cópia com drivers, atualizações, apps removidos, edições, recursos e ajustes **[dono]** | M23 |
| V3-12 | **ISO autossuficiente**: o WinKit inteiro dentro da cópia **[dono]** | M23 |
| V3-13 | **O WinKit grava o pendrive**, para UEFI, BIOS ou os dois **[dono]** | M24 |
| V3-14 | **Windows 7 SP1 e 8.1 em modo limitado**, 32 e 64 bits **[dono]** | M25 |

### 1.1 Respostas do dono que definem o escopo

- Modo em etapas e barra lateral **coexistem**.
- Tipo de PC: oferecer **todas as opções** (UEFI, BIOS, os dois); quando uma não serve para o Windows alvo, **avisar na tela**.
- Windows 7: o WinKit **não baixa** (a Microsoft não oferece mais); a pessoa aponta a ISO dela.
- Windows 10: oferecer **todas as versões que a Microsoft oferece** (edições, idiomas, 32 e 64 bits).
- ISO autossuficiente: a pessoa **escolhe onde salvar antes de começar**.
- Gravar o pendrive: confirmação **digitando a letra** do pendrive.
- Download: **conferir a integridade** e **pausar e retomar**.
- Backup: **.zip** opcional; **sem versões antigas**; **sem senha**; **só ao clicar**; pode rodar **enquanto a pessoa configura**; **avisos** conforme o que acontecer.
- Windows 7 "SP2": não existe oficialmente; o equivalente é o **Convenience Rollup (KB3125574)**, oferecido como opção dentro da ISO personalizada.

### 1.2 Assumido, a confirmar na aprovação

- O backup fica **nos dois lugares**: seção "Backup do PC" e etapa do fluxo de reinstalação.
- **Não existe modo espelho**: o backup nunca apaga nada, nem na origem nem no destino.

### 1.3 Fora do escopo da v3 (explicitamente)

- **Criar arquivos .rar** (formato fechado; criar exige o WinRAR licenciado). O backup compacta em .zip.
- **Embutir ou automatizar o Ventoy e o Rufus.** Eles são baixados do site oficial e abertos para a pessoa usar (D-046).
- **Baixar ISO de sites não oficiais**, inclusive do Windows 7.
- **Versões antigas do Windows 10** (1507 a 21H2): a Microsoft só oferece a última (22H2). O WinKit diz isso na tela.
- **Backup de imagem do disco inteiro** (estilo Macrium/Veeam). O backup é de arquivos.
- **Agendamento do backup** **[dono]**: só ao clicar.
- **Formatar qualquer disco que não seja o pendrive USB escolhido** (D-045).

## 2. O que muda nos princípios

| Princípio antigo | Passa a ser | Decisão |
|---|---|---|
| "A ISO do Windows nunca é modificada" (D-002) | **A ISO original nunca é modificada.** O WinKit pode gerar uma **cópia** personalizada, num arquivo novo, em pasta escolhida pela pessoa. | D-044 |
| "Nada pesado vai para dentro da ISO" (D-001) | Continua no modo Ventoy e no pendrive comum. Na **ISO autossuficiente**, que é opcional, o WinKit inteiro vai dentro da cópia, com aviso de tamanho. | D-044 |
| "Nunca particionar, formatar ou apagar discos" (D-017, CLAUDE.md) | Continua para todo disco, **exceto** o pendrive USB escolhido pela pessoa no caminho "o WinKit grava o pendrive", com as travas da D-045. O `autounattend.xml` continua sem `DiskConfiguration` (R-18). | D-045 |
| "Atualizações: só a opção leve" (D-011) | Na ISO personalizada, a pessoa pode integrar atualizações (`.msu`/`.cab`) na cópia. Fora dela, nada muda. | D-048 |
| "Dependências de produção: pydantic, PyYAML, PySide6" (R-43) | Acrescenta **`pycdlib`** (LGPL, Python puro) para montar a ISO. | D-048 |

O `CLAUDE.md`, o `ARQUITETURA.md` e os READMEs (R-56) são atualizados no commit que muda cada princípio, **não antes**.

## 3. Decisões propostas (D-044 a D-054)

### D-044 — Cópia personalizada da ISO, nunca a original
**Contexto:** o dono quer modificar a ISO e ter uma ISO que funcione sozinha. Mexer na original arrisca perder a única cópia e quebra a regra de mais peso do projeto.
**Decisão:** a ISO original é aberta só para leitura (montada com `-Access ReadOnly` ou lida pelo `pycdlib`). Todo trabalho acontece numa pasta de trabalho escolhida pela pessoa, e o resultado é um **arquivo novo** (`<nome>-winkit.iso`). O Construtor confere, antes e depois, que o SHA-256 da original não mudou (teste de proteção).
**Consequências:** precisa de espaço (cerca de 3× o tamanho da ISO, mais apps e backups na autossuficiente) e tempo; o Studio mostra as duas coisas antes de começar.

### D-045 — Formatar só o pendrive USB escolhido, com travas
**Contexto:** o dono quer que o WinKit grave o pendrive sozinho quando a pessoa não quiser Ventoy nem Rufus.
**Decisão:** só `platform/usb_writer.py` pode apagar um disco, e só se todas as travas passarem, conferidas **de novo imediatamente antes** de apagar:
1. o disco tem `BusType = USB` (CIM `MSFT_Disk`, número, nunca texto);
2. não é disco de sistema, de boot, de paginação nem tem o volume do Windows em execução;
3. o número do disco **e** o número de série são os mesmos mostrados à pessoa;
4. a pessoa **digitou a letra** do pendrive na confirmação, que mostra modelo, tamanho e o que existe nele hoje **[dono]**;
5. tamanho entre 8 GB e 512 GB (acima disso, provável HD externo: recusado com aviso).
**Consequências:** um HD externo USB nunca é gravado por engano; um pendrive acima de 512 GB precisa do Ventoy ou do Rufus.

### D-046 — Ventoy e Rufus: baixados, abertos e detectados, nunca embutidos
**Contexto:** os dois são GPLv3; o Rufus não tem linha de comando completa; o dono quer que o WinKit baixe e abra **[dono]**.
**Decisão:** o WinKit baixa o executável da página oficial de releases (GitHub de cada projeto), confere o SHA-256 quando o projeto publica (R-61), grava em `%LOCALAPPDATA%\WinKit\ferramentas\<nome>-<versão>\` e o **abre** para a pessoa usar (no Rufus, já com a ISO escolhida, `-i <iso>`). Depois o WinKit **detecta** o resultado no pendrive. Nenhum binário de terceiros vai no pacote do WinKit.
**Consequências:** nenhuma obrigação de GPL para o WinKit; precisa de internet na primeira vez; versões novas desses programas podem mudar o que o WinKit detecta (H39).

### D-047 — ISO oficial pelo Fido, download pelo WinKit
**Contexto:** a Microsoft não tem API pública de download; o Fido (GPLv3, do autor do Rufus) obtém o link oficial e é mantido em dia quando a Microsoft muda o site.
**Decisão:** o WinKit baixa o `Fido.ps1` oficial (R-61) e o roda só para **obter o link** (`-GetUrl`, saída é uma URL, não texto localizado). O download em si é do WinKit (`platform/download.py`, só biblioteca padrão), com progresso, velocidade, tempo restante, **pausa e retomada** (cabeçalho `Range`) e conferência do SHA-256 publicado pela Microsoft quando disponível (H38). Links da Microsoft expiram em 24 h: ao retomar depois disso, o WinKit pede um link novo e continua de onde parou.
**Consequências:** Windows 11, 10 e 8.1 baixáveis; 7 não. Se a Microsoft bloquear o acesso (acontece por região ou excesso de pedidos), a tela explica e oferece "usar uma ISO que já tenho".

### D-048 — Cópia personalizada com DISM e ISO montada pelo `pycdlib`
**Contexto:** gerar uma ISO de boot exige montar as imagens (DISM, que vem no Windows) e escrever o ISO com UDF + El Torito (BIOS e UEFI). O `oscdimg` da Microsoft vem no ADK, com redistribuição incerta.
**Decisão:**
- imagens (`install.wim`, `boot.wim`) alteradas pelo **DISM** via `platform/dism.py` (R-14, códigos de saída, nunca texto);
- ISO escrito pelo **`pycdlib`** (nova dependência, R-44), copiando os arquivos de boot **da própria ISO original** (`etfsboot.com`, `efisys.bin`), sem trocar nenhum;
- se o `oscdimg` já estiver instalado no PC (ADK), a pessoa pode escolher usá-lo.
**Consequências:** H36 precisa ser confirmada na VM antes do M23 seguir para a autossuficiente; se falhar, fica só o `oscdimg` (a tela explica como instalar o ADK).

### D-049 — Gravação do pendrive: FAT32 com `install.wim` dividido
**Contexto:** UEFI só dá boot por FAT32 sem driver extra; o `install.wim` costuma passar de 4 GB.
**Decisão:** a pessoa escolhe o tipo de PC **[dono]**:
| Opção | Partição | Observação |
|---|---|---|
| UEFI e BIOS (padrão) | MBR, uma partição FAT32 ativa | `bootsect /nt60` da própria ISO para o BIOS |
| Só UEFI | GPT, uma partição FAT32 | PCs de 2012 em diante |
| Só BIOS | MBR, FAT32 ativa | PCs antigos; Windows 11 avisa que não é suportado |
O `install.wim` acima de 4 GB vira `install.swm` (`dism /Split-Image`), que o instalador aceita (H40). Depois de gravar, o WinKit segue como no pendrive comum (D-034).
**Consequências:** sem NTFS no pendrive (evita o driver UEFI:NTFS do Rufus). O Windows 7 em UEFI tem restrições próprias (§12).

### D-050 — Windows 7 e 8.1: agente legado em PowerShell 2.0
**Contexto:** o Agente atual é Python 3.12 empacotado, que não roda no Windows 7 (e no 8.1 é incerto, H47). O dono quer o "modo limitado" **[dono]**.
**Decisão:** para Windows alvo 7 ou 8.1, o Construtor grava um **agente legado**: scripts PowerShell compatíveis com a versão 2.0, gerados a partir da receita pelo `core` (como o XML), sem Python. Só as funções marcadas como compatíveis entram (R-63, §12.3). O resumo final é um HTML simples gerado pelo script.
**Consequências:** duas implementações para algumas etapas (drivers, apps offline, backups, ajustes, Wi-Fi, energia). Testes comparam o plano dos dois agentes.

### D-051 — Backup: cópia simples, aditiva, conferida
**Contexto:** o objetivo é **formatar sem perder nada** **[dono]**; o espelho propaga apagamentos e vírus de resgate.
**Decisão:**
- cópia com robocopy (`/E`, nunca `/MIR` nem `/PURGE`; `/XJ` para não seguir junções), com cópia de sombra para arquivos abertos (reaproveita o M6);
- nunca apaga nada, nem na origem nem no destino; sem versões antigas, sem senha **[dono]**;
- **conferência**: depois de copiar, compara tamanho e SHA-256 de cada arquivo, gravando `WinKit-backup\<data>\manifesto.json`;
- **.zip opcional** (`zipfile` da biblioteca padrão, ZIP64 para mais de 4 GB) **[dono]**;
- disco identificado por um marcador `WinKit-backup\winkit-backup.json` com UUID, não pela letra;
- retoma de onde parou (o manifesto diz o que já foi conferido).
**Consequências:** um backup refeito copia de novo só o que mudou (robocopy compara data e tamanho); arquivos apagados no PC continuam no backup.

### D-052 — Modo em etapas e barra lateral sobre as mesmas páginas
**Decisão:** cada página do Studio é uma etapa. O modo em etapas é uma **ordem** de páginas, que depende do caminho e do Windows alvo, mais uma barra inferior (Voltar / Pular / Avançar) e um indicador "etapa 4 de 11". A barra lateral continua; clicar nela não perde o progresso. Etapas que não servem para o caminho ou o Windows alvo aparecem esmaecidas, com o motivo (R-63). O progresso fica nas preferências do Studio, não na receita.

### D-053 — Central de tarefas longas, com fila por disco
**Contexto:** backup, download, ISO personalizada e gravação podem rodar enquanto a pessoa configura **[dono]**, e duas no mesmo disco ficam muito lentas.
**Decisão:** uma central de tarefas no Studio (um painel e um ícone na barra lateral) mostra cada tarefa com porcentagem, velocidade e tempo restante. Tarefas que usam o mesmo disco físico entram em **fila**; tarefas em discos diferentes rodam juntas. Avisos do sistema (bandeja) ao concluir, falhar, faltar espaço ou o disco ser desconectado **[dono]**. Fechar o Studio com tarefa em andamento pede confirmação.

### D-054 — Tarefas pesadas nunca na thread da interface
**Contexto:** o dono percebeu lentidão; a medição mostrou que as telas desenham em menos de 0,3 s, e a demora vem de consultas ao Windows feitas ao abrir a tela (listar discos pelo PowerShell, somar o tamanho do pendrive inteiro).
**Decisão:** R-59. Telas mostram primeiro o que está em cache e completam em segundo plano, com indicador de "carregando".

## 4. Regras novas do código (R-59 a R-64)

- **R-59** Nenhuma chamada a `platform` que fale com o sistema (PowerShell, CIM, registro remoto, varredura de disco, rede) roda na thread da interface. O `refresh()` de uma página só lê dados em memória; o resto passa pelo executor de tarefas. Teste: com serviços falsos que demoram 2 s, toda página abre em menos de 200 ms.
- **R-60** Apagar, particionar ou formatar disco só em `platform/usb_writer.py`, só com as travas da D-045 conferidas imediatamente antes. Teste de proteção: o disco do sistema, um disco interno e um HD externo acima de 512 GB nunca são aceitos, mesmo com confirmação.
- **R-61** Programas e arquivos baixados (Ventoy, Rufus, Fido, ISOs, atualizações) só de URLs oficiais listadas em `data/downloads.yaml`, com SHA-256 conferido quando o fornecedor publica. Nada baixado é executado antes da conferência.
- **R-62** Imagem montada pelo DISM é sempre desmontada com descarte em `finally`; ao iniciar, o Studio limpa montagens órfãs do WinKit (`/Cleanup-Mountpoints` só nas pastas do WinKit).
- **R-63** Toda função declara os Windows alvo que suporta (`targets: [11, 10, 8.1, 7]` no catálogo ou na etapa). O planejador nunca põe uma etapa num Windows que ela não suporta, e a interface mostra o motivo.
- **R-64** A ISO original é aberta só para leitura; teste de proteção confere que o SHA-256 dela não muda depois de gerar a cópia (D-044).

## 5. Arquitetura transversal

### 5.1 Receita: campos novos (aditivos, D-039 continua)
```
target_windows: { version: "11"|"10"|"8.1"|"7", arch: "x64"|"x86", edition, language }  # V3-06, V3-14
media: { path: "ventoy"|"rufus"|"microsoft"|"winkit_usb"|"custom_iso",                     # V3-06
         boot: "uefi_bios"|"uefi"|"bios",                                                    # V3-13
         custom_iso: { output: VolumeRef+caminho, self_contained: bool,                      # V3-11/12
                       drivers: bool, updates: [arquivo], remove_appx: bool,
                       editions: [nome], features: bool, offline_tweaks: bool,
                       win7_rollup: bool } }
pc_backup: { sources: [...], destination: VolumeRef, zip: bool,                              # V3-09
             restore_after_install: bool }                                                   # V3-10
```
O progresso do modo em etapas **não** fica na receita (D-052).

### 5.2 Catálogos novos e alterados
- `data/downloads.yaml` (novo): URLs oficiais e como conferir cada download (R-61).
- `data/windows_versions.yaml` (novo): versões, edições, arquiteturas, o que a Microsoft oferece para baixar, limites (Windows 11 só 64 bits e UEFI; Windows 7 sem Secure Boot…).
- `data/legacy_drivers.yaml` (novo): classes de dispositivo que o 7 e o 8.1 não têm nativamente (USB 3.0/xHCI, NVMe) e como reconhecê-las pelo HardwareID.
- `tweaks.yaml`, `bloatware.yaml`, `features.yaml`, `app_catalog.yaml`: campo `targets` (R-63); padrão `[11, 10]` para o que já existe.

### 5.3 Plataforma: módulos novos (todos com fake)
| Módulo | Faz |
|---|---|
| `platform/download.py` | HTTP com progresso, pausa, retomada e SHA-256 (biblioteca padrão) |
| `platform/external_tools.py` | baixa, confere e abre Ventoy, Rufus e Fido |
| `platform/media_detect.py` (estende `media.py`) | Ventoy instalado, versão; opções gravadas pelo Rufus |
| `platform/dism.py` | montar, alterar, desmontar, dividir e exportar imagens |
| `platform/iso_writer.py` | escreve a ISO com `pycdlib` (ou `oscdimg`) |
| `platform/usb_writer.py` | lista pendrives seguros e grava (D-045, R-60) |
| `platform/disk_info.py` | tipo (SSD/HD/NVMe/USB), barramento, espaço, BitLocker (CIM, JSON) |
| `platform/window_style.py` | atributos de janela do Windows 11 (DWM) para a barra e o contorno |

### 5.4 Studio
- Barra inferior do modo em etapas e ordem das etapas por caminho (D-052).
- Central de tarefas (D-053).
- Páginas novas: **Caminho**, **Windows alvo**, **Mídia** (muda conforme o caminho), **Backup do PC**, **ISO personalizada**, **Gravar pendrive**.
- Tela de abertura enquanto o programa carrega.

### 5.5 CLI
`winkit iso baixar`, `winkit iso personalizar`, `winkit pendrive gravar` (exige `--confirmar <letra>`), `winkit backup-pc fazer|conferir|restaurar`, `winkit ferramenta baixar ventoy|rufus`. Todos com `--simular` onde houver escrita.

## 6. M19 — Correções: velocidade, nitidez e janela; testes na VM

### 6.1 V3-01 — Velocidade do Studio
**Medição (2026-11-01):** com serviços falsos, todas as telas abrem em menos de 0,3 s. No Windows real, a demora vem de:
- tela **Pendrive**: lista discos pelo PowerShell e **soma o tamanho de tudo no pendrive** a cada abertura;
- tela **Pastas do usuário**: consulta os discos pelo PowerShell;
- **abertura do programa**: carrega o Qt inteiro antes de mostrar qualquer coisa.
**O que fazer:**
1. R-59 em todas as páginas: dados em cache primeiro, consulta em segundo plano, indicador "carregando";
2. tamanhos do pendrive lidos do `manifesto.json` (o Construtor já grava), sem varrer as pastas;
3. páginas montadas só na primeira vez que são abertas;
4. consultas CIM agrupadas numa única chamada de PowerShell quando a tela precisa de várias;
5. tela de abertura com o logo enquanto carrega;
6. Preferências: abrir sem consultar o sistema.
**Testes:** R-59 (serviços falsos lentos); tempo de abertura do Studio medido no CI do Windows, com limite.
**Pronto quando:** nenhuma tela leva mais de 200 ms para aparecer no CI com serviços falsos lentos; o dono confirma na VM e no PC dele.

### 6.2 V3-02 — Nitidez em telas de alta resolução
**Medição:** na escala de 250%, o texto fica nítido, mas ícones e logo ficam levemente borrados: são desenhados para no máximo 200% e esticados.
**O que fazer:** ícones e logo desenhados na escala real da tela (já são vetoriais), redesenhados ao mudar de monitor; revisar linhas de 1 pixel em escalas quebradas (150%, 175%).
**Testes:** captura em 100%, 150%, 250% e 300% (offscreen), comparando que os ícones têm pixels na escala certa.

### 6.3 V3-03 — Janela
**O que o print do dono mostrou:** Windows 11 no tema escuro, WinKit no tema claro, barra de título preta sobre conteúdo claro (o contraste dá a sensação de "cortado"); janela maximizada (o Windows 11 tira os cantos arredondados de qualquer janela maximizada); barra de rolagem lateral grossa e sempre visível.
**O que fazer:** `platform/window_style.py` usa os atributos de janela do Windows 11 (barra escura ou clara conforme o tema **do app**; cor do contorno; cantos arredondados); barra de rolagem fina, que aparece ao passar o mouse; no Windows 10, só barra e contorno (o sistema não arredonda).
**Hipótese:** H45.

### 6.4 V3-04 — Testes na VM do dono
**Objetivo:** que eu (Claude, na nuvem) consiga rodar os roteiros de validação numa VM no PC do dono.
**Como funciona:**
1. o dono instala o **Claude para desktop** e, em Settings → Claude Code → Remote Control, compartilha uma pasta (ex.: `C:\WinKit-testes`), ou roda `claude remote-control` nessa pasta;
2. a sessão pede acesso à pasta; o dono aprova no app;
3. com o acesso, a sessão roda os scripts de `scripts/vm/` no PC do dono:
   - `nova-vm.ps1`: cria uma VM **Hyper-V** (Windows 11 Pro; TPM virtual, Secure Boot, 4 GB, disco de 64 GB) com a ISO escolhida;
   - `ponto.ps1`: cria e volta pontos de restauração da VM (checkpoints);
   - `coletar-logs.ps1`: copia os logs do WinKit de dentro da VM para a pasta compartilhada;
4. para ver e clicar dentro da VM, o controle de tela do app desktop.
**Limite:** o Hyper-V não repassa pendrive USB para a VM. Por isso:
- caminhos com ISO (ISO personalizada e autossuficiente) são testados direto no Hyper-V;
- Ventoy e Rufus são testados no **VirtualBox** (repassa USB) ou num PC de testes.
**Arquivos:** `docs/validacao/VM_REMOTA.md`, `scripts/vm/*.ps1`.

## 7. M20 — Modo em etapas e escolha do caminho

### 7.1 V3-05 — Modo em etapas
Ordem padrão (muda conforme o caminho, §7.2):
1. Boas-vindas e aviso;
2. **Caminho**;
3. **Windows alvo** (versão, edição, idioma, 32/64 bits; "tenho a ISO" ou "baixar");
4. **Mídia** (Ventoy, Rufus, gravar pendrive ou ISO personalizada);
5. **Backup do PC** (opcional; começa em segundo plano);
6. Windows e conta;
7. O que levar (sugestões, apps, configurações, drivers, fontes, jogos…);
8. Sistema (ajustes, apps de fábrica, recursos, energia…);
9. Rede (Wi-Fi, DNS, unidades, navegadores);
10. Revisar e construir;
11. **Pronto**: "pode formatar" só aparece depois do backup terminado e conferido (D-051).
Barra inferior: Voltar / Pular / Avançar e "etapa n de N". Pular é sempre permitido; a revisão lista o que foi pulado.

### 7.2 V3-06 — Escolha do caminho
| Caminho | Para quem | O WinKit faz | A pessoa faz |
|---|---|---|---|
| **Ventoy** | quer várias ISOs num pendrive | detecta o Ventoy; se não tiver, baixa e abre o Ventoy2Disk; depois grava a pasta `WinKit\` | instala o Ventoy no pendrive pelo Ventoy2Disk |
| **Rufus** | já usa o Rufus | baixa e abre o Rufus com a ISO; detecta o pendrive gravado e as opções que o Rufus aplicou | grava a ISO pelo Rufus |
| **Ferramenta da Microsoft** | tem um pendrive feito por ela | detecta e segue (já existe, M13) | grava pela ferramenta |
| **O WinKit grava** | não quer outro programa | grava a ISO no pendrive (M24) | escolhe o pendrive e confirma digitando a letra |
| **ISO personalizada** | quer uma ISO pronta | gera a cópia (M23); depois a pessoa escolhe como levá-la ao pendrive (qualquer caminho acima) ou usa numa VM | escolhe o que entra e onde salvar |

### 7.3 V3-07 — Ventoy e Rufus
- **Detectar Ventoy:** partição `VTOYEFI` e `ventoy\ventoy.json` (já existe, M2); versão pelo arquivo `ventoy\version` quando houver.
- **Detectar Rufus e as opções dele:** ler os arquivos de resposta que o Rufus grava no pendrive (`autounattend.xml` na raiz e `sources\$OEM$\$$\Panther\unattend.xml`, H17/H39) e reconhecer as opções conhecidas: sem TPM/Secure Boot/RAM, conta local, sem coleta de dados, sem BitLocker, opções regionais.
- **Conflito Rufus × receita:** a tela mostra lado a lado ("o Rufus já faz isto"; "a receita pede aquilo") e pergunta qual vale. O WinKit nunca apaga o arquivo do Rufus sem a pessoa escolher; quando a pessoa escolhe a receita, o arquivo do Rufus é guardado em `WinKit\rufus-original\` antes.
- **Baixar e abrir:** D-046, R-61. O Rufus e o Ventoy pedem administrador e o SmartScreen pode avisar (H46).

## 8. M21 — Baixar a ISO oficial

**V3-08.** Escolhas: versão (11, 10, 8.1), edição, idioma, arquitetura (o 11 só tem 64 bits; o 10 e o 8.1, 32 e 64 **[dono]**). O link vem do Fido (D-047).
**Painel de download:** porcentagem, velocidade atual e média, tempo restante, tamanho baixado/total, botões **Pausar / Continuar / Cancelar**; continua sozinho se a rede cair; conferência no fim (SHA-256 publicado pela Microsoft, H38; senão, confere ao menos que a ISO abre e tem `sources\install.*`).
**Onde salvar:** a pessoa escolhe antes de começar; o WinKit avisa se o disco não tem espaço.
**Windows 7:** botão "usar uma ISO que já tenho", com conferência de que é o 7 SP1 (lê a versão de dentro da imagem).
**Hipóteses:** H37, H38.

## 9. M22 — Backup para HD secundário

### 9.1 V3-09 — Fazer o backup
**Onde fica:** seção "Backup do PC" (funciona sem reinstalar nada) e etapa 5 do modo em etapas (assumido, §1.2).
**Destino:** lista de discos com tipo e velocidade esperada (H44):
| Tipo | Rótulo | Escrita típica |
|---|---|---|
| NVMe | muito rápido | acima de 1 GB/s |
| SSD SATA | rápido | ~550 MB/s |
| HD | mais lento | 80–160 MB/s |
| USB desconhecido | "desconhecido" (a gaveta esconde o tipo; o WinKit não chuta) | medido |
| Pendrive USB 2.0 | muito lento | 3–10 MB/s |
Também: espaço livre, sistema de arquivos, BitLocker bloqueado, e aviso forte quando o destino é o **mesmo disco físico** do Windows.
**Origem:** pastas do usuário, pastas escolhidas, configurações de apps e saves que o WinKit já conhece, sugestões do assistente (V2-20).
**Antes de começar:** tamanho, quantidade de arquivos e **tempo previsto, medido**: o WinKit copia uma amostra (algumas dezenas de MB e algumas centenas de arquivos pequenos) para o destino e calcula, recalibrando durante a cópia. Avisos: espaço insuficiente, arquivo acima de 4 GB em FAT32, nomes inválidos no destino, permissões que se perdem em exFAT, caminhos longos.
**Durante:** D-051 e D-053 (central de tarefas, fila por disco, avisos). Se o backup e a gravação do pendrive usarem o mesmo disco, um espera o outro.
**Cópia extra no pendrive:** opcional, com aviso de tempo e tamanho.
**Depois:** relatório (copiados, conferidos, falharam e por quê) e o aviso "pode formatar" só se tudo foi conferido; se algum arquivo falhou, a pessoa decide.

### 9.2 V3-10 — Trazer de volta
- **À mão:** "Backup do PC" → escolher o backup (o WinKit acha o disco pelo marcador) → prévia → restaurar **somando** ao que existe, nunca substituindo sem escolha (D-007).
- **Na instalação:** opção "puxar o backup depois de instalar"; na Fase 2, o Agente procura o disco pelo marcador (R-52, por número de série, nunca letra) e restaura nas pastas certas do usuário novo. Disco ausente = etapa pulada com motivo.
- **.zip:** extraído na restauração, com a mesma regra de soma.

## 10. M23 — ISO personalizada

### 10.1 V3-11 — O que pode mudar na cópia
| Opção | Como | Windows alvo |
|---|---|---|
| Drivers do PC atual (e de uma pasta) no instalador e no Windows | DISM `/Add-Driver` no `boot.wim` (índices 1 e 2) e no `install.wim` | todos |
| Atualizações `.msu`/`.cab` apontadas pela pessoa | DISM `/Add-Package` | todos |
| Convenience Rollup do 7 ("SP2") | pré-requisito KB3020369 + KB3125574, do Catálogo do Microsoft Update (R-61) | 7 |
| Remover apps de fábrica | DISM `/Remove-ProvisionedAppxPackage`, lista do `bloatware.yaml` | 11, 10, 8.1 |
| Deixar só as edições escolhidas | DISM `/Export-Image` | todos |
| Ligar recursos do Windows | DISM `/Enable-Feature` | todos |
| Ajustes do registro já na imagem | hive offline carregado e descarregado em `finally` (R-17) | conforme `targets` |
Antes de começar: espaço necessário, tempo estimado e onde salvar **[dono]**.
Durante: central de tarefas, com a etapa atual ("montando a imagem 2 de 3…").

### 10.2 V3-12 — ISO autossuficiente
O que entra na cópia, além do §10.1: `autounattend.xml` na raiz e a pasta `WinKit\` inteira (receita, Agente, instaladores, drivers, backups). Na instalação, o bootstrap acha a pasta `WinKit\` na própria mídia, como no pendrive comum (D-034). Aviso de tamanho antes (pode passar de 10 GB); se a pessoa depois gravar num pendrive FAT32, o WinKit divide o que passar de 4 GB.
**Uso direto em VM:** é o caminho mais fácil para testar (V3-04).

## 11. M24 — O WinKit grava o pendrive

**V3-13.**
1. Lista só pendrives seguros (D-045), com modelo, tamanho e o que existe neles.
2. Tipo de PC: UEFI e BIOS (padrão), só UEFI ou só BIOS (D-049), com avisos por Windows alvo (o 11 em BIOS não é suportado; o 7 em UEFI tem restrições).
3. Confirmação: resumo + **digitar a letra do pendrive** **[dono]**.
4. Grava: limpa o disco, cria a partição, formata FAT32, copia os arquivos (dividindo o `install.wim`), torna o boot possível (`bootsect` para BIOS), confere os arquivos copiados.
5. Segue como pendrive comum: grava `autounattend.xml` e a pasta `WinKit\`.
**Testes de proteção (R-60):** disco do sistema, disco interno, HD externo USB acima de 512 GB, número de série diferente do mostrado, letra digitada errada: tudo recusado. Gravação simulada com fake que registra cada operação.
**Hipótese:** H40.

## 12. M25 — Windows 7 e 8.1 em modo limitado

### 12.1 Escolha
Sempre a última versão de cada um: **Windows 7 SP1** e **Windows 8.1** (com a atualização de abril de 2014), **32 ou 64 bits** **[dono]**. O 8.0 não entra (a 8.1 o substitui).

### 12.2 Avisos obrigatórios na tela
- Sem atualizações de segurança desde janeiro de 2023: usar desconectado da internet ou por conta e risco.
- Sem winget: só programas com instalador próprio.
- **Drivers que o Windows alvo não tem** (USB 3.0, NVMe): o WinKit procura no PC atual dispositivos dessas classes (`legacy_drivers.yaml`) e **avisa e pergunta** se continua assim ou se gera a ISO personalizada com esses drivers **[dono]**. Sem eles, o instalador pode não ver o teclado, o mouse ou o SSD.
- Windows 7 em UEFI: só 64 bits, exige CSM/vídeo legado em muitos PCs e não tem Secure Boot (H41).

### 12.3 O que funciona no modo limitado (R-63)
| Função | 7 | 8.1 |
|---|---|---|
| Instalação automática, conta local, idioma, fuso, nome do PC, edição | sim | sim |
| Drivers (`pnputil`) | sim | sim |
| Programas com instalador próprio (silencioso) | sim | sim |
| Backups de configurações e restauração | sim | sim |
| Wi-Fi (`netsh wlan add profile`) | sim | sim |
| Ajustes do registro marcados `targets: [7]`/`[8.1]` | sim | sim |
| Plano de energia | sim | sim |
| Recursos do Windows (DISM online) | sim | sim |
| Backup do PC (V3-09/10) | sim | sim |
| winget, apps de fábrica (Appx), Iniciar e barra, apps padrão, navegadores por política, DNS seguro, Windows Update, "aplicar neste PC" | não | não |
Etapas "não" aparecem esmaecidas com o motivo (D-052).

### 12.4 Agente legado (D-050)
Scripts PowerShell 2.0 gerados pelo `core` a partir da receita (testes de snapshot como o XML, R-42); log em texto e resumo HTML simples gravados no pendrive; mesmo bootstrap (`SetupComplete.cmd`).
**Hipóteses:** H42, H43, H47.

## 13. M26 — Fechamento da v3
Como o M18: revisão cruzada dos documentos (PLANO, ARQUITETURA com D-044 a D-054 e R-59 a R-64, STATUS, ESTRUTURA, READMEs nos três idiomas), traduções, capturas novas, `smoke.ps1` com os comandos novos (todos com `--simular`), auditoria (`ponytail-audit`), release `0.17.0` e relatório final.

## 14. Sugestões aguardando aprovação
Fora do escopo até o dono aprovar uma a uma:
- **V3-15 Saúde do PC antes de formatar:** BitLocker ligado (e se a chave de recuperação está salva), espaço, licença do Windows (digital ou chave), backup feito e conferido.
- **V3-16 Exportar a chave de recuperação do BitLocker** para o pendrive ou o disco de backup.
- **V3-17 Dispensar requisitos do Windows 11** (TPM, Secure Boot, RAM) em PCs não suportados, como o Rufus faz, com aviso de que a Microsoft não suporta.

## 15. Hipóteses novas (H36 a H48)

| # | Hipótese | Se falhar | Marco |
|---|---|---|---|
| H36 | O `pycdlib` gera ISO (UDF + El Torito BIOS e UEFI) que o instalador aceita, com `install.wim` acima de 4 GB | Só `oscdimg` (ADK instalado pela pessoa) | M23 |
| H37 | O `Fido -GetUrl` funciona para 11, 10 e 8.1, e os links aceitam `Range` (retomar) | Download sem retomada; refaz do zero | M21 |
| H38 | A Microsoft publica um SHA-256 conferível para cada ISO baixada | Conferência só estrutural (a ISO abre e tem `install.*`) | M21 |
| H39 | As versões atuais do Rufus deixam as opções num arquivo legível no pendrive | O WinKit só diz "pendrive do Rufus" e pergunta as opções à pessoa | M20 |
| H40 | O instalador usa `install.swm` num pendrive FAT32 gravado pelo WinKit (UEFI e BIOS) | NTFS + instrução de usar o Rufus | M24 |
| H41 | O Windows 7 x64 dá boot em UEFI com o `bootmgfw.efi` tirado da imagem | Windows 7 só em BIOS/CSM | M25 |
| H42 | O PowerShell 2.0 do Windows 7 SP1 roda os scripts do agente legado | Agente legado em `.cmd` com menos funções | M25 |
| H43 | O DISM do Windows 11 faz manutenção offline de imagens do 7 e do 8.1 | ISO personalizada só para 10 e 11 | M25 |
| H44 | `MSFT_PhysicalDisk` dá tipo e barramento confiáveis para discos internos | Mostrar só "disco interno" e medir a velocidade | M22 |
| H45 | Os atributos de janela do Windows 11 (barra escura, cor do contorno) funcionam em janelas Qt | Barra no tema do sistema; só a barra de rolagem muda | M19 |
| H46 | Ventoy e Rufus baixados pelo WinKit abrem sem bloqueio além do aviso do SmartScreen | Instrução de abrir à mão | M20 |
| H47 | O Agente atual (Python 3.12) roda no Windows 8.1 | 8.1 usa o agente legado (já previsto) | M25 |
| H48 | Mídias antigas (7, 8.1, 10 antigo) ainda dão boot com Secure Boot ligado depois da troca de certificados da Microsoft (2026) | Aviso para desligar o Secure Boot na instalação | M24/M25 |

## 16. Riscos novos
- **Gravar o disco errado.** Mitigação: D-045, R-60, testes de proteção, conferência imediatamente antes.
- **Espaço e tempo** da ISO personalizada (dezenas de GB, até uma hora). Mitigação: estimativa antes, retomada, limpeza garantida (R-62).
- **A Microsoft muda o site de download.** Mitigação: Fido baixado na hora (mantido pelo autor do Rufus); "usar uma ISO que já tenho".
- **Ventoy e Rufus mudam formato.** Mitigação: detecção tolerante; na dúvida, perguntar.
- **Windows 7 e 8.1 inseguros.** Mitigação: avisos obrigatórios; nada de Windows Update automático neles.
- **Certificados do Secure Boot (2026).** Mitigação: nunca trocar os arquivos de boot da ISO original; aviso (H48).
- **Antivírus** pode estranhar o WinKit montando imagens e gravando discos. Mitigação: só ferramentas do próprio Windows, caminhos absolutos (R-12).

## 17. Dívidas já previstas
- Versões antigas do Windows 10 não baixáveis (a Microsoft só oferece a 22H2).
- Pendrive acima de 512 GB só pelo Ventoy ou Rufus (D-045).
- Pendrive em NTFS (para arquivos acima de 4 GB sem dividir) fora da v3.
- Agente legado com menos funções que o Agente atual (§12.3).
- Testes de Ventoy e Rufus fora do Hyper-V (sem USB na VM).

## 18. Estratégia de testes da v3
- **Fakes** para tudo de `platform` novo (download, DISM, gravação, disco), gravando cada operação, como na v2 (R-40).
- **Download:** servidor HTTP local nos testes (biblioteca padrão), com queda no meio, retomada e hash errado.
- **ISO:** no Linux, o `pycdlib` gera uma ISO pequena com os arquivos de boot de uma fixture, e o teste a lê de volta (UDF, El Torito, duas entradas de boot).
- **Gravação:** fake de disco; testes de proteção da R-60.
- **Backup:** pastas temporárias com arquivos grandes esparsos, nomes inválidos, arquivo aberto, queda no meio e retomada; conferência por hash.
- **Modo em etapas:** testes de interface (offscreen) para cada caminho e cada Windows alvo, conferindo a ordem e as etapas esmaecidas.
- **R-59:** serviços falsos lentos; tempo de abertura das páginas.
- **Agente legado:** snapshot dos scripts gerados; execução real no CI do Windows com PowerShell 2.0 quando disponível (senão, na VM).
- **Testes de proteção novos:** R-60 (disco errado), R-64 (ISO original intacta), D-051 (o backup nunca apaga nada).

## 19. Ordem, dependências e versões

| Marco | Conteúdo | Depende de | Versão |
|---|---|---|---|
| M19 | V3-01, 02, 03, 04 | — | 0.10.0 |
| M20 | V3-05, 06, 07 | M19 | 0.11.0 |
| M21 | V3-08 | M20 | 0.12.0 |
| M22 | V3-09, 10 | M19 (central de tarefas) | 0.13.0 |
| M23 | V3-11, 12 | M21 (ISO), validação de H36 | 0.14.0 |
| M24 | V3-13 | M23 (divisão do `install.wim`) | 0.15.0 |
| M25 | V3-14 | M23, M24 | 0.16.0 |
| M26 | fechamento | todos | 0.17.0 |

O M19 vem primeiro porque corrige o que o dono já sente (lentidão, nitidez, janela) e porque o V3-04 (testes na VM) permite validar os marcos seguintes enquanto são feitos. O M22 (backup) pode andar em paralelo ao M21.

## 20. O que depende do dono do projeto
1. **Aprovar este plano**, incluindo §1.2 (backup nos dois lugares, sem espelho) e cada sugestão do §14.
2. **Ligar o PC à sessão** (V3-04): Claude para desktop, pasta compartilhada pelo Remote Control.
3. **Hyper-V ligado** no Windows 11 Pro (Recursos do Windows → Hyper-V), ou VirtualBox.
4. **Um pendrive de testes** que possa ser apagado (M24) e, se possível, um PC velho ou VM com BIOS para o Windows 7.
5. **ISOs do Windows 7 SP1 e 8.1** se quiser testar o M25 (o 8.1 o WinKit baixa; o 7 não).
6. Executar ou acompanhar os roteiros `docs/validacao/M19.md` a `M25.md`.
