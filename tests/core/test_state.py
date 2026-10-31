from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.factories import app, recipe
from winkit.core.catalog.loader import default_catalogs
from winkit.core.errors import StateError
from winkit.core.planner.planner import plan
from winkit.core.state import models as st
from winkit.i18n import legacy, render

NOW = datetime(2026, 11, 2, 15, 0, tzinfo=UTC)


def make():
    p = plan(recipe(apps=[app("a"), app("b")]), default_catalogs())
    return p, st.new_state(p, "sha256:x", NOW)


def test_new_state_has_every_step_pending() -> None:
    p, s = make()
    assert set(s.steps) == set(p.ids())
    assert s.counts()["pending"] == len(p.steps)


def test_happy_path() -> None:
    _, s = make()
    st.mark_running(s, "app:a", 1, NOW)
    assert s.step("app:a").attempts == 1
    st.mark_done(s, "app:a", NOW, reboot_required=True)
    assert s.step("app:a").status == "done"
    assert s.reboot_pending


def test_invalid_transitions() -> None:
    _, s = make()
    with pytest.raises(StateError):
        st.mark_done(s, "app:a", NOW)  # não está running
    st.mark_running(s, "app:a", 1, NOW)
    with pytest.raises(StateError):
        st.mark_running(s, "app:a", 1, NOW)
    st.mark_done(s, "app:a", NOW)
    with pytest.raises(StateError):
        st.mark_running(s, "app:a", 1, NOW)
    with pytest.raises(StateError):
        st.mark_skipped(s, "app:a", NOW, legacy("x"))
    with pytest.raises(StateError):
        s.step("app:zzz")


def test_retry_until_max_attempts() -> None:
    _, s = make()
    for _ in range(st.MAX_ATTEMPTS):
        assert st.should_run(s.step("app:b"))
        st.mark_running(s, "app:b", 2, NOW)
        st.mark_failed(s, "app:b", NOW, legacy("código 1603"))
    assert not st.should_run(s.step("app:b"))
    with pytest.raises(StateError):
        st.mark_running(s, "app:b", 2, NOW)


def test_non_recoverable_failure_is_not_retried() -> None:
    _, s = make()
    st.mark_running(s, "app:b", 2, NOW)
    st.mark_failed(s, "app:b", NOW, legacy("hash"), recoverable=False)
    assert not st.should_run(s.step("app:b"))


def test_recover_interrupted() -> None:
    _, s = make()
    st.mark_running(s, "app:a", 1, NOW)
    assert st.recover_interrupted(s) == ["app:a"]
    assert s.step("app:a").status == "pending"
    # interrompida demais vira falha definitiva
    for _ in range(st.MAX_ATTEMPTS - 1):
        st.mark_running(s, "app:a", 1, NOW)
        st.recover_interrupted(s)
    assert s.step("app:a").status == "failed"
    assert not s.step("app:a").recoverable


def test_skip_and_reset_for_retry() -> None:
    _, s = make()
    st.mark_skipped(s, "app:a", NOW, legacy("desmarcado"))
    assert render(s.step("app:a").reason) == "desmarcado"
    st.reset_for_retry(s, "app:a")
    assert s.step("app:a").status == "pending"
    with pytest.raises(StateError):
        st.reset_for_retry(s, "app:a")


def test_phase_complete() -> None:
    p, s = make()
    assert not st.phase_complete(s, p, 1)
    for step in p.phase(1):
        st.mark_running(s, step.id, 1, NOW)
        st.mark_done(s, step.id, NOW)
    assert st.phase_complete(s, p, 1)


def test_sync_with_plan_adds_new_steps() -> None:
    p, s = make()
    del s.steps["app:b"]
    assert st.sync_with_plan(s, p) == ["app:b"]


def test_serialization_roundtrip_and_corruption() -> None:
    _, s = make()
    st.mark_running(s, "app:a", 1, NOW)
    loaded = st.load_state(st.dump_state(s))
    assert loaded == s
    with pytest.raises(StateError):
        st.load_state("{quebrado")
    with pytest.raises(StateError):
        st.load_state('{"schema_version": 1}')


def test_phase_state_accessor() -> None:
    _, s = make()
    assert s.phase_state(1) is s.phase1
    assert s.phase_state(2) is s.phase2
