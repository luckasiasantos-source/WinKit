from __future__ import annotations

import os
from pathlib import Path

import pytest

from winkit.core.errors import IntegrityError
from winkit.core.fsutil import atomic_write_bytes, atomic_write_text
from winkit.core.manifest import manifest as mf


def make_tree(root: Path) -> None:
    (root / "Apps" / "a").mkdir(parents=True)
    (root / "Apps" / "a" / "setup.exe").write_bytes(b"MZ" + b"x" * 100)
    (root / "Drivers" / "Net").mkdir(parents=True)
    (root / "Drivers" / "Net" / "n.inf").write_text("[Version]")
    (root / "Perfis").mkdir()
    (root / "Perfis" / "ignorado.txt").write_text("fora")


def test_scan_collects_only_requested_subdirs(tmp_path: Path) -> None:
    make_tree(tmp_path)
    m = mf.scan(tmp_path, ["Apps", "Drivers", "NaoExiste"])
    assert sorted(m.files) == ["Apps/a/setup.exe", "Drivers/Net/n.inf"]
    assert m.total_size("Apps/") == 102
    assert len(m.files["Apps/a/setup.exe"].sha256) == 64


def test_scan_reuses_hash_when_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_tree(tmp_path)
    first = mf.scan(tmp_path, ["Apps"])
    calls: list[Path] = []
    monkeypatch.setattr(mf, "hash_file", lambda p: calls.append(p) or "x")
    second = mf.scan(tmp_path, ["Apps"], previous=first)
    assert calls == []
    assert second == first


def test_diff_detects_changes(tmp_path: Path) -> None:
    make_tree(tmp_path)
    old = mf.scan(tmp_path, ["Apps", "Drivers"])
    (tmp_path / "Apps" / "a" / "setup.exe").write_bytes(b"MZ-nova")
    (tmp_path / "Drivers" / "Net" / "n.inf").unlink()
    (tmp_path / "Apps" / "b.exe").write_bytes(b"b")
    new = mf.scan(tmp_path, ["Apps", "Drivers"], previous=old)
    d = mf.diff(old, new)
    assert d.added == ("Apps/b.exe",)
    assert d.changed == ("Apps/a/setup.exe",)
    assert d.removed == ("Drivers/Net/n.inf",)
    assert not d.empty
    assert mf.diff(new, new).empty


def test_verify(tmp_path: Path) -> None:
    make_tree(tmp_path)
    m = mf.scan(tmp_path, ["Apps"])
    mf.verify(tmp_path, "Apps/a/setup.exe", m)
    mf.verify_tree(tmp_path, "Apps/", m)
    with pytest.raises(IntegrityError, match="fora do manifesto"):
        mf.verify(tmp_path, "Apps/nada.exe", m)
    target = tmp_path / "Apps" / "a" / "setup.exe"
    target.write_bytes(b"MZ" + b"y" * 100)  # mesmo tamanho, conteúdo diferente
    with pytest.raises(IntegrityError, match="alterado"):
        mf.verify(tmp_path, "Apps/a/setup.exe", m)
    target.unlink()
    with pytest.raises(IntegrityError, match="ausente"):
        mf.verify(tmp_path, "Apps/a/setup.exe", m)


def test_serialization(tmp_path: Path) -> None:
    make_tree(tmp_path)
    m = mf.scan(tmp_path, ["Apps"])
    assert mf.load_manifest(mf.dump_manifest(m)) == m
    with pytest.raises(IntegrityError):
        mf.load_manifest("nao")


def test_atomic_write(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "arq.json"
    atomic_write_text(target, "olá\n")
    assert target.read_text(encoding="utf-8") == "olá\n"
    atomic_write_bytes(target, b"\x00\x01")
    assert target.read_bytes() == b"\x00\x01"
    assert [p.name for p in target.parent.iterdir()] == ["arq.json"]


def test_atomic_write_cleans_temp_on_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_: object) -> None:
        raise OSError("disco cheio")

    monkeypatch.setattr(os, "fsync", boom)
    with pytest.raises(OSError):
        atomic_write_text(tmp_path / "x.txt", "a")
    with pytest.raises(OSError):
        atomic_write_bytes(tmp_path / "y.bin", b"a")
    assert list(tmp_path.iterdir()) == []
