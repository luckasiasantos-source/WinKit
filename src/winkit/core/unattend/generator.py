"""Geração do ``autounattend.xml`` (PLANO.md §9).

Construído com ``xml.etree.ElementTree`` (R-24). Nunca contém configuração de disco
(R-18, D-017): o usuário sempre escolhe o disco no instalador.
"""

from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from winkit.core.catalog.models import Catalogs
from winkit.core.errors import UnattendError
from winkit.core.recipe.models import Account, Recipe
from winkit.core.unattend.commands import (
    bootstrap_command,
    first_logon_command,
    labconfig_commands,
    reg_add_command,
)
from winkit.i18n import t

NS = "urn:schemas-microsoft-com:unattend"
WCM = "http://schemas.microsoft.com/WMIConfig/2002/State"
ET.register_namespace("", NS)
ET.register_namespace("wcm", WCM)

#: Elementos que configurariam disco/partição — proibidos (R-18).
FORBIDDEN_ELEMENTS = (
    "DiskConfiguration",
    "InstallTo",
    "InstallToAvailablePartition",
    "ImageInstall",
)
ENCRYPTION_TWEAK = "system.prevent_device_encryption"


@dataclass(frozen=True)
class UnattendTarget:
    ui_language: str  # idioma presente na ISO (§9.5)
    architecture: str  # "amd64" | "arm64"
    os_major: int | None  # 10 | 11 | None


def template_name(profile_id: str, language: str, architecture: str) -> str:
    return f"winkit-{profile_id}-{language}-{architecture}.xml"


def _q(tag: str) -> str:
    return f"{{{NS}}}{tag}"


def _sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    el = ET.SubElement(parent, _q(tag))
    if text is not None:
        el.text = text
    return el


def _component(settings: ET.Element, name: str, arch: str) -> ET.Element:
    return ET.SubElement(
        settings,
        _q("component"),
        {
            "name": name,
            "processorArchitecture": arch,
            "publicKeyToken": "31bf3856ad364e35",
            "language": "neutral",
            "versionScope": "nonSxS",
        },
    )


def _bool(value: bool) -> str:
    return "true" if value else "false"


def encode_password(password: str) -> str:
    """Formato "ocultado" do Windows: Base64(UTF-16LE(senha + "Password")). Não é criptografia."""
    return base64.b64encode((password + "Password").encode("utf-16-le")).decode("ascii")


def _password(parent: ET.Element, account: Account) -> None:
    pw = _sub(parent, "Password")
    if account.password_mode == "stored" and account.password:  # noqa: S105
        _sub(pw, "Value", encode_password(account.password))
        _sub(pw, "PlainText", "false")
    else:
        _sub(pw, "Value", "")
        _sub(pw, "PlainText", "true")


def _run_sync(
    parent: ET.Element, container: str, item: str, commands: list[tuple[str, str]]
) -> None:
    rs = _sub(parent, container)
    for order, (description, path) in enumerate(commands, start=1):
        cmd = ET.SubElement(rs, _q(item), {f"{{{WCM}}}action": "add"})
        _sub(cmd, "Description", description)
        _sub(cmd, "Order", str(order))
        _sub(cmd, "Path", path)


def generate_unattend(
    recipe: Recipe, catalogs: Catalogs, target: UnattendTarget, *, pendrive_id: str
) -> bytes:
    arch = target.architecture
    if arch not in ("amd64", "arm64"):
        raise UnattendError(f"arquitetura sem suporte: {arch}")
    edition = catalogs.edition(recipe.windows.edition)
    if edition is None:
        raise UnattendError(f"edição desconhecida: {recipe.windows.edition}")
    win = recipe.windows
    ui_lang = target.ui_language if win.ui_language == "auto" else win.ui_language

    root = ET.Element(_q("unattend"))
    _windows_pe(root, recipe, arch, ui_lang, key=edition.generic_key, os_major=target.os_major)
    _specialize(root, recipe, catalogs, arch, pendrive_id)
    _oobe_system(root, recipe, arch, ui_lang)

    ET.indent(root, space="  ")
    data: bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    check_safety(data)
    return data + b"\n"


def _windows_pe(
    root: ET.Element, recipe: Recipe, arch: str, ui_lang: str, *, key: str, os_major: int | None
) -> None:
    win = recipe.windows
    pe = ET.SubElement(root, _q("settings"), {"pass": "windowsPE"})
    intl = _component(pe, "Microsoft-Windows-International-Core-WinPE", arch)
    _sub(intl, "InputLocale", win.input_locale)
    _sub(_sub(intl, "SetupUILanguage"), "UILanguage", ui_lang)
    _sub(intl, "SystemLocale", win.system_locale)
    _sub(intl, "UILanguage", ui_lang)
    _sub(intl, "UserLocale", win.user_locale)

    setup = _component(pe, "Microsoft-Windows-Setup", arch)
    du = _sub(setup, "DynamicUpdate")
    _sub(du, "Enable", _bool(recipe.updates.during_setup))
    _sub(du, "WillShowUI", "OnError")
    if os_major != 10:
        bypass = [("WinKit: requisitos do Windows 11", c) for c in labconfig_commands()]
        _run_sync(setup, "RunSynchronous", "RunSynchronousCommand", bypass)
    ud = _sub(setup, "UserData")
    _sub(ud, "AcceptEula", "true")
    pk = _sub(ud, "ProductKey")
    _sub(pk, "Key", key)
    _sub(pk, "WillShowUI", "OnError")


def _specialize(
    root: ET.Element, recipe: Recipe, catalogs: Catalogs, arch: str, pendrive_id: str
) -> None:
    win = recipe.windows
    sp = ET.SubElement(root, _q("settings"), {"pass": "specialize"})
    shell = _component(sp, "Microsoft-Windows-Shell-Setup", arch)
    if win.computer_name:
        _sub(shell, "ComputerName", win.computer_name)
    _sub(shell, "TimeZone", win.time_zone)

    commands: list[tuple[str, str]] = []
    if win.prevent_device_encryption:  # D-020
        tweak = catalogs.tweak(ENCRYPTION_TWEAK)
        if tweak is None:
            raise UnattendError(f"ajuste {ENCRYPTION_TWEAK} ausente do catálogo")
        for op in tweak.apply:
            if op.reg_set is None:
                raise UnattendError(f"{ENCRYPTION_TWEAK}: só reg_set é suportado na instalação")
            commands.append(("WinKit: não criptografar o disco", reg_add_command(op.reg_set)))
    commands.append(
        ("WinKit: preparar o agente", bootstrap_command(pendrive_id, recipe.meta.profile_id))
    )
    deploy = _component(sp, "Microsoft-Windows-Deployment", arch)
    _run_sync(deploy, "RunSynchronous", "RunSynchronousCommand", commands)


def _oobe_system(root: ET.Element, recipe: Recipe, arch: str, ui_lang: str) -> None:
    win = recipe.windows
    oobe_pass = ET.SubElement(root, _q("settings"), {"pass": "oobeSystem"})
    intl = _component(oobe_pass, "Microsoft-Windows-International-Core", arch)
    _sub(intl, "InputLocale", win.input_locale)
    _sub(intl, "SystemLocale", win.system_locale)
    _sub(intl, "UILanguage", ui_lang)
    _sub(intl, "UserLocale", win.user_locale)

    shell = _component(oobe_pass, "Microsoft-Windows-Shell-Setup", arch)
    account = win.account
    if account.auto_logon:
        al = _sub(shell, "AutoLogon")
        _sub(al, "Enabled", "true")
        _sub(al, "LogonCount", "1")
        _password(al, account)
        _sub(al, "Username", account.username)
    flc = _sub(shell, "FirstLogonCommands")
    sc = ET.SubElement(flc, _q("SynchronousCommand"), {f"{{{WCM}}}action": "add"})
    _sub(sc, "CommandLine", first_logon_command())
    _sub(sc, "Description", "WinKit: iniciar a Fase 2")
    _sub(sc, "Order", "1")
    _sub(sc, "RequiresUserInput", "false")
    oobe = _sub(shell, "OOBE")
    for flag in (
        "HideEULAPage",
        "HideLocalAccountScreen",
        "HideOEMRegistrationScreen",
        "HideOnlineAccountScreens",
        "HideWirelessSetupInOOBE",
    ):
        _sub(oobe, flag, "true")
    _sub(oobe, "ProtectYourPC", "3")
    _sub(shell, "TimeZone", win.time_zone)
    accounts = _sub(_sub(shell, "UserAccounts"), "LocalAccounts")
    acc = ET.SubElement(accounts, _q("LocalAccount"), {f"{{{WCM}}}action": "add"})
    _sub(acc, "Description", t("unattend.account_description"))
    _sub(acc, "DisplayName", account.display_name or account.username)
    _sub(acc, "Group", "Administrators")
    _sub(acc, "Name", account.username)
    _password(acc, account)


def check_safety(xml: bytes) -> None:
    """Defesa em profundidade: recusa XML com qualquer elemento de disco (R-18)."""
    try:
        root = ET.fromstring(xml)  # noqa: S314 — XML gerado por nós mesmos
    except ET.ParseError as exc:
        raise UnattendError(f"XML gerado é inválido: {exc}") from exc
    for el in root.iter():
        local = el.tag.rsplit("}", 1)[-1]
        if local in FORBIDDEN_ELEMENTS:
            raise UnattendError(f"elemento proibido no XML: {local} (R-18)")
