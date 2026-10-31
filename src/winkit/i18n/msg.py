"""Mensagem estruturada: chave + parâmetros, traduzida só na borda (D-031)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

Param = str | int | float


class Msg(BaseModel):
    """Texto ainda não traduzido. Guardado no estado e no resumo; montado por ``render``."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    key: str
    params: dict[str, Param] = Field(default_factory=dict)


def msg(key: str, /, **params: Param) -> Msg:
    return Msg(key=key, params=params)


def legacy(text: str) -> Msg:
    """Texto pronto de versões antigas (estado v1) ou detalhe técnico sem tradução."""
    return Msg(key="legacy.text", params={"text": text})
