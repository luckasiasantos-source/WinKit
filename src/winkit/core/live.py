"""Prévia do modo "aplicar neste PC" (D-033, R-54): o que cada etapa faria, sem fazer nada."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from winkit.core.text import Msg

PreviewStatus = Literal["already_done", "will_change", "not_applicable"]


class PreviewItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    step_id: str
    kind: str
    title: str
    status: PreviewStatus
    changes: tuple[Msg, ...] = ()
    warnings: tuple[Msg, ...] = ()


class LivePreview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[PreviewItem, ...] = Field(default_factory=tuple)
    #: Etapas fora do plano por não serem seguras no modo ao vivo (R-54).
    not_live_safe: tuple[str, ...] = ()

    def count(self, status: PreviewStatus) -> int:
        return sum(1 for i in self.items if i.status == status)
