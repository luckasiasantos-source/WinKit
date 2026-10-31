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
