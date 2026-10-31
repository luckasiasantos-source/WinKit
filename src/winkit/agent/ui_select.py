"""Escolhe a apresentação da Fase 2 conforme o modo da receita (D-008).

TODO(DT-012): no M3 todos os modos usam ``NullUi`` (sem janela); a janela Qt, a contagem
regressiva e a bandeja entram no M9.
"""

from __future__ import annotations

from winkit.agent.progress import AgentUi, NullUi
from winkit.core.recipe.models import Recipe


def select_ui(recipe: Recipe) -> AgentUi:
    del recipe
    return NullUi()
