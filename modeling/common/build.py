"""Deterministically build `blender/common/common.blend`, render `review/common/`, and emit `assets/manifest/common.json`.

Run via:
    resoloop blender run modeling/common/build.py --json
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import bmesh  # type: ignore
import bpy  # type: ignore
from mathutils import Vector  # type: ignore

from modeling.lib.materials import create_pbr_material
from modeling.lib.render import render_review_images
from modeling.lib.scene import reset_scene, save_blend

KEY = "common"
BLEND_REL_PATH = "blender/common/common.blend"
SCRIPT_REL_PATH = "modeling/common/build.py"
MANIFEST_REL_PATH = "assets/manifest/common.json"


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
        [v000, v100, v101, v001],  # Front (-Y)
        [v110, v010, v011, v111],  # Back (+Y)
        [v010, v000, v001, v011],  # Left (-X)
        [v100, v110, v111, v101],  # Right (+X)
        [v001, v101, v111, v011],  # Top (+Z)
        [v010, v110, v100, v000],  # Bottom (-Z)
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
    segments: int = 8,
    material_index: int = 0,
    twist_rad: float = 0.0,
) -> None:
    """Add a vertical n-gon frustum/cylinder/cone from z0 (radius r0) to z1 (radius r1)."""
    cx, cy = center_xy
    ring0 = []
    ring1 = []
    for i in range(segments):
        a0 = 2.0 * math.pi * i / segments
        a1 = a0 + twist_rad
        ring0.append(bm.verts.new((cx + r0 * math.cos(a0), cy + r0 * math.sin(a0), z0)))
        if r1 > 1e-5:
            ring1.append(bm.verts.new((cx + r1 * math.cos(a1), cy + r1 * math.sin(a1), z1)))

    # Bottom cap
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
            u0 = i / segments
            u1 = (i + 1) / segments
            f_side.loops[0][uv_layer].uv = (u0, 0.0)
            f_side.loops[1][uv_layer].uv = (u1, 0.0)
            f_side.loops[2][uv_layer].uv = (0.5 * (u0 + u1), 1.0)
    else:
        for i in range(segments):
            jn = (i + 1) % segments
            f_side = bm.faces.new([ring0[i], ring0[jn], ring1[jn], ring1[i]])
            f_side.material_index = material_index
            u0 = i / segments
            u1 = (i + 1) / segments
            f_side.loops[0][uv_layer].uv = (u0, 0.0)
            f_side.loops[1][uv_layer].uv = (u1, 0.0)
            f_side.loops[2][uv_layer].uv = (u1, 1.0)
            f_side.loops[3][uv_layer].uv = (u0, 1.0)

        f_top = bm.faces.new(ring1)
        f_top.material_index = material_index
        for i, loop in enumerate(f_top.loops):
            ang = 2.0 * math.pi * i / segments
            loop[uv_layer].uv = (0.5 + 0.45 * math.cos(ang), 0.5 + 0.45 * math.sin(ang))


def _add_prism_quad(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    p0: tuple[float, float, float],
    p1: tuple[float, float, float],
    half_width_y: float,
    half_height_z: float,
    material_index: int = 0,
) -> None:
    """Add a rectangular bar connecting 3D points p0 and p1 (extruded in Y and Z)."""
    x0, y0, z0 = p0
    x1, y1, z1 = p1
    v000 = bm.verts.new((x0, y0 - half_width_y, z0 - half_height_z))
    v100 = bm.verts.new((x1, y1 - half_width_y, z1 - half_height_z))
    v110 = bm.verts.new((x1, y1 + half_width_y, z1 - half_height_z))
    v010 = bm.verts.new((x0, y0 + half_width_y, z0 - half_height_z))
    v001 = bm.verts.new((x0, y0 - half_width_y, z0 + half_height_z))
    v101 = bm.verts.new((x1, y1 - half_width_y, z1 + half_height_z))
    v111 = bm.verts.new((x1, y1 + half_width_y, z1 + half_height_z))
    v011 = bm.verts.new((x0, y0 + half_width_y, z0 + half_height_z))

    uv_quad = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    faces_spec = [
        [v000, v100, v101, v001],
        [v110, v010, v011, v111],
        [v010, v000, v001, v011],
        [v100, v110, v111, v101],
        [v001, v101, v111, v011],
        [v010, v110, v100, v000],
    ]
    for verts in faces_spec:
        f = bm.faces.new(verts)
        f.material_index = material_index
        for loop, uv in zip(f.loops, uv_quad):
            loop[uv_layer].uv = uv


def get_common_materials() -> dict[str, bpy.types.Material]:
    """Create or retrieve the shared PBR materials for `common` parts."""
    return {
        "iron": create_pbr_material(
            "MAT_CMN_WroughtIron",
            base_color=(0.14, 0.15, 0.18, 1.0),
            roughness=0.42,
            metallic=0.82,
        ),
        "stone": create_pbr_material(
            "MAT_CMN_WarmStone",
            base_color=(0.36, 0.33, 0.38, 1.0),
            roughness=0.78,
            metallic=0.05,
        ),
        "wood": create_pbr_material(
            "MAT_CMN_WarmWood",
            base_color=(0.38, 0.23, 0.13, 1.0),
            roughness=0.68,
            metallic=0.02,
        ),
        "glow": create_pbr_material(
            "MAT_CMN_AmberGlow",
            base_color=(1.0, 0.72, 0.22, 1.0),
            roughness=0.20,
            metallic=0.0,
            emission_color=(1.0, 0.62, 0.14, 1.0),
            emission_strength=4.5,
        ),
        "pumpkin": create_pbr_material(
            "MAT_CMN_PumpkinOrange",
            base_color=(0.92, 0.38, 0.06, 1.0),
            roughness=0.52,
            metallic=0.0,
        ),
        "stem": create_pbr_material(
            "MAT_CMN_PumpkinStem",
            base_color=(0.24, 0.30, 0.14, 1.0),
            roughness=0.76,
            metallic=0.0,
        ),
        "flag_purple": create_pbr_material(
            "MAT_CMN_FlagPurple",
            base_color=(0.44, 0.18, 0.64, 1.0),
            roughness=0.62,
            metallic=0.05,
        ),
        "flag_gold": create_pbr_material(
            "MAT_CMN_FlagGold",
            base_color=(0.95, 0.68, 0.14, 1.0),
            roughness=0.54,
            metallic=0.12,
        ),
    }


def build_street_lamp(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    location: tuple[float, float, float] = (-6.0, 0.0, 0.0),
) -> bpy.types.Object:
    """Create `CMN_StreetLamp_001`: 3.5m wrought-iron Halloween carnival streetlamp with glowing lantern."""
    mesh = bpy.data.meshes.new("CMN_StreetLamp_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material slots: 0=stone, 1=iron, 2=glow, 3=pumpkin
    # 1. Octagonal stone plinth base (z=0.0..0.42)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.0, 0.18, 0.28, 0.26, segments=8, material_index=0)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.18, 0.42, 0.24, 0.18, segments=8, material_index=0)

    # 2. Tapered iron post with decorative collars (z=0.42..3.15)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.42, 0.56, 0.15, 0.12, segments=8, material_index=1)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.56, 1.65, 0.085, 0.068, segments=8, material_index=1)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 1.65, 1.76, 0.105, 0.105, segments=8, material_index=1)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 1.76, 3.05, 0.064, 0.052, segments=8, material_index=1)
    # Post top spire (z=3.05..3.42)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 3.05, 3.16, 0.085, 0.075, segments=8, material_index=1)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 3.16, 3.42, 0.055, 0.0, segments=8, material_index=1)

    # 3. Curved scroll arm extending toward +X (x=0.0..0.48, z=2.70..3.18)
    arm_pts = [
        (0.04, 0.0, 2.78),
        (0.18, 0.0, 2.98),
        (0.34, 0.0, 3.10),
        (0.46, 0.0, 3.04),
    ]
    for p0, p1 in zip(arm_pts[:-1], arm_pts[1:]):
        _add_prism_quad(bm, uv_layer, p0, p1, half_width_y=0.025, half_height_z=0.028, material_index=1)
    # Lower scroll brace
    _add_prism_quad(bm, uv_layer, (0.05, 0.0, 2.48), (0.28, 0.0, 2.96), 0.018, 0.020, material_index=1)

    # 4. Hanging hexagonal lantern at x=0.46, y=0.0, z=2.28..2.98
    lx, ly = 0.46, 0.0
    # Hanging rod
    _add_frustum_z(bm, uv_layer, (lx, ly), 2.86, 3.04, 0.018, 0.018, segments=6, material_index=1)
    # Witch-hat lantern roof (z=2.70..2.90)
    _add_frustum_z(bm, uv_layer, (lx, ly), 2.70, 2.76, 0.21, 0.15, segments=6, material_index=1)
    _add_frustum_z(bm, uv_layer, (lx, ly), 2.76, 2.92, 0.14, 0.0, segments=6, material_index=1)
    # Glowing amber glass core (z=2.40..2.70)
    _add_frustum_z(bm, uv_layer, (lx, ly), 2.40, 2.70, 0.11, 0.14, segments=6, material_index=2)
    # Lantern bottom base & finial (z=2.24..2.40)
    _add_frustum_z(bm, uv_layer, (lx, ly), 2.34, 2.40, 0.09, 0.12, segments=6, material_index=1)
    _add_frustum_z(bm, uv_layer, (lx, ly), 2.22, 2.34, 0.0, 0.06, segments=6, material_index=1)

    # 5. Decorative mini pumpkin charm on opposite side (-X bracket, x=-0.18, z=2.62..2.80)
    _add_prism_quad(bm, uv_layer, (-0.04, 0.0, 2.82), (-0.18, 0.0, 2.82), 0.016, 0.018, material_index=1)
    _add_frustum_z(bm, uv_layer, (-0.18, 0.0), 2.62, 2.70, 0.05, 0.09, segments=8, material_index=3)
    _add_frustum_z(bm, uv_layer, (-0.18, 0.0), 2.70, 2.78, 0.09, 0.04, segments=8, material_index=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["stone"], mats["iron"], mats["glow"], mats["pumpkin"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("CMN_StreetLamp_001", mesh)
    obj.location = Vector(location)
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_fence(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    location: tuple[float, float, float] = (-3.2, 0.0, 0.0),
) -> bpy.types.Object:
    """Create `CMN_Fence_001`: 3.0m wide decorative stone-post & wrought-iron Halloween fence section."""
    mesh = bpy.data.meshes.new("CMN_Fence_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material slots: 0=stone, 1=iron, 2=pumpkin, 3=glow
    # 1. Low stone curb along span x=-1.50..+1.50 (z=0.0..0.16)
    _add_box(bm, uv_layer, (-1.50, -0.11, 0.0), (1.50, 0.11, 0.16), material_index=0)

    # 2. Left & Right stone end pillars at x=-1.38 and x=+1.38 (z=0.0..1.12)
    for px in (-1.38, 1.38):
        _add_box(bm, uv_layer, (px - 0.12, -0.14, 0.0), (px + 0.12, 0.14, 0.96), material_index=0)
        _add_box(bm, uv_layer, (px - 0.14, -0.15, 0.96), (px + 0.14, 0.15, 1.04), material_index=0)
        _add_frustum_z(bm, uv_layer, (px, 0.0), 1.04, 1.15, 0.11, 0.0, segments=4, material_index=1)

    # 3. Horizontal wrought-iron rails (lower z=0.26..0.31, upper z=0.86..0.91)
    _add_box(bm, uv_layer, (-1.26, -0.035, 0.26), (1.26, 0.035, 0.31), material_index=1)
    _add_box(bm, uv_layer, (-1.26, -0.035, 0.86), (1.26, 0.035, 0.91), material_index=1)

    # 4. Vertical iron pickets with spear tips across span
    picket_xs = [-1.08, -0.84, -0.60, -0.36, 0.36, 0.60, 0.84, 1.08]
    for vx in picket_xs:
        _add_box(bm, uv_layer, (vx - 0.02, -0.02, 0.16), (vx + 0.02, 0.02, 0.98), material_index=1)
        _add_frustum_z(bm, uv_layer, (vx, 0.0), 0.98, 1.09, 0.032, 0.0, segments=4, material_index=1)

    # 5. Center decorative iron ring & pumpkin medallion (x=-0.22..+0.22, z=0.42..0.82)
    _add_box(bm, uv_layer, (-0.18, -0.03, 0.16), (-0.14, 0.03, 0.96), material_index=1)
    _add_box(bm, uv_layer, (0.14, -0.03, 0.16), (0.18, 0.03, 0.96), material_index=1)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.48, 0.60, 0.08, 0.13, segments=8, material_index=2)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.60, 0.72, 0.13, 0.07, segments=8, material_index=2)
    # Glowing emblem eye band
    _add_box(bm, uv_layer, (-0.06, -0.135, 0.58), (0.06, 0.135, 0.63), material_index=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["stone"], mats["iron"], mats["pumpkin"], mats["glow"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("CMN_Fence_001", mesh)
    obj.location = Vector(location)
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_handrail(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    location: tuple[float, float, float] = (0.4, 0.0, 0.0),
) -> bpy.types.Object:
    """Create `CMN_Handrail_001`: 3.0m sturdy bridge/cliff safety handrail & balustrade (height 1.15m)."""
    mesh = bpy.data.meshes.new("CMN_Handrail_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material slots: 0=stone, 1=wood, 2=iron, 3=glow
    # 1. Continuous bottom safety curb (prevents stepping off edges, z=0.0..0.18)
    _add_box(bm, uv_layer, (-1.50, -0.12, 0.0), (1.50, 0.12, 0.18), material_index=0)

    # 2. End & center heavy support posts (x=-1.40, 0.0, +1.40, z=0.18..1.15)
    for px in (-1.40, 0.0, 1.40):
        _add_box(bm, uv_layer, (px - 0.09, -0.10, 0.18), (px + 0.09, 0.10, 1.08), material_index=1)
        _add_box(bm, uv_layer, (px - 0.10, -0.11, 1.08), (px + 0.10, 0.11, 1.15), material_index=2)

    # 3. Heavy top handrail beam (z=0.98..1.08) and mid safety rail (z=0.54..0.62)
    _add_box(bm, uv_layer, (-1.50, -0.08, 0.98), (1.50, 0.08, 1.08), material_index=1)
    _add_box(bm, uv_layer, (-1.40, -0.05, 0.54), (1.40, 0.05, 0.62), material_index=2)

    # 4. Closely spaced vertical safety balusters (every 0.28m)
    baluster_xs = [-1.12, -0.84, -0.56, -0.28, 0.28, 0.56, 0.84, 1.12]
    for bx in baluster_xs:
        _add_box(bm, uv_layer, (bx - 0.025, -0.03, 0.18), (bx + 0.025, 0.03, 0.98), material_index=2)

    # 5. Embedded amber safety reflector strips on center post
    _add_box(bm, uv_layer, (-0.05, -0.105, 0.78), (0.05, 0.105, 0.88), material_index=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["stone"], mats["wood"], mats["iron"], mats["glow"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("CMN_Handrail_001", mesh)
    obj.location = Vector(location)
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_garland_flag(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    location: tuple[float, float, float] = (4.2, 0.0, 0.0),
) -> bpy.types.Object:
    """Create `CMN_GarlandFlag_001`: 3.6m festive carnival twin-pole pennant garland & hanging lanterns."""
    mesh = bpy.data.meshes.new("CMN_GarlandFlag_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material slots: 0=iron, 1=flag_purple, 2=flag_gold, 3=pumpkin, 4=glow
    # 1. Twin iron poles at x=-1.70 and x=+1.70 (z=0.0..3.20)
    for px in (-1.70, 1.70):
        _add_frustum_z(bm, uv_layer, (px, 0.0), 0.0, 0.22, 0.15, 0.12, segments=8, material_index=0)
        _add_frustum_z(bm, uv_layer, (px, 0.0), 0.22, 3.05, 0.055, 0.042, segments=8, material_index=0)
        _add_frustum_z(bm, uv_layer, (px, 0.0), 3.05, 3.20, 0.07, 0.0, segments=8, material_index=0)

    # 2. Catenary garland rope from (-1.70, 0, 2.96) sagging to (0.0, 0, 2.56) and back to (+1.70, 0, 2.96)
    rope_segments = 12
    rope_pts: list[tuple[float, float, float]] = []
    for i in range(rope_segments + 1):
        t = -1.0 + 2.0 * i / rope_segments
        rx = 1.70 * t
        rz = 2.56 + 0.40 * (t * t)
        rope_pts.append((rx, 0.0, rz))

    for p0, p1 in zip(rope_pts[:-1], rope_pts[1:]):
        _add_prism_quad(bm, uv_layer, p0, p1, half_width_y=0.015, half_height_z=0.015, material_index=0)

    # 3. Triangular pennant flags along each rope segment (alternating purple, gold, orange)
    flag_mats = [1, 2, 3]
    for i in range(rope_segments):
        p0 = rope_pts[i]
        p1 = rope_pts[i + 1]
        mx = 0.5 * (p0[0] + p1[0])
        mz = 0.5 * (p0[2] + p1[2]) - 0.26
        mat_idx = flag_mats[i % len(flag_mats)]
        # Small double-sided prism pennant
        v_tl_f = bm.verts.new((p0[0] + 0.02, -0.015, p0[2] - 0.01))
        v_tr_f = bm.verts.new((p1[0] - 0.02, -0.015, p1[2] - 0.01))
        v_tip_f = bm.verts.new((mx, -0.015, mz))
        v_tl_b = bm.verts.new((p0[0] + 0.02, 0.015, p0[2] - 0.01))
        v_tr_b = bm.verts.new((p1[0] - 0.02, 0.015, p1[2] - 0.01))
        v_tip_b = bm.verts.new((mx, 0.015, mz))

        for tri_verts in (
            [v_tl_f, v_tr_f, v_tip_f],
            [v_tr_b, v_tl_b, v_tip_b],
        ):
            f = bm.faces.new(tri_verts)
            f.material_index = mat_idx
            f.loops[0][uv_layer].uv = (0.0, 1.0)
            f.loops[1][uv_layer].uv = (1.0, 1.0)
            f.loops[2][uv_layer].uv = (0.5, 0.0)

        for side_verts in (
            [v_tl_b, v_tr_b, v_tr_f, v_tl_f],
            [v_tr_f, v_tr_b, v_tip_b, v_tip_f],
            [v_tip_f, v_tip_b, v_tl_b, v_tl_f],
        ):
            f = bm.faces.new(side_verts)
            f.material_index = mat_idx
            for loop, uv in zip(f.loops, [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]):
                loop[uv_layer].uv = uv

    # 4. Three glowing carnival paper lanterns suspended at t=-0.5, 0.0, +0.5
    for lx, lz in ((-0.85, 2.66), (0.0, 2.56), (0.85, 2.66)):
        _add_frustum_z(bm, uv_layer, (lx, 0.0), lz - 0.22, lz - 0.12, 0.06, 0.10, segments=8, material_index=4)
        _add_frustum_z(bm, uv_layer, (lx, 0.0), lz - 0.12, lz - 0.02, 0.10, 0.06, segments=8, material_index=4)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["iron"], mats["flag_purple"], mats["flag_gold"], mats["pumpkin"], mats["glow"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("CMN_GarlandFlag_001", mesh)
    obj.location = Vector(location)
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_bench(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    location: tuple[float, float, float] = (-4.2, -2.5, 0.0),
) -> bpy.types.Object:
    """Create `CMN_Bench_001`: 1.8m carnival park bench with wrought-iron frame and wooden slats."""
    mesh = bpy.data.meshes.new("CMN_Bench_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material slots: 0=iron, 1=wood, 2=pumpkin
    # 1. Three wrought-iron leg frames at x=-0.80, 0.0, +0.80
    for lx in (-0.80, 0.0, 0.80):
        # Front leg (-Y) and rear leg (+Y)
        _add_box(bm, uv_layer, (lx - 0.035, -0.28, 0.0), (lx + 0.035, -0.20, 0.44), material_index=0)
        _add_box(bm, uv_layer, (lx - 0.035, 0.18, 0.0), (lx + 0.035, 0.26, 0.86), material_index=0)
        # Under-seat crossbar
        _add_box(bm, uv_layer, (lx - 0.03, -0.26, 0.38), (lx + 0.03, 0.24, 0.44), material_index=0)
        # Armrest on outer frames
        if abs(lx) > 0.5:
            _add_box(bm, uv_layer, (lx - 0.04, -0.26, 0.44), (lx + 0.04, -0.18, 0.62), material_index=0)
            _add_box(bm, uv_layer, (lx - 0.045, -0.27, 0.60), (lx + 0.045, 0.22, 0.65), material_index=0)

    # 2. Wooden seat slats (4 slats across y=-0.26..+0.16, z=0.44..0.48)
    for sy in (-0.23, -0.11, 0.01, 0.13):
        _add_box(bm, uv_layer, (-0.88, sy - 0.045, 0.44), (0.88, sy + 0.045, 0.48), material_index=1)

    # 3. Wooden backrest slats (3 slats at y=0.20..0.24, z=0.54..0.84)
    for sz in (0.56, 0.68, 0.80):
        _add_box(bm, uv_layer, (-0.88, 0.19, sz - 0.04), (0.88, 0.23, sz + 0.04), material_index=1)

    # 4. Small decorative pumpkin finial on top center of backrest
    _add_frustum_z(bm, uv_layer, (0.0, 0.21), 0.84, 0.90, 0.06, 0.08, segments=8, material_index=2)
    _add_frustum_z(bm, uv_layer, (0.0, 0.21), 0.90, 0.95, 0.08, 0.03, segments=8, material_index=2)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["iron"], mats["wood"], mats["pumpkin"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("CMN_Bench_001", mesh)
    obj.location = Vector(location)
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_lantern(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    location: tuple[float, float, float] = (-1.2, -2.5, 0.0),
) -> bpy.types.Object:
    """Create `CMN_Lantern_001`: 0.78m hexagonal glowing Halloween lantern with witch-hat cap."""
    mesh = bpy.data.meshes.new("CMN_Lantern_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material slots: 0=iron, 1=glow
    # 1. Hexagonal base foot (z=0.0..0.12)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.0, 0.06, 0.20, 0.17, segments=6, material_index=0)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.06, 0.12, 0.15, 0.18, segments=6, material_index=0)
    # 2. Glowing hexagonal glass core (z=0.12..0.46)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.12, 0.46, 0.14, 0.17, segments=6, material_index=1)
    # 3. Witch-hat brim & pointed roof (z=0.46..0.72)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.46, 0.52, 0.24, 0.16, segments=6, material_index=0)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.52, 0.72, 0.15, 0.02, segments=6, material_index=0)
    # 4. Top hanging loop block (z=0.72..0.78)
    _add_box(bm, uv_layer, (-0.04, -0.02, 0.72), (0.04, 0.02, 0.78), material_index=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["iron"], mats["glow"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("CMN_Lantern_001", mesh)
    obj.location = Vector(location)
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_small_pumpkin(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    location: tuple[float, float, float] = (1.2, -2.5, 0.0),
) -> bpy.types.Object:
    """Create `CMN_SmallPumpkin_001`: 0.65m ribbed Jack-o'-Lantern pumpkin with stem and glowing face."""
    mesh = bpy.data.meshes.new("CMN_SmallPumpkin_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material slots: 0=pumpkin, 1=stem, 2=glow
    # 1. Ribbed pumpkin body built from 16 radial segments with alternating outer/inner furrow radii
    segs = 16
    z_levels = [
        (0.0, 0.14),
        (0.08, 0.27),
        (0.24, 0.32),
        (0.38, 0.28),
        (0.48, 0.15),
    ]
    rings: list[list[bmesh.types.BMVert]] = []
    for z, base_r in z_levels:
        ring: list[bmesh.types.BMVert] = []
        for i in range(segs):
            ang = 2.0 * math.pi * i / segs
            rib_scale = 1.04 if (i % 2 == 0) else 0.91
            r = base_r * rib_scale
            ring.append(bm.verts.new((r * math.cos(ang), r * math.sin(ang), z)))
        rings.append(ring)

    # Bottom cap
    f_bot = bm.faces.new(list(reversed(rings[0])))
    f_bot.material_index = 0
    for i, loop in enumerate(f_bot.loops):
        ang = 2.0 * math.pi * i / segs
        loop[uv_layer].uv = (0.5 + 0.45 * math.cos(ang), 0.5 + 0.45 * math.sin(ang))

    # Side bands
    for r_idx in range(len(rings) - 1):
        r0 = rings[r_idx]
        r1 = rings[r_idx + 1]
        v0 = r_idx / (len(rings) - 1)
        v1 = (r_idx + 1) / (len(rings) - 1)
        for i in range(segs):
            jn = (i + 1) % segs
            f_side = bm.faces.new([r0[i], r0[jn], r1[jn], r1[i]])
            f_side.material_index = 0
            u0 = i / segs
            u1 = (i + 1) / segs
            f_side.loops[0][uv_layer].uv = (u0, v0)
            f_side.loops[1][uv_layer].uv = (u1, v0)
            f_side.loops[2][uv_layer].uv = (u1, v1)
            f_side.loops[3][uv_layer].uv = (u0, v1)

    # Top cap
    f_top = bm.faces.new(rings[-1])
    f_top.material_index = 0
    for i, loop in enumerate(f_top.loops):
        ang = 2.0 * math.pi * i / segs
        loop[uv_layer].uv = (0.5 + 0.45 * math.cos(ang), 0.5 + 0.45 * math.sin(ang))

    # 2. Twisted woody stem on top (z=0.47..0.64)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.47, 0.56, 0.075, 0.048, segments=6, material_index=1, twist_rad=0.25)
    _add_frustum_z(bm, uv_layer, (0.02, 0.01), 0.56, 0.64, 0.048, 0.024, segments=6, material_index=1, twist_rad=0.35)

    # 3. Glowing Jack-o'-Lantern face features on the front (-Y) side
    # Left & Right triangular eyes
    for ex0, ex1 in ((-0.15, -0.05), (0.05, 0.15)):
        em = 0.5 * (ex0 + ex1)
        vf0 = bm.verts.new((ex0, -0.295, 0.27))
        vf1 = bm.verts.new((ex1, -0.295, 0.27))
        vf2 = bm.verts.new((em, -0.285, 0.37))
        vb0 = bm.verts.new((ex0, -0.25, 0.27))
        vb1 = bm.verts.new((ex1, -0.25, 0.27))
        vb2 = bm.verts.new((em, -0.25, 0.37))
        for tri in ([vf0, vf1, vf2], [vb1, vb0, vb2]):
            f = bm.faces.new(tri)
            f.material_index = 2
            f.loops[0][uv_layer].uv = (0.0, 0.0)
            f.loops[1][uv_layer].uv = (1.0, 0.0)
            f.loops[2][uv_layer].uv = (0.5, 1.0)
        for q in ([vb0, vb1, vf1, vf0], [vf1, vb1, vb2, vf2], [vf2, vb2, vb0, vf0]):
            f = bm.faces.new(q)
            f.material_index = 2
            for loop, uv in zip(f.loops, [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]):
                loop[uv_layer].uv = uv

    # Nose
    _add_box(bm, uv_layer, (-0.032, -0.312, 0.21), (0.032, -0.26, 0.26), material_index=2)
    # Grinning mouth (center + raised corners)
    _add_box(bm, uv_layer, (-0.13, -0.302, 0.12), (0.13, -0.25, 0.165), material_index=2)
    _add_box(bm, uv_layer, (-0.18, -0.288, 0.145), (-0.12, -0.24, 0.19), material_index=2)
    _add_box(bm, uv_layer, (0.12, -0.288, 0.145), (0.18, -0.24, 0.19), material_index=2)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["pumpkin"], mats["stem"], mats["glow"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("CMN_SmallPumpkin_001", mesh)
    obj.location = Vector(location)
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


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


def _make_manifest_entry(obj: bpy.types.Object, category: str, notes: str) -> dict[str, Any]:
    tris, verts = _count_mesh_stats([obj])
    bounds = _compute_local_bounds([obj], obj.location)
    bmin = bounds["min"]
    bmax = bounds["max"]
    width = round(max(0.01, bmax[0] - bmin[0]), 4)
    depth = round(max(0.01, bmax[1] - bmin[1]), 4)
    height = round(max(0.01, bmax[2] - bmin[2]), 4)
    mat_names = [m.name for m in obj.data.materials if m is not None]

    return {
        "asset_id": obj.name,
        "key": KEY,
        "category": category,
        "area_id": "common",
        "collection": KEY,
        "blend_file": BLEND_REL_PATH,
        "script_file": SCRIPT_REL_PATH,
        "origin_policy": "ground_center",
        "origin_world": [
            round(float(obj.location.x), 4),
            round(float(obj.location.y), 4),
            round(float(obj.location.z), 4),
        ],
        "dimensions_m": {
            "width": width,
            "depth": depth,
            "height": height,
        },
        "bounds_local": bounds,
        "parts": [
            {
                "part_id": obj.name,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            }
        ],
        "hierarchy": {
            "asset_root": obj.name,
            "motion_roots": [],
            "visual_roots": [obj.name],
            "attachment_points": [],
        },
        "materials": mat_names,
        "textures": [],
        "metrics": {
            "measured": True,
            "measurement_source": "blender_scene",
            "triangles": tris,
            "vertices": verts,
            "materials_count": len(mat_names),
            "objects_count": 1,
        },
        "export_result": {
            "status": "unexported",
            "bundle_dir": None,
            "apply_plan": None,
            "report_file": None,
        },
        "replacement": {
            "is_placeholder": False,
            "modifiable": True,
            "notes": notes,
            "future_target": None,
        },
    }


def write_common_manifest(
    root: Path,
    objects_with_meta: list[tuple[bpy.types.Object, str, str]],
) -> None:
    """Write `assets/manifest/common.json` from measured Blender scene objects."""
    manifest_path = root / MANIFEST_REL_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_data: dict[str, Any] = {
        "schema_version": "1.0",
        "key": KEY,
        "updated_at": "2026-10-31T09:00:00Z",
        "assets": [_make_manifest_entry(obj, cat, notes) for obj, cat, notes in objects_with_meta],
    }
    manifest_path.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_common() -> dict[str, Any]:
    """Build all common parts, render review images, save `blender/common/common.blend`, and write `assets/manifest/common.json`."""
    _scene, common_col = reset_scene(KEY, seed=101)
    mats = get_common_materials()

    lamp_obj = build_street_lamp(common_col, mats, location=(-6.0, 0.0, 0.0))
    fence_obj = build_fence(common_col, mats, location=(-3.2, 0.0, 0.0))
    rail_obj = build_handrail(common_col, mats, location=(0.4, 0.0, 0.0))
    garland_obj = build_garland_flag(common_col, mats, location=(4.2, 0.0, 0.0))
    bench_obj = build_bench(common_col, mats, location=(-4.2, -2.5, 0.0))
    lantern_obj = build_lantern(common_col, mats, location=(-1.2, -2.5, 0.0))
    pumpkin_obj = build_small_pumpkin(common_col, mats, location=(1.2, -2.5, 0.0))

    objects_with_meta = [
        (
            lamp_obj,
            "lighting",
            "Reusable wrought-iron Halloween carnival streetlamp (1 object, ground_center origin at z=0.0). Append via append_common_part(..., 'CMN_StreetLamp_001', ...).",
        ),
        (
            fence_obj,
            "architecture",
            "Reusable 3.0m decorative wrought-iron & stone-post fence section along X axis (ground_center origin at z=0.0).",
        ),
        (
            rail_obj,
            "architecture",
            "Reusable 3.0m sturdy bridge & cliff safety handrail/balustrade section along X axis (height 1.15m, ground_center origin at z=0.0).",
        ),
        (
            garland_obj,
            "prop",
            "Reusable 3.6m festive carnival twin-pole pennant garland & hanging lanterns along X axis (ground_center origin at z=0.0).",
        ),
        (
            bench_obj,
            "prop",
            "Reusable 1.8m carnival park bench with iron armrests and wooden slats (ground_center origin at z=0.0).",
        ),
        (
            lantern_obj,
            "lighting",
            "Reusable 0.78m hexagonal glowing Halloween lantern with witch-hat cap (ground_center origin at z=0.0).",
        ),
        (
            pumpkin_obj,
            "prop",
            "Reusable 0.64m ribbed Jack-o'-Lantern small pumpkin prop facing -Y (ground_center origin at z=0.0).",
        ),
    ]

    lineup_png = PROJECT_ROOT / "review" / "common" / "01_common_lineup.png"
    detail_png = PROJECT_ROOT / "review" / "common" / "02_common_detail.png"

    render_review_images(
        views=[
            {
                "filepath": lineup_png,
                "location": (-0.6, -10.5, 4.2),
                "target": (-0.5, -0.8, 1.3),
                "lens_mm": 30.0,
            },
            {
                "filepath": detail_png,
                "location": (-1.5, -6.2, 1.6),
                "target": (-1.2, -2.0, 0.55),
                "lens_mm": 32.0,
            },
        ],
        width=1280,
        height=720,
        samples=32,
    )

    blend_path = PROJECT_ROOT / BLEND_REL_PATH
    save_blend(blend_path, pack_images=True)

    write_common_manifest(PROJECT_ROOT, objects_with_meta)

    summary = {
        "key": KEY,
        "blend_file": BLEND_REL_PATH,
        "objects_count": len(bpy.data.objects),
        "object_names": sorted(o.name for o in bpy.data.objects),
        "meshes_count": len(bpy.data.meshes),
        "materials_count": len(bpy.data.materials),
        "review_images": [
            str(lineup_png.relative_to(PROJECT_ROOT)),
            str(detail_png.relative_to(PROJECT_ROOT)),
        ],
    }
    print("COMMON_BUILD_SUMMARY:" + json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    build_common()
