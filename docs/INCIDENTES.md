# WinKit — Incidentes (o que deu errado)

> Documento vivo. Registra **tudo que deu errado**: bugs relevantes, hipóteses que se mostraram falsas, testes em hardware real que falharam, decisões que precisaram ser revertidas.
> O objetivo é não repetir o erro. Entradas nunca são apagadas.

## Formato

```
### IN-nnn — título curto
- Data:
- Marco:
- O que aconteceu: fatos observados (mensagens, comportamento, logs)
- Causa raiz: por que aconteceu (não só o sintoma)
- Impacto: o que quebrou, quem foi afetado, dados perdidos?
- Correção: o que foi feito (commit)
- Prevenção: teste, regra ou mudança de processo para não repetir (link para R-xx, DT-xxx ou D-xxx)
```

## Incidentes

### IN-001 — CI falhou na instalação: pasta `data/` inexistente
- Data: 2026-10-31
- Marco: M0
- O que aconteceu: o primeiro CI (Linux e Windows) falhou em `uv sync` com `FileNotFoundError: Forced include not found: .../data`.
- Causa raiz: o `pyproject.toml` mandava o hatchling incluir `data/` no pacote, mas a pasta estava vazia; o git não versiona pastas vazias, então ela não existia no checkout do CI. Localmente ela existia, então os testes locais passaram.
- Impacto: nenhum teste rodou no CI do M0 (incluindo os testes de Windows real).
- Correção: catálogos movidos para `src/winkit/data/` e `force-include` removido (D-021).
- Prevenção: antes de cada commit, rodar `uv sync --locked` a partir de um clone limpo (`git clone` local para uma pasta temporária) quando mexer em empacotamento.

### IN-002 — Backup do `ventoy.json` copiava o arquivo do próprio WinKit
- Data: 2026-10-31
- Marco: M2
- O que aconteceu: o teste `test_rebuild_is_idempotent` falhou: na segunda construção apareceu um `ventoy.json.winkit-bak` que não existia na primeira.
- Causa raiz: o backup só era criado "se existir `ventoy.json` e ainda não houver backup". Num pendrive sem `ventoy.json`, a primeira construção criava o arquivo e não criava backup; a segunda via o arquivo (gerado pelo WinKit) e o tratava como o original do usuário.
- Impacto: nenhum (pego pelo teste antes de qualquer uso real). Se tivesse passado, "restaurar o backup" devolveria uma configuração do WinKit em vez do estado original.
- Correção: na primeira construção o backup é sempre gravado; sem arquivo original, ele recebe `{}`.
- Prevenção: teste de idempotência mantido (rodar `construir` duas vezes deve produzir exatamente os mesmos arquivos).

### IN-003 — Commit do M2 enviado com erros de lint nos testes
- Data: 2026-10-31
- Marco: M2
- O que aconteceu: o commit `f0d7789` foi enviado com 4 avisos do ruff em arquivos de teste.
- Causa raiz: a verificação foi encadeada como `ruff ... | tail -1 && git commit`; o `| tail` devolve o código de saída do `tail` (0), então o erro do ruff não impediu o commit.
- Impacto: CI do commit `f0d7789` falha no passo de lint; nenhum efeito funcional.
- Correção: avisos corrigidos no commit seguinte.
- Prevenção: `scripts/check.sh` com `set -euo pipefail`, obrigatório antes de cada commit (`CLAUDE.md`).

### IN-004 — Snapshot do XML falhava no Windows por causa de CRLF
- Data: 2026-10-31
- Marco: M2 (descoberto no CI do M2)
- O que aconteceu: `test_snapshot_default_recipe` passou no Linux e falhou no CI Windows; a diferença eram só as quebras de linha.
- Causa raiz: o Git no Windows (com `core.autocrlf`) converte LF em CRLF no checkout; o arquivo de referência deixou de bater byte a byte com o XML gerado.
- Impacto: só o teste; o XML gerado pelo WinKit não mudou.
- Correção: `.gitattributes` com `* text=auto eol=lf`.
- Prevenção: todo arquivo de referência comparado por bytes fica coberto pelo `.gitattributes`.

### IN-005 — `bootstrap.ps1` com acentos corrompidos e erro silencioso
- Data: 2026-10-31
- Marco: M2 (descoberto no CI do M2)
- O que aconteceu: no CI Windows, o log do bootstrap saiu com `inÃ­cio` em vez de `início`, e um marcador inexistente não gerou "ERRO" no log.
- Causa raiz: (1) o Windows PowerShell 5.1 lê scripts UTF-8 **sem BOM** como ANSI; (2) com `$ErrorActionPreference = 'Continue'`, `Get-Content` de um arquivo inexistente é um erro não fatal: o script seguia com `$marker` vazio e concluía, errado, que era "marcador de outro pendrive".
- Impacto: no Windows real, logs ilegíveis e um pendrive com problema seria ignorado em silêncio, sem rastro do motivo.
- Correção: script gravado com BOM UTF-8; `$ErrorActionPreference = 'Stop'` dentro do bloco principal; o registro do erro no `catch` é protegido para nunca quebrar a instalação.
- Prevenção: teste `test_script_has_utf8_bom` (roda em qualquer sistema) e `test_builder_copies_script_byte_for_byte`; testes reais no CI Windows.

### IN-006 — Apps desmarcados do inventário bloqueavam o `construir`
- Data: 2026-10-31
- Marco: M5
- O que aconteceu: no teste de ponta a ponta da CLI, `construir` falhou com "precisa de um instalador" para apps que vieram do inventário e não foram marcados.
- Causa raiz: a validação exigia instalador/ID do winget de **todos** os apps da receita; o inventário guarda todos os apps do PC (desmarcados) para o usuário escolher.
- Impacto: impediria qualquer construção depois de `coletar apps`.
- Correção: as exigências de fonte de instalação só valem para apps marcados.
- Prevenção: `test_unselected_apps_do_not_need_installer`.

### IN-007 — Edição por script falhou em silêncio (espera do winget desligada)
- Data: 2026-10-31
- Marco: M5
- O que aconteceu: a etapa do winget nunca esperava o winget ficar disponível; o teste `test_winget_never_available_defers` falhou.
- Causa raiz: processo de desenvolvimento. A alteração foi feita por substituição de texto, mas o formatador já tinha reformatado aquele trecho; a substituição não encontrou nada e não avisou. O mesmo aconteceu antes com fixtures de teste no M4.
- Impacto: nenhum em produção (pego pelo teste).
- Correção: ligação refeita no executor.
- Prevenção: toda edição por script verifica que o trecho original existe antes de substituir (falha alta); testes de comportamento cobrem cada ligação entre executor e etapa.

### IN-008 — Arquivo com nome inválido no Windows entrou no repositório e quebrou o CI
- Data: 2026-10-31
- Marco: M3 (descoberto ao verificar o CI do M4)
- O que aconteceu: os CIs do M3, da correção do M3 e do M4 falharam no Windows já no checkout: `error: invalid path 'C:\ProgramData/WinKit/Logs/agente-erro-fatal.log'`. Nenhum teste rodou no Windows nesses commits (o pacote também não foi gerado).
- Causa raiz: (1) `program_data()` caía em `r"C:\ProgramData"` quando a variável de ambiente não existia; no Linux isso é um caminho **relativo** com esse nome literal, criado dentro do repositório por um teste do M3 (antes de ele usar `PROGRAMDATA`); (2) o commit usava `git add -A`, que incluiu o arquivo; (3) eu não conferi o resultado do CI antes de seguir para o M4.
- Impacto: três commits sem validação no Windows.
- Correção: arquivo removido; `program_data()` nunca devolve caminho relativo fora do Windows; `.gitignore` bloqueia nomes com letra de unidade.
- Prevenção: testes `test_no_windows_drive_paths_tracked` e `test_program_data_is_never_relative`; conferir o CI do commit anterior antes de fechar o marco seguinte.

### IN-009 — Atalho de app portátil quebrado; testes tocando disco e navegador reais
- Data: 2026-10-31
- Marco: M5/M6 (descoberto no CI Windows do M6 e do M7)
- O que aconteceu: `test_portable_shortcuts` passou no Linux e falhou no Windows com "molde ABS inválido: `{ABS:D:\Portateis\Tool}\tool.exe`". No mesmo CI, processos do Edge ficaram abertos no runner.
- Causa raiz: (1) **bug real**: o atalho de um app portátil é "pasta absoluta + executável", mas o leitor de moldes recusava qualquer texto depois de `{ABS:...}`; (2) no Linux o `D:` não existe, então o backup era pulado e o atalho nem rodava — o teste aceitava "pulado" e não exercitava o caminho de sucesso; no runner Windows o `D:` existe e o teste chegou a gravar em `D:\` real; (3) o teste do comando `summary` chamava `os.startfile`, que abre o navegador de verdade no Windows.
- Impacto: no PC real, todo app portátil fora das pastas do usuário ficaria sem atalho.
- Correção: `{ABS:pasta}\resto` passa a ser um caminho dentro da pasta absoluta; teste com unidade que nunca existe (`Q:`) e teste novo do caminho de sucesso com pasta do perfil; `open_file` substituível e substituído no teste.
- Prevenção: testes de comportamento afirmam o resultado esperado exato (não "feito ou pulado"); testes nunca usam letras de unidade que podem existir (`C:`/`D:`) para gravar.

## Lições da fase de desenho

Problemas encontrados na conversa anterior (PDF de referência) e corrigidos **antes** de virar código. Ficam registrados porque são erros fáceis de repetir.

### L-001 — Embutir o `oscdimg.exe` no aplicativo
- **O que dizia a referência:** embutir o `oscdimg.exe` como recurso do aplicativo.
- **Problema:** viola a licença do Windows ADK (redistribuição).
- **Resolução:** tornou-se irrelevante com D-002 (a ISO nunca é remontada).

### L-002 — Injetar driver só no `install.wim`
- **Problema:** drivers de armazenamento e rede também precisariam ir para o `boot.wim` (WinPE), senão o instalador não enxerga o disco.
- **Resolução:** irrelevante com D-002; drivers vão pelo pendrive + `pnputil` (M4); limite registrado como H10/DT-009.

### L-003 — Assumir que a ISO tem `install.wim`
- **Problema:** muitas ISOs vêm com `install.esd`, que não pode ser montado para escrita.
- **Resolução:** irrelevante com D-002; para leitura, `Get-WindowsImage` funciona com os dois.

### L-004 — Exportar todos os drivers do PC atual sem filtro
- **Problema:** traz drivers que não fazem sentido sozinhos (impressoras, componentes de software).
- **Resolução:** seleção por classe com recomendados (`PLANO.md` §7.2).

### L-005 — Restaurar em `%APPDATA%` a partir do `SetupComplete.cmd`
- **Problema:** o `SetupComplete.cmd` roda como SYSTEM, antes de existir o perfil do usuário; `%APPDATA%` ali é o do SYSTEM.
- **Resolução:** restaurar no perfil Default na Fase 1 e no perfil real na Fase 2 (`PLANO.md` §6.3, §11.2).

### L-006 — Achar que dá para levar sessões e senhas
- **Problema:** tokens e senhas protegidos por DPAPI não funcionam em outra máquina/conta.
- **Resolução:** avisos na captura (`PLANO.md` §7.4.6).

### L-007 — Usar `HKCU\...\RunOnce` a partir do SYSTEM
- **O que dizia a referência:** registrar `RunOnce` em `HKCU` dentro do `SetupComplete.cmd`.
- **Problema:** como SYSTEM, `HKCU` é o registro do próprio SYSTEM, não do usuário que ainda vai ser criado.
- **Resolução:** tarefa agendada no logon (D-012).
