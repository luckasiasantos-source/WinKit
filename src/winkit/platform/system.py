"""Informações básicas do sistema e caminhos de ferramentas nativas (R-12)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: Sem janela de console para processos filhos no Windows (modo silencioso).
CREATE_NO_WINDOW = 0x08000000


def is_windows() -> bool:
    return sys.platform == "win32"


def system_root() -> Path:
    """``C:\\Windows`` (ou equivalente), lido do ambiente."""
    return Path(os.environ.get("SYSTEMROOT") or os.environ.get("WINDIR") or r"C:\Windows")


def system32(*parts: str) -> Path:
    """Caminho absoluto de uma ferramenta em ``System32``.

    Processos 32-bit em Windows 64-bit seriam redirecionados para ``SysWOW64``; o
    WinKit é sempre 64-bit, então ``System32`` é o diretório nativo.
    """
    return system_root().joinpath("System32", *parts)


def powershell_exe() -> Path:
    return system32("WindowsPowerShell", "v1.0", "powershell.exe")


def program_data() -> Path:
    return Path(os.environ.get("PROGRAMDATA") or r"C:\ProgramData")


def winkit_program_data() -> Path:
    """``C:\\ProgramData\\WinKit`` — área local do Agente no Windows novo (D-013)."""
    return program_data() / "WinKit"
