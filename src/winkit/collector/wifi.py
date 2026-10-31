"""Coleta das redes Wi-Fi salvas no PC atual (V2-02, D-036)."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from winkit.core import layout
from winkit.core.errors import WinKitError
from winkit.core.fsutil import atomic_write_bytes
from winkit.core.recipe.models import Recipe, WifiNetwork
from winkit.core.secrets import SECRETS
from winkit.core.wifi import key_material, network_id, parse_profile, strip_key
from winkit.platform.wifi import WifiManager


def collect_wifi(wifi: WifiManager, root: Path, recipe: Recipe) -> list[WifiNetwork]:
    """Exporta os perfis, grava no pendrive e atualiza a receita. Devolve as redes novas."""
    tmp = Path(tempfile.mkdtemp(prefix="winkit-wifi-"))
    added: list[WifiNetwork] = []
    try:
        for exported in wifi.export_profiles(tmp):
            data = exported.read_bytes()
            try:
                prof = parse_profile(data)
            except ValueError:
                continue
            SECRETS.add(key_material(data))
            nid = network_id(prof)
            folder = layout.wifi_dir(recipe.meta.profile_id).removeprefix(layout.WINKIT + "/")
            rel = f"{folder}/{nid}.xml"
            current = next((n for n in recipe.wifi.networks if n.id == nid), None)
            keep_key = current.include_key if current is not None else True
            atomic_write_bytes(layout.payload(root, rel), data if keep_key else strip_key(data))
            if current is None:
                item = WifiNetwork(
                    id=nid,
                    ssid=prof.ssid,
                    security=prof.security,
                    include_key=prof.has_key,
                    selected=prof.security != "enterprise",
                    file=rel,
                )
                recipe.wifi.networks.append(item)
                added.append(item)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)  # a cópia com senhas não fica no disco
    return added


def set_include_key(root: Path, recipe: Recipe, network_id_: str, include: bool) -> bool:
    """Tirar a senha reescreve o arquivo sem ela. Devolvê-la exige ler as redes de novo."""
    item = next((n for n in recipe.wifi.networks if n.id == network_id_), None)
    if item is None:
        raise WinKitError(f"rede não encontrada: {network_id_}")
    path = layout.payload(root, item.file)
    if include:
        if not path.is_file() or key_material(path.read_bytes()) is None:
            return False
        item.include_key = True
        return True
    if path.is_file():
        atomic_write_bytes(path, strip_key(path.read_bytes()))
    item.include_key = False
    return True
