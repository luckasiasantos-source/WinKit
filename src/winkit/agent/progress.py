"""Interface entre o Agente e a apresentação (sem Qt — R-35).

``NullUi`` é o comportamento do modo silencioso sem bandeja e dos testes. A interface Qt
(M9) implementa o mesmo protocolo em ``winkit.agent.ui``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from winkit.core.planner.models import PlannedStep
from winkit.core.summary import Summary


@dataclass(frozen=True)
class Choice:
    action: Literal["start", "postpone"]
    #: Para etapas com ``user_choice``: quais o usuário deixou marcadas. None = padrão da receita.
    selected: frozenset[str] | None = None
    computer_name: str | None = None


class AgentUi(Protocol):
    def choose(self, pending: list[PlannedStep], done_before_login: dict[str, int]) -> Choice: ...

    def progress(self, done: int, total: int, current: str) -> None: ...

    def waiting(self, reason: Literal["pendrive", "network", "winget"], active: bool) -> None: ...

    def notify(self, title: str, message: str) -> None: ...

    def ask_reboot(self) -> bool: ...

    def finished(self, summary: Summary, html: Path) -> None: ...


@dataclass
class NullUi:
    """Nada é exibido. Grava as chamadas para os testes."""

    events: list[tuple[str, object]] = field(default_factory=list)
    reboot_answer: bool = False
    choice: Choice = field(default_factory=lambda: Choice("start"))

    def choose(self, pending: list[PlannedStep], done_before_login: dict[str, int]) -> Choice:
        self.events.append(("choose", [s.id for s in pending]))
        return self.choice

    def progress(self, done: int, total: int, current: str) -> None:
        self.events.append(("progress", (done, total, current)))

    def waiting(self, reason: Literal["pendrive", "network", "winget"], active: bool) -> None:
        self.events.append(("waiting", (reason, active)))

    def notify(self, title: str, message: str) -> None:
        self.events.append(("notify", (title, message)))

    def ask_reboot(self) -> bool:
        self.events.append(("ask_reboot", None))
        return self.reboot_answer

    def finished(self, summary: Summary, html: Path) -> None:
        self.events.append(("finished", html))
