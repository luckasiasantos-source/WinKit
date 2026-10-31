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

### IN-010 — Erro de tipo só visível no Windows bloqueou três CIs seguidos
- Data: 2026-10-31
- Marco: M8 (descoberto ao conferir o CI do M10)
- O que aconteceu: os CIs do M8, da correção do IN-009 e do M9 falharam no Windows no passo do mypy (`power.py: Returning Any from function declared to return "float"`); os testes do Windows nem rodaram nesses commits.
- Causa raiz: no Linux, o mypy trata o código depois de `if sys.platform != "win32": return` como inalcançável e não o verifica; no Windows ele verifica. A verificação local (`scripts/check.sh`) só rodava o mypy do Linux. E eu conferi o CI tarde (só depois de três commits).
- Impacto: três commits sem testes no Windows; nenhum efeito funcional (o valor era um `int` do ctypes).
- Correção: conversão explícita em `power.py`.
- Prevenção: `scripts/check.sh` e o CI rodam também `mypy --platform win32`; conferir o CI a cada commit, não a cada marco.

### IN-011 — Duas dívidas marcadas como quitadas por engano
- Data: 2026-10-31
- Marco: M9 (descoberto na revisão final dos documentos)
- O que aconteceu: no commit do M9, DT-013 (códigos de reinício do winget) e DT-014 (casamento nome ↔ ID do winget) apareceram como "✅ quitada no M9 (janela Qt…)", mas só a DT-012 tinha sido resolvida.
- Causa raiz: a troca do estado da DT-012 foi feita por substituição de texto em todas as ocorrências de `- Estado: aberta` a partir dela, e não só na primeira.
- Impacto: só documental; o documento escondia duas dívidas abertas.
- Correção: DT-013 e DT-014 voltaram para "aberta".
- Prevenção: editar documento vivo trocando o bloco inteiro da entrada (título + estado), nunca uma linha genérica que se repete; conferir o `git diff` dos documentos antes do commit.

### IN-012 — Primeira release falhou ao conferir que a versão ainda não existia
- Data: 2026-10-31
- Marco: Fechamento (release `v0.1.0`)
- O que aconteceu: o workflow `Release` falhou no passo "Conferir a versão", logo depois do `uv sync`, sem mensagem de erro.
- Causa raiz: o passo usa `gh release view` esperando o código 1 ("não existe"). No `pwsh`, o GitHub Actions encerra o passo com o último `$LASTEXITCODE`, então o caso esperado virou falha. Não dava para testar o workflow localmente (sem PowerShell aqui).
- Impacto: nenhum; a release não foi criada.
- Correção: zerar `$LASTEXITCODE` depois da verificação.
- Prevenção: em passos `pwsh` do Actions, todo comando nativo cujo código diferente de zero é esperado termina com `$global:LASTEXITCODE = 0`.

### IN-013 — Tabelas de tradução fora do executável empacotado
- Data: 2026-10-31
- Marco: M11 (CI do commit "base da tradução")
- O que aconteceu: no teste de fumaça do pacote Windows, `winkit construir` quebrou com `ModuleNotFoundError: No module named 'winkit.i18n.messages'`. No Linux e nos testes tudo passava.
- Causa raiz: as tabelas de mensagens eram carregadas com `importlib.import_module(nome)`. O PyInstaller só empacota os módulos que enxerga em `import` no código, então as tabelas ficaram de fora do executável.
- Impacto: nenhum para o usuário (a release 0.1.0 não tinha esse código); o CI pegou antes.
- Correção: importações explícitas dentro de `_load` (`from winkit.i18n.messages import pt_br`), que o PyInstaller detecta.
- Prevenção: teste `test_no_dynamic_imports_in_package` proíbe `import_module` e `__import__` no pacote; o teste de fumaça com executáveis continua obrigatório no CI.

### IN-014 — Testes da CLI dependiam do idioma do Windows da máquina de teste
- Data: 2026-10-31
- Marco: M11 (CI do commit de fechamento)
- O que aconteceu: no CI do Windows, 8 testes da CLI falharam porque as mensagens saíram em inglês ("Recipe created at…") em vez de português. No Linux passavam.
- Causa raiz: a CLI escolhe o idioma por `--idioma`, depois `WINKIT_LANG`, depois o idioma do Windows. O runner do GitHub é em inglês; no Linux a detecção cai em pt-BR. Os testes fixavam o idioma do processo, mas a CLI o redefinia ao iniciar.
- Impacto: só nos testes; o comportamento do produto estava certo.
- Correção: o `conftest.py` fixa `WINKIT_LANG=pt-BR` em todo teste (os testes de idioma mudam de propósito).
- Prevenção: todo teste de componente que detecta idioma roda com o idioma fixado; a detecção real tem testes próprios.

### IN-015 — Tirar a senha de um Wi-Fi mudava o autounattend.xml gerado depois
- Data: 2026-10-31
- Marco: M14 (achado pela suíte completa, antes de qualquer commit)
- O que aconteceu: depois de um teste que tirava a senha de um perfil de Wi-Fi, o `autounattend.xml` passou a sair com prefixo `ns0:` no lugar do namespace padrão, e o teste de snapshot falhou só quando os testes rodavam juntos.
- Causa raiz: `ET.register_namespace("", ...)` altera um registro **global** do ElementTree. O código do Wi-Fi registrava o namespace dele como padrão e sobrescrevia o do gerador do XML de instalação, que só registrava o seu ao ser importado.
- Impacto: no Studio, tirar a senha de uma rede e depois construir o pendrive geraria um XML com prefixos. É XML válido, mas o instalador do Windows nunca foi testado com ele.
- Correção: o Wi-Fi usa `ET.tostring(..., default_namespace=...)` e não toca no registro; o gerador reafirma os prefixos imediatamente antes de serializar.
- Prevenção: `test_no_global_xml_namespace_registration` (só o gerador pode registrar) e `test_strip_key_does_not_change_other_xml`.

### IN-016 — Commit feito com a verificação falhando (pipe escondeu o erro)
- Data: 2026-10-31
- Marco: M14 (commit `67a6e40`, V2-09)
- O que aconteceu: o commit do diagnóstico de drivers foi feito e enviado com dois erros de lint num arquivo de teste (importação fora de ordem e linha longa). Os testes passavam; só o lint falhava.
- Causa raiz: a verificação foi chamada como `scripts/check.sh | tail -2 && git commit …`. Num pipe, o código de saída é o do `tail` (sempre 0), então o `&&` seguiu mesmo com o `check.sh` parado no lint. Repetiu a falha de processo do IN-003 por outro caminho.
- Impacto: nenhum no aplicativo (só estilo de um teste); a CI mostraria o erro.
- Correção: commit seguinte corrige o lint, com `check.sh` terminando em `== OK`.
- Prevenção: rodar a verificação sem pipe antes do commit (`scripts/check.sh > log; echo $?`) ou com `set -o pipefail`; nunca encadear `git commit` depois de um pipe.

### IN-017 — Release 0.4.0 travou no passo de testes
- Data: 2026-10-31
- Marco: M13/M14 (execução da release de `b652529`)
- O que aconteceu: o passo "Testes" da release ficou mais de 50 minutos parado no Windows, sem saída, enquanto a CI do **mesmo commit** tinha passado em 6 minutos. A execução foi cancelada; a 0.4.0 não foi publicada separadamente (as mudanças dela saem na 0.5.0).
- Causa raiz: não identificada. O job não tinha limite de tempo e o `pytest -q` não diz qual teste está rodando, então o log não mostra onde parou. Suspeita: um teste que toca o Windows real (mutex, PowerShell) travando de forma intermitente no runner.
- Impacto: uma release a menos; nenhum efeito no aplicativo.
- Correção: `faulthandler_timeout = 300` no pytest (um teste preso imprime a pilha de todas as threads) e `timeout-minutes: 25` nos passos de teste da CI e da release; a release também fixa `QT_QPA_PLATFORM=offscreen`, como a CI.
- Prevenção: se acontecer de novo, o log mostra o teste e a linha; o achado vira um incidente com causa raiz.

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
