from __future__ import annotations

import json
from pathlib import Path

import pytest

from winkit.cli.main import main
from winkit.core import layout
from winkit.platform.fakes.disks import FakeDiskInspector
from winkit.platform.fakes.services import fake_services
from winkit.platform.services import Services


@pytest.fixture
def services() -> Services:
    return fake_services()


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
    empty = fake_services(disks=FakeDiskInspector(rows=[]))
    code, text = run(["pendrive", "listar"], empty)
    assert code == 1


def test_pendrive_by_letter(services: Services) -> None:
    code, text = run(["validar", "--pendrive", "Z:"], services)
    assert code == 2 and "Z:" in text


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--version"])
    assert "WinKit" in capsys.readouterr().out


def test_coletar_drivers(tmp_path: Path, services: Services) -> None:
    raiz = ["--raiz", str(tmp_path)]
    run(["receita", "nova", *raiz, "--usuario", "Samuel"], services)
    code, text = run(["coletar", "drivers", *raiz, "--listar"], services)
    assert code == 0 and "[x]" in text and "[ ] Impressora" in text
    assert not (tmp_path / "WinKit" / "Drivers").exists()
    code, text = run(["coletar", "drivers", *raiz], services)
    assert code == 0 and "3 drivers exportados" in text
    code, text = run(["coletar", "drivers", *raiz, "--classe", "Printer"], services)
    assert "1 driver exportado" in text
    code, text = run(["construir", *raiz], services)
    assert "Manifesto:" in text and "Drivers" in text


def test_apps_flow(tmp_path: Path, services: Services) -> None:
    from tests.core.test_installer_detect import fake_pe
    from winkit.platform.fakes.apps import FakeWinget

    raiz = ["--raiz", str(tmp_path / "pen")]
    (tmp_path / "pen").mkdir()
    run(["receita", "nova", *raiz, "--usuario", "Samuel"], services)
    code, text = run(["coletar", "apps", *raiz], services)
    assert code == 0 and "discord" in text and "[ ]" in text
    code, text = run(["apps", "marcar", "discord", "7zip", *raiz, "--ordem", "5"], services)
    assert code == 0 and "2 apps marcados" in text
    code, text = run(["apps", "marcar", "nao-existe", *raiz], services)
    assert code == 1
    winget = services.winget
    assert isinstance(winget, FakeWinget)
    winget.downloads["7zip.7zip"] = ("nullsoft", "machine", "/S")
    code, text = run(["apps", "baixar", *raiz], services)
    assert "ok  7zip" in text and "não discord" in text
    code, text = run(["apps", "listar", *raiz], services)
    assert "[x] 7zip" in text and "instalador offline" in text
    setup = tmp_path / "x.exe"
    setup.write_bytes(fake_pe([".text"], b"Nullsoft.NSIS"))
    code, text = run(
        ["apps", "adicionar", *raiz, "--instalador", str(setup), "--nome", "X"], services
    )
    assert code == 0 and "tipo nsis" in text
    unknown = tmp_path / "y.exe"
    unknown.write_bytes(fake_pe([".text"]))
    code, text = run(
        ["apps", "adicionar", *raiz, "--instalador", str(unknown), "--nome", "Y"], services
    )
    assert code == 1 and "--args" in text
    code, text = run(["apps", "desmarcar", "y", *raiz], services)
    assert code == 0
    code, text = run(["construir", *raiz], services)
    assert code == 0, text
    code, text = run(["validar", *raiz], services)
    assert code == 0, text


def test_backup_flow(tmp_path: Path) -> None:
    old = tmp_path / "C"
    d = old / "Users" / "Samuel" / "AppData" / "Roaming" / "discord"
    d.mkdir(parents=True)
    (d / "settings.json").write_text("{}")
    tool = old / "Ferramentas" / "Tool"
    tool.mkdir(parents=True)
    (tool / "tool.exe").write_bytes(b"MZ")
    services = fake_services(old_pc=old)
    pen = tmp_path / "pen"
    pen.mkdir()
    raiz = ["--raiz", str(pen)]
    run(["receita", "nova", *raiz, "--usuario", "Samuel"], services)
    code, text = run(["coletar", "backups", *raiz], services)
    assert code == 0 and "Nenhuma sugestão" in text
    run(["coletar", "apps", *raiz], services)
    run(["apps", "marcar", "discord", *raiz], services)
    code, text = run(["coletar", "backups", *raiz, "--adicionar-recomendados"], services)
    assert code == 0 and "[x] Discord" in text and "1 backup recomendado" in text
    code, text = run(
        [
            "backup",
            "adicionar",
            r"C:\Users\Samuel\AppData\Roaming\discord",
            *raiz,
            "--nome",
            "Discord inteiro",
            "--conflito",
            "overwrite",
        ],
        services,
    )
    assert code == 0 and r"{APPDATA}\discord" in text
    code, text = run(
        [
            "apps",
            "portatil",
            *raiz,
            "--pasta",
            r"C:\Ferramentas\Tool",
            "--nome",
            "Tool",
            "--exe",
            "tool.exe",
        ],
        services,
    )
    assert code == 0 and "ABS" in text
    code, text = run(["backup", "capturar", *raiz], services)
    assert code == 0, text
    assert text.count("ok ") == 3 and "cópia de sombra" in text
    code, text = run(["backup", "listar", *raiz], services)
    assert "capturado" in text and "ainda não" not in text
    code, text = run(["sincronizar", *raiz], services)
    assert code == 0 and "Recapturando" in text and "Manifesto" in text
    code, text = run(["validar", *raiz], services)
    assert code == 0, text
    code, text = run(["backup", "remover", "discord-inteiro", *raiz], services)
    assert code == 0
    assert not (pen / "WinKit" / "Perfis" / "padrao" / "Backups" / "discord-inteiro").exists()
    code, text = run(["backup", "remover", "nao-existe", *raiz], services)
    assert code == 1


def test_language_option_and_english_aliases(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """D-030/D-032: ``--idioma`` traduz ajuda e saída; os apelidos em inglês funcionam."""
    from winkit.cli.main import main
    from winkit.i18n import current_language

    raiz = ["--raiz", str(tmp_path / "pen")]
    out: list[str] = []
    services = fake_services()
    assert (
        main(
            ["--idioma", "en-US", "recipe", "new", *raiz, "--usuario", "Sam"],
            services=services,
            out=out.append,
        )
        == 0
    )
    assert current_language() == "en-US" and out[-1].startswith("Recipe created at")
    out.clear()
    assert main(["--idioma=es", "plan", *raiz], services=services, out=out.append) == 0
    assert out[0].startswith("Fase 1") and "pasos" in out[0]
    with pytest.raises(SystemExit):
        main(["--idioma", "en-US", "build", "--help"], services=services, out=out.append)
    help_text = capsys.readouterr().out
    assert "prepare the USB drive" not in help_text or "--agente" in help_text
    assert "folder of the compiled Agent" in help_text


def test_winkit_lang_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from winkit.cli.main import main
    from winkit.i18n import current_language

    monkeypatch.setenv("WINKIT_LANG", "es-MX")
    out: list[str] = []
    main(
        ["receita", "nova", "--raiz", str(tmp_path / "p"), "--usuario", "Ana"],
        services=fake_services(),
        out=out.append,
    )
    assert current_language() == "es" and out[-1].startswith("Receta creada")
