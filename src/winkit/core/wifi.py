"""Perfis de Wi-Fi exportados pelo Windows (V2-02, D-036).

Lidos e alterados como XML (esquema ``WLANProfile``), nunca pelo texto do ``netsh`` (R-13).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Literal

from pydantic import BaseModel, ConfigDict

from winkit.core.text import slugify

NS = "http://www.microsoft.com/networking/WLAN/profile/v1"
Security = Literal["open", "wpa2_personal", "wpa3_personal", "enterprise", "other"]
_ENTERPRISE = {"WPA", "WPA2", "WPA3", "WPA3ENT", "WPA3ENT192"}


class WifiProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    ssid: str
    security: Security
    has_key: bool


def _q(tag: str) -> str:
    return f"{{{NS}}}{tag}"


def _find(root: ET.Element, path: str) -> ET.Element | None:
    return root.find("/".join(_q(p) for p in path.split("/")))


def _ssid(root: ET.Element) -> str:
    name = _find(root, "SSIDConfig/SSID/name")
    if name is not None and name.text:
        return name.text
    hex_el = _find(root, "SSIDConfig/SSID/hex")
    if hex_el is not None and hex_el.text:
        try:
            return bytes.fromhex(hex_el.text).decode("utf-8", errors="replace")
        except ValueError:
            pass
    return ""


def parse_profile(data: bytes) -> WifiProfile:
    root = ET.fromstring(data)  # noqa: S314 — arquivo do próprio PC, exportado pelo Windows
    if root.tag != _q("WLANProfile"):
        raise ValueError("não é um perfil de Wi-Fi do Windows")
    name_el = _find(root, "name")
    name = name_el.text if name_el is not None and name_el.text else ""
    auth_el = _find(root, "MSM/security/authEncryption/authentication")
    onex_el = _find(root, "MSM/security/authEncryption/useOneX")
    auth = (auth_el.text or "").strip() if auth_el is not None else ""
    one_x = onex_el is not None and (onex_el.text or "").strip().lower() == "true"
    security: Security
    if one_x or auth.upper() in _ENTERPRISE:
        security = "enterprise"
    elif auth.lower() == "open":
        security = "open"
    elif auth.upper() in ("WPA2PSK", "WPAPSK"):
        security = "wpa2_personal"
    elif auth.upper() == "WPA3SAE":
        security = "wpa3_personal"
    else:
        security = "other"
    return WifiProfile(
        name=name,
        ssid=_ssid(root) or name,
        security=security,
        has_key=key_material(data) is not None,
    )


def key_material(data: bytes) -> str | None:
    root = ET.fromstring(data)  # noqa: S314
    el = _find(root, "MSM/security/sharedKey/keyMaterial")
    return el.text if el is not None and el.text else None


def strip_key(data: bytes) -> bytes:
    """Remove a senha (``sharedKey``): o Windows pede a senha ao conectar.

    Nunca usar ``ET.register_namespace``: o registro é global e mudaria o XML gerado
    depois no mesmo processo, inclusive o ``autounattend.xml`` (IN-015).
    """
    root = ET.fromstring(data)  # noqa: S314
    security = _find(root, "MSM/security")
    if security is not None:
        for el in list(security):
            if el.tag == _q("sharedKey"):
                security.remove(el)
    out: bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True, default_namespace=NS)
    return out


def network_id(profile: WifiProfile) -> str:
    """Id estável e seguro para nome de arquivo (R-05)."""
    import hashlib  # noqa: PLC0415

    digest = hashlib.sha256(profile.name.encode("utf-8")).hexdigest()[:6]
    return f"{slugify(profile.name, max_length=40)}-{digest}"
