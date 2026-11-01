"""Link oficial da ISO do Windows, obtido pelo Fido (V3-08, D-047, H37).

O Fido (GPLv3, do autor do Rufus) conversa com o site da Microsoft e devolve o link de download.
O WinKit baixa o ``Fido.ps1`` da release oficial, confere a assinatura digital (Akeo Consulting)
e só então o roda, pedindo só o link (``-GetUrl``). O download em si é do WinKit.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from winkit.core.errors import WinKitError
from winkit.platform import download as dl
from winkit.platform.powershell import PowerShell

FIDO_REPO = "pbatard/Fido"
RAW = "https://raw.githubusercontent.com/{repo}/{tag}/Fido.ps1"
SIGNER = "Akeo Consulting"
#: Idioma da ISO → nome usado pelo site da Microsoft (o que o Fido espera em ``-Lang``).
LANGUAGES: dict[str, str] = {
    "pt-BR": "Brazilian Portuguese",
    "pt-PT": "Portuguese",
    "en-US": "English",
    "en-GB": "English International",
    "es-ES": "Spanish",
    "es-MX": "Spanish (Mexico)",
    "fr-FR": "French",
    "de-DE": "German",
    "it-IT": "Italian",
}

_CHECK_SIGNATURE = r"""
$sig = Get-AuthenticodeSignature -LiteralPath $Path
[pscustomobject]@{
  Status = [int]$sig.Status
  Subject = if ($sig.SignerCertificate) { $sig.SignerCertificate.Subject } else { '' }
}
"""

_GET_URL = r"""
$url = & $Fido -Win $Win -Rel Latest -Ed Pro -Lang $Lang -Arch $Arch -GetUrl
[pscustomobject]@{ Url = [string]($url | Select-Object -Last 1) }
"""


class IsoLinks(Protocol):
    def url(self, version: str, arch: str, language: str) -> str: ...


class FidoLinks:
    def __init__(
        self,
        ps: PowerShell,
        tools_dir: Path,
        *,
        get_json: Callable[[str], Any] = dl.get_json,
        downloader: Callable[..., Path] = dl.download,
    ) -> None:
        self._ps = ps
        self._dir = tools_dir
        self._get_json = get_json
        self._download = downloader

    def _script(self) -> Path:
        tag = str(
            self._get_json(f"https://api.github.com/repos/{FIDO_REPO}/releases/latest")["tag_name"]
        )
        path = self._download(
            RAW.format(repo=FIDO_REPO, tag=tag), self._dir / f"fido-{tag}" / "Fido.ps1"
        )
        sig = self._ps.run_json(_CHECK_SIGNATURE, {"Path": str(path)})
        if not sig or sig[0].get("Status") != 0 or SIGNER not in str(sig[0].get("Subject", "")):
            path.unlink(missing_ok=True)
            raise WinKitError("o Fido baixado não tem a assinatura do autor; download cancelado")
        return path

    def url(self, version: str, arch: str, language: str) -> str:
        name = LANGUAGES.get(language, "English")
        out = self._ps.run_json(
            _GET_URL,
            {"Fido": str(self._script()), "Win": f"Windows {version}", "Lang": name, "Arch": arch},
            timeout=300,
        )
        url = str(out[0].get("Url", "")) if out else ""
        if not url.startswith("https://"):
            raise WinKitError(
                "a Microsoft não devolveu o link agora (pode ser limite de pedidos ou região); "
                "tente mais tarde ou use uma ISO que você já tem"
            )
        return url


def tools_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".cache") / "WinKit" / "ferramentas"
