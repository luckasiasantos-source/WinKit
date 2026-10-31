"""Registro único de segredos do processo (R-53, D-036).

Senhas de Wi-Fi e de contas, e os caminhos dos arquivos que as contêm, entram aqui assim
que são lidos. O ``runner``, o ``EventLog`` e o resumo trocam qualquer ocorrência por ``***``.
"""

from __future__ import annotations

import threading

MASK = "***"
_MIN_LENGTH = 4  # valores curtos demais mascarariam texto comum


class SecretRegistry:
    def __init__(self) -> None:
        self._values: set[str] = set()
        self._lock = threading.Lock()

    def add(self, value: str | None) -> None:
        if value and len(value) >= _MIN_LENGTH:
            with self._lock:
                self._values.add(value)

    def values(self) -> list[str]:
        with self._lock:
            return sorted(self._values, key=len, reverse=True)  # os maiores primeiro

    def mask(self, text: str) -> str:
        for value in self.values():
            text = text.replace(value, MASK)
        return text

    def clear(self) -> None:
        with self._lock:
            self._values.clear()


#: Registro do processo. Testes limpam com ``SECRETS.clear()``.
SECRETS = SecretRegistry()
