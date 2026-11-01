# Testes numa VM do seu PC, com o Claude na nuvem (V3-04)

O Claude roda numa máquina na nuvem e não enxerga o seu PC. Para ele rodar os roteiros de validação numa VM sua, o seu PC precisa ser ligado à sessão.

## 1. Ligar o PC à sessão (uma vez)
1. Instale o **Claude para desktop** no seu PC e entre com a mesma conta.
2. Crie uma pasta para os testes, por exemplo `C:\WinKit-testes`, e copie para ela a pasta `scripts\vm` do repositório.
3. No app: **Settings → Claude Code → Remote Control** e adicione a pasta `C:\WinKit-testes`. Alternativa: abra um terminal nessa pasta e rode `claude remote-control`.
4. Avise na conversa. A sessão pede para usar a pasta; você aprova no app.
5. Para o Claude ver e clicar dentro da VM, ligue também o controle de tela do app desktop quando ele pedir.

## 2. Preparar o Hyper-V (uma vez)
- Windows 11 **Pro**: Painel de Controle → Programas → Ativar ou desativar recursos do Windows → **Hyper-V** → reiniciar.
- No Windows 11 Home não há Hyper-V: use o **VirtualBox** (os scripts abaixo são só para Hyper-V).

## 3. Scripts (`scripts/vm/`, rodar como administrador)
| Script | Faz |
|---|---|
| `nova-vm.ps1 -Iso <arquivo.iso> [-Geracao 1\|2]` | cria a VM (geração 2 = UEFI com TPM e Secure Boot; 1 = BIOS, para o Windows 7) e o ponto `vazia` |
| `ponto.ps1 -Acao listar\|criar\|voltar [-Ponto nome]` | pontos de restauração da VM (voltar ao `vazia` para repetir um teste) |
| `coletar-logs.ps1` | copia `C:\ProgramData\WinKit` e o resumo de dentro da VM para `C:\WinKit-testes\logs` |

## 4. Limites
- O Hyper-V **não repassa pendrive USB** para a VM. Teste por ele os caminhos com ISO (ISO personalizada e autossuficiente).
- Os caminhos com pendrive (Ventoy, Rufus, gravado pelo WinKit) precisam do **VirtualBox** (que repassa USB) ou de um PC de testes.
- Nunca use o seu disco de verdade numa VM.
