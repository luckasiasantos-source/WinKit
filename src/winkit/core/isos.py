"""Informações lidas de uma ISO do Windows (somente leitura — D-002)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

IsoArch = Literal["x86", "amd64", "arm", "arm64", "unknown"]

#: Valores de ``Architecture`` do ``Get-WindowsImage`` (enum ImageArchitecture do DISM).
DISM_ARCH: dict[int, IsoArch] = {0: "x86", 5: "arm", 9: "amd64", 12: "arm64"}

_LANG_RE = re.compile(r"^([a-z]{2,3}(?:-[A-Za-z0-9]{2,8})+)")


class IsoEdition(BaseModel):
    model_config = ConfigDict(frozen=True)
    index: int
    name: str


class IsoInfo(BaseModel):
    model_config = ConfigDict(frozen=True)
    #: Caminho dentro da partição do Ventoy, no formato do ``ventoy.json`` ("/pasta/x.iso").
    image: str
    size: int
    mtime_ns: int
    is_windows: bool
    os_major: int | None = None
    build: int | None = None
    architecture: IsoArch = "unknown"
    languages: tuple[str, ...] = ()
    default_language: str | None = None
    editions: tuple[IsoEdition, ...] = ()

    @property
    def name(self) -> str:
        return self.image.rsplit("/", 1)[-1]


def build_from_version(version: str) -> int | None:
    """``"10.0.26100.1742"`` → ``26100``."""
    parts = version.split(".")
    if len(parts) >= 3 and parts[2].isdigit():
        return int(parts[2])
    return None


def os_major_from_build(build: int | None) -> int | None:
    if build is None:
        return None
    return 11 if build >= 22000 else 10


def language_code(raw: str) -> str | None:
    """Extrai só o código de cultura (``"pt-BR (Padrão)"`` → ``"pt-BR"``) — R-13."""
    match = _LANG_RE.match(raw.strip())
    return match.group(1) if match else None


# ------------------------------------------------------------------ índice para o Agente (V2-08)
class IsoIndexEntry(BaseModel):
    """O que o Agente precisa saber de cada ISO para achar a fonte offline do .NET 3.5."""

    model_config = ConfigDict(frozen=True)
    image: str  # "/pasta/x.iso", relativo à raiz do pendrive
    build: int | None = None
    architecture: IsoArch = "unknown"
    languages: tuple[str, ...] = ()


class IsoIndex(BaseModel):
    model_config = ConfigDict(frozen=True)
    isos: tuple[IsoIndexEntry, ...] = ()


def iso_index(infos: list[IsoInfo]) -> IsoIndex:
    return IsoIndex(
        isos=tuple(
            IsoIndexEntry(
                image=i.image, build=i.build, architecture=i.architecture, languages=i.languages
            )
            for i in infos
            if i.is_windows
        )
    )


def pick_iso(
    index: IsoIndex, *, build: int | None, architecture: str, language: str | None
) -> IsoIndexEntry | None:
    """A ISO do mesmo build e arquitetura do Windows em execução; prefere o mesmo idioma.

    Sem o build não há como garantir que os arquivos batem: nenhuma ISO é escolhida.
    """
    if build is None:
        return None
    same = [i for i in index.isos if i.build == build and i.architecture == architecture]
    if language:
        lang = language.casefold()
        preferred = [i for i in same if lang in (x.casefold() for x in i.languages)]
        if preferred:
            return preferred[0]
    return same[0] if same else None
