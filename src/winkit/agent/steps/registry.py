"""Mapa tipo de etapa → implementação."""

from __future__ import annotations

from winkit.agent.steps.app import AppStep, ShortcutStep
from winkit.agent.steps.backup import BackupStep
from winkit.agent.steps.base import StepContext, StepHandler, StepResult
from winkit.agent.steps.driver import DriverStep
from winkit.agent.steps.finalize import FinalizeStep
from winkit.agent.steps.system import BloatStep, PowerStep, RenameComputerStep
from winkit.agent.steps.tweak import TweakStep
from winkit.core.planner.models import StepKind

PLACEHOLDER_KINDS: tuple[StepKind, ...] = ("windows_update",)


class NotImplementedStep:
    """Tipo de etapa ainda não implementado nesta versão: pula com motivo claro."""

    def check(self, ctx: StepContext) -> bool:
        return False

    def run(self, ctx: StepContext) -> StepResult:
        return StepResult.skipped(f'etapa do tipo "{ctx.step.kind}" ainda não implementada')


def default_handlers() -> dict[StepKind, StepHandler]:
    placeholder = NotImplementedStep()
    handlers: dict[StepKind, StepHandler] = dict.fromkeys(PLACEHOLDER_KINDS, placeholder)
    handlers["driver"] = DriverStep()
    handlers["app"] = AppStep()
    handlers["backup"] = BackupStep()
    handlers["bloat"] = BloatStep()
    handlers["tweak"] = TweakStep()
    handlers["power"] = PowerStep()
    handlers["rename_computer"] = RenameComputerStep()
    handlers["shortcut"] = ShortcutStep()
    handlers["finalize"] = FinalizeStep()
    return handlers
