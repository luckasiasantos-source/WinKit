from __future__ import annotations

from pathlib import Path

from tests.factories import recipe
from winkit.collector.drivers import export_drivers, list_candidates
from winkit.core import layout
from winkit.core.catalog.loader import default_catalogs
from winkit.platform.fakes.drivers import FakeDriverManager

CAT = default_catalogs()


def test_candidates_sorted_and_classified() -> None:
    cands = list_candidates(FakeDriverManager(), CAT)
    assert [c.driver.class_name for c in cands] == ["Net", "System", "Display", "Printer"]
    rec = {c.driver.class_name: c.recommended for c in cands}
    assert rec == {"Net": True, "System": True, "Display": True, "Printer": False}
    net = cands[0]
    assert net.item_id == "net-realtek-oem12"
    assert net.payload_path == "Drivers/net/realtek-oem12-10-68-815-2024"


def test_export_adds_to_recipe_and_is_idempotent(tmp_path: Path) -> None:
    mgr = FakeDriverManager()
    r = recipe()
    cands = [c for c in list_candidates(mgr, CAT) if c.recommended]
    added = export_drivers(mgr, cands, root=tmp_path, recipe=r)
    assert len(added) == 3 and len(r.drivers) == 3
    net = r.drivers[0]
    assert (net.class_name, net.priority, net.original_inf) == ("Net", 0, "rt25cx21x64.inf")
    assert (layout.payload(tmp_path, net.path) / "rt25cx21x64.inf").is_file()
    # segunda vez: não duplica nem reexporta
    (layout.payload(tmp_path, net.path) / "marca.txt").write_text("x")
    export_drivers(mgr, cands, root=tmp_path, recipe=r)
    assert len(r.drivers) == 3
    assert (layout.payload(tmp_path, net.path) / "marca.txt").exists()


def test_unknown_class_gets_defaults() -> None:
    from winkit.platform.drivers import InstalledDriver

    mgr = FakeDriverManager(
        drivers=[InstalledDriver("oem1.inf", "x.inf", "Estranha", "Acme", "1", None, False)]
    )
    c = list_candidates(mgr, CAT)[0]
    assert (c.label, c.priority, c.recommended) == ("Estranha", 5, False)
