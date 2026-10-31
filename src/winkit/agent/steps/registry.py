"""Mapa tipo de etapa → implementação."""

from __future__ import annotations

from winkit.agent.steps.base import StepContext, StepHandler, StepResult
from winkit.agent.steps.finalize import FinalizeStep
from winkit.core.planner.models import StepKind

PLACEHOLDER_KINDS: tuple[StepKind, ...] = (
    "driver",
    "bloat",
    "tweak",
    "power",
    "backup",
    "app",
    "shortcut",
    "rename_computer",
    "windows_update",
)


class NotImplementedStep:
    """Tipo de etapa ainda não implementado nesta versão: pula com motivo claro."""

    def check(self, ctx: StepContext) -> bool:
        return False

    def run(self, ctx: StepContext) -> StepResult:
        return StepResult.skipped(f'etapa do tipo "{ctx.step.kind}" ainda não implementada')


def default_handlers() -> dict[StepKind, StepHandler]:
    placeholder = NotImplementedStep()
    handlers: dict[StepKind, StepHandler] = dict.fromkeys(PLACEHOLDER_KINDS, placeholder)
    handlers["finalize"] = FinalizeStep()
    return handlers
