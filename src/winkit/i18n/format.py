"""Números, tamanhos, datas e durações por idioma, sem o módulo ``locale`` (D-030)."""

from __future__ import annotations

from datetime import datetime, timedelta

from winkit.i18n.core import current_language
from winkit.i18n.languages import Language


def _decimal(value: float, digits: int, lang: Language) -> str:
    text = f"{value:.{digits}f}"
    return text if lang == "en-US" else text.replace(".", ",")


def format_size(n: int, lang: Language | None = None) -> str:
    lang = lang or current_language()
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{_decimal(size, 1, lang)} {unit}"
        size /= 1024
    return f"{_decimal(size, 1, lang)} TB"  # pragma: no cover


def format_duration(seconds: float | None) -> str:
    """Forma curta igual nos três idiomas: "1 h 05 min", "3 min 07 s"."""
    if seconds is None:
        return "—"
    td = timedelta(seconds=round(seconds))
    hours, rem = divmod(td.seconds + td.days * 86400, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours} h {minutes:02d} min" if hours else f"{minutes} min {secs:02d} s"


def format_datetime(value: datetime, lang: Language | None = None) -> str:
    lang = lang or current_language()
    if lang == "en-US":
        return value.strftime("%m/%d/%Y %H:%M")
    return value.strftime("%d/%m/%Y %H:%M")
