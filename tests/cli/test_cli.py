from __future__ import annotations

import json
from pathlib import Path

import pytest

from winkit.cli.main import main
from winkit.core import layout
from winkit.platform.fakes.disks import FakeDiskInspector, windows_iso
from winkit.platform.fakes.runner import FakeRunner
from winkit.platform.services import Services


@pytest.fixture
def services() -> Services:
    return Services(
        runner=FakeRunner(), disks=FakeDiskInspector(isos={"Windows11.iso": windows_iso()})
    )


def run(argv: list[str], services: Services) -> tuple[int, str]:
    lines: list[str] = []
    code = main(argv, services=services, out=lines.append)
    return code, "\n".join(lines)


def test_full_flow_in_a_folder(tmp_path: Path, services: Services) -> None:
    root = tmp_path / "pen"
    root.mkdir()
    (root / "Windows11.iso").write_bytes(b"iso")
    raiz = ["--raiz", str(root)]

    code, text = run(
        ["receita", "nova", *raiz, "--usuario", "Samuel", "--nome-pc", "PC-SAM"], services
    )
    assert code == 0 and "Receita criada" in text
    code, text = run(["receita", "nova", *raiz, "--usuario", "Samuel"], services)
    assert code == 1 and "sobrescrever" in text

    code, text = run(["plano", *raiz], services)
    assert code == 0 and "Fase 1" in text and "Concluir" in text

    code, text = run(["construir", *raiz, "--somente-xml"], services)
    assert code == 0, text
    assert "Modelo gravado: /ventoy/script/winkit-padrao-pt-BR-amd64.xml" in text
    assert "Windows 11 build 26100" in text

    code, text = run(["validar", *raiz], services)
    assert code == 0 and "Tudo certo" in text
    recipe = json.loads((root / layout.recipe_file("padrao")).read_text(encoding="utf-8"))
    assert recipe["windows"]["computer_name"] == "PC-SAM"


def test_invalid_username(tmp_path: Path, services: Services) -> None:
    code, text = run(
        ["receita", "nova", "--raiz", str(tmp_path), "--usuario", "Administrator"], services
    )
    assert code == 1 and "reservado" in text


def test_build_without_recipe_reports_error(tmp_path: Path, services: Services) -> None:
    code, text = run(["construir", "--raiz", str(tmp_path)], services)
    assert code == 2 and "receita nova" in text


def test_validate_failure_exit_code(tmp_path: Path, services: Services) -> None:
    code, text = run(["validar", "--raiz", str(tmp_path)], services)
    assert code == 1 and "problema" in text


def test_plan_flags(tmp_path: Path, services: Services) -> None:
    run(["receita", "nova", "--raiz", str(tmp_path), "--usuario", "Samuel"], services)
    code, text = run(["plano", "--raiz", str(tmp_path), "--sem-fase1"], services)
    assert code == 0 and "Fase 1 (0 etapas)" in text and "veio da Fase 1" in text


def test_pendrive_listar(services: Services) -> None:
    code, text = run(["pendrive", "listar"], services)
    assert code == 0 and "E:" in text and "exFAT" in text
    empty = Services(runner=FakeRunner(), disks=FakeDiskInspector(rows=[]))
    code, text = run(["pendrive", "listar"], empty)
    assert code == 1


def test_pendrive_by_letter(services: Services) -> None:
    code, text = run(["validar", "--pendrive", "Z:"], services)
    assert code == 2 and "Z:" in text


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--version"])
    assert "WinKit" in capsys.readouterr().out
