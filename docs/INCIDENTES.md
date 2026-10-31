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
