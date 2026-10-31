"""``CommandRunner`` falso: grava as chamadas e devolve respostas programadas."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from winkit.platform.runner import CommandResult

Matcher = Callable[[tuple[str, ...]], bool]
Responder = Callable[[tuple[str, ...]], CommandResult]


@dataclass
class RecordedCall:
    args: tuple[str, ...]
    timeout: float
    cwd: Path | None
    env: Mapping[str, str] | None
    stdin: bytes | None


def result(
    args: Sequence[str] = (),
    exit_code: int = 0,
    stdout: bytes | str = b"",
    stderr: bytes | str = b"",
    timed_out: bool = False,
) -> CommandResult:
    return CommandResult(
        args=tuple(args),
        exit_code=exit_code,
        stdout=stdout.encode() if isinstance(stdout, str) else stdout,
        stderr=stderr.encode() if isinstance(stderr, str) else stderr,
        duration=0.0,
        timed_out=timed_out,
    )


@dataclass
class FakeRunner:
    """Responde à primeira regra cujo ``matcher`` aceitar os argumentos.

    Sem regra correspondente, devolve código 0 e saída vazia (ou lança, se ``strict``).
    """

    strict: bool = False
    calls: list[RecordedCall] = field(default_factory=list)
    _rules: list[tuple[Matcher, Responder]] = field(default_factory=list)

    def when(self, matcher: Matcher, responder: Responder | CommandResult) -> FakeRunner:
        if isinstance(responder, CommandResult):
            fixed = responder
            self._rules.append((matcher, lambda args: fixed))
        else:
            self._rules.append((matcher, responder))
        return self

    def when_contains(self, needle: str, responder: Responder | CommandResult) -> FakeRunner:
        return self.when(lambda args: any(needle.lower() in a.lower() for a in args), responder)

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
        argv = tuple(os.fspath(a) for a in args)
        self.calls.append(RecordedCall(argv, timeout, cwd, env, stdin))
        for matcher, responder in self._rules:
            if matcher(argv):
                res = responder(argv)
                return CommandResult(
                    args=argv,
                    exit_code=res.exit_code,
                    stdout=res.stdout,
                    stderr=res.stderr,
                    duration=res.duration,
                    timed_out=res.timed_out,
                    secrets=tuple(secrets),
                )
        if self.strict:
            raise AssertionError(f"chamada inesperada: {argv}")
        return result(argv)

    def executables(self) -> list[str]:
        return [Path(c.args[0]).name.lower() for c in self.calls]
