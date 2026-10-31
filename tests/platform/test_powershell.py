from __future__ import annotations

import base64
import json
import re
import sys

import pytest

from winkit.core.errors import PowerShellError
from winkit.platform.fakes.runner import FakeRunner, result
from winkit.platform.powershell import (
    PowerShell,
    build_script,
    encode_command,
    parse_json_output,
)
from winkit.platform.runner import SubprocessRunner


def _decode_params(script: str) -> dict[str, object]:
    match = re.search(r"FromBase64String\('([A-Za-z0-9+/=]*)'\)", script)
    assert match
    return json.loads(base64.b64decode(match.group(1)).decode("utf-8"))


def test_params_are_never_interpolated_into_the_script() -> None:
    evil = "'; Remove-Item C:\\ -Recurse; '"
    script = build_script("Write-Output $p.Name", {"Name": evil}, json_output=True)
    assert evil not in script
    assert _decode_params(script) == {"Name": evil}


def test_unicode_params_roundtrip() -> None:
    script = build_script("$p.N", {"N": "Configurações ção ✓"}, json_output=False)
    assert _decode_params(script) == {"N": "Configurações ção ✓"}


def test_body_with_braces_is_kept() -> None:
    body = "Get-Item | Where-Object { $_.Name -eq 'x' }"
    assert "{ $_.Name -eq 'x' }" in build_script(body, None, json_output=True)


def test_encode_command_is_utf16le_base64() -> None:
    assert base64.b64decode(encode_command("Olá")).decode("utf-16-le") == "Olá"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (b"", []),
        (b"[]", []),
        (b'[{"a":1}]', [{"a": 1}]),
        (b'{"a":1}', [{"a": 1}]),
        ('\ufeff[{"n":"ção"}]'.encode(), [{"n": "ção"}]),
    ],
)
def test_parse_json_output(raw: bytes, expected: list[object]) -> None:
    assert parse_json_output(raw) == expected


def test_run_json_uses_encoded_command_and_parses() -> None:
    runner = FakeRunner().when_contains("-EncodedCommand", result(stdout=b'[{"x":"y"}]'))
    ps = PowerShell(runner)
    assert ps.run_json("Get-Thing") == [{"x": "y"}]
    args = runner.calls[0].args
    assert args[0].lower().endswith("powershell.exe")
    assert "-NoProfile" in args and "-NonInteractive" in args
    script = base64.b64decode(args[-1]).decode("utf-16-le")
    assert "Get-Thing" in script
    assert "ConvertTo-Json" in script


def test_run_json_raises_on_failure() -> None:
    runner = FakeRunner().when_contains("-EncodedCommand", result(exit_code=1, stderr="boom"))
    with pytest.raises(PowerShellError, match="boom"):
        PowerShell(runner).run_json("Get-Thing")


def test_run_json_raises_on_timeout() -> None:
    runner = FakeRunner().when_contains("-EncodedCommand", result(timed_out=True, exit_code=-1))
    with pytest.raises(PowerShellError) as exc:
        PowerShell(runner).run_json("Get-Thing")
    assert exc.value.timed_out


def test_run_json_raises_on_invalid_json() -> None:
    runner = FakeRunner().when_contains("-EncodedCommand", result(stdout=b"nao json"))
    with pytest.raises(PowerShellError, match="JSON"):
        PowerShell(runner).run_json("Get-Thing")


def test_run_plain_ok() -> None:
    runner = FakeRunner()
    assert PowerShell(runner).run("Do-It").ok


@pytest.mark.windows
def test_real_powershell_roundtrip() -> None:
    ps = PowerShell(SubprocessRunner())
    out = ps.run_json(
        "[pscustomobject]@{ Name = $p.Name; Len = $p.Name.Length; Sum = $p.A + $p.B }",
        {"Name": "Configurações \"aspas\" 'simples' ✓", "A": 2, "B": 3},
        timeout=120,
    )
    assert out == [{"Name": "Configurações \"aspas\" 'simples' ✓", "Len": 33, "Sum": 5}]


@pytest.mark.windows
def test_real_powershell_error_is_raised() -> None:
    with pytest.raises(PowerShellError):
        PowerShell(SubprocessRunner()).run_json("throw 'falha proposital'", timeout=120)


@pytest.mark.windows
def test_real_powershell_empty_and_list() -> None:
    ps = PowerShell(SubprocessRunner())
    assert ps.run_json("$null", timeout=120) == []
    assert ps.run_json("1,2,3", timeout=120) == [1, 2, 3]


def test_platform_marker_sanity() -> None:
    assert sys.platform  # garante que o arquivo roda em qualquer plataforma
