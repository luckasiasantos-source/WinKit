"""Idiomas suportados e normalização de etiquetas BCP-47 (D-030)."""

from __future__ import annotations

from typing import Literal, cast

Language = Literal["pt-BR", "en-US", "es"]
SUPPORTED: tuple[Language, ...] = ("pt-BR", "en-US", "es")
BASE: Language = "pt-BR"
#: Escolha do usuário: um idioma ou "auto" (detectar).
LanguageChoice = Literal["auto", "pt-BR", "en-US", "es"]
CHOICES: tuple[LanguageChoice, ...] = ("auto", "pt-BR", "en-US", "es")


def normalize(tag: str | None) -> Language:
    """``pt-PT``/``pt`` → pt-BR, ``es-*`` → es, ``en-*`` e qualquer outro → en-US."""
    if not tag:
        return "en-US"
    lower = tag.strip().replace("_", "-").lower()
    if lower in ("pt-br", "pt") or lower.startswith("pt-"):
        return "pt-BR"
    if lower == "es" or lower.startswith("es-"):
        return "es"
    return "en-US"


def is_language(value: str) -> bool:
    return value in SUPPORTED


def as_language(value: str) -> Language:
    if not is_language(value):
        raise ValueError(f"idioma não suportado: {value}")
    return cast(Language, value)
