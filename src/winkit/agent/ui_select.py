"""Escolhe a apresentação da Fase 2 conforme o modo da receita (D-008).

- ``countdown`` / ``interactive``: janela Qt (com bandeja);
- ``silent``: só bandeja e notificação final (ou nada, se ambos estiverem desligados).

O Qt só é importado aqui dentro, nunca no caminho da Fase 1 (R-35).
"""

from __future__ import annotations

import logging

from winkit.agent.progress import AgentUi, NullUi
from winkit.core.recipe.models import Recipe

log = logging.getLogger(__name__)


def select_ui(recipe: Recipe) -> AgentUi:
    ex = recipe.execution
    if ex.mode == "silent" and not (ex.show_tray_icon or ex.notify_on_finish):
        return NullUi()
    try:
        from winkit.agent.ui.qt import QtAgentUi  # noqa: PLC0415 — Qt só quando necessário
    except ImportError as exc:  # Qt indisponível: segue sem janela
        log.warning("interface gráfica indisponível (%s); seguindo sem janela", exc)
        return NullUi()
    return QtAgentUi(ex)
