"""Inventário de um PC para o relatório antes/depois (V2-19). Só o que é preciso comparar."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SnapApp(_Model):
    name: str
    version: str = ""
    publisher: str = ""
    winget_id: str | None = None


class SnapDevice(_Model):
    name: str
    hardware_ids: tuple[str, ...] = ()
    #: ``ConfigManagerErrorCode``: 0 = funcionando.
    code: int = 0


class Snapshot(_Model):
    schema_version: int = 1
    windows_build: int | None = None
    apps: list[SnapApp] = Field(default_factory=list)
    devices: list[SnapDevice] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)  # ids de features.yaml ligados
    fonts: list[str] = Field(default_factory=list)  # nomes completos das fontes do usuário
