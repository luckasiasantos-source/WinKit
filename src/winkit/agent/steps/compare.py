"""Etapa: relatório antes/depois (V2-19, R29). Compara o Windows novo com o inventário do PC
antigo gravado no pendrive e guarda o resultado para o resumo. É um relatório: roda uma vez."""

from __future__ import annotations

from winkit.agent.steps.base import StepBase, StepContext, StepResult
from winkit.core import layout
from winkit.core.compare import compare
from winkit.core.errors import WinKitError
from winkit.core.inventory_snapshot import Snapshot
from winkit.i18n import Msg, msg
from winkit.platform.snapshot import take_snapshot


class CompareStep(StepBase):
    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        return False

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        return (msg("preview.compare"),)

    def run(self, ctx: StepContext) -> StepResult:
        if ctx.pendrive is None:
            return StepResult.deferred(msg("agent.reconnect_pendrive"))
        path = ctx.pendrive / layout.snapshot_file(ctx.recipe.meta.profile_id)
        if not path.is_file():
            return StepResult.skipped(msg("step.compare.no_before"))
        try:
            before = Snapshot.model_validate_json(path.read_text(encoding="utf-8"))
            s = ctx.services
            after = take_snapshot(
                s.inventory, s.devices, s.features, ctx.catalogs, build=s.env.windows_build()
            )
        except (WinKitError, OSError, ValueError) as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        names = {f.id: f.name for f in ctx.catalogs.features}
        result = compare(before, after, names)
        ctx.state.comparison = result
        if result.empty:
            return StepResult.ok(msg("step.compare.nothing"))
        n = len(result.missing_apps) + len(result.driverless) + len(result.missing_features)
        return StepResult.ok(msg("step.compare.found", n=n))
