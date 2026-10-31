"""Tradução dos textos dos catálogos (D-030): a base fica em pt-BR, as outras línguas por cima.

Função pura: recebe os catálogos e a tabela de tradução e devolve cópias com os textos trocados.
Itens sem tradução continuam em português (o teste de completude impede que isso aconteça).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from winkit.core.catalog.models import Catalogs


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TweakText(_Model):
    title: str
    description: str


class BloatText(_Model):
    name: str
    #: Tradução de ``side_effect`` (itens "cuidado") ou de ``reason`` (itens bloqueados).
    text: str | None = None


class LabelText(_Model):
    label: str


class WhatText(_Model):
    what: str


class FeatureText(_Model):
    name: str
    description: str


class CatalogTranslation(_Model):
    tweaks: dict[str, TweakText] = Field(default_factory=dict)
    bloatware: dict[str, BloatText] = Field(default_factory=dict)
    driver_classes: dict[str, LabelText] = Field(default_factory=dict)
    dpapi_patterns: dict[str, WhatText] = Field(default_factory=dict)
    features: dict[str, FeatureText] = Field(default_factory=dict)


def localize(catalogs: Catalogs, tr: CatalogTranslation) -> Catalogs:
    tweaks = [
        tw.model_copy(update=tr.tweaks[tw.id].model_dump()) if tw.id in tr.tweaks else tw
        for tw in catalogs.tweaks
    ]
    bloatware = []
    for b in catalogs.bloatware:
        text = tr.bloatware.get(b.id)
        if text is None:
            bloatware.append(b)
            continue
        update: dict[str, str] = {"name": text.name}
        if text.text and b.side_effect:
            update["side_effect"] = text.text
        elif text.text and b.reason:
            update["reason"] = text.text
        bloatware.append(b.model_copy(update=update))
    classes = [
        d.model_copy(update={"label": tr.driver_classes[d.name].label})
        if d.name in tr.driver_classes
        else d
        for d in catalogs.driver_classes
    ]
    patterns = [
        p.model_copy(update={"what": tr.dpapi_patterns[p.id].what})
        if p.id in tr.dpapi_patterns
        else p
        for p in catalogs.dpapi_patterns
    ]
    features = [
        f.model_copy(update=tr.features[f.id].model_dump()) if f.id in tr.features else f
        for f in catalogs.features
    ]
    return catalogs.model_copy(
        update={
            "features": features,
            "tweaks": tweaks,
            "bloatware": bloatware,
            "driver_classes": classes,
            "dpapi_patterns": patterns,
        }
    )


def missing_translations(catalogs: Catalogs, tr: CatalogTranslation) -> list[str]:
    """Itens do catálogo base sem tradução (completude, R-51)."""
    out = [f"tweaks.{t.id}" for t in catalogs.tweaks if t.id not in tr.tweaks]
    for b in catalogs.bloatware:
        text = tr.bloatware.get(b.id)
        if text is None:
            out.append(f"bloatware.{b.id}")
        elif (b.side_effect or b.reason) and not text.text:
            out.append(f"bloatware.{b.id}.text")
    out += [
        f"driver_classes.{d.name}"
        for d in catalogs.driver_classes
        if d.name not in tr.driver_classes
    ]
    out += [
        f"dpapi_patterns.{p.id}" for p in catalogs.dpapi_patterns if p.id not in tr.dpapi_patterns
    ]
    out += [f"features.{f.id}" for f in catalogs.features if f.id not in tr.features]
    return out


def orphan_translations(catalogs: Catalogs, tr: CatalogTranslation) -> list[str]:
    """Traduções que apontam para itens que não existem mais."""
    out = [f"tweaks.{k}" for k in tr.tweaks if catalogs.tweak(k) is None]
    out += [f"bloatware.{k}" for k in tr.bloatware if catalogs.bloat(k) is None]
    names = {d.name for d in catalogs.driver_classes}
    out += [f"driver_classes.{k}" for k in tr.driver_classes if k not in names]
    ids = {p.id for p in catalogs.dpapi_patterns}
    out += [f"dpapi_patterns.{k}" for k in tr.dpapi_patterns if k not in ids]
    out += [f"features.{k}" for k in tr.features if catalogs.feature(k) is None]
    return out
