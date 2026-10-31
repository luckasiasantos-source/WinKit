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
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

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
from winkit.collector import drivers as driver_collector
from winkit.core import layout
from winkit.core.catalog.loader import default_catalogs
from winkit.core.errors import RecipeError, WinKitError
from winkit.core.planner.models import PlanContext
from winkit.core.planner.planner import plan
from winkit.core.recipe.io import new_recipe
from winkit.core.recipe.validation import validate_recipe
from winkit.core.text import human_size
from winkit.i18n import t
from winkit.platform.services import Services, real_services
from winkit.platform.session import is_admin
from winkit.platform.system import is_windows

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
        used = ", ".join(f"{k} {human_size(v)}" for k, v in report.sizes.items())
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
    out(t("validate.problems", count=len(rep.problems)))
    for p in rep.problems:
        out(f"  x {p}")
    return 1


def cmd_coletar_drivers(args: argparse.Namespace, services: Services, out: Out) -> int:
    tgt = _target(args, services)
    _require_admin()
    recipe = load_profile_recipe(tgt.root, args.perfil)
    catalogs = default_catalogs()
    candidates = driver_collector.list_candidates(services.drivers, catalogs)
    out(t("collect.drivers_found", count=len(candidates)))
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


# ------------------------------------------------------------------ parser
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

    col = sub.add_parser("coletar", help="coleta do PC atual: drivers, apps, backups")
    col_sub = col.add_subparsers(dest="what", required=True)
    cdrv = col_sub.add_parser("drivers", parents=[common], help="exporta drivers de terceiros")
    cdrv.add_argument("--listar", action="store_true", help="só mostra, não exporta")
    cdrv.add_argument(
        "--todos", action="store_true", help="todas as classes, não só as recomendadas"
    )
    cdrv.add_argument("--classe", action="append", help="só estas classes (ex.: Net, Display)")
    cdrv.set_defaults(func=cmd_coletar_drivers)

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
