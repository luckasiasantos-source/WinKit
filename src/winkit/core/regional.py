"""Padrões regionais do PC atual para a receita nova (D-030): formatos, teclado e fuso.

Puro: recebe os valores crus lidos do registro e devolve só o que for válido.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

_KLID = re.compile(r"^[0-9A-Fa-f]{8}$")
_LOCALE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
_TZ = re.compile(r"^[A-Za-z0-9 ().+\-]{2,64}$")


class RegionalDefaults(BaseModel):
    """Valores que a receita nova herda do PC atual. ``None`` = manter o padrão da receita."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    user_locale: str | None = None
    input_locale: str | None = None
    time_zone: str | None = None


def input_locale_from(preload: str | None, substitute: str | None) -> str | None:
    """``Preload\\1`` (KLID) + ``Substitutes`` → formato do autounattend ``0416:00010416``.

    O idioma vem dos 4 últimos dígitos do KLID de ``Preload``; o layout de teclado, do
    substituto quando existir (ex.: ABNT2 = 00010416).
    """
    if not preload or not _KLID.match(preload):
        return None
    layout = substitute if substitute and _KLID.match(substitute) else preload
    return f"{preload[-4:].upper()}:{layout.upper()}"


def regional_from_values(
    *,
    locale_name: str | None,
    preload: str | None,
    substitute: str | None,
    time_zone: str | None,
) -> RegionalDefaults:
    locale = locale_name if locale_name and _LOCALE.match(locale_name) else None
    tz = time_zone if time_zone and _TZ.match(time_zone) else None
    return RegionalDefaults(
        user_locale=locale, input_locale=input_locale_from(preload, substitute), time_zone=tz
    )
