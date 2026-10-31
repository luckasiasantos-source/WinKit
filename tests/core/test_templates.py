from __future__ import annotations

import pytest

from winkit.core.errors import PathTemplateError
from winkit.core.paths import templates as tp

OLD_PC = {
    "USERPROFILE": r"C:\Users\Samuel",
    "APPDATA": r"C:\Users\Samuel\AppData\Roaming",
    "LOCALAPPDATA": r"C:\Users\Samuel\AppData\Local",
    "LOCALLOW": r"C:\Users\Samuel\AppData\LocalLow",
    "DOCUMENTS": r"C:\Users\Samuel\OneDrive\Documentos",
    "SAVEDGAMES": r"C:\Users\Samuel\Saved Games",
    "PROGRAMDATA": r"C:\ProgramData",
    "PROGRAMFILES": r"C:\Program Files",
    "PROGRAMFILESX86": r"C:\Program Files (x86)",
}
NEW_PC = {
    **tp.profile_folders(r"C:\Users\Lucas"),
    "PROGRAMDATA": r"C:\ProgramData",
    "PROGRAMFILES": r"C:\Program Files",
    "PROGRAMFILESX86": r"C:\Program Files (x86)",
    "PUBLIC": r"C:\Users\Public",
}


@pytest.mark.parametrize(
    ("literal", "template"),
    [
        (r"C:\Users\Samuel\AppData\Roaming\discord", r"{APPDATA}\discord"),
        ("c:\\users\\samuel\\appdata\\roaming\\Discord\\", r"{APPDATA}\Discord"),
        (r"C:/Users/Samuel/AppData/Local/Google/Chrome", r"{LOCALAPPDATA}\Google\Chrome"),
        (r"C:\Users\Samuel\AppData\LocalLow\Game", r"{LOCALLOW}\Game"),
        (r"C:\Users\Samuel\OneDrive\Documentos\My Games\X", r"{DOCUMENTS}\My Games\X"),
        (r"C:\Users\Samuel\.vscode\extensions", r"{USERPROFILE}\.vscode\extensions"),
        (r"C:\Users\Samuel\AppData\Roaming", "{APPDATA}"),
        (r"C:\Program Files (x86)\Steam\config", r"{PROGRAMFILESX86}\Steam\config"),
        (r"C:\Program Files\WinRAR\rarreg.key", r"{PROGRAMFILES}\WinRAR\rarreg.key"),
        (r"\\?\C:\ProgramData\App", r"{PROGRAMDATA}\App"),
    ],
)
def test_translation_uses_longest_prefix(literal: str, template: str) -> None:
    res = tp.to_template(literal, OLD_PC)
    assert res.template == template
    assert res.warning is None


def test_absolute_paths_get_warning() -> None:
    res = tp.to_template(r"D:\Jogos\Save", OLD_PC)
    assert res.template == r"{ABS:D:\Jogos\Save}"
    assert res.parsed.is_absolute and res.parsed.drive == "D:"
    assert res.warning and "D:" in res.warning


def test_windows_dir_is_refused() -> None:
    with pytest.raises(PathTemplateError, match="Windows"):
        tp.to_template(r"C:\Windows\System32\x", OLD_PC, windows_dir=r"C:\Windows")


@pytest.mark.parametrize("bad", ["", "   ", "relativo\\x", r"\\servidor\share\x"])
def test_bad_literals(bad: str) -> None:
    with pytest.raises(PathTemplateError):
        tp.to_template(bad, OLD_PC)


def test_traversal_is_normalized_away() -> None:
    res = tp.to_template(r"C:\Users\Samuel\AppData\Roaming\a\..\b", OLD_PC)
    assert res.template == r"{APPDATA}\b"


@pytest.mark.parametrize(
    ("template", "resolved"),
    [
        (r"{APPDATA}\discord", r"C:\Users\Lucas\AppData\Roaming\discord"),
        ("{APPDATA}", r"C:\Users\Lucas\AppData\Roaming"),
        (r"{DOCUMENTS}\My Games", r"C:\Users\Lucas\Documents\My Games"),
        (r"{SAVEDGAMES}\X", r"C:\Users\Lucas\Saved Games\X"),
        (r"{PROGRAMFILESX86}\Steam", r"C:\Program Files (x86)\Steam"),
        (r"{ABS:D:\Jogos\Save}", r"D:\Jogos\Save"),
        ("{APPDATA}/a/b", r"C:\Users\Lucas\AppData\Roaming\a\b"),
    ],
)
def test_resolution(template: str, resolved: str) -> None:
    assert tp.resolve(template, NEW_PC) == resolved


def test_roundtrip_between_machines() -> None:
    literal = r"C:\Users\Samuel\OneDrive\Documentos\Jogo\cfg.ini"
    template = tp.to_template(literal, OLD_PC).template
    assert tp.resolve(template, NEW_PC) == r"C:\Users\Lucas\Documents\Jogo\cfg.ini"


@pytest.mark.parametrize(
    "bad",
    [
        "APPDATA\\x",
        "{appdata}\\x",
        "{NOPE}\\x",
        r"{APPDATA}\..\..\Windows",
        r"{ABS:relativo}",
        r"{APPDATA:C:\x}",
    ],
)
def test_parse_rejects(bad: str) -> None:
    with pytest.raises(PathTemplateError):
        tp.parse(bad)


def test_abs_traversal_is_normalized() -> None:
    assert tp.parse(r"{ABS:D:\a\..\..\b}").absolute == r"D:\b"


def test_parse_flags() -> None:
    assert tp.parse(r"{APPDATA}\x").is_profile
    assert not tp.parse(r"{PROGRAMDATA}\x").is_profile
    assert tp.parse(r"{PROGRAMDATA}\x").drive is None


def test_resolve_unknown_folder() -> None:
    with pytest.raises(PathTemplateError):
        tp.resolve(r"{PUBLIC}\x", {"APPDATA": r"C:\x"})


def test_default_profile_and_retarget() -> None:
    folders = tp.profile_folders(r"C:\Users\Default")
    assert folders["APPDATA"] == r"C:\Users\Default\AppData\Roaming"
    assert folders["USERPROFILE"] == r"C:\Users\Default"
    mixed = tp.retarget(NEW_PC, r"C:\Users\Default")
    assert mixed["PROGRAMFILES"] == r"C:\Program Files"
    assert mixed["LOCALAPPDATA"] == r"C:\Users\Default\AppData\Local"


def test_normalize() -> None:
    assert tp.normalize("C:\\") == "C:\\"
    assert tp.normalize(r"C:\a\b\\") == r"C:\a\b"


def test_abs_with_suffix_is_a_path_inside_the_folder() -> None:  # IN-009
    parsed = tp.parse(r"{ABS:D:\Apps\Tool}\tool.exe")
    assert parsed.absolute == r"D:\Apps\Tool\tool.exe" and parsed.drive == "D:"
    assert tp.resolve(r"{ABS:D:\Apps\Tool}\bin\x.exe", {}) == r"D:\Apps\Tool\bin\x.exe"
