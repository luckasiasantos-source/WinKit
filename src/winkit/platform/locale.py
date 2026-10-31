"""Idioma e padrões regionais do Windows atual, por API e registro (R-13, D-030)."""

from __future__ import annotations

import ctypes
import os
import sys

from winkit.core.regional import RegionalDefaults, regional_from_values
from winkit.i18n import Language, normalize
from winkit.platform.registry import Registry

_LOCALE_NAME_MAX_LENGTH = 85


def ui_language_tag() -> str | None:
    """Etiqueta BCP-47 do idioma de exibição (``pt-BR``, ``es-MX``…). ``None`` fora do Windows."""
    forced = os.environ.get("WINKIT_LANG")
    if forced:
        return forced
    if sys.platform != "win32":
        return None
    kernel32 = ctypes.windll.kernel32
    langid = int(kernel32.GetUserDefaultUILanguage())
    buf = ctypes.create_unicode_buffer(_LOCALE_NAME_MAX_LENGTH)
    if kernel32.LCIDToLocaleName(langid, buf, _LOCALE_NAME_MAX_LENGTH, 0) <= 0:
        return None
    return str(buf.value) or None


def detect_language() -> Language:
    """Idioma suportado mais próximo do Windows; fora dele (testes, Linux): pt-BR."""
    tag = ui_language_tag()
    if tag is None:
        return "pt-BR"
    return normalize(tag)


def read_regional(registry: Registry) -> RegionalDefaults:
    """Formatos, teclado e fuso do usuário atual, pelo registro (nunca por texto, R-13)."""
    preload = registry.get("HKCU", r"Keyboard Layout\Preload", "1")
    substitute = (
        registry.get("HKCU", r"Keyboard Layout\Substitutes", str(preload)) if preload else None
    )
    return regional_from_values(
        locale_name=registry.get("HKCU", r"Control Panel\International", "LocaleName"),
        preload=str(preload) if preload else None,
        substitute=str(substitute) if substitute else None,
        time_zone=registry.get(
            "HKLM", r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation", "TimeZoneKeyName"
        ),
    )
