"""Etapas de manutenção (V2-18, R27).

- ``maintenance:winget``: tarefa semanal (ou a cada 4 semanas) do **usuário** que atualiza os
  apps com o winget; Fase 2, porque o winget é por usuário. O ``winget.exe`` é resolvido pelo
  caminho absoluto na hora (R-12).
- ``maintenance:defrag``: garante a otimização nativa do Windows; nunca cria uma própria.
"""

from __future__ import annotations

from winkit.agent.steps.base import StepBase, StepContext, StepResult, local_path
from winkit.core.errors import WinKitError
from winkit.core.maintenance import DEFRAG_FOLDER, DEFRAG_TASK, TaskSpec, winget_task
from winkit.i18n import Msg, msg


def _spec(ctx: StepContext) -> TaskSpec | None:
    folders = ctx.folders()
    winget = f"{folders['LOCALAPPDATA']}\\Microsoft\\WindowsApps\\winget.exe"
    log = f"{folders['PROGRAMDATA']}\\WinKit\\Manutencao\\winget.log"
    return winget_task(ctx.recipe.maintenance, winget, log)


class WingetMaintenanceStep(StepBase):
    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        spec = _spec(ctx)
        return spec is None or ctx.services.scheduler.user_task_matches(spec)

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        m = ctx.recipe.maintenance
        return (msg(f"preview.maintenance_winget_{m.winget_upgrade}", time=m.winget_time),)

    def run(self, ctx: StepContext) -> StepResult:
        spec = _spec(ctx)
        if spec is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        if not local_path(spec.execute).is_file():
            return StepResult.skipped(msg("step.maintenance.no_winget"))
        try:
            ctx.services.scheduler.ensure_user_task(spec)
        except WinKitError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        return StepResult.ok(msg("step.maintenance.winget_task"))


class DefragStep(StepBase):
    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        state = ctx.services.scheduler.builtin_task(DEFRAG_FOLDER, DEFRAG_TASK, enable=False)
        return state in ("enabled", "absent")

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        return (msg("preview.maintenance_defrag"),)

    def run(self, ctx: StepContext) -> StepResult:
        try:
            state = ctx.services.scheduler.builtin_task(DEFRAG_FOLDER, DEFRAG_TASK, enable=True)
        except WinKitError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        if state == "absent":
            return StepResult.skipped(msg("step.maintenance.no_defrag_task"))
        key = "step.maintenance.defrag_enabled" if state == "changed" else "step.already_done"
        return StepResult.ok(msg(key))


class MaintenanceStep(StepBase):
    """Despacha pelo ``ref`` da etapa (``winget`` ou ``defrag``)."""

    live_safe = True

    def _impl(self, ctx: StepContext) -> WingetMaintenanceStep | DefragStep:
        return WingetMaintenanceStep() if ctx.step.ref == "winget" else DefragStep()

    def check(self, ctx: StepContext) -> bool:
        return self._impl(ctx).check(ctx)

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        return self._impl(ctx).preview_changes(ctx)

    def run(self, ctx: StepContext) -> StepResult:
        return self._impl(ctx).run(ctx)
