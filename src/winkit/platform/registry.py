"""Registro do Windows via ``winreg`` (PLANO.md §13.2).

Hives aceitos: ``HKLM``, ``HKCU``, ``HKU``. O perfil Default é montado em
``HKU\\WinKitDefault`` com ``reg.exe load`` (que habilita o privilégio necessário) e
desmontado com ``reg.exe unload`` — sempre em ``try/finally`` (R-17).
"""

from __future__ import annotations

import contextlib
import gc
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Protocol

from winkit.core.catalog.models import RegType
from winkit.core.errors import RegistryError
from winkit.platform.runner import CommandRunner
from winkit.platform.system import system32

log = logging.getLogger(__name__)

DEFAULT_HIVE_MOUNT = "WinKitDefault"


class Registry(Protocol):
    def get(self, hive: str, key: str, value: str) -> Any: ...

    def set(self, hive: str, key: str, value: str, reg_type: RegType, data: Any) -> None: ...

    def delete_value(self, hive: str, key: str, value: str) -> bool: ...

    def delete_key(self, hive: str, key: str) -> bool: ...

    def key_exists(self, hive: str, key: str) -> bool: ...

    def create_key(self, hive: str, key: str) -> None: ...

    def subkeys(self, hive: str, key: str) -> list[str]: ...

    def values(self, hive: str, key: str) -> dict[str, Any]: ...

    def load_hive(self, mount: str, file: Path) -> None: ...

    def unload_hive(self, mount: str) -> None: ...


@contextlib.contextmanager
def mounted_hive(reg: Registry, file: Path, mount: str = DEFAULT_HIVE_MOUNT) -> Iterator[str]:
    """Monta um ``NTUSER.DAT`` e devolve o prefixo de chave sob ``HKU``."""
    reg.load_hive(mount, file)
    try:
        yield mount
    finally:
        gc.collect()  # handles abertos impedem o unload
        reg.unload_hive(mount)


def encode_binary(data: str) -> bytes:
    cleaned = data.replace(" ", "").replace(",", "")
    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:
        raise RegistryError(f"valor binário inválido: {data!r}") from exc


class WindowsRegistry:  # pragma: no cover — exercitado no CI Windows
    def __init__(self, runner: CommandRunner) -> None:
        self._runner: CommandRunner = runner
        self._ready = False

    def _init(self) -> None:
        """Carrega o ``winreg`` no primeiro uso: criar o serviço nunca falha fora do Windows."""
        if self._ready:
            return
        if sys.platform != "win32":
            raise RegistryError("registro só existe no Windows")
        import winreg  # noqa: PLC0415 — só existe no Windows

        self._w: Any = winreg
        self._ready = True
        self._roots: dict[str, Any] = {
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER,
            "HKU": winreg.HKEY_USERS,
        }
        self._types: dict[str, int] = {
            "dword": winreg.REG_DWORD,
            "qword": winreg.REG_QWORD,
            "sz": winreg.REG_SZ,
            "expand_sz": winreg.REG_EXPAND_SZ,
            "multi_sz": winreg.REG_MULTI_SZ,
            "binary": winreg.REG_BINARY,
        }

    def _root(self, hive: str) -> Any:
        self._init()
        try:
            return self._roots[hive]
        except KeyError as exc:
            raise RegistryError(f"hive desconhecido: {hive}") from exc

    def get(self, hive: str, key: str, value: str) -> Any:
        self._init()
        w = self._w
        try:
            with w.OpenKey(self._root(hive), key, 0, w.KEY_READ | w.KEY_WOW64_64KEY) as k:
                data, _ = w.QueryValueEx(k, value)
                return data
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise RegistryError(f"{hive}\\{key}\\{value}: {exc}") from exc

    def set(self, hive: str, key: str, value: str, reg_type: RegType, data: Any) -> None:
        self._init()
        w = self._w
        payload = encode_binary(data) if reg_type == "binary" else data
        try:
            with w.CreateKeyEx(self._root(hive), key, 0, w.KEY_WRITE | w.KEY_WOW64_64KEY) as k:
                w.SetValueEx(k, value, 0, self._types[reg_type], payload)
        except OSError as exc:
            raise RegistryError(f"{hive}\\{key}\\{value}: {exc}") from exc

    def delete_value(self, hive: str, key: str, value: str) -> bool:
        self._init()
        w = self._w
        try:
            with w.OpenKey(self._root(hive), key, 0, w.KEY_SET_VALUE | w.KEY_WOW64_64KEY) as k:
                w.DeleteValue(k, value)
                return True
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise RegistryError(f"{hive}\\{key}\\{value}: {exc}") from exc

    def delete_key(self, hive: str, key: str) -> bool:
        self._init()
        w = self._w
        try:
            w.DeleteKeyEx  # noqa: B018 — garante a API
            self._delete_tree(self._root(hive), key)
            return True
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise RegistryError(f"{hive}\\{key}: {exc}") from exc

    def _delete_tree(self, root: Any, key: str) -> None:
        self._init()
        w = self._w
        access = w.KEY_ALL_ACCESS | w.KEY_WOW64_64KEY
        with w.OpenKey(root, key, 0, access) as k:
            while True:
                try:
                    child = w.EnumKey(k, 0)
                except OSError:
                    break
                self._delete_tree(root, f"{key}\\{child}")
        w.DeleteKeyEx(root, key, w.KEY_WOW64_64KEY, 0)

    def key_exists(self, hive: str, key: str) -> bool:
        self._init()
        w = self._w
        try:
            with w.OpenKey(self._root(hive), key, 0, w.KEY_READ | w.KEY_WOW64_64KEY):
                return True
        except FileNotFoundError:
            return False

    def create_key(self, hive: str, key: str) -> None:
        self._init()
        w = self._w
        try:
            with w.CreateKeyEx(self._root(hive), key, 0, w.KEY_WRITE | w.KEY_WOW64_64KEY):
                pass
        except OSError as exc:
            raise RegistryError(f"{hive}\\{key}: {exc}") from exc

    def subkeys(self, hive: str, key: str) -> list[str]:
        self._init()
        w = self._w
        out: list[str] = []
        try:
            with w.OpenKey(self._root(hive), key, 0, w.KEY_READ | w.KEY_WOW64_64KEY) as k:
                i = 0
                while True:
                    try:
                        out.append(w.EnumKey(k, i))
                    except OSError:
                        break
                    i += 1
        except FileNotFoundError:
            return []
        return out

    def values(self, hive: str, key: str) -> dict[str, Any]:
        self._init()
        w = self._w
        out: dict[str, Any] = {}
        try:
            with w.OpenKey(self._root(hive), key, 0, w.KEY_READ | w.KEY_WOW64_64KEY) as k:
                i = 0
                while True:
                    try:
                        name, data, _ = w.EnumValue(k, i)
                    except OSError:
                        break
                    out[name] = data
                    i += 1
        except FileNotFoundError:
            return {}
        return out

    def load_hive(self, mount: str, file: Path) -> None:
        res = self._runner.run(
            [str(system32("reg.exe")), "load", f"HKU\\{mount}", str(file)], timeout=60
        )
        if not res.ok:
            raise RegistryError(f"não foi possível montar {file} (reg load código {res.exit_code})")

    def unload_hive(self, mount: str) -> None:
        for _ in range(5):
            res = self._runner.run(
                [str(system32("reg.exe")), "unload", f"HKU\\{mount}"], timeout=60
            )
            if res.ok:
                return
            gc.collect()
        log.error("não foi possível desmontar HKU\\%s", mount)
        raise RegistryError(f"não foi possível desmontar HKU\\{mount}")
