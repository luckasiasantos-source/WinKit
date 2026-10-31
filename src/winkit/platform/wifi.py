"""Perfis de Wi-Fi pelo ``netsh wlan`` (V2-02).

Só o **código de saída** e os **arquivos XML** gerados são usados; o texto do ``netsh`` é
localizado e nunca é lido (R-13).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Protocol

from winkit.platform.runner import CommandRunner
from winkit.platform.services_base import service_running
from winkit.platform.system import system32


class WifiManager(Protocol):
    def has_wlan(self) -> bool:
        """O serviço de Wi-Fi (``WlanSvc``) existe? Sem ele não há o que adicionar."""
        ...

    def export_profiles(self, dest: Path) -> list[Path]:
        """Exporta todos os perfis **com a senha** (``key=clear``) para ``dest``."""
        ...

    def add_profile(self, xml_path: Path) -> int:
        """Adiciona para todos os usuários; devolve o código de saída."""
        ...

    def profile_exists(self, name: str) -> bool: ...


class WindowsWifi:
    def __init__(self, runner: CommandRunner) -> None:
        self._runner = runner

    def _netsh(self, *args: str) -> int:
        return self._runner.run([str(system32("netsh.exe")), "wlan", *args], timeout=120).exit_code

    def has_wlan(self) -> bool:
        return service_running(self._runner, "WlanSvc")

    def export_profiles(self, dest: Path) -> list[Path]:
        dest.mkdir(parents=True, exist_ok=True)
        self._netsh("export", "profile", "key=clear", f"folder={dest}")
        return sorted(dest.glob("*.xml"))

    def add_profile(self, xml_path: Path) -> int:
        return self._netsh("add", "profile", f"filename={xml_path}", "user=all")

    def profile_exists(self, name: str) -> bool:
        tmp = Path(tempfile.mkdtemp(prefix="winkit-wifi-"))
        try:
            code = self._netsh("export", "profile", f"name={name}", f"folder={tmp}")
            return code == 0 and any(tmp.glob("*.xml"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
