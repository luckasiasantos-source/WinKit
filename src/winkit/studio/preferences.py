"""Preferências do Studio (idioma e tema), em ``%APPDATA%\\WinKit\\studio.json`` (D-030, D-042)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from winkit.core.fsutil import atomic_write_text
from winkit.i18n import LanguageChoice

ThemeChoice = Literal["auto", "light", "dark"]


class Preferences(BaseModel):
    model_config = ConfigDict(extra="ignore")
    language: LanguageChoice = "auto"
    theme: ThemeChoice = "auto"


def default_path() -> Path:
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / ".config"
    return root / "WinKit" / "studio.json"


def load(path: Path | None = None) -> Preferences:
    path = path or default_path()
    try:
        return Preferences.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, ValidationError):
        return Preferences()


def save(prefs: Preferences, path: Path | None = None) -> None:
    path = path or default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, prefs.model_dump_json(indent=2) + "\n")
