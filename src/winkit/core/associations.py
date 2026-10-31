"""Apps padrão (V2-05): ler e filtrar o XML do ``dism /Export-DefaultAppAssociations``.

Função pura. O XML não tem namespace; é gerado de novo com ``ElementTree`` (R-24), sem tocar
no registro global de prefixos (IN-015).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from winkit.core.catalog.models import AssociationGroup


@dataclass(frozen=True)
class Association:
    identifier: str  # ".pdf" ou "http"
    prog_id: str
    application: str


class AssociationsError(ValueError):
    pass


def parse(data: bytes) -> list[Association]:
    try:
        root = ET.fromstring(data)  # noqa: S314 — arquivo local gerado pelo dism
    except ET.ParseError as exc:
        raise AssociationsError(f"XML de associações inválido: {exc}") from exc
    if root.tag != "DefaultAssociations":
        raise AssociationsError("não é um arquivo de associações do Windows")
    out = []
    for node in root.iter("Association"):
        ident = (node.get("Identifier") or "").strip()
        prog = (node.get("ProgId") or "").strip()
        if ident and prog:
            out.append(
                Association(ident.lower(), prog, (node.get("ApplicationName") or "").strip())
            )
    return out


def identifiers(groups: list[AssociationGroup], chosen: list[str]) -> set[str]:
    return {i for g in groups if g.id in chosen for i in g.identifiers}


def filtered_xml(items: list[Association], keep: set[str]) -> bytes:
    root = ET.Element("DefaultAssociations")
    for a in sorted(items, key=lambda x: x.identifier):
        if a.identifier in keep:
            ET.SubElement(
                root,
                "Association",
                {"Identifier": a.identifier, "ProgId": a.prog_id, "ApplicationName": a.application},
            )
    ET.indent(root)
    data: bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return data + b"\n"


def summary(items: list[Association], group: AssociationGroup) -> str | None:
    """Nome do app atual do grupo (o mais frequente entre os identificadores do grupo)."""
    names = [a.application or a.prog_id for a in items if a.identifier in group.identifiers]
    if not names:
        return None
    return max(sorted(set(names)), key=names.count)


def user_choice_key(identifier: str) -> str:
    """Onde o Windows guarda a escolha do usuário para uma extensão ou protocolo."""
    explorer = r"Software\Microsoft\Windows\CurrentVersion\Explorer"
    if identifier.startswith("."):
        return rf"{explorer}\FileExts\{identifier}\UserChoice"
    shell = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations"
    return rf"{shell}\{identifier}\UserChoice"
