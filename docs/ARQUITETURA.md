# WinKit — Arquitetura e Regras do Código

> Documento vivo. **As regras deste arquivo são obrigatórias.** Quem precisar quebrar uma regra registra antes uma decisão nova (seção 6) explicando por quê.
>
> O *porquê* do produto está em `PLANO.md`. Este arquivo descreve *como o código é organizado* e *como ele deve ser escrito*.

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Camadas e regra de dependência](#2-camadas-e-regra-de-dependência)
3. [Módulos e responsabilidades](#3-módulos-e-responsabilidades)
4. [Contratos centrais](#4-contratos-centrais)
5. [Regras do código](#5-regras-do-código)
6. [Registro de decisões](#6-registro-de-decisões)

---

## 1. Visão geral

Três programas, um único pacote Python (`winkit`):

| Programa | Entrada | Comandos | Onde roda |
|---|---|---|---|
| **WinKit Studio** | `winkit` (CLI) / `winkit-studio` (GUI, M10) | `coletar`, `construir`, `sincronizar`, `validar`, `pendrive` | PC atual |
| **WinKit Agent** | `winkit-agent.exe` | `phase1`, `phase2`, `summary` | Windows novo |
| **Bootstrap** | `bootstrap.ps1` | — | Windows novo, etapa *specialize* |

Fluxo de dados:

```
 PC atual                                      pendrive                         Windows novo
┌──────────┐  Inventory   ┌──────────┐  Recipe ┌────────────────┐  Recipe  ┌─────────┐  Plan  ┌──────────┐
│ collector│ ───────────► │  Recipe  │ ──────► │ builder → disco│ ───────► │ planner │ ─────► │ executor │
└──────────┘              │ (editada)│         └────────────────┘          └─────────┘        └────┬─────┘
                          └──────────┘                                                            │ State
                                                                                                  ▼
                                                                                         estado.json, logs
```

Os objetos que atravessam as fronteiras são sempre **modelos Pydantic do `core`**: `Inventory`, `Recipe`, `Plan`, `State`, `Manifest`. Nenhum módulo passa dicionários soltos entre camadas.

---

## 2. Camadas e regra de dependência

```
nível 5   ui/            winkit/ui (kit visual), studio/ui, agent/ui   (PySide6)
nível 4   cli/           agent/main.py                      (pontos de entrada)
nível 3   collector/     builder/     agent/ (exceto ui)    (casos de uso)
nível 2   platform/                                          (efeitos colaterais no Windows)
nível 1   core/                                              (puro)
dados     src/winkit/data/*.yaml                                        (lidos via core/catalog)
textos    i18n/                                              (importável por qualquer nível)
```

**Regra:** um módulo só importa módulos de nível **menor ou igual** ao seu, e nunca de outro módulo do mesmo nível 3 (ex.: `builder` não importa `collector`; o que for comum desce para `core` ou `platform`).

Proibições específicas (verificadas pelo import-linter no CI):

| Módulo | Não pode importar |
|---|---|
| `winkit.core.*` | `winkit.platform`, `winkit.collector`, `winkit.builder`, `winkit.agent`, `winkit.cli`, `winkit.studio`, `PySide6`, `winreg`, `subprocess`, `ctypes`, `msvcrt`, `_winapi` |
| `winkit.platform.*` | `winkit.collector`, `winkit.builder`, `winkit.agent`, `winkit.cli`, `winkit.studio`, `PySide6` |
| `winkit.collector`, `winkit.builder`, `winkit.agent` (fora de `agent.ui`) | `PySide6`, e um ao outro |
| Qualquer módulo exceto `winkit.platform.runner` | `subprocess` |

Por que isso importa:
- `core` roda e é testado no Linux (o ambiente de desenvolvimento). Ali está toda a lógica de decisão.
- `platform` é o único lugar com efeitos colaterais no sistema. Tudo atrás de interfaces (`Protocol`), com versões falsas em `platform/fakes/` para os testes.
- Casos de uso recebem as dependências de `platform` por parâmetro (injeção de dependência simples, sem framework), então podem ser testados com fakes.

---

## 3. Módulos e responsabilidades

### 3.1 `core/` — puro

| Módulo | Responsabilidade | Entradas → saídas |
|---|---|---|
| `core/recipe/` | Modelos da receita, validação (regras 6.2 do plano), migrações por `schema_version` | JSON ↔ `Recipe` |
| `core/catalog/` | Modelos e carregamento dos YAML de `src/winkit/data/` | YAML → `AppCatalog`, `TweakCatalog`, `BloatwareCatalog`... |
| `core/paths/` | Moldes de caminho: tradução (literal → molde) e resolução (molde → literal) | `(caminho, KnownFolders)` → `PathTemplate` e vice-versa |
| `core/planner/` | Decide fase e ordem de cada etapa (regras R1–R15 do plano) | `(Recipe, Catalogs, PlanContext)` → `Plan` (etapas + itens excluídos com motivo) |
| `core/state/` | Modelo do estado do Agente e transições válidas | `State` + evento → `State` |
| `core/manifest/` | Manifesto de arquivos e cálculo do que mudou | `(Manifest, Manifest)` → `ManifestDiff` |
| `core/ventoy/` | Mesclagem do `ventoy.json` | `(json existente, entradas WinKit)` → json novo |
| `core/unattend/` | Geração do `autounattend.xml` e da linha de bootstrap | `(Recipe, IsoInfo)` → `bytes` (XML) |
| `core/installers/` | Detecção do tipo de instalador por bytes (inclui leitura das seções PE) | `bytes` (cabeçalho/conteúdo) → `InstallerType` |
| `core/inventory.py` | Inventário de apps: filtros, escopo, correspondência com catálogo/winget, sugestão de item | valores do registro/JSON → `InstalledApp` → `AppItem` |
| `core/winget_manifest.py` | Manifesto do `winget download` → tipo, escopo, argumentos | pasta → `DownloadedPackage` |
| `core/errors.py` | Hierarquia de exceções | — |
| `core/fsutil.py` | Escrita atômica (R-16) e `write_if_changed` (preserva data e manifesto) | `(Path, texto/bytes)` → arquivo |
| `core/text.py` | `slugify`, `human_size` | texto → texto |

### 3.2 `platform/` — Windows

| Módulo | Responsabilidade | Interface |
|---|---|---|
| `runner.py` | **Único** ponto de `subprocess` | `CommandRunner` |
| `powershell.py` | PowerShell com UTF-8 e saída JSON | `PowerShell` |
| `registry.py` | Leitura/escrita via `winreg`; carga/descarga de hive | `Registry` |
| `known_folders.py` | `SHGetKnownFolderPath` via `ctypes` | `KnownFoldersProvider` |
| `fs.py` | Caminhos longos (`\\?\`), escrita atômica, espaço livre | `FileSystem` |
| `copy.py` | robocopy e alternativa em Python (captura e restauração), salvaguarda R-20 | `Copier` |
| `vss.py` | Cópias de sombra (CIM), exposição por link, pendentes | `ShadowCopies`, `PendingSnapshots` |
| `drivers.py` | Listagem (`Get-WindowsDriver`), exportação e instalação (`pnputil`) de drivers | `DriverManager` |
| `appx.py` | Pacotes MSIX: remoção para todos os usuários e presença | `AppxManager` |
| `features.py` | Recursos opcionais do Windows; renomear o computador | `SystemFeatures` |
| `winget.py` | export, download, install, list, registro do App Installer | `Winget` |
| `inventory.py` | Apps instalados: registro de desinstalação + `Get-AppxPackage` | `AppInventory` |
| `shortcuts.py` | Atalhos `.lnk` (WScript.Shell) | `Shortcuts` |
| `installers.py` | Execução de instaladores com tempo limite e códigos de saída | `InstallerRunner` |
| `disks.py` | Detecção do Ventoy, montagem de ISO somente leitura, leitura de edições | `DiskInspector` |
| `scheduler.py` | Tarefas agendadas | `TaskScheduler` |
| `session.py` | Privilégio de administrador | — |
| `power.py` | Ociosidade da sessão e reinício agendado | `SessionControl` |
| `windows_update.py` | Windows Update via COM | `WindowsUpdater` |
| `environment.py` | Unidades, internet (NCSI), build do Windows, trava de instância única | `Environment` |
| `accounts.py` | Garante a conta no grupo Administradores pelo SID (H11) | `Accounts` |
| `services.py` | Fábrica das implementações reais para o Studio | `Services` |
| `fakes/` | Uma implementação falsa para cada interface acima | — |

### 3.3 Casos de uso

| Módulo | Responsabilidade |
|---|---|
| `collector/apps.py` | Inventário → receita, `winget download` para o pendrive, instalador local |
| `collector/drivers.py` | Candidatos (classe, prioridade, recomendado) e exportação idempotente para o pendrive |
| `collector/backups.py` | Sugestões (catálogo), adicionar pasta/arquivo/portátil, captura com VSS por volume, espaço, avisos DPAPI, `item.json` |
| `builder/target.py` | Escolha do pendrive e checagens (sistema de arquivos, espaço) |
| `builder/isos.py` | Leitura e cache das ISOs |
| `builder/payload.py` | Gravação de Agent/Apps/Drivers/Backups + manifesto + marcador |
| `builder/build.py` | Orquestra a construção completa e a sincronização |
| `builder/assets/bootstrap.ps1` | Script de bootstrap (copiado para o pendrive) |
| `agent/main.py` | Ponto de entrada (`phase1`, `phase2`, `retry`, `summary`) |
| `agent/phases.py` | Abre a sessão (receita, estado, plano), redes de segurança, Fase 1, Fase 2, fallback |
| `agent/paths.py`, `store.py`, `eventlog.py`, `pendrive.py`, `progress.py`, `cleanup.py`, `services.py`, `ui_select.py` | Caminhos locais, estado atômico, logs, localização do pendrive, protocolo de UI sem Qt, limpeza, serviços, escolha da UI |
| `agent/executor.py` | Executa um `Plan`, persiste `State`, trata reinicialização e pendrive ausente; `context()` monta o contexto de uma etapa (usado também pela prévia) |
| `agent/live.py` | Modo "aplicar neste PC" (D-033): plano ao vivo, prévia sem escrita, ponto de restauração antes, estado e resumo por aplicação em `ProgramData\WinKit\Aplicacoes` |
| `agent/steps/restore.py`, `platform/restore.py` | Ponto de restauração (V2-10) por CIM `SystemRestore` e `Win32_ShadowStorage` |
| `core/live.py` | Modelos da prévia (`PreviewItem`, `LivePreview`) |
| `data/features.yaml`, `platform/features.py`, `platform/iso_mount.py`, `collector/features.py`, `agent/steps/feature.py` | Recursos do Windows (V2-08): catálogo, liga recursos e capacidades, monta a ISO só para leitura (D-043) |
| `core/devices.py`, `platform/devices.py`, `agent/steps/driver_report.py` | Dispositivos sem driver (V2-09): tabela de códigos, CIM `Win32_PnPEntity`, busca dirigida no Windows Update, seção do resumo |
| `core/dns.py`, `platform/dns.py`, `platform/hosts.py`, `agent/steps/network_privacy.py`, `data/dns_providers.yaml`, `data/hosts_blocklists.yaml` | DNS seguro e bloqueio pelo `hosts` (V2-16): bloco marcado, resto do arquivo preservado byte a byte |
| `platform/netdrives.py`, `collector/netdrives.py`, `agent/steps/network_drive.py` | Unidades de rede (V2-17): registro `Network` no perfil Default, `WScript.Network` ao vivo; `ProviderName` lido do Windows novo (R-13) |
| `core/maintenance.py`, `agent/steps/maintenance.py`, `platform/scheduler.py` (tarefas do usuário e nativas) | Manutenção (V2-18): especificação pura da tarefa do winget, otimização nativa do disco, Sensor de Armazenamento como ajuste |
| `data/presets.yaml`, `core/presets.py` | Perfis rápidos (V2-15): aplicar = mesclar (D-040), a prévia usa a mesma função numa cópia |
| `core/fonts.py`, `collector/fonts.py`, `platform/fonts.py`, `agent/steps/font.py` | Fontes (V2-07): leitor da tabela `name`, cópia ao marcar, instalação sem sobrescrever (`_winkit`) |
| `data/file_associations.yaml`, `core/associations.py`, `platform/associations.py`, `collector/associations.py`, `agent/steps/default_apps.py` | Apps padrão (V2-05): XML do `dism` inteiro no pendrive, filtrado por grupo na hora; importação só na Fase 1; conferência do `UserChoice` na Fase 2 |
| `data/personal_settings.yaml`, `core/personal.py`, `collector/personal.py`, `platform/personal.py`, `agent/steps/personal.py` | Aparência pessoal (V2-06, D-037): só valores do catálogo, validados na captura; papel de parede em `%SystemRoot%\Web\Wallpaper\WinKit` |
| `data/browsers.yaml`, `data/extensions.yaml`, `data/search_providers.yaml`, `core/browsers.py`, `collector/browsers.py`, `platform/browsers.py`, `agent/steps/browser.py` | Navegadores prontos (V2-12, D-038): receita → operações tipadas de registro por navegador e modo; leitura só de ids e nomes de extensões; desfazer só o que o WinKit grava |
| `core/start_layout.py`, `collector/start_layout.py`, `agent/steps/start_layout.py` | Iniciar e barra (V2-04): `LayoutModification.xml`/`.json` no perfil Default (snapshots), `start2.bin` só no mesmo build; XML com prefixos literais, sem `register_namespace` |
| `core/volumes.py`, `platform/volumes.py` | Resolver de volumes (D-035, R-52): pelo serial do CIM `Win32_Volume`, letra atual só para montar caminhos |
| `core/user_folders.py`, `collector/user_folders.py`, `agent/steps/user_folders.py` | Pastas do usuário em outro disco (V2-14): `User Shell Folders` com `%USERNAME%`; "Copiar agora" só em `merge` |
| `core/vdf.py`, `core/games.py`, `collector/games.py`, `agent/steps/game_library.py` | Jogos sem baixar de novo (V2-13): `libraryfolders.vdf` da Steam e manifestos da Epic |
| `agent/steps/account.py`, `platform/accounts.py` | Contas extras (V2-11): `LocalAccount` no XML, grupo conferido pelo SID, `PasswordExpired`; nunca ao vivo |
| `core/share.py`, `data/templates/*.winkit.json` | Receitas compartilháveis e modelos (V2-23, D-040): formato sem campos pessoais (`extra="forbid"`), importar = mesclar com prévia |
| `core/inventory_snapshot.py`, `core/compare.py`, `platform/snapshot.py`, `collector/snapshot.py`, `agent/steps/compare.py` | Relatório antes/depois (V2-19): o mesmo retrato (apps, dispositivos, recursos) do PC antigo e do Windows novo, comparado por id do winget, nome normalizado e HardwareID |
| `core/userassist.py`, `core/suggest.py`, `platform/usage.py`, `collector/suggest.py`, `data/game_saves.yaml` | Assistente "o que levar" (V2-20): sinais locais (UserAssist, inventário, catálogo, saves, pastas da raiz), pontuação pura e determinística; nada é adicionado sem escolha |
| `core/versions.py`, `collector/app_updates.py` | Atualizar instaladores do pendrive (V2-21, D-041): baixar para comparar; a pasta velha só sai depois que a receita aponta para a nova |
| `core/secrets.py` | Registro único de segredos do processo (R-53); `runner` e `EventLog` mascaram |
| `core/wifi.py`, `collector/wifi.py`, `platform/wifi.py`, `agent/steps/wifi.py` | Wi-Fi (V2-02): XML do perfil, coleta, `netsh` só por código de saída e arquivos, etapa antes do login |
| `core/media.py` | Pendrive comum (D-034): reconhecer a mídia de instalação, marcar o `autounattend.xml` do WinKit |
| `builder/target.py` | Destino com tipo `ventoy` ou `setup`; lista os dois tipos de pendrive |
| `agent/integrity.py` | Confere arquivo ou pasta do pendrive contra o `manifesto.json` (R-22) |
| `agent/fakes.py`, `platform/fakes/services.py` | Fábricas de serviços falsos (um lugar só para acrescentar campos) |
| `agent/reboot.py`, `steps/windows_update.py` | Política de reinício; Windows Update |
| `agent/steps/tweak.py`, `steps/system.py` | Motor de ajustes (onde gravar conforme o alvo); bloatware, energia, nome do PC |
| `agent/steps/*.py` | Uma classe por tipo de etapa: `DriverStep`, `BloatStep`, `TweakStep`, `BackupStep`, `AppStep`, `ShortcutStep`, `WindowsUpdateStep`, `CleanupStep` |
| `studio/controller.py` | Fachada do Studio sem Qt: pendrive, receita, apps, drivers, backups, plano, construir |
| `studio/ui/` (`base.py`, `window.py`, `pages/{common,prepare,bring,system,finish}.py`), `studio/main.py` | GUI do Studio: barra lateral agrupada com busca (D-042), uma página por seção, tarefas em segundo plano, troca de idioma e tema sem reiniciar |
| `studio/preferences.py` | Preferências do Studio (idioma, tema) em `%APPDATA%\WinKit\studio.json` |
| `platform/locale.py` | Idioma de exibição do Windows (`GetUserDefaultUILanguage`) para o modo automático (D-030) |
| `agent/ui/qt.py` | Janela da Fase 2 (Início, Progresso, Concluído), diálogo de reinício, bandeja; ponte entre threads (import tardio) |
| `ui/theme.py`, `ui/widgets.py` | Kit visual compartilhado estilo macOS (D-026) |

---

## 4. Contratos centrais

### 4.1 Etapa do Agente

```python
class Step(Protocol):
    id: str                      # "app:7zip"
    kind: StepKind
    phase: Literal[1, 2]
    needs_pendrive: bool
    needs_network: bool

    def check(self, ctx: StepContext) -> bool:
        """True se o efeito desejado já existe. Não pode ter efeito colateral."""

    def run(self, ctx: StepContext) -> StepResult:
        """Produz o efeito. Precisa ser seguro rodar de novo após uma falha no meio."""

    live_safe: bool              # desde o M12 (R-54): pode rodar num Windows em uso?

    def preview(self, ctx: StepContext) -> PreviewItem:
        """O que run() faria, sem efeito colateral (modo "aplicar neste PC", D-033)."""
```

Desde o M12 as etapas herdam `StepBase` (`agent/steps/base.py`): `live_safe = True` e uma prévia padrão a partir de `check()`; etapas com prévia própria (backup: arquivos novos × mantidos) sobrescrevem `preview`. `StepContext.mode` diz se é instalação (`install`) ou modo ao vivo (`live`).

`StepResult`: `ok`, `reboot_required`, `skipped(reason)`, `failed(reason, recoverable)`. O executor nunca deixa uma exceção de uma etapa derrubar o Agente: captura, registra, marca `failed` e segue (P4 do plano).

### 4.2 Executor

```
para cada etapa do plano na fase atual, em ordem:
    se estado[etapa] == done: continua
    se dependência não está done: marca skipped("dependência falhou") e continua
    se needs_pendrive e pendrive ausente: espera (11.6 do plano)
    se check(): marca done ("já estava feito") e continua
    marca running (grava estado)
    resultado = run()
    grava estado conforme resultado
    se reboot_required: aplica política de reinício
```

### 4.3 Planejador

`plan(recipe: Recipe, catalogs: Catalogs, ctx: PlanContext) -> Plan` — função pura e determinística: a mesma entrada gera exatamente o mesmo plano (ordenação estável por `order`, depois por `id`). `PlanContext` contém: modo de execução efetivo, se a Fase 1 rodou (para o fallback), build do Windows de destino.

### 4.4 Execução de comandos

```python
runner.run(
    args: Sequence[str],          # nunca string única
    *, timeout: float,            # obrigatório
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    log_to: Path | None = None,
) -> CommandResult               # args, exit_code, stdout(bytes), stderr(bytes), duration
```

---

## 5. Regras do código

### 5.1 Linguagem e idioma

- **R-01** Python 3.12. Nada de recursos de versões mais novas.
- **R-02** Identificadores (variáveis, funções, classes, módulos, chaves JSON da receita) em **inglês**.
- **R-03** Todo texto exibido ao usuário (CLI, GUI, notificações, resumo, motivos das etapas, avisos da validação e do Construtor) em **pt-BR, en-US e es**, e **somente** em `winkit/i18n/messages/*.py` e `winkit/i18n/catalogs/*.yaml` (D-030). Nenhuma string de interface solta pelo código. Exceções documentadas: mensagens técnicas de exceção e linhas livres do log (`agente.log`), que ficam em pt-BR (DT-016), e o log técnico do `bootstrap.ps1`.
- **R-04** Documentação, comentários e mensagens de commit em pt-BR. Exceções: `README.en.md`, `README.es.md`, notas da release e `NOTICE` (trilíngue).
- **R-05** Nomes de arquivo e pasta gravados no pendrive: só `[a-z0-9-_.]`, exceto os que o Windows/Ventoy exigem (`ventoy.json`, `SetupComplete.cmd`).

### 5.2 Estilo e tipos

- **R-06** `ruff format` e `ruff check` sem avisos. Configuração única no `pyproject.toml`.
- **R-07** Anotação de tipos em toda função. `mypy --strict` em `core/`; `mypy` padrão nos demais.
- **R-08** Sem `Any` em `core/`, exceto na fronteira de parse de JSON/YAML, imediatamente validado por Pydantic.
- **R-09** Dados que atravessam módulos são modelos Pydantic (`frozen=True` quando possível) ou `dataclass(frozen=True)`. Nada de `dict` solto entre camadas.
- **R-10** Funções curtas e com um propósito. Comentário explica **por quê**, não **o quê**. Comentário obrigatório onde há comportamento do Windows não óbvio, com link para a fonte.

### 5.3 Efeitos colaterais e sistema

- **R-11** `subprocess` só em `platform/runner.py`. Sempre lista de argumentos, nunca `shell=True`, sempre `timeout`.
- **R-12** Executáveis do sistema chamados por **caminho absoluto** (`%SystemRoot%\System32\robocopy.exe`), resolvido em `platform/`. Nunca depender do `PATH`.
- **R-13** **Nunca interpretar texto localizado** de ferramentas (`pnputil`, `robocopy`, `reg`, `winget list`, `dism`...). Usar código de saída, JSON (PowerShell `ConvertTo-Json`), CIM ou registro. O Windows do usuário é pt-BR e o texto muda entre idiomas e versões.
- **R-14** PowerShell só via `platform/powershell.py` (força UTF-8, `$ErrorActionPreference='Stop'`, saída JSON). Valores vindos do Python entram no script como **parâmetros**, nunca por interpolação de string.
- **R-15** Caminhos com `pathlib.Path`. Acesso a arquivo no Windows sempre via `platform.fs` (prefixo `\\?\` para caminhos longos). Nunca escrever `C:\` fixo: usar Known Folders ou variáveis de ambiente.
- **R-16** Escrita de `receita.json`, `estado.json`, `manifesto.json`, `ventoy.json` e `winkit.marker` sempre **atômica** (arquivo temporário na mesma pasta + `os.replace`).
- **R-17** Recursos abertos (hive carregado, cópia de sombra, ISO montada, link simbólico temporário) sempre liberados em `try/finally` ou gerenciador de contexto, inclusive em erro.

### 5.4 Segurança de dados

- **R-18** Nunca gerar XML com `DiskConfiguration` ou `ImageInstall/OSImage/InstallTo`. Teste de proteção obrigatório.
- **R-19** **Modo Ventoy:** o Construtor só escreve em `WinKit\` e em `ventoy\script\winkit-*.xml`, e só mescla `ventoy\ventoy.json`. **Modo pendrive comum (D-034, M13):** só escreve em `WinKit\`, `\autounattend.xml` e, uma vez, `\autounattend.xml.winkit-bak`; e, se o Rufus deixou respostas em `sources\$OEM$\$$\Panther\unattend.xml`, as move para `unattend.xml.winkit-bak` na mesma pasta (H17). Qualquer escrita fora disso é bug (teste `tests/builder/test_setup_media.py`).
- **R-20** `robocopy /MIR` só é permitido com destino dentro de `WinKit\Perfis\<perfil>\Backups\<id>\dados\`. A função que chama `/MIR` valida o destino e lança `UnsafeOperationError` se não for.
- **R-21** Restauração usa `merge` salvo escolha explícita na receita.
- **R-22** Instaladores, drivers e o Agente têm SHA-256 conferido contra o `manifesto.json` antes de serem executados/instalados.
- **R-23** Senhas nunca aparecem em log. O `runner` aceita uma lista de argumentos sensíveis que são mascarados como `***` no log.
- **R-24** XML gerado só com `xml.etree.ElementTree`, nunca concatenando strings (escape correto de `&`, `<`, aspas em nomes de usuário etc.).

### 5.5 Erros

- **R-25** Hierarquia em `core/errors.py`, com raiz `WinKitError`. Subclasses principais: `RecipeError`, `CatalogError`, `PlatformError` (→ `CommandError`, `PowerShellError`, `RegistryError`, `VssError`), `PendriveError`, `UnsafeOperationError`, `StepError`.
- **R-26** Nunca `except Exception: pass`. Toda exceção capturada é registrada com contexto (etapa, comando, caminho) ou relançada.
- **R-27** Mensagem de erro para o usuário diz **o que aconteceu** e **o que fazer** (via `i18n`). Detalhe técnico vai para o log.
- **R-28** No Agente, falha de uma etapa nunca derruba as outras (executor, 4.2). No `bootstrap.ps1`, nada pode sair com código diferente de 0.

### 5.6 Idempotência e retomada

- **R-29** Toda etapa do Agente tem `check()` sem efeito colateral e `run()` seguro para repetir.
- **R-30** O estado é gravado **antes** (`running`) e **depois** (`done`/`failed`) de cada etapa.
- **R-31** O pendrive é sempre localizado pelo marcador (`pendrive_id`), nunca pela letra de unidade.

### 5.7 Dados versus código

- **R-32** Listas que mudam com o Windows ou com os apps (bloatware, ajustes, switches, pastas conhecidas, chaves genéricas, padrões DPAPI) ficam em `src/winkit/data/*.yaml`, nunca no código.
- **R-33** Todo ajuste em `tweaks.yaml` tem `source` (referência) e `undo`.
- **R-34** Ajustes só usam operações tipadas (`reg_set`, `reg_delete_value`, `reg_delete_key`, `service_start_type`, `optional_feature_disable`, `powercfg`, `appx_remove`). Não existe operação de comando arbitrário.

### 5.8 Interface

- **R-35** PySide6 só em `studio/ui/` e `agent/ui/`. A Fase 1 nunca importa Qt (teste de proteção).
- **R-36** A interface não contém lógica de negócio: chama os mesmos serviços do CLI.
- **R-37** Operações demoradas na GUI rodam fora da thread de interface (`QThread`/`QRunnable`), com progresso e cancelamento quando possível.

### 5.9 Testes

- **R-38** Todo código novo vem com teste. `core` ≥ 90% de cobertura; `collector`/`builder`/`agent` ≥ 80%.
- **R-39** Testes de `platform` que tocam o sistema real são marcados `@pytest.mark.windows` e só rodam no Windows.
- **R-40** Saídas reais de comandos (JSON do PowerShell, `winget export`, `ventoy.json` de exemplo) ficam gravadas em `tests/fixtures/` e são a base dos fakes.
- **R-41** Testes de proteção (seção 19.2 do plano) não podem ser removidos nem marcados como `skip`.
- **R-42** XML e `ventoy.json` gerados têm teste de snapshot; atualizar um snapshot exige explicar a mudança no commit.

### 5.10 Dependências

- **R-43** Dependências permitidas em produção: `pydantic`, `PyYAML`, `PySide6`. Em desenvolvimento: `pytest`, `pytest-cov`, `ruff`, `mypy`, `import-linter`, `pyinstaller`, `types-PyYAML`.
- **R-44** Adicionar dependência exige uma decisão nova na seção 6.
- **R-45** Versões travadas em `uv.lock`.

### 5.11 Versionamento e commits

- **R-46** Versão do produto em semver, definida só em `winkit/__init__.py`. Studio e Agente gravados no mesmo pendrive têm sempre a mesma versão.
- **R-47** `schema_version` de receita, estado e manifesto são inteiros independentes; mudança incompatível exige migração e teste da migração.
- **R-48** Commits pequenos, mensagem em pt-BR no imperativo, citando o marco: `M1: adiciona planejador de fases`.
- **R-49** Todo commit atualiza `docs/CHANGELOG.md`, e os demais documentos vivos quando aplicável (ver `CLAUDE.md`).
- **R-50** Marcação de pendência no código só no formato `TODO(DT-nnn): ...`, citando uma entrada existente em `DIVIDAS_TECNICAS.md`. Um teste falha se encontrar `TODO` sem referência válida.

### 5.11a Regras da v2 (`PLANO_V2.md` §4)

- **R-51** Toda chave de mensagem existe nos três idiomas, com os mesmos marcadores `{x}` e as mesmas formas de plural. Toda chave usada no código existe; toda chave existente é usada (com lista explícita de prefixos dinâmicos). Em vigor desde o M11.
- **R-52** Volumes fora do disco do sistema são referenciados só por `VolumeRef` (número de série, D-035). Nenhum campo da receita guarda letra de unidade fixa, salvo `letter_hint` e `{ABS:...}`. Em vigor desde o M16.
- **R-53** Arquivos e valores com segredo (senhas de Wi-Fi, senhas de contas) ficam num registro único (`core/secrets.py`); o `runner`, o `EventLog` e o resumo os mascaram. Em vigor desde o M14.
- **R-54** Toda etapa do Agente declara `live_safe` e implementa `preview()` sem efeito colateral. Em vigor desde o M12.
- **R-55** Strings de interface só aparecem dentro de `t(...)`, `tn(...)` ou `Msg(...)`: nenhum literal de texto passado a `label`, `button`, `Row`, `section`, `setText`, `setWindowTitle`, `setToolTip`, `QMessageBox.*`, `help=`/`description=` do `argparse` nem a `out()`/`print()` da CLI. Em vigor desde o M11.
- **R-56** Toda mudança que altera o que o README descreve (funções, requisitos, comandos, estado do projeto, aviso) atualiza os READMEs no mesmo commit, nos três idiomas. O `README.md` traz a versão em inglês logo abaixo da portuguesa, gerada do `README.en.md` por `scripts/sync_readme.py`; o começo do `README.md` avisa que ela existe. Em vigor desde 2026-10-31.
- **R-57** `docs/ESTRUTURA.md` descreve a árvore do projeto e cada arquivo de código. É gerado por `scripts/gen_estrutura.py` a partir das docstrings (todo módulo tem docstring) e regerado no mesmo commit que cria, move, remove ou muda a descrição de um arquivo. Em vigor desde 2026-10-31.
- **R-58** Toda tarefa de código usa a skill `ponytail` (`.claude/skills/`, cópia de github.com/DietrichGebert/ponytail, MIT). Em conflito, valem as regras deste documento e do `CLAUDE.md` (documentos vivos, pt-BR, cobertura da R-38); `shortcut:` exige entrada em `DIVIDAS_TECNICAS.md`, como `TODO` (R-50). Em vigor desde 2026-11-01.
- **R-59** Nenhuma leitura lenta do sistema (PowerShell, CIM, varredura de disco, rede) roda na thread da interface: o `refresh()` de uma página lê o cache do controlador (`Page.slow`) e o resto carrega em segundo plano (D-054). Em vigor desde o M19.

### 5.12 Como as regras são verificadas automaticamente

| Regra | Verificação |
|---|---|
| Camadas (seção 2) | import-linter (`pyproject.toml`, 5 contratos) + `tests/test_architecture.py` (pega imports dentro de funções) |
| R-06 | `ruff check` e `ruff format --check` no CI |
| R-07 | `mypy` no CI e no `scripts/check.sh`, duas vezes: plataforma atual e `--platform win32` (IN-010); `strict` em `winkit.core` |
| R-11 | contrato "subprocess só em platform.runner" + teste AST de `shell=` |
| R-35 | `test_phase1_does_not_import_qt` |
| R-50 | `test_todo_requires_debt_entry` |
| R-51 | `tests/i18n/test_parity.py` (chaves, marcadores, plurais) e `tests/i18n/test_usage.py` (toda chave usada existe; toda chave existente é usada) |
| R-53 | `tests/agent/test_wifi.py::test_wifi_password_never_logged` (a senha da fixture não aparece em log, estado nem resumo) |
| R-54 | `tests/agent/test_live.py::test_preview_never_writes` (todo serviço de escrita falha durante a prévia) |
| D-002 (V2-08) | `tests/agent/test_features.py::test_iso_is_dismounted_even_when_enabling_fails` (a ISO é sempre desmontada) |
| `hosts` (V2-16) | `tests/agent/test_network_privacy.py::test_hosts_block_roundtrip_keeps_user_bytes` (CRLF, LF, BOM, Latin-1) e `test_catalogs_are_safe` (nenhum domínio da Microsoft) |
| R-42 (V2-04) | `tests/agent/test_start_layout.py` — snapshots de `LayoutModification.xml` e `.json` em `tests/fixtures/start_layout/` |
| R-52 | `tests/agent/test_user_folders.py::test_recipe_rejects_drive_letters_in_volume_paths` (caminhos de volume nunca levam letra) |
| V2-23 | `tests/core/test_share.py::test_export_never_contains_personal_data` (conta, senha, Wi-Fi, caminhos e volumes nunca saem) |
| V2-21 | `tests/core/test_app_updates.py::test_failure_in_the_middle_keeps_old_version` |
| V2-20 | `tests/collector/test_suggest.py::test_dismissed_never_come_back_and_accept_adds` (ignoradas não voltam; nada entra sem "Adicionar") |
| XML (IN-015) | `test_no_global_xml_namespace_registration` e `test_strip_key_does_not_change_other_xml` |
| R-55 | `tests/i18n/test_usage.py::test_no_loose_ui_strings` (AST em `studio`, `agent/ui`, `ui`, `cli`) |
| R-50, R-58 | `test_todo_requires_debt_entry` também cobre `shortcut:` |
| R-59 | `tests/ui/test_responsive.py` (com leituras de 2 s, toda página abre em menos de 0,5 s no CI) |
| R-56, R-57 | `tests/test_docs_sync.py` (README.md com a versão em inglês igual ao README.en.md; ESTRUTURA.md igual ao que o gerador produz) |
| Empacotamento | `test_no_dynamic_imports_in_package` (IN-013) |

---

## 6. Registro de decisões

Formato: **D-nnn — título** · data · status (`aceita`, `substituída por D-xxx`, `revogada`). Decisões nunca são apagadas; quando mudam, ganham status novo e uma decisão nova é criada.

### D-001 — Conteúdo pesado mora no pendrive (Modo B)
2026-10-31 · aceita
**Contexto:** embutir apps, drivers e backups na ISO exige regravar 6–10 GB a cada mudança e torna a ISO enorme.
**Decisão:** todo conteúdo pesado fica em `WinKit\` no pendrive Ventoy.
**Consequências:** a instalação depende do pendrive estar conectado; uma pasta serve a todas as ISOs; atualizar um instalador leva segundos.

### D-002 — A ISO nunca é modificada
2026-10-31 · aceita
**Contexto:** com D-001, a única coisa que iria para a ISO seria o `autounattend.xml`; o plugin `auto_install` do Ventoy injeta esse arquivo sem alterar a ISO.
**Decisão:** o WinKit nunca regrava, converte ou altera ISO/WIM/ESD.
**Consequências:** sem dependência de ADK/`oscdimg`/`xorriso`; trocar a ISO por uma mais nova não exige nada; o fluxo só funciona via Ventoy; depende de H1.

### D-003 — Python 3.12 + PySide6
2026-10-31 · aceita
**Contexto:** o desenvolvimento acontece num ambiente Linux; a maior parte da lógica precisa ser testável fora do Windows.
**Decisão:** Python 3.12, PySide6 para interface, empacotamento PyInstaller.
**Consequências:** executáveis grandes (~80–150 MB com Qt), aceitável num pendrive de 100 GB; possível desconfiança de antivírus (H7).

### D-004 — Motor primeiro, interface depois
2026-10-31 · aceita
**Decisão:** M0–M9 entregam o motor por linha de comando (e a janela do Agente no M9); o Studio gráfico vem no M10.
**Consequências:** até o M10, a seleção de itens é feita editando a receita ou por comandos do CLI.

### D-005 — Backup em pasta crua
2026-10-31 · aceita
**Contexto:** ZIP seria mais rápido e verificável; o usuário prefere poder ver e editar os arquivos.
**Decisão:** backups ficam como pastas normais em `Backups\<id>\dados\`.
**Consequências:** tratamento de caminhos longos, FAT32 e muitos arquivos pequenos (7.4.3 do plano); backups não têm verificação por hash; depende de H8.

### D-006 — Captura com cópia de sombra (VSS)
2026-10-31 · aceita
**Decisão:** a captura lê de uma cópia de sombra do volume para copiar arquivos em uso.
**Consequências:** o Studio roda como administrador; só funciona em NTFS interno (fallback de cópia direta); depende de H6.

### D-007 — Restauração mescla sem sobrescrever
2026-10-31 · aceita
**Decisão:** padrão `merge` (copia só o que não existe no destino); `overwrite` e `skip` por item.

### D-008 — Modo de início configurável
2026-10-31 · aceita
**Decisão:** a receita define `silent`, `countdown` ou `interactive`.

### D-009 — Fases mescladas
2026-10-31 · aceita
**Decisão:** tudo o que é possível roda antes do login (Fase 1, SYSTEM); o resto roda depois do login, em segundo plano ou com janela (Fase 2). O planejador decide a fase de cada etapa; itens `decide_at_runtime` vão para a Fase 2 nos modos com janela.

### D-010 — Sem teste em VM no produto
2026-10-31 · aceita
**Decisão:** o produto não oferece teste da ISO em máquina virtual.

### D-011 — Atualizações: só a opção leve
2026-10-31 · aceita
**Decisão:** a receita liga ou desliga o Windows Update durante e depois da instalação; não há integração de atualizações na imagem.

### D-012 — Fase 1 via `SetupComplete.cmd`, Fase 2 via tarefa agendada, com fallback
2026-10-31 · aceita
**Decisão:** `bootstrap.ps1` (etapa *specialize*) cria o `SetupComplete.cmd` e a tarefa `\WinKit\Fase2` (gatilho no logon, grupo Administradores, privilégio máximo). Se a Fase 1 não rodar, a Fase 2 executa as etapas pendentes dela redirecionadas ao perfil real.
**Consequências:** cobre o risco H3 sem depender dele.

### D-013 — Agente copiado para o disco local
2026-10-31 · aceita
**Decisão:** o Agente roda de `C:\ProgramData\WinKit\Agent\`, não do pendrive.
**Consequências:** reinicializações e mudança de letra não quebram o Agente; o pendrive só é necessário para o conteúdo.

### D-014 — Cópias com robocopy
2026-10-31 · aceita
**Decisão:** captura e restauração usam `robocopy` (nativo, caminhos longos, tentativas, exclusões, modos de conflito via `/XC /XN /XO`).
**Consequências:** resultado lido só pelo código de saída (R-13).

### D-015 — PyInstaller em modo onedir
2026-10-31 · aceita
**Decisão:** onedir, nunca onefile.
**Consequências:** mais rápido, menos alarmes de antivírus; uma pasta em vez de um `.exe` único.

### D-016 — Edição escolhida por chave genérica de instalação
2026-10-31 · aceita
**Decisão:** a edição vem de `src/winkit/data/editions.yaml` (chaves públicas de instalação da Microsoft), não de `InstallFrom` com índice de imagem.
**Consequências:** não exige configuração de disco no XML (R-18); não ativa o Windows.

### D-017 — Nunca automatizar a escolha de disco
2026-10-31 · aceita
**Decisão:** o usuário sempre escolhe o disco/partição no instalador.
**Consequências:** a instalação não é 100% sem toque, em troca de nunca apagar o disco errado.

### D-018 — Identificadores em inglês, textos em pt-BR
2026-10-31 · alterada por D-030
**Decisão:** R-02 a R-04. Desde o M11, os textos ao usuário existem em pt-BR, en-US e es (D-030).

### D-019 — Documentos vivos e CHANGELOG obrigatórios
2026-10-31 · aceita
**Contexto:** pedido do usuário: a arquitetura, o andamento, as dívidas técnicas, o que deu errado e o mapa de mudanças devem estar sempre documentados.
**Decisão:** `ARQUITETURA.md`, `STATUS.md`, `DIVIDAS_TECNICAS.md`, `INCIDENTES.md` e `CHANGELOG.md` são atualizados no mesmo commit da mudança (`CLAUDE.md`, R-49).

### D-020 — Criptografia automática do dispositivo desligada por padrão
2026-10-31 · aceita
**Contexto:** pedido do usuário. O Windows 11 liga a criptografia automática do disco, inclusive quando uma conta Microsoft é adicionada depois da instalação; o usuário não quer isso por padrão.
**Decisão:** `windows.prevent_device_encryption` é `true` por padrão em toda receita. O XML grava `HKLM\SYSTEM\CurrentControlSet\Control\BitLocker\PreventDeviceEncryption = 1` na etapa *specialize*, antes da OOBE.
**Consequências:** o disco não é criptografado automaticamente em nenhum momento; o BitLocker manual continua disponível. Quem quiser o comportamento padrão do Windows desmarca a opção na receita.

### D-021 — Catálogos dentro do pacote Python
2026-10-31 · aceita
**Contexto:** o plano previa `data/` na raiz do repositório, incluído no pacote por configuração do empacotador. O CI falhou porque a pasta vazia não existe no git (IN-001), e o PyInstaller exigiria a mesma configuração duplicada.
**Decisão:** os catálogos ficam em `src/winkit/data/` e são lidos com `importlib.resources`.
**Consequências:** um único lugar, funciona igual em desenvolvimento, no pacote instalado e no executável.

### D-022 — `core` pode ler e gravar arquivos comuns
2026-10-31 · aceita
**Contexto:** "puro" foi definido como "sem Windows, sem Qt, sem subprocess". O manifesto (hashes) e a leitura dos catálogos precisam ler arquivos.
**Decisão:** `core` pode usar `pathlib`/`hashlib`/`importlib.resources` para ler e gravar arquivos comuns, porque isso é portável e testável no Linux. Continua proibido: APIs específicas do Windows, registro, processos, Qt.

### D-023 — Três caminhos para iniciar o Agente
2026-10-31 · aceita
**Contexto:** a Fase 1 depende do `SetupComplete.cmd` (H3) e a Fase 2 de uma tarefa agendada criada na etapa *specialize*, quando não se sabe se o serviço de agendamento já está disponível.
**Decisão:** (1) `SetupComplete.cmd` → Fase 1; (2) tarefa `\WinKit\Fase2` registrada pelo bootstrap **e** garantida de novo pelo Agente; (3) `FirstLogonCommands` no XML inicia a Fase 2 com `cmd /c start` (não bloqueia a área de trabalho). A trava de instância única do Agente torna as execuções repetidas inofensivas.
**Consequências:** a Fase 2 começa mesmo se um dos mecanismos falhar; a Fase 1 que não rodou é coberta pelo fallback de D-012.

### D-024 — Resumo em HTML estático e remoção condicional do Agente
2026-10-31 · aceita
**Contexto:** o plano previa apagar o Agente no fim (§10.4), mas o resumo tem botão "tentar de novo" e um atalho na área de trabalho; e um executável não consegue apagar a própria pasta enquanto roda.
**Decisão:** o resumo é gravado como `resumo.html` (estático, abre sem o Agente) e `resumo.json`. A pasta do Agente só é removida se nada falhou, por um comando em `HKLM\...\RunOnce` executado no próximo login. Com falhas, o Agente fica para permitir `winkit-agent.exe retry`.
**Consequências:** sem falhas, nada do WinKit sobra além de `C:\ProgramData\WinKit\Logs`, `estado.json` e o resumo.

### D-025 — Pacote de distribuição em duas pastas onedir
2026-10-31 · aceita
**Decisão:** `WinKit-<versão>\winkit\` (CLI, com console, sem Qt) e `WinKit-<versão>\winkit-agent\` (Agente, sem console). O `construir` copia `winkit-agent` para o pendrive automaticamente quando roda a partir do pacote. O CI gera o pacote no Windows e o testa com os executáveis prontos.

### D-026 — Interface no estilo macOS
2026-10-31 · aceita
**Contexto:** pedido do usuário: "uma interface bonita, bem feitinha, estilo Mac".
**Decisão:** kit visual próprio em `winkit/ui` (folha de estilo gerada de tokens de cor claro/escuro, inspirada no "Ajustes do Sistema"): barra lateral, listas agrupadas em cartões arredondados, chaves animadas, botões em pílula com o azul de destaque, títulos grandes, ícones de símbolo em quadrados coloridos. A moldura da janela continua a do Windows (sem imitar os botões de semáforo do Mac). Fonte: Segoe UI Variable/Segoe UI no Windows.
**Consequências:** o mesmo kit serve ao Agente e ao Studio; o import-linter garante que o kit não dependa de casos de uso nem da plataforma.

### D-027 — Studio como executável próprio, com elevação
2026-10-31 · aceita
**Contexto:** ler ISOs, drivers e copiar arquivos em uso exige administrador; o usuário vai usar a GUI.
**Decisão:** `winkit-studio.exe` (janela, `uac_admin=True` no PyInstaller) ao lado de `winkit.exe` (CLI) e `winkit-agent`. Ícone único gerado a partir do desenho do kit visual. O CI abre o Studio empacotado com `--teste-fumaca`.
**Consequências:** o pacote tem três pastas onedir; Studio e Agente carregam o Qt cada um (~200 MB no total), aceitável num pendrive de 100 GB.

### D-028 — Código aberto sob Apache-2.0, com aviso de "100% vibe-codado"
2026-10-31 · aceita
**Contexto:** o dono vai publicar o repositório como código aberto e escolheu a licença Apache 2.0. Todo o código foi escrito por IA e ainda não foi validado em instalação real; o dono não quer nenhuma responsabilidade pelo uso.
**Decisão:** `LICENSE` com o texto da Apache-2.0; `NOTICE` com direitos autorais e o aviso de isenção ("pré-alpha, projeto pessoal, quem usa é testador; 100% vibe-codado, uso por conta e risco, toda a responsabilidade é de quem usa"). O mesmo aviso aparece em destaque no README, no `LEIA-ME.txt` do pacote (que leva também `LICENSE` e `NOTICE`) e numa seção "Aviso" da primeira página do Studio (chaves `studio.disclaimer.*`, nos três idiomas).
**Consequências:** o aviso acompanha o programa, não só o repositório. Contribuições entram sob a mesma licença (seção 5 da Apache-2.0). O PySide6 (LGPL) continua compatível, porque é usado como biblioteca dinâmica.

### D-029 — Releases prontas para baixar, publicadas por tag
2026-10-31 · aceita
**Contexto:** o dono quer que as pessoas baixem o programa já compilado, sem precisar do código.
**Decisão:** o workflow `release.yml` roda ao enviar uma tag `vX.Y.Z` (que precisa bater com `winkit.__version__`) ou à mão (`workflow_dispatch`, que cria a tag `v<versão>` no commit; recusa se a release já existir): testes, `packaging\build.ps1`, `packaging\smoke.ps1` (o mesmo teste de fumaça do CI), `.zip` com SHA-256 e `gh release create` com `packaging/NOTAS_DA_VERSAO.md`. Enquanto a validação em VM não terminar, as versões saem como **pré-lançamento**, com o título "pré-alpha".
**Consequências:** publicar uma versão = subir `__version__`, registrar no CHANGELOG e enviar a tag. Os executáveis não são assinados (DT-001), então o SmartScreen pode avisar; as notas explicam.

### D-030 — Interface em três idiomas, com o português como base
2026-10-31 · aceita
**Contexto:** projeto público; pedido do dono de inglês e espanhol.
**Decisão:** idiomas `pt-BR` (base), `en-US` e `es` (espanhol neutro, "tú"). Mensagens em `winkit/i18n/messages/{pt_br,en_us,es}.py` com as mesmas chaves e marcadores (R-51); textos dos catálogos YAML traduzidos por arquivos `winkit/i18n/catalogs/{en_us,es}.yaml`. Idioma: Studio = preferência salva ou idioma do Windows; CLI = `--idioma`, `WINKIT_LANG` ou idioma do Windows; Agente = `execution.language` da receita (`auto` = idioma do Windows novo).
**Consequências:** R-03, R-04 e D-018 mudam; `winkit.i18n` vira camada pura com contrato próprio no import-linter. Detalhes em `PLANO_V2.md` §3 e §6.

### D-031 — Mensagens estruturadas (`Msg`) no que é guardado
2026-10-31 · aceita
**Decisão:** `Msg(key, params)` (`winkit/i18n/msg.py`, reexportado por `core/text.py`) substitui texto pronto em `StepResult.message`, `StepState.error/reason`, `AgentState.warnings` e `SummaryItem.detail`. O texto é montado só na borda (interface, log, HTML). O estado sobe para `schema_version: 2`, com migração (R-47). Títulos do plano continuam texto pronto, porque o plano é recalculado no idioma atual e nunca é gravado.

### D-032 — Comandos da CLI em português, com apelidos em inglês
2026-10-31 · aceita
**Decisão:** nomes atuais mantidos; apelidos em inglês via `aliases`; ajuda e saída no idioma escolhido. Sem apelidos em espanhol.

### D-033 — Modo "aplicar neste PC" com prévia e ponto de restauração antes
2026-10-31 · aceita
**Decisão:** comando `winkit-agent apply`; prévia sempre antes (`preview()` sem efeito colateral, R-54); ponto de restauração antes, ligado por padrão; etapas declaram `live_safe`; estado separado por aplicação. Detalhes em `PLANO_V2.md` §7.2.

### D-034 — Pendrive comum: só `autounattend.xml` na raiz e `WinKit\`
2026-10-31 · aceita
**Decisão:** pendrive gravado pelo Rufus ou pela Ferramenta de Criação de Mídia é reconhecido pelos arquivos do instalador (sem `VTOYEFI`); o Construtor escreve só `\autounattend.xml` (com cópia `.winkit-bak` uma vez) e `\WinKit\`. O WinKit nunca embute nem chama o Rufus. Detalhes em `PLANO_V2.md` §8.

### D-035 — Volumes pelo número de série, nunca pela letra
2026-10-31 · aceita
**Decisão:** `VolumeRef(serial, label, letter_hint, size)`; serial de `Win32_Volume.SerialNumber`; no destino, a letra atual é usada para montar caminhos; volume ausente = etapa pulada; nunca se troca letra (R-52).

### D-036 — Dados sensíveis novos fora da receita
2026-10-31 · aceita
**Decisão:** senhas de Wi-Fi em arquivos próprios no perfil, nunca na receita nem em log; registro de segredos mascarado (R-53); aviso permanente no Studio e opção de levar a rede sem a senha.

### D-037 — Configurações pessoais por catálogo curado
2026-10-31 · aceita
**Decisão:** valores do `HKCU` só a partir de `personal_settings.yaml` (chave, tipo, faixa, fonte); nada de `.reg` bruto.

### D-038 — Políticas de navegador em modo "recomendado"
2026-10-31 · aceita
**Decisão:** página inicial e buscador pela chave `Recommended`; extensões como extensões externas (removíveis); forçar só por escolha explícita; aviso de "gerenciado pela organização".

### D-039 — Campos novos da receita são aditivos
2026-10-31 · aceita
**Decisão:** todo campo novo tem padrão que reproduz a v1; a receita continua `schema_version: 1` enquanto nenhum campo mudar de significado. O estado do Agente sobe para 2 (D-031).

### D-040 — Perfis rápidos e receitas compartilháveis sem dados pessoais
2026-10-31 · aceita
**Decisão:** perfis rápidos só listam ids (aplicar = mesclar); receita compartilhável tem formato próprio que por construção não contém conta, nomes, senhas, drivers, backups, Wi-Fi, volumes nem instaladores offline; importar sempre mostra prévia.

### D-041 — Atualização de instaladores por `winget download` e manifesto
2026-10-31 · aceita
**Decisão:** verificar = baixar e comparar a versão do manifesto YAML (ou `Find-WinGetPackage` se o módulo existir); o instalador antigo só é apagado depois que o novo está no lugar e no manifesto.

### D-042 — Barra lateral do Studio agrupada e com busca
2026-10-31 · aceita
**Decisão:** seções em grupos (Preparar, O que levar, Sistema, Rede, Concluir), campo de busca e Preferências (idioma e tema) no rodapé.

### D-043 — Segunda chance na Fase 2 e ISO montada só para leitura
2026-10-31 · aceita
**Contexto:** o .NET 3.5 precisa da pasta `sources\sxs` da mídia de instalação; sem ela, só pela internet (Fase 2). Um mesmo modelo do Ventoy serve a várias ISOs, então o nome da ISO não pode ir no XML.
**Decisão:** o Construtor grava `WinKit/isos.json` (imagem, build, arquitetura, idiomas) no modo Ventoy. A etapa `feature` usa, nesta ordem, `sources\sxs` do pendrive comum, a ISO do mesmo build montada com `Mount-DiskImage -Access ReadOnly` (desmontada sempre em `finally`, D-002) ou, na Fase 2, o Windows Update. Etapas da Fase 1 com `PlannedStep.phase2_fallback` que ficarem pendentes rodam de novo no começo da Fase 2, sem esperar o pendrive.
**Consequências:** o .NET 3.5 instala sem internet antes do login quando há ISO do mesmo build; sem ela, a instalação continua e o recurso entra depois do login. Os outros tipos de etapa não ganharam a segunda chance (DT-020).

### D-054 — Leituras lentas do sistema nunca na thread da interface
2026-11-01 · aceita (M19, `PLANO_V3.md`)
**Contexto:** o Studio travava ao abrir: a lista de pendrives (PowerShell) era lida antes de mostrar a janela, e a página Pendrive somava o tamanho de tudo no pendrive a cada abertura.
**Decisão:** R-59. O controlador guarda as leituras lentas num cache (`StudioController.cache`, por chave); `Page.slow(chave)` devolve o cache ou carrega em segundo plano (`TaskRunner.background`, sem folha modal) e redesenha a página quando chega. As páginas são criadas só na primeira visita. Uma tela de abertura com o logo aparece antes das importações pesadas.
**Consequências:** a janela abre na hora; a lista de pendrives aparece logo depois, com "Carregando…" no meio. O cache dos tamanhos é esquecido ao trocar de pendrive e depois de construir.
