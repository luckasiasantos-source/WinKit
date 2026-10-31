"""Iniciar e barra de tarefas (V2-04): arquivos que o Windows 11 lê no perfil Default.

- Barra: ``LayoutModification.xml`` com ``CustomTaskbarLayoutCollection`` (``Replace``).
- Iniciar (modo lista): ``LayoutModification.json`` no formato da política ``ConfigureStartPins``.
- Iniciar (modo exato): cópia do ``start2.bin`` (só na mesma versão do Windows, H27).

O XML é montado com ``ElementTree`` (R-24). Os prefixos documentados pela Microsoft entram como
nomes e atributos ``xmlns:*`` literais, sem ``register_namespace`` (estado global — IN-015).
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

from winkit.core.recipe.models import PinRef

NS = {
    "xmlns": "http://schemas.microsoft.com/Start/2014/LayoutModification",
    "xmlns:defaultlayout": "http://schemas.microsoft.com/Start/2014/FullDefaultLayout",
    "xmlns:start": "http://schemas.microsoft.com/Start/2014/StartLayout",
    "xmlns:taskbar": "http://schemas.microsoft.com/Start/2014/TaskbarLayout",
}
START_HOST = "Microsoft.Windows.StartMenuExperienceHost_cw5n1h2txyewy"
#: Relativos à raiz do perfil.
SHELL_DIR = ("AppData", "Local", "Microsoft", "Windows", "Shell")
START2_DIR = ("AppData", "Local", "Packages", START_HOST, "LocalState")
TASKBAR_PINNED = r"Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"
START_MENU = r"Microsoft\Windows\Start Menu\Programs"


def taskbar_xml(pins: list[PinRef]) -> bytes:
    root = ET.Element("LayoutModificationTemplate", {**NS, "Version": "1"})
    coll = ET.SubElement(root, "CustomTaskbarLayoutCollection", {"PinListPlacement": "Replace"})
    layout = ET.SubElement(coll, "defaultlayout:TaskbarLayout")
    pin_list = ET.SubElement(layout, "taskbar:TaskbarPinList")
    for pin in pins:
        if not pin.selected:
            continue
        if pin.kind == "packaged_app":
            ET.SubElement(pin_list, "taskbar:UWA", {"AppUserModelID": pin.value})
        else:
            ET.SubElement(pin_list, "taskbar:DesktopApp", {"DesktopApplicationLinkPath": pin.value})
    ET.indent(root)
    data: bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return data + b"\n"


def start_json(pins: list[PinRef]) -> bytes:
    pinned = [
        {"packagedAppId": p.value} if p.kind == "packaged_app" else {"desktopAppLink": p.value}
        for p in pins
        if p.selected
    ]
    return (json.dumps({"pinnedList": pinned}, ensure_ascii=False, indent=2) + "\n").encode()
