"""Deterministically build `blender/C_candy/C_candy.blend`, render `review/C_candy/`,
and emit `layout/areas/C_candy.json` and `assets/manifest/C_candy.json`.

Run via:
    resoloop blender run modeling/C_candy/build.py --json
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

from modeling.lib.common_parts import append_common_part
from modeling.lib.materials import create_pbr_material
from modeling.lib.primitives import create_empty
from modeling.lib.render import render_review_images
from modeling.lib.scene import reset_scene, save_blend

KEY = "C_candy"
AREA_ID = "C_candy"
BLEND_REL_PATH = "blender/C_candy/C_candy.blend"
SCRIPT_REL_PATH = "modeling/C_candy/build.py"
MANIFEST_REL_PATH = "assets/manifest/C_candy.json"
AREA_LAYOUT_REL_PATH = "layout/areas/C_candy.json"
UPDATED_AT = "2026-10-31T12:00:00Z"


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


def _add_frustum_x(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    center_yz: tuple[float, float],
    x0: float,
    x1: float,
    r0: float,
    r1: float,
    segments: int = 8,
    material_index: int = 0,
) -> None:
    """Add a horizontal cylinder/frustum along the X axis from x0 to x1."""
    cy, cz = center_yz
    ring0 = []
    ring1 = []
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        ring0.append(bm.verts.new((x0, cy + r0 * math.cos(a), cz + r0 * math.sin(a))))
        ring1.append(bm.verts.new((x1, cy + r1 * math.cos(a), cz + r1 * math.sin(a))))

    f0 = bm.faces.new(list(reversed(ring0)))
    f0.material_index = material_index
    for i, loop in enumerate(f0.loops):
        ang = 2.0 * math.pi * i / segments
        loop[uv_layer].uv = (0.5 + 0.45 * math.cos(ang), 0.5 + 0.45 * math.sin(ang))

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

    f1 = bm.faces.new(ring1)
    f1.material_index = material_index
    for i, loop in enumerate(f1.loops):
        ang = 2.0 * math.pi * i / segments
        loop[uv_layer].uv = (0.5 + 0.45 * math.cos(ang), 0.5 + 0.45 * math.sin(ang))


def _add_prism_bar(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    p0: tuple[float, float, float],
    p1: tuple[float, float, float],
    half_width: float,
    half_height: float,
    material_index: int = 0,
) -> None:
    """Add a 3D rectangular bar connecting p0 and p1."""
    v0 = Vector(p0)
    v1 = Vector(p1)
    chord = v1 - v0
    if chord.length < 1e-5:
        return
    tangent = chord.normalized()
    up_ref = Vector((0.0, 0.0, 1.0)) if abs(tangent.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    side = tangent.cross(up_ref).normalized()
    up = side.cross(tangent).normalized()

    s_vec = side * half_width
    u_vec = up * half_height

    a0 = bm.verts.new(tuple(v0 - s_vec - u_vec))
    a1 = bm.verts.new(tuple(v0 + s_vec - u_vec))
    a2 = bm.verts.new(tuple(v0 + s_vec + u_vec))
    a3 = bm.verts.new(tuple(v0 - s_vec + u_vec))

    b0 = bm.verts.new(tuple(v1 - s_vec - u_vec))
    b1 = bm.verts.new(tuple(v1 + s_vec - u_vec))
    b2 = bm.verts.new(tuple(v1 + s_vec + u_vec))
    b3 = bm.verts.new(tuple(v1 - s_vec + u_vec))

    uv_quad = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    for verts in [
        [a0, a1, b1, b0],
        [a1, a2, b2, b1],
        [a2, a3, b3, b2],
        [a3, a0, b0, b3],
        [a3, a2, a1, a0],
        [b0, b1, b2, b3],
    ]:
        f = bm.faces.new(verts)
        f.material_index = material_index
        for loop, uv in zip(f.loops, uv_quad):
            loop[uv_layer].uv = uv


def _create_socket_marker_mesh(
    name: str,
    collection: bpy.types.Collection,
    location: tuple[float, float, float],
    mat: bpy.types.Material,
    parent: bpy.types.Object | None = None,
    radius: float = 0.05,
) -> bpy.types.Object:
    """Create a small diamond/octahedron marker mesh with local origin at (0,0,0) for attachment_point preservation."""
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), -radius, 0.0, 0.008, radius, segments=6, material_index=0)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.0, radius, radius, 0.0, segments=6, material_index=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    mesh.materials.append(mat)

    obj = bpy.data.objects.new(name, mesh)
    obj.location = Vector(location)
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def get_candy_materials() -> dict[str, bpy.types.Material]:
    """Create or retrieve all `MAT_CCD_*` PBR materials for Area C."""
    return {
        "cobble_choc": create_pbr_material(
            "MAT_CCD_ChocolateCobble",
            base_color=(0.24, 0.15, 0.18, 1.0),
            roughness=0.74,
            metallic=0.04,
        ),
        "cobble_sugar": create_pbr_material(
            "MAT_CCD_SugarStone",
            base_color=(0.48, 0.36, 0.46, 1.0),
            roughness=0.68,
            metallic=0.04,
        ),
        "candy_red": create_pbr_material(
            "MAT_CCD_CandyRuby",
            base_color=(0.88, 0.16, 0.34, 1.0),
            roughness=0.32,
            metallic=0.08,
        ),
        "candy_cream": create_pbr_material(
            "MAT_CCD_FrostingCream",
            base_color=(0.96, 0.90, 0.82, 1.0),
            roughness=0.40,
            metallic=0.02,
        ),
        "candy_mint": create_pbr_material(
            "MAT_CCD_PeppermintTeal",
            base_color=(0.22, 0.78, 0.68, 1.0),
            roughness=0.35,
            metallic=0.06,
        ),
        "gingerbread": create_pbr_material(
            "MAT_CCD_GingerbreadWall",
            base_color=(0.56, 0.32, 0.16, 1.0),
            roughness=0.66,
            metallic=0.02,
        ),
        "dark_wood": create_pbr_material(
            "MAT_CCD_WitchTimber",
            base_color=(0.22, 0.13, 0.11, 1.0),
            roughness=0.64,
            metallic=0.04,
        ),
        "witch_roof": create_pbr_material(
            "MAT_CCD_WitchPlumRoof",
            base_color=(0.28, 0.14, 0.38, 1.0),
            roughness=0.58,
            metallic=0.08,
        ),
        "cauldron_iron": create_pbr_material(
            "MAT_CCD_CauldronIron",
            base_color=(0.14, 0.15, 0.18, 1.0),
            roughness=0.42,
            metallic=0.85,
        ),
        "brass_gear": create_pbr_material(
            "MAT_CCD_CarnivalBrass",
            base_color=(0.86, 0.64, 0.22, 1.0),
            roughness=0.30,
            metallic=0.88,
        ),
        "straw_gold": create_pbr_material(
            "MAT_CCD_BroomStraw",
            base_color=(0.78, 0.58, 0.22, 1.0),
            roughness=0.72,
            metallic=0.02,
        ),
        "amber_window": create_pbr_material(
            "MAT_CCD_WarmWindowGlow",
            base_color=(1.0, 0.74, 0.24, 1.0),
            roughness=0.18,
            metallic=0.0,
            emission_color=(1.0, 0.64, 0.16, 1.0),
            emission_strength=4.2,
        ),
        "potion_emerald": create_pbr_material(
            "MAT_CCD_PotionEmeraldGlow",
            base_color=(0.18, 0.96, 0.52, 1.0),
            roughness=0.15,
            metallic=0.0,
            emission_color=(0.16, 0.92, 0.48, 1.0),
            emission_strength=5.0,
        ),
        "potion_magenta": create_pbr_material(
            "MAT_CCD_PotionMagentaGlow",
            base_color=(0.96, 0.24, 0.78, 1.0),
            roughness=0.16,
            metallic=0.0,
            emission_color=(0.94, 0.20, 0.76, 1.0),
            emission_strength=4.6,
        ),
        "starlight_cyan": create_pbr_material(
            "MAT_CCD_StarlightTrailGlow",
            base_color=(0.42, 0.86, 1.0, 1.0),
            roughness=0.15,
            metallic=0.1,
            emission_color=(0.36, 0.80, 1.0, 1.0),
            emission_strength=4.8,
        ),
        "pumpkin_orange": create_pbr_material(
            "MAT_CCD_CandyPumpkin",
            base_color=(0.94, 0.42, 0.08, 1.0),
            roughness=0.46,
            metallic=0.02,
        ),
    }


def build_candy_street_paving(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `CCD_CandyStreetPaving_001` at (33.0, 0.0, 0.0) covering the main street, forecourt, and N/S paths."""
    mesh = bpy.data.meshes.new("CCD_CandyStreetPaving_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material slots:
    # 0=cobble_choc, 1=cobble_sugar, 2=candy_red, 3=candy_cream, 4=candy_mint
    # Local coordinates relative to origin (33.0, 0.0, 0.0):
    # World x=20..35.3 -> local x=-13.0..+2.3
    # 1. Main East-West candy cobblestone street (local x=-13.0..+2.3, y=-2.2..+2.2, z=0.0..0.04)
    _add_box(bm, uv_layer, (-13.0, -2.2, 0.0), (2.3, 2.2, 0.04), material_index=0)
    # Decorative pastel stepping tiles along the center of the street (z=0.04..0.055)
    for i in range(10):
        tx0 = -12.6 + i * 1.45
        tx1 = tx0 + 1.05
        mat_idx = 1 if i % 2 == 0 else 3
        _add_box(bm, uv_layer, (tx0, -1.35, 0.04), (tx1, 1.35, 0.055), material_index=mat_idx)

    # 2. Workshop Forecourt Plaza (world x=28.0..35.3 -> local x=-5.0..+2.3, y=-4.4..+4.4, z=0.0..0.04)
    _add_box(bm, uv_layer, (-5.0, -4.4, 0.0), (2.3, 4.4, 0.038), material_index=1)
    # Central peppermint medallion inlay at forecourt origin (0.0, 0.0) (z=0.038..0.06)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.038, 0.056, 1.85, 1.85, segments=16, material_index=3)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.056, 0.064, 1.30, 1.30, segments=12, material_index=2)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.064, 0.070, 0.65, 0.65, segments=10, material_index=4)

    # 3. North & South Stall Promenades (world x=24.2..34.8 -> local x=-8.8..+1.8, y=±2.2..±4.5)
    _add_box(bm, uv_layer, (-8.8, 2.2, 0.0), (1.8, 4.5, 0.035), material_index=0)
    _add_box(bm, uv_layer, (-8.8, -4.5, 0.0), (1.8, -2.2, 0.035), material_index=0)

    # 4. North Side Path to Conn_C_North_Side ([22.0, 16.0, 0.0], w=2.6m)
    # World x=20.7..23.3 -> local x=-12.3..-9.7, y=2.2..16.0
    _add_box(bm, uv_layer, (-12.3, 2.2, 0.0), (-9.7, 16.0, 0.035), material_index=1)
    _add_box(bm, uv_layer, (-10.2, 2.2, 0.0), (-8.4, 4.5, 0.035), material_index=1)

    # 5. South Side Path to Conn_C_South_Side ([22.0, -16.0, 0.0], w=2.6m)
    # World x=20.7..23.3 -> local x=-12.3..-9.7, y=-16.0..-2.2
    _add_box(bm, uv_layer, (-12.3, -16.0, 0.0), (-9.7, -2.2, 0.035), material_index=1)
    _add_box(bm, uv_layer, (-10.2, -4.5, 0.0), (-8.4, -2.2, 0.035), material_index=1)

    # 6. Candy-striped curbstones along outer street edges (outside the 4.0m main corridor y=-2.0..2.0)
    for idx in range(8):
        cx0 = -8.6 + idx * 1.30
        cx1 = cx0 + 1.10
        cmat = 2 if idx % 2 == 0 else 3
        _add_box(bm, uv_layer, (cx0, 4.45, 0.0), (cx1, 4.68, 0.14), material_index=cmat)
        _add_box(bm, uv_layer, (cx0, -4.68, 0.0), (cx1, -4.45, 0.14), material_index=cmat)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (
        mats["cobble_choc"],
        mats["cobble_sugar"],
        mats["candy_red"],
        mats["candy_cream"],
        mats["candy_mint"],
    ):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("CCD_CandyStreetPaving_001", mesh)
    obj.location = Vector((33.0, 0.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_candy_arch(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `CCD_CandyArch_001` (landmark `LM_C_CandyArch_001`) at (33.0, 0.0, 0.0), height 9.5m.

    Spans across the main street with pillars at y = ±3.2m (clear inner opening 5.4m > 4.0m road width)
    and arch beam above z = 5.8m so sightline `LOS_CentralPlaza_To_EastCandy` ([12,0,1.7]->[33,0,5.5])
    passes cleanly into the arch crown and frames the workshop behind it.
    """
    mesh = bpy.data.meshes.new("CCD_CandyArch_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material slots:
    # 0=gingerbread, 1=candy_red, 2=candy_cream, 3=candy_mint, 4=witch_roof, 5=amber_window, 6=pumpkin_orange, 7=dark_wood
    for side_sign in (-1.0, 1.0):
        py = side_sign * 3.20
        # Biscuit & chocolate octagonal plinth base (z=0.0..0.85, radius <= 0.50 so inner y is ±2.70m)
        _add_frustum_z(bm, uv_layer, (0.0, py), 0.0, 0.45, 0.50, 0.46, segments=8, material_index=0)
        _add_frustum_z(bm, uv_layer, (0.0, py), 0.45, 0.85, 0.44, 0.36, segments=8, material_index=2)

        # Stacked twisted candy-cane column drums (z=0.85..5.80)
        drum_count = 10
        z_step = (5.80 - 0.85) / drum_count
        for d in range(drum_count):
            dz0 = 0.85 + d * z_step
            dz1 = dz0 + z_step
            d_mat = 1 if d % 2 == 0 else 2
            _add_frustum_z(
                bm,
                uv_layer,
                (0.0, py),
                dz0,
                dz1,
                0.28,
                0.28,
                segments=10,
                material_index=d_mat,
                twist_rad=0.28 * side_sign,
            )

        # Frosted capital collar (z=5.80..6.20)
        _add_frustum_z(bm, uv_layer, (0.0, py), 5.80, 6.20, 0.38, 0.44, segments=8, material_index=2)

        # Giant peppermint swirl lollipop medallion on each shoulder (y=±3.20, z=6.60..8.10)
        _add_frustum_z(bm, uv_layer, (0.0, py), 6.20, 6.80, 0.06, 0.06, segments=6, material_index=2)
        _add_frustum_x(bm, uv_layer, (py, 7.35), -0.18, 0.18, 0.62, 0.62, segments=12, material_index=1)
        _add_frustum_x(bm, uv_layer, (py, 7.35), -0.22, 0.22, 0.38, 0.38, segments=10, material_index=3)

        # Hanging glowing candy lantern beneath the arch haunch (y=±2.35, z=5.25..5.95)
        ly = side_sign * 2.35
        _add_frustum_z(bm, uv_layer, (0.0, ly), 5.75, 6.05, 0.03, 0.03, segments=6, material_index=7)
        _add_frustum_z(bm, uv_layer, (0.0, ly), 5.35, 5.75, 0.18, 0.22, segments=6, material_index=5)
        _add_frustum_z(bm, uv_layer, (0.0, ly), 5.20, 5.35, 0.0, 0.14, segments=6, material_index=4)

    # Arch lintel & stepped gothic-candy ribs spanning y=-3.45..+3.45 above z=5.85m
    _add_box(bm, uv_layer, (-0.38, -3.45, 5.85), (0.38, 3.45, 6.48), material_index=0)
    _add_box(bm, uv_layer, (-0.44, -3.55, 6.48), (0.44, 3.55, 6.72), material_index=2)
    _add_box(bm, uv_layer, (-0.32, -2.40, 6.72), (0.32, 2.40, 7.25), material_index=4)

    # Diagonal arch braces from pillars (y=±3.0, z=4.8) to arch haunch (y=±1.9, z=5.90)
    # Keeping y=-1.9..+1.9 completely clear below z=5.85m!
    _add_prism_bar(bm, uv_layer, (0.0, -3.05, 4.75), (0.0, -1.95, 5.90), 0.14, 0.16, material_index=1)
    _add_prism_bar(bm, uv_layer, (0.0, 3.05, 4.75), (0.0, 1.95, 5.90), 0.14, 0.16, material_index=1)

    # Central Jack-o'-Lantern emblem & witch-hat spire reaching exact z=9.50m
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 7.15, 7.95, 0.58, 0.52, segments=10, material_index=6)
    # Glowing eyes & grin on -X (west-facing toward Central Plaza) and +X
    _add_box(bm, uv_layer, (-0.56, -0.26, 7.55), (0.56, -0.10, 7.74), material_index=5)
    _add_box(bm, uv_layer, (-0.56, 0.10, 7.55), (0.56, 0.26, 7.74), material_index=5)
    _add_box(bm, uv_layer, (-0.58, -0.30, 7.28), (0.58, 0.30, 7.44), material_index=5)

    # Witch-hat brim & spire reaching z=9.50m
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 7.90, 8.08, 0.95, 0.65, segments=10, material_index=4)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 8.08, 8.24, 0.58, 0.52, segments=10, material_index=1)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 8.24, 9.10, 0.50, 0.16, segments=8, material_index=4)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 9.10, 9.50, 0.16, 0.0, segments=8, material_index=5)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (
        mats["gingerbread"],
        mats["candy_red"],
        mats["candy_cream"],
        mats["candy_mint"],
        mats["witch_roof"],
        mats["amber_window"],
        mats["pumpkin_orange"],
        mats["dark_wood"],
    ):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("CCD_CandyArch_001", mesh)
    obj.location = Vector((33.0, 0.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_m04_workshop_proxy(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `CCD_M04_CandyWorkshopProxy_001`: proxy for Meshy `M04` at (38.0, 0.0, 0.0), rot_z=+90 deg.

    Built in M04's exact local frame from `assets/meshy/received.json`:
      - `bounds_local_m`: min [-4.0, -2.683, 0.0], max [4.0, 2.683, 7.628] (8.0m x 5.367m x 7.628m)
      - `front_local`: +Y (when rotated +90 deg around Z, local +Y faces -X West toward the Candy Street)
      - `points_local_m`:
          * `door_bottom_centre`: [-0.006, 2.128, 0.116]
          * `door_top_centre`:    [-0.006, 2.128, 2.009]
          * `bay_window_centre`:  [2.096, 2.506, 1.126]
          * `shop_window_centre`: [-2.13, 2.632, 0.979]
          * `upper_window_centre`:[1.339, 2.086, 3.312]
          * `dormer_window_centre`:[-2.277, 2.002, 3.354]
    """
    mesh = bpy.data.meshes.new("CCD_M04_CandyWorkshopProxy_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material slots:
    # 0=gingerbread, 1=dark_wood, 2=candy_cream, 3=witch_roof, 4=candy_red, 5=candy_mint, 6=amber_window, 7=cobble_choc
    # 1. Exact outer plinth & eaves trim defining the exact [-4.0..4.0] x [-2.683..2.683] x [0.0..7.628] envelope
    _add_box(bm, uv_layer, (-3.85, -2.45, 0.0), (3.85, 2.15, 0.42), material_index=7)
    # Front stone step at door_bottom_centre (x=-0.006, y=2.128..2.683, z=0.0..0.116)
    _add_box(bm, uv_layer, (-0.75, 2.10, 0.0), (0.75, 2.683, 0.116), material_index=7)

    # 2. Main ground-floor gingerbread & half-timber body (x=-3.75..3.75, y=-2.35..2.12, z=0.42..3.60)
    _add_box(bm, uv_layer, (-3.75, -2.35, 0.42), (3.75, 2.12, 2.75), material_index=0)
    # Upper overhanging half-timber story (x=-3.90..3.90, y=-2.50..2.22, z=2.75..4.15)
    _add_box(bm, uv_layer, (-3.90, -2.50, 2.75), (3.90, 2.22, 4.15), material_index=2)
    # Timber beams on front (+Y) facade
    for bx in (-3.70, -1.35, 1.35, 3.70):
        _add_box(bm, uv_layer, (bx - 0.12, 2.08, 0.42), (bx + 0.12, 2.26, 4.15), material_index=1)
    _add_box(bm, uv_layer, (-3.92, 2.08, 2.65), (3.92, 2.28, 2.85), material_index=1)

    # 3. Relief Arched Shop Door at door_bottom_centre [-0.006, 2.128, 0.116] .. door_top_centre [-0.006, 2.128, 2.009]
    # Width 0.84m (x=-0.426..+0.414), height 1.893m (z=0.116..2.009)
    _add_box(bm, uv_layer, (-0.54, 2.08, 0.116), (0.53, 2.28, 2.12), material_index=4)
    _add_box(bm, uv_layer, (-0.426, 2.12, 0.116), (0.414, 2.34, 2.009), material_index=1)
    # Glowing fanlight window at top of relief door
    _add_box(bm, uv_layer, (-0.30, 2.14, 1.55), (0.29, 2.36, 1.92), material_index=6)
    # Candy-cane porch canopy over front door (y=2.12..2.64, z=2.12..2.52)
    _add_box(bm, uv_layer, (-0.82, 2.12, 2.12), (0.82, 2.64, 2.42), material_index=4)

    # 4. Right Bay Window at bay_window_centre [2.096, 2.506, 1.126]
    _add_box(bm, uv_layer, (1.28, 2.10, 0.55), (2.92, 2.58, 1.72), material_index=1)
    _add_box(bm, uv_layer, (1.38, 2.16, 0.68), (2.82, 2.62, 1.58), material_index=6)
    # Bay window striped awning
    _add_box(bm, uv_layer, (1.22, 2.10, 1.72), (2.98, 2.66, 2.02), material_index=5)

    # 5. Left Shop Display Window at shop_window_centre [-2.13, 2.632, 0.979]
    _add_box(bm, uv_layer, (-3.05, 2.10, 0.48), (-1.22, 2.64, 1.52), material_index=1)
    _add_box(bm, uv_layer, (-2.92, 2.16, 0.60), (-1.34, 2.683, 1.40), material_index=6)
    # Shop window striped awning reaching y=+2.683m
    _add_box(bm, uv_layer, (-3.12, 2.10, 1.52), (-1.16, 2.683, 1.86), material_index=4)

    # 6. Upper Gable Window at upper_window_centre [1.339, 2.086, 3.312]
    _add_box(bm, uv_layer, (0.78, 2.02, 2.88), (1.90, 2.34, 3.78), material_index=1)
    _add_box(bm, uv_layer, (0.88, 2.08, 2.98), (1.80, 2.38, 3.66), material_index=6)

    # 7. Left Dormer Window at dormer_window_centre [-2.277, 2.002, 3.354]
    _add_box(bm, uv_layer, (-2.84, 1.96, 2.92), (-1.72, 2.32, 3.82), material_index=1)
    _add_box(bm, uv_layer, (-2.72, 2.02, 3.02), (-1.84, 2.36, 3.70), material_index=6)

    # 8. Steep Witch-Hat & Crooked Gable Roof spanning exact x=-4.0..+4.0, y=-2.683..+2.683, z=3.95..7.628
    # Broad scalloped eaves base (exact X=-4.0..+4.0, Y=-2.683..+2.683)
    _add_box(bm, uv_layer, (-4.0, -2.683, 3.95), (4.0, 2.683, 4.32), material_index=3)
    # Mid roof tier
    _add_box(bm, uv_layer, (-3.45, -2.15, 4.32), (3.45, 2.15, 5.25), material_index=3)
    # Upper gable ridge & witch-hat tower over central/right bay
    _add_box(bm, uv_layer, (-2.65, -1.55, 5.25), (2.65, 1.55, 6.05), material_index=3)
    _add_frustum_z(bm, uv_layer, (0.45, 0.15), 6.00, 7.05, 1.35, 0.42, segments=8, material_index=3)
    # Spire tip reaching exact height z=7.628m
    _add_frustum_z(bm, uv_layer, (0.45, 0.15), 7.05, 7.628, 0.42, 0.0, segments=8, material_index=4)

    # Crooked brick/gingerbread chimney on left roof slope (x=-2.45, y=-0.65, z=5.20..6.95)
    _add_frustum_z(bm, uv_layer, (-2.45, -0.65), 5.20, 6.75, 0.42, 0.34, segments=8, material_index=0)
    _add_frustum_z(bm, uv_layer, (-2.45, -0.65), 6.75, 6.98, 0.46, 0.38, segments=8, material_index=2)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (
        mats["gingerbread"],
        mats["dark_wood"],
        mats["candy_cream"],
        mats["witch_roof"],
        mats["candy_red"],
        mats["candy_mint"],
        mats["amber_window"],
        mats["cobble_choc"],
    ):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("CCD_M04_CandyWorkshopProxy_001", mesh)
    obj.location = Vector((38.0, 0.0, 0.0))
    obj.rotation_euler = (0.0, 0.0, math.radians(90.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_candy_stall(
    name: str,
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    location: tuple[float, float, float],
    facing_sign_y: float,
    awning_mat_key: str,
    glow_mat_key: str,
    roof_height: float = 4.6,
) -> bpy.types.Object:
    """Create a crooked Halloween candy/potion market stall facing `facing_sign_y` (-1 for South, +1 for North)."""
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material slots: 0=gingerbread, 1=dark_wood, 2=awning, 3=candy_cream, 4=witch_roof, 5=glow
    fy = 1.0 if facing_sign_y >= 0.0 else -1.0

    # Plinth & counter base (width 3.4m: x=-1.7..1.7, depth 2.4m: y=-1.2..1.2)
    _add_box(bm, uv_layer, (-1.70, -1.20, 0.0), (1.70, 1.20, 0.22), material_index=1)
    # Rear cabinet enclosure
    ry0, ry1 = (-1.15, 0.35) if fy > 0 else (-0.35, 1.15)
    _add_box(bm, uv_layer, (-1.58, ry0, 0.22), (1.58, ry1, 2.55), material_index=0)

    # Front serving counter (on the street-facing side)
    cy0, cy1 = (0.35, 1.18) if fy > 0 else (-1.18, -0.35)
    _add_box(bm, uv_layer, (-1.65, cy0, 0.22), (1.65, cy1, 1.05), material_index=1)
    _add_box(bm, uv_layer, (-1.72, cy0 - 0.05, 1.05), (1.72, cy1 + 0.05, 1.16), material_index=3)

    # Glowing candy jars / potion bottles along the counter & rear shelf
    jar_y = 0.76 * fy
    for jx in (-1.15, -0.45, 0.35, 1.05):
        _add_frustum_z(bm, uv_layer, (jx, jar_y), 1.16, 1.54, 0.15, 0.13, segments=8, material_index=5)
        _add_frustum_z(bm, uv_layer, (jx, jar_y), 1.54, 1.66, 0.09, 0.11, segments=8, material_index=1)

    # Corner candy-cane support posts
    for px in (-1.52, 1.52):
        _add_frustum_z(bm, uv_layer, (px, 1.02 * fy), 1.16, 2.55, 0.09, 0.09, segments=8, material_index=2)

    # Striped awning canopy projecting toward the street
    ay0, ay1 = (-1.25, 1.38) if fy > 0 else (-1.38, 1.25)
    _add_box(bm, uv_layer, (-1.80, ay0, 2.48), (1.80, ay1, 2.88), material_index=2)
    _add_box(bm, uv_layer, (-1.75, ay0 + 0.08, 2.36), (1.75, ay1 - 0.08, 2.48), material_index=3)

    # Crooked witch-gable roof & spire finial reaching roof_height
    _add_box(bm, uv_layer, (-1.55, -1.05, 2.88), (1.55, 1.05, 3.55), material_index=4)
    _add_frustum_z(bm, uv_layer, (0.15 * fy, 0.0), 3.55, roof_height - 0.35, 0.92, 0.22, segments=8, material_index=4)
    _add_frustum_z(bm, uv_layer, (0.15 * fy, 0.0), roof_height - 0.35, roof_height, 0.22, 0.0, segments=8, material_index=2)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (
        mats["gingerbread"],
        mats["dark_wood"],
        mats[awning_mat_key],
        mats["candy_cream"],
        mats["witch_roof"],
        mats[glow_mat_key],
    ):
        mesh.materials.append(m)

    obj = bpy.data.objects.new(name, mesh)
    obj.location = Vector(location)
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_magic_cauldron(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, bpy.types.Object]:
    """Create `CCD_MagicCauldron_001` (G09 & I02) at (34.4, 5.2, 0.0) with separate body, liquid, stirring rod, and attachments."""
    root_empty = create_empty(
        "CCD_MagicCauldron_001",
        collection,
        location=(34.4, 5.2, 0.0),
        display_type="PLAIN_AXES",
        display_size=0.35,
    )

    # 1. Static Body (`CCD_MagicCauldron_001_Body`): stone fire ring, glowing embers, cast-iron cauldron vessel, side handles
    body_mesh = bpy.data.meshes.new("CCD_MagicCauldron_001_Body_Mesh")
    bm_body = bmesh.new()
    uv_body = bm_body.loops.layers.uv.new("UVMap")
    # 0=cobble_choc, 1=cauldron_iron, 2=brass_gear, 3=amber_window, 4=candy_red
    # Stone hearth base & glowing fire bed (z=0.0..0.24)
    _add_frustum_z(bm_body, uv_body, (0.0, 0.0), 0.0, 0.18, 1.05, 0.96, segments=12, material_index=0)
    _add_frustum_z(bm_body, uv_body, (0.0, 0.0), 0.18, 0.25, 0.68, 0.60, segments=10, material_index=3)
    # Three cast-iron claw feet
    for i in range(3):
        ang = 2.0 * math.pi * i / 3.0
        _add_frustum_z(
            bm_body,
            uv_body,
            (0.62 * math.cos(ang), 0.62 * math.sin(ang)),
            0.08,
            0.34,
            0.14,
            0.10,
            segments=8,
            material_index=1,
        )
    # Bulging cauldron belly & flared rim (z=0.20..1.28)
    _add_frustum_z(bm_body, uv_body, (0.0, 0.0), 0.20, 0.48, 0.56, 0.88, segments=14, material_index=1)
    _add_frustum_z(bm_body, uv_body, (0.0, 0.0), 0.48, 0.96, 0.88, 0.82, segments=14, material_index=1)
    _add_frustum_z(bm_body, uv_body, (0.0, 0.0), 0.96, 1.14, 0.82, 0.72, segments=14, material_index=1)
    _add_frustum_z(bm_body, uv_body, (0.0, 0.0), 1.14, 1.28, 0.72, 0.86, segments=14, material_index=1)
    # Decorative brass belly band & side lug handles
    _add_frustum_z(bm_body, uv_body, (0.0, 0.0), 0.68, 0.78, 0.90, 0.90, segments=14, material_index=2)
    for sx in (-1.0, 1.0):
        _add_box(bm_body, uv_body, (sx * 0.82, -0.14, 0.78), (sx * 1.02, 0.14, 1.04), material_index=2)

    bmesh.ops.recalc_face_normals(bm_body, faces=bm_body.faces)
    bm_body.to_mesh(body_mesh)
    bm_body.free()
    body_mesh.update()
    for m in (mats["cobble_choc"], mats["cauldron_iron"], mats["brass_gear"], mats["amber_window"], mats["candy_red"]):
        body_mesh.materials.append(m)

    body_obj = bpy.data.objects.new("CCD_MagicCauldron_001_Body", body_mesh)
    collection.objects.link(body_obj)
    body_obj.parent = root_empty
    body_obj.location = Vector((0.0, 0.0, 0.0))
    body_obj.scale = Vector((1.0, 1.0, 1.0))

    # 2. Separate Liquid Surface (`CCD_MagicCauldron_001_Liquid`) at local (0.0, 0.0, 1.12)
    # Kept as an independent Mesh object so I02 can switch its material color/emission and G09 can pulse it.
    liq_mesh = bpy.data.meshes.new("CCD_MagicCauldron_001_Liquid_Mesh")
    bm_liq = bmesh.new()
    uv_liq = bm_liq.loops.layers.uv.new("UVMap")
    # 0=potion_emerald, 1=potion_magenta
    _add_frustum_z(bm_liq, uv_liq, (0.0, 0.0), 0.0, 0.06, 0.70, 0.72, segments=14, material_index=0)
    # Bubbling potion mounds on the liquid surface
    for bx, by, br, bh, bmat in [
        (-0.26, 0.18, 0.14, 0.14, 0),
        (0.28, -0.16, 0.12, 0.13, 1),
        (0.10, 0.30, 0.10, 0.12, 0),
        (-0.18, -0.28, 0.11, 0.12, 1),
    ]:
        _add_frustum_z(bm_liq, uv_liq, (bx, by), 0.05, bh, br, 0.03, segments=8, material_index=bmat)

    bmesh.ops.recalc_face_normals(bm_liq, faces=bm_liq.faces)
    bm_liq.to_mesh(liq_mesh)
    bm_liq.free()
    liq_mesh.update()
    liq_mesh.materials.append(mats["potion_emerald"])
    liq_mesh.materials.append(mats["potion_magenta"])

    liq_obj = bpy.data.objects.new("CCD_MagicCauldron_001_Liquid", liq_mesh)
    collection.objects.link(liq_obj)
    liq_obj.parent = root_empty
    liq_obj.location = Vector((0.0, 0.0, 1.12))
    liq_obj.scale = Vector((1.0, 1.0, 1.0))

    # 3. Stirring Rod MotionRoot (`CCD_MagicCauldron_001_StirRodPivot`) at local (0.0, 0.0, 1.16)
    stir_pivot = create_empty(
        "CCD_MagicCauldron_001_StirRodPivot",
        collection,
        location=(0.0, 0.0, 1.16),
        parent=root_empty,
        display_type="ARROWS",
        display_size=0.22,
    )

    # 4. Stirring Rod Mesh (`CCD_MagicCauldron_001_StirRod`) parented to `StirRodPivot`
    rod_mesh = bpy.data.meshes.new("CCD_MagicCauldron_001_StirRod_Mesh")
    bm_rod = bmesh.new()
    uv_rod = bm_rod.loops.layers.uv.new("UVMap")
    # 0=dark_wood, 1=brass_gear, 2=potion_magenta
    # Angled stirring shaft from submerged paddle (-0.16, 0.0, -0.52) through pivot (0,0,0) to upper knob (0.24, 0.0, 0.86)
    _add_prism_bar(bm_rod, uv_rod, (-0.16, 0.0, -0.52), (0.24, 0.0, 0.82), 0.045, 0.045, material_index=0)
    # Submerged stirring paddle blade
    _add_box(bm_rod, uv_rod, (-0.26, -0.14, -0.54), (-0.06, 0.14, -0.18), material_index=0)
    # Brass collar & glowing crystal pommel at top of stirring rod
    _add_frustum_z(bm_rod, uv_rod, (0.24, 0.0), 0.76, 0.84, 0.07, 0.08, segments=8, material_index=1)
    _add_frustum_z(bm_rod, uv_rod, (0.24, 0.0), 0.84, 0.98, 0.09, 0.0, segments=8, material_index=2)

    bmesh.ops.recalc_face_normals(bm_rod, faces=bm_rod.faces)
    bm_rod.to_mesh(rod_mesh)
    bm_rod.free()
    rod_mesh.update()
    for m in (mats["dark_wood"], mats["brass_gear"], mats["potion_magenta"]):
        rod_mesh.materials.append(m)

    rod_obj = bpy.data.objects.new("CCD_MagicCauldron_001_StirRod", rod_mesh)
    collection.objects.link(rod_obj)
    rod_obj.parent = stir_pivot
    rod_obj.location = Vector((0.0, 0.0, 0.0))
    rod_obj.scale = Vector((1.0, 1.0, 1.0))

    # 5. Attachment points for G09 bubble particles & steam/audio
    bubble_attach = _create_socket_marker_mesh(
        "CCD_MagicCauldron_001_BubbleAttach",
        collection,
        location=(0.0, 0.0, 0.14),
        mat=mats["potion_emerald"],
        parent=liq_obj,
        radius=0.05,
    )
    smoke_attach = _create_socket_marker_mesh(
        "CCD_MagicCauldron_001_SmokeAttach",
        collection,
        location=(0.0, 0.0, 1.56),
        mat=mats["starlight_cyan"],
        parent=root_empty,
        radius=0.05,
    )

    return {
        "root": root_empty,
        "body": body_obj,
        "liquid": liq_obj,
        "stir_pivot": stir_pivot,
        "stir_rod": rod_obj,
        "bubble_attach": bubble_attach,
        "smoke_attach": smoke_attach,
    }


def build_cauldron_color_control(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, bpy.types.Object]:
    """Create `CCD_CauldronColorControl_001` (I02 interactive pedestal) at (33.0, 3.8, 0.0)."""
    root_empty = create_empty(
        "CCD_CauldronColorControl_001",
        collection,
        location=(33.0, 3.8, 0.0),
        display_type="PLAIN_AXES",
        display_size=0.25,
    )

    # 1. Static Pedestal (`CCD_CauldronColorControl_001_Pedestal`) with 3 color sample vials
    ped_mesh = bpy.data.meshes.new("CCD_CauldronColorControl_001_Pedestal_Mesh")
    bm_ped = bmesh.new()
    uv_ped = bm_ped.loops.layers.uv.new("UVMap")
    # 0=cobble_choc, 1=cauldron_iron, 2=brass_gear, 3=potion_emerald, 4=potion_magenta, 5=amber_window
    _add_frustum_z(bm_ped, uv_ped, (0.0, 0.0), 0.0, 0.16, 0.36, 0.32, segments=8, material_index=0)
    _add_frustum_z(bm_ped, uv_ped, (0.0, 0.0), 0.16, 0.86, 0.14, 0.12, segments=8, material_index=1)
    _add_box(bm_ped, uv_ped, (-0.32, -0.24, 0.86), (0.32, 0.24, 1.02), material_index=2)
    # Three color sample vials on the lectern (Emerald, Magenta, Amber)
    for vx, vmat in [(-0.18, 3), (0.0, 4), (0.18, 5)]:
        _add_frustum_z(bm_ped, uv_ped, (vx, 0.10), 1.02, 1.20, 0.045, 0.040, segments=8, material_index=vmat)

    bmesh.ops.recalc_face_normals(bm_ped, faces=bm_ped.faces)
    bm_ped.to_mesh(ped_mesh)
    bm_ped.free()
    ped_mesh.update()
    for m in (
        mats["cobble_choc"],
        mats["cauldron_iron"],
        mats["brass_gear"],
        mats["potion_emerald"],
        mats["potion_magenta"],
        mats["amber_window"],
    ):
        ped_mesh.materials.append(m)

    ped_obj = bpy.data.objects.new("CCD_CauldronColorControl_001_Pedestal", ped_mesh)
    collection.objects.link(ped_obj)
    ped_obj.parent = root_empty
    ped_obj.location = Vector((0.0, 0.0, 0.0))
    ped_obj.scale = Vector((1.0, 1.0, 1.0))

    # 2. Switch MotionRoot (`CCD_CauldronColorControl_001_SwitchPivot`) at local (0.0, -0.06, 1.02)
    switch_pivot = create_empty(
        "CCD_CauldronColorControl_001_SwitchPivot",
        collection,
        location=(0.0, -0.06, 1.02),
        parent=root_empty,
        display_type="ARROWS",
        display_size=0.16,
    )

    # 3. Interactive Crystal Orb Switch (`CCD_CauldronColorControl_001_CrystalOrb`)
    orb_mesh = bpy.data.meshes.new("CCD_CauldronColorControl_001_CrystalOrb_Mesh")
    bm_orb = bmesh.new()
    uv_orb = bm_orb.loops.layers.uv.new("UVMap")
    # 0=brass_gear, 1=potion_magenta
    _add_frustum_z(bm_orb, uv_orb, (0.0, 0.0), 0.0, 0.06, 0.11, 0.09, segments=8, material_index=0)
    _add_frustum_z(bm_orb, uv_orb, (0.0, 0.0), 0.06, 0.16, 0.09, 0.13, segments=8, material_index=1)
    _add_frustum_z(bm_orb, uv_orb, (0.0, 0.0), 0.16, 0.26, 0.13, 0.0, segments=8, material_index=1)
    bmesh.ops.recalc_face_normals(bm_orb, faces=bm_orb.faces)
    bm_orb.to_mesh(orb_mesh)
    bm_orb.free()
    orb_mesh.update()
    orb_mesh.materials.append(mats["brass_gear"])
    orb_mesh.materials.append(mats["potion_magenta"])

    orb_obj = bpy.data.objects.new("CCD_CauldronColorControl_001_CrystalOrb", orb_mesh)
    collection.objects.link(orb_obj)
    orb_obj.parent = switch_pivot
    orb_obj.location = Vector((0.0, 0.0, 0.0))
    orb_obj.scale = Vector((1.0, 1.0, 1.0))

    # 4. Touch interaction attachment point
    touch_attach = _create_socket_marker_mesh(
        "CCD_CauldronColorControl_001_TouchAttach",
        collection,
        location=(0.0, -0.14, 0.14),
        mat=mats["starlight_cyan"],
        parent=switch_pivot,
        radius=0.04,
    )

    return {
        "root": root_empty,
        "pedestal": ped_obj,
        "switch_pivot": switch_pivot,
        "crystal_orb": orb_obj,
        "touch_attach": touch_attach,
    }


def _build_gear_wheel_mesh(
    name: str,
    radius: float,
    thickness_x: float,
    teeth: int,
    mat_wheel: bpy.types.Material,
    mat_hub: bpy.types.Material,
) -> bpy.types.Mesh:
    """Create a gear wheel mesh in the YZ plane centered at local (0,0,0) with rotation axis X."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    hx = 0.5 * thickness_x
    _add_frustum_x(bm, uv_layer, (0.0, 0.0), -hx, hx, radius * 0.78, radius * 0.78, segments=12, material_index=0)
    _add_frustum_x(bm, uv_layer, (0.0, 0.0), -hx * 1.4, hx * 1.4, radius * 0.28, radius * 0.28, segments=8, material_index=1)
    for i in range(teeth):
        ang = 2.0 * math.pi * i / teeth
        p0 = (0.0, (radius * 0.68) * math.cos(ang), (radius * 0.68) * math.sin(ang))
        p1 = (0.0, radius * math.cos(ang), radius * math.sin(ang))
        _add_prism_bar(bm, uv_layer, p0, p1, half_width=hx * 0.85, half_height=radius * 0.11, material_index=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    mesh.materials.append(mat_wheel)
    mesh.materials.append(mat_hub)
    return mesh


def build_candy_machine(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, bpy.types.Object]:
    """Create `CCD_CandyMachine_001` (G10) at (34.4, -5.2, 0.0) with body, rotating gears, reciprocating extruder, and chute."""
    root_empty = create_empty(
        "CCD_CandyMachine_001",
        collection,
        location=(34.4, -5.2, 0.0),
        display_type="PLAIN_AXES",
        display_size=0.35,
    )

    # 1. Static Machine Body (`CCD_CandyMachine_001_Body`)
    body_mesh = bpy.data.meshes.new("CCD_CandyMachine_001_Body_Mesh")
    bm_body = bmesh.new()
    uv_body = bm_body.loops.layers.uv.new("UVMap")
    # 0=cauldron_iron, 1=brass_gear, 2=candy_red, 3=potion_magenta, 4=witch_roof, 5=candy_cream
    _add_box(bm_body, uv_body, (-0.75, -0.68, 0.0), (0.75, 0.58, 0.24), material_index=0)
    _add_box(bm_body, uv_body, (-0.64, -0.56, 0.24), (0.64, 0.52, 1.42), material_index=2)
    _add_box(bm_body, uv_body, (-0.68, -0.60, 1.32), (0.68, 0.56, 1.48), material_index=1)
    # Glowing gumball/candy hopper globe (z=1.48..2.46)
    _add_frustum_z(bm_body, uv_body, (0.0, -0.04), 1.48, 1.98, 0.52, 0.66, segments=12, material_index=3)
    _add_frustum_z(bm_body, uv_body, (0.0, -0.04), 1.98, 2.46, 0.66, 0.42, segments=12, material_index=3)
    # Witch-cat hat topper on the candy globe (z=2.44..3.18)
    _add_frustum_z(bm_body, uv_body, (0.0, -0.04), 2.44, 2.58, 0.72, 0.52, segments=10, material_index=4)
    _add_frustum_z(bm_body, uv_body, (0.0, -0.04), 2.58, 3.18, 0.44, 0.0, segments=8, material_index=4)
    # Side brass steam pipe (+X side)
    _add_frustum_z(bm_body, uv_body, (0.72, -0.10), 0.55, 2.15, 0.09, 0.08, segments=8, material_index=1)

    bmesh.ops.recalc_face_normals(bm_body, faces=bm_body.faces)
    bm_body.to_mesh(body_mesh)
    bm_body.free()
    body_mesh.update()
    for m in (
        mats["cauldron_iron"],
        mats["brass_gear"],
        mats["candy_red"],
        mats["potion_magenta"],
        mats["witch_roof"],
        mats["candy_cream"],
    ):
        body_mesh.materials.append(m)

    body_obj = bpy.data.objects.new("CCD_CandyMachine_001_Body", body_mesh)
    collection.objects.link(body_obj)
    body_obj.parent = root_empty
    body_obj.location = Vector((0.0, 0.0, 0.0))
    body_obj.scale = Vector((1.0, 1.0, 1.0))

    # 2. Main Rotating Gear (`CCD_CandyMachine_001_GearMainPivot` + `CCD_CandyMachine_001_GearMain`)
    gear_main_pivot = create_empty(
        "CCD_CandyMachine_001_GearMainPivot",
        collection,
        location=(-0.70, -0.08, 1.15),
        parent=root_empty,
        display_type="ARROWS",
        display_size=0.20,
    )
    gear_main_mesh = _build_gear_wheel_mesh(
        "CCD_CandyMachine_001_GearMain_Mesh",
        radius=0.46,
        thickness_x=0.12,
        teeth=8,
        mat_wheel=mats["brass_gear"],
        mat_hub=mats["cauldron_iron"],
    )
    gear_main_obj = bpy.data.objects.new("CCD_CandyMachine_001_GearMain", gear_main_mesh)
    collection.objects.link(gear_main_obj)
    gear_main_obj.parent = gear_main_pivot
    gear_main_obj.location = Vector((0.0, 0.0, 0.0))
    gear_main_obj.scale = Vector((1.0, 1.0, 1.0))

    # 3. Sub Counter-Rotating Gear (`CCD_CandyMachine_001_GearSubPivot` + `CCD_CandyMachine_001_GearSub`)
    gear_sub_pivot = create_empty(
        "CCD_CandyMachine_001_GearSubPivot",
        collection,
        location=(-0.70, 0.42, 1.66),
        parent=root_empty,
        display_type="ARROWS",
        display_size=0.18,
    )
    gear_sub_mesh = _build_gear_wheel_mesh(
        "CCD_CandyMachine_001_GearSub_Mesh",
        radius=0.32,
        thickness_x=0.12,
        teeth=8,
        mat_wheel=mats["candy_mint"],
        mat_hub=mats["brass_gear"],
    )
    gear_sub_obj = bpy.data.objects.new("CCD_CandyMachine_001_GearSub", gear_sub_mesh)
    collection.objects.link(gear_sub_obj)
    gear_sub_obj.parent = gear_sub_pivot
    gear_sub_obj.location = Vector((0.0, 0.0, 0.0))
    gear_sub_obj.scale = Vector((1.0, 1.0, 1.0))

    # 4. Reciprocating Candy Extruder Piston (`CCD_CandyMachine_001_ExtruderPivot` + `CCD_CandyMachine_001_Extruder`)
    extruder_pivot = create_empty(
        "CCD_CandyMachine_001_ExtruderPivot",
        collection,
        location=(0.0, 0.52, 1.05),
        parent=root_empty,
        display_type="ARROWS",
        display_size=0.18,
    )
    ext_mesh = bpy.data.meshes.new("CCD_CandyMachine_001_Extruder_Mesh")
    bm_ext = bmesh.new()
    uv_ext = bm_ext.loops.layers.uv.new("UVMap")
    _add_box(bm_ext, uv_ext, (-0.11, -0.10, -0.09), (0.11, 0.28, 0.09), material_index=0)
    _add_box(bm_ext, uv_ext, (-0.18, 0.28, -0.15), (0.18, 0.40, 0.15), material_index=1)
    bmesh.ops.recalc_face_normals(bm_ext, faces=bm_ext.faces)
    bm_ext.to_mesh(ext_mesh)
    bm_ext.free()
    ext_mesh.update()
    ext_mesh.materials.append(mats["brass_gear"])
    ext_mesh.materials.append(mats["candy_red"])

    extruder_obj = bpy.data.objects.new("CCD_CandyMachine_001_Extruder", ext_mesh)
    collection.objects.link(extruder_obj)
    extruder_obj.parent = extruder_pivot
    extruder_obj.location = Vector((0.0, 0.0, 0.0))
    extruder_obj.scale = Vector((1.0, 1.0, 1.0))

    # 5. Candy Delivery Chute (`CCD_CandyMachine_001_Chute`) & Outlet Attachment (`CCD_CandyMachine_001_OutletAttach`)
    chute_mesh = bpy.data.meshes.new("CCD_CandyMachine_001_Chute_Mesh")
    bm_chute = bmesh.new()
    uv_chute = bm_chute.loops.layers.uv.new("UVMap")
    _add_prism_bar(bm_chute, uv_chute, (0.0, 0.0, 0.36), (0.0, 0.54, 0.12), 0.22, 0.10, material_index=0)
    _add_box(bm_chute, uv_chute, (-0.26, 0.42, 0.0), (0.26, 0.64, 0.18), material_index=1)
    bmesh.ops.recalc_face_normals(bm_chute, faces=bm_chute.faces)
    bm_chute.to_mesh(chute_mesh)
    bm_chute.free()
    chute_mesh.update()
    chute_mesh.materials.append(mats["brass_gear"])
    chute_mesh.materials.append(mats["cauldron_iron"])

    chute_obj = bpy.data.objects.new("CCD_CandyMachine_001_Chute", chute_mesh)
    collection.objects.link(chute_obj)
    chute_obj.parent = root_empty
    chute_obj.location = Vector((0.0, 0.50, 0.42))
    chute_obj.scale = Vector((1.0, 1.0, 1.0))

    outlet_attach = _create_socket_marker_mesh(
        "CCD_CandyMachine_001_OutletAttach",
        collection,
        location=(0.0, 0.54, 0.20),
        mat=mats["amber_window"],
        parent=chute_obj,
        radius=0.05,
    )

    return {
        "root": root_empty,
        "body": body_obj,
        "gear_main_pivot": gear_main_pivot,
        "gear_main": gear_main_obj,
        "gear_sub_pivot": gear_sub_pivot,
        "gear_sub": gear_sub_obj,
        "extruder_pivot": extruder_pivot,
        "extruder": extruder_obj,
        "chute": chute_obj,
        "outlet_attach": outlet_attach,
    }


def build_magic_broom(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, bpy.types.Object]:
    """Create `CCD_MagicBroom_001` (G12 self-sweeping broom) with floor-near pivot at (28.5, 3.2, 0.05)."""
    root_pivot = create_empty(
        "CCD_MagicBroom_001",
        collection,
        location=(28.5, 3.2, 0.05),
        display_type="ARROWS",
        display_size=0.22,
    )

    broom_mesh = bpy.data.meshes.new("CCD_MagicBroom_001_BroomMesh_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    # 0=straw_gold, 1=brass_gear, 2=dark_wood, 3=candy_red
    # Flared straw bristle bundle hovering just above floor (z=0.0..0.52)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.0, 0.24, 0.22, 0.16, segments=10, material_index=0)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.24, 0.50, 0.16, 0.07, segments=10, material_index=0)
    # Brass binding rings
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.46, 0.54, 0.085, 0.080, segments=8, material_index=1)
    # Crooked wooden broomstick handle (z=0.52..1.68)
    _add_prism_bar(bm, uv_layer, (0.0, 0.0, 0.50), (0.05, -0.02, 1.15), 0.032, 0.032, material_index=2)
    _add_prism_bar(bm, uv_layer, (0.05, -0.02, 1.15), (-0.03, 0.02, 1.68), 0.030, 0.030, material_index=2)
    # Decorative candy-red ribbon collar
    _add_box(bm, uv_layer, (-0.09, -0.06, 0.54), (0.09, 0.06, 0.62), material_index=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(broom_mesh)
    bm.free()
    broom_mesh.update()
    for m in (mats["straw_gold"], mats["brass_gear"], mats["dark_wood"], mats["candy_red"]):
        broom_mesh.materials.append(m)

    broom_obj = bpy.data.objects.new("CCD_MagicBroom_001_BroomMesh", broom_mesh)
    collection.objects.link(broom_obj)
    broom_obj.parent = root_pivot
    broom_obj.location = Vector((0.0, 0.0, 0.0))
    broom_obj.scale = Vector((1.0, 1.0, 1.0))

    sweep_attach = _create_socket_marker_mesh(
        "CCD_MagicBroom_001_SweepAttach",
        collection,
        location=(0.0, 0.0, 0.06),
        mat=mats["starlight_cyan"],
        parent=broom_obj,
        radius=0.04,
    )

    return {
        "root": root_pivot,
        "broom": broom_obj,
        "sweep_attach": sweep_attach,
    }


def build_m08_flying_witch_proxy(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `CCD_M08_FlyingWitchProxy_001`: proxy for Meshy `M08` at Waypoint 0 (43.2, 0.0, 10.2), rot=(0,0,0).

    Exact local & world bounds matching `assets/meshy/received.json`:
      - `origin_policy`: "hinge_pivot"
      - `front_local`: "+Y"
      - `bounds_local_m`: min [-0.637, -1.215, -0.612], max [0.905, 0.912, 1.888]
      - `dimensions_m`: width_x 1.542, depth_y 2.126, height_z 2.500
      - `points_local_m`:
          * `broom_tip`:          [0.0, 0.91, 0.214]
          * `bristle_end_centre`: [0.0, -1.043, -0.245]
    """
    mesh = bpy.data.meshes.new("CCD_M08_FlyingWitchProxy_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material slots: 0=dark_wood, 1=straw_gold, 2=witch_roof, 3=candy_cream, 4=candy_red, 5=amber_window
    # 1. Angled broomstick shaft from bristle_end_centre (0.0, -1.043, -0.245) through (0,0,0) to broom_tip (0.0, 0.912, 0.214)
    _add_prism_bar(bm, uv_layer, (0.0, -0.72, -0.17), (0.0, 0.912, 0.214), 0.045, 0.045, material_index=0)
    # Bristle tail bundle reaching exact y = -1.215m
    _add_prism_bar(bm, uv_layer, (0.0, -1.215, -0.285), (0.0, -0.68, -0.16), 0.22, 0.18, material_index=1)
    # Hanging lantern & lower robe hem reaching exact z = -0.612m
    _add_box(bm, uv_layer, (-0.28, -0.26, -0.612), (0.28, 0.24, -0.05), material_index=2)
    _add_frustum_z(bm, uv_layer, (0.0, 0.78), -0.18, 0.12, 0.10, 0.12, segments=6, material_index=5)

    # 2. Billowing witch cape & side scroll ribbons defining exact X bounds [-0.637..+0.905]
    _add_box(bm, uv_layer, (-0.637, -0.58, -0.12), (0.905, 0.36, 0.58), material_index=2)

    # 3. Witch torso, head, and pointed witch hat reaching exact z = +1.888m
    _add_frustum_z(bm, uv_layer, (0.04, -0.06), 0.0, 0.78, 0.32, 0.22, segments=8, material_index=2)
    _add_frustum_z(bm, uv_layer, (0.04, -0.04), 0.78, 1.12, 0.18, 0.16, segments=8, material_index=3)
    # Broad witch hat brim & crooked cone reaching z = 1.888m
    _add_frustum_z(bm, uv_layer, (0.04, -0.04), 1.10, 1.22, 0.52, 0.36, segments=10, material_index=2)
    _add_frustum_z(bm, uv_layer, (0.04, -0.04), 1.22, 1.32, 0.32, 0.28, segments=8, material_index=4)
    _add_frustum_z(bm, uv_layer, (0.04, -0.04), 1.32, 1.888, 0.28, 0.0, segments=8, material_index=2)

    # 4. Small companion cat perched ahead of the witch on the front broom shaft (y=+0.42..+0.68)
    _add_frustum_z(bm, uv_layer, (0.0, 0.52), 0.12, 0.46, 0.14, 0.10, segments=8, material_index=2)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (
        mats["dark_wood"],
        mats["straw_gold"],
        mats["witch_roof"],
        mats["candy_cream"],
        mats["candy_red"],
        mats["amber_window"],
    ):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("CCD_M08_FlyingWitchProxy_001", mesh)
    obj.location = Vector((43.2, 0.0, 10.2))
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


PATROL_LOOP_WAYPOINTS_WORLD: list[tuple[float, float, float]] = [
    (43.2, 0.0, 10.2),
    (39.5, 7.5, 10.5),
    (33.0, 9.5, 10.4),
    (26.5, 7.5, 10.1),
    (24.5, 0.0, 9.8),
    (26.5, -7.5, 10.1),
    (33.0, -9.5, 10.4),
    (39.5, -7.5, 10.5),
]


def build_witch_patrol_loop(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, bpy.types.Object]:
    """Create `CCD_WitchPatrolLoop_001` (G11 closed upper-air patrol loop) at (33.0, 0.0, 0.0)."""
    origin = Vector((33.0, 0.0, 0.0))
    root_empty = create_empty(
        "CCD_WitchPatrolLoop_001",
        collection,
        location=(33.0, 0.0, 0.0),
        display_type="PLAIN_AXES",
        display_size=0.40,
    )

    ring_mesh = bpy.data.meshes.new("CCD_WitchPatrolLoop_001_GuideRing_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    # 0=starlight_cyan, 1=amber_window
    local_pts = [
        (wx - origin.x, wy - origin.y, wz - origin.z)
        for wx, wy, wz in PATROL_LOOP_WAYPOINTS_WORLD
    ]
    n_pts = len(local_pts)
    for i in range(n_pts):
        p0 = local_pts[i]
        p1 = local_pts[(i + 1) % n_pts]
        # Slender glowing starlight guide ribbon segment in the sky
        _add_prism_bar(bm, uv_layer, p0, p1, half_width=0.045, half_height=0.025, material_index=0)
        # Star-beacon waypoint diamond at each waypoint
        wx, wy, wz = p0
        _add_frustum_z(bm, uv_layer, (wx, wy), wz - 0.18, wz, 0.02, 0.14, segments=6, material_index=1)
        _add_frustum_z(bm, uv_layer, (wx, wy), wz, wz + 0.18, 0.14, 0.0, segments=6, material_index=1)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ring_mesh)
    bm.free()
    ring_mesh.update()
    ring_mesh.materials.append(mats["starlight_cyan"])
    ring_mesh.materials.append(mats["amber_window"])

    ring_obj = bpy.data.objects.new("CCD_WitchPatrolLoop_001_GuideRing", ring_mesh)
    collection.objects.link(ring_obj)
    ring_obj.parent = root_empty
    ring_obj.location = Vector((0.0, 0.0, 0.0))
    ring_obj.scale = Vector((1.0, 1.0, 1.0))

    # Carrier MotionRoot at Waypoint 0: local (10.2, 0.0, 10.2) -> world (43.2, 0.0, 10.2)
    carrier_pivot = create_empty(
        "CCD_WitchPatrolLoop_001_CarrierPivot",
        collection,
        location=(10.2, 0.0, 10.2),
        parent=root_empty,
        display_type="ARROWS",
        display_size=0.30,
    )
    carrier_marker = _create_socket_marker_mesh(
        "CCD_WitchPatrolLoop_001_CarrierAttach",
        collection,
        location=(0.0, 0.0, 0.0),
        mat=mats["starlight_cyan"],
        parent=carrier_pivot,
        radius=0.06,
    )

    return {
        "root": root_empty,
        "guide_ring": ring_obj,
        "carrier_pivot": carrier_pivot,
        "carrier_attach": carrier_marker,
    }


COMMON_PLACEMENTS_SPEC: list[dict[str, Any]] = [
    {
        "placement_id": "CCD_StreetLamp_WestNorth_001",
        "common_asset_id": "CMN_StreetLamp_001",
        "category": "lighting",
        "position": (21.8, 3.2, 0.0),
        "rotation_deg": (0.0, 0.0, -90.0),
        "notes": "West entrance north-side streetlamp illuminating Conn_C_West_Main.",
    },
    {
        "placement_id": "CCD_StreetLamp_WestSouth_001",
        "common_asset_id": "CMN_StreetLamp_001",
        "category": "lighting",
        "position": (21.8, -3.2, 0.0),
        "rotation_deg": (0.0, 0.0, 90.0),
        "notes": "West entrance south-side streetlamp illuminating Conn_C_West_Main.",
    },
    {
        "placement_id": "CCD_StreetLamp_MidNorth_001",
        "common_asset_id": "CMN_StreetLamp_001",
        "category": "lighting",
        "position": (28.6, 4.1, 0.0),
        "rotation_deg": (0.0, 0.0, -90.0),
        "notes": "Mid-street north promenade streetlamp between candy stalls.",
    },
    {
        "placement_id": "CCD_StreetLamp_MidSouth_001",
        "common_asset_id": "CMN_StreetLamp_001",
        "category": "lighting",
        "position": (28.6, -4.1, 0.0),
        "rotation_deg": (0.0, 0.0, 90.0),
        "notes": "Mid-street south promenade streetlamp between candy stalls.",
    },
    {
        "placement_id": "CCD_StreetLamp_PlazaNorth_001",
        "common_asset_id": "CMN_StreetLamp_001",
        "category": "lighting",
        "position": (35.0, 7.2, 0.0),
        "rotation_deg": (0.0, 0.0, -135.0),
        "notes": "Workshop forecourt north-east streetlamp beside the magic cauldron.",
    },
    {
        "placement_id": "CCD_StreetLamp_PlazaSouth_001",
        "common_asset_id": "CMN_StreetLamp_001",
        "category": "lighting",
        "position": (35.0, -7.2, 0.0),
        "rotation_deg": (0.0, 0.0, 135.0),
        "notes": "Workshop forecourt south-east streetlamp beside the candy machine.",
    },
    {
        "placement_id": "CCD_Garland_WestNorth_001",
        "common_asset_id": "CMN_GarlandFlag_001",
        "category": "prop",
        "position": (26.2, 4.2, 0.0),
        "rotation_deg": (0.0, 0.0, 0.0),
        "notes": "Carnival pennant garland along the north candy stall frontage.",
    },
    {
        "placement_id": "CCD_Garland_WestSouth_001",
        "common_asset_id": "CMN_GarlandFlag_001",
        "category": "prop",
        "position": (26.2, -4.2, 0.0),
        "rotation_deg": (0.0, 0.0, 0.0),
        "notes": "Carnival pennant garland along the south pastry stall frontage.",
    },
    {
        "placement_id": "CCD_Bench_NorthSide_001",
        "common_asset_id": "CMN_Bench_001",
        "category": "prop",
        "position": (24.2, 8.8, 0.0),
        "rotation_deg": (0.0, 0.0, -90.0),
        "notes": "Visitor rest bench along the east edge of the north side path.",
    },
    {
        "placement_id": "CCD_Bench_SouthSide_001",
        "common_asset_id": "CMN_Bench_001",
        "category": "prop",
        "position": (24.2, -8.8, 0.0),
        "rotation_deg": (0.0, 0.0, 90.0),
        "notes": "Visitor rest bench along the east edge of the south side path.",
    },
    {
        "placement_id": "CCD_Fence_NorthPathEast_001",
        "common_asset_id": "CMN_Fence_001",
        "category": "architecture",
        "position": (24.2, 13.0, 0.0),
        "rotation_deg": (0.0, 0.0, 90.0),
        "notes": "Decorative wrought-iron fence guiding the north side walkway toward Conn_C_North_Side.",
    },
    {
        "placement_id": "CCD_Fence_SouthPathEast_001",
        "common_asset_id": "CMN_Fence_001",
        "category": "architecture",
        "position": (24.2, -13.0, 0.0),
        "rotation_deg": (0.0, 0.0, 90.0),
        "notes": "Decorative wrought-iron fence guiding the south side walkway toward Conn_C_South_Side.",
    },
    {
        "placement_id": "CCD_Lantern_NorthConn_001",
        "common_asset_id": "CMN_Lantern_001",
        "category": "lighting",
        "position": (20.35, 15.2, 0.0),
        "rotation_deg": (0.0, 0.0, 0.0),
        "notes": "Ground guide lantern beside Conn_C_North_Side (clear of 2.6m walkway x=20.7..23.3).",
    },
    {
        "placement_id": "CCD_Lantern_SouthConn_001",
        "common_asset_id": "CMN_Lantern_001",
        "category": "lighting",
        "position": (20.35, -15.2, 0.0),
        "rotation_deg": (0.0, 0.0, 0.0),
        "notes": "Ground guide lantern beside Conn_C_South_Side (clear of 2.6m walkway x=20.7..23.3).",
    },
    {
        "placement_id": "CCD_Pumpkin_ArchNorth_001",
        "common_asset_id": "CMN_SmallPumpkin_001",
        "category": "prop",
        "position": (32.2, 3.75, 0.0),
        "rotation_deg": (0.0, 0.0, -60.0),
        "notes": "Jack-o'-Lantern accent at the north plinth of CCD_CandyArch_001.",
    },
    {
        "placement_id": "CCD_Pumpkin_ArchSouth_001",
        "common_asset_id": "CMN_SmallPumpkin_001",
        "category": "prop",
        "position": (32.2, -3.75, 0.0),
        "rotation_deg": (0.0, 0.0, -120.0),
        "notes": "Jack-o'-Lantern accent at the south plinth of CCD_CandyArch_001.",
    },
]


def _deduplicate_imported_materials() -> None:
    """Remap any `.001` duplicate materials created during `bpy.data.libraries.load` back to canonical materials."""
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.data is None:
            continue
        for slot in obj.material_slots:
            mat = slot.material
            if mat is not None and "." in mat.name:
                base_name = mat.name.split(".", 1)[0]
                base_mat = bpy.data.materials.get(base_name)
                if base_mat is not None:
                    slot.material = base_mat

    for mat in list(bpy.data.materials):
        if "." in mat.name and mat.users == 0:
            bpy.data.materials.remove(mat)


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


def _compute_world_bounds(objs: list[bpy.types.Object]) -> tuple[list[float], list[float]]:
    bpy.context.view_layer.update()
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for obj in objs:
        if obj.type == "MESH" and obj.data is not None:
            mw = obj.matrix_world
            for v in obj.data.vertices:
                wpt = mw @ v.co
                xs.append(float(wpt.x))
                ys.append(float(wpt.y))
                zs.append(float(wpt.z))
    if not xs:
        return [0.0, 0.0, 0.0], [1.0, 1.0, 1.0]
    return [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]


def _collect_material_names(objs: list[bpy.types.Object]) -> list[str]:
    names: set[str] = set()
    for obj in objs:
        if obj.type == "MESH" and obj.data is not None:
            for mat in obj.data.materials:
                if mat is not None:
                    names.add(mat.name)
    return sorted(names)


def _make_single_asset_entry(
    obj: bpy.types.Object,
    category: str,
    origin_policy: str,
    notes: str,
    is_placeholder: bool = False,
    future_target: str | None = None,
) -> dict[str, Any]:
    bpy.context.view_layer.update()
    tris, verts = _count_mesh_stats([obj])
    bmin, bmax = _compute_world_bounds([obj])
    origin_w = obj.matrix_world.translation
    local_min = [round(bmin[i] - float(origin_w[i]), 4) for i in range(3)]
    local_max = [round(bmax[i] - float(origin_w[i]), 4) for i in range(3)]
    width = round(max(0.01, local_max[0] - local_min[0]), 4)
    depth = round(max(0.01, local_max[1] - local_min[1]), 4)
    height = round(max(0.01, local_max[2] - local_min[2]), 4)
    mat_names = _collect_material_names([obj])

    return {
        "asset_id": obj.name,
        "key": KEY,
        "category": category,
        "area_id": AREA_ID,
        "collection": KEY,
        "blend_file": BLEND_REL_PATH,
        "script_file": SCRIPT_REL_PATH,
        "origin_policy": origin_policy,
        "origin_world": [
            round(float(origin_w.x), 4),
            round(float(origin_w.y), 4),
            round(float(origin_w.z), 4),
        ],
        "dimensions_m": {
            "width": width,
            "depth": depth,
            "height": height,
        },
        "bounds_local": {
            "min": local_min,
            "max": local_max,
        },
        "parts": [
            {
                "part_id": obj.name,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": origin_policy,
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
            "is_placeholder": is_placeholder,
            "modifiable": True,
            "notes": notes,
            "future_target": future_target,
        },
    }


def _make_multipart_asset_entry(
    asset_id: str,
    category: str,
    origin_policy: str,
    root_obj: bpy.types.Object,
    parts_spec: list[tuple[bpy.types.Object, str, bpy.types.Object | None, str]],
    motion_roots: list[str],
    visual_roots: list[str],
    attachment_points: list[str],
    notes: str,
    is_placeholder: bool = False,
    future_target: str | None = None,
) -> dict[str, Any]:
    bpy.context.view_layer.update()
    all_objs = [p[0] for p in parts_spec]
    tris, verts = _count_mesh_stats(all_objs)
    bmin, bmax = _compute_world_bounds(all_objs)
    origin_w = root_obj.matrix_world.translation
    local_min = [round(bmin[i] - float(origin_w[i]), 4) for i in range(3)]
    local_max = [round(bmax[i] - float(origin_w[i]), 4) for i in range(3)]
    width = round(max(0.01, local_max[0] - local_min[0]), 4)
    depth = round(max(0.01, local_max[1] - local_min[1]), 4)
    height = round(max(0.01, local_max[2] - local_min[2]), 4)
    mat_names = _collect_material_names(all_objs)

    parts_list: list[dict[str, Any]] = []
    for part_obj, role, parent_obj, part_origin_policy in parts_spec:
        if parent_obj is None or role == "asset_root":
            pivot_local = [0.0, 0.0, 0.0]
            parent_name = None
        else:
            pw = parent_obj.matrix_world.translation
            cw = part_obj.matrix_world.translation
            pivot_local = [
                round(float(cw.x - pw.x), 4),
                round(float(cw.y - pw.y), 4),
                round(float(cw.z - pw.z), 4),
            ]
            parent_name = parent_obj.name
        parts_list.append(
            {
                "part_id": part_obj.name,
                "role": role,
                "parent_part": parent_name,
                "origin_policy": part_origin_policy,
                "pivot_local": pivot_local,
            }
        )

    return {
        "asset_id": asset_id,
        "key": KEY,
        "category": category,
        "area_id": AREA_ID,
        "collection": KEY,
        "blend_file": BLEND_REL_PATH,
        "script_file": SCRIPT_REL_PATH,
        "origin_policy": origin_policy,
        "origin_world": [
            round(float(origin_w.x), 4),
            round(float(origin_w.y), 4),
            round(float(origin_w.z), 4),
        ],
        "dimensions_m": {
            "width": width,
            "depth": depth,
            "height": height,
        },
        "bounds_local": {
            "min": local_min,
            "max": local_max,
        },
        "parts": parts_list,
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
            "objects_count": len(parts_list),
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


def write_c_candy_layout(root: Path, manifest_assets: list[dict[str, Any]]) -> None:
    """Write `layout/areas/C_candy.json` conforming to `layout/schema/area_layout.schema.json` and `tools/check_data.py`."""
    assets_by_id = {a["asset_id"]: a for a in manifest_assets}
    common_rot_by_id = {
        spec["placement_id"]: [float(v) for v in spec["rotation_deg"]]
        for spec in COMMON_PLACEMENTS_SPEC
    }

    def _dims_vec(asset_id: str) -> list[float]:
        d = assets_by_id[asset_id]["dimensions_m"]
        return [float(d["width"]), float(d["depth"]), float(d["height"])]

    placements_list: list[dict[str, Any]] = []
    for asset in manifest_assets:
        aid = asset["asset_id"]
        if aid == "CCD_M04_CandyWorkshopProxy_001":
            rot_deg = [0.0, 0.0, 90.0]
        elif aid in common_rot_by_id:
            rot_deg = common_rot_by_id[aid]
        else:
            rot_deg = [0.0, 0.0, 0.0]
        dims = asset["dimensions_m"]
        clearance_r = round(0.5 * max(float(dims["width"]), float(dims["depth"])), 3)
        placements_list.append(
            {
                "placement_id": f"CCD_Place_{aid}",
                "asset_id": aid,
                "source_key": KEY,
                "category": asset["category"],
                "position": list(asset["origin_world"]),
                "rotation_euler_deg": rot_deg,
                "scale": [1.0, 1.0, 1.0],
                "origin_policy": asset["origin_policy"],
                "clearance_radius_m": clearance_r,
            }
        )

    area_layout: dict[str, Any] = {
        "schema_version": "1.0",
        "area_id": AREA_ID,
        "key": KEY,
        "name": "魔女のキャンディストリート",
        "area_name": "魔女のキャンディストリート",
        "theme": "甘いお菓子の街並み、光る大釜とキャンディ製造機、魔女の工房前広場",
        "updated_at": UPDATED_AT,
        "bounds": {
            "min": [20.0, -20.0, 0.0],
            "max": [48.0, 20.0, 14.0],
        },
        "bounds_m": {
            "bounds_min": [20.0, -20.0, 0.0],
            "bounds_max": [48.0, 20.0, 14.0],
            "center_m": [33.0, 0.0, 0.0],
            "ground_elevation_m": 0.0,
        },
        "Anchor": {
            "anchor_id": "ANC_C_CandyPlazaCenter",
            "position": [33.0, 0.0, 0.0],
            "dimensions_m": [28.0, 40.0, 14.0],
            "orientation_deg": 180.0,
            "forward_axis": "-X",
            "up_axis": "+Z",
            "role": "Area C central forecourt anchor at [33.0, 0.0, 0.0] beneath LM_C_CandyArch_001, facing -X West (180 deg) toward Central Plaza and framing the Witch Candy Workshop (M04) at [38.0, 0.0, 0.0].",
            "notes": "Area C central forecourt anchor at [33.0, 0.0, 0.0] beneath LM_C_CandyArch_001, facing -X West toward Central Plaza and framing the Witch Candy Workshop (M04) at [38.0, 0.0, 0.0].",
        },
        "Circulation": {
            "primary_path_id": "Route_East_Candy_Bridge",
            "min_walk_width_m": 2.6,
            "entry_points": [
                [20.0, 0.0, 0.0],
                [22.0, 16.0, 0.0],
                [22.0, -16.0, 0.0],
            ],
            "loop_description": (
                "Main 4.0m candy cobblestone boulevard from Conn_C_West_Main [20.0, 0.0, 0.0] through "
                "LM_C_CandyArch_001 [33.0, 0.0, 0.0] into the Witch Candy Workshop forecourt, joined by "
                "2.6m side walkways from Conn_C_North_Side [22.0, 16.0, 0.0] and Conn_C_South_Side [22.0, -16.0, 0.0]."
            ),
        },
        "Framing": {
            "left_edge": "North candy & potion stalls (CCD_SweetStall_NorthWest_001, CCD_PotionStall_NorthEast_001) and bubbling Magic Cauldron (CCD_MagicCauldron_001)",
            "right_edge": "South pastry & gumball stalls (CCD_PastryStall_SouthWest_001, CCD_GumballStall_SouthEast_001) and Mechanical Candy Machine (CCD_CandyMachine_001)",
            "focal_target": "LM_C_CandyArch_001 at [33.0, 0.0, 0.0] framing CCD_M04_CandyWorkshopProxy_001 at [38.0, 0.0, 0.0] and upper-air CCD_M08_FlyingWitchProxy_001 patrol loop",
            "view_cone_deg": 65.0,
        },
        "Story_Cluster": [
            {
                "cluster_id": "SC_C_CandyBoulevardStalls",
                "center": [28.4, 0.0, 0.0],
                "radius_m": 7.5,
                "intent": "Striped candy stalls, carnival garlands, and the self-sweeping magic broom (G12) flanking the main cobblestone promenade.",
                "asset_ids": [
                    "CCD_SweetStall_NorthWest_001",
                    "CCD_PotionStall_NorthEast_001",
                    "CCD_PastryStall_SouthWest_001",
                    "CCD_GumballStall_SouthEast_001",
                    "CCD_MagicBroom_001",
                ],
            },
            {
                "cluster_id": "SC_C_CauldronAlchemyCorner",
                "center": [33.8, 4.6, 0.0],
                "radius_m": 3.2,
                "intent": "Bubbling magic cauldron (G09) with stirring rod and interactive color-switching crystal lectern (I02).",
                "asset_ids": [
                    "CCD_MagicCauldron_001",
                    "CCD_CauldronColorControl_001",
                ],
            },
            {
                "cluster_id": "SC_C_CandyFactoryForecourt",
                "center": [36.2, -2.4, 0.0],
                "radius_m": 5.5,
                "intent": "Landmark Candy Arch (LM_C_CandyArch_001), Witch's Candy Workshop facade (M04), and Mechanical Candy Machine (G10).",
                "asset_ids": [
                    "CCD_CandyArch_001",
                    "CCD_M04_CandyWorkshopProxy_001",
                    "CCD_CandyMachine_001",
                ],
            },
            {
                "cluster_id": "SC_C_SkyWitchPatrol",
                "center": [33.0, 0.0, 10.2],
                "radius_m": 10.5,
                "intent": "Closed 8-waypoint upper-air witch patrol loop (G11) and Flying Witch on broom (M08) circling above the candy street.",
                "asset_ids": [
                    "CCD_WitchPatrolLoop_001",
                    "CCD_M08_FlyingWitchProxy_001",
                ],
            },
        ],
        "Exclusions": [
            {
                "zone_id": "EX_C_MainBoulevardWalkway",
                "bounds": {
                    "min": [20.0, -2.0, 0.0],
                    "max": [35.3, 2.0, 4.5],
                },
                "reason": "Keep 4.0m main candy street walkway and Conn_C_West_Main approach clear of static obstacles.",
            },
            {
                "zone_id": "EX_C_NorthSideWalkway",
                "bounds": {
                    "min": [20.7, 3.4, 0.0],
                    "max": [23.3, 16.0, 4.0],
                },
                "reason": "Keep 2.6m north side walkway to Conn_C_North_Side clear of static obstacles.",
            },
            {
                "zone_id": "EX_C_SouthSideWalkway",
                "bounds": {
                    "min": [20.7, -16.0, 0.0],
                    "max": [23.3, -3.4, 4.0],
                },
                "reason": "Keep 2.6m south side walkway to Conn_C_South_Side clear of static obstacles.",
            },
            {
                "zone_id": "EX_C_SkyPatrolCorridor",
                "bounds": {
                    "min": [23.5, -10.8, 9.0],
                    "max": [44.2, 10.8, 12.2],
                },
                "reason": "Keep upper-air G11/M08 flying witch patrol corridor clear of tall spires.",
            },
        ],
        "Path": [
            {
                "path_id": "Path_C_Main_CandyBoulevard",
                "waypoints": [
                    [20.0, 0.0, 0.0],
                    [26.5, 0.0, 0.0],
                    [33.0, 0.0, 0.0],
                    [35.0, 0.0, 0.0],
                ],
                "width_m": 4.0,
                "clear_height_m": 4.5,
                "connects_to": [
                    "Conn_C_West_Main",
                    "ANC_C_CandyPlazaCenter",
                ],
            },
            {
                "path_id": "Path_C_North_SideLink",
                "waypoints": [
                    [22.0, 16.0, 0.0],
                    [22.0, 3.4, 0.0],
                    [26.5, 3.4, 0.0],
                    [33.0, 0.0, 0.0],
                ],
                "width_m": 2.6,
                "clear_height_m": 4.0,
                "connects_to": [
                    "Conn_C_North_Side",
                    "Path_C_Main_CandyBoulevard",
                ],
            },
            {
                "path_id": "Path_C_South_SideLink",
                "waypoints": [
                    [22.0, -16.0, 0.0],
                    [22.0, -3.4, 0.0],
                    [26.5, -3.4, 0.0],
                    [33.0, 0.0, 0.0],
                ],
                "width_m": 2.6,
                "clear_height_m": 4.0,
                "connects_to": [
                    "Conn_C_South_Side",
                    "Path_C_Main_CandyBoulevard",
                ],
            },
        ],
        "Building_Shell": [
            {
                "building_id": "BS_C_CandyArch_001",
                "asset_id": "CCD_CandyArch_001",
                "position": [33.0, 0.0, 0.0],
                "rotation_deg": [0.0, 0.0, 0.0],
                "dimensions_m": _dims_vec("CCD_CandyArch_001"),
                "entrance_side": "-X",
                "is_enterable": True,
                "landmark_id": "LM_C_CandyArch_001",
                "clear_opening_width_m": 5.4,
                "clear_opening_height_m": 5.85,
            },
            {
                "building_id": "BS_C_CandyWorkshop_001",
                "asset_id": "CCD_M04_CandyWorkshopProxy_001",
                "position": [38.0, 0.0, 0.0],
                "rotation_deg": [0.0, 0.0, 90.0],
                "dimensions_m": _dims_vec("CCD_M04_CandyWorkshopProxy_001"),
                "entrance_side": "-X",
                "is_enterable": False,
                "meshy_id": "M04",
                "replacement_target": "M04_WitchCandyWorkshop_001",
                "local_dimensions_m": [8.0, 5.367, 7.628],
                "front_local": "+Y",
                "front_world": "-X",
            },
            {
                "building_id": "BS_C_SweetStall_NW_001",
                "asset_id": "CCD_SweetStall_NorthWest_001",
                "position": [26.2, 5.8, 0.0],
                "rotation_deg": [0.0, 0.0, 0.0],
                "dimensions_m": _dims_vec("CCD_SweetStall_NorthWest_001"),
                "entrance_side": "-Y",
                "is_enterable": False,
            },
            {
                "building_id": "BS_C_PotionStall_NE_001",
                "asset_id": "CCD_PotionStall_NorthEast_001",
                "position": [30.6, 6.2, 0.0],
                "rotation_deg": [0.0, 0.0, 0.0],
                "dimensions_m": _dims_vec("CCD_PotionStall_NorthEast_001"),
                "entrance_side": "-Y",
                "is_enterable": False,
            },
            {
                "building_id": "BS_C_PastryStall_SW_001",
                "asset_id": "CCD_PastryStall_SouthWest_001",
                "position": [26.2, -5.8, 0.0],
                "rotation_deg": [0.0, 0.0, 0.0],
                "dimensions_m": _dims_vec("CCD_PastryStall_SouthWest_001"),
                "entrance_side": "+Y",
                "is_enterable": False,
            },
            {
                "building_id": "BS_C_GumballStall_SE_001",
                "asset_id": "CCD_GumballStall_SouthEast_001",
                "position": [30.6, -6.2, 0.0],
                "rotation_deg": [0.0, 0.0, 0.0],
                "dimensions_m": _dims_vec("CCD_GumballStall_SouthEast_001"),
                "entrance_side": "+Y",
                "is_enterable": False,
            },
        ],
        "Hero_or_Gimmick": [
            {
                "gimmick_id": "G09",
                "asset_id": "CCD_MagicCauldron_001",
                "type": "animation_effect",
                "position": [34.4, 5.2, 0.0],
                "rotation_deg": [0.0, 0.0, 0.0],
                "pivot_policy": "hinge_pivot",
                "motion_axis": "+Z",
                "motion_range": [0.0, 360.0],
                "clear_radius_m": 1.4,
                "sub_parts": {
                    "vessel_body": "CCD_MagicCauldron_001_Body",
                    "liquid_surface": "CCD_MagicCauldron_001_Liquid",
                    "stir_rod_pivot": "CCD_MagicCauldron_001_StirRodPivot",
                    "stir_rod_mesh": "CCD_MagicCauldron_001_StirRod",
                    "bubble_emitter_attach": "CCD_MagicCauldron_001_BubbleAttach",
                    "smoke_audio_attach": "CCD_MagicCauldron_001_SmokeAttach",
                },
                "rest_pose": {
                    "stir_rod_pivot_local_m": [0.0, 0.0, 1.16],
                    "stir_rod_rotation_deg": [0.0, 0.0, 0.0],
                    "wobble_tilt_deg": [-12.0, 12.0],
                },
            },
            {
                "gimmick_id": "I02",
                "asset_id": "CCD_CauldronColorControl_001",
                "type": "interactive_color_switch",
                "position": [33.0, 3.8, 0.0],
                "rotation_deg": [0.0, 0.0, 0.0],
                "pivot_policy": "hinge_pivot",
                "motion_axis": "+Z",
                "motion_range": [0.0, 360.0],
                "clear_radius_m": 0.65,
                "target_gimmick_id": "G09",
                "target_liquid_object": "CCD_MagicCauldron_001_Liquid",
                "target_bubble_attach": "CCD_MagicCauldron_001_BubbleAttach",
                "sub_parts": {
                    "pedestal": "CCD_CauldronColorControl_001_Pedestal",
                    "switch_pivot": "CCD_CauldronColorControl_001_SwitchPivot",
                    "crystal_orb": "CCD_CauldronColorControl_001_CrystalOrb",
                    "touch_attach": "CCD_CauldronColorControl_001_TouchAttach",
                },
                "color_presets": [
                    {"name": "EmeraldPotion", "color_hex": "#2EFF88"},
                    {"name": "MagentaElixir", "color_hex": "#F53DC7"},
                    {"name": "AmberPumpkin", "color_hex": "#FFB338"},
                ],
            },
            {
                "gimmick_id": "G10",
                "asset_id": "CCD_CandyMachine_001",
                "type": "mechanical_rotation",
                "position": [34.4, -5.2, 0.0],
                "rotation_deg": [0.0, 0.0, 0.0],
                "pivot_policy": "hinge_pivot",
                "motion_axis": "+X",
                "motion_range": [0.0, 360.0],
                "clear_radius_m": 1.35,
                "sub_parts": {
                    "body": "CCD_CandyMachine_001_Body",
                    "gear_main_pivot": "CCD_CandyMachine_001_GearMainPivot",
                    "gear_main": "CCD_CandyMachine_001_GearMain",
                    "gear_sub_pivot": "CCD_CandyMachine_001_GearSubPivot",
                    "gear_sub": "CCD_CandyMachine_001_GearSub",
                    "extruder_pivot": "CCD_CandyMachine_001_ExtruderPivot",
                    "extruder": "CCD_CandyMachine_001_Extruder",
                    "chute": "CCD_CandyMachine_001_Chute",
                    "outlet_attach": "CCD_CandyMachine_001_OutletAttach",
                },
                "motion_channels": {
                    "gear_main": {"pivot": "CCD_CandyMachine_001_GearMainPivot", "axis": "+X", "range_deg": [0.0, 360.0]},
                    "gear_sub": {"pivot": "CCD_CandyMachine_001_GearSubPivot", "axis": "-X", "range_deg": [0.0, -360.0]},
                    "extruder": {"pivot": "CCD_CandyMachine_001_ExtruderPivot", "axis": "+Y", "stroke_m": [0.0, 0.28]},
                },
            },
            {
                "gimmick_id": "G12",
                "asset_id": "CCD_MagicBroom_001",
                "type": "sweeping_motion",
                "position": [28.5, 3.2, 0.05],
                "rotation_deg": [0.0, 0.0, 0.0],
                "pivot_policy": "hinge_pivot",
                "motion_axis": "+Z",
                "motion_range": [-28.0, 28.0],
                "clear_radius_m": 0.75,
                "sub_parts": {
                    "motion_root": "CCD_MagicBroom_001",
                    "broom_mesh": "CCD_MagicBroom_001_BroomMesh",
                    "sweep_dust_attach": "CCD_MagicBroom_001_SweepAttach",
                },
                "motion_channels": {
                    "yaw_deg": [-28.0, 28.0],
                    "pitch_deg": [-14.0, 14.0],
                    "slide_x_m": [-0.45, 0.45],
                },
            },
            {
                "gimmick_id": "G11",
                "asset_id": "CCD_WitchPatrolLoop_001",
                "type": "patrol_loop",
                "position": [33.0, 0.0, 0.0],
                "rotation_deg": [0.0, 0.0, 0.0],
                "pivot_policy": "hinge_pivot",
                "motion_axis": "+Z",
                "motion_range": [0.0, 360.0],
                "clear_radius_m": 10.5,
                "rider_asset_id": "CCD_M08_FlyingWitchProxy_001",
                "meshy_replacement_target": "M08_FlyingWitch_001",
                "meshy_id": "M08",
                "patrol_loop_closed": True,
                "patrol_loop_waypoints_m": [list(pt) for pt in PATROL_LOOP_WAYPOINTS_WORLD],
                "min_altitude_m": 9.8,
                "max_altitude_m": 10.5,
                "min_clearance_above_roof_m": 1.96,
            },
            {
                "gimmick_id": "M08_Hero",
                "asset_id": "CCD_M08_FlyingWitchProxy_001",
                "type": "patrol_rider_proxy",
                "position": [43.2, 0.0, 10.2],
                "rotation_deg": [0.0, 0.0, 0.0],
                "pivot_policy": "hinge_pivot",
                "motion_axis": "+Y",
                "motion_range": [0.0, 360.0],
                "clear_radius_m": 1.35,
                "meshy_id": "M08",
                "replacement_target": "M08_FlyingWitch_001",
                "front_local": "+Y",
                "bounds_local_m": {
                    "min": [-0.637, -1.215, -0.612],
                    "max": [0.905, 0.912, 1.888],
                },
                "points_local_m": {
                    "broom_tip": [0.0, 0.91, 0.214],
                    "bristle_end_centre": [0.0, -1.043, -0.245],
                },
            },
            {
                "gimmick_id": "M04_Hero",
                "asset_id": "CCD_M04_CandyWorkshopProxy_001",
                "type": "landmark_building_proxy",
                "position": [38.0, 0.0, 0.0],
                "rotation_deg": [0.0, 0.0, 90.0],
                "pivot_policy": "ground_center",
                "motion_axis": "+Z",
                "motion_range": [0.0, 0.0],
                "clear_radius_m": 4.2,
                "meshy_id": "M04",
                "replacement_target": "M04_WitchCandyWorkshop_001",
                "front_local": "+Y",
                "front_world": "-X",
                "local_dimensions_m": [8.0, 5.367, 7.628],
                "points_local_m": {
                    "door_bottom_centre": [-0.006, 2.128, 0.116],
                    "door_top_centre": [-0.006, 2.128, 2.009],
                    "bay_window_centre": [2.096, 2.506, 1.126],
                    "shop_window_centre": [-2.13, 2.632, 0.979],
                    "upper_window_centre": [1.339, 2.086, 3.312],
                    "dormer_window_centre": [-2.277, 2.002, 3.354],
                },
            },
        ],
        "Obstacle": [
            {
                "obstacle_id": "OBS_C_CauldronSafetyZone",
                "position": [34.4, 5.2, 0.0],
                "dimensions_m": [2.2, 2.2, 2.2],
                "keep_out_m": 0.4,
            },
            {
                "obstacle_id": "OBS_C_CandyMachineSafetyZone",
                "position": [34.4, -5.2, 0.0],
                "dimensions_m": [2.0, 2.4, 3.2],
                "keep_out_m": 0.4,
            },
            {
                "obstacle_id": "OBS_C_WorkshopFootprintZone",
                "position": [38.0, 0.0, 0.0],
                "dimensions_m": [5.367, 8.0, 7.628],
                "keep_out_m": 0.3,
            },
        ],
        "Light_Anchor": [
            {
                "light_id": "LA_C_CandyArchCrown_001",
                "position": [33.0, 0.0, 5.6],
                "color_hex": "#FFB347",
                "intensity": 3.5,
                "range_m": 12.0,
            },
            {
                "light_id": "LA_C_CauldronGlow_001",
                "position": [34.4, 5.2, 1.35],
                "color_hex": "#2EFF88",
                "intensity": 4.0,
                "range_m": 8.5,
            },
            {
                "light_id": "LA_C_CandyMachineGlow_001",
                "position": [34.4, -5.2, 2.0],
                "color_hex": "#FF3EC8",
                "intensity": 3.2,
                "range_m": 8.0,
            },
            {
                "light_id": "LA_C_WorkshopEntrance_001",
                "position": [35.4, 0.0, 2.2],
                "color_hex": "#FFC45C",
                "intensity": 3.0,
                "range_m": 10.0,
            },
            {
                "light_id": "LA_C_PatrolLoopStarlight_001",
                "position": [33.0, 0.0, 10.2],
                "color_hex": "#6BE0FF",
                "intensity": 2.5,
                "range_m": 18.0,
            },
        ],
        "Viewpoint": [
            {
                "viewpoint_id": "VP_C_WestStreetEntry",
                "position": [21.2, 0.0, 1.7],
                "look_at": [35.0, 0.0, 3.8],
                "fov_deg": 60.0,
            },
            {
                "viewpoint_id": "VP_C_PlazaForecourt",
                "position": [30.2, -1.8, 1.7],
                "look_at": [36.5, 1.2, 2.8],
                "fov_deg": 60.0,
            },
            {
                "viewpoint_id": "VP_C_SkyPatrolWatch",
                "position": [28.0, -4.0, 1.7],
                "look_at": [36.0, 2.0, 9.8],
                "fov_deg": 65.0,
            },
        ],
        "Common_Placement": [
            {
                "placement_id": spec["placement_id"],
                "common_asset_id": spec["common_asset_id"],
                "instance_name": spec["placement_id"],
                "position": list(spec["position"]),
                "rotation_deg": list(spec["rotation_deg"]),
                "rotation_euler_deg": list(spec["rotation_deg"]),
                "scale": [1.0, 1.0, 1.0],
                "role": spec["notes"],
            }
            for spec in COMMON_PLACEMENTS_SPEC
        ],
        "placements": placements_list,
    }

    layout_path = root / AREA_LAYOUT_REL_PATH
    layout_path.parent.mkdir(parents=True, exist_ok=True)
    layout_path.write_text(
        json.dumps(area_layout, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_c_candy_manifest(root: Path, manifest_assets: list[dict[str, Any]]) -> None:
    """Write `assets/manifest/C_candy.json` conforming to `assets/schema/manifest.schema.json`."""
    manifest_data: dict[str, Any] = {
        "schema_version": "1.0",
        "key": KEY,
        "updated_at": UPDATED_AT,
        "assets": manifest_assets,
    }
    manifest_path = root / MANIFEST_REL_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_c_candy() -> dict[str, Any]:
    """Deterministically build Area C (`C_candy`), render review views, save `.blend`, and emit JSONs."""
    _scene, c_col = reset_scene(KEY, seed=404)
    mats = get_candy_materials()

    paving_obj = build_candy_street_paving(c_col, mats)
    arch_obj = build_candy_arch(c_col, mats)
    m04_obj = build_m04_workshop_proxy(c_col, mats)

    stall_nw_obj = build_candy_stall(
        "CCD_SweetStall_NorthWest_001",
        c_col,
        mats,
        location=(26.2, 5.8, 0.0),
        facing_sign_y=-1.0,
        awning_mat_key="candy_red",
        glow_mat_key="amber_window",
        roof_height=4.6,
    )
    stall_ne_obj = build_candy_stall(
        "CCD_PotionStall_NorthEast_001",
        c_col,
        mats,
        location=(30.6, 6.2, 0.0),
        facing_sign_y=-1.0,
        awning_mat_key="candy_mint",
        glow_mat_key="potion_emerald",
        roof_height=4.8,
    )
    stall_sw_obj = build_candy_stall(
        "CCD_PastryStall_SouthWest_001",
        c_col,
        mats,
        location=(26.2, -5.8, 0.0),
        facing_sign_y=1.0,
        awning_mat_key="pumpkin_orange",
        glow_mat_key="amber_window",
        roof_height=4.5,
    )
    stall_se_obj = build_candy_stall(
        "CCD_GumballStall_SouthEast_001",
        c_col,
        mats,
        location=(30.6, -6.2, 0.0),
        facing_sign_y=1.0,
        awning_mat_key="candy_red",
        glow_mat_key="potion_magenta",
        roof_height=4.7,
    )

    cauldron_parts = build_magic_cauldron(c_col, mats)
    control_parts = build_cauldron_color_control(c_col, mats)
    machine_parts = build_candy_machine(c_col, mats)
    broom_parts = build_magic_broom(c_col, mats)
    m08_obj = build_m08_flying_witch_proxy(c_col, mats)
    patrol_parts = build_witch_patrol_loop(c_col, mats)

    common_blend_path = PROJECT_ROOT / "blender" / "common" / "common.blend"
    appended_common_entries: list[dict[str, Any]] = []
    for spec in COMMON_PLACEMENTS_SPEC:
        inst_obj = append_common_part(
            common_blend_path=common_blend_path,
            source_object_name=spec["common_asset_id"],
            instance_name=spec["placement_id"],
            collection=c_col,
            location=spec["position"],
            rotation_euler_deg=spec["rotation_deg"],
        )
        appended_common_entries.append((inst_obj, spec))

    _deduplicate_imported_materials()
    bpy.context.view_layer.update()

    manifest_assets: list[dict[str, Any]] = [
        _make_single_asset_entry(
            paving_obj,
            category="terrain",
            origin_policy="ground_center",
            notes="Candy cobblestone main street (x=20..35.3, width 4.0m), workshop forecourt medallion plaza, and North/South side paths to Conn_C_North_Side and Conn_C_South_Side.",
        ),
        _make_single_asset_entry(
            arch_obj,
            category="architecture",
            origin_policy="ground_center",
            notes="Landmark LM_C_CandyArch_001 at [33.0, 0.0, 0.0] (height 9.5m, clear opening width 5.4m, clear height 5.85m) with twisted candy-cane columns, lollipop shoulders, and witch-hat pumpkin spire.",
        ),
        _make_single_asset_entry(
            m04_obj,
            category="architecture",
            origin_policy="ground_center",
            notes=(
                "Meshy M04 proxy (Witch's Candy Workshop exterior) at [38.0, 0.0, 0.0], rotation_z_deg=90.0 "
                "(local +Y front faces -X West toward Candy Street). Local dimensions 8.0 x 5.367 x 7.628 m "
                "(world AABB 5.367 x 8.0 x 7.628 m); matches W09 received.json scale=4.2052, yaw_deg=180.0, "
                "and relief door/window feature coordinates."
            ),
            is_placeholder=True,
            future_target="M04_WitchCandyWorkshop_001",
        ),
        _make_single_asset_entry(
            stall_nw_obj,
            category="architecture",
            origin_policy="ground_center",
            notes="North-West striped awning candy stall facing -Y toward the Candy Street.",
        ),
        _make_single_asset_entry(
            stall_ne_obj,
            category="architecture",
            origin_policy="ground_center",
            notes="North-East witch potion & confection stall facing -Y toward the Candy Street.",
        ),
        _make_single_asset_entry(
            stall_sw_obj,
            category="architecture",
            origin_policy="ground_center",
            notes="South-West pumpkin-tart & cupcake stall facing +Y toward the Candy Street.",
        ),
        _make_single_asset_entry(
            stall_se_obj,
            category="architecture",
            origin_policy="ground_center",
            notes="South-East syrup & gumball stall facing +Y toward the Candy Street.",
        ),
        _make_multipart_asset_entry(
            asset_id="CCD_MagicCauldron_001",
            category="gimmick",
            origin_policy="ground_center",
            root_obj=cauldron_parts["root"],
            parts_spec=[
                (cauldron_parts["root"], "asset_root", None, "ground_center"),
                (cauldron_parts["body"], "static_part", cauldron_parts["root"], "ground_center"),
                (cauldron_parts["liquid"], "static_part", cauldron_parts["root"], "ground_center"),
                (cauldron_parts["stir_pivot"], "motion_root", cauldron_parts["root"], "hinge_pivot"),
                (cauldron_parts["stir_rod"], "visual_root", cauldron_parts["stir_pivot"], "hinge_pivot"),
                (cauldron_parts["bubble_attach"], "attachment_point", cauldron_parts["liquid"], "attachment_point"),
                (cauldron_parts["smoke_attach"], "attachment_point", cauldron_parts["root"], "attachment_point"),
            ],
            motion_roots=["CCD_MagicCauldron_001_StirRodPivot"],
            visual_roots=[
                "CCD_MagicCauldron_001_Body",
                "CCD_MagicCauldron_001_Liquid",
                "CCD_MagicCauldron_001_StirRod",
            ],
            attachment_points=[
                "CCD_MagicCauldron_001_BubbleAttach",
                "CCD_MagicCauldron_001_SmokeAttach",
            ],
            notes=(
                "G09 & I02 Magic Cauldron assembly at [34.4, 5.2, 0.0]: separate vessel body, color-switchable "
                "liquid surface (z=1.12m), stirring rod pivot (z=1.16m, +Z continuous 0..360 deg + ±12 deg tilt), "
                "and bubble/smoke attachment points."
            ),
        ),
        _make_multipart_asset_entry(
            asset_id="CCD_CauldronColorControl_001",
            category="gimmick",
            origin_policy="ground_center",
            root_obj=control_parts["root"],
            parts_spec=[
                (control_parts["root"], "asset_root", None, "ground_center"),
                (control_parts["pedestal"], "static_part", control_parts["root"], "ground_center"),
                (control_parts["switch_pivot"], "motion_root", control_parts["root"], "hinge_pivot"),
                (control_parts["crystal_orb"], "visual_root", control_parts["switch_pivot"], "hinge_pivot"),
                (control_parts["touch_attach"], "attachment_point", control_parts["switch_pivot"], "attachment_point"),
            ],
            motion_roots=["CCD_CauldronColorControl_001_SwitchPivot"],
            visual_roots=[
                "CCD_CauldronColorControl_001_Pedestal",
                "CCD_CauldronColorControl_001_CrystalOrb",
            ],
            attachment_points=["CCD_CauldronColorControl_001_TouchAttach"],
            notes=(
                "I02 Interactive Cauldron Color Control pedestal at [33.0, 3.8, 0.0] facing the forecourt: "
                "switches CCD_MagicCauldron_001_Liquid and bubble emission between Emerald, Magenta, and Amber."
            ),
        ),
        _make_multipart_asset_entry(
            asset_id="CCD_CandyMachine_001",
            category="gimmick",
            origin_policy="ground_center",
            root_obj=machine_parts["root"],
            parts_spec=[
                (machine_parts["root"], "asset_root", None, "ground_center"),
                (machine_parts["body"], "static_part", machine_parts["root"], "ground_center"),
                (machine_parts["gear_main_pivot"], "motion_root", machine_parts["root"], "hinge_pivot"),
                (machine_parts["gear_main"], "visual_root", machine_parts["gear_main_pivot"], "hinge_pivot"),
                (machine_parts["gear_sub_pivot"], "motion_root", machine_parts["root"], "hinge_pivot"),
                (machine_parts["gear_sub"], "visual_root", machine_parts["gear_sub_pivot"], "hinge_pivot"),
                (machine_parts["extruder_pivot"], "motion_root", machine_parts["root"], "hinge_pivot"),
                (machine_parts["extruder"], "visual_root", machine_parts["extruder_pivot"], "hinge_pivot"),
                (machine_parts["chute"], "static_part", machine_parts["root"], "ground_center"),
                (machine_parts["outlet_attach"], "attachment_point", machine_parts["chute"], "attachment_point"),
            ],
            motion_roots=[
                "CCD_CandyMachine_001_GearMainPivot",
                "CCD_CandyMachine_001_GearSubPivot",
                "CCD_CandyMachine_001_ExtruderPivot",
            ],
            visual_roots=[
                "CCD_CandyMachine_001_Body",
                "CCD_CandyMachine_001_GearMain",
                "CCD_CandyMachine_001_GearSub",
                "CCD_CandyMachine_001_Extruder",
                "CCD_CandyMachine_001_Chute",
            ],
            attachment_points=["CCD_CandyMachine_001_OutletAttach"],
            notes=(
                "G10 Mechanical Candy Machine at [34.4, -5.2, 0.0] with separate cabinet/globe body, "
                "counter-rotating main & sub gears (X axis), reciprocating candy extruder piston (+Y stroke 0..0.28m), "
                "delivery chute, and candy spawn outlet attachment point."
            ),
        ),
        _make_multipart_asset_entry(
            asset_id="CCD_MagicBroom_001",
            category="gimmick",
            origin_policy="hinge_pivot",
            root_obj=broom_parts["root"],
            parts_spec=[
                (broom_parts["root"], "asset_root", None, "hinge_pivot"),
                (broom_parts["broom"], "visual_root", broom_parts["root"], "hinge_pivot"),
                (broom_parts["sweep_attach"], "attachment_point", broom_parts["broom"], "attachment_point"),
            ],
            motion_roots=["CCD_MagicBroom_001"],
            visual_roots=["CCD_MagicBroom_001_BroomMesh"],
            attachment_points=["CCD_MagicBroom_001_SweepAttach"],
            notes=(
                "G12 Self-Sweeping Magic Broom with floor-near pivot at [28.5, 3.2, 0.05] "
                "(yaw ±28 deg, pitch ±14 deg, local X slide ±0.45m, outside main walkway)."
            ),
        ),
        _make_single_asset_entry(
            m08_obj,
            category="gimmick",
            origin_policy="hinge_pivot",
            notes=(
                "Meshy M08 proxy (Flying Witch on broom) at patrol loop Waypoint 0 [43.2, 0.0, 10.2], "
                "rotation=(0,0,0), front_local=+Y, exact dimensions 1.542 x 2.126 x 2.5 m "
                "(bounds_local min [-0.637, -1.215, -0.612], max [0.905, 0.912, 1.888]); "
                "matches W09 received.json scale=1.3125, yaw_deg=-124.25."
            ),
            is_placeholder=True,
            future_target="M08_FlyingWitch_001",
        ),
        _make_multipart_asset_entry(
            asset_id="CCD_WitchPatrolLoop_001",
            category="sky_boundary",
            origin_policy="ground_center",
            root_obj=patrol_parts["root"],
            parts_spec=[
                (patrol_parts["root"], "asset_root", None, "ground_center"),
                (patrol_parts["guide_ring"], "static_part", patrol_parts["root"], "ground_center"),
                (patrol_parts["carrier_pivot"], "motion_root", patrol_parts["root"], "hinge_pivot"),
                (patrol_parts["carrier_attach"], "attachment_point", patrol_parts["carrier_pivot"], "attachment_point"),
            ],
            motion_roots=["CCD_WitchPatrolLoop_001_CarrierPivot"],
            visual_roots=["CCD_WitchPatrolLoop_001_GuideRing"],
            attachment_points=["CCD_WitchPatrolLoop_001_CarrierAttach"],
            notes=(
                "G11 Upper-air closed 8-waypoint patrol loop over Area C (x=24.5..43.2, y=-9.5..9.5, z=9.8..10.5m) "
                "with starlight guide ribbon, 8 waypoint beacons, and carrier pivot/attachment at [43.2, 0.0, 10.2] "
                "for M08_FlyingWitch_001 (>=1.96m vertical clearance above M04 roof)."
            ),
        ),
    ]

    for inst_obj, spec in appended_common_entries:
        manifest_assets.append(
            _make_single_asset_entry(
                inst_obj,
                category=spec["category"],
                origin_policy="ground_center",
                notes=f"{spec['notes']} (Appended from {spec['common_asset_id']}).",
            )
        )

    overview_png = PROJECT_ROOT / "review" / "C_candy" / "01_candy_street_overview.png"
    gimmicks_png = PROJECT_ROOT / "review" / "C_candy" / "02_gimmicks_and_pivots.png"
    connections_png = PROJECT_ROOT / "review" / "C_candy" / "03_connections_and_patrol.png"

    render_review_images(
        views=[
            {
                "filepath": overview_png,
                "location": (19.5, -2.6, 3.6),
                "target": (34.5, 0.0, 4.2),
                "lens_mm": 24.0,
            },
            {
                "filepath": gimmicks_png,
                "location": (26.5, -1.2, 3.4),
                "target": (34.8, 0.2, 1.9),
                "lens_mm": 18.0,
            },
            {
                "filepath": connections_png,
                "location": (18.5, -18.5, 16.5),
                "target": (33.5, 0.5, 3.5),
                "lens_mm": 22.0,
            },
        ],
        width=1280,
        height=720,
        samples=32,
    )

    blend_path = PROJECT_ROOT / BLEND_REL_PATH
    save_blend(blend_path, pack_images=True)

    write_c_candy_manifest(PROJECT_ROOT, manifest_assets)
    write_c_candy_layout(PROJECT_ROOT, manifest_assets)

    summary = {
        "key": KEY,
        "blend_file": BLEND_REL_PATH,
        "manifest_file": MANIFEST_REL_PATH,
        "layout_file": AREA_LAYOUT_REL_PATH,
        "assets_count": len(manifest_assets),
        "objects_count": len(c_col.all_objects),
        "meshes_count": len(bpy.data.meshes),
        "materials_count": len(bpy.data.materials),
        "review_images": [
            str(overview_png.relative_to(PROJECT_ROOT)),
            str(gimmicks_png.relative_to(PROJECT_ROOT)),
            str(connections_png.relative_to(PROJECT_ROOT)),
        ],
    }
    print("C_CANDY_BUILD_SUMMARY:" + json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    build_c_candy()
