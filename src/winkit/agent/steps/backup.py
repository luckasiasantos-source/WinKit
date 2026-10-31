"""Etapa: restaurar uma pasta ou arquivo de configuração (M6, itens 13, 14, 30).

Na Fase 1 o destino de moldes de perfil é o perfil Default (C:\\Users\\Default), que o
Windows clona para a conta nova (H4). Na Fase 2 é o perfil do usuário logado.
"""

from __future__ import annotations

import ntpath

from winkit.agent.steps.base import StepContext, StepResult, local_path
from winkit.core.errors import PathTemplateError, WinKitError
from winkit.core.paths import templates
from winkit.core.recipe.models import BackupItem
from winkit.i18n import t


def _item(ctx: StepContext) -> BackupItem | None:
    return ctx.recipe.backup(ctx.step.ref)


def destination(ctx: StepContext, item: BackupItem) -> str:
    return templates.resolve(item.template, ctx.folders())


class BackupStep:
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
            return StepResult.skipped("backup não está mais na receita")
        parsed = templates.parse(item.template)
        if parsed.is_absolute and parsed.drive and not local_path(parsed.drive + "\\").exists():
            return StepResult.skipped(t("step.drive_missing", drive=parsed.drive))
        try:
            dest_str = destination(ctx, item)
        except PathTemplateError as exc:
            return StepResult.failed(str(exc), recoverable=False)
        src = ctx.payload(item.data_path)
        if not src.is_dir():
            return StepResult.failed(
                f"backup ausente no pendrive: {item.data_path}", recoverable=False
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
                        f"arquivo {name} não está no backup", recoverable=False
                    )
                copied = copier.copy_file(source_file, dest, policy=item.on_conflict)
                note = None if copied else "já existia no destino (mantido)"
                return StepResult.ok(note)
            copier.restore_tree(src, dest, policy=item.on_conflict, log=log)
        except (OSError, WinKitError) as exc:
            return StepResult.failed(str(exc))
        return StepResult.ok(f"restaurado em {dest_str}")
