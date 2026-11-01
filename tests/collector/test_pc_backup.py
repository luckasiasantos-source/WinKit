"""Backup do PC (V3-09/10, D-051): cópia conferida, retomada, .zip e restauração que soma."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from winkit.collector import pc_backup as pc
from winkit.collector.backups import local_source
from winkit.core.pc_backup import BACKUP_DIR

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


DOCS = r"C:\Users\Samuel\Documents"
FOLDERS = {"DOCUMENTS": DOCS, "USERPROFILE": r"C:\Users\Samuel"}


def _tree(root: Path) -> Path:
    docs = local_source(root, DOCS)
    (docs / "Trabalho").mkdir(parents=True)
    (docs / "a.txt").write_text("a")
    (docs / "Trabalho" / "b.bin").write_bytes(os.urandom(300_000))
    return docs


def _root(tmp: Path):  # type: ignore[no-untyped-def]
    return lambda literal: local_source(tmp / "C", literal)


def test_backup_verifies_resumes_and_never_deletes(tmp_path: Path) -> None:
    docs = _tree(tmp_path / "C")
    (tmp_path / "C" / "Projetos").mkdir()
    (tmp_path / "C" / "Projetos" / "p.py").write_text("print(1)")
    dest = tmp_path / "D"
    sources = pc.make_sources([DOCS, r"C:\Projetos"], FOLDERS)
    assert [s.label for s in sources] == ["documents", "projetos"]
    assert (sources[0].template, sources[1].template) == ("{DOCUMENTS}", r"{ABS:C:\Projetos}")
    kw = {"computer": "PC-ANTIGO", "now": NOW, "source_root": _root(tmp_path)}
    with pytest.raises(pc.BackupStopped):  # para depois do primeiro arquivo
        pc.run_backup(sources, dest, should_stop=lambda: True, **kw)
    seen: list[int] = []
    m = pc.run_backup(sources, dest, progress=lambda p: seen.append(p.done_files), **kw)
    base = dest / BACKUP_DIR / "pc-antigo"
    assert len(m.files) == 3 and not m.failed and seen[-1] == 3
    assert (base / "documents" / "Trabalho" / "b.bin").read_bytes() == (
        docs / "Trabalho" / "b.bin"
    ).read_bytes()
    assert (dest / BACKUP_DIR / "winkit-backup.json").is_file()
    # refazer: só o que mudou; o que sumiu do PC continua no backup
    before = (base / "documents" / "a.txt").stat().st_mtime_ns
    (docs / "Trabalho" / "b.bin").unlink()
    (docs / "novo.txt").write_text("n")
    m2 = pc.run_backup(sources, dest, **kw)
    assert (base / "documents" / "Trabalho" / "b.bin").is_file()
    assert (base / "documents" / "a.txt").stat().st_mtime_ns == before
    assert "documents/novo.txt" in m2.files and "documents/Trabalho/b.bin" in m2.files


def test_zip_mode_and_restore_merges(tmp_path: Path) -> None:
    _tree(tmp_path / "C")
    dest = tmp_path / "D"
    sources = pc.make_sources([DOCS], FOLDERS)
    pc.run_backup(sources, dest, computer="pc", now=NOW, zip_mode=True, source_root=_root(tmp_path))
    ((base, manifest),) = pc.find_backups([dest])
    assert manifest.zip and (base / "backup.zip").is_file()
    new = r"C:\Users\Ana\Documents"
    new_docs = local_source(tmp_path / "C", new)
    new_docs.mkdir(parents=True)
    (new_docs / "a.txt").write_text("versão nova, não pode ser trocada")
    targets = pc.restore_targets(manifest, {"DOCUMENTS": new})
    assert targets == {"documents": new}
    report = pc.restore(base, manifest, targets, target_root=_root(tmp_path))
    assert (report.copied, report.kept, report.failed) == (1, 1, {})
    assert (new_docs / "a.txt").read_text().startswith("versão nova")
    assert (new_docs / "Trabalho" / "b.bin").stat().st_size == 300_000


def test_locked_file_uses_shadow_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs = _tree(tmp_path / "C")
    shadow = tmp_path / "sombra"
    locked = docs / "a.txt"
    in_shadow = local_source(shadow, DOCS) / "a.txt"
    in_shadow.parent.mkdir(parents=True)
    in_shadow.write_text("a da sombra")
    real_open = Path.open

    def fake_open(self: Path, *a, **k):  # type: ignore[no-untyped-def]
        if self == locked:
            raise PermissionError("em uso")
        return real_open(self, *a, **k)

    monkeypatch.setattr(Path, "open", fake_open)
    sources = pc.make_sources([DOCS], FOLDERS)
    m = pc.run_backup(
        sources,
        tmp_path / "D",
        computer="pc",
        now=NOW,
        source_root=_root(tmp_path),
        snapshot_root=lambda vol: shadow,
    )
    assert not m.failed
    assert (tmp_path / "D" / BACKUP_DIR / "pc" / "documents" / "a.txt").read_text() == "a da sombra"


def test_measure_speed_cleans_up(tmp_path: Path) -> None:
    mb_s, ms_file = pc.measure_speed(tmp_path)
    assert mb_s > 0 and ms_file > 0 and list(tmp_path.iterdir()) == []
