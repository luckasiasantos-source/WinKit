"""Mapa tipo de etapa → implementação."""

from __future__ import annotations

from winkit.agent.steps.app import AppStep, ShortcutStep
from winkit.agent.steps.backup import BackupStep
from winkit.agent.steps.base import StepBase, StepContext, StepHandler, StepResult
from winkit.agent.steps.driver import DriverStep
from winkit.agent.steps.finalize import FinalizeStep
from winkit.agent.steps.restore import RestorePointStep
from winkit.agent.steps.system import BloatStep, PowerStep, RenameComputerStep
from winkit.agent.steps.tweak import TweakStep
from winkit.agent.steps.wifi import WifiStep
from winkit.agent.steps.windows_update import WindowsUpdateStep
from winkit.core.planner.models import StepKind
from winkit.i18n import msg

PLACEHOLDER_KINDS: tuple[StepKind, ...] = ()


class NotImplementedStep(StepBase):
    """Tipo de etapa ainda não implementado nesta versão: pula com motivo claro."""

    def check(self, ctx: StepContext) -> bool:
        return False

    def run(self, ctx: StepContext) -> StepResult:
        return StepResult.skipped(msg("step.not_implemented", kind=ctx.step.kind))


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
    handlers["windows_update"] = WindowsUpdateStep()
    handlers["shortcut"] = ShortcutStep()
    handlers["restore_point"] = RestorePointStep()
    handlers["wifi"] = WifiStep()
    handlers["finalize"] = FinalizeStep()
    return handlers
