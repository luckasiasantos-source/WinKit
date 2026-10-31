"""Resumo da execução do Agente (PLANO.md §12.4, item 36).

O resumo é gravado como ``resumo.json`` e ``resumo.html``. O HTML é estático e abre pelo
atalho da área de trabalho mesmo depois que o Agente for removido (D-024).
"""

from __future__ import annotations

import html
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from winkit.core.devices import ProblemDevice, problem_text
from winkit.core.planner.models import Plan
from winkit.core.recipe.models import Recipe
from winkit.core.state.models import AgentState
from winkit.core.text import Msg, msg
from winkit.i18n import current_language, render, t
from winkit.i18n.format import format_datetime
from winkit.i18n.format import format_duration as _format_duration


class SummaryItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    title: str
    phase: int
    status: str
    detail: Msg | None = None


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
    warnings: tuple[Msg, ...]
    #: V2-09: dispositivos que ficaram sem driver e drivers achados no Windows Update.
    devices: tuple[ProblemDevice, ...] = ()
    drivers_found: tuple[str, ...] = ()

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
        warnings.extend(msg("summary.backup_warning", name=b.name, warning=w) for w in b.warnings)
    if recipe.windows.account.password_mode == "empty":  # noqa: S105 — modo, não senha
        warnings.append(msg("summary.set_password"))
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
        warnings=tuple(_unique(warnings)),
        devices=tuple(state.devices),
        drivers_found=tuple(state.drivers_found),
    )


def _unique(items: list[Msg]) -> list[Msg]:
    seen: set[str] = set()
    out: list[Msg] = []
    for item in items:
        key = item.model_dump_json()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def format_duration(seconds: float | None) -> str:
    return _format_duration(seconds)


def _status_label(status: str) -> str:
    if status in ("done", "failed", "skipped", "pending", "running"):
        return t(f"summary.status.{status}")
    return status


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


def _devices_html(summary: Summary) -> str:
    """Seção "Dispositivos sem driver" (V2-09): o que fazer com o que sobrou."""
    e = html.escape
    parts: list[str] = []
    if summary.drivers_found:
        found = "".join(f"<li>{e(x)}</li>" for x in summary.drivers_found)
        parts.append(f"<h2>{e(t('summary.drivers_found'))}</h2><ul>{found}</ul>")
    if summary.devices:
        rows = []
        for d in summary.devices:
            ids = ", ".join(d.hardware_ids[:2]) or d.device_id
            rows.append(
                f"<tr class='failed'><td>{d.code}</td><td>{e(d.name)}"
                f"<div class='d'>{e(render(problem_text(d.code)))}</div>"
                f"<div class='d'>{e(ids)}</div></td></tr>"
            )
        parts.append(
            f"<h2>{e(t('summary.devices'))}</h2><p>{e(t('summary.devices_hint'))}</p>"
            f"<table>{''.join(rows)}</table>"
        )
    return "\n".join(parts)


def render_html(summary: Summary, *, log_path: str) -> str:
    """HTML autocontido, com todo texto escapado."""
    e = html.escape

    def rows(status: str | None = None) -> str:
        out = []
        for i in summary.items:
            if status and i.status != status:
                continue
            text = render(i.detail)
            detail = f"<div class='d'>{e(text)}</div>" if text else ""
            out.append(
                f"<tr class='{e(i.status)}'><td>{i.phase}</td><td>{e(i.title)}{detail}</td>"
                f"<td>{e(_status_label(i.status))}</td></tr>"
            )
        return "\n".join(out)

    total = summary.phase1_seconds or 0.0
    total += summary.phase2_seconds or 0.0
    warnings = "".join(f"<li>{e(render(w))}</li>" for w in summary.warnings)
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
    device_block = _devices_html(summary)
    generated = e(t("summary.generated_at", when=format_datetime(summary.generated_at)))
    lang = current_language()
    return (
        f'<!doctype html>\n<html lang="{lang}"><head><meta charset="utf-8">\n'
        f"<title>{title}</title>\n<style>{_CSS}</style></head><body>\n"
        f"<h1>{title} — {e(summary.computer)}</h1>\n"
        f"<p>{times}</p>\n<p><strong>{counts}</strong></p>\n"
        f"{fail_block}\n{warn_block}\n{device_block}"
        f"<h2>{e(t('summary.everything'))}</h2>\n<table>{rows()}</table>\n"
        f'<p class="mut">{e(t("summary.full_log", path=log_path))}<br>{generated}</p>\n'
        "</body></html>\n"
    )
