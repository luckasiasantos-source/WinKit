"""Tradução: ``t``, ``tn`` e ``render`` no idioma atual do processo (R-03, D-030)."""

from __future__ import annotations

import importlib
import logging
import threading
from dataclasses import dataclass

from winkit.i18n.languages import BASE, Language
from winkit.i18n.msg import Msg

log = logging.getLogger("winkit.i18n")


@dataclass(frozen=True)
class Plural:
    """Formas de plural suficientes para pt, en e es: ``one`` só quando n == 1."""

    one: str
    other: str


Entry = str | Plural

_MODULES: dict[Language, str] = {
    "pt-BR": "winkit.i18n.messages.pt_br",
    "en-US": "winkit.i18n.messages.en_us",
    "es": "winkit.i18n.messages.es",
}
_lock = threading.Lock()
_current: Language = BASE
_cache: dict[Language, dict[str, Entry]] = {}
_warned: set[tuple[Language, str]] = set()


def messages_for(lang: Language) -> dict[str, Entry]:
    with _lock:
        if lang not in _cache:
            module = importlib.import_module(_MODULES[lang])
            _cache[lang] = module.MESSAGES
        return _cache[lang]


def set_language(lang: Language) -> None:
    global _current  # noqa: PLW0603 — idioma é estado do processo (D-030)
    with _lock:
        _current = lang


def current_language() -> Language:
    return _current


def _entry(key: str) -> Entry:
    lang = _current
    table = messages_for(lang)
    if key in table:
        return table[key]
    base = messages_for(BASE)
    if key not in base:
        raise KeyError(key)
    if (lang, key) not in _warned:
        _warned.add((lang, key))
        log.warning("texto sem tradução para %s: %s", lang, key)
    return base[key]


def t(key: str, /, **params: object) -> str:
    """Texto ``key`` no idioma atual. Chave inexistente é erro de programação."""
    entry = _entry(key)
    if isinstance(entry, Plural):
        raise TypeError(f"{key} tem plural; use tn()")
    return entry.format(**params) if params else entry


def tn(key: str, n: int, /, **params: object) -> str:
    """Texto com plural: ``tn("apps.count", 3)`` → "3 aplicativos"."""
    entry = _entry(key)
    if not isinstance(entry, Plural):
        raise TypeError(f"{key} não tem plural; use t()")
    template = entry.one if n == 1 else entry.other
    return template.format(n=n, **params)


def render(message: Msg | str | None) -> str:
    """Monta o texto de uma ``Msg``. Chave desconhecida (estado de outra versão) vira a chave."""
    if message is None:
        return ""
    if isinstance(message, str):
        return message
    try:
        entry = _entry(message.key)
    except KeyError:
        return message.key
    template = entry.other if isinstance(entry, Plural) else entry
    try:
        return template.format(**message.params)
    except (KeyError, IndexError, ValueError):
        return template
