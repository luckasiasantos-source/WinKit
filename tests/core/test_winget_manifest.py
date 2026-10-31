from __future__ import annotations

from pathlib import Path

import pytest

from winkit.core.errors import WinKitError
from winkit.core.winget_manifest import parse_download_dir, split_args


@pytest.mark.parametrize(
    ("text", "args"),
    [
        ("/S", ["/S"]),
        ("/VERYSILENT /NORESTART", ["/VERYSILENT", "/NORESTART"]),
        ('/v"/qn ALLUSERS=1" /s', ['/v"/qn ALLUSERS=1"', "/s"]),
        ("  ", []),
        ('INSTALLDIR="C:\\Program Files\\X" /q', ['INSTALLDIR="C:\\Program Files\\X"', "/q"]),
    ],
)
def test_split_args(text: str, args: list[str]) -> None:
    assert split_args(text) == args


def write(folder: Path, yaml_text: str, exe: str = "setup.exe") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / exe).write_bytes(b"MZ" + b"x" * 100)
    (folder / "m.yaml").write_text(yaml_text, encoding="utf-8")
    return folder


def test_root_level_manifest(tmp_path: Path) -> None:
    d = write(
        tmp_path,
        "PackageIdentifier: A.B\nPackageVersion: 1.2\nInstallerType: nullsoft\n"
        "Scope: machine\nInstallerSwitches:\n  Silent: /S\n  Custom: /D=x\n",
    )
    pkg = parse_download_dir(d)
    assert (pkg.package_id, pkg.version, pkg.installer_type, pkg.scope) == (
        "A.B",
        "1.2",
        "nsis",
        "machine",
    )
    assert pkg.silent_args == ("/S", "/D=x")
    assert pkg.installer.name == "setup.exe"


def test_installers_list_manifest(tmp_path: Path) -> None:
    d = write(
        tmp_path,
        "PackageIdentifier: A.B\nPackageVersion: 2\nInstallers:\n"
        "  - InstallerType: wix\n    Scope: user\n",
    )
    pkg = parse_download_dir(d)
    assert pkg.installer_type == "msi" and pkg.scope == "user" and pkg.silent_args == ()


def test_unsupported_types(tmp_path: Path) -> None:
    pkg = parse_download_dir(write(tmp_path, "PackageIdentifier: A\nInstallerType: zip\n"))
    assert pkg.installer_type is None and pkg.raw_type == "zip"


def test_errors(tmp_path: Path) -> None:
    with pytest.raises(WinKitError, match="manifesto"):
        parse_download_dir(tmp_path)
    (tmp_path / "m.yaml").write_text("- lista\n", encoding="utf-8")
    with pytest.raises(WinKitError, match="inválido"):
        parse_download_dir(tmp_path)
    (tmp_path / "m.yaml").write_text("PackageIdentifier: A\n", encoding="utf-8")
    with pytest.raises(WinKitError, match="instalador"):
        parse_download_dir(tmp_path)
