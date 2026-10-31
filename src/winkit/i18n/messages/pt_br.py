"""Textos em português do Brasil: a base de todas as traduções (R-03, R-51).

Uso: ``t("chave", nome="valor")``. Chave inexistente é erro de programação e lança ``KeyError``.
"""

from __future__ import annotations

from winkit.i18n.core import Entry, Plural

MESSAGES: dict[str, Entry] = {
    "legacy.text": "{text}",
    # ---------------------------------------------------------------- geral
    "app.name": "WinKit",
    "error.unexpected": "Erro inesperado: {detail}. Veja o log para mais detalhes.",
    "error.not_windows": "Este comando só funciona no Windows.",
    "error.needs_admin": "Este comando precisa ser executado como administrador.",
    # ---------------------------------------------------------------- receita
    "recipe.invalid": "A receita tem problemas:\n{problems}",
    "recipe.silent_missing": (
        "No modo silencioso ninguém vai responder perguntas. Preencha: {fields}"
    ),
    "recipe.computer_name_invalid": (
        'Nome de computador inválido: "{name}". Use de 1 a 15 caracteres '
        "(letras, números e hífen), sem ser só números."
    ),
    "recipe.username_invalid": 'Nome de usuário inválido: "{name}". {reason}',
    "recipe.username_reserved": "Este nome é reservado pelo Windows.",
    "recipe.username_chars": 'Não use os caracteres \\ / [ ] : ; | = , + * ? < > " @',
    "recipe.password_missing": "A senha está marcada como armazenada, mas está vazia.",
    "recipe.password_stored_warning": (
        "Atenção: a senha vai ficar legível no pendrive (o Windows só aceita senha "
        "em texto ou Base64 no arquivo de respostas)."
    ),
    "recipe.duplicate_id": 'Identificador repetido: "{id}" aparece mais de uma vez em {section}.',
    "recipe.unknown_dependency": '"{id}" depende de "{dep}", que não existe na receita.',
    "recipe.dependency_cycle": "Dependência em ciclo entre: {ids}.",
    "recipe.unknown_backup_ref": '"{app}" se refere ao backup "{backup}", que não existe.',
    "recipe.unknown_tweak": 'Ajuste desconhecido: "{id}".',
    "recipe.unknown_bloat": 'Pacote de bloatware desconhecido: "{id}".',
    "recipe.blocked_bloat": '"{id}" não pode ser removido: {reason}',
    "recipe.missing_installer": 'O app "{id}" precisa de um instalador (campo installer.path).',
    "recipe.missing_winget_id": 'O app "{id}" é instalado pelo winget, mas não tem winget_id.',
    "recipe.portable_needs_backup": (
        'O app portátil "{id}" precisa apontar a pasta do programa (portable_backup).'
    ),
    "recipe.unknown_installer_type": (
        'O instalador de "{id}" é de tipo desconhecido: informe os argumentos silenciosos.'
    ),
    "recipe.migration_unsupported": (
        "Esta receita foi criada por uma versão mais nova do WinKit (formato {found}); "
        "esta versão entende até o formato {supported}."
    ),
    # ---------------------------------------------------------------- caminhos
    "paths.inside_windows": "Pastas dentro de C:\\Windows não podem ser copiadas: {path}",
    "paths.absolute_warning": (
        "Este caminho fica fora das pastas do usuário e depende da unidade {drive} existir "
        "no PC novo: {path}"
    ),
    "paths.drive_missing": "A unidade {drive} não existe neste PC.",
    # ---------------------------------------------------------------- pendrive / construtor
    "pendrive.none": (
        "Nenhum pendrive Ventoy foi encontrado. Conecte o pendrive (com o Ventoy já instalado) "
        "e tente de novo."
    ),
    "pendrive.many": "Mais de um pendrive Ventoy encontrado. Escolha um com --pendrive.",
    "pendrive.not_found_letter": "A unidade {letter} não é a partição de dados de um pendrive Ventoy.",
    "pendrive.fat32_big_file": (
        "O pendrive está em FAT32, que não aceita arquivos acima de 4 GB: {path}"
    ),
    "pendrive.no_space": (
        "Espaço insuficiente no pendrive: são necessários {needed}, há {free} livres "
        "(deixando {margin} de margem)."
    ),
    "builder.summary": "Resumo da construção:",
    "builder.done": "Pendrive pronto em {root}.",
    "builder.iso_found": "ISO encontrada: {name} — Windows {os} build {build}, {arch}, {langs}",
    "builder.iso_skipped": "Ignorada (não parece uma ISO do Windows): {name}",
    "builder.no_isos": "Nenhuma ISO do Windows encontrada no pendrive.",
    "builder.arch_mismatch": (
        "A ISO {name} é {iso_arch}, mas a receita é para {recipe_arch}. Ela não receberá o "
        "modelo do WinKit."
    ),
    "builder.ventoy_json_invalid": (
        "O ventoy.json existente é inválido ({detail}). Nada foi alterado. Corrija ou apague "
        "o arquivo e tente de novo."
    ),
    "builder.confirm": "Continuar? [s/N] ",
    "builder.cancelled": "Cancelado. Nada foi alterado.",
    "validate.ok": "Tudo certo: o pendrive está consistente.",
    "validate.problems": Plural(
        one="Foi encontrado {n} problema:", other="Foram encontrados {n} problemas:"
    ),
    "validate.warnings": "Avisos ({count}):",
    # ---------------------------------------------------------------- coletor
    "collect.apps_found": Plural(
        one="{n} aplicativo encontrado.", other="{n} aplicativos encontrados."
    ),
    "collect.drivers_found": Plural(
        one="{n} driver de terceiros encontrado.", other="{n} drivers de terceiros encontrados."
    ),
    "collect.vss_unavailable": (
        "Não foi possível criar a cópia de sombra de {volume} ({detail}). Copiando diretamente: "
        "arquivos em uso podem falhar."
    ),
    "collect.vss_not_ntfs": ("{volume} não é um disco NTFS interno; copiando sem cópia de sombra."),
    "collect.dpapi_warning": (
        "{path}: {what}. O backup será feito, mas isso não vai funcionar no PC novo."
    ),
    "collect.close_app_hint": (
        "Dica: feche {app} antes da captura; bancos de dados abertos podem ficar inconsistentes."
    ),
    "collect.many_files": "{path} tem {count} arquivos; a cópia para o pendrive pode demorar.",
    # ---------------------------------------------------------------- agente
    "agent.title": "WinKit — Finalizando a configuração",
    "agent.done_before_login": "Já feito antes do login",
    "agent.todo_now": "A fazer agora",
    "agent.starting_in": "Iniciando em {seconds} s…",
    "agent.start": "Iniciar",
    "agent.postpone": "Adiar para o próximo login",
    "agent.progress": "{done} de {total} — {current}",
    "agent.tray_tip": "WinKit: {done} de {total} — {current}",
    "agent.finished": "WinKit concluído",
    "agent.finished_with_warnings": Plural(
        one="WinKit concluído — {n} aviso", other="WinKit concluído — {n} avisos"
    ),
    "agent.finished_with_failures": Plural(
        one="WinKit concluído — {n} falha. Abra o resumo.",
        other="WinKit concluído — {n} falhas. Abra o resumo.",
    ),
    "agent.reconnect_pendrive": "Reconecte o pendrive WinKit para continuar.",
    "agent.reboot_needed": "É preciso reiniciar para continuar a configuração.",
    "agent.reboot_now": "Reiniciar agora",
    "agent.reboot_later": "Depois",
    "agent.reboot_idle_warning": "O computador vai reiniciar em {seconds} s para continuar a configuração.",
    "agent.summary_shortcut": "Resumo do WinKit",
    "agent.already_running": "O WinKit já está em execução.",
    "agent.waiting_winget": "Aguardando o winget ficar disponível…",
    "agent.waiting_network": "Aguardando conexão com a internet…",
    # ---------------------------------------------------------------- interface do Agente
    "ui.ask": "Perguntar",
    "ui.ask_tip": "Mostrar na janela do primeiro login para confirmar na hora",
    "ui.agent.title": "Finalizando a configuração",
    "ui.agent.subtitle": "O Windows já está instalado. Falta pouco para deixar tudo do seu jeito.",
    "ui.agent.nothing_before": "Nada — tudo será feito agora.",
    "ui.agent.included": "incluído",
    "ui.agent.only_summary": "Só falta gerar o resumo.",
    "ui.agent.todo_footer": "Desligue o que não quiser agora. Itens sem chave fazem parte da receita.",
    "ui.agent.countdown_paused": "Contagem pausada — clique em Iniciar quando quiser.",
    "ui.agent.progress_title": "Configurando…",
    "ui.agent.minimize": "Continuar em segundo plano",
    "ui.agent.open_summary": "Abrir resumo",
    "ui.agent.close": "Fechar",
    "ui.agent.all_done": "Tudo pronto",
    "ui.agent.done_with_failures": "Concluído com pendências",
    "ui.agent.reboot_title": "Reiniciar agora?",
    "ui.agent.show_progress": "Mostrar progresso",
    "ui.count.driver": Plural(one="{n} driver instalado", other="{n} drivers instalados"),
    "ui.count.bloat": Plural(
        one="{n} app pré-instalado removido", other="{n} apps pré-instalados removidos"
    ),
    "ui.count.tweak": Plural(one="{n} ajuste aplicado", other="{n} ajustes aplicados"),
    "ui.count.power": Plural(one="Plano de energia ajustado", other="Plano de energia ajustado"),
    "ui.count.backup": Plural(
        one="{n} configuração restaurada", other="{n} configurações restauradas"
    ),
    "ui.count.app": Plural(one="{n} app instalado", other="{n} apps instalados"),
    # ---------------------------------------------------------------- títulos das etapas
    "plan.driver": "Driver: {name}",
    "plan.bloat": "Remover: {name}",
    "plan.tweak": "Ajuste: {name}",
    "plan.power": "Plano de energia",
    "plan.backup": "Restaurar: {name}",
    "plan.app": "Instalar: {name}",
    "plan.shortcut": "Atalhos: {name}",
    "plan.rename_computer": "Nome do computador",
    "plan.windows_update": "Windows Update",
    "plan.finalize": "Concluir e gerar resumo",
    "plan.excluded_os": "não se aplica a esta versão do Windows",
    "plan.excluded_unknown_tweak": "ajuste desconhecido no catálogo",
    "plan.excluded_specialize": "aplicado durante a instalação do Windows",
    "plan.excluded_unknown_bloat": "pacote desconhecido no catálogo",
    # ---------------------------------------------------------------- resumo
    "summary.title": "Resumo do WinKit",
    "summary.total_time": "Tempo total: {duration}",
    "summary.phase_time": "Fase {phase}: {duration}",
    "summary.counts": "{done} feitos · {failed} com falha · {skipped} pulados",
    "summary.failures": "Falhas",
    "summary.warnings": "Avisos",
    "summary.open_log": "Abrir log",
    "summary.retry_failed": "Tentar de novo os que falharam",
    "summary.remove_shortcut": "Apagar este atalho",
    "summary.set_password": "Sua conta está sem senha. Defina uma em Configurações > Contas.",
    # ---------------------------------------------------------------- etapas (motivos)
    "step.dependency_failed": 'não executado porque "{dep}" falhou',
    "step.already_done": "já estava feito",
    "step.drive_missing": "a unidade {drive} não existe",
    "step.no_network": "sem conexão com a internet; será tentado no próximo login",
    "step.winget_unavailable": "o winget não ficou disponível; será tentado no próximo login",
    "step.exit_code": "o instalador retornou o código {code}",
    "step.timeout": "o instalador excedeu o tempo limite de {minutes} min",
    "step.hash_mismatch": "o arquivo no pendrive está corrompido ou foi alterado: {path}",
    "step.not_selected": "desmarcado na janela",
    "step.manual_install_hint": "Instale manualmente; o instalador está em {path}",
    "step.os_not_applicable": "não se aplica a esta versão do Windows",
    "step.failed_generic": "falhou: {detail}",
    "step.not_in_recipe": "não está mais na receita",
    "step.wu_failed": "o Windows Update falhou: {detail}",
    "step.wu_none": "nenhuma atualização disponível",
    "step.wu_code": "o Windows Update terminou com o código {code}",
    "step.wu_installed": Plural(
        one="{n} atualização instalada", other="{n} atualizações instaladas"
    ),
    "step.wu_some_errors": Plural(
        one="{n} atualização instalada; houve erros (veja o log)",
        other="{n} atualizações instaladas; algumas com erro (veja o log)",
    ),
    "step.pnputil_code": "o pnputil retornou o código {code}",
    "step.driver_no_device": "nenhum dispositivo presente usa este driver",
    "step.bloat_absent": "não estava instalado",
    "step.bloat_removed": "removido ({provisioned} provisionado, {installed} instalado)",
    "step.power_scheme_failed": "o plano {scheme} não pôde ser ativado",
    "step.hibernate_failed": "a hibernação não pôde ser alterada",
    "step.power_both_failed": "o plano {scheme} não pôde ser ativado e a hibernação não pôde ser alterada",
    "step.no_name_chosen": "nenhum nome escolhido",
    "step.invalid_name": "nome inválido: {name}",
    "step.same_name": "o computador já tinha esse nome",
    "step.renamed": "renomeado para {name}",
    "step.backup_missing": "backup ausente no pendrive: {path}",
    "step.backup_file_missing": "o arquivo {name} não está no backup",
    "step.kept_existing": "já existia no destino (mantido)",
    "step.restored_to": "restaurado em {path}",
    "step.not_implemented": 'etapa do tipo "{kind}" ainda não implementada',
    "step.pending_others": Plural(
        one="{n} etapa pendente: {ids}", other="{n} etapas pendentes: {ids}"
    ),
    "step.finalize_counts": "{done} feitas, {failed} com falha",
    "step.portable_by_shortcut": "app portátil: tratado pela etapa de atalhos",
    "step.no_shortcuts": "nenhum atalho definido",
    "step.winget_code": "o winget retornou o código {code}",
    "step.installer_failed": "o instalador retornou o código {code}. Instale manualmente; o instalador está em {path}",
    "step.waiting_dependency": 'aguardando "{dep}"',
    "step.failed_unknown": "falhou",
    "step.interrupted_repeatedly": "interrompida repetidamente (reinício ou queda de energia)",
    "agent.recipe_changed": "A receita mudou depois do início; etapas novas foram acrescentadas.",
    "summary.status.done": "feito",
    "summary.status.failed": "falhou",
    "summary.status.skipped": "pulado",
    "summary.status.pending": "pendente",
    "summary.status.running": "interrompido",
    "summary.everything": "Tudo o que foi feito",
    "summary.full_log": "Log completo: {path}",
    "summary.generated_at": "Gerado em {when}",
    "summary.backup_warning": "{name}: {warning}",
}
