"""Modelos do plano de execução do Agente (PLANO.md §11)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from winkit.core.recipe.models import ExecutionMode

StepKind = Literal[
    "driver",
    "wifi",
    "dns",
    "hosts",
    "network_drive",
    "maintenance",
    "env",
    "font",
    "default_apps",
    "bloat",
    "feature",
    "tweak",
    "power",
    "backup",
    "app",
    "shortcut",
    "rename_computer",
    "windows_update",
    "driver_report",
    "default_apps_verify",
    "restore_point",
    "finalize",
]
#: Onde o efeito acontece: máquina, perfil Default (Fase 1) ou perfil do usuário logado.
Target = Literal["machine", "default_profile", "user_profile"]
Phase = Literal[1, 2]


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlannedStep(_Frozen):
    id: str  # "<kind>:<ref>"
    kind: StepKind
    ref: str
    phase: Phase
    title: str
    target: Target
    needs_pendrive: bool = False
    needs_network: bool = False
    depends_on: tuple[str, ...] = ()
    #: Aparece com caixa de seleção na janela da Fase 2 (``decide_at_runtime`` efetivo).
    user_choice: bool = False
    #: Estava na Fase 1, mas a Fase 1 não rodou (fallback de D-012).
    moved_from_phase1: bool = False
    #: Etapa da Fase 1 que, se adiada (ex.: sem fonte offline), tenta de novo na Fase 2.
    phase2_fallback: bool = False


class ExcludedItem(_Frozen):
    kind: StepKind
    ref: str
    reason: str


#: ``install`` = Windows recém-instalado; ``live`` = aplicar num Windows em uso (D-033).
PlanMode = Literal["install", "live"]


class PlanContext(_Frozen):
    os_major: int | None = None
    build: int | None = None
    phase1_ran: bool = True
    mode: PlanMode = "install"
    #: Só estes tipos de etapa (modo ao vivo, "o que aplicar"); ``None`` = todos.
    only_kinds: frozenset[StepKind] | None = None
    #: Modo ao vivo: ponto de restauração antes de tudo (D-033), ligado por padrão.
    restore_before: bool = True


class Plan(_Frozen):
    mode: ExecutionMode
    steps: tuple[PlannedStep, ...]
    excluded: tuple[ExcludedItem, ...] = ()

    def phase(self, number: int) -> list[PlannedStep]:
        return [s for s in self.steps if s.phase == number]

    def step(self, step_id: str) -> PlannedStep | None:
        return next((s for s in self.steps if s.id == step_id), None)

    def ids(self) -> list[str]:
        return [s.id for s in self.steps]
