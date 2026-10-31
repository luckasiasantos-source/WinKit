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
| `agent/executor.py` | Executa um `Plan`, persiste `State`, trata reinicialização e pendrive ausente |
| `agent/integrity.py` | Confere arquivo ou pasta do pendrive contra o `manifesto.json` (R-22) |
| `agent/fakes.py`, `platform/fakes/services.py` | Fábricas de serviços falsos (um lugar só para acrescentar campos) |
| `agent/reboot.py`, `steps/windows_update.py` | Política de reinício; Windows Update |
| `agent/steps/tweak.py`, `steps/system.py` | Motor de ajustes (onde gravar conforme o alvo); bloatware, energia, nome do PC |
| `agent/steps/*.py` | Uma classe por tipo de etapa: `DriverStep`, `BloatStep`, `TweakStep`, `BackupStep`, `AppStep`, `ShortcutStep`, `WindowsUpdateStep`, `CleanupStep` |
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
```

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
- **R-03** Todo texto exibido ao usuário (CLI, GUI, notificações, resumo, `agente.log`) em **pt-BR**, e **somente** em `winkit/i18n/pt_br.py`. Nenhuma string de interface solta pelo código.
- **R-04** Documentação, comentários e mensagens de commit em pt-BR.
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
- **R-19** O Construtor só escreve em `WinKit\` e em `ventoy\script\winkit-*.xml`, e só mescla `ventoy\ventoy.json`. Qualquer escrita fora disso é bug.
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

### 5.12 Como as regras são verificadas automaticamente

| Regra | Verificação |
|---|---|
| Camadas (seção 2) | import-linter (`pyproject.toml`, 5 contratos) + `tests/test_architecture.py` (pega imports dentro de funções) |
| R-06 | `ruff check` e `ruff format --check` no CI |
| R-07 | `mypy` no CI (`strict` em `winkit.core`) |
| R-11 | contrato "subprocess só em platform.runner" + teste AST de `shell=` |
| R-35 | `test_phase1_does_not_import_qt` |
| R-50 | `test_todo_requires_debt_entry` |

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
2026-10-31 · aceita
**Decisão:** R-02 a R-04.

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
