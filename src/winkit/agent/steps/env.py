"""Etapa: variáveis de ambiente e PATH (V2-22, R26).

Destino pelo alvo da etapa: ``machine`` → ``HKLM``; ``default_profile`` → perfil Default
montado; ``user_profile`` → ``HKCU`` (com aviso aos programas abertos).
- Variável que já existe com outro valor **não** é sobrescrita (R-21), a menos que a receita
  diga ``replace``.
- O PATH só ganha entradas no fim, sem duplicar; nunca perde nenhuma.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from winkit.agent.steps.base import StepBase, StepContext, StepResult, item, local_path
from winkit.core.env import MACHINE_ENV_KEY, USER_ENV_KEY, merge_path, norm_entry
from winkit.core.errors import WinKitError
from winkit.core.live import PreviewItem
from winkit.core.recipe.models import EnvVar
from winkit.i18n import msg
from winkit.platform.registry import DEFAULT_HIVE_MOUNT, mounted_hive


@dataclass(frozen=True)
class _Where:
    hive: str
    key: str


@contextmanager
def _location(ctx: StepContext, scope: str) -> Iterator[_Where]:
    if scope == "machine":
        yield _Where("HKLM", MACHINE_ENV_KEY)
    elif ctx.step.target == "default_profile":
        hive = Path(local_path(ctx.services.folders.default_profile_root())) / "NTUSER.DAT"
        with mounted_hive(ctx.services.registry, hive):
            yield _Where("HKU", f"{DEFAULT_HIVE_MOUNT}\\{USER_ENV_KEY}")
    else:
        yield _Where("HKCU", USER_ENV_KEY)


def _parse_ref(ref: str) -> tuple[str, str, str | None]:
    """``var.user.JAVA_HOME`` → (var, user, JAVA_HOME); ``path.machine`` → (path, machine, None)."""
    what, scope, *rest = ref.split(".", 2)
    return what, scope, rest[0] if rest else None


def _var(ctx: StepContext, scope: str, name: str | None) -> EnvVar | None:
    return next(
        (
            v
            for v in ctx.recipe.environment.variables
            if v.scope == scope and name is not None and v.name.casefold() == name.casefold()
        ),
        None,
    )


def _paths(ctx: StepContext, scope: str) -> list[str]:
    return [p.value for p in ctx.recipe.environment.path_entries if p.selected and p.scope == scope]


def _get_path(ctx: StepContext, where: _Where) -> str | None:
    values = ctx.services.registry.values(where.hive, where.key)
    raw = next((v for k, v in values.items() if k.casefold() == "path"), None)
    return raw if isinstance(raw, str) else None


class EnvStep(StepBase):
    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        if ctx.step.target == "default_profile":
            return False  # o perfil Default só é lido com a hive montada; gravar de novo é seguro
        what, scope, name = _parse_ref(ctx.step.ref)
        with _location(ctx, scope) as where:
            if what == "path":
                current = {norm_entry(e) for e in (_get_path(ctx, where) or "").split(";")}
                return all(norm_entry(p) in current for p in _paths(ctx, scope))
            var = _var(ctx, scope, name)
            if var is None:
                return True
            current = ctx.services.registry.get(where.hive, where.key, var.name)
            return bool(current == var.value)

    def preview(self, ctx: StepContext) -> PreviewItem:
        what, scope, name = _parse_ref(ctx.step.ref)
        if self.check(ctx):
            return item(ctx, "already_done")
        if what == "path":
            return item(
                ctx,
                "will_change",
                (msg("preview.env_path", entries="; ".join(_paths(ctx, scope))),),
            )
        var = _var(ctx, scope, name)
        if var is None:
            return item(ctx, "not_applicable")
        current = None
        if ctx.step.target != "default_profile":
            with _location(ctx, scope) as where:
                current = ctx.services.registry.get(where.hive, where.key, var.name)
        if current is not None and var.on_conflict == "skip":
            warning = msg(
                "preview.env_conflict", name=var.name, current=str(current), new=var.value
            )
            return item(ctx, "not_applicable", warnings=(warning,))
        return item(ctx, "will_change", (msg("preview.env_var", name=var.name, value=var.value),))

    def run(self, ctx: StepContext) -> StepResult:
        what, scope, name = _parse_ref(ctx.step.ref)
        try:
            with _location(ctx, scope) as where:
                result = (
                    self._path(ctx, where, scope)
                    if what == "path"
                    else self._set(ctx, where, scope, name)
                )
        except WinKitError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        if result.outcome == "done" and where.hive in ("HKCU", "HKLM"):
            ctx.services.env.broadcast_env_change()
        return result

    def _set(self, ctx: StepContext, where: _Where, scope: str, name: str | None) -> StepResult:
        var = _var(ctx, scope, name)
        if var is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        reg = ctx.services.registry
        current = reg.get(where.hive, where.key, var.name)
        if current is not None and current != var.value and var.on_conflict == "skip":
            return StepResult.skipped(msg("step.env.exists", name=var.name))
        reg.set(where.hive, where.key, var.name, var.kind, var.value)
        return StepResult.ok(msg("step.env.set", name=var.name))

    def _path(self, ctx: StepContext, where: _Where, scope: str) -> StepResult:
        current = _get_path(ctx, where)
        new_value, added = merge_path(current, _paths(ctx, scope))
        if not added:
            return StepResult.ok(msg("step.already_done"))
        ctx.services.registry.set(where.hive, where.key, "Path", "expand_sz", new_value)
        return StepResult.ok(msg("step.env.path_added", n=len(added)))
