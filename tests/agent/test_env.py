"""Variáveis de ambiente e PATH (V2-22): moldes, mescla do PATH, coleta, etapa e CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.agent.helpers import World, make_world
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.phases import run_phase1
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.collector.env import collect_env
from winkit.core.catalog.loader import default_catalogs
from winkit.core.env import MACHINE_ENV_KEY, merge_path, to_env_template
from winkit.core.recipe.models import EnvPathEntry, EnvVar
from winkit.core.recipe.validation import validate_recipe
from winkit.platform.fakes.registry import FakeRegistry
from winkit.platform.fakes.services import fake_services
from winkit.platform.fakes.system import FakeEnvironment
from winkit.platform.registry import DEFAULT_HIVE_MOUNT

OLD = {
    "USERPROFILE": r"C:\Users\Samuel",
    "LOCALAPPDATA": r"C:\Users\Samuel\AppData\Local",
    "APPDATA": r"C:\Users\Samuel\AppData\Roaming",
    "PROGRAMFILES": r"C:\Program Files",
    "PROGRAMDATA": r"C:\ProgramData",
}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (r"C:\Users\Samuel\go", r"%USERPROFILE%\go"),
        (r"c:\users\samuel\AppData\Local\Programs\x", r"%LOCALAPPDATA%\Programs\x"),
        (r"C:\Program Files\Java\jdk-21", r"%ProgramFiles%\Java\jdk-21"),
        (r"C:\Windows\System32", r"%SystemRoot%\System32"),
        (r"D:\ferramentas", r"D:\ferramentas"),
        ("só texto", "só texto"),
        (r"C:\Users\Samuel\a;D:\b", r"%USERPROFILE%\a;D:\b"),
    ],
)
def test_to_env_template(raw: str, expected: str) -> None:
    value, _ = to_env_template(raw, OLD, windows_dir=r"C:\Windows")
    assert value == expected


def test_merge_path_never_removes_or_duplicates() -> None:
    current = r"%SystemRoot%\system32;C:\Tools\;%USERPROFILE%\go\bin"
    new, added = merge_path(
        current, [r"c:\tools", r"%USERPROFILE%\GO\BIN\\", r"D:\novo", r"D:\novo"]
    )
    assert added == [r"D:\novo"]
    assert new == current + r";D:\novo"
    assert merge_path(current, [r"C:\Tools"]) == (current, [])
    assert merge_path(None, [r"D:\x"]) == (r"D:\x", [r"D:\x"])
    assert merge_path("a;", ["b"]) == ("a;b", ["b"])


def old_pc_registry() -> FakeRegistry:
    reg = FakeRegistry()
    reg.set("HKCU", "Environment", "GOPATH", "sz", r"C:\Users\Samuel\go")
    reg.set("HKCU", "Environment", "TEMP", "expand_sz", r"%USERPROFILE%\AppData\Local\Temp")
    reg.set("HKCU", "Environment", "OneDrive", "sz", r"C:\Users\Samuel\OneDrive")
    reg.set(
        "HKCU",
        "Environment",
        "Path",
        "expand_sz",
        r"%USERPROFILE%\AppData\Local\Microsoft\WindowsApps;C:\Users\Samuel\go\bin",
    )
    reg.set("HKLM", MACHINE_ENV_KEY, "JAVA_HOME", "sz", r"C:\Program Files\Java\jdk-21")
    reg.set("HKLM", MACHINE_ENV_KEY, "Path", "expand_sz", r"%SystemRoot%\system32;D:\ferramentas")
    reg.set("HKLM", MACHINE_ENV_KEY, "NUMBER_OF_PROCESSORS", "sz", "8")
    return reg


def test_collect_only_non_default_and_unselected(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    r = w.recipe()
    vars_, paths = collect_env(
        old_pc_registry(), r, default_catalogs().protected_env, OLD, r"C:\Windows"
    )
    assert {(v.name, v.value, v.scope) for v in vars_} == {
        ("GOPATH", r"%USERPROFILE%\go", "user"),
        ("JAVA_HOME", r"%ProgramFiles%\Java\jdk-21", "machine"),
    }
    assert all(v.kind == "expand_sz" and not v.selected for v in vars_)
    assert {(p.value, p.scope) for p in paths} == {
        (r"%USERPROFILE%\go\bin", "user"),
        (r"D:\ferramentas", "machine"),
    }
    again = collect_env(old_pc_registry(), r, default_catalogs().protected_env, OLD, None)
    assert again == ([], [])  # não duplica


def test_validation_rejects_protected_names(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    r = w.recipe()
    r.environment.variables = [EnvVar(name="TEMP", value="x"), EnvVar(name="A", value="1")]
    errors = validate_recipe(r, default_catalogs()).errors
    assert any("TEMP" in e for e in errors) and not any(" A " in e for e in errors)


def _world(tmp_path: Path) -> World:
    w = make_world(tmp_path)
    r = w.recipe()
    r.environment.variables = [
        EnvVar(name="GOPATH", value=r"%USERPROFILE%\go"),
        EnvVar(name="JAVA_HOME", value=r"%ProgramFiles%\Java\jdk-21", scope="machine"),
        EnvVar(name="EDITOR", value="code", kind="sz"),
    ]
    r.environment.path_entries = [
        EnvPathEntry(value=r"%USERPROFILE%\go\bin"),
        EnvPathEntry(value=r"D:\ferramentas", scope="machine"),
        EnvPathEntry(value=r"D:\nao-levar", scope="machine", selected=False),
    ]
    w.save_recipe(r)
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    reg.set("HKLM", MACHINE_ENV_KEY, "Path", "expand_sz", r"%SystemRoot%\system32")
    return w


def test_phase1_machine_and_default_profile(tmp_path: Path) -> None:
    w = _world(tmp_path)
    run_phase1(w.runtime())
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    assert reg.get("HKLM", MACHINE_ENV_KEY, "JAVA_HOME") == r"%ProgramFiles%\Java\jdk-21"
    assert reg.get("HKLM", MACHINE_ENV_KEY, "Path") == r"%SystemRoot%\system32;D:\ferramentas"
    default = rf"{DEFAULT_HIVE_MOUNT}\Environment"
    assert reg.get("HKU", default, "GOPATH") == r"%USERPROFILE%\go"
    assert reg.get_type("HKU", default, "GOPATH") == "expand_sz"
    assert reg.get_type("HKU", default, "EDITOR") == "sz"
    assert reg.get("HKU", default, "Path") == r"%USERPROFILE%\go\bin"
    assert reg.mounted == {}
    state = StateStore(w.paths.state).load()
    assert state is not None
    assert all(state.step(k).status == "done" for k in state.steps if k.startswith("env:"))


def test_live_never_overwrites_without_replace(tmp_path: Path) -> None:
    w = _world(tmp_path)
    reg = w.services.registry
    assert isinstance(reg, FakeRegistry)
    reg.set("HKCU", "Environment", "GOPATH", "sz", r"D:\meu-go")
    kinds = frozenset({"env"})
    opts = {"root": w.pendrive, "restore_point": False, "only_kinds": kinds}
    preview = run_live(w.runtime(), LiveOptions(simulate=True, **opts))  # type: ignore[arg-type]
    assert preview.preview is not None
    go = next(i for i in preview.preview.items if i.step_id == "env:var.user.GOPATH")
    assert go.status == "not_applicable" and go.warnings  # mostra os dois valores
    result = run_live(w.runtime(), LiveOptions(**opts))  # type: ignore[arg-type]
    assert reg.get("HKCU", "Environment", "GOPATH") == r"D:\meu-go"
    assert reg.get("HKCU", "Environment", "EDITOR") == "code"
    assert result.run_dir is not None
    state = StateStore(result.run_dir / "estado.json").load()
    assert state is not None and state.step("env:var.user.GOPATH").status == "skipped"
    env = w.services.env
    assert isinstance(env, FakeEnvironment) and env.broadcasts > 0  # avisa os programas abertos

    r = w.recipe()
    r.environment.variables[0].on_conflict = "replace"
    w.save_recipe(r)
    run_live(w.runtime(), LiveOptions(**opts))  # type: ignore[arg-type]
    assert reg.get("HKCU", "Environment", "GOPATH") == r"%USERPROFILE%\go"


def test_cli_env(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    services = fake_services(registry=old_pc_registry())
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=services, out=out.append)

    assert run("coletar", "variaveis") == 0
    env = w.recipe().environment
    assert {v.name for v in env.variables} == {"GOPATH", "JAVA_HOME"}
    assert not any(v.selected for v in env.variables)
    assert run("variaveis", "marcar", "GOPATH", "D:\\ferramentas") == 0
    env = w.recipe().environment
    assert [v.name for v in env.variables if v.selected] == ["GOPATH"]
    assert [p.value for p in env.path_entries if p.selected] == [r"D:\ferramentas"]
    assert run("env", "set", "EDITOR", "code", "--substituir") == 0
    assert run("variaveis", "definir", "PATH", r"D:\bin", "--sistema") == 0
    assert run("variaveis", "definir", "TEMP", "x") == 1
    env = w.recipe().environment
    editor = next(v for v in env.variables if v.name == "EDITOR")
    assert editor.on_conflict == "replace"
    assert any(p.value == r"D:\bin" and p.scope == "machine" for p in env.path_entries)
