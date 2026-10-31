"""Etapa: Windows Update depois da instalação (item 21, versão leve — D-011)."""

from __future__ import annotations

from winkit.agent.steps.base import StepBase, StepContext, StepResult
from winkit.core.errors import WinKitError
from winkit.i18n import msg
from winkit.platform.windows_update import WU_SUCCEEDED_WITH_ERRORS


class WindowsUpdateStep(StepBase):
    def check(self, ctx: StepContext) -> bool:
        return False

    def run(self, ctx: StepContext) -> StepResult:
        include = ctx.recipe.updates.include_drivers_from_windows_update
        try:
            res = ctx.services.updater.install_all(
                include_drivers=include, log=ctx.log.step_log(ctx.step.id)
            )
        except WinKitError as exc:
            return StepResult.failed(msg("step.wu_failed", detail=str(exc)))
        if res.found == 0:
            return StepResult.ok(msg("step.wu_none"))
        for title in res.titles:
            ctx.log.info(f"atualização: {title}", step=ctx.step.id)
        if not res.ok:
            return StepResult.failed(msg("step.wu_code", code=res.result_code))
        key = (
            "step.wu_some_errors"
            if res.result_code == WU_SUCCEEDED_WITH_ERRORS
            else "step.wu_installed"
        )
        return StepResult.ok(msg(key, n=res.found), reboot=res.reboot_required)
