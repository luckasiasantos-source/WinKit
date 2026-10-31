"""Contrato das etapas do Agente (ARQUITETURA.md §4.1, R-29)."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol

from winkit.agent.eventlog import EventLog
from winkit.agent.paths import AgentPaths
from winkit.agent.progress import AgentUi
from winkit.agent.services import AgentServices
from winkit.core.catalog.models import Catalogs
from winkit.core.live import PreviewItem
from winkit.core.paths import templates
from winkit.core.planner.models import Plan, PlannedStep
from winkit.core.recipe.models import Recipe
from winkit.core.state.models import AgentState
from winkit.i18n import Msg, msg

Outcome = Literal["done", "skipped", "failed", "deferred"]


@dataclass(frozen=True)
class StepResult:
    outcome: Outcome
    message: Msg | None = None
    reboot_required: bool = False
    recoverable: bool = True

    @classmethod
    def ok(cls, message: Msg | None = None, *, reboot: bool = False) -> StepResult:
        return cls("done", message, reboot_required=reboot)

    @classmethod
    def skipped(cls, reason: Msg) -> StepResult:
        return cls("skipped", reason)

    @classmethod
    def failed(cls, error: Msg, *, recoverable: bool = True) -> StepResult:
        return cls("failed", error, recoverable=recoverable)

    @classmethod
    def deferred(cls, reason: Msg) -> StepResult:
        return cls("deferred", reason)


@dataclass
class StepContext:
    step: PlannedStep
    plan: Plan
    state: AgentState
    recipe: Recipe
    catalogs: Catalogs
    services: AgentServices
    paths: AgentPaths
    log: EventLog
    ui: AgentUi
    pendrive: Path | None
    phase: int
    clock: Callable[[], datetime]
    #: Espera ``probe()`` ficar verdadeiro por até N segundos, avisando a interface (motivo).
    wait: Callable[[Callable[[], bool], float, str], bool] = lambda probe, s, r: probe()
    winget_wait_seconds: float = 600.0
    #: ``install`` = Windows recém-instalado; ``live`` = aplicar num Windows em uso (D-033).
    mode: Literal["install", "live"] = "install"

    def folders(self) -> dict[str, str]:
        """Pastas para resolver moldes de caminho conforme o alvo da etapa."""
        f = self.services.folders
        machine = f.machine()
        if self.step.target == "default_profile":
            return templates.retarget(machine, f.default_profile_root())
        return {**machine, **f.current_user()}

    def payload(self, rel: str) -> Path:
        if self.pendrive is None:
            raise RuntimeError("etapa precisa do pendrive, mas ele não foi localizado")
        return self.pendrive / "WinKit" / rel


class StepHandler(Protocol):
    #: Pode rodar num Windows em uso (modo "aplicar neste PC", R-54)?
    live_safe: bool

    def check(self, ctx: StepContext) -> bool:
        """``True`` se o efeito já existe. Sem efeito colateral."""
        ...

    def run(self, ctx: StepContext) -> StepResult: ...

    def preview(self, ctx: StepContext) -> PreviewItem:
        """O que ``run`` faria. **Nunca** pode mudar nada (R-54)."""
        ...


class StepBase:
    """Padrão das etapas: seguras no modo ao vivo e prévia a partir de ``check``."""

    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        return False

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        return (msg("preview.will_run", title=ctx.step.title),)

    def preview(self, ctx: StepContext) -> PreviewItem:
        try:
            done = self.check(ctx)
        except Exception:  # noqa: BLE001 — prévia nunca quebra; na dúvida, "vai mudar"
            done = False
        if done:
            return item(ctx, "already_done")
        return item(ctx, "will_change", self.preview_changes(ctx))


def item(
    ctx: StepContext,
    status: Literal["already_done", "will_change", "not_applicable"],
    changes: tuple[Msg, ...] = (),
    warnings: tuple[Msg, ...] = (),
) -> PreviewItem:
    return PreviewItem(
        step_id=ctx.step.id,
        kind=ctx.step.kind,
        title=ctx.step.title,
        status=status,
        changes=changes,
        warnings=warnings,
    )


def local_path(windows_path: str) -> Path:
    """Caminho do Windows → ``Path`` local (no Linux dos testes, troca ``\\`` por ``/``)."""
    if sys.platform == "win32":
        return Path(windows_path)
    return Path(windows_path.replace("\\", os.sep))
