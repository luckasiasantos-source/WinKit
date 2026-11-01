"""Trazer o backup do PC de volta na instalação (V3-10): disco pelo serial, soma sem trocar."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from tests.agent.helpers import make_world
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.store import StateStore
from winkit.collector import pc_backup as pc
from winkit.collector.backups import local_source
from winkit.core.recipe.models import VolumeRef
from winkit.platform.fakes.volumes import FakeVolumes


def test_phase2_restores_from_backup_disk(tmp_path: Path) -> None:
    old = tmp_path / "antigo"
    docs = old / "Users" / "Samuel" / "Documents"
    docs.mkdir(parents=True)
    (docs / "tese.docx").write_text("tese")
    disk = tmp_path / "hd"
    sources = pc.make_sources(
        [r"C:\Users\Samuel\Documents"], {"DOCUMENTS": r"C:\Users\Samuel\Documents"}
    )
    pc.run_backup(
        sources,
        disk,
        computer="PC-ANTIGO",
        now=datetime(2026, 11, 1, tzinfo=UTC),
        source_root=lambda lit: local_source(old, lit),
    )
    (tmp_path / "w").mkdir()
    w = make_world(tmp_path / "w")
    vols = w.services.volumes
    assert isinstance(vols, FakeVolumes)
    vols.add("1A2B3C4D", "E", disk)
    r = w.recipe()
    r.pc_backup.destination = VolumeRef(serial="1A2B3C4D", label="Backup")
    r.pc_backup.restore_after_install = True
    w.save_recipe(r)
    run_phase1(w.runtime())
    run_phase2(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("pc_restore:pc").status == "done"
    restored = list(w.system.rglob("tese.docx"))
    assert restored and restored[0].read_text() == "tese"


def test_missing_disk_is_skipped(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    r = w.recipe()
    r.pc_backup.destination = VolumeRef(serial="DEADBEEF")
    r.pc_backup.restore_after_install = True
    w.save_recipe(r)
    run_phase1(w.runtime())
    run_phase2(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("pc_restore:pc").status == "skipped"
