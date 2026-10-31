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
from winkit.i18n import t, tn
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
            f"{_gib(v.free)} livres de {_gib(v.size)}"
        )
    return 0


def cmd_receita_nova(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    path = tgt.root / layout.recipe_file(args.perfil)
    if path.exists() and not args.sobrescrever:
        out(f"Já existe uma receita em {path}. Use --sobrescrever para trocar.")
        return 1
    marker = ensure_marker(tgt.root, _now())
    recipe = new_recipe(
        pendrive_id=marker.pendrive_id,
        username=args.usuario,
        profile_id=args.perfil,
        source_pc=os.environ.get("COMPUTERNAME"),
        now=_now(),
    )
    if args.nome_pc:
        recipe.windows.computer_name = args.nome_pc
    report = validate_recipe(recipe, default_catalogs())
    if not report.ok:
        out(t("recipe.invalid", problems="\n".join(report.errors)))
        return 1
    saved = save_profile_recipe(tgt.root, recipe)
    out(f"Receita criada em {saved}")
    return 0


def cmd_plano(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    ctx = PlanContext(os_major=args.windows, build=args.build, phase1_ran=not args.sem_fase1)
    p = plan(recipe, default_catalogs(), ctx)
    for phase in (1, 2):
        steps = p.phase(phase)
        out(f"Fase {phase} ({len(steps)} etapas):")
        for s in steps:
            flags = []
            if s.user_choice:
                flags.append("decidir na hora")
            if s.moved_from_phase1:
                flags.append("veio da Fase 1")
            if s.needs_network:
                flags.append("internet")
            suffix = f"  [{', '.join(flags)}]" if flags else ""
            out(f"  - {s.title}{suffix}")
    if p.excluded:
        out("Fora do plano:")
        for e in p.excluded:
            out(f"  - {e.kind} {e.ref}: {e.reason}")
    return 0


def cmd_construir(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    out(f"Pendrive: {tgt.description}")
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
        out(f"Ignorada: {image} — {reason}")
    for tpl in report.templates:
        out(f"Modelo gravado: {tpl}")
    for name in report.removed_templates:
        out(f"Modelo antigo removido: {name}")
    if report.warnings:
        out(t("validate.warnings", count=len(report.warnings)))
        for w in report.warnings:
            out(f"  ! {w}")
    if report.sizes:
        used = ", ".join(f"{t(f'size.{k}')} {human_size(v)}" for k, v in report.sizes.items())
        out(f"Espaço usado no pendrive: {used}; livre: {human_size(tgt.free)}")
    if report.manifest_files:
        a, c, r = report.manifest_changes
        out(
            f"Manifesto: {report.manifest_files} arquivos ({a} novos, {c} alterados, {r} removidos)"
        )
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
    out(f"{len(added)} driver(s) exportado(s) para o pendrive e incluído(s) na receita.")
    return 0


def _save(tgt: targets.Target, recipe: Recipe) -> None:
    recipe.meta.updated_at = _now()
    save_profile_recipe(tgt.root, recipe)


def _source_label(source: str, winget_id: str | None) -> str:
    if source == "winget_online":
        return f"winget ({winget_id})"
    if source == "portable":
        return "portátil"
    return "instalador offline"


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
    out(
        f"{len(added)} app(s) novos na receita (todos desmarcados). Marque com: "
        "winkit apps marcar <id>"
    )
    return cmd_apps_listar(args, services, out)


def cmd_apps_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    for a in sorted(recipe.apps, key=lambda x: (not x.selected, x.order, x.name.casefold())):
        mark = "x" if a.selected else " "
        where = "por usuário" if a.scope == "user" else "máquina"
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
        out(f"Não encontrados na receita: {', '.join(missing)}")
        return 1
    out(f"{len(args.ids)} app(s) {'marcado(s)' if value else 'desmarcado(s)'}.")
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
        out("O winget não está disponível neste PC.")
        return 1
    failures = 0
    for item in items:
        free = targets.from_folder(tgt.root).free if args.raiz else tgt.free
        res = app_collector.download_app(services.winget, tgt.root, item, catalogs, free_bytes=free)
        out(f"  {'ok ' if res.ok else 'não'} {item.id}: {res.message}")
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
        f'App "{item.name}" adicionado: tipo {item.installer.type}, '
        f"argumentos {' '.join(item.installer.args) or '(nenhum)'}"
    )
    if item.installer.type == "unknown" and not item.installer.args:
        out("Atenção: tipo desconhecido. Informe os argumentos silenciosos com --args.")
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
        out(
            "Nenhuma sugestão: marque apps primeiro (winkit apps marcar ...) ou adicione "
            "pastas com 'winkit backup adicionar'."
        )
        return 0
    added = 0
    for sug in suggestions:
        pick = sug.recommended and sug.exists
        mark = "x" if pick else " "
        size = human_size(sug.size) if sug.exists else "não existe neste PC"
        out(f"  [{mark}] {sug.app_name}: {sug.template}  ({size})")
        if sug.warning:
            out(f"        ! {sug.warning}")
        if pick and args.adicionar_recomendados:
            backup_collector.add_suggestion(recipe, catalogs, sug)
            added += 1
    if args.adicionar_recomendados:
        _save(tgt, recipe)
        out(f"{added} backup(s) recomendados incluídos. Capture com: winkit backup capturar")
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
    out(f'Backup "{item.name}" ({item.id}) → {item.template}')
    if warning:
        out(f"  ! {warning}")
    out("Capture com: winkit backup capturar " + item.id)
    return 0


def cmd_backup_listar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    recipe = load_profile_recipe(tgt.root, args.perfil)
    for b in recipe.backups:
        mark = "x" if b.selected else " "
        data = layout.payload(tgt.root, b.data_path)
        state = "capturado" if data.exists() else "ainda não capturado"
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
        flag = "ok " if item.ok else "não"
        vss = " (cópia de sombra)" if item.used_vss else ""
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
        out(f"Backup não encontrado: {args.id}")
        return 1
    recipe.backups = [b for b in recipe.backups if b.id != args.id]
    folder = layout.payload(tgt.root, item.data_path).parent
    if folder.is_dir() and folder.parent.name == "Backups":
        shutil.rmtree(folder)
    _save(tgt, recipe)
    out(f"Backup {args.id} removido da receita e do pendrive.")
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
    out(f'App portátil "{app.name}": pasta {item.template}, atalho para {args.exe}.')
    out("Capture com: winkit backup capturar " + item.id)
    return 0


def cmd_sincronizar(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    if not args.sem_backups:
        recipe = load_profile_recipe(tgt.root, args.perfil)
        out("Recapturando backups...")
        _capture(args, services, tgt, recipe, out, only=None)
    args.somente_xml = False
    args.agente = None
    return cmd_construir(args, services, out)


# ------------------------------------------------------------------ parser
def _add_collect_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    col = sub.add_parser("coletar", help="coleta do PC atual: drivers, apps, backups")
    col_sub = col.add_subparsers(dest="what", required=True)
    cdrv = col_sub.add_parser("drivers", parents=[common], help="exporta drivers de terceiros")
    cdrv.add_argument("--listar", action="store_true", help="só mostra, não exporta")
    cdrv.add_argument(
        "--todos", action="store_true", help="todas as classes, não só as recomendadas"
    )
    cdrv.add_argument("--classe", action="append", help="só estas classes (ex.: Net, Display)")
    cdrv.set_defaults(func=cmd_coletar_drivers)

    cbk = col_sub.add_parser(
        "backups", parents=[common], help="sugere pastas de configuração dos apps marcados"
    )
    cbk.add_argument("--adicionar-recomendados", action="store_true")
    cbk.set_defaults(func=cmd_coletar_backups)

    capp = col_sub.add_parser("apps", parents=[common], help="lê os apps instalados neste PC")
    capp.add_argument(
        "--incluir-redistribuiveis",
        action="store_true",
        help="inclui Visual C++, .NET etc. (normalmente vêm junto com os apps)",
    )
    capp.set_defaults(func=cmd_coletar_apps)


def _add_apps_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    apps = sub.add_parser("apps", help="escolher e preparar os aplicativos da receita")
    apps_sub = apps.add_subparsers(dest="action", required=True)
    apps_sub.add_parser("listar", parents=[common]).set_defaults(func=cmd_apps_listar)
    for name, value in (("marcar", True), ("desmarcar", False)):
        mk = apps_sub.add_parser(name, parents=[common])
        mk.add_argument("ids", nargs="+", help="ids dos apps (veja 'winkit apps listar')")
        mk.add_argument("--ordem", type=int, help="ordem de instalação (menor primeiro)")
        mk.add_argument(
            "--decidir-na-hora",
            action=argparse.BooleanOptionalAction,
            default=None,
            help="mostrar na janela do primeiro login para confirmar",
        )
        mk.set_defaults(func=cmd_apps_marcar, command_value=value)
    bx = apps_sub.add_parser(
        "baixar", parents=[common], help="baixa para o pendrive (offline) com winget download"
    )
    bx.add_argument("ids", nargs="*", help="padrão: todos os marcados que usam o winget")
    bx.set_defaults(func=cmd_apps_baixar)
    ad = apps_sub.add_parser("adicionar", parents=[common], help="usa um instalador seu")
    ad.add_argument("--instalador", required=True, help="caminho do .exe/.msi/.msix")
    ad.add_argument("--nome", required=True, help="nome do app")
    ad.add_argument("--args", help="argumentos silenciosos (padrão: detectados pelo tipo)")
    ad.add_argument("--escopo", choices=["machine", "user"], default="machine")
    ad.set_defaults(func=cmd_apps_adicionar)
    pt = apps_sub.add_parser("portatil", parents=[common], help="app sem instalador (só a pasta)")
    pt.add_argument("--pasta", required=True, help="pasta do programa neste PC")
    pt.add_argument("--nome", required=True)
    pt.add_argument("--exe", required=True, help="executável dentro da pasta (ex.: app.exe)")
    pt.set_defaults(func=cmd_apps_portatil)


def _add_backup_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    bk = sub.add_parser("backup", help="pastas e arquivos de configuração")
    bk_sub = bk.add_subparsers(dest="action", required=True)
    add = bk_sub.add_parser("adicionar", parents=[common], help="inclui uma pasta ou arquivo")
    add.add_argument("caminho", help=r"ex.: C:\Users\Voce\AppData\Roaming\discord")
    add.add_argument("--nome")
    add.add_argument(
        "--conflito",
        choices=["merge", "overwrite", "skip"],
        default="merge",
        help="se já existir no PC novo: mesclar (padrão), sobrescrever ou pular",
    )
    add.add_argument("--decidir-na-hora", action="store_true")
    add.set_defaults(func=cmd_backup_adicionar)
    bk_sub.add_parser("listar", parents=[common]).set_defaults(func=cmd_backup_listar)
    cap = bk_sub.add_parser("capturar", parents=[common], help="copia para o pendrive")
    cap.add_argument("ids", nargs="*")
    cap.add_argument("--sem-vss", action="store_true", help="não usar cópia de sombra")
    cap.set_defaults(func=cmd_backup_capturar)
    rm = bk_sub.add_parser("remover", parents=[common])
    rm.add_argument("id")
    rm.set_defaults(func=cmd_backup_remover)

    sync = sub.add_parser(
        "sincronizar",
        parents=[common],
        help="recaptura backups e atualiza o pendrive (só o que mudou)",
    )
    sync.add_argument("--sem-backups", action="store_true")
    sync.add_argument("--sem-vss", action="store_true")
    sync.set_defaults(func=cmd_sincronizar)


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--pendrive", help="letra da unidade do pendrive Ventoy (ex.: E:)")
    common.add_argument("--raiz", help="usar uma pasta como se fosse o pendrive (simulação)")
    common.add_argument("--sistema-arquivos", default="exFAT", help=argparse.SUPPRESS)
    common.add_argument("--perfil", default="padrao", help="perfil da receita (padrão: padrao)")

    parser = argparse.ArgumentParser(prog="winkit", description="WinKit Studio")
    parser.add_argument("--version", action="version", version=f"WinKit {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="mostra detalhes técnicos")
    sub = parser.add_subparsers(dest="command", required=True)

    pend = sub.add_parser("pendrive", help="pendrives Ventoy conectados")
    pend_sub = pend.add_subparsers(dest="action", required=True)
    pend_sub.add_parser("listar", parents=[common]).set_defaults(func=cmd_pendrive_listar)

    rec = sub.add_parser("receita", help="criar e consultar a receita")
    rec_sub = rec.add_subparsers(dest="action", required=True)
    nova = rec_sub.add_parser("nova", parents=[common], help="cria uma receita nova")
    nova.add_argument("--usuario", required=True, help="nome da conta local do Windows novo")
    nova.add_argument("--nome-pc", help="nome do computador")
    nova.add_argument("--sobrescrever", action="store_true")
    nova.set_defaults(func=cmd_receita_nova)

    pl = sub.add_parser("plano", parents=[common], help="mostra o que o Agente vai fazer")
    pl.add_argument("--windows", type=int, choices=[10, 11], default=11)
    pl.add_argument("--build", type=int, default=None)
    pl.add_argument("--sem-fase1", action="store_true", help="simula a Fase 1 não ter rodado")
    pl.set_defaults(func=cmd_plano)

    cons = sub.add_parser("construir", parents=[common], help="prepara o pendrive")
    cons.add_argument(
        "--somente-xml",
        action="store_true",
        help="só XMLs, ventoy.json e bootstrap (sem apps, drivers e backups)",
    )
    cons.add_argument("--agente", help="pasta do Agente compilado (winkit-agent)")
    cons.set_defaults(func=cmd_construir)

    _add_collect_parsers(sub, common)
    _add_apps_parsers(sub, common)
    _add_backup_parsers(sub, common)

    val = sub.add_parser("validar", parents=[common], help="confere o pendrive sem alterar nada")
    val.set_defaults(func=cmd_validar)
    return parser


def main(
    argv: Sequence[str] | None = None, *, services: Services | None = None, out: Out = _out
) -> int:
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
        out(f"Erro: {exc}")
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
