from __future__ import annotations

from datetime import datetime

import pytest

from winkit.i18n.format import format_datetime, format_duration, format_size
from winkit.i18n.languages import as_language, normalize


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("pt-BR", "pt-BR"),
        ("pt-PT", "pt-BR"),
        ("pt", "pt-BR"),
        ("PT_br", "pt-BR"),
        ("es-MX", "es"),
        ("es-ES", "es"),
        ("es", "es"),
        ("es-419", "es"),
        ("en-US", "en-US"),
        ("en-GB", "en-US"),
        ("fr-FR", "en-US"),
        ("", "en-US"),
        (None, "en-US"),
    ],
)
def test_normalize(tag: str | None, expected: str) -> None:
    assert normalize(tag) == expected


def test_as_language_rejects_unknown() -> None:
    assert as_language("es") == "es"
    with pytest.raises(ValueError):
        as_language("fr-FR")


def test_sizes_per_language() -> None:
    assert format_size(1536, "pt-BR") == "1,5 KB"
    assert format_size(1536, "es") == "1,5 KB"
    assert format_size(1536, "en-US") == "1.5 KB"
    assert format_size(10, "en-US") == "10 B"
    assert format_size(3 * 1024**3, "en-US") == "3.0 GB"


def test_dates_and_durations() -> None:
    dt = datetime(2026, 10, 31, 9, 5)
    assert format_datetime(dt, "pt-BR") == "31/10/2026 09:05"
    assert format_datetime(dt, "en-US") == "10/31/2026 09:05"
    assert format_duration(None) == "—"
    assert format_duration(65) == "1 min 05 s"
    assert format_duration(3900) == "1 h 05 min"
