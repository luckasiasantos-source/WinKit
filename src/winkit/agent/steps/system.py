"""Etapas de sistema: bloatware (item 11, 37), energia (item 34), nome do computador (item 33)."""

from __future__ import annotations

from winkit.agent.steps.base import StepBase, StepContext, StepResult
from winkit.core.errors import WinKitError
from winkit.core.recipe.validation import validate_computer_name
from winkit.i18n import msg
from winkit.platform.appx import DEPROVISIONED
from winkit.platform.system import system32

# GUIDs dos planos de energia do Windows e cópias fixas do WinKit (planos ocultos em PCs
# com Modern Standby precisam ser duplicados antes de ativar).
BALANCED = "381b4222-f694-41f0-9685-ff5bb260df2e"
HIGH_PERFORMANCE = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
ULTIMATE = "e9a42b02-d5df-448d-aa00-03f14749eb61"
WINKIT_HIGH = "6f9c2f0a-3e1b-4a4e-9d55-8f2d1c7b5a01"
WINKIT_ULTIMATE = "6f9c2f0a-3e1b-4a4e-9d55-8f2d1c7b5a02"
POWER_KEY = r"SYSTEM\CurrentControlSet\Control\Session Manager\Power"


class BloatStep(StepBase):
    def check(self, ctx: StepContext) -> bool:
        if ctx.services.appx.is_present(ctx.step.ref):
            return False
        if not ctx.recipe.bloatware.block_reinstall:
            return True
        entry = ctx.catalogs.bloat(ctx.step.ref)
        family = entry.family_name if entry else None
        return family is not None and ctx.services.registry.key_exists(
            "HKLM", f"{DEPROVISIONED}\\{family}"
        )

    def run(self, ctx: StepContext) -> StepResult:
        name = ctx.step.ref
        try:
            res = ctx.services.appx.remove(name)
        except WinKitError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        if ctx.recipe.bloatware.block_reinstall:  # item 37
            entry = ctx.catalogs.bloat(name)
            family = res.family or (entry.family_name if entry else None)
            if family:
                ctx.services.registry.create_key("HKLM", f"{DEPROVISIONED}\\{family}")
        if res.provisioned == 0 and res.installed == 0:
            return StepResult.ok(msg("step.bloat_absent"))
        return StepResult.ok(
            msg("step.bloat_removed", provisioned=res.provisioned, installed=res.installed)
        )


class PowerStep(StepBase):
    def check(self, ctx: StepContext) -> bool:
        return False

    def _powercfg(self, ctx: StepContext, *args: str) -> int:
        return ctx.services.runner.run(
            [str(system32("powercfg.exe")), *args], timeout=120
        ).exit_code

    def _activate(self, ctx: StepContext, source: str, copy: str | None) -> bool:
        if self._powercfg(ctx, "/setactive", source) == 0:
            return True
        if copy is None:
            return False
        if self._powercfg(ctx, "/setactive", copy) == 0:
            return True
        return (
            self._powercfg(ctx, "/duplicatescheme", source, copy) == 0
            and self._powercfg(ctx, "/setactive", copy) == 0
        )

    def run(self, ctx: StepContext) -> StepResult:
        p = ctx.recipe.power
        scheme_failed = hibernate_failed = False
        if p.scheme != "unchanged":
            source, copy = {
                "balanced": (BALANCED, None),
                "high_performance": (HIGH_PERFORMANCE, WINKIT_HIGH),
                "ultimate": (ULTIMATE, WINKIT_ULTIMATE),
            }[p.scheme]
            if not self._activate(ctx, source, copy):
                scheme_failed = True
        hibernate_arg = None if p.hibernate is None else ("on" if p.hibernate else "off")
        if hibernate_arg and self._powercfg(ctx, "/hibernate", hibernate_arg) != 0:
            hibernate_failed = True
        if p.fast_startup is not None:
            ctx.services.registry.set(
                "HKLM", POWER_KEY, "HiberbootEnabled", "dword", 1 if p.fast_startup else 0
            )
        if scheme_failed and hibernate_failed:
            return StepResult.failed(msg("step.power_both_failed", scheme=p.scheme))
        if scheme_failed:
            return StepResult.failed(msg("step.power_scheme_failed", scheme=p.scheme))
        if hibernate_failed:
            return StepResult.failed(msg("step.hibernate_failed"))
        return StepResult.ok()


class RenameComputerStep(StepBase):
    def check(self, ctx: StepContext) -> bool:
        return False

    def run(self, ctx: StepContext) -> StepResult:
        name = ctx.state.computer_name_choice or ctx.recipe.windows.computer_name
        if not name:
            return StepResult.skipped(msg("step.no_name_chosen"))
        if not validate_computer_name(name):
            return StepResult.failed(msg("step.invalid_name", name=name), recoverable=False)
        try:
            renamed = ctx.services.features.rename_computer(name)
        except WinKitError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        if not renamed:
            return StepResult.ok(msg("step.same_name"))
        return StepResult.ok(msg("step.renamed", name=name), reboot=True)
