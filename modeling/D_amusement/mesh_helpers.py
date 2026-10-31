"""BMesh primitive helpers and PBR material palette for Area D (`D_amusement`)."""

from __future__ import annotations

import math
from typing import Any

import bmesh  # type: ignore
import bpy  # type: ignore
from mathutils import Vector  # type: ignore

from modeling.lib.materials import create_pbr_material
from modeling.lib.scene import deg_to_rad_tuple


def add_box(
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


def add_frustum_z(
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
    rx_scale: float = 1.0,
    ry_scale: float = 1.0,
) -> None:
    """Add a vertical n-gon frustum (optionally elliptical via rx_scale/ry_scale) from z0 to z1."""
    cx, cy = center_xy
    top_mat = material_index if top_material_index is None else top_material_index
    ring0 = []
    ring1 = []
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        ring0.append(bm.verts.new((cx + r0 * rx_scale * ca, cy + r0 * ry_scale * sa, z0)))
        if r1 > 1e-5:
            ring1.append(bm.verts.new((cx + r1 * rx_scale * ca, cy + r1 * ry_scale * sa, z1)))

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


def add_cylinder_x(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    center_yz: tuple[float, float],
    x0: float,
    x1: float,
    radius: float,
    segments: int = 16,
    material_index: int = 0,
    cap_material_index: int | None = None,
) -> None:
    """Add a horizontal cylinder along the X axis (for wheels, axles, and boilers)."""
    cy, cz = center_yz
    cap_mat = material_index if cap_material_index is None else cap_material_index
    ring0 = []
    ring1 = []
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        y = cy + radius * math.cos(a)
        z = cz + radius * math.sin(a)
        ring0.append(bm.verts.new((x0, y, z)))
        ring1.append(bm.verts.new((x1, y, z)))

    f_left = bm.faces.new(list(reversed(ring0)))
    f_left.material_index = cap_mat
    for i, loop in enumerate(f_left.loops):
        ang = 2.0 * math.pi * i / segments
        loop[uv_layer].uv = (0.5 + 0.45 * math.cos(ang), 0.5 + 0.45 * math.sin(ang))

    f_right = bm.faces.new(ring1)
    f_right.material_index = cap_mat
    for i, loop in enumerate(f_right.loops):
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


def add_cylinder_y(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    center_xz: tuple[float, float],
    y0: float,
    y1: float,
    r0: float,
    r1: float | None = None,
    segments: int = 16,
    material_index: int = 0,
    front_cap_material_index: int | None = None,
) -> None:
    """Add a horizontal cylinder/frustum along the Y axis (for locomotive boiler & ghost face)."""
    cx, cz = center_xz
    rad1 = r0 if r1 is None else r1
    front_mat = material_index if front_cap_material_index is None else front_cap_material_index
    ring0 = []
    ring1 = []
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        ring0.append(bm.verts.new((cx + r0 * ca, y0, cz + r0 * sa)))
        ring1.append(bm.verts.new((cx + rad1 * ca, y1, cz + rad1 * sa)))

    # At y0 (-Y normal): CCW viewed from -Y
    f_back = bm.faces.new(ring0)
    f_back.material_index = material_index
    for i, loop in enumerate(f_back.loops):
        ang = 2.0 * math.pi * i / segments
        loop[uv_layer].uv = (0.5 + 0.45 * math.cos(ang), 0.5 + 0.45 * math.sin(ang))

    # At y1 (+Y normal): reversed
    f_front = bm.faces.new(list(reversed(ring1)))
    f_front.material_index = front_mat
    for i, loop in enumerate(f_front.loops):
        ang = 2.0 * math.pi * i / segments
        loop[uv_layer].uv = (0.5 + 0.45 * math.cos(ang), 0.5 + 0.45 * math.sin(ang))

    for i in range(segments):
        jn = (i + 1) % segments
        f_side = bm.faces.new([ring0[jn], ring0[i], ring1[i], ring1[jn]])
        f_side.material_index = material_index
        u0 = i / segments
        u1 = (i + 1) / segments
        f_side.loops[0][uv_layer].uv = (u1, 0.0)
        f_side.loops[1][uv_layer].uv = (u0, 0.0)
        f_side.loops[2][uv_layer].uv = (u0, 1.0)
        f_side.loops[3][uv_layer].uv = (u1, 1.0)


def add_annulus_z(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    r_inner: float,
    r_outer: float,
    z0: float,
    z1: float,
    segments: int = 24,
    material_index: int = 0,
    rx_scale: float = 1.0,
    ry_scale: float = 1.0,
) -> None:
    """Add a closed ring (annulus) between r_inner and r_outer from z0 to z1 centered at (0,0)."""
    in_bot = []
    in_top = []
    out_bot = []
    out_top = []
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        in_bot.append(bm.verts.new((r_inner * rx_scale * ca, r_inner * ry_scale * sa, z0)))
        in_top.append(bm.verts.new((r_inner * rx_scale * ca, r_inner * ry_scale * sa, z1)))
        out_bot.append(bm.verts.new((r_outer * rx_scale * ca, r_outer * ry_scale * sa, z0)))
        out_top.append(bm.verts.new((r_outer * rx_scale * ca, r_outer * ry_scale * sa, z1)))

    uv_quad = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    for i in range(segments):
        jn = (i + 1) % segments
        quads = [
            [in_top[i], out_top[i], out_top[jn], in_top[jn]],
            [out_bot[i], in_bot[i], in_bot[jn], out_bot[jn]],
            [out_bot[i], out_bot[jn], out_top[jn], out_top[i]],
            [in_bot[jn], in_bot[i], in_top[i], in_top[jn]],
        ]
        for verts in quads:
            f = bm.faces.new(verts)
            f.material_index = material_index
            for loop, uv in zip(f.loops, uv_quad):
                loop[uv_layer].uv = uv


def add_oriented_beam(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    p0: tuple[float, float, float],
    p1: tuple[float, float, float],
    width: float,
    thickness: float,
    material_index: int = 0,
) -> None:
    """Add a 3D beam or rail segment from p0 to p1 with horizontal width and vertical thickness."""
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    horiz_len = math.hypot(dx, dy)
    if horiz_len < 1e-5:
        add_box(
            bm,
            uv_layer,
            (p0[0] - 0.5 * width, p0[1] - 0.5 * width, min(p0[2], p1[2])),
            (p0[0] + 0.5 * width, p0[1] + 0.5 * width, max(p0[2], p1[2]) + thickness),
            material_index=material_index,
        )
        return

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
        [v0_bl, v0_br, v0_tr, v0_tl],
        [v1_br, v1_bl, v1_tl, v1_tr],
        [v1_bl, v0_bl, v0_tl, v1_tl],
        [v0_br, v1_br, v1_tr, v0_tr],
        [v0_tl, v0_tr, v1_tr, v1_tl],
        [v1_bl, v1_br, v0_br, v0_bl],
    ]
    for verts in faces_spec:
        f = bm.faces.new(verts)
        f.material_index = material_index
        for loop, uv in zip(f.loops, uv_quad):
            loop[uv_layer].uv = uv


def create_empty_node(
    name: str,
    collection: bpy.types.Collection,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_euler_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    parent: bpy.types.Object | None = None,
    display_size: float = 0.5,
) -> bpy.types.Object:
    """Create a plain axes Empty object with unit scale for asset/motion/attachment roots."""
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = float(display_size)
    obj.location = Vector(location)
    obj.rotation_euler = deg_to_rad_tuple(rotation_euler_deg)
    obj.scale = Vector((1.0, 1.0, 1.0))
    if parent is not None:
        obj.parent = parent
    collection.objects.link(obj)
    return obj


def finalize_mesh_obj(
    name: str,
    bm: bmesh.types.BMesh,
    collection: bpy.types.Collection,
    materials: list[bpy.types.Material],
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_euler_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    """Recalculate outward normals, build mesh, attach materials, and link object with unit scale."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for mat in materials:
        mesh.materials.append(mat)

    obj = bpy.data.objects.new(name, mesh)
    obj.location = Vector(location)
    obj.rotation_euler = deg_to_rad_tuple(rotation_euler_deg)
    obj.scale = Vector((1.0, 1.0, 1.0))
    if parent is not None:
        obj.parent = parent
    collection.objects.link(obj)
    return obj


def get_d_amusement_materials() -> dict[str, bpy.types.Material]:
    """Create or retrieve `MAT_DAM_*` PBR materials for Area D (`D_amusement`)."""
    return {
        "pumpkin_orange": create_pbr_material(
            "MAT_DAM_PumpkinOrange",
            base_color=(0.94, 0.42, 0.08, 1.0),
            roughness=0.46,
            metallic=0.02,
        ),
        "pumpkin_dark_rib": create_pbr_material(
            "MAT_DAM_PumpkinDarkRib",
            base_color=(0.72, 0.25, 0.04, 1.0),
            roughness=0.55,
            metallic=0.02,
        ),
        "pumpkin_stem": create_pbr_material(
            "MAT_DAM_PumpkinStem",
            base_color=(0.18, 0.36, 0.14, 1.0),
            roughness=0.72,
            metallic=0.0,
        ),
        "carnival_purple": create_pbr_material(
            "MAT_DAM_CarnivalPurple",
            base_color=(0.30, 0.13, 0.48, 1.0),
            roughness=0.48,
            metallic=0.08,
        ),
        "carnival_gold": create_pbr_material(
            "MAT_DAM_CarnivalGold",
            base_color=(0.90, 0.68, 0.18, 1.0),
            roughness=0.30,
            metallic=0.82,
        ),
        "carnival_cream": create_pbr_material(
            "MAT_DAM_CarnivalCream",
            base_color=(0.95, 0.90, 0.80, 1.0),
            roughness=0.52,
            metallic=0.02,
        ),
        "ghost_white": create_pbr_material(
            "MAT_DAM_GhostWhite",
            base_color=(0.96, 0.96, 0.99, 1.0),
            roughness=0.36,
            metallic=0.0,
            emission_color=(0.85, 0.90, 1.0, 1.0),
            emission_strength=0.45,
        ),
        "witch_hat_black": create_pbr_material(
            "MAT_DAM_WitchHatBlack",
            base_color=(0.11, 0.09, 0.16, 1.0),
            roughness=0.64,
            metallic=0.05,
        ),
        "warm_wood": create_pbr_material(
            "MAT_DAM_WarmWood",
            base_color=(0.38, 0.23, 0.13, 1.0),
            roughness=0.68,
            metallic=0.02,
        ),
        "iron_steel": create_pbr_material(
            "MAT_DAM_IronSteel",
            base_color=(0.16, 0.17, 0.21, 1.0),
            roughness=0.42,
            metallic=0.85,
        ),
        "plaza_stone": create_pbr_material(
            "MAT_DAM_PlazaStone",
            base_color=(0.32, 0.24, 0.37, 1.0),
            roughness=0.76,
            metallic=0.04,
        ),
        "amber_glow": create_pbr_material(
            "MAT_DAM_AmberGlow",
            base_color=(1.0, 0.72, 0.20, 1.0),
            roughness=0.18,
            metallic=0.0,
            emission_color=(1.0, 0.62, 0.12, 1.0),
            emission_strength=4.2,
        ),
    }
