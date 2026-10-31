from __future__ import annotations

from pathlib import Path

import pytest

from winkit.platform.disks import WindowsDiskInspector, iso_from_json, partition_from_json
from winkit.platform.fakes.powershell import FakePowerShell
from winkit.platform.powershell import PowerShell
from winkit.platform.runner import SubprocessRunner

PARTITION = {
    "DiskNumber": 2,
    "DiskName": "SanDisk",
    "BusType": "USB",
    "PartitionNumber": 1,
    "Size": 100,
    "DriveLetter": "E",
    "Label": "Ventoy",
    "FileSystem": "exFAT",
    "SizeRemaining": 40,
}
ISO = {
    "Windows": True,
    "Version": "10.0.26100.1742",
    "Architecture": 9,
    "Languages": ["en-US", "pt-BR (Padrão)"],
    "DefaultLanguageIndex": 1,
    "Editions": [{"Index": 1, "Name": "Windows 11 Home"}, {"Index": 6, "Name": "Windows 11 Pro"}],
}


def test_partition_from_json() -> None:
    row = partition_from_json(PARTITION)
    assert (row.drive_letter, row.file_system, row.size_remaining) == ("E", "exFAT", 40)
    empty = partition_from_json({**PARTITION, "DriveLetter": "", "Label": None})
    assert empty.drive_letter is None and empty.label is None


def test_iso_from_json() -> None:
    info = iso_from_json(ISO, image="/w.iso", size=10, mtime_ns=2)
    assert info.is_windows and info.os_major == 11 and info.build == 26100
    assert info.architecture == "amd64"
    assert info.languages == ("en-US", "pt-BR") and info.default_language == "pt-BR"
    assert [e.index for e in info.editions] == [1, 6]
    assert info.name == "w.iso"


def test_iso_from_json_edge_cases() -> None:
    assert not iso_from_json({"Windows": False}, image="/x.iso", size=1, mtime_ns=1).is_windows
    odd = iso_from_json(
        {**ISO, "Architecture": 77, "DefaultLanguageIndex": 9}, image="/w.iso", size=1, mtime_ns=1
    )
    assert odd.architecture == "unknown" and odd.default_language == "en-US"


def test_inspector_uses_powershell(tmp_path: Path) -> None:
    iso = tmp_path / "w.iso"
    iso.write_bytes(b"x")
    ps = FakePowerShell().when("Get-Disk", [PARTITION]).when("Mount-DiskImage", [ISO])
    insp = WindowsDiskInspector(ps)  # type: ignore[arg-type]
    assert insp.list_partitions()[0].drive_letter == "E"
    info = insp.read_iso(iso, "/w.iso")
    assert info.build == 26100 and info.size == 1
    assert ps.calls[1].params == {"Path": str(iso)}
    assert "Dismount-DiskImage" in ps.calls[1].body  # sempre desmonta (R-17)
    empty = WindowsDiskInspector(FakePowerShell())  # type: ignore[arg-type]
    assert not empty.read_iso(iso, "/w.iso").is_windows


@pytest.mark.windows
@pytest.mark.admin
def test_real_list_partitions() -> None:
    rows = WindowsDiskInspector(PowerShell(SubprocessRunner())).list_partitions()
    assert rows, "o sistema deveria ter ao menos um disco"
    assert any(r.drive_letter == "C" for r in rows)
