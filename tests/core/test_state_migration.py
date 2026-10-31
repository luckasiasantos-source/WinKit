"""Estado v1 (texto pronto) → v2 (Msg), D-031 e R-47."""

from __future__ import annotations

import json

import pytest

from winkit.core.errors import StateError
from winkit.core.state.migrations import migrate_state
from winkit.core.state.models import dump_state, load_state
from winkit.i18n import render, set_language

V1 = {
    "schema_version": 1,
    "recipe_hash": "sha256:abc",
    "created_at": "2026-10-31T10:00:00-03:00",
    "phase1": {"status": "done", "runs": 1},
    "phase2": {"status": "running", "runs": 1},
    "steps": {
        "app:steam": {"status": "failed", "attempts": 2, "error": "código 1603"},
        "backup:d": {"status": "skipped", "reason": "unidade D: não existe"},
        "app:7zip": {"status": "done", "attempts": 1, "reason": None},
    },
    "reboot_pending": False,
    "warnings": ["A receita mudou depois do início."],
}


def test_v1_becomes_v2_without_losing_text() -> None:
    state = load_state(json.dumps(V1))
    assert state.schema_version == 2
    assert render(state.step("app:steam").error) == "código 1603"
    assert render(state.step("backup:d").reason) == "unidade D: não existe"
    assert state.step("app:7zip").reason is None
    assert [render(w) for w in state.warnings] == ["A receita mudou depois do início."]
    set_language("en-US")  # texto antigo não tem tradução: continua o mesmo
    assert render(state.step("app:steam").error) == "código 1603"


def test_v2_roundtrip() -> None:
    state = load_state(json.dumps(V1))
    again = load_state(dump_state(state))
    assert again == state


def test_unknown_version_is_rejected() -> None:
    with pytest.raises(StateError):
        migrate_state({**V1, "schema_version": 99})
    assert migrate_state([1, 2]) == [1, 2]
