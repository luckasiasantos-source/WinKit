"""Etapa: instalar um pacote de drivers do pendrive com ``pnputil`` (M4)."""

from __future__ import annotations

from winkit.agent.integrity import verify_payload
from winkit.agent.steps.base import StepContext, StepResult
from winkit.core.errors import IntegrityError, PlatformError
from winkit.i18n import msg


class DriverStep:
    def check(self, ctx: StepContext) -> bool:
        return False  # pnputil /add-driver é idempotente

    def run(self, ctx: StepContext) -> StepResult:
        item = next((d for d in ctx.recipe.drivers if d.id == ctx.step.ref), None)
        if item is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        assert ctx.pendrive is not None  # noqa: S101 — garantido pelo executor (needs_pendrive)
        try:
            verify_payload(ctx.pendrive, item.path, tree=True)
        except IntegrityError as exc:
            return StepResult.failed(msg("step.hash_mismatch", path=str(exc)), recoverable=False)
        folder = ctx.payload(item.path)
        try:
            result = ctx.services.drivers.install(folder, log=ctx.log.step_log(ctx.step.id))
        except PlatformError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        if not result.ok:
            return StepResult.failed(msg("step.pnputil_code", code=result.exit_code))
        note = msg("step.driver_no_device") if result.exit_code == 259 else None
        return StepResult.ok(note, reboot=result.reboot)
