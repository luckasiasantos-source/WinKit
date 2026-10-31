"""Textos en español neutro (tú). Mismas claves y marcadores que ``pt_br`` (R-51)."""

from __future__ import annotations

from winkit.i18n.core import Entry, Plural

MESSAGES: dict[str, Entry] = {
    "legacy.text": "{text}",
    # ---------------------------------------------------------------- general
    "app.name": "WinKit",
    "error.unexpected": "Error inesperado: {detail}. Consulta el registro para más detalles.",
    "error.not_windows": "Este comando solo funciona en Windows.",
    "error.needs_admin": "Este comando debe ejecutarse como administrador.",
    # ---------------------------------------------------------------- receta
    "recipe.invalid": "La receta tiene problemas:\n{problems}",
    "recipe.silent_missing": "En modo silencioso nadie responderá preguntas. Completa: {fields}",
    "recipe.computer_name_invalid": (
        'Nombre de equipo no válido: "{name}". Usa de 1 a 15 caracteres '
        "(letras, números y guion), que no sean solo números."
    ),
    "recipe.username_invalid": 'Nombre de usuario no válido: "{name}". {reason}',
    "recipe.username_reserved": "Este nombre está reservado por Windows.",
    "recipe.username_chars": 'No uses los caracteres \\ / [ ] : ; | = , + * ? < > " @',
    "recipe.password_missing": "La contraseña está marcada como guardada, pero está vacía.",
    "recipe.password_stored_warning": (
        "Atención: la contraseña quedará legible en la memoria USB (Windows solo acepta "
        "contraseñas en texto o Base64 en el archivo de respuestas)."
    ),
    "recipe.duplicate_id": 'Identificador repetido: "{id}" aparece más de una vez en {section}.',
    "recipe.unknown_dependency": '"{id}" depende de "{dep}", que no existe en la receta.',
    "recipe.dependency_cycle": "Dependencia circular entre: {ids}.",
    "recipe.unknown_backup_ref": '"{app}" hace referencia a la copia "{backup}", que no existe.',
    "recipe.unknown_tweak": 'Ajuste desconocido: "{id}".',
    "recipe.unknown_bloat": 'Paquete de bloatware desconocido: "{id}".',
    "recipe.blocked_bloat": '"{id}" no se puede quitar: {reason}',
    "recipe.missing_installer": 'La aplicación "{id}" necesita un instalador (campo installer.path).',
    "recipe.missing_winget_id": 'La aplicación "{id}" se instala con winget, pero no tiene winget_id.',
    "recipe.portable_needs_backup": (
        'La aplicación portátil "{id}" debe indicar la carpeta del programa (portable_backup).'
    ),
    "recipe.unknown_installer_type": (
        'El instalador de "{id}" es de un tipo desconocido: indica los argumentos silenciosos.'
    ),
    "recipe.migration_unsupported": (
        "Esta receta la creó una versión más nueva de WinKit (formato {found}); "
        "esta versión entiende hasta el formato {supported}."
    ),
    # ---------------------------------------------------------------- rutas
    "paths.inside_windows": "Las carpetas dentro de C:\\Windows no se pueden copiar: {path}",
    "paths.absolute_warning": (
        "Esta ruta está fuera de las carpetas del usuario y depende de que la unidad {drive} "
        "exista en el PC nuevo: {path}"
    ),
    "paths.drive_missing": "La unidad {drive} no existe en este PC.",
    # ---------------------------------------------------------------- memoria USB / constructor
    "pendrive.none": (
        "No se encontró ninguna memoria USB con Ventoy. Conecta la memoria (con Ventoy ya "
        "instalado) e inténtalo de nuevo."
    ),
    "pendrive.many": "Se encontró más de una memoria USB con Ventoy. Elige una con --pendrive.",
    "pendrive.not_found_letter": "La unidad {letter} no es la partición de datos de una memoria USB con Ventoy.",
    "pendrive.fat32_big_file": "La memoria USB está en FAT32, que no acepta archivos de más de 4 GB: {path}",
    "pendrive.no_space": (
        "Espacio insuficiente en la memoria USB: se necesitan {needed}, hay {free} libres "
        "(dejando {margin} de margen)."
    ),
    "builder.summary": "Resumen de la preparación:",
    "builder.done": "Memoria USB lista en {root}.",
    "builder.iso_found": "ISO encontrada: {name} — Windows {os} compilación {build}, {arch}, {langs}",
    "builder.iso_skipped": "Ignorada (no parece una ISO de Windows): {name}",
    "builder.no_isos": "No se encontró ninguna ISO de Windows en la memoria USB.",
    "builder.arch_mismatch": (
        "La ISO {name} es {iso_arch}, pero la receta es para {recipe_arch}. No recibirá la "
        "plantilla de WinKit."
    ),
    "builder.ventoy_json_invalid": (
        "El ventoy.json existente no es válido ({detail}). No se cambió nada. Corrige o borra "
        "el archivo e inténtalo de nuevo."
    ),
    "builder.confirm": "¿Continuar? [s/N] ",
    "builder.cancelled": "Cancelado. No se cambió nada.",
    "validate.ok": "Todo bien: la memoria USB está en orden.",
    "validate.problems": Plural(
        one="Se encontró {n} problema:", other="Se encontraron {n} problemas:"
    ),
    "validate.warnings": "Avisos ({count}):",
    # ---------------------------------------------------------------- recolector
    "collect.apps_found": Plural(
        one="{n} aplicación encontrada.", other="{n} aplicaciones encontradas."
    ),
    "collect.drivers_found": Plural(
        one="{n} controlador de terceros encontrado.",
        other="{n} controladores de terceros encontrados.",
    ),
    "collect.vss_unavailable": (
        "No se pudo crear la instantánea de {volume} ({detail}). Copiando directamente: "
        "los archivos en uso pueden fallar."
    ),
    "collect.vss_not_ntfs": "{volume} no es un disco NTFS interno; copiando sin instantánea.",
    "collect.dpapi_warning": (
        "{path}: {what}. Se hará la copia, pero esto no funcionará en el PC nuevo."
    ),
    "collect.close_app_hint": (
        "Consejo: cierra {app} antes de la captura; las bases de datos abiertas pueden quedar "
        "inconsistentes."
    ),
    "collect.many_files": "{path} tiene {count} archivos; copiarlos a la memoria USB puede tardar.",
    # ---------------------------------------------------------------- agente
    "agent.title": "WinKit — Terminando la configuración",
    "agent.done_before_login": "Ya hecho antes del inicio de sesión",
    "agent.todo_now": "Por hacer ahora",
    "agent.starting_in": "Empieza en {seconds} s…",
    "agent.start": "Empezar",
    "agent.postpone": "Posponer al próximo inicio de sesión",
    "agent.progress": "{done} de {total} — {current}",
    "agent.tray_tip": "WinKit: {done} de {total} — {current}",
    "agent.finished": "WinKit terminó",
    "agent.finished_with_warnings": Plural(
        one="WinKit terminó — {n} aviso", other="WinKit terminó — {n} avisos"
    ),
    "agent.finished_with_failures": Plural(
        one="WinKit terminó — {n} error. Abre el resumen.",
        other="WinKit terminó — {n} errores. Abre el resumen.",
    ),
    "agent.reconnect_pendrive": "Vuelve a conectar la memoria USB de WinKit para continuar.",
    "agent.reboot_needed": "Hay que reiniciar para continuar la configuración.",
    "agent.reboot_now": "Reiniciar ahora",
    "agent.reboot_later": "Más tarde",
    "agent.reboot_idle_warning": "El equipo se reiniciará en {seconds} s para continuar la configuración.",
    "agent.summary_shortcut": "Resumen de WinKit",
    "agent.already_running": "WinKit ya se está ejecutando.",
    "agent.waiting_winget": "Esperando a que winget esté disponible…",
    "agent.waiting_network": "Esperando conexión a internet…",
    # ---------------------------------------------------------------- ventana del agente
    "ui.ask": "Preguntar",
    "ui.ask_tip": "Mostrar en la ventana del primer inicio de sesión para confirmar en el momento",
    "ui.agent.title": "Terminando la configuración",
    "ui.agent.subtitle": "Windows ya está instalado. Falta poco para dejarlo a tu gusto.",
    "ui.agent.nothing_before": "Nada — todo se hará ahora.",
    "ui.agent.included": "incluido",
    "ui.agent.only_summary": "Solo falta generar el resumen.",
    "ui.agent.todo_footer": "Desactiva lo que no quieras ahora. Los elementos sin interruptor son parte de la receta.",
    "ui.agent.countdown_paused": "Cuenta regresiva en pausa — haz clic en Empezar cuando quieras.",
    "ui.agent.progress_title": "Configurando…",
    "ui.agent.minimize": "Continuar en segundo plano",
    "ui.agent.open_summary": "Abrir resumen",
    "ui.agent.close": "Cerrar",
    "ui.agent.all_done": "Todo listo",
    "ui.agent.done_with_failures": "Terminado con pendientes",
    "ui.agent.reboot_title": "¿Reiniciar ahora?",
    "ui.agent.show_progress": "Mostrar progreso",
    "ui.count.driver": Plural(
        one="{n} controlador instalado", other="{n} controladores instalados"
    ),
    "ui.count.bloat": Plural(
        one="{n} aplicación preinstalada quitada", other="{n} aplicaciones preinstaladas quitadas"
    ),
    "ui.count.tweak": Plural(one="{n} ajuste aplicado", other="{n} ajustes aplicados"),
    "ui.count.power": Plural(one="Plan de energía ajustado", other="Plan de energía ajustado"),
    "ui.count.backup": Plural(
        one="{n} configuración restaurada", other="{n} configuraciones restauradas"
    ),
    "ui.count.app": Plural(one="{n} aplicación instalada", other="{n} aplicaciones instaladas"),
    # ---------------------------------------------------------------- títulos de los pasos
    "plan.driver": "Controlador: {name}",
    "plan.bloat": "Quitar: {name}",
    "plan.tweak": "Ajuste: {name}",
    "plan.power": "Plan de energía",
    "plan.backup": "Restaurar: {name}",
    "plan.app": "Instalar: {name}",
    "plan.shortcut": "Accesos directos: {name}",
    "plan.rename_computer": "Nombre del equipo",
    "plan.windows_update": "Windows Update",
    "plan.finalize": "Terminar y generar el resumen",
    "plan.excluded_os": "no se aplica a esta versión de Windows",
    "plan.excluded_unknown_tweak": "ajuste desconocido en el catálogo",
    "plan.excluded_specialize": "se aplica durante la instalación de Windows",
    "plan.excluded_unknown_bloat": "paquete desconocido en el catálogo",
    # ---------------------------------------------------------------- resumen
    "summary.title": "Resumen de WinKit",
    "summary.total_time": "Tiempo total: {duration}",
    "summary.phase_time": "Fase {phase}: {duration}",
    "summary.counts": "{done} hechos · {failed} con error · {skipped} omitidos",
    "summary.failures": "Errores",
    "summary.warnings": "Avisos",
    "summary.open_log": "Abrir registro",
    "summary.retry_failed": "Reintentar los que fallaron",
    "summary.remove_shortcut": "Borrar este acceso directo",
    "summary.set_password": "Tu cuenta no tiene contraseña. Define una en Configuración > Cuentas.",
    # ---------------------------------------------------------------- pasos (motivos)
    "step.dependency_failed": 'no se ejecutó porque "{dep}" falló',
    "step.already_done": "ya estaba hecho",
    "step.drive_missing": "la unidad {drive} no existe",
    "step.no_network": "sin conexión a internet; se intentará en el próximo inicio de sesión",
    "step.winget_unavailable": "winget no estuvo disponible; se intentará en el próximo inicio de sesión",
    "step.exit_code": "el instalador devolvió el código {code}",
    "step.timeout": "el instalador superó el tiempo límite de {minutes} min",
    "step.hash_mismatch": "el archivo de la memoria USB está dañado o fue modificado: {path}",
    "step.not_selected": "desactivado en la ventana",
    "step.manual_install_hint": "Instálalo manualmente; el instalador está en {path}",
    "step.os_not_applicable": "no se aplica a esta versión de Windows",
    "step.failed_generic": "falló: {detail}",
    "step.not_in_recipe": "ya no está en la receta",
    "step.wu_failed": "Windows Update falló: {detail}",
    "step.wu_none": "no hay actualizaciones disponibles",
    "step.wu_code": "Windows Update terminó con el código {code}",
    "step.wu_installed": Plural(
        one="{n} actualización instalada", other="{n} actualizaciones instaladas"
    ),
    "step.wu_some_errors": Plural(
        one="{n} actualización instalada; hubo errores (consulta el registro)",
        other="{n} actualizaciones instaladas; algunas con errores (consulta el registro)",
    ),
    "step.pnputil_code": "pnputil devolvió el código {code}",
    "step.driver_no_device": "ningún dispositivo presente usa este controlador",
    "step.bloat_absent": "no estaba instalado",
    "step.bloat_removed": "quitado ({provisioned} aprovisionado, {installed} instalado)",
    "step.power_scheme_failed": "no se pudo activar el plan {scheme}",
    "step.hibernate_failed": "no se pudo cambiar la hibernación",
    "step.power_both_failed": "no se pudo activar el plan {scheme} ni cambiar la hibernación",
    "step.no_name_chosen": "no se eligió ningún nombre",
    "step.invalid_name": "nombre no válido: {name}",
    "step.same_name": "el equipo ya tenía ese nombre",
    "step.renamed": "renombrado a {name}",
    "step.backup_missing": "falta la copia en la memoria USB: {path}",
    "step.backup_file_missing": "el archivo {name} no está en la copia",
    "step.kept_existing": "ya existía en el destino (se conservó)",
    "step.restored_to": "restaurado en {path}",
    "step.not_implemented": 'el paso de tipo "{kind}" aún no está implementado',
    "step.pending_others": Plural(
        one="{n} paso pendiente: {ids}", other="{n} pasos pendientes: {ids}"
    ),
    "step.finalize_counts": "{done} hechos, {failed} con error",
    "step.portable_by_shortcut": "aplicación portátil: la gestiona el paso de accesos directos",
    "step.no_shortcuts": "no hay accesos directos definidos",
    "step.winget_code": "winget devolvió el código {code}",
    "step.installer_failed": "el instalador devolvió el código {code}. Instálalo manualmente; el instalador está en {path}",
    "step.waiting_dependency": 'esperando "{dep}"',
    "step.failed_unknown": "falló",
    "step.interrupted_repeatedly": "interrumpido varias veces (reinicio o corte de energía)",
    "agent.recipe_changed": "La receta cambió después de empezar; se agregaron pasos nuevos.",
    "summary.status.done": "hecho",
    "summary.status.failed": "falló",
    "summary.status.skipped": "omitido",
    "summary.status.pending": "pendiente",
    "summary.status.running": "interrumpido",
    "summary.everything": "Todo lo que se hizo",
    "summary.full_log": "Registro completo: {path}",
    "summary.generated_at": "Generado el {when}",
    "summary.backup_warning": "{name}: {warning}",
}
