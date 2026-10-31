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
- Estado: aberta
- Origem: M5
- Onde: `src/winkit/platform/winget.py` (`REBOOT_CODES`)
- Descrição: os códigos `0x8A150109`/`0x8A15010A` como "instalado, precisa reiniciar" vêm da documentação de memória, não de teste real.
- Impacto: um app que pede reinício pode aparecer como "falhou" com esse código.
- Plano: confirmar na VM (M5) e ajustar a tabela.
- Prioridade: baixa

### DT-014 — Correspondência nome do app ↔ ID do winget é heurística
- Estado: aberta
- Origem: M5
- Onde: `src/winkit/core/inventory.py` (`_heuristic_id`)
- Descrição: o `winget export` traz só IDs; o nome exibido no Windows é casado por heurística (última parte do ID × primeira palavra do nome). Apps da Loja (msstore) não são casados.
- Impacto: alguns apps aparecem sem ID do winget (precisam de instalador próprio) ou, raramente, com o ID errado.
- Plano: usar o módulo `Microsoft.WinGet.Client` (`Get-WinGetPackage`, saída em objetos) quando estiver instalado; manter a heurística como alternativa.
- Prioridade: média

### DT-015 — Licença do projeto não definida
- Estado: ✅ quitada em 2026-10-31 (Apache-2.0, D-028)
- Origem: fechamento da v1 (README para código aberto)
- Onde: `pyproject.toml` (`license = "Proprietary"`), `README.md` (seção Licença), falta o arquivo `LICENSE`
- Descrição: o projeto deve virar código aberto, mas a licença ainda não foi escolhida pelo dono.
- Impacto: sem licença, ninguém pode legalmente usar, modificar ou redistribuir o código, mesmo com o repositório público.
- Plano: escolher (MIT, Apache-2.0 ou GPL-3.0), criar `LICENSE`, ajustar `pyproject.toml` e o README. O PySide6 é LGPL; qualquer uma delas é compatível com o uso dinâmico atual.
- Prioridade: alta antes de tornar o repositório público

### DT-016 — Mensagens técnicas e linhas livres do log só em português
- Estado: aberta
- Origem: M11
- Onde: exceções de `winkit.core.errors`/`winkit.platform` e chamadas livres de `EventLog.info/warning/error`
- Descrição: os textos para o usuário (interface, CLI, motivos das etapas, avisos, resumo) estão nos três idiomas, mas o **detalhe técnico** de uma exceção (ex.: "falhou: <detalhe>") e as linhas livres do `agente.log` continuam em pt-BR.
- Impacto: num Windows em inglês ou espanhol, o detalhe técnico de um erro aparece em português dentro de uma frase traduzida.
- Plano: converter as exceções que chegam ao usuário em `Msg` conforme aparecerem em issues.
- Prioridade: baixa

### DT-017 — Traduções feitas por IA, sem revisão nativa
- Estado: aberta
- Origem: M11
- Onde: `src/winkit/i18n/messages/{en_us,es}.py`, `src/winkit/i18n/catalogs/*.yaml`, `README.en.md`, `README.es.md`
- Descrição: inglês e espanhol escritos por IA, seguindo o glossário do `PLANO_V2.md` §6.6.
- Impacto: frases pouco naturais ou termos diferentes dos que o Windows usa.
- Plano: revisão por falantes nativos; issues com rótulo `tradução`.
- Prioridade: baixa

### DT-018 — "Aplicar neste PC" roda no processo do Studio, sem progresso por etapa
- Estado: aberta
- Origem: M12
- Onde: `src/winkit/studio/controller.py` (`live_apply`), `src/winkit/studio/ui/pages/finish.py` (`LivePage`)
- Descrição: o plano previa o Studio chamando o Agente como processo separado e acompanhando um `progresso.jsonl`. Foi feito no mesmo processo, numa thread, com a folha "Aplicando…" sem progresso por etapa.
- Impacto: uma falha grave no motor pode derrubar o Studio; durante a aplicação não se vê qual etapa está rodando (o resumo no fim mostra tudo).
- Plano: passar o progresso do executor para a interface (sinal Qt a partir de um `AgentUi` próprio) e, se necessário, rodar `winkit-agent apply` como processo.
- Prioridade: média

### DT-019 — Senhas de Wi-Fi legíveis no pendrive
- Estado: aceita (como a DT-006)
- Origem: M14 (V2-02, D-036)
- Onde: `WinKit\Perfis\<perfil>\Wifi\*.xml`
- Descrição: o Windows só exporta e importa a senha da rede em texto (`key=clear`); sem DPAPI portátil não há como protegê-la no pendrive.
- Impacto: quem pegar o pendrive lê as senhas das redes levadas.
- Plano: aviso permanente no Studio e na CLI; opção de levar a rede sem a senha; a cópia temporária no PC novo é apagada logo após o uso e o registro de segredos impede que vá para logs.
- Prioridade: baixa

### DT-020 — Etapas da Fase 1 adiadas só têm segunda chance quando marcadas
- Estado: aberta
- Origem: M14 (V2-08, D-043)
- Onde: `agent/executor.py` (`run_phase`), `core/planner/planner.py`
- Descrição: uma etapa da Fase 1 adiada (ex.: um driver com o pendrive ausente) volta a pendente, mas a Fase 2 só roda as etapas da Fase 2 e as marcadas com `phase2_fallback` (hoje só o .NET 3.5). As outras ficam pendentes e o resumo final espera por elas; o atalho "Tentar de novo" não as alcança.
- Impacto: raro (o pendrive costuma estar conectado na Fase 1), mas a instalação pode terminar sem a limpeza final.
- Plano: avaliar por tipo quais etapas podem rodar na Fase 2 com o alvo trocado (Default → usuário, como no fallback D-012) e marcá-las.
- Prioridade: média

### DT-021 — DNS não chega a adaptadores que aparecerem depois
- Estado: aberta
- Origem: M14 (V2-16)
- Onde: `agent/steps/network_privacy.py` (`DnsStep`)
- Descrição: os servidores DNS são gravados em cada adaptador físico que existe na hora (`Get-NetAdapter -Physical`). Um adaptador novo (um Wi-Fi USB ligado depois) fica com o DNS da rede. A política global `DoHPolicy` é gravada para reduzir o efeito, mas não troca os servidores.
- Impacto: baixo; o usuário pode rodar "Aplicar neste PC" de novo só com "Servidor DNS".
- Plano: avaliar uma tarefa agendada no evento de adaptador novo, ou a política de servidores DNS por GPO (`NameServer`).
- Prioridade: baixa

### DT-022 — Fontes da máquina pela data de criação
- Estado: aberta
- Origem: M15 (V2-07)
- Onde: `collector/fonts.py`
- Descrição: as fontes "para todos" que o usuário instalou são separadas das do Windows pela data de criação do arquivo, posterior a `InstallDate`. Atualizações do Windows e programas também instalam fontes depois; elas aparecem na lista (desmarcadas). O catálogo `default_fonts.yaml` (gerado numa VM limpa, PLANO_V2 §21) ainda não existe.
- Impacto: a lista pode mostrar fontes que vieram com o Windows ou com o Office; como nada vem marcado, só polui a tela.
- Plano: gerar `default_fonts.yaml` na validação na VM e usar como lista de exclusão.
- Prioridade: baixa

### DT-023 — Aparência: sem reaplicação na Fase 2 e sem ponteiros personalizados
- Estado: aberta
- Origem: M15 (V2-06)
- Onde: `agent/steps/personal.py`, `data/personal_settings.yaml`
- Descrição: o plano previa conferir e reaplicar papel de parede e cor na Fase 2, caso o Windows troque pelo tema padrão no primeiro login (H26). Isso ficou para depois da validação na VM. Ponteiros fora de `%SystemRoot%\cursors` (arquivos `.cur`/`.ani` próprios) também não são levados: o valor é descartado na captura.
- Impacto: se H26 for falsa, o papel de parede e a cor podem voltar ao padrão no primeiro login; quem usa ponteiro baixado da internet precisa reinstalar.
- Plano: validar H26; se falsa, uma etapa de conferência na Fase 2 no `HKCU`. Cursores próprios: copiar para `%SystemRoot%\Cursors\WinKit\` e reescrever os caminhos.
- Prioridade: média
