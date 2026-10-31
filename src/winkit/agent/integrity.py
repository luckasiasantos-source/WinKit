"""Verificação de integridade do conteúdo do pendrive antes de executar (R-22)."""

from __future__ import annotations

from pathlib import Path

from winkit.core import layout
from winkit.core.errors import IntegrityError
from winkit.core.manifest.manifest import Manifest, load_manifest, verify, verify_tree


def load_pendrive_manifest(root: Path) -> Manifest:
    path = root / layout.MANIFEST
    if not path.is_file():
        raise IntegrityError("manifesto.json ausente no pendrive (rode 'winkit construir')")
    return load_manifest(path.read_text(encoding="utf-8"))


def verify_payload(root: Path, rel_to_winkit: str, *, tree: bool) -> None:
    """Confere um arquivo (``tree=False``) ou uma pasta inteira (``tree=True``)."""
    manifest = load_pendrive_manifest(root)
    rel = f"{layout.WINKIT}/{rel_to_winkit}".rstrip("/")
    if tree:
        if not any(k.startswith(rel + "/") for k in manifest.files):
            raise IntegrityError(f"pasta fora do manifesto: {rel}")
        verify_tree(root, rel + "/", manifest)
    else:
        verify(root, rel, manifest)
