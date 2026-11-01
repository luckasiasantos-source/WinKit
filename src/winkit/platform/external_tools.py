"""Ventoy e Rufus: baixar da release oficial, conferir e abrir para a pessoa usar (V3-07, D-046).

Nada de terceiros vai no pacote do WinKit: os programas ficam em
``%LOCALAPPDATA%\\WinKit\\ferramentas\\<id>-<versão>\\`` e são abertos como estão.
"""

from __future__ import annotations

import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from winkit.core.catalog.models import DownloadSource
from winkit.core.errors import WinKitError
from winkit.platform import download as dl

API = "https://api.github.com/repos/{repo}/releases/latest"
_HEX = re.compile(r"\b[0-9a-fA-F]{64}\b")


@dataclass(frozen=True)
class Release:
    version: str
    asset_name: str
    url: str
    sha256: str | None


def find_sha256(text: str, asset_name: str) -> str | None:
    """Soma SHA-256 da linha que cita o arquivo (``sha256.txt`` ou o texto da release)."""
    for line in text.splitlines():
        if asset_name in line:
            match = _HEX.search(line)
            if match:
                return match.group(0).lower()
    return None


def latest_release(
    source: DownloadSource,
    *,
    get_json: Callable[[str], Any] = dl.get_json,
    get_text: Callable[[str], str] = dl.get_text,
) -> Release:
    data = get_json(API.format(repo=source.repo))
    version = str(data.get("tag_name", "")).lstrip("v")
    assets = data.get("assets", [])
    asset = next((a for a in assets if re.match(source.asset, a.get("name", ""))), None)
    if asset is None or not version:
        raise WinKitError(f"{source.name}: arquivo não encontrado na última release")
    sha: str | None = None
    if source.checksum_asset:
        sums = next((a for a in assets if re.match(source.checksum_asset, a.get("name", ""))), None)
        if sums is not None:
            sha = find_sha256(get_text(sums["browser_download_url"]), asset["name"])
    else:
        sha = find_sha256(str(data.get("body") or ""), asset["name"])
    return Release(version, asset["name"], asset["browser_download_url"], sha)


def fetch(
    source: DownloadSource,
    tools_dir: Path,
    *,
    release: Release,
    downloader: Callable[..., Path] = dl.download,
    progress: Callable[[dl.Progress], None] | None = None,
) -> Path:
    """Baixa (se ainda não tiver), confere e devolve o executável."""
    folder = tools_dir / f"{source.id}-{release.version}"
    file = downloader(
        release.url, folder / release.asset_name, sha256=release.sha256, progress=progress
    )
    if source.exe_in_zip is None:
        return file
    exe = folder / source.exe_in_zip.format(version=release.version)
    if not exe.is_file():
        with zipfile.ZipFile(file) as z:
            for member in z.namelist():  # nada fora da pasta (zip malicioso)
                target = (folder / member).resolve()
                if not target.is_relative_to(folder.resolve()):
                    raise WinKitError(f"zip com caminho inválido: {member}")
            z.extractall(folder)
    if not exe.is_file():
        raise WinKitError(f"{source.name}: executável não encontrado no pacote")
    return exe
