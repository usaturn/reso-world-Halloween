"""Deterministically build `blender/probe/probe.blend`, render `review/probe/`, and emit probe layout/manifest JSONs.

Run via:
    resoloop blender run modeling/probe/build.py --json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import bmesh  # type: ignore
import bpy  # type: ignore
from mathutils import Vector  # type: ignore

from modeling.lib.materials import (
    create_pbr_material,
    generate_asymmetric_test_png,
)
from modeling.lib.primitives import create_empty
from modeling.lib.render import render_review_images
from modeling.lib.scene import (
    reset_scene,
    save_blend,
)

KEY = "probe"
BLEND_REL_PATH = "blender/probe/probe.blend"
SCRIPT_REL_PATH = "modeling/probe/build.py"
TEX_REL_PATH = "blender/probe/textures/p0_asym_test.png"


def _add_uv_box(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    min_pt: tuple[float, float, float],
    max_pt: tuple[float, float, float],
) -> None:
    """Add an axis-aligned box to `bm` with outward normals and 0..1 UVs per face."""
    x0, y0, z0 = min_pt
    x1, y1, z1 = max_pt

    v000 = bm.verts.new((x0, y0, z0))
    v100 = bm.verts.new((x1, y0, z0))
    v110 = bm.verts.new((x1, y1, z0))
    v010 = bm.verts.new((x0, y1, z0))
    v001 = bm.verts.new((x0, y0, z1))
    v101 = bm.verts.new((x1, y0, z1))
    v111 = bm.verts.new((x1, y1, z1))
    v011 = bm.verts.new((x0, y1, z1))

    # Each face listed CCW when viewed from outside so normal points outward.
    faces_spec = [
        # Front (-Y)
        ([v000, v100, v101, v001], [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]),
        # Back (+Y)
        ([v110, v010, v011, v111], [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]),
        # Left (-X)
        ([v010, v000, v001, v011], [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]),
        # Right (+X)
        ([v100, v110, v111, v101], [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]),
        # Top (+Z)
        ([v001, v101, v111, v011], [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]),
        # Bottom (-Z)
        ([v010, v110, v100, v000], [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]),
    ]
    for verts, uvs in faces_spec:
        f = bm.faces.new(verts)
        for loop, uv in zip(f.loops, uvs):
            loop[uv_layer].uv = uv


def build_meter_ref(collection: bpy.types.Collection) -> bpy.types.Object:
    """Create `P0_MeterRef_001`: exact 1.0m x 1.0m x 1.0m reference block at (-1.5, 0.0, 0.0).

    Includes a lower 0.5m full 1mx1m base and an upper 0.5m rear block + front indicator step
    so total bounds are [-0.5..0.5, -0.5..0.5, 0.0..1.0] (1m x 1m x 1m) while visually
    showing +Z (top) and -Y/+Y orientation.
    """
    mesh = bpy.data.meshes.new("P0_MeterRef_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Lower half: full 1.0m x 1.0m x 0.5m
    _add_uv_box(bm, uv_layer, (-0.5, -0.5, 0.0), (0.5, 0.5, 0.5))
    # Upper half: 1.0m wide, 0.6m deep (y from -0.1 to +0.5), z from 0.5 to 1.0
    _add_uv_box(bm, uv_layer, (-0.5, -0.1, 0.5), (0.5, 0.5, 1.0))
    # Front-right corner calibration post reaching z=0.75 so +X/-X is also asymmetric
    _add_uv_box(bm, uv_layer, (0.2, -0.5, 0.5), (0.5, -0.1, 0.75))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    mat = create_pbr_material(
        "MAT_P0_MeterRef",
        base_color=(0.88, 0.42, 0.10, 1.0),
        roughness=0.55,
        metallic=0.0,
    )
    mesh.materials.append(mat)

    obj = bpy.data.objects.new("P0_MeterRef_001", mesh)
    obj.location = Vector((-1.5, 0.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_asym_sign(collection: bpy.types.Collection, tex_path: Path) -> bpy.types.Object:
    """Create `P0_AsymSign_001`: ground-centered sign board at (0.0, 0.0, 0.0) with asymmetric UV test texture."""
    mesh = bpy.data.meshes.new("P0_AsymSign_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Ground base plate (0.5m x 0.24m x 0.08m)
    _add_uv_box(bm, uv_layer, (-0.25, -0.12, 0.0), (0.25, 0.12, 0.08))
    # Vertical post (0.12m x 0.12m, z=0.08..0.50)
    _add_uv_box(bm, uv_layer, (-0.06, -0.06, 0.08), (0.06, 0.06, 0.50))
    # Main sign board (1.0m x 0.10m, z=0.50..1.30) with full 0..1 UV mapping on front (-Y) and back (+Y)
    _add_uv_box(bm, uv_layer, (-0.50, -0.05, 0.50), (0.50, 0.05, 1.30))
    # Upper-right asymmetric fin (+X/+Z indicator, x=0.30..0.50, z=1.30..1.40)
    _add_uv_box(bm, uv_layer, (0.30, -0.04, 1.30), (0.50, 0.04, 1.40))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    mat = create_pbr_material(
        "MAT_P0_AsymSign",
        base_color=(1.0, 1.0, 1.0, 1.0),
        roughness=0.65,
        metallic=0.0,
        base_color_image_path=tex_path,
    )
    mesh.materials.append(mat)

    obj = bpy.data.objects.new("P0_AsymSign_001", mesh)
    obj.location = Vector((0.0, 0.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_pivot_gate(collection: bpy.types.Collection) -> dict[str, bpy.types.Object]:
    """Create `P0_PivotGate_001` hierarchical assembly at (1.5, 0.0, 0.0)."""
    root_empty = create_empty(
        "P0_PivotGate_001",
        collection,
        location=(1.5, 0.0, 0.0),
        display_type="PLAIN_AXES",
        display_size=0.25,
    )

    mat_iron = create_pbr_material(
        "MAT_P0_GateIron",
        base_color=(0.18, 0.19, 0.22, 1.0),
        roughness=0.45,
        metallic=0.80,
    )
    mat_leaf = create_pbr_material(
        "MAT_P0_GateLeaf",
        base_color=(0.45, 0.24, 0.72, 1.0),
        roughness=0.50,
        metallic=0.35,
    )

    # Static Post + threshold base (`P0_PivotGate_001_Post`)
    post_mesh = bpy.data.meshes.new("P0_PivotGate_001_Post_Mesh")
    bm_post = bmesh.new()
    uv_post = bm_post.loops.layers.uv.new("UVMap")
    # Threshold sill: width 1.0m (-0.5..+0.5), depth 0.24m (-0.12..+0.12), height 0.10m (0.0..0.10)
    _add_uv_box(bm_post, uv_post, (-0.50, -0.12, 0.0), (0.50, 0.12, 0.10))
    # Left hinge pillar centered at x=-0.40, z=0.10..1.30
    _add_uv_box(bm_post, uv_post, (-0.48, -0.08, 0.10), (-0.32, 0.08, 1.30))
    # Right latch pillar centered at x=+0.44, z=0.10..1.20
    _add_uv_box(bm_post, uv_post, (0.38, -0.08, 0.10), (0.50, 0.08, 1.20))
    bmesh.ops.recalc_face_normals(bm_post, faces=bm_post.faces)
    bm_post.to_mesh(post_mesh)
    bm_post.free()
    post_mesh.update()
    post_mesh.materials.append(mat_iron)

    post_obj = bpy.data.objects.new("P0_PivotGate_001_Post", post_mesh)
    collection.objects.link(post_obj)
    post_obj.parent = root_empty
    post_obj.location = Vector((0.0, 0.0, 0.0))
    post_obj.scale = Vector((1.0, 1.0, 1.0))

    # MotionRoot Empty (`P0_PivotGate_001_Hinge`) at hinge axis (-0.40, 0.0, 0.10)
    hinge_empty = create_empty(
        "P0_PivotGate_001_Hinge",
        collection,
        location=(-0.40, 0.0, 0.10),
        rotation_euler_deg=(0.0, 0.0, 15.0),
        parent=root_empty,
        display_type="ARROWS",
        display_size=0.20,
    )

    # VisualRoot Gate Leaf (`P0_PivotGate_001_Leaf`) with local origin at hinge (0,0,0)
    leaf_mesh = bpy.data.meshes.new("P0_PivotGate_001_Leaf_Mesh")
    bm_leaf = bmesh.new()
    uv_leaf = bm_leaf.loops.layers.uv.new("UVMap")
    # Hinge barrel sleeve (x=0.0..0.08, z=0.0..1.05)
    _add_uv_box(bm_leaf, uv_leaf, (0.0, -0.04, 0.0), (0.08, 0.04, 1.05))
    # Lower rail (x=0.08..0.76, z=0.08..0.18)
    _add_uv_box(bm_leaf, uv_leaf, (0.08, -0.03, 0.08), (0.76, 0.03, 0.18))
    # Upper rail (x=0.08..0.76, z=0.82..0.92)
    _add_uv_box(bm_leaf, uv_leaf, (0.08, -0.03, 0.82), (0.76, 0.03, 0.92))
    # Outer vertical stile (x=0.68..0.76, z=0.08..1.00)
    _add_uv_box(bm_leaf, uv_leaf, (0.68, -0.03, 0.08), (0.76, 0.03, 1.00))
    # Middle vertical bar (x=0.36..0.42, z=0.18..0.82)
    _add_uv_box(bm_leaf, uv_leaf, (0.36, -0.025, 0.18), (0.42, 0.025, 0.82))
    bmesh.ops.recalc_face_normals(bm_leaf, faces=bm_leaf.faces)
    bm_leaf.to_mesh(leaf_mesh)
    bm_leaf.free()
    leaf_mesh.update()
    leaf_mesh.materials.append(mat_leaf)

    leaf_obj = bpy.data.objects.new("P0_PivotGate_001_Leaf", leaf_mesh)
    collection.objects.link(leaf_obj)
    leaf_obj.parent = hinge_empty
    leaf_obj.location = Vector((0.0, 0.0, 0.0))
    leaf_obj.scale = Vector((1.0, 1.0, 1.0))

    # AttachmentPoint Empty (`P0_PivotGate_001_Hook`) at tip of leaf (0.72, 0.0, 0.88)
    hook_empty = create_empty(
        "P0_PivotGate_001_Hook",
        collection,
        location=(0.72, 0.0, 0.88),
        parent=leaf_obj,
        display_type="SPHERE",
        display_size=0.08,
    )

    return {
        "root": root_empty,
        "post": post_obj,
        "hinge": hinge_empty,
        "leaf": leaf_obj,
        "hook": hook_empty,
    }


def verify_concept_art_readability_in_blender(root: Path) -> list[dict[str, Any]]:
    """Verify that all 7 concept_art/*.png files can be loaded by Blender (`bpy.data.images.load`)."""
    concept_dir = root / "concept_art"
    results: list[dict[str, Any]] = []
    for png_path in sorted(concept_dir.glob("*.png")):
        img = bpy.data.images.load(str(png_path.resolve()), check_existing=False)
        width, height = int(img.size[0]), int(img.size[1])
        channels = int(img.channels)
        readable = width > 0 and height > 0
        results.append({
            "file": str(png_path.relative_to(root)),
            "width": width,
            "height": height,
            "channels": channels,
            "readable_in_blender": readable,
        })
        bpy.data.images.remove(img)
    return results


def _count_mesh_stats(objs: list[bpy.types.Object]) -> tuple[int, int]:
    tris = 0
    verts = 0
    for obj in objs:
        if obj.type == "MESH" and obj.data is not None:
            mesh = obj.data
            mesh.calc_loop_triangles()
            tris += len(mesh.loop_triangles)
            verts += len(mesh.vertices)
    return tris, verts


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


def write_probe_data_files(
    root: Path,
    meter_obj: bpy.types.Object,
    sign_obj: bpy.types.Object,
    gate_objs: dict[str, bpy.types.Object],
) -> None:
    """Write `modeling/probe/probe_layout.json` and `modeling/probe/probe_manifest.json`."""
    probe_dir = root / "modeling" / "probe"
    probe_dir.mkdir(parents=True, exist_ok=True)

    bundle_dir_rel = "exports/probe/bundle"
    apply_plan_rel = "exports/probe/bundle/model.apply.json"
    report_file_rel = "exports/probe/bundle/report.json"
    has_export = (
        (root / bundle_dir_rel).is_dir()
        and (root / report_file_rel).is_file()
    )
    export_result_entry: dict[str, Any] = (
        {
            "status": "verified_resonite",
            "bundle_dir": bundle_dir_rel,
            "apply_plan": apply_plan_rel,
            "report_file": report_file_rel,
        }
        if has_export
        else {
            "status": "unexported",
            "bundle_dir": None,
            "apply_plan": None,
            "report_file": None,
        }
    )

    m_tris, m_verts = _count_mesh_stats([meter_obj])
    m_bounds = _compute_local_bounds([meter_obj], meter_obj.location)

    s_tris, s_verts = _count_mesh_stats([sign_obj])
    s_bounds = _compute_local_bounds([sign_obj], sign_obj.location)

    g_mesh_objs = [gate_objs["post"], gate_objs["leaf"]]
    g_tris, g_verts = _count_mesh_stats(g_mesh_objs)
    g_bounds = _compute_local_bounds(g_mesh_objs, gate_objs["root"].location)

    manifest_data: dict[str, Any] = {
        "schema_version": "1.0",
        "key": "probe",
        "updated_at": "2026-10-31T00:00:00Z",
        "assets": [
            {
                "asset_id": "P0_MeterRef_001",
                "key": "probe",
                "category": "probe",
                "area_id": "probe",
                "collection": "probe",
                "blend_file": BLEND_REL_PATH,
                "script_file": SCRIPT_REL_PATH,
                "origin_policy": "ground_center",
                "origin_world": [-1.5, 0.0, 0.0],
                "dimensions_m": {"width": 1.0, "depth": 1.0, "height": 1.0},
                "bounds_local": m_bounds,
                "parts": [
                    {
                        "part_id": "P0_MeterRef_001",
                        "role": "asset_root",
                        "parent_part": None,
                        "origin_policy": "ground_center",
                        "pivot_local": [0.0, 0.0, 0.0],
                    }
                ],
                "hierarchy": {
                    "asset_root": "P0_MeterRef_001",
                    "motion_roots": [],
                    "visual_roots": ["P0_MeterRef_001"],
                    "attachment_points": [],
                },
                "materials": ["MAT_P0_MeterRef"],
                "textures": [],
                "metrics": {
                    "measured": True,
                    "measurement_source": "blender_scene",
                    "triangles": m_tris,
                    "vertices": m_verts,
                    "materials_count": 1,
                    "objects_count": 1,
                },
                "export_result": export_result_entry,
                "replacement": {
                    "is_placeholder": False,
                    "modifiable": True,
                    "notes": "1m x 1m x 1m P0 scale and axis reference block.",
                    "future_target": None,
                },
            },
            {
                "asset_id": "P0_AsymSign_001",
                "key": "probe",
                "category": "probe",
                "area_id": "probe",
                "collection": "probe",
                "blend_file": BLEND_REL_PATH,
                "script_file": SCRIPT_REL_PATH,
                "origin_policy": "ground_center",
                "origin_world": [0.0, 0.0, 0.0],
                "dimensions_m": {"width": 1.0, "depth": 0.24, "height": 1.4},
                "bounds_local": s_bounds,
                "parts": [
                    {
                        "part_id": "P0_AsymSign_001",
                        "role": "asset_root",
                        "parent_part": None,
                        "origin_policy": "ground_center",
                        "pivot_local": [0.0, 0.0, 0.0],
                    }
                ],
                "hierarchy": {
                    "asset_root": "P0_AsymSign_001",
                    "motion_roots": [],
                    "visual_roots": ["P0_AsymSign_001"],
                    "attachment_points": [],
                },
                "materials": ["MAT_P0_AsymSign"],
                "textures": [TEX_REL_PATH],
                "metrics": {
                    "measured": True,
                    "measurement_source": "blender_scene",
                    "triangles": s_tris,
                    "vertices": s_verts,
                    "materials_count": 1,
                    "objects_count": 1,
                },
                "export_result": export_result_entry,
                "replacement": {
                    "is_placeholder": False,
                    "modifiable": True,
                    "notes": "Asymmetric UV and texture orientation test signboard.",
                    "future_target": None,
                },
            },
            {
                "asset_id": "P0_PivotGate_001",
                "key": "probe",
                "category": "probe",
                "area_id": "probe",
                "collection": "probe",
                "blend_file": BLEND_REL_PATH,
                "script_file": SCRIPT_REL_PATH,
                "origin_policy": "ground_center",
                "origin_world": [1.5, 0.0, 0.0],
                "dimensions_m": {"width": 1.0, "depth": 0.35, "height": 1.3},
                "bounds_local": g_bounds,
                "parts": [
                    {
                        "part_id": "P0_PivotGate_001",
                        "role": "asset_root",
                        "parent_part": None,
                        "origin_policy": "ground_center",
                        "pivot_local": [0.0, 0.0, 0.0],
                    },
                    {
                        "part_id": "P0_PivotGate_001_Post",
                        "role": "static_part",
                        "parent_part": "P0_PivotGate_001",
                        "origin_policy": "ground_center",
                        "pivot_local": [0.0, 0.0, 0.0],
                    },
                    {
                        "part_id": "P0_PivotGate_001_Hinge",
                        "role": "motion_root",
                        "parent_part": "P0_PivotGate_001",
                        "origin_policy": "hinge_pivot",
                        "pivot_local": [-0.4, 0.0, 0.1],
                    },
                    {
                        "part_id": "P0_PivotGate_001_Leaf",
                        "role": "visual_root",
                        "parent_part": "P0_PivotGate_001_Hinge",
                        "origin_policy": "hinge_pivot",
                        "pivot_local": [0.0, 0.0, 0.0],
                    },
                    {
                        "part_id": "P0_PivotGate_001_Hook",
                        "role": "attachment_point",
                        "parent_part": "P0_PivotGate_001_Leaf",
                        "origin_policy": "attachment_point",
                        "pivot_local": [0.72, 0.0, 0.88],
                    },
                ],
                "hierarchy": {
                    "asset_root": "P0_PivotGate_001",
                    "motion_roots": ["P0_PivotGate_001_Hinge"],
                    "visual_roots": ["P0_PivotGate_001_Post", "P0_PivotGate_001_Leaf"],
                    "attachment_points": ["P0_PivotGate_001_Hook"],
                },
                "materials": ["MAT_P0_GateIron", "MAT_P0_GateLeaf"],
                "textures": [],
                "metrics": {
                    "measured": True,
                    "measurement_source": "blender_scene",
                    "triangles": g_tris,
                    "vertices": g_verts,
                    "materials_count": 2,
                    "objects_count": 5,
                },
                "export_result": export_result_entry,
                "replacement": {
                    "is_placeholder": False,
                    "modifiable": True,
                    "notes": "Parent-child hierarchy and hinge pivot gate assembly.",
                    "future_target": None,
                },
            },
        ],
    }

    layout_data: dict[str, Any] = {
        "schema_version": "1.0",
        "area_id": "probe",
        "key": "probe",
        "name": "P0 Technical Probe Stage",
        "theme": "Technical calibration lineup for 1m scale, UV asymmetry, and parent-child pivot hierarchy",
        "bounds": {"min": [-3.0, -2.0, 0.0], "max": [3.0, 2.0, 2.5]},
        "Anchor": {
            "anchor_id": "P0_AsymSign_001",
            "position": [0.0, 0.0, 0.0],
            "dimensions_m": [1.0, 0.24, 1.4],
            "orientation_deg": 0.0,
            "role": "Central UV and orientation calibration signboard",
        },
        "Circulation": {
            "primary_path_id": "P0_Front_Walk_001",
            "min_walk_width_m": 2.5,
            "entry_points": [[-2.5, -1.5, 0.0], [2.5, -1.5, 0.0]],
            "loop_description": "Front viewing corridor along y = -1.5m facing +Y",
        },
        "Framing": {
            "left_edge": "P0_MeterRef_001 at x = -1.5m",
            "right_edge": "P0_PivotGate_001 at x = +1.5m",
            "focal_target": "P0_AsymSign_001 at x = 0.0m",
            "view_cone_deg": 60.0,
        },
        "Story_Cluster": [
            {
                "cluster_id": "P0_Cluster_Calibration",
                "center": [0.0, 0.0, 0.0],
                "radius_m": 2.5,
                "intent": "Verify 1m dimensions, texture UV orientation, and hinge rotation pivot",
                "asset_ids": ["P0_MeterRef_001", "P0_AsymSign_001", "P0_PivotGate_001"],
            }
        ],
        "Common_Placement": [],
        "Hero_or_Gimmick": {
            "asset_id": "P0_PivotGate_001",
            "motion_roots": ["P0_PivotGate_001_Hinge"],
            "visual_roots": ["P0_PivotGate_001_Post", "P0_PivotGate_001_Leaf"],
            "attachment_points": ["P0_PivotGate_001_Hook"],
            "interaction_notes": "Gate leaf rotates around P0_PivotGate_001_Hinge (+Z axis) without shifting post.",
        },
        "Exclusions": [
            {
                "zone_id": "P0_Excl_CameraFront",
                "bounds": {"min": [-2.5, -2.0, 0.0], "max": [2.5, -0.6, 2.0]},
                "reason": "Keep front viewing corridor unobstructed for review cameras.",
            }
        ],
        "placements": [
            {
                "placement_id": "P0_Place_MeterRef_001",
                "asset_id": "P0_MeterRef_001",
                "source_key": "probe",
                "category": "probe",
                "position": [-1.5, 0.0, 0.0],
                "rotation_euler_deg": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "origin_policy": "ground_center",
                "clearance_radius_m": 0.75,
            },
            {
                "placement_id": "P0_Place_AsymSign_001",
                "asset_id": "P0_AsymSign_001",
                "source_key": "probe",
                "category": "probe",
                "position": [0.0, 0.0, 0.0],
                "rotation_euler_deg": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "origin_policy": "ground_center",
                "clearance_radius_m": 0.65,
            },
            {
                "placement_id": "P0_Place_PivotGate_001",
                "asset_id": "P0_PivotGate_001",
                "source_key": "probe",
                "category": "probe",
                "position": [1.5, 0.0, 0.0],
                "rotation_euler_deg": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "origin_policy": "ground_center",
                "clearance_radius_m": 0.75,
            },
        ],
    }

    (probe_dir / "probe_manifest.json").write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (probe_dir / "probe_layout.json").write_text(
        json.dumps(layout_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_probe() -> dict[str, Any]:
    """Build the probe scene, render review images, save `blender/probe/probe.blend`, and write probe JSONs."""
    _scene, probe_col = reset_scene(KEY, seed=42)

    tex_path = PROJECT_ROOT / TEX_REL_PATH
    generate_asymmetric_test_png(tex_path, width=256, height=256)

    # Verify concept_art readability inside Blender without keeping unused datablocks
    concept_art_checks = verify_concept_art_readability_in_blender(PROJECT_ROOT)

    meter_obj = build_meter_ref(probe_col)
    sign_obj = build_asym_sign(probe_col, tex_path)
    gate_objs = build_pivot_gate(probe_col)

    overview_png = PROJECT_ROOT / "review" / "probe" / "01_probe_overview.png"
    detail_png = PROJECT_ROOT / "review" / "probe" / "02_probe_detail.png"

    render_review_images(
        views=[
            {
                "filepath": overview_png,
                "location": (0.0, -4.4, 1.85),
                "target": (0.0, 0.0, 0.65),
                "lens_mm": 35.0,
            },
            {
                "filepath": detail_png,
                "location": (1.35, -2.5, 1.35),
                "target": (0.75, 0.0, 0.65),
                "lens_mm": 40.0,
            },
        ],
        width=960,
        height=540,
        samples=24,
    )

    blend_path = PROJECT_ROOT / BLEND_REL_PATH
    save_blend(blend_path, pack_images=True)

    write_probe_data_files(PROJECT_ROOT, meter_obj, sign_obj, gate_objs)

    summary = {
        "key": KEY,
        "blend_file": BLEND_REL_PATH,
        "objects_count": len(bpy.data.objects),
        "object_names": sorted(o.name for o in bpy.data.objects),
        "meshes_count": len(bpy.data.meshes),
        "materials_count": len(bpy.data.materials),
        "images_count": len([i for i in bpy.data.images if i.name not in ("Render Result", "Viewer Node")]),
        "concept_art_checked": len(concept_art_checks),
        "concept_art_all_readable": all(c["readable_in_blender"] for c in concept_art_checks),
        "concept_art_results": concept_art_checks,
        "review_images": [
            str(overview_png.relative_to(PROJECT_ROOT)),
            str(detail_png.relative_to(PROJECT_ROOT)),
        ],
    }
    print("PROBE_BUILD_SUMMARY:" + json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    build_probe()
