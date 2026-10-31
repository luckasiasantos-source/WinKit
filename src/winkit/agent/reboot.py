"""Política de reinicialização da Fase 2 (PLANO.md §11.5)."""

from __future__ import annotations

from winkit.agent.eventlog import EventLog
from winkit.agent.progress import AgentUi
from winkit.agent.services import AgentServices
from winkit.core.recipe.models import RebootPolicy
from winkit.i18n import t

IDLE_SECONDS = 5 * 60
AUTO_DELAY = 60
ASK_DELAY = 15


def handle_reboot(
    policy: RebootPolicy, *, ui: AgentUi, services: AgentServices, log: EventLog
) -> bool:
    """Aplica a política. Devolve True se a reinicialização foi agendada."""
    message = t("agent.reboot_needed")
    if policy == "never":
        log.info("reinício necessário; política 'never': aguardando o usuário")
        return False
    if policy == "auto_if_idle":
        idle = services.session.idle_seconds()
        if idle >= IDLE_SECONDS:
            ui.notify(t("app.name"), t("agent.reboot_idle_warning", seconds=AUTO_DELAY))
            services.session.reboot(delay_seconds=AUTO_DELAY, message=message)
            log.info(f"reinício automático agendado (ocioso há {idle:.0f} s)")
            return True
        log.info(f"reinício adiado: usuário ativo (ocioso há {idle:.0f} s)")
        ui.notify(t("app.name"), message)
        return False
    if ui.ask_reboot():
        services.session.reboot(delay_seconds=ASK_DELAY, message=message)
        log.info("reinício confirmado pelo usuário")
        return True
    log.info("reinício adiado pelo usuário")
    return False
