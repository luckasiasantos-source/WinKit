"""Registro falso em memória (chaves sem diferenciar maiúsculas, como no Windows)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from winkit.core.catalog.models import RegType
from winkit.core.errors import RegistryError


@dataclass
class FakeRegistry:
    data: dict[tuple[str, str], dict[str, tuple[str, Any]]] = field(default_factory=dict)
    mounted: dict[str, Path] = field(default_factory=dict)
    fail_on: set[str] = field(default_factory=set)  # trechos de chave que geram erro

    @staticmethod
    def _k(hive: str, key: str) -> tuple[str, str]:
        return hive.upper(), key.strip("\\").lower()

    def _check(self, key: str) -> None:
        if any(part.lower() in key.lower() for part in self.fail_on):
            raise RegistryError(f"acesso negado: {key}")

    def get(self, hive: str, key: str, value: str) -> Any:
        entry = self.data.get(self._k(hive, key), {}).get(value.lower())
        return None if entry is None else entry[1]

    def get_type(self, hive: str, key: str, value: str) -> str | None:
        entry = self.data.get(self._k(hive, key), {}).get(value.lower())
        return None if entry is None else entry[0]

    def set(self, hive: str, key: str, value: str, reg_type: RegType, data: Any) -> None:
        self._check(key)
        self.data.setdefault(self._k(hive, key), {})[value.lower()] = (reg_type, data)

    def delete_value(self, hive: str, key: str, value: str) -> bool:
        self._check(key)
        values = self.data.get(self._k(hive, key))
        if values is None or value.lower() not in values:
            return False
        del values[value.lower()]
        return True

    def delete_key(self, hive: str, key: str) -> bool:
        self._check(key)
        h, k = self._k(hive, key)
        doomed = [x for x in self.data if x[0] == h and (x[1] == k or x[1].startswith(k + "\\"))]
        for x in doomed:
            del self.data[x]
        return bool(doomed)

    def key_exists(self, hive: str, key: str) -> bool:
        h, k = self._k(hive, key)
        return any(x[0] == h and (x[1] == k or x[1].startswith(k + "\\")) for x in self.data)

    def create_key(self, hive: str, key: str) -> None:
        self._check(key)
        self.data.setdefault(self._k(hive, key), {})

    def subkeys(self, hive: str, key: str) -> list[str]:
        h, k = self._k(hive, key)
        prefix = k + "\\" if k else ""
        names = {
            x[1][len(prefix) :].split("\\")[0]
            for x in self.data
            if x[0] == h and x[1].startswith(prefix) and x[1] != k
        }
        return sorted(names)

    def values(self, hive: str, key: str) -> dict[str, Any]:
        return {name: v[1] for name, v in self.data.get(self._k(hive, key), {}).items()}

    def load_hive(self, mount: str, file: Path) -> None:
        if mount in self.mounted:
            raise RegistryError(f"{mount} já montado")
        self.mounted[mount] = file

    def unload_hive(self, mount: str) -> None:
        if mount not in self.mounted:
            raise RegistryError(f"{mount} não está montado")
        del self.mounted[mount]
