"""Pastas conhecidas do Windows (``SHGetKnownFolderPath``) — PLANO.md §6.3."""

from __future__ import annotations

import ctypes
import os
import sys
import uuid
from typing import Protocol

from winkit.core.errors import PlatformError
from winkit.platform.registry import Registry

#: Variável do molde → KNOWNFOLDERID.
KNOWN_FOLDER_IDS: dict[str, str] = {
    "USERPROFILE": "5E6C858F-0E22-4760-9AFE-EA3317B67173",
    "APPDATA": "3EB685DB-65F9-4CF6-A03A-E3EF65729F3D",
    "LOCALAPPDATA": "F1B32785-6FBA-4FCF-9D55-7B8E7F157091",
    "LOCALLOW": "A520A1A4-1780-4FF6-BD18-167343C5AF16",
    "DOCUMENTS": "FDD39AD0-238F-46AF-ADB4-6C85480369C7",
    "PICTURES": "33E28130-4E1E-4676-835A-98395C3BC3BB",
    "VIDEOS": "18989B1D-99B5-455B-841C-AB7C74E4DDFC",
    "MUSIC": "4BD8D571-6D19-48D3-BE97-422220080E43",
    "DESKTOP": "B4BFCC3A-DB2C-424C-B029-7FE99A87C641",
    "DOWNLOADS": "374DE290-123F-4565-9164-39C4925E467B",
    "SAVEDGAMES": "4C5C32FF-BB9D-43B0-B5B4-2D72E54EAAA4",
    "PROGRAMDATA": "62AB5D82-FDC1-4DC3-A9DD-070D1D495D97",
    "PROGRAMFILES": "905E63B6-C1BF-494E-B29C-65B732D3D21A",
    "PROGRAMFILESX86": "7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E",
    "PUBLIC": "DFDF76A2-C82A-4D63-906A-5644AC457385",
}
MACHINE_KEYS = ("PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILESX86", "PUBLIC")
PROFILE_LIST = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"


class KnownFolders(Protocol):
    def machine(self) -> dict[str, str]: ...

    def current_user(self) -> dict[str, str]: ...

    def default_profile_root(self) -> str: ...

    def windows_dir(self) -> str: ...


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def parse(cls, text: str) -> _GUID:
        u = uuid.UUID(text)
        g = cls()
        g.Data1, g.Data2, g.Data3 = u.fields[0], u.fields[1], u.fields[2]
        for i, b in enumerate(u.bytes[8:]):
            g.Data4[i] = b
        return g


def known_folder(folder_id: str) -> str:  # pragma: no cover — CI Windows
    if sys.platform != "win32":
        raise PlatformError("pastas conhecidas só existem no Windows")
    shell32, ole32 = ctypes.windll.shell32, ctypes.windll.ole32
    out = ctypes.c_wchar_p()
    guid = _GUID.parse(folder_id)
    hr = shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out))
    try:
        if hr != 0 or out.value is None:
            raise PlatformError(
                f"SHGetKnownFolderPath falhou para {folder_id}: 0x{hr & 0xFFFFFFFF:08X}"
            )
        return out.value
    finally:
        ole32.CoTaskMemFree(out)


class WindowsKnownFolders:  # pragma: no cover — CI Windows
    def __init__(self, registry: Registry) -> None:
        self._registry = registry

    def machine(self) -> dict[str, str]:
        return {k: known_folder(KNOWN_FOLDER_IDS[k]) for k in MACHINE_KEYS}

    def current_user(self) -> dict[str, str]:
        out = {}
        for key, fid in KNOWN_FOLDER_IDS.items():
            if key in MACHINE_KEYS:
                continue
            try:
                out[key] = known_folder(fid)
            except PlatformError:
                continue  # ex.: Jogos Salvos inexistente para contas de sistema
        return out

    def default_profile_root(self) -> str:
        raw = self._registry.get("HKLM", PROFILE_LIST, "Default")
        if not raw:
            raw = os.environ.get("SYSTEMDRIVE", "C:") + r"\Users\Default"
        return os.path.expandvars(str(raw))

    def windows_dir(self) -> str:
        return os.environ.get("SYSTEMROOT", r"C:\Windows")
