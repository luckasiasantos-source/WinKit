"""Download com retomada e conferência (V3-07/08) e ferramentas externas (D-046, R-61)."""

from __future__ import annotations

import hashlib
import io
import threading
import zipfile
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from winkit.core.catalog.loader import default_catalogs
from winkit.core.errors import WinKitError
from winkit.platform import download as dl
from winkit.platform import external_tools as tools

DATA = bytes(range(256)) * 20_000  # ~5 MB
FILES: dict[str, bytes] = {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:  # silêncio nos testes
        pass

    def do_GET(self) -> None:
        body = FILES.get(self.path)
        if body is None:
            self.send_error(404)
            return
        start = 0
        rng = self.headers.get("Range")
        if rng:
            start = int(rng.split("=")[1].split("-")[0])
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(body) - 1}/{len(body)}")
        else:
            self.send_response(200)
        self.send_header("Content-Length", str(len(body) - start))
        self.end_headers()
        self.wfile.write(body[start:])


@pytest.fixture
def server() -> Iterator[str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_pause_resume_and_verify(server: str, tmp_path: Path) -> None:
    FILES["/win.iso"] = DATA
    dest = tmp_path / "win.iso"
    seen: list[dl.Progress] = []
    stop = {"now": True}
    with pytest.raises(dl.DownloadPaused):
        dl.download(
            f"{server}/win.iso", dest, progress=seen.append, should_stop=lambda: stop["now"]
        )
    part = tmp_path / "win.iso.part"
    assert part.is_file() and 0 < part.stat().st_size < len(DATA) and not dest.exists()
    sha = hashlib.sha256(DATA).hexdigest()
    dl.download(f"{server}/win.iso", dest, sha256=sha, progress=seen.append)  # continua
    assert dest.read_bytes() == DATA and not part.exists()
    assert seen[-1].done == len(DATA) and seen[-1].fraction == 1.0
    assert dl.download(f"{server}/win.iso", dest, sha256=sha) == dest  # já baixado


def test_wrong_hash_is_deleted(server: str, tmp_path: Path) -> None:
    FILES["/x.bin"] = b"abc"
    with pytest.raises(WinKitError):
        dl.download(f"{server}/x.bin", tmp_path / "x.bin", sha256="0" * 64)
    assert not (tmp_path / "x.bin").exists() and not (tmp_path / "x.bin.part").exists()


def _zip(names: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in names.items():
            z.writestr(name, data)
    return buf.getvalue()


def test_ventoy_release_is_verified_and_extracted(server: str, tmp_path: Path) -> None:
    ventoy = default_catalogs().download("ventoy")
    assert ventoy is not None
    package = _zip({"ventoy-1.1.05/Ventoy2Disk.exe": b"MZ"})
    FILES["/v.zip"] = package
    FILES["/sha256.txt"] = (
        f"{hashlib.sha256(package).hexdigest()}  ventoy-1.1.05-windows.zip\n".encode()
    )
    api = {
        "tag_name": "v1.1.05",
        "assets": [
            {"name": "ventoy-1.1.05-linux.tar.gz", "browser_download_url": f"{server}/nope"},
            {"name": "ventoy-1.1.05-windows.zip", "browser_download_url": f"{server}/v.zip"},
            {"name": "sha256.txt", "browser_download_url": f"{server}/sha256.txt"},
        ],
    }
    release = tools.latest_release(ventoy, get_json=lambda url: api, get_text=dl.get_text)
    assert release.version == "1.1.05" and release.sha256
    exe = tools.fetch(ventoy, tmp_path, release=release)
    assert exe.read_bytes() == b"MZ" and exe.name == "Ventoy2Disk.exe"


def test_zip_slip_is_refused(server: str, tmp_path: Path) -> None:
    ventoy = default_catalogs().download("ventoy")
    assert ventoy is not None
    FILES["/bad.zip"] = _zip({"../../fora.exe": b"MZ"})
    release = tools.Release("1.0", "ventoy-1.0-windows.zip", f"{server}/bad.zip", None)
    with pytest.raises(WinKitError):
        tools.fetch(ventoy, tmp_path / "t", release=release)
    assert not (tmp_path / "fora.exe").exists()


def test_rufus_hash_from_release_text() -> None:
    rufus = default_catalogs().download("rufus")
    assert rufus is not None
    sha = "a" * 64
    api = {
        "tag_name": "v4.6",
        "body": f"SHA-256:\n- `rufus-4.6.exe`: {sha}\n",
        "assets": [
            {"name": "rufus-4.6p.exe", "browser_download_url": "u1"},
            {"name": "rufus-4.6.exe", "browser_download_url": "u2"},
        ],
    }
    release = tools.latest_release(rufus, get_json=lambda url: api)
    assert (release.asset_name, release.url, release.sha256) == ("rufus-4.6.exe", "u2", sha)
