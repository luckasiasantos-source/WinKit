"""Aparência pessoal (V2-06, D-037): regras puras de captura e validação.

Cada valor do registro passa pelo catálogo (tipo, valores permitidos, padrão, tamanho). O que
não passa é descartado na captura e nunca chega ao Windows novo.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from winkit.core.catalog.models import PersonalGroup, PersonalValueSpec
from winkit.core.recipe.models import PersonalValue

#: Lê ``HKCU\\<chave>\\<valor>``; devolve ``None`` se não existe.
Reader = Callable[[str, str], object]

WALLPAPER_KEY = r"Control Panel\Desktop"
WALLPAPER_VALUE = "WallPaper"
JPEG = b"\xff\xd8\xff"
PNG = b"\x89PNG\r\n\x1a\n"
BMP = b"BM"


def value_id(spec: PersonalValueSpec) -> str:
    return f"{spec.key}\\{spec.value}"


def _data(spec: PersonalValueSpec, raw: object) -> int | str | None:
    """O dado no formato da receita, se o tipo bater (binário vira hexadecimal)."""
    if spec.type == "dword":
        ok = isinstance(raw, int) and not isinstance(raw, bool) and 0 <= raw <= 0xFFFFFFFF
        return raw if ok else None  # type: ignore[return-value]
    if spec.type == "binary":
        if isinstance(raw, bytes | bytearray):
            data = bytes(raw).hex()
        elif isinstance(raw, str) and re.fullmatch(r"[0-9a-fA-F]*", raw):
            data = raw.lower()
        else:
            return None
        return data if spec.length is None or len(data) == 2 * spec.length else None
    return raw if isinstance(raw, str) else None


def normalize(spec: PersonalValueSpec, raw: object) -> PersonalValue | None:
    """O valor lido no formato da receita, ou ``None`` se não passar na validação."""
    data = _data(spec, raw)
    if data is None:
        return None
    if spec.allowed is not None and data not in spec.allowed:
        return None
    if spec.pattern is not None and not re.fullmatch(spec.pattern, str(data)):
        return None
    return PersonalValue(type=spec.type, data=data)


def capture(
    groups: list[PersonalGroup], read: Reader
) -> tuple[dict[str, PersonalValue], list[str]]:
    """(valores válidos por id, ids descartados por não passarem na validação)."""
    values: dict[str, PersonalValue] = {}
    dropped: list[str] = []
    for g in groups:
        for spec in g.values:
            raw = read(spec.key, spec.value)
            if raw is None:
                continue
            ok = normalize(spec, raw)
            if ok is None:
                dropped.append(value_id(spec))
            else:
                values[value_id(spec)] = ok
    return values, dropped


def image_kind(data: bytes) -> str | None:
    """Extensão pela assinatura do arquivo (o ``TranscodedWallpaper`` não tem extensão)."""
    if data.startswith(JPEG):
        return "jpg"
    if data.startswith(PNG):
        return "png"
    if data.startswith(BMP):
        return "bmp"
    return None


def same(stored: object, wanted: PersonalValue) -> bool:
    if wanted.type == "binary" and isinstance(stored, bytes | bytearray):
        return bytes(stored).hex() == wanted.data
    return stored == wanted.data
