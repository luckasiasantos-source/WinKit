from __future__ import annotations

from pathlib import Path

import pytest

from tests.factories import FIXED_NOW
from winkit.builder import target as targets
from winkit.builder.build import ensure_marker, save_profile_recipe
from winkit.core.recipe.io import new_recipe
from winkit.platform.fakes.disks import FakeDiskInspector, windows_iso


@pytest.fixture
def pendrive(tmp_path: Path) -> Path:
    root = tmp_path / "pendrive"
    root.mkdir()
    (root / "Windows11.iso").write_bytes(b"iso11")
    (root / "linux").mkdir()
    (root / "linux" / "ubuntu.iso").write_bytes(b"ubuntu")
    marker = ensure_marker(root, FIXED_NOW)
    save_profile_recipe(
        root, new_recipe(pendrive_id=marker.pendrive_id, username="Samuel", now=FIXED_NOW)
    )
    return root


@pytest.fixture
def inspector() -> FakeDiskInspector:
    return FakeDiskInspector(isos={"Windows11.iso": windows_iso()})


@pytest.fixture
def target(pendrive: Path) -> targets.Target:
    return targets.from_folder(pendrive)
