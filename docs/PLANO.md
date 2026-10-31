# WinKit — Plano do Produto e de Implementação

> Documento vivo. Descreve **o que** o produto é, **como** foi desenhado e **em que ordem** será construído.
> Regras de código ficam em `ARQUITETURA.md`; o andamento real fica em `STATUS.md`.
>
> Nome do produto: **WinKit**. Repositório: `WinKit` (antes `Iso-Modify-Win11`; o GitHub redireciona os links antigos).
> Data da primeira versão deste plano: 2026-10-31.

## Sumário

0. [Como ler este documento](#0-como-ler-este-documento)
1. [Visão do produto](#1-visão-do-produto)
2. [Decisões fechadas](#2-decisões-fechadas)
3. [Escopo: v1, depois e fora](#3-escopo-v1-depois-e-fora)
4. [Visão geral da arquitetura](#4-visão-geral-da-arquitetura)
5. [Layout no pendrive](#5-layout-no-pendrive)
6. [A receita](#6-a-receita)
7. [Coletor](#7-coletor)
8. [Construtor](#8-construtor)
9. [O `autounattend.xml`](#9-o-autounattendxml)
10. [Agente: inicialização (bootstrap)](#10-agente-inicialização-bootstrap)
11. [Agente: fases, planejador e máquina de estados](#11-agente-fases-planejador-e-máquina-de-estados)
12. [Agente: modos de execução e interface](#12-agente-modos-de-execução-e-interface)
13. [Motores compartilhados](#13-motores-compartilhados)
14. [Bloatware e ajustes do sistema](#14-bloatware-e-ajustes-do-sistema)
15. [Dados versionados (catálogos)](#15-dados-versionados-catálogos)
16. [Segurança e salvaguardas](#16-segurança-e-salvaguardas)
17. [Stack e ferramentas](#17-stack-e-ferramentas)
18. [Estrutura do repositório](#18-estrutura-do-repositório)
19. [Estratégia de testes](#19-estratégia-de-testes)
20. [Marcos de implementação](#20-marcos-de-implementação)
21. [Hipóteses a validar](#21-hipóteses-a-validar)
22. [Riscos](#22-riscos)
23. [Documentos vivos](#23-documentos-vivos)
24. [Rastreabilidade: função → marco](#24-rastreabilidade-função--marco)
25. [Glossário](#25-glossário)

---

## 0. Como ler este documento

- **Fase 1 / Fase 2** referem-se às etapas do Agente dentro do Windows novo (seção 11), não a marcos de desenvolvimento.
- **Marcos** (M0, M1...) são as etapas de desenvolvimento (seção 20).
- **H1, H2...** são hipóteses técnicas ainda não comprovadas no hardware real (seção 21). Nenhuma parte do desenho que dependa de uma hipótese é considerada pronta antes de a hipótese ser validada.
- **D-001...** são decisões registradas em `ARQUITETURA.md`.
- Números entre parênteses, como **(item 28)**, referem-se ao cardápio de funções discutido no início do projeto (tabela da seção 3).

---

## 1. Visão do produto

### 1.1 Problema

Reinstalar o Windows é demorado por causa de tudo que vem depois da instalação: caçar drivers, baixar e instalar aplicativos um a um, remover aplicativos inúteis, desligar telemetria, refazer preferências visuais e reconfigurar cada aplicativo do zero.

O usuário usa **Ventoy** num pendrive de 100 GB com várias ISOs, e por isso não quer o Rufus nem uma ISO por pendrive.

### 1.2 Solução

Um aplicativo para Windows que:

1. **No PC atual**, lê o que você tem (aplicativos instalados, drivers, pastas de configuração), deixa você escolher o que quer levar e grava tudo numa pasta `WinKit/` do pendrive Ventoy, junto com uma *receita*.
2. **No pendrive**, configura o plugin `auto_install` do Ventoy para que qualquer ISO do Windows instale de forma automatizada, **sem a ISO ser modificada**.
3. **No Windows novo**, um Agente lê a receita no pendrive e faz o resto: drivers, remoção de bloatware, ajustes, restauração das pastas de configuração e instalação dos aplicativos, de forma silenciosa, com contagem regressiva ou interativa.

### 1.3 Princípios

| # | Princípio | Consequência prática |
|---|---|---|
| P1 | **A ISO é intocável** | O produto nunca regrava ISO. Trocar a ISO por uma versão mais nova não exige refazer nada. |
| P2 | **O pendrive é a fonte da verdade** | Receita, instaladores, drivers, backups, logs: tudo em `WinKit/`. Uma única pasta serve a todas as ISOs. |
| P3 | **Nada destrutivo por padrão** | Nunca particiona disco, nunca sobrescreve arquivo do usuário sem escolha explícita, faz cópia de segurança antes de editar `ventoy.json`. |
| P4 | **Erros não travam a instalação** | Um item que falha é registrado e o Agente segue para o próximo. |
| P5 | **Tudo é retomável** | Reinicializações, queda de energia ou pendrive removido não fazem o Agente repetir ou perder trabalho. |
| P6 | **Dados não são código** | Listas de bloatware, ajustes, switches de instaladores e pastas de configuração conhecidas ficam em arquivos de dados versionados, não no código. |
| P7 | **Explicável** | Tudo que o Agente fez fica em log legível, gravado de volta no pendrive, e num resumo no Windows novo. |

### 1.4 Quem usa

Um único usuário técnico, em uso pessoal, que prepara o pendrive no próprio PC e instala o Windows nas próprias máquinas. O produto **não** é uma ferramenta corporativa de implantação em massa.

---

## 2. Decisões fechadas

Decisões tomadas com o usuário durante o desenho. Detalhes e justificativa no Registro de Decisões de `ARQUITETURA.md`.

| Tema | Decisão | Decisão nº |
|---|---|---|
| Onde fica o conteúdo pesado | **Modo B**: tudo no pendrive (`WinKit/`) | D-001 |
| A ISO | **Nunca é modificada**; o `autounattend.xml` é injetado pelo plugin `auto_install` do Ventoy | D-002 |
| Linguagem | **Python 3.12 + PySide6** | D-003 |
| Ordem de construção | **Motor primeiro (linha de comando), interface gráfica depois** | D-004 |
| Formato do backup no pendrive | **Pasta crua** (não ZIP), editável à mão | D-005 |
| Captura de arquivos em uso | **Cópia de sombra (VSS)** | D-006 |
| Conflito na restauração | **Mesclar sem sobrescrever** por padrão | D-007 |
| Início do Agente | Opção na receita: **silencioso, contagem regressiva ou interativo** | D-008 |
| Fases | **Mescladas**: tudo o que for possível antes do login (Fase 1), o resto depois do login em segundo plano (Fase 2) | D-009 |
| Teste em VM | **Fora do produto** | D-010 |
| Atualizações do Windows | **Opção leve**: ligar ou não o Windows Update; sem embutir atualizações na imagem | D-011 |

---

## 3. Escopo: v1, depois e fora

### 3.1 Cardápio de funções e destino

| Nº | Função | Destino | Observação |
|---|---|---|---|
| 1 | Ler ISO e detectar edições/versão/idioma/arquitetura | **v1** | Somente leitura. Nunca converte nem altera. |
| 2 | Gerar `autounattend.xml` | **v1** | Conta local, idioma, teclado, fuso, bypass, edição. |
| 3 | Instalar apps silenciosamente | **v1** | Pelo Agente, a partir do pendrive. |
| 4 | Remontar ISO bootável | **Fora** | Contraria P1. |
| 5 | Injetar drivers no `install.wim`/`boot.wim` | **Fora** | Contraria P1. Se um SSD não for visto pelo instalador, ver H10. |
| 6 | Drivers no pendrive + `pnputil` | **v1** | |
| 7 | Exportar drivers do PC atual, filtrando genéricos | **v1** | |
| 8 | Listar apps instalados no PC atual e escolher | **v1** | |
| 9 | winget | **v1** | Híbrido: baixar antes para o pendrive ou instalar online. |
| 10 | Ordem de instalação e "depois do primeiro login" | **v1** | |
| 11 | Escolher bloatware a remover | **v1** | Lista em níveis de risco. |
| 12 | Captura de backup de pastas | **v1** | |
| 13 | Restauração no perfil Default (antes do login) | **v1** | |
| 14 | Restauração no primeiro logon | **v1** | |
| 15 | Backup de chaves de registro `HKCU` | **v2** (curado) | Só valores curados de um catálogo (V2-06, D-037), nunca o `HKCU` bruto. |
| 16 | Aviso do que não sobrevive (tokens, senhas) | **v1** | |
| 17 | Receita salva em JSON | **v1** | Espinha do projeto. |
| 18 | Teste da ISO em VM | **Fora** | Decisão do usuário. |
| 19 | Modo Ventoy nativo | **v1** | Virou o único modo. |
| 20 | Windows 10 | Depois | A estrutura já nasce preparada. |
| 21 | Atualizações (leve) | **v1** | A versão "pesada" (slipstream) está fora. |
| 22 | Motor primeiro, interface depois | **v1** | Decisão de processo. |
| 23 | Perfis múltiplos | Depois | O layout do pendrive já nasce com `Perfis/`. |
| 24 | Detecção automática do pendrive Ventoy | **v1** | |
| 25 | Estimativa de espaço | **v1** | |
| 26 | Log de volta no pendrive | **v1** | |
| 27 | Atualizar só o que mudou no pendrive | **v1** | |
| 28 | Sugestão de pastas de configuração | **v1** | |
| 29 | Fixar na barra de tarefas | **v2** | V2-04: layout no perfil Default antes do primeiro login (H27, H28). |
| 30 | Restaurar arquivos soltos | **v1** | |
| 31 | Ajustes de privacidade | **v1** | |
| 32 | Ajustes visuais | **v1** | |
| 33 | Nome do computador | **v1** | |
| 34 | Plano de energia | **v1** | |
| 35 | Escolher backups na janela do primeiro login | **v1** | Via marcação "decidir na hora". |
| 36 | Tela final de resumo | **v1** | |
| 37 | Bloquear reinstalação de apps removidos | **v1** | |

**Funções da v2** (detalhes em [`PLANO_V2.md`](PLANO_V2.md) §1; todas implementadas, validação na VM pendente):

| Código | Função | Marco |
|---|---|---|
| V2-00 | Interface em inglês e espanhol | M11 |
| V2-03, V2-10 | Aplicar neste PC, com prévia e ponto de restauração | M12 |
| V2-01 | Pendrive comum (Rufus ou Ferramenta de Criação de Mídia) | M13 |
| V2-02, 08, 09, 16, 17, 18, 22 | Wi-Fi, recursos do Windows, drivers que faltam, DNS e `hosts`, unidades de rede, manutenção, variáveis de ambiente | M14 |
| V2-04, 05, 06, 07, 12, 15 | Iniciar e barra, apps padrão, aparência, fontes, navegadores, perfis rápidos | M15 |
| V2-11, 13, 14 | Contas extras, jogos sem baixar de novo, pastas do usuário em outro disco | M16 |
| V2-19, 20, 21, 23 | Relatório antes/depois, assistente "o que levar", atualizar instaladores, receitas compartilháveis | M17 |

### 3.2 Fora do escopo, explicitamente

- Modificar, converter ou regravar qualquer ISO, WIM ou ESD.
- Particionar ou formatar discos, ou escolher o disco de destino automaticamente.
- Restaurar contas, senhas, cookies, tokens de sessão ou qualquer dado protegido por DPAPI (não funcionaria; ver 7.4.6).
- Ativação do Windows ou contorno de licenciamento.
- Remoção do Microsoft Edge (só existe oficialmente na União Europeia).
- Implantação corporativa (domínio, Intune, várias máquinas em paralelo).

---

## 4. Visão geral da arquitetura

### 4.1 Os três componentes

```
┌───────────────────────── PC ATUAL (Windows, administrador) ─────────────────────────┐
│                                                                                     │
│   WinKit Studio  (CLI no início, GUI PySide6 a partir do M10)                       │
│   ┌───────────────┐        ┌──────────────────┐                                     │
│   │   COLETOR     │ ─────► │   CONSTRUTOR     │                                     │
│   │ apps, drivers,│ receita│ ventoy.json,     │                                     │
│   │ backups (VSS) │        │ autounattend,    │                                     │
│   └───────────────┘        │ payload WinKit/  │                                     │
│                            └────────┬─────────┘                                     │
└─────────────────────────────────────┼───────────────────────────────────────────────┘
                                      │ grava
                                      ▼
┌────────────────────────── PENDRIVE VENTOY (exFAT) ──────────────────────────────────┐
│  ISOs originais intactas · ventoy/ventoy.json · ventoy/script/*.xml · WinKit/       │
└─────────────────────────────────────┬───────────────────────────────────────────────┘
                                      │ boot pelo Ventoy, auto_install injeta o XML
                                      ▼
┌──────────────────────────────── WINDOWS NOVO ───────────────────────────────────────┐
│  Instalador do Windows ──► specialize: bootstrap.ps1 (copia o Agente do pendrive)   │
│                        ──► SetupComplete.cmd: AGENTE Fase 1 (SYSTEM, sem tela)       │
│                        ──► primeiro login: AGENTE Fase 2 (tarefa agendada, usuário)  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

| Componente | Onde roda | Privilégio | Interface |
|---|---|---|---|
| **Coletor** | PC atual | Administrador (VSS e drivers exigem) | CLI → GUI no M10 |
| **Construtor** | PC atual | Administrador | CLI → GUI no M10 |
| **Agente** | Windows novo | Fase 1: SYSTEM. Fase 2: usuário administrador, elevado | Fase 1: nenhuma. Fase 2: janela, bandeja ou nada, conforme o modo |

Coletor e Construtor são o mesmo executável (**WinKit Studio**). O Agente é um executável separado (**winkit-agent**), copiado para o pendrive pelo Construtor.

### 4.2 Camadas do código

```
        ┌──────────────────────────────────────────────┐
        │  ui/        (PySide6: Studio e janela do Agente) │
        ├──────────────────────────────────────────────┤
        │  cli/       (linha de comando)                   │
        ├──────────────────────────────────────────────┤
        │  collector/   builder/   agent/   (funções)      │
        ├───────────────────────┬──────────────────────┤
        │  core/  (puro, testável │  platform/ (Windows:   │
        │  no Linux)              │  registro, VSS, ...)   │
        └───────────────────────┴──────────────────────┘
                     src/winkit/data/  (catálogos YAML versionados)
```

Regra de dependência: uma camada só importa as que estão **abaixo** dela. `core` não importa nada do projeto além de si mesmo. `platform` só importa `core`. Detalhes em `ARQUITETURA.md`.

### 4.3 Fluxo de ponta a ponta

1. Usuário roda `winkit coletar` no PC atual → inventário de apps, drivers e pastas candidatas.
2. Usuário marca o que quer (editando a receita no M1–M9; pela GUI a partir do M10).
3. `winkit construir` → detecta o pendrive Ventoy, estima espaço, copia instaladores, drivers e backups, grava a receita, gera os XMLs, mescla o `ventoy.json`, copia o Agente.
4. Usuário dá boot pelo Ventoy e escolhe a ISO. O Ventoy pergunta qual modelo de instalação automática usar (ou escolhe sozinho, conforme `autosel`).
5. O Windows instala. Usuário escolhe o disco manualmente (P3).
6. Na etapa *specialize*, `bootstrap.ps1` acha o pendrive, copia o Agente para `C:\ProgramData\WinKit\`, cria o `SetupComplete.cmd` e registra a tarefa da Fase 2.
7. `SetupComplete.cmd` roda a **Fase 1** como SYSTEM, antes da tela de login.
8. Login automático na conta local. A tarefa agendada roda a **Fase 2**.
9. No fim: notificação, resumo, log gravado no pendrive, limpeza de senha e arquivos temporários.

---

## 5. Layout no pendrive

```
<Partição de dados do Ventoy>\
├── Windows11_25H2.iso                       ← ISOs originais, nunca modificadas
├── Windows10_22H2.iso
├── ventoy\
│   ├── ventoy.json                          ← mesclado pelo Construtor (nunca substituído)
│   ├── ventoy.json.winkit-bak               ← cópia antes da primeira alteração
│   └── script\
│       ├── winkit-padrao-pt-BR-amd64.xml    ← um XML por (perfil, idioma da ISO, arquitetura)
│       └── winkit-padrao-en-US-amd64.xml
└── WinKit\
    ├── winkit.marker                        ← JSON: id do pendrive, versão do WinKit
    ├── manifesto.json                       ← tamanho, data e SHA-256 de Agent/Apps/Drivers
    ├── Agent\
    │   ├── bootstrap.ps1                    ← chamado pelo XML na etapa specialize
    │   ├── VERSION
    │   └── winkit-agent\                    ← PyInstaller "onedir"
    │       ├── winkit-agent.exe
    │       └── _internal\...
    ├── Apps\                                ← compartilhado entre perfis
    │   └── <app-id>\<versão>\
    │       ├── <instalador>.exe|.msi|.msix
    │       └── winget-manifest.yaml         ← quando veio de "winget download"
    ├── Drivers\                             ← compartilhado entre perfis
    │   └── <classe>\<provedor>_<inf>_<versão>\*.inf, *.sys, *.cat ...
    ├── Perfis\
    │   └── padrao\                          ← v1 usa só "padrao"; item 23 depois
    │       ├── receita.json
    │       └── Backups\
    │           └── <backup-id>\
    │               ├── item.json            ← molde de caminho, filtros, política de conflito
    │               └── dados\...            ← PASTA CRUA, editável à mão (D-005)
    └── Logs\
        └── <nome-do-pc>_<AAAA-MM-DD_HH-MM>\
            ├── agente.log                   ← legível
            ├── eventos.jsonl                ← estruturado
            ├── estado.json                  ← cópia do estado final
            └── resumo.json
```

### 5.1 Regras do layout

- O Construtor **só escreve** dentro de `WinKit\` e em arquivos `ventoy\script\winkit-*.xml`, além de **mesclar** `ventoy\ventoy.json`. Nunca toca em mais nada na partição.
- `winkit.marker` contém um `pendrive_id` (UUID gerado na primeira construção). O XML carrega esse id, e o Agente só aceita um pendrive cujo marcador tenha o mesmo id. Isso evita confusão se houver dois pendrives WinKit plugados.
- `Apps\` e `Drivers\` têm conteúdo verificado por hash (`manifesto.json`) antes de executar. `Backups\` **não** é verificado por hash, porque o usuário pode editá-lo à mão (D-005).
- Nomes de pasta usam só `[a-z0-9-_.]` para evitar problemas de codificação entre exFAT, FAT32 e WinPE.

---

## 6. A receita

A receita é um único arquivo JSON (`Perfis\<perfil>\receita.json`) que descreve **tudo** o que o Agente deve fazer. Ela é:

- **Validada por esquema** (Pydantic v2) no Studio e no Agente.
- **Versionada** (`schema_version`, inteiro). Mudança incompatível → nova versão + função de migração em `core/recipe/migrations.py`.
- **A única entrada do Agente.** O Agente não toma decisões que não estejam na receita ou no planejador (seção 11.2).

### 6.1 Estrutura

> **Fonte autoritativa:** `src/winkit/core/recipe/models.py`. O exemplo abaixo é ilustrativo; campos acrescentados na implementação (M1): `windows.computer_name_decide_at_runtime`, `windows.prevent_device_encryption` (D-020), `apps[].requires_non_elevated`, `apps[].winget_source`, `apps[].installer.timeout_minutes`, `apps[].installer.sha256`, `power.scheme = "unchanged"` (padrão: não mexer no plano de energia). O modo de execução padrão é `countdown`.

```jsonc
{
  "schema_version": 1,
  "meta": {
    "profile_id": "padrao",
    "pendrive_id": "6f1c...-uuid",
    "created_at": "2026-11-02T14:03:00-03:00",
    "updated_at": "2026-11-02T14:03:00-03:00",
    "winkit_version": "0.1.0",
    "source_pc": "DESKTOP-ANTIGO"
  },

  "execution": {
    "mode": "silent",                 // "silent" | "countdown" | "interactive"   (D-008)
    "countdown_seconds": 30,          // usado só em "countdown"
    "show_tray_icon": true,           // no modo silencioso: ícone de progresso na bandeja
    "notify_on_finish": true,
    "desktop_summary_shortcut": true, // item 36
    "reboot_policy": "ask"            // Fase 2: "ask" | "auto_if_idle" | "never"
  },

  "windows": {
    "target_os": [11],                // [10, 11] quando o item 20 for feito
    "edition": "pro",                 // seleciona a chave genérica (seção 9.4)
    "architecture": "amd64",          // "amd64" | "arm64"
    "ui_language": "auto",            // "auto" = idioma da ISO (seção 9.5)
    "input_locale": "0416:00010416",  // pt-BR ABNT2
    "user_locale": "pt-BR",
    "system_locale": "pt-BR",
    "time_zone": "E. South America Standard Time",
    "computer_name": "PC-SAMUEL",     // item 33; null = Windows gera um nome
    "prevent_device_encryption": true, // PADRÃO true (D-020): Windows não criptografa sozinho,
                                       // nem depois de entrar com conta Microsoft
    "account": {
      "username": "Samuel",
      "display_name": "Samuel",
      "password_mode": "empty",       // "empty" | "stored" (ver 16.3)
      "password": null,               // só com "stored"
      "auto_logon": true
    }
  },

  "updates": {                        // item 21 (D-011)
    "during_setup": false,            // Dynamic Update do instalador
    "windows_update_after_install": true,
    "include_drivers_from_windows_update": false,
    "block_wu_driver_replacement": true
  },

  "drivers": [
    {
      "id": "net-realtek-rtl8125",
      "selected": true,
      "path": "Drivers/Net/realtek_oem12_10.68",
      "class": "Net",
      "provider": "Realtek",
      "version": "10.68.815.2024",
      "original_inf": "rt25cx21x64.inf",
      "priority": 0                   // menor = instala antes (rede e armazenamento = 0)
    }
  ],

  "apps": [
    {
      "id": "7zip",
      "name": "7-Zip",
      "selected": true,
      "source": "offline",            // "offline" | "winget_online" | "portable"
      "scope": "machine",             // "machine" | "user"
      "installer": {
        "path": "Apps/7zip/24.09/7z2409-x64.exe",
        "type": "nsis",               // detectado (seção 13.3) ou do catálogo
        "args": ["/S"],
        "success_codes": [0],
        "reboot_codes": [3010, 1641]
      },
      "winget_id": "7zip.7zip",
      "after_install": {
        "kill_processes": [],
        "disable_autostart": [],
        "shortcuts": []
      },
      "order": 10,
      "depends_on": [],
      "restore_backups_after_install": [],  // backups que só podem entrar depois do instalador
      "decide_at_runtime": false            // D-009: vai para a janela da Fase 2
    }
  ],

  "backups": [
    {
      "id": "discord-settings",
      "name": "Discord — configurações",
      "selected": true,
      "kind": "folder",               // "folder" | "file" (item 30)
      "template": "{APPDATA}\\discord",
      "data_path": "Perfis/padrao/Backups/discord-settings",
      "exclude": ["Cache", "Code Cache", "GPUCache", "logs", "Local Storage"],
      "on_conflict": "merge",         // "merge" | "overwrite" | "skip"   (D-007)
      "related_app": "discord",
      "decide_at_runtime": false,     // item 35
      "warnings": ["dpapi:Local Storage"]   // item 16; preenchido pelo Coletor
    }
  ],

  "bloatware": {
    "remove": ["Clipchamp.Clipchamp", "Microsoft.BingNews"],
    "block_reinstall": true,          // item 37
    "disable_consumer_content": true
  },

  "tweaks": [
    { "id": "privacy.advertising_id", "enabled": true, "decide_at_runtime": false },
    { "id": "visual.dark_theme",      "enabled": true, "decide_at_runtime": true  }
  ],

  "power": {                          // item 34
    "scheme": "high_performance",     // "balanced" | "high_performance" | "ultimate"
    "hibernate": false,
    "fast_startup": false
  }
}
```

Itens com `selected = false` ficam na receita (para o Studio lembrar do inventário), mas o planejador os ignora.

### 6.2 Regras de validação

| Regra | Onde é checada | Mensagem ao usuário |
|---|---|---|
| `mode = silent` exige que nenhum campo obrigatório esteja vazio e ignora `decide_at_runtime` | Studio, ao construir | "No modo silencioso, ninguém vai responder perguntas. Preencha: …" |
| `computer_name`: 1–15 caracteres, só letras, números e `-`, não pode ser só números | Studio | "Nome de computador inválido: …" |
| `username`: não pode ser nome reservado (`Administrator`, `Guest`, `DefaultAccount`, `Administrador`, `Convidado`...) nem conter `\ / [ ] : ; \| = , + * ? < > "` | Studio | |
| Todo `path` referenciado existe no pendrive | Studio (construção) e Agente (antes de executar) | |
| `depends_on` não forma ciclo | Studio | |
| Um `backup` com `related_app` cuja instalação apaga a pasta precisa estar em `restore_backups_after_install` | Studio, com base no catálogo | Aviso, não erro |
| `password_mode = stored` gera aviso de segurança | Studio | Ver 16.3 |
| `architecture` da receita compatível com a ISO | Construtor | Aviso por ISO |

### 6.3 Moldes de caminho

O Coletor **nunca** grava caminhos literais da máquina antiga. Ele traduz para um molde com variáveis, resolvidas no Windows novo:

| Variável | Resolve para (Windows novo) | Pasta conhecida (Known Folder) |
|---|---|---|
| `{USERPROFILE}` | `C:\Users\<usuário>` | `FOLDERID_Profile` |
| `{APPDATA}` | `...\AppData\Roaming` | `FOLDERID_RoamingAppData` |
| `{LOCALAPPDATA}` | `...\AppData\Local` | `FOLDERID_LocalAppData` |
| `{LOCALLOW}` | `...\AppData\LocalLow` | `FOLDERID_LocalAppDataLow` |
| `{DOCUMENTS}` | Documentos (mesmo se redirecionado pelo OneDrive na máquina antiga) | `FOLDERID_Documents` |
| `{PICTURES}` `{VIDEOS}` `{MUSIC}` `{DESKTOP}` `{DOWNLOADS}` | idem | respectivos |
| `{SAVEDGAMES}` | Jogos Salvos | `FOLDERID_SavedGames` |
| `{PROGRAMDATA}` | `C:\ProgramData` | `FOLDERID_ProgramData` |
| `{PROGRAMFILES}` / `{PROGRAMFILESX86}` | | `FOLDERID_ProgramFiles` / `...X86` |
| `{PUBLIC}` | `C:\Users\Public` | `FOLDERID_Public` |
| `{ABS:D:\Jogos\X}` | o mesmo caminho absoluto | — |

Algoritmo de tradução (`core/paths/templates.py`):

1. Normaliza o caminho (resolve `..`, maiúsculas/minúsculas, barra final).
2. Resolve todas as Known Folders **da máquina antiga** (via `platform`).
3. Escolhe a correspondência de **prefixo mais longo** (ex.: `{LOCALLOW}` ganha de `{USERPROFILE}`).
4. Se nada corresponder → `{ABS:...}` com aviso "este caminho depende do disco `D:` existir no PC novo".
5. Caminhos dentro de `C:\Windows` são **recusados** (não faz sentido restaurar ali).

Resolução no Windows novo (`agent`):

- Na **Fase 1**, variáveis de perfil (`{APPDATA}`, `{DOCUMENTS}`...) resolvem para o **perfil Default** (`C:\Users\Default\...`), que o Windows clona ao criar a conta do usuário. Ver H4.
- Na **Fase 2**, resolvem para o perfil do usuário logado.
- `{ABS:...}` só é resolvido na Fase 2, e se a unidade não existir o item é marcado como `skipped` com motivo legível no resumo.

---

## 7. Coletor

Roda no PC atual. Comando: `winkit coletar [apps|drivers|backups|tudo]`. Produz/atualiza a receita com tudo **desmarcado**, exceto as sugestões marcadas como `recommended` no catálogo.

### 7.1 Inventário de aplicativos (item 8)

#### 7.1.1 Fontes

| Fonte | Como ler | O que dá |
|---|---|---|
| Registro de desinstalação 64-bit | `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*` | Apps Win32 de máquina |
| Registro de desinstalação 32-bit | `HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*` | Apps 32-bit |
| Registro de desinstalação do usuário | `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\*` | Apps por usuário (Discord, Spotify, VS Code user...) |
| Pacotes MSIX/Loja | PowerShell `Get-AppxPackage` → JSON | Apps da Loja |
| winget | `winget export -o <tmp>.json --include-versions --accept-source-agreements` | Correspondência nome → ID do winget, só para pacotes encontrados nas fontes |

Leitura do registro: módulo `winreg` (só em `platform`). Nunca via `reg query` (texto localizado).

#### 7.1.2 Filtros (remover ruído)

Descartar entradas com:
- `SystemComponent = 1`
- `ParentKeyName` presente (atualizações e subcomponentes)
- `ReleaseType` em `Update`, `Hotfix`, `Security Update`
- Sem `DisplayName`
- Pacotes de framework MSIX (`IsFramework = true`) e pacotes do sistema (`SignatureKind = System`)
- Redistribuíveis (Visual C++, .NET Runtime, DirectX) — **listados à parte** como "dependências", porque podem ser necessários mas normalmente vêm junto com os apps

#### 7.1.3 Classificação de cada app

Para cada app, o Coletor decide uma **fonte sugerida** e um **escopo**:

```
tem winget_id?
├─ sim, fonte winget comunitária ("winget")
│    └─ sugerido: source=offline via "winget download" (ver 7.1.4)
├─ sim, fonte "msstore"
│    └─ sugerido: source=winget_online (a Loja não permite download offline sem conta corporativa)
└─ não
     ├─ catálogo conhece o app? → usa as regras do catálogo
     └─ não → source=offline, o usuário aponta o instalador (Studio pede o arquivo)

escopo:
  entrada veio de HKCU, ou InstallLocation dentro de %LOCALAPPDATA% → user
  caso contrário → machine
```

Apps portáteis não aparecem no registro. O usuário adiciona com "Adicionar app portátil": aponta a pasta, e o Coletor cria um `backup` do tipo pasta + um atalho (`source=portable`).

#### 7.1.4 `winget download`

Para apps com ID no winget e fonte comunitária, o Coletor oferece **baixar agora** para `WinKit\Apps\<id>\<versão>\` com `winget download --id <id> --download-directory <dir> --accept-package-agreements --accept-source-agreements`. Isso traz o instalador **e** o manifesto YAML, que contém o tipo de instalador e os switches silenciosos (`InstallerSwitches.Silent`). Requer winget ≥ 1.8.

Vantagens: instala **offline**, pode ir para a **Fase 1** (antes do login) quando o escopo for `machine`, e versão fica fixa e conhecida.

#### 7.1.5 Saída

`inventario.json` (cache local do Studio, não vai para o pendrive) + entradas `apps[]` na receita com `selected=false`.

### 7.2 Drivers (item 7)

1. Listar: `Get-WindowsDriver -Online` (sem `-All`, ou seja, só drivers de terceiros) → JSON com `Driver` (oemNN.inf), `OriginalFileName`, `ClassName`, `ProviderName`, `Version`, `Date`, `BootCritical`.
2. Agrupar por classe. Pré-selecionar como **recomendado**: `Net`, `SCSIAdapter`, `HDC`, `System` (chipset), `MEDIA` (áudio), `Bluetooth`. Deixar desmarcado: `Printer`, `SoftwareComponent`, `Extension` (geralmente vêm com o software do fabricante e não fazem sentido sozinhos).
3. Exportar os selecionados: `pnputil /export-driver oemNN.inf <destino>` um por um. Verifica apenas o código de saída e se a pasta de destino contém um `.inf` (nunca lê o texto do `pnputil`, que é localizado).
4. Destino: `WinKit\Drivers\<classe>\<provedor>_<oemNN>_<versão>\`.
5. Prioridade: rede e armazenamento = 0, chipset = 1, resto = 5. Rede primeiro porque a Fase 2 depende de internet para o winget.

Aviso exibido: driver de vídeo exportado assim instala o driver, mas **não** o painel do fabricante (NVIDIA App, AMD Adrenalin). Para ter o painel, adicione o instalador do fabricante como app.

### 7.3 Sugestão de pastas de configuração (item 28)

Para cada app marcado, o Coletor consulta `src/winkit/data/app_catalog.yaml` (seção 15) e verifica, **na máquina atual**, quais pastas conhecidas existem e quanto ocupam (já descontando os filtros de exclusão). Mostra como sugestões:

```
Discord
  [x] {APPDATA}\discord\settings.json        2 KB
  [ ] {APPDATA}\discord\Local Storage        48 MB   ⚠ contém token de login (não funcionará)
Visual Studio Code
  [x] {APPDATA}\Code\User                    1,2 MB
  [x] {USERPROFILE}\.vscode\extensions       410 MB
```

O usuário também pode adicionar qualquer pasta ou arquivo manualmente.

### 7.4 Captura de backup (itens 12, 16, 30)

#### 7.4.1 Fluxo

```
1. Para cada volume de origem distinto (C:, D:, ...) dos backups selecionados:
     se NTFS e interno → criar cópia de sombra (VSS)
     senão            → cópia direta, com aviso
2. Para cada backup:
     origem = caminho dentro da cópia de sombra (ou o original)
     destino = WinKit\Perfis\<perfil>\Backups\<id>\dados\
     robocopy origem destino /MIR (+ exclusões) — captura substitui a anterior
     grava item.json
3. Apagar todas as cópias de sombra (sempre, inclusive em caso de erro — try/finally)
```

#### 7.4.2 Cópia de sombra (VSS) — detalhes (D-006)

- Criar: `Invoke-CimMethod -ClassName Win32_ShadowCopy -MethodName Create -Arguments @{Volume='C:\'; Context='ClientAccessible'}` → `ShadowID`.
- Obter o caminho: `Get-CimInstance Win32_ShadowCopy -Filter "ID='<ShadowID>'"` → `DeviceObject` (`\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopyN`).
- Acesso: o `robocopy` não lida bem com caminhos `\\?\GLOBALROOT`. Criar um link simbólico de diretório temporário `C:\ProgramData\WinKit\snap\<n>` → `DeviceObject\` (a barra final é obrigatória) e copiar a partir dele. Ver H6.
- Apagar: `Remove-CimInstance` na instância da cópia de sombra; remover o link.
- Pré-requisitos: administrador e serviço VSS habilitado. Se falhar → oferecer cópia direta com aviso (arquivos em uso podem falhar).
- Consistência: a cópia de sombra é "como se o PC tivesse desligado naquele instante". Para apps com banco de dados aberto (navegadores, launchers), o Studio recomenda fechar o app antes, mas não obriga.
- Limpeza garantida: as cópias de sombra criadas recebem o id registrado em `C:\ProgramData\WinKit\vss-pendentes.json`; na próxima execução do Studio, cópias de sombra órfãs desse arquivo são apagadas.

#### 7.4.3 Pasta crua no pendrive (D-005)

| Problema | Tratamento |
|---|---|
| Caminhos > 260 caracteres | `robocopy` suporta nativamente; código Python usa o prefixo `\\?\` em todo acesso de arquivo (helper `platform.fs.long_path`) |
| Partição do Ventoy em FAT32 | Detectado no Construtor. Arquivo > 4 GB → erro antes de copiar, com o nome do arquivo |
| Resolução de data no FAT32 (2 s) | `robocopy /FFT` em todas as cópias para o pendrive |
| Links simbólicos e junções dentro da origem | `/XJ` (não segue junções), registrado no log; links de arquivo são copiados como conteúdo |
| Fluxos alternativos (ADS) e ACLs | Perdidos (exFAT não suporta). Irrelevante para configurações de apps |
| Muitos arquivos pequenos | Filtros de exclusão padrão (7.4.4) e aviso com a contagem de arquivos |
| Edição manual pelo usuário | Respeitada: a restauração copia o que estiver em `dados\` no momento |

#### 7.4.4 Exclusões padrão

Aplicadas a todo backup, editáveis por item: `Cache`, `Code Cache`, `GPUCache`, `DawnCache`, `ShaderCache`, `GrShaderCache`, `Crashpad`, `CrashDumps`, `logs`, `*.log`, `*.tmp`, `Temp`, `blob_storage`, `Service Worker\CacheStorage`.

#### 7.4.5 `item.json`

```json
{
  "id": "discord-settings",
  "template": "{APPDATA}\\discord",
  "kind": "folder",
  "captured_at": "2026-11-02T14:10:00-03:00",
  "source_literal": "C:\\Users\\Samuel\\AppData\\Roaming\\discord",
  "file_count": 37,
  "size_bytes": 1832211,
  "used_vss": true,
  "exclude": ["Cache", "Code Cache", "GPUCache", "logs"],
  "warnings": []
}
```

`source_literal` é só informativo (para o usuário entender de onde veio). **Nunca** é usado para restaurar.

#### 7.4.6 Avisos do que não sobrevive (item 16)

Dados protegidos por DPAPI estão presos à conta e à máquina de origem. O Coletor marca, na captura:

| Padrão encontrado | Aviso |
|---|---|
| `Local Storage\leveldb` em apps Electron (Discord, Slack, Teams) | "Login/token não funcionará; você terá que entrar de novo" |
| `Login Data`, `Cookies`, `Local State`, `Web Data` (Chromium) | "Senhas e cookies salvos não funcionarão" |
| `logins.json` + `key4.db` (Firefox) | Funciona só se não houver senha mestra ligada ao Windows — aviso genérico |
| Arquivos `*.dpapi`, pastas `Credentials`, `Protect` | "Credenciais do Windows não são transferíveis" |
| Regras extras por app | Vindas de `src/winkit/data/app_catalog.yaml` |

O aviso **não impede** a captura. Fica em `warnings` no item e aparece no resumo final.

---

## 8. Construtor

Roda no PC atual. Comandos: `winkit construir`, `winkit sincronizar` (item 27), `winkit validar`, `winkit pendrive listar`.

### 8.1 Detecção do pendrive Ventoy (item 24)

1. `Get-Disk | Get-Partition | Get-Volume` → JSON.
2. Um disco é Ventoy se tiver uma partição com rótulo `VTOYEFI` (≈ 32 MB, FAT) **e** outra partição de dados (normalmente rótulo `Ventoy`, exFAT ou NTFS).
3. A partição de dados com letra atribuída é o destino.
4. Mais de um pendrive Ventoy → o usuário escolhe. Nenhum → erro com instrução.
5. Registra o sistema de arquivos (exFAT/NTFS/FAT32) para as regras de 7.4.3.

### 8.2 Leitura das ISOs (item 1)

Para cada `*.iso` na partição de dados (recursivo, ignorando `WinKit\` e `ventoy\`):

1. `Mount-DiskImage -ImagePath <iso> -Access ReadOnly -PassThru` → letra.
2. `Get-WindowsImage -ImagePath <letra>:\sources\install.wim` (ou `.esd`, funciona igual para leitura) → índices e nomes.
3. Para cada índice: `Get-WindowsImage -ImagePath ... -Index N` → `Version` (build), `Architecture`, `Languages`.
4. `Dismount-DiskImage` sempre (try/finally).
5. Resultado em cache em `%LOCALAPPDATA%\WinKit\iso-cache.json`, chave = caminho + tamanho + data de modificação.

Uso: identificar Windows 10 vs 11 (build < 22000 → 10), idioma e arquitetura, e quais edições existem. ISOs que não são do Windows são ignoradas.

### 8.3 `ventoy.json` (item 19)

O plugin `auto_install` do Ventoy associa ISOs a modelos de resposta:

```json
{
  "auto_install": [
    {
      "image": "/Windows11_25H2.iso",
      "template": ["/ventoy/script/winkit-padrao-pt-BR-amd64.xml"],
      "autosel": 1,
      "timeout": 10
    }
  ]
}
```

Regras de mesclagem:

1. Se `ventoy.json` existir, faz o parse. **JSON inválido → aborta sem alterar nada** e mostra a posição do erro.
2. Na primeira alteração, copia para `ventoy.json.winkit-bak` (nunca sobrescreve esse backup depois).
3. Preserva todas as outras chaves e plugins.
4. Dentro de `auto_install`, entradas do WinKit são identificadas por terem um `template` começando com `/ventoy/script/winkit-`. Elas são atualizadas no lugar. Entradas de terceiros não são tocadas; se uma entrada de terceiro já aponta para a mesma ISO, o WinKit acrescenta seu modelo à lista `template` dela em vez de criar outra entrada.
5. Uma entrada por ISO (por causa do idioma — ver 9.5). O uso da chave `parent` (uma regra para uma pasta inteira) fica como otimização futura, depende de H1.
6. `autosel` e `timeout`: no modo silencioso, `autosel = 1` (o modelo do WinKit) com `timeout` configurável; nos outros modos, `autosel = 1` com `timeout` maior, para dar tempo de escolher "sem modelo" no menu do Ventoy.
7. Escrita atômica (arquivo temporário + renomear).

### 8.4 Gravação do payload

Ordem, com estimativa de espaço **antes** de copiar qualquer coisa (item 25):

```
1. Calcular bytes necessários: Agent + Apps novos/alterados + Drivers novos/alterados + Backups
2. shutil.disk_usage(partição) → livre
3. Se necessário > livre - margem(500 MB) → erro com detalhamento por categoria
4. Mostrar resumo e pedir confirmação (CLI: --sim para pular)
5. Copiar Agent\   (sempre substitui; versão nova)
6. Copiar Apps\ e Drivers\ (incremental, 8.5)
7. Capturar Backups (7.4)
8. Gravar receita.json (validada)
9. Gerar e gravar XMLs (seção 9)
10. Mesclar ventoy.json (8.3)
11. Gravar manifesto.json e winkit.marker
12. Validar (8.6)
```

Os passos 8–11 só acontecem se 5–7 terminarem sem erro, para nunca deixar o pendrive com uma receita apontando para arquivos que não foram copiados.

### 8.5 Sincronização incremental (item 27)

`manifesto.json` guarda, por arquivo de `Agent\`, `Apps\` e `Drivers\`: caminho relativo, tamanho, data de modificação e SHA-256.

`winkit sincronizar`:
- Copia só o que mudou (tamanho ou data diferentes → recalcula hash para confirmar).
- Remove do pendrive apps e drivers que saíram da receita (com confirmação).
- Recaptura backups marcados como alterados (ou todos, com `--backups`).
- Regera XMLs e `ventoy.json` só se a parte correspondente da receita mudou.

### 8.6 Validação (`winkit validar`)

Checa o pendrive sem alterar nada:
- Receita válida pelo esquema; regras de 6.2.
- Todo arquivo referenciado existe; hashes de `Apps\`/`Drivers\`/`Agent\` batem com o manifesto.
- Cada ISO tem entrada em `ventoy.json` e o XML existe e é XML válido.
- Versão do Agente no pendrive = versão do Studio.
- Avisos: arquivo > 4 GB em FAT32, arquitetura incompatível, app `msstore` exigindo internet, etc.

---

## 9. O `autounattend.xml`

Gerado por `core/unattend/` (lógica pura, testável no Linux) e gravado pelo `builder`, com `xml.etree.ElementTree` (**nunca** concatenando strings — ver ARQUITETURA.md). Um arquivo por combinação (perfil, idioma da ISO, arquitetura).

### 9.1 O que vai em cada etapa

| Etapa (pass) | Componente | Conteúdo |
|---|---|---|
| `windowsPE` | `Microsoft-Windows-International-Core-WinPE` | `SetupUILanguage`, `InputLocale`, `SystemLocale`, `UILanguage`, `UserLocale` |
| `windowsPE` | `Microsoft-Windows-Setup` | `UserData/ProductKey/Key` (chave genérica da edição, 9.4), `WillShowUI=OnError`; `AcceptEula=true`; `DynamicUpdate/Enable` conforme `updates.during_setup`; `RunSynchronous` com as chaves `LabConfig` (`BypassTPMCheck`, `BypassSecureBootCheck`, `BypassRAMCheck`) — redundante com o Ventoy, mas mantém o XML válido fora dele |
| `windowsPE` | — | **Sem `DiskConfiguration` e sem `ImageInstall/InstallTo`**: o usuário escolhe o disco (P3) |
| `specialize` | `Microsoft-Windows-Shell-Setup` | `ComputerName` (se definido), `TimeZone` |
| `specialize` | `Microsoft-Windows-Deployment` | `RunSynchronous`: (1) desativar a criptografia automática do dispositivo — **padrão ligado** (D-020, 14.3); (2) **bootstrap** (seção 10) |
| `oobeSystem` | `Microsoft-Windows-International-Core` | `InputLocale`, `SystemLocale`, `UILanguage`, `UserLocale` |
| `oobeSystem` | `Microsoft-Windows-Shell-Setup` | `OOBE` (`HideEULAPage`, `HideOnlineAccountScreens`, `HideWirelessSetupInOOBE`, `ProtectYourPC=3`, `HideOEMRegistrationScreen`), `UserAccounts/LocalAccounts` (conta local, grupo `Administrators`), `AutoLogon` (`LogonCount=1`, conforme 16.3) |

Todos os componentes recebem `processorArchitecture` da receita (`amd64` ou `arm64`).

### 9.2 Comando de bootstrap embutido

O XML contém apenas uma linha que localiza o pendrive certo e chama `bootstrap.ps1`. O campo `Path` aceita no máximo 259 caracteres, por isso a forma implementada (M2, `core/unattend/commands.py`, coberta por teste de snapshot) é:

```
cmd.exe /c for %d in (D E F ... Z) do @if exist %d:\WinKit\winkit.marker powershell.exe -nop -ep Bypass -File %d:\WinKit\Agent\bootstrap.ps1 %d: <pendrive_id> <perfil>
```

O `bootstrap.ps1` confere o `pendrive_id` do marcador e ignora pendrives de outro WinKit. Forma original planejada, descartada por exceder o limite:

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
  $id='<pendrive_id>';
  foreach($d in (Get-PSDrive -PSProvider FileSystem)){
    $m=Join-Path $d.Root 'WinKit\winkit.marker';
    if((Test-Path $m) -and ((Get-Content $m -Raw | ConvertFrom-Json).pendrive_id -eq $id)){
      & (Join-Path $d.Root 'WinKit\Agent\bootstrap.ps1') -PendriveRoot $d.Root -Profile '<perfil>'; break
    }
  }"
```

### 9.3 Senha

- `password_mode = empty`: `<Value></Value>` com `PlainText=true`. Recomendado em conjunto com o aviso de definir senha depois.
- `password_mode = stored`: o Windows aceita a senha "codificada" (Base64 de `senha + "Password"`), que **não é criptografia**. Fica legível no pendrive e em `C:\Windows\Panther\unattend.xml`. O Agente apaga esses arquivos no fim (10.4, 11.6). Aviso obrigatório no Studio.

### 9.4 Edição

A edição é escolhida pela **chave genérica de instalação** pública da Microsoft (não ativa o Windows; só seleciona a edição). As chaves ficam em `src/winkit/data/editions.yaml`. Se a máquina tiver licença digital ou chave no firmware, o Windows ativa sozinho depois.

### 9.5 Idioma

`UILanguage` **precisa** ser um idioma presente na imagem; senão o instalador falha. Por isso `ui_language = auto` usa o idioma da ISO detectado em 8.2, enquanto teclado, formatos regionais e fuso usam os valores da receita. Por isso existe um XML por idioma de ISO.

Desde o M11 (D-030), a receita nova **nasce com os valores do PC atual** (formatos, teclado e fuso, lidos do registro por `platform/locale.read_regional`); se não der para ler, ficam os padrões do Brasil. A descrição da conta local no XML sai no idioma do Studio.

---

## 10. Agente: inicialização (bootstrap)

### 10.1 `bootstrap.ps1` (roda na etapa *specialize*, como SYSTEM)

```
1. Recebe -PendriveRoot e -Profile
2. Copia WinKit\Agent\winkit-agent\  →  C:\ProgramData\WinKit\Agent\winkit-agent\
   (cópia local: o Agente continua funcionando entre reinicializações mesmo sem o pendrive;
    o pendrive só é necessário para o conteúdo — instaladores, drivers, backups)
3. Copia a receita → C:\ProgramData\WinKit\receita.json
4. Grava C:\ProgramData\WinKit\bootstrap.json  { pendrive_id, profile, timestamp, agent_version }
5. Cria C:\Windows\Setup\Scripts\SetupComplete.cmd (ou acrescenta uma linha, se já existir):
       "C:\ProgramData\WinKit\Agent\winkit-agent\winkit-agent.exe" phase1
6. Registra a tarefa agendada "WinKit\Fase2" (10.3)
7. Grava log em C:\ProgramData\WinKit\Logs\bootstrap.log
8. Sai SEMPRE com código 0 (um erro aqui não pode abortar a instalação do Windows)
```

É PowerShell (e não o Agente Python) para ser pequeno, rápido e não depender de nada na etapa *specialize*.

### 10.2 Por que `SetupComplete.cmd`

Roda como SYSTEM depois da instalação e antes da tela de login, com a tela nativa "Preparando o Windows". É o lugar natural da Fase 1.

**Risco conhecido:** a documentação da Microsoft indica que o `SetupComplete.cmd` não é executado quando o Windows é instalado com chave de produto OEM (exceto edições Enterprise). Muitos PCs de marca têm chave OEM no firmware. Usar a chave genérica da receita (9.4) provavelmente evita o problema, mas isso é a **hipótese H3**. Por isso existe o fallback de 10.3.

### 10.3 Tarefa agendada da Fase 2 e fallback

- Nome: `\WinKit\Fase2`.
- Gatilho: **ao fazer logon** (qualquer usuário).
- Principal: grupo `BUILTIN\Administrators`, `RunLevel = Highest` → roda na sessão do usuário logado, já elevado, **sem pedido de UAC**.
- Ação: `C:\ProgramData\WinKit\Agent\winkit-agent\winkit-agent.exe phase2`.
- Principal pelo SID `S-1-5-32-544` (Administradores), nunca pelo nome do grupo, que muda com o idioma.
- **Terceira rede de segurança (D-023):** o XML tem um `FirstLogonCommands` que inicia a Fase 2 sem bloquear a área de trabalho (`cmd /c start`), caso a tarefa agendada não tenha sido criada na etapa *specialize*. O Agente usa trava de instância única, então rodar duas vezes não causa problema.
- **Fallback:** ao iniciar, `phase2` lê o estado (11.4). Se a Fase 1 nunca rodou (H3 falhou, ou o `SetupComplete.cmd` foi ignorado), ela executa as etapas da Fase 1 primeiro, **redirecionando** os destinos do perfil Default para o perfil do usuário atual. O resultado final é o mesmo, só que mais tarde.
- A tarefa é removida na limpeza final (11.6).

### 10.4 O que é limpo no fim

- `C:\Windows\Setup\Scripts\SetupComplete.cmd`
- `C:\Windows\Panther\unattend.xml` e `C:\Windows\Panther\Unattend\*` (podem conter senha)
- Valores de logon automático em `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon` (`DefaultPassword`, `AutoAdminLogon`, `AutoLogonCount`) — o Windows já remove com `LogonCount=1`, o Agente confere
- Tarefa agendada `\WinKit\Fase2`
- `C:\ProgramData\WinKit\Agent\` (o executável)
- **Mantém**: `C:\ProgramData\WinKit\Logs\`, `estado.json`, `resumo.json` (para a tela de resumo)

---

## 11. Agente: fases, planejador e máquina de estados

### 11.1 Fase 1 × Fase 2 (D-009)

| | **Fase 1** | **Fase 2** |
|---|---|---|
| Quando | `SetupComplete.cmd`, antes da tela de login | Primeiro login (tarefa agendada) e logins seguintes até terminar |
| Quem | SYSTEM | Usuário administrador, elevado |
| Tela | Nativa "Preparando o Windows". **Nenhuma janela nossa** | Conforme o modo (seção 12) |
| Pode reiniciar? | Sim, livremente (ninguém está usando) | Conforme `reboot_policy` |
| Internet | Não garantida | Esperada (para winget e Windows Update) |
| Perfil de usuário | Não existe ainda → destino é o perfil Default | Existe → destino é o perfil real |

### 11.2 Planejador: em que fase cada etapa cai

O planejador (`core/planner/`) é uma **função pura**: `plan(receita, contexto) -> Plano`. Não executa nada; só decide ordem e fase. Totalmente testável no Linux.

Regras, aplicadas nesta ordem:

| # | Regra |
|---|---|
| R1 | Se `execution.mode = silent`, todo `decide_at_runtime` é tratado como `false`. |
| R2 | Item com `decide_at_runtime = true` → **Fase 2** (precisa da janela). |
| R3 | Drivers → **Fase 1**. |
| R4 | Remoção de bloatware e bloqueio de reinstalação → **Fase 1**. |
| R5 | Ajustes com escopo `machine` (nome do PC, energia, políticas) → **Fase 1**. |
| R6 | Ajustes com escopo `user` → **Fase 1**, aplicados ao registro do perfil Default; se R2, **Fase 2** no `HKCU` real. |
| R7 | Backup com molde de perfil (`{APPDATA}`, `{DOCUMENTS}`...) → **Fase 1** no perfil Default. |
| R8 | Backup com molde `{PROGRAMDATA}`, `{PROGRAMFILES}` ou `{PROGRAMFILESX86}` → **Fase 1** (não depende de perfil). Backup `{ABS:...}` → **Fase 2** (a unidade pode não existir antes). |
| R9 | App `source=offline`, `scope=machine` → **Fase 1**. |
| R10 | App `source=winget_online` → **Fase 2** (o winget não é confiável como SYSTEM antes do login — ver H5). |
| R11 | App `scope=user` → **Fase 2** (precisa do perfil do usuário). |
| R12 | App `source=portable` → como um backup (R7/R8) + criação de atalho na Fase 2. |
| R13 | Backup listado em `restore_backups_after_install` de um app → mesma fase do app, **depois** dele. |
| R14 | Windows Update → **última etapa da Fase 2**. |
| R15 | Etapa da Fase 1 que falhou com erro recuperável → nova tentativa na Fase 2 (uma vez). |

Detalhes fixados na implementação (M1, `core/planner/planner.py`):
- `updates.block_wu_driver_replacement` e `bloatware.disable_consumer_content` viram etapas de ajuste implícitas (`tweak:system.wu_no_driver_replacement` e `tweak:system.consumer_content`), na Fase 1.
- Ajustes com `stage: specialize` (hoje só a criptografia, D-020) não viram etapa do Agente: vão no XML e aparecem em `plan.excluded`.
- Bloatware ou ajuste que não se aplica à versão do Windows (`windows.os`, `min_build`, `max_build`) também vai para `plan.excluded`, com o motivo.
- Uma dependência de app que não foi selecionada é ignorada.
- No fallback (Fase 1 não rodou), as etapas da Fase 1 vão para o começo da Fase 2 mantendo a ordem relativa, e `default_profile` vira `user_profile`.

Ordem **dentro** de cada fase:

```
FASE 1                                     FASE 2
 1. localizar pendrive + verificar hashes   1. trava de instância única + localizar pendrive
 2. drivers (prioridade 0 → 9)              2. [fallback] etapas pendentes da Fase 1
 3. nome do PC, energia, políticas          3. janela/bandeja conforme o modo (seção 12)
 4. bloatware + bloqueio de reinstalação    4. esperar área de trabalho pronta e rede (com limite de tempo)
 5. ajustes de usuário → perfil Default     5. backups restantes ({ABS}, decididos na hora)
 6. backups → perfil Default                6. esperar winget disponível (11.5)
 7. apps de máquina offline                 7. apps (ordem + dependências)
      (por `order`, respeitando `depends_on`)  8. backups pós-instalação (R13)
 8. backups pós-instalação (R13)            9. ajustes decididos na hora → HKCU
 9. copiar logs para o pendrive            10. atalhos de apps portáteis
                                           11. Windows Update
                                           12. resumo, notificação, atalho, logs, limpeza
```

**Backups vêm antes dos apps** na mesma fase, para que, se você abrir um app enquanto o resto instala, as configurações já estejam lá. A exceção é R13.

### 11.3 Etapas (steps)

Cada etapa é um objeto com:

```
id               "app:7zip", "backup:discord-settings", "driver:net-realtek-rtl8125" ...
kind             driver | bloat | tweak | backup | app | shortcut | windows_update | cleanup
phase            1 | 2
needs_pendrive   bool     (instaladores, drivers e backups: sim; ajustes: não)
needs_network    bool
reversible       bool
depends_on       [ids]
```

Contrato de toda etapa (ver ARQUITETURA.md, "Idempotência"):
- `check()` → já está feito? (ex.: app já instalado, pasta já restaurada, chave já com o valor)
- `run()` → faz.
- Rodar duas vezes não causa dano nem duplica nada.

### 11.4 Estado e retomada

`C:\ProgramData\WinKit\estado.json`, gravado de forma atômica a cada mudança:

```json
{
  "schema_version": 1,
  "recipe_hash": "sha256:...",
  "phase1": { "status": "done", "started_at": "...", "finished_at": "..." },
  "phase2": { "status": "running", "boot_count": 2 },
  "steps": {
    "driver:net-realtek-rtl8125": { "status": "done",    "attempts": 1, "phase_ran": 1 },
    "app:discord":                { "status": "pending", "attempts": 0 },
    "app:steam":                  { "status": "failed",  "attempts": 2, "error": "código de saída 1603" },
    "backup:d-jogos":             { "status": "skipped", "reason": "unidade D: não existe" }
  },
  "reboot_pending": false
}
```

Status possíveis: `pending → running → done | failed | skipped`. Uma etapa encontrada como `running` ao iniciar significa que o processo morreu no meio (queda de energia, reinício forçado): roda `check()` e, se não estiver feita, executa de novo (até 3 tentativas no total).

### 11.5 Reinicializações

- Códigos de saída `3010` e `1641` (e os `reboot_codes` do app) marcam `reboot_pending = true`.
- **Fase 1**: o Agente termina as etapas que não dependem de reinício e devolve o controle ao Windows; o reinício natural após o `SetupComplete.cmd` resolve. Se uma etapa exigir reinício **antes** de outra (`depends_on`), a dependente vai para a Fase 2.
- **Fase 2**: conforme `reboot_policy`:
  - `ask`: notificação "Reiniciar agora / Depois". Se ignorada, a Fase 2 continua no próximo login.
  - `auto_if_idle`: reinicia sozinho se não houver entrada de teclado/mouse há 5 minutos (`GetLastInputInfo`), com aviso de 60 s.
  - `never`: espera o usuário reiniciar por conta própria.
- **Disponibilidade do winget** na Fase 2: espera `Microsoft.DesktopAppInstaller` registrado e `winget --version` com código 0, por até 10 minutos; tenta `Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe` uma vez. Sem sucesso → apps winget ficam `pending` para o próximo login e o resumo explica.

### 11.6 Pendrive removido

- Toda etapa com `needs_pendrive` verifica o marcador (mesmo `pendrive_id`) antes de começar.
- Se sumir: etapas que não precisam do pendrive continuam; as outras esperam, verificando a cada 5 s.
- Modo com janela: aviso na janela. Modo silencioso: notificação "Reconecte o pendrive WinKit para continuar" (uma vez a cada 5 minutos, no máximo).
- A letra da unidade pode mudar entre reinicializações: o pendrive é sempre procurado pelo marcador, nunca pela letra.

### 11.7 Logs (item 26)

- `C:\ProgramData\WinKit\Logs\agente.log` (texto legível, pt-BR) e `eventos.jsonl` (um evento JSON por linha: horário, etapa, nível, mensagem, dados).
- Copiados para `WinKit\Logs\<nome-do-pc>_<data>\` no pendrive ao fim da Fase 1, ao fim da Fase 2 e a cada erro, se o pendrive estiver presente.
- Saída de instaladores é capturada em arquivo próprio por etapa (`Logs\steps\<id>.log`); MSI com `/l*v`.

---

## 12. Agente: modos de execução e interface

### 12.1 Os três modos (D-008)

| Modo | Fase 1 | Fase 2 |
|---|---|---|
| **Silencioso** | Igual em todos os modos: sem janela | Nenhuma janela. Ícone na bandeja (se `show_tray_icon`), notificação ao terminar |
| **Contagem regressiva** | | Janela com a lista de etapas pré-marcadas e "Iniciando em N s". Qualquer interação para a contagem |
| **Interativo** | | Mesma janela, sem contagem; espera "Iniciar" |

### 12.2 Janela da Fase 2 (modos com janela)

```
┌─ WinKit — Finalizando a configuração ──────────────────────────────┐
│ Já feito antes do login: 6 drivers · 14 apps removidos ·          │
│ 9 ajustes · 3 backups · 4 apps                         [detalhes] │
│                                                                    │
│ A fazer agora:                                                     │
│  Backups                                                           │
│   [x] Saves do jogo X  →  D:\Jogos\X          ⚠ unidade D: ausente │
│  Apps                                                              │
│   [x] Discord          (winget)                                    │
│   [x] Spotify          (winget)                                    │
│  Ajustes                                                           │
│   [x] Tema escuro                                                  │
│  Windows Update                                                    │
│   [x] Instalar atualizações                                        │
│                                                                    │
│ Iniciando em 27 s…        [Adiar para o próximo login] [Iniciar]   │
└────────────────────────────────────────────────────────────────────┘
```

- Itens com `decide_at_runtime = true` aparecem com a escolha padrão da receita, editáveis.
- Itens sem essa marcação aparecem como informação, sem caixa de seleção.
- Depois de "Iniciar": a janela vira uma tela de progresso, que pode ser minimizada para a bandeja.
- "Adiar para o próximo login": nada é feito agora; a tarefa roda de novo no próximo login.

### 12.3 Modo silencioso

- Nenhuma janela, em nenhum momento, salvo a notificação final e os avisos de pendrive (11.6) e reinício (11.5).
- Ícone na bandeja com dica "WinKit: 7 de 12 — instalando Discord"; clicar abre a tela de progresso (opcional, `show_tray_icon`).
- Ao terminar: notificação "WinKit concluído — 2 avisos" + atalho "Resumo do WinKit" na área de trabalho (`desktop_summary_shortcut`).
- Instaladores que abrem o app no final: o Agente encerra os processos listados em `after_install.kill_processes` (do catálogo) e remove as entradas de inicialização automática de `disable_autostart`. Sem garantia de 100% para apps desconhecidos — registrado como DT.

### 12.4 Tela de resumo (item 36)

Aberta pelo atalho na área de trabalho ou ao fim dos modos com janela:
- Tempo total, por fase.
- Contagem por tipo: feito, falhou, pulado.
- Lista de falhas com motivo legível e o que fazer ("Steam: o instalador retornou 1603. Instale manualmente; o instalador está em `WinKit\Apps\steam\`").
- Lista de avisos (dados DPAPI, unidade ausente, senha vazia).
- Botões: "Abrir log", "Tentar de novo os que falharam", "Apagar este atalho".

### 12.5 Tecnologia da interface

- PySide6 (`QWidget`, `QSystemTrayIcon` — no Windows 11 `showMessage` vira notificação nativa).
- **Qt só é importado na Fase 2**, e só se o modo precisar (import tardio). A Fase 1 nunca carrega Qt (teste automatizado garante — ver ARQUITETURA.md).
- Textos em pt-BR, centralizados em `winkit/i18n/pt_br.py`.

---

## 13. Motores compartilhados

### 13.1 Cópia de arquivos (`platform/copy.py`)

Implementado sobre `robocopy` (presente em todo Windows, suporta caminhos longos, tentativas e exclusões).

| Uso | Parâmetros |
|---|---|
| Captura para o pendrive (espelho) | `/MIR /COPY:DAT /DCOPY:T /FFT /XJ /R:1 /W:1 /NP /NJH /NJS /UNILOG:<log>` + `/XD`/`/XF` |
| Restauração `merge` (padrão) | `/E /COPY:DAT /DCOPY:T /XC /XN /XO /XJ /R:1 /W:1` → só copia arquivos que **não existem** no destino |
| Restauração `overwrite` | `/E /COPY:DAT /DCOPY:T /IS /IT /XJ /R:1 /W:1` |
| Restauração `skip` | Se a pasta de destino existir, não faz nada |
| Arquivo solto | `robocopy <pasta> <destino> <arquivo>` com as mesmas regras |

Interpretação do código de saída do `robocopy`: `0–7` sucesso (bits informativos), `≥ 8` falha. Nunca se lê o texto da saída. `/UNILOG` grava o log em UTF-16, convertido para UTF-8 ao copiar para o pendrive.

### 13.2 Registro e perfil Default (`platform/registry.py`)

- Ajustes `user` na Fase 1: `reg load HKU\WinKitDefault C:\Users\Default\NTUSER.DAT` → aplicar via `winreg` em `HKEY_USERS\WinKitDefault\...` → fechar todos os handles → `reg unload`. Sempre em try/finally; antes do `unload` chama `gc.collect()` porque handles abertos impedem a descarga.
- Ajustes `user` na Fase 2: `HKEY_CURRENT_USER` direto.
- Ajustes `machine`: `HKEY_LOCAL_MACHINE`.
- Operações suportadas: definir valor (DWORD, QWORD, SZ, EXPAND_SZ, MULTI_SZ, BINARY), apagar valor, apagar chave, criar chave vazia.

### 13.3 Execução de instaladores (`platform/installers.py`)

Detecção do tipo (quando não vem do catálogo nem do manifesto winget), por assinatura no arquivo:

| Tipo | Como detectar | Switches silenciosos padrão |
|---|---|---|
| MSI | Cabeçalho OLE `D0 CF 11 E0 A1 B1 1A E1` + extensão `.msi` | `msiexec /i <f> /qn /norestart /l*v <log>` |
| MSIX/APPX | ZIP com `AppxManifest.xml` | `Add-AppxProvisionedPackage -Online` (máquina) ou `Add-AppxPackage` (usuário) |
| Inno Setup | String `Inno Setup Setup Data` no executável | `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-` |
| NSIS | String `Nullsoft.NSIS` / `NullsoftInst` | `/S` |
| WiX Burn | Seção PE `.wixburn` | `/quiet /norestart` |
| InstallShield | String `InstallShield` | `/s /v"/qn /norestart"` (varia — exige confirmação) |
| Squirrel | String `Squirrel` / `Update.exe` embutido | `-s` (sempre escopo `user`) |
| Desconhecido | — | O Studio exige que o usuário informe os argumentos |

Regras de execução:
- Lista de argumentos, sem shell.
- Limite de tempo por instalador (padrão 30 min, configurável no catálogo).
- Códigos de sucesso e de reinício por app (padrão `[0]` e `[3010, 1641]`).
- Antes de rodar: verifica o SHA-256 do arquivo contra o `manifesto.json`.
- Depois: `kill_processes`, `disable_autostart`.

### 13.4 winget (`platform/winget.py`)

- Instalação: `winget install --id <id> --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity --scope <machine|user>` (+ `--source msstore` quando for o caso).
- Resultado só pelo código de saída (os códigos do winget são documentados; tabela em `platform/winget_codes.py`). "Já instalado" conta como sucesso.

### 13.5 Appx (`platform/appx.py`)

- Remover para todos: `Get-AppxProvisionedPackage -Online | Where DisplayName -eq <nome> | Remove-AppxProvisionedPackage -Online -AllUsers` e `Get-AppxPackage -AllUsers -Name <nome> | Remove-AppxPackage -AllUsers`.
- Bloquear reinstalação (item 37): criar a chave `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Appx\AppxAllUserStore\Deprovisioned\<PackageFamilyName>`.

### 13.6 Execução de comandos externos (`platform/runner.py`)

Ponto único para `subprocess`. Ver as regras em ARQUITETURA.md. PowerShell sempre via `platform/powershell.py`, que:
- Chama `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command`.
- Prefixa `[Console]::OutputEncoding=[Text.Encoding]::UTF8; $ErrorActionPreference='Stop';`.
- Converte o resultado com `ConvertTo-Json -Depth 8 -Compress` e devolve objetos Python.
- Erros do PowerShell viram `PowerShellError` com a mensagem e o comando.

---

## 14. Bloatware e ajustes do sistema

### 14.1 Bloatware (itens 11 e 37)

Lista em `src/winkit/data/bloatware.yaml`, cada entrada com: nome do pacote, nome amigável em pt-BR, nível de risco, efeitos colaterais, versões de Windows em que existe.

| Nível | Comportamento no Studio | Exemplos |
|---|---|---|
| `safe` | Pode ser pré-selecionado | Clipchamp, Notícias, Clima, Solitaire, Dicas, Hub de Comentários, Mapas, Teams pessoal, Bing Search, Obter Ajuda, Power Automate, Paciência, Pessoas |
| `caution` | Desmarcado; ao marcar, mostra o efeito colateral | Apps Xbox (quebra Game Pass/Game Bar), Fotos, Ferramenta de Captura, Calculadora, Copilot, Widgets, Outlook novo, OneDrive |
| `blocked` | Não pode ser marcado; aparece com o motivo | Microsoft Store, Instalador de Aplicativo (é o winget), frameworks (VCLibs, UI.Xaml, .NET Native), Segurança do Windows, ShellExperienceHost, StartMenuExperienceHost |

O Construtor mostra só os pacotes presentes nas ISOs do pendrive (lidos em 8.2 por versão/build).

**Impedir que voltem:**
- Item 37: chave `Deprovisioned` (13.5) para cada pacote removido.
- `disable_consumer_content`: valores do `ContentDeliveryManager` no perfil Default (`SilentInstalledAppsEnabled=0`, `PreInstalledAppsEnabled=0`, `OemPreInstalledAppsEnabled=0`, `ContentDeliveryAllowed=0` e os `SubscribedContent-*`), porque a política `DisableWindowsConsumerFeatures` só é respeitada nas edições Enterprise/Education.

### 14.2 Ajustes (itens 31, 32, 34)

Definidos em `src/winkit/data/tweaks.yaml` (formato em 15.2). Lista inicial:

**Privacidade (31)**

| id | Escopo |
|---|---|
| `privacy.telemetry_minimum` | machine |
| `privacy.advertising_id` | user |
| `privacy.activity_history` | machine |
| `privacy.tailored_experiences` | user |
| `privacy.start_bing_search` | user |
| `privacy.start_suggestions` | user |
| `privacy.copilot` | user + machine |
| `privacy.recall` | machine (desativar o recurso opcional) |
| `privacy.widgets` | machine |
| `privacy.welcome_experience` | user |
| `privacy.lock_screen_tips` | user |

**Visual (32)**

| id | Escopo | Só Win11 |
|---|---|---|
| `visual.dark_theme` | user | |
| `visual.taskbar_left` | user | ✓ |
| `visual.show_extensions` | user | |
| `visual.show_hidden_files` | user | |
| `visual.classic_context_menu` | user | ✓ |
| `visual.explorer_this_pc` | user | |
| `visual.hide_task_view_button` | user | |
| `visual.hide_widgets_button` | user | ✓ |
| `visual.start_hide_recommended` | user | ✓ |

**Energia (34)**: `power.scheme`, `power.hibernate`, `power.fast_startup` (`powercfg` + `HiberbootEnabled`) — machine.

**Sistema** (novos, levantados no desenho):

| id | Escopo | Por quê |
|---|---|---|
| `windows.prevent_device_encryption` (campo da receita, não um ajuste opcional) | machine, na etapa *specialize* | **Ligado por padrão (D-020).** O Windows 11 liga a criptografia automática do dispositivo, inclusive no momento em que uma conta Microsoft é adicionada depois. Com `PreventDeviceEncryption=1` gravado antes da OOBE, o Windows não criptografa o disco sozinho em nenhum desses casos. O BitLocker continua disponível para ser ligado manualmente. |
| `system.wu_no_driver_replacement` | machine | Impede o Windows Update de trocar os drivers que você instalou (`updates.block_wu_driver_replacement`) |

**Os valores exatos de registro não estão neste plano de propósito**: eles vão no `src/winkit/data/tweaks.yaml`, cada um com o campo `source` (link para a documentação ou referência que justifica o valor), e são cobertos por teste de esquema.

### 14.3 Ajustes que rodam fora das fases

`windows.prevent_device_encryption` precisa rodar **antes** de a criptografia começar, por isso é um `RunSynchronous` na etapa *specialize* do XML, e não uma etapa do Agente.

---

## 15. Dados versionados (catálogos)

Todos em `src/winkit/data/`, em YAML, cada um com esquema Pydantic em `core/catalog/` e teste que valida o arquivo no CI.

### 15.1 `src/winkit/data/app_catalog.yaml`

```yaml
- id: discord
  name: Discord
  match:                                 # como reconhecer no inventário
    display_name_regex: "^Discord$"
    winget_ids: ["Discord.Discord"]
  scope: user
  installer:
    type: squirrel
    args: ["-s"]
  after_install:
    kill_processes: ["Discord.exe", "Update.exe"]
    disable_autostart:
      - hive: HKCU
        key: 'Software\Microsoft\Windows\CurrentVersion\Run'
        value: Discord
  config_paths:                          # item 28
    - template: '{APPDATA}\discord\settings.json'
      kind: file
      recommended: true
    - template: '{APPDATA}\discord\Local Storage'
      kind: folder
      recommended: false
      warning: dpapi_token
  installer_wipes_config: false          # se true → backup vai em restore_backups_after_install
```

### 15.2 `src/winkit/data/tweaks.yaml`

```yaml
- id: visual.show_extensions
  title: Mostrar extensões de arquivo
  description: Exibe ".exe", ".pdf" etc. no Explorador de Arquivos.
  category: visual
  risk: safe
  scope: user
  windows: { os: [10, 11], min_build: null, max_build: null }
  source: "<link da documentação>"
  apply:
    - reg_set: { key: 'Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced',
                 value: HideFileExt, type: dword, data: 0 }
  undo:
    - reg_set: { key: 'Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced',
                 value: HideFileExt, type: dword, data: 1 }
```

Operações permitidas em `apply`/`undo`: `reg_set`, `reg_delete_value`, `reg_delete_key`, `service_start_type`, `optional_feature_disable`, `powercfg`, `appx_remove`. **Não existe operação "rodar comando arbitrário"** — se um ajuste precisar de algo novo, cria-se uma operação nova, tipada e testada.

### 15.3 Outros

| Arquivo | Conteúdo |
|---|---|
| `src/winkit/data/bloatware.yaml` | 14.1 |
| `src/winkit/data/editions.yaml` | Edição → chave genérica de instalação pública, por sistema (10/11) |
| `src/winkit/data/installer_signatures.yaml` | Assinaturas e switches da tabela 13.3 |
| `src/winkit/data/dpapi_patterns.yaml` | Padrões da tabela 7.4.6 |
| `src/winkit/data/default_excludes.yaml` | Exclusões de 7.4.4 |
| `src/winkit/data/driver_classes.yaml` | Classes de driver, prioridade e se é recomendada |

---

## 16. Segurança e salvaguardas

### 16.1 Salvaguardas de dados

| Risco | Salvaguarda |
|---|---|
| Apagar o disco errado | Nunca há `DiskConfiguration` no XML; teste automatizado garante que o XML gerado não contém esse elemento |
| Corromper o `ventoy.json` | Parse antes; aborta em JSON inválido; backup `.winkit-bak`; escrita atômica |
| Apagar arquivos do usuário no pendrive | O Construtor só escreve em `WinKit\` e `ventoy\script\winkit-*.xml`; `/MIR` só é usado dentro de `WinKit\Perfis\<perfil>\Backups\<id>\dados\` (o código verifica o caminho antes de chamar) |
| Sobrescrever configuração no PC novo | Restauração `merge` por padrão (D-007) |
| Cópias de sombra órfãs ocupando disco | Registro em `vss-pendentes.json` + limpeza na próxima execução |
| Pendrive corrompido executando instalador adulterado | SHA-256 de `Apps\`/`Drivers\`/`Agent\` verificado antes de executar |

### 16.2 Superfície de execução

- O Agente roda como SYSTEM e como administrador. Ele só executa o que está na receita e nos catálogos; não existe operação de "comando arbitrário" nos ajustes (15.2).
- Os únicos executáveis rodados são: instaladores listados na receita (com hash conferido), ferramentas do Windows (`robocopy`, `pnputil`, `powercfg`, `msiexec`, `reg`, `powershell`, `winget`) por caminho absoluto em `%SystemRoot%\System32` (exceto o `winget`, resolvido pelo pacote do App Installer).
- Sem telemetria. Nenhuma conexão de rede é feita pelo WinKit, exceto via `winget` e Windows Update quando a receita pedir.

### 16.3 Senha da conta

- Padrão recomendado: `password_mode = empty`. O resumo final lembra de definir uma senha.
- `stored`: aviso explícito no Studio de que a senha fica **legível** no pendrive (9.3). O Agente apaga as cópias no Windows novo (10.4), mas não no pendrive.

### 16.4 Assinatura de código

Os executáveis não são assinados no v1 (registrado como dívida técnica). Arquivos copiados de exFAT não recebem a marca "baixado da internet", então o SmartScreen não deve bloquear; o Defender pode suspeitar de executáveis PyInstaller (H7).

---

## 17. Stack e ferramentas

| Item | Escolha | Por quê |
|---|---|---|
| Linguagem | Python 3.12 | D-003 |
| Interface | PySide6 (Qt 6) | Licença LGPL, bandeja e notificações nativas |
| Validação de dados | Pydantic v2 | Esquema da receita e dos catálogos, exporta JSON Schema |
| Catálogos | YAML (PyYAML, `safe_load`) | Editável por humanos, com comentários |
| XML | `xml.etree.ElementTree` (biblioteca padrão) | Escapa tudo corretamente; zero dependência |
| CLI | `argparse` (biblioteca padrão) | Zero dependência; poucos comandos |
| Testes | pytest, pytest-cov | |
| Qualidade | ruff (lint + formatação), mypy (`--strict` em `core/`) | |
| Regras de camadas | import-linter | Garante a regra de dependência de 4.2 no CI |
| Ambiente | uv | Rápido, com arquivo de travamento de versões |
| Empacotamento | PyInstaller, modo **onedir** | Onefile extrai para `%TEMP%` a cada execução (lento, mais alarmes de antivírus) |
| CI | GitHub Actions: Linux (core, builder) + `windows-latest` (platform) | |

Ferramentas do Windows usadas (todas nativas, nada a instalar): `robocopy`, `pnputil`, `powercfg`, `msiexec`, `reg`, PowerShell 5.1, `winget` (App Installer).

**Nenhuma** dependência do Windows ADK, `oscdimg`, 7-Zip, `xorriso` ou wimlib — consequência direta de D-002.

---

## 18. Estrutura do repositório

```
WinKit/
├── CLAUDE.md                       regras obrigatórias para quem mexe no código
├── README.md                       apresentação, aviso de uso por conta e risco, licença
├── CONTRIBUTING.md                 como contribuir
├── LICENSE                         Apache License 2.0
├── NOTICE                          direitos autorais e aviso de isenção (100% vibe-codado)
├── pyproject.toml
├── uv.lock
├── .github/workflows/ci.yml        lint, tipos, testes (Linux + Windows), empacotamento
├── .github/workflows/release.yml   tag vX.Y.Z → compila, testa e publica a release com o .zip
├── docs/
│   ├── PLANO.md                    este arquivo
│   ├── ARQUITETURA.md              arquitetura, regras de código, registro de decisões
│   ├── STATUS.md                   andamento por marco
│   ├── DIVIDAS_TECNICAS.md
│   ├── INCIDENTES.md               o que deu errado
│   ├── CHANGELOG.md                mapa de todas as mudanças
│   └── validacao/                  roteiros de teste manual em hardware real (um por marco)
├── src/winkit/data/                           catálogos YAML (seção 15)
├── src/winkit/
│   ├── __init__.py                 versão
│   ├── i18n/pt_br.py               todos os textos exibidos ao usuário
│   ├── data/                       catálogos YAML (seção 15), empacotados junto com o código (D-021)
│   ├── core/                       PURO — sem Windows, sem Qt, sem subprocess
│   │   ├── recipe/                 modelos Pydantic, validação, migrações
│   │   ├── catalog/                modelos dos catálogos + carregamento
│   │   ├── paths/                  moldes de caminho (6.3)
│   │   ├── planner/                planejador de fases (11.2)
│   │   ├── state/                  modelo do estado + transições (11.4)
│   │   ├── manifest/               manifesto e diff incremental (8.5)
│   │   ├── ventoy/                 mesclagem do ventoy.json (8.3)
│   │   ├── unattend/               geração do XML (seção 9)
│   │   ├── installers/             detecção de tipo por bytes (13.3)
│   │   └── errors.py               hierarquia de exceções
│   ├── platform/                   Windows — efeitos colaterais, atrás de interfaces
│   │   ├── interfaces.py           Protocols: Registry, Shell, Fs, Vss, Appx, Winget...
│   │   ├── runner.py               único ponto de subprocess
│   │   ├── powershell.py
│   │   ├── registry.py
│   │   ├── known_folders.py
│   │   ├── copy.py                 robocopy
│   │   ├── vss.py
│   │   ├── drivers.py
│   │   ├── appx.py
│   │   ├── winget.py
│   │   ├── installers.py
│   │   ├── disks.py                detecção do Ventoy, leitura de ISO
│   │   ├── scheduler.py            tarefas agendadas
│   │   └── fakes/                  implementações falsas para testes no Linux
│   ├── collector/                  seção 7
│   ├── builder/                    seção 8 (usa core.unattend e core.ventoy)
│   │   └── assets/bootstrap.ps1
│   ├── agent/                      seções 10–12
│   │   ├── main.py                 phase1 | phase2 | summary
│   │   ├── steps/                  uma classe por tipo de etapa
│   │   ├── executor.py             roda o plano, persiste estado
│   │   └── ui/                     PySide6 — import tardio
│   ├── studio/ui/                  PySide6 (M10)
│   └── cli/                        winkit coletar | construir | sincronizar | validar | pendrive
├── packaging/
│   ├── winkit-studio.spec, winkit.spec, winkit-agent.spec
│   ├── build.ps1                   gera dist\WinKit-<versão>
│   ├── smoke.ps1                   teste de fumaça com os executáveis prontos
│   ├── LEIA-ME.txt                 vai dentro do pacote
│   └── NOTAS_DA_VERSAO.md          texto da página da release
└── tests/
    ├── core/                       roda no Linux
    ├── builder/                    roda no Linux com fakes
    ├── collector/                  roda no Linux com fakes
    ├── agent/                      roda no Linux com fakes
    ├── platform/                   só Windows (marcador pytest "windows")
    ├── src/winkit/data/                       valida todos os YAML
    └── fixtures/                   amostras: ventoy.json, instaladores mínimos, saídas JSON gravadas
```

---

## 19. Estratégia de testes

### 19.1 Camadas de teste

| Camada | Onde roda | O que cobre | Meta |
|---|---|---|---|
| Unitário `core` | Linux e Windows, CI | Receita, planejador, moldes de caminho, manifesto, ventoy.json, XML, detecção de instalador | ≥ 90% de cobertura |
| Unitário `collector`/`builder`/`agent` com fakes | Linux e Windows, CI | Fluxos completos sem tocar o sistema | ≥ 80% |
| Integração `platform` | `windows-latest`, CI | registro (chaves temporárias em HKCU), robocopy, PowerShell JSON, VSS (se o runner permitir), carregar/descarregar hive | Caminho feliz + erros principais |
| Snapshot | CI | XML gerado e `ventoy.json` mesclado comparados com arquivos de referência | Toda mudança no XML aparece no diff de revisão |
| Dados | CI | Todos os YAML validam no esquema; ids únicos; todo ajuste tem `source` e `undo` | 100% |
| **Validação em hardware real** | PC do usuário | Roteiro manual por marco em `docs/validacao/` | Obrigatória para fechar M2, M3, M5, M6, M7, M8 |

### 19.2 Testes de proteção (não podem ser removidos)

- O XML gerado nunca contém `DiskConfiguration` nem `InstallTo`.
- A Fase 1 não importa `PySide6` (roda o caminho da Fase 1 com `sys.modules` vigiado).
- Nenhum módulo de `core` importa `platform`, `winreg`, `subprocess` ou `PySide6` (import-linter).
- `/MIR` só é chamado com destino dentro de uma pasta `dados\` de backup.
- Mesclar o `ventoy.json` preserva chaves desconhecidas e entradas de terceiros.

### 19.3 Validação em hardware real

O ambiente de desenvolvimento é Linux; o produto roda em Windows e depende do Ventoy e do instalador do Windows. Por isso cada marco que mexe nisso tem um roteiro em `docs/validacao/Mx.md` com passos, resultado esperado e campo para o usuário anotar o resultado. Resultado diferente do esperado vira entrada em `INCIDENTES.md`.

---

## 20. Marcos de implementação

Cada marco tem um **critério de pronto**. Um marco só é marcado como concluído em `STATUS.md` quando o critério for cumprido, incluindo a validação em hardware quando indicada.

### M0 — Fundação
- `pyproject.toml`, uv, ruff, mypy, pytest, import-linter, CI (Linux + Windows).
- Estrutura de pastas da seção 18 com `__init__.py`.
- `core/errors.py`, `i18n/pt_br.py`, `platform/runner.py` e `platform/powershell.py` (com testes).
- **Pronto quando:** CI verde nas duas plataformas, com os testes de proteção de camadas ativos.

### M1 — Núcleo puro
- Modelos da receita + validação 6.2 + migração (estrutura).
- Moldes de caminho (6.3) — tradução e resolução, com fake de Known Folders.
- Catálogos: esquemas + versões iniciais de `editions.yaml`, `installer_signatures.yaml`, `default_excludes.yaml`, `driver_classes.yaml`, `dpapi_patterns.yaml`.
- Planejador (11.2) com as regras R1–R15, ordenação e detecção de ciclos.
- Modelo de estado (11.4) e transições.
- Manifesto e diff incremental (8.5).
- **Pronto quando:** todos os testes de `core` passam no Linux com ≥ 90% de cobertura.

### M2 — Construtor mínimo + primeira instalação real
- Detecção do Ventoy (8.1) e leitura de ISOs (8.2).
- Gerador do XML (seção 9) — conta local, idioma, teclado, fuso, edição, bypass, criptografia, bootstrap.
- Mesclagem do `ventoy.json` (8.3).
- `bootstrap.ps1` mínimo: só grava `bootstrap.json` e um log em `C:\ProgramData\WinKit\` e copia o log para o pendrive.
- CLI: `winkit pendrive listar`, `winkit construir --somente-xml`, `winkit validar`.
- **Pronto quando (hardware real):** boot pelo Ventoy, Windows instala com conta local sem conta Microsoft, nome do PC e fuso corretos, a ISO não foi alterada (hash igual), e o log do bootstrap aparece no pendrive. **Valida H1, H2, H9.**

### M3 — Esqueleto do Agente
- `winkit-agent` empacotado (PyInstaller onedir) com `phase1`, `phase2`, `summary`.
- Executor + estado persistido + retomada + trava de instância única.
- `SetupComplete.cmd`, tarefa agendada, fallback de 10.3, limpeza de 10.4.
- Localização do pendrive pelo marcador; espera se removido (11.6).
- Logs (11.7) copiados para o pendrive.
- Etapa de teste "no-op" em cada fase para provar o encadeamento.
- **Pronto quando (hardware real):** a Fase 1 roda antes do login, a Fase 2 roda no primeiro login, uma reinicialização forçada no meio é retomada sem repetir etapas, e a limpeza remove tudo de 10.4. **Valida H3, H7.**

### M4 — Drivers
- Coletor de drivers (7.2) + exportação.
- Etapa de instalação com `pnputil /add-driver <dir>\*.inf /subdirs /install` (código de saída; nunca o texto).
- **Pronto quando (hardware real):** rede funciona no primeiro login sem intervenção, com os drivers vindos do pendrive.

### M5 — Aplicativos
- Inventário (7.1) + classificação + `winget export`.
- `winget download` para o pendrive.
- Detecção de tipo de instalador (13.3) + `installer_signatures.yaml`.
- Primeiras entradas de `app_catalog.yaml` (os apps que o usuário mais usa).
- Etapas: instalador offline (Fase 1 e 2), winget online (Fase 2), portátil.
- Espera do winget (11.5), códigos de reinício, `kill_processes`, `disable_autostart`.
- **Pronto quando (hardware real):** os apps escolhidos estão instalados após o primeiro login, com apps de máquina já presentes antes do login. **Valida H5.**

### M6 — Backups
- VSS (7.4.2) + limpeza de órfãs.
- Captura com robocopy para pasta crua (7.4.3) + exclusões + avisos DPAPI (7.4.6).
- Sugestões de pastas (7.3) a partir do catálogo.
- Restauração Fase 1 (perfil Default) e Fase 2 (perfil real, `{ABS}`), com `merge`/`overwrite`/`skip`.
- Arquivos soltos (item 30).
- **Pronto quando (hardware real):** ao abrir pela primeira vez um app com backup, as configurações já estão lá; arquivos em uso na captura foram copiados. **Valida H4, H6, H8.**

### M7 — Bloatware e ajustes
- `bloatware.yaml` e `tweaks.yaml` completos para Windows 11 com `source`.
- Motor de operações (15.2) sobre `platform/registry.py`, `appx.py`, `powercfg`.
- Carga/descarga do hive Default (13.2).
- Bloqueio de reinstalação (13.5) e conteúdo do consumidor (14.1).
- **Pronto quando (hardware real):** os apps removidos não aparecem no menu Iniciar no primeiro login nem voltam após um ciclo de Windows Update; os ajustes estão ativos na conta nova.

### M8 — Windows Update, resumo e notificações
- Windows Update via API COM `Microsoft.Update.Session` (sem módulos de terceiros), com filtro de drivers.
- Política de reinício (11.5).
- `resumo.json`, tela de resumo (versão mínima em texto/HTML local até o M9), atalho na área de trabalho.
- **Pronto quando (hardware real):** instalação completa em modo silencioso, sem nenhuma janela além da notificação final, com resumo correto.

### M9 — Interface do Agente
- Janela da Fase 2 (12.2), contagem regressiva, modo interativo, `decide_at_runtime`.
- Bandeja + notificações (12.3).
- Tela de resumo em Qt (12.4), "tentar de novo".
- **Pronto quando (hardware real):** os três modos funcionam; mudar uma escolha na janela altera o que é feito.

### M10 — WinKit Studio (GUI)
- Telas: Pendrive → Windows e conta → Drivers → Apps → Backups → Bloatware → Ajustes → Modo de execução → Revisão e construção.
- Usa exatamente os mesmos serviços do CLI (nenhuma lógica nova na interface).
- **Pronto quando:** dá para fazer todo o fluxo sem editar JSON à mão.

### Depois do v1 (backlog ordenado)

> A v2 (M11–M18) está detalhada em [`PLANO_V2.md`](PLANO_V2.md) e **implementada** (0.9.0); falta a validação na VM (roteiros `docs/validacao/M11.md` a `M17.md`). Os itens 3 (backup de `HKCU`, agora em forma curada, D-037) e 4 (fixar na barra, V2-04) deste backlog foram absorvidos por ela.

1. Item 20 — Windows 10 (catálogos com `os: [10]`, validação em hardware).
2. Item 23 — Perfis múltiplos (o Ventoy mostra um menu com os modelos; um XML por perfil).
3. Item 15 — Backup de registro `HKCU`.
4. Item 29 — Fixar na barra de tarefas.
5. `parent` no `ventoy.json` (se H1 confirmar).
6. Assinatura de código.

---

## 21. Hipóteses a validar

| # | Hipótese | Se for falsa | Validada em |
|---|---|---|---|
| H1 | O `auto_install` do Ventoy aplica as etapas `windowsPE`, `specialize` e `oobeSystem` do nosso XML numa ISO original. Saber também se a chave `parent` funciona na versão atual do Ventoy | Bloqueante para D-002: teríamos que reconsiderar injetar o XML na ISO | M2 |
| H2 | A partição de dados do Ventoy está visível com letra de unidade na etapa *specialize* e no `SetupComplete.cmd` | Copiar o Agente na etapa *windowsPE* (onde o pendrive certamente está visível) para `C:` | M2 |
| H3 | O `SetupComplete.cmd` executa quando a instalação usa a chave genérica, mesmo em PC com chave OEM no firmware | O fallback (10.3) já cobre: tudo vai para a Fase 2 | M3 |
| H4 | O `SetupComplete.cmd` roda **antes** de o perfil do usuário ser criado a partir do Default, então o que gravamos no Default chega à conta nova | Retargetar backups e ajustes `user` para a Fase 2 (perfil real) | M6 |
| H5 | O winget fica disponível na sessão do usuário em até ~10 min após o primeiro login numa instalação limpa | Priorizar `winget download` (offline) para todos os apps possíveis | M5 |
| H6 | `robocopy` lê de uma cópia de sombra através de um link simbólico de diretório | Copiar com Python (`\\?\GLOBALROOT\...`) | M6 |
| H7 | O Agente PyInstaller roda como SYSTEM no `SetupComplete.cmd` sem bloqueio do Defender | Ajustes de empacotamento; em último caso, Fase 1 em PowerShell | M3 |
| H8 | O desempenho de leitura de milhares de arquivos pequenos em exFAT via USB é aceitável | Revisar D-005 (ZIP) com o usuário | M6 |
| H9 | PowerShell funciona na etapa *specialize* | Bootstrap em `cmd` puro | M2 |
| H11 | O valor `Administrators` no elemento `Group` da conta local funciona num Windows em pt-BR (onde o grupo se chama "Administradores") | O Agente (Fase 1) adiciona a conta ao grupo pelo SID `S-1-5-32-544` | M2 |
| H10 | O instalador do Windows enxerga o SSD do usuário sem driver extra | Fora do escopo do WinKit (exigiria modificar a ISO); documentar como carregar driver manualmente na tela do instalador | M2 |

---

## 22. Riscos

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Mudanças do Windows 11 (novas versões) quebram ajustes ou nomes de pacotes | Alta | Médio | Dados versionados com `min_build`/`max_build`; ajustes falham isolados (P4) |
| Microsoft endurecer o OOBE contra conta local | Média | Alto | `LocalAccounts` no XML é o mecanismo oficial de implantação; acompanhar a cada versão |
| Instaladores mudam switches ou abrem janelas mesmo silenciosos | Alta | Baixo | Catálogo + `kill_processes`; falha isolada + resumo |
| Antivírus marca o Agente | Média | Médio | onedir, sem ofuscação; assinatura de código depois |
| Ventoy mudar o formato do `auto_install` | Baixa | Alto | Testes de snapshot + validação a cada versão do Ventoy |
| Desenvolvimento sem acesso direto a Windows real | Certa | Médio | CI `windows-latest` + roteiros de validação em hardware por marco |
| Código 100% escrito por IA, sem auditoria humana completa, publicado como código aberto | Certa | Alto | Aviso de isenção no README, no `NOTICE`, no `LEIA-ME.txt` do pacote e na primeira página do Studio; licença Apache-2.0 (sem garantias, seções 7 e 8); pedido de relato de erros por issues (D-028) |

---

## 23. Documentos vivos

| Documento | Conteúdo | Atualizado quando |
|---|---|---|
| `PLANO.md` | Produto, desenho, marcos | Escopo ou comportamento muda |
| `ARQUITETURA.md` | Camadas, regras de código, registro de decisões (D-xxx) | Arquitetura, dependência ou regra muda |
| `STATUS.md` | Estado de cada item de cada marco; hipóteses validadas | Todo item começado, concluído ou bloqueado |
| `DIVIDAS_TECNICAS.md` | Tudo que está provisório, incompleto ou conscientemente simplificado | Toda vez que algo é feito "por enquanto" |
| `INCIDENTES.md` | O que deu errado: causa raiz, impacto, correção, prevenção | Toda falha relevante, hipótese falsa ou teste real falho |
| `CHANGELOG.md` | Mapa de **todas** as mudanças e implementações, por data e marco | **Todo commit** |

Regra: código e documentos mudam **no mesmo commit** (ver `CLAUDE.md`).

---

## 24. Rastreabilidade: função → marco

| Função | Marco | | Função | Marco |
|---|---|---|---|---|
| 1 Ler ISO | M2 | | 21 Updates | M8 |
| 2 autounattend | M2 | | 24 Detectar Ventoy | M2 |
| 3 Apps silenciosos | M5 | | 25 Estimativa de espaço | M5 (apps) / M6 (backups) |
| 6 Drivers + pnputil | M4 | | 26 Log no pendrive | M3 |
| 7 Exportar drivers | M4 | | 27 Sincronização incremental | M1 (diff) + M5 |
| 8 Listar apps | M5 | | 28 Sugestão de pastas | M6 |
| 9 winget | M5 | | 30 Arquivos soltos | M6 |
| 10 Ordem | M1 (planejador) + M5 | | 31 Privacidade | M7 |
| 11 Bloatware | M7 | | 32 Visual | M7 |
| 12 Captura | M6 | | 33 Nome do PC | M2 |
| 13 Restaurar no Default | M6 | | 34 Energia | M7 |
| 14 Restaurar no logon | M6 | | 35 Escolher na janela | M9 |
| 16 Avisos DPAPI | M6 | | 36 Resumo | M8 + M9 |
| 17 Receita | M1 | | 37 Bloquear reinstalação | M7 |
| 19 Ventoy nativo | M2 | | Modos de execução | M3 (silencioso) + M9 |

Funções da v2: a tabela por código e marco está em [`PLANO_V2.md`](PLANO_V2.md) §1 e, resumida, no fim da §3.1 acima. O item 15 virou V2-06 (valores curados) e o 29 virou V2-04.

---

## 25. Glossário

| Termo | Significado |
|---|---|
| **Ventoy** | Ferramenta que permite dar boot em várias ISOs de um mesmo pendrive |
| **`auto_install`** | Plugin do Ventoy que injeta um arquivo de respostas na instalação do Windows sem alterar a ISO |
| **`autounattend.xml`** | Arquivo de respostas que automatiza o instalador do Windows |
| **Etapa (pass)** | Fase do instalador do Windows: `windowsPE`, `specialize`, `oobeSystem` |
| **OOBE** | Telas de configuração inicial do Windows (idioma, conta, privacidade) |
| **`SetupComplete.cmd`** | Script que o Windows roda como SYSTEM ao final da instalação, antes do login |
| **Perfil Default** | `C:\Users\Default`: molde copiado para toda conta nova |
| **Hive** | Arquivo do registro (`NTUSER.DAT` é o `HKCU` de um perfil) |
| **VSS** | Serviço de Cópias de Sombra do Windows: instantâneo de um volume que permite ler arquivos em uso |
| **DPAPI** | Criptografia do Windows atrelada à conta/máquina; dados protegidos com ela não funcionam em outra máquina |
| **Provisionado** | App que o Windows instala em toda conta nova |
| **winget** | Gerenciador de pacotes oficial do Windows |
| **Receita** | `receita.json`: tudo o que o Agente deve fazer |
| **Payload** | Tudo o que está em `WinKit\` no pendrive |
| **Molde de caminho** | Caminho com variáveis (`{APPDATA}\discord`) resolvido na máquina de destino |
