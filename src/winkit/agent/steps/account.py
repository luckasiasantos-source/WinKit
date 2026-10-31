"""Etapa: conta extra (V2-11, R24).

A conta é criada pelo ``autounattend.xml``; aqui o Agente garante o grupo pelo **SID** (o nome
do grupo muda com o idioma, H11), tira do grupo Administradores quem deve ser padrão e, se a
receita pede, faz o Windows pedir uma senha nova no primeiro login. Nunca roda ao vivo.
"""

from __future__ import annotations

from winkit.agent.steps.base import StepBase, StepContext, StepResult
from winkit.core.errors import WinKitError
from winkit.core.recipe.models import ExtraAccount
from winkit.i18n import Msg, msg


def _account(ctx: StepContext) -> ExtraAccount | None:
    return next(
        (a for a in ctx.recipe.windows.extra_accounts if a.username.casefold() == ctx.step.ref),
        None,
    )


class AccountStep(StepBase):
    #: O modo "aplicar neste PC" nunca cria nem muda contas (R-54).
    live_safe = False

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        a = _account(ctx)
        return (msg("preview.account", name=a.username),) if a else ()

    def run(self, ctx: StepContext) -> StepResult:
        a = _account(ctx)
        if a is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        accounts = ctx.services.accounts
        try:
            result = accounts.ensure_group(a.username, admin=a.group == "administrators")
            if result == "no_user":
                return StepResult.failed(msg("step.account.missing", name=a.username))
            if a.password_mode == "must_change":  # noqa: S105 — modo, não senha
                accounts.expire_password(a.username)
        except WinKitError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        key = "step.account.admin" if a.group == "administrators" else "step.account.standard"
        return StepResult.ok(msg(key, name=a.username))
