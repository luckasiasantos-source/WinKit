# WinKit — Dívidas Técnicas

> Documento vivo. Tudo que está **provisório, incompleto, simplificado de propósito ou sabidamente frágil**.
> Regra: `TODO` no código sem entrada aqui não é permitido. Ao quitar uma dívida, mude o estado para ✅ e registre o commit — não apague a entrada.

## Formato

```
### DT-nnn — título
- Estado: aberta | ✅ quitada (commit/data) | aceita (não será quitada, com motivo)
- Origem: desenho | M<n> | incidente IN-nnn
- Onde: arquivo(s) ou área
- Descrição: o que está faltando ou provisório
- Impacto: o que acontece por causa disso
- Plano: como e quando quitar
- Prioridade: alta | média | baixa
```

## Abertas

Ainda não há código. As entradas abaixo são **dívidas de desenho**: limitações conhecidas e aceitas conscientemente no plano.

### DT-001 — Executáveis sem assinatura de código
- Estado: aberta
- Origem: desenho (`PLANO.md` §16.4)
- Onde: `packaging/`
- Descrição: Studio e Agente não são assinados.
- Impacto: possível alerta do Defender/SmartScreen (H7).
- Plano: avaliar certificado de assinatura depois do v1.
- Prioridade: média

### DT-002 — Instaladores por usuário rodam elevados
- Estado: aberta
- Origem: desenho (`PLANO.md` §10.3)
- Onde: `agent/steps/app.py` (futuro)
- Descrição: a Fase 2 roda elevada; alguns instaladores por usuário (Squirrel e similares) preferem rodar sem elevação.
- Impacto: um instalador específico pode recusar ou se comportar diferente.
- Plano: se aparecer caso real, adicionar execução sem elevação (tarefa agendada com nível limitado) para apps marcados no catálogo.
- Prioridade: baixa

### DT-003 — Sem garantia de 100% de silêncio
- Estado: aceita (depende de terceiros)
- Origem: desenho (`PLANO.md` §12.3)
- Onde: catálogo de apps
- Descrição: alguns instaladores abrem o app ou uma janela no fim mesmo com parâmetro silencioso. Só os apps no catálogo têm `kill_processes`/`disable_autostart`.
- Impacto: no modo silencioso, um app desconhecido pode abrir sozinho.
- Plano: crescer o catálogo conforme os apps reais do usuário.
- Prioridade: baixa

### DT-004 — Política de "conteúdo do consumidor" depende de valores por usuário
- Estado: aceita
- Origem: desenho (`PLANO.md` §14.1)
- Descrição: `DisableWindowsConsumerFeatures` só vale em Enterprise/Education; em Home/Pro usamos valores do `ContentDeliveryManager`, que a Microsoft pode mudar.
- Impacto: apps sugeridos podem voltar em versões futuras do Windows.
- Plano: revisar `tweaks.yaml` a cada versão nova do Windows.
- Prioridade: média

### DT-005 — Fixados do menu Iniciar não são tratados
- Estado: aberta
- Origem: desenho
- Descrição: o Windows 11 cria atalhos promocionais no Iniciar que não são pacotes instalados; o v1 não remove esses fixados.
- Impacto: ícones promocionais podem aparecer no Iniciar mesmo sem o app.
- Plano: avaliar com o item 29 (barra de tarefas/Iniciar).
- Prioridade: baixa

### DT-006 — Senha "armazenada" fica legível no pendrive
- Estado: aceita (limitação do formato do Windows)
- Origem: desenho (`PLANO.md` §9.3, §16.3)
- Descrição: o `autounattend.xml` só suporta senha em texto ou em Base64.
- Impacto: quem tiver o pendrive lê a senha.
- Plano: recomendar `password_mode = empty`; aviso obrigatório no Studio.
- Prioridade: média

### DT-007 — Uma entrada de `ventoy.json` por ISO
- Estado: aberta
- Origem: desenho (`PLANO.md` §8.3)
- Descrição: não usamos a chave `parent` (uma regra para a pasta toda) até validar H1.
- Impacto: ISO nova copiada para o pendrive exige rodar `winkit sincronizar`.
- Plano: adotar `parent` se H1 confirmar e todas as ISOs da pasta tiverem o mesmo idioma.
- Prioridade: baixa

### DT-008 — Apps da Loja (msstore) exigem internet
- Estado: aceita
- Origem: desenho (`PLANO.md` §7.1.3)
- Descrição: `winget download` não baixa pacotes `msstore` sem conta corporativa.
- Impacto: esses apps só instalam na Fase 2 com internet.
- Plano: nenhum; o resumo explica.
- Prioridade: baixa

### DT-009 — Sem tratamento de drivers para o instalador (WinPE)
- Estado: aceita (contraria D-002)
- Origem: desenho (H10)
- Descrição: se o instalador do Windows não enxergar o SSD, o WinKit não resolve.
- Impacto: o usuário precisa carregar o driver manualmente na tela do instalador.
- Plano: documentar o procedimento se acontecer.
- Prioridade: baixa

### DT-010 — Valores dos catálogos não validados em Windows real
- Estado: aberta
- Origem: M1
- Onde: `src/winkit/data/tweaks.yaml`, `bloatware.yaml`, `editions.yaml`, `app_catalog.yaml`
- Descrição: valores de registro, nomes de pacote, publisher ids, chaves genéricas e caminhos de configuração vieram de documentação e conhecimento prévio; nenhum foi aplicado ainda num Windows real.
- Impacto: um ajuste pode não ter efeito, ou um pacote pode ter outro nome numa build específica. Como cada etapa falha isolada (P4), o efeito é um item "falhou" no resumo.
- Plano: validar no roteiro de VM do M7 e no CI Windows (ajustes aplicados num hive de teste).
- Prioridade: média

### DT-011 — Ajustes do registro protegidos pelo Windows (UCPD)
- Estado: aberta
- Origem: M1
- Onde: `visual.hide_widgets_button` (`TaskbarDa`)
- Descrição: versões recentes do Windows 11 bloqueiam a escrita de alguns valores do Explorer no `HKCU` do usuário logado. Aplicar no perfil Default (Fase 1, hive offline) deve funcionar; aplicar na Fase 2 pode falhar.
- Impacto: o ajuste aparece como falha quando decidido na hora.
- Plano: confirmar na VM; se falhar, marcar o ajuste como "só Fase 1" no catálogo.
- Prioridade: baixa

## Quitadas

### DT-012 — Fase 2 sem janela até o M9
- Estado: ✅ quitada no M9 (janela Qt, bandeja e notificações)
- Origem: M3
- Onde: `src/winkit/agent/ui_select.py`
- Descrição: todos os modos de início usam `NullUi` (nenhuma janela, sem bandeja); contagem regressiva, modo interativo e escolhas na hora entram no M9.
- Impacto: até o M9, `countdown` e `interactive` se comportam como `silent`.
- Plano: M9 (janela Qt, bandeja, notificações).
- Prioridade: alta (é funcionalidade pedida)

### DT-013 — Códigos de reinício do winget não confirmados
- Estado: ✅ quitada no M9 (janela Qt, bandeja e notificações)
- Origem: M5
- Onde: `src/winkit/platform/winget.py` (`REBOOT_CODES`)
- Descrição: os códigos `0x8A150109`/`0x8A15010A` como "instalado, precisa reiniciar" vêm da documentação de memória, não de teste real.
- Impacto: um app que pede reinício pode aparecer como "falhou" com esse código.
- Plano: confirmar na VM (M5) e ajustar a tabela.
- Prioridade: baixa

### DT-014 — Correspondência nome do app ↔ ID do winget é heurística
- Estado: ✅ quitada no M9 (janela Qt, bandeja e notificações)
- Origem: M5
- Onde: `src/winkit/core/inventory.py` (`_heuristic_id`)
- Descrição: o `winget export` traz só IDs; o nome exibido no Windows é casado por heurística (última parte do ID × primeira palavra do nome). Apps da Loja (msstore) não são casados.
- Impacto: alguns apps aparecem sem ID do winget (precisam de instalador próprio) ou, raramente, com o ID errado.
- Plano: usar o módulo `Microsoft.WinGet.Client` (`Get-WinGetPackage`, saída em objetos) quando estiver instalado; manter a heurística como alternativa.
- Prioridade: média

