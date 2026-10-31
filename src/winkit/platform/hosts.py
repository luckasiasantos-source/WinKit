"""O arquivo ``hosts`` do Windows (V2-16). As regras do bloco ficam em ``core/dns.py``."""

from __future__ import annotations

import sys
from pathlib import Path

from winkit.core.dns import with_block, without_block
from winkit.core.fsutil import atomic_write_bytes


def hosts_file(windows_dir: str) -> Path:
    base = Path(windows_dir) if sys.platform == "win32" else Path(windows_dir.replace("\\", "/"))
    return base / "System32" / "drivers" / "etc" / "hosts"


def read_hosts(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return b""


def write_block(path: Path, domains: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(path, with_block(read_hosts(path), domains))  # R-16


def remove_block(path: Path) -> bool:
    """Desfazer: tira o bloco do WinKit e mantém o resto. True se havia um bloco."""
    data, removed = without_block(read_hosts(path))
    if removed:
        atomic_write_bytes(path, data)
    return removed
