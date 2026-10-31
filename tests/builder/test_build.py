from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.factories import FIXED_NOW
from winkit import __version__
from winkit.builder import target as targets
from winkit.builder.build import BuildOptions, build, load_profile_recipe, save_profile_recipe
from winkit.builder.isos import find_iso_files, scan_isos
from winkit.builder.validate import validate_pendrive
from winkit.core import layout
from winkit.core.catalog.loader import default_catalogs
from winkit.core.errors import PendriveError, RecipeError, RecipeValidationError, VentoyConfigError
from winkit.platform.fakes.disks import FakeDiskInspector, ventoy_rows, windows_iso

CAT = default_catalogs()


def run(target: targets.Target, inspector: FakeDiskInspector, **kw: object):
    return build(target, inspector, CAT, BuildOptions(**kw), now=FIXED_NOW)  # type: ignore[arg-type]


def ventoy_json(root: Path) -> dict:
    return json.loads((root / layout.VENTOY_JSON).read_text(encoding="utf-8"))


def test_full_xml_build(target: targets.Target, inspector: FakeDiskInspector) -> None:
    report = run(target, inspector)
    root = target.root
    assert [i.image for i in report.isos] == ["/Windows11.iso"]
    assert (
        "/linux/ubuntu.iso",
        "Ignorada (não parece uma ISO do Windows): ubuntu.iso",
    ) in report.skipped
    xml = root / "ventoy" / "script" / "winkit-padrao-pt-BR-amd64.xml"
    assert xml.is_file()
    assert report.pendrive_id.encode() in xml.read_bytes()
    entries = ventoy_json(root)["auto_install"]
    assert entries == [
        {
            "image": "/Windows11.iso",
            "template": ["/ventoy/script/winkit-padrao-pt-BR-amd64.xml"],
            "autosel": 1,
            "timeout": 15,
        }
    ]
    assert (root / layout.BOOTSTRAP).read_text(encoding="utf-8-sig").startswith("# WinKit")
    assert (root / layout.AGENT_VERSION).read_text().strip() == __version__
    assert not report.agent_copied


def test_iso_file_was_never_modified(target: targets.Target, inspector: FakeDiskInspector) -> None:
    iso = target.root / "Windows11.iso"
    before = (iso.read_bytes(), iso.stat().st_mtime_ns)
    run(target, inspector)
    assert (iso.read_bytes(), iso.stat().st_mtime_ns) == before  # D-002


def test_only_allowed_paths_are_written(
    target: targets.Target, inspector: FakeDiskInspector
) -> None:  # R-19
    before = set(target.root.rglob("*"))
    run(target, inspector)
    created = {p.relative_to(target.root).as_posix() for p in target.root.rglob("*")} - {
        p.relative_to(target.root).as_posix() for p in before
    }
    for rel in created:
        assert rel.startswith(("WinKit", "ventoy/ventoy.json", "ventoy/script")) or rel in (
            "ventoy",
            "ventoy/script",
        ), rel
    scripts = [p.name for p in (target.root / "ventoy" / "script").iterdir()]
    assert all(n.startswith("winkit-") for n in scripts)


def test_silent_mode_uses_short_timeout(
    target: targets.Target, inspector: FakeDiskInspector
) -> None:
    r = load_profile_recipe(target.root, "padrao")
    r.execution.mode = "silent"
    save_profile_recipe(target.root, r)
    run(target, inspector)
    assert ventoy_json(target.root)["auto_install"][0]["timeout"] == 5


def test_rebuild_is_idempotent(target: targets.Target, inspector: FakeDiskInspector) -> None:
    run(target, inspector)
    snapshot = {p: p.read_bytes() for p in target.root.rglob("*") if p.is_file()}
    run(target, inspector)
    assert {p: p.read_bytes() for p in target.root.rglob("*") if p.is_file()} == snapshot


def test_existing_ventoy_json_is_preserved_and_backed_up(
    target: targets.Target, inspector: FakeDiskInspector
) -> None:
    vj = target.root / layout.VENTOY_JSON
    vj.parent.mkdir(parents=True, exist_ok=True)
    original = {"control": [{"VTOY_DEFAULT_SEARCH_ROOT": "/ISO"}]}
    vj.write_text(json.dumps(original), encoding="utf-8")
    run(target, inspector)
    data = ventoy_json(target.root)
    assert data["control"] == original["control"]
    backup = target.root / layout.VENTOY_BACKUP
    assert json.loads(backup.read_text(encoding="utf-8")) == original
    run(target, inspector)  # o backup original nunca é sobrescrito
    assert json.loads(backup.read_text(encoding="utf-8")) == original


def test_invalid_ventoy_json_aborts_without_changes(
    target: targets.Target, inspector: FakeDiskInspector
) -> None:
    vj = target.root / layout.VENTOY_JSON
    vj.parent.mkdir(parents=True, exist_ok=True)
    vj.write_text("{ quebrado", encoding="utf-8")
    with pytest.raises(VentoyConfigError):
        run(target, inspector)
    assert vj.read_text(encoding="utf-8") == "{ quebrado"
    assert not (target.root / layout.VENTOY_BACKUP).exists()


def test_removed_iso_removes_template_and_entry(
    target: targets.Target, inspector: FakeDiskInspector
) -> None:
    run(target, inspector)
    (target.root / "Windows11.iso").unlink()
    (target.root / "Win11-en.iso").write_bytes(b"en")
    inspector.isos["Win11-en.iso"] = windows_iso(lang="en-US")
    report = run(target, inspector)
    assert report.removed_templates == ["winkit-padrao-pt-BR-amd64.xml"]
    entries = ventoy_json(target.root)["auto_install"]
    assert [e["image"] for e in entries] == ["/Win11-en.iso"]
    assert entries[0]["template"] == ["/ventoy/script/winkit-padrao-en-US-amd64.xml"]


def test_arch_and_os_filtering(target: targets.Target, inspector: FakeDiskInspector) -> None:
    (target.root / "arm.iso").write_bytes(b"a")
    (target.root / "win10.iso").write_bytes(b"10")
    inspector.isos["arm.iso"] = windows_iso(arch="arm64")
    inspector.isos["win10.iso"] = windows_iso(build=19045)
    report = run(target, inspector)
    assert [i.image for i in report.isos] == ["/Windows11.iso"]
    reasons = dict(report.skipped)
    assert "arquitetura" in reasons["/arm.iso"]
    assert "Windows 10" in reasons["/win10.iso"]
    assert any("arm64" in w for w in report.warnings)


def test_win10_iso_when_recipe_targets_both(
    target: targets.Target, inspector: FakeDiskInspector
) -> None:
    (target.root / "Windows11.iso").unlink()
    (target.root / "win10.iso").write_bytes(b"10")
    inspector.isos["win10.iso"] = windows_iso(build=19045)
    r = load_profile_recipe(target.root, "padrao")
    r.windows.target_os = [10, 11]
    save_profile_recipe(target.root, r)
    run(target, inspector)
    xml = (target.root / "ventoy" / "script" / "winkit-padrao-pt-BR-amd64.xml").read_text("utf-8")
    assert "BypassTPMCheck" not in xml


def test_no_isos_warns(target: targets.Target) -> None:
    report = run(target, FakeDiskInspector())
    assert any("Nenhuma ISO" in w for w in report.warnings)
    assert "auto_install" not in ventoy_json(target.root)


def test_recipe_errors(target: targets.Target, inspector: FakeDiskInspector) -> None:
    (target.root / layout.recipe_file("padrao")).unlink()
    with pytest.raises(RecipeError, match="receita nova"):
        run(target, inspector)


def test_invalid_recipe_blocks_build(target: targets.Target, inspector: FakeDiskInspector) -> None:
    r = load_profile_recipe(target.root, "padrao")
    r.windows.computer_name = "nome inválido"
    save_profile_recipe(target.root, r)
    with pytest.raises(RecipeValidationError):
        run(target, inspector)
    assert not (target.root / layout.VENTOY_JSON).exists()


def test_recipe_from_other_pendrive_is_realigned(
    target: targets.Target, inspector: FakeDiskInspector
) -> None:
    r = load_profile_recipe(target.root, "padrao")
    r.meta.pendrive_id = "99999999-0000-0000-0000-000000000000"
    save_profile_recipe(target.root, r)
    report = run(target, inspector)
    assert any("outro pendrive" in w for w in report.warnings)
    assert load_profile_recipe(target.root, "padrao").meta.pendrive_id == report.pendrive_id


def test_agent_copy(target: targets.Target, inspector: FakeDiskInspector, tmp_path: Path) -> None:
    agent = tmp_path / "winkit-agent"
    (agent / "_internal").mkdir(parents=True)
    (agent / "winkit-agent.exe").write_bytes(b"MZ")
    (agent / "_internal" / "lib.dll").write_bytes(b"x")
    report = run(target, inspector, agent_source=agent)
    assert report.agent_copied
    assert (target.root / layout.AGENT_BIN_DIR / "_internal" / "lib.dll").is_file()
    with pytest.raises(PendriveError):
        run(target, inspector, agent_source=tmp_path / "vazio")


def test_iso_cache(target: targets.Target, inspector: FakeDiskInspector, tmp_path: Path) -> None:
    cache = tmp_path / "cache.json"
    scan_isos(target.root, inspector, cache)
    scan_isos(target.root, inspector, cache)
    assert inspector.reads.count("/Windows11.iso") == 1
    (target.root / "Windows11.iso").write_bytes(b"mudou de tamanho")
    scan_isos(target.root, inspector, cache)
    assert inspector.reads.count("/Windows11.iso") == 2
    cache.write_text("lixo", encoding="utf-8")
    infos, _ = scan_isos(target.root, inspector, cache)
    assert infos


def test_iso_read_errors_are_collected(target: targets.Target) -> None:
    class Broken(FakeDiskInspector):
        def read_iso(self, iso_path: Path, image: str):
            raise OSError("falha ao montar")

    infos, errors = scan_isos(target.root, Broken())
    assert infos == [] and len(errors) == 2


def test_find_iso_files_skips_winkit_and_ventoy(pendrive: Path) -> None:
    (pendrive / "WinKit" / "x.iso").write_bytes(b"")
    (pendrive / "ventoy").mkdir()
    (pendrive / "ventoy" / "y.ISO").write_bytes(b"")
    (pendrive / "Z.ISO").write_bytes(b"")
    names = [p.name for p in find_iso_files(pendrive)]
    assert names == ["ubuntu.iso", "Windows11.iso", "Z.ISO"]


# ------------------------------------------------------------------ alvo
def test_resolve_target() -> None:
    insp = FakeDiskInspector()
    assert targets.resolve_target(insp, None).root == Path("E:\\")
    assert targets.resolve_target(insp, "e").description.startswith("E:")
    with pytest.raises(PendriveError):
        targets.resolve_target(insp, "Z:")
    with pytest.raises(PendriveError, match="Nenhum"):
        targets.resolve_target(FakeDiskInspector(rows=[]), None)
    many = FakeDiskInspector(
        rows=ventoy_rows("E")
        + [
            r.__class__(
                **{**r.__dict__, "disk_number": 5, "drive_letter": "K" if r.drive_letter else None}
            )
            for r in ventoy_rows()
            if r.disk_number == 2
        ]
    )
    with pytest.raises(PendriveError, match="Mais de um"):
        targets.resolve_target(many, None)


def test_target_fat32_flag(tmp_path: Path) -> None:
    assert targets.from_folder(tmp_path, "FAT32").is_fat32
    assert not targets.from_folder(tmp_path).is_fat32


# ------------------------------------------------------------------ validação do pendrive
def test_validate_after_build(target: targets.Target, inspector: FakeDiskInspector) -> None:
    run(target, inspector)
    rep = validate_pendrive(target.root, CAT)
    assert rep.ok, rep.problems
    assert any("executável do Agente" in w for w in rep.warnings)


def test_validate_detects_problems(target: targets.Target, inspector: FakeDiskInspector) -> None:
    rep = validate_pendrive(target.root, CAT)
    assert any("ventoy.json" in p for p in rep.problems)
    run(target, inspector)
    xml = target.root / "ventoy" / "script" / "winkit-padrao-pt-BR-amd64.xml"
    xml.write_bytes(
        xml.read_bytes().replace(
            b'<settings pass="windowsPE">', b'<settings pass="windowsPE"><DiskConfiguration/>'
        )
    )
    (target.root / layout.BOOTSTRAP).unlink()
    (target.root / layout.AGENT_VERSION).write_text("0.0.1")
    rep = validate_pendrive(target.root, CAT)
    assert any("R-18" in p for p in rep.problems)
    assert any("bootstrap" in p for p in rep.problems)
    assert any("0.0.1" in w for w in rep.warnings)
    xml.unlink()
    assert any("modelo ausente" in p for p in validate_pendrive(target.root, CAT).problems)


def test_validate_without_marker(tmp_path: Path) -> None:
    assert "marker" in validate_pendrive(tmp_path, CAT).problems[0]
    (tmp_path / "WinKit").mkdir()
    (tmp_path / layout.MARKER).write_text("lixo")
    assert "corrompido" in validate_pendrive(tmp_path, CAT).problems[0]


def test_validate_missing_payload_and_fat32(
    target: targets.Target, inspector: FakeDiskInspector
) -> None:
    from tests.factories import app, backup, driver

    r = load_profile_recipe(target.root, "padrao")
    r.apps = [app("x")]
    r.backups = [backup("b")]
    r.drivers = [driver("d")]
    save_profile_recipe(target.root, r)
    run(target, inspector)
    rep = validate_pendrive(target.root, CAT)
    assert {p.split(":")[0] for p in rep.problems} >= {"app x", "backup b", "driver d"}


def test_validate_checks_manifest(target: targets.Target, inspector: FakeDiskInspector) -> None:
    from winkit.core.fsutil import atomic_write_text
    from winkit.core.manifest.manifest import dump_manifest, scan

    run(target, inspector)
    atomic_write_text(
        target.root / layout.MANIFEST, dump_manifest(scan(target.root, layout.MANIFEST_SUBDIRS))
    )
    assert validate_pendrive(target.root, CAT).ok
    (target.root / layout.BOOTSTRAP).write_text("adulterado", encoding="utf-8")
    assert any("alterado" in p for p in validate_pendrive(target.root, CAT).problems)
