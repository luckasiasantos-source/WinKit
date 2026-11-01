"""Etapa: trazer o backup do PC de volta depois de instalar (V3-10, D-051).

Acha o disco de backup pelo número de série (R-52) e restaura **somando**: arquivo que já existe
no destino nunca é trocado (D-007). Disco ausente = etapa pulada com motivo.
"""

from __future__ import annotations

from winkit.agent.steps.base import StepBase, StepContext, StepResult, local_path
from winkit.core.pc_backup import find_backups, restore, restore_targets
from winkit.core.volumes import resolve
from winkit.i18n import Msg, msg


class PcRestoreStep(StepBase):
    live_safe = True  # só acrescenta arquivos que faltam

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        return (msg("preview.pc_restore"),)

    def run(self, ctx: StepContext) -> StepResult:
        ref = ctx.recipe.pc_backup.destination
        if ref is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        v = resolve(ref, ctx.services.volumes.volumes())
        if v is None or not v.letter:
            return StepResult.skipped(
                msg("step.pc_restore.no_volume", label=ref.label or ref.serial)
            )
        found = find_backups([ctx.services.volumes.root(str(v.letter))])
        if not found:
            return StepResult.skipped(msg("step.pc_restore.none"))
        base, manifest = max(found, key=lambda bm: bm[1].updated_at)
        targets = restore_targets(manifest, ctx.folders())
        report = restore(base, manifest, targets, target_root=local_path)
        if report.failed:
            return StepResult.failed(
                msg("step.pc_restore.partial", copied=report.copied, failed=len(report.failed))
            )
        return StepResult.ok(msg("step.pc_restore.done", copied=report.copied, kept=report.kept))
