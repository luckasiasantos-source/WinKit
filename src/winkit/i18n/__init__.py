"""Textos exibidos ao usuário em pt-BR, en-US e es (R-03, D-030)."""

from winkit.i18n.core import Plural, current_language, messages_for, render, set_language, t, tn
from winkit.i18n.languages import (
    BASE,
    CHOICES,
    SUPPORTED,
    Language,
    LanguageChoice,
    normalize,
)
from winkit.i18n.msg import Msg, legacy, msg

__all__ = [
    "BASE",
    "CHOICES",
    "SUPPORTED",
    "Language",
    "LanguageChoice",
    "Msg",
    "Plural",
    "current_language",
    "legacy",
    "messages_for",
    "msg",
    "normalize",
    "render",
    "set_language",
    "t",
    "tn",
]
