"""Resumo da execução do Agente (PLANO.md §12.4, item 36).

O resumo é gravado como ``resumo.json`` e ``resumo.html``. O HTML é estático e abre pelo
atalho da área de trabalho mesmo depois que o Agente for removido (D-024).
"""

from __future__ import annotations

import html
from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict

from winkit.core.planner.models import Plan
from winkit.core.recipe.models import Recipe
from winkit.core.state.models import AgentState
from winkit.i18n import t


class SummaryItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    title: str
    phase: int
    status: str
    detail: str | None = None


class Summary(BaseModel):
    model_config = ConfigDict(frozen=True)
    computer: str
    generated_at: datetime
    phase1_seconds: float | None
    phase2_seconds: float | None
    done: int
    failed: int
    skipped: int
    pending: int
    items: tuple[SummaryItem, ...]
    warnings: tuple[str, ...]

    @property
    def failures(self) -> list[SummaryItem]:
        return [i for i in self.items if i.status == "failed"]


def _seconds(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    return max(0.0, (end - start).total_seconds())


def build_summary(
    plan: Plan, state: AgentState, recipe: Recipe, *, computer: str, now: datetime
) -> Summary:
    items: list[SummaryItem] = []
    for step in plan.steps:
        if step.kind == "finalize":
            continue
        st = state.steps.get(step.id)
        if st is None:
            continue
        detail = st.error if st.status == "failed" else st.reason
        items.append(
            SummaryItem(
                id=step.id, title=step.title, phase=step.phase, status=st.status, detail=detail
            )
        )
    warnings = list(state.warnings)
    for b in recipe.selected_backups():
        warnings.extend(f"{b.name}: {w}" for w in b.warnings)
    if recipe.windows.account.password_mode == "empty":  # noqa: S105 — modo, não senha
        warnings.append(t("summary.set_password"))
    counts = {
        k: sum(1 for i in items if i.status == k) for k in ("done", "failed", "skipped", "pending")
    }
    p2_end = state.phase2.finished_at or now
    return Summary(
        computer=computer,
        generated_at=now,
        phase1_seconds=_seconds(state.phase1.started_at, state.phase1.finished_at),
        phase2_seconds=_seconds(state.phase2.started_at, p2_end),
        done=counts["done"],
        failed=counts["failed"],
        skipped=counts["skipped"],
        pending=counts["pending"],
        items=tuple(items),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    td = timedelta(seconds=round(seconds))
    hours, rem = divmod(td.seconds + td.days * 86400, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours} h {minutes:02d} min" if hours else f"{minutes} min {secs:02d} s"


_STATUS_LABEL = {
    "done": "feito",
    "failed": "falhou",
    "skipped": "pulado",
    "pending": "pendente",
    "running": "interrompido",
}


_CSS = """
:root {
  color-scheme: light dark;
  --bg: #fff; --fg: #1b1b1b; --mut: #666; --ok: #1a7f37; --bad: #c62828; --line: #ddd;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #1e1e1e; --fg: #eee; --mut: #aaa; --line: #444; --ok: #57c46b; --bad: #ff6b6b; }
}
body {
  font: 15px/1.5 "Segoe UI", system-ui, sans-serif;
  background: var(--bg); color: var(--fg);
  max-width: 900px; margin: 24px auto; padding: 0 16px;
}
h1 { font-size: 22px; }
.mut { color: var(--mut); }
table { width: 100%; border-collapse: collapse; margin: 8px 0 24px; }
td { border-bottom: 1px solid var(--line); padding: 6px 8px; vertical-align: top; }
tr.failed td:last-child { color: var(--bad); font-weight: 600; }
tr.done td:last-child { color: var(--ok); }
.d { color: var(--mut); font-size: 13px; }
"""


def render_html(summary: Summary, *, log_path: str) -> str:
    """HTML autocontido, com todo texto escapado."""
    e = html.escape

    def rows(status: str | None = None) -> str:
        out = []
        for i in summary.items:
            if status and i.status != status:
                continue
            detail = f"<div class='d'>{e(i.detail)}</div>" if i.detail else ""
            out.append(
                f"<tr class='{e(i.status)}'><td>{i.phase}</td><td>{e(i.title)}{detail}</td>"
                f"<td>{e(_STATUS_LABEL.get(i.status, i.status))}</td></tr>"
            )
        return "\n".join(out)

    total = summary.phase1_seconds or 0.0
    total += summary.phase2_seconds or 0.0
    warnings = "".join(f"<li>{e(w)}</li>" for w in summary.warnings)
    failures = rows("failed")
    title = e(t("summary.title"))
    times = " · ".join(
        [
            e(t("summary.total_time", duration=format_duration(total))),
            e(t("summary.phase_time", phase=1, duration=format_duration(summary.phase1_seconds))),
            e(t("summary.phase_time", phase=2, duration=format_duration(summary.phase2_seconds))),
        ]
    )
    counts = e(
        t("summary.counts", done=summary.done, failed=summary.failed, skipped=summary.skipped)
    )
    fail_block = f"<h2>{e(t('summary.failures'))}</h2><table>{failures}</table>" if failures else ""
    warn_block = f"<h2>{e(t('summary.warnings'))}</h2><ul>{warnings}</ul>" if warnings else ""
    generated = e(summary.generated_at.strftime("%d/%m/%Y %H:%M"))
    return (
        '<!doctype html>\n<html lang="pt-BR"><head><meta charset="utf-8">\n'
        f"<title>{title}</title>\n<style>{_CSS}</style></head><body>\n"
        f"<h1>{title} — {e(summary.computer)}</h1>\n"
        f"<p>{times}</p>\n<p><strong>{counts}</strong></p>\n"
        f"{fail_block}\n{warn_block}\n"
        f"<h2>Tudo o que foi feito</h2>\n<table>{rows()}</table>\n"
        f'<p class="mut">Log completo: {e(log_path)}<br>Gerado em {generated}</p>\n'
        "</body></html>\n"
    )
