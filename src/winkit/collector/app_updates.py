"""Atualizar os instaladores do pendrive (V2-21, D-041).

Sem o módulo do winget para PowerShell, **verificar é baixar**: ``winget download`` numa pasta
temporária e a versão vem do manifesto baixado. Se a versão é maior:
1. a pasta nova entra no lugar (``Apps/<id>/<versão>``);
2. a receita é atualizada e **salva**;
3. só então a pasta antiga é apagada.
Qualquer falha antes do passo 3 deixa a versão antiga intacta.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from winkit.core import layout
from winkit.core.catalog.models import Catalogs
from winkit.core.errors import WinKitError
from winkit.core.installers.detect import default_args
from winkit.core.manifest.manifest import hash_file
from winkit.core.recipe.models import AppItem, InstallerSpec, Recipe
from winkit.core.text import slugify
from winkit.core.versions import compare
from winkit.core.winget_manifest import parse_download_dir
from winkit.platform.winget import Winget

Status = Literal["newer", "same", "older", "manual", "failed", "updated"]


@dataclass(frozen=True)
class UpdateCheck:
    app_id: str
    name: str
    current: str | None
    available: str | None
    status: Status
    detail: str = ""


def current_version(item: AppItem) -> str | None:
    if item.installer_version:
        return item.installer_version
    if item.installer and item.installer.path:  # receitas antigas: Apps/<id>/<versão>/arquivo
        parts = item.installer.path.split("/")
        return parts[2] if len(parts) >= 4 else None
    return None


def _old_folder(root: Path, item: AppItem) -> Path | None:
    if not item.installer or not item.installer.path:
        return None
    parts = item.installer.path.split("/")
    return layout.payload(root, "/".join(parts[:3])) if len(parts) >= 4 else None


def refresh_app(  # noqa: PLR0911 — um retorno por resultado possível
    winget: Winget,
    root: Path,
    item: AppItem,
    catalogs: Catalogs,
    *,
    apply: bool,
    save: Callable[[], None],
) -> UpdateCheck:
    current = current_version(item)
    if not item.winget_id or item.winget_source == "msstore":
        return UpdateCheck(item.id, item.name, current, None, "manual")
    staging = layout.payload(root, f"Apps/{item.id}/.verificando")
    shutil.rmtree(staging, ignore_errors=True)
    try:
        code = winget.download(item.winget_id, staging)
        if code != 0:
            return UpdateCheck(
                item.id, item.name, current, None, "failed", f"0x{code & 0xFFFFFFFF:08X}"
            )
        pkg = parse_download_dir(staging)
        available = pkg.version
        if not available or pkg.installer_type is None:
            return UpdateCheck(item.id, item.name, current, available, "failed", pkg.raw_type or "")
        order = compare(available, current) if current else 1
        status: Status = "newer" if order > 0 else "same" if order == 0 else "older"
        if status != "newer" or not apply:
            return UpdateCheck(item.id, item.name, current, available, status)
        old = _old_folder(root, item)
        final_rel = f"Apps/{item.id}/{slugify(available)}"
        final = layout.payload(root, final_rel)
        if old is not None and final.resolve() == old.resolve():
            return UpdateCheck(item.id, item.name, current, available, "same")
        shutil.rmtree(final, ignore_errors=True)
        staging.rename(final)
        installer = final / pkg.installer.name
        same_type = item.installer is not None and item.installer.type == pkg.installer_type
        args = (
            list(item.installer.args)
            if same_type and item.installer
            else list(pkg.silent_args)
            or default_args(pkg.installer_type, catalogs.installer_signatures)
        )
        item.installer = InstallerSpec(
            path=f"{final_rel}/{installer.name}",
            type=pkg.installer_type,
            args=args,
            sha256=hash_file(installer),
            timeout_minutes=item.installer.timeout_minutes if item.installer else 30,
        )
        item.installer_version = available
        save()  # a receita aponta para a versão nova antes de qualquer coisa ser apagada
        if old is not None and old.exists():
            shutil.rmtree(old, ignore_errors=True)
        return UpdateCheck(item.id, item.name, current, available, "updated")
    except (WinKitError, OSError) as exc:
        return UpdateCheck(item.id, item.name, current, None, "failed", str(exc))
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def refresh_apps(
    winget: Winget,
    root: Path,
    recipe: Recipe,
    catalogs: Catalogs,
    *,
    apply: bool,
    ids: list[str] | None,
    save: Callable[[], None],
    now: datetime,
) -> list[UpdateCheck]:
    out = []
    for item in recipe.selected_apps():
        if item.source != "offline" or (ids and item.id not in ids):
            continue
        out.append(refresh_app(winget, root, item, catalogs, apply=apply, save=save))
    recipe.meta.last_update_check = now
    save()
    return out


def needs_check(recipe: Recipe, now: datetime, *, days: int = 30) -> bool:
    """Faixa do Studio: há apps offline e a última verificação tem mais de ``days`` dias."""
    if not any(a.source == "offline" for a in recipe.selected_apps()):
        return False
    last = recipe.meta.last_update_check or recipe.meta.created_at
    return (now - last).days >= days
