"""Aparência pessoal (V2-06): validação dos valores, papel de parede, perfil Default e ao vivo."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.phases import run_phase1
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.collector.personal import collect_personal
from winkit.core.catalog.loader import default_catalogs
from winkit.core.personal import WALLPAPER_KEY, WALLPAPER_VALUE, image_kind, normalize
from winkit.platform.fakes.backup import FakeOldPcFolders
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.services import fake_services
from winkit.platform.fakes.system_tweaks import FakeLiveAppearance
from winkit.platform.registry import DEFAULT_HIVE_MOUNT

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64
APPDATA = r"C:\Users\Samuel\AppData\Roaming"
ACCENT = r"Software\Microsoft\Windows\DWM"
MOUSE = r"Control Panel\Mouse"


def spec(group: str, value: str):  # type: ignore[no-untyped-def]
    g = default_catalogs().personal_group(group)
    assert g is not None
    return next(s for s in g.values if s.value == value)


@pytest.mark.parametrize(
    ("group", "value", "raw", "ok"),
    [
        ("mouse", "MouseSensitivity", "10", True),
        ("mouse", "MouseSensitivity", "99", False),  # fora da faixa
        ("mouse", "MouseSpeed", "1", True),
        ("mouse", "MouseSpeed", 1, False),  # tipo errado
        ("accent", "ColorPrevalence", 1, True),
        ("accent", "ColorPrevalence", 7, False),
        ("accent", "AccentPalette", b"\x01" * 32, True),
        ("accent", "AccentPalette", b"\x01" * 31, False),  # tamanho errado
        ("cursor", "Arrow", r"%SystemRoot%\cursors\aero_arrow.cur", True),
        ("cursor", "Arrow", r"C:\Users\Samuel\meu.cur", False),  # fora da pasta do Windows
        ("cursor", "Arrow", "", True),
    ],
)
def test_values_are_validated(group: str, value: str, raw: object, ok: bool) -> None:
    assert (normalize(spec(group, value), raw) is not None) is ok


def test_image_kind() -> None:
    assert image_kind(JPEG) == "jpg"
    assert image_kind(b"\x89PNG\r\n\x1a\n...") == "png"
    assert image_kind(b"texto") is None


def old_pc(
    tmp_path: Path, *, wallpaper_exists: bool = True
) -> tuple[FakeRegistry, FakeOldPcFolders]:
    folders = FakeOldPcFolders(tmp_path / "C")
    reg = FakeRegistry()
    reg.set("HKCU", ACCENT, "AccentColor", "dword", 0xFFD77800)
    reg.set("HKCU", ACCENT, "ColorPrevalence", "dword", 9)  # inválido: descartado
    reg.set("HKCU", MOUSE, "MouseSensitivity", "sz", "14")
    reg.set("HKCU", MOUSE, "MouseSpeed", "sz", "0")
    themes = (
        tmp_path
        / "C"
        / "Users"
        / "Samuel"
        / "AppData"
        / "Roaming"
        / "Microsoft"
        / "Windows"
        / "Themes"
    )
    themes.mkdir(parents=True)
    (themes / "TranscodedWallpaper").write_bytes(JPEG)
    if wallpaper_exists:
        pics = tmp_path / "C" / "Users" / "Samuel" / "Pictures"
        pics.mkdir(parents=True)
        (pics / "praia.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
        reg.set("HKCU", WALLPAPER_KEY, WALLPAPER_VALUE, "sz", r"C:\Users\Samuel\Pictures\praia.png")
    else:
        reg.set("HKCU", WALLPAPER_KEY, WALLPAPER_VALUE, "sz", r"C:\Users\Samuel\apagado.jpg")
    return reg, folders


def test_collect_validates_and_falls_back_to_transcoded(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    reg, folders = old_pc(tmp_path, wallpaper_exists=False)
    r = w.recipe()
    report = collect_personal(
        reg, w.pendrive, r, default_catalogs(), appdata=APPDATA, volume_root=folders.volume_root
    )
    assert report.dropped == [rf"{ACCENT}\ColorPrevalence"]
    assert rf"{ACCENT}\AccentColor" in r.personal.values
    assert r.personal.wallpaper_file is not None and r.personal.wallpaper_file.endswith(".jpg")
    assert set(r.personal.groups) == {"wallpaper", "accent", "mouse"}


def _world(tmp_path: Path) -> World:
    w = make_world(tmp_path)
    reg, folders = old_pc(tmp_path)
    r = w.recipe()
    collect_personal(
        reg, w.pendrive, r, default_catalogs(), appdata=APPDATA, volume_root=folders.volume_root
    )
    w.save_recipe(r)
    return w


def test_phase1_writes_default_profile_and_copies_wallpaper(tmp_path: Path) -> None:
    w = _world(tmp_path)
    run_phase1(w.runtime())
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    pre = DEFAULT_HIVE_MOUNT + "\\"
    assert reg.get("HKU", pre + ACCENT, "AccentColor") == 0xFFD77800
    assert reg.get("HKU", pre + ACCENT, "ColorPrevalence") is None  # o inválido nunca chega
    assert reg.get("HKU", pre + MOUSE, "MouseSensitivity") == "14"
    wall = reg.get("HKU", pre + WALLPAPER_KEY, WALLPAPER_VALUE)
    assert wall.endswith(r"Web\Wallpaper\WinKit\papel-de-parede.png")
    copied = w.system / "Windows" / "Web" / "Wallpaper" / "WinKit" / "papel-de-parede.png"
    assert copied.read_bytes().startswith(b"\x89PNG")
    assert reg.mounted == {}
    state = StateStore(w.paths.state).load()
    assert state is not None
    assert all(state.step(k).status == "done" for k in state.steps if k.startswith("personal:"))


def test_live_applies_now_and_then_is_done(tmp_path: Path) -> None:
    w = _world(tmp_path)
    live = w.services.appearance
    assert isinstance(live, FakeLiveAppearance)
    opts = {"root": w.pendrive, "restore_point": False, "only_kinds": frozenset({"personal"})}
    run_live(w.runtime(), LiveOptions(**opts))  # type: ignore[arg-type]
    assert len(live.wallpapers) == 1
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    assert reg.get("HKCU", MOUSE, "MouseSensitivity") == "14"
    again = run_live(w.runtime(), LiveOptions(simulate=True, **opts))  # type: ignore[arg-type]
    assert again.preview is not None
    assert {i.status for i in again.preview.items} == {"already_done"}


def test_cli_appearance(tmp_path: Path) -> None:
    (tmp_path / "w").mkdir()
    w = make_world(tmp_path / "w")
    reg, folders = old_pc(tmp_path)
    services = fake_services(old_pc=folders.base, registry=reg)
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=services, out=out.append)

    assert run("coletar", "aparencia") == 0
    assert any("[x] mouse" in x for x in out)
    assert run("aparencia", "desmarcar", "mouse") == 0
    assert "mouse" not in w.recipe().personal.groups
    assert run("appearance", "select", "nada") == 1
