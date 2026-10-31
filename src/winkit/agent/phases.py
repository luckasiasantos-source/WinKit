"""Orquestração das fases do Agente (PLANO.md §11, D-009, D-012, D-023)."""

from __future__ import annotations

import json
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from winkit.agent.eventlog import EventLog
from winkit.agent.executor import Executor, PhaseOutcome, Waits
from winkit.agent.paths import AgentPaths
from winkit.agent.pendrive import PendriveLocator
from winkit.agent.progress import AgentUi, NullUi
from winkit.agent.reboot import handle_reboot
from winkit.agent.services import AgentServices
from winkit.agent.steps.base import StepHandler
from winkit.agent.steps.registry import default_handlers
from winkit.agent.store import StateStore
from winkit.core import layout
from winkit.core.catalog.models import Catalogs
from winkit.core.errors import RecipeError, StateError, WinKitError
from winkit.core.isos import os_major_from_build
from winkit.core.planner.models import Plan, PlanContext, StepKind
from winkit.core.planner.planner import plan as make_plan
from winkit.core.recipe.io import load_recipe, recipe_hash
from winkit.core.recipe.models import Recipe
from winkit.core.state import models as st
from winkit.i18n import Language, msg, normalize, set_language
from winkit.platform.environment import single_instance

INSTANCE_NAME = "WinKitAgent"


@dataclass
class Runtime:
    paths: AgentPaths
    services: AgentServices
    catalogs: Catalogs
    clock: Callable[[], datetime]
    sleep: Callable[[float], None] = time.sleep
    ui_factory: Callable[[Recipe], AgentUi] = field(default=lambda recipe: NullUi())
    handlers: dict[StepKind, StepHandler] = field(default_factory=default_handlers)
    waits: Waits = field(default_factory=Waits)
    #: Idioma do Windows atual (para ``execution.language = auto``, D-030).
    detect_language: Callable[[], str] = lambda: "pt-BR"
    #: Recarrega os catálogos no idioma escolhido (``None`` = manter os recebidos, como nos testes).
    catalog_loader: Callable[[], Catalogs] | None = None


def apply_language(rt: Runtime, recipe: Recipe, *, override: Language | None = None) -> None:
    """Janela, notificações, resumo e motivos no idioma da receita (ou no de quem chamou)."""
    choice = override or recipe.execution.language
    set_language(normalize(rt.detect_language()) if choice == "auto" else choice)
    if rt.catalog_loader is not None:
        rt.catalogs = rt.catalog_loader()


@dataclass
class Session:
    rt: Runtime
    log: EventLog
    recipe: Recipe
    state: st.AgentState
    plan: Plan
    store: StateStore
    locator: PendriveLocator

    def executor(self, ui: AgentUi) -> Executor:
        rt = self.rt
        return Executor(
            plan=self.plan,
            state=self.state,
            store=self.store,
            recipe=self.recipe,
            catalogs=rt.catalogs,
            services=rt.services,
            paths=rt.paths,
            handlers=rt.handlers,
            log=self.log,
            ui=ui,
            locator=self.locator,
            clock=rt.clock,
            sleep=rt.sleep,
            waits=rt.waits,
        )

    def mirror_logs(self) -> None:
        root = self.locator.find()
        if root is None:
            self.log.info("pendrive ausente: logs não copiados")
            return
        name = f"{self.rt.services.env.computer_name()}_{self.state.created_at:%Y-%m-%d_%H-%M}"
        dest = self.log.mirror_to(root, name)
        if dest is not None:
            self.log.info(f"logs copiados para {dest}")


# ------------------------------------------------------------------ carga
def load_agent_recipe(rt: Runtime, log: EventLog) -> Recipe | None:
    recipe = _find_recipe(rt, log)
    if recipe is not None:
        apply_language(rt, recipe)
    return recipe


def _find_recipe(rt: Runtime, log: EventLog) -> Recipe | None:
    if rt.paths.recipe.is_file():
        try:
            return load_recipe(rt.paths.recipe.read_text(encoding="utf-8-sig"))
        except RecipeError as exc:
            log.error(f"receita local inválida: {exc}")
    # receita local ausente (já limpa ou bootstrap incompleto): tenta o pendrive
    pendrive_id = None
    if rt.paths.bootstrap.is_file():
        try:
            info = json.loads(rt.paths.bootstrap.read_text(encoding="utf-8-sig"))
            pendrive_id = info.get("pendrive_id")
            profile = info.get("profile", "padrao")
        except (ValueError, OSError) as exc:
            log.error(f"bootstrap.json ilegível: {exc}")
    if not pendrive_id:
        log.error("receita não encontrada (nem local, nem pelo bootstrap)")
        return None
    root = PendriveLocator(rt.services.env, str(pendrive_id)).find()
    if root is None:
        log.error("receita local ausente e pendrive não encontrado")
        return None
    path = root / layout.recipe_file(str(profile))
    try:
        return load_recipe(path.read_text(encoding="utf-8-sig"))
    except (RecipeError, OSError) as exc:
        log.error(f"receita do pendrive ilegível: {exc}")
        return None


def open_session(rt: Runtime, log: EventLog, *, phase: int) -> Session | None:
    recipe = load_agent_recipe(rt, log)
    if recipe is None:
        return None
    store = StateStore(rt.paths.state)
    try:
        state = store.load()
    except StateError as exc:
        log.error(f"estado corrompido; começando do zero: {exc}")
        state = None

    build = rt.services.env.windows_build()
    phase1_ran = phase == 1 or (state is not None and state.phase1.status == "done")
    ctx = PlanContext(os_major=os_major_from_build(build), build=build, phase1_ran=phase1_ran)
    plan = make_plan(recipe, rt.catalogs, ctx)
    if state is None:
        state = st.new_state(plan, recipe_hash(recipe), rt.clock())
    elif state.recipe_hash != recipe_hash(recipe):
        state.warnings.append(msg("agent.recipe_changed"))
        state.recipe_hash = recipe_hash(recipe)
    added = st.sync_with_plan(state, plan)
    if added:
        log.info(f"etapas acrescentadas ao estado: {', '.join(added)}")
    recovered = st.recover_interrupted(state)
    if recovered:
        log.warning(f"etapas interrompidas retomadas: {', '.join(recovered)}")
    if not phase1_ran:
        log.warning("a Fase 1 não rodou antes do login; suas etapas rodam agora (fallback D-012)")
    store.save(state)
    locator = PendriveLocator(rt.services.env, recipe.meta.pendrive_id)
    return Session(rt, log, recipe, state, plan, store, locator)


def _safety_nets(s: Session, *, phase: int) -> None:
    rt, log = s.rt, s.log
    try:
        created = rt.services.scheduler.ensure_phase2_task(rt.paths.agent_exe)
        log.info("tarefa da Fase 2 " + ("criada" if created else "já existia"))
    except WinKitError as exc:
        log.error(f"não foi possível garantir a tarefa da Fase 2: {exc}")
    if phase == 1 or s.state.phase1.status != "done":
        username = s.recipe.windows.account.username
        try:
            result = rt.services.accounts.ensure_administrator(username)
            log.info(f"conta {username} no grupo Administradores: {result}")  # H11
        except WinKitError as exc:
            log.error(f"não foi possível conferir o grupo da conta: {exc}")


# ------------------------------------------------------------------ fases
def run_phase1(rt: Runtime) -> int:
    """Antes do login, como SYSTEM. Sempre devolve 0 (nunca atrapalha o Windows)."""
    log = EventLog(rt.paths.logs, rt.clock)
    log.attach_python_logging()
    try:
        with single_instance(INSTANCE_NAME, rt.paths.locks) as only:
            if not only:
                log.warning("outra instância do Agente já está rodando")
                return 0
            s = open_session(rt, log, phase=1)
            if s is None:
                return 0
            log.info("== Fase 1 ==")
            ps = s.state.phase1
            ps.status, ps.runs = "running", ps.runs + 1
            ps.started_at = ps.started_at or rt.clock()
            s.store.save(s.state)
            _safety_nets(s, phase=1)
            outcome = s.executor(NullUi()).run_phase(1)
            ps.status, ps.finished_at = "done", rt.clock()
            s.store.save(s.state)
            _log_outcome(log, 1, outcome)
            s.mirror_logs()
    finally:
        log.detach_python_logging()
    return 0


def run_phase2(rt: Runtime, *, retry_failed: bool = False) -> int:
    log = EventLog(rt.paths.logs, rt.clock)
    log.attach_python_logging()
    try:
        with single_instance(INSTANCE_NAME, rt.paths.locks) as only:
            if not only:
                log.info("Fase 2 já em execução; esta chamada foi ignorada")
                return 0
            s = open_session(rt, log, phase=2)
            if s is None:
                return 1
            if retry_failed:
                for step_id, sst in s.state.steps.items():
                    if sst.status in ("failed", "skipped") and step_id != "finalize:summary":
                        st.reset_for_retry(s.state, step_id)
                s.store.save(s.state)
            log.info("== Fase 2 ==")
            if st.phase_complete(s.state, s.plan, 2):
                log.info("nada a fazer: todas as etapas já terminaram")
                return 0
            _safety_nets(s, phase=2)
            ui = rt.ui_factory(s.recipe)
            pending = [x for x in s.plan.phase(2) if st.should_run(s.state.step(x.id))]
            before = Counter(x.kind for x in s.plan.phase(1) if s.state.step(x.id).status == "done")
            choice = ui.choose(pending, {str(k): v for k, v in before.items()})
            if choice.action == "postpone":
                s.state.postponed = True
                s.store.save(s.state)
                log.info("adiado pelo usuário para o próximo login")
                return 0
            s.state.postponed = False
            s.state.reboot_pending = False  # nova sessão: reinícios anteriores já ocorreram
            if choice.computer_name:
                s.state.computer_name_choice = choice.computer_name
            ps = s.state.phase2
            ps.status, ps.runs = "running", ps.runs + 1
            ps.started_at = ps.started_at or rt.clock()
            s.store.save(s.state)
            outcome = s.executor(ui).run_phase(2, choice.selected)
            if st.phase_complete(s.state, s.plan, 2):
                ps.status, ps.finished_at = "done", rt.clock()
            s.store.save(s.state)
            _log_outcome(log, 2, outcome)
            if outcome.reboot_required:
                log.info("reinicialização necessária para concluir algumas etapas")
                handle_reboot(
                    s.recipe.execution.reboot_policy, ui=ui, services=rt.services, log=log
                )
            s.mirror_logs()
    finally:
        log.detach_python_logging()
    return 0


def _log_outcome(log: EventLog, phase: int, outcome: PhaseOutcome) -> None:
    log.info(
        f"Fase {phase} terminou: {outcome.ran} etapa(s) executada(s), "
        f"{outcome.deferred} adiada(s)" + (", reinício pendente" if outcome.reboot_required else "")
    )


def open_summary(paths: AgentPaths) -> Path | None:
    return paths.summary_html if paths.summary_html.is_file() else None
