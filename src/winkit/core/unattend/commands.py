"""Linhas de comando embutidas no ``autounattend.xml`` (PLANO.md §9.2).

O campo ``Path`` de ``RunSynchronousCommand`` aceita no máximo 259 caracteres; por isso o
bootstrap usa ``cmd /c for`` e parâmetros curtos, e o tamanho é verificado.
"""

from __future__ import annotations

import string

from winkit.core.catalog.models import RegSet
from winkit.core.errors import UnattendError

MAX_COMMAND_LENGTH = 259
#: C: é o próprio Windows sendo instalado; o pendrive está em outra letra.
_LETTERS = " ".join(string.ascii_uppercase[3:])
AGENT_EXE = r"%ProgramData%\WinKit\Agent\winkit-agent\winkit-agent.exe"

_REG_TYPES = {
    "dword": "REG_DWORD",
    "qword": "REG_QWORD",
    "sz": "REG_SZ",
    "expand_sz": "REG_EXPAND_SZ",
    "multi_sz": "REG_MULTI_SZ",
    "binary": "REG_BINARY",
}


def _check(cmd: str) -> str:
    if len(cmd) > MAX_COMMAND_LENGTH:
        raise UnattendError(f"comando com {len(cmd)} caracteres (máximo {MAX_COMMAND_LENGTH})")
    if any(ch in cmd for ch in "\r\n"):
        raise UnattendError("comando não pode ter quebra de linha")
    return cmd


def bootstrap_command(pendrive_id: str, profile_id: str) -> str:
    """Procura o pendrive pelo marcador e chama ``bootstrap.ps1`` (D-012)."""
    for value in (pendrive_id, profile_id):
        if not value or any(not (ch.isalnum() or ch in "-_") for ch in value):
            raise UnattendError(f"identificador inválido para a linha de comando: {value!r}")
    return _check(
        f"cmd.exe /c for %d in ({_LETTERS}) do @if exist %d:\\WinKit\\winkit.marker "
        f"powershell.exe -nop -ep Bypass -File %d:\\WinKit\\Agent\\bootstrap.ps1 "
        f"%d: {pendrive_id} {profile_id}"
    )


def first_logon_command() -> str:
    """Rede de segurança: inicia a Fase 2 no primeiro logon sem bloquear a área de trabalho."""
    return _check(f'cmd.exe /c if exist "{AGENT_EXE}" start "" "{AGENT_EXE}" phase2 --first-logon')


def reg_add_command(op: RegSet, default_hive: str = "HKLM") -> str:
    hive = op.hive or default_hive
    if hive != "HKLM":
        raise UnattendError("na instalação só é possível gravar em HKLM")
    key = f"{hive}\\{op.key}"
    data = "\\0".join(op.data) if isinstance(op.data, list) else str(op.data)
    value = "/ve" if op.value == "" else f'/v "{op.value}"'
    return _check(f'reg.exe add "{key}" {value} /t {_REG_TYPES[op.type]} /d "{data}" /f')


def labconfig_commands() -> list[str]:
    """Pula as checagens de requisitos do Windows 11 (redundante com o Ventoy)."""
    return [
        _check(f'reg.exe add "HKLM\\SYSTEM\\Setup\\LabConfig" /v {name} /t REG_DWORD /d 1 /f')
        for name in ("BypassTPMCheck", "BypassSecureBootCheck", "BypassRAMCheck", "BypassCPUCheck")
    ]
