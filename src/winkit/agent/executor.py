"""Executa as etapas de uma fase do plano (ARQUITETURA.md §4.2).

Garantias: uma etapa que falha nunca derruba as outras (P4, R-28); o estado é gravado antes
e depois de cada etapa (R-30); falta de pendrive ou de internet adia a etapa sem gastar
tentativa; dependência que falhou faz a dependente ser pulada.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from winkit.agent.eventlog import EventLog
from winkit.agent.paths import AgentPaths
from winkit.agent.pendrive import PendriveLocator
from winkit.agent.progress import AgentUi
from winkit.agent.services import AgentServices
from winkit.agent.steps.base import StepContext, StepHandler, StepResult
from winkit.agent.store import StateStore
from winkit.core.catalog.models import Catalogs
from winkit.core.planner.models import Plan, PlannedStep, StepKind
from winkit.core.recipe.models import Recipe
from winkit.core.state import models as st
from winkit.i18n import msg, render


@dataclass
class Waits:
    pendrive_seconds: float = 15 * 60
    network_seconds: float = 10 * 60
    winget_seconds: float = 10 * 60
    poll_seconds: float = 5.0


@dataclass
class PhaseOutcome:
    ran: int = 0
    deferred: int = 0
    reboot_required: bool = False


class Executor:
    def __init__(
        self,
        *,
        plan: Plan,
        state: st.AgentState,
        store: StateStore,
        recipe: Recipe,
        catalogs: Catalogs,
        services: AgentServices,
        paths: AgentPaths,
        handlers: dict[StepKind, StepHandler],
        log: EventLog,
        ui: AgentUi,
        locator: PendriveLocator,
        clock: Callable[[], datetime],
        sleep: Callable[[float], None] = time.sleep,
        waits: Waits | None = None,
    ) -> None:
        self.plan = plan
        self.state = state
        self.store = store
        self.recipe = recipe
        self.catalogs = catalogs
        self.services = services
        self.paths = paths
        self.handlers = handlers
        self.log = log
        self.ui = ui
        self.locator = locator
        self.clock = clock
        self.sleep = sleep
        self.waits = waits or Waits()
        self._pendrive: Path | None = None

    # ------------------------------------------------------------------ espera
    def _wait_for(self, probe: Callable[[], bool], seconds: float, reason: str) -> bool:
        if probe():
            return True
        self.ui.waiting(reason, True)  # type: ignore[arg-type]
        waited = 0.0
        try:
            while waited < seconds:
                self.sleep(self.waits.poll_seconds)
                waited += self.waits.poll_seconds
                if probe():
                    return True
            return False
        finally:
            self.ui.waiting(reason, False)  # type: ignore[arg-type]

    def _probe_pendrive(self) -> bool:
        self._pendrive = self.locator.find()
        return self._pendrive is not None

    def pendrive(self) -> Path | None:
        if self._pendrive is None or not (self._pendrive / "WinKit").exists():
            self._probe_pendrive()
        return self._pendrive

    # ------------------------------------------------------------------ execução
    def run_phase(self, phase: int, selection: frozenset[str] | None = None) -> PhaseOutcome:
        outcome = PhaseOutcome()
        steps = self.plan.phase(phase)
        total = len(steps)
        for index, step in enumerate(steps):
            self.ui.progress(index, total, step.title)
            result = self._run_one(step, phase, selection)
            final = self.state.step(step.id)
            self.ui.step_result(step.id, final.status, render(final.error or final.reason))
            if result == "ran":
                outcome.ran += 1
            elif result == "deferred":
                outcome.deferred += 1
        self.ui.progress(total, total, "")
        outcome.reboot_required = self.state.reboot_pending
        return outcome

    def _dependency_problem(self, step: PlannedStep) -> tuple[str, str] | None:
        """("skip", dep) se uma dependência falhou de vez; ("wait", dep) se ainda não rodou."""
        for dep in step.depends_on:
            ds = self.state.steps.get(dep)
            if ds is None or ds.status == "done":
                continue
            if ds.status == "skipped" or (ds.status == "failed" and not st.should_run(ds)):
                return ("skip", dep)
            return ("wait", dep)
        return None

    def _run_one(  # noqa: PLR0911 — cada saída antecipada é um caso do contrato §4.2
        self, step: PlannedStep, phase: int, selection: frozenset[str] | None
    ) -> str:
        state = self.state
        now = self.clock()
        sst = state.step(step.id)
        if not st.should_run(sst):
            return "noop"
        if step.user_choice and selection is not None and step.id not in selection:
            st.mark_skipped(state, step.id, now, msg("step.not_selected"))
            self.log.info("desmarcado na janela", step=step.id)
            self.store.save(state)
            return "noop"

        problem = self._dependency_problem(step)
        if problem is not None:
            kind, dep = problem
            if kind == "skip":
                st.mark_skipped(state, step.id, now, msg("step.dependency_failed", dep=dep))
                self.log.warning(f"pulada: dependência {dep} falhou", step=step.id)
                self.store.save(state)
                return "noop"
            sst.reason = msg("step.waiting_dependency", dep=dep)
            self.store.save(state)
            return "deferred"

        if step.needs_pendrive and not self._wait_for(
            lambda: self.pendrive() is not None, self.waits.pendrive_seconds, "pendrive"
        ):
            sst.reason = msg("agent.reconnect_pendrive")
            self.log.warning("pendrive ausente; etapa adiada", step=step.id)
            self.store.save(state)
            return "deferred"
        if step.needs_network and not self._wait_for(
            self.services.env.has_internet, self.waits.network_seconds, "network"
        ):
            sst.reason = msg("step.no_network")
            self.log.warning("sem internet; etapa adiada", step=step.id)
            self.store.save(state)
            return "deferred"

        handler = self.handlers[step.kind]
        ctx = StepContext(
            step=step,
            plan=self.plan,
            state=state,
            recipe=self.recipe,
            catalogs=self.catalogs,
            services=self.services,
            paths=self.paths,
            log=self.log,
            ui=self.ui,
            pendrive=self.pendrive() if step.needs_pendrive else self._pendrive,
            phase=phase,
            clock=self.clock,
            wait=self._wait_for,
            winget_wait_seconds=self.waits.winget_seconds,
        )
        st.mark_running(state, step.id, phase, self.clock())
        self.store.save(state)
        self.log.info(f"início: {step.title}", step=step.id)
        try:
            if handler.check(ctx):
                result = StepResult.ok(msg("step.already_done"))
            else:
                result = handler.run(ctx)
        except Exception as exc:  # noqa: BLE001 — P4: nenhuma etapa derruba o Agente
            self.log.error(f"erro inesperado: {exc}", step=step.id, exc=exc)
            result = StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        self._apply(step, result)
        return "deferred" if result.outcome == "deferred" else "ran"

    def _apply(self, step: PlannedStep, result: StepResult) -> None:
        state, now = self.state, self.clock()
        match result.outcome:
            case "done":
                st.mark_done(
                    state,
                    step.id,
                    now,
                    reboot_required=result.reboot_required,
                    reason=result.message,
                )
                text = render(result.message)
                self.log.info("concluída" + (f": {text}" if text else ""), step=step.id)
            case "skipped":
                st.mark_skipped(state, step.id, now, result.message or msg("legacy.text", text=""))
                self.log.info(f"pulada: {render(result.message)}", step=step.id)
            case "failed":
                st.mark_failed(
                    state,
                    step.id,
                    now,
                    result.message or msg("step.failed_unknown"),
                    recoverable=result.recoverable,
                )
                self.log.error(f"falhou: {render(result.message)}", step=step.id)
            case "deferred":
                st.mark_deferred(state, step.id, result.message or msg("legacy.text", text=""))
                self.log.info(f"adiada: {render(result.message)}", step=step.id)
        self.store.save(state)
