"""Linha de comando do WinKit Studio (D-004).

Comandos:
  winkit pendrive listar
  winkit receita nova --usuario NOME [--perfil padrao] [--sobrescrever]
  winkit plano [--windows 11 --build 26100] [--sem-fase1]
  winkit construir [--somente-xml] [--agente PASTA]
  winkit validar

Opções globais: --pendrive E:  ou  --raiz PASTA (usa uma pasta como se fosse o pendrive).
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from winkit import __version__
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.phases import Runtime
from winkit.builder import target as targets
from winkit.builder.build import (
    BuildOptions,
    build,
    ensure_marker,
    load_profile_recipe,
    save_profile_recipe,
)
from winkit.builder.validate import validate_pendrive
from winkit.collector import apps as app_collector
from winkit.collector import backups as backup_collector
from winkit.collector import drivers as driver_collector
from winkit.core import layout
from winkit.core.catalog.loader import default_catalogs
from winkit.core.errors import RecipeError, WinKitError
from winkit.core.planner.models import PlanContext
from winkit.core.planner.planner import plan
from winkit.core.recipe.io import new_recipe
from winkit.core.recipe.models import Recipe
from winkit.core.recipe.validation import validate_recipe
from winkit.core.text import human_size
from winkit.core.winget_manifest import split_args
from winkit.i18n import CHOICES, current_language, normalize, render, set_language, t, tn
from winkit.platform.locale import detect_language
from winkit.platform.services import Services, real_services
from winkit.platform.session import is_admin
from winkit.platform.system import is_windows
from winkit.platform.vss import PendingSnapshots

Out = Callable[[str], None]


def _out(text: str) -> None:
    sys.stdout.write(text + "\n")


def _gib(n: int) -> str:
    return f"{n / 1024**3:.1f} GB"


def _now() -> datetime:
    return datetime.now(UTC)


def _cache_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".cache") / "WinKit" / "iso-cache.json"


def default_agent_source() -> Path | None:
    """No pacote, o Agente fica ao lado da pasta da CLI: WinKit-x.y\\winkit-agent."""
    if getattr(sys, "frozen", False):
        candidate = Path(sys.executable).resolve().parent.parent / "winkit-agent"
        if (candidate / layout.AGENT_EXE_NAME).is_file():
            return candidate
    return None


def _target(args: argparse.Namespace, services: Services) -> targets.Target:
    if args.raiz:
        return targets.from_folder(Path(args.raiz), args.sistema_arquivos)
    _require_admin()
    return targets.resolve_target(services.disks, args.pendrive)


def _require_admin() -> None:
    if is_windows() and not is_admin():
        raise WinKitError(t("error.needs_admin"))


# ------------------------------------------------------------------ comandos
def cmd_pendrive_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    del args
    _require_admin()
    found = targets.list_targets(services.disks)
    if not found:
        out(t("pendrive.none"))
        return 1
    for v in found:
        out(
            f"{v.data_letter}  {v.disk_name} ({v.bus_type})  {v.file_system}  "
            + t("cli.free_of", free=_gib(v.free), size=_gib(v.size))
        )
    return 0


def cmd_receita_nova(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    path = tgt.root / layout.recipe_file(args.perfil)
    if path.exists() and not args.sobrescrever:
        out(t("cli.recipe_exists", path=path))
        return 1
    marker = ensure_marker(tgt.root, _now())
    recipe = new_recipe(
        pendrive_id=marker.pendrive_id,
        username=args.usuario,
        profile_id=args.perfil,
        source_pc=os.environ.get("COMPUTERNAME"),
        now=_now(),
        regional=services.regional(),
    )
    if args.nome_pc:
        recipe.windows.computer_name = args.nome_pc
    report = validate_recipe(recipe, default_catalogs())
    if not report.ok:
        out(t("recipe.invalid", problems="\n".join(report.errors)))
        return 1
    saved = save_profile_recipe(tgt.root, recipe)
    out(t("cli.recipe_created", path=saved))
    return 0


def cmd_plano(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    ctx = PlanContext(os_major=args.windows, build=args.build, phase1_ran=not args.sem_fase1)
    p = plan(recipe, default_catalogs(), ctx)
    for phase in (1, 2):
        steps = p.phase(phase)
        out(tn("cli.plan_phase", len(steps), phase=phase))
        for s in steps:
            flags = []
            if s.user_choice:
                flags.append(t("cli.flag_ask"))
            if s.moved_from_phase1:
                flags.append(t("cli.flag_from_phase1"))
            if s.needs_network:
                flags.append(t("cli.flag_internet"))
            suffix = f"  [{', '.join(flags)}]" if flags else ""
            out(f"  - {s.title}{suffix}")
    if p.excluded:
        out(t("cli.excluded"))
        for e in p.excluded:
            out(f"  - {e.kind} {e.ref}: {e.reason}")
    return 0


def cmd_construir(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    out(t("cli.pendrive", description=tgt.description))
    options = BuildOptions(
        profile_id=args.perfil,
        xml_only=args.somente_xml,
        agent_source=Path(args.agente) if args.agente else default_agent_source(),
        iso_cache=None if args.raiz else _cache_path(),
    )
    report = build(tgt, services.disks, default_catalogs(), options, now=_now())
    for iso in report.isos:
        out(
            t(
                "builder.iso_found",
                name=iso.name,
                os=iso.os_major,
                build=iso.build,
                arch=iso.architecture,
                langs=", ".join(iso.languages),
            )
        )
    for image, reason in report.skipped:
        out(t("cli.iso_ignored", image=image, reason=reason))
    for tpl in report.templates:
        out(t("cli.template_written", name=tpl))
    for name in report.removed_templates:
        out(t("cli.template_removed", name=name))
    if report.warnings:
        out(t("validate.warnings", count=len(report.warnings)))
        for w in report.warnings:
            out(f"  ! {w}")
    if report.sizes:
        used = ", ".join(f"{t(f'size.{k}')} {human_size(v)}" for k, v in report.sizes.items())
        out(t("cli.space_used", used=used, free=human_size(tgt.free)))
    if report.manifest_files:
        a, c, r = report.manifest_changes
        out(t("cli.manifest", files=report.manifest_files, added=a, changed=c, removed=r))
    out(t("builder.done", root=tgt.root))
    return 0


def cmd_validar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    rep = validate_pendrive(
        tgt.root, default_catalogs(), profile_id=args.perfil, file_system=tgt.file_system
    )
    if rep.warnings:
        out(t("validate.warnings", count=len(rep.warnings)))
        for w in rep.warnings:
            out(f"  ! {w}")
    if rep.ok:
        out(t("validate.ok"))
        return 0
    out(tn("validate.problems", len(rep.problems)))
    for p in rep.problems:
        out(f"  x {p}")
    return 1


def cmd_coletar_drivers(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    _require_admin()
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    candidates = driver_collector.list_candidates(services.drivers, catalogs)
    out(tn("collect.drivers_found", len(candidates)))
    wanted_classes = {c.casefold() for c in args.classe or []}
    chosen = []
    for c in candidates:
        if args.todos:
            pick = True
        elif wanted_classes:
            pick = c.driver.class_name.casefold() in wanted_classes
        else:
            pick = c.recommended
        mark = "x" if pick else " "
        d = c.driver
        out(f"  [{mark}] {c.label:38} {d.provider} {d.version} ({d.published_name})")
        if pick:
            chosen.append(c)
    if args.listar:
        return 0
    added = driver_collector.export_drivers(services.drivers, chosen, root=tgt.root, recipe=recipe)
    recipe.meta.updated_at = _now()
    save_profile_recipe(tgt.root, recipe)
    out(tn("cli.drivers_exported", len(added)))
    return 0


def _save(tgt: targets.Target, recipe: Recipe) -> None:
    recipe.meta.updated_at = _now()
    save_profile_recipe(tgt.root, recipe)


def _source_label(source: str, winget_id: str | None) -> str:
    if source == "winget_online":
        return f"winget ({winget_id})"
    if source == "portable":
        return t("cli.src_portable")
    return t("cli.src_offline")


def cmd_coletar_apps(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    apps = app_collector.collect_inventory(services.inventory, services.winget, catalogs)
    out(tn("collect.apps_found", len(apps)))
    added = app_collector.add_inventory(
        recipe, apps, catalogs, include_redist=args.incluir_redistribuiveis
    )
    _save(tgt, recipe)
    out(tn("cli.apps_added", len(added)))
    return cmd_apps_listar(args, services, out)


def cmd_apps_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    for a in sorted(recipe.apps, key=lambda x: (not x.selected, x.order, x.name.casefold())):
        mark = "x" if a.selected else " "
        where = t("cli.scope_user") if a.scope == "user" else t("cli.scope_machine")
        label = _source_label(a.source, a.winget_id)
        out(f"  [{mark}] {a.id:28} {a.name[:36]:36} {where:11} {label}")
    return 0


def cmd_apps_marcar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    value = args.command_value
    missing = []
    for app_id in args.ids:
        item = recipe.app(app_id)
        if item is None:
            missing.append(app_id)
            continue
        item.selected = value
        if args.ordem is not None:
            item.order = args.ordem
        if args.decidir_na_hora is not None:
            item.decide_at_runtime = args.decidir_na_hora
    _save(tgt, recipe)
    if missing:
        out(t("cli.not_found", ids=", ".join(missing)))
        return 1
    out(tn("cli.apps_selected" if value else "cli.apps_deselected", len(args.ids)))
    return 0


def cmd_apps_baixar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    if args.ids:
        items = [a for a in recipe.apps if a.id in set(args.ids)]
    else:
        items = [
            a
            for a in recipe.selected_apps()
            if a.source == "winget_online" and a.winget_source == "winget"
        ]
    if not services.winget.available():
        out(t("cli.winget_missing"))
        return 1
    failures = 0
    for item in items:
        free = targets.from_folder(tgt.root).free if args.raiz else tgt.free
        res = app_collector.download_app(services.winget, tgt.root, item, catalogs, free_bytes=free)
        out(f"  {t('cli.ok') if res.ok else t('cli.no')} {item.id}: {res.message}")
        failures += 0 if res.ok else 1
    _save(tgt, recipe)
    return 0 if failures == 0 else 1


def cmd_apps_adicionar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    item = app_collector.add_local_installer(
        tgt.root,
        recipe,
        Path(args.instalador),
        name=args.nome,
        catalogs=default_catalogs(),
        args=split_args(args.args) if args.args is not None else None,
        scope=args.escopo,
    )
    _save(tgt, recipe)
    assert item.installer is not None  # noqa: S101
    out(
        t(
            "cli.app_added",
            name=item.name,
            type=item.installer.type,
            args=" ".join(item.installer.args) or t("cli.none"),
        )
    )
    if item.installer.type == "unknown" and not item.installer.args:
        out(t("cli.unknown_type"))
        return 1
    return 0


def _old_folders(services: Services) -> dict[str, str]:
    return {**services.folders.machine(), **services.folders.current_user()}


def _studio_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".cache") / "WinKit"


def _free(tgt: targets.Target) -> int:
    return targets.from_folder(tgt.root).free


def cmd_coletar_backups(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    suggestions = backup_collector.suggest(
        recipe, catalogs, _old_folders(services), services.volume_root
    )
    if not suggestions:
        out(t("cli.no_suggestions"))
        return 0
    added = 0
    for sug in suggestions:
        pick = sug.recommended and sug.exists
        mark = "x" if pick else " "
        size = human_size(sug.size) if sug.exists else t("studio.backups.missing_here")
        out(f"  [{mark}] {sug.app_name}: {sug.template}  ({size})")
        if sug.warning:
            out(f"        ! {sug.warning}")
        if pick and args.adicionar_recomendados:
            backup_collector.add_suggestion(recipe, catalogs, sug)
            added += 1
    if args.adicionar_recomendados:
        _save(tgt, recipe)
        out(tn("cli.backups_added", added))
    return 0


def cmd_backup_adicionar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    literal = args.caminho
    local = backup_collector.local_source(services.volume_root(literal[:2].upper()), literal)
    kind: Literal["file", "folder"] = "file" if local.is_file() else "folder"
    item, warning = backup_collector.add_backup(
        recipe,
        default_catalogs(),
        name=args.nome or Path(literal.replace("\\", "/")).name,
        literal=literal,
        old_folders=_old_folders(services),
        windows_dir=services.folders.windows_dir(),
        kind=kind,
        on_conflict=args.conflito,
        decide_at_runtime=args.decidir_na_hora,
    )
    _save(tgt, recipe)
    out(t("cli.backup_added", name=item.name, id=item.id, template=item.template))
    if warning:
        out(f"  ! {warning}")
    out(t("cli.capture_hint", id=item.id))
    return 0


def cmd_backup_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    for b in recipe.backups:
        mark = "x" if b.selected else " "
        data = layout.payload(tgt.root, b.data_path)
        state = t("studio.backups.captured") if data.exists() else t("studio.backups.not_captured")
        out(f"  [{mark}] {b.id:30} {b.template}  [{b.on_conflict}] {state}")
        for w in b.warnings:
            out(f"        ! {w}")
    return 0


def _capture(
    args: argparse.Namespace,
    services: Services,
    tgt: targets.Target,
    recipe: Recipe,
    out: Out,
    *,
    only: set[str] | None,
) -> bool:
    _require_admin()
    studio = _studio_dir()
    report = backup_collector.capture(
        tgt.root,
        recipe,
        default_catalogs(),
        copier=services.copier,
        vss=services.vss,
        pending=PendingSnapshots(studio / "vss-pendentes.json"),
        old_folders=_old_folders(services),
        link_base=studio,
        free_bytes=_free(tgt),
        use_vss=not getattr(args, "sem_vss", False),
        only=only,
        volume_root=services.volume_root,
        now=_now,
    )
    for note in report.notes:
        out(f"  ! {note}")
    for item in report.items:
        flag = t("cli.ok") if item.ok else t("cli.no")
        vss = f" ({t('cli.shadow_copy')})" if item.used_vss else ""
        out(f"  {flag} {item.backup_id}: {item.message}{vss}")
        for w in item.warnings:
            out(f"        ! {w}")
    _save(tgt, recipe)
    return report.ok


def cmd_backup_capturar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    ok = _capture(args, services, tgt, recipe, out, only=set(args.ids) if args.ids else None)
    return 0 if ok else 1


def cmd_backup_remover(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    item = recipe.backup(args.id)
    if item is None:
        out(t("cli.backup_not_found", id=args.id))
        return 1
    recipe.backups = [b for b in recipe.backups if b.id != args.id]
    folder = layout.payload(tgt.root, item.data_path).parent
    if folder.is_dir() and folder.parent.name == "Backups":
        shutil.rmtree(folder)
    _save(tgt, recipe)
    out(t("cli.backup_removed", id=args.id))
    return 0


def cmd_apps_portatil(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    app, item = backup_collector.add_portable_app(
        recipe,
        default_catalogs(),
        literal_folder=args.pasta,
        old_folders=_old_folders(services),
        name=args.nome,
        exe=args.exe,
        windows_dir=services.folders.windows_dir(),
    )
    _save(tgt, recipe)
    out(t("cli.portable_added", name=app.name, template=item.template, exe=args.exe))
    out(t("cli.capture_hint", id=item.id))
    return 0


def _agent_runtime() -> Runtime:
    from winkit.agent.main import build_runtime  # noqa: PLC0415 — só o "aplicar" precisa do Agente

    return build_runtime()


#: Monta o Agente para ``winkit aplicar`` (os testes trocam por um com dublês).
AGENT_RUNTIME: Callable[[], Runtime] = _agent_runtime


def cmd_aplicar(args: argparse.Namespace, services: Services, out: Out) -> int:
    """V2-03: aplica a receita neste Windows, com prévia e ponto de restauração (D-033)."""
    if args.sem_ponto_de_restauracao and not args.sei_o_que_estou_fazendo:
        out(t("cli.live_needs_confirmation"))
        return 2
    root = _target(args, services).root
    kinds = frozenset(k.strip() for k in (args.somente or "").split(",") if k.strip())
    options = LiveOptions(
        root=root,
        profile_id=args.perfil,
        simulate=args.simular,
        only_kinds=kinds or None,  # type: ignore[arg-type]
        restore_point=not args.sem_ponto_de_restauracao,
        language=current_language(),
    )
    result = run_live(AGENT_RUNTIME(), options)
    if result.preview is not None:
        for item in result.preview.items:
            out(f"  [{t(f'preview.status.{item.status}')}] {item.title}")
            for change in (*item.changes, *item.warnings):
                out(f"      {render(change)}")
        for step_id in result.preview.not_live_safe:
            out(f"  [{t('preview.status.not_applicable')}] {step_id}: {t('step.not_live_safe')}")
        return 0
    counts = result.counts
    out(
        t(
            "cli.live_done",
            done=counts.get("done", 0),
            failed=counts.get("failed", 0),
            skipped=counts.get("skipped", 0),
        )
    )
    if result.summary_html is not None:
        out(t("cli.summary_at", path=result.summary_html))
    return result.code


def cmd_sincronizar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    if not args.sem_backups:
        recipe = load_profile_recipe(tgt.root, args.perfil)
        out(t("cli.recapturing"))
        _capture(args, services, tgt, recipe, out, only=None)
    args.somente_xml = False
    args.agente = None
    return cmd_construir(args, services, out)


# ------------------------------------------------------------------ parser
def _add_collect_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    col = sub.add_parser("coletar", aliases=["collect"], help=t("cli.h.collect"))
    col_sub = col.add_subparsers(dest="what", required=True)
    cdrv = col_sub.add_parser("drivers", parents=[common], help=t("cli.h.collect_drivers"))
    cdrv.add_argument("--listar", action="store_true", help=t("cli.h.list_only"))
    cdrv.add_argument("--todos", action="store_true", help=t("cli.h.all_classes"))
    cdrv.add_argument("--classe", action="append", help=t("cli.h.classes"))
    cdrv.set_defaults(func=cmd_coletar_drivers)

    cbk = col_sub.add_parser("backups", parents=[common], help=t("cli.h.collect_backups"))
    cbk.add_argument("--adicionar-recomendados", action="store_true")
    cbk.set_defaults(func=cmd_coletar_backups)

    capp = col_sub.add_parser("apps", parents=[common], help=t("cli.h.collect_apps"))
    capp.add_argument(
        "--incluir-redistribuiveis",
        action="store_true",
        help=t("cli.h.redist"),
    )
    capp.set_defaults(func=cmd_coletar_apps)


def _add_apps_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    apps = sub.add_parser("apps", help=t("cli.h.apps"))
    apps_sub = apps.add_subparsers(dest="action", required=True)
    apps_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_apps_listar
    )
    for name, alias, value in (("marcar", "select", True), ("desmarcar", "deselect", False)):
        mk = apps_sub.add_parser(name, aliases=[alias], parents=[common])
        mk.add_argument("ids", nargs="+", help=t("cli.h.app_ids"))
        mk.add_argument("--ordem", type=int, help=t("cli.h.order"))
        mk.add_argument(
            "--decidir-na-hora",
            action=argparse.BooleanOptionalAction,
            default=None,
            help=t("cli.h.decide_later"),
        )
        mk.set_defaults(func=cmd_apps_marcar, command_value=value)
    bx = apps_sub.add_parser(
        "baixar", aliases=["download"], parents=[common], help=t("cli.h.download")
    )
    bx.add_argument("ids", nargs="*", help=t("cli.h.download_ids"))
    bx.set_defaults(func=cmd_apps_baixar)
    ad = apps_sub.add_parser(
        "adicionar", aliases=["add"], parents=[common], help=t("cli.h.add_app")
    )
    ad.add_argument("--instalador", required=True, help=t("cli.h.installer"))
    ad.add_argument("--nome", required=True, help=t("cli.h.app_name"))
    ad.add_argument("--args", help=t("cli.h.silent_args"))
    ad.add_argument("--escopo", choices=["machine", "user"], default="machine")
    ad.set_defaults(func=cmd_apps_adicionar)
    pt = apps_sub.add_parser(
        "portatil", aliases=["portable"], parents=[common], help=t("cli.h.portable")
    )
    pt.add_argument("--pasta", required=True, help=t("cli.h.portable_folder"))
    pt.add_argument("--nome", required=True)
    pt.add_argument("--exe", required=True, help=t("cli.h.portable_exe"))
    pt.set_defaults(func=cmd_apps_portatil)


def _add_backup_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    bk = sub.add_parser("backup", help=t("cli.h.backup"))
    bk_sub = bk.add_subparsers(dest="action", required=True)
    add = bk_sub.add_parser(
        "adicionar", aliases=["add"], parents=[common], help=t("cli.h.backup_add")
    )
    add.add_argument("caminho", help=t("cli.h.backup_path"))
    add.add_argument("--nome")
    add.add_argument(
        "--conflito",
        choices=["merge", "overwrite", "skip"],
        default="merge",
        help=t("cli.h.conflict"),
    )
    add.add_argument("--decidir-na-hora", action="store_true")
    add.set_defaults(func=cmd_backup_adicionar)
    bk_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_backup_listar
    )
    cap = bk_sub.add_parser(
        "capturar", aliases=["capture"], parents=[common], help=t("cli.h.capture")
    )
    cap.add_argument("ids", nargs="*")
    cap.add_argument("--sem-vss", action="store_true", help=t("cli.h.no_vss"))
    cap.set_defaults(func=cmd_backup_capturar)
    rm = bk_sub.add_parser("remover", aliases=["remove"], parents=[common])
    rm.add_argument("id")
    rm.set_defaults(func=cmd_backup_remover)

    sync = sub.add_parser(
        "sincronizar",
        aliases=["sync"],
        parents=[common],
        help=t("cli.h.sync"),
    )
    sync.add_argument("--sem-backups", action="store_true")
    sync.add_argument("--sem-vss", action="store_true")
    sync.set_defaults(func=cmd_sincronizar)


def choose_language(argv: Sequence[str]) -> None:
    """Idioma antes de montar o parser, para a ajuda já sair traduzida (D-030, D-032).

    Ordem: ``--idioma`` → ``WINKIT_LANG`` → idioma do Windows.
    """
    chosen = None
    for i, arg in enumerate(argv):
        if arg == "--idioma" and i + 1 < len(argv):
            chosen = argv[i + 1]
        elif arg.startswith("--idioma="):
            chosen = arg.split("=", 1)[1]
    if chosen and chosen != "auto" and chosen in CHOICES:
        set_language(normalize(chosen))
    else:
        set_language(detect_language())


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--pendrive", help=t("cli.h.pendrive"))
    common.add_argument("--raiz", help=t("cli.h.root"))
    common.add_argument("--sistema-arquivos", default="exFAT", help=argparse.SUPPRESS)
    common.add_argument("--perfil", default="padrao", help=t("cli.h.profile"))

    parser = argparse.ArgumentParser(prog="winkit", description=t("cli.h.description"))
    parser.add_argument("--version", action="version", version=f"WinKit {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help=t("cli.h.verbose"))
    parser.add_argument("--idioma", choices=CHOICES, default="auto", help=t("cli.h.language"))
    sub = parser.add_subparsers(dest="command", required=True)

    pend = sub.add_parser("pendrive", aliases=["drive"], help=t("cli.h.pendrive_cmd"))
    pend_sub = pend.add_subparsers(dest="action", required=True)
    pend_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_pendrive_listar
    )

    rec = sub.add_parser("receita", aliases=["recipe"], help=t("cli.h.recipe"))
    rec_sub = rec.add_subparsers(dest="action", required=True)
    nova = rec_sub.add_parser("nova", aliases=["new"], parents=[common], help=t("cli.h.recipe_new"))
    nova.add_argument("--usuario", required=True, help=t("cli.h.user"))
    nova.add_argument("--nome-pc", help=t("cli.h.pc_name"))
    nova.add_argument("--sobrescrever", action="store_true")
    nova.set_defaults(func=cmd_receita_nova)

    pl = sub.add_parser("plano", aliases=["plan"], parents=[common], help=t("cli.h.plan"))
    pl.add_argument("--windows", type=int, choices=[10, 11], default=11)
    pl.add_argument("--build", type=int, default=None)
    pl.add_argument("--sem-fase1", action="store_true", help=t("cli.h.no_phase1"))
    pl.set_defaults(func=cmd_plano)

    cons = sub.add_parser("construir", aliases=["build"], parents=[common], help=t("cli.h.build"))
    cons.add_argument(
        "--somente-xml",
        action="store_true",
        help=t("cli.h.xml_only"),
    )
    cons.add_argument("--agente", help=t("cli.h.agent_folder"))
    cons.set_defaults(func=cmd_construir)

    _add_collect_parsers(sub, common)
    _add_apps_parsers(sub, common)
    _add_backup_parsers(sub, common)

    ap = sub.add_parser("aplicar", aliases=["apply"], parents=[common], help=t("cli.h.apply"))
    ap.add_argument("--simular", action="store_true", help=t("cli.h.simulate"))
    ap.add_argument("--somente", help=t("cli.h.only_kinds"))
    ap.add_argument("--sem-ponto-de-restauracao", action="store_true", help=t("cli.h.no_restore"))
    ap.add_argument("--sei-o-que-estou-fazendo", action="store_true", help=argparse.SUPPRESS)
    ap.set_defaults(func=cmd_aplicar)

    val = sub.add_parser(
        "validar", aliases=["validate"], parents=[common], help=t("cli.h.validate")
    )
    val.set_defaults(func=cmd_validar)
    return parser


def main(
    argv: Sequence[str] | None = None, *, services: Services | None = None, out: Out = _out
) -> int:
    choose_language(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        svc = services or real_services()
        func: Callable[[argparse.Namespace, Services, Out], int] = args.func
        return func(args, svc, out)
    except RecipeError as exc:
        out(str(exc))
        return 2
    except WinKitError as exc:
        out(t("cli.error", detail=exc))
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
