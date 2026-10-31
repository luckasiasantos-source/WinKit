from __future__ import annotations

import pytest

from winkit.core.isos import build_from_version, language_code, os_major_from_build


@pytest.mark.parametrize(
    ("v", "b"),
    [
        ("10.0.26100.1742", 26100),
        ("10.0.19045", 19045),
        ("10.0", None),
        ("", None),
        ("a.b.c", None),
    ],
)
def test_build_from_version(v: str, b: int | None) -> None:
    assert build_from_version(v) == b


def test_os_major() -> None:
    assert os_major_from_build(22000) == 11
    assert os_major_from_build(19045) == 10
    assert os_major_from_build(None) is None


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("pt-BR (Padrão)", "pt-BR"),
        ("en-US (Default)", "en-US"),
        ("pt-BR", "pt-BR"),
        ("zh-Hant-TW", "zh-Hant-TW"),
        ("(Padrão)", None),
    ],
)
def test_language_code(raw: str, code: str | None) -> None:
    assert language_code(raw) == code
