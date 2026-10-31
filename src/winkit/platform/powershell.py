"""Execução de PowerShell com UTF-8 e resultado em JSON (ARQUITETURA.md, R-13, R-14).

Os valores vindos do Python nunca são interpolados no texto do script: eles são
serializados em JSON, codificados em Base64 e reconstruídos como ``$p`` dentro do
PowerShell. O script inteiro é enviado por ``-EncodedCommand`` (UTF-16LE em Base64),
então aspas e caracteres especiais nunca quebram a linha de comando.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from winkit.core.errors import PowerShellError
from winkit.platform.runner import CommandResult, CommandRunner
from winkit.platform.system import powershell_exe

DEFAULT_TIMEOUT = 300.0

_PRELUDE = """\
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$p = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{params}')) | ConvertFrom-Json
"""

_JSON_WRAP = """\
try {{
    $__r = & {{
{body}
    }}
    if ($null -eq $__r) {{ '[]' }}
    else {{ ConvertTo-Json -InputObject @($__r) -Depth 8 -Compress }}
}} catch {{
    [Console]::Error.WriteLine(($_ | Out-String))
    exit 1
}}
"""

_PLAIN_WRAP = """\
try {{
{body}
}} catch {{
    [Console]::Error.WriteLine(($_ | Out-String))
    exit 1
}}
"""


def build_script(body: str, params: Mapping[str, Any] | None, *, json_output: bool) -> str:
    payload = json.dumps(dict(params or {}), ensure_ascii=False).encode("utf-8")
    encoded = base64.b64encode(payload).decode("ascii")
    indented = "\n".join("        " + line for line in body.strip("\n").splitlines())
    wrap = _JSON_WRAP if json_output else _PLAIN_WRAP
    return _PRELUDE.format(params=encoded) + wrap.format(body=indented)


def encode_command(script: str) -> str:
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def parse_json_output(raw: bytes) -> list[Any]:
    text = raw.decode("utf-8-sig", errors="strict").strip()
    if not text:
        return []
    value = json.loads(text)
    return value if isinstance(value, list) else [value]


class PowerShell:
    def __init__(self, runner: CommandRunner, exe: Path | None = None) -> None:
        self._runner = runner
        self._exe = exe or powershell_exe()

    def _invoke(self, script: str, timeout: float, log_to: Path | None) -> CommandResult:
        return self._runner.run(
            [
                str(self._exe),
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encode_command(script),
            ],
            timeout=timeout,
            log_to=log_to,
        )

    def run_json(
        self,
        body: str,
        params: Mapping[str, Any] | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        log_to: Path | None = None,
    ) -> list[Any]:
        """Executa ``body`` e devolve a saída como lista de objetos JSON."""
        result = self._invoke(build_script(body, params, json_output=True), timeout, log_to)
        self._raise_if_failed(result, body)
        try:
            return parse_json_output(result.stdout)
        except (ValueError, UnicodeDecodeError) as exc:
            raise PowerShellError(
                f"saída do PowerShell não é JSON válido: {exc}: {result.stdout_text()[:500]}"
            ) from exc

    def run(
        self,
        body: str,
        params: Mapping[str, Any] | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        log_to: Path | None = None,
    ) -> CommandResult:
        """Executa ``body`` sem interpretar a saída; lança erro se falhar."""
        result = self._invoke(build_script(body, params, json_output=False), timeout, log_to)
        self._raise_if_failed(result, body)
        return result

    @staticmethod
    def _raise_if_failed(result: CommandResult, body: str) -> None:
        if result.timed_out:
            raise PowerShellError("PowerShell excedeu o tempo limite", timed_out=True)
        if result.exit_code != 0:
            first_line = body.strip().splitlines()[0] if body.strip() else ""
            raise PowerShellError(
                f"PowerShell falhou (código {result.exit_code}) em '{first_line}': "
                f"{result.stderr_text().strip()[:2000]}",
                exit_code=result.exit_code,
            )
