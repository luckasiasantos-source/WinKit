"""Modo "aplicar neste PC" (V2-03, D-033): a receita num Windows já instalado.

Diferenças em relação à instalação:
- tudo roda numa só passada, no perfil do usuário atual (o planejador usa o fallback da
  Fase 1, que já troca o perfil Default pelo do usuário — R31);
- antes de qualquer mudança: prévia (nada é escrito, R-54) e ponto de restauração (R30);
- cada aplicação tem estado, logs e resumo próprios em ``ProgramData\\WinKit\\Aplicacoes``;
- nada de limpeza de instalação, tarefa da Fase 2 ou reinício automático.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from winkit.agent.eventlog import EventLog
from winkit.agent.executor import Executor
from winkit.agent.paths import AgentPaths
from winkit.agent.phases import INSTANCE_NAME, Runtime, apply_language
from winkit.agent.progress import AgentUi, NullUi
from winkit.agent.store import StateStore
from winkit.core import layout
from winkit.core.errors import RecipeError
from winkit.core.fsutil import atomic_write_text
from winkit.core.isos import os_major_from_build
from winkit.core.live import LivePreview, PreviewItem
from winkit.core.planner.models import Plan, PlanContext, StepKind
from winkit.core.planner.planner import plan as make_plan
from winkit.core.recipe.io import load_recipe, recipe_hash
from winkit.core.recipe.models import Recipe
from winkit.core.state import models as st
from winkit.i18n import Language
from winkit.platform.environment import single_instance

RUNS_DIR = "Aplicacoes"


@dataclass(frozen=True)
class LiveOptions:
    root: Path  # pasta que contém WinKit\ (pendrive ou cópia local)
    profile_id: str = "padrao"
    simulate: bool = False
    only_kinds: frozenset[StepKind] | None = None
    restore_point: bool = True
    #: Idioma de quem chamou (Studio, CLI); ``None`` = o da receita, como na instalação.
    language: Language | None = None


@dataclass
class LiveResult:
    code: int
    run_dir: Path | None = None
    preview: LivePreview | None = None
    summary_html: Path | None = None
    counts: dict[str, int] = field(default_factory=dict)


class FixedLocator:
    """O conteúdo do WinKit está numa pasta conhecida (não precisa procurar o marcador)."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def find(self) -> Path | None:
        return self.root if (self.root / layout.WINKIT).is_dir() else None


def load_live_recipe(options: LiveOptions) -> Recipe:
    path = options.root / layout.recipe_file(options.profile_id)
    if not path.is_file():
        raise RecipeError(f"receita não encontrada: {path}")
    return load_recipe(path.read_text(encoding="utf-8-sig"))


def live_plan(rt: Runtime, recipe: Recipe, options: LiveOptions) -> tuple[Plan, tuple[str, ...]]:
    """Plano do modo ao vivo, sem as etapas que não são seguras num Windows em uso (R-54)."""
    build = rt.services.env.windows_build()
    ctx = PlanContext(
        os_major=os_major_from_build(build),
        build=build,
        phase1_ran=False,
        mode="live",
        only_kinds=options.only_kinds,
        restore_before=options.restore_point,
    )
    plan = make_plan(recipe, rt.catalogs, ctx)
    unsafe = tuple(s.id for s in plan.steps if not rt.handlers[s.kind].live_safe)
    if unsafe:
        plan = plan.model_copy(update={"steps": tuple(s for s in plan.steps if s.id not in unsafe)})
    return plan, unsafe


def run_live(
    rt: Runtime,
    options: LiveOptions,
    *,
    ui: AgentUi | None = None,
    stamp: Callable[[], str] | None = None,
) -> LiveResult:
    ui = ui or NullUi()
    recipe = load_live_recipe(options)
    apply_language(rt, recipe, override=options.language)
    name = (stamp or (lambda: rt.clock().strftime("%Y-%m-%d_%H-%M-%S")))()
    run_dir = rt.paths.base / RUNS_DIR / name
    paths = AgentPaths(run_dir)
    log = EventLog(paths.logs, rt.clock)
    log.attach_python_logging()
    try:
        with single_instance(INSTANCE_NAME, rt.paths.locks) as only:
            if not only:
                log.warning("outra instância do Agente já está rodando")
                return LiveResult(code=3, run_dir=run_dir)
            plan, unsafe = live_plan(rt, recipe, options)
            state = st.new_state(plan, recipe_hash(recipe), rt.clock())
            store = StateStore(paths.state)
            executor = Executor(
                plan=plan,
                state=state,
                store=store,
                recipe=recipe,
                catalogs=rt.catalogs,
                services=rt.services,
                paths=paths,
                handlers=rt.handlers,
                log=log,
                ui=ui,
                locator=FixedLocator(options.root),
                clock=rt.clock,
                sleep=rt.sleep,
                waits=rt.waits,
                mode="live",
            )
            if options.simulate:
                preview = _preview(executor, plan, unsafe)
                atomic_write_text(run_dir / "previa.json", preview.model_dump_json(indent=2))
                log.info(f"prévia: {len(preview.items)} etapas")
                return LiveResult(code=0, run_dir=run_dir, preview=preview)
            log.info("== Aplicar neste PC ==")
            store.save(state)
            executor.run_phase(2)
            _mirror(log, options.root, rt, name)
            counts = state.counts()
            return LiveResult(
                code=0 if counts["failed"] == 0 else 1,
                run_dir=run_dir,
                summary_html=paths.summary_html if paths.summary_html.is_file() else None,
                counts=counts,
            )
    finally:
        log.detach_python_logging()


def _preview(executor: Executor, plan: Plan, unsafe: tuple[str, ...]) -> LivePreview:
    items: list[PreviewItem] = []
    for step in plan.phase(2):
        if step.kind == "finalize":
            continue
        handler = executor.handlers[step.kind]
        items.append(handler.preview(executor.context(step, 2)))
    return LivePreview(items=tuple(items), not_live_safe=unsafe)


def _mirror(log: EventLog, root: Path, rt: Runtime, name: str) -> None:
    computer = rt.services.env.computer_name()
    log.mirror_to(root, f"{computer}_{name}_aplicar")
