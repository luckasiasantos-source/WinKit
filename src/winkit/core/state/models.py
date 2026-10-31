"""Estado persistido do Agente e transições válidas (PLANO.md §11.4, R-29, R-30).

O arquivo ``estado.json`` é gravado antes (``running``) e depois (``done``/``failed``/
``skipped``) de cada etapa. Uma etapa encontrada como ``running`` ao iniciar indica que
o processo morreu no meio: ``recover_interrupted`` a devolve para ``pending``.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from winkit.core.errors import StateError
from winkit.core.planner.models import Plan

StepStatus = Literal["pending", "running", "done", "failed", "skipped"]
PhaseStatus = Literal["pending", "running", "done"]
MAX_ATTEMPTS = 3
STATE_SCHEMA_VERSION: Literal[1] = 1


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class StepState(_Model):
    status: StepStatus = "pending"
    attempts: int = 0
    phase_ran: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    reason: str | None = None
    recoverable: bool = True
    reboot_required: bool = False
    #: Escolha feita na janela da Fase 2 (None = não perguntado).
    user_selected: bool | None = None


class PhaseState(_Model):
    status: PhaseStatus = "pending"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    runs: int = 0


class AgentState(_Model):
    schema_version: Literal[1] = STATE_SCHEMA_VERSION
    recipe_hash: str
    created_at: datetime
    phase1: PhaseState = Field(default_factory=PhaseState)
    phase2: PhaseState = Field(default_factory=PhaseState)
    steps: dict[str, StepState] = Field(default_factory=dict)
    reboot_pending: bool = False
    warnings: list[str] = Field(default_factory=list)
    postponed: bool = False

    def step(self, step_id: str) -> StepState:
        try:
            return self.steps[step_id]
        except KeyError as exc:
            raise StateError(f"etapa desconhecida no estado: {step_id}") from exc

    def counts(self) -> dict[str, int]:
        c = Counter(s.status for s in self.steps.values())
        return {k: c.get(k, 0) for k in ("pending", "running", "done", "failed", "skipped")}

    def phase_state(self, phase: int) -> PhaseState:
        return self.phase1 if phase == 1 else self.phase2


# ------------------------------------------------------------------ criação e sincronização
def new_state(plan: Plan, recipe_hash: str, now: datetime) -> AgentState:
    return AgentState(
        recipe_hash=recipe_hash,
        created_at=now,
        steps={s.id: StepState() for s in plan.steps},
    )


def sync_with_plan(state: AgentState, plan: Plan) -> list[str]:
    """Garante uma entrada para cada etapa do plano; devolve as que foram adicionadas."""
    added = [s.id for s in plan.steps if s.id not in state.steps]
    for step_id in added:
        state.steps[step_id] = StepState()
    return added


def recover_interrupted(state: AgentState) -> list[str]:
    """Etapas presas em ``running`` (processo morreu) voltam para ``pending``."""
    recovered = [k for k, v in state.steps.items() if v.status == "running"]
    for k in recovered:
        st = state.steps[k]
        if st.attempts >= MAX_ATTEMPTS:
            st.status = "failed"
            st.error = "interrompida repetidamente (reinício ou queda de energia)"
            st.recoverable = False
        else:
            st.status = "pending"
    return recovered


# ------------------------------------------------------------------ transições
def should_run(st: StepState) -> bool:
    if st.status == "pending":
        return True
    return st.status == "failed" and st.recoverable and st.attempts < MAX_ATTEMPTS


def mark_running(state: AgentState, step_id: str, phase: int, now: datetime) -> StepState:
    st = state.step(step_id)
    if st.status in ("done", "skipped"):
        raise StateError(f"{step_id} já está {st.status}")
    if st.status == "running":
        raise StateError(f"{step_id} já está em execução")
    if st.status == "failed" and not should_run(st):
        raise StateError(f"{step_id} esgotou as tentativas")
    st.status = "running"
    st.attempts += 1
    st.phase_ran = phase
    st.started_at = now
    st.finished_at = None
    st.error = None
    return st


def _require_running(state: AgentState, step_id: str) -> StepState:
    st = state.step(step_id)
    if st.status != "running":
        raise StateError(f"{step_id} não está em execução (está {st.status})")
    return st


def mark_done(
    state: AgentState,
    step_id: str,
    now: datetime,
    *,
    reboot_required: bool = False,
    reason: str | None = None,
) -> StepState:
    st = _require_running(state, step_id)
    st.status = "done"
    st.finished_at = now
    st.reboot_required = reboot_required
    st.reason = reason
    if reboot_required:
        state.reboot_pending = True
    return st


def mark_failed(
    state: AgentState, step_id: str, now: datetime, error: str, *, recoverable: bool = True
) -> StepState:
    st = _require_running(state, step_id)
    st.status = "failed"
    st.finished_at = now
    st.error = error
    st.recoverable = recoverable
    return st


def mark_skipped(state: AgentState, step_id: str, now: datetime, reason: str) -> StepState:
    """Pular não exige ``running``: dependência falhou, desmarcado na janela etc."""
    st = state.step(step_id)
    if st.status == "done":
        raise StateError(f"{step_id} já está concluída")
    st.status = "skipped"
    st.finished_at = now
    st.reason = reason
    return st


def reset_for_retry(state: AgentState, step_id: str) -> StepState:
    """ "Tentar de novo" pela tela de resumo: zera tentativas de uma etapa com falha."""
    st = state.step(step_id)
    if st.status not in ("failed", "skipped"):
        raise StateError(f"{step_id} não falhou nem foi pulada")
    st.status = "pending"
    st.attempts = 0
    st.error = None
    st.reason = None
    st.recoverable = True
    return st


def phase_complete(state: AgentState, plan: Plan, phase: int) -> bool:
    return all(
        state.step(s.id).status in ("done", "skipped")
        or (state.step(s.id).status == "failed" and not should_run(state.step(s.id)))
        for s in plan.phase(phase)
    )


# ------------------------------------------------------------------ serialização
def dump_state(state: AgentState) -> str:
    return state.model_dump_json(indent=2) + "\n"


def load_state(text: str) -> AgentState:
    try:
        data = json.loads(text)
        return AgentState.model_validate(data)
    except (ValueError, ValidationError) as exc:
        raise StateError(f"estado corrompido: {exc}") from exc
