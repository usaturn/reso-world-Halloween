"""Deterministic Blender scene builder for Area D (`D_amusement`, W05 / Issue #7)."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from typing import Any

import bpy  # type: ignore
from mathutils import Vector  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modeling.D_amusement.assets_rides import (
    build_amusement_plaza,
    build_carnival_stall,
    build_carousel,
    build_ghost_train,
    build_pumpkin_cups,
    build_ticket_booth,
    build_train_track,
)
from modeling.D_amusement.layout_data import (
    AREA_ID,
    KEY,
    build_d_amusement_area_layout_dict,
)
from modeling.D_amusement.mesh_helpers import get_d_amusement_materials
from modeling.lib.common_parts import append_common_part
from modeling.lib.render import render_review_images
from modeling.lib.scene import reset_scene, save_blend

BLEND_REL_PATH = "blender/D_amusement/D_amusement.blend"
SCRIPT_REL_PATH = "modeling/D_amusement/build.py"
AREA_LAYOUT_REL_PATH = "layout/areas/D_amusement.json"
MANIFEST_REL_PATH = "assets/manifest/D_amusement.json"
COMMON_BLEND_REL_PATH = "blender/common/common.blend"


def _deduplicate_imported_materials() -> None:
    """Remap any `.NNN` duplicate materials created during `append_common_part` to their canonical base material."""
    import re

    suffix_re = re.compile(r"^(.+)\.[0-9]{3}$")
    for mesh in bpy.data.meshes:
        for idx, mat in enumerate(mesh.materials):
            if mat is None:
                continue
            m = suffix_re.match(mat.name)
            if m:
                base_name = m.group(1)
                base_mat = bpy.data.materials.get(base_name)
                if base_mat is not None:
                    mesh.materials[idx] = base_mat
                else:
                    mat.name = base_name

    for mat in list(bpy.data.materials):
        if suffix_re.match(mat.name):
            bpy.data.materials.remove(mat, do_unlink=True)


def _ensure_common_blend_for_append() -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    """Return path to `blender/common/common.blend`, or build a temporary copy if absent in a fresh checkout."""
    common_path = PROJECT_ROOT / COMMON_BLEND_REL_PATH
    if common_path.is_file():
        return common_path, None

    from modeling.common.build import (
        build_bench,
        build_fence,
        build_garland_flag,
        build_handrail,
        build_lantern,
        build_small_pumpkin,
        build_street_lamp,
        get_common_materials,
    )

    tmp_dir = tempfile.TemporaryDirectory(prefix="d_amusement_common_")
    tmp_blend = Path(tmp_dir.name) / "common.blend"
    _scene, common_col = reset_scene("common", seed=101)
    cmats = get_common_materials()
    build_street_lamp(common_col, cmats, location=(-6.0, 0.0, 0.0))
    build_fence(common_col, cmats, location=(-3.2, 0.0, 0.0))
    build_handrail(common_col, cmats, location=(0.4, 0.0, 0.0))
    build_garland_flag(common_col, cmats, location=(4.2, 0.0, 0.0))
    build_bench(common_col, cmats, location=(-4.2, -2.5, 0.0))
    build_lantern(common_col, cmats, location=(-1.2, -2.5, 0.0))
    build_small_pumpkin(common_col, cmats, location=(1.2, -2.5, 0.0))
    save_blend(tmp_blend, pack_images=False)
    return tmp_blend, tmp_dir


def place_d_amusement_common_parts(
    collection: bpy.types.Collection,
    common_blend_path: Path,
) -> list[bpy.types.Object]:
    """Append and place `Common_Placement` instances from `common.blend`."""
    area_layout = build_d_amusement_area_layout_dict()
    placed: list[bpy.types.Object] = []
    for cp in area_layout["Common_Placement"]:
        inst_obj = append_common_part(
            common_blend_path=common_blend_path,
            source_object_name=cp["common_asset_id"],
            instance_name=cp["instance_name"],
            collection=collection,
            location=tuple(cp["position"]),
            rotation_euler_deg=tuple(cp["rotation_euler_deg"]),
        )
        placed.append(inst_obj)
    _deduplicate_imported_materials()
    return placed


def _collect_subtree(root_obj: bpy.types.Object) -> list[bpy.types.Object]:
    """Return `[root_obj, ...all descendants...]` in deterministic name order."""
    result = [root_obj]
    children = sorted(root_obj.children, key=lambda o: o.name)
    for child in children:
        result.extend(_collect_subtree(child))
    return result


def _count_mesh_stats(objs: list[bpy.types.Object]) -> tuple[int, int, list[str]]:
    tris = 0
    verts = 0
    mat_set: set[str] = set()
    for obj in objs:
        if obj.type == "MESH" and obj.data is not None:
            mesh = obj.data
            mesh.calc_loop_triangles()
            tris += len(mesh.loop_triangles)
            verts += len(mesh.vertices)
            for m in mesh.materials:
                if m is not None:
                    mat_set.add(m.name)
    return tris, verts, sorted(mat_set)


def _compute_local_bounds(objs: list[bpy.types.Object], root_origin: Vector) -> dict[str, list[float]]:
    bpy.context.view_layer.update()
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for obj in objs:
        if obj.type == "MESH":
            for corner in obj.bound_box:
                wpt = obj.matrix_world @ Vector(corner)
                rel = wpt - root_origin
                xs.append(float(rel.x))
                ys.append(float(rel.y))
                zs.append(float(rel.z))
    if not xs:
        return {"min": [-0.5, -0.5, 0.0], "max": [0.5, 0.5, 1.0]}
    return {
        "min": [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)],
        "max": [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)],
    }


def _classify_part_role(
    obj: bpy.types.Object,
    root_obj: bpy.types.Object,
    motion_roots: set[str],
    attachment_points: set[str],
) -> tuple[str, str]:
    """Return `(role, origin_policy)` for a part in an asset hierarchy."""
    if obj == root_obj:
        return "asset_root", "ground_center"
    if obj.name in motion_roots:
        return "motion_root", "hinge_pivot"
    if obj.name in attachment_points or "_Att_" in obj.name:
        return "attachment_point", "attachment_point"
    if obj.type == "MESH":
        if "Wheel" in obj.name or "M05_" in obj.name or "M06_" in obj.name:
            return "visual_root", "hinge_pivot"
        return "visual_root", "ground_center"
    return "sub_part", "local_center"


def _make_manifest_entry(
    root_obj: bpy.types.Object,
    category: str,
    motion_roots: list[str],
    attachment_points: list[str],
    is_placeholder: bool,
    future_target: str | None,
    notes: str,
) -> dict[str, Any]:
    subtree = _collect_subtree(root_obj)
    tris, verts, mat_names = _count_mesh_stats(subtree)
    bounds = _compute_local_bounds(subtree, root_obj.location)
    bmin, bmax = bounds["min"], bounds["max"]
    width = round(max(0.01, bmax[0] - bmin[0]), 4)
    depth = round(max(0.01, bmax[1] - bmin[1]), 4)
    height = round(max(0.01, bmax[2] - bmin[2]), 4)

    motion_set = set(motion_roots)
    attach_set = set(attachment_points)
    parts: list[dict[str, Any]] = []
    visual_roots: list[str] = []

    for obj in subtree:
        role, origin_pol = _classify_part_role(obj, root_obj, motion_set, attach_set)
        if obj.type == "MESH" and obj.name not in attach_set:  # W07: attachment sockets are meshes, not visuals
            visual_roots.append(obj.name)
        parts.append(
            {
                "part_id": obj.name,
                "role": role,
                "parent_part": obj.parent.name if obj.parent is not None else None,
                "origin_policy": origin_pol,
                "pivot_local": [
                    round(float(obj.location.x), 4),
                    round(float(obj.location.y), 4),
                    round(float(obj.location.z), 4),
                ],
            }
        )

    return {
        "asset_id": root_obj.name,
        "key": KEY,
        "category": category,
        "area_id": AREA_ID,
        "collection": KEY,
        "blend_file": BLEND_REL_PATH,
        "script_file": SCRIPT_REL_PATH,
        "origin_policy": "ground_center",
        "origin_world": [
            round(float(root_obj.location.x), 4),
            round(float(root_obj.location.y), 4),
            round(float(root_obj.location.z), 4),
        ],
        "dimensions_m": {"width": width, "depth": depth, "height": height},
        "bounds_local": bounds,
        "parts": parts,
        "hierarchy": {
            "asset_root": root_obj.name,
            "motion_roots": motion_roots,
            "visual_roots": visual_roots,
            "attachment_points": attachment_points,
        },
        "materials": mat_names,
        "textures": [],
        "metrics": {
            "measured": True,
            "measurement_source": "blender_scene",
            "triangles": tris,
            "vertices": verts,
            "materials_count": len(mat_names),
            "objects_count": len(subtree),
        },
        "export_result": {
            "status": "unexported",
            "bundle_dir": None,
            "apply_plan": None,
            "report_file": None,
        },
        "replacement": {
            "is_placeholder": is_placeholder,
            "modifiable": True,
            "notes": notes,
            "future_target": future_target,
        },
    }


def build_d_amusement() -> dict[str, Any]:
    """Build Area D (`D_amusement`), render review PNGs, save `D_amusement.blend`, and write JSON files."""
    no_render = "--no-render" in sys.argv
    common_blend_path, tmp_common_dir = _ensure_common_blend_for_append()
    try:
        _scene, col = reset_scene(KEY, seed=105)
        mats = get_d_amusement_materials()

        plaza_obj = build_amusement_plaza(col, mats)
        carousel_obj = build_carousel(col, mats)
        track_obj = build_train_track(col, mats)
        train_obj = build_ghost_train(col, mats)
        cups_obj = build_pumpkin_cups(col, mats)
        booth_obj = build_ticket_booth(col, mats)
        stall_obj = build_carnival_stall(col, mats)

        placed_common = place_d_amusement_common_parts(col, common_blend_path)
    finally:
        if tmp_common_dir is not None:
            tmp_common_dir.cleanup()

    assets_spec = [
        (
            plaza_obj,
            "architecture",
            [],
            [],
            False,
            None,
            "South Amusement Promenade paving, golden curbs, West Carousel court, and East Ghost Train / Pumpkin Cups court.",
        ),
        (
            carousel_obj,
            "gimmick",
            [
                "DAM_Carousel_001_TurnRoot",
                "DAM_Carousel_001_SeatRoot_001",
                "DAM_Carousel_001_SeatRoot_002",
                "DAM_Carousel_001_SeatRoot_003",
                "DAM_Carousel_001_SeatRoot_004",
            ],
            [
                "DAM_Carousel_001_Att_M05_CenterCasing",
                "DAM_Carousel_001_Att_M05_Canopy",
            ],
            True,
            "M05_CenterCasing",
            "G13/G14 Pumpkin Carousel (~10m diameter). M05 replaces DAM_Carousel_001_M05_CenterCasing (1.861x1.907x3.400m at TurnRoot+[0,0,0.19], world z=0.55m) and DAM_Carousel_001_M05_Canopy (9.314x9.512x6.387m at TurnRoot+[0,0,3.154], world z=3.514m). Base, TurnRoot, Floor, Poles, and SeatRoot_001..004 remain from W05.",
        ),
        (
            track_obj,
            "architecture",
            [],
            [],
            False,
            None,
            "G15 flat closed-loop stadium track (center (12.0, -31.5, 0.0), curve radius 4.5m, straight 4.0m, rail top z=0.14m, gauge 0.76m) with Sleepers, Rails, and LoopGuide.",
        ),
        (
            train_obj,
            "gimmick",
            [
                "DAM_GhostTrain_001_EngineRoot",
                "DAM_GhostTrain_001_CarRoot_001",
            ],
            [
                "DAM_GhostTrain_001_Att_M06_Engine",
                "DAM_GhostTrain_001_Att_CouplerRear",
                "DAM_GhostTrain_001_Att_Headlamp",
            ],
            True,
            "M06_GhostTrainEngine",
            "G15 Ghost Train 2-car consist (total length 6.00m). M06 replaces DAM_GhostTrain_001_M06_EngineShell (1.211x3.000x1.905m at EngineRoot origin [0,0,0], world [7.5,-30.5,0.14], +Y forward). EngineWheelFront/Rear (y=±0.414, z=0.21, r=0.21m) and CarRoot_001 (2.75m behind) remain from W05.",
        ),
        (
            cups_obj,
            "gimmick",
            [
                "DAM_PumpkinCups_001_TurnRoot",
                "DAM_PumpkinCups_001_CupRoot_001",
                "DAM_PumpkinCups_001_CupRoot_002",
                "DAM_PumpkinCups_001_CupRoot_003",
            ],
            [
                "DAM_PumpkinCups_001_Att_CenterTop",
            ],
            False,
            None,
            "G16 Spinning Pumpkin Cups attraction: main turntable TurnRoot (+Z 0..360 deg) and 3 counter-rotating pumpkin teacups CupRoot_001..003 at r=1.72m (+Z 0..360 deg).",
        ),
        (
            booth_obj,
            "architecture",
            [],
            [
                "DAM_TicketBooth_001_Att_Sign",
                "DAM_TicketBooth_001_Att_Lantern",
            ],
            False,
            None,
            "Whimsical pumpkin-roofed Ticket & Treat Booth facing West toward the South Promenade next to the Ghost Train boarding platform.",
        ),
        (
            stall_obj,
            "architecture",
            [],
            [
                "DAM_CarnivalStall_001_Att_Sign",
                "DAM_CarnivalStall_001_Att_Lantern",
            ],
            False,
            None,
            "Festive Pumpkin Ring-Toss & Candy Carnival Stall on the South-West court with sign and lantern attachment points.",
        ),
    ]

    blend_path = PROJECT_ROOT / BLEND_REL_PATH
    save_blend(blend_path, pack_images=True)

    area_layout_data = build_d_amusement_area_layout_dict()
    manifest_data: dict[str, Any] = {
        "schema_version": "1.0",
        "key": KEY,
        "updated_at": "2026-10-31T21:45:00Z",
        "assets": [_make_manifest_entry(*spec) for spec in assets_spec],
    }

    area_layout_path = PROJECT_ROOT / AREA_LAYOUT_REL_PATH
    manifest_path = PROJECT_ROOT / MANIFEST_REL_PATH
    area_layout_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    area_layout_path.write_text(json.dumps(area_layout_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    review_dir = PROJECT_ROOT / "review" / KEY
    views = [
        {
            "filepath": review_dir / "01_d_amusement_overview.png",
            "location": (25.0, -56.0, 19.0),
            "target": (0.0, -33.0, 2.2),
            "lens_mm": 26.0,
        },
        {
            "filepath": review_dir / "02_d_amusement_carousel_m05.png",
            "location": (-1.5, -43.5, 5.2),
            "target": (-10.5, -32.0, 3.2),
            "lens_mm": 28.0,
        },
        {
            "filepath": review_dir / "03_d_amusement_ghost_train_m06.png",
            "location": (2.2, -38.8, 4.2),
            "target": (9.5, -31.0, 1.0),
            "lens_mm": 30.0,
        },
        {
            "filepath": review_dir / "04_d_amusement_pumpkin_cups_stall.png",
            "location": (3.0, -50.5, 4.5),
            "target": (11.5, -42.5, 1.1),
            "lens_mm": 30.0,
        },
    ]
    if not no_render:
        render_review_images(views=views, width=1280, height=720, samples=32)

    summary = {
        "key": KEY,
        "blend_file": BLEND_REL_PATH,
        "objects_count": len(bpy.data.objects),
        "d_amusement_assets_count": len(assets_spec),
        "common_instances_count": len(placed_common),
        "meshes_count": len(bpy.data.meshes),
        "materials_count": len(bpy.data.materials),
        "review_images": [str(v["filepath"].relative_to(PROJECT_ROOT)) for v in views],
    }
    print("D_AMUSEMENT_BUILD_SUMMARY:" + json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    build_d_amusement()
