# Roteiros de validação em hardware real

O código é desenvolvido e testado automaticamente num ambiente Linux e no CI do Windows, mas o comportamento real (Ventoy, instalador do Windows, primeiro login) só pode ser confirmado no seu PC.

Cada marco que depende disso ganha um roteiro `Mx.md` nesta pasta. Você executa os passos e preenche o resultado. Resultado diferente do esperado vira uma entrada em `docs/INCIDENTES.md`.

## Modelo

```
# Validação do M<n> — <título>

**Versão testada:** 0.x.y   **Data:**   **Hardware:**   **Versão do Ventoy:**   **ISO:**

## Preparação
1. ...

## Passos
| # | Passo | Resultado esperado | Resultado obtido | OK? |
|---|---|---|---|---|
| 1 | ... | ... | | |

## Hipóteses validadas neste roteiro
| Hipótese | Confirmada? | Observação |
|---|---|---|

## Arquivos para anexar
- `WinKit\Logs\<pc>_<data>\` do pendrive
```

## Ordem sugerida

Prepare a VM uma vez com [`AMBIENTE_VM.md`](AMBIENTE_VM.md) e siga os roteiros em ordem. Os da v1 (M2 a M10) cobrem o fluxo básico do pendrive Ventoy; os da v2 cobrem as funções novas:

| Roteiro | O que valida | Hipóteses |
|---|---|---|
| [M11](M11.md) | Inglês e espanhol | H12 |
| [M12](M12.md) | Aplicar neste PC, prévia e ponto de restauração | H13, H14, H15 |
| [M13](M13.md) | Pendrive do Rufus ou da Microsoft | H16, H17, H18 |
| [M14](M14.md) | Wi-Fi, recursos, drivers que faltam, DNS, unidades de rede, manutenção, variáveis | H19 a H24 |
| [M15](M15.md) | Perfis rápidos, fontes, apps padrão, aparência, navegadores, Iniciar e barra | H25 a H31, H35 |
| [M16](M16.md) | Pastas em outro disco, jogos, contas extras | H32, H33 |
| [M17](M17.md) | Sugestões, modelos, exportação, atualização dos instaladores, comparação | H34 |
| [M19](M19.md) | Velocidade, nitidez e janela; testes numa VM do seu PC ([VM_REMOTA](VM_REMOTA.md)) | H45 |
| [M20](M20.md) | Modo em etapas, etapa Começar, Ventoy e Rufus baixados e abertos | H39, H46 |
