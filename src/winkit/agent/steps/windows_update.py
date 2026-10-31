"""Etapa: Windows Update depois da instalação (item 21, versão leve — D-011)."""

from __future__ import annotations

from winkit.agent.steps.base import StepContext, StepResult
from winkit.core.errors import WinKitError
from winkit.platform.windows_update import WU_SUCCEEDED_WITH_ERRORS


class WindowsUpdateStep:
    def check(self, ctx: StepContext) -> bool:
        return False

    def run(self, ctx: StepContext) -> StepResult:
        include = ctx.recipe.updates.include_drivers_from_windows_update
        try:
            res = ctx.services.updater.install_all(
                include_drivers=include, log=ctx.log.step_log(ctx.step.id)
            )
        except WinKitError as exc:
            return StepResult.failed(f"Windows Update: {exc}")
        if res.found == 0:
            return StepResult.ok("nenhuma atualização disponível")
        for title in res.titles:
            ctx.log.info(f"atualização: {title}", step=ctx.step.id)
        if not res.ok:
            return StepResult.failed(f"Windows Update terminou com o código {res.result_code}")
        note = f"{res.found} atualização(ões) instalada(s)"
        if res.result_code == WU_SUCCEEDED_WITH_ERRORS:
            note += ", algumas com erro (veja o log)"
        return StepResult.ok(note, reboot=res.reboot_required)
