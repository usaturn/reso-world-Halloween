"""Deterministically build `blender/world/world.blend`, render `review/world/`, and emit world layout/manifest JSONs.

Run via:
    resoloop blender run modeling/world/build.py --json
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

from modeling.common.build import BLEND_REL_PATH as COMMON_BLEND_REL_PATH
from modeling.common.build import build_common
from modeling.lib.common_parts import append_common_part
from modeling.lib.materials import create_pbr_material
from modeling.lib.render import render_review_images
from modeling.lib.scene import reset_scene, save_blend
from modeling.world.layout_data import (
    build_world_area_layout_dict,
    build_world_layout_dict,
)

KEY = "world"
BLEND_REL_PATH = "blender/world/world.blend"
SCRIPT_REL_PATH = "modeling/world/build.py"
WORLD_LAYOUT_REL_PATH = "layout/world_layout.json"
AREA_LAYOUT_REL_PATH = "layout/areas/world.json"
MANIFEST_REL_PATH = "assets/manifest/world.json"


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
    segments: int = 16,
    material_index: int = 0,
    top_material_index: int | None = None,
) -> None:
    """Add a vertical n-gon frustum from z0 (radius r0) to z1 (radius r1)."""
    cx, cy = center_xy
    top_mat = material_index if top_material_index is None else top_material_index
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
        f_top.material_index = top_mat
        for i, loop in enumerate(f_top.loops):
            ang = 2.0 * math.pi * i / segments
            loop[uv_layer].uv = (0.5 + 0.45 * math.cos(ang), 0.5 + 0.45 * math.sin(ang))


def _add_annulus_z(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    r_inner: float,
    r_outer: float,
    z0: float,
    z1: float,
    segments: int = 32,
    material_index: int = 0,
) -> None:
    """Add a flat ring (annulus) between r_inner and r_outer from z0 to z1 centered at (0,0)."""
    in_bot = []
    in_top = []
    out_bot = []
    out_top = []
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        in_bot.append(bm.verts.new((r_inner * ca, r_inner * sa, z0)))
        in_top.append(bm.verts.new((r_inner * ca, r_inner * sa, z1)))
        out_bot.append(bm.verts.new((r_outer * ca, r_outer * sa, z0)))
        out_top.append(bm.verts.new((r_outer * ca, r_outer * sa, z1)))

    uv_quad = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    for i in range(segments):
        jn = (i + 1) % segments
        quads = [
            [in_top[i], out_top[i], out_top[jn], in_top[jn]],  # Top (+Z)
            [out_bot[i], in_bot[i], in_bot[jn], out_bot[jn]],  # Bottom (-Z)
            [out_bot[i], out_bot[jn], out_top[jn], out_top[i]],  # Outer rim
            [in_bot[jn], in_bot[i], in_top[i], in_top[jn]],  # Inner rim
        ]
        for verts in quads:
            f = bm.faces.new(verts)
            f.material_index = material_index
            for loop, uv in zip(f.loops, uv_quad):
                loop[uv_layer].uv = uv


def _add_oriented_beam(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    p0: tuple[float, float, float],
    p1: tuple[float, float, float],
    width: float,
    thickness: float,
    material_index: int = 0,
) -> None:
    """Add a 3D deck/beam or rail from p0 to p1 with horizontal width (perpendicular in XY) and vertical thickness (in Z)."""
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    horiz_len = math.hypot(dx, dy)
    if horiz_len < 1e-5:
        _add_box(
            bm,
            uv_layer,
            (p0[0] - 0.5 * width, p0[1] - 0.5 * width, min(p0[2], p1[2])),
            (p0[0] + 0.5 * width, p0[1] + 0.5 * width, max(p0[2], p1[2]) + thickness),
            material_index=material_index,
        )
        return

    # Unit right vector in XY perpendicular to p0->p1
    rx = dy / horiz_len
    ry = -dx / horiz_len
    hw = 0.5 * width

    v0_bl = bm.verts.new((p0[0] - rx * hw, p0[1] - ry * hw, p0[2]))
    v0_br = bm.verts.new((p0[0] + rx * hw, p0[1] + ry * hw, p0[2]))
    v1_br = bm.verts.new((p1[0] + rx * hw, p1[1] + ry * hw, p1[2]))
    v1_bl = bm.verts.new((p1[0] - rx * hw, p1[1] - ry * hw, p1[2]))

    v0_tl = bm.verts.new((p0[0] - rx * hw, p0[1] - ry * hw, p0[2] + thickness))
    v0_tr = bm.verts.new((p0[0] + rx * hw, p0[1] + ry * hw, p0[2] + thickness))
    v1_tr = bm.verts.new((p1[0] + rx * hw, p1[1] + ry * hw, p1[2] + thickness))
    v1_tl = bm.verts.new((p1[0] - rx * hw, p1[1] - ry * hw, p1[2] + thickness))

    uv_quad = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    faces_spec = [
        [v0_bl, v0_br, v0_tr, v0_tl],  # Start cap
        [v1_br, v1_bl, v1_tl, v1_tr],  # End cap
        [v1_bl, v0_bl, v0_tl, v1_tl],  # Left side
        [v0_br, v1_br, v1_tr, v0_tr],  # Right side
        [v0_tl, v0_tr, v1_tr, v1_tl],  # Top (+Z)
        [v1_bl, v1_br, v0_br, v0_bl],  # Bottom (-Z)
    ]
    for verts in faces_spec:
        f = bm.faces.new(verts)
        f.material_index = material_index
        for loop, uv in zip(f.loops, uv_quad):
            loop[uv_layer].uv = uv


def get_world_materials() -> dict[str, bpy.types.Material]:
    """Create or retrieve PBR materials for the `world` scene."""
    return {
        "cliff_rock": create_pbr_material(
            "MAT_WLD_CliffRock",
            base_color=(0.17, 0.14, 0.22, 1.0),
            roughness=0.88,
            metallic=0.02,
        ),
        "plaza_cobble": create_pbr_material(
            "MAT_WLD_PlazaCobble",
            base_color=(0.34, 0.29, 0.38, 1.0),
            roughness=0.76,
            metallic=0.04,
        ),
        "ring_road": create_pbr_material(
            "MAT_WLD_RingRoadStone",
            base_color=(0.46, 0.37, 0.32, 1.0),
            roughness=0.70,
            metallic=0.05,
        ),
        "mansion_slate": create_pbr_material(
            "MAT_WLD_MansionSlate",
            base_color=(0.24, 0.22, 0.30, 1.0),
            roughness=0.78,
            metallic=0.08,
        ),
        "candy_paving": create_pbr_material(
            "MAT_WLD_CandyPaving",
            base_color=(0.48, 0.30, 0.38, 1.0),
            roughness=0.68,
            metallic=0.04,
        ),
        "amusement_paving": create_pbr_material(
            "MAT_WLD_AmusementPaving",
            base_color=(0.38, 0.26, 0.42, 1.0),
            roughness=0.72,
            metallic=0.05,
        ),
        "forest_moss": create_pbr_material(
            "MAT_WLD_ForestMoss",
            base_color=(0.19, 0.28, 0.20, 1.0),
            roughness=0.86,
            metallic=0.0,
        ),
        "bridge_timber": create_pbr_material(
            "MAT_WLD_BridgeTimber",
            base_color=(0.36, 0.22, 0.13, 1.0),
            roughness=0.72,
            metallic=0.02,
        ),
        "parapet_iron": create_pbr_material(
            "MAT_WLD_ParapetIron",
            base_color=(0.15, 0.16, 0.20, 1.0),
            roughness=0.45,
            metallic=0.80,
        ),
        "beacon_glow": create_pbr_material(
            "MAT_WLD_BeaconGlow",
            base_color=(1.0, 0.64, 0.16, 1.0),
            roughness=0.22,
            metallic=0.0,
            emission_color=(1.0, 0.56, 0.12, 1.0),
            emission_strength=3.8,
        ),
    }


def build_central_island(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `WLD_CentralIsland_001`: Central Area A floating island landmass (R=18.5m, top z=0.0m, bottom z=-12.0m)."""
    mesh = bpy.data.meshes.new("WLD_CentralIsland_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Slot 0: cliff_rock, Slot 1: plaza_cobble
    # Upper stone terrace rim (z=-1.2m..0.0m, r=17.8m..18.5m) with top surface in plaza_cobble
    _add_frustum_z(
        bm,
        uv_layer,
        (0.0, 0.0),
        -1.2,
        0.0,
        17.8,
        18.5,
        segments=16,
        material_index=0,
        top_material_index=1,
    )
    # Mid cliff body (z=-6.5m..-1.2m)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), -6.5, -1.2, 11.5, 17.8, segments=16, material_index=0)
    # Lower tapered spire underside (z=-12.0m..-6.5m)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), -12.0, -6.5, 2.2, 11.5, segments=12, material_index=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["cliff_rock"], mats["plaza_cobble"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("WLD_CentralIsland_001", mesh)
    obj.location = Vector((0.0, 0.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_north_plateau(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `WLD_NorthPlateau_001`: North Area B Haunted Mansion elevated plateau at (0, 34, 0), top z=+1.5m."""
    mesh = bpy.data.meshes.new("WLD_NorthPlateau_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Local coordinates relative to (0.0, 34.0, 0.0) -> world y=[20..48] is local y=[-14..+14], x=[-20..+20]
    # Slot 0: cliff_rock, Slot 1: mansion_slate
    # Walkable plateau top deck (x=-20..20, y=-14..14, z=0.0..1.5m)
    _add_box(bm, uv_layer, (-20.0, -14.0, 0.0), (20.0, 14.0, 1.5), material_index=1)
    # Upper retaining terrace skirt (z=-3.5..0.0m)
    _add_box(bm, uv_layer, (-18.5, -13.0, -3.5), (18.5, 13.0, 0.0), material_index=0)
    # Tapered floating cliff underside (z=-14.0..-3.5m)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), -14.0, -3.5, 3.5, 16.5, segments=12, material_index=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["cliff_rock"], mats["mansion_slate"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("WLD_NorthPlateau_001", mesh)
    obj.location = Vector((0.0, 34.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_east_island(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `WLD_EastIsland_001`: East Area C Candy Market island wing at (34, 0, 0), top z=0.0m."""
    mesh = bpy.data.meshes.new("WLD_EastIsland_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Local coordinates relative to (34.0, 0.0, 0.0) -> world x=[20..48] is local x=[-14..+14], y=[-20..+20]
    # Slot 0: cliff_rock, Slot 1: candy_paving
    _add_box(bm, uv_layer, (-14.0, -20.0, -1.2), (14.0, 20.0, 0.0), material_index=1)
    _add_box(bm, uv_layer, (-12.5, -18.0, -4.5), (12.5, 18.0, -1.2), material_index=0)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), -11.0, -4.5, 2.8, 13.5, segments=12, material_index=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["cliff_rock"], mats["candy_paving"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("WLD_EastIsland_001", mesh)
    obj.location = Vector((34.0, 0.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_south_island(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `WLD_SouthIsland_001`: South Area D Trick Amusement & Entrance wing at (0, -34, 0), top z=0.0m."""
    mesh = bpy.data.meshes.new("WLD_SouthIsland_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Local coordinates relative to (0.0, -34.0, 0.0) -> world x=[-22..+22], world y=[-48..-20] is local y=[-14..+14]
    # Slot 0: cliff_rock, Slot 1: amusement_paving
    _add_box(bm, uv_layer, (-22.0, -14.0, -1.2), (22.0, 14.0, 0.0), material_index=1)
    _add_box(bm, uv_layer, (-19.5, -12.5, -4.5), (19.5, 12.5, -1.2), material_index=0)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), -11.5, -4.5, 3.0, 15.0, segments=12, material_index=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["cliff_rock"], mats["amusement_paving"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("WLD_SouthIsland_001", mesh)
    obj.location = Vector((0.0, -34.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_west_island(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `WLD_WestIsland_001`: West Area E Witch's Forest wing at (-34, 0, 0), top z=0.0m."""
    mesh = bpy.data.meshes.new("WLD_WestIsland_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Local coordinates relative to (-34.0, 0.0, 0.0) -> world x=[-48..-20] is local x=[-14..+14], y=[-20..+20]
    # Slot 0: cliff_rock, Slot 1: forest_moss
    _add_box(bm, uv_layer, (-14.0, -20.0, -1.2), (14.0, 20.0, 0.0), material_index=1)
    _add_box(bm, uv_layer, (-12.5, -18.0, -4.5), (12.5, 18.0, -1.2), material_index=0)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), -11.5, -4.5, 2.8, 13.5, segments=12, material_index=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["cliff_rock"], mats["forest_moss"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("WLD_WestIsland_001", mesh)
    obj.location = Vector((-34.0, 0.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_central_ring_road(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `WLD_CentralRingRoad_001`: 3.5m-wide Central Ring Road (R=11.0m..14.5m), inner plaza disc, and cardinal aprons."""
    mesh = bpy.data.meshes.new("WLD_CentralRingRoad_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Slot 0: ring_road, Slot 1: plaza_cobble, Slot 2: beacon_glow
    # 1. Inner cobblestone plaza circle (r=0..10.75m, z=0.0..0.03m)
    _add_frustum_z(bm, uv_layer, (0.0, 0.0), 0.0, 0.03, 10.75, 10.75, segments=32, material_index=1)
    # 2. Central Pumpkin Tower pedestal ring (r=3.2m..4.2m, z=0.03..0.12m)
    _add_annulus_z(bm, uv_layer, 3.2, 4.2, 0.03, 0.12, segments=24, material_index=0)
    # 3. Main 3.5m-wide Central Ring Road (inner R=10.75m, outer R=14.25m, z=0.0..0.06m)
    _add_annulus_z(bm, uv_layer, 10.75, 14.25, 0.0, 0.06, segments=32, material_index=0)
    # 4. Four cardinal approach aprons connecting the ring road inner curve to the bridge threshold (14.25m)
    # Using z=0.0..0.058m avoids coplanar Z-fighting with the ring road / bridge deck at z=0.06m
    # North apron (width 4.0m)
    _add_box(bm, uv_layer, (-2.0, 13.8, 0.0), (2.0, 14.25, 0.058), material_index=0)
    # East apron (width 4.0m)
    _add_box(bm, uv_layer, (13.8, -2.0, 0.0), (14.25, 2.0, 0.058), material_index=0)
    # South apron (width 4.0m)
    _add_box(bm, uv_layer, (-2.0, -14.25, 0.0), (2.0, -13.8, 0.058), material_index=0)
    # West apron (width 3.8m)
    _add_box(bm, uv_layer, (-14.25, -1.9, 0.0), (-13.8, 1.9, 0.058), material_index=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["ring_road"], mats["plaza_cobble"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("WLD_CentralRingRoad_001", mesh)
    obj.location = Vector((0.0, 0.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def _add_handrail_span(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    p0: tuple[float, float, float],
    p1: tuple[float, float, float],
    curb_mat_idx: int,
    rail_mat_idx: int,
    glow_mat_idx: int | None = None,
) -> None:
    """Add a 1.15m tall continuous bridge/cliff safety parapet + handrail from 3D point p0 to p1."""
    # Bottom continuous safety curb (width=0.24m, height=0.22m)
    _add_oriented_beam(bm, uv_layer, p0, p1, width=0.24, thickness=0.22, material_index=curb_mat_idx)
    # Mid safety rail (z + 0.58m..0.66m)
    _add_oriented_beam(
        bm,
        uv_layer,
        (p0[0], p0[1], p0[2] + 0.58),
        (p1[0], p1[1], p1[2] + 0.58),
        width=0.10,
        thickness=0.08,
        material_index=rail_mat_idx,
    )
    # Top safety handrail (z + 1.02m..1.14m)
    _add_oriented_beam(
        bm,
        uv_layer,
        (p0[0], p0[1], p0[2] + 1.02),
        (p1[0], p1[1], p1[2] + 1.02),
        width=0.18,
        thickness=0.12,
        material_index=rail_mat_idx,
    )
    # Vertical posts along the span every ~1.8m
    length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    num_posts = max(2, int(round(length / 1.8)) + 1)
    for i in range(num_posts):
        t = i / max(1, num_posts - 1)
        px = p0[0] + t * (p1[0] - p0[0])
        py = p0[1] + t * (p1[1] - p0[1])
        pz = p0[2] + t * (p1[2] - p0[2])
        _add_box(
            bm,
            uv_layer,
            (px - 0.11, py - 0.11, pz + 0.18),
            (px + 0.11, py + 0.11, pz + 1.18),
            material_index=curb_mat_idx if (i in (0, num_posts - 1)) else rail_mat_idx,
        )
        if glow_mat_idx is not None and i in (0, num_posts - 1):
            _add_box(
                bm,
                uv_layer,
                (px - 0.07, py - 0.07, pz + 1.18),
                (px + 0.07, py + 0.07, pz + 1.30),
                material_index=glow_mat_idx,
            )


def build_north_bridge(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `WLD_NorthBridge_001`: 4.0m-wide sloped Stone Arch Bridge & North Mansion Avenue at (0, 17.25, 0)."""
    mesh = bpy.data.meshes.new("WLD_NorthBridge_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Origin at (0.0, 17.25, 0.0)
    # World y=14.25m -> local y=-3.0m (z=0.0m)
    # World y=20.25m -> local y=+3.0m (z=1.5m)
    # Plus North Mansion Avenue spine on the plateau from world y=20.25..36.0m (local y=+3.0..+18.75m, z=1.5m)
    # Slot 0: ring_road, Slot 1: cliff_rock, Slot 2: parapet_iron, Slot 3: beacon_glow
    # 1. Sloped bridge deck (width=4.0m, thickness=0.32m, local y=-3.0..+3.0, z=-0.26..0.06 at start to z=1.24..1.56 at end)
    _add_oriented_beam(
        bm,
        uv_layer,
        (0.0, -3.0, -0.26),
        (0.0, 3.0, 1.24),
        width=4.0,
        thickness=0.32,
        material_index=0,
    )
    # 2. Under-arch stone support ribs & piers (local y=-2.8..+2.8, z=-2.2..0.8)
    _add_box(bm, uv_layer, (-1.8, -2.8, -1.8), (1.8, -1.6, 0.0), material_index=1)
    _add_box(bm, uv_layer, (-1.8, 1.6, -1.2), (1.8, 2.8, 1.3), material_index=1)
    _add_oriented_beam(
        bm,
        uv_layer,
        (0.0, -2.2, -1.0),
        (0.0, 2.2, 0.4),
        width=3.2,
        thickness=0.6,
        material_index=1,
    )
    # 3. Left & Right 1.15m tall bridge safety handrails along the sloped span (x=-1.88 and x=+1.88)
    _add_handrail_span(bm, uv_layer, (-1.88, -3.0, 0.04), (-1.88, 3.0, 1.54), 1, 2, 3)
    _add_handrail_span(bm, uv_layer, (1.88, -3.0, 0.04), (1.88, 3.0, 1.54), 1, 2, 3)

    # 4. Continuation of the 4.0m main road on the North Plateau (local y=+3.0..+18.75, z=1.50..1.56)
    _add_box(bm, uv_layer, (-2.0, 3.0, 1.50), (2.0, 18.75, 1.56), material_index=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["ring_road"], mats["cliff_rock"], mats["parapet_iron"], mats["beacon_glow"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("WLD_NorthBridge_001", mesh)
    obj.location = Vector((0.0, 17.25, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_east_bridge(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `WLD_EastBridge_001`: 4.0m-wide East Festive Causeway Bridge & Candy Alley road at (17.25, 0, 0)."""
    mesh = bpy.data.meshes.new("WLD_EastBridge_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Origin at (17.25, 0.0, 0.0) -> bridge span local x=-3.0..+3.0 (world x=14.25..20.25), plus avenue to world x=42.25 (local x=+25.0)
    # Slot 0: ring_road, Slot 1: cliff_rock, Slot 2: parapet_iron, Slot 3: beacon_glow
    _add_box(bm, uv_layer, (-3.0, -2.0, -0.30), (3.0, 2.0, 0.06), material_index=0)
    # Under-bridge stone arch piers
    _add_box(bm, uv_layer, (-2.6, -1.8, -1.8), (-1.4, 1.8, -0.30), material_index=1)
    _add_box(bm, uv_layer, (1.4, -1.8, -1.8), (2.6, 1.8, -0.30), material_index=1)
    _add_box(bm, uv_layer, (-1.6, -1.6, -0.95), (1.6, 1.6, -0.30), material_index=1)
    # Safety balustrades on both sides of the chasm crossing (y=-1.88 and y=+1.88)
    _add_handrail_span(bm, uv_layer, (-3.0, -1.88, 0.04), (3.0, -1.88, 0.04), 1, 2, 3)
    _add_handrail_span(bm, uv_layer, (-3.0, 1.88, 0.04), (3.0, 1.88, 0.04), 1, 2, 3)
    # Main Candy Alley road surface across Area C (local x=3.0..25.0, width=4.0m)
    _add_box(bm, uv_layer, (3.0, -2.0, 0.0), (25.0, 2.0, 0.06), material_index=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["ring_road"], mats["cliff_rock"], mats["parapet_iron"], mats["beacon_glow"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("WLD_EastBridge_001", mesh)
    obj.location = Vector((17.25, 0.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_south_promenade(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `WLD_SouthPromenade_001`: 4.0m-wide South Grand Promenade, Causeway Bridge & Spawn Terrace at (0, -30, 0)."""
    mesh = bpy.data.meshes.new("WLD_SouthPromenade_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Origin at (0.0, -30.0, 0.0)
    # Bridge span: world y=-20.25..-14.25 -> local y=+9.75..+15.75
    # Main promenade through Area D: world y=-41.0..-20.25 -> local y=-11.0..+9.75
    # South Entrance Spawn Plaza terrace at world y=-46.0..-41.0 -> local y=-16.0..-11.0
    # Slot 0: ring_road, Slot 1: cliff_rock, Slot 2: parapet_iron, Slot 3: beacon_glow
    # 1. South Causeway Bridge deck (local y=+9.75..+15.75, width=4.0m)
    _add_box(bm, uv_layer, (-2.0, 9.75, -0.30), (2.0, 15.75, 0.06), material_index=0)
    _add_box(bm, uv_layer, (-1.8, 10.2, -1.8), (1.8, 11.4, -0.30), material_index=1)
    _add_box(bm, uv_layer, (-1.8, 14.1, -1.8), (1.8, 15.3, -0.30), material_index=1)
    _add_box(bm, uv_layer, (-1.6, 11.4, -0.95), (1.6, 14.1, -0.30), material_index=1)
    # Safety handrails on both sides of the South Bridge
    _add_handrail_span(bm, uv_layer, (-1.88, 9.75, 0.04), (-1.88, 15.75, 0.04), 1, 2, 3)
    _add_handrail_span(bm, uv_layer, (1.88, 9.75, 0.04), (1.88, 15.75, 0.04), 1, 2, 3)

    # 2. Main 4.0m promenade road through Area D (local y=-11.0..+9.75)
    _add_box(bm, uv_layer, (-2.0, -11.0, 0.0), (2.0, 9.75, 0.06), material_index=0)

    # 3. South Spawn Arrival Terrace at world y=-44.0m (local y=-16.5..-11.0m, 9.0m wide x 5.5m deep)
    _add_box(bm, uv_layer, (-4.5, -16.5, 0.0), (4.5, -11.0, 0.06), material_index=0)
    # South-edge safety balustrade behind spawn terrace (local y=-16.38, x=-4.4..+4.4)
    _add_handrail_span(bm, uv_layer, (-4.4, -16.38, 0.04), (4.4, -16.38, 0.04), 1, 2, 3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["ring_road"], mats["cliff_rock"], mats["parapet_iron"], mats["beacon_glow"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("WLD_SouthPromenade_001", mesh)
    obj.location = Vector((0.0, -30.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_west_bridge(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `WLD_WestBridge_001`: 3.8m-wide West Timber & Stone Viaduct Bridge & Forest road at (-17.25, 0, 0)."""
    mesh = bpy.data.meshes.new("WLD_WestBridge_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Origin at (-17.25, 0.0, 0.0) -> bridge span local x=-3.0..+3.0 (world x=-20.25..-14.25), plus forest road to local x=-25.0
    # Slot 0: bridge_timber, Slot 1: cliff_rock, Slot 2: parapet_iron, Slot 3: beacon_glow
    _add_box(bm, uv_layer, (-3.0, -1.9, -0.28), (3.0, 1.9, 0.06), material_index=0)
    _add_box(bm, uv_layer, (-2.6, -1.7, -1.8), (-1.4, 1.7, -0.28), material_index=1)
    _add_box(bm, uv_layer, (1.4, -1.7, -1.8), (2.6, 1.7, -0.28), material_index=1)
    _add_box(bm, uv_layer, (-1.6, -1.5, -0.90), (1.6, 1.5, -0.28), material_index=0)
    # Safety handrails on both sides of the West Bridge (y=-1.78 and y=+1.78)
    _add_handrail_span(bm, uv_layer, (-3.0, -1.78, 0.04), (3.0, -1.78, 0.04), 0, 2, 3)
    _add_handrail_span(bm, uv_layer, (-3.0, 1.78, 0.04), (3.0, 1.78, 0.04), 0, 2, 3)

    # Main forest timber/stone road across Area E (local x=-25.0..-3.0, width=3.8m)
    _add_box(bm, uv_layer, (-25.0, -1.9, 0.0), (-3.0, 1.9, 0.05), material_index=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["bridge_timber"], mats["cliff_rock"], mats["parapet_iron"], mats["beacon_glow"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("WLD_WestBridge_001", mesh)
    obj.location = Vector((-17.25, 0.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_outer_loop_paths(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `WLD_OuterLoopPaths_001`: 4 diagonal 2.6m-wide inter-area bridges (NE, SE, SW, NW) with ramps and safety handrails."""
    mesh = bpy.data.meshes.new("WLD_OuterLoopPaths_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Slot 0: bridge_timber, Slot 1: cliff_rock, Slot 2: parapet_iron
    # W07 (Issue #9): the NE/NW bridges used to rise in one straight ramp to (+-15.5, 22.5, 1.5), so their decks met
    # the north plateau's edge (y = 20) at z 0.78..1.2 and left a 0.3..0.7 m wall across the bridge. The ramp now
    # reaches z 1.5 at (+-19.0, 19.0), where the deck's inner edge first touches y = 20, and runs level onto the
    # plateau from there (ramp 16.6 deg). See docs/p1-handoff.md.
    diagonal_spans = [
        # NE: Area B (16, 22, 1.5) <-> Area C (22, 16, 0.0): level landing + ramp
        ((15.5, 22.5, 1.50), (19.0, 19.0, 1.50)),
        ((19.0, 19.0, 1.50), (22.5, 15.5, 0.02)),
        # SE: Area C (22, -16, 0.0) <-> Area D (16, -22, 0.0)
        ((22.5, -15.5, 0.02), (15.5, -22.5, 0.02)),
        # SW: Area D (-16, -22, 0.0) <-> Area E (-22, -16, 0.0)
        ((-15.5, -22.5, 0.02), (-22.5, -15.5, 0.02)),
        # NW: Area E (-22, 16, 0.0) <-> Area B (-16, 22, 1.5): ramp + level landing
        ((-22.5, 15.5, 0.02), (-19.0, 19.0, 1.50)),
        ((-19.0, 19.0, 1.50), (-15.5, 22.5, 1.50)),
    ]

    deck_width = 2.8  # walkable clear width 2.6m between side rails
    for p0, p1 in diagonal_spans:
        # Deck beam
        _add_oriented_beam(
            bm,
            uv_layer,
            (p0[0], p0[1], p0[2] - 0.24),
            (p1[0], p1[1], p1[2] - 0.24),
            width=deck_width,
            thickness=0.26,
            material_index=0,
        )
        # Compute perpendicular offset in XY for left/right safety handrails
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        hlen = math.hypot(dx, dy)
        rx = (dy / hlen) * 1.28
        ry = (-dx / hlen) * 1.28
        for sign in (-1.0, 1.0):
            rp0 = (p0[0] + sign * rx, p0[1] + sign * ry, p0[2])
            rp1 = (p1[0] + sign * rx, p1[1] + sign * ry, p1[2])
            _add_handrail_span(bm, uv_layer, rp0, rp1, 1, 2, None)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["bridge_timber"], mats["cliff_rock"], mats["parapet_iron"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("WLD_OuterLoopPaths_001", mesh)
    obj.location = Vector((0.0, 0.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_cliff_safety_walls(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `WLD_CliffSafetyWalls_001`: 1.15m tall perimeter cliff-edge safety walls around the central island and 4 outer wings."""
    mesh = bpy.data.meshes.new("WLD_CliffSafetyWalls_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Slot 0: cliff_rock, Slot 1: parapet_iron
    # 1. Central Island diagonal rim guard segments (between the 4 cardinal bridges, at radius ~17.5m)
    central_arcs = [
        ((3.2, 17.2, 0.0), (12.2, 12.2, 0.0)),
        ((12.2, 12.2, 0.0), (17.2, 3.2, 0.0)),
        ((17.2, -3.2, 0.0), (12.2, -12.2, 0.0)),
        ((12.2, -12.2, 0.0), (3.2, -17.2, 0.0)),
        ((-3.2, -17.2, 0.0), (-12.2, -12.2, 0.0)),
        ((-12.2, -12.2, 0.0), (-17.2, -3.2, 0.0)),
        ((-17.2, 3.2, 0.0), (-12.2, 12.2, 0.0)),
        ((-12.2, 12.2, 0.0), (-3.2, 17.2, 0.0)),
    ]
    # 2. Outer island perimeter cliff guard segments (leaving all bridge & side-bridge portals open)
    outer_segments = [
        # North Plateau (z=1.5m) outer perimeter
        ((-19.5, 47.5, 1.5), (19.5, 47.5, 1.5)),
        ((-19.5, 24.5, 1.5), (-19.5, 47.5, 1.5)),
        ((19.5, 24.5, 1.5), (19.5, 47.5, 1.5)),
        ((-14.0, 20.4, 1.5), (-2.4, 20.4, 1.5)),
        ((2.4, 20.4, 1.5), (14.0, 20.4, 1.5)),
        # East Island (z=0.0m) outer perimeter
        ((47.5, -19.5, 0.0), (47.5, 19.5, 0.0)),
        ((24.5, 19.5, 0.0), (47.5, 19.5, 0.0)),
        ((24.5, -19.5, 0.0), (47.5, -19.5, 0.0)),
        ((20.4, 2.4, 0.0), (20.4, 14.0, 0.0)),
        ((20.4, -14.0, 0.0), (20.4, -2.4, 0.0)),
        # South Island (z=0.0m) outer perimeter
        ((-21.5, -47.5, 0.0), (-4.6, -47.5, 0.0)),
        ((4.6, -47.5, 0.0), (21.5, -47.5, 0.0)),
        ((-21.5, -47.5, 0.0), (-21.5, -24.5, 0.0)),
        ((21.5, -47.5, 0.0), (21.5, -24.5, 0.0)),
        ((-14.0, -20.4, 0.0), (-2.4, -20.4, 0.0)),
        ((2.4, -20.4, 0.0), (14.0, -20.4, 0.0)),
        # West Island (z=0.0m) outer perimeter
        ((-47.5, -19.5, 0.0), (-47.5, 19.5, 0.0)),
        ((-47.5, 19.5, 0.0), (-24.5, 19.5, 0.0)),
        ((-47.5, -19.5, 0.0), (-24.5, -19.5, 0.0)),
        ((-20.4, 2.4, 0.0), (-20.4, 14.0, 0.0)),
        ((-20.4, -14.0, 0.0), (-20.4, -2.4, 0.0)),
    ]

    for p0, p1 in central_arcs + outer_segments:
        _add_handrail_span(bm, uv_layer, p0, p1, 0, 1, None)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["cliff_rock"], mats["parapet_iron"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("WLD_CliffSafetyWalls_001", mesh)
    obj.location = Vector((0.0, 0.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


def build_floating_islets(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Create `WLD_FloatingIslets_001`: 4 atmospheric distant floating islets with glowing Halloween beacons."""
    mesh = bpy.data.meshes.new("WLD_FloatingIslets_001_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Slot 0: cliff_rock, Slot 1: beacon_glow
    islet_specs = [
        (46.0, 44.0, 6.0, 5.5),
        (48.0, -44.0, 4.5, 5.0),
        (-48.0, -44.0, 5.0, 5.2),
        (-46.0, 44.0, 6.5, 5.5),
    ]
    for ix, iy, iz, radius in islet_specs:
        # Rock cap
        _add_frustum_z(bm, uv_layer, (ix, iy), iz - 1.2, iz, radius * 0.9, radius, segments=10, material_index=0)
        # Tapered craggy underside
        _add_frustum_z(bm, uv_layer, (ix, iy), iz - 8.5, iz - 1.2, 0.8, radius * 0.9, segments=8, material_index=0)
        # Glowing crystal/lantern monolith beacon on top
        _add_frustum_z(bm, uv_layer, (ix, iy), iz, iz + 2.8, 0.9, 0.4, segments=6, material_index=1)
        _add_frustum_z(bm, uv_layer, (ix, iy), iz + 2.8, iz + 4.0, 0.4, 0.0, segments=6, material_index=1)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for m in (mats["cliff_rock"], mats["beacon_glow"]):
        mesh.materials.append(m)

    obj = bpy.data.objects.new("WLD_FloatingIslets_001", mesh)
    obj.location = Vector((0.0, 0.0, 0.0))
    obj.scale = Vector((1.0, 1.0, 1.0))
    collection.objects.link(obj)
    return obj


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


def place_world_common_parts(collection: bpy.types.Collection, common_blend_path: Path) -> list[bpy.types.Object]:
    """Place reusable common parts from `blender/common/common.blend` into the `world` collection."""
    area_layout = build_world_area_layout_dict()
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


def _make_world_manifest_entry(
    obj: bpy.types.Object,
    category: str,
    notes: str,
) -> dict[str, Any]:
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
        "area_id": "world",
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


def write_world_data_files(
    root: Path,
    world_objects_with_meta: list[tuple[bpy.types.Object, str, str]],
) -> None:
    """Write `layout/world_layout.json`, `layout/areas/world.json`, and `assets/manifest/world.json`."""
    world_layout_path = root / WORLD_LAYOUT_REL_PATH
    area_layout_path = root / AREA_LAYOUT_REL_PATH
    manifest_path = root / MANIFEST_REL_PATH

    world_layout_path.parent.mkdir(parents=True, exist_ok=True)
    area_layout_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    world_layout_data = build_world_layout_dict()
    area_layout_data = build_world_area_layout_dict()
    manifest_data: dict[str, Any] = {
        "schema_version": "1.0",
        "key": KEY,
        "updated_at": "2026-10-31T09:00:00Z",
        "assets": [
            _make_world_manifest_entry(obj, cat, notes)
            for obj, cat, notes in world_objects_with_meta
        ],
    }

    world_layout_path.write_text(
        json.dumps(world_layout_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    area_layout_path.write_text(
        json.dumps(area_layout_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_world() -> dict[str, Any]:
    """Build the world terrain/bridges/roads scene, render `review/world/`, save `blender/world/world.blend`, and write JSONs."""
    common_blend_path = PROJECT_ROOT / COMMON_BLEND_REL_PATH
    if not common_blend_path.is_file():
        build_common()

    _scene, world_col = reset_scene(KEY, seed=102)
    mats = get_world_materials()

    central_island = build_central_island(world_col, mats)
    north_plateau = build_north_plateau(world_col, mats)
    east_island = build_east_island(world_col, mats)
    south_island = build_south_island(world_col, mats)
    west_island = build_west_island(world_col, mats)
    ring_road = build_central_ring_road(world_col, mats)
    north_bridge = build_north_bridge(world_col, mats)
    east_bridge = build_east_bridge(world_col, mats)
    south_promenade = build_south_promenade(world_col, mats)
    west_bridge = build_west_bridge(world_col, mats)
    outer_loop = build_outer_loop_paths(world_col, mats)
    safety_walls = build_cliff_safety_walls(world_col, mats)
    floating_islets = build_floating_islets(world_col, mats)

    placed_common = place_world_common_parts(world_col, common_blend_path)

    world_objects_with_meta = [
        (
            central_island,
            "terrain",
            "Central Area A floating island landmass (R=18.5m, top z=0.0m, tapered cliff down to z=-12.0m).",
        ),
        (
            north_plateau,
            "terrain",
            "North Area B Haunted Mansion elevated plateau (center=(0,34,1.5), top walkable terrace at z=+1.5m).",
        ),
        (
            east_island,
            "terrain",
            "East Area C Candy Market Alley floating island wing (center=(34,0,0), top z=0.0m).",
        ),
        (
            south_island,
            "terrain",
            "South Area D Trick Amusement & Entrance floating island wing (center=(0,-34,0), top z=0.0m).",
        ),
        (
            west_island,
            "terrain",
            "West Area E Witch's Forest floating island wing (center=(-34,0,0), top z=0.0m).",
        ),
        (
            ring_road,
            "terrain",
            "Central cobblestone plaza disc (diameter 22m) and 3.5m-wide Central Ring Road (outer diameter 29m) with 4 cardinal bridge aprons.",
        ),
        (
            north_bridge,
            "architecture",
            "4.0m-wide North Stone Arch Bridge & gentle ramp (slope 15.2 deg from z=0.0m to z=1.5m) with 1.15m safety handrails.",
        ),
        (
            east_bridge,
            "architecture",
            "4.0m-wide East Festive Causeway Bridge and Candy Alley road spine with 1.15m safety handrails.",
        ),
        (
            south_promenade,
            "architecture",
            "4.0m-wide South Grand Promenade, Causeway Bridge, and South Entrance Spawn Terrace (y=-44m) with 1.15m safety handrails.",
        ),
        (
            west_bridge,
            "architecture",
            "3.8m-wide West Timber & Stone Viaduct Bridge and Forest road spine with 1.15m safety handrails.",
        ),
        (
            outer_loop,
            "architecture",
            "Four 2.6m-wide diagonal inter-area bridges (NE, SE, SW, NW) with gentle ramps and 1.10m safety handrails.",
        ),
        (
            safety_walls,
            "architecture",
            "1.15m-tall perimeter stone & iron safety guard walls along exposed cliff edges of all 5 island sections.",
        ),
        (
            floating_islets,
            "sky_boundary",
            "Four distant floating rock islets with glowing amber monolith beacons framing the horizon.",
        ),
    ]

    overview_png = PROJECT_ROOT / "review" / "world" / "01_world_overview.png"
    bridges_png = PROJECT_ROOT / "review" / "world" / "02_world_routes_bridges.png"
    entrance_png = PROJECT_ROOT / "review" / "world" / "03_world_south_entrance.png"

    render_review_images(
        views=[
            {
                "filepath": overview_png,
                "location": (52.0, -72.0, 58.0),
                "target": (0.0, 0.0, 0.0),
                "lens_mm": 26.0,
            },
            {
                "filepath": bridges_png,
                "location": (24.0, -26.0, 18.0),
                "target": (0.0, 6.0, 0.8),
                "lens_mm": 28.0,
            },
            {
                "filepath": entrance_png,
                "location": (0.0, -51.0, 3.8),
                "target": (0.0, -14.0, 1.5),
                "lens_mm": 30.0,
            },
        ],
        width=1280,
        height=720,
        samples=32,
    )

    blend_path = PROJECT_ROOT / BLEND_REL_PATH
    save_blend(blend_path, pack_images=True)

    write_world_data_files(PROJECT_ROOT, world_objects_with_meta)

    summary = {
        "key": KEY,
        "blend_file": BLEND_REL_PATH,
        "objects_count": len(bpy.data.objects),
        "world_assets_count": len(world_objects_with_meta),
        "common_instances_count": len(placed_common),
        "object_names": sorted(o.name for o in bpy.data.objects),
        "meshes_count": len(bpy.data.meshes),
        "materials_count": len(bpy.data.materials),
        "review_images": [
            str(overview_png.relative_to(PROJECT_ROOT)),
            str(bridges_png.relative_to(PROJECT_ROOT)),
            str(entrance_png.relative_to(PROJECT_ROOT)),
        ],
    }
    print("WORLD_BUILD_SUMMARY:" + json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    build_world()
