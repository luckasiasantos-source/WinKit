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
from winkit.collector import app_updates
from winkit.collector import apps as app_collector
from winkit.collector import associations as assoc_collector
from winkit.collector import backups as backup_collector
from winkit.collector import browsers as browser_collector
from winkit.collector import drivers as driver_collector
from winkit.collector import env as env_collector
from winkit.collector import features as feature_collector
from winkit.collector import fonts as font_collector
from winkit.collector import games as games_collector
from winkit.collector import netdrives as netdrive_collector
from winkit.collector import personal as personal_collector
from winkit.collector import start_layout as start_collector
from winkit.collector import user_folders as folders_collector
from winkit.collector import wifi as wifi_collector
from winkit.core import dns as dns_rules
from winkit.core import layout, share
from winkit.core.browsers import undo_operations
from winkit.core.catalog.loader import default_catalogs
from winkit.core.errors import RecipeError, WinKitError
from winkit.core.fsutil import atomic_write_text
from winkit.core.maintenance import DAYS, TASK_FOLDER
from winkit.core.planner.models import PlanContext
from winkit.core.planner.planner import plan
from winkit.core.presets import apply_preset, preview_preset
from winkit.core.recipe.io import new_recipe
from winkit.core.recipe.models import (
    BrowserConfig,
    EnvScope,
    EnvVar,
    ExtraAccount,
    Recipe,
    UserFolders,
)
from winkit.core.recipe.validation import username_problem, validate_recipe
from winkit.core.text import human_size
from winkit.core.user_folders import ORDER as USER_FOLDER_ORDER
from winkit.core.user_folders import default_folders
from winkit.core.volumes import by_letter
from winkit.core.volumes import ref_for as volume_ref
from winkit.core.volumes import resolve as resolve_volume
from winkit.core.winget_manifest import split_args
from winkit.i18n import CHOICES, current_language, normalize, render, set_language, t, tn
from winkit.platform import browsers as browser_policies
from winkit.platform import hosts
from winkit.platform.environment import WindowsEnvironment
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
    return targets.resolve_target(services.disks, args.pendrive, services.volume_root)


def _require_admin() -> None:
    if is_windows() and not is_admin():
        raise WinKitError(t("error.needs_admin"))


# ------------------------------------------------------------------ comandos
def cmd_pendrive_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    del args
    _require_admin()
    found = targets.list_targets(services.disks, services.volume_root)
    if not found:
        out(t("pendrive.none"))
        return 1
    for v in found:
        out(
            f"{v.data_letter}  [{t(f'pendrive.kind_{v.kind}')}]  {v.disk_name} ({v.bus_type})  "
            f"{v.file_system}  " + t("cli.free_of", free=_gib(v.free), size=_gib(v.size))
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
        tgt.root,
        default_catalogs(),
        profile_id=args.perfil,
        file_system=tgt.file_system,
        kind=tgt.kind,
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


# ------------------------------------------------------------------ Wi-Fi (V2-02)
def cmd_coletar_wifi(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    _require_admin()
    recipe = load_profile_recipe(tgt.root, args.perfil)
    if services.wifi is None:
        out(t("cli.wifi_unavailable"))
        return 1
    added = wifi_collector.collect_wifi(services.wifi, tgt.root, recipe)
    _save(tgt, recipe)
    out(tn("cli.wifi_found", len(added)))
    out(t("cli.wifi_warning"))
    return cmd_wifi_listar(args, services, out)


def cmd_wifi_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    for n in recipe.wifi.networks:
        mark = "x" if n.selected and n.security != "enterprise" else " "
        key = t("cli.wifi_with_key") if n.include_key else t("cli.wifi_without_key")
        security = t(f"studio.wifi.security.{n.security}")
        out(f"  [{mark}] {n.id:28} {n.ssid[:30]:30} {security}  {key}")
    return 0


def cmd_wifi_marcar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    missing = []
    for nid in args.ids:
        item = next((n for n in recipe.wifi.networks if n.id == nid), None)
        if item is None:
            missing.append(nid)
            continue
        item.selected = args.command_value
        if args.sem_senha:
            wifi_collector.set_include_key(tgt.root, recipe, nid, include=False)
    _save(tgt, recipe)
    if missing:
        out(t("cli.not_found", ids=", ".join(missing)))
        return 1
    return cmd_wifi_listar(args, services, out)


# ------------------------------------------------------------------ recursos do Windows (V2-08)
def cmd_recursos_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    chosen = set(recipe.windows.optional_features)
    for f in catalogs.features:
        mark = "x" if f.id in chosen else " "
        notes = []
        if f.needs_network:
            notes.append(
                t("studio.features.offline" if f.offline_source else "studio.features.network")
            )
        if f.restart:
            notes.append(t("studio.features.restart"))
        if not f.windows.allows_edition(recipe.windows.edition):
            notes.append(t("studio.features.needs_pro"))
        out(f"  [{mark}] {f.id:16} {f.name}" + (f"  ({', '.join(notes)})" if notes else ""))
    return 0


def cmd_recursos_marcar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    missing = [i for i in args.ids if catalogs.feature(i) is None]
    for feature_id in args.ids:
        if feature_id not in missing:
            feature_collector.set_feature(recipe, feature_id, args.command_value)
    _save(tgt, recipe)
    if missing:
        out(t("cli.not_found", ids=", ".join(missing)))
        return 1
    return cmd_recursos_listar(args, services, out)


def cmd_coletar_recursos(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    _require_admin()
    recipe = load_profile_recipe(tgt.root, args.perfil)
    if services.features is None:
        out(t("cli.features_unavailable"))
        return 1
    added = feature_collector.add_enabled_here(services.features, default_catalogs(), recipe)
    _save(tgt, recipe)
    out(tn("studio.features.read_done", len(added)))
    return cmd_recursos_listar(args, services, out)


# ------------------------------------------------------------------ DNS e bloqueios (V2-16)
def cmd_dns_mostrar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    d = recipe.dns
    target = dns_rules.resolve(d, catalogs)
    if target is None:
        out(t("cli.dns_unchanged"))
    else:
        out(t("cli.dns_servers", servers=", ".join(target.servers)))
        if target.doh_template:
            mode = t("cli.dns_required") if d.require_doh else t("cli.dns_allowed")
            out(t("cli.dns_doh", template=target.doh_template, mode=mode))
    out(t("cli.dns_providers", ids=", ".join(p.id for p in catalogs.dns_providers)))
    for b in catalogs.hosts_blocklists:
        mark = "x" if b.id in d.hosts_blocklists else " "
        out(f"  [{mark}] {b.id:16} {b.name} — {tn('studio.dns.domains', len(b.domains))}")
    return 0


def cmd_dns_definir(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    d = recipe.dns
    d.provider = args.provedor
    d.provider_id = args.id
    d.require_doh = args.exigir_criptografia
    if args.servidores is not None:
        d.custom_servers = [s.strip() for s in args.servidores.split(",") if s.strip()]
    if args.modelo_doh is not None:
        d.custom_doh_template = args.modelo_doh or None
    problems = dns_rules.problems(d, default_catalogs())
    if problems:
        for p in problems:
            out(render(p))
        return 1
    _save(tgt, recipe)
    return cmd_dns_mostrar(args, services, out)


def cmd_dns_bloqueios(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    missing = [i for i in args.ids if catalogs.blocklist(i) is None]
    chosen = [x for x in recipe.dns.hosts_blocklists if x not in args.ids]
    if args.command_value:
        chosen += [i for i in args.ids if i not in missing]
    recipe.dns.hosts_blocklists = chosen
    _save(tgt, recipe)
    if missing:
        out(t("cli.not_found", ids=", ".join(missing)))
        return 1
    return cmd_dns_mostrar(args, services, out)


def cmd_dns_remover_do_pc(args: argparse.Namespace, services: Services, out: Out) -> int:
    _require_admin()
    removed = hosts.remove_block(hosts.hosts_file(services.folders.windows_dir()))
    out(t("studio.dns.removed" if removed else "studio.dns.nothing_to_remove"))
    return 0


# ------------------------------------------------------------------ unidades de rede (V2-17)
def cmd_coletar_unidades(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    if services.registry is None:
        out(t("cli.registry_unavailable"))
        return 1
    added = netdrive_collector.collect_drives(services.registry, recipe)
    _save(tgt, recipe)
    out(tn("studio.drives.read_done", len(added)))
    return cmd_unidades_listar(args, services, out)


def cmd_unidades_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    for d in sorted(recipe.network_drives, key=lambda x: x.letter):
        out(f"  [{'x' if d.selected else ' '}] {d.letter}:  {d.remote_path}")
    out(t("studio.drives.footer"))
    return 0


def cmd_unidades_adicionar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    try:
        netdrive_collector.add_drive(recipe, args.letra, args.caminho)
    except ValueError:
        out(t("studio.drives.invalid"))
        return 1
    _save(tgt, recipe)
    return cmd_unidades_listar(args, services, out)


def cmd_unidades_remover(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    if not netdrive_collector.remove_drive(recipe, args.letra):
        out(t("cli.not_found", ids=args.letra))
        return 1
    _save(tgt, recipe)
    return cmd_unidades_listar(args, services, out)


def _add_drive_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    un = sub.add_parser("unidades", aliases=["drives"], help=t("cli.h.drives"))
    un_sub = un.add_subparsers(dest="action", required=True)
    un_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_unidades_listar
    )
    ad = un_sub.add_parser("adicionar", aliases=["add"], parents=[common])
    ad.add_argument("letra", help=t("cli.h.drive_letter"))
    ad.add_argument("caminho", help=t("cli.h.drive_path"))
    ad.set_defaults(func=cmd_unidades_adicionar)
    rm = un_sub.add_parser("remover", aliases=["remove"], parents=[common])
    rm.add_argument("letra", help=t("cli.h.drive_letter"))
    rm.set_defaults(func=cmd_unidades_remover)


# ------------------------------------------------------------------ manutenção (V2-18)
_WINGET_CHOICES = {
    "nao": "off",
    "off": "off",
    "semanal": "weekly",
    "weekly": "weekly",
    "mensal": "monthly",
    "monthly": "monthly",
}


def cmd_manutencao_mostrar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    m = load_profile_recipe(tgt.root, args.perfil).maintenance
    choice = t(f"studio.maintenance.{m.winget_upgrade}")
    out(t("cli.maintenance_winget", choice=choice))
    if m.winget_upgrade != "off":
        out(
            t(
                "cli.maintenance_when",
                day=t(f"studio.maintenance.day.{m.winget_day}"),
                time=m.winget_time,
            )
        )
    yes, no = t("cli.yes"), t("cli.no")
    out(t("cli.maintenance_storage_sense", value=yes if m.storage_sense else no))
    out(t("cli.maintenance_defrag", value=yes if m.ensure_defrag_schedule else no))
    return 0


def cmd_manutencao_definir(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    m = recipe.maintenance
    if args.winget is not None:
        m.winget_upgrade = _WINGET_CHOICES[args.winget]  # type: ignore[assignment]
    if args.dia is not None:
        m.winget_day = args.dia
    if args.hora is not None:
        m.winget_time = args.hora
    if args.sensor is not None:
        m.storage_sense = args.sensor
    if args.desfragmentar is not None:
        m.ensure_defrag_schedule = args.desfragmentar
    _save(tgt, recipe)
    return cmd_manutencao_mostrar(args, services, out)


def cmd_manutencao_remover(args: argparse.Namespace, services: Services, out: Out) -> int:
    _require_admin()
    if services.scheduler is None:
        out(t("cli.scheduler_unavailable"))
        return 1
    n = services.scheduler.remove_folder(TASK_FOLDER)
    out(tn("cli.maintenance_removed", n))
    return 0


def _add_maintenance_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    mt = sub.add_parser("manutencao", aliases=["maintenance"], help=t("cli.h.maintenance"))
    mt_sub = mt.add_subparsers(dest="action", required=True)
    mt_sub.add_parser("mostrar", aliases=["show"], parents=[common]).set_defaults(
        func=cmd_manutencao_mostrar
    )
    df = mt_sub.add_parser("definir", aliases=["set"], parents=[common])
    df.add_argument("--winget", choices=sorted(_WINGET_CHOICES), help=t("cli.h.maintenance_winget"))
    df.add_argument("--dia", choices=list(DAYS), help=t("cli.h.maintenance_day"))
    df.add_argument("--hora", help=t("cli.h.maintenance_time"))
    df.add_argument(
        "--sensor", action=argparse.BooleanOptionalAction, help=t("cli.h.storage_sense")
    )
    df.add_argument(
        "--desfragmentar", action=argparse.BooleanOptionalAction, help=t("cli.h.defrag")
    )
    df.set_defaults(func=cmd_manutencao_definir)
    mt_sub.add_parser(
        "remover-do-pc",
        aliases=["remove-from-pc"],
        parents=[common],
        help=t("cli.h.maintenance_remove"),
    ).set_defaults(func=cmd_manutencao_remover)


# ------------------------------------------------------------------ variáveis de ambiente (V2-22)
def cmd_coletar_variaveis(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    if services.registry is None:
        out(t("cli.registry_unavailable"))
        return 1
    f = services.folders
    new_vars, new_paths = env_collector.collect_env(
        services.registry,
        recipe,
        default_catalogs().protected_env,
        {**f.machine(), **f.current_user()},
        f.windows_dir(),
    )
    _save(tgt, recipe)
    out(tn("studio.env.read_done", len(new_vars) + len(new_paths)))
    out(t("cli.env_hint"))
    return cmd_variaveis_listar(args, services, out)


def cmd_variaveis_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    env = load_profile_recipe(tgt.root, args.perfil).environment
    for v in env.variables:
        flag = f" ({t('studio.env.replace')})" if v.on_conflict == "replace" else ""
        scope = t(f"studio.env.scope_{v.scope}")
        out(f"  [{'x' if v.selected else ' '}] {v.name} = {v.value}  [{scope}]{flag}")
    for p in env.path_entries:
        scope = t(f"studio.env.scope_{p.scope}")
        line = t("cli.env_path_item", value=p.value)
        out(f"  [{'x' if p.selected else ' '}] {line}  [{scope}]")
    return 0


def cmd_variaveis_marcar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    missing = env_collector.select(recipe, args.nomes, selected=args.command_value)
    _save(tgt, recipe)
    if missing:
        out(t("cli.not_found", ids=", ".join(missing)))
        return 1
    return cmd_variaveis_listar(args, services, out)


def cmd_variaveis_definir(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    scope: EnvScope = "machine" if args.sistema else "user"
    catalogs = default_catalogs()
    if args.nome.casefold() == "path":
        env_collector.add_path(recipe, args.valor, scope)
    elif catalogs.protected_env.is_protected(args.nome):
        out(t("recipe.env_protected", name=args.nome))
        return 1
    else:
        try:
            var = EnvVar(
                name=args.nome,
                value=args.valor,
                scope=scope,
                on_conflict="replace" if args.substituir else "skip",
            )
        except ValueError:
            out(t("cli.env_bad_name", name=args.nome))
            return 1
        env_collector.set_variable(recipe, var)
    _save(tgt, recipe)
    return cmd_variaveis_listar(args, services, out)


def _add_env_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    va = sub.add_parser("variaveis", aliases=["env"], help=t("cli.h.env"))
    va_sub = va.add_subparsers(dest="action", required=True)
    va_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_variaveis_listar
    )
    for name, alias, value in (("marcar", "select", True), ("desmarcar", "deselect", False)):
        vm = va_sub.add_parser(name, aliases=[alias], parents=[common])
        vm.add_argument("nomes", nargs="+", help=t("cli.h.env_names"))
        vm.set_defaults(func=cmd_variaveis_marcar, command_value=value)
    vd = va_sub.add_parser("definir", aliases=["set"], parents=[common])
    vd.add_argument("nome", help=t("cli.h.env_name"))
    vd.add_argument("valor", help=t("cli.h.env_value"))
    vd.add_argument("--sistema", action="store_true", help=t("cli.h.env_machine"))
    vd.add_argument("--substituir", action="store_true", help=t("cli.h.env_replace"))
    vd.set_defaults(func=cmd_variaveis_definir)


# ------------------------------------------------------------------ perfis rápidos (V2-15)
def cmd_perfil_rapido_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    for p in default_catalogs().presets:
        out(f"  {p.id:14} {p.name} — {p.description}")
    return 0


def cmd_perfil_rapido_aplicar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    preset = catalogs.preset(args.id)
    if preset is None:
        out(t("cli.not_found", ids=args.id))
        return 1
    result = (preview_preset if args.simular else apply_preset)(preset, recipe, catalogs)
    for change in result.changes:
        out("  + " + render(change))
    for warning in result.warnings:
        out("  ! " + render(warning))
    if not result.changes and not result.warnings:
        out(t("studio.presets.nothing"))
    if not args.simular:
        _save(tgt, recipe)
    return 0


def _add_preset_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    pr = sub.add_parser("perfil-rapido", aliases=["preset"], help=t("cli.h.presets"))
    pr_sub = pr.add_subparsers(dest="action", required=True)
    pr_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_perfil_rapido_listar
    )
    pa = pr_sub.add_parser("aplicar", aliases=["apply"], parents=[common])
    pa.add_argument("id", help=t("cli.h.preset_id"))
    pa.add_argument("--simular", action="store_true", help=t("cli.h.preset_simulate"))
    pa.set_defaults(func=cmd_perfil_rapido_aplicar)


# ------------------------------------------------------------------ fontes (V2-07)
def cmd_coletar_fontes(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    if services.registry is None:
        out(t("cli.registry_unavailable"))
        return 1
    added, errors = font_collector.collect_fonts(
        services.registry, services.folders.windows_dir(), services.volume_root, recipe
    )
    _save(tgt, recipe)
    out(tn("studio.fonts.read_done", len(added)))
    for path in errors:
        out(t("cli.font_unreadable", path=path))
    out(t("studio.fonts.license"))
    return cmd_fontes_listar(args, services, out)


def cmd_fontes_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    for f in load_profile_recipe(tgt.root, args.perfil).fonts:
        origin = t(f"studio.fonts.origin_{f.origin}")
        out(f"  [{'x' if f.selected else ' '}] {f.id:30} {f.full_name}  ({origin})")
    return 0


def cmd_fontes_marcar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    missing = [
        i
        for i in args.ids
        if not font_collector.select_font(
            tgt.root, recipe, i, args.command_value, services.volume_root
        )
    ]
    _save(tgt, recipe)
    if missing:
        out(t("cli.not_found", ids=", ".join(missing)))
        return 1
    return cmd_fontes_listar(args, services, out)


def _add_font_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    fo = sub.add_parser("fontes", aliases=["fonts"], help=t("cli.h.fonts"))
    fo_sub = fo.add_subparsers(dest="action", required=True)
    fo_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_fontes_listar
    )
    for name, alias, value in (("marcar", "select", True), ("desmarcar", "deselect", False)):
        fm = fo_sub.add_parser(name, aliases=[alias], parents=[common])
        fm.add_argument("ids", nargs="+", help=t("cli.h.font_ids"))
        fm.set_defaults(func=cmd_fontes_marcar, command_value=value)


# ------------------------------------------------------------------ apps padrão (V2-05)
def cmd_coletar_associacoes(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    if services.associations is None:
        out(t("cli.defaults_unavailable"))
        return 1
    assoc_collector.collect_associations(
        services.associations, tgt.root, recipe, default_catalogs()
    )
    _save(tgt, recipe)
    out(t("studio.defaults.warning"))
    return cmd_associacoes_listar(args, services, out)


def cmd_associacoes_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    if not recipe.default_apps.associations_file:
        out(t("studio.defaults.none"))
        return 0
    for group, app in assoc_collector.group_rows(tgt.root, recipe, default_catalogs()):
        mark = "x" if group.id in recipe.default_apps.groups else " "
        out(f"  [{mark}] {group.id:10} {group.name}: {app or t('studio.defaults.no_app')}")
    return 0


def cmd_associacoes_marcar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    missing = [g for g in args.grupos if catalogs.association_group(g) is None]
    for group_id in args.grupos:
        if group_id not in missing:
            assoc_collector.set_group(recipe, group_id, args.command_value)
    _save(tgt, recipe)
    if missing:
        out(t("cli.not_found", ids=", ".join(missing)))
        return 1
    return cmd_associacoes_listar(args, services, out)


def _add_default_apps_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    da = sub.add_parser("associacoes", aliases=["defaults"], help=t("cli.h.defaults"))
    da_sub = da.add_subparsers(dest="action", required=True)
    da_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_associacoes_listar
    )
    for name, alias, value in (("marcar", "select", True), ("desmarcar", "deselect", False)):
        dm = da_sub.add_parser(name, aliases=[alias], parents=[common])
        dm.add_argument("grupos", nargs="+", help=t("cli.h.default_groups"))
        dm.set_defaults(func=cmd_associacoes_marcar, command_value=value)


# ------------------------------------------------------------------ aparência (V2-06)
def cmd_coletar_aparencia(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    if services.registry is None:
        out(t("cli.registry_unavailable"))
        return 1
    report = personal_collector.collect_personal(
        services.registry,
        tgt.root,
        recipe,
        default_catalogs(),
        appdata=services.folders.current_user()["APPDATA"],
        volume_root=services.volume_root,
    )
    _save(tgt, recipe)
    out(tn("studio.appearance.read_done", report.values))
    if report.dropped:
        out(tn("studio.appearance.dropped", len(report.dropped)))
    if report.wallpaper_skipped:
        out(t("studio.appearance.no_wallpaper"))
    return cmd_aparencia_listar(args, services, out)


def cmd_aparencia_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    p = load_profile_recipe(tgt.root, args.perfil).personal
    for g in default_catalogs().personal_groups:
        n = sum(1 for s in g.values if f"{s.key}\\{s.value}" in p.values)
        if g.file and p.wallpaper_file:
            n += 1
        if n:
            out(f"  [{'x' if g.id in p.groups else ' '}] {g.id:16} {g.name} ({n})")
    return 0


def cmd_aparencia_marcar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    missing = [g for g in args.grupos if catalogs.personal_group(g) is None]
    for group_id in args.grupos:
        if group_id not in missing:
            personal_collector.set_group(recipe, group_id, args.command_value)
    _save(tgt, recipe)
    if missing:
        out(t("cli.not_found", ids=", ".join(missing)))
        return 1
    return cmd_aparencia_listar(args, services, out)


def _add_appearance_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    ap = sub.add_parser("aparencia", aliases=["appearance"], help=t("cli.h.appearance"))
    ap_sub = ap.add_subparsers(dest="action", required=True)
    ap_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_aparencia_listar
    )
    for name, alias, value in (("marcar", "select", True), ("desmarcar", "deselect", False)):
        am = ap_sub.add_parser(name, aliases=[alias], parents=[common])
        am.add_argument("grupos", nargs="+", help=t("cli.h.appearance_groups"))
        am.set_defaults(func=cmd_aparencia_marcar, command_value=value)


# ------------------------------------------------------------------ navegadores (V2-12)
def cmd_coletar_navegadores(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    f = services.folders
    found = browser_collector.collect_browsers(
        recipe, default_catalogs(), {**f.machine(), **f.current_user()}, services.volume_root
    )
    _save(tgt, recipe)
    out(tn("cli.browsers_found", len(found)))
    return cmd_navegador_listar(args, services, out)


def cmd_navegador_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    catalogs = default_catalogs()
    for cfg in load_profile_recipe(tgt.root, args.perfil).browsers:
        entry = catalogs.browser(cfg.id)
        mode = t(f"studio.browsers.{cfg.mode}")
        out(
            f"[{'x' if cfg.selected else ' '}] {cfg.id}: {entry.name if entry else cfg.id} ({mode})"
        )
        if cfg.homepage:
            out("    " + t("cli.browser_homepage", url=cfg.homepage))
        if cfg.search:
            out("    " + t("cli.browser_search", id=cfg.search))
        for e in cfg.extensions:
            out(f"    [{'x' if e.selected else ' '}] {e.name or e.id}  {e.id}")
    return 0


def cmd_navegador_definir(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    if catalogs.browser(args.id) is None:
        out(t("cli.not_found", ids=args.id))
        return 1
    cfg = next((b for b in recipe.browsers if b.id == args.id), None)
    if cfg is None:
        cfg = BrowserConfig(id=args.id)
        recipe.browsers = [*recipe.browsers, cfg]
    if args.extensoes:
        missing = browser_collector.add_suggested(cfg, catalogs, args.extensoes.split(","))
        if missing:
            out(t("cli.not_found", ids=", ".join(missing)))
            return 1
    if args.busca is not None:
        if args.busca and catalogs.search_provider(args.busca) is None:
            out(t("cli.not_found", ids=args.busca))
            return 1
        cfg.search = args.busca or None
    if args.pagina is not None:
        try:
            cfg.homepage = args.pagina or None
        except ValueError:
            out(t("studio.browsers.bad_url"))
            return 1
    if args.forcar is not None:
        cfg.mode = "force" if args.forcar else "suggest"
    _save(tgt, recipe)
    return cmd_navegador_listar(args, services, out)


def cmd_navegador_remover(args: argparse.Namespace, services: Services, out: Out) -> int:
    _require_admin()
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    cfg = next((b for b in recipe.browsers if b.id == args.id), None)
    if cfg is None or services.registry is None:
        out(t("cli.not_found", ids=args.id))
        return 1
    n = browser_policies.undo(services.registry, undo_operations(cfg, default_catalogs()))
    out(tn("cli.browser_removed", n))
    return 0


def _add_browser_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    nv = sub.add_parser("navegador", aliases=["browser"], help=t("cli.h.browsers"))
    nv_sub = nv.add_subparsers(dest="action", required=True)
    nv_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_navegador_listar
    )
    nd = nv_sub.add_parser("definir", aliases=["set"], parents=[common])
    nd.add_argument("id", help=t("cli.h.browser_id"))
    nd.add_argument("--extensoes", help=t("cli.h.browser_extensions"))
    nd.add_argument("--busca", help=t("cli.h.browser_search"))
    nd.add_argument("--pagina", help=t("cli.h.browser_homepage"))
    nd.add_argument(
        "--forcar", action=argparse.BooleanOptionalAction, help=t("cli.h.browser_force")
    )
    nd.set_defaults(func=cmd_navegador_definir)
    nr = nv_sub.add_parser("remover-do-pc", aliases=["remove-from-pc"], parents=[common])
    nr.add_argument("id", help=t("cli.h.browser_id"))
    nr.set_defaults(func=cmd_navegador_remover)


# ------------------------------------------------------------------ Iniciar e barra (V2-04)
def cmd_coletar_iniciar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    f = services.folders
    pinned, orphans = start_collector.collect_start_layout(
        recipe,
        tgt.root,
        {**f.machine(), **f.current_user()},
        services.volume_root,
        build=WindowsEnvironment().windows_build(),
    )
    recipe.start_layout.mode = args.modo
    _save(tgt, recipe)
    out(tn("studio.start.read_done", pinned))
    if orphans:
        out(t("studio.start.orphans", names=", ".join(orphans)))
    for pin in recipe.start_layout.taskbar_pins:
        out(f"  [x] {pin.name}")
    return 0


def _add_start_parsers(col_sub: Any, common: argparse.ArgumentParser) -> None:
    ci = col_sub.add_parser(
        "iniciar", aliases=["start"], parents=[common], help=t("cli.h.collect_start")
    )
    ci.add_argument("--modo", choices=["list", "exact"], default="list", help=t("cli.h.start_mode"))
    ci.set_defaults(func=cmd_coletar_iniciar)


# ------------------------------------------------------------------ pastas do usuário (V2-14)
_FOLDER_ALIASES = {
    "area-de-trabalho": "desktop",
    "desktop": "desktop",
    "documentos": "documents",
    "documents": "documents",
    "downloads": "downloads",
    "imagens": "pictures",
    "pictures": "pictures",
    "videos": "videos",
    "musicas": "music",
    "music": "music",
}


def cmd_pastas_mostrar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    uf = load_profile_recipe(tgt.root, args.perfil).user_folders
    if not uf.enabled or uf.volume is None:
        out(t("cli.folders_off"))
        return 0
    vols = services.volumes.volumes() if services.volumes else []
    v = resolve_volume(uf.volume, vols)
    letter = v.letter if v and v.letter else (uf.volume.letter_hint or "?")
    out(t("cli.folders_volume", label=uf.volume.label or uf.volume.serial, serial=uf.volume.serial))
    for folder, rel in uf.folders.items():
        out(f"  {t(f'folder.{folder}')}: {letter}:\\{rel}")
    return 0


def cmd_pastas_definir(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    vols = services.volumes.volumes() if services.volumes else []
    wanted = args.volume.upper().rstrip(":\\")
    v = next((x for x in vols if x.serial == wanted), None) or by_letter(wanted, vols)
    if v is None or v.is_system:
        out(t("cli.folders_bad_volume", volume=args.volume))
        return 1
    chosen = []
    for name in args.pastas.split(","):
        folder = _FOLDER_ALIASES.get(name.strip().lower())
        if folder is None:
            out(t("cli.not_found", ids=name))
            return 1
        chosen.append(folder)
    base = args.base if args.base is not None else t("studio.folders.default_base")
    names = {f: t(f"folder.{f}") for f in USER_FOLDER_ORDER}
    recipe.user_folders = UserFolders(
        enabled=True, volume=volume_ref(v), folders=default_folders(base, names, chosen)
    )
    recipe.meta.source_system_volume = folders_collector.system_serial(vols)
    _save(tgt, recipe)
    return cmd_pastas_mostrar(args, services, out)


def cmd_pastas_copiar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    if services.volumes is None:
        out(t("cli.folders_off"))
        return 1
    try:
        report = folders_collector.copy_now(
            recipe,
            services.volumes,
            services.copier,
            services.folders.current_user(),
            services.volume_root,
        )
    except FileNotFoundError:
        out(
            t(
                "cli.folders_bad_volume",
                volume=recipe.user_folders.volume.serial if recipe.user_folders.volume else "?",
            )
        )
        return 1
    out(tn("studio.folders.copied", len(report.copied)))
    return 0


def _add_folder_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    pa = sub.add_parser("pastas", aliases=["folders"], help=t("cli.h.folders"))
    pa_sub = pa.add_subparsers(dest="action", required=True)
    pa_sub.add_parser("mostrar", aliases=["show"], parents=[common]).set_defaults(
        func=cmd_pastas_mostrar
    )
    pd = pa_sub.add_parser("definir", aliases=["set"], parents=[common])
    pd.add_argument("--volume", required=True, help=t("cli.h.folders_volume"))
    pd.add_argument("--base", help=t("cli.h.folders_base"))
    pd.add_argument(
        "--pastas",
        default="documentos,downloads,imagens,videos,musicas",
        help=t("cli.h.folders_list"),
    )
    pd.set_defaults(func=cmd_pastas_definir)
    pa_sub.add_parser(
        "copiar-agora", aliases=["copy-now"], parents=[common], help=t("cli.h.folders_copy")
    ).set_defaults(func=cmd_pastas_copiar)


# ------------------------------------------------------------------ jogos (V2-13)
def cmd_coletar_jogos(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    if services.registry is None:
        out(t("cli.registry_unavailable"))
        return 1
    vols = services.volumes.volumes() if services.volumes else []
    recipe.meta.source_system_volume = folders_collector.system_serial(vols)
    report = games_collector.collect_games(
        services.registry,
        tgt.root,
        recipe,
        vols,
        machine=services.folders.machine(),
        volume_root=services.volume_root,
    )
    _save(tgt, recipe)
    out(tn("studio.games.read_done", len(report.added)))
    if report.on_system:
        out(t("studio.games.on_system", names=", ".join(report.on_system)))
    return cmd_jogos_listar(args, services, out)


def cmd_jogos_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    for lib in load_profile_recipe(tgt.root, args.perfil).game_libraries:
        out(f"  [{'x' if lib.selected else ' '}] {lib.id:40} {lib.name}")
    return 0


def cmd_jogos_marcar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    missing = games_collector.select(recipe, args.ids, selected=args.command_value)
    _save(tgt, recipe)
    if missing:
        out(t("cli.not_found", ids=", ".join(missing)))
        return 1
    return cmd_jogos_listar(args, services, out)


def _add_game_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    jg = sub.add_parser("jogos", aliases=["games"], help=t("cli.h.games"))
    jg_sub = jg.add_subparsers(dest="action", required=True)
    jg_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_jogos_listar
    )
    for name, alias, value in (("marcar", "select", True), ("desmarcar", "deselect", False)):
        jm = jg_sub.add_parser(name, aliases=[alias], parents=[common])
        jm.add_argument("ids", nargs="+", help=t("cli.h.game_ids"))
        jm.set_defaults(func=cmd_jogos_marcar, command_value=value)


# ------------------------------------------------------------------ contas extras (V2-11)
def cmd_contas_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    win = load_profile_recipe(tgt.root, args.perfil).windows
    out(f"  * {win.account.username}  ({t('studio.extra.main')})")
    for a in win.extra_accounts:
        group = t(f"studio.extra.group_{a.group}")
        out(f"  - {a.username}  ({group}, {t(f'studio.extra.password_{a.password_mode}')})")
    return 0


def cmd_contas_adicionar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    mode = "stored" if args.senha else ("empty" if args.sem_senha else "must_change")
    taken = {recipe.windows.account.username.casefold()}
    taken |= {a.username.casefold() for a in recipe.windows.extra_accounts}
    problem = username_problem(args.nome)
    if problem is None and args.nome.casefold() in taken:
        problem = t("recipe.account_duplicate", name=args.nome)
    if problem:
        out(problem)
        return 1
    account = ExtraAccount(
        username=args.nome,
        display_name=args.nome_exibicao,
        group="administrators" if args.admin else "users",
        password_mode=mode,
        password=args.senha,
    )
    recipe.windows.extra_accounts = [*recipe.windows.extra_accounts, account]
    _save(tgt, recipe)
    if mode == "stored":
        out(t("recipe.password_stored_warning"))
    return cmd_contas_listar(args, services, out)


def cmd_contas_remover(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    before = len(recipe.windows.extra_accounts)
    recipe.windows.extra_accounts = [
        a for a in recipe.windows.extra_accounts if a.username.casefold() != args.nome.casefold()
    ]
    if len(recipe.windows.extra_accounts) == before:
        out(t("cli.not_found", ids=args.nome))
        return 1
    _save(tgt, recipe)
    return cmd_contas_listar(args, services, out)


def cmd_backup_para_quem(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    item = recipe.backup(args.id)
    if item is None:
        out(t("cli.not_found", ids=args.id))
        return 1
    item.for_accounts = "main" if args.quem in ("principal", "main") else "all"
    _save(tgt, recipe)
    out(t("cli.backup_for", id=item.id, who=t(f"cli.backup_for_{item.for_accounts}")))
    return 0


def _add_account_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    ct = sub.add_parser("contas", aliases=["accounts"], help=t("cli.h.accounts"))
    ct_sub = ct.add_subparsers(dest="action", required=True)
    ct_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_contas_listar
    )
    ca = ct_sub.add_parser("adicionar", aliases=["add"], parents=[common])
    ca.add_argument("nome", help=t("cli.h.account_name"))
    ca.add_argument("--nome-exibicao", help=t("cli.h.account_display"))
    ca.add_argument("--admin", action="store_true", help=t("cli.h.account_admin"))
    pw = ca.add_mutually_exclusive_group()
    pw.add_argument("--sem-senha", action="store_true", help=t("cli.h.account_no_password"))
    pw.add_argument("--senha", help=t("cli.h.account_password"))
    ca.set_defaults(func=cmd_contas_adicionar)
    cr = ct_sub.add_parser("remover", aliases=["remove"], parents=[common])
    cr.add_argument("nome", help=t("cli.h.account_name"))
    cr.set_defaults(func=cmd_contas_remover)
    bp = sub.add_parser(
        "backup-para-quem", aliases=["backup-for"], parents=[common], help=t("cli.h.backup_for")
    )
    bp.add_argument("id", help=t("cli.h.backup_id"))
    bp.add_argument(
        "quem", choices=["todas", "principal", "all", "main"], help=t("cli.h.backup_who")
    )
    bp.set_defaults(func=cmd_backup_para_quem)


# ------------------------------------------------------------------ receitas compartilháveis
def cmd_receita_exportar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    data = share.export_recipe(
        recipe,
        title=args.titulo or Path(args.arquivo).stem,
        description=args.descricao or "",
        version=__version__,
    )
    atomic_write_text(Path(args.arquivo), share.dumps(data))
    out(t("cli.share_exported", path=args.arquivo))
    return 0


def _print_import(result: share.ImportResult, out: Out) -> None:
    for change in result.changes:
        out("  + " + render(change))
    for ignored in result.ignored:
        out("  ! " + render(ignored))
    if not result.changes and not result.ignored:
        out(t("studio.presets.nothing"))


def _import_share(
    data: share.ShareableRecipe, args: argparse.Namespace, services: Services, out: Out
) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    if args.aplicar:
        _print_import(share.import_recipe(data, recipe, catalogs), out)
        _save(tgt, recipe)
    else:
        _print_import(share.preview_import(data, recipe, catalogs), out)
        out(t("cli.share_preview_hint"))
    return 0


def cmd_receita_importar(args: argparse.Namespace, services: Services, out: Out) -> int:
    try:
        data = share.loads(Path(args.arquivo).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        out(t("studio.templates.invalid", detail=str(exc)))
        return 1
    return _import_share(data, args, services, out)


def cmd_receita_modelo(args: argparse.Namespace, services: Services, out: Out) -> int:
    if args.id is None:
        for template_id in share.TEMPLATE_IDS:
            title = t(f"template.{template_id}.title")
            out(f"  {template_id:12} {title} — {t(f'template.{template_id}.description')}")
        return 0
    try:
        data = share.load_template(args.id)
    except share.ShareError:
        out(t("cli.not_found", ids=args.id))
        return 1
    return _import_share(data, args, services, out)


def _add_share_parsers(rec_sub: Any, common: argparse.ArgumentParser) -> None:
    ex = rec_sub.add_parser(
        "exportar", aliases=["export"], parents=[common], help=t("cli.h.share_export")
    )
    ex.add_argument("arquivo", help=t("cli.h.share_file"))
    ex.add_argument("--titulo", help=t("cli.h.share_title"))
    ex.add_argument("--descricao", help=t("cli.h.share_description"))
    ex.set_defaults(func=cmd_receita_exportar)
    im = rec_sub.add_parser(
        "importar", aliases=["import"], parents=[common], help=t("cli.h.share_import")
    )
    im.add_argument("arquivo", help=t("cli.h.share_file"))
    im.add_argument("--aplicar", action="store_true", help=t("cli.h.share_apply"))
    im.set_defaults(func=cmd_receita_importar)
    mo = rec_sub.add_parser(
        "modelo", aliases=["template"], parents=[common], help=t("cli.h.share_template")
    )
    mo.add_argument("id", nargs="?", help=t("cli.h.share_template_id"))
    mo.add_argument("--aplicar", action="store_true", help=t("cli.h.share_apply"))
    mo.set_defaults(func=cmd_receita_modelo)


def _add_dns_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    dns = sub.add_parser("dns", help=t("cli.h.dns"))
    dns_sub = dns.add_subparsers(dest="action", required=True)
    dns_sub.add_parser("mostrar", aliases=["show"], parents=[common]).set_defaults(
        func=cmd_dns_mostrar
    )
    df = dns_sub.add_parser("definir", aliases=["set"], parents=[common])
    df.add_argument("provedor", help=t("cli.h.dns_provider"))
    df.add_argument("--id", help=t("cli.h.dns_id"))
    df.add_argument("--servidores", help=t("cli.h.dns_servers"))
    df.add_argument("--modelo-doh", help=t("cli.h.dns_template"))
    df.add_argument("--exigir-criptografia", action="store_true", help=t("cli.h.dns_require"))
    df.set_defaults(func=cmd_dns_definir)
    bl = dns_sub.add_parser("bloqueios", aliases=["blocklists"], help=t("cli.h.blocklists"))
    bl_sub = bl.add_subparsers(dest="subaction", required=True)
    for name, alias, value in (("marcar", "select", True), ("desmarcar", "deselect", False)):
        bm = bl_sub.add_parser(name, aliases=[alias], parents=[common])
        bm.add_argument("ids", nargs="+", help=t("cli.h.blocklist_ids"))
        bm.set_defaults(func=cmd_dns_bloqueios, command_value=value)
    bl_sub.add_parser(
        "remover-do-pc", aliases=["remove-from-pc"], parents=[common], help=t("cli.h.unblock")
    ).set_defaults(func=cmd_dns_remover_do_pc)


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
def _add_feature_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    rec = sub.add_parser("recursos", aliases=["features"], help=t("cli.h.features"))
    rec_sub = rec.add_subparsers(dest="action", required=True)
    rec_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_recursos_listar
    )
    for name, alias, value in (("marcar", "select", True), ("desmarcar", "deselect", False)):
        rm = rec_sub.add_parser(name, aliases=[alias], parents=[common])
        rm.add_argument("ids", nargs="+", help=t("cli.h.feature_ids"))
        rm.set_defaults(func=cmd_recursos_marcar, command_value=value)


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

    cwifi = col_sub.add_parser("wifi", parents=[common], help=t("cli.h.collect_wifi"))
    cwifi.set_defaults(func=cmd_coletar_wifi)
    crec = col_sub.add_parser(
        "recursos", aliases=["features"], parents=[common], help=t("cli.h.collect_features")
    )
    crec.set_defaults(func=cmd_coletar_recursos)
    cun = col_sub.add_parser(
        "unidades", aliases=["drives"], parents=[common], help=t("cli.h.collect_drives")
    )
    cun.set_defaults(func=cmd_coletar_unidades)
    cva = col_sub.add_parser(
        "variaveis", aliases=["env"], parents=[common], help=t("cli.h.collect_env")
    )
    cva.set_defaults(func=cmd_coletar_variaveis)
    cfo = col_sub.add_parser(
        "fontes", aliases=["fonts"], parents=[common], help=t("cli.h.collect_fonts")
    )
    cfo.set_defaults(func=cmd_coletar_fontes)
    cas = col_sub.add_parser(
        "associacoes", aliases=["defaults"], parents=[common], help=t("cli.h.collect_defaults")
    )
    cas.set_defaults(func=cmd_coletar_associacoes)
    cap = col_sub.add_parser(
        "aparencia", aliases=["appearance"], parents=[common], help=t("cli.h.collect_appearance")
    )
    cap.set_defaults(func=cmd_coletar_aparencia)
    cnv = col_sub.add_parser(
        "navegadores", aliases=["browsers"], parents=[common], help=t("cli.h.collect_browsers")
    )
    cnv.set_defaults(func=cmd_coletar_navegadores)
    _add_start_parsers(col_sub, common)
    cjg = col_sub.add_parser(
        "jogos", aliases=["games"], parents=[common], help=t("cli.h.collect_games")
    )
    cjg.set_defaults(func=cmd_coletar_jogos)

    capp = col_sub.add_parser("apps", parents=[common], help=t("cli.h.collect_apps"))
    capp.add_argument(
        "--incluir-redistribuiveis",
        action="store_true",
        help=t("cli.h.redist"),
    )
    capp.set_defaults(func=cmd_coletar_apps)


def cmd_apps_atualizar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    results = app_updates.refresh_apps(
        services.winget,
        tgt.root,
        recipe,
        default_catalogs(),
        apply=not args.verificar,
        ids=args.ids or None,
        save=lambda: _save(tgt, recipe),
        now=datetime.now(UTC),
    )
    for r in results:
        line = t(
            f"studio.apps.update_{r.status}",
            name=r.name,
            current=r.current or "?",
            available=r.available or "?",
        )
        out("  " + line + (f" ({r.detail})" if r.detail else ""))
    if not results:
        out(t("studio.apps.no_offline"))
    return 1 if any(r.status == "failed" for r in results) else 0


def _add_apps_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    apps = sub.add_parser("apps", help=t("cli.h.apps"))
    apps_sub = apps.add_subparsers(dest="action", required=True)
    au = apps_sub.add_parser(
        "atualizar", aliases=["update"], parents=[common], help=t("cli.h.apps_update")
    )
    au.add_argument("ids", nargs="*", help=t("cli.h.apps_update_ids"))
    au.add_argument("--verificar", action="store_true", help=t("cli.h.apps_update_check"))
    au.set_defaults(func=cmd_apps_atualizar)
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


def _add_system_and_network_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    """Comandos da v2 para o grupo Sistema e Rede (M14)."""
    _add_feature_parsers(sub, common)
    _add_dns_parsers(sub, common)
    _add_drive_parsers(sub, common)
    _add_maintenance_parsers(sub, common)
    _add_env_parsers(sub, common)
    _add_preset_parsers(sub, common)
    _add_font_parsers(sub, common)
    _add_default_apps_parsers(sub, common)
    _add_appearance_parsers(sub, common)
    _add_browser_parsers(sub, common)
    _add_folder_parsers(sub, common)
    _add_game_parsers(sub, common)
    _add_account_parsers(sub, common)


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
    _add_share_parsers(rec_sub, common)

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

    wifi = sub.add_parser("wifi", help=t("cli.h.wifi"))
    wifi_sub = wifi.add_subparsers(dest="action", required=True)
    wifi_sub.add_parser("listar", aliases=["list"], parents=[common]).set_defaults(
        func=cmd_wifi_listar
    )
    for name, alias, value in (("marcar", "select", True), ("desmarcar", "deselect", False)):
        wm = wifi_sub.add_parser(name, aliases=[alias], parents=[common])
        wm.add_argument("ids", nargs="+", help=t("cli.h.wifi_ids"))
        wm.add_argument("--sem-senha", action="store_true", help=t("cli.h.wifi_no_key"))
        wm.set_defaults(func=cmd_wifi_marcar, command_value=value)

    _add_system_and_network_parsers(sub, common)

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
