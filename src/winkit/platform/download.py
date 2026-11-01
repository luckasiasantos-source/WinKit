"""Download HTTP com progresso, pausa, retomada e conferência de SHA-256 (V3-07, V3-08; R-61).

Só biblioteca padrão. O arquivo é baixado em ``<destino>.part``; ao pausar ou cair, a próxima
chamada continua de onde parou (cabeçalho ``Range``). Só vira ``<destino>`` depois de conferido.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from winkit import __version__
from winkit.core.errors import WinKitError

CHUNK = 1024 * 1024
USER_AGENT = f"WinKit/{__version__}"


@dataclass(frozen=True)
class Progress:
    done: int
    total: int | None
    speed: float  # bytes por segundo (média dos últimos segundos)

    @property
    def fraction(self) -> float | None:
        return self.done / self.total if self.total else None

    @property
    def eta(self) -> float | None:
        if not self.total or self.speed <= 0:
            return None
        return (self.total - self.done) / self.speed


class DownloadPaused(WinKitError):  # noqa: N818 — é um estado, não um erro de verdade
    """Parado a pedido; o ``.part`` fica para continuar depois."""


Opener = Callable[[urllib.request.Request, float], Any]


def _open(req: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310 — URLs do catálogo (R-61)


def get_json(url: str, *, opener: Opener = _open, timeout: float = 30) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    with opener(req, timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_text(url: str, *, opener: Opener = _open, timeout: float = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    with opener(req, timeout) as resp:
        return str(resp.read().decode("utf-8", errors="replace"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(CHUNK):
            h.update(block)
    return h.hexdigest()


def download(
    url: str,
    dest: Path,
    *,
    sha256: str | None = None,
    progress: Callable[[Progress], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    opener: Opener = _open,
    timeout: float = 60,
    clock: Callable[[], float] = time.monotonic,
) -> Path:
    if dest.is_file() and (sha256 is None or sha256_file(dest).lower() == sha256.lower()):
        return dest
    part = dest.with_name(dest.name + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    start = part.stat().st_size if part.is_file() else 0
    headers = {"User-Agent": USER_AGENT}
    if start:
        headers["Range"] = f"bytes={start}-"
    req = urllib.request.Request(url, headers=headers)  # noqa: S310
    with opener(req, timeout) as resp:
        if start and getattr(resp, "status", 200) != 206:  # o servidor ignorou o Range
            start = 0
        length = resp.headers.get("Content-Length")
        total = start + int(length) if length else None
        done = start
        window: list[tuple[float, int]] = [(clock(), done)]
        with part.open("ab" if start else "wb") as f:
            while block := resp.read(CHUNK):
                f.write(block)
                done += len(block)
                now = clock()
                window.append((now, done))
                while len(window) > 2 and now - window[0][0] > 5:  # média dos últimos 5 s
                    window.pop(0)
                span = now - window[0][0]
                speed = (done - window[0][1]) / span if span > 0 else 0.0
                if progress is not None:
                    progress(Progress(done, total, speed))
                if should_stop is not None and should_stop():
                    raise DownloadPaused(str(part))
    if total is not None and done < total:
        raise WinKitError(f"download incompleto ({done} de {total} bytes); tente continuar")
    if sha256 is not None and sha256_file(part).lower() != sha256.lower():
        part.unlink()
        raise WinKitError(f"o arquivo baixado não confere (SHA-256): {dest.name}")
    part.replace(dest)
    return dest
