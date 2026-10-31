"""``PowerShell`` falso: casa o corpo do script por trecho e devolve objetos prontos."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from winkit.core.errors import PowerShellError
from winkit.platform.fakes.runner import result
from winkit.platform.runner import CommandResult

JsonResponder = Callable[[Mapping[str, Any]], list[Any]]


@dataclass
class PsCall:
    body: str
    params: dict[str, Any]
    json_output: bool


@dataclass
class FakePowerShell:
    calls: list[PsCall] = field(default_factory=list)
    _rules: list[tuple[str, JsonResponder | list[Any] | Exception]] = field(default_factory=list)

    def when(self, needle: str, response: JsonResponder | list[Any] | Exception) -> FakePowerShell:
        self._rules.append((needle, response))
        return self

    def _respond(self, body: str, params: Mapping[str, Any]) -> list[Any]:
        for needle, response in self._rules:
            if needle in body:
                if isinstance(response, Exception):
                    raise response
                if callable(response):
                    return response(params)
                return response
        return []

    def run_json(
        self,
        body: str,
        params: Mapping[str, Any] | None = None,
        *,
        timeout: float = 300.0,
        log_to: Path | None = None,
    ) -> list[Any]:
        p = dict(params or {})
        self.calls.append(PsCall(body, p, True))
        return self._respond(body, p)

    def run(
        self,
        body: str,
        params: Mapping[str, Any] | None = None,
        *,
        timeout: float = 300.0,
        log_to: Path | None = None,
    ) -> CommandResult:
        p = dict(params or {})
        self.calls.append(PsCall(body, p, False))
        self._respond(body, p)
        return result()

    def bodies(self) -> list[str]:
        return [c.body for c in self.calls]


def ps_error(message: str = "falhou") -> PowerShellError:
    return PowerShellError(message, exit_code=1)
