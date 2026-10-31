"""Etapa: ponto de restauração "Windows pronto" ou "antes de aplicar" (V2-10, D-033)."""

from __future__ import annotations

import os

from winkit.agent.steps.base import StepBase, StepContext, StepResult
from winkit.core.errors import WinKitError
from winkit.core.text import Msg
from winkit.i18n import msg, t
from winkit.i18n.format import format_datetime
from winkit.platform.restore import FREQUENCY_VALUE, SR_KEY, SR_POLICY_KEY


def system_drive() -> str:
    """``C:\\`` — o volume do Windows vem da variável de ambiente, nunca fixo (R-15)."""
    return (os.environ.get("SYSTEMDRIVE") or "C:").rstrip("\\") + "\\"


class RestorePointStep(StepBase):
    live_safe = True

    def _description(self, ctx: StepContext) -> str:
        key = (
            "restore.description_before"
            if ctx.step.ref == "before"
            else "restore.description_ready"
        )
        return t(key, when=format_datetime(ctx.clock()))

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        percent = ctx.recipe.restore_point.max_disk_percent
        return (msg("preview.restore_point", percent=percent),)

    def run(self, ctx: StepContext) -> StepResult:
        reg = ctx.services.registry
        if reg.get("HKLM", SR_POLICY_KEY, "DisableSR") == 1:
            return StepResult.skipped(msg("step.restore.disabled_by_policy"))
        restore = ctx.services.restore
        drive = system_drive()
        previous = reg.get("HKLM", SR_KEY, FREQUENCY_VALUE)
        try:
            restore.enable(drive)
            restore.ensure_max_percent(drive, ctx.recipe.restore_point.max_disk_percent)
            # sem isso o Windows recusa um segundo ponto em 24 h
            reg.set("HKLM", SR_KEY, FREQUENCY_VALUE, "dword", 0)
            code = restore.create(self._description(ctx))
        except WinKitError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        finally:
            if previous is None:
                reg.delete_value("HKLM", SR_KEY, FREQUENCY_VALUE)
            else:
                reg.set("HKLM", SR_KEY, FREQUENCY_VALUE, "dword", previous)
        if code != 0:
            return StepResult.failed(msg("step.restore.code", code=code))
        return StepResult.ok(msg("step.restore.created"))
