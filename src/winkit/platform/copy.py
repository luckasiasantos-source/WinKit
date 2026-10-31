"""Cópia de pastas e arquivos para captura e restauração de backups (PLANO.md §13.1, D-014).

Duas implementações com a mesma semântica:
- ``RobocopyCopier`` (Windows): caminhos longos, tentativas, exclusões; resultado só pelo
  código de saída (0–7 sucesso, ≥ 8 falha — R-13).
- ``PythonCopier``: usada nos testes e como alternativa se o robocopy faltar.

Salvaguarda R-20: o modo espelho (que apaga no destino) só aceita destino
``.../Backups/<id>/dados``.
"""

from __future__ import annotations

import fnmatch
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from winkit.core.errors import PlatformError, UnsafeOperationError
from winkit.platform.runner import CommandRunner
from winkit.platform.system import system32

Policy = Literal["merge", "overwrite", "skip"]


@dataclass(frozen=True)
class CopyStats:
    files: int
    bytes: int


class Copier(Protocol):
    def mirror(self, src: Path, dst: Path, *, excludes: list[str], log: Path | None) -> None: ...

    def restore_tree(self, src: Path, dst: Path, *, policy: Policy, log: Path | None) -> None: ...

    def copy_file(self, src: Path, dst: Path, *, policy: Policy) -> bool: ...


def ensure_mirror_target(dst: Path) -> None:
    parts = [p.casefold() for p in dst.parts]
    if len(parts) < 3 or parts[-1] != "dados" or parts[-3] != "backups":
        raise UnsafeOperationError(f"espelho recusado fora de Backups/<id>/dados: {dst} (R-20)")


def split_excludes(excludes: list[str]) -> tuple[list[str], list[str], list[str]]:
    """(nomes de pasta, padrões de arquivo, caminhos relativos)."""
    names, patterns, relative = [], [], []
    for raw in excludes:
        e = raw.strip().replace("/", "\\")
        if not e:
            continue
        if "\\" in e:
            relative.append(e)
        elif "*" in e or "?" in e:
            patterns.append(e)
        else:
            names.append(e)
    return names, patterns, relative


def is_excluded(rel_posix: str, excludes: list[str]) -> bool:
    names, patterns, relative = split_excludes(excludes)
    parts = rel_posix.split("/")
    low_parts = [p.casefold() for p in parts]
    if any(n.casefold() in low_parts for n in names):
        return True
    if any(fnmatch.fnmatch(parts[-1].casefold(), p.casefold()) for p in patterns):
        return True
    low = rel_posix.casefold()
    return any(
        low == r.replace("\\", "/").casefold()
        or low.startswith(r.replace("\\", "/").casefold() + "/")
        for r in relative
    )


def tree_stats(src: Path, excludes: list[str]) -> CopyStats:
    files = size = 0
    if src.is_file():
        return CopyStats(1, src.stat().st_size)
    for dirpath, dirnames, filenames in os.walk(src):
        rel_dir = Path(dirpath).relative_to(src).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir + "/"
        dirnames[:] = [d for d in dirnames if not is_excluded(rel_dir + d, excludes)]
        for f in filenames:
            if is_excluded(rel_dir + f, excludes):
                continue
            files += 1
            try:
                size += (Path(dirpath) / f).stat().st_size
            except OSError:
                continue
    return CopyStats(files, size)


class PythonCopier:
    def mirror(self, src: Path, dst: Path, *, excludes: list[str], log: Path | None) -> None:
        ensure_mirror_target(dst)
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        if src.is_file():
            shutil.copy2(src, dst / src.name)
            return
        for dirpath, dirnames, filenames in os.walk(src):
            rel = Path(dirpath).relative_to(src)
            rel_s = "" if rel.as_posix() == "." else rel.as_posix() + "/"
            dirnames[:] = [
                d
                for d in dirnames
                if not is_excluded(rel_s + d, excludes) and not (Path(dirpath) / d).is_symlink()
            ]
            (dst / rel).mkdir(parents=True, exist_ok=True)
            for f in filenames:
                if not is_excluded(rel_s + f, excludes):
                    shutil.copy2(Path(dirpath) / f, dst / rel / f)

    def restore_tree(self, src: Path, dst: Path, *, policy: Policy, log: Path | None) -> None:
        if policy == "skip" and dst.exists():
            return
        for dirpath, _dirnames, filenames in os.walk(src):
            rel = Path(dirpath).relative_to(src)
            (dst / rel).mkdir(parents=True, exist_ok=True)
            for f in filenames:
                target = dst / rel / f
                if policy == "merge" and target.exists():
                    continue
                shutil.copy2(Path(dirpath) / f, target)

    def copy_file(self, src: Path, dst: Path, *, policy: Policy) -> bool:
        if dst.exists() and policy in ("merge", "skip"):
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True


_COMMON = ["/COPY:DAT", "/DCOPY:T", "/XJ", "/R:1", "/W:1", "/NP", "/NJH", "/NJS", "/FFT"]


class RobocopyCopier:
    def __init__(self, runner: CommandRunner) -> None:
        self._runner = runner

    def _run(self, args: list[str], log: Path | None, timeout: float = 7200) -> None:
        argv = [str(system32("robocopy.exe")), *args]
        if log is not None:
            log.parent.mkdir(parents=True, exist_ok=True)
            argv.append(f"/UNILOG+:{log}")
        res = self._runner.run(argv, timeout=timeout)
        if res.timed_out or res.exit_code >= 8:
            raise PlatformError(f"robocopy falhou (código {res.exit_code})")

    def mirror(self, src: Path, dst: Path, *, excludes: list[str], log: Path | None) -> None:
        ensure_mirror_target(dst)
        names, patterns, relative = split_excludes(excludes)
        if src.is_file():
            dst.mkdir(parents=True, exist_ok=True)
            self._run([str(src.parent), str(dst), src.name, *_COMMON], log)
            return
        xd = [*names, *(str(src / r) for r in relative)]
        args = [str(src), str(dst), "/MIR", *_COMMON]
        if xd:
            args += ["/XD", *xd]
        if patterns:
            args += ["/XF", *patterns]
        self._run(args, log)

    def restore_tree(self, src: Path, dst: Path, *, policy: Policy, log: Path | None) -> None:
        if policy == "skip" and dst.exists():
            return
        mode = ["/XC", "/XN", "/XO"] if policy == "merge" else ["/IS", "/IT"]
        self._run([str(src), str(dst), "/E", *mode, *_COMMON], log)

    def copy_file(self, src: Path, dst: Path, *, policy: Policy) -> bool:
        if dst.exists() and policy in ("merge", "skip"):
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.name == src.name:
            self._run([str(src.parent), str(dst.parent), src.name, "/IS", "/IT", *_COMMON], None)
        else:
            shutil.copy2(src, dst)
        return True
