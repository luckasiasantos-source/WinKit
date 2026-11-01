"""Opções que o Rufus gravou no pendrive (V3-07, H39). Leitor puro, sem Windows.

O Rufus põe as escolhas do diálogo "Windows User Experience" em arquivos de resposta. O WinKit
troca o ``autounattend.xml`` da raiz pelo dele (guardando o original); esta lista mostra o que o
Rufus fazia e se a receita do WinKit também faz.
"""

from __future__ import annotations

from dataclasses import dataclass

from winkit.core.recipe.models import Recipe

#: opção → trechos que a denunciam no XML (comandos ``reg add`` e elementos do unattend).
MARKERS: dict[str, tuple[str, ...]] = {
    "bypass_requirements": ("BypassTPMCheck", "BypassSecureBootCheck", "BypassRAMCheck"),
    "no_online_account": ("BypassNRO", "HideOnlineAccountScreens"),
    "local_account": ("<LocalAccount",),
    "no_data_collection": ("<ProtectYourPC>3<",),
    "no_bitlocker": ("PreventDeviceEncryption",),
    "regional": ("<UserLocale>", "<InputLocale>"),
}


@dataclass(frozen=True)
class RufusOption:
    id: str
    covered: bool  # a receita do WinKit também faz


def detect(xml_texts: list[str]) -> list[str]:
    text = "\n".join(xml_texts)
    return [opt for opt, needles in MARKERS.items() if any(n in text for n in needles)]


def compare(found: list[str], recipe: Recipe) -> list[RufusOption]:
    covered = {
        "bypass_requirements": recipe.target_windows.version == "11",
        "no_online_account": True,
        "local_account": True,
        "no_data_collection": True,
        "no_bitlocker": recipe.windows.prevent_device_encryption,
        "regional": True,
    }
    return [RufusOption(o, covered[o]) for o in found]
