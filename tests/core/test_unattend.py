from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tests.factories import recipe
from winkit.core.catalog.loader import default_catalogs
from winkit.core.catalog.models import RegSet
from winkit.core.errors import UnattendError
from winkit.core.unattend import commands
from winkit.core.unattend.generator import (
    NS,
    UnattendTarget,
    check_safety,
    encode_password,
    generate_unattend,
    template_name,
)

CAT = default_catalogs()
PID = "11111111-2222-3333-4444-555555555555"
SNAPSHOT = Path(__file__).resolve().parents[1] / "fixtures" / "unattend_default.xml"
N = {"u": NS}


def gen(r=None, *, lang="pt-BR", arch="amd64", os_major=11) -> ET.Element:
    data = generate_unattend(
        r or recipe(), CAT, UnattendTarget(lang, arch, os_major), pendrive_id=PID
    )
    return ET.fromstring(data)


def texts(root: ET.Element, path: str) -> list[str]:
    return [el.text or "" for el in root.findall(path, N)]


def test_snapshot_default_recipe() -> None:
    """Mudança no XML exige atualizar o snapshot conscientemente (R-42)."""
    data = generate_unattend(recipe(), CAT, UnattendTarget("pt-BR", "amd64", 11), pendrive_id=PID)
    if not SNAPSHOT.exists():  # pragma: no cover — primeira geração
        SNAPSHOT.write_bytes(data)
    assert data == SNAPSHOT.read_bytes()


def test_three_passes_in_order() -> None:
    root = gen()
    assert [s.get("pass") for s in root.findall("u:settings", N)] == [
        "windowsPE",
        "specialize",
        "oobeSystem",
    ]


def test_no_disk_configuration_ever() -> None:  # R-18 — teste de proteção
    root = gen()
    tags = {el.tag.split("}")[-1] for el in root.iter()}
    assert not tags & {
        "DiskConfiguration",
        "InstallTo",
        "ImageInstall",
        "InstallToAvailablePartition",
    }


def test_check_safety_rejects_disk_elements() -> None:
    bad = f'<unattend xmlns="{NS}"><settings><DiskConfiguration/></settings></unattend>'.encode()
    with pytest.raises(UnattendError, match="R-18"):
        check_safety(bad)
    with pytest.raises(UnattendError, match="inválido"):
        check_safety(b"<nao-fecha>")


def test_language_and_locale() -> None:
    root = gen(lang="en-US")
    assert texts(root, ".//u:SetupUILanguage/u:UILanguage") == ["en-US"]
    assert texts(root, ".//u:UILanguage") == ["en-US", "en-US", "en-US"]
    assert set(texts(root, ".//u:InputLocale")) == {"0416:00010416"}
    assert set(texts(root, ".//u:UserLocale")) == {"pt-BR"}
    r = recipe()
    r.windows.ui_language = "pt-BR"
    assert set(texts(gen(r, lang="en-US"), ".//u:UILanguage")) == {"pt-BR"}


def test_edition_key() -> None:
    assert texts(gen(), ".//u:ProductKey/u:Key") == ["VK7JG-NPHTM-C97JM-9MPGT-3V66T"]
    r = recipe()
    r.windows.edition = "home"
    assert texts(gen(r), ".//u:ProductKey/u:Key") == ["YTMG3-N6DKC-DKB77-7M9GH-8HVX7"]


def test_computer_name_and_timezone() -> None:
    assert texts(gen(), ".//u:ComputerName") == []
    r = recipe()
    r.windows.computer_name = "PC-SAMUEL"
    root = gen(r)
    assert texts(root, ".//u:ComputerName") == ["PC-SAMUEL"]
    assert set(texts(root, ".//u:TimeZone")) == {"E. South America Standard Time"}


def test_encryption_disabled_by_default() -> None:  # D-020
    paths = texts(gen(), ".//u:RunSynchronousCommand/u:Path")
    assert any("PreventDeviceEncryption" in p and '/d "1"' in p for p in paths)
    r = recipe()
    r.windows.prevent_device_encryption = False
    assert not any("PreventDeviceEncryption" in p for p in texts(gen(r), ".//u:Path"))


def test_bootstrap_is_last_specialize_command() -> None:
    root = gen()
    sp = root.findall("u:settings", N)[1]
    paths = texts(sp, ".//u:RunSynchronousCommand/u:Path")
    assert paths[-1] == commands.bootstrap_command(PID, "padrao")
    orders = texts(sp, ".//u:RunSynchronousCommand/u:Order")
    assert orders == [str(i) for i in range(1, len(orders) + 1)]


def test_labconfig_only_for_windows_11() -> None:
    assert any("BypassTPMCheck" in p for p in texts(gen(), ".//u:Path"))
    assert not any("BypassTPMCheck" in p for p in texts(gen(os_major=10), ".//u:Path"))


def test_dynamic_update_follows_recipe() -> None:
    assert texts(gen(), ".//u:DynamicUpdate/u:Enable") == ["false"]
    r = recipe()
    r.updates.during_setup = True
    assert texts(gen(r), ".//u:DynamicUpdate/u:Enable") == ["true"]


def test_empty_password() -> None:
    root = gen()
    assert texts(root, ".//u:LocalAccount/u:Password/u:Value") == [""]
    assert texts(root, ".//u:LocalAccount/u:Password/u:PlainText") == ["true"]
    assert texts(root, ".//u:AutoLogon/u:LogonCount") == ["1"]


def test_stored_password_is_encoded_not_plain() -> None:
    r = recipe()
    r.windows.account.password_mode = "stored"
    r.windows.account.password = "Minha&Senha<1>"
    data = generate_unattend(r, CAT, UnattendTarget("pt-BR", "amd64", 11), pendrive_id=PID)
    assert b"Minha" not in data
    root = ET.fromstring(data)
    values = texts(root, ".//u:Password/u:Value")
    assert values == [encode_password("Minha&Senha<1>")] * 2
    decoded = base64.b64decode(values[0]).decode("utf-16-le")
    assert decoded == "Minha&Senha<1>Password"


def test_no_autologon_when_disabled() -> None:
    r = recipe()
    r.windows.account.auto_logon = False
    assert gen(r).find(".//u:AutoLogon", N) is None


def test_special_characters_are_escaped() -> None:
    r = recipe()
    r.windows.account.display_name = 'Sam & "Lucas" <x>'
    root = gen(r)
    assert texts(root, ".//u:DisplayName") == ['Sam & "Lucas" <x>']


def test_account_and_oobe() -> None:
    root = gen()
    assert texts(root, ".//u:LocalAccount/u:Name") == ["Samuel"]
    assert texts(root, ".//u:LocalAccount/u:Group") == ["Administrators"]
    assert texts(root, ".//u:OOBE/u:HideOnlineAccountScreens") == ["true"]
    assert texts(root, ".//u:OOBE/u:ProtectYourPC") == ["3"]
    first = texts(root, ".//u:FirstLogonCommands/u:SynchronousCommand/u:CommandLine")
    assert first == [commands.first_logon_command()]


def test_architecture() -> None:
    root = gen(arch="arm64")
    archs = {c.get("processorArchitecture") for c in root.iter(f"{{{NS}}}component")}
    assert archs == {"arm64"}
    assert {c.get("processorArchitecture") for c in gen(arch="x86").iter(f"{{{NS}}}component")} == {
        "x86"
    }  # 32 bits: Windows 10, 8.1 e 7 (V3-14)
    with pytest.raises(UnattendError):
        gen(arch="mips")


def test_unknown_edition() -> None:
    r = recipe()
    object.__setattr__(r.windows, "edition", "inexistente")
    with pytest.raises(UnattendError):
        gen(r)


def test_template_name() -> None:
    assert template_name("padrao", "pt-BR", "amd64") == "winkit-padrao-pt-BR-amd64.xml"


# ------------------------------------------------------------------ comandos
def test_bootstrap_command_shape_and_length() -> None:
    cmd = commands.bootstrap_command(PID, "padrao")
    assert len(cmd) <= commands.MAX_COMMAND_LENGTH
    assert "%d:\\WinKit\\winkit.marker" in cmd
    assert cmd.endswith(f"%d: {PID} padrao")
    assert "(D E F" in cmd and " C " not in cmd.split("(")[1].split(")")[0]
    long_profile = "p" * 40
    assert len(commands.bootstrap_command(PID, long_profile)) <= commands.MAX_COMMAND_LENGTH


@pytest.mark.parametrize("bad", ["a b", "x&calc", "", "a;b", 'a"b'])
def test_bootstrap_command_rejects_unsafe_ids(bad: str) -> None:
    with pytest.raises(UnattendError):
        commands.bootstrap_command(bad, "padrao")
    with pytest.raises(UnattendError):
        commands.bootstrap_command(PID, bad)


def test_command_length_limit() -> None:
    with pytest.raises(UnattendError):
        commands._check("x" * 300)
    with pytest.raises(UnattendError):
        commands._check("a\nb")


def test_reg_add_command() -> None:
    op = RegSet(key=r"SYSTEM\X", value="V", type="dword", data=1)
    assert (
        commands.reg_add_command(op)
        == 'reg.exe add "HKLM\\SYSTEM\\X" /v "V" /t REG_DWORD /d "1" /f'
    )
    default_value = RegSet(key=r"SOFTWARE\Y", value="", type="sz", data="")
    assert "/ve" in commands.reg_add_command(default_value)
    multi = RegSet(key="K", value="M", type="multi_sz", data=["a", "b"])
    assert '/d "a\\0b"' in commands.reg_add_command(multi)
    with pytest.raises(UnattendError):
        commands.reg_add_command(RegSet(key="K", value="V", type="dword", data=1, hive="HKCU"))


def test_first_logon_command_guards_missing_agent() -> None:
    cmd = commands.first_logon_command()
    assert cmd.startswith("cmd.exe /c if exist")
    assert "phase2" in cmd


@pytest.mark.parametrize(
    ("lang", "text"),
    [
        ("pt-BR", "Conta local criada pelo WinKit"),
        ("en-US", "Local account created by WinKit"),
        ("es", "Cuenta local creada por WinKit"),
    ],
)
def test_account_description_follows_language(lang: str, text: str) -> None:
    from winkit.i18n import set_language

    set_language(lang)  # type: ignore[arg-type]
    root = gen()
    assert text in ET.tostring(root, encoding="unicode")
