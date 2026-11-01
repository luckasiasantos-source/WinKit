"""ISO personalizada: uma **cópia** da ISO original com drivers, atualizações, edições e apps
de fábrica ajustados, e opcionalmente o WinKit inteiro dentro (V3-11, V3-12; D-044, D-048).

A ISO original só é lida (montada só para leitura); no fim, tamanho e data dela são conferidos
(R-64). Imagens montadas são sempre desmontadas, descartando se algo falhou (R-62).
"""

from __future__ import annotations

import shutil
import stat
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from winkit.builder import target as targets
from winkit.builder.build import BuildOptions, build
from winkit.core import layout
from winkit.core.catalog.models import Catalogs
from winkit.core.errors import WinKitError
from winkit.platform.disks import DiskInspector
from winkit.platform.image_tools import ImageTools
from winkit.platform.iso_mount import IsoMounter, mounted_iso
from winkit.platform.iso_writer import write_iso

Progress = Callable[[str, float], None]  # (etapa, fração da etapa)


@dataclass
class CustomIsoOptions:
    original: Path
    output: Path
    work_dir: Path
    #: Índices das edições a manter (vazio = todas).
    editions: list[int] = field(default_factory=list)
    drivers: list[Path] = field(default_factory=list)
    updates: list[Path] = field(default_factory=list)
    remove_apps: list[str] = field(default_factory=list)
    #: Pendrive com a pasta ``WinKit\\`` a embutir (ISO autossuficiente, V3-12).
    self_contained_from: Path | None = None
    profile_id: str = "padrao"
    agent_source: Path | None = None


def needed_space(original: Path, extra: int = 0) -> int:
    """Pasta de trabalho: cópia da ISO + imagem exportada + a ISO nova (+ conteúdo do WinKit)."""
    return 3 * original.stat().st_size + 2 * extra + 2 * 1024**3


def _writable_copy(src: Path, dst: Path, progress: Progress) -> None:
    files = [p for p in src.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files) or 1
    done = 0
    for p in files:
        out = dst / p.relative_to(src)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, out)
        out.chmod(stat.S_IREAD | stat.S_IWRITE)  # arquivos da ISO vêm somente leitura
        done += p.stat().st_size
        progress("copy", done / total)


def _service(
    tools: ImageTools, wim: Path, index: int, mount: Path, opts: CustomIsoOptions, *, boot: bool
) -> None:
    tools.mount(wim, index, mount)
    ok = False
    try:
        for d in opts.drivers:
            tools.add_drivers(mount, d)
        if not boot:
            for pkg in opts.updates:
                tools.add_package(mount, pkg)
            wanted = set(opts.remove_apps)
            for name in tools.provisioned_apps(mount):
                if name in wanted:
                    tools.remove_app(mount, name)
        ok = True
    finally:
        tools.unmount(mount, save=ok)


def build_custom_iso(
    opts: CustomIsoOptions,
    *,
    tools: ImageTools,
    mounter: IsoMounter,
    inspector: DiskInspector,
    catalogs: Catalogs,
    now: datetime,
    progress: Progress = lambda step, frac: None,
) -> Path:
    if opts.output.resolve() == opts.original.resolve():
        raise WinKitError("a ISO nova não pode substituir a original")
    before = opts.original.stat()
    work = opts.work_dir / "winkit-iso"
    tools.cleanup(work)
    shutil.rmtree(work, ignore_errors=True)
    media, mount = work / "midia", work / "montagem"
    try:
        with mounted_iso(mounter, opts.original) as drive:
            _writable_copy(drive, media, progress)
        sources = media / "sources"
        wim = next(
            (sources / n for n in ("install.wim", "install.esd") if (sources / n).is_file()), None
        )
        if wim is None:
            raise WinKitError("a ISO não tem sources\\install.wim nem install.esd")
        keep = opts.editions or [i.index for i in tools.images(wim)]
        new_wim = work / "install.wim"
        for n, index in enumerate(keep, 1):  # exportar também converte .esd em .wim
            tools.export(wim, index, new_wim)
            progress("export", n / len(keep))
        if opts.drivers or opts.updates or opts.remove_apps:
            for n in range(1, len(keep) + 1):
                _service(tools, new_wim, n, mount, opts, boot=False)
                progress("service", n / len(keep))
            if opts.drivers:  # o instalador também precisa ver o disco (ex.: NVMe, RAID)
                boot_wim = sources / "boot.wim"
                for index in (1, 2):
                    _service(tools, boot_wim, index, mount, opts, boot=True)
        wim.unlink()
        shutil.move(str(new_wim), sources / "install.wim")
        if opts.self_contained_from is not None:
            shutil.copytree(
                opts.self_contained_from / layout.WINKIT, media / layout.WINKIT, dirs_exist_ok=True
            )
            build(
                targets.from_folder(media),
                inspector,
                catalogs,
                BuildOptions(profile_id=opts.profile_id, agent_source=opts.agent_source),
                now=now,
            )
            progress("winkit", 1.0)
        write_iso(
            media, opts.output, progress=lambda done, total: progress("iso", done / max(total, 1))
        )
    finally:
        tools.cleanup(work)
        shutil.rmtree(work, ignore_errors=True)
    after = opts.original.stat()
    if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
        raise WinKitError("a ISO original mudou durante o processo; não use a cópia")  # R-64
    return opts.output
