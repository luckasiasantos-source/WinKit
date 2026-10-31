"""Ponto de entrada do Agente: ``winkit-agent.exe phase1 | phase2 | retry | summary``."""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from winkit import __version__
from winkit.agent import phases
from winkit.agent.eventlog import EventLog
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.paths import AgentPaths
from winkit.agent.phases import Runtime
from winkit.agent.services import real_agent_services
from winkit.agent.ui_select import select_ui
from winkit.core.catalog.loader import default_catalogs
from winkit.platform.locale import detect_language
from winkit.platform.system import winkit_program_data


def import_phase1_modules() -> None:
    """Teste de proteção (R-35): importar este módulo não pode carregar Qt.

    Todos os módulos da Fase 1 já foram importados no topo deste arquivo; a janela Qt só é
    importada dentro de ``select_ui``, quando o modo exige.
    """


def _now() -> datetime:
    return datetime.now(UTC).astimezone()


def _crash_file(exc: BaseException) -> None:
    try:
        base = winkit_program_data() / "Logs"
        base.mkdir(parents=True, exist_ok=True)
        with (base / "agente-erro-fatal.log").open("a", encoding="utf-8") as fh:
            fh.write(f"{_now().isoformat()} WinKit {__version__}\n")
            fh.write("".join(traceback.format_exception(exc)) + "\n")
    except OSError:
        pass


def open_file(path: Path) -> None:
    """Abre com o programa padrão (navegador para o resumo). Substituível nos testes."""
    if sys.platform == "win32":  # pragma: no cover
        os.startfile(path)  # noqa: S606


def build_runtime() -> Runtime:
    return Runtime(
        paths=AgentPaths(winkit_program_data()),
        services=real_agent_services(),
        catalogs=default_catalogs(),
        clock=_now,
        ui_factory=select_ui,
        detect_language=detect_language,
        catalog_loader=default_catalogs,
    )


def _ensure_streams() -> None:
    """Executável sem console (D-015): stdout/stderr são None e o argparse quebraria."""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115, PTH123
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115, PTH123


def run_phase2_with_ui(rt: Runtime, *, retry: bool = False) -> int:
    """Cria a interface conforme o modo da receita e roda a Fase 2 dentro dela."""
    recipe = phases.load_agent_recipe(rt, EventLog(rt.paths.logs, rt.clock))
    if recipe is None:
        return phases.run_phase2(rt, retry_failed=retry)
    ui = rt.ui_factory(recipe)
    host = getattr(ui, "host", None)
    if host is None:
        return phases.run_phase2(rt, retry_failed=retry)
    fixed = replace(rt, ui_factory=lambda _recipe: ui)
    code: int = host(lambda: phases.run_phase2(fixed, retry_failed=retry))
    return code


def live_options(args: argparse.Namespace) -> LiveOptions:
    kinds = frozenset(k.strip() for k in args.somente.split(",") if k.strip())
    return LiveOptions(
        root=Path(args.root),
        profile_id=args.perfil,
        simulate=args.simular,
        only_kinds=kinds or None,
        restore_point=not args.sem_ponto_de_restauracao,
    )


def run_apply_command(rt: Runtime, args: argparse.Namespace) -> int:
    result = run_live(rt, live_options(args))
    if result.summary_html is not None and not args.simular:
        open_file(result.summary_html)
    return result.code


def main(argv: Sequence[str] | None = None) -> int:
    _ensure_streams()
    parser = argparse.ArgumentParser(prog="winkit-agent", description="Agente do WinKit")
    parser.add_argument("--version", action="version", version=f"WinKit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("phase1", help="Fase 1: antes do login (SetupComplete.cmd)")
    p2 = sub.add_parser("phase2", help="Fase 2: depois do login")
    p2.add_argument("--first-logon", action="store_true", help="chamado pelo FirstLogonCommands")
    sub.add_parser("retry", help="tenta de novo as etapas que falharam")
    sub.add_parser("summary", help="abre o resumo")
    ap = sub.add_parser("apply", help="aplica a receita neste Windows (modo ao vivo, D-033)")
    ap.add_argument("--root", required=True, help="pasta que contém WinKit\\ (o pendrive)")
    ap.add_argument("--perfil", default="padrao")
    ap.add_argument("--simular", action="store_true", help="só a prévia; não muda nada")
    ap.add_argument("--somente", default="", help="tipos de etapa separados por vírgula")
    ap.add_argument("--sem-ponto-de-restauracao", action="store_true")
    args = parser.parse_args(argv)

    try:
        rt = build_runtime()
        if args.command == "phase1":
            return phases.run_phase1(rt)
        if args.command == "phase2":
            return run_phase2_with_ui(rt)
        if args.command == "retry":
            return run_phase2_with_ui(rt, retry=True)
        if args.command == "apply":
            return run_apply_command(rt, args)
        html = phases.open_summary(rt.paths)
        if html is not None:
            open_file(html)
        return 0 if html else 1
    except BaseException as exc:  # noqa: BLE001 — a Fase 1 nunca pode quebrar o SetupComplete
        _crash_file(exc)
        return 0 if args.command == "phase1" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
