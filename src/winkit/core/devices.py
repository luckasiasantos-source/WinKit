"""Dispositivos com problema no Gerenciador de Dispositivos (V2-09).

O código ``ConfigManagerErrorCode`` é traduzido por **tabela** (nunca pelo texto do Windows,
R-13). Fonte: https://learn.microsoft.com/windows-hardware/drivers/install/device-manager-error-messages
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from winkit.core.text import Msg, msg

#: Códigos documentados que o resumo explica; os outros usam um texto genérico com o número.
PROBLEM_CODES: frozenset[int] = frozenset(
    {1, 3, 10, 12, 14, 18, 19, 21, 22, 24, 28, 29, 31, 32, 37, 39, 41, 43, 45, 48, 52}
)
#: Não são falta de driver: desabilitado pelo usuário (22) ou aparelho desconectado (45).
NOT_A_DRIVER_PROBLEM: frozenset[int] = frozenset({22, 45})


class ProblemDevice(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str  # só exibido, nunca interpretado
    device_id: str
    code: int
    hardware_ids: tuple[str, ...] = ()

    @property
    def needs_driver(self) -> bool:
        return self.code not in NOT_A_DRIVER_PROBLEM


def problem_text(code: int) -> Msg:
    if code in PROBLEM_CODES:
        return msg(f"device.problem.{code}")
    return msg("device.problem.other", code=code)


def needing_drivers(devices: list[ProblemDevice]) -> list[ProblemDevice]:
    return [d for d in devices if d.needs_driver]


def hardware_ids(devices: list[ProblemDevice]) -> list[str]:
    """Todos os ids de hardware, sem repetir (comparação sem maiúsculas)."""
    seen: dict[str, str] = {}
    for d in devices:
        for hid in d.hardware_ids:
            seen.setdefault(hid.casefold(), hid)
    return list(seen.values())
