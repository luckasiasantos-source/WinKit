from __future__ import annotations

import json

import pytest

from winkit.core.errors import VentoyConfigError
from winkit.core.ventoy.config import AutoInstallEntry, merge_auto_install, winkit_entries
from winkit.core.ventoy.detect import PartitionRow, find_ventoy_targets
from winkit.platform.fakes.disks import ventoy_rows

T1 = "/ventoy/script/winkit-padrao-pt-BR-amd64.xml"
T2 = "/ventoy/script/winkit-padrao-en-US-amd64.xml"


def merge(text: str | None, entries: list[AutoInstallEntry], profile: str = "padrao") -> dict:
    return json.loads(merge_auto_install(text, entries, autosel=1, timeout=10, profile_id=profile))


def test_detects_ventoy_disk() -> None:
    targets = find_ventoy_targets(ventoy_rows("F", "exFAT"))
    assert len(targets) == 1
    t = targets[0]
    assert (t.data_letter, t.file_system, t.root) == ("F:", "exFAT", "F:\\")
    assert not t.is_fat32


def test_fat32_and_no_letter() -> None:
    rows = ventoy_rows("G", "FAT32")
    assert find_ventoy_targets(rows)[0].is_fat32
    no_letter = [PartitionRow(**{**r.__dict__, "drive_letter": None}) for r in rows]
    assert find_ventoy_targets(no_letter) == []


def test_non_ventoy_disks_ignored() -> None:
    rows = [r for r in ventoy_rows() if r.label != "VTOYEFI"]
    assert find_ventoy_targets(rows) == []


def test_two_ventoy_disks() -> None:
    rows = ventoy_rows("E") + [
        PartitionRow(
            **{**r.__dict__, "disk_number": 3, "drive_letter": "H" if r.drive_letter else None}
        )
        for r in ventoy_rows()
        if r.disk_number == 2
    ]
    assert [t.data_letter for t in find_ventoy_targets(rows)] == ["E:", "H:"]


def test_merge_into_empty() -> None:
    data = merge(None, [AutoInstallEntry("/Win11.iso", T1)])
    assert data == {
        "auto_install": [{"image": "/Win11.iso", "template": [T1], "autosel": 1, "timeout": 10}]
    }


def test_merge_preserves_other_plugins_and_third_party_entries() -> None:
    existing = {
        "control": [{"VTOY_DEFAULT_MENU_MODE": "0"}],
        "theme": {"file": "/ventoy/theme/x.txt"},
        "auto_install": [
            {"image": "/Ubuntu.iso", "template": "/ventoy/script/ubuntu.cfg"},
        ],
    }
    data = merge(json.dumps(existing), [AutoInstallEntry("/Win11.iso", T1)])
    assert data["control"] == existing["control"]
    assert data["theme"] == existing["theme"]
    assert data["auto_install"][0] == existing["auto_install"][0]
    assert data["auto_install"][1]["image"] == "/Win11.iso"


def test_merge_appends_to_third_party_entry_for_same_iso() -> None:
    existing = {
        "auto_install": [
            {"image": "/Win11.iso", "template": "/ventoy/script/meu.xml", "timeout": 30}
        ]
    }
    data = merge(json.dumps(existing), [AutoInstallEntry("/Win11.iso", T1)])
    entry = data["auto_install"][0]
    assert entry["template"] == ["/ventoy/script/meu.xml", T1]
    assert entry["timeout"] == 30  # configuração do usuário mantida


def test_merge_is_idempotent_and_updates_in_place() -> None:
    first = merge_auto_install(
        None, [AutoInstallEntry("/Win11.iso", T1)], autosel=1, timeout=10, profile_id="padrao"
    )
    again = merge_auto_install(
        first, [AutoInstallEntry("/Win11.iso", T2)], autosel=1, timeout=5, profile_id="padrao"
    )
    entry = json.loads(again)["auto_install"][0]
    assert entry["template"] == [T2] and entry["timeout"] == 5
    assert (
        merge_auto_install(
            again, [AutoInstallEntry("/Win11.iso", T2)], autosel=1, timeout=5, profile_id="padrao"
        )
        == again
    )


def test_merge_removes_stale_entries_of_this_profile_only() -> None:
    other = "/ventoy/script/winkit-notebook-pt-BR-amd64.xml"
    existing = {
        "auto_install": [
            {"image": "/Velha.iso", "template": [T1]},
            {"image": "/Velha2.iso", "template": [T1, other]},
            {"image": "/Outro.iso", "template": [other]},
        ]
    }
    data = merge(json.dumps(existing), [])
    assert data["auto_install"] == [
        {"image": "/Velha2.iso", "template": other},
        {"image": "/Outro.iso", "template": [other]},
    ]


def test_merge_keeps_other_profile_templates_on_same_iso() -> None:
    other = "/ventoy/script/winkit-notebook-pt-BR-amd64.xml"
    existing = {"auto_install": [{"image": "/Win11.iso", "template": [other]}]}
    data = merge(json.dumps(existing), [AutoInstallEntry("/Win11.iso", T1)])
    assert data["auto_install"][0]["template"] == [T1, other]


def test_empty_auto_install_is_removed() -> None:
    data = merge(json.dumps({"auto_install": [{"image": "/x.iso", "template": [T1]}]}), [])
    assert "auto_install" not in data


@pytest.mark.parametrize("bad", ["{quebrado", "[]", '{"auto_install": {}}'])
def test_invalid_existing_config_raises(bad: str) -> None:
    with pytest.raises(VentoyConfigError):
        merge_auto_install(bad, [], autosel=1, timeout=1, profile_id="padrao")


def test_non_dict_items_are_preserved() -> None:
    data = merge(json.dumps({"auto_install": ["estranho"]}), [AutoInstallEntry("/a.iso", T1)])
    assert data["auto_install"][0] == "estranho"


def test_winkit_entries() -> None:
    text = json.dumps(
        {
            "auto_install": [
                {"image": "/a.iso", "template": [T1, "/ventoy/script/meu.xml"]},
                {"image": "/b.iso", "template": "/ventoy/script/x.xml"},
                {"image": 3},
            ]
        }
    )
    assert winkit_entries(text) == [AutoInstallEntry("/a.iso", T1)]
    assert winkit_entries(None) == []
