from __future__ import annotations

from datetime import UTC, datetime

from winkit.core.recipe.io import new_recipe
from winkit.core.regional import RegionalDefaults, input_locale_from, regional_from_values
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.locale import read_regional

NOW = datetime(2026, 10, 31, tzinfo=UTC)


def test_input_locale_uses_substitute_layout() -> None:
    assert input_locale_from("00000416", "00010416") == "0416:00010416"  # ABNT2
    assert input_locale_from("0000080a", None) == "080A:0000080A"
    assert input_locale_from("lixo", None) is None
    assert input_locale_from(None, None) is None


def test_invalid_values_are_dropped() -> None:
    r = regional_from_values(
        locale_name="es-MX",
        preload="0000080A",
        substitute=None,
        time_zone="Central Standard Time (Mexico)",
    )
    assert r == RegionalDefaults(
        user_locale="es-MX",
        input_locale="080A:0000080A",
        time_zone="Central Standard Time (Mexico)",
    )
    bad = regional_from_values(locale_name="!!", preload="x", substitute=None, time_zone="'; drop")
    assert bad == RegionalDefaults()


def test_new_recipe_takes_regional_defaults() -> None:
    plain = new_recipe(pendrive_id="12345678", username="Ana", now=NOW)
    assert plain.windows.user_locale == "pt-BR"
    r = new_recipe(
        pendrive_id="12345678",
        username="Ana",
        now=NOW,
        regional=RegionalDefaults(
            user_locale="en-US", input_locale="0409:00000409", time_zone="Pacific Standard Time"
        ),
    )
    assert (r.windows.user_locale, r.windows.system_locale) == ("en-US", "en-US")
    assert (
        r.windows.input_locale == "0409:00000409" and r.windows.time_zone == "Pacific Standard Time"
    )


def test_read_regional_from_registry() -> None:
    reg = FakeRegistry()
    reg.set("HKCU", r"Keyboard Layout\Preload", "1", "sz", "00000416")
    reg.set("HKCU", r"Keyboard Layout\Substitutes", "00000416", "sz", "00010416")
    reg.set("HKCU", r"Control Panel\International", "LocaleName", "sz", "pt-BR")
    reg.set(
        "HKLM",
        r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation",
        "TimeZoneKeyName",
        "sz",
        "E. South America Standard Time",
    )
    assert read_regional(reg) == RegionalDefaults(
        user_locale="pt-BR",
        input_locale="0416:00010416",
        time_zone="E. South America Standard Time",
    )
    assert read_regional(FakeRegistry()) == RegionalDefaults()
