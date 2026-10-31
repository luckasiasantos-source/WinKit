from __future__ import annotations

import sys
from pathlib import Path

import pytest

from winkit.core.errors import PlatformError, UnsafeOperationError
from winkit.platform.copy import (
    PythonCopier,
    RobocopyCopier,
    is_excluded,
    split_excludes,
    tree_stats,
)
from winkit.platform.fakes.runner import FakeRunner, result
from winkit.platform.runner import SubprocessRunner

DADOS = Path("Perfis") / "padrao" / "Backups" / "x" / "dados"


def make_src(tmp: Path) -> Path:
    src = tmp / "src"
    (src / "sub").mkdir(parents=True)
    (src / "Cache").mkdir()
    (src / "a.json").write_text("A")
    (src / "sub" / "b.txt").write_text("B")
    (src / "debug.log").write_text("log")
    (src / "Cache" / "c.bin").write_text("C")
    return src


def test_split_and_is_excluded() -> None:
    assert split_excludes(["Cache", "*.log", "plugin\\Cache", " "]) == (
        ["Cache"],
        ["*.log"],
        ["plugin\\Cache"],
    )
    ex = ["Cache", "*.log", "plugin/x"]
    assert is_excluded("Cache/c.bin", ex)
    assert is_excluded("sub/cache", ex)  # sem diferenciar maiúsculas
    assert is_excluded("a.LOG", ex)
    assert is_excluded("plugin/x/y", ex) and not is_excluded("plugin/xy", ex)
    assert not is_excluded("a.json", ex)


def test_tree_stats(tmp_path: Path) -> None:
    src = make_src(tmp_path)
    assert tree_stats(src, ["Cache", "*.log"]).files == 2
    assert tree_stats(src / "a.json", []).files == 1


def test_mirror_with_excludes_and_replace(tmp_path: Path) -> None:
    src = make_src(tmp_path)
    dst = tmp_path / DADOS
    dst.mkdir(parents=True)
    (dst / "velho.txt").write_text("apagar")
    PythonCopier().mirror(src, dst, excludes=["Cache", "*.log"], log=None)
    files = sorted(p.relative_to(dst).as_posix() for p in dst.rglob("*") if p.is_file())
    assert files == ["a.json", "sub/b.txt"]


def test_mirror_single_file(tmp_path: Path) -> None:
    src = make_src(tmp_path) / "a.json"
    dst = tmp_path / DADOS
    PythonCopier().mirror(src, dst, excludes=[], log=None)
    assert (dst / "a.json").read_text() == "A"


@pytest.mark.parametrize("bad", ["qualquer", "Backups/x", "Perfis/padrao/dados"])
def test_mirror_refuses_unsafe_targets(tmp_path: Path, bad: str) -> None:  # R-20
    with pytest.raises(UnsafeOperationError):
        PythonCopier().mirror(tmp_path, tmp_path / bad, excludes=[], log=None)
    with pytest.raises(UnsafeOperationError):
        RobocopyCopier(FakeRunner()).mirror(tmp_path, tmp_path / bad, excludes=[], log=None)


def test_restore_policies(tmp_path: Path) -> None:
    src = make_src(tmp_path)
    dst = tmp_path / "dst"
    dst.mkdir()
    (dst / "a.json").write_text("meu")
    c = PythonCopier()
    c.restore_tree(src, dst, policy="merge", log=None)
    assert (dst / "a.json").read_text() == "meu"  # mesclar não sobrescreve (D-007)
    assert (dst / "sub" / "b.txt").read_text() == "B"
    c.restore_tree(src, dst, policy="overwrite", log=None)
    assert (dst / "a.json").read_text() == "A"
    (dst / "a.json").write_text("meu")
    c.restore_tree(src, dst, policy="skip", log=None)
    assert (dst / "a.json").read_text() == "meu"
    fresh = tmp_path / "novo"
    c.restore_tree(src, fresh, policy="skip", log=None)
    assert (fresh / "a.json").exists()


def test_copy_file_policies(tmp_path: Path) -> None:
    src = make_src(tmp_path) / "a.json"
    dst = tmp_path / "x" / "a.json"
    c = PythonCopier()
    assert c.copy_file(src, dst, policy="merge")
    dst.write_text("meu")
    assert not c.copy_file(src, dst, policy="merge")
    assert not c.copy_file(src, dst, policy="skip")
    assert c.copy_file(src, dst, policy="overwrite") and dst.read_text() == "A"


def test_robocopy_arguments(tmp_path: Path) -> None:
    runner = FakeRunner()
    rc = RobocopyCopier(runner)
    src = make_src(tmp_path)
    rc.mirror(src, tmp_path / DADOS, excludes=["Cache", "*.log", "a\\b"], log=tmp_path / "l.log")
    args = runner.calls[-1].args
    assert args[0].lower().endswith("robocopy.exe")
    assert "/MIR" in args and "/XJ" in args and "/FFT" in args
    assert args[args.index("/XD") + 1] == "Cache"
    assert str(src / "a\\b") in args
    assert args[args.index("/XF") + 1] == "*.log"
    assert any(a.startswith("/UNILOG+:") for a in args)
    rc.restore_tree(src, tmp_path / "d", policy="merge", log=None)
    assert {"/XC", "/XN", "/XO", "/E"} <= set(runner.calls[-1].args)
    rc.restore_tree(src, tmp_path / "d2", policy="overwrite", log=None)
    assert {"/IS", "/IT"} <= set(runner.calls[-1].args)
    n = len(runner.calls)
    (tmp_path / "d3").mkdir()
    rc.restore_tree(src, tmp_path / "d3", policy="skip", log=None)
    assert len(runner.calls) == n


@pytest.mark.parametrize(("code", "ok"), [(0, True), (1, True), (7, True), (8, False), (16, False)])
def test_robocopy_exit_codes(tmp_path: Path, code: int, ok: bool) -> None:
    src = make_src(tmp_path)
    runner = FakeRunner().when_contains("robocopy", result(exit_code=code))
    copier = RobocopyCopier(runner)
    if ok:
        copier.restore_tree(src, tmp_path / "d", policy="merge", log=None)
    else:
        with pytest.raises(PlatformError):
            copier.restore_tree(src, tmp_path / "d", policy="merge", log=None)


@pytest.mark.windows
def test_real_robocopy(tmp_path: Path) -> None:
    src = make_src(tmp_path)
    deep = src.joinpath(*["pasta-com-nome-comprido"] * 12)
    Path("\\\\?\\" + str(deep)).mkdir(parents=True, exist_ok=True)
    (Path("\\\\?\\" + str(deep)) / "fundo.txt").write_text("caminho longo")
    rc = RobocopyCopier(SubprocessRunner())
    dst = tmp_path / DADOS
    rc.mirror(src, dst, excludes=["Cache", "*.log"], log=tmp_path / "r.log")
    assert (dst / "a.json").exists() and not (dst / "Cache").exists()
    copied = list(Path("\\\\?\\" + str(dst)).rglob("fundo.txt"))
    assert copied, "caminho > 260 caracteres deveria ser copiado"
    out = tmp_path / "restaurado"
    rc.restore_tree(dst, out, policy="merge", log=None)
    assert (out / "sub" / "b.txt").read_text() == "B"
    assert sys.platform == "win32"
