"""Resumo com Msg: o mesmo estado sai em cada idioma (D-031)."""

from __future__ import annotations

from datetime import UTC, datetime

from tests.factories import app, backup, recipe
from winkit.core.catalog.loader import default_catalogs
from winkit.core.planner.planner import plan
from winkit.core.state import models as st
from winkit.core.summary import build_summary, render_html
from winkit.core.text import msg
from winkit.i18n import set_language

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


def _summary():  # type: ignore[no-untyped-def]
    r = recipe(apps=[app("a"), app("b")], backups=[backup("x", warnings=["contém token"])])
    p = plan(r, default_catalogs())
    s = st.new_state(p, "h", NOW)
    st.mark_running(s, "app:a", 1, NOW)
    st.mark_failed(s, "app:a", NOW, msg("step.exit_code", code=1603))
    st.mark_running(s, "app:b", 1, NOW)
    st.mark_done(s, "app:b", NOW, reason=msg("step.already_done"))
    return build_summary(p, s, r, computer="PC-TESTE", now=NOW)


def test_summary_keeps_messages_untranslated() -> None:
    summary = _summary()
    failed = next(i for i in summary.items if i.id == "app:a")
    assert failed.detail is not None and failed.detail.key == "step.exit_code"
    keys = {w.key for w in summary.warnings}
    assert {"summary.backup_warning", "summary.set_password"} <= keys


def test_html_in_each_language() -> None:
    summary = _summary()
    pt = render_html(summary, log_path="C:\\log")
    assert 'lang="pt-BR"' in pt and "o instalador retornou o código 1603" in pt
    assert "Tudo o que foi feito" in pt and "31/10/2026" in pt
    set_language("en-US")
    en = render_html(summary, log_path="C:\\log")
    assert 'lang="en-US"' in en and "the installer returned code 1603" in en
    assert "Everything that was done" in en and "10/31/2026" in en and "falhou" not in en
    set_language("es")
    es = render_html(summary, log_path="C:\\log")
    assert 'lang="es"' in es and "el instalador devolvió el código 1603" in es
    assert "Todo lo que se hizo" in es


def test_html_escapes_everything() -> None:
    summary = _summary()
    html = render_html(summary, log_path="<script>")
    assert "<script>" not in html
