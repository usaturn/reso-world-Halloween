"""Deterministically build `blender/B_mansion/B_mansion.blend`, render `review/B_mansion/`, and emit area layout & manifest JSONs.

Run via:
    resoloop blender run modeling/B_mansion/build.py --json
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import bmesh  # type: ignore
import bpy  # type: ignore
from mathutils import Euler, Vector  # type: ignore

from modeling.B_mansion.layout_data import (
    COMMON_PLACEMENTS,
    build_b_mansion_area_layout_dict,
)
from modeling.common.build import BLEND_REL_PATH as COMMON_BLEND_REL_PATH
from modeling.common.build import build_common
from modeling.lib.common_parts import append_common_part
from modeling.lib.materials import create_pbr_material
from modeling.lib.render import render_review_images
from modeling.lib.scene import reset_scene, save_blend

KEY = "B_mansion"
BLEND_REL_PATH = "blender/B_mansion/B_mansion.blend"
SCRIPT_REL_PATH = "modeling/B_mansion/build.py"
AREA_LAYOUT_REL_PATH = "layout/areas/B_mansion.json"
MANIFEST_REL_PATH = "assets/manifest/B_mansion.json"


def _add_box(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    min_pt: tuple[float, float, float],
    max_pt: tuple[float, float, float],
    material_index: int = 0,
) -> None:
    """Add an axis-aligned box with outward normals, 0..1 UVs, and material_index."""
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
    uv_quad = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    faces_spec = [
        [v000, v100, v101, v001],  # -Y
        [v110, v010, v011, v111],  # +Y
        [v010, v000, v001, v011],  # -X
        [v100, v110, v111, v101],  # +X
        [v001, v101, v111, v011],  # +Z
        [v010, v110, v100, v000],  # -Z
    ]
    for verts in faces_spec:
        f = bm.faces.new(verts)
        f.material_index = material_index
        for loop, uv in zip(f.loops, uv_quad):
            loop[uv_layer].uv = uv


def _add_frustum_z(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    center_xy: tuple[float, float],
    z0: float,
    z1: float,
    r0: float,
    r1: float,
    segments: int = 12,
    material_index: int = 0,
) -> None:
    """Add a vertical n-gon frustum or cone from z0 (radius r0) to z1 (radius r1)."""
    cx, cy = center_xy
    ring0 = []
    ring1 = []
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        ring0.append(bm.verts.new((cx + r0 * math.cos(a), cy + r0 * math.sin(a), z0)))
        if r1 > 1e-5:
            ring1.append(bm.verts.new((cx + r1 * math.cos(a), cy + r1 * math.sin(a), z1)))

    f_bot = bm.faces.new(list(reversed(ring0)))
    f_bot.material_index = material_index
    for i, loop in enumerate(f_bot.loops):
        ang = 2.0 * math.pi * i / segments
        loop[uv_layer].uv = (0.5 + 0.45 * math.cos(ang), 0.5 + 0.45 * math.sin(ang))

    if r1 <= 1e-5:
        apex = bm.verts.new((cx, cy, z1))
        for i in range(segments):
            jn = (i + 1) % segments
            f_side = bm.faces.new([ring0[i], ring0[jn], apex])
            f_side.material_index = material_index
            u0, u1 = i / segments, (i + 1) / segments
            f_side.loops[0][uv_layer].uv = (u0, 0.0)
            f_side.loops[1][uv_layer].uv = (u1, 0.0)
            f_side.loops[2][uv_layer].uv = (0.5 * (u0 + u1), 1.0)
    else:
        for i in range(segments):
            jn = (i + 1) % segments
            f_side = bm.faces.new([ring0[i], ring0[jn], ring1[jn], ring1[i]])
            f_side.material_index = material_index
            u0, u1 = i / segments, (i + 1) / segments
            f_side.loops[0][uv_layer].uv = (u0, 0.0)
            f_side.loops[1][uv_layer].uv = (u1, 0.0)
            f_side.loops[2][uv_layer].uv = (u1, 1.0)
            f_side.loops[3][uv_layer].uv = (u0, 1.0)

        f_top = bm.faces.new(ring1)
        f_top.material_index = material_index
        for i, loop in enumerate(f_top.loops):
            ang = 2.0 * math.pi * i / segments
            loop[uv_layer].uv = (0.5 + 0.45 * math.cos(ang), 0.5 + 0.45 * math.sin(ang))


def _add_tube_segment(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    p0: tuple[float, float, float],
    p1: tuple[float, float, float],
    r0: float,
    r1: float,
    segments: int = 8,
    material_index: int = 0,
) -> None:
    """Add a 3D tapered cylinder/branch between p0 and p1."""
    v0 = Vector(p0)
    v1 = Vector(p1)
    axis = v1 - v0
    if axis.length < 1e-5:
        return
    z_dir = axis.normalized()
    up_ref = Vector((0.0, 0.0, 1.0)) if abs(z_dir.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    x_dir = z_dir.cross(up_ref).normalized()
    y_dir = z_dir.cross(x_dir).normalized()

    ring0 = []
    ring1 = []
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        radial = x_dir * math.cos(a) + y_dir * math.sin(a)
        ring0.append(bm.verts.new(v0 + radial * r0))
        ring1.append(bm.verts.new(v1 + radial * r1))

    f_bot = bm.faces.new(list(reversed(ring0)))
    f_bot.material_index = material_index
    for loop in f_bot.loops:
        loop[uv_layer].uv = (0.5, 0.5)

    for i in range(segments):
        jn = (i + 1) % segments
        f_side = bm.faces.new([ring0[i], ring0[jn], ring1[jn], ring1[i]])
        f_side.material_index = material_index
        f_side.loops[0][uv_layer].uv = (0.0, 0.0)
        f_side.loops[1][uv_layer].uv = (1.0, 0.0)
        f_side.loops[2][uv_layer].uv = (1.0, 1.0)
        f_side.loops[3][uv_layer].uv = (0.0, 1.0)

    f_top = bm.faces.new(ring1)
    f_top.material_index = material_index
    for loop in f_top.loops:
        loop[uv_layer].uv = (0.5, 0.5)


def _create_mesh_obj(
    name: str,
    bm: bmesh.types.BMesh,
    materials: list[bpy.types.Material],
    collection: bpy.types.Collection,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    """Finalize a BMesh into a Blender MESH object with uniform scale and clean normals."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    for m in materials:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    if parent is not None:
        obj.parent = parent
    obj.location = Vector(location)
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = Euler(tuple(math.radians(d) for d in rotation_deg), "XYZ")
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def _create_empty_obj(
    name: str,
    collection: bpy.types.Collection,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    """Create an Empty object with uniform (1,1,1) scale."""
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.25
    if parent is not None:
        obj.parent = parent
    obj.location = Vector(location)
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = Euler(tuple(math.radians(d) for d in rotation_deg), "XYZ")
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def get_b_mansion_materials() -> dict[str, bpy.types.Material]:
    """Create all `MAT_BMN_*` PBR materials for Area B."""
    return {
        "courtyard_slate": create_pbr_material(
            "MAT_BMN_CourtyardSlate",
            base_color=(0.19, 0.18, 0.23, 1.0),
            roughness=0.78,
        ),
        "grave_soil": create_pbr_material(
            "MAT_BMN_GraveyardSoil",
            base_color=(0.12, 0.10, 0.14, 1.0),
            roughness=0.92,
        ),
        "mansion_stone": create_pbr_material(
            "MAT_BMN_MansionWallStone",
            base_color=(0.24, 0.21, 0.29, 1.0),
            roughness=0.74,
        ),
        "mansion_roof": create_pbr_material(
            "MAT_BMN_MansionRoofTile",
            base_color=(0.13, 0.11, 0.18, 1.0),
            roughness=0.65,
        ),
        "wrought_iron": create_pbr_material(
            "MAT_BMN_WroughtIron",
            base_color=(0.10, 0.10, 0.13, 1.0),
            metallic=0.82,
            roughness=0.42,
        ),
        "dark_wood": create_pbr_material(
            "MAT_BMN_DarkOakWood",
            base_color=(0.22, 0.13, 0.09, 1.0),
            roughness=0.68,
        ),
        "dead_bark": create_pbr_material(
            "MAT_BMN_DeadTreeBark",
            base_color=(0.18, 0.14, 0.16, 1.0),
            roughness=0.88,
        ),
        "tombstone": create_pbr_material(
            "MAT_BMN_TombstoneGranite",
            base_color=(0.38, 0.37, 0.43, 1.0),
            roughness=0.72,
        ),
        "ghost_cloth": create_pbr_material(
            "MAT_BMN_GhostCloth",
            base_color=(0.92, 0.95, 1.0, 1.0),
            roughness=0.35,
            emission_color=(0.55, 0.72, 1.0, 1.0),
            emission_strength=1.2,
        ),
        "warm_glow": create_pbr_material(
            "MAT_BMN_WarmWindowGlow",
            base_color=(1.0, 0.66, 0.22, 1.0),
            roughness=0.25,
            emission_color=(1.0, 0.62, 0.18, 1.0),
            emission_strength=4.2,
        ),
        "eerie_glow": create_pbr_material(
            "MAT_BMN_EerieVioletGlow",
            base_color=(0.68, 0.38, 1.0, 1.0),
            roughness=0.30,
            emission_color=(0.68, 0.35, 1.0, 1.0),
            emission_strength=3.2,
        ),
        "bell_bronze": create_pbr_material(
            "MAT_BMN_BellBronze",
            base_color=(0.76, 0.56, 0.22, 1.0),
            metallic=0.85,
            roughness=0.32,
        ),
        "hall_carpet": create_pbr_material(
            "MAT_BMN_HallVelvetCarpet",
            base_color=(0.48, 0.10, 0.16, 1.0),
            roughness=0.80,
        ),
    }


def build_courtyard_ground(
    col: bpy.types.Collection, mats: dict[str, bpy.types.Material]
) -> dict[str, Any]:
    """Build `BMN_CourtyardGround_001` at (0.0, 32.0, 1.5), including porch steps to z=1.779m."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    # Origin is (0.0, 32.0, 1.5)
    # 1. Central courtyard slate terrace (world x=-5.2..5.2, y=20.2..36.4, local y=-11.8..+4.4)
    _add_box(bm, uv, (-5.2, -11.8, 0.0), (5.2, 4.4, 0.06), material_index=0)
    # 2. East & West diagonal bridge connector paths (world y=21.2..29.5, x=-16.2..+16.2)
    _add_box(bm, uv, (-16.2, -10.8, 0.0), (-5.2, -7.8, 0.05), material_index=0)
    _add_box(bm, uv, (5.2, -10.8, 0.0), (16.2, -7.8, 0.05), material_index=0)
    # 3. West and East graveyard soil beds with low stone curbing (world x=±5.4..±14.0, y=24.5..35.8)
    for sign in (-1.0, 1.0):
        x_in, x_out = sorted([sign * 5.4, sign * 14.0])
        _add_box(bm, uv, (x_in, -7.5, 0.0), (x_out, 3.8, 0.08), material_index=1)
        _add_box(bm, uv, (x_in, -7.5, 0.0), (x_out, -7.25, 0.20), material_index=2)
        _add_box(bm, uv, (x_in, 3.55, 0.0), (x_out, 3.8, 0.20), material_index=2)
    # 4. Gentle 3-step / ramp porch apron bridging world y=34.8..36.39 (local y=2.8..4.39) up to z=+0.279m
    # Aligned with M03 porch arch centre at world x=+0.335 (stops flush at mansion plinth y=36.3895 to prevent z-fighting)
    _add_box(bm, uv, (-1.6, 2.8, 0.0), (2.25, 4.388, 0.10), material_index=2)
    _add_box(bm, uv, (-1.45, 3.35, 0.10), (2.10, 4.388, 0.19), material_index=2)
    _add_box(bm, uv, (-1.30, 3.88, 0.19), (1.95, 4.388, 0.279), material_index=2)
    # Side step cheek blocks
    _add_box(bm, uv, (-1.85, 2.8, 0.0), (-1.45, 4.388, 0.42), material_index=2)
    _add_box(bm, uv, (2.05, 2.8, 0.0), (2.45, 4.388, 0.42), material_index=2)

    obj = _create_mesh_obj(
        "BMN_CourtyardGround_001",
        bm,
        [mats["courtyard_slate"], mats["grave_soil"], mats["mansion_stone"]],
        col,
        location=(0.0, 32.0, 1.5),
    )
    return {
        "asset_id": "BMN_CourtyardGround_001",
        "category": "terrain",
        "origin_policy": "ground_center",
        "root_obj": obj,
        "all_objs": [obj],
        "parts": [
            {
                "part_id": "BMN_CourtyardGround_001",
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            }
        ],
        "hierarchy": {
            "asset_root": "BMN_CourtyardGround_001",
            "motion_roots": [],
            "visual_roots": ["BMN_CourtyardGround_001"],
            "attachment_points": [],
        },
        "is_placeholder": False,
        "future_target": None,
        "notes": "Courtyard slate paving, east/west diagonal bridge connector walkways, graveyard soil beds, and gentle 3-step porch approach rising +0.279m (z=1.779m) to M03's front porch.",
    }


def build_front_gate(
    col: bpy.types.Collection, mats: dict[str, bpy.types.Material]
) -> dict[str, Any]:
    """Build `BMN_FrontGate_001` at (0.0, 21.5, 1.5) with 5.2m clear road span and 2 lantern hooks."""
    root = _create_empty_obj("BMN_FrontGate_001", col, location=(0.0, 21.5, 1.5))

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    # Left & Right Gothic stone pillars at x = -2.85 and +2.85 (clear width = 5.1m > 4.0m main road)
    for sx in (-1.0, 1.0):
        px = sx * 2.85
        _add_box(bm, uv, (px - 0.45, -0.45, 0.0), (px + 0.45, 0.45, 0.55), material_index=0)
        _add_box(bm, uv, (px - 0.36, -0.36, 0.55), (px + 0.36, 0.36, 4.20), material_index=0)
        _add_box(bm, uv, (px - 0.46, -0.46, 4.20), (px + 0.46, 0.46, 4.50), material_index=0)
        # Pillar top glowing pumpkin/lantern finial
        _add_frustum_z(bm, uv, (px, 0.0), 4.50, 5.05, 0.28, 0.16, segments=8, material_index=2)
        _add_frustum_z(bm, uv, (px, 0.0), 5.05, 5.45, 0.24, 0.0, segments=8, material_index=1)
        # Side iron fence wings from x=±3.3 to x=±4.75
        wx0, wx1 = sorted([sx * 3.30, sx * 4.75])
        _add_box(bm, uv, (wx0, -0.15, 0.0), (wx1, 0.15, 0.35), material_index=0)
        _add_box(bm, uv, (wx0, -0.05, 0.35), (wx1, 0.05, 2.20), material_index=1)

    # Overhead wrought-iron Gothic arch spanning x=-2.85..+2.85 at height z=4.35..5.85m
    arch_segs = 10
    for i in range(arch_segs):
        t0 = i / arch_segs
        t1 = (i + 1) / arch_segs
        x0 = -2.85 + 5.70 * t0
        x1 = -2.85 + 5.70 * t1
        z0 = 4.35 + 1.35 * math.sin(math.pi * t0)
        z1 = 4.35 + 1.35 * math.sin(math.pi * t1)
        _add_tube_segment(bm, uv, (x0, 0.0, z0), (x1, 0.0, z1), 0.11, 0.11, segments=6, material_index=1)
        _add_tube_segment(bm, uv, (x0, 0.0, z0 + 0.32), (x1, 0.0, z1 + 0.32), 0.08, 0.08, segments=6, material_index=1)
    # Central crest medallion at apex (0.0, 0.0, 5.95)
    _add_box(bm, uv, (-0.42, -0.10, 5.55), (0.42, 0.10, 6.25), material_index=1)
    _add_box(bm, uv, (-0.24, -0.13, 5.70), (0.24, 0.13, 6.10), material_index=2)

    arch_obj = _create_mesh_obj(
        "BMN_FrontGate_001_Arch",
        bm,
        [mats["mansion_stone"], mats["wrought_iron"], mats["warm_glow"]],
        col,
        parent=root,
    )

    hooks = []
    for label, hx in (("HookWest", -2.35), ("HookEast", 2.35)):
        hbm = bmesh.new()
        huv = hbm.loops.layers.uv.new("UVMap")
        _add_box(hbm, huv, (-0.12, -0.06, -0.08), (0.12, 0.06, 0.08), material_index=0)
        _add_frustum_z(hbm, huv, (0.0, 0.0), -0.38, -0.08, 0.14, 0.10, segments=6, material_index=1)
        hobj = _create_mesh_obj(
            f"BMN_FrontGate_001_{label}",
            hbm,
            [mats["wrought_iron"], mats["warm_glow"]],
            col,
            location=(hx, 0.0, 3.65),
            parent=root,
        )
        hooks.append(hobj)

    return {
        "asset_id": "BMN_FrontGate_001",
        "category": "architecture",
        "origin_policy": "ground_center",
        "root_obj": root,
        "all_objs": [root, arch_obj, *hooks],
        "parts": [
            {
                "part_id": "BMN_FrontGate_001",
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": "BMN_FrontGate_001_Arch",
                "role": "visual_root",
                "parent_part": "BMN_FrontGate_001",
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": "BMN_FrontGate_001_HookWest",
                "role": "attachment_point",
                "parent_part": "BMN_FrontGate_001",
                "origin_policy": "attachment_point",
                "pivot_local": [-2.35, 0.0, 3.65],
            },
            {
                "part_id": "BMN_FrontGate_001_HookEast",
                "role": "attachment_point",
                "parent_part": "BMN_FrontGate_001",
                "origin_policy": "attachment_point",
                "pivot_local": [2.35, 0.0, 3.65],
            },
        ],
        "hierarchy": {
            "asset_root": "BMN_FrontGate_001",
            "motion_roots": [],
            "visual_roots": ["BMN_FrontGate_001_Arch"],
            "attachment_points": ["BMN_FrontGate_001_HookWest", "BMN_FrontGate_001_HookEast"],
        },
        "is_placeholder": False,
        "future_target": None,
        "notes": "Gothic stone & wrought-iron courtyard entrance arch with 5.1m clear road span and hanging lantern attachment hooks.",
    }


def build_dead_tree(
    idx: int,
    location: tuple[float, float, float],
    rot_z_deg: float,
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `BMN_DeadTree_001` or `002` with a gnarled trunk and a branch `LanternHook` attachment_point."""
    asset_id = f"BMN_DeadTree_{idx:03d}"
    root = _create_empty_obj(asset_id, col, location=location, rotation_deg=(0.0, 0.0, rot_z_deg))

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    # Roots + gnarled trunk segments
    _add_frustum_z(bm, uv, (0.0, 0.0), 0.0, 0.65, 0.72, 0.44, segments=8, material_index=0)
    _add_tube_segment(bm, uv, (0.0, 0.0, 0.55), (0.18, -0.10, 2.20), 0.44, 0.30, segments=8, material_index=0)
    _add_tube_segment(bm, uv, (0.18, -0.10, 2.15), (-0.12, 0.08, 3.85), 0.30, 0.18, segments=7, material_index=0)
    _add_tube_segment(bm, uv, (-0.12, 0.08, 3.80), (0.05, 0.0, 5.10), 0.18, 0.06, segments=6, material_index=0)
    # Reaching spooky branches
    branches = [
        ((0.12, -0.05, 2.35), (1.45, -0.35, 3.10), 0.20, 0.06),
        ((0.02, 0.02, 2.85), (-1.35, 0.30, 3.75), 0.18, 0.05),
        ((-0.08, 0.05, 3.55), (0.95, 0.85, 4.55), 0.14, 0.04),
        ((-0.05, 0.04, 3.60), (-0.85, -0.90, 4.45), 0.14, 0.04),
    ]
    for p0, p1, r0, r1 in branches:
        _add_tube_segment(bm, uv, p0, p1, r0, r1, segments=6, material_index=0)

    trunk_id = f"{asset_id}_Trunk"
    trunk_obj = _create_mesh_obj(trunk_id, bm, [mats["dead_bark"]], col, parent=root)

    # Branch lantern hook (attachment_point with mesh so hierarchy exporter preserves the slot)
    hook_id = f"{asset_id}_LanternHook"
    hbm = bmesh.new()
    huv = hbm.loops.layers.uv.new("UVMap")
    _add_tube_segment(hbm, huv, (0.0, 0.0, 0.0), (0.0, 0.0, -0.32), 0.03, 0.03, segments=6, material_index=0)
    _add_frustum_z(hbm, huv, (0.0, 0.0), -0.62, -0.32, 0.16, 0.12, segments=6, material_index=1)
    hook_obj = _create_mesh_obj(
        hook_id,
        hbm,
        [mats["wrought_iron"], mats["warm_glow"]],
        col,
        location=(1.35, -0.32, 3.05),
        parent=root,
    )

    return {
        "asset_id": asset_id,
        "category": "prop",
        "origin_policy": "ground_center",
        "root_obj": root,
        "all_objs": [root, trunk_obj, hook_obj],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": trunk_id,
                "role": "visual_root",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": hook_id,
                "role": "attachment_point",
                "parent_part": asset_id,
                "origin_policy": "attachment_point",
                "pivot_local": [1.35, -0.32, 3.05],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [],
            "visual_roots": [trunk_id],
            "attachment_points": [hook_id],
        },
        "is_placeholder": False,
        "future_target": None,
        "notes": "Gnarled courtyard dead tree with reaching branches and a preserved branch lantern attachment hook.",
    }


def build_tilting_tombstone(
    idx: int,
    location: tuple[float, float, float],
    rot_z_deg: float,
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `BMN_Tombstone_001` or `002` (G07 Tilting Tombstone gimmick with StaticBase + TiltHinge -> Slab)."""
    asset_id = f"BMN_Tombstone_{idx:03d}"
    base_id = f"{asset_id}_StaticBase"
    hinge_id = f"{asset_id}_TiltHinge"
    slab_id = f"{asset_id}_Slab"

    root = _create_empty_obj(asset_id, col, location=location, rotation_deg=(0.0, 0.0, rot_z_deg))

    # Static stone plinth anchored to graveyard ground
    bbm = bmesh.new()
    buv = bbm.loops.layers.uv.new("UVMap")
    _add_box(bbm, buv, (-0.52, -0.28, 0.0), (0.52, 0.28, 0.18), material_index=0)
    base_obj = _create_mesh_obj(base_id, bbm, [mats["tombstone"]], col, parent=root)

    # Motion root hinge at local z=0.18m (top of plinth)
    hinge_obj = _create_empty_obj(hinge_id, col, location=(0.0, 0.0, 0.18), parent=root)

    # Tilting gothic headstone slab (built in hinge local space z=0..1.35m)
    sbm = bmesh.new()
    suv = sbm.loops.layers.uv.new("UVMap")
    _add_box(sbm, suv, (-0.38, -0.14, 0.0), (0.38, 0.14, 0.95), material_index=0)
    _add_box(sbm, suv, (-0.28, -0.13, 0.95), (0.28, 0.13, 1.18), material_index=0)
    # Cross finial on top + glowing epitaph rune plaque
    _add_box(sbm, suv, (-0.08, -0.09, 1.18), (0.08, 0.09, 1.48), material_index=0)
    _add_box(sbm, suv, (-0.20, -0.09, 1.28), (0.20, 0.09, 1.38), material_index=0)
    _add_box(sbm, suv, (-0.22, -0.16, 0.42), (0.22, 0.16, 0.72), material_index=1)
    slab_obj = _create_mesh_obj(
        slab_id,
        sbm,
        [mats["tombstone"], mats["eerie_glow"]],
        col,
        parent=hinge_obj,
    )

    return {
        "asset_id": asset_id,
        "category": "gimmick",
        "origin_policy": "ground_center",
        "root_obj": root,
        "all_objs": [root, base_obj, hinge_obj, slab_obj],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": base_id,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": hinge_id,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.18],
            },
            {
                "part_id": slab_id,
                "role": "visual_root",
                "parent_part": hinge_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.0],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [hinge_id],
            "visual_roots": [base_id, slab_id],
            "attachment_points": [],
        },
        "is_placeholder": False,
        "future_target": None,
        "notes": "G07 Tilting Tombstone gimmick with fixed stone base and Y-axis hinge_pivot at z=+0.18m (-18..+18 deg).",
    }


def build_static_tombstone(
    idx: int,
    location: tuple[float, float, float],
    rot_z_deg: float,
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build static tombstone prop `BMN_Tombstone_003` or `004` (1 object = 1 mesh)."""
    asset_id = f"BMN_Tombstone_{idx:03d}"
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    _add_box(bm, uv, (-0.48, -0.26, 0.0), (0.48, 0.26, 0.20), material_index=0)
    if idx == 3:
        # Obelisk pillar headstone
        _add_frustum_z(bm, uv, (0.0, 0.0), 0.20, 1.45, 0.28, 0.16, segments=4, material_index=0)
        _add_frustum_z(bm, uv, (0.0, 0.0), 1.45, 1.75, 0.16, 0.0, segments=4, material_index=1)
    else:
        # Celtic cross monument headstone
        _add_box(bm, uv, (-0.34, -0.14, 0.20), (0.34, 0.14, 1.10), material_index=0)
        _add_box(bm, uv, (-0.12, -0.12, 1.10), (0.12, 0.12, 1.68), material_index=0)
        _add_box(bm, uv, (-0.32, -0.12, 1.28), (0.32, 0.12, 1.48), material_index=0)
        _add_frustum_z(bm, uv, (0.0, 0.0), 1.22, 1.54, 0.22, 0.22, segments=8, material_index=1)

    obj = _create_mesh_obj(
        asset_id,
        bm,
        [mats["tombstone"], mats["eerie_glow"]],
        col,
        location=location,
        rotation_deg=(0.0, 0.0, rot_z_deg),
    )
    return {
        "asset_id": asset_id,
        "category": "prop",
        "origin_policy": "ground_center",
        "root_obj": obj,
        "all_objs": [obj],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            }
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [],
            "visual_roots": [asset_id],
            "attachment_points": [],
        },
        "is_placeholder": False,
        "future_target": None,
        "notes": "Static gothic graveyard monument variant (1 object = 1 mesh).",
    }


def build_mansion_placeholder(
    col: bpy.types.Collection, mats: dict[str, bpy.types.Material]
) -> dict[str, Any]:
    """Build `BMN_MansionPlaceholder_001` matching W09 M03 footprint (15.0m x 10.221m x 10.607m) at (0, 41.5, 1.5), rot_z=180°."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    # Local space matches M03_HauntedMansion_001 exactly:
    # bounds_local_m: min [-7.5, -5.1105, 0.0], max [7.5, 5.1105, 10.607], front_local = +Y
    # 1. Foundation plinth: x=-7.5..7.5, y=-5.1105..5.1105, z=0.0..0.279 (porch floor z=0.279m)
    _add_box(bm, uv, (-7.5, -5.1105, 0.0), (7.5, 5.1105, 0.279), material_index=0)

    # 2. Main mansion body behind porch back wall (y=-5.1105..+1.55), leaving central entrance hall void
    # Left wing (x=-7.5..-1.95) and Right wing (x=+1.30..+7.5)
    _add_box(bm, uv, (-7.5, -5.1105, 0.279), (-1.95, 1.55, 6.60), material_index=0)
    _add_box(bm, uv, (1.30, -5.1105, 0.279), (7.5, 1.55, 6.60), material_index=0)
    # Central upper floor above the doorway & entrance hall (x=-1.95..+1.30, z=4.20..7.40)
    _add_box(bm, uv, (-1.95, -5.1105, 4.20), (1.30, 1.55, 7.40), material_index=0)
    # Porch back wall at y=1.35..1.55 flanking the door opening (door opening x_local = -1.144..+0.474, z_local = 0.279..2.962)
    _add_box(bm, uv, (-1.95, 1.35, 0.279), (-1.144, 1.55, 4.20), material_index=0)
    _add_box(bm, uv, (0.474, 1.35, 0.279), (1.30, 1.55, 4.20), material_index=0)
    _add_box(bm, uv, (-1.144, 1.35, 2.962), (0.474, 1.55, 4.20), material_index=0)

    # 3. Raised 3-bay front arcade porch (y=1.55..4.076, porch columns along y=4.076)
    # Central arch columns at x=-1.302 and x=+0.632 (matching M03 porch_arch_right_ground & porch_arch_left_ground)
    col_xs = [-6.8, -3.8, -1.302, 0.632, 3.8, 6.8]
    for cx in col_xs:
        _add_box(bm, uv, (cx - 0.24, 3.82, 0.279), (cx + 0.24, 4.32, 3.75), material_index=0)
    # Porch arcade lintel / balcony at z=3.75..4.45 and central gothic gable apex at z=5.80
    _add_box(bm, uv, (-7.2, 1.55, 3.75), (7.2, 4.35, 4.35), material_index=1)
    _add_frustum_z(bm, uv, (-0.335, 3.0), 4.35, 6.20, 2.1, 0.1, segments=4, material_index=1)

    # 4. Steep Gothic Mansard Roofs & Twin Turret Spires reaching exactly z=10.607m
    _add_box(bm, uv, (-7.35, -4.95, 6.60), (-2.10, 1.40, 8.35), material_index=1)
    _add_box(bm, uv, (1.45, -4.95, 6.60), (7.35, 1.40, 8.35), material_index=1)
    # Central main spire (reaches exactly z=10.607m)
    _add_frustum_z(bm, uv, (-0.335, -1.2), 7.40, 10.607, 2.45, 0.0, segments=6, material_index=1)
    # Side octagonal turret spires
    _add_frustum_z(bm, uv, (-5.2, 0.2), 8.35, 10.35, 1.65, 0.0, segments=8, material_index=1)
    _add_frustum_z(bm, uv, (5.2, 0.2), 8.35, 10.35, 1.65, 0.0, segments=8, material_index=1)

    # 5. Glowing upper Gothic windows on front (+Y) and side walls
    for wx in (-5.6, -3.1, -0.335, 2.8, 5.6):
        _add_box(bm, uv, (wx - 0.48, 1.48, 4.75), (wx + 0.48, 1.62, 6.05), material_index=2)
    # Decorative wrought-iron roof cresting
    _add_box(bm, uv, (-6.5, -1.5, 8.35), (6.5, -1.35, 8.75), material_index=3)

    obj = _create_mesh_obj(
        "BMN_MansionPlaceholder_001",
        bm,
        [mats["mansion_stone"], mats["mansion_roof"], mats["warm_glow"], mats["wrought_iron"]],
        col,
        location=(0.0, 41.5, 1.5),
        rotation_deg=(0.0, 0.0, 180.0),
    )
    return {
        "asset_id": "BMN_MansionPlaceholder_001",
        "category": "architecture",
        "origin_policy": "ground_center",
        "root_obj": obj,
        "all_objs": [obj],
        "parts": [
            {
                "part_id": "BMN_MansionPlaceholder_001",
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            }
        ],
        "hierarchy": {
            "asset_root": "BMN_MansionPlaceholder_001",
            "motion_roots": [],
            "visual_roots": ["BMN_MansionPlaceholder_001"],
            "attachment_points": [],
        },
        "is_placeholder": True,
        "future_target": "M03_HauntedMansion_001",
        "notes": (
            "P1 architectural placeholder for M03_HauntedMansion_001 matching confirmed W09 dimensions "
            "(15.0m x 10.221m x 10.607m), porch floor (z_local=0.279m -> z_world=1.779m), front arcade, "
            "and open doorway cutout at world (0.335, 39.95, 1.779)."
        ),
    }


def build_mansion_double_door(
    col: bpy.types.Collection, mats: dict[str, bpy.types.Material]
) -> dict[str, Any]:
    """Build `BMN_MansionDoubleDoor_001` (G06) at (0.335, 39.95, 1.779) matching M03's 1.618m x 2.683m doorway."""
    asset_id = "BMN_MansionDoubleDoor_001"
    frame_id = f"{asset_id}_Frame"
    hinge_l_id = f"{asset_id}_HingeLeft"
    leaf_l_id = f"{asset_id}_LeafLeft"
    hinge_r_id = f"{asset_id}_HingeRight"
    leaf_r_id = f"{asset_id}_LeafRight"

    root = _create_empty_obj(asset_id, col, location=(0.335, 39.95, 1.779))

    # Static gothic arch doorframe surrounding x=-0.809..+0.809, z=0.0..2.683
    fbm = bmesh.new()
    fuv = fbm.loops.layers.uv.new("UVMap")
    _add_box(fbm, fuv, (-0.94, -0.14, 0.0), (-0.809, 0.14, 2.75), material_index=0)
    _add_box(fbm, fuv, (0.809, -0.14, 0.0), (0.94, 0.14, 2.75), material_index=0)
    _add_box(fbm, fuv, (-0.96, -0.16, 2.683), (0.96, 0.16, 2.92), material_index=0)
    frame_obj = _create_mesh_obj(frame_id, fbm, [mats["wrought_iron"]], col, parent=root)

    # Left Hinge at local (-0.809, 0.0, 0.0) -> world (-0.474, 39.95, 1.779)
    hinge_l = _create_empty_obj(hinge_l_id, col, location=(-0.809, 0.0, 0.0), parent=root)
    lbm = bmesh.new()
    luv = lbm.loops.layers.uv.new("UVMap")
    _add_box(lbm, luv, (0.0, -0.05, 0.0), (0.802, 0.05, 2.66), material_index=0)
    # Iron strap hinges + ring knocker at x=+0.66
    _add_box(lbm, luv, (0.0, -0.07, 0.45), (0.55, 0.07, 0.55), material_index=1)
    _add_box(lbm, luv, (0.0, -0.07, 2.05), (0.55, 0.07, 2.15), material_index=1)
    _add_box(lbm, luv, (0.60, -0.09, 1.20), (0.72, 0.09, 1.38), material_index=2)
    leaf_l = _create_mesh_obj(
        leaf_l_id,
        lbm,
        [mats["dark_wood"], mats["wrought_iron"], mats["bell_bronze"]],
        col,
        parent=hinge_l,
    )

    # Right Hinge at local (+0.809, 0.0, 0.0) -> world (+1.144, 39.95, 1.779)
    hinge_r = _create_empty_obj(hinge_r_id, col, location=(0.809, 0.0, 0.0), parent=root)
    rbm = bmesh.new()
    ruv = rbm.loops.layers.uv.new("UVMap")
    _add_box(rbm, ruv, (-0.802, -0.05, 0.0), (0.0, 0.05, 2.66), material_index=0)
    _add_box(rbm, ruv, (-0.55, -0.07, 0.45), (0.0, 0.07, 0.55), material_index=1)
    _add_box(rbm, ruv, (-0.55, -0.07, 2.05), (0.0, 0.07, 2.15), material_index=1)
    _add_box(rbm, ruv, (-0.72, -0.09, 1.20), (-0.60, 0.09, 1.38), material_index=2)
    leaf_r = _create_mesh_obj(
        leaf_r_id,
        rbm,
        [mats["dark_wood"], mats["wrought_iron"], mats["bell_bronze"]],
        col,
        parent=hinge_r,
    )

    return {
        "asset_id": asset_id,
        "category": "gimmick",
        "origin_policy": "ground_center",
        "root_obj": root,
        "all_objs": [root, frame_obj, hinge_l, leaf_l, hinge_r, leaf_r],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": frame_id,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": hinge_l_id,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [-0.809, 0.0, 0.0],
            },
            {
                "part_id": leaf_l_id,
                "role": "visual_root",
                "parent_part": hinge_l_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": hinge_r_id,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.809, 0.0, 0.0],
            },
            {
                "part_id": leaf_r_id,
                "role": "visual_root",
                "parent_part": hinge_r_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.0],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [hinge_l_id, hinge_r_id],
            "visual_roots": [frame_id, leaf_l_id, leaf_r_id],
            "attachment_points": [],
        },
        "is_placeholder": False,
        "future_target": None,
        "notes": (
            "G06 Haunted Mansion Double Doors (separate from M03 so it survives P2 M03 replacement). "
            "Left hinge at (-0.809,0,0) swings +Z 0..+85 deg; Right hinge at (+0.809,0,0) swings -Z -85..0 deg."
        ),
    }


def build_entrance_hall(
    col: bpy.types.Collection, mats: dict[str, bpy.types.Material]
) -> dict[str, Any]:
    """Build `BMN_EntranceHall_001` at (0.335, 41.80, 1.779) directly behind the G06 double doors."""
    asset_id = "BMN_EntranceHall_001"
    room_id = f"{asset_id}_Room"
    hook_id = f"{asset_id}_ChandelierHook"

    root = _create_empty_obj(asset_id, col, location=(0.335, 41.80, 1.779))

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    # Origin at (0.335, 41.80, 1.779); door plane is at world y=39.95 -> local y=-1.85
    # Floor slab & velvet red carpet runner (local x=-1.60..+1.60, y=-1.85..+1.85)
    _add_box(bm, uv, (-1.60, -1.85, -0.06), (1.60, 1.85, 0.02), material_index=0)
    _add_box(bm, uv, (-0.65, -1.82, 0.02), (0.65, 1.65, 0.05), material_index=1)
    # Left, Right, and Back wainscoting walls + ceiling at z=3.75m
    _add_box(bm, uv, (-1.65, -1.85, 0.0), (-1.48, 1.85, 3.75), material_index=2)
    _add_box(bm, uv, (1.48, -1.85, 0.0), (1.65, 1.85, 3.75), material_index=2)
    _add_box(bm, uv, (-1.65, 1.68, 0.0), (1.65, 1.85, 3.75), material_index=2)
    _add_box(bm, uv, (-1.65, -1.85, 3.65), (1.65, 1.85, 3.82), material_index=2)
    # Glowing gothic portrait/mirror focal frame on back wall (y=+1.60)
    _add_box(bm, uv, (-0.75, 1.56, 1.10), (0.75, 1.68, 2.85), material_index=3)
    room_obj = _create_mesh_obj(
        room_id,
        bm,
        [mats["courtyard_slate"], mats["hall_carpet"], mats["dark_wood"], mats["warm_glow"]],
        col,
        parent=root,
    )

    # Chandelier attachment hook at ceiling center (0.0, 0.0, 3.45)
    cbm = bmesh.new()
    cuv = cbm.loops.layers.uv.new("UVMap")
    _add_tube_segment(cbm, cuv, (0.0, 0.0, 0.20), (0.0, 0.0, -0.25), 0.04, 0.04, segments=6, material_index=0)
    _add_frustum_z(cbm, cuv, (0.0, 0.0), -0.45, -0.20, 0.42, 0.12, segments=8, material_index=1)
    hook_obj = _create_mesh_obj(
        hook_id,
        cbm,
        [mats["wrought_iron"], mats["warm_glow"]],
        col,
        location=(0.0, 0.0, 3.45),
        parent=root,
    )

    return {
        "asset_id": asset_id,
        "category": "architecture",
        "origin_policy": "ground_center",
        "root_obj": root,
        "all_objs": [root, room_obj, hook_obj],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": room_id,
                "role": "visual_root",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": hook_id,
                "role": "attachment_point",
                "parent_part": asset_id,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, 0.0, 3.45],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [],
            "visual_roots": [room_id],
            "attachment_points": [hook_id],
        },
        "is_placeholder": False,
        "future_target": None,
        "notes": "Gothic entrance hall vestibule behind G06 double doors with red carpet runner and ceiling chandelier attachment point.",
    }


def build_window_ghost(
    idx: int,
    location: tuple[float, float, float],
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `BMN_WindowGhost_001` or `002` (G08 Peeking Window Ghost on facade window)."""
    asset_id = f"BMN_WindowGhost_{idx:03d}"
    frame_id = f"{asset_id}_WindowFrame"
    pivot_id = f"{asset_id}_PeekPivot"
    ghost_id = f"{asset_id}_GhostBody"

    root = _create_empty_obj(asset_id, col, location=location)

    # Ornate gothic window sill & casing (static_part)
    fbm = bmesh.new()
    fuv = fbm.loops.layers.uv.new("UVMap")
    _add_box(fbm, fuv, (-0.62, -0.18, -0.08), (0.62, 0.18, 0.06), material_index=0)
    _add_box(fbm, fuv, (-0.56, -0.10, 0.06), (-0.42, 0.10, 1.35), material_index=0)
    _add_box(fbm, fuv, (0.42, -0.10, 0.06), (0.56, 0.10, 1.35), material_index=0)
    _add_box(fbm, fuv, (-0.60, -0.12, 1.35), (0.60, 0.12, 1.52), material_index=0)
    frame_obj = _create_mesh_obj(frame_id, fbm, [mats["mansion_stone"]], col, parent=root)

    # Motion root PeekPivot at local (0.0, -0.12, 0.0)
    pivot_obj = _create_empty_obj(pivot_id, col, location=(0.0, -0.12, 0.0), parent=root)

    # Cute peeking ghost body (tilts/slides outward toward -Y)
    gbm = bmesh.new()
    guv = gbm.loops.layers.uv.new("UVMap")
    _add_frustum_z(gbm, guv, (0.0, -0.12), 0.10, 0.68, 0.34, 0.24, segments=10, material_index=0)
    _add_frustum_z(gbm, guv, (0.0, -0.12), 0.68, 0.92, 0.24, 0.06, segments=10, material_index=0)
    # Cute waving arms + glowing eyes
    _add_tube_segment(gbm, guv, (-0.22, -0.15, 0.52), (-0.42, -0.32, 0.68), 0.08, 0.05, segments=6, material_index=0)
    _add_tube_segment(gbm, guv, (0.22, -0.15, 0.52), (0.42, -0.32, 0.68), 0.08, 0.05, segments=6, material_index=0)
    _add_box(gbm, guv, (-0.12, -0.38, 0.62), (-0.04, -0.32, 0.72), material_index=1)
    _add_box(gbm, guv, (0.04, -0.38, 0.62), (0.12, -0.32, 0.72), material_index=1)
    ghost_obj = _create_mesh_obj(
        ghost_id,
        gbm,
        [mats["ghost_cloth"], mats["warm_glow"]],
        col,
        parent=pivot_obj,
    )

    return {
        "asset_id": asset_id,
        "category": "gimmick",
        "origin_policy": "hinge_pivot",
        "root_obj": root,
        "all_objs": [root, frame_obj, pivot_obj, ghost_obj],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": frame_id,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": pivot_id,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, -0.12, 0.0],
            },
            {
                "part_id": ghost_id,
                "role": "visual_root",
                "parent_part": pivot_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.0],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [pivot_id],
            "visual_roots": [frame_id, ghost_id],
            "attachment_points": [],
        },
        "is_placeholder": False,
        "future_target": None,
        "notes": "G08 Peeking Window Ghost assembly mounted independently on upper facade window so it survives P2 M03 replacement.",
    }


def build_floating_ghost(
    idx: int,
    location: tuple[float, float, float],
    rot_z_deg: float,
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `BMN_FloatingGhost_001` or `002` (G05 Courtyard Floating Ghost)."""
    asset_id = f"BMN_FloatingGhost_{idx:03d}"
    pivot_id = f"{asset_id}_FloatPivot"
    body_id = f"{asset_id}_GhostBody"
    charm_id = f"{asset_id}_LanternCharm"

    root = _create_empty_obj(asset_id, col, location=location, rotation_deg=(0.0, 0.0, rot_z_deg))
    pivot_obj = _create_empty_obj(pivot_id, col, location=(0.0, 0.0, 0.0), parent=root)

    gbm = bmesh.new()
    guv = gbm.loops.layers.uv.new("UVMap")
    # Cute sheet ghost silhouette with witch hat & waving arms
    _add_frustum_z(gbm, guv, (0.0, 0.0), -0.45, 0.35, 0.46, 0.28, segments=12, material_index=0)
    _add_frustum_z(gbm, guv, (0.0, 0.0), 0.35, 0.62, 0.28, 0.10, segments=12, material_index=0)
    # Little witch hat brim + cone
    _add_frustum_z(gbm, guv, (0.0, 0.0), 0.58, 0.63, 0.34, 0.30, segments=10, material_index=1)
    _add_frustum_z(gbm, guv, (0.0, 0.0), 0.63, 1.02, 0.18, 0.0, segments=8, material_index=1)
    # Outstretched arms + glowing eyes
    _add_tube_segment(gbm, guv, (-0.25, 0.0, 0.15), (-0.52, -0.18, 0.28), 0.09, 0.05, segments=6, material_index=0)
    _add_tube_segment(gbm, guv, (0.25, 0.0, 0.15), (0.52, -0.18, 0.28), 0.09, 0.05, segments=6, material_index=0)
    _add_box(gbm, guv, (-0.13, -0.30, 0.22), (-0.05, -0.24, 0.32), material_index=2)
    _add_box(gbm, guv, (0.05, -0.30, 0.22), (0.13, -0.24, 0.32), material_index=2)
    body_obj = _create_mesh_obj(
        body_id,
        gbm,
        [mats["ghost_cloth"], mats["mansion_roof"], mats["warm_glow"]],
        col,
        parent=pivot_obj,
    )

    # Hand lantern charm attachment_point mesh at (0.52, -0.18, 0.10)
    cbm = bmesh.new()
    cuv = cbm.loops.layers.uv.new("UVMap")
    _add_frustum_z(cbm, cuv, (0.0, 0.0), -0.16, 0.04, 0.11, 0.09, segments=6, material_index=0)
    charm_obj = _create_mesh_obj(
        charm_id,
        cbm,
        [mats["eerie_glow"]],
        col,
        location=(0.52, -0.18, 0.10),
        parent=pivot_obj,
    )

    return {
        "asset_id": asset_id,
        "category": "gimmick",
        "origin_policy": "hinge_pivot",
        "root_obj": root,
        "all_objs": [root, pivot_obj, body_obj, charm_obj],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": pivot_id,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": body_id,
                "role": "visual_root",
                "parent_part": pivot_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": charm_id,
                "role": "attachment_point",
                "parent_part": pivot_id,
                "origin_policy": "attachment_point",
                "pivot_local": [0.52, -0.18, 0.10],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [pivot_id],
            "visual_roots": [body_id],
            "attachment_points": [charm_id],
        },
        "is_placeholder": False,
        "future_target": None,
        "notes": "G05 Courtyard Floating Ghost with vertical bobbing Z (-0.35..+0.35m) and yaw sway (-20..+20 deg) on FloatPivot.",
    }


def build_mansion_bell(
    col: bpy.types.Collection, mats: dict[str, bpy.types.Material]
) -> dict[str, Any]:
    """Build `BMN_MansionBell_001` (I04 Interactive Haunted Mansion Bell) at (-3.4, 35.8, 1.5)."""
    asset_id = "BMN_MansionBell_001"
    stand_id = f"{asset_id}_Stand"
    hinge_id = f"{asset_id}_BellHinge"
    bell_id = f"{asset_id}_BellBody"
    sound_id = f"{asset_id}_SoundPoint"

    root = _create_empty_obj(asset_id, col, location=(-3.4, 35.8, 1.5))

    # Stone plinth + gothic iron/timber belfry stand
    sbm = bmesh.new()
    suv = sbm.loops.layers.uv.new("UVMap")
    _add_box(sbm, suv, (-0.65, -0.55, 0.0), (0.65, 0.55, 0.28), material_index=0)
    _add_box(sbm, suv, (-0.52, -0.12, 0.28), (-0.36, 0.12, 2.55), material_index=1)
    _add_box(sbm, suv, (0.36, -0.12, 0.28), (0.52, 0.12, 2.55), material_index=1)
    _add_box(sbm, suv, (-0.62, -0.18, 2.45), (0.62, 0.18, 2.65), material_index=2)
    # Gable roof cap over belfry + pull-rope handle at reachable height z=1.10..1.65m
    _add_frustum_z(sbm, suv, (0.0, 0.0), 2.65, 3.25, 0.72, 0.05, segments=4, material_index=1)
    _add_tube_segment(sbm, suv, (0.26, -0.18, 2.40), (0.26, -0.18, 1.15), 0.025, 0.025, segments=6, material_index=3)
    stand_obj = _create_mesh_obj(
        stand_id,
        sbm,
        [mats["mansion_stone"], mats["dark_wood"], mats["wrought_iron"], mats["warm_glow"]],
        col,
        parent=root,
    )

    # BellHinge motion_root at local (0.0, 0.0, 2.45)
    hinge_obj = _create_empty_obj(hinge_id, col, location=(0.0, 0.0, 2.45), parent=root)

    # Swinging bronze bell body (in hinge local coordinates z=-0.55..0.05)
    bbm = bmesh.new()
    buv = bbm.loops.layers.uv.new("UVMap")
    _add_box(bbm, buv, (-0.18, -0.08, -0.06), (0.18, 0.08, 0.06), material_index=1)
    _add_frustum_z(bbm, buv, (0.0, 0.0), -0.48, -0.06, 0.32, 0.15, segments=12, material_index=0)
    _add_frustum_z(bbm, buv, (0.0, 0.0), -0.56, -0.44, 0.07, 0.04, segments=8, material_index=0)
    bell_obj = _create_mesh_obj(
        bell_id,
        bbm,
        [mats["bell_bronze"], mats["wrought_iron"]],
        col,
        parent=hinge_obj,
    )

    # Sound/particle effect attachment_point mesh at local (0.0, 0.0, 2.15)
    pbm = bmesh.new()
    puv = pbm.loops.layers.uv.new("UVMap")
    _add_frustum_z(pbm, puv, (0.0, 0.0), -0.06, 0.06, 0.12, 0.12, segments=8, material_index=0)
    sound_obj = _create_mesh_obj(
        sound_id,
        pbm,
        [mats["eerie_glow"]],
        col,
        location=(0.0, 0.0, 2.15),
        parent=root,
    )

    return {
        "asset_id": asset_id,
        "category": "gimmick",
        "origin_policy": "ground_center",
        "root_obj": root,
        "all_objs": [root, stand_obj, hinge_obj, bell_obj, sound_obj],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": stand_id,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": hinge_id,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 2.45],
            },
            {
                "part_id": bell_id,
                "role": "visual_root",
                "parent_part": hinge_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": sound_id,
                "role": "attachment_point",
                "parent_part": asset_id,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, 0.0, 2.15],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [hinge_id],
            "visual_roots": [stand_id, bell_id],
            "attachment_points": [sound_id],
        },
        "is_placeholder": False,
        "future_target": None,
        "notes": "I04 Interactive Haunted Mansion Bell stand with X-axis swinging BellHinge (-28..+28 deg) at z=+2.45m and SoundPoint attachment slot.",
    }


def _deduplicate_imported_materials() -> None:
    """Remap any `.NNN` duplicate materials created during `append_common_part` to their canonical base material."""
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


def place_b_mansion_common_parts(
    col: bpy.types.Collection, common_blend_path: Path
) -> list[bpy.types.Object]:
    """Place reusable `CMN_*` common assets into `B_mansion` collection and deduplicate materials."""
    placed: list[bpy.types.Object] = []
    for cp in COMMON_PLACEMENTS:
        inst_obj = append_common_part(
            common_blend_path=common_blend_path,
            source_object_name=cp["common_asset_id"],
            instance_name=cp["instance_name"],
            collection=col,
            location=tuple(cp["position"]),
            rotation_euler_deg=tuple(cp["rotation_euler_deg"]),
        )
        placed.append(inst_obj)
    _deduplicate_imported_materials()
    return placed


def _measure_asset_entry(spec: dict[str, Any]) -> dict[str, Any]:
    """Measure triangles, vertices, materials, and local bounds from Blender scene objects."""
    bpy.context.view_layer.update()
    root_obj: bpy.types.Object = spec["root_obj"]
    all_objs: list[bpy.types.Object] = spec["all_objs"]
    inv_root = root_obj.matrix_world.inverted()

    tris = 0
    verts = 0
    mat_set: list[str] = []
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []

    for obj in all_objs:
        if obj.type == "MESH" and obj.data is not None:
            mesh = obj.data
            mesh.calc_loop_triangles()
            tris += len(mesh.loop_triangles)
            verts += len(mesh.vertices)
            for m in mesh.materials:
                if m is not None and m.name not in mat_set:
                    mat_set.append(m.name)
            for v in mesh.vertices:
                wpt = obj.matrix_world @ v.co
                lpt = inv_root @ wpt
                xs.append(float(lpt.x))
                ys.append(float(lpt.y))
                zs.append(float(lpt.z))

    bmin = [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)]
    bmax = [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)]
    width = round(max(0.01, bmax[0] - bmin[0]), 4)
    depth = round(max(0.01, bmax[1] - bmin[1]), 4)
    height = round(max(0.01, bmax[2] - bmin[2]), 4)

    return {
        "asset_id": spec["asset_id"],
        "key": KEY,
        "category": spec["category"],
        "area_id": KEY,
        "collection": KEY,
        "blend_file": BLEND_REL_PATH,
        "script_file": SCRIPT_REL_PATH,
        "origin_policy": spec["origin_policy"],
        "origin_world": [
            round(float(root_obj.location.x), 4),
            round(float(root_obj.location.y), 4),
            round(float(root_obj.location.z), 4),
        ],
        "dimensions_m": {
            "width": width,
            "depth": depth,
            "height": height,
        },
        "bounds_local": {
            "min": bmin,
            "max": bmax,
        },
        "parts": spec["parts"],
        "hierarchy": spec["hierarchy"],
        "materials": mat_set,
        "textures": [],
        "metrics": {
            "measured": True,
            "measurement_source": "blender_scene",
            "triangles": tris,
            "vertices": verts,
            "materials_count": len(mat_set),
            "objects_count": len(all_objs),
        },
        "export_result": {
            "status": "unexported",
            "bundle_dir": None,
            "apply_plan": None,
            "report_file": None,
        },
        "replacement": {
            "is_placeholder": spec["is_placeholder"],
            "modifiable": True,
            "notes": spec["notes"],
            "future_target": spec["future_target"],
        },
    }


def build_b_mansion() -> dict[str, Any]:
    """Build the `B_mansion` scene, render `review/B_mansion/`, save `B_mansion.blend`, and write layout/manifest JSONs."""
    common_blend_path = PROJECT_ROOT / COMMON_BLEND_REL_PATH
    if not common_blend_path.is_file():
        build_common()

    _scene, col = reset_scene(KEY, seed=303)
    mats = get_b_mansion_materials()

    asset_specs: list[dict[str, Any]] = [
        build_courtyard_ground(col, mats),
        build_front_gate(col, mats),
        build_dead_tree(1, (-7.2, 26.5, 1.5), 20.0, col, mats),
        build_dead_tree(2, (7.2, 26.5, 1.5), -25.0, col, mats),
        build_tilting_tombstone(1, (-6.2, 30.0, 1.5), 12.0, col, mats),
        build_tilting_tombstone(2, (6.2, 30.0, 1.5), -12.0, col, mats),
        build_static_tombstone(3, (-9.5, 32.5, 1.5), 18.0, col, mats),
        build_static_tombstone(4, (9.5, 32.5, 1.5), -18.0, col, mats),
        build_mansion_placeholder(col, mats),
        build_mansion_double_door(col, mats),
        build_entrance_hall(col, mats),
        build_window_ghost(1, (-4.2, 37.35, 4.8), col, mats),
        build_window_ghost(2, (4.2, 37.35, 4.8), col, mats),
        build_floating_ghost(1, (-4.6, 28.0, 2.6), 15.0, col, mats),
        build_floating_ghost(2, (4.6, 33.0, 2.8), -20.0, col, mats),
        build_mansion_bell(col, mats),
    ]

    placed_common = place_b_mansion_common_parts(col, common_blend_path)

    overview_png = PROJECT_ROOT / "review" / KEY / "01_mansion_courtyard_overview.png"
    facade_png = PROJECT_ROOT / "review" / KEY / "02_mansion_facade_and_doors.png"
    gimmicks_png = PROJECT_ROOT / "review" / KEY / "03_gimmicks_graveyard_and_bell.png"

    render_review_images(
        views=[
            {
                "filepath": overview_png,
                "location": (0.0, 15.5, 6.2),
                "target": (0.0, 36.0, 4.2),
                "lens_mm": 26.0,
            },
            {
                "filepath": facade_png,
                "location": (0.335, 31.8, 2.75),
                "target": (0.335, 40.0, 2.95),
                "lens_mm": 28.0,
            },
            {
                "filepath": gimmicks_png,
                "location": (-1.2, 23.8, 3.2),
                "target": (-5.8, 32.5, 2.5),
                "lens_mm": 28.0,
            },
        ],
        width=1280,
        height=720,
        samples=32,
    )

    blend_path = PROJECT_ROOT / BLEND_REL_PATH
    save_blend(blend_path, pack_images=True)

    area_layout_path = PROJECT_ROOT / AREA_LAYOUT_REL_PATH
    manifest_path = PROJECT_ROOT / MANIFEST_REL_PATH
    area_layout_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    area_layout_data = build_b_mansion_area_layout_dict()
    manifest_data: dict[str, Any] = {
        "schema_version": "1.0",
        "key": KEY,
        "updated_at": "2026-10-31T12:00:00Z",
        "assets": [_measure_asset_entry(spec) for spec in asset_specs],
    }

    area_layout_path.write_text(
        json.dumps(area_layout_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    summary = {
        "key": KEY,
        "blend_file": BLEND_REL_PATH,
        "objects_count": len(bpy.data.objects),
        "b_mansion_assets_count": len(asset_specs),
        "common_instances_count": len(placed_common),
        "meshes_count": len(bpy.data.meshes),
        "materials_count": len(bpy.data.materials),
        "review_images": [
            str(overview_png.relative_to(PROJECT_ROOT)),
            str(facade_png.relative_to(PROJECT_ROOT)),
            str(gimmicks_png.relative_to(PROJECT_ROOT)),
        ],
    }
    print("B_MANSION_BUILD_SUMMARY:" + json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    build_b_mansion()
