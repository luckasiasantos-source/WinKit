"""Etapa: instalar uma fonte para todos os usuários (V2-07).

Copia para ``%SystemRoot%\\Fonts`` e grava o valor em ``HKLM\\...\\Fonts``. Um arquivo de mesmo
nome com outro conteúdo nunca é sobrescrito: a cópia ganha o sufixo ``_winkit``. Ao vivo, a
fonte também é carregada na sessão (``AddFontResourceW``).
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from winkit.agent.steps.base import StepBase, StepContext, StepResult, local_path
from winkit.core.fonts import FONTS_KEY, FontError, read_names, registry_name
from winkit.core.recipe.models import FontItem
from winkit.i18n import Msg, msg


def _item(ctx: StepContext) -> FontItem | None:
    return next((f for f in ctx.recipe.fonts if f.id == ctx.step.ref), None)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fonts_dir(ctx: StepContext) -> Path:
    return local_path(ctx.services.folders.windows_dir()) / "Fonts"


def _destination(ctx: StepContext, item: FontItem) -> Path:
    """O nome original, ou com ``_winkit`` se já existe outro arquivo com esse nome."""
    name = Path(item.file).name
    dest = _fonts_dir(ctx) / name
    if dest.exists() and item.sha256 and _sha(dest) != item.sha256:
        dest = dest.with_name(f"{dest.stem}_winkit{dest.suffix}")
    return dest


class FontStep(StepBase):
    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        item = _item(ctx)
        if item is None or not item.file or not item.sha256:
            return False
        dest = _destination(ctx, item)
        if not dest.is_file() or _sha(dest) != item.sha256:
            return False
        values = ctx.services.registry.values("HKLM", FONTS_KEY)
        return any(
            isinstance(v, str) and v.casefold() == dest.name.casefold() for v in values.values()
        )

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        item = _item(ctx)
        return (msg("preview.font", name=item.full_name),) if item else ()

    def run(self, ctx: StepContext) -> StepResult:
        item = _item(ctx)
        if item is None or not item.file:
            return StepResult.skipped(msg("step.not_in_recipe"))
        src = ctx.payload(item.file)
        try:
            data = src.read_bytes()
            names = read_names(data)
        except (OSError, FontError) as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)), recoverable=False)
        if item.sha256 and hashlib.sha256(data).hexdigest() != item.sha256:
            return StepResult.failed(msg("step.font.changed"), recoverable=False)
        dest = _destination(ctx, item)
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copyfile(src, dest)
            ctx.services.registry.set("HKLM", FONTS_KEY, registry_name(names), "sz", dest.name)
        except OSError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        if ctx.mode == "live" and not ctx.services.font_loader.load(dest):
            ctx.log.warning(
                f"fonte instalada, mas não carregada na sessão: {dest.name}", step=ctx.step.id
            )
        return StepResult.ok(msg("step.font.installed", name=item.full_name))
