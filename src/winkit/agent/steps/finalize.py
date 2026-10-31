"""Etapa final: resumo (item 36), atalho na área de trabalho e limpeza."""

from __future__ import annotations

from pathlib import Path

from winkit.agent.cleanup import cleanup
from winkit.agent.steps.base import StepBase, StepContext, StepResult, local_path
from winkit.core.fsutil import atomic_write_text
from winkit.core.state.models import should_run
from winkit.core.summary import build_summary, render_html
from winkit.i18n import msg, t, tn


def _pending_others(ctx: StepContext) -> list[str]:
    out = []
    for step in ctx.plan.steps:
        if step.id == ctx.step.id:
            continue
        s = ctx.state.steps.get(step.id)
        if s is not None and (s.status == "pending" or (s.status == "failed" and should_run(s))):
            out.append(step.id)
    return out


def write_summary(ctx: StepContext) -> Path:
    summary = build_summary(
        ctx.plan,
        ctx.state,
        ctx.recipe,
        computer=ctx.services.env.computer_name(),
        now=ctx.clock(),
    )
    atomic_write_text(ctx.paths.summary_json, summary.model_dump_json(indent=2) + "\n")
    html = render_html(summary, log_path=str(ctx.log.dir / "agente.log"))
    atomic_write_text(ctx.paths.summary_html, html)
    if ctx.recipe.execution.desktop_summary_shortcut and ctx.mode != "live":
        _desktop_shortcut(ctx)
    ctx.ui.finished(summary, ctx.paths.summary_html)
    return ctx.paths.summary_html


def _desktop_shortcut(ctx: StepContext) -> None:
    """Atalho ``.url`` (não precisa de COM) apontando para o ``resumo.html``."""
    desktop = ctx.services.folders.current_user().get("DESKTOP")
    if not desktop:
        return
    target = ctx.paths.summary_html.resolve().as_uri()
    content = f"[InternetShortcut]\r\nURL={target}\r\n"
    atomic_write_text(local_path(desktop) / f"{t('agent.summary_shortcut')}.url", content)


def _retry_shortcut(ctx: StepContext) -> None:
    """Com falhas, o Agente fica instalado (D-024) e ganha um atalho "tentar de novo"."""
    desktop = ctx.services.folders.current_user().get("DESKTOP")
    if not desktop:
        return
    try:
        ctx.services.shortcuts.create(
            local_path(desktop) / f"{t('summary.retry_failed')} (WinKit).lnk",
            str(ctx.paths.agent_exe),
            "retry",
        )
    except Exception as exc:  # noqa: BLE001 — atalho é conveniência
        ctx.log.warning(f"atalho de nova tentativa não criado: {exc}", step=ctx.step.id)


class FinalizeStep(StepBase):
    def check(self, ctx: StepContext) -> bool:
        return False

    def run(self, ctx: StepContext) -> StepResult:
        if ctx.mode == "live":
            return self._live(ctx)
        write_summary(ctx)
        pending = _pending_others(ctx)
        if pending:
            # resumo parcial gravado; a limpeza espera o resto (próximo login)
            return StepResult.deferred(
                msg("step.pending_others", n=len(pending), ids=", ".join(pending[:5]))
            )
        failures = [k for k, v in ctx.state.steps.items() if v.status == "failed"]
        report = cleanup(ctx.services, ctx.paths, remove_agent=not failures)
        if failures:
            _retry_shortcut(ctx)
        for err in report.errors:
            ctx.log.warning(f"limpeza: {err}", step=ctx.step.id)
        for item in report.removed:
            ctx.log.info(f"removido: {item}", step=ctx.step.id)
        counts = ctx.state.counts()
        if ctx.recipe.execution.notify_on_finish:
            if failures:
                text = tn("agent.finished_with_failures", len(failures))
            elif ctx.state.warnings:
                text = tn("agent.finished_with_warnings", len(ctx.state.warnings))
            else:
                text = t("agent.finished")
            ctx.ui.notify(t("app.name"), text)
        return StepResult.ok(
            msg("step.finalize_counts", done=counts["done"], failed=counts["failed"])
        )

    def _live(self, ctx: StepContext) -> StepResult:
        """Modo ao vivo (R31): só o resumo; nada de limpeza, Agente ou atalhos de instalação."""
        write_summary(ctx)
        counts = ctx.state.counts()
        return StepResult.ok(
            msg("step.finalize_counts", done=counts["done"], failed=counts["failed"])
        )
