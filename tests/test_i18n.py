from __future__ import annotations

import string

import pytest

from winkit.i18n import MESSAGES, t


def test_format_with_kwargs() -> None:
    assert t("paths.drive_missing", drive="D:") == "A unidade D: não existe neste PC."


def test_unknown_key_raises() -> None:
    with pytest.raises(KeyError):
        t("nao.existe")


@pytest.mark.parametrize("key", sorted(MESSAGES))
def test_every_message_is_a_valid_format_string(key: str) -> None:
    fields = [f for _, f, _, _ in string.Formatter().parse(MESSAGES[key]) if f]
    t(key, **dict.fromkeys(fields, "x"))
