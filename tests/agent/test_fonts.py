"""Fontes (V2-07): leitor da tabela name, coleta, cópia ao marcar, etapa e conflito de nome.

As fontes de teste são geradas aqui mesmo (só o cabeçalho sfnt e a tabela ``name``), então não
há arquivo de terceiros nem licença envolvida.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.phases import run_phase1
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.collector.fonts import collect_fonts, select_font
from winkit.core.fonts import (
    FONTS_KEY,
    INSTALL_KEY,
    USER_FONTS_KEY,
    FontError,
    read_names,
    registry_name,
)
from winkit.platform.fakes.backup import FakeOldPcFolders
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.services import fake_services
from winkit.platform.fakes.system_tweaks import FakeFontLoader

INSTALLED_AT = 1_700_000_000


def mtime(path: Path) -> float:
    """Data controlada pelo teste (no Windows a de criação não muda com ``os.utime``, IN-018)."""
    return path.stat().st_mtime


def _new(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_font(family: str, full: str, *, cff: bool = False, mac_only: bool = False) -> bytes:
    """Fonte mínima: cabeçalho sfnt com uma tabela ``name`` (formato 0)."""
    records = []
    strings = b""
    for name_id, text in ((1, family), (4, full)):
        if mac_only:
            raw, plat, enc, lang = text.encode("latin-1"), 1, 0, 0
        else:
            raw, plat, enc, lang = text.encode("utf-16-be"), 3, 1, 0x0409
        records.append(struct.pack(">HHHHHH", plat, enc, lang, name_id, len(raw), len(strings)))
        strings += raw
    header = struct.pack(">HHH", 0, len(records), 6 + 12 * len(records))
    name = header + b"".join(records) + strings
    offset = 12 + 16
    tag = b"OTTO" if cff else b"\x00\x01\x00\x00"
    sfnt = tag + struct.pack(">HHHH", 1, 16, 0, 0)
    sfnt += b"name" + struct.pack(">III", 0, offset, len(name))
    return sfnt + name


def make_ttc(*fonts: bytes) -> bytes:
    header_len = 12 + 4 * len(fonts)
    offsets, body, pos = [], b"", header_len
    for f in fonts:
        offsets.append(pos)
        # cada fonte dentro do TTC aponta para a tabela com deslocamento absoluto
        fixed = bytearray(f)
        struct.pack_into(">I", fixed, 12 + 8, struct.unpack_from(">I", f, 12 + 8)[0] + pos)
        body += bytes(fixed)
        pos += len(f)
    return (
        b"ttcf"
        + struct.pack(">HHI", 1, 0, len(fonts))
        + b"".join(struct.pack(">I", o) for o in offsets)
        + body
    )


def test_read_names_variants() -> None:
    names = read_names(make_font("Inter", "Inter Regular"))
    assert (names.family, names.full_name, names.kind) == ("Inter", "Inter Regular", "TrueType")
    assert registry_name(names) == "Inter Regular (TrueType)"
    assert read_names(make_font("Fira", "Fira Bold", cff=True)).kind == "OpenType"
    assert read_names(make_font("Mac", "Mac Font", mac_only=True)).family == "Mac"
    ttc = make_ttc(make_font("Família", "Família Normal"), make_font("Outra", "Outra"))
    assert read_names(ttc).family == "Família"
    with pytest.raises(FontError):
        read_names(b"isto nao e fonte")
    with pytest.raises(FontError):
        read_names(make_font("Inter", "Inter Regular")[:30])  # truncada


def old_pc(tmp_path: Path) -> tuple[FakeRegistry, FakeOldPcFolders]:
    folders = FakeOldPcFolders(tmp_path / "C")
    user_fonts = (
        tmp_path
        / "C"
        / "Users"
        / "Samuel"
        / "AppData"
        / "Local"
        / "Microsoft"
        / "Windows"
        / "Fonts"
    )
    user_fonts.mkdir(parents=True)
    (user_fonts / "Inter-Regular.ttf").write_bytes(make_font("Inter", "Inter Regular"))
    machine = tmp_path / "C" / "Windows" / "Fonts"
    machine.mkdir(parents=True)
    (machine / "arial.ttf").write_bytes(make_font("Arial", "Arial"))
    os.utime(machine / "arial.ttf", (INSTALLED_AT - 100, INSTALLED_AT - 100))  # veio com o Windows
    (machine / "FiraCode.otf").write_bytes(make_font("Fira Code", "Fira Code Regular", cff=True))
    os.utime(machine / "FiraCode.otf", (INSTALLED_AT + 100, INSTALLED_AT + 100))
    (machine / "quebrada.ttf").write_bytes(b"lixo")
    os.utime(machine / "quebrada.ttf", (INSTALLED_AT + 100, INSTALLED_AT + 100))
    reg = FakeRegistry()
    reg.set("HKLM", INSTALL_KEY, "InstallDate", "dword", INSTALLED_AT)
    reg.set(
        "HKCU",
        USER_FONTS_KEY,
        "Inter Regular (TrueType)",
        "sz",
        r"C:\Users\Samuel\AppData\Local\Microsoft\Windows\Fonts\Inter-Regular.ttf",
    )
    reg.set("HKLM", FONTS_KEY, "Arial (TrueType)", "sz", "arial.ttf")
    reg.set("HKLM", FONTS_KEY, "Fira Code Regular (OpenType)", "sz", "FiraCode.otf")
    reg.set("HKLM", FONTS_KEY, "Quebrada (TrueType)", "sz", "quebrada.ttf")
    return reg, folders


def test_collect_skips_windows_fonts_and_copies_only_on_select(tmp_path: Path) -> None:
    w = make_world(_new(tmp_path / "w"))
    reg, folders = old_pc(tmp_path)
    r = w.recipe()
    added, errors = collect_fonts(reg, r"C:\Windows", folders.volume_root, r, mtime)
    assert {(f.full_name, f.origin) for f in added} == {
        ("Inter Regular", "user"),
        ("Fira Code Regular", "machine"),
    }
    assert errors == [r"C:\Windows\Fonts\quebrada.ttf"]
    assert not any(f.selected or f.file for f in added)
    assert not (w.pendrive / "WinKit" / "Perfis" / "padrao" / "Fontes").exists()  # nada copiado
    inter = next(f for f in added if f.family == "Inter")
    assert select_font(w.pendrive, r, inter.id, True, folders.volume_root)
    assert inter.file.startswith("Perfis/padrao/Fontes/") and inter.sha256
    assert (w.pendrive / "WinKit" / inter.file).is_file()
    assert collect_fonts(reg, r"C:\Windows", folders.volume_root, r, mtime) == ([], errors)


def _world(tmp_path: Path) -> World:
    w = make_world(_new(tmp_path / "w"))
    reg, folders = old_pc(tmp_path)
    r = w.recipe()
    collect_fonts(reg, r"C:\Windows", folders.volume_root, r, mtime)
    for f in r.fonts:
        select_font(w.pendrive, r, f.id, True, folders.volume_root)
    w.save_recipe(r)
    return w


def test_install_for_all_users_without_overwriting(tmp_path: Path) -> None:
    w = _world(tmp_path)
    fonts_dir = w.system / "Windows" / "Fonts"
    fonts_dir.mkdir(parents=True)
    inter = next(f for f in w.recipe().fonts if f.family == "Inter")
    other = fonts_dir / Path(inter.file).name
    other.write_bytes(b"outra fonte com o mesmo nome")
    run_phase1(w.runtime())
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    assert other.read_bytes() == b"outra fonte com o mesmo nome"  # nunca sobrescreve
    winkit_copy = other.with_name(f"{other.stem}_winkit{other.suffix}")
    assert winkit_copy.is_file()
    assert reg.get("HKLM", FONTS_KEY, "Inter Regular (TrueType)") == winkit_copy.name
    assert reg.get("HKLM", FONTS_KEY, "Fira Code Regular (OpenType)") is not None
    state = StateStore(w.paths.state).load()
    assert state is not None
    assert all(state.step(k).status == "done" for k in state.steps if k.startswith("font:"))


def test_live_loads_in_session_and_second_preview_is_done(tmp_path: Path) -> None:
    w = _world(tmp_path)
    loader = w.services.font_loader
    assert isinstance(loader, FakeFontLoader)
    opts = {"root": w.pendrive, "restore_point": False, "only_kinds": frozenset({"font"})}
    run_live(w.runtime(), LiveOptions(**opts))  # type: ignore[arg-type]
    assert len(loader.loaded) == 2
    again = run_live(w.runtime(), LiveOptions(simulate=True, **opts))  # type: ignore[arg-type]
    assert again.preview is not None
    assert {i.status for i in again.preview.items} == {"already_done"}


def test_cli_fonts(tmp_path: Path) -> None:
    w = make_world(_new(tmp_path / "w"))
    reg, folders = old_pc(tmp_path)
    # a CLI usa a data de criação real; tira a fonte "do Windows" para o teste não depender dela
    reg.delete_value("HKLM", FONTS_KEY, "Arial (TrueType)")
    services = fake_services(old_pc=folders.base, registry=reg)
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=services, out=out.append)

    assert run("coletar", "fontes") == 0
    ids = [f.id for f in w.recipe().fonts]
    assert len(ids) == 2
    assert run("fontes", "marcar", ids[0]) == 0
    assert [f.selected for f in w.recipe().fonts] == [True, False]
    assert run("fonts", "deselect", ids[0]) == 0
    assert run("fontes", "marcar", "nada") == 1
