"""Único ponto de execução de processos externos (ARQUITETURA.md, R-11).

Regras:
- argumentos sempre em lista, nunca ``shell=True``;
- ``timeout`` obrigatório; ao estourar, a árvore de processos é encerrada;
- no Windows, nenhum processo filho abre janela de console;
- argumentos sensíveis (``secrets``) aparecem como ``***`` em logs (R-23);
- a saída é devolvida em bytes: interpretar texto localizado é proibido (R-13).
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from winkit.core.errors import CommandError
from winkit.platform.system import CREATE_NO_WINDOW, is_windows, system32

log = logging.getLogger(__name__)

from winkit.core.secrets import MASK, SECRETS  # noqa: E402 — R-53


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    exit_code: int
    stdout: bytes
    stderr: bytes
    duration: float
    timed_out: bool = False
    secrets: tuple[str, ...] = field(default=(), repr=False)

    @property
    def ok(self) -> bool:
        return not self.timed_out and self.exit_code == 0

    def display_args(self) -> str:
        return " ".join(mask_secrets(self.args, self.secrets))

    def stdout_text(self) -> str:
        """Texto para LOG apenas (nunca para tomar decisões — R-13)."""
        return decode_for_log(self.stdout)

    def stderr_text(self) -> str:
        return decode_for_log(self.stderr)

    def check(self) -> CommandResult:
        """Lança ``CommandError`` se o comando falhou."""
        if self.timed_out:
            raise CommandError(f"tempo limite excedido: {self.display_args()}", timed_out=True)
        if self.exit_code != 0:
            detail = self.stderr_text().strip() or self.stdout_text().strip()
            raise CommandError(
                f"código {self.exit_code}: {self.display_args()}"
                + (f" — {detail[:2000]}" if detail else ""),
                exit_code=self.exit_code,
            )
        return self


class CommandRunner(Protocol):
    def run(
        self,
        args: Sequence[str | os.PathLike[str]],
        *,
        timeout: float,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        log_to: Path | None = None,
        secrets: Sequence[str] = (),
        stdin: bytes | None = None,
    ) -> CommandResult: ...


def mask_secrets(args: Sequence[str], secrets: Sequence[str]) -> list[str]:
    """Mascara os segredos da chamada e os do registro do processo (R-23, R-53)."""
    out = []
    for arg in args:
        masked = arg
        for secret in secrets:
            if secret:
                masked = masked.replace(secret, MASK)
        out.append(SECRETS.mask(masked))
    return out


def decode_for_log(data: bytes) -> str:
    """Decodifica saída de ferramentas só para exibição em log.

    Tenta UTF-8 (com e sem BOM), UTF-16 (robocopy /UNILOG, alguns utilitários) e, por fim,
    a página de código OEM do console pt-BR (cp850), substituindo o que não decodificar.
    """
    if not data:
        return ""
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp850", errors="replace")


class SubprocessRunner:
    """Implementação real do ``CommandRunner``."""

    def run(
        self,
        args: Sequence[str | os.PathLike[str]],
        *,
        timeout: float,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        log_to: Path | None = None,
        secrets: Sequence[str] = (),
        stdin: bytes | None = None,
    ) -> CommandResult:
        if isinstance(args, (str, bytes)):
            raise TypeError("args deve ser uma lista de argumentos, nunca uma string")
        if timeout <= 0:
            raise ValueError("timeout deve ser positivo")
        argv = tuple(os.fspath(a) for a in args)
        shown = " ".join(mask_secrets(argv, secrets))
        log.debug("executando: %s", shown)

        full_env = None
        if env is not None:
            full_env = dict(os.environ)
            full_env.update(env)

        creationflags = CREATE_NO_WINDOW if is_windows() else 0
        start = time.monotonic()
        try:
            proc = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=full_env,
                creationflags=creationflags,
            )
        except OSError as exc:
            raise CommandError(f"não foi possível executar {shown}: {exc}") from exc

        timed_out = False
        try:
            out, err = proc.communicate(input=stdin, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._kill_tree(proc)
            out, err = proc.communicate()
        duration = time.monotonic() - start
        result = CommandResult(
            args=argv,
            exit_code=proc.returncode if proc.returncode is not None else -1,
            stdout=out or b"",
            stderr=err or b"",
            duration=duration,
            timed_out=timed_out,
            secrets=tuple(secrets),
        )
        log.debug(
            "terminou: %s → código %s em %.1fs%s",
            shown,
            result.exit_code,
            duration,
            " (tempo limite)" if timed_out else "",
        )
        if log_to is not None:
            _append_log(log_to, result)
        return result

    @staticmethod
    def _kill_tree(proc: subprocess.Popen[bytes]) -> None:
        if is_windows():
            # taskkill /T encerra também os filhos (instaladores costumam disparar outros).
            subprocess.run(
                [str(system32("taskkill.exe")), "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
                check=False,
                timeout=60,
            )
        proc.kill()


def _append_log(path: Path, result: CommandResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"$ {result.display_args()}\n")
        fh.write(f"# código {result.exit_code} em {result.duration:.1f}s")
        fh.write(" (tempo limite)\n" if result.timed_out else "\n")
        if result.stdout:
            fh.write(mask_text(result.stdout_text(), result.secrets) + "\n")
        if result.stderr:
            fh.write("# stderr\n" + mask_text(result.stderr_text(), result.secrets) + "\n")


def mask_text(text: str, secrets: Sequence[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, MASK)
    return SECRETS.mask(text)


def launch(args: Sequence[str | os.PathLike[str]], *, cwd: Path | None = None) -> None:
    """Abre um programa com janela (Ventoy, Rufus) e não espera ele fechar (V3-07)."""
    argv = [os.fspath(a) for a in args]
    log.debug("abrindo: %s", " ".join(argv))
    try:
        subprocess.Popen(argv, cwd=cwd, close_fds=True)
    except OSError as exc:
        raise CommandError(f"não foi possível abrir {argv[0]}: {exc}") from exc
