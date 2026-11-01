"""Comandos da v3 na CLI (PLANO_V3 §5.5): ISO, gravar pendrive, backup do PC e ferramentas."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from winkit.builder.custom_iso import CustomIsoOptions, build_custom_iso
from winkit.builder.usb_media import write_usb
from winkit.collector import pc_backup
from winkit.collector.backups import local_source
from winkit.core import pc_backup as core_pc
from winkit.core.catalog.loader import default_catalogs
from winkit.core.errors import WinKitError
from winkit.core.usb_safety import refusal_reasons
from winkit.i18n import render, t
from winkit.i18n.format import format_duration, format_size
from winkit.platform import download as dl
from winkit.platform import external_tools
from winkit.platform.services import Services
from winkit.platform.windows_download import tools_dir

Out = Callable[[str], None]


def _need(value: Any, what: str) -> Any:
    if value is None:
        raise WinKitError(t("cli.v3.unavailable", what=what))
    return value


def _every_5(out: Out) -> Callable[[float], None]:
    last = [-5]

    def show(fraction: float) -> None:
        pct = int(fraction * 100)
        if pct >= last[0] + 5:
            last[0] = pct
            out(t("cli.v3.progress", percent=pct))

    return show


def cmd_iso_baixar(args: argparse.Namespace, services: Services, out: Out) -> int:
    links = _need(services.iso_links, "iso_links")
    if args.versao == "7":
        raise WinKitError(t("studio.download.no_win7"))
    url = links.url(args.versao, args.arquitetura, args.idioma)
    show = _every_5(out)
    path = dl.download(url, Path(args.saida), progress=lambda p: show(p.fraction or 0))
    info = services.disks.read_iso(path, path.name)
    if not info.is_windows:
        raise WinKitError(t("cli.v3.not_windows_iso", path=str(path)))
    out(t("cli.v3.iso_done", path=str(path)))
    return 0


def cmd_iso_personalizar(args: argparse.Namespace, services: Services, out: Out) -> int:
    original, saida = Path(args.original), Path(args.saida)
    opts = CustomIsoOptions(
        original=original,
        output=saida,
        work_dir=Path(args.trabalho) if args.trabalho else saida.parent,
        editions=args.edicao or [],
        drivers=[Path(d) for d in args.drivers or []],
        updates=[Path(u) for u in args.atualizacao or []],
        self_contained_from=Path(args.raiz) if args.autossuficiente and args.raiz else None,
        profile_id=args.perfil,
    )
    show = _every_5(out)
    build_custom_iso(
        opts,
        tools=_need(services.image_tools, "image_tools"),
        mounter=_need(services.iso_mounter, "iso_mounter"),
        inspector=services.disks,
        catalogs=default_catalogs(),
        now=datetime.now(UTC),
        progress=lambda step, frac: show(frac) if step == "iso" else None,
    )
    out(t("cli.v3.iso_done", path=str(saida)))
    return 0


def cmd_pendrive_gravar(args: argparse.Namespace, services: Services, out: Out) -> int:
    writer = _need(services.usb_writer, "usb_writer")
    disk = next((d for d in writer.usb_disks() if d.number == args.disco), None)
    if disk is None:
        raise WinKitError(t("usb.refuse_gone"))
    reasons = refusal_reasons(disk, disk, args.confirmar)
    for r in reasons:
        out("! " + render(r))
    if reasons:
        return 1
    if args.simular:
        out(t("cli.v3.would_erase", model=disk.model, size=format_size(disk.size)))
        return 0
    letter = write_usb(
        Path(args.iso),
        disk,
        args.confirmar,
        args.boot,
        writer=writer,
        tools=_need(services.image_tools, "image_tools"),
        mounter=_need(services.iso_mounter, "iso_mounter"),
        runner=services.runner,
        volume_root=services.volume_root,
    )
    out(t("studio.writeusb.done", letter=letter))
    return 0


def _source_root(services: Services) -> Callable[[str], Path]:
    return lambda literal: local_source(services.volume_root(literal[:2].upper()), literal)


def cmd_backup_pc_fazer(args: argparse.Namespace, services: Services, out: Out) -> int:
    folders = {**services.folders.machine(), **services.folders.current_user()}
    literals = args.pasta or pc_backup.default_literals(folders)
    sources = pc_backup.make_sources(literals, folders)
    dest = services.volume_root(args.destino.upper().rstrip("\\"))
    if args.simular:
        files = [f for s in sources for f in pc_backup.scan(_source_root(services)(s.literal))]
        total = sum(f.size for f in files)
        speed, per_file = pc_backup.measure_speed(dest / core_pc.BACKUP_DIR)
        secs = core_pc.estimate_seconds(total, len(files), speed, per_file)
        out(t("studio.pcbackup.estimate_title", size=format_size(total), n=len(files)))
        out(t("studio.pcbackup.estimate_detail", time=format_duration(secs), speed=f"{speed:.0f}"))
        return 0
    manifest = pc_backup.run_backup(
        sources,
        dest,
        computer=os.environ.get("COMPUTERNAME") or "pc",
        now=datetime.now(UTC),
        zip_mode=args.zip,
        source_root=_source_root(services),
    )
    out(t("studio.pcbackup.done", n=len(manifest.files), size=format_size(manifest.total_bytes)))
    for key, why in manifest.failed.items():
        out(f"! {key}: {why}")
    return 1 if manifest.failed else 0


def cmd_backup_pc_restaurar(args: argparse.Namespace, services: Services, out: Out) -> int:
    found = core_pc.find_backups([services.volume_root(args.origem.upper().rstrip("\\"))])
    if not found:
        out(t("studio.pcbackup.none_found"))
        return 1
    base, manifest = max(found, key=lambda bm: bm[1].updated_at)
    folders = {**services.folders.machine(), **services.folders.current_user()}
    report = core_pc.restore(
        base,
        manifest,
        core_pc.restore_targets(manifest, folders),
        target_root=_source_root(services),
    )
    out(
        t(
            "studio.pcbackup.restored",
            copied=report.copied,
            kept=report.kept,
            failed=len(report.failed),
        )
    )
    return 1 if report.failed else 0


def cmd_ferramenta_baixar(args: argparse.Namespace, services: Services, out: Out) -> int:
    del services
    source = default_catalogs().download(args.nome)
    if source is None:
        raise WinKitError(t("cli.not_found", ids=args.nome))
    release = external_tools.latest_release(source)
    exe = external_tools.fetch(source, tools_dir(), release=release)
    out(t("cli.v3.tool_done", name=source.name, path=str(exe)))
    return 0


def add_pendrive_write(pend_sub: Any, common: argparse.ArgumentParser) -> None:
    g = pend_sub.add_parser("gravar", aliases=["write"], parents=[common], help=t("cli.h.v3_write"))
    g.add_argument("--iso", required=True, help=t("cli.h.v3_iso"))
    g.add_argument("--disco", type=int, required=True, help=t("cli.h.v3_disk"))
    g.add_argument("--confirmar", required=True, help=t("cli.h.v3_confirm"))
    g.add_argument("--boot", choices=["uefi_bios", "uefi", "bios"], default="uefi_bios")
    g.add_argument("--simular", action="store_true", help=t("cli.h.simulate"))
    g.set_defaults(func=cmd_pendrive_gravar)


def add_parsers(sub: Any, common: argparse.ArgumentParser) -> None:
    iso = sub.add_parser("iso", help=t("cli.h.v3_iso_cmd"))
    iso_sub = iso.add_subparsers(dest="action", required=True)
    b = iso_sub.add_parser("baixar", aliases=["download"], parents=[common])
    b.add_argument("--versao", choices=["11", "10", "8.1"], default="11")
    b.add_argument("--arquitetura", choices=["x64", "x86"], default="x64")
    b.add_argument("--idioma", default="pt-BR")
    b.add_argument("--saida", required=True, help=t("cli.h.v3_output"))
    b.set_defaults(func=cmd_iso_baixar)
    p = iso_sub.add_parser("personalizar", aliases=["customize"], parents=[common])
    p.add_argument("--original", required=True, help=t("cli.h.v3_iso"))
    p.add_argument("--saida", required=True, help=t("cli.h.v3_output"))
    p.add_argument("--trabalho", help=t("cli.h.v3_work"))
    p.add_argument("--edicao", type=int, action="append", help=t("cli.h.v3_edition"))
    p.add_argument("--drivers", action="append", help=t("cli.h.v3_drivers"))
    p.add_argument("--atualizacao", action="append", help=t("cli.h.v3_update"))
    p.add_argument("--autossuficiente", action="store_true", help=t("cli.h.v3_self"))
    p.set_defaults(func=cmd_iso_personalizar)

    bk = sub.add_parser("backup-pc", aliases=["pc-backup"], help=t("cli.h.v3_backup_cmd"))
    bk_sub = bk.add_subparsers(dest="action", required=True)
    f = bk_sub.add_parser("fazer", aliases=["run"], parents=[common])
    f.add_argument("--destino", required=True, help=t("cli.h.v3_dest"))
    f.add_argument("--pasta", action="append", help=t("cli.h.v3_folder"))
    f.add_argument("--zip", action="store_true", help=t("studio.pcbackup.zip"))
    f.add_argument("--simular", action="store_true", help=t("cli.h.v3_estimate"))
    f.set_defaults(func=cmd_backup_pc_fazer)
    r = bk_sub.add_parser("restaurar", aliases=["restore"], parents=[common])
    r.add_argument("--origem", required=True, help=t("cli.h.v3_dest"))
    r.set_defaults(func=cmd_backup_pc_restaurar)

    fe = sub.add_parser("ferramenta", aliases=["tool"], help=t("cli.h.v3_tool_cmd"))
    fe_sub = fe.add_subparsers(dest="action", required=True)
    fb = fe_sub.add_parser("baixar", aliases=["download"], parents=[common])
    fb.add_argument("nome", choices=["ventoy", "rufus"])
    fb.set_defaults(func=cmd_ferramenta_baixar)
