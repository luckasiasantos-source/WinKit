"""Contas extras (V2-11): validação, XML, grupo pelo SID e backups "só a principal"."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from tests.agent.helpers import World, make_world
from winkit.agent.live import LiveOptions, run_live
from winkit.agent.phases import run_phase1, run_phase2
from winkit.agent.store import StateStore
from winkit.cli import main as cli
from winkit.core.catalog.loader import default_catalogs
from winkit.core.planner.models import PlanContext
from winkit.core.planner.planner import plan
from winkit.core.recipe.models import BackupItem, ExtraAccount
from winkit.core.recipe.validation import validate_recipe
from winkit.core.secrets import SECRETS
from winkit.core.unattend.generator import NS, UnattendTarget, generate_unattend
from winkit.platform.fakes.services import fake_services
from winkit.platform.fakes.system import FakeAccounts

SNAP = Path(__file__).resolve().parents[1] / "fixtures" / "unattend_extra_accounts.xml"
N = {"u": NS}


def _recipe(tmp_path: Path):  # type: ignore[no-untyped-def]
    r = make_world(tmp_path).recipe()
    r.windows.extra_accounts = [
        ExtraAccount(username="Ana", display_name="Ana & Cia", group="administrators"),
        ExtraAccount(username="Visita", group="users", password_mode="empty"),
    ]
    return r


def test_validation(tmp_path: Path) -> None:
    r = _recipe(tmp_path)
    assert validate_recipe(r, default_catalogs()).errors == []
    r.windows.extra_accounts.append(ExtraAccount(username="samuel"))  # igual à principal
    r.windows.extra_accounts.append(ExtraAccount(username="Administrador"))
    r.windows.extra_accounts.append(ExtraAccount(username="Com/barra"))
    r.windows.extra_accounts.append(ExtraAccount(username="Senha", password_mode="stored"))
    errors = validate_recipe(r, default_catalogs()).errors
    assert len(errors) == 4


def test_unattend_snapshot_with_two_extra_accounts(tmp_path: Path) -> None:
    r = _recipe(tmp_path)
    data = generate_unattend(
        r, default_catalogs(), UnattendTarget("pt-BR", "amd64", 11), pendrive_id="x" * 36
    )
    if not SNAP.exists():  # pragma: no cover — primeira geração (R-42)
        SNAP.write_bytes(data)
    assert data == SNAP.read_bytes()
    root = ET.fromstring(data)
    accounts = root.findall(".//u:LocalAccount", N)
    assert [a.findtext("u:Name", namespaces=N) for a in accounts] == ["Samuel", "Ana", "Visita"]
    assert [a.findtext("u:Group", namespaces=N) for a in accounts] == [
        "Administrators",
        "Administrators",
        "Users",
    ]
    assert root.find(".//u:AutoLogon/u:Username", N).text == "Samuel"  # type: ignore[union-attr]
    assert b"Ana &amp; Cia" in data


def _world(tmp_path: Path) -> World:
    w = make_world(tmp_path)
    r = w.recipe()
    r.windows.extra_accounts = [
        ExtraAccount(username="Ana", group="administrators", password_mode="empty"),
        ExtraAccount(username="Visita"),  # padrão, troca a senha no primeiro acesso
    ]
    w.save_recipe(r)
    accounts = w.services.accounts
    assert isinstance(accounts, FakeAccounts)
    accounts.users |= {"Ana", "Visita"}
    accounts.admins.add("Visita")  # o XML não garante o grupo em todo idioma (H11)
    return w


def test_phase1_fixes_groups_by_sid_and_expires_password(tmp_path: Path) -> None:
    w = _world(tmp_path)
    p = plan(w.recipe(), default_catalogs(), PlanContext(os_major=11, build=26100))
    assert [s.id for s in p.phase(1)][:2] == ["account:ana", "account:visita"]  # R24
    run_phase1(w.runtime())
    accounts = w.services.accounts
    assert isinstance(accounts, FakeAccounts)
    assert "Ana" in accounts.admins and "Visita" not in accounts.admins
    assert accounts.expired == {"Visita"}
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("account:visita").status == "done"


def test_missing_account_fails_and_live_never_touches(tmp_path: Path) -> None:
    w = _world(tmp_path)
    accounts = w.services.accounts
    assert isinstance(accounts, FakeAccounts)
    accounts.users.discard("Ana")
    preview = run_live(
        w.runtime(), LiveOptions(root=w.pendrive, simulate=True, restore_point=False)
    )
    assert preview.preview is not None and "account:ana" in preview.preview.not_live_safe
    run_phase1(w.runtime())
    state = StateStore(w.paths.state).load()
    assert state is not None and state.step("account:ana").status == "failed"


def test_backup_for_main_goes_to_phase2_user_profile(tmp_path: Path) -> None:
    r = _recipe(tmp_path)
    r.backups = [
        BackupItem(
            id="todos",
            name="Todos",
            template=r"{APPDATA}\A",
            data_path="Perfis/padrao/Backups/todos/dados",
        ),
        BackupItem(
            id="meu",
            name="Meu",
            template=r"{APPDATA}\B",
            data_path="Perfis/padrao/Backups/meu/dados",
            for_accounts="main",
        ),
    ]
    p = plan(r, default_catalogs(), PlanContext(os_major=11, build=26100))
    todos, meu = p.step("backup:todos"), p.step("backup:meu")
    assert todos is not None and (todos.phase, todos.target) == (1, "default_profile")
    assert meu is not None and (meu.phase, meu.target) == (2, "user_profile")


def test_stored_passwords_are_registered_as_secrets(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    r = w.recipe()
    r.windows.extra_accounts = [
        ExtraAccount(username="Ana", password_mode="stored", password="segredo-da-ana-42")
    ]
    w.save_recipe(r)
    accounts = w.services.accounts
    assert isinstance(accounts, FakeAccounts)
    accounts.users.add("Ana")
    run_phase1(w.runtime())
    run_phase2(w.runtime())
    assert SECRETS.mask("x segredo-da-ana-42 y") != "x segredo-da-ana-42 y"
    for path in w.paths.base.rglob("*"):
        if path.is_file() and path.name != "receita.json":
            assert b"segredo-da-ana-42" not in path.read_bytes(), path


def test_cli_accounts(tmp_path: Path) -> None:
    w = make_world(tmp_path)
    out: list[str] = []
    raiz = ["--raiz", str(w.pendrive)]

    def run(*argv: str) -> int:
        return cli.main([*argv, *raiz], services=fake_services(), out=out.append)

    assert run("contas", "adicionar", "Ana", "--admin") == 0
    assert run("accounts", "add", "Visita", "--sem-senha") == 0
    assert run("contas", "adicionar", "ana") == 1  # repetida
    extras = w.recipe().windows.extra_accounts
    assert [(a.username, a.group, a.password_mode) for a in extras] == [
        ("Ana", "administrators", "must_change"),
        ("Visita", "users", "empty"),
    ]
    assert run("contas", "remover", "visita") == 0
    assert [a.username for a in w.recipe().windows.extra_accounts] == ["Ana"]
    assert run("contas", "remover", "nada") == 1
