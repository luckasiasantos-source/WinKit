"""Etapa: Iniciar e barra de tarefas no perfil Default (V2-04, R20).

O Windows só lê esses arquivos ao **criar** um perfil, então a etapa vale na Fase 1. Fora dela
(fallback ou ao vivo) pula com a instrução manual.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from winkit.agent.steps.base import StepBase, StepContext, StepResult, local_path
from winkit.core.fsutil import atomic_write_bytes
from winkit.core.start_layout import SHELL_DIR, START2_DIR, start_json, taskbar_xml
from winkit.i18n import Msg, msg


class StartLayoutStep(StepBase):
    #: Mexer no Iniciar de um Windows em uso pede API privada (H29): só na instalação.
    live_safe = False

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        return (msg("preview.start_layout"),)

    def run(self, ctx: StepContext) -> StepResult:
        s = ctx.recipe.start_layout
        if ctx.phase != 1 or ctx.step.target != "default_profile":
            return StepResult.skipped(msg("step.start_layout.manual"))
        profile = Path(local_path(ctx.services.folders.default_profile_root()))
        done: list[str] = []
        try:
            if any(p.selected for p in s.taskbar_pins):
                atomic_write_bytes(
                    profile.joinpath(*SHELL_DIR, "LayoutModification.xml"),
                    taskbar_xml(s.taskbar_pins),
                )
                done.append("taskbar")
            exact = s.mode == "exact" and s.start_file is not None
            if exact and s.source_build == ctx.services.env.windows_build():
                dest = profile.joinpath(*START2_DIR, "start2.bin")
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ctx.payload(str(s.start_file)), dest)
                done.append("start_exact")
            else:
                if exact:
                    ctx.state.warnings.append(msg("summary.start_exact_other_build"))
                if any(p.selected for p in s.start_pins):
                    atomic_write_bytes(
                        profile.joinpath(*SHELL_DIR, "LayoutModification.json"),
                        start_json(s.start_pins),
                    )
                    done.append("start_list")
        except OSError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        if not done:
            return StepResult.skipped(msg("step.not_in_recipe"))
        return StepResult.ok(msg("step.start_layout.done"))
