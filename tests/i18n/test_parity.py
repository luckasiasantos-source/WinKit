"""R-51: as três tabelas têm as mesmas chaves, marcadores e formas de plural."""

from __future__ import annotations

import string

import pytest

from winkit.i18n import SUPPORTED, Plural, messages_for
from winkit.i18n.core import Entry

BASE = messages_for("pt-BR")
OTHERS = [lang for lang in SUPPORTED if lang != "pt-BR"]


def _fields(text: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


def _all_fields(entry: Entry) -> set[str]:
    if isinstance(entry, Plural):
        return _fields(entry.one) | _fields(entry.other)
    return _fields(entry)


@pytest.mark.parametrize("lang", OTHERS)
def test_same_keys(lang: str) -> None:
    table = messages_for(lang)  # type: ignore[arg-type]
    assert sorted(set(BASE) - set(table)) == [], "faltam traduções"
    assert sorted(set(table) - set(BASE)) == [], "chaves que não existem em pt-BR"


@pytest.mark.parametrize("lang", OTHERS)
def test_same_placeholders_and_kind(lang: str) -> None:
    table = messages_for(lang)  # type: ignore[arg-type]
    problems = []
    for key, entry in BASE.items():
        other = table.get(key)
        if other is None:
            continue
        if isinstance(entry, Plural) != isinstance(other, Plural):
            problems.append(f"{key}: plural em um idioma e não no outro")
        elif _all_fields(entry) != _all_fields(other):
            problems.append(f"{key}: {_all_fields(entry)} != {_all_fields(other)}")
    assert problems == []


@pytest.mark.parametrize("lang", SUPPORTED)
def test_every_entry_formats(lang: str) -> None:
    for key, entry in messages_for(lang).items():
        texts = [entry.one, entry.other] if isinstance(entry, Plural) else [entry]
        for text in texts:
            fields = _fields(text)
            text.format(**dict.fromkeys(fields, "x"))  # não pode lançar
            assert key


#: Textos que coincidem de verdade com o português (nomes, siglas e palavras iguais).
SAME_AS_BASE: dict[str, set[str]] = {
    "en-US": {
        "plan.driver",
        "studio.pendrive.iso_detail",
        "studio.apps.src_winget",
        "cli.backup_added",
    },
    "es": {
        "validate.warnings",
        "ui.agent.progress_title",
        "plan.tweak",
        "plan.backup",
        "plan.app",
        "studio.keywords.pendrive",
        "studio.keywords.apps",
        "studio.backups.recommended",
        "cli.iso_ignored",
        "collect.portable_name",
        "restore.description_before",
        "studio.dns.custom",
        "step.network_drive.mapped",
        "studio.drives.letter",
        "step.env.set",
        "studio.presets.confirm_title",
        "studio.fonts.origin_machine",
    },
}
ALWAYS_SAME = {
    "legacy.text",
    "app.name",
    "plan.windows_update",
    "agent.progress",
    "agent.tray_tip",
    "summary.phase_time",
    "studio.window_title",
    "studio.live.kind.windows_update",
    "plan.wifi",
    "studio.wifi.security.enterprise",
    "summary.backup_warning",
    "cli.dns_servers",
    "cli.env_path_item",
    "preset.dns",
}


@pytest.mark.parametrize("lang", OTHERS)
def test_translated_not_identical(lang: str) -> None:
    """Valor igual ao português costuma ser esquecimento; exceções ficam listadas acima."""
    table = messages_for(lang)  # type: ignore[arg-type]
    allowed = ALWAYS_SAME | SAME_AS_BASE[lang]
    same = [
        k
        for k, v in BASE.items()
        if k not in allowed and not isinstance(v, Plural) and table.get(k) == v and len(v) > 12
    ]
    assert same == []
