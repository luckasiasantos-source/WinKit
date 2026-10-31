"""Etapa: aplicar um ajuste do catálogo (M7, itens 31, 32; R-34).

Destino do registro conforme o alvo da etapa (PLANO.md §13.2):
- ``machine`` → HKLM;
- ``default_profile`` → HKU\\WinKitDefault (NTUSER.DAT do perfil Default montado);
- ``user_profile`` → HKCU.
Operações com ``hive: HKLM`` explícito sempre vão para a máquina.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path

from winkit.agent.steps.base import StepContext, StepResult, local_path
from winkit.core.catalog.models import Tweak, TweakOp
from winkit.core.errors import WinKitError
from winkit.i18n import msg
from winkit.platform.registry import DEFAULT_HIVE_MOUNT, mounted_hive
from winkit.platform.system import system32

SERVICE_START = {"automatic": 2, "manual": 3, "disabled": 4}
SERVICES_KEY = r"SYSTEM\CurrentControlSet\Services"


@dataclass(frozen=True)
class Location:
    hive: str
    key: str


def locate(op_hive: str | None, key: str, tweak: Tweak, target: str) -> Location:
    if op_hive == "HKLM" or (op_hive is None and tweak.scope == "machine"):
        return Location("HKLM", key)
    if op_hive == "HKCU" or op_hive is None:
        if target == "default_profile":
            return Location("HKU", f"{DEFAULT_HIVE_MOUNT}\\{key}")
        return Location("HKCU", key)
    raise WinKitError(f"hive desconhecido: {op_hive}")


def needs_default_hive(tweak: Tweak, target: str) -> bool:
    if target != "default_profile":
        return False
    for op in tweak.apply:
        inner = op.reg_set or op.reg_delete_value or op.reg_delete_key
        if inner is not None and inner.hive in (None, "HKCU") and tweak.scope == "user":
            return True
    return False


@contextmanager
def registry_scope(ctx: StepContext, tweak: Tweak) -> Iterator[None]:
    if needs_default_hive(tweak, ctx.step.target):
        hive = local_path(ctx.services.folders.default_profile_root()) / "NTUSER.DAT"
        with mounted_hive(ctx.services.registry, Path(hive)):
            yield
    else:
        with nullcontext():
            yield


def apply_op(ctx: StepContext, tweak: Tweak, op: TweakOp) -> bool:
    """Aplica uma operação. Devolve True se exige reinício."""
    reg = ctx.services.registry
    target = ctx.step.target
    if op.reg_set is not None:
        loc = locate(op.reg_set.hive, op.reg_set.key, tweak, target)
        reg.set(loc.hive, loc.key, op.reg_set.value, op.reg_set.type, op.reg_set.data)
    elif op.reg_delete_value is not None:
        loc = locate(op.reg_delete_value.hive, op.reg_delete_value.key, tweak, target)
        reg.delete_value(loc.hive, loc.key, op.reg_delete_value.value)
    elif op.reg_delete_key is not None:
        loc = locate(op.reg_delete_key.hive, op.reg_delete_key.key, tweak, target)
        reg.delete_key(loc.hive, loc.key)
    elif op.service_start_type is not None:
        svc = op.service_start_type
        reg.set(
            "HKLM", f"{SERVICES_KEY}\\{svc.service}", "Start", "dword", SERVICE_START[svc.start]
        )
    elif op.optional_feature_disable is not None or op.optional_feature_enable is not None:
        enable = op.optional_feature_enable is not None
        feature = op.optional_feature_enable or op.optional_feature_disable
        assert feature is not None  # noqa: S101 — garantido pelo ramo
        result = ctx.services.features.set_optional_feature(feature.feature, enabled=enable)
        ctx.log.info(f"recurso {feature.feature}: {result}", step=ctx.step.id)
        return result == "restart"
    elif op.powercfg is not None:
        res = ctx.services.runner.run(
            [str(system32("powercfg.exe")), *op.powercfg.args], timeout=120
        )
        if res.exit_code != 0:
            raise WinKitError(f"powercfg {' '.join(op.powercfg.args)} retornou {res.exit_code}")
    elif op.appx_remove is not None:
        ctx.services.appx.remove(op.appx_remove.package)
    return False


def already_applied(ctx: StepContext, tweak: Tweak) -> bool:
    """Só ajustes 100% de registro fora do perfil Default podem ser conferidos sem efeito."""
    if ctx.step.target == "default_profile":
        return False
    reg = ctx.services.registry
    for op in tweak.apply:
        if op.reg_set is not None:
            loc = locate(op.reg_set.hive, op.reg_set.key, tweak, ctx.step.target)
            if reg.get(loc.hive, loc.key, op.reg_set.value) != op.reg_set.data:
                return False
        elif op.reg_delete_value is not None:
            loc = locate(op.reg_delete_value.hive, op.reg_delete_value.key, tweak, ctx.step.target)
            if reg.get(loc.hive, loc.key, op.reg_delete_value.value) is not None:
                return False
        else:
            return False
    return True


class TweakStep:
    def check(self, ctx: StepContext) -> bool:
        tweak = ctx.catalogs.tweak(ctx.step.ref)
        return tweak is not None and already_applied(ctx, tweak)

    def run(self, ctx: StepContext) -> StepResult:
        tweak = ctx.catalogs.tweak(ctx.step.ref)
        if tweak is None:
            return StepResult.skipped(msg("plan.excluded_unknown_tweak"))
        reboot = False
        try:
            with registry_scope(ctx, tweak):
                for op in tweak.apply:
                    reboot = apply_op(ctx, tweak, op) or reboot
        except WinKitError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        return StepResult.ok(reboot=reboot)
