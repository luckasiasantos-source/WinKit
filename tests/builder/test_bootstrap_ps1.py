"""Testes reais do bootstrap.ps1 no Windows (CI windows-latest)."""

from __future__ import annotations

import json
import os
import subprocess
from importlib import resources
from pathlib import Path

import pytest

from tests.factories import FIXED_NOW
from winkit.builder.build import ensure_marker, save_profile_recipe
from winkit.core import layout
from winkit.core.recipe.io import new_recipe

SCRIPT = resources.files("winkit.builder").joinpath("assets/bootstrap.ps1")


def _ps(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    exe = (
        Path(os.environ["SYSTEMROOT"])
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    return subprocess.run(
        [str(exe), "-NoProfile", "-ExecutionPolicy", "Bypass", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=120,
    )


@pytest.mark.windows
def test_script_parses_without_errors(tmp_path: Path) -> None:
    script = tmp_path / "bootstrap.ps1"
    script.write_bytes(SCRIPT.read_bytes())
    code = (
        "$e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
        f"'{script}', [ref]$null, [ref]$e); if ($e.Count) {{ $e | Out-String; exit 1 }}"
    )
    proc = _ps("-Command", code, env=dict(os.environ))
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.windows
def test_bootstrap_without_agent(tmp_path: Path) -> None:
    pen = tmp_path / "pen"
    pen.mkdir()
    marker = ensure_marker(pen, FIXED_NOW)
    save_profile_recipe(
        pen, new_recipe(pendrive_id=marker.pendrive_id, username="Samuel", now=FIXED_NOW)
    )
    script = pen / layout.BOOTSTRAP
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_bytes(SCRIPT.read_bytes())
    program_data = tmp_path / "ProgramData"
    program_data.mkdir()
    env = {**os.environ, "ProgramData": str(program_data)}

    proc = _ps(
        "-File",
        str(script),
        str(pen)[:2] if False else str(pen),
        marker.pendrive_id,
        "padrao",
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    base = program_data / "WinKit"
    info = json.loads((base / "bootstrap.json").read_text(encoding="utf-8-sig"))
    assert info["pendrive_id"] == marker.pendrive_id and info["agent_present"] is False
    assert (base / "receita.json").is_file()
    log = (base / "Logs" / "bootstrap.log").read_text(encoding="utf-8-sig")
    assert "bootstrap concluído" in log
    copied = list((pen / "WinKit" / "Logs").glob("*/bootstrap.log"))
    assert copied

    # segunda execução: nada a fazer
    proc = _ps("-File", str(script), str(pen), marker.pendrive_id, "padrao", env=env)
    assert proc.returncode == 0
    assert "já executado" in (base / "Logs" / "bootstrap.log").read_text(encoding="utf-8-sig")


@pytest.mark.windows
def test_bootstrap_ignores_other_pendrive(tmp_path: Path) -> None:
    pen = tmp_path / "pen"
    pen.mkdir()
    ensure_marker(pen, FIXED_NOW)
    script = pen / layout.BOOTSTRAP
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_bytes(SCRIPT.read_bytes())
    program_data = tmp_path / "ProgramData"
    program_data.mkdir()
    env = {**os.environ, "ProgramData": str(program_data)}
    proc = _ps("-File", str(script), str(pen), "outro-id", "padrao", env=env)
    assert proc.returncode == 0
    assert not (program_data / "WinKit" / "bootstrap.json").exists()
    assert "outro pendrive" in (program_data / "WinKit" / "Logs" / "bootstrap.log").read_text(
        encoding="utf-8-sig"
    )


@pytest.mark.windows
def test_bootstrap_never_fails_installation(tmp_path: Path) -> None:
    program_data = tmp_path / "ProgramData"
    program_data.mkdir()
    env = {**os.environ, "ProgramData": str(program_data)}
    script = tmp_path / "bootstrap.ps1"
    script.write_bytes(SCRIPT.read_bytes())
    proc = _ps("-File", str(script), str(tmp_path / "nao-existe"), "x", "padrao", env=env)
    assert proc.returncode == 0  # erro registrado, mas a instalação segue
    assert "ERRO" in (program_data / "WinKit" / "Logs" / "bootstrap.log").read_text(
        encoding="utf-8-sig"
    )
