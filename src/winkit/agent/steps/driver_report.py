"""Etapa: dispositivos sem driver e busca dirigida no Windows Update (V2-09, R28).

É um relatório: roda uma vez por execução (``check`` sempre falso) e grava no estado a lista
final para o resumo. Só os drivers que casam com os ids de hardware dos dispositivos com
problema são instalados.
"""

from __future__ import annotations

from winkit.agent.steps.base import StepBase, StepContext, StepResult, item
from winkit.core.devices import hardware_ids, needing_drivers
from winkit.core.errors import WinKitError
from winkit.core.live import PreviewItem
from winkit.i18n import msg


class DriverReportStep(StepBase):
    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        return False

    def preview(self, ctx: StepContext) -> PreviewItem:
        """Só consulta os dispositivos (leitura); nada é instalado na prévia (R-54)."""
        try:
            missing = needing_drivers(ctx.services.devices.problem_devices())
        except WinKitError:
            missing = []
        if not missing:
            return item(ctx, "already_done")
        return item(ctx, "will_change", (msg("preview.driver_report", n=len(missing)),))

    def run(self, ctx: StepContext) -> StepResult:
        devices = ctx.services.devices
        try:
            found = devices.problem_devices()
        except WinKitError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        missing = needing_drivers(found)
        reboot = False
        installed: list[str] = []
        if missing and ctx.recipe.updates.fix_missing_drivers:
            if ctx.services.env.has_internet():
                ids = hardware_ids(missing)
                log = ctx.paths.logs / "drivers_windows_update.log"
                try:
                    result = ctx.services.updater.install_drivers_for(ids, log=log)
                except WinKitError as exc:
                    ctx.log.warning(f"busca de drivers falhou: {exc}", step=ctx.step.id)
                else:
                    installed = list(result.titles)
                    reboot = result.reboot_required
                    ctx.log.info(f"drivers instalados: {len(installed)}", step=ctx.step.id)
                    found = devices.problem_devices()
            else:
                ctx.log.info("sem internet: busca de drivers não feita", step=ctx.step.id)
        remaining = needing_drivers(found)
        ctx.state.devices = remaining
        ctx.state.drivers_found = installed
        if not remaining:
            key = "step.driver_report.fixed" if installed else "step.driver_report.ok"
            return StepResult.ok(msg(key, n=len(installed)), reboot=reboot)
        return StepResult.ok(msg("step.driver_report.remaining", n=len(remaining)), reboot=reboot)
