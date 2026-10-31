"""Mesclagem do ``ventoy.json`` (PLANO.md §8.3).

Regras: nunca descartar chaves de outros plugins; nunca tocar em entradas de terceiros
(a não ser para acrescentar nosso modelo à lista de uma entrada que já aponta para a
mesma ISO); entradas do WinKit são reconhecidas pelo prefixo do modelo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from winkit.core.errors import VentoyConfigError

TEMPLATE_PREFIX = "/ventoy/script/winkit-"


@dataclass(frozen=True)
class AutoInstallEntry:
    image: str  # "/Windows11.iso"
    template: str  # "/ventoy/script/winkit-padrao-pt-BR-amd64.xml"


def _templates(entry: dict[str, Any]) -> list[str]:
    tpl = entry.get("template", [])
    if isinstance(tpl, str):
        return [tpl]
    if isinstance(tpl, list):
        return [x for x in tpl if isinstance(x, str)]
    return []


def _is_winkit(template: str) -> bool:
    return template.startswith(TEMPLATE_PREFIX)


def parse_config(text: str | None) -> dict[str, Any]:
    if text is None or not text.strip():
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise VentoyConfigError(f"linha {exc.lineno}, coluna {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise VentoyConfigError("o arquivo deve conter um objeto JSON")
    auto = data.get("auto_install")
    if auto is not None and not isinstance(auto, list):
        raise VentoyConfigError('"auto_install" deve ser uma lista')
    return data


def merge_auto_install(
    text: str | None,
    entries: list[AutoInstallEntry],
    *,
    autosel: int,
    timeout: int,
    profile_id: str,
) -> str:
    """Devolve o novo conteúdo do ``ventoy.json`` com as entradas do WinKit atualizadas.

    Entradas deste perfil que não estão em ``entries`` (ISO removida do pendrive) são
    retiradas; entradas de outros perfis do WinKit são preservadas.
    """
    data = parse_config(text)
    auto: list[Any] = list(data.get("auto_install") or [])
    ours_prefix = f"{TEMPLATE_PREFIX}{profile_id}-"
    wanted = {e.image: e.template for e in entries}

    new_auto: list[Any] = []
    handled: set[str] = set()
    for item in auto:
        if not isinstance(item, dict):
            new_auto.append(item)
            continue
        image = item.get("image")
        templates = _templates(item)
        others = [tp for tp in templates if not tp.startswith(ours_prefix)]
        if image in wanted and image not in handled:
            handled.add(image)
            if all(_is_winkit(tp) for tp in others):
                # entrada nossa (deste ou de outro perfil): reescreve mantendo outros perfis
                new_auto.append(_entry(image, [wanted[image], *others], autosel, timeout))
            else:
                # entrada de terceiro para a mesma ISO: só acrescenta nosso modelo
                merged = dict(item)
                merged["template"] = [*others, wanted[image]]
                new_auto.append(merged)
            continue
        if templates and len(others) != len(templates):
            # tinha modelo deste perfil, mas a ISO não está mais na lista
            if others:
                kept = dict(item)
                kept["template"] = others if len(others) > 1 else others[0]
                new_auto.append(kept)
            continue
        new_auto.append(item)

    for e in entries:
        if e.image not in handled:
            new_auto.append(_entry(e.image, [e.template], autosel, timeout))
            handled.add(e.image)

    if new_auto:
        data["auto_install"] = new_auto
    else:
        data.pop("auto_install", None)
    return json.dumps(data, ensure_ascii=False, indent=4) + "\n"


def _entry(image: str, templates: list[str], autosel: int, timeout: int) -> dict[str, Any]:
    return {"image": image, "template": templates, "autosel": autosel, "timeout": timeout}


def winkit_entries(text: str | None) -> list[AutoInstallEntry]:
    """Entradas do WinKit presentes no arquivo (para validação)."""
    out: list[AutoInstallEntry] = []
    for item in parse_config(text).get("auto_install") or []:
        if isinstance(item, dict) and isinstance(item.get("image"), str):
            out.extend(
                AutoInstallEntry(item["image"], tp) for tp in _templates(item) if _is_winkit(tp)
            )
    return out
