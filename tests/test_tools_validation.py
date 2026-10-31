"""Tests for S-criteria validation guards in tools/check_data.py and tools/check_blend.py.

Guards tested (preventing silent false-positive acceptance of broken data/scenes):
1. `check_data.py`: accepts valid probe manifest & layout; rejects duplicate `asset_id` across manifests,
   dangling `asset_id` / `parent_part` references, falsified unmeasured metrics (`measured: false` with numbers),
   and non-existent referenced files on disk.
2. `check_blend.py`: accepts valid `blender/probe/probe.blend` and orthogonal uniform transforms; rejects
   `.001` / default names, negative scale, non-uniform scale, shear matrices, and missing external image files.
"""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

from tools.check_blend import (
    check_name_conventions,
    check_transform_matrix_and_scale,
    inspect_blend_file_via_resoloop,
)
from tools.check_data import (
    PROJECT_ROOT,
    run_validation,
    validate_area_layout_data,
    validate_manifest_data,
)


def _load_probe_manifest() -> dict:
    path = PROJECT_ROOT / "modeling" / "probe" / "probe_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_probe_layout() -> dict:
    path = PROJECT_ROOT / "modeling" / "probe" / "probe_layout.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_check_data_accepts_valid_probe_and_rejects_broken_invariants(tmp_path: Path) -> None:
    # 1. Valid pass case on actual probe data
    ok, errors, counts = run_validation(root=PROJECT_ROOT, key="probe")
    assert ok is True, f"Valid probe data should pass, got: {errors}"
    assert counts["area_layouts"] == 1
    assert counts["manifests"] == 1

    base_manifest = _load_probe_manifest()
    base_layout = _load_probe_layout()

    # 2. Duplicate asset_id across manifests must be rejected
    seen_ids: dict[str, str] = {"P0_MeterRef_001": "assets/manifest/other.json"}
    dup_errors = validate_manifest_data(
        copy.deepcopy(base_manifest),
        source_label="probe_manifest.json",
        root=PROJECT_ROOT,
        seen_global_asset_ids=seen_ids,
        check_files_exist=False,
    )
    assert any("duplicate asset_id" in e for e in dup_errors)

    # 3. Dangling parent_part and dangling area_layout asset_id reference must be rejected
    bad_ref_manifest = copy.deepcopy(base_manifest)
    bad_ref_manifest["assets"][2]["parts"][1]["parent_part"] = "P0_NonExistent_Parent"
    ref_errors = validate_manifest_data(
        bad_ref_manifest,
        root=PROJECT_ROOT,
        check_files_exist=False,
    )
    assert any("missing parent_part" in e for e in ref_errors)

    bad_layout = copy.deepcopy(base_layout)
    bad_layout["placements"][0]["asset_id"] = "P0_Missing_Asset_999"
    layout_ref_errors = validate_area_layout_data(
        bad_layout,
        known_assets_by_key={"probe": {"P0_MeterRef_001", "P0_AsymSign_001", "P0_PivotGate_001"}},
    )
    assert any("not found in manifest" in e for e in layout_ref_errors)

    # 4. Unmeasured metrics with numeric values (or missing unmeasured_reason) must be rejected
    bad_metrics_manifest = copy.deepcopy(base_manifest)
    bad_metrics_manifest["assets"][0]["metrics"] = {
        "measured": False,
        "triangles": 36,  # Prohibited when measured is False
        "vertices": None,
        "materials_count": None,
        "objects_count": None,
    }
    metric_errors = validate_manifest_data(
        bad_metrics_manifest,
        root=PROJECT_ROOT,
        check_files_exist=False,
    )
    assert any("must be null when measured is false" in e for e in metric_errors)
    assert any("unmeasured_reason" in e for e in metric_errors)

    # 5. Missing referenced file on disk must be rejected when check_files_exist=True
    missing_file_manifest = copy.deepcopy(base_manifest)
    missing_file_manifest["assets"][0]["blend_file"] = "blender/probe/non_existent.blend"
    file_errors = validate_manifest_data(
        missing_file_manifest,
        root=PROJECT_ROOT,
        check_files_exist=True,
    )
    assert any("does not exist on disk" in e for e in file_errors)


def test_check_blend_transforms_and_naming_guards() -> None:
    # 1. Valid pass case
    assert check_name_conventions("P0_MeterRef_001", kind="object") == []
    identity_3x3 = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    assert check_transform_matrix_and_scale("P0_MeterRef_001", (1.0, 1.0, 1.0), identity_3x3) == []

    # 2. .001 suffix and default Blender names must be rejected
    assert any(".NNN" in e for e in check_name_conventions("P0_MeterRef_001.001", kind="object"))
    assert any("Default Blender name" in e for e in check_name_conventions("Cube", kind="object"))

    # 3. Negative scale, non-uniform scale, and shear must be rejected
    neg_errors = check_transform_matrix_and_scale(
        "P0_BadNeg_001",
        (-1.0, 1.0, 1.0),
        [[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    )
    assert any("Negative" in e for e in neg_errors)

    non_uniform_errors = check_transform_matrix_and_scale(
        "P0_BadScale_001",
        (1.0, 2.0, 1.0),
        [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 1.0]],
    )
    assert any("Non-uniform" in e for e in non_uniform_errors)

    shear_3x3 = [[1.0, 0.35, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    shear_errors = check_transform_matrix_and_scale(
        "P0_BadShear_001",
        (1.0, 1.0, 1.0),
        shear_3x3,
    )
    assert any("Shear detected" in e for e in shear_errors)


def test_check_blend_end_to_end_accepts_probe_and_rejects_broken_blend(tmp_path: Path) -> None:
    # 1. Valid probe.blend must pass
    valid_report = inspect_blend_file_via_resoloop(
        PROJECT_ROOT / "blender" / "probe" / "probe.blend",
        root=PROJECT_ROOT,
    )
    assert valid_report["ok"] is True, f"probe.blend failed inspection: {valid_report['errors']}"

    # 2. Create a broken .blend in tmp_path with missing external image, .001 object name, and negative scale
    bad_blend = tmp_path / "broken.blend"
    builder_script = tmp_path / "make_broken.py"
    builder_script.write_text(
        f"""import bpy
obj = bpy.data.objects.get("Cube")
if obj is not None:
    obj.name = "P0_BadObj_001.001"
    obj.scale = (-1.0, 2.0, 1.0)
img = bpy.data.images.new("P0_MissingTex_001", width=4, height=4)
img.source = "FILE"
img.filepath = "//does_not_exist_anywhere.png"
img.use_fake_user = True
bpy.ops.wm.save_as_mainfile(filepath={str(bad_blend)!r}, check_existing=False)
""",
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["resoloop", "blender", "run", str(builder_script), "--json"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout

    broken_report = inspect_blend_file_via_resoloop(bad_blend, root=PROJECT_ROOT)
    assert broken_report["ok"] is False
    joined_errors = "\n".join(broken_report["errors"])
    assert "Duplicate numeric suffix (.NNN)" in joined_errors
    assert "Negative or zero local scale" in joined_errors
    assert "Non-uniform local scale" in joined_errors
    assert "Missing external image file" in joined_errors
