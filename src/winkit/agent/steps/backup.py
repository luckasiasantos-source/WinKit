"""Etapa: restaurar uma pasta ou arquivo de configuração (M6, itens 13, 14, 30).

Na Fase 1 o destino de moldes de perfil é o perfil Default (C:\\Users\\Default), que o
Windows clona para a conta nova (H4). Na Fase 2 é o perfil do usuário logado.
"""

from __future__ import annotations

import ntpath
from pathlib import Path

from winkit.agent.steps.base import StepBase, StepContext, StepResult, item, local_path
from winkit.core.errors import PathTemplateError, WinKitError
from winkit.core.live import PreviewItem
from winkit.core.paths import templates
from winkit.core.recipe.models import BackupItem
from winkit.i18n import msg


def _item(ctx: StepContext) -> BackupItem | None:
    return ctx.recipe.backup(ctx.step.ref)


def destination(ctx: StepContext, item: BackupItem) -> str:
    return templates.resolve(item.template, ctx.folders())


def _count(src: Path, dest: Path) -> tuple[int, int]:
    """(arquivos no backup, quantos já existem no destino) — só leitura."""
    total = existing = 0
    for path in src.rglob("*"):
        if path.is_file():
            total += 1
            if (dest / path.relative_to(src)).exists():
                existing += 1
    return total, existing


class BackupStep(StepBase):
    def preview(self, ctx: StepContext) -> PreviewItem:
        """Quantos arquivos seriam copiados e quantos já existem (mantidos no modo mesclar)."""
        b = _item(ctx)
        if b is None or ctx.pendrive is None:
            return item(ctx, "not_applicable", (msg("step.not_in_recipe"),))
        try:
            dest_str = destination(ctx, b)
        except PathTemplateError as exc:
            return item(ctx, "not_applicable", (msg("step.failed_generic", detail=str(exc)),))
        src, dest = ctx.payload(b.data_path), local_path(dest_str)
        if not src.is_dir():
            return item(ctx, "not_applicable", (msg("step.backup_missing", path=b.data_path),))
        if b.kind == "file":
            name = ntpath.basename(dest_str)
            total, existing = int((src / name).is_file()), int(dest.exists())
        else:
            total, existing = _count(src, dest)
        overwrite = b.on_conflict == "overwrite"
        if total == 0 or (existing == total and not overwrite):
            return item(ctx, "already_done")
        changes = (msg("preview.backup_copy", new=total - existing, kept=existing, path=dest_str),)
        warnings = (msg("preview.backup_overwrite", n=existing),) if overwrite and existing else ()
        return item(ctx, "will_change", changes, warnings)

    def check(self, ctx: StepContext) -> bool:
        item = _item(ctx)
        if item is None or item.on_conflict != "skip":
            return False  # mesclar/sobrescrever são idempotentes; rodar de novo é seguro
        try:
            return local_path(destination(ctx, item)).exists()
        except PathTemplateError:
            return False

    def run(self, ctx: StepContext) -> StepResult:  # noqa: PLR0911 — um motivo por saída
        item = _item(ctx)
        if item is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        parsed = templates.parse(item.template)
        if parsed.is_absolute and parsed.drive and not local_path(parsed.drive + "\\").exists():
            return StepResult.skipped(msg("step.drive_missing", drive=parsed.drive))
        try:
            dest_str = destination(ctx, item)
        except PathTemplateError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)), recoverable=False)
        src = ctx.payload(item.data_path)
        if not src.is_dir():
            return StepResult.failed(
                msg("step.backup_missing", path=item.data_path), recoverable=False
            )
        dest = local_path(dest_str)
        copier = ctx.services.copier
        log = ctx.log.step_log(ctx.step.id)
        try:
            if item.kind == "file":
                name = ntpath.basename(dest_str)
                source_file = src / name
                if not source_file.is_file():
                    return StepResult.failed(
                        msg("step.backup_file_missing", name=name), recoverable=False
                    )
                copied = copier.copy_file(source_file, dest, policy=item.on_conflict)
                note = None if copied else msg("step.kept_existing")
                return StepResult.ok(note)
            copier.restore_tree(src, dest, policy=item.on_conflict, log=log)
        except (OSError, WinKitError) as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        return StepResult.ok(msg("step.restored_to", path=dest_str))
