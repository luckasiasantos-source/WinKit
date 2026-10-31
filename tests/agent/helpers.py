"""Ambiente de teste do Agente: pendrive simulado + "C:" simulado + serviços falsos."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from winkit.agent.executor import Waits
from winkit.agent.fakes import fake_agent_services
from winkit.agent.paths import AgentPaths
from winkit.agent.phases import Runtime
from winkit.agent.progress import NullUi
from winkit.agent.services import AgentServices
from winkit.builder import target as targets
from winkit.builder.build import BuildOptions, build, ensure_marker, save_profile_recipe
from winkit.core import layout
from winkit.core.catalog.loader import default_catalogs
from winkit.core.recipe.io import dump_recipe, new_recipe
from winkit.core.recipe.models import Recipe
from winkit.platform.fakes.disks import FakeDiskInspector, windows_iso
from winkit.platform.fakes.system import (
    FakeEnvironment,
)

START = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self._ticks = itertools.count()

    def __call__(self) -> datetime:
        return START + timedelta(seconds=next(self._ticks))


@dataclass
class World:
    tmp: Path
    pendrive: Path
    system: Path  # raiz do "C:" simulado
    services: AgentServices
    ui: NullUi = field(default_factory=NullUi)
    sleeps: list[float] = field(default_factory=list)

    @property
    def paths(self) -> AgentPaths:
        return AgentPaths(self.system / "ProgramData" / "WinKit")

    @property
    def env(self) -> FakeEnvironment:
        assert isinstance(self.services.env, FakeEnvironment)
        return self.services.env

    def runtime(self, **kw: object) -> Runtime:
        return Runtime(
            paths=self.paths,
            services=self.services,
            catalogs=default_catalogs(),
            clock=Clock(),
            sleep=self.sleeps.append,
            ui_factory=lambda r: self.ui,
            waits=Waits(pendrive_seconds=10, network_seconds=10, poll_seconds=5),
            **kw,  # type: ignore[arg-type]
        )

    def recipe(self) -> Recipe:
        from winkit.builder.build import load_profile_recipe

        return load_profile_recipe(self.pendrive, "padrao")

    def save_recipe(self, recipe: Recipe) -> None:
        save_profile_recipe(self.pendrive, recipe)
        self.bootstrap()

    def bootstrap(self) -> None:
        """Faz o que o bootstrap.ps1 faria: copia a receita e grava bootstrap.json."""
        base = self.paths.base
        base.mkdir(parents=True, exist_ok=True)
        (base / "receita.json").write_text(dump_recipe(self.recipe()), encoding="utf-8")
        marker = layout.read_marker(self.pendrive)
        assert marker is not None
        (base / "bootstrap.json").write_text(
            f'{{"pendrive_id": "{marker.pendrive_id}", "profile": "padrao"}}', encoding="utf-8"
        )


def make_world(tmp: Path) -> World:
    pendrive = tmp / "pendrive"
    pendrive.mkdir()
    (pendrive / "Windows11.iso").write_bytes(b"iso")
    marker = ensure_marker(pendrive, START)
    save_profile_recipe(
        pendrive, new_recipe(pendrive_id=marker.pendrive_id, username="Samuel", now=START)
    )
    build(
        targets.from_folder(pendrive),
        FakeDiskInspector(isos={"Windows11.iso": windows_iso()}),
        default_catalogs(),
        BuildOptions(),
        now=START,
    )
    system = tmp / "C"
    (system / "Windows" / "Setup" / "Scripts").mkdir(parents=True)
    (system / "Windows" / "Panther").mkdir(parents=True)
    (system / "Users" / "Samuel" / "Desktop").mkdir(parents=True)
    services = fake_agent_services(pendrive=pendrive, system=system)
    world = World(tmp=tmp, pendrive=pendrive, system=system, services=services)
    world.bootstrap()
    return world
