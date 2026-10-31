"""Coleta de aplicativos do PC atual (PLANO.md §7.1, itens 8 e 9)."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from winkit.core import layout
from winkit.core.catalog.models import Catalogs
from winkit.core.errors import WinKitError
from winkit.core.installers.detect import default_args, detect_type, read_head
from winkit.core.inventory import (
    InstalledApp,
    match_inventory,
    merge_into_recipe,
    parse_winget_export,
    to_app_item,
)
from winkit.core.manifest.manifest import hash_file
from winkit.core.recipe.models import AppItem, InstallerSpec, Recipe, Scope
from winkit.core.text import slugify
from winkit.core.winget_manifest import parse_download_dir
from winkit.platform.inventory import AppInventory
from winkit.platform.winget import Winget

MIN_FREE_BYTES = 2 * 1024**3


def collect_inventory(
    inventory: AppInventory, winget: Winget, catalogs: Catalogs
) -> list[InstalledApp]:
    apps = inventory.installed()
    export: list[tuple[str, str]] = []
    if winget.available():
        with tempfile.TemporaryDirectory(prefix="winkit-") as tmp:
            path = Path(tmp) / "winget-export.json"
            if winget.export(path):
                export = parse_winget_export(path.read_text(encoding="utf-8-sig"))
    return match_inventory(apps, export, catalogs)


def add_inventory(
    recipe: Recipe, apps: list[InstalledApp], catalogs: Catalogs, *, include_redist: bool = False
) -> list[AppItem]:
    items = [to_app_item(a, catalogs) for a in apps if include_redist or not a.redistributable]
    return merge_into_recipe(recipe, items)


@dataclass(frozen=True)
class DownloadResult:
    app_id: str
    ok: bool
    message: str


def download_app(  # noqa: PLR0911 — cada retorno é um motivo diferente para o usuário
    winget: Winget, root: Path, item: AppItem, catalogs: Catalogs, *, free_bytes: int
) -> DownloadResult:
    """``winget download`` para ``WinKit/Apps/<id>/<versão>/`` e torna o app offline (§7.1.4)."""
    if not item.winget_id or item.winget_source == "msstore":
        return DownloadResult(
            item.id, False, "sem ID do winget comunitário (apps da Loja não baixam)"
        )
    if free_bytes < MIN_FREE_BYTES:
        return DownloadResult(item.id, False, "menos de 2 GB livres no pendrive")
    staging = layout.payload(root, f"Apps/{item.id}/.baixando")
    shutil.rmtree(staging, ignore_errors=True)
    code = winget.download(item.winget_id, staging)
    if code != 0:
        shutil.rmtree(staging, ignore_errors=True)
        return DownloadResult(item.id, False, f"winget download retornou 0x{code & 0xFFFFFFFF:08X}")
    try:
        pkg = parse_download_dir(staging)
    except WinKitError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        return DownloadResult(item.id, False, str(exc))
    if pkg.installer_type is None:
        shutil.rmtree(staging, ignore_errors=True)
        return DownloadResult(
            item.id, False, f'tipo "{pkg.raw_type}" não instala offline; ficará pelo winget online'
        )
    args = list(pkg.silent_args) or default_args(pkg.installer_type, catalogs.installer_signatures)
    if pkg.installer_type == "exe_custom" and not args:
        shutil.rmtree(staging, ignore_errors=True)
        return DownloadResult(item.id, False, "instalador sem parâmetro silencioso conhecido")
    final_rel = f"Apps/{item.id}/{slugify(pkg.version) if pkg.version else 'atual'}"
    final = layout.payload(root, final_rel)
    shutil.rmtree(final, ignore_errors=True)
    staging.rename(final)
    installer = final / pkg.installer.name
    item.installer = InstallerSpec(
        path=f"{final_rel}/{installer.name}",
        type=pkg.installer_type,
        args=args,
        sha256=hash_file(installer),
        timeout_minutes=item.installer.timeout_minutes if item.installer else 30,
    )
    item.source = "offline"
    if pkg.scope is not None:
        item.scope = pkg.scope
    return DownloadResult(item.id, True, f"{pkg.package_id} {pkg.version} ({pkg.raw_type})")


def add_local_installer(
    root: Path,
    recipe: Recipe,
    file: Path,
    *,
    name: str,
    catalogs: Catalogs,
    args: list[str] | None = None,
    scope: Scope = "machine",
) -> AppItem:
    """Copia um instalador para o pendrive e cria o app offline (já marcado)."""
    app_id = slugify(name)
    rel = f"Apps/{app_id}/local/{slugify(file.stem)}{file.suffix.lower()}"
    dest = layout.payload(root, rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file, dest)
    kind = detect_type(read_head(dest), dest.name, catalogs.installer_signatures)
    final_args = args if args is not None else default_args(kind, catalogs.installer_signatures)
    if kind == "squirrel":
        scope = "user"
    item = AppItem(
        id=app_id,
        name=name,
        selected=True,
        source="offline",
        scope=scope,
        installer=InstallerSpec(path=rel, type=kind, args=final_args, sha256=hash_file(dest)),
    )
    existing = {a.id: i for i, a in enumerate(recipe.apps)}
    if app_id in existing:
        recipe.apps[existing[app_id]] = item
    else:
        recipe.apps.append(item)
    return item
