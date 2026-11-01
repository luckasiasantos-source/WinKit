"""Windows 7 e 8.1 em modo limitado (V3-14, D-050, R-63)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tests.factories import app, recipe
from winkit.core import compat, legacy_agent
from winkit.core.catalog.loader import default_catalogs
from winkit.core.catalog.models import DownloadSource
from winkit.core.errors import WinKitError
from winkit.core.recipe.models import BackupItem, InstallerSpec, WifiNetwork
from winkit.core.unattend.generator import UnattendTarget, generate_unattend
from winkit.platform.external_tools import fetch_direct

CAT = default_catalogs()


def _xml(version: str, arch: str = "amd64") -> str:
    r = recipe()
    r.target_windows.version = version  # type: ignore[assignment]
    r.windows.architecture = arch  # type: ignore[assignment]
    return generate_unattend(
        r, CAT, UnattendTarget("pt-BR", arch, None), pendrive_id="x" * 36
    ).decode()


def test_unattend_for_windows_7_and_81() -> None:
    win7 = _xml("7", "x86")
    for absent in (
        "HideOnlineAccountScreens",
        "HideLocalAccountScreen",
        "<Key>",
        "LabConfig",
        "bootstrap",
    ):
        assert absent not in win7, absent
    assert "winkit-legado.ps1" in win7 and 'processorArchitecture="x86"' in win7
    assert "HideEULAPage" in win7 and "<LocalAccount" in win7
    win81 = _xml("8.1")
    assert "HideOnlineAccountScreens" in win81 and "<Key>" not in win81
    assert "winkit-legado.ps1" in win81
    win11 = _xml("11")
    assert "<Key>" in win11 and "winkit-legado.ps1" not in win11


def test_legacy_script_adds_and_never_replaces() -> None:
    r = recipe()
    r.target_windows.version = "7"
    a = app("sevenzip", name="7-Zip")
    a.installer = InstallerSpec(path="Apps/sevenzip/7z.exe", type="nsis", args=["/S"])
    r.apps = [a]
    r.backups = [
        BackupItem(
            id="b",
            name="Notepad++",
            template=r"{APPDATA}\Notepad++",
            data_path="Perfis/padrao/Backups/b/dados",
        ),
        BackupItem(
            id="c", name="Tema", template=r"{LOCALLOW}\x", data_path="Perfis/padrao/Backups/c/dados"
        ),
    ]
    r.wifi.networks = [WifiNetwork(id="casa", ssid="Casa", file="Perfis/padrao/Wifi/casa.xml")]
    r.power.scheme = "high_performance"
    script = legacy_agent.generate(r, CAT)
    assert "Apps\\sevenzip\\7z.exe" in script and "'/S'" in script
    assert "robocopy.exe" in script and "/XC /XN /XO" in script and "/MIR" not in script
    assert (
        "$env:APPDATA" in script and "pulado" in script
    )  # {LOCALLOW} fica de fora do agente legado
    assert "netsh.exe wlan add profile" in script and "powercfg.exe /setactive SCHEME_MIN" in script
    assert "legado.feito" in script  # roda uma vez só


def test_compat_and_missing_drivers() -> None:
    assert compat.supported("apps", "7") and not compat.supported("bloat", "7")
    assert compat.supported("bloat", "11")
    ids = [r"PCI\VEN_8086&DEV_A12F&CC_0C0330", r"PCI\VEN_144D&DEV_A808&CC_010802"]
    assert compat.missing_native_drivers("7", ids) == ["nvme", "usb3"]
    assert compat.missing_native_drivers("8.1", ids) == []


def test_fetch_direct_checks_sha1(tmp_path: Path) -> None:
    data = b"msu"
    good = DownloadSource(
        id="kb",
        name="KB",
        url="https://x/kb.msu",
        sha1=hashlib.sha1(data).hexdigest(),  # noqa: S324
    )

    def downloader(url: str, dest: Path, **_: object) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest

    assert fetch_direct(good, tmp_path, downloader=downloader).read_bytes() == data
    bad = good.model_copy(update={"sha1": "0" * 40})
    with pytest.raises(WinKitError):
        fetch_direct(bad, tmp_path / "b", downloader=downloader)
    assert not (tmp_path / "b" / "kb.msu").exists()
    assert {d.id for d in CAT.downloads} >= {"win7_kb3125574_x64", "win7_kb3020369_x86"}
