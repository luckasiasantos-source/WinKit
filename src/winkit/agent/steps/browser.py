"""Etapa: navegador pronto (V2-12, R21). As políticas no ``HKLM`` valem quando o navegador for
instalado, então a etapa roda na Fase 1, mesmo antes dos apps."""

from __future__ import annotations

from winkit.agent.steps.base import StepBase, StepContext, StepResult
from winkit.core.browsers import operations
from winkit.core.errors import WinKitError
from winkit.core.recipe.models import BrowserConfig
from winkit.i18n import Msg, msg
from winkit.platform import browsers as policies


def _cfg(ctx: StepContext) -> BrowserConfig | None:
    return next((b for b in ctx.recipe.browsers if b.id == ctx.step.ref), None)


class BrowserStep(StepBase):
    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        cfg = _cfg(ctx)
        return cfg is not None and policies.applied(
            ctx.services.registry, operations(cfg, ctx.catalogs)
        )

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        cfg = _cfg(ctx)
        entry = ctx.catalogs.browser(ctx.step.ref)
        if cfg is None or entry is None:
            return ()
        n = sum(1 for e in cfg.extensions if e.selected)
        return (msg("preview.browser", name=entry.name, n=n),)

    def run(self, ctx: StepContext) -> StepResult:
        cfg = _cfg(ctx)
        entry = ctx.catalogs.browser(ctx.step.ref)
        if cfg is None or entry is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        ops = operations(cfg, ctx.catalogs)
        if not ops:
            return StepResult.skipped(msg("step.browser.nothing"))
        try:
            policies.apply(ctx.services.registry, ops)
        except WinKitError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        return StepResult.ok(msg("step.browser.done", name=entry.name))
