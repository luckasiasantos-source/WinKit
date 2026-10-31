# WinKit v2 — Plano de implementação (M11 a M18)

> **Estado deste documento:** **aprovado pelo dono do projeto em 2026-10-31**; em implementação (ver `STATUS.md`).
> Quando aprovado, ele vira documento vivo como o `PLANO.md`: muda no mesmo commit que mudar o código (`CLAUDE.md`).
>
> **Relação com os outros documentos:** o `PLANO.md` continua descrevendo a v1 (M0–M10), que está implementada. Este arquivo descreve **só o que é novo**. Onde a v2 muda algo da v1, a seção diz explicitamente "muda o PLANO.md §x". As decisões propostas aqui (D-030 em diante) e as mudanças de regra (§4) só entram no `ARQUITETURA.md` no primeiro commit do M11, depois da aprovação.
>
> **Aviso que continua valendo:** o projeto é pré-alpha, pessoal e 100% vibe-codado (D-028). Cada marco termina com um roteiro de validação em VM, executado pelo dono.

## Sumário

0. [Como ler](#0-como-ler)
1. [Escopo: os 24 itens da v2](#1-escopo-os-24-itens-da-v2)
2. [Princípios que não mudam](#2-princípios-que-não-mudam)
3. [Decisões propostas (D-030 a D-042)](#3-decisões-propostas-d-030-a-d-042)
4. [Mudanças nas regras do código](#4-mudanças-nas-regras-do-código)
5. [Arquitetura transversal](#5-arquitetura-transversal)
6. [M11 — Inglês e espanhol](#6-m11--inglês-e-espanhol)
7. [M12 — Aplicar neste PC e ponto de restauração](#7-m12--aplicar-neste-pc-e-ponto-de-restauração)
8. [M13 — Pendrive comum (Rufus e ferramenta da Microsoft)](#8-m13--pendrive-comum-rufus-e-ferramenta-da-microsoft)
9. [M14 — Rede e sistema](#9-m14--rede-e-sistema)
10. [M15 — Personalização](#10-m15--personalização)
11. [M16 — Contas, pastas e jogos](#11-m16--contas-pastas-e-jogos)
12. [M17 — Inteligência do pendrive](#12-m17--inteligência-do-pendrive)
13. [M18 — Fechamento da v2](#13-m18--fechamento-da-v2)
14. [Hipóteses novas (H12 a H35)](#14-hipóteses-novas-h12-a-h35)
15. [Riscos novos](#15-riscos-novos)
16. [Dívidas técnicas já previstas](#16-dívidas-técnicas-já-previstas)
17. [Estratégia de testes da v2](#17-estratégia-de-testes-da-v2)
18. [Ordem, dependências e versões](#18-ordem-dependências-e-versões)
19. [Rastreabilidade: item → marco → arquivos](#19-rastreabilidade-item--marco--arquivos)
20. [Checklists obrigatórios (commit e marco)](#20-checklists-obrigatórios-commit-e-marco)
21. [O que depende do dono do projeto](#21-o-que-depende-do-dono-do-projeto)

---

## 0. Como ler

- Cada função nova tem um código **V2-nn**, que segue a numeração das listas sugeridas na conversa: V2-01 a V2-10 vêm da primeira lista, V2-11 a V2-20 da segunda, V2-21 a V2-23 dos três extras, e V2-00 é a tradução.
- Toda função é descrita sempre nos mesmos blocos, nesta ordem:
  1. **Objetivo**: o que a pessoa ganha.
  2. **Como se usa**: telas do Studio e comandos da CLI.
  3. **Dados**: campos novos na receita, catálogos YAML e arquivos no pendrive.
  4. **Captura**: o que o Coletor lê no PC antigo.
  5. **Construtor**: o que vai para o pendrive.
  6. **Planejador**: em que fase cai e por qual regra (R16 em diante, continuando o §11.2 do `PLANO.md`).
  7. **Etapa do Agente**: `check()`, `run()`, desfazer, e o comportamento no modo "aplicar neste PC" (V2-03).
  8. **Plataforma**: o mecanismo do Windows usado, **sempre sem ler texto localizado** (R-13).
  9. **Segurança**: dados sensíveis, o que nunca vai para log, o que nunca é feito.
  10. **Textos**: chaves de i18n nos três idiomas.
  11. **Testes**: o que é testado e como.
  12. **Validação na VM**: o que o dono confere.
  13. **Hipóteses, riscos e dívidas**: o que ainda não sabemos.
  14. **Arquivos**: novos e alterados.
  15. **Pronto quando**: critério objetivo de conclusão.
- "Fase 1" e "Fase 2" seguem o `PLANO.md` §11.1. "Modo ao vivo" é o novo modo do V2-03 (aplicar num Windows já instalado).
- Nada aqui adiciona dependência nova de produção (R-43, R-44). Tudo que precisar de parser (VDF da Steam, tabela `name` de fontes, UserAssist) é escrito no `core` e testado no Linux.

---

## 1. Escopo: os 24 itens da v2

| Código | Função | Marco | Tamanho |
|---|---|---|---|
| V2-00 | Interface em **inglês e espanhol** (além do português) | M11 | G |
| V2-01 | **Pendrive comum**: Rufus ou Ferramenta de Criação de Mídia, sem Ventoy | M13 | M |
| V2-02 | **Redes Wi-Fi** levadas do PC antigo e conectadas antes do login | M14 | P |
| V2-03 | **Aplicar neste PC**: rodar a receita num Windows já instalado | M12 | G |
| V2-04 | **Menu Iniciar e barra de tarefas** fixados | M15 | M |
| V2-05 | **Apps padrão** (navegador, PDF, player…) | M15 | P |
| V2-06 | **Aparência pessoal** (papel de parede, cor de destaque, cursor, mouse) | M15 | P |
| V2-07 | **Fontes** instaladas pelo usuário | M15 | P |
| V2-08 | **Recursos do Windows** (WSL, Sandbox, Hyper-V, .NET 3.5, OpenSSH) | M14 | P |
| V2-09 | **Diagnóstico de drivers**: dispositivos sem driver e busca no Windows Update | M14 | P |
| V2-10 | **Ponto de restauração "Windows pronto"** | M12 | P |
| V2-11 | **Contas extras** (família, convidado) | M16 | M |
| V2-12 | **Navegadores prontos** (extensões, página inicial, buscador) | M15 | M |
| V2-13 | **Jogos sem baixar de novo** (Steam e Epic) | M16 | M |
| V2-14 | **Pastas do usuário em outro disco** (Documentos, Downloads…) | M16 | M |
| V2-15 | **Modo gamer** e outros perfis rápidos | M15 | P |
| V2-16 | **Privacidade de rede**: DNS seguro e bloqueio no `hosts` | M14 | P |
| V2-17 | **Unidades de rede** mapeadas | M14 | P |
| V2-18 | **Tarefas de manutenção** (atualizar apps, Sensor de Armazenamento) | M14 | P |
| V2-19 | **Relatório antes/depois** (PC antigo × novo) | M17 | M |
| V2-20 | **Assistente "o que levar"** | M17 | G |
| V2-21 | **Atualizar os instaladores** guardados no pendrive | M17 | M |
| V2-22 | **Variáveis de ambiente e PATH** | M14 | P |
| V2-23 | **Receitas compartilháveis** e modelos prontos | M17 | M |

Tamanho: **P** = uma etapa e uma tela simples; **M** = captura, etapa e tela com escolhas; **G** = mexe em várias camadas ou cria um modo novo.

### 1.1 Fora do escopo da v2 (explicitamente)

- **Embutir ou automatizar o Rufus.** O Rufus não tem linha de comando completa, formata o pendrive inteiro (contraria P3/D-017) e é GPL. O WinKit só **reconhece** um pendrive já gravado por ele (V2-01, D-034).
- **Trocar a letra de unidade, particionar ou formatar** qualquer disco, mesmo para as pastas do usuário (V2-14) e os jogos (V2-13). Volumes são achados pelo número de série (D-035).
- **Contas Microsoft ou de domínio** nas contas extras (V2-11). Só contas locais.
- **Senhas, cookies e tokens** de navegadores (V2-12). Continuam fora (DPAPI, `PLANO.md` §3.2).
- **Lojas de jogos além de Steam e Epic** com reconexão automática (V2-13). As outras ganham só a lista de pastas e a instrução de "localizar jogo".
- **Backup bruto do `HKCU`** (antigo item 15). A v2 leva só valores curados de um catálogo (D-037).
- **Revisão das traduções por falantes nativos.** As traduções são feitas por IA e ficam registradas como dívida (DT prevista §16).

---

## 2. Princípios que não mudam

Todos os princípios e regras da v1 continuam valendo (`PLANO.md` §1.3 e `ARQUITETURA.md` §5). Os que mais pesam na v2:

| Princípio / regra | Como a v2 respeita |
|---|---|
| **A ISO nunca é modificada** (D-002) | No V2-01 o WinKit grava só `autounattend.xml` na raiz e a pasta `WinKit\`; nunca toca em `sources\`, `boot\` ou `efi\`. A ISO do Ventoy só é **montada como leitura** para o .NET 3.5 offline (V2-08) |
| **Nada pesado na ISO** (D-001) | Tudo que é novo (Wi-Fi, fontes, papel de parede, inventário, manifestos de jogos) vai em `WinKit\Perfis\<perfil>\` |
| **Nunca particionar ou formatar** (P3, D-017, R-18) | V2-14 e V2-13 só **apontam** para pastas que já existem em volumes achados pelo número de série; nunca mudam letra nem criam partição |
| **Restauração aditiva** (D-007, R-21) | PATH, fontes, extensões, bibliotecas da Steam, redes Wi-Fi e unidades de rede são **acrescentados**; nada é apagado no destino. No modo ao vivo isso é ainda mais importante |
| **`core` puro** (camadas) | Parsers novos (VDF, fontes, UserAssist), comparação antes/depois, exportação de receita compartilhável e prévia do modo ao vivo ficam no `core` |
| **Sem `shell=True`, tudo pelo `runner`** (R-11) | Comandos novos (`netsh`, `dism`, `vssadmin` não; CIM sim) passam por `platform.runner`/`platform.powershell` com lista de argumentos |
| **Nunca ler texto localizado** (R-13) | Cada função lista o mecanismo não localizado: XML do `netsh wlan export`, XML do DISM, CIM, registro, JSON, arquivos `.lnk` lidos por COM, códigos de saída |
| **Dados mudam, código não** (R-32) | Listas novas em YAML: provedores de DNS, listas de bloqueio, extensões, recursos, valores pessoais curados, perfis rápidos, variáveis protegidas |
| **Operações tipadas** (R-34) | Ajustes ganham só operações novas tipadas (`capability_add`, `storage_sense`…); continua não existindo "comando arbitrário" |
| **Documentos vivos** (R-49) | Cada commit atualiza `CHANGELOG.md` e os documentos afetados (§20) |

---

## 3. Decisões propostas (D-030 a D-042)

Entram no `ARQUITETURA.md` §6 no primeiro commit do M11, com estado "aceita". Se o dono discordar de alguma, ela muda antes de começar.

### D-030 — Interface em três idiomas, com o português como base
**Contexto:** o projeto será público e o dono quer inglês e espanhol.
**Decisão:**
- Os idiomas suportados são `pt-BR` (base), `en-US` e `es` (espanhol neutro latino-americano, tratamento por "tú").
- As mensagens ficam em `winkit/i18n/messages/{pt_br,en_us,es}.py`, uma por idioma, com **exatamente as mesmas chaves e os mesmos marcadores `{nome}`**. Um teste garante isso.
- Os textos dos catálogos YAML (títulos, descrições, nomes) continuam em português no YAML e ganham **arquivos de tradução** em `winkit/i18n/catalogs/{en_us,es}.yaml`, chaveados por `<catálogo>.<id>.<campo>`.
- O idioma de cada componente é escolhido assim:
  - **Studio:** preferência salva; senão, idioma de exibição do Windows.
  - **CLI:** `--idioma`, depois a variável `WINKIT_LANG`, depois o idioma do Windows.
  - **Agente:** campo `execution.language` da receita (`auto` = idioma do Windows novo).
**Consequências:** R-03 e D-018 mudam (§4). Toda string de interface que hoje está solta no código (Studio, janela do Agente, CLI, motivos de etapa) vai para os arquivos de mensagens.

### D-031 — Mensagens estruturadas atravessam as camadas, não texto pronto
**Contexto:** hoje o estado (`estado.json`), os motivos de etapa e o resumo guardam texto em português pronto. Num Windows em inglês, o resumo sairia misturado.
**Decisão:**
- Novo tipo `Msg(key: str, params: dict[str, str | int | float])` no `core`.
- `StepResult`, `StepState.error/reason`, `SummaryItem` e `ExcludedItem.reason` passam a guardar `Msg` e não texto.
- O texto só é montado na borda: interface, log legível e HTML do resumo.
- O `estado.json` sobe para `schema_version: 2`, com migração e teste (R-47). Textos antigos viram `Msg("legacy.text", {"text": ...})`.
**Consequências:** o resumo e a janela podem trocar de idioma sem reprocessar nada; o `eventos.jsonl` fica neutro de idioma.

### D-032 — Nomes de comando da CLI continuam em português, com apelidos em inglês
**Decisão:** `winkit receita nova`, `winkit construir` etc. ficam como estão (scripts existentes não quebram). Cada comando ganha um apelido em inglês (`recipe new`, `build`, `collect`…) via `aliases` do `argparse`. Ajuda e saída seguem o idioma escolhido. Não haverá apelidos em espanhol (a manutenção triplicaria; a ajuda em espanhol já explica os comandos).

### D-033 — Modo "aplicar neste PC" com prévia e ponto de restauração antes
**Contexto:** V2-03. Rodar a receita num Windows em uso pode mudar coisas que a pessoa não espera.
**Decisão:**
- Novo comando do Agente, `winkit-agent apply`, chamado pelo Studio (botão "Aplicar neste PC") ou pela CLI (`winkit aplicar`).
- Antes de qualquer mudança, sempre:
  1. **Prévia** (simulação): cada etapa diz "já está feito", "vai mudar" ou "não se aplica aqui", sem efeito colateral.
  2. **Ponto de restauração** (V2-10), ligado por padrão. Desligá-lo exige confirmação explícita.
- Toda etapa declara se é segura no modo ao vivo (`live_safe`); as que não são ficam fora do plano, com o motivo.
- O estado de cada aplicação fica separado: `C:\ProgramData\WinKit\Aplicacoes\<data-hora>\`.
**Consequências:** o contrato de etapa ganha `live_safe` e `preview()` (§5.5). É também a forma mais rápida de testar etapas na VM, sem reinstalar o Windows.

### D-034 — Pendrive comum: só `autounattend.xml` na raiz e a pasta `WinKit\`
**Contexto:** V2-01.
**Decisão:**
- Um pendrive de instalação do Windows gravado pelo Rufus ou pela Ferramenta de Criação de Mídia é reconhecido pelos arquivos do instalador, sem a partição `VTOYEFI`.
- O Construtor só escreve `\autounattend.xml` e `\WinKit\`.
- Se já houver um `autounattend.xml` (o Rufus cria um quando se marcam as opções dele), ele é copiado uma única vez para `autounattend.xml.winkit-bak`, e o Studio avisa.
- O WinKit nunca embute nem chama o Rufus.
**Consequências:** R-19 ganha um segundo modo (§4). O pendrive passa a ter um "tipo" (`ventoy` ou `setup`) no `Target`.

### D-035 — Volumes identificados pelo número de série, nunca pela letra
**Contexto:** V2-13, V2-14 e V2-17 apontam para outros discos. Num Windows recém-instalado a letra pode mudar.
**Decisão:**
- Novo modelo `VolumeRef(serial: str, label: str | None, letter_hint: str | None, size: int)`.
- O número de série vem de `Win32_Volume.SerialNumber` (CIM), não de texto. No destino, o volume é achado pelo serial; a letra **atual** é usada para montar os caminhos.
- Se não achar o volume, a etapa é pulada com motivo claro. Nunca se troca letra de unidade.

### D-036 — Dados sensíveis novos ficam fora da receita
**Contexto:** senhas de Wi-Fi (V2-02) e senhas das contas extras (V2-11).
**Decisão:**
- Senhas de Wi-Fi ficam em arquivos próprios (`Perfis/<p>/Wifi/*.xml`), nunca na receita, nunca no log, nunca no `eventos.jsonl`.
- O `runner` mascara qualquer argumento que aponte para esses arquivos (R-23).
- O Studio mostra um aviso permanente de que o pendrive passa a carregar essas senhas, e oferece levar a rede **sem** a senha.
- As cópias temporárias no `C:` são apagadas na limpeza (`PLANO.md` §10.4).
**Consequências:** dívida prevista (as senhas ficam legíveis no pendrive, como a DT-006).

### D-037 — Configurações pessoais por catálogo curado de valores do registro
**Contexto:** V2-06 e V2-15 precisam levar valores do `HKCU` (cor, cursor, mouse).
**Decisão:**
- Novo catálogo `personal_settings.yaml`: grupos de valores (`HKCU\Control Panel\Mouse\MouseSensitivity`…) com tipo, faixa válida e fonte.
- O Coletor só lê o que está no catálogo; o Agente só grava o que está no catálogo.
- Nada de exportar e importar `.reg` bruto.
**Consequências:** fica conferível e seguro; cada versão do Windows pode filtrar valores (`windows:`).

### D-038 — Políticas de navegador em modo "recomendado"
**Decisão:**
- Página inicial e buscador usam as políticas da chave `...\Recommended` do Chrome e do Edge, que **podem ser mudadas** pelo usuário depois. Forçar é escolha explícita.
- Extensões entram pelo mecanismo de **extensão externa**, que o usuário pode remover depois; `ExtensionInstallForcelist`, que trava a extensão, só por escolha explícita.
- O Firefox usa `ExtensionSettings` com `normal_installed`.
- O Studio avisa que o navegador vai mostrar "gerenciado pela sua organização".

### D-039 — Campos novos da receita são aditivos; `schema_version` da receita continua 1
**Contexto:** R-47 exige migração para mudança incompatível.
**Decisão:**
- Todos os campos novos têm valor padrão que reproduz o comportamento da v1, então uma receita v1 continua válida sem migração.
- Como o Studio e o Agente gravados no mesmo pendrive têm sempre a mesma versão (R-46), não existe o caso "Agente antigo lendo receita nova".
- A receita só sobe para `schema_version: 2` se algum campo **mudar de significado**.
- O estado sobe para 2 por causa do D-031.

### D-040 — Perfis rápidos e receitas compartilháveis sem dados pessoais
**Decisão:**
- **Perfis rápidos** (`presets.yaml`: Gamer, Privacidade máxima, Escritório, Programador) são só listas de ids de ajustes, bloatware, recursos e energia. Aplicar um perfil é mesclar, nunca substituir.
- **Receita compartilhável** (`.winkit.json`) é um formato próprio, com `share_schema_version`, que por construção não tem:
  - conta, nome do PC, senhas, `pendrive_id`;
  - drivers;
  - backups com dados;
  - Wi-Fi, unidades de rede, valores de variáveis;
  - volumes;
  - instaladores offline.
  Apps entram só por id do catálogo ou do winget.
- Importar sempre mostra uma prévia, com o publicador de cada app.

### D-041 — Atualização dos instaladores por `winget download` e manifesto
**Contexto:** V2-21. O `winget show` não tem saída JSON, e ler o texto dele violaria R-13.
**Decisão:**
- Verificar uma atualização é baixar com `winget download --id <id> --exact` para uma pasta temporária e comparar a versão do **manifesto YAML** baixado (`core/winget_manifest.py`, já existe) com a guardada.
- Se o módulo PowerShell `Microsoft.WinGet.Client` estiver instalado, `Find-WinGetPackage` (objetos) é usado só para *verificar* sem baixar.
- O instalador antigo só é apagado depois de o novo estar no lugar e no manifesto (R-22).

### D-042 — Barra lateral do Studio agrupada e com busca
**Contexto:** de 10 para cerca de 26 seções.
**Decisão:**
- A barra lateral ganha grupos com título, no estilo do "Ajustes do Sistema" do macOS:
  - **Preparar:** Pendrive, Windows e conta, Contas extras, Modelos.
  - **O que levar:** Sugestões, Aplicativos, Configurações dos apps, Jogos, Drivers, Fontes, Aparência, Apps padrão, Iniciar e barra.
  - **Sistema:** Apps pré-instalados, Ajustes, Recursos do Windows, Pastas do usuário, Variáveis de ambiente, Energia e atualizações, Manutenção.
  - **Rede:** Wi-Fi, DNS e bloqueios, Unidades de rede, Navegadores.
  - **Concluir:** Primeiro login, Revisar e construir, Aplicar neste PC.
- Um campo de busca no topo filtra as seções pelo título e por palavras-chave.
- Preferências (idioma, tema) ficam num botão de engrenagem no rodapé.

---

## 4. Mudanças nas regras do código

Aplicadas no `ARQUITETURA.md` §5 no primeiro commit do M11.

| Regra | Hoje | Passa a ser |
|---|---|---|
| **R-03** | Texto ao usuário em pt-BR, só em `i18n/pt_br.py` | Texto ao usuário em **pt-BR, en-US e es**, só em `winkit/i18n/messages/*.py` e `winkit/i18n/catalogs/*.yaml`. Nenhuma string de interface solta no código. Exceção documentada: o log técnico do `bootstrap.ps1`, que fica em inglês simples (é lido em issues e não é interface) |
| **R-04** | Documentação em pt-BR | Igual. Únicas exceções: `README.en.md`, `README.es.md`, as notas da release e o `NOTICE` (trilíngue) |
| **R-19** | Construtor só escreve em `WinKit\` e `ventoy\script\winkit-*.xml`, e mescla `ventoy.json` | **Modo Ventoy:** igual. **Modo pendrive comum (D-034):** só escreve em `WinKit\`, `\autounattend.xml` e, uma vez, `\autounattend.xml.winkit-bak`. Qualquer outra escrita é bug (teste de proteção) |
| **D-018** | Identificadores em inglês, textos em pt-BR | Identificadores em inglês; textos nos três idiomas (D-030) |

Regras novas:

- **R-51** Toda chave de mensagem existe nos três idiomas, com os mesmos marcadores. Toda chave usada no código existe; toda chave existente é usada (com lista explícita de chaves dinâmicas). Tudo verificado por teste.
- **R-52** Volumes fora do disco do sistema são referenciados só por `VolumeRef` (D-035). É proibido gravar letra de unidade fixa na receita, salvo em `letter_hint`. Teste de proteção: nenhum campo da receita aceita `^[A-Z]:\\` fora de `{ABS:...}` e de `letter_hint`.
- **R-53** Arquivos com segredo (Wi-Fi, senhas) são declarados num registro único (`core/secrets.py`). O `runner`, o `EventLog` e o resumo mascaram qualquer caminho ou valor desse registro. Teste: simular uma etapa de Wi-Fi e conferir que nenhum log contém a senha da fixture.
- **R-54** Toda etapa declara `live_safe: bool` e implementa `preview()` sem efeito colateral. Teste: rodar `preview()` de todas as etapas com fakes que **falham em qualquer escrita**.
- **R-55** Strings de interface só aparecem dentro de `t(...)` ou `Msg(...)`. Um teste AST percorre `studio/ui`, `agent/ui`, `cli` e `ui` e falha se encontrar um literal de texto passado a `label`, `button`, `Row`, `section`, `setText`, `setWindowTitle`, `setToolTip`, `QMessageBox.*` ou `help=` do `argparse` (lista de exceções vazia por padrão).

---

## 5. Arquitetura transversal

O que muda para várias funções ao mesmo tempo. É feito **uma vez**, no marco em que aparece pela primeira vez, e reaproveitado depois.

### 5.1 Receita: campos novos (aditivos, D-039)

Esboço Pydantic (`core/recipe/models.py`). Todos com padrão que mantém o comportamento da v1. Em cada campo, o marco em que entra.

```python
Language = Literal["auto", "pt-BR", "en-US", "es"]

class Execution(_Model):            # existente
    ...
    language: Language = "auto"     # M11 — idioma do Agente e do resumo

class VolumeRef(_Model):            # M16 (D-035)
    serial: Annotated[str, Field(pattern=r"^[0-9A-F]{8}$")]
    label: str | None = None
    letter_hint: str | None = None  # só informativo
    size: int = 0

class ExtraAccount(_Model):         # M16 — V2-11
    username: Annotated[str, Field(min_length=1, max_length=20)]
    display_name: str | None = None
    group: Literal["administrators", "users"] = "users"
    password_mode: Literal["empty", "stored", "must_change"] = "must_change"
    password: str | None = Field(default=None, repr=False)

class WindowsSettings(_Model):      # existente
    ...
    extra_accounts: list[ExtraAccount] = []                  # M16
    optional_features: list[str] = []                        # M14 — V2-08 (ids de features.yaml)

class RestorePoint(_Model):         # M12 — V2-10
    enabled: bool = True
    max_disk_percent: Annotated[int, Field(ge=1, le=50)] = 5

class Wifi(_Model):                 # M14 — V2-02
    networks: list[WifiNetwork] = []   # id, ssid, security, include_key, file (Perfis/<p>/Wifi/...)

class Dns(_Model):                  # M14 — V2-16
    provider: str = "unchanged"     # id de dns_providers.yaml ou "custom"
    custom_servers: list[str] = []
    custom_doh_template: str | None = None
    require_doh: bool = False
    hosts_blocklists: list[str] = []   # ids de hosts_blocklists.yaml

class NetworkDrive(_Model):         # M14 — V2-17
    letter: Annotated[str, Field(pattern=r"^[D-Z]$")]
    remote_path: Annotated[str, Field(pattern=r"^\\\\[^\\]+\\.+")]
    label: str | None = None

class Maintenance(_Model):          # M14 — V2-18
    winget_upgrade: Literal["off", "weekly", "monthly"] = "off"
    storage_sense: bool = False
    ensure_defrag_schedule: bool = True

class EnvVar(_Model):               # M14 — V2-22
    name: str
    value: str                      # com %USERPROFILE% etc. (moldado na captura)
    scope: Literal["user", "machine"] = "user"
    kind: Literal["sz", "expand_sz"] = "expand_sz"

class EnvPathEntry(_Model):         # M14 — V2-22 (implementado assim: cada pasta com escopo e marca)
    value: str
    scope: Literal["user", "machine"] = "user"
    selected: bool = True

class Environment(_Model):          # M14 — V2-22
    variables: list[EnvVar] = []       # EnvVar também ganhou `selected`
    path_entries: list[EnvPathEntry] = []

class DefaultApps(_Model):          # M15 — V2-05 (implementado assim)
    enabled: bool = False
    associations_file: PayloadPath | None = None   # XML do DISM inteiro; filtrado na hora
    groups: list[str] = []          # ids de file_associations.yaml (navegador, pdf…)

class Personal(_Model):             # M15 — V2-06
    groups: list[str] = []          # ids de grupos de personal_settings.yaml
    values: dict[str, PersonalValue] = {}   # capturados (tipo + dado), chave = id do valor
    wallpaper_file: PayloadPath | None = None

class FontItem(_Model):             # M15 — V2-07
    id: ItemId
    family: str
    file: PayloadPath
    scope: Literal["machine", "user"] = "machine"
    selected: bool = True

class StartLayout(_Model):          # M15 — V2-04
    start_mode: Literal["unchanged", "copy_exact", "pins_list"] = "unchanged"
    start_pins: list[PinRef] = []
    taskbar_pins: list[PinRef] = []
    start_snapshot_file: PayloadPath | None = None   # start2.bin (copy_exact)

class BrowserSetup(_Model):         # M15 — V2-12
    browser: Literal["chrome", "edge", "firefox", "brave"]
    extensions: list[str] = []      # ids de extensions.yaml ou ids crus capturados
    extension_mode: Literal["suggest", "force"] = "suggest"
    homepage: str | None = None
    search_provider: str | None = None   # id de search_providers.yaml
    policy_mode: Literal["recommended", "mandatory"] = "recommended"

class UserFolders(_Model):          # M16 — V2-14 (implementado assim)
    enabled: bool = False
    volume: VolumeRef | None = None
    # pasta → caminho relativo ao volume, com %USERNAME% (ex.: Usuarios\%USERNAME%\Documentos);
    # a "pasta base" vira só um atalho da tela para montar esses caminhos
    folders: dict[Literal["desktop", "documents", "downloads", "pictures", "videos", "music"], str] = {}

class GameLibrary(_Model):          # M16 — V2-13 (implementado assim: um jogo da Epic por item)
    id: ItemId
    launcher: Literal["steam", "epic"]
    name: str
    volume: VolumeRef
    relative_path: str              # ex.: "SteamLibrary" ou "Epic Games\Fortnite" (sem letra, R-52)
    games: int = 0
    manifest: PayloadPath | None = None   # .item da Epic, copiado
    selected: bool = True

class Recipe(_Model):               # existente — seções novas
    ...
    restore_point: RestorePoint = RestorePoint()       # M12
    wifi: Wifi = Wifi()                                # M14
    dns: Dns = Dns()                                   # M14
    network_drives: list[NetworkDrive] = []            # M14
    maintenance: Maintenance = Maintenance()           # M14
    environment: Environment = Environment()           # M14
    default_apps: DefaultApps = DefaultApps()          # M15
    personal: Personal = Personal()                    # M15
    fonts: list[FontItem] = []                         # M15
    start_layout: StartLayout = StartLayout()          # M15
    browsers: list[BrowserSetup] = []                  # M15
    presets_applied: list[str] = []                    # M15 — só histórico/rótulo
    user_folders: UserFolders = UserFolders()          # M16
    game_libraries: list[GameLibrary] = []             # M16
    compare_after_install: bool = True                 # M17 — V2-19
```

Campos novos em modelos que já existem (também aditivos):

| Campo | Marco | Uso |
|---|---|---|
| `updates.fix_missing_drivers: bool = True` | M14 | V2-09: procurar no Windows Update os drivers que faltarem |
| `BackupItem.for_accounts: Literal["all", "main"] = "all"` | M16 | V2-11: backup só da conta principal |
| `BackupItem.on_conflict` (já existe) | — | Ganha uso no modo ao vivo (prévia destaca `overwrite`) |
| `EnvVar.on_conflict: Literal["skip", "replace"] = "skip"` | M14 | V2-22 |
| `meta.source_system_volume: str | None` | M16 | Serial do volume do sistema antigo (recusa levar o que está no `C:` antigo) |
| `AppItem.installer_version: str | None` | M17 | V2-21 |
| `meta.last_update_check: datetime | None` | M17 | V2-21 |
| `meta.dismissed_suggestions: list[str] = []` | M17 | V2-20 |

Regras de validação novas (`core/recipe/validation.py`), todas com mensagem em `Msg`:
- `extra_accounts`:
  - nomes únicos, sem repetir a conta principal, mesmas regras de nome da v1;
  - `stored` exige senha;
  - no modo silencioso, `must_change` é permitido.
- `network_drives`: letras únicas, que não colidam com `user_folders.volume.letter_hint`.
- `optional_features`, `dns.provider`, `hosts_blocklists`, `browsers[].extensions` (quando não são ids crus), `personal.groups` e `presets_applied` precisam existir nos catálogos.
- `user_folders.enabled` exige `volume` e pelo menos uma pasta.
- `game_libraries[].volume` não pode ser o volume do sistema (serial do volume em que estava o `C:` antigo, guardado na captura).
- `default_apps.enabled` exige `associations_file` e `selected`.
- `start_layout.start_mode = copy_exact` exige `start_snapshot_file` e a mesma versão principal de Windows de origem e destino (aviso, não erro).

### 5.2 Catálogos novos e alterados (`src/winkit/data/`)

| Arquivo | Marco | Conteúdo | Modelo novo em `core/catalog/models.py` |
|---|---|---|---|
| `features.yaml` | M14 | Recursos opcionais e capacidades: id, nome, tipo (`feature`/`capability`), nomes técnicos, edições permitidas, precisa de internet?, precisa reiniciar?, fonte | `WindowsFeature` |
| `dns_providers.yaml` | M14 | Cloudflare, Cloudflare for Families, Quad9, Google, AdGuard, NextDNS (com campo do id pessoal), IPv4/IPv6, modelo DoH, fonte | `DnsProvider` |
| `hosts_blocklists.yaml` | M14 | Listas pequenas e curadas (anúncios, rastreadores), **sem domínios da Microsoft** (ver §15), domínios em linha, fonte e licença | `HostsBlocklist` |
| `protected_env.yaml` | M14 | Variáveis que nunca são levadas (`SystemRoot`, `windir`, `PROCESSOR_*`, `NUMBER_OF_PROCESSORS`, `OS`, `ComSpec`, `PATHEXT`, `TEMP`/`TMP` de máquina, `DriverData`, `PSModulePath`…) | lista simples |
| `personal_settings.yaml` | M15 | Grupos (`accent`, `cursor`, `mouse`, `wallpaper_style`, `keyboard_repeat`): valores com chave, tipo, faixa ou lista permitida, `windows:`, fonte | `PersonalGroup`, `PersonalValueSpec` |
| `extensions.yaml` | M15 | Extensões conhecidas por navegador: id da loja, nome, categoria, fonte | `BrowserExtension` |
| `search_providers.yaml` | M15 | Google, Bing, DuckDuckGo, Brave Search, Ecosia: nome, URL de busca com `{searchTerms}`, sugestões | `SearchProvider` |
| `browsers.yaml` | M15 | Por navegador: raiz das políticas, chave de extensões externas, URL de atualização da loja, como detectar a instalação | `BrowserSpec` |
| `presets.yaml` | M15 | Perfis rápidos: id, nome, descrição, ajustes, bloatware, recursos, energia, valores pessoais | `Preset` |
| `file_associations.yaml` | M15 | Extensões e protocolos mais comuns, agrupados (Navegador, PDF, Vídeo, Música, Imagens, Compactados), para a tela de apps padrão | `AssociationGroup` |
| `game_saves.yaml` | M17 | Pastas de saves conhecidas (subconjunto curado), opcionalmente ampliado pelo manifesto do Ludusavi (§12.4) | `GameSaveEntry` |
| `tweaks.yaml` (alterado) | M14–M15 | Categoria nova `gaming`; ajustes de jogo (V2-15) e do Sensor de Armazenamento (V2-18) | `Tweak.category` ganha `gaming`, `maintenance` |
| `bloatware.yaml` (alterado) | M15 | Sem mudança de formato; perfis rápidos referenciam ids | — |
| `OsFilter` (alterado) | M14 | Campo novo `editions: list[Edition] | None` (Sandbox e Hyper-V exigem Pro ou superior) | `OsFilter.editions` |
| `TweakOp` (alterado) | M14 | Operações tipadas novas: `capability_add` (`{name}`), `capability_remove`; `optional_feature_enable` já existe | `CapabilityOp` |

Cada catálogo novo tem `source` em cada item (R-33, quando for ajuste) e um teste de carga que valida **todos** os itens (o padrão de `tests/core/test_catalogs.py`).

### 5.3 Layout do pendrive: pastas novas (muda o `PLANO.md` §5)

```
WinKit\
└── Perfis\<perfil>\
    ├── receita.json
    ├── Backups\...                       (v1)
    ├── Wifi\<id>.xml                     M14  ← XML do netsh; contém a senha se include_key (D-036)
    ├── Associacoes\padrao.xml            M15  ← XML do DISM, já filtrado
    ├── Aparencia\papel-de-parede.<ext>   M15
    ├── Fontes\<id>.<ttf|otf|ttc>         M15
    ├── Iniciar\start2.bin                M15  ← só no modo copy_exact
    ├── Jogos\<id>\*.item                 M16  ← manifestos da Epic
    ├── Navegadores\<navegador>.json      M15  ← extensões capturadas (só ids e nomes)
    └── Inventario\antes.json             M17  ← inventário do PC antigo (V2-19)
```

- `manifesto.json` passa a cobrir também `Perfis/<p>/Fontes` e `Perfis/<p>/Aparencia` (o Windows interpreta esses arquivos; um arquivo trocado seria problema). `Wifi`, `Associacoes` e `Inventario` são conferidos por **validação de formato** (XML/JSON bem-formados e com o esquema esperado) antes de usar, não por hash, porque o usuário pode editá-los, como os backups (D-005).
- `layout.py` ganha constantes e funções `wifi_dir(p)`, `fonts_dir(p)` etc.; nenhum caminho é montado à mão fora dele.
- No **modo pendrive comum** (V2-01), o layout de `WinKit\` é o mesmo. Muda só o que fica fora dele (§8).

### 5.4 Planejador: regras novas e ordem das fases (continua o `PLANO.md` §11.2)

Tipos de etapa novos (`StepKind`):

| Tipo | Função | Fase padrão | Destino |
|---|---|---|---|
| `restore_point` | V2-10 | 2, penúltima (antes do `finalize`) | machine |
| `wifi` | V2-02 | 1, logo depois dos drivers | machine |
| `feature` | V2-08 | 1 (sem internet) ou 2 (com internet) | machine |
| `driver_report` | V2-09 | 2, depois do Windows Update | machine |
| `dns` | V2-16 | 1, depois do Wi-Fi | machine |
| `hosts` | V2-16 | 1 | machine |
| `network_drive` | V2-17 | 1 (perfil Default) ou 2 | default/user profile |
| `maintenance` | V2-18 | 2 (tarefa do winget precisa do usuário) | machine/user |
| `env` | V2-22 | 1 (máquina e Default) ou 2 | machine/default/user |
| `default_apps` | V2-05 | 1 | machine (afeta perfis novos) |
| `personal` | V2-06 | 1 (Default) + reaplicação na Fase 2 | default/user profile |
| `font` | V2-07 | 1 | machine |
| `start_layout` | V2-04 | 1 (Default) | default profile |
| `browser` | V2-12 | 1 | machine |
| `account` | V2-11 | 1 (ajuste de grupo e senha; a criação é no XML) | machine |
| `user_folders` | V2-14 | 1 (Default), **antes** de backups e ajustes de usuário | default/user profile |
| `game_library` | V2-13 | 2, depois do app do launcher | machine/user |
| `compare` | V2-19 | 2, antes do `finalize` | machine |

Regras novas, aplicadas depois de R1–R15:

| # | Regra |
|---|---|
| R16 | `user_folders` vem antes de qualquer `backup` e `tweak` de usuário da mesma fase, porque os moldes `{DOCUMENTS}`, `{DESKTOP}`, `{DOWNLOADS}` passam a apontar para o volume escolhido |
| R17 | `wifi` vem logo depois de `driver` na Fase 1 (precisa do driver de rede) e antes de qualquer etapa com `needs_network` da Fase 2 |
| R18 | `dns` e `hosts` vêm depois de `wifi` |
| R19 | `feature` com `needs_network` (capacidades e .NET 3.5 sem fonte offline) → Fase 2; sem → Fase 1. Se exige reinício, `reboot_required` segue o `PLANO.md` §11.5 |
| R20 | `default_apps` e `start_layout` só na Fase 1 (precisam rodar antes de o perfil ser criado — H4, H25, H27, H28). No fallback (Fase 1 não rodou) e no modo ao vivo: `default_apps` vira `skipped` com a instrução de abrir "Aplicativos padrão"; `start_layout` usa o modo da Fase 2 (§10.4) |
| R21 | `browser` depende dos apps de navegador selecionados: se o navegador vem de app da receita, a etapa grava as políticas mesmo antes da instalação (o navegador as lê ao abrir), mas `depends_on` aponta para o app só para ordenar o resumo |
| R22 | `game_library` depende do `app:<launcher>` correspondente (Steam/Epic) e roda depois dele, com o launcher fechado (`kill_processes`) |
| R23 | `personal` aplica no Default na Fase 1 e, na Fase 2, **confere e reaplica** o papel de parede e a cor de destaque (o Windows 11 pode trocar o tema no primeiro login — H26) |
| R24 | `account` (ajuste de grupo e senha das contas extras) roda na Fase 1, logo no começo |
| R25 | `network_drive`: no Default (Fase 1) grava os valores de `HKCU\Network`; se `decide_at_runtime`, vai para a Fase 2 no `HKCU` real |
| R26 | `env` de escopo `machine` → Fase 1; `user` → Fase 1 no Default; no modo ao vivo → no `HKCU` real |
| R27 | `maintenance` → Fase 2 (a tarefa do winget roda como o usuário) |
| R28 | `driver_report` → depois de `windows_update` |
| R29 | `compare` → depois de `driver_report` e antes de `restore_point` |
| R30 | `restore_point` → última etapa antes do `finalize`, para que o ponto represente o "Windows pronto". No modo ao vivo, uma segunda etapa `restore_point:before` vem **antes de tudo** (D-033) |
| R31 | No **modo ao vivo**: as etapas `live_safe=False` vão para `excluded` com o motivo; `default_profile` vira `user_profile` (como no fallback); `rename_computer` só se a receita pedir e sempre como escolha na hora; `finalize` não apaga o Agente nem arquivos de instalação |
| R32 | `font`, `start_layout`, `personal` e `default_apps` exigem `windows.os` compatível com o catálogo (`OsFilter`), como os ajustes |
| R33 | Etapas novas com `decide_at_runtime` seguem R1/R2 (modo silencioso = sem pergunta) |

Ordem atualizada (substitui a tabela do `PLANO.md` §11.2):

```
FASE 1                                          FASE 2
 1. localizar pendrive + hashes                 1. trava de instância única + pendrive
 2. account (grupos e senhas das contas extras) 2. [fallback] pendentes da Fase 1
 3. drivers                                     3. janela/bandeja conforme o modo
 4. wifi                                        4. esperar área de trabalho e rede
 5. dns, hosts                                  5. personal (conferir e reaplicar)
 6. nome do PC, energia, políticas, features    6. backups restantes ({ABS}, na hora)
 7. bloatware + bloqueio de reinstalação        7. esperar winget
 8. user_folders (Default)                      8. apps
 9. ajustes de usuário, personal, env (Default) 9. backups pós-instalação (R13)
10. default_apps, start_layout, browser, font  10. game_library
11. network_drive (Default)                    11. ajustes decididos na hora, env/network (HKCU)
12. backups → Default                          12. features com internet
13. apps de máquina offline                    13. atalhos de portáteis, maintenance
14. backups pós-instalação (R13)               14. Windows Update
15. copiar logs                                15. driver_report
                                               16. compare
                                               17. restore_point
                                               18. finalize
```

Testes do planejador (`tests/core/test_planner_v2.py`): um caso por regra R16–R33, mais propriedades:
- determinismo (o mesmo plano duas vezes);
- toda etapa nova aparece numa só fase;
- `depends_on` sempre aponta para etapa anterior;
- no modo ao vivo nenhuma etapa tem destino `default_profile`.

### 5.5 Contrato de etapa: o que muda (muda o `ARQUITETURA.md` §4.1)

```python
class StepHandler(Protocol):
    live_safe: bool                                  # R-54

    def check(self, ctx: StepContext) -> bool: ...
    def run(self, ctx: StepContext) -> StepResult: ...
    def preview(self, ctx: StepContext) -> Preview:  # R-54, sem efeito colateral
        ...

@dataclass(frozen=True)
class Preview:
    status: Literal["already_done", "will_change", "not_applicable", "needs_choice"]
    changes: tuple[Msg, ...] = ()                    # "Valor X: 1 → 0", "Copiar 3 arquivos (12 MB)"
    warnings: tuple[Msg, ...] = ()
```

- `StepResult.message` vira `Msg | None` (D-031).
- `StepContext` ganha:
  - `mode: Literal["install", "live"]`;
  - `volumes: VolumeResolver` (D-035);
  - `secrets: SecretRegistry` (R-53).
- O padrão de `preview()` para as etapas da v1 é `already_done` se `check()`, senão `will_change` com uma `Msg` genérica. As etapas de backup ganham uma prévia real (lista de arquivos que seriam copiados e de conflitos que seriam pulados, por `robocopy /L`, que só lista, com o resultado lido do **código de saída e da contagem de arquivos do relatório JSON da cópia em Python**, nunca do texto do robocopy).

### 5.6 Plataforma: módulos novos (com fakes)

Cada módulo segue o padrão da v1:
- um `Protocol` com a interface;
- uma implementação `Windows*`, que usa PowerShell com saída JSON, o registro ou CIM;
- um fake em `platform/fakes/`;
- fixtures reais em `tests/fixtures/` (R-40), capturadas na VM.

| Módulo | Marco | Interface (resumo) | Mecanismo |
|---|---|---|---|
| `platform/restore.py` | M12 | `enable(drive)`, `set_max_percent(n)`, `create(description) -> int`, `list() -> list[RestorePointInfo]` | CIM `root\default:SystemRestore` (`Enable`, `CreateRestorePoint`), `Win32_ShadowStorage.MaxSpace`, registro `SystemRestorePointCreationFrequency` |
| `platform/media.py` | M13 | `list_setup_drives()`, `read_setup_image(root)` | `Get-Volume`/`Get-Partition`/`Get-Disk` em JSON (já usado em `disks.py`); `Get-WindowsImage -ImagePath <root>\sources\install.wim|esd` |
| `platform/wifi.py` | M14 | `export_profiles(dest) -> list[Path]`, `add_profile(xml_path)`, `profile_exists(ssid)` | `netsh wlan export profile key=clear folder=<dest>` (só o **código de saída** e os **arquivos XML** gerados); `netsh wlan add profile filename=<x> user=all`; existência pelo registro `HKLM\SOFTWARE\Microsoft\Wlansvc\Profiles` não é estável → por `netsh wlan export profile name=<ssid> folder=<tmp>` e checar o arquivo |
| `platform/features.py` (ampliado) | M14 | `add_capability(name)`, `capability_state(name)`, `enable_feature(name, source=None)` | `Get/Add-WindowsCapability -Online` (objetos → JSON), `Enable-WindowsOptionalFeature -Source -LimitAccess` |
| `platform/devices.py` | M14 | `problem_devices() -> list[DeviceProblem]` | CIM `Win32_PnPEntity` com `ConfigManagerErrorCode <> 0`: `PNPDeviceID`, `Name` (só exibido, nunca interpretado), `ConfigManagerErrorCode`, `HardwareID` |
| `platform/windows_update.py` (ampliado) | M14 | `search_drivers(hardware_ids)` | COM `Microsoft.Update.Session`, critério `IsInstalled=0 and Type='Driver'`, filtro por `DriverHardwareID` |
| `platform/dns.py` | M14 | `physical_adapters()`, `set_servers(index, servers)`, `add_doh(server, template)`, `set_doh_policy(level)` | `Get-NetAdapter -Physical`, `Set-DnsClientServerAddress`, `Add-DnsClientDohServerAddress` (Windows 11), registro `HKLM\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient\DoHPolicy` |
| `platform/hosts.py` | M14 | `read_block()`, `write_block(lines)`, `remove_block()` | arquivo `%SystemRoot%\System32\drivers\etc\hosts`, bloco entre `# >>> WinKit` e `# <<< WinKit`, gravação atômica, preserva codificação e o resto do arquivo |
| `platform/netdrives.py` | M14 | `list_mapped()`, `map(letter, path)`, `write_persistent(hive_root, letter, path)` | registro `HKCU\Network\<letra>`; mapeamento ao vivo por COM `WScript.Network.MapNetworkDrive(letter, path, True)` |
| `platform/scheduler.py` (ampliado) | M14 | `ensure_task(TaskSpec)`, `remove_task(path, name)` | os mesmos cmdlets `ScheduledTasks` da Fase 2 |
| `platform/environment.py` (ampliado) | M14 | `read_vars(scope)`, `set_var(scope, name, value, kind)`, `broadcast_change()` | registro `HKCU\Environment` e `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment`; `SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment")` via `ctypes` |
| `platform/associations.py` | M15 | `export(dest)`, `import_(xml)`, `current_progid(ext)` | `dism.exe /Online /Export-DefaultAppAssociations:<f>` e `/Import-DefaultAppAssociations:<f>` (código de saída + XML); `HKCU\...\FileExts\<ext>\UserChoice\ProgId` |
| `platform/personal.py` | M15 | `read_values(specs)`, `write_values(values, hive_root)`, `apply_wallpaper_live(path)` | registro; `SystemParametersInfoW(SPI_SETDESKWALLPAPER)` via `ctypes` no modo ao vivo e na Fase 2 |
| `platform/fonts.py` | M15 | `list_user_installed(since)`, `install_machine(file, face_name)`, `installed(face_name)` | registro `HKLM`/`HKCU\...\Fonts`, data de instalação do Windows (`HKLM\...\CurrentVersion\InstallDate`), cópia para `%SystemRoot%\Fonts`, `AddFontResourceW` + `WM_FONTCHANGE` no modo ao vivo |
| `platform/shell_links.py` | M15 | `read_link(path) -> LinkInfo` | COM `WScript.Shell.CreateShortcut(path)`: `TargetPath`, `Arguments`, `WorkingDirectory` (dados, não texto localizado) |
| `platform/browsers.py` | M15 | `installed()`, `chromium_extensions(profile_dir)`, `firefox_extensions(profile_dir)`, `write_policies(spec, values)` | registro (políticas e extensões externas), JSON `Preferences`/`Secure Preferences`, `extensions.json` do Firefox, `distribution\policies.json` |
| `platform/accounts.py` (ampliado) | M16 | `ensure_group_member(user, sid)`, `set_must_change(user)`, `exists(user)` | `Add-LocalGroupMember -SID`, ADSI `WinNT://./<user>` (`PasswordExpired=1`) |
| `platform/volumes.py` | M16 | `list_volumes() -> list[VolumeInfo]`, `find(ref) -> VolumeInfo | None` | CIM `Win32_Volume` (`SerialNumber`, `DriveLetter`, `Label`, `Capacity`, `SystemVolume`) |
| `platform/known_folders.py` (ampliado) | M16 | `redirect(folder, path, hive_root)` | registro `...\Explorer\User Shell Folders` (REG_EXPAND_SZ) com os GUIDs/nomes de valor oficiais |
| `platform/games.py` | M16 | `steam_root()`, `steam_libraries()`, `epic_manifests()` | registro `HKCU\Software\Valve\Steam\SteamPath`; `libraryfolders.vdf` (parser no `core`); `C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests\*.item` (JSON) |
| `platform/usage.py` | M17 | `userassist_entries()` | registro `HKCU\...\Explorer\UserAssist\{GUID}\Count` (valores binários, decodificados no `core`) |

`platform/services.py` (`Services`) e `agent/services.py` (`AgentServices`) ganham os campos novos. `fake_services()` e `fake_agent_services()` montam todos os fakes.

### 5.7 Resolver de volumes (D-035)

- `core/volumes.py`:
  - `VolumeRef`;
  - `resolve(ref, volumes) -> ResolvedVolume | None`, função pura: casa pelo serial e, para desempatar, pelo tamanho;
  - `retarget(path_on_old_pc, ref, resolved) -> str`: troca a letra antiga pela atual.
- Molde de caminho novo: `{VOL:<serial>}\resto` (análogo a `{ABS:...}`).
  - `templates.parse` aceita o molde novo, e `resolve` precisa de um `VolumeResolver` no contexto.
  - Testes no estilo do IN-009, usando seriais inventados e pastas temporárias, nunca `C:`/`D:` reais.
- Teste de proteção (R-52): nenhum molde da receita contém letra fixa fora de `{ABS:` e `letter_hint`.

### 5.8 Segredos (D-036, R-53)

- `core/secrets.py` define:
  - `SecretRegistry`, com caminhos e valores sensíveis registrados em tempo de execução;
  - `mask(text) -> text`.
- `platform/runner.py`: os argumentos que contêm um caminho do registro de segredos viram `***` no log de comando.
- O `EventLog` passa toda mensagem por `mask`.
- Teste de proteção `test_wifi_password_never_logged`: a fixture tem a senha `senha-de-teste-123`; depois de capturar, construir e rodar as etapas com fakes, nenhum arquivo em `Logs/` nem o `estado.json` contém essa senha.

### 5.9 Studio: estrutura nova (D-042)

- `studio/ui/window.py`:
  - `SECTIONS` vira `GROUPS: list[SectionGroup]`, cada grupo com título (chave de i18n) e seções (`title_key`, ícone, cor, classe da página, palavras-chave);
  - a barra lateral desenha os títulos de grupo como rótulos pequenos em cinza, como no macOS;
  - campo de busca no topo (`QLineEdit` com ícone), que filtra as seções em tempo real pelo título traduzido e pelas palavras-chave traduzidas;
  - rodapé com a engrenagem de **Preferências**: idioma (Automático, Português, English, Español) e tema (Automático, Claro, Escuro).
- `studio/ui/pages.py` (1110 linhas) é dividido num pacote `studio/ui/pages/`, um módulo por grupo (`prepare.py`, `bring.py`, `system.py`, `network.py`, `finish.py`), para não passar de ~400 linhas por arquivo.
- `studio/controller.py` ganha os métodos de cada função, sempre sem Qt (R-36), testados em `tests/studio/test_controller*.py`.
- `tests/ui/test_studio_ui.py` passa a percorrer `GROUPS` em vez de `SECTIONS`: toda página abre nos três idiomas, sem receita e com receita.

### 5.10 CLI: comandos novos (resumo; detalhe em cada função)

| Comando | Apelido (D-032) | Marco |
|---|---|---|
| `winkit aplicar [--simular] [--sem-ponto-de-restauracao]` | `apply` | M12 |
| `winkit pendrive listar` (passa a mostrar o tipo) | `drive list` | M13 |
| `winkit coletar wifi`, `wifi listar/marcar/desmarcar [--sem-senha]` | `collect wifi`, `wifi …` | M14 |
| `winkit recursos listar/marcar/desmarcar` | `features …` | M14 |
| `winkit dns definir <provedor>`, `winkit dns bloqueios marcar/desmarcar` | `dns …` | M14 |
| `winkit coletar unidades`, `winkit unidades listar/remover` | `collect drives`, `drives …` | M14 |
| `winkit manutencao definir --winget semanal --sensor` | `maintenance set` | M14 |
| `winkit coletar variaveis`, `winkit variaveis listar/marcar/desmarcar` | `collect env`, `env …` | M14 |
| `winkit coletar associacoes`, `winkit associacoes marcar/desmarcar` | `collect defaults`, `defaults …` | M15 |
| `winkit coletar aparencia`, `winkit aparencia grupos marcar/desmarcar` | `collect look`, `look …` | M15 |
| `winkit coletar fontes`, `winkit fontes listar/marcar/desmarcar` | `collect fonts`, `fonts …` | M15 |
| `winkit coletar iniciar [--modo exato|lista]` | `collect start` | M15 |
| `winkit coletar navegadores`, `winkit navegador definir <nav> …` | `collect browsers`, `browser set` | M15 |
| `winkit perfil-rapido listar/aplicar <id>` | `preset list/apply` | M15 |
| `winkit contas adicionar/remover/listar` | `accounts …` | M16 |
| `winkit pastas definir --volume <serial|letra> --pastas …` | `folders set` | M16 |
| `winkit coletar jogos`, `winkit jogos listar/marcar/desmarcar` | `collect games`, `games …` | M16 |
| `winkit apps atualizar [--verificar]` | `apps update` | M17 |
| `winkit receita exportar <arquivo>`, `winkit receita importar <arquivo> [--aplicar]` | `recipe export/import` | M17 |
| `winkit coletar inventario` | `collect inventory` | M17 |
| `winkit sugestoes` | `suggest` | M17 |

O `cli/main.py` (699 linhas) é dividido num pacote `cli/commands/`, um módulo por grupo de comandos, mantendo `cli/main.py` só com o `argparse` e o despacho.

### 5.11 Resumo (`core/summary.py`): seções novas

- **Dispositivos sem driver** (V2-09): nome exibido, código do problema traduzido por **tabela** de códigos (`ConfigManagerErrorCode` → `Msg`), e se o Windows Update encontrou um driver.
- **Comparação com o PC antigo** (V2-19): apps que faltaram, backups não restaurados, dispositivos sem driver que tinham driver no PC antigo.
- **O que fazer agora**: lista de ações manuais geradas pelas etapas, por exemplo:
  - "Abra Aplicativos padrão e escolha o leitor de PDF" (V2-05);
  - "Entre na Steam e confira a biblioteca" (V2-13);
  - "Defina a senha das contas extras" (V2-11).
- O HTML ganha `lang` conforme o idioma e passa a usar `Msg` em todos os itens (D-031).

### 5.12 Estado do Agente: `schema_version` 2 (D-031)

- `StepState.error` e `StepState.reason` passam de `str` para `Msg`.
- `core/state/migrations.py`, novo, faz a migração 1 → 2 (texto vira `Msg("legacy.text", {"text": ...})`), com teste a partir de um `estado.json` real da v1 (fixture).
- `AgentState.mode: Literal["install", "live"]` entra com padrão `install`.

### 5.13 Empacotamento e CI

- `packaging/smoke.ps1` ganha, a cada marco, a verificação do comando novo:
  - `winkit aplicar --simular --raiz` com a receita de exemplo (M12);
  - receita com Wi-Fi de fixture (M14);
  - e assim por diante.
- O CI continua com Linux e Windows. Testes que tocam o Windows real (`@pytest.mark.windows`) são só de leitura, ou escrevem só em `HKCU\Software\WinKitTest` e em pastas temporárias. **Nunca** mudam DNS, hosts, recursos, pontos de restauração ou contas no runner.
- O workflow de release (`release.yml`) não muda; cada marco termina com uma versão (§18).

---

## 6. M11 — Inglês e espanhol

**Código:** V2-00 · **Tamanho:** G · **Versão ao concluir:** `0.2.0` · **Depende de:** nada (é o primeiro marco da v2, para que todas as funções novas já nasçam traduzidas).

### 6.1 Objetivo

O Studio, a CLI, a janela do Agente, as notificações, o resumo e o README em **português, inglês e espanhol**, escolhidos automaticamente pelo idioma do Windows e trocáveis a qualquer momento.

### 6.2 Inventário do que precisa ser traduzido

Levantamento feito no código atual (base para as tarefas do §6.4):

| Origem | Onde está hoje | Volume aproximado | Destino |
|---|---|---|---|
| Mensagens centrais | `i18n/pt_br.py` (194 linhas, ~120 chaves) | já chaveado | `i18n/messages/pt_br.py` + tradução |
| Chamadas `t(...)` | 279 chamadas no código | já chaveado | sem mudança de chamada |
| Studio | `studio/ui/pages.py` (1110 linhas), `window.py`, `base.py` | ~250 textos **soltos** | extrair para chaves `studio.*` |
| Janela do Agente | `agent/ui/qt.py` (557 linhas) | ~60 textos soltos | extrair para chaves `agent.ui.*` |
| CLI | `cli/main.py` (699 linhas): `help=`, `description=`, saídas `print` | ~150 textos | extrair para `cli.*` |
| Motivos de etapa | `agent/steps/*.py` (8 arquivos): `StepResult.skipped/failed(f"...")` | ~45 textos | `Msg("step.*")` (D-031) |
| Resumo HTML | `core/summary.py` (176 linhas) | ~30 textos | chaves `summary.*` |
| Catálogos | `tweaks.yaml`, `bloatware.yaml`, `driver_classes.yaml`, `dpapi_patterns.yaml`, `editions.yaml`, `app_catalog.yaml` (nomes de app ficam como estão) | ~300 campos | `i18n/catalogs/{en_us,es}.yaml` |
| Aviso de isenção | `studio/ui/pages.py` (`DISCLAIMER`), `NOTICE`, `LEIA-ME.txt`, notas da release | 4 lugares | chave `disclaimer.*` + arquivos trilíngues |
| Documentação pública | `README.md`, `NOTICE`, `packaging/LEIA-ME.txt`, `packaging/NOTAS_DA_VERSAO.md` | 4 arquivos | `README.en.md`, `README.es.md`, `LEIA-ME`/`README` no pacote, notas trilíngues |
| XML de instalação | `core/unattend/generator.py`: `Description` da conta ("Conta local criada pelo WinKit") | 1 texto | chave `unattend.account_description`, no idioma da receita |
| Log legível do Agente | `agente.log` | segue o `EventLog` | idioma do Agente; o `eventos.jsonl` guarda a chave e os parâmetros |
| `bootstrap.ps1` | log técnico | ~10 linhas | inglês simples (exceção da R-03, §4) |

Ficam **fora** da tradução (documentado):
- documentos internos em `docs/`, que seguem em pt-BR (R-04);
- nomes de aplicativos e pacotes;
- identificadores técnicos (ids, chaves de registro);
- nomes dos comandos da CLI (D-032).

### 6.3 Desenho técnico

#### 6.3.1 Módulo `winkit/i18n/`

```
winkit/i18n/
├── __init__.py          t(), tn(), set_language(), current_language(), Msg render
├── languages.py         SUPPORTED = ("pt-BR", "en-US", "es"); normalize(tag) -> Language
├── messages/
│   ├── __init__.py
│   ├── pt_br.py         MESSAGES: dict[str, str | Plural]   (base, fonte da verdade)
│   ├── en_us.py
│   └── es.py
├── catalogs/
│   ├── en_us.yaml       tweaks.<id>.title: ..., bloatware.<id>.name: ...
│   └── es.yaml
└── format.py            format_size, format_duration, format_datetime, format_count por idioma
```

- `t(key, **params)`:
  - procura no idioma atual;
  - se faltar no idioma atual, usa o pt-BR e registra um aviso no log, uma vez por chave (não deveria acontecer, porque R-51 é testada);
  - chave inexistente em pt-BR continua sendo `KeyError` (erro de programação).
- `tn(key, n, **params)`: plural simples com as formas `one` e `other`, suficientes para pt, en e es. Exemplo: `"apps.count": Plural(one="{n} aplicativo", other="{n} aplicativos")`.
- `Msg` (D-031) mora em `core/text.py`, que é puro, e é renderizado por `i18n.render(msg)`.
  - Por que o `core` não chama `t()` direto: hoje chama em alguns pontos (planejador, validação). Isso continua permitido, porque o `i18n` é puro e não depende de plataforma. Mas onde o texto precisa **sobreviver** a uma troca de idioma (estado, resumo, prévia), passa a ser `Msg`.
- `set_language(lang)`:
  - estado global do processo, protegido por lock;
  - chamado uma vez na inicialização de cada executável, e na troca de idioma do Studio (que reconstrói as páginas).
- `languages.normalize`:
  - `pt-*` → `pt-BR` (Portugal recebe o português do Brasil; registrado como limitação);
  - `es-*` → `es`;
  - `en-*` → `en-US`;
  - qualquer outro → `en-US`.
- `format.py`, sem usar o módulo `locale` do Python (que depende do sistema):
  - separador decimal `,` em pt/es e `.` em en;
  - unidades `KB/MB/GB` iguais nos três;
  - data `dd/mm/aaaa` em pt/es e `mm/dd/yyyy` em en, mais `HH:MM`;
  - duração na forma curta "1 h 5 min", igual nos três idiomas.

#### 6.3.2 Detecção do idioma (`platform/locale.py`, novo)

- `ui_language() -> str`: `GetUserDefaultUILanguage()` (LANGID) via `ctypes`, convertido com `LCIDToLocaleName` para a tag BCP-47 (`pt-BR`, `en-US`, `es-MX`…). É API, não texto.
- `regional_defaults() -> RegionalDefaults`, para pré-preencher a receita nova com os valores do PC atual em vez de valores fixos do Brasil, tudo pelo registro:
  - **formatos:** `HKCU\Control Panel\International\LocaleName`;
  - **teclado:** `HKCU\Keyboard Layout\Preload\1` (KLID) e `Substitutes`, convertidos para o formato `0416:00010416` do XML;
  - **fuso:** `HKLM\SYSTEM\CurrentControlSet\Control\TimeZoneInformation\TimeZoneKeyName`.
- No Linux (testes e CI): `WINKIT_LANG`, senão `pt-BR`.
- Fake: `FakeLocale(ui="en-US", regional=...)`.

Isso **muda o `PLANO.md` §9.5**: `user_locale`, `system_locale`, `input_locale` e `time_zone` deixam de nascer fixos em pt-BR/Brasília; nascem do PC atual (continuam editáveis no Studio).

#### 6.3.3 Escolha do idioma por componente

| Componente | Ordem de escolha | Onde fica salvo |
|---|---|---|
| Studio | Preferência do usuário → idioma do Windows | `%APPDATA%\WinKit\studio.json` (`{"language": "auto"}`), gravação atômica (R-16) |
| CLI | `--idioma` (opção global nova) → `WINKIT_LANG` → idioma do Windows | não salva |
| Agente | `recipe.execution.language` → se `auto`: idioma de exibição do Windows **novo** | na receita |
| Resumo HTML | o do Agente | — |
| `autounattend.xml` | o da receita (`execution.language`; `auto` → idioma do Studio no momento da construção) | — |

#### 6.3.4 Catálogos traduzidos

- *(Implementado em `src/winkit/data/i18n_en_us.yaml` e `i18n_es.yaml`, YAML aninhado por catálogo e id — os ids de bloatware têm ponto, e a pasta `data/` já entra no executável empacotado.)* Formato originalmente planejado, com chaves planas:
  ```yaml
  tweaks.privacy.telemetry_minimum.title: Minimum telemetry
  tweaks.privacy.telemetry_minimum.description: Sends Microsoft only the required diagnostic data.
  bloatware.Microsoft.BingNews.name: News
  bloatware.Microsoft.Copilot.side_effect: The Copilot assistant is removed; it can be reinstalled from the Microsoft Store.
  driver_classes.Net.label: Network
  dpapi_patterns.electron_token.what: login token
  editions.pro.name: Pro
  ```
- `core/catalog/localize.py` (puro): `localize(catalogs, overlay) -> Catalogs`, que devolve cópias congeladas com os campos traduzidos.
- `default_catalogs(lang)` carrega a base e aplica o overlay. O cache passa a ser por idioma.
- Testes:
  - **completude**: todo item traduzível de todo catálogo tem entrada nos dois overlays;
  - **órfãos**: nenhuma chave de overlay aponta para um id inexistente;
  - os ids de bloatware têm ponto (`Microsoft.BingNews`), então a chave é montada com o id inteiro entre o prefixo e o campo, e o parser divide pelo **primeiro** e **último** ponto conhecidos.

#### 6.3.5 Studio

- Troca de idioma em tempo de execução: `StudioWindow.set_language(lang)`, que:
  1. chama `i18n.set_language`;
  2. salva a preferência;
  3. **reconstrói** a barra lateral e a página atual (as páginas já têm `refresh()`; o título e o subtítulo passam a ser propriedades que leem `t()`);
  4. reaplica o tema.
- Atributos de classe `title_text`/`subtitle_text` viram `title_key`/`subtitle_key`.
- Textos longos (aviso de isenção, explicações) usam `QLabel` com quebra de linha; a largura mínima da janela é conferida nos três idiomas (inglês costuma ser mais curto e espanhol ~20% mais longo que o português).
- Atalho: o seletor de idioma também aparece na página **Pendrive** na primeira execução, junto com o aviso de isenção.

#### 6.3.6 Agente

- `run_phase2_with_ui` define o idioma antes de criar a janela.
- A Fase 1, sem janela, define o idioma só para o log legível.
- Notificações e bandeja usam `t()`.
- O `EventLog` grava no `eventos.jsonl` `{"key": ..., "params": ...}` e no `agente.log` o texto renderizado.

#### 6.3.7 CLI

- Opção global `--idioma {auto,pt-BR,en-US,es}`.
- O `argparse` é montado **depois** de definir o idioma. Para isso, um pré-parse de `--idioma` e de `WINKIT_LANG` acontece antes de montar o parser, para que `help=` já saia traduzido.
- Apelidos em inglês (D-032): `sub.add_parser("construir", aliases=["build"], ...)`.
- Saídas de tabela (`apps listar`, `plano`) com cabeçalhos traduzidos; formatos de tamanho e data por `i18n.format`.

#### 6.3.8 Documentação pública

- `README.md` (pt-BR) ganha no topo os links "English | Español".
- `README.en.md` e `README.es.md` têm o mesmo conteúdo, incluindo o aviso de isenção completo.
- `NOTICE` ganha a seção em espanhol (já tem pt e en).
- `packaging/LEIA-ME.txt` é complementado por `README.txt` (en) e `LEAME.txt` (es); `build.ps1` copia os três.
- `packaging/NOTAS_DA_VERSAO.md` fica trilíngue (três blocos, com o aviso em cada um).
- Capturas de tela em `docs/imagens/en/` e `docs/imagens/es/`, geradas pelo mesmo script offscreen de hoje.

### 6.4 Tarefas, em ordem de commit

Cada linha é um commit (ou poucos), sempre com `scripts/check.sh` verde e o `CHANGELOG.md` atualizado.

1. **Decisões e regras.**
   - `ARQUITETURA.md`: D-030, D-031, D-032, D-039, D-042 e mudanças da R-03, R-04, R-19 e D-018; R-51 a R-55 marcadas como "em vigor a partir do M11/M12…" conforme o marco.
   - `STATUS.md`: M11 🟨.
2. **Estrutura do `i18n`.**
   - Mover `pt_br.py` para `messages/`; criar `languages.py`, `format.py`, `Plural`, `tn()`, `set_language()` e o render de `Msg`.
   - Testes de paridade (R-51) já ligados, com `en_us.py`/`es.py` inicialmente cópias marcadas como "a traduzir"; o teste de "não traduzido" fica como `xfail` estrito até o passo 9.
3. **`Msg` no núcleo.**
   - `core/text.py` (`Msg`); `StepResult`, `ExcludedItem`, `SummaryItem` e `StepState` passam a usar `Msg`.
   - Estado `schema_version` 2 com migração e fixture da v1 (D-031, R-47).
4. **Motivos das etapas** (8 arquivos de `agent/steps/`): todo texto vira `Msg("step.<tipo>.<motivo>", ...)`.
5. **Extração do Studio.**
   - Dividir `pages.py` em pacote (§5.9) **sem mudar comportamento**, num commit separado e só de refatoração.
   - Em seguida, extrair os textos para `studio.*`.
6. **Extração da janela do Agente** (`agent/ui/qt.py`).
7. **Extração da CLI.** Extrair os textos, criar `--idioma` e os apelidos. *(Feito no M11 sem dividir `cli/main.py` em pacote: a divisão fica para quando os comandos novos do M12–M17 forem entrando, um módulo por grupo.)*
8. **Teste AST da R-55**, ligado depois dos passos 5 a 7, quando não sobrar texto solto.
9. **Traduções**:
   - `en_us.py`, `es.py`, `catalogs/en_us.yaml`, `catalogs/es.yaml`;
   - o `xfail` do passo 2 vira teste normal;
   - revisão de consistência de termos com o glossário do §6.6.
10. **Detecção do idioma e padrões regionais** (`platform/locale.py`, receita nova com valores do PC atual). Muda o `PLANO.md` §9.5.
11. **Troca de idioma no Studio** (Preferências, reconstrução das páginas, `studio.json`).
12. **Agente e resumo no idioma da receita** (`execution.language`, `lang` no HTML, notificações, testes por idioma).
13. **`autounattend.xml`**:
    - descrição da conta no idioma da receita;
    - snapshots novos `unattend_default_en.xml` e `unattend_default_es.xml` (R-42, com explicação no commit).
14. **Documentação pública trilíngue** (READMEs, NOTICE, LEIA-ME, notas da release, `build.ps1`).
15. **Capturas de tela** nos três idiomas e conferência visual (claro e escuro).
16. **Roteiro de validação** `docs/validacao/M11.md`, `STATUS.md` (M11 ✅ código), release `0.2.0`.

### 6.5 Testes

| Teste | O que garante |
|---|---|
| `tests/i18n/test_parity.py` | Mesmas chaves e mesmos marcadores `{x}` nos três idiomas; formas `one`/`other` presentes em todo `Plural` (R-51) |
| `tests/i18n/test_usage.py` | Toda chave literal em `t("...")`, `tn("...")` e `Msg("...")` no código existe; toda chave existente é usada, com exceção de uma lista explícita de prefixos dinâmicos (`step.`, `summary.status.`) |
| `tests/i18n/test_no_untranslated.py` | Nenhum valor em `en_us`/`es` é idêntico ao pt-BR, exceto uma lista de exceções (nomes próprios, "WinKit", "Wi-Fi", "OK") |
| `tests/i18n/test_format.py` | Tamanhos, datas, durações e plurais nos três idiomas |
| `tests/i18n/test_languages.py` | `normalize` de `pt-PT`, `es-MX`, `es-ES`, `en-GB`, `fr-FR` (→ en-US), vazio e inválido |
| `tests/core/test_catalog_localize.py` | Completude e órfãos dos overlays; os catálogos traduzidos continuam validando os modelos |
| `tests/test_architecture.py` (R-55) | Teste AST: nenhum literal de texto em chamadas de interface |
| `tests/core/test_state_migration.py` | Estado v1 real → v2; v2 lê e grava sem perda |
| `tests/ui/test_studio_ui.py` | Toda página abre nos três idiomas, com e sem receita; a troca de idioma reconstrói a barra lateral; o aviso de isenção aparece traduzido |
| `tests/ui/test_agent_ui.py` | A janela do Agente nos três idiomas (contagem regressiva, escolhas, progresso, concluído) |
| `tests/cli/test_cli_i18n.py` | `--idioma en-US` traduz a ajuda e as saídas; os apelidos funcionam; `WINKIT_LANG` é respeitado |
| `tests/core/test_summary.py` | O resumo HTML em cada idioma, com `lang` correto |
| `tests/core/test_unattend.py` | Snapshots pt/en/es; `check_safety` continua passando |
| `tests/platform/test_locale.py` | Mapeamento LANGID → tag com fake; marcado `windows` para ler o idioma real (só leitura) |

### 6.6 Glossário de tradução (fixo, para consistência)

| pt-BR | en-US | es |
|---|---|---|
| pendrive | USB drive | memoria USB |
| receita | recipe | receta |
| perfil (do WinKit) | profile | perfil |
| primeiro login | first sign-in | primer inicio de sesión |
| ajustes | tweaks | ajustes |
| apps pré-instalados | preinstalled apps | aplicaciones preinstaladas |
| configurações dos apps | app settings | configuración de las aplicaciones |
| construir (o pendrive) | build | preparar |
| cópia de sombra | shadow copy | instantánea de volumen |
| decidir na hora | decide later | decidir en el momento |
| modo silencioso / contagem regressiva / interativo | silent / countdown / interactive | silencioso / cuenta regresiva / interactivo |
| ponto de restauração | restore point | punto de restauración |
| aplicar neste PC | apply to this PC | aplicar en este PC |
| pré-alpha, vibe-codado | pre-alpha, vibe-coded | pre-alfa, hecho con vibe coding |

### 6.7 Validação na VM (`docs/validacao/M11.md`)

1. Windows 11 em **inglês** na VM: abrir o Studio. Deve abrir em inglês, com teclado, formatos e fuso pré-preenchidos com os da VM.
2. Trocar para espanhol em Preferências: toda a janela muda, sem textos cortados (conferir as 26 seções).
3. Construir o pendrive com `execution.language = auto` e instalar uma ISO em espanhol: a janela da Fase 2, as notificações e o resumo saem em espanhol.
4. Mesma receita com ISO em português: tudo em português.
5. `winkit --idioma en-US --help` e `winkit build --help`.
6. Conferir o `eventos.jsonl` (chaves, não texto) e o `agente.log` (texto no idioma).

### 6.8 Hipóteses, riscos e dívidas

- **H12:** `GetUserDefaultUILanguage` devolve o idioma do pacote de idioma ativo também na Fase 1 (como SYSTEM). Se falso, a Fase 1 usa o idioma do sistema (`GetSystemDefaultUILanguage`), o que só afeta o log.
- **Risco:** textos maiores em espanhol cortados em botões. Mitigação: botões com tamanho pelo conteúdo e teste visual por idioma.
- **Dívida prevista:** traduções feitas por IA, sem revisão nativa (§16).

### 6.9 Arquivos

- **Novos:**
  - `i18n/languages.py`, `i18n/format.py`, `i18n/messages/{__init__,pt_br,en_us,es}.py`, `i18n/catalogs/{en_us,es}.yaml`;
  - `core/catalog/localize.py`, `core/state/migrations.py`, `platform/locale.py`;
  - os pacotes `studio/ui/pages/*.py` e `cli/commands/*.py`;
  - `README.en.md`, `README.es.md`, `packaging/README.txt`, `packaging/LEAME.txt`;
  - os testes listados no §6.5;
  - `docs/validacao/M11.md`.
- **Alterados:**
  - `i18n/__init__.py`, `core/text.py`, `core/summary.py`, `core/planner/*`, `core/state/models.py`, `core/recipe/models.py` (`execution.language`), `core/unattend/generator.py`, `core/catalog/loader.py`;
  - `agent/steps/*.py`, `agent/eventlog.py`, `agent/main.py`, `agent/ui/qt.py`;
  - `studio/main.py`, `studio/ui/window.py`, `studio/ui/base.py`, `studio/controller.py`;
  - `cli/main.py`, `collector/*` (mensagens), `builder/*` (mensagens);
  - `README.md`, `NOTICE`, `packaging/LEIA-ME.txt`, `packaging/NOTAS_DA_VERSAO.md`, `packaging/build.ps1`;
  - os documentos vivos.

### 6.10 Pronto quando

- Os testes do §6.5 passam no Linux e no Windows, e o teste AST (R-55) não tem exceções.
- O Studio, a CLI, o Agente e o resumo funcionam nos três idiomas, com troca no Studio sem reiniciar.
- READMEs, NOTICE, LEIA-ME e notas da release estão nos três idiomas.
- Existe o roteiro `M11.md`, a release `0.2.0` está publicada e os documentos vivos estão atualizados.

---

## 7. M12 — Aplicar neste PC e ponto de restauração

**Códigos:** V2-03, V2-10 · **Versão ao concluir:** `0.3.0` · **Depende de:** M11 (Msg, textos).

Por que juntos e logo no começo:
- o modo ao vivo **exige** o ponto de restauração antes de mexer (D-033);
- o modo ao vivo é a forma mais rápida de validar todas as etapas dos marcos seguintes na VM, **sem reinstalar o Windows a cada teste**.

### 7.1 V2-10 — Ponto de restauração "Windows pronto"

**Objetivo.** No fim da instalação, criar um ponto de restauração chamado "WinKit — Windows pronto (data)". Se algo quebrar depois (um driver, um app), dá para voltar ao Windows recém-configurado. No modo ao vivo, cria também um ponto **antes** de aplicar.

**Como se usa.**
- **Studio:** em "Energia e atualizações", um cartão "Ponto de restauração" com uma chave (ligada por padrão) e o espaço máximo (padrão 5% do disco).
- **CLI:** `winkit receita definir ponto-de-restauracao --ligado --espaco 5`.

**Dados.** `recipe.restore_point` (`enabled`, `max_disk_percent`). Sem catálogo e sem arquivo no pendrive.

**Planejador.**
- Instalação: etapa `restore_point:ready` (R30), penúltima da Fase 2.
- Modo ao vivo: também `restore_point:before`, a primeira etapa.

**Etapa do Agente** (`agent/steps/restore.py`, `RestorePointStep`, `live_safe=True`):
- `check()`: já existe um ponto com a mesma descrição criada pelo WinKit nesta execução? (Guardado no estado com o `SequenceNumber` devolvido.)
- `run()`:
  1. ligar a proteção do sistema no volume do Windows (`SystemRestore.Enable("C:\")`, com a letra do volume do sistema obtida de `%SystemDrive%`, nunca fixa);
  2. definir `Win32_ShadowStorage.MaxSpace` = `max_disk_percent` do volume;
  3. gravar `SystemRestorePointCreationFrequency=0` (o Windows recusa um segundo ponto em 24 h sem isso) e **restaurar o valor anterior** no fim;
  4. `SystemRestore.CreateRestorePoint(descricao, 12 /*MODIFY_SETTINGS*/, 100 /*BEGIN_SYSTEM_CHANGE*/)`;
  5. conferir pela lista de pontos (`SystemRestore` em CIM), que tem número de sequência e data, não texto.
- Falhas tratadas:
  - proteção desativada por política (`HKLM\SOFTWARE\Policies\Microsoft\Windows NT\SystemRestore\DisableSR=1`): `skipped` com motivo;
  - código de retorno do CIM diferente de 0: `failed` recuperável.
- `preview()`: "Criar ponto de restauração; reservar até X GB".

**Plataforma.** `platform/restore.py` (§5.6), todo por CIM no PowerShell com saída JSON. Fake: `FakeRestore`, com lista em memória e falha configurável.

**Segurança.** Não apaga pontos existentes. Só aumenta o espaço máximo, nunca reduz (reduzir apagaria pontos antigos): se o valor atual for maior, mantém.

**Textos:** `restore.title`, `restore.description`, `step.restore.created`, `step.restore.disabled_by_policy`, `summary.restore_point`.

**Testes.**
- Unidade: a etapa com fake (cria, já existe, política bloqueia, falha do CIM).
- Frequência restaurada mesmo em erro (`try/finally`, R-17).
- Planejador R30.
- `@windows`: só `list()`, só leitura.

**Validação na VM.** Depois da instalação, "Criar um ponto de restauração" → "Restauração do Sistema" mostra o ponto "WinKit — Windows pronto"; a proteção está ativa no `C:` com 5%.

**Hipóteses.** H13: `CreateRestorePoint` funciona na sessão do usuário elevada na Fase 2, logo depois do Windows Update (o serviço `VSS` e o `srservice` estão prontos).

**Arquivos:**
- novos: `platform/restore.py`, `platform/fakes/restore.py`, `agent/steps/restore.py`, os testes;
- alterados: `core/recipe/models.py`, `core/planner/*`, `agent/steps/registry.py`, `studio/ui/pages/system.py`, `cli/commands/recipe.py`, `core/summary.py`.

**Pronto quando:** o ponto é criado no fim da instalação e antes do modo ao vivo, os testes passam e o roteiro está escrito.

### 7.2 V2-03 — Aplicar neste PC (modo ao vivo)

**Objetivo.** Rodar a receita (ou parte dela) num Windows **já instalado**, sem formatar: instalar os apps que faltam, aplicar ajustes, remover bloatware, restaurar configurações, ligar recursos. Serve para:
- quem não quer reinstalar;
- arrumar um PC de outra pessoa;
- testar o WinKit na VM sem reinstalar a cada vez.

**Como se usa.**
- **Studio:** seção nova **"Aplicar neste PC"** (grupo Concluir). Fluxo em três passos:
  1. **Escolher o que aplicar.** Lista por categoria (Apps, Configurações, Ajustes, Apps pré-instalados, Recursos…), com tudo da receita marcado e caixas para desmarcar. Avisos fixos:
     - "Isto muda o Windows que você está usando agora";
     - "Feche os apps cujas configurações serão restauradas".
  2. **Prévia.** O Studio roda `winkit-agent apply --simular` em segundo plano e mostra, por etapa, "já está assim", "vai mudar" (com os detalhes de `Preview.changes`) ou "não se aplica aqui" (com o motivo). Nenhuma mudança é feita nesse passo.
  3. **Aplicar.** Botão principal "Criar ponto de restauração e aplicar". A janela do Agente abre no modo interativo, com progresso. No fim, o resumo.
- **CLI:**
  - `winkit aplicar --pendrive E: [--perfil padrao] [--simular] [--somente apps,ajustes] [--sem-ponto-de-restauracao]`;
  - `--sem-ponto-de-restauracao` exige também `--sei-o-que-estou-fazendo` (proteção contra uso acidental, D-033).
- **Pelo pendrive, em outro PC:** o Agente também roda direto dele: `E:\WinKit\Agent\winkit-agent\winkit-agent.exe apply`.

**Dados.**
- Sem campos novos obrigatórios na receita. Opções da execução (o que aplicar, sem ponto) vão por argumento.
- **Origem do conteúdo:** o pendrive (pelo marcador, R-31) ou uma pasta local que contenha `WinKit\` (o Studio usa a raiz que já tem aberta).

**Planejador** (`PlanContext` ganha `mode: Literal["install", "live"]` e `only_kinds: frozenset[StepKind] | None`):
- R31: exclui `live_safe=False` com motivo; `default_profile` → `user_profile`; `finalize` em versão "ao vivo".
- R30: `restore_point:before` antes de tudo (se não houver `--sem-ponto…`).
- O que muda por tipo:

| Tipo | No modo ao vivo |
|---|---|
| `driver` | Igual (`pnputil /add-driver /install`), seguro |
| `app` | Igual; `check()` já detecta o app instalado e pula |
| `backup` | Igual, em `merge` (nunca sobrescreve, R-21); a prévia lista o que seria copiado e os conflitos que seriam pulados. Se `on_conflict=overwrite` estiver na receita, a prévia avisa em destaque e o passo 1 pede confirmação item a item |
| `tweak` | Aplicado no `HKCU` real e no `HKLM`; os ajustes de usuário valem já no próximo login (alguns na hora, como o tema) |
| `bloat` | Remove para o usuário atual e desprovisiona (já é o comportamento da Fase 2) |
| `power` | Igual |
| `rename_computer` | Só se marcado no passo 1; sempre pergunta; exige reinício |
| `windows_update` | Igual (opcional no passo 1) |
| `finalize` | Gera o resumo; **não** apaga o Agente, não mexe em `Panther`, não remove a tarefa da Fase 2 (que não existe aqui) |
| Etapas novas da v2 | Cada uma declara o seu comportamento ao vivo nas seções seguintes |

**Etapa e executor.**
- Novo comando em `agent/main.py`: `apply [--root <pasta>] [--perfil <id>] [--simular] [--somente <tipos>] [--sem-ponto-de-restauracao]`.
- `agent/phases.py` ganha `run_live(rt, options)`:
  1. carrega a receita e o manifesto;
  2. confere os hashes (R-22);
  3. monta o plano com `mode="live"`;
  4. cria o estado em `C:\ProgramData\WinKit\Aplicacoes\<AAAA-MM-DD_HH-MM-SS>\estado.json`;
  5. executa com o mesmo executor da Fase 2;
  6. grava o resumo em `...\Aplicacoes\<...>\resumo.html` e o abre;
  7. copia os logs para `WinKit\Logs\<pc>_<data>_aplicar\`.
- `--simular`: monta o plano e chama `preview()` de cada etapa (R-54), gravando `previa.json` (lista de `Preview` serializada com `Msg`). O Studio lê esse JSON. **Teste de proteção:** em modo simulação, os fakes de plataforma falham em qualquer escrita.
- Instância única: a mesma trava da Fase 2 (não deixa rodar "aplicar" e "Fase 2" ao mesmo tempo).
- *(Implementado de outro jeito no M12:)* o Studio e a CLI rodam o motor do Agente (`agent/live.py`) **no próprio processo**, numa thread de fundo (`TaskRunner`), com os mesmos serviços reais. Motivo: o Studio já roda como administrador e assim não depende de achar o executável do Agente. A ideia original (processo separado com `progresso.jsonl`) fica registrada como dívida (DT-018). O comando `winkit-agent apply` continua existindo para rodar direto do pendrive, sem o Studio.

**Plataforma.** Nada novo além do `restore.py`. O `runner` ganha `start_detached(args)` para o Studio iniciar o Agente e acompanhar o processo.

**Segurança.**
- Ponto de restauração antes (D-033).
- `merge` sempre por padrão.
- Prévia obrigatória no Studio: o botão "Aplicar" só fica ativo depois da prévia.
- Bloatware marcado como `caution` aparece destacado na prévia.
- O modo ao vivo nunca:
  - cria conta;
  - mexe em `PreventDeviceEncryption` (o disco atual pode já estar criptografado; a prévia mostra o estado do BitLocker só como informação, por `Win32_EncryptableVolume.ProtectionStatus`);
  - remove apps que não estão na lista.

**Textos:** `live.*` (título, avisos, passos, botões), `preview.status.*`, `step.*.preview.*`.

**Testes.**
- **Planejador:** R31 para cada tipo; `only_kinds`; ordem com `restore_point:before`.
- **`run_live` com fakes:** aplica, recupera de interrupção, segunda execução (tudo `already_done`).
- **Simulação sem escrita** (proteção).
- **Studio:** fluxo dos três passos com o Agente simulado (`TaskRunner` síncrono e um fake de processo que escreve o `progresso.jsonl`).
- **CLI:** `aplicar --simular --raiz`.
- **Fumaça (`smoke.ps1`):** `winkit-agent apply --simular --root <pendrive de teste>` retorna 0 e grava `previa.json`.

**Validação na VM** (`docs/validacao/M12.md`):
1. VM com Windows 11 já instalado e "sujo" (apps de fábrica, sem ajustes).
2. Prévia: confere que lista o que mudaria.
3. Aplicar: ponto de restauração criado antes; apps instalados; ajustes e bloatware aplicados; backups restaurados sem sobrescrever arquivos já existentes (criar um arquivo de teste antes e conferir que continua igual).
4. Aplicar de novo: tudo "já está assim".
5. Restaurar o ponto "antes": o Windows volta ao estado anterior.

**Hipóteses.**
- H14: `pnputil /add-driver /install` num Windows em uso não força reinício sem aviso.
- H15: remover pacotes Appx com o usuário logado não exige sair da sessão.

**Riscos.**
- Um app aberto impede restaurar a configuração dele (arquivo em uso). Mitigação: a prévia avisa quais apps da receita estão abertos (processos do `kill_processes`/`close_before_capture` do catálogo) e oferece fechá-los.

**Arquivos:**
- novos: `agent/live.py`, `studio/ui/pages/finish.py` (página "Aplicar neste PC"), `docs/validacao/M12.md`, os testes;
- alterados: `agent/main.py`, `agent/phases.py`, `agent/executor.py`, `agent/steps/*` (`live_safe`, `preview`), `core/planner/*`, `platform/runner.py`, `studio/controller.py`, `cli/commands/apply.py`, `packaging/smoke.ps1`.

**Pronto quando:** a prévia e a aplicação funcionam pelo Studio e pela CLI, nada é escrito na simulação (teste de proteção) e o roteiro M12 está escrito.

---

## 8. M13 — Pendrive comum (Rufus e ferramenta da Microsoft)

**Código:** V2-01 · **Versão ao concluir:** `0.4.0` · **Depende de:** M11.

### 8.1 Objetivo

Usar o WinKit com um pendrive de instalação gravado pelo **Rufus** ou pela **Ferramenta de Criação de Mídia da Microsoft**, além do Ventoy. Tudo continua funcionando (apps, drivers, backups, ajustes), com uma diferença: só cabe uma versão do Windows por pendrive.

### 8.2 Como se usa

- **Studio**, página **Pendrive**:
  - a lista mostra os dois tipos, com um selo: "Ventoy (várias ISOs)" ou "Pendrive de instalação (Rufus/Microsoft)";
  - um link "Como gravar com o Rufus" abre `docs/RUFUS.md` (versão traduzida no README);
  - ao escolher um pendrive comum que já tem `autounattend.xml`, aparece um aviso: "Este pendrive já tem respostas automáticas (provavelmente do Rufus). O WinKit vai guardar uma cópia como `autounattend.xml.winkit-bak` e usar as dele."
- **CLI:** `winkit pendrive listar` mostra a coluna "Tipo"; `--pendrive E:` funciona igual para os dois.
- **`docs/RUFUS.md`** (novo, com cópia resumida no README), com as configurações recomendadas:
  - esquema GPT, destino UEFI, sistema de arquivos NTFS;
  - na janela "Experiência do usuário do Windows", **desmarcar** tudo: o WinKit já faz conta local, pula requisitos e desliga a coleta de dados. Se ficar marcado, o WinKit guarda a cópia e substitui.

### 8.3 Detecção (`core/media/detect.py`, puro, e `platform/media.py`)

- Um volume é "pendrive de instalação do Windows" quando:
  - está num disco com `BusType = USB` (ou `SD`); outros barramentos não, para nunca escrever num disco interno por engano;
  - tem letra;
  - na raiz, `setup.exe`, `sources\` com `install.wim`, `install.esd` ou `install.swm`, e `boot.wim`;
  - o disco **não** tem partição `VTOYEFI` (senão é Ventoy, tratado como antes).
- O layout do Rufus com "UEFI:NTFS" (partição NTFS principal + partição pequena FAT `UEFI_NTFS`) é reconhecido: a partição alvo é a que tem `sources\`.
- `read_setup_image(root)`:
  - `Get-WindowsImage -ImagePath <root>\sources\install.wim|esd` em JSON (índices, nomes, edições, idioma, build, arquitetura), **só leitura**, sem montar;
  - com `.swm` (imagem dividida), o primeiro arquivo `install.swm` (H16).
- `Target` (`builder/target.py`) ganha `kind: Literal["ventoy", "setup"]` e `setup_image: IsoInfo | None`.

### 8.4 Construtor (`builder/build.py`)

- O modo `setup` reaproveita tudo que escreve em `WinKit\`. Muda só o que fica fora:

  | | Ventoy | Pendrive comum |
  |---|---|---|
  | Respostas automáticas | `ventoy\script\winkit-<perfil>-<idioma>-<arq>.xml` (um por ISO) + `ventoy.json` mesclado | `\autounattend.xml` (um só, do idioma da imagem) |
  | Cópia de segurança | `ventoy\ventoy.json.winkit-bak` | `\autounattend.xml.winkit-bak` (uma vez, se existia um que não é do WinKit) |
  | Escolha no boot | Menu do Ventoy (modelo `winkit-…`) | Automática (o instalador lê `autounattend.xml` da raiz) |

- O `autounattend.xml` gerado leva o comentário `<!-- WinKit <versão> <pendrive_id> -->`. É assim que se reconhece um arquivo do próprio WinKit, para não fazer cópia de segurança dele mesmo na reconstrução (lição do IN-002). A leitura é por XML (`ElementTree`, comentários preservados com `TreeBuilder(insert_comments=True)`).
- Validação (`builder/validate.py`):
  - **a)** a imagem tem a edição da receita (pelo índice/nome técnico);
  - **b)** FAT32 com arquivo > 4 GB não acontece (o WinKit nunca grava arquivo > 4 GB em FAT32; aviso como hoje);
  - **c)** existe um `sources\$OEM$\$$\Panther\unattend.xml` (o Rufus pode gravar ali também, H17). Nesse caso, avisa e também faz a cópia `.winkit-bak` e remove o original, porque ele seria aplicado depois do nosso e poderia desfazer a conta local. É a **única** escrita fora de `WinKit\` e da raiz, e precisa entrar explicitamente na R-19 se H17 se confirmar;
  - **d)** `check_safety` do XML, igual à v1.
- Teste de proteção da R-19 no modo comum: depois de construir num pendrive simulado (pasta com `setup.exe`, `sources\install.wim` falso), a lista de arquivos alterados fora de `WinKit\` é exatamente `{autounattend.xml, autounattend.xml.winkit-bak}` (mais o `$OEM$` se H17).

### 8.5 Instalação

- O instalador do Windows procura `autounattend.xml` na raiz das mídias removíveis na etapa `windowsPE`. O resto do fluxo (bootstrap pelo marcador, Fase 1, Fase 2) é idêntico, porque o comando de bootstrap procura `\WinKit\winkit.marker` em todas as letras.
- O XML do modo comum **não** precisa das chaves `LabConfig` do Ventoy, mas continua levando (mantém o XML válido e burla os requisitos do Windows 11 da mesma forma, `PLANO.md` §9.1).

### 8.6 Testes

- `core/media/detect.py`: Ventoy × comum × disco interno com `sources\` (não aceita) × UEFI:NTFS × sem letra.
- Construtor:
  - modo comum completo numa pasta simulada;
  - reconstrução sem cópia da própria cópia;
  - `.winkit-bak` só uma vez;
  - snapshot do `autounattend.xml` comum (R-42).
- Validação: a edição ausente gera erro; `$OEM$` gera aviso.
- Studio: o selo e o aviso. CLI: a coluna "Tipo".
- Fumaça: `winkit construir --raiz <pasta-com-setup>` cria `autounattend.xml`.

### 8.7 Validação na VM (`docs/validacao/M13.md`)

1. Gravar um pendrive com o Rufus (opções da Experiência do Windows desmarcadas). Construir com o WinKit. Instalar na VM (USB passado para a VM). Conferir a Fase 1 e a Fase 2 completas.
2. Repetir com as opções do Rufus **marcadas**. Conferir o aviso, os `.winkit-bak` e que a conta local do WinKit prevaleceu.
3. Repetir com um pendrive da Ferramenta de Criação de Mídia (`install.esd`).

### 8.8 Hipóteses

- **H16:** `Get-WindowsImage` lê os metadados de uma imagem dividida (`.swm`) pelo primeiro arquivo.
- **H17:** o Rufus grava respostas em `sources\$OEM$\$$\Panther\unattend.xml` além (ou em vez) da raiz. Confirmar com fixtures reais das versões atuais do Rufus.
- **H18:** com `autounattend.xml` na raiz do pendrive e outro disco removível conectado, o instalador usa o do pendrive de boot (ordem de busca do instalador).

### 8.9 Arquivos

- **Novos:** `core/media/{__init__,detect}.py`, `platform/media.py`, `platform/fakes/media.py`, `docs/RUFUS.md`, `docs/validacao/M13.md`, os testes, `tests/fixtures/rufus/*` (capturados na validação).
- **Alterados:** `builder/target.py`, `builder/build.py`, `builder/validate.py`, `core/layout.py`, `core/unattend/generator.py` (comentário de origem), `studio/ui/pages/prepare.py`, `cli/commands/drive.py`, `README*.md`, `ARQUITETURA.md` (R-19).

### 8.10 Pronto quando

O Studio e a CLI preparam um pendrive comum com as mesmas funções do Ventoy, os testes de proteção da R-19 nos dois modos passam e o roteiro M13 está escrito.

---

## 9. M14 — Rede e sistema

**Códigos:** V2-02, V2-08, V2-09, V2-16, V2-17, V2-18, V2-22 · **Versão ao concluir:** `0.5.0` · **Depende de:** M11, M12 (prévia/`live_safe`).

### 9.1 V2-02 — Redes Wi-Fi

**Objetivo.** As redes Wi-Fi salvas no PC antigo já funcionam no Windows novo, **antes do primeiro login**. Assim o winget, o Windows Update e a Fase 2 têm internet sem ninguém digitar senha.

**Como se usa.**
- **Studio**, seção **Wi-Fi** (grupo Rede):
  - botão "Ler redes deste PC"; lista com nome da rede, segurança e uma chave "Levar a senha" (ligada por padrão);
  - aviso fixo (D-036): "As senhas ficam legíveis no pendrive. Guarde-o em lugar seguro ou desligue 'Levar a senha'";
  - redes corporativas (802.1X/EAP) aparecem desabilitadas, com o motivo "usa login da empresa; não pode ser levada".
- **CLI:** `winkit coletar wifi`; `winkit wifi listar`; `winkit wifi marcar <id>... [--sem-senha]`; `winkit wifi desmarcar <id>...`.

**Dados.**
- `recipe.wifi.networks[]`: `id` (derivado do SSID com `slug` + hash curto, R-05), `ssid`, `security` (`open`/`wpa2_personal`/`wpa3_personal`/`enterprise`), `include_key`, `selected`, `file`.
- Arquivo `Perfis/<p>/Wifi/<id>.xml`: o XML exportado pelo Windows (esquema `WLANProfile`). Se `include_key=false`, a captura grava o XML **sem** o elemento `sharedKey/keyMaterial` (remoção por `ElementTree`).

**Captura** (`collector/wifi.py`):
1. `platform.wifi.export_profiles(tmp)`: `netsh wlan export profile key=clear folder=<tmp>`. Usa só o código de saída e os arquivos `.xml` criados; o texto do netsh é ignorado (R-13).
2. Para cada XML (`core/wifi.py`, puro): ler `name`, `SSIDConfig/SSID/name` (ou `hex`, para SSIDs não ASCII), `MSM/security/authEncryption/authentication`; se `enterprise` (`WPA2`/`WPA3ENT` com `OneX`), marcar como não levável.
3. Copiar para o pendrive, já sem a chave quando pedido. A pasta temporária é apagada em `finally` (R-17).
- Requer administrador (o Studio já é).

**Construtor.** Copia `Wifi/` (já está no perfil). Valida cada XML (bem-formado, `WLANProfile`) em `validar`.

**Planejador.** Etapa `wifi:<id>` na Fase 1, logo depois dos drivers (R17), `needs_pendrive=True`.

**Etapa** (`agent/steps/wifi.py`, `live_safe=True`):
- `check()`: o perfil com esse nome já existe? (`profile_exists` exporta só aquele nome para uma pasta temporária e confere o arquivo.)
- `run()`: copiar o XML para `C:\ProgramData\WinKit\tmp\wifi\` (ACL só SYSTEM/Administradores) e rodar `netsh wlan add profile filename=<arquivo> user=all`; apagar a cópia em `finally`.
  - Sem adaptador Wi-Fi (o serviço `WlanSvc` não existe ou não está rodando: consultado por `Get-Service` em JSON): `skipped` com "Este PC não tem Wi-Fi".
- `preview()`: "Adicionar a rede «X»" ou "A rede «X» já existe".

**Segurança.**
- O caminho do XML e a senha entram no `SecretRegistry` (R-53).
- O log diz só "rede adicionada: <ssid>".
- A cópia temporária é apagada, e o `finalize` confere se a pasta `tmp\wifi` está vazia.

**Textos:** `wifi.*`, `step.wifi.*`.

**Testes.**
- `core/wifi.py`: fixtures reais de XML WPA2, WPA3, aberta, enterprise e SSID em hexadecimal; remoção da chave.
- Coletor: com o fake de `netsh` (que cria os arquivos).
- Etapa: sem Wi-Fi, já existe, adiciona.
- **Proteção:** `test_wifi_password_never_logged` (§5.8).

**Validação na VM.** A VM de captura tem uma rede salva (dá para criar um perfil pelo XML mesmo sem adaptador real). Na instalação, conferir com `netsh wlan show profiles` (leitura visual do dono, não do código) que a rede existe antes do login. Em notebook real (opcional), conectar sozinho.

**Hipóteses.**
- H19: o serviço `WlanSvc` está ativo e aceita `add profile` na Fase 1 (`SetupComplete`, como SYSTEM).
- H20: o Windows conecta sozinho a um perfil `connectionMode=auto` antes do login.

**Arquivos:** `core/wifi.py`, `collector/wifi.py`, `platform/wifi.py`, `platform/fakes/wifi.py`, `agent/steps/wifi.py`, `core/secrets.py`, `studio/ui/pages/network.py`, `cli/commands/wifi.py`, os testes e fixtures.

**Pronto quando:** as redes viajam com e sem senha, a senha nunca aparece em log (teste) e o roteiro está escrito.

### 9.2 V2-08 — Recursos do Windows

**Objetivo.** Ligar já na instalação recursos que hoje exigem várias telas: WSL, Plataforma de Máquina Virtual, Windows Sandbox, Hyper-V, .NET Framework 3.5, cliente e servidor OpenSSH, Telnet, TFTP, IIS básico.

**Como se usa.**
- **Studio**, seção **Recursos do Windows** (grupo Sistema): lista com chaves, descrição, selos "precisa de internet" e "reinicia", e itens indisponíveis na edição escolhida desabilitados com o motivo ("exige Pro ou superior").
- **CLI:** `winkit recursos listar|marcar|desmarcar`.

**Dados.**
- **Catálogo `features.yaml`** (§5.2). Exemplos:
  ```yaml
  - id: wsl
    name: Subsistema do Windows para Linux (WSL)
    parts:
      - {feature: Microsoft-Windows-Subsystem-Linux}
      - {feature: VirtualMachinePlatform}
    needs_network: false        # o WSL baixa o kernel no primeiro uso do `wsl`
    restart: true
    source: https://learn.microsoft.com/windows/wsl/install-manual
  - id: sandbox
    name: Área Restrita do Windows (Sandbox)
    parts: [{feature: Containers-DisposableClientVM}]
    windows: {editions: [pro, pro_n, pro_workstations, education, enterprise]}
    restart: true
  - id: netfx3
    name: .NET Framework 3.5
    parts: [{feature: NetFx3, offline_source: sources/sxs}]
    needs_network: true          # sem fonte offline
  - id: openssh_server
    name: Servidor OpenSSH
    parts: [{capability: OpenSSH.Server~~~~0.0.1.0}]
    needs_network: true
  ```
- **Receita:** `windows.optional_features: [ids]`.

**Captura (opcional).** "Ler recursos deste PC": lista os recursos do catálogo que estão ligados no PC atual (`Get-WindowsOptionalFeature -Online` / `Get-WindowsCapability -Online` em JSON) e sugere marcar.

**Planejador.** Etapa `feature:<id>`:
- sem internet → Fase 1;
- com internet → Fase 2 (R19).
- **.NET 3.5 offline:**
  - modo Ventoy: o Agente **monta a ISO original como leitura** (`Mount-DiskImage -Access ReadOnly`, sem modificá-la, D-002), usa `sources\sxs` como `-Source -LimitAccess` e desmonta em `finally`;
  - modo comum: usa `sources\sxs` do próprio pendrive;
  - com fonte offline disponível, a etapa vai para a Fase 1 com `needs_pendrive=True`;
  - para achar a ISO certa: um mesmo modelo do Ventoy serve a várias ISOs, então o nome da ISO não pode ir no XML. O Construtor grava `WinKit/isos.json` com nome, idioma, arquitetura e build de cada ISO (dados que ele já lê em `builder/isos.py`). O Agente escolhe a ISO cujo idioma, arquitetura e build batem com o Windows em execução (`CurrentBuild` e `UBR` no registro, não texto);
  - se nenhuma ISO bater, a etapa cai para a Fase 2, online.

**Etapa** (`agent/steps/feature.py`, `live_safe=True`):
- `check()`: todas as partes `Enabled`/`Installed`.
- `run()`: liga cada parte; `restart` → `reboot_required`.
- Nunca desliga nada (o desligamento continua só pelos ajustes `optional_feature_disable` da v1, como o Recall).
- `preview()`: "Ligar X (exige reinício)".

**Plataforma.** `platform/features.py` ampliado (§5.6); as operações tipadas `capability_add`/`capability_remove` também ficam disponíveis para os ajustes (R-34).

**Testes.**
- Catálogo: todos os ids válidos, filtro por edição.
- Planejador: R19, a fonte offline muda a fase.
- Etapa: com fake (já ligado, liga, reinício, capacidade sem internet → `deferred`).
- Montagem da ISO sempre desmontada (`finally`).

**Validação na VM.** Marcar WSL, Sandbox (com edição Pro), .NET 3.5 e OpenSSH Server. Conferir em "Recursos do Windows" e `Get-WindowsCapability`. Conferir que o .NET 3.5 foi instalado **sem internet** (VM com rede desligada na Fase 1).

**Hipóteses.**
- H21: `Mount-DiskImage -Access ReadOnly` de uma ISO na partição exFAT do Ventoy funciona na Fase 1, como SYSTEM.
- H22: `Enable-WindowsOptionalFeature` funciona na Fase 1 sem o serviço Windows Update ativo.

**Arquivos:** `data/features.yaml`, `core/catalog/models.py`, `core/recipe/models.py`, `platform/features.py`, `platform/iso_mount.py` (montagem só leitura), `agent/steps/feature.py`, `studio/ui/pages/system.py`, `cli/commands/features.py`, os testes.

### 9.3 V2-09 — Diagnóstico de drivers

**Objetivo.** No fim da instalação, mostrar quais dispositivos ficaram **sem driver** (os "pontos de exclamação" do Gerenciador de Dispositivos), procurar automaticamente no Windows Update os drivers **só desses dispositivos** e dizer o que fazer com o que sobrar.

**Como se usa.**
- **Studio**, em "Drivers": chave "Ao terminar, procurar drivers que faltarem" (ligada por padrão).
- O resultado aparece no resumo e no modo ao vivo.

**Dados.** `recipe.updates.fix_missing_drivers: bool = True` (campo novo, aditivo).

**Planejador.** Etapa `driver_report` depois do `windows_update` (R28), Fase 2, `needs_network` só se for procurar.

**Etapa** (`agent/steps/driver_report.py`, `live_safe=True`):
1. `devices.problem_devices()` (CIM `Win32_PnPEntity`, `ConfigManagerErrorCode <> 0`).
2. Se houver e a opção estiver ligada: `windows_update.search_drivers(hardware_ids)`; baixar e instalar só os que casam com o `HardwareID` dos dispositivos com problema.
3. Consultar de novo.
4. Gravar no estado a lista final (nome exibido, código, ids de hardware) para o resumo.
- Os códigos de problema são traduzidos por **tabela** (`ConfigManagerErrorCode` 1, 10, 18, 22, 28, 31, 43… → `Msg("device.problem.<n>")`, com fonte na documentação da Microsoft). O `Name` é só exibido, nunca interpretado.
- `check()` é sempre `False` (é um relatório; roda uma vez por execução).

**Testes.** Fixtures de JSON do CIM (com e sem problemas); com o fake do WU (encontra, não encontra, falha); a tabela de códigos cobre os códigos documentados; o resumo mostra a seção.

**Validação na VM.** VM com um dispositivo sem driver (ex.: um controlador virtual que o Windows não conhece, ou desabilitar um driver antes): conferir a seção do resumo.

**Arquivos:** `platform/devices.py`, `platform/windows_update.py`, `core/devices.py` (tabela de códigos), `agent/steps/driver_report.py`, `core/summary.py`, os testes.

### 9.4 V2-16 — Privacidade de rede: DNS seguro e bloqueio no `hosts`

**Objetivo.**
- **DNS:** usar um DNS mais rápido e privado (Cloudflare, Quad9, Google, AdGuard, NextDNS), com DNS criptografado (DoH) no Windows 11.
- **Bloqueio:** opcionalmente, bloquear anúncios e rastreadores pelo arquivo `hosts`.

**Como se usa.**
- **Studio**, seção **DNS e bloqueios** (grupo Rede):
  - "Servidor DNS": Não mudar (padrão), Cloudflare, Cloudflare para Famílias, Quad9, Google, AdGuard, NextDNS (campo do id pessoal) ou Personalizado;
  - chave "Exigir DNS criptografado" (só Windows 11);
  - lista de bloqueios com chaves e o número de domínios de cada uma;
  - aviso: "Bloquear pelo hosts pode quebrar alguns sites; dá para desfazer".
- **CLI:** `winkit dns definir cloudflare [--exigir-criptografia]`, `winkit dns bloqueios marcar|desmarcar <id>`.

**Dados.**
- `recipe.dns` (§5.1).
- Catálogos `dns_providers.yaml` e `hosts_blocklists.yaml` (§5.2). As listas de bloqueio são **pequenas e curadas**, gravadas no próprio YAML (sem baixar nada da internet na instalação), com `source` e `license` de cada uma. Não entram domínios da Microsoft (risco §15: o Defender trata como sequestro do `hosts`).

**Planejador.** `dns` e `hosts` na Fase 1, depois do Wi-Fi (R18).

**Etapas** (`agent/steps/network_privacy.py`, `live_safe=True` nas duas):
- **`dns`:**
  - para cada adaptador físico (`Get-NetAdapter -Physical`, JSON), `Set-DnsClientServerAddress` com IPv4 e IPv6;
  - no Windows 11, `Add-DnsClientDohServerAddress` com o modelo DoH (para servidores que já estão na lista do Windows, só confere) e a política `DoHPolicy` (2 = permitir, 3 = exigir);
  - `check()` compara os servidores atuais (JSON) com os desejados.
  - **Limitação** registrada como dívida: um adaptador que aparecer **depois** (ex.: um Wi-Fi USB) não recebe o DNS. Por isso a política global de DoH também é gravada.
- **`hosts`:**
  - lê o arquivo; remove o bloco antigo do WinKit (entre `# >>> WinKit` e `# <<< WinKit`), se houver; acrescenta o bloco novo;
  - gravação atômica (R-16), mantendo o resto do arquivo **byte a byte** e a codificação original;
  - `check()`: o bloco existe e tem o mesmo hash;
  - **desfazer:** remover o bloco (exposto no modo ao vivo e na CLI `winkit dns bloqueios remover-do-pc`).

**Testes.**
- `platform/hosts.py` com arquivos de exemplo: com e sem bloco, CRLF, UTF-8 com BOM, arquivo com conteúdo do usuário preservado.
- Catálogos: nenhum domínio da Microsoft (lista de sufixos proibidos no teste), IPs válidos, modelos DoH com `https://`.
- Etapa `dns` com fake (com e sem DoH, Windows 10 sem DoH → só servidores).

**Validação na VM.** `Get-DnsClientServerAddress` e `Get-DnsClientDohServerAddress` (conferência visual); abrir um site da lista de bloqueio e ver que não carrega; desfazer.

**Hipóteses.** H23: `Set-DnsClientServerAddress` funciona na Fase 1 para adaptadores cujo driver acabou de ser instalado pelo `pnputil`.

**Arquivos:** `data/dns_providers.yaml`, `data/hosts_blocklists.yaml`, `platform/dns.py`, `platform/hosts.py`, os fakes, `agent/steps/network_privacy.py`, `studio/ui/pages/network.py`, `cli/commands/dns.py`, os testes.

### 9.5 V2-17 — Unidades de rede mapeadas

**Objetivo.** As unidades de rede do PC antigo (ex.: `Z:` → `\\nas\filmes`) reaparecem no Windows novo.

**Como se usa.**
- **Studio**, seção **Unidades de rede** (grupo Rede): "Ler deste PC"; lista letra → caminho, com chaves; botão "Adicionar" (letra e caminho).
- Aviso: "A senha do servidor não é levada; o Windows vai pedir na primeira vez".
- Atalhos da pasta "Rede" (`%APPDATA%\Microsoft\Windows\Network Shortcuts`) são sugeridos como backup comum (molde `{APPDATA}`), sem código novo.
- **CLI:** `winkit coletar unidades`, `winkit unidades listar|adicionar|remover`.

**Dados.** `recipe.network_drives[]` (§5.1).

**Captura.** Registro `HKCU\Network\<letra>`: `RemotePath`; outros valores ignorados (`UserName` não é levado).

**Planejador.**
- Fase 1 no perfil Default (R25): grava em `HKU\WinKitDefault\Network\<letra>` os valores `RemotePath`, `ConnectionType=1`, `ProviderType=0x20000`, `DeferFlags=4` e `ProviderName`. Este último é **lido do registro do próprio Windows novo** (`HKLM\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\NetworkProvider\Name`), para não depender do idioma (R-13).
- No modo ao vivo e quando `decide_at_runtime`: Fase 2 com `WScript.Network.MapNetworkDrive(letter, path, True)`; se o servidor estiver fora do ar, cai na gravação do registro do usuário.

**Etapa** (`agent/steps/network_drive.py`, `live_safe=True`):
- `check()`: o valor `RemotePath` já existe com o mesmo caminho.
- Letra já usada por outra coisa: `skipped` com motivo (nunca substitui).

**Testes.** Fake de registro com a hive Default; no modo ao vivo, o fake do COM (servidor fora → registro); colisão de letra.

**Validação na VM.** Compartilhar uma pasta no host da VM; mapear no PC de captura; conferir a letra no Windows novo, que pede a senha.

**Hipóteses.** H24: valores em `HKCU\Network` gravados no perfil Default são reconectados no primeiro login do usuário novo.

**Arquivos:** `platform/netdrives.py`, `agent/steps/network_drive.py`, `collector/netdrives.py`, `studio/ui/pages/network.py`, `cli/commands/drives.py`, os testes.

### 9.6 V2-18 — Tarefas de manutenção

**Objetivo.** O Windows novo se mantém sozinho: apps atualizados pelo winget, disco limpo pelo Sensor de Armazenamento e otimização do SSD garantida.

**Como se usa.**
- **Studio**, seção **Manutenção** (grupo Sistema):
  - "Atualizar apps automaticamente": Não, Toda semana, A cada 4 semanas, com dia e hora (o módulo `ScheduledTasks` do PowerShell não tem gatilho mensal; "mensal" vira semanal com intervalo de 4 semanas);
  - "Ligar o Sensor de Armazenamento";
  - "Garantir a otimização semanal do disco" (ligado).
- **CLI:** `winkit manutencao definir --winget semanal --sensor`.

**Dados.** `recipe.maintenance` (§5.1). O Sensor de Armazenamento vira um **ajuste** do catálogo (`maintenance.storage_sense`, categoria nova `maintenance`), com `undo`. A tarefa do winget e a otimização são etapas próprias.

**Planejador.** `maintenance:winget` na Fase 2 (R27); o ajuste segue as regras de ajuste da v1; `maintenance:defrag` na Fase 1.

**Etapas** (`agent/steps/maintenance.py`, `live_safe=True`):
- **`maintenance:winget`:**
  - cria a tarefa `\WinKit\Manutencao\AtualizarApps` (`ScheduledTasks`), gatilho semanal ou mensal;
  - executa como o **usuário** (o winget é por usuário), com privilégio mais alto;
  - ação: `winget.exe upgrade --all --silent --accept-package-agreements --accept-source-agreements --disable-interactivity`, pelo caminho absoluto do `winget.exe` resolvido na hora (`%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe`, R-12);
  - log em `%ProgramData%\WinKit\Logs\manutencao\`.
  - `check()`: a tarefa existe com a mesma ação e o mesmo gatilho.
- **`maintenance:defrag`:** confere que a tarefa nativa `\Microsoft\Windows\Defrag\ScheduledDefrag` está habilitada (`Get-ScheduledTask` em JSON) e a habilita se não estiver. Nunca cria otimização própria.
- **Desfazer** (ao vivo e CLI): remover a pasta de tarefas `\WinKit\Manutencao\`.

**Testes.** Especificação da tarefa (gatilho semanal/mensal, ação, principal) gerada por função pura; etapa com fake do agendador; o ajuste novo valida no catálogo.

**Validação na VM.** `taskschd.msc`: tarefa presente; rodar a tarefa manualmente e ver o log do winget; Sensor de Armazenamento ligado em Configurações.

**Arquivos:** `core/maintenance.py` (spec das tarefas), `platform/scheduler.py`, `agent/steps/maintenance.py`, `data/tweaks.yaml`, `studio/ui/pages/system.py`, `cli/commands/maintenance.py`, os testes.

### 9.7 V2-22 — Variáveis de ambiente e PATH

**Objetivo.** Quem programa leva as variáveis de ambiente (`JAVA_HOME`, `GOPATH`, chaves de configuração) e as pastas extras do `PATH`, sem copiar à mão.

**Como se usa.**
- **Studio**, seção **Variáveis de ambiente** (grupo Sistema):
  - "Ler deste PC": duas listas, "Do usuário" e "Do sistema", só com o que **não** é padrão do Windows (filtro `protected_env.yaml` e comparação com valores conhecidos);
  - cada variável com chave e o valor (editável);
  - o PATH aparece por entrada, cada uma com chave e um selo "não existe no PC novo ainda" quando aponta para a pasta de um app que será instalado (só informativo).
- **CLI:** `winkit coletar variaveis`, `winkit variaveis listar|marcar|desmarcar|definir`.

**Dados.** `recipe.environment` (§5.1). Na captura, os valores com caminhos do usuário viram moldes de ambiente (`C:\Users\Samuel\go` → `%USERPROFILE%\go`, tipo `expand_sz`), reaproveitando a lógica de `core/paths/templates.to_template` (adaptada para a sintaxe `%VAR%`).

**Planejador** (R26):
- escopo `machine` → Fase 1 no `HKLM`;
- `user` → Fase 1 no Default;
- ao vivo → `HKCU` real + `broadcast_change()`.

**Etapa** (`agent/steps/env.py`, `live_safe=True`):
- **Variável:** se não existe, cria. Se existe com outro valor, **não sobrescreve** (R-21): `skipped` com "já existe com outro valor", e a prévia mostra os dois valores. A exceção é a escolha explícita "substituir" no Studio (campo `on_conflict` por variável, padrão `skip`).
- **PATH:** **acrescenta** as entradas que faltam, no fim, sem duplicar (comparação sem diferenciar maiúsculas e sem a barra final) e sem nunca remover.
- Nomes da lista protegida são recusados na validação da receita.

**Testes.** Mescla do PATH (duplicatas, barras, maiúsculas, `%VAR%`); conversão para molde; lista protegida; etapa com fake de registro nos três destinos.

**Validação na VM.** `JAVA_HOME` e uma pasta no PATH do usuário; conferir num terminal novo depois do login.

**Arquivos:** `core/env.py`, `data/protected_env.yaml`, `platform/environment.py`, `collector/env.py`, `agent/steps/env.py`, `studio/ui/pages/system.py`, `cli/commands/env.py`, os testes.

### 9.8 M14 — Pronto quando

As sete funções funcionam na instalação e no modo ao vivo (com prévia), os testes de proteção de segredos e do `hosts` passam e o roteiro `docs/validacao/M14.md` cobre as sete. Release `0.5.0`.

---

## 10. M15 — Personalização

**Códigos:** V2-04, V2-05, V2-06, V2-07, V2-12, V2-15 · **Versão ao concluir:** `0.6.0` · **Depende de:** M11, M12, M14 (operações tipadas novas).

### 10.1 V2-05 — Apps padrão

**Objetivo.** Navegador, leitor de PDF, player de vídeo e de música, visualizador de imagens e compactador padrão iguais aos do PC antigo.

**Como se usa.**
- **Studio**, seção **Apps padrão** (grupo O que levar):
  - "Ler deste PC": grupos do catálogo `file_associations.yaml` (Navegador: `http`, `https`, `.htm`, `.html`; PDF: `.pdf`; Vídeo: `.mp4`, `.mkv`…), cada um com o app atual e uma chave;
  - aviso honesto: "O Windows protege a escolha de apps padrão. O WinKit aplica o que der na instalação; para apps instalados depois do primeiro login, o resumo vai pedir para você confirmar em Aplicativos padrão".
- **CLI:** `winkit coletar associacoes`, `winkit associacoes marcar|desmarcar <grupo>`.

**Dados.** `recipe.default_apps` (§5.1); arquivo `Perfis/<p>/Associacoes/padrao.xml`.

**Captura.**
1. `dism.exe /Online /Export-DefaultAppAssociations:<tmp>\assoc.xml`, usando só o código de saída e o XML.
2. `core/associations.py` (puro): lê o XML (`DefaultAssociations/Association[@Identifier, @ProgId, @ApplicationName]`) e filtra só as extensões e protocolos dos grupos marcados.
3. Grava o XML filtrado no pendrive.

**Planejador.** Etapa `default_apps` só na Fase 1 (R20). No fallback e no modo ao vivo: `skipped` com a ação manual "Abrir Aplicativos padrão" (o resumo tem um link `ms-settings:defaultapps`).

**Etapa** (`agent/steps/default_apps.py`, `live_safe=False`):
- `run()`: `dism.exe /Online /Import-DefaultAppAssociations:<arquivo>`. Vale para perfis criados depois, por isso só na Fase 1 (H25).
- Depois do primeiro login (verificação na Fase 2, etapa `default_apps:verify`): para cada associação, ler `HKCU\...\FileExts\<ext>\UserChoice\ProgId` (ou `...\Shell\Associations\UrlAssociations\<proto>\UserChoice`) e comparar. As que não pegaram (normalmente porque o app foi instalado na Fase 2) vão para "O que fazer agora" no resumo.

**Testes.** Parser e filtro do XML com fixture real; o planejador manda para a Fase 1 e pula no ao vivo; verificação com fake de registro.

**Validação na VM.** Firefox (instalado offline na Fase 1) como navegador padrão e SumatraPDF para `.pdf`: conferir depois do login; um app da Fase 2 aparece no resumo como pendente.

**Hipóteses.** H25: `/Import-DefaultAppAssociations` na Fase 1 vale para a conta criada no primeiro login, para apps já instalados.

**Arquivos:** `data/file_associations.yaml`, `core/associations.py`, `platform/associations.py`, `collector/associations.py`, `agent/steps/default_apps.py`, `studio/ui/pages/bring.py`, `cli/commands/defaults.py`, os testes.

### 10.2 V2-06 — Aparência pessoal

**Objetivo.** Papel de parede, cor de destaque, ponteiro do mouse, velocidade e precisão do mouse e repetição do teclado iguais aos do PC antigo.

**Como se usa.**
- **Studio**, seção **Aparência** (grupo O que levar): "Ler deste PC", com prévia do papel de parede (miniatura), amostra da cor de destaque, nome do esquema de ponteiro e chaves por grupo.
- **CLI:** `winkit coletar aparencia`, `winkit aparencia grupos marcar|desmarcar <grupo>`.

**Dados.**
- **Catálogo `personal_settings.yaml`** (D-037). Exemplo:
  ```yaml
  - id: accent
    name: Cor de destaque
    values:
      - {key: 'Software\Microsoft\Windows\DWM', value: AccentColor, type: dword}
      - {key: 'Software\Microsoft\Windows\DWM', value: ColorPrevalence, type: dword, allowed: [0, 1]}
      - {key: 'Software\Microsoft\Windows\CurrentVersion\Explorer\Accent', value: AccentPalette, type: binary, length: 32}
      - {key: 'Software\Microsoft\Windows\CurrentVersion\Explorer\Accent', value: StartColorMenu, type: dword}
      - {key: 'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize', value: ColorPrevalence, type: dword, allowed: [0, 1]}
    source: https://learn.microsoft.com/...
  - id: mouse
    name: Velocidade e precisão do mouse
    values:
      - {key: 'Control Panel\Mouse', value: MouseSensitivity, type: sz, pattern: '^([1-9]|1[0-9]|20)$'}
      - {key: 'Control Panel\Mouse', value: MouseSpeed, type: sz, allowed: ['0', '1', '2']}
      - {key: 'Control Panel\Mouse', value: MouseThreshold1, type: sz, pattern: '^[0-9]{1,2}$'}
      - {key: 'Control Panel\Mouse', value: MouseThreshold2, type: sz, pattern: '^[0-9]{1,2}$'}
  - id: cursor
    name: Ponteiro do mouse
    values: [...]   # HKCU\Control Panel\Cursors: (Default), Arrow, Hand... só caminhos em %SystemRoot%\Cursors
  - id: keyboard_repeat
    name: Repetição do teclado
    values: [...]   # Control Panel\Keyboard: KeyboardDelay, KeyboardSpeed
  - id: wallpaper
    name: Papel de parede
    file: true      # o arquivo vai para o pendrive
    values: [...]   # Control Panel\Desktop: WallpaperStyle, TileWallpaper
  ```
- Valores fora da faixa ou do padrão são **descartados na captura** (com aviso), nunca gravados.
- Ponteiros personalizados (fora de `%SystemRoot%\Cursors`): os arquivos `.cur`/`.ani` vão para `Perfis/<p>/Aparencia/cursores/` e são reescritos para `%SystemRoot%\Cursors\WinKit\` na aplicação.
- **Receita:** `recipe.personal` (§5.1); papel de parede em `Perfis/<p>/Aparencia/papel-de-parede.<ext>`.

**Captura.**
- O papel de parede vem de `HKCU\Control Panel\Desktop\WallPaper`. Se o arquivo original não existir mais, usa `%APPDATA%\Microsoft\Windows\Themes\TranscodedWallpaper` (sem extensão; o tipo é detectado pelos bytes iniciais, JPEG ou PNG, no `core`).
- Apresentação de slides e Windows Spotlight não são levados (aviso).

**Planejador.**
- Fase 1 no Default (R23): copia o papel de parede para `%SystemRoot%\Web\Wallpaper\WinKit\` (pasta de máquina que sobrevive à limpeza do Agente) e grava os valores.
- Fase 2: confere `WallPaper` e a cor e reaplica se o Windows trocou (H26). O papel de parede é reaplicado ao vivo com `SystemParametersInfoW`.

**Etapa** (`agent/steps/personal.py`, `live_safe=True`; ao vivo grava no `HKCU` e aplica na hora): `check()` compara todos os valores do grupo.

**Testes.** Catálogo (faixas e padrões); captura descarta valores inválidos; detecção JPEG/PNG; etapa nos dois destinos; reaplicação na Fase 2.

**Validação na VM.** Mudar papel de parede, cor de destaque e velocidade do mouse na VM de captura e conferir no Windows novo depois do login.

**Hipóteses.** H26: o Windows 11 mantém o papel de parede e a cor gravados no perfil Default no primeiro login (sem trocar pelo tema padrão).

**Arquivos:** `data/personal_settings.yaml`, `core/personal.py`, `platform/personal.py`, `collector/personal.py`, `agent/steps/personal.py`, `studio/ui/pages/bring.py`, `cli/commands/look.py`, os testes.

### 10.3 V2-07 — Fontes

**Objetivo.** As fontes que você instalou (para design, Office, programação) já estão no Windows novo.

**Como se usa.**
- **Studio**, seção **Fontes** (grupo O que levar):
  - "Ler deste PC": lista por família (nome lido do próprio arquivo da fonte), com tamanho, origem ("instalada só para você" / "para todos") e chave;
  - aviso: "Fontes podem ter licença; leve só as que você tem direito de usar".
- **CLI:** `winkit coletar fontes`, `winkit fontes listar|marcar|desmarcar`.

**Dados.** `recipe.fonts[]` (§5.1); arquivos em `Perfis/<p>/Fontes/`, cobertos pelo manifesto (§5.3).

**Captura.**
- **Fontes do usuário:** registro `HKCU\Software\Microsoft\Windows NT\CurrentVersion\Fonts` (valores com caminho completo, normalmente `%LOCALAPPDATA%\Microsoft\Windows\Fonts`).
- **Fontes da máquina instaladas pelo usuário:** `HKLM\...\Fonts` com arquivos em `%SystemRoot%\Fonts` cuja data de criação é **posterior à instalação do Windows** (`HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\InstallDate`, um número, não texto).
  - Heurística registrada como dívida: atualizações do Windows também instalam fontes depois. Mitigação: catálogo `default_fonts.yaml` gerado na VM (§21) com os arquivos de fonte de um Windows limpo, usado como lista de exclusão.
- **Nome da família:** parser da tabela `name` do formato OpenType/TrueType/TTC em `core/fonts.py` (puro, sem dependência nova): `nameID` 1 (família) e 4 (nome completo), plataforma Windows (3) e idioma `0x0409`.

**Planejador.** Etapa `font:<id>` na Fase 1 (escopo máquina, que vale para todas as contas).

**Etapa** (`agent/steps/font.py`, `live_safe=True`):
- `check()`: o arquivo existe em `%SystemRoot%\Fonts` com o mesmo SHA-256 e o valor `HKLM\...\Fonts\<Nome> (TrueType|OpenType)` existe.
- `run()`: copia (sem sobrescrever arquivo de mesmo nome com conteúdo diferente: grava com sufixo `_winkit`) e grava o valor do registro.
- Ao vivo: também `AddFontResourceW` + `WM_FONTCHANGE`, para valer sem sair da sessão.

**Testes.** Parser da tabela `name` com fontes **geradas no próprio teste** (cabeçalho sfnt + tabela `name`; nenhum arquivo de terceiros nem licença); TTC; arquivo corrompido gera erro claro; etapa com conflito de nome.

**Validação na VM.** Instalar duas fontes livres (uma só para o usuário, uma para todos) e conferir no Word/WordPad do Windows novo.

**Arquivos:** `core/fonts.py`, `platform/fonts.py`, `collector/fonts.py`, `agent/steps/font.py`, `studio/ui/pages/bring.py`, `cli/commands/fonts.py`, os testes e fixtures.

### 10.4 V2-04 — Menu Iniciar e barra de tarefas

**Objetivo.** Os ícones fixados no Iniciar e na barra de tarefas iguais aos do PC antigo, na medida do que o Windows 11 permite. Quita parcialmente a DT-005 e o antigo item 29.

**Como se usa.**
- **Studio**, seção **Iniciar e barra** (grupo O que levar), com dois modos explicados:
  - **"Cópia exata"** (só quando a versão do Windows é a mesma): copia o layout do Iniciar como está;
  - **"Lista"**: o WinKit monta a lista de fixados a partir dos apps que você escolher, e funciona entre versões.
- Barra de tarefas: lista dos atalhos fixados hoje, com chaves.
- Aviso: "Apps instalados depois do primeiro login podem não aparecer fixados; o resumo mostra quais".
- **CLI:** `winkit coletar iniciar --modo exato|lista`.

**Dados.** `recipe.start_layout` (§5.1); `Perfis/<p>/Iniciar/start2.bin` no modo exato.

**Captura.**
- **Iniciar, modo exato:** `%LOCALAPPDATA%\Packages\Microsoft.Windows.StartMenuExperienceHost_cw5n1h2txyewy\LocalState\start2.bin` (copiado com VSS se em uso).
- **Iniciar, modo lista:** os apps escolhidos na tela (dos apps da receita e dos apps do sistema): `packagedAppId` (AUMID, do Appx) ou `desktopAppLink` (atalho `.lnk` no menu Iniciar).
- **Barra de tarefas:** os `.lnk` de `%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\`, lidos por `platform/shell_links.py` (COM) para descobrir o destino. Cada um vira um `PinRef` (`kind: desktop_link|packaged_app`, valor).

**Planejador.** Etapa `start_layout` na Fase 1, no Default (R20).

**Etapa** (`agent/steps/start_layout.py`):
- **Modo exato:** copia `start2.bin` para o mesmo caminho dentro de `C:\Users\Default\AppData\Local\Packages\...\LocalState\` (H27).
- **Modo lista e barra:** gera `C:\Users\Default\AppData\Local\Microsoft\Windows\Shell\LayoutModification.xml` com `CustomTaskbarLayoutCollection`/`TaskbarPinList` (`PinListPlacement="Replace"`), lista documentada pela Microsoft para o Windows 11. Para o Iniciar, gera o JSON de fixados no formato `ConfigureStartPins` (`pinnedList` com `packagedAppId`/`desktopAppLink`) em `LayoutModification.json` (H28).
- **Ao vivo** (`live_safe=False` para o modo exato; o modo lista é aplicado só à **barra** do usuário atual, recriando os `.lnk` fixados — H29). Caso contrário, `skipped` com instrução manual.
- XML e JSON gerados com `ElementTree`/`json` (R-24), com snapshot (R-42).

**Testes.** Geração de XML e JSON (snapshots); leitura de `.lnk` com fake; o planejador; o modo exato exige a mesma versão (aviso).

**Validação na VM.** Os dois modos; conferir os ícones no primeiro login; um app da Fase 2 aparece no resumo como "fixe manualmente".

**Hipóteses.**
- H27: copiar `start2.bin` para o perfil Default reproduz o Iniciar na conta nova (mesma versão do Windows).
- H28: `LayoutModification.json` no perfil Default é respeitado pelo Windows 11 atual para os fixados do Iniciar.
- H29: os fixados da barra podem ser recriados ao vivo sem API privada. Se falso, o modo ao vivo da barra fica como instrução manual.

**Riscos.** A Microsoft muda o formato do Iniciar com frequência. O modo exato é marcado como "experimental" no Studio.

**Arquivos:** `core/start_layout.py` (geração), `platform/shell_links.py`, `collector/start_layout.py`, `agent/steps/start_layout.py`, `studio/ui/pages/bring.py`, `cli/commands/start.py`, os testes e snapshots.

### 10.5 V2-12 — Navegadores prontos

**Objetivo.** Chrome, Edge, Firefox e Brave já com as extensões de sempre (uBlock, Bitwarden, Dark Reader…), página inicial e buscador, **sem** levar senhas, cookies ou login (DPAPI, fora do escopo).

**Como se usa.**
- **Studio**, seção **Navegadores** (grupo Rede):
  - um cartão por navegador detectado no PC antigo ou selecionado nos apps;
  - extensões: as **instaladas no PC antigo** (lidas do perfil do navegador) + as sugeridas do catálogo;
  - página inicial; buscador (lista do catálogo);
  - modo: "Sugerir (você pode mudar depois)" (padrão, D-038) ou "Forçar";
  - aviso: "O navegador vai mostrar 'Gerenciado pela sua organização' porque o WinKit usa as políticas oficiais".
- **CLI:** `winkit coletar navegadores`, `winkit navegador definir chrome --extensoes ublock-lite,bitwarden --busca duckduckgo --pagina https://...`.

**Dados.** `recipe.browsers[]` (§5.1), com as extensões (id da loja, nome, nome curto no AMO) dentro da própria receita; catálogos `browsers.yaml`, `extensions.yaml`, `search_providers.yaml` (§5.2). O arquivo `Navegadores/<nav>.json` previsto ficou desnecessário.

**Captura** (`collector/browsers.py`):
- **Chromium** (Chrome/Edge/Brave): para cada perfil em `User Data\*\`, lê `Secure Preferences` e `Preferences` (JSON), `extensions.settings`, e ignora extensões de componente e do sistema (`location` 5/10). O nome vem do `manifest.json` da extensão (resolvendo `__MSG_name__` pelo `_locales`).
- **Firefox:** `profiles.ini` → perfil padrão → `extensions.json` (`addons[].id`, `defaultLocale.name`, `type == "extension"`, `location == "app-profile"`).
- **Página inicial e buscador:** não são lidos do PC antigo (ficam em arquivos protegidos ou sincronizados pela conta). São escolhidos na tela.

**Planejador.** Etapa `browser:<nav>` na Fase 1 (R21). As políticas no `HKLM` valem quando o navegador for instalado.

**Etapa** (`agent/steps/browser.py`, `live_safe=True`):
- **Chrome/Edge/Brave, extensões no modo sugerir:** chave de extensão externa `HKLM\SOFTWARE\WOW6432Node\<fornecedor>\<nav>\Extensions\<id>` com `update_url` da loja (do catálogo `browsers.yaml`). O navegador pergunta "Ativar extensão?" no primeiro uso e o usuário pode remover.
- **Modo forçar:** `ExtensionInstallForcelist` nas políticas.
- **Página inicial e buscador:** `HKLM\SOFTWARE\Policies\<fornecedor>\<nav>\Recommended` (`HomepageLocation`, `HomepageIsNewTabPage`, `RestoreOnStartup`, `DefaultSearchProviderEnabled`, `DefaultSearchProviderName`, `DefaultSearchProviderSearchURL`). No modo forçar, sem `Recommended`.
- **Firefox:** `ExtensionSettings` (`installation_mode: normal_installed` ou `force_installed`, `install_url` do AMO) e `Homepage`/`SearchEngines` (`Add` + `Default`) por política no registro `HKLM\SOFTWARE\Policies\Mozilla\Firefox` (valores JSON aceitos pela política).
- `check()` compara os valores. **Desfazer** (ao vivo/CLI): apagar só as chaves criadas pelo WinKit (registradas no estado).
- Todas as escritas são operações tipadas de registro (R-34), geradas por `core/browsers.py` (puro) a partir da receita e dos catálogos.

**Testes.**
- Geração das operações para cada navegador e modo (tabela de casos).
- Leitores de extensões com fixtures reais de `Preferences`, `Secure Preferences` e `extensions.json` (sem dados pessoais).
- Catálogos: ids no formato certo (32 letras a–p no Chromium; e-mail ou GUID no Firefox) e URLs `https`.

**Validação na VM.** Instalar Chrome e Firefox pela receita; abrir e conferir as extensões oferecidas, o buscador e a página inicial; mudar o buscador manualmente (modo sugerir permite).

**Hipóteses.**
- H30: extensões externas por registro continuam aceitas no Chrome e no Edge estáveis atuais para usuários não gerenciados.
- H31: o Brave aceita as mesmas políticas do Chromium em `HKLM\SOFTWARE\Policies\BraveSoftware\Brave`.

**Arquivos:** os três catálogos, `core/browsers.py`, `platform/browsers.py`, `collector/browsers.py`, `agent/steps/browser.py`, `studio/ui/pages/network.py`, `cli/commands/browser.py`, os testes e fixtures.

### 10.6 V2-15 — Modo gamer e outros perfis rápidos

**Objetivo.** Um clique liga um conjunto coerente de escolhas. O **Gamer**:
- Modo de Jogo;
- agendamento de GPU acelerado por hardware;
- precisão do ponteiro desligada (sem aceleração do mouse);
- gravação em segundo plano do Xbox desligada;
- otimizações para jogos em janela;
- plano de energia de alto desempenho;
- Xbox Game Bar opcional.

Outros perfis: **Privacidade máxima**, **Escritório**, **Programador** (WSL, OpenSSH, variáveis, Terminal).

**Como se usa.**
- **Studio**: um cartão "Perfis rápidos" no topo de **Ajustes** (a seção separada "Modelos" no grupo Preparar ficou para depois, porque o cartão já cobre o uso):
  - cada perfil mostra o que vai mudar (lista) antes de aplicar;
  - aplicar **mescla** com a receita (D-040), nunca desmarca o que já estava marcado.
- **CLI:** `winkit perfil-rapido listar`, `winkit perfil-rapido aplicar gamer`.

**Dados.**
- **`presets.yaml`:**
  ```yaml
  - id: gamer
    name: Gamer
    description: Menos interrupções e mais desempenho em jogos.
    tweaks: [gaming.game_mode, gaming.hags, gaming.no_mouse_acceleration, gaming.no_background_recording, gaming.windowed_optimizations]
    power: {scheme: high_performance}
    personal_groups: []
    bloatware_keep: [Microsoft.XboxGamingOverlay]   # nunca remover no perfil gamer
    features: []
  ```
- **Ajustes novos** em `tweaks.yaml`, categoria `gaming`, cada um com `source` e `undo`:
  - `gaming.game_mode`: `HKCU\Software\Microsoft\GameBar` `AutoGameModeEnabled=1`;
  - `gaming.hags`: `HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers` `HwSchMode=2`, `risk: caution` (depende da GPU e exige reinício);
  - `gaming.no_mouse_acceleration`: `HKCU\Control Panel\Mouse` `MouseSpeed=0`, `MouseThreshold1=0`, `MouseThreshold2=0`;
  - `gaming.no_background_recording`: `HKCU\System\GameConfigStore` `GameDVR_Enabled=0` e a política `AllowGameDVR=0`;
  - `gaming.windowed_optimizations`: `HKCU\Software\Microsoft\DirectX\UserGpuPreferences` `DirectXUserGlobalSettings="SwapEffectUpgradeEnable=1;"`.
- **Fica fora de propósito:** desligar a Integridade da Memória (VBS/HVCI) aumentaria o FPS em alguns jogos, mas reduz a segurança. Não entra em nenhum perfil; se um dia entrar, só como ajuste avulso `risk: caution` com aviso explícito.
- `recipe.presets_applied` só registra o histórico (para a tela mostrar "Gamer aplicado").

**Planejador e Agente.** Nada novo: um perfil só marca itens que já têm etapas (ajustes, energia, recursos, bloatware).

**Testes.** Todo id de todo perfil existe nos catálogos; aplicar é mescla (idempotente; nunca desmarca); o perfil gamer não remove o Xbox Game Bar mesmo se a receita mandar (aviso de conflito na tela).

**Validação na VM.** Aplicar Gamer e conferir os valores no registro e o plano de energia.

**Arquivos:** `data/presets.yaml`, `data/tweaks.yaml`, `core/presets.py`, `studio/ui/pages/prepare.py` e `system.py`, `cli/commands/presets.py`, os testes.

### 10.7 M15 — Pronto quando

As seis funções funcionam na instalação e, onde marcadas `live_safe`, no modo ao vivo. Os snapshots de `LayoutModification.xml/json` estão revisados e o roteiro `M15.md` está escrito. Release `0.6.0`.

---

## 11. M16 — Contas, pastas e jogos

**Códigos:** V2-11, V2-13, V2-14 · **Versão ao concluir:** `0.7.0` · **Depende de:** M11, M12, M14 (variáveis), e do resolver de volumes (§5.7), criado neste marco.

### 11.1 Base do marco: resolver de volumes (D-035, R-52)

Feito **primeiro**, porque V2-13 e V2-14 dependem dele:
- `core/volumes.py`, `platform/volumes.py` e o fake;
- molde `{VOL:<serial>}`;
- teste de proteção da R-52.

A captura guarda também o serial do volume do sistema antigo (`recipe.meta.source_system_volume`, campo novo aditivo), para recusar "levar" pastas que estavam no próprio `C:` antigo (que será formatado).

### 11.2 V2-14 — Pastas do usuário em outro disco

**Objetivo.** Documentos, Downloads, Imagens, Vídeos, Músicas e Área de Trabalho ficam num **outro disco ou partição** (ex.: `D:\Usuarios\Samuel\Documentos`). Assim a próxima formatação do `C:` não apaga nada, e no Windows novo as pastas já apontam para os arquivos que continuam lá. É a função que mais economiza tempo numa reinstalação.

**Como se usa.**
- **Studio**, seção **Pastas do usuário** (grupo Sistema):
  - escolha do volume (lista de volumes **que não são o do sistema**, com rótulo, letra, tamanho e espaço livre);
  - pasta base (padrão `Usuarios\<seu usuário>`);
  - chaves por pasta;
  - se o PC antigo **já** usa pastas em outro disco, o Studio detecta e pré-preenche;
  - prévia dos caminhos finais;
  - aviso: "O WinKit não move arquivos. Se as pastas ainda estão no C:, copie-as para o outro disco antes de formatar (o Studio pode fazer isso agora, sem apagar a origem)";
  - botão opcional **"Copiar agora"**, que copia de `C:\Users\<você>\Documentos` para o destino com robocopy em modo `merge` (D-007), **nunca** `/MOV` nem `/MIR`, com progresso.
- **CLI:** `winkit pastas definir --volume <serial|letra> --base "Usuarios\Samuel" --pastas documentos,downloads,imagens`; `winkit pastas copiar-agora`.

**Dados.** `recipe.user_folders` (§5.1).

**Captura.** Lê `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders`; se algum valor aponta para outro volume, monta a sugestão. A lista de volumes vem de CIM `Win32_Volume`.

**Planejador.** Etapa `user_folders` na Fase 1 no Default, **antes** de backups e ajustes de usuário (R16). Os moldes `{DOCUMENTS}`, `{DESKTOP}`, `{DOWNLOADS}`, `{PICTURES}`, `{VIDEOS}` e `{MUSIC}` passam a resolver para o destino redirecionado (`core/paths/templates.py` consulta `user_folders` no contexto).

**Etapa** (`agent/steps/user_folders.py`, `live_safe=True`):
1. Resolver o volume pelo serial. Se não achar: `skipped` com "o disco <rótulo> não foi encontrado; as pastas ficaram no lugar padrão" (nunca falha a instalação).
2. Montar o caminho com a **letra atual** do volume: `<letra>:\Usuarios\%USERNAME%\Documentos`.
   - No Default: valor `REG_EXPAND_SZ` com `%USERNAME%`, que o Windows expande por usuário, então vale também para contas extras. Ver H32.
3. Criar as pastas que não existem (para o usuário principal; para os outros, o Explorer cria no login), com ACL herdada.
4. Gravar os valores de `User Shell Folders`, pelos nomes de valor oficiais: `Personal`, `{374DE290-123F-4565-9164-39C4925E467B}` (Downloads), `My Pictures`, `My Video`, `My Music`, `Desktop`.
5. **Ao vivo:** só aponta. O "Copiar agora" é uma ação separada, explícita.

Segurança:
- nunca move nem apaga arquivos;
- nunca muda letra de unidade;
- a pasta de destino existente é usada como está (merge).
- Aviso de conflito com o OneDrive: se o "Backup de pastas" do OneDrive for ligado depois, ele assume essas pastas. Fica no resumo como informação.

**Testes.** Resolver (achou, não achou, letra mudou); geração dos valores (todos os GUIDs/nomes); moldes de backup resolvidos para o volume; etapa com fake; "Copiar agora" usa `merge` (o fake do copiador recusa `/MIR` fora de `Backups/`, R-20, e `/MOV` sempre).

**Validação na VM.** VM com dois discos virtuais: Documentos em `D:` no Windows antigo; reinstalar no disco 1 (o `D:` intacto); depois do login, Documentos aponta para `D:` com os arquivos. Testar também com a letra do `D:` trocada para `E:` antes de instalar (o WinKit acha pelo serial).

**Hipóteses.** H32: `REG_EXPAND_SZ` com `%USERNAME%` em `User Shell Folders` do perfil Default é expandido corretamente no primeiro login de cada conta.

**Arquivos:** `core/volumes.py`, `core/user_folders.py`, `platform/volumes.py`, `platform/known_folders.py`, `collector/user_folders.py`, `agent/steps/user_folders.py`, `studio/ui/pages/system.py`, `cli/commands/folders.py`, os testes.

### 11.3 V2-13 — Jogos sem baixar de novo

**Objetivo.** Jogos da Steam e da Epic instalados em outro disco aparecem como instalados no Windows novo, **sem baixar de novo**. Para as outras lojas, o Studio lista as pastas e explica como "localizar o jogo".

**Como se usa.**
- **Studio**, seção **Jogos** (grupo O que levar):
  - "Procurar jogos neste PC": por loja, as bibliotecas encontradas, com volume, número de jogos e tamanho;
  - bibliotecas no volume do sistema aparecem desabilitadas: "está no C:, que será formatado. Mova a biblioteca para outro disco pela própria Steam antes";
  - chave por biblioteca;
  - os jogos da Epic aparecem um a um;
  - a seção também sugere os **saves** conhecidos (`{SAVED_GAMES}`, `{DOCUMENTS}\My Games`, catálogo `game_saves.yaml` no M17) como backups comuns.
- **CLI:** `winkit coletar jogos`, `winkit jogos listar|marcar|desmarcar`.

**Dados.** `recipe.game_libraries[]` (§5.1); os manifestos da Epic em `Perfis/<p>/Jogos/<id>/`.

**Captura.**
- **Steam:**
  - `SteamPath` em `HKCU\Software\Valve\Steam`;
  - `<SteamPath>\steamapps\libraryfolders.vdf`, lido pelo parser VDF em `core/vdf.py` (puro, formato texto de chaves e valores entre aspas; não é texto localizado);
  - para cada biblioteca: caminho, `apps` (appid → tamanho);
  - o volume de cada biblioteca vira `VolumeRef`.
- **Epic:**
  - `C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests\*.item` (JSON: `InstallLocation`, `AppName`, `DisplayName`, `CatalogNamespace`…), mais a entrada correspondente em `C:\ProgramData\Epic\UnrealEngineLauncher\LauncherInstalled.dat` (JSON);
  - só jogos cuja `InstallLocation` está fora do volume do sistema;
  - os `.item` são copiados para o pendrive (são pequenos).

**Planejador.** Etapa `game_library:<id>` na Fase 2, depois do app do launcher (R22). Se o launcher não está na receita: `skipped` com "instale a Steam/Epic e rode 'Aplicar neste PC' só com Jogos", que usa o modo ao vivo.

**Etapa** (`agent/steps/game_library.py`, `live_safe=True`):
- **Steam:**
  1. fechar a Steam (processos do catálogo);
  2. ler o `libraryfolders.vdf` do Windows novo (criado pela instalação ou ausente);
  3. **acrescentar** a biblioteca com o caminho resolvido pelo volume (letra atual), sem duplicar;
  4. gravar atomicamente.
  - A Steam detecta os `appmanifest_*.acf` da pasta `steamapps` da biblioteca no próximo início (H33). `check()`: a biblioteca já está no arquivo.
- **Epic:**
  1. fechar o launcher;
  2. copiar cada `.item` para a pasta `Manifests` do Windows novo, **reescrevendo** `InstallLocation`, `ManifestLocation` e `StagingLocation` para a letra atual do volume;
  3. acrescentar a entrada no `LauncherInstalled.dat` sem duplicar.
  - A cópia só acontece se a pasta do jogo existe no destino.
- **Nunca** mexe nos arquivos dos jogos.

**Testes.** Parser e gravação VDF (ida e volta, aspas, escapes, chaves aninhadas); reescrita dos manifestos da Epic; resolução por volume; etapa com o fake do sistema de arquivos; o volume do sistema é recusado.

**Validação na VM.** Steam com um jogo gratuito pequeno instalado em `D:\SteamLibrary`; reinstalar o Windows; depois da Fase 2 a Steam mostra o jogo como instalado (pode pedir "verificar arquivos"). Epic: idem com um jogo gratuito pequeno.

**Hipóteses.** H33: acrescentar a biblioteca no `libraryfolders.vdf` com a Steam fechada é suficiente para ela reconhecer os jogos já presentes.

**Riscos.** Mudanças de formato das lojas. Mitigação: a etapa nunca falha a instalação; o resumo ensina o caminho manual.

**Arquivos:** `core/vdf.py`, `core/games.py`, `platform/games.py`, `collector/games.py`, `agent/steps/game_library.py`, `studio/ui/pages/bring.py`, `cli/commands/games.py`, os testes e fixtures (VDF e `.item` reais anonimizados).

### 11.4 V2-11 — Contas extras

**Objetivo.** Criar na instalação outras contas locais (família, convidado, uma conta de trabalho), cada uma como **administrador** ou **padrão**, com as mesmas configurações do perfil padrão.

**Como se usa.**
- **Studio**, seção **Contas extras** (grupo Preparar): lista; "Adicionar conta" com nome, nome de exibição, tipo e senha:
  - "**trocar no primeiro acesso**" (padrão): a conta nasce sem senha e o Windows pede uma senha nova no primeiro login;
  - "sem senha";
  - "definida agora": fica no pendrive, como a DT-006.
- Os backups ganham, na tela de Configurações dos apps, o campo **"Para quem"**: Todas as contas (padrão, perfil Default) ou só a conta principal.
- **CLI:** `winkit contas adicionar <nome> [--admin] [--sem-senha|--senha X]` (sem opção = trocar no primeiro acesso), `winkit contas listar|remover`, `winkit backup-para-quem <id> todas|principal`.

**Dados.**
- `windows.extra_accounts[]` (§5.1).
- `BackupItem.for_accounts: Literal["all", "main"] = "all"` (campo novo aditivo). O comportamento da v1 é `all`, porque a Fase 1 já restaura no Default, que serve a todas as contas.

**Construtor.** O `autounattend.xml` ganha uma `LocalAccount` por conta extra (mesma geração por `ElementTree`, R-24). O grupo é `Administrators` ou `Users`, com a mesma ressalva de idioma da H11.

**Planejador.** Etapa `account:<nome>` na Fase 1, no começo (R24).

**Etapa** (`agent/steps/account.py`, `live_safe=False`, porque o modo ao vivo nunca cria conta):
- Garante a participação no grupo pelo **SID** (`S-1-5-32-544` administradores, `S-1-5-32-545` usuários), corrigindo a H11 também para as contas extras; e tira do grupo Administradores quem deve ser padrão (o XML não garante isso em todos os idiomas).
- Senha "trocar no primeiro acesso": ADSI `PasswordExpired = 1`.
- `check()`: grupo e flag corretos.
- Backups `for_accounts: main` (raros, ex.: arquivos de um app só seu) são restaurados na Fase 2 no perfil do usuário principal, em vez do Default (planejador, R7 ajustada).

**Segurança.**
- O modo silencioso aceita contas extras.
- O `AutoLogon` continua só na conta principal.
- A senha "definida agora" entra no `SecretRegistry` (R-53) e no XML no formato do Windows, que não é criptografia (DT-006).
- O Agente apaga o XML do `Panther` no fim (`PLANO.md` §10.4).

**Testes.** Validação (nomes únicos, conflito com a principal, reservados); snapshot do XML com duas contas extras; etapa com fake (grupo por SID, `PasswordExpired`); planejador.

**Validação na VM.** Duas contas extras (uma admin, uma padrão com "trocar no primeiro acesso"); entrar em cada uma; conferir o grupo em `lusrmgr.msc`, o pedido de senha nova e os ajustes e configurações do Default aplicados.

**Arquivos:** `core/recipe/models.py`, `core/recipe/validation.py`, `core/unattend/generator.py`, `platform/accounts.py`, `agent/steps/account.py`, `studio/ui/pages/prepare.py`, `cli/commands/accounts.py`, os testes e snapshots.

### 11.5 M16 — Pronto quando

As três funções e o resolver de volumes estão prontos, com o teste de proteção da R-52 ativo. O roteiro `M16.md` cobre a VM com dois discos. Release `0.7.0`.

---

## 12. M17 — Inteligência do pendrive

**Códigos:** V2-19, V2-20, V2-21, V2-23 · **Versão ao concluir:** `0.8.0` · **Depende de:** todos os anteriores (o assistente e o relatório usam as capturas de todas as funções).

### 12.1 V2-21 — Atualizar os instaladores do pendrive

**Objetivo.** O pendrive montado há meses instala versões velhas dos apps. Esta função verifica e baixa as versões novas dos instaladores offline, sem precisar refazer a receita.

**Como se usa.**
- **Studio**, em **Aplicativos**, botão "Procurar atualizações". Lista "versão no pendrive → versão nova", com o tamanho a baixar e chaves; botão "Atualizar selecionados". Ao abrir o Studio com um pendrive com mais de 30 dias desde a última verificação, aparece uma faixa discreta "Há apps que podem estar desatualizados".
- **CLI:** `winkit apps atualizar [--verificar] [<id>...]`.

**Dados.** `AppItem.installer` já tem `path` e `sha256`. Campo novo aditivo `AppItem.installer_version: str | None` e `recipe.meta.last_update_check: datetime | None`.

**Funcionamento** (`collector/app_updates.py`, D-041):
1. **Verificar:**
   - com o módulo `Microsoft.WinGet.Client` instalado, `Find-WinGetPackage -Id <id> -MatchOption Equals -Source winget` (objetos → JSON) dá a versão disponível sem baixar;
   - sem o módulo, a verificação **é** o download do passo 2 (a tela avisa que vai baixar).
2. **Baixar:**
   - `winget download --id <id> --exact --download-directory <tmp>`;
   - lê o manifesto YAML baixado (`core/winget_manifest.py`) para a versão, o tipo de instalador e o hash;
   - confere o SHA-256 do arquivo baixado contra o do manifesto.
3. **Trocar:** se a versão é maior (`core/versions.py`, comparação semântica tolerante a `1.2.3.4`, `2024.10`, sufixos):
   1. move para `Apps/<id>/<versão-nova>/`;
   2. atualiza a receita (`path`, `sha256`, `installer_version`) e o manifesto (R-22);
   3. **só então** apaga a pasta da versão antiga.
   - Se qualquer passo falhar, a versão antiga continua intacta.
4. Apps sem `winget_id` (instalador próprio do usuário): "atualização manual" (informativo).

**Testes.** Comparação de versões (tabela de casos reais); fluxo com o fake do winget (mais nova, igual, mais velha, falha no meio = nada muda); manifesto e receita atualizados juntos; a pasta velha só é apagada no fim.

**Validação na VM.** Pendrive com uma versão antiga de um app (baixar uma versão específica com `winget download --version`); "Procurar atualizações" encontra; atualizar; construir; instalar e conferir a versão nova.

**Arquivos:** `core/versions.py`, `collector/app_updates.py`, `platform/winget.py` (ampliado), `studio/ui/pages/bring.py`, `cli/commands/apps.py`, os testes.

### 12.2 V2-23 — Receitas compartilháveis e modelos prontos

**Objetivo.**
- Exportar a sua receita **sem dados pessoais** para compartilhar ("meu setup de programador").
- Importar receitas de outras pessoas.
- Começar de modelos prontos que vêm no WinKit.

**Como se usa.**
- **Studio**, seção **Modelos** (grupo Preparar):
  - **"Começar de um modelo"**: cartões dos modelos que vêm no pacote (Gamer, Programador, Escritório, Privacidade máxima, Mínimo);
  - **"Importar receita"**: abre um `.winkit.json`;
  - **"Exportar minha receita"**: salva um `.winkit.json`.
  - Importar sempre abre uma prévia: lista do que entra, com o **publicador** de cada app do winget, e o que foi ignorado e por quê (id desconhecido, versão do catálogo diferente). O usuário confirma e o conteúdo é **mesclado** (D-040).
- **CLI:** `winkit receita exportar meu-setup.winkit.json`, `winkit receita importar arquivo.winkit.json [--aplicar]`; sem `--aplicar`, só mostra a prévia.

**Dados.**
- **Formato `ShareableRecipe`** (`core/share.py`), com `share_schema_version: 1`, `winkit_version`, `title`, `description`, `language` e:
  - `apps`: só `{catalog_id | winget_id, scope, order}`;
  - `bloatware`, `tweaks`, `power`, `optional_features`, `maintenance`, `dns` (sem id pessoal do NextDNS), `browsers` (sem página inicial pessoal: só buscador e extensões), `personal_groups` (só **quais** grupos, sem valores), `presets_applied`, `execution` (modo, sem idioma).
  - **Nunca:**
    - `meta`, `windows.account`, `extra_accounts`, `computer_name`;
    - `drivers`, `backups`, `wifi`, `network_drives`;
    - `environment`, `user_folders`, `game_libraries`, `fonts`, `default_apps`, `start_layout`;
    - instaladores offline.
  - O modelo Pydantic **não tem** esses campos (`extra="forbid"`): um arquivo com eles é recusado.
- Modelos prontos em `src/winkit/data/templates/*.winkit.json`, validados no CI.

**Segurança.**
- Um arquivo importado só contém ids de catálogo e ids do winget; não existe campo que execute algo (R-34).
- A prévia mostra o id do winget de cada app (o publicador vindo do manifesto ficou para depois: DT-025).
- Um teste de proteção exporta uma receita completa de fixture (com senha, Wi-Fi, usuário, caminhos) e confere que nenhum desses valores aparece no arquivo gerado.

**Testes.** Exportar → importar (ida e volta); proteção de dados pessoais; mescla idempotente; ids desconhecidos ignorados com motivo; modelos do pacote válidos.

**Arquivos:** `core/share.py`, `data/templates/*.winkit.json`, `studio/ui/pages/prepare.py`, `cli/commands/recipe.py`, os testes.

### 12.3 V2-19 — Relatório antes/depois

**Objetivo.** No fim da instalação, comparar o Windows novo com o PC antigo:
- apps que estavam lá e não foram instalados;
- dispositivos com driver no antigo e sem driver no novo;
- backups que não foram restaurados;
- recursos ligados lá e não aqui.

**Como se usa.**
- **Studio**, em "Revisar e construir": chave "Comparar com este PC no fim da instalação" (ligada). Na construção, o Studio grava o inventário do PC atual.
- O resultado sai no resumo HTML (seção "Comparação com o PC antigo") e em `Logs/.../comparacao.json`.

**Dados.**
- **`Perfis/<p>/Inventario/antes.json`** (`core/inventory_snapshot.py`, modelo `Snapshot`):
  - apps (nome, versão, publicador, id do winget quando houver);
  - dispositivos (`PNPDeviceID`, `HardwareID`, classe, versão do driver, `ConfigManagerErrorCode`);
  - recursos ligados;
  - fontes do usuário;
  - versão do Windows.
- Gerado pelo Coletor reaproveitando o inventário de apps (M5), os drivers (M4) e as consultas novas (`devices`, `features`).
- `recipe.compare_after_install` (§5.1).

**Planejador.** Etapa `compare` na Fase 2 (R29), `needs_pendrive=True` (lê o `antes.json`).

**Etapa** (`agent/steps/compare.py`, `live_safe=True`):
1. gera o `Snapshot` do Windows novo com as mesmas funções;
2. `core/compare.py` (puro) produz `Comparison` (listas por categoria, cada item com `Msg` de explicação);
3. grava no estado para o resumo.
- Comparação de apps por id do winget, depois por nome normalizado (`core/text.normalize`). Dispositivos por `HardwareID`: se o hardware é o mesmo e não tem driver, é destacado.

**Testes.** `core/compare.py` com snapshots de fixture (mesmo hardware; hardware diferente, quando o relatório deixa de comparar drivers e avisa; apps renomeados); geração do snapshot com fakes; resumo.

**Validação na VM.** Instalar com 2 apps a menos do que o PC de captura tinha e com um driver faltando: o relatório mostra os dois apps e o dispositivo.

**Arquivos:** `core/inventory_snapshot.py`, `core/compare.py`, `collector/snapshot.py`, `agent/steps/compare.py`, `core/summary.py`, os testes.

### 12.4 V2-20 — Assistente "o que levar"

**Objetivo.** Em vez de você lembrar de tudo, o WinKit analisa o PC atual e sugere o que vale levar, explicando o porquê:
- "Você abriu o OBS 143 vezes; quer levar as cenas?";
- "A pasta de saves de Hades tem 12 MB";
- "Este app não está na receita, mas você usa todo dia".

**Como se usa.**
- **Studio**, seção **Sugestões** (primeira do grupo O que levar): botão "Analisar este PC" (leva de segundos a um minuto, com progresso). Resultado em cartões por categoria:
  - **Apps que você usa** e não estão na receita;
  - **Configurações recomendadas** dos apps da receita que ainda não estão em backup;
  - **Saves de jogos**;
  - **Pastas grandes fora do lugar comum** (ex.: `C:\Projetos`), sugeridas como backup ou como aviso "isto está no C: e será apagado";
  - **Outras coisas que dá para levar**: Wi-Fi, fontes, aparência, variáveis, quando detectadas e ainda não marcadas.
- Cada cartão tem "Adicionar" e "Ignorar" (o ignorado não volta, guardado em `recipe.meta.dismissed_suggestions`). Nada é adicionado sozinho.
- **CLI:** `winkit sugestoes listar [--json]`, `winkit sugestoes adicionar <id>...`, `winkit sugestoes ignorar <id>...` (o id é estável, ex.: `app:Mozilla.Firefox`, `save:hades`).

**Fontes de sinal (todas locais, nada sai do PC):**

| Sinal | Origem | Leitura |
|---|---|---|
| Uso de programas | `HKCU\...\Explorer\UserAssist\{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}\Count` (executáveis) e `{F4E57C4B-2036-45F0-A9AB-443BCFE33D9F}\Count` (atalhos) | Nome do valor em ROT13 (decodificado no `core`); dado binário de 72 bytes: contador em `+4`, tempo em foco em `+12`, último uso (FILETIME) em `+60` (formato do Windows 7 em diante; H34) |
| Apps instalados | Inventário da M5 | já existe |
| Pastas de configuração | Catálogo de apps (`config_paths`) | já existe; sugere as recomendadas que faltam |
| Saves de jogos | `game_saves.yaml` (subconjunto curado) + opcional: o manifesto do projeto Ludusavi (licença MIT), baixado sob demanda para `%APPDATA%\WinKit\cache\` com confirmação, atribuição no `NOTICE` | caminhos com moldes, conferidos se existem |
| Pastas grandes fora do comum | Raiz do volume do sistema: pastas que não são do Windows nem de programas (`Windows`, `Program Files*`, `ProgramData`, `Users`, `$*`, `Recovery`, `PerfLogs` excluídas), com tamanho calculado com limite de tempo | só nomes e tamanhos |
| Outras funções | As capturas das funções V2-02, 06, 07, 17 e 22 em modo "só contar" | — |

**Ranqueamento** (`core/suggest.py`, puro):
- pontuação por frequência e recência de uso (UserAssist), por tamanho (com teto, para não priorizar só o que é grande) e por haver configuração conhecida no catálogo;
- explicação montada com `Msg` ("usado {n} vezes; último uso há {dias} dias").
- Determinístico e testado com dados de fixture.

**Privacidade.** Tudo roda localmente. O resultado é gravado só no pendrive, e só se aceito. O download do manifesto do Ludusavi é opcional e explícito.

**Testes.** Decodificação do UserAssist (ROT13 e estrutura binária, com fixtures geradas a partir de valores reais anonimizados); ranqueamento (casos de empate, recência); exclusões de pastas do sistema; as sugestões ignoradas não voltam; desempenho (limite de tempo na varredura de tamanho, com fake de sistema de arquivos lento).

**Validação na VM.** Usar alguns apps várias vezes na VM de captura; analisar; conferir que aparecem no topo, com explicação coerente.

**Hipóteses.** H34: a estrutura binária do UserAssist (72 bytes, contador em `+4`, FILETIME em `+60`) continua igual no Windows 11 atual.

**Arquivos:** `core/userassist.py`, `core/suggest.py`, `data/game_saves.yaml`, `platform/usage.py`, `collector/suggest.py`, `studio/ui/pages/bring.py`, `cli/main.py`, os testes. (Pendências em DT-026.)

### 12.5 M17 — Pronto quando

As quatro funções estão prontas, com os testes de proteção (dados pessoais fora do formato compartilhável; atualização que falha não perde a versão antiga). Roteiro `M17.md`. Release `0.8.0`.

---

## 13. M18 — Fechamento da v2

**Versão ao concluir:** `0.9.0` (continua pré-alpha; a `1.0.0` só depois de o dono validar tudo em hardware real).

Tarefas:
1. **Revisão cruzada** de todos os documentos vivos:
   - o `PLANO.md` passa a incorporar ou referenciar este plano (as tabelas §3.1 e §24 ganham as linhas V2);
   - `ARQUITETURA.md` com todas as decisões e regras;
   - `STATUS.md` com M11–M18;
   - `DIVIDAS_TECNICAS.md` com tudo que ficou provisório.
2. **Revisão das traduções:** consistência com o glossário (§6.6) e textos novos dos marcos M12–M17 nos três idiomas (os testes da R-51 já garantem a existência).
3. **Capturas de tela** novas (26 seções × 3 idiomas, claro e escuro, só das seções principais no README).
4. **README** (três idiomas) com as funções novas, o modo pendrive comum, o modo "Aplicar neste PC" e o aviso de isenção atualizado.
5. **`smoke.ps1`** cobrindo os comandos novos de todas as funções com `--raiz` e `--simular`.
6. **Auditoria das regras:**
   - rodar `scripts/check.sh`;
   - conferir a cobertura (`core` ≥ 90%, demais ≥ 80%, R-38);
   - nenhum `TODO` sem DT (R-50);
   - teste AST (R-55) sem exceções.
7. **Release `0.9.0`** com notas trilíngues listando tudo que é novo e as hipóteses ainda não validadas.
8. **Relatório final ao dono**: o que foi feito, o que validar (roteiros M11–M17), hipóteses abertas, dívidas e incidentes.

---

## 14. Hipóteses novas (H12 a H35)

Continuam a tabela do `PLANO.md` §21. Cada uma é validada no roteiro do marco indicado. Se for falsa, vira incidente e a alternativa é aplicada.

| # | Hipótese | Se for falsa | Marco |
|---|---|---|---|
| H12 | `GetUserDefaultUILanguage` funciona como SYSTEM na Fase 1 | Usar `GetSystemDefaultUILanguage` (só afeta o log da Fase 1) | M11 |
| H13 | `CreateRestorePoint` funciona na Fase 2, logo depois do Windows Update | Criar o ponto no início da Fase 2 (antes do WU) e documentar | M12 |
| H14 | `pnputil /add-driver /install` num Windows em uso não força reinício sem aviso | No modo ao vivo, drivers ficam desmarcados por padrão, com aviso | M12 |
| H15 | Remover Appx com o usuário logado não exige sair da sessão | O resumo pede para sair e entrar de novo | M12 |
| H16 | `Get-WindowsImage` lê metadados de `.swm` pelo primeiro arquivo | Pedir ao usuário a edição manualmente para pendrives com imagem dividida | M13 |
| H17 | O Rufus grava respostas também em `sources\$OEM$\$$\Panther\unattend.xml` | Remover o item da R-19 (não será preciso tocar ali) | M13 |
| H18 | O instalador usa o `autounattend.xml` do pendrive de boot mesmo com outra mídia removível conectada | Avisar para deixar só o pendrive conectado na instalação | M13 |
| H19 | `WlanSvc` aceita `add profile` na Fase 1 | Adicionar as redes no início da Fase 2 (antes de esperar a rede) | M14 |
| H20 | O Windows conecta sozinho a um perfil automático antes do login | Só afeta o tempo; a Fase 2 conecta | M14 |
| H21 | `Mount-DiskImage -Access ReadOnly` de ISO no exFAT do Ventoy funciona na Fase 1 | .NET 3.5 só online (Fase 2) no modo Ventoy | M14 |
| H22 | `Enable-WindowsOptionalFeature` funciona na Fase 1 | Recursos vão para a Fase 2 | M14 |
| H23 | `Set-DnsClientServerAddress` funciona para adaptadores recém-instalados na Fase 1 | DNS vai para a Fase 2 | M14 |
| H24 | Valores de `HKCU\Network` no perfil Default reconectam no primeiro login | Mapear na Fase 2 por COM | M14 |
| H25 | `/Import-DefaultAppAssociations` na Fase 1 vale para a conta criada no primeiro login | Só instrução manual no resumo | M15 |
| H26 | O Windows 11 mantém o papel de parede e a cor do perfil Default no primeiro login | A reaplicação da Fase 2 (R23) já cobre | M15 |
| H27 | Copiar `start2.bin` para o Default reproduz o Iniciar (mesma versão) | O modo exato é retirado; fica só o modo lista | M15 |
| H28 | `LayoutModification.json` no Default é respeitado pelo Windows 11 atual | Iniciar só pelo modo exato; a barra continua pelo XML | M15 |
| H29 | Os fixados da barra podem ser recriados ao vivo sem API privada | No modo ao vivo, a barra vira instrução manual | M15 |
| H30 | Extensões externas por registro continuam aceitas no Chrome e no Edge | Usar `ExtensionSettings` com `normal_installed` (política) | M15 |
| H31 | O Brave aceita as mesmas políticas do Chromium | Brave só com extensões por instrução manual | M15 |
| H32 | `%USERNAME%` em `User Shell Folders` do Default expande certo em cada conta | Redirecionar na Fase 2 por conta (contas extras no primeiro login de cada uma) | M16 |
| H33 | Acrescentar a biblioteca no `libraryfolders.vdf` basta para a Steam reconhecer os jogos | Instruir "Adicionar pasta de biblioteca" no resumo, com o caminho pronto | M16 |
| H34 | A estrutura binária do UserAssist é a mesma no Windows 11 atual | Ranqueamento só por tamanho e catálogo (sem uso) | M17 |
| H35 | O endereço `addons.mozilla.org/.../latest/<id>/latest.xpi` aceita o id da extensão quando não há nome curto | Firefox só com as extensões que têm nome curto no catálogo | M15 |

---

## 15. Riscos novos

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| O modo ao vivo muda algo que a pessoa não esperava num Windows em uso | Média | Alto | Prévia obrigatória, ponto de restauração antes, merge sempre, itens `caution` destacados (D-033) |
| Senhas de Wi-Fi expostas no pendrive perdido | Média | Alto | Aviso permanente, opção sem senha, segredo nunca em log (D-036, R-53) |
| O Defender acusar o `hosts` como sequestro | Média (se incluir domínios da Microsoft) | Médio | Listas curadas sem domínios da Microsoft, verificadas por teste |
| Formatos internos da Microsoft (Iniciar, apps padrão) mudarem | Alta | Médio | Etapas nunca falham a instalação; modo "experimental"; resumo com instrução manual |
| Formatos das lojas de jogos mudarem | Média | Baixo | Idem; nunca mexe nos arquivos dos jogos |
| Traduções com erros (feitas por IA) | Alta | Baixo | Glossário fixo, testes de paridade, pedido de correção no README |
| Crescimento do Studio (26 seções) deixar a interface confusa | Média | Médio | Grupos e busca (D-042); modelos e perfis rápidos para começar rápido |
| Políticas de navegador mostrarem "gerenciado pela organização" e assustarem | Alta | Baixo | Aviso na tela; modo recomendado; desfazer |
| Receitas compartilhadas com apps maliciosos do winget | Baixa | Alto | Prévia com publicador; só ids; nunca instaladores offline no formato compartilhável |
| Volume do usuário (D:) com letra diferente na instalação | Média | Médio | Busca pelo serial (D-035) |
| Escopo grande demais para validar em VM | Alta | Médio | Modo ao vivo (M12) torna cada teste de etapa rápido; roteiros por marco |

---

## 16. Dívidas técnicas já previstas

Entram no `DIVIDAS_TECNICAS.md` quando o código correspondente for escrito (R-50), com estas descrições:

| Prevista | Origem | Descrição | Plano para quitar |
|---|---|---|---|
| Traduções sem revisão nativa | M11 | en-US e es feitos por IA | Revisão por falantes; issues com rótulo `tradução` |
| Português de Portugal recebe pt-BR | M11 | `pt-PT` → `pt-BR` | Arquivo `pt_pt.py` se houver pedido |
| Senhas de Wi-Fi legíveis no pendrive | M14 | Como a DT-006 | Sem solução sem DPAPI; aceita, com aviso |
| DNS só nos adaptadores presentes | M14 | Adaptadores novos ficam com o DNS padrão (exceto a política de DoH) | Tarefa no logon que reaplica, se houver pedido |
| Fontes "instaladas pelo usuário" por data | M15 | Atualizações do Windows podem instalar fontes depois da data de instalação | `default_fonts.yaml` gerado na VM |
| Apps padrão para apps da Fase 2 | M15 | O Windows protege `UserChoice`; ficam como instrução manual | Sem solução oficial; acompanhar o Windows |
| Iniciar e barra para apps da Fase 2 | M15 | Fixados de apps instalados depois do primeiro login não aparecem | Acompanhar APIs da Microsoft |
| Lojas de jogos além de Steam/Epic | M16 | Só instrução manual | GOG/EA/Ubisoft por demanda |
| Assistente sem uso real de jogos | M17 | O UserAssist não registra jogos iniciados pelo launcher | Ler o histórico das lojas, se fizer sentido |

---

## 17. Estratégia de testes da v2

- **Mesmas camadas da v1** (`PLANO.md` §19):
  - `core` puro no Linux com cobertura ≥ 90%;
  - `collector`/`builder`/`agent` com fakes ≥ 80%;
  - `platform` com `@pytest.mark.windows`, só leitura ou só em áreas de teste.
- **Fixtures reais (R-40)**, capturadas pelo dono na VM com um script de captura (`scripts/capturar_fixtures.ps1`, novo, M11): o script grava os arquivos em `fixtures-capturadas\` e **anonimiza** usuários, SSIDs, senhas, ids pessoais e caminhos. Lista do que capturar:
  - XML do `netsh wlan export` (com rede fictícia);
  - XML do `dism /Export-DefaultAppAssociations`;
  - JSON de `Get-WindowsOptionalFeature`/`Get-WindowsCapability`;
  - `Win32_PnPEntity` com problema;
  - `Get-DnsClientServerAddress`/`Get-DnsClientDohServerAddress`;
  - `libraryfolders.vdf` e `.item` da Epic;
  - `Preferences`/`Secure Preferences`/`extensions.json` sem dados pessoais;
  - valores do UserAssist;
  - respostas do Rufus (`autounattend.xml` e `$OEM$`);
  - `Get-WindowsImage` de `install.esd`.
  
  Enquanto não houver fixture real, os testes usam fixtures construídas a partir da documentação, marcadas no nome (`*_doc.xml`) e com dívida aberta para trocar.
- **Testes de proteção novos (não podem ser removidos, R-41):**
  - `test_live_preview_never_writes` (R-54);
  - `test_wifi_password_never_logged` (R-53);
  - `test_no_fixed_drive_letters_in_recipe` (R-52);
  - `test_setup_mode_writes_only_allowed_files` (R-19, modo comum);
  - `test_shareable_recipe_has_no_personal_data` (D-040);
  - `test_hosts_preserves_user_content`;
  - `test_hosts_blocklists_have_no_microsoft_domains`;
  - `test_user_folders_never_moves_files` (fake recusa `/MOV` e `/MIR`);
  - `test_ui_strings_are_translated` (R-55);
  - `test_messages_parity` (R-51).
- **Interface:** cada página nova abre nos três idiomas, com e sem receita, em claro e escuro (offscreen).
- **Fumaça com executáveis:** `smoke.ps1` estendido a cada marco (§5.13).
- **Validação em VM:** um roteiro por marco (`docs/validacao/M11.md` … `M17.md`), no formato dos atuais (passo, esperado, resultado, observação), usando o modo ao vivo sempre que possível para não reinstalar.

---

## 18. Ordem, dependências e versões

```
M11 (i18n) ──► M12 (ao vivo + ponto de restauração) ──► M14 (rede e sistema) ──► M15 (personalização) ──► M16 (contas, pastas, jogos) ──► M17 (inteligência) ──► M18
   └────────► M13 (pendrive comum) ─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

| Marco | Versão | Por que nesta ordem |
|---|---|---|
| M11 | 0.2.0 | Tudo que vier depois já nasce nos três idiomas e usa `Msg` |
| M12 | 0.3.0 | O modo ao vivo acelera a validação de todos os marcos seguintes |
| M13 | 0.4.0 | Independente; pode ser feito antes ou depois do M14 sem impacto |
| M14 | 0.5.0 | Rede primeiro (Wi-Fi, DNS) ajuda a Fase 2 de todas as funções seguintes |
| M15 | 0.6.0 | Personalização usa as operações tipadas e o padrão de catálogo do M14 |
| M16 | 0.7.0 | Introduz o resolver de volumes, que só V2-13/V2-14 usam |
| M17 | 0.8.0 | Precisa das capturas de todas as funções anteriores |
| M18 | 0.9.0 | Fechamento |

Cada marco:
1. é desenvolvido no branch de trabalho;
2. termina com `scripts/check.sh` verde e CI verde (Linux, Windows, empacotamento e fumaça);
3. publica a release pré-alpha pelo workflow `Release` (D-029);
4. é avisado ao dono com o roteiro de validação.

---

## 19. Rastreabilidade: item → marco → arquivos

| Código | Marco | Etapa(s) do Agente | Plataforma | Coletor | Catálogo | Studio (página) | CLI |
|---|---|---|---|---|---|---|---|
| V2-00 | M11 | — | `locale.py` | — | overlays `i18n/catalogs` | Preferências | `--idioma` |
| V2-01 | M13 | — | `media.py` | — | — | Pendrive | `pendrive listar` |
| V2-02 | M14 | `wifi` | `wifi.py` | `wifi.py` | — | Wi-Fi | `coletar wifi`, `wifi` |
| V2-03 | M12 | todas (`live_safe`) | `runner.start_detached` | — | — | Aplicar neste PC | `aplicar` |
| V2-04 | M15 | `start_layout` | `shell_links.py` | `start_layout.py` | — | Iniciar e barra | `coletar iniciar` |
| V2-05 | M15 | `default_apps` | `associations.py` | `associations.py` | `file_associations.yaml` | Apps padrão | `coletar associacoes`, `associacoes` |
| V2-06 | M15 | `personal` | `personal.py` | `personal.py` | `personal_settings.yaml` | Aparência | `coletar aparencia`, `aparencia` |
| V2-07 | M15 | `font` | `fonts.py` | `fonts.py` | (`default_fonts.yaml`) | Fontes | `coletar fontes`, `fontes` |
| V2-08 | M14 | `feature` | `features.py`, `iso_mount.py` | (opcional) | `features.yaml` | Recursos do Windows | `recursos` |
| V2-09 | M14 | `driver_report` | `devices.py`, `windows_update.py` | — | — | Drivers | — |
| V2-10 | M12 | `restore_point` | `restore.py` | — | — | Energia e atualizações | `receita definir` |
| V2-11 | M16 | `account` | `accounts.py` | — | — | Contas extras | `contas` |
| V2-12 | M15 | `browser` | `browsers.py` | `browsers.py` | `browsers/extensions/search_providers.yaml` | Navegadores | `coletar navegadores`, `navegador` |
| V2-13 | M16 | `game_library` | `games.py`, `volumes.py` | `games.py` | (`game_saves.yaml`) | Jogos | `coletar jogos`, `jogos` |
| V2-14 | M16 | `user_folders` | `known_folders.py`, `volumes.py` | `user_folders.py` | — | Pastas do usuário | `pastas` |
| V2-15 | M15 | (ajustes existentes) | — | — | `presets.yaml`, `tweaks.yaml` | Modelos, Ajustes | `perfil-rapido` |
| V2-16 | M14 | `dns`, `hosts` | `dns.py`, `hosts.py` | — | `dns_providers.yaml`, `hosts_blocklists.yaml` | DNS e bloqueios | `dns` |
| V2-17 | M14 | `network_drive` | `netdrives.py` | `netdrives.py` | — | Unidades de rede | `coletar unidades`, `unidades` |
| V2-18 | M14 | `maintenance` | `scheduler.py` | — | `tweaks.yaml` | Manutenção | `manutencao` |
| V2-19 | M17 | `compare` | `devices.py`, `features.py` | `snapshot.py` | — | Revisar e construir | `coletar inventario` |
| V2-20 | M17 | — | `usage.py` | `suggest.py` | `game_saves.yaml` | Sugestões | `sugestoes` |
| V2-21 | M17 | — | `winget.py` | `app_updates.py` | — | Aplicativos | `apps atualizar` |
| V2-22 | M14 | `env` | `environment.py` | `env.py` | `protected_env.yaml` | Variáveis de ambiente | `coletar variaveis`, `variaveis` |
| V2-23 | M17 | — | — | — | `data/templates/` | Modelos | `receita exportar/importar` |

---

## 20. Checklists obrigatórios (commit e marco)

### 20.1 A cada commit (CLAUDE.md, IN-003, R-49)

- [ ] `scripts/check.sh` termina com `== OK` (ruff, formato, mypy nas duas plataformas, import-linter, pytest).
- [ ] `docs/CHANGELOG.md` com a entrada do commit (sempre).
- [ ] Documentos afetados atualizados no **mesmo commit**:
  - `STATUS.md`: item começado, concluído ou bloqueado;
  - `ARQUITETURA.md`: decisão, regra, camada ou dependência;
  - `DIVIDAS_TECNICAS.md`: algo provisório ou `TODO(DT-nnn)`;
  - `INCIDENTES.md`: algo quebrou ou uma hipótese caiu;
  - `PLANO.md`/`PLANO_V2.md`: escopo ou comportamento.
- [ ] Textos novos com chave nos **três** idiomas (R-51); nenhum texto solto (R-55).
- [ ] Identificadores em inglês; mensagem de commit em pt-BR, no imperativo, citando o marco (R-48).
- [ ] Nada de `shell=True`; comandos externos por `platform.runner`/`powershell` (R-11, R-14).
- [ ] Nenhum texto localizado interpretado (R-13); o mecanismo usado está citado no comentário da função de plataforma.
- [ ] Sem escrita fora do permitido (R-19), sem `DiskConfiguration` (R-18), sem `/MIR` fora de `Backups/` (R-20).
- [ ] Edição de documentos por **bloco inteiro**, conferindo o `git diff` (IN-011).
- [ ] Scripts de edição afirmam que o texto antigo existe antes de substituir (IN-007).

### 20.2 Ao fim de cada marco

- [ ] CI verde no Linux e no Windows, empacotamento e fumaça (conferir **a cada commit**, não só no fim — IN-010).
- [ ] Cobertura dentro das metas (R-38).
- [ ] Testes de proteção do marco ativos.
- [ ] Interface conferida visualmente (offscreen) nos três idiomas, claro e escuro.
- [ ] Roteiro `docs/validacao/Mnn.md` escrito.
- [ ] `STATUS.md` com o marco "✅ código" e "⬜ validação".
- [ ] Release pré-alpha publicada e aviso ao dono.

---

## 21. O que depende do dono do projeto

1. **Aprovar este plano**, ou pedir mudanças em decisões específicas (§3).
2. **Validar na VM** ao fim de cada marco, pelos roteiros. Para os marcos M14 a M17, de preferência com o modo ao vivo (M12), sem reinstalar.
3. **Capturar fixtures reais** com `scripts/capturar_fixtures.ps1` numa VM limpa e numa VM "de uso", e enviar a pasta anonimizada (R-40). Inclui gerar o `default_fonts.yaml` numa VM limpa.
4. **Gravar um pendrive com o Rufus** (com e sem as opções dele) para o M13.
5. **VM com dois discos** para o M16.
6. Opcional: pedir a falantes nativos para revisar o inglês e o espanhol.
