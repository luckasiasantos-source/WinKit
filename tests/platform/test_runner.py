from __future__ import annotations

import sys
from pathlib import Path

import pytest

from winkit.core.errors import CommandError
from winkit.platform.runner import (
    CommandResult,
    SubprocessRunner,
    decode_for_log,
    mask_secrets,
)

PY = sys.executable


def test_runs_command_and_captures_bytes() -> None:
    res = SubprocessRunner().run([PY, "-c", "print('olá')"], timeout=30)
    assert res.ok
    assert res.exit_code == 0
    assert "olá" in res.stdout_text()
    assert isinstance(res.stdout, bytes)


def test_nonzero_exit_code_is_reported_not_raised() -> None:
    res = SubprocessRunner().run([PY, "-c", "import sys; sys.exit(3)"], timeout=30)
    assert res.exit_code == 3
    assert not res.ok
    with pytest.raises(CommandError) as exc:
        res.check()
    assert exc.value.exit_code == 3


def test_timeout_kills_process() -> None:
    res = SubprocessRunner().run([PY, "-c", "import time; time.sleep(30)"], timeout=0.5)
    assert res.timed_out
    assert not res.ok
    assert res.duration < 20
    with pytest.raises(CommandError) as exc:
        res.check()
    assert exc.value.timed_out


def test_string_args_are_rejected() -> None:
    with pytest.raises(TypeError):
        SubprocessRunner().run("echo oi", timeout=5)  # type: ignore[arg-type]


def test_timeout_must_be_positive() -> None:
    with pytest.raises(ValueError):
        SubprocessRunner().run([PY, "-c", "pass"], timeout=0)


def test_missing_executable_raises_command_error(tmp_path: Path) -> None:
    with pytest.raises(CommandError):
        SubprocessRunner().run([str(tmp_path / "nao-existe.exe")], timeout=5)


def test_stdin_and_env_and_cwd(tmp_path: Path) -> None:
    code = "import os,sys; print(sys.stdin.read() + os.environ['WK_X'] + os.getcwd())"
    res = SubprocessRunner().run(
        [PY, "-c", code], timeout=30, stdin=b"abc-", env={"WK_X": "xyz-"}, cwd=tmp_path
    )
    assert res.stdout_text().strip() == "abc-xyz-" + str(tmp_path)


def test_log_masks_secrets(tmp_path: Path) -> None:
    log = tmp_path / "logs" / "cmd.log"
    SubprocessRunner().run(
        [PY, "-c", "print('segredo123')", "--senha=segredo123"],
        timeout=30,
        log_to=log,
        secrets=["segredo123"],
    )
    content = log.read_text(encoding="utf-8")
    assert "segredo123" not in content
    assert "***" in content


def test_mask_secrets_ignores_empty() -> None:
    assert mask_secrets(["a", "b"], [""]) == ["a", "b"]


def test_display_args_masks() -> None:
    res = CommandResult(("x", "pw=abc"), 0, b"", b"", 0.0, secrets=("abc",))
    assert res.display_args() == "x pw=***"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (b"", ""),
        ("ação".encode(), "ação"),
        (b"\xef\xbb\xbfbom", "bom"),
        ("utf16".encode("utf-16"), "utf16"),
        ("ação".encode("cp850"), "ação"),
    ],
)
def test_decode_for_log(raw: bytes, expected: str) -> None:
    assert decode_for_log(raw) == expected
