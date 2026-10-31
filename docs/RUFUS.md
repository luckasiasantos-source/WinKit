# Usar o WinKit com um pendrive gravado pelo Rufus (ou pela ferramenta da Microsoft)

> Pré-alpha: teste primeiro numa máquina virtual (veja o aviso no [README](../README.md#aviso)).

O jeito recomendado continua sendo o **Ventoy** (várias ISOs no mesmo pendrive). Se você prefere o **Rufus** ou a **Ferramenta de Criação de Mídia da Microsoft**, o WinKit também funciona. A diferença é que cabe só uma versão do Windows por pendrive.

O WinKit **não grava** o pendrive e **nunca formata nada**: você grava com o Rufus e depois o WinKit acrescenta só duas coisas:

- `autounattend.xml` na raiz, que o instalador do Windows lê sozinho;
- a pasta `WinKit\`, com receita, Agente, apps, drivers e backups.

Nada dentro de `sources\`, `boot\` ou `efi\` é alterado.

## Configurações recomendadas no Rufus

| Opção | Valor |
|---|---|
| Esquema de partição | **GPT** |
| Sistema de destino | **UEFI (não CSM)** |
| Sistema de arquivos | **NTFS** (o `install.wim` do Windows 11 passa de 4 GB) |
| Janela "Experiência do usuário do Windows" | **Desmarque tudo**. O WinKit já faz conta local, pula requisitos e desliga a coleta de dados |

Se as opções do Rufus ficarem marcadas, o Rufus grava o próprio arquivo de respostas. Ao construir, o WinKit:

1. guarda uma cópia como `autounattend.xml.winkit-bak`;
2. move a cópia de `sources\$OEM$\$$\Panther\unattend.xml` (se existir) para `unattend.xml.winkit-bak`;
3. usa as respostas dele.

O Studio e o `winkit construir` avisam quando isso acontece.

## Passo a passo

1. Grave o pendrive com o Rufus (ou com a ferramenta da Microsoft).
2. Abra o WinKit Studio. Em **Pendrive**, o pendrive aparece com o selo **Instalação (Rufus/Microsoft)**; clique em **Usar**.
3. Siga a barra lateral normalmente e, no fim, **Construir pendrive**.
4. Dê boot pelo pendrive. A instalação segue sozinha; você só escolhe o disco.

Pela linha de comando:

```powershell
winkit pendrive listar
winkit receita nova --pendrive F: --usuario Ana
winkit construir --pendrive F:
winkit validar --pendrive F:
```

## Dúvidas comuns

- **Posso usar FAT32?** Só se o `install.wim` tiver menos de 4 GB (o Rufus divide em `.swm` quando precisa; o WinKit lê o primeiro arquivo). NTFS é mais simples.
- **E se eu tiver outro pendrive conectado na instalação?** Deixe só o pendrive do WinKit conectado (hipótese H18 do `PLANO_V2.md`).
- **Vale também para o pendrive da Ferramenta de Criação de Mídia?** Sim. Ela usa `install.esd`, que o WinKit também lê.
