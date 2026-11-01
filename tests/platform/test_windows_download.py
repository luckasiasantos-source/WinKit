"""Link da ISO pelo Fido (V3-08, D-047): assinatura conferida antes de rodar."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from winkit.core.errors import WinKitError
from winkit.platform.fakes.powershell import FakePowerShell
from winkit.platform.windows_download import FidoLinks


def _links(tmp_path: Path, ps: FakePowerShell) -> FidoLinks:
    def downloader(url: str, dest: Path, **_: Any) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# Fido")
        return dest

    return FidoLinks(
        ps,  # type: ignore[arg-type]
        tmp_path,
        get_json=lambda url: {"tag_name": "v1.65"},
        downloader=downloader,
    )


def test_signed_fido_gives_url(tmp_path: Path) -> None:
    ps = FakePowerShell()
    ps.when("Get-AuthenticodeSignature", [{"Status": 0, "Subject": "CN=Akeo Consulting, O=Akeo"}])
    ps.when("-GetUrl", [{"Url": "https://software.download.prss.microsoft.com/x.iso"}])
    url = _links(tmp_path, ps).url("11", "x64", "pt-BR")
    assert url.endswith("x.iso")
    params = ps.calls[-1].params
    assert params["Lang"] == "Brazilian Portuguese" and params["Win"] == "Windows 11"


def test_unsigned_fido_is_refused_and_deleted(tmp_path: Path) -> None:
    ps = FakePowerShell()
    ps.when("Get-AuthenticodeSignature", [{"Status": 2, "Subject": ""}])
    with pytest.raises(WinKitError):
        _links(tmp_path, ps).url("10", "x86", "en-US")
    assert not (tmp_path / "fido-v1.65" / "Fido.ps1").exists()


def test_no_url_explains(tmp_path: Path) -> None:
    ps = FakePowerShell()
    ps.when("Get-AuthenticodeSignature", [{"Status": 0, "Subject": "CN=Akeo Consulting"}])
    ps.when("-GetUrl", [{"Url": "Error: blocked"}])
    with pytest.raises(WinKitError, match="Microsoft"):
        _links(tmp_path, ps).url("11", "x64", "es-ES")
