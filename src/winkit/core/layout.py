"""Layout fixo do pendrive (PLANO.md §5) e o arquivo marcador.

Caminhos relativos à raiz da partição de dados do Ventoy, sempre com ``/``.
Caminhos dentro da receita são relativos a ``WinKit/``.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from winkit.core.errors import PendriveError

WINKIT = "WinKit"
MARKER = f"{WINKIT}/winkit.marker"
MANIFEST = f"{WINKIT}/manifesto.json"
AGENT_DIR = f"{WINKIT}/Agent"
AGENT_BIN_DIR = f"{AGENT_DIR}/winkit-agent"
AGENT_EXE_NAME = "winkit-agent.exe"
BOOTSTRAP = f"{AGENT_DIR}/bootstrap.ps1"
AGENT_VERSION = f"{AGENT_DIR}/VERSION"
APPS = f"{WINKIT}/Apps"
DRIVERS = f"{WINKIT}/Drivers"
PROFILES = f"{WINKIT}/Perfis"
LOGS = f"{WINKIT}/Logs"
VENTOY_DIR = "ventoy"
VENTOY_JSON = f"{VENTOY_DIR}/ventoy.json"
VENTOY_BACKUP = f"{VENTOY_DIR}/ventoy.json.winkit-bak"
SCRIPT_DIR = f"{VENTOY_DIR}/script"
#: Subpastas de ``root`` cobertas pelo manifesto (hash verificado antes de executar — R-22).
MANIFEST_SUBDIRS = (AGENT_DIR, APPS, DRIVERS)


def profile_dir(profile_id: str) -> str:
    return f"{PROFILES}/{profile_id}"


def recipe_file(profile_id: str) -> str:
    return f"{profile_dir(profile_id)}/receita.json"


def backups_dir(profile_id: str) -> str:
    return f"{profile_dir(profile_id)}/Backups"


def wifi_dir(profile_id: str) -> str:
    """Perfis de Wi-Fi exportados (contêm a senha quando levada — D-036)."""
    return f"{profile_dir(profile_id)}/Wifi"


def payload(root: Path, rel_to_winkit: str) -> Path:
    """Caminho absoluto de um item da receita (relativo a ``WinKit/``)."""
    return root / WINKIT / rel_to_winkit


class Marker(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pendrive_id: str
    winkit_version: str
    created_at: datetime


def new_marker(version: str, now: datetime) -> Marker:
    return Marker(pendrive_id=str(uuid.uuid4()), winkit_version=version, created_at=now)


def dump_marker(marker: Marker) -> str:
    return marker.model_dump_json(indent=2) + "\n"


def load_marker(text: str) -> Marker:
    try:
        return Marker.model_validate(json.loads(text))
    except (ValueError, ValidationError) as exc:
        raise PendriveError(f"marcador WinKit corrompido: {exc}") from exc


def read_marker(root: Path) -> Marker | None:
    path = root / MARKER
    if not path.is_file():
        return None
    return load_marker(path.read_text(encoding="utf-8-sig"))
