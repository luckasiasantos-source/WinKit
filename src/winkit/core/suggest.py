"""Assistente "o que levar" (V2-20): pontuação e ordenação puras e determinísticas.

Frequência e recência de uso (UserAssist) pesam mais; tamanho entra com teto, para não
favorecer só o que é grande.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from winkit.i18n.msg import Msg

SuggestionKind = Literal["app", "config", "save", "folder", "other"]
KIND_ORDER: dict[str, int] = {"app": 0, "config": 1, "save": 2, "folder": 3, "other": 4}
MAX_COUNT = 200
RECENT_DAYS = 30
SIZE_CAP = 5 * 1024**3


@dataclass(frozen=True)
class Suggestion:
    id: str  # estável: "app:Mozilla.Firefox", "save:hades"…
    kind: SuggestionKind
    title: str
    reason: Msg
    score: float
    #: O que "Adicionar" faz (winget_id, template…); só dados, nada é executado.
    payload: dict[str, str] = field(default_factory=dict)


def usage_score(count: int, last_used: datetime | None, now: datetime) -> float:
    freq = min(count, MAX_COUNT) / MAX_COUNT * 60
    if last_used is None:
        return freq
    days = max(0, (now - last_used).days)
    return freq + max(0, RECENT_DAYS - days) / RECENT_DAYS * 40


def size_score(size: int) -> float:
    return min(max(size, 0), SIZE_CAP) / SIZE_CAP * 50


def rank(items: list[Suggestion], dismissed: list[str]) -> list[Suggestion]:
    ignored = set(dismissed)
    kept = [s for s in items if s.id not in ignored]
    return sorted(kept, key=lambda s: (KIND_ORDER[s.kind], -round(s.score, 3), s.title.casefold()))
