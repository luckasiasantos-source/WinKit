"""Etapas: apps padrão (V2-05, R20).

- ``default_apps:import`` (Fase 1): ``dism /Import-DefaultAppAssociations`` com o XML filtrado
  pelos grupos escolhidos. Vale para a conta criada no primeiro login (H25). Fora da Fase 1 o
  Windows não deixa aplicar sem o usuário: a etapa pula com a ação manual.
- ``default_apps_verify:user`` (Fase 2): confere o ``UserChoice`` de cada item e põe no resumo
  os que não pegaram (normalmente apps instalados depois do login).
"""

from __future__ import annotations

from winkit.agent.steps.base import StepBase, StepContext, StepResult
from winkit.core.associations import (
    Association,
    AssociationsError,
    filtered_xml,
    identifiers,
    parse,
    user_choice_key,
)
from winkit.core.fsutil import atomic_write_bytes
from winkit.i18n import Msg, msg


def _wanted(ctx: StepContext) -> list[Association]:
    d = ctx.recipe.default_apps
    if not d.associations_file or ctx.pendrive is None:
        return []
    keep = identifiers(ctx.catalogs.association_groups, d.groups)
    items = parse(ctx.payload(d.associations_file).read_bytes())
    return [a for a in items if a.identifier in keep]


class DefaultAppsStep(StepBase):
    #: O Windows protege a escolha de apps padrão num sistema em uso (R-54).
    live_safe = False

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        return (msg("preview.default_apps"),)

    def run(self, ctx: StepContext) -> StepResult:
        if ctx.phase != 1:
            return StepResult.skipped(msg("step.default_apps.manual"))
        try:
            wanted = _wanted(ctx)
        except (OSError, AssociationsError) as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)), recoverable=False)
        if not wanted:
            return StepResult.skipped(msg("step.not_in_recipe"))
        tmp = ctx.paths.base / "tmp" / "associacoes.xml"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(tmp, filtered_xml(wanted, {a.identifier for a in wanted}))
        code = ctx.services.associations.import_file(tmp)
        if code != 0:
            return StepResult.failed(msg("step.default_apps.code", code=code))
        return StepResult.ok(msg("step.default_apps.imported", n=len(wanted)))


class DefaultAppsVerifyStep(StepBase):
    live_safe = True

    def run(self, ctx: StepContext) -> StepResult:
        try:
            wanted = _wanted(ctx)
        except (OSError, AssociationsError) as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)), recoverable=False)
        reg = ctx.services.registry
        missing = [
            a.identifier
            for a in wanted
            if reg.get("HKCU", user_choice_key(a.identifier), "ProgId") != a.prog_id
        ]
        if missing:
            ctx.state.warnings.append(
                msg("summary.default_apps_pending", ids=", ".join(sorted(missing)))
            )
            return StepResult.ok(msg("step.default_apps.pending", n=len(missing)))
        return StepResult.ok(msg("step.default_apps.all_set"))
