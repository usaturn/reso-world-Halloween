"""Mesh and hierarchy builders for Central Plaza gimmicks, interactions, show rig, and entrance gate (`A_plaza` / W02)."""

from __future__ import annotations

import math
from typing import Any

import bmesh  # type: ignore
import bpy  # type: ignore
from mathutils import Euler, Vector  # type: ignore

from modeling.lib.primitives import create_empty


def add_box(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    min_pt: tuple[float, float, float],
    max_pt: tuple[float, float, float],
    material_index: int = 0,
) -> None:
    """Add an axis-aligned UV-mapped box to `bm`."""
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
    lobes: int = 0,
    lobe_amp: float = 0.0,
) -> None:
    """Add a vertical cylinder/cone/ribbed frustum to `bm`."""
    cx, cy = center_xy
    bot_ring = []
    top_ring = []
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        mod = 1.0 + (lobe_amp * math.cos(lobes * a) if lobes > 0 else 0.0)
        ca, sa = math.cos(a), math.sin(a)
        bot_ring.append(bm.verts.new((cx + r0 * mod * ca, cy + r0 * mod * sa, z0)))
        top_ring.append(bm.verts.new((cx + r1 * mod * ca, cy + r1 * mod * sa, z1)))

    bot_center = bm.verts.new((cx, cy, z0))
    top_center = bm.verts.new((cx, cy, z1))

    for i in range(segments):
        jn = (i + 1) % segments
        u0 = i / segments
        u1 = (i + 1) / segments

        f_side = bm.faces.new([bot_ring[i], bot_ring[jn], top_ring[jn], top_ring[i]])
        f_side.material_index = material_index
        for loop, uv in zip(f_side.loops, [(u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)]):
            loop[uv_layer].uv = uv

        f_top = bm.faces.new([top_center, top_ring[i], top_ring[jn]])
        f_top.material_index = material_index
        for loop, uv in zip(f_top.loops, [(0.5, 0.5), (u0, 1.0), (u1, 1.0)]):
            loop[uv_layer].uv = uv

        f_bot = bm.faces.new([bot_center, bot_ring[jn], bot_ring[i]])
        f_bot.material_index = material_index
        for loop, uv in zip(f_bot.loops, [(0.5, 0.5), (u1, 0.0), (u0, 0.0)]):
            loop[uv_layer].uv = uv


def add_annulus_sector_z(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    r_inner: float,
    r_outer: float,
    z0: float,
    z1: float,
    ang0_deg: float,
    ang1_deg: float,
    steps: int = 12,
    material_index: int = 0,
) -> None:
    """Add a curved ring sector (or full ring when ang1 - ang0 == 360) centered at (0, 0)."""
    a0 = math.radians(ang0_deg)
    a1 = math.radians(ang1_deg)
    in_bot = []
    in_top = []
    out_bot = []
    out_top = []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * (i / steps)
        ca, sa = math.cos(a), math.sin(a)
        in_bot.append(bm.verts.new((r_inner * ca, r_inner * sa, z0)))
        in_top.append(bm.verts.new((r_inner * ca, r_inner * sa, z1)))
        out_bot.append(bm.verts.new((r_outer * ca, r_outer * sa, z0)))
        out_top.append(bm.verts.new((r_outer * ca, r_outer * sa, z1)))

    uv_quad = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    for i in range(steps):
        jn = i + 1
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

    # End caps at ang0 and ang1
    for verts in (
        [in_bot[0], out_bot[0], out_top[0], in_top[0]],
        [out_bot[-1], in_bot[-1], in_top[-1], out_top[-1]],
    ):
        f = bm.faces.new(verts)
        f.material_index = material_index
        for loop, uv in zip(f.loops, uv_quad):
            loop[uv_layer].uv = uv


def finalize_mesh_obj(
    name: str,
    bm: bmesh.types.BMesh,
    materials: list[bpy.types.Material],
    collection: bpy.types.Collection,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_euler_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    """Convert `bm` to a Blender Mesh Object with uniform (1,1,1) scale and link to `collection`."""
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    for m in materials:
        mesh.materials.append(m)

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    obj.location = Vector(location)
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = Euler(tuple(math.radians(a) for a in rotation_euler_deg), "XYZ")
    obj.scale = Vector((1.0, 1.0, 1.0))
    return obj


def create_socket_attachment_mesh(
    name: str,
    collection: bpy.types.Collection,
    mat: bpy.types.Material,
    location: tuple[float, float, float],
    parent: bpy.types.Object,
    radius: float = 0.04,
) -> bpy.types.Object:
    """Create a small octagonal attachment socket MESH so `resoloop blender export --preserve-hierarchy` preserves it."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    add_frustum_z(bm, uv, (0.0, 0.0), -radius, radius, radius, radius * 0.7, segments=8, material_index=0)
    return finalize_mesh_obj(name, bm, [mat], collection, location=location, parent=parent)


def build_dancing_pumpkin_asset(
    spec: dict[str, Any],
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build one independent G01 dancing pumpkin asset (`APL_DancingPumpkin_001`..`006`)."""
    asset_id = spec["asset_id"]
    pos = tuple(spec["position"])
    rot = tuple(spec["rotation_euler_deg"])

    root_obj = create_empty(
        asset_id,
        collection,
        location=pos,
        rotation_euler_deg=rot,
        display_type="PLAIN_AXES",
        display_size=0.25,
    )

    # Static stone & brass pedestal base (`_Pedestal`, z=0.0..0.24m, radius=0.38m)
    bm_ped = bmesh.new()
    uv_ped = bm_ped.loops.layers.uv.new("UVMap")
    add_frustum_z(bm_ped, uv_ped, (0.0, 0.0), 0.0, 0.16, 0.38, 0.34, segments=12, material_index=0)
    add_frustum_z(bm_ped, uv_ped, (0.0, 0.0), 0.16, 0.24, 0.35, 0.30, segments=12, material_index=1)
    ped_obj = finalize_mesh_obj(
        f"{asset_id}_Pedestal",
        bm_ped,
        [mats["fountain_stone"], mats["plaza_brass"]],
        collection,
        location=(0.0, 0.0, 0.0),
        parent=root_obj,
    )

    # MotionRoot + VisualRoot (`_Body`, pivot at z=0.24m)
    bm_body = bmesh.new()
    uv_body = bm_body.loops.layers.uv.new("UVMap")
    # Ribbed pumpkin body (local z=0.0..0.52m, radius=0.34m)
    add_frustum_z(
        bm_body, uv_body, (0.0, 0.0), 0.0, 0.16, 0.22, 0.34, segments=16, material_index=0, lobes=8, lobe_amp=0.08
    )
    add_frustum_z(
        bm_body, uv_body, (0.0, 0.0), 0.16, 0.38, 0.34, 0.33, segments=16, material_index=0, lobes=8, lobe_amp=0.08
    )
    add_frustum_z(
        bm_body, uv_body, (0.0, 0.0), 0.38, 0.52, 0.33, 0.18, segments=16, material_index=0, lobes=8, lobe_amp=0.06
    )
    # Glowing eyes & smile on -Y face
    add_box(bm_body, uv_body, (-0.15, -0.35, 0.26), (-0.05, -0.28, 0.36), material_index=1)
    add_box(bm_body, uv_body, (0.05, -0.35, 0.26), (0.15, -0.28, 0.36), material_index=1)
    add_box(bm_body, uv_body, (-0.16, -0.36, 0.12), (0.16, -0.28, 0.20), material_index=1)
    # Mini witch hat on top (local z=0.50..0.86m)
    add_frustum_z(bm_body, uv_body, (0.0, 0.0), 0.50, 0.54, 0.32, 0.30, segments=12, material_index=2)
    add_frustum_z(bm_body, uv_body, (0.0, 0.0), 0.54, 0.86, 0.18, 0.02, segments=10, material_index=2)

    body_obj = finalize_mesh_obj(
        f"{asset_id}_Body",
        bm_body,
        [mats["jack_orange"], mats["jack_glow"], mats["witch_hat"]],
        collection,
        location=(0.0, 0.0, 0.24),
        parent=root_obj,
    )

    glow_attach = create_socket_attachment_mesh(
        f"{asset_id}_GlowAttach",
        collection,
        mats["jack_glow"],
        location=(0.0, -0.22, 0.26),
        parent=body_obj,
        radius=0.03,
    )

    return {
        "asset_id": asset_id,
        "category": "gimmick",
        "origin_policy": "ground_center",
        "root": root_obj,
        "all_objs": [root_obj, ped_obj, body_obj, glow_attach],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": ped_obj.name,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": body_obj.name,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.24],
            },
            {
                "part_id": glow_attach.name,
                "role": "attachment_point",
                "parent_part": body_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, -0.22, 0.26],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [body_obj.name],
            "visual_roots": [ped_obj.name, body_obj.name],
            "attachment_points": [glow_attach.name],
        },
        "motion": {
            "gimmick_id": "G01",
            "type": "vertical_bounce_and_tilt",
            "rest_pose_local": [0.0, 0.0, 0.24],
            "bounce_z_range_m": [-0.02, 0.18],
            "tilt_roll_deg_range": [-12.0, 12.0],
            "phase_deg": spec["phase_deg"],
            "envelope_radius_m": 0.55,
            "walkway_clearance_verified": True,
        },
        "notes": f"G01 independent dancing pumpkin ({asset_id}) on stone rim pedestal with separated motion_root body and glow attachment.",
    }


def build_floating_candy_asset(
    spec: dict[str, Any],
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build one independent G02 floating candy asset (`APL_FloatingCandy_001`..`004`)."""
    asset_id = spec["asset_id"]
    pos = tuple(spec["position"])
    rot = tuple(spec["rotation_euler_deg"])
    style = spec["style"]

    root_obj = create_empty(
        asset_id,
        collection,
        location=pos,
        rotation_euler_deg=rot,
        display_type="PLAIN_AXES",
        display_size=0.25,
    )

    hub_obj = create_empty(
        f"{asset_id}_OrbitHub",
        collection,
        location=(0.0, 0.0, 0.0),
        parent=root_obj,
        display_type="ARROWS",
        display_size=0.20,
    )

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    if style == "swirl_lollipop":
        # Stick (z=-0.55..0.0) + large swirl candy disc (z=-0.05..0.45) + ribbon bow
        add_frustum_z(bm, uv, (0.0, 0.0), -0.55, 0.0, 0.035, 0.035, segments=8, material_index=2)
        add_frustum_z(
            bm, uv, (0.0, 0.0), -0.05, 0.45, 0.28, 0.28, segments=16, material_index=0, lobes=6, lobe_amp=0.06
        )
        add_box(bm, uv, (-0.34, -0.09, 0.12), (0.34, 0.09, 0.28), material_index=1)
        add_box(bm, uv, (-0.18, -0.06, -0.14), (0.18, 0.06, -0.02), material_index=1)
    else:
        # Wrapped star/bonbon candy with flared wrapper tails along X
        add_frustum_z(
            bm, uv, (0.0, 0.0), -0.24, 0.24, 0.28, 0.28, segments=14, material_index=1, lobes=5, lobe_amp=0.10
        )
        add_box(bm, uv, (-0.52, -0.16, -0.14), (-0.24, 0.16, 0.14), material_index=0)
        add_box(bm, uv, (0.24, -0.16, -0.14), (0.52, 0.16, 0.14), material_index=0)

    candy_obj = finalize_mesh_obj(
        f"{asset_id}_CandyBody",
        bm,
        [mats["candy_magenta"], mats["candy_gold"], mats["plaza_brass"]],
        collection,
        location=(0.0, 0.0, 0.0),
        parent=hub_obj,
    )

    sparkle_attach = create_socket_attachment_mesh(
        f"{asset_id}_SparkleAttach",
        collection,
        mats["candy_gold"],
        location=(0.0, 0.0, 0.32),
        parent=candy_obj,
        radius=0.03,
    )

    return {
        "asset_id": asset_id,
        "category": "gimmick",
        "origin_policy": "hinge_pivot",
        "root": root_obj,
        "all_objs": [root_obj, hub_obj, candy_obj, sparkle_attach],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": hub_obj.name,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": candy_obj.name,
                "role": "visual_root",
                "parent_part": hub_obj.name,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": sparkle_attach.name,
                "role": "attachment_point",
                "parent_part": candy_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, 0.0, 0.32],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [hub_obj.name],
            "visual_roots": [candy_obj.name],
            "attachment_points": [sparkle_attach.name],
        },
        "motion": {
            "gimmick_id": "G02",
            "type": "hover_bob_and_orbit",
            "motion_center_world": [0.0, 0.0, 2.50],
            "orbit_radius_m": 3.40,
            "orbit_angle_deg": spec["orbit_angle_deg"],
            "bob_z_range_m": [-0.25, 0.25],
            "safe_z_world_range_m": [2.00, 3.10],
            "sightline_clearance_verified": True,
        },
        "notes": f"G02 floating candy ({asset_id}, style={style}) with hover/orbit motion_root and sparkle attachment.",
    }


def build_seq_lantern_asset(
    spec: dict[str, Any],
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build one independent G04 sequential-lighting lantern asset (`APL_SeqLantern_001`..`008`)."""
    asset_id = spec["asset_id"]
    pos = tuple(spec["position"])
    rot = tuple(spec["rotation_euler_deg"])
    seq_idx = int(spec["sequence_index"])

    root_obj = create_empty(
        asset_id,
        collection,
        location=pos,
        rotation_euler_deg=rot,
        display_type="PLAIN_AXES",
        display_size=0.25,
    )

    # Static stone & wrought-iron column (`_Pillar`, z=0.0..2.05m)
    bm_pil = bmesh.new()
    uv_pil = bm_pil.loops.layers.uv.new("UVMap")
    add_frustum_z(bm_pil, uv_pil, (0.0, 0.0), 0.0, 0.35, 0.40, 0.32, segments=8, material_index=0)
    add_frustum_z(bm_pil, uv_pil, (0.0, 0.0), 0.35, 1.85, 0.22, 0.16, segments=8, material_index=1)
    add_frustum_z(bm_pil, uv_pil, (0.0, 0.0), 1.85, 2.05, 0.18, 0.28, segments=8, material_index=2)
    pillar_obj = finalize_mesh_obj(
        f"{asset_id}_Pillar",
        bm_pil,
        [mats["fountain_stone"], mats["gate_iron"], mats["plaza_brass"]],
        collection,
        location=(0.0, 0.0, 0.0),
        parent=root_obj,
    )

    # Lantern cage & glowing core (`_LanternHead`, pivot at z=2.05m, top at z=2.85m)
    bm_head = bmesh.new()
    uv_head = bm_head.loops.layers.uv.new("UVMap")
    add_frustum_z(bm_head, uv_head, (0.0, 0.0), 0.0, 0.52, 0.22, 0.26, segments=8, material_index=1)
    add_frustum_z(bm_head, uv_head, (0.0, 0.0), 0.52, 0.80, 0.30, 0.03, segments=8, material_index=0)
    head_obj = finalize_mesh_obj(
        f"{asset_id}_LanternHead",
        bm_head,
        [mats["gate_iron"], mats["lantern_glow"]],
        collection,
        location=(0.0, 0.0, 2.05),
        parent=root_obj,
    )

    light_attach = create_socket_attachment_mesh(
        f"{asset_id}_LightAttach",
        collection,
        mats["lantern_glow"],
        location=(0.0, 0.0, 0.30),
        parent=head_obj,
        radius=0.035,
    )

    return {
        "asset_id": asset_id,
        "category": "lighting",
        "origin_policy": "ground_center",
        "root": root_obj,
        "all_objs": [root_obj, pillar_obj, head_obj, light_attach],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": pillar_obj.name,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": head_obj.name,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, 0.0, 2.05],
            },
            {
                "part_id": light_attach.name,
                "role": "attachment_point",
                "parent_part": head_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, 0.0, 0.30],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [head_obj.name],
            "visual_roots": [pillar_obj.name, head_obj.name],
            "attachment_points": [light_attach.name],
        },
        "motion": {
            "gimmick_id": "G04",
            "type": "sequential_lantern_chase",
            "sequence_group": "G04_Plaza_Ring_Chase",
            "sequence_index": seq_idx,
            "sequence_total": 8,
            "sector": spec["sector"],
            "light_point_local": [0.0, 0.0, 2.35],
        },
        "notes": f"G04 sequential-lighting plaza lantern #{seq_idx} ({spec['sector']}) at R=9.80m with light attachment point.",
    }


def build_jack_interaction_pedestal(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `APL_JackInteractionPedestal_001` (I03 Giant Jack reaction trigger at (0, -4.65, 0))."""
    asset_id = "APL_JackInteractionPedestal_001"
    root_obj = create_empty(
        asset_id,
        collection,
        location=(0.0, -4.65, 0.0),
        rotation_euler_deg=(0.0, 0.0, 0.0),
        display_type="PLAIN_AXES",
        display_size=0.25,
    )

    bm_base = bmesh.new()
    uv_base = bm_base.loops.layers.uv.new("UVMap")
    add_frustum_z(bm_base, uv_base, (0.0, 0.0), 0.0, 0.22, 0.48, 0.42, segments=8, material_index=0)
    add_frustum_z(bm_base, uv_base, (0.0, 0.0), 0.22, 0.86, 0.26, 0.22, segments=8, material_index=0)
    add_box(bm_base, uv_base, (-0.34, -0.28, 0.86), (0.34, 0.24, 0.96), material_index=1)
    base_obj = finalize_mesh_obj(
        f"{asset_id}_Base",
        bm_base,
        [mats["fountain_stone"], mats["plaza_brass"]],
        collection,
        location=(0.0, 0.0, 0.0),
        parent=root_obj,
    )

    bm_btn = bmesh.new()
    uv_btn = bm_btn.loops.layers.uv.new("UVMap")
    add_frustum_z(
        bm_btn, uv_btn, (0.0, 0.0), 0.0, 0.16, 0.18, 0.14, segments=12, material_index=0, lobes=8, lobe_amp=0.06
    )
    btn_obj = finalize_mesh_obj(
        f"{asset_id}_OrbButton",
        bm_btn,
        [mats["jack_glow"]],
        collection,
        location=(0.0, -0.06, 0.96),
        parent=root_obj,
    )

    eff_attach = create_socket_attachment_mesh(
        f"{asset_id}_EffectAttach",
        collection,
        mats["water_magic"],
        location=(0.0, 0.0, 0.18),
        parent=btn_obj,
        radius=0.03,
    )

    return {
        "asset_id": asset_id,
        "category": "gimmick",
        "origin_policy": "ground_center",
        "root": root_obj,
        "all_objs": [root_obj, base_obj, btn_obj, eff_attach],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": base_obj.name,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": btn_obj.name,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, -0.06, 0.96],
            },
            {
                "part_id": eff_attach.name,
                "role": "attachment_point",
                "parent_part": btn_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, 0.0, 0.18],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [btn_obj.name],
            "visual_roots": [base_obj.name, btn_obj.name],
            "attachment_points": [eff_attach.name],
        },
        "motion": {
            "interaction_id": "I03",
            "type": "button_press_and_remote_reaction",
            "press_axis_local": [0.0, 0.0, -1.0],
            "press_stroke_m": 0.05,
            "linked_targets": [
                "APL_GiantJackProxy_001_EyeLightAttach",
                "APL_GiantJackProxy_001_MouthReactionAttach",
            ],
        },
        "notes": "I03 reachable player interaction pedestal outside south fountain basin, linked to Giant Jack eye and mouth reaction attachment points.",
    }


def build_trick_or_treat_stand(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `APL_TrickOrTreatStand_001` (I01 Trick-or-Treat interactive stand at (-4.80, -6.20, 0.0))."""
    asset_id = "APL_TrickOrTreatStand_001"
    root_obj = create_empty(
        asset_id,
        collection,
        location=(-4.80, -6.20, 0.0),
        rotation_euler_deg=(0.0, 0.0, 35.0),
        display_type="PLAIN_AXES",
        display_size=0.25,
    )

    bm_st = bmesh.new()
    uv_st = bm_st.loops.layers.uv.new("UVMap")
    add_box(bm_st, uv_st, (-0.50, -0.40, 0.0), (0.50, 0.40, 0.18), material_index=0)
    add_box(bm_st, uv_st, (-0.36, -0.28, 0.18), (0.36, 0.28, 0.92), material_index=1)
    # Cauldron/pumpkin candy bowl on top rear (y=+0.02..+0.32, z=0.92..1.32)
    add_frustum_z(bm_st, uv_st, (0.0, 0.12), 0.92, 1.32, 0.24, 0.28, segments=12, material_index=2)
    # Decorative mini arch sign on back
    add_box(bm_st, uv_st, (-0.38, 0.22, 0.92), (-0.30, 0.28, 1.68), material_index=1)
    add_box(bm_st, uv_st, (0.30, 0.22, 0.92), (0.38, 0.28, 1.68), material_index=1)
    add_box(bm_st, uv_st, (-0.42, 0.20, 1.62), (0.42, 0.30, 1.85), material_index=3)
    stand_obj = finalize_mesh_obj(
        f"{asset_id}_Stand",
        bm_st,
        [mats["fountain_stone"], mats["witch_hat"], mats["jack_orange"], mats["plaza_brass"]],
        collection,
        location=(0.0, 0.0, 0.0),
        parent=root_obj,
    )

    bm_btn = bmesh.new()
    uv_btn = bm_btn.loops.layers.uv.new("UVMap")
    add_box(bm_btn, uv_btn, (-0.14, -0.10, 0.0), (0.14, 0.10, 0.09), material_index=0)
    btn_obj = finalize_mesh_obj(
        f"{asset_id}_Button",
        bm_btn,
        [mats["candy_magenta"]],
        collection,
        location=(0.0, -0.18, 0.94),
        parent=root_obj,
    )

    pop_attach = create_socket_attachment_mesh(
        f"{asset_id}_CandyPopAttach",
        collection,
        mats["candy_gold"],
        location=(0.0, 0.12, 1.36),
        parent=stand_obj,
        radius=0.04,
    )

    return {
        "asset_id": asset_id,
        "category": "gimmick",
        "origin_policy": "ground_center",
        "root": root_obj,
        "all_objs": [root_obj, stand_obj, btn_obj, pop_attach],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": stand_obj.name,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": btn_obj.name,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, -0.18, 0.94],
            },
            {
                "part_id": pop_attach.name,
                "role": "attachment_point",
                "parent_part": stand_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, 0.12, 1.36],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [btn_obj.name],
            "visual_roots": [stand_obj.name, btn_obj.name],
            "attachment_points": [pop_attach.name],
        },
        "motion": {
            "interaction_id": "I01",
            "type": "button_press_candy_popup",
            "press_axis_local": [0.0, 0.0, -1.0],
            "press_stroke_m": 0.05,
            "spawn_attachment": pop_attach.name,
        },
        "notes": "I01 Trick-or-Treat interactive stand with separated button motion_root and candy/pumpkin pop-up attachment point.",
    }


def build_fireworks_switch(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `APL_FireworksSwitch_001` (I05 Fireworks launch switch stand at (4.80, -6.20, 0.0))."""
    asset_id = "APL_FireworksSwitch_001"
    root_obj = create_empty(
        asset_id,
        collection,
        location=(4.80, -6.20, 0.0),
        rotation_euler_deg=(0.0, 0.0, -35.0),
        display_type="PLAIN_AXES",
        display_size=0.25,
    )

    bm_ped = bmesh.new()
    uv_ped = bm_ped.loops.layers.uv.new("UVMap")
    add_box(bm_ped, uv_ped, (-0.48, -0.40, 0.0), (0.48, 0.40, 0.20), material_index=0)
    add_box(bm_ped, uv_ped, (-0.32, -0.26, 0.20), (0.32, 0.26, 0.92), material_index=1)
    # Decorative twin rocket launch tubes on rear of pedestal
    add_frustum_z(bm_ped, uv_ped, (-0.16, 0.14), 0.92, 1.48, 0.08, 0.08, segments=10, material_index=2)
    add_frustum_z(bm_ped, uv_ped, (0.16, 0.14), 0.92, 1.48, 0.08, 0.08, segments=10, material_index=2)
    add_frustum_z(bm_ped, uv_ped, (-0.16, 0.14), 1.48, 1.66, 0.11, 0.01, segments=10, material_index=3)
    add_frustum_z(bm_ped, uv_ped, (0.16, 0.14), 1.48, 1.66, 0.11, 0.01, segments=10, material_index=3)
    ped_obj = finalize_mesh_obj(
        f"{asset_id}_Pedestal",
        bm_ped,
        [mats["fountain_stone"], mats["gate_iron"], mats["plaza_brass"], mats["candy_magenta"]],
        collection,
        location=(0.0, 0.0, 0.0),
        parent=root_obj,
    )

    bm_lev = bmesh.new()
    uv_lev = bm_lev.loops.layers.uv.new("UVMap")
    add_box(bm_lev, uv_lev, (-0.04, -0.04, 0.0), (0.04, 0.04, 0.34), material_index=0)
    add_box(bm_lev, uv_lev, (-0.12, -0.06, 0.30), (0.12, 0.06, 0.40), material_index=1)
    lever_obj = finalize_mesh_obj(
        f"{asset_id}_Lever",
        bm_lev,
        [mats["plaza_brass"], mats["jack_glow"]],
        collection,
        location=(0.0, -0.14, 0.92),
        rotation_euler_deg=(-20.0, 0.0, 0.0),
        parent=root_obj,
    )

    sig_attach = create_socket_attachment_mesh(
        f"{asset_id}_LaunchSignalAttach",
        collection,
        mats["jack_glow"],
        location=(0.0, 0.14, 1.68),
        parent=ped_obj,
        radius=0.04,
    )

    return {
        "asset_id": asset_id,
        "category": "gimmick",
        "origin_policy": "ground_center",
        "root": root_obj,
        "all_objs": [root_obj, ped_obj, lever_obj, sig_attach],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": ped_obj.name,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": lever_obj.name,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [0.0, -0.14, 0.92],
            },
            {
                "part_id": sig_attach.name,
                "role": "attachment_point",
                "parent_part": ped_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, 0.14, 1.68],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [lever_obj.name],
            "visual_roots": [ped_obj.name, lever_obj.name],
            "attachment_points": [sig_attach.name],
        },
        "motion": {
            "interaction_id": "I05",
            "type": "lever_pull_fireworks_trigger",
            "hinge_axis_local": [1.0, 0.0, 0.0],
            "angle_range_deg": [-25.0, 25.0],
            "linked_targets": [
                "APL_PeriodicShowRig_001_FireworksLaunchAttach",
                "APL_PeriodicShowRig_001_FireworksBurstAttach",
            ],
        },
        "notes": "I05 Fireworks launch switch stand with separated lever motion_root and sky fireworks trigger attachment point.",
    }


def build_photo_arch(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `APL_PhotoArch_001`: photo spot stage & crescent-moon pumpkin arch at (11.20, -11.20, 0.0)."""
    asset_id = "APL_PhotoArch_001"
    root_obj = create_empty(
        asset_id,
        collection,
        location=(11.20, -11.20, 0.0),
        rotation_euler_deg=(0.0, 0.0, 45.0),
        display_type="PLAIN_AXES",
        display_size=0.30,
    )

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    # Stepped circular stage platform (z=0.0..0.18m, radius=1.85m)
    add_frustum_z(bm, uv, (0.0, 0.0), 0.0, 0.10, 1.85, 1.80, segments=16, material_index=0)
    add_frustum_z(bm, uv, (0.0, 0.0), 0.10, 0.18, 1.55, 1.50, segments=16, material_index=2)
    # Left & Right ornate arch columns (x=-1.40 and x=+1.40, z=0.18..2.65m)
    for sx in (-1.0, 1.0):
        add_box(bm, uv, (sx * 1.52, -0.22, 0.18), (sx * 1.24, 0.22, 0.65), material_index=0)
        add_box(bm, uv, (sx * 1.46, -0.15, 0.65), (sx * 1.30, 0.15, 2.65), material_index=1)
        # Side mini jack-o'-lantern finial at column shoulder
        add_frustum_z(
            bm, uv, (sx * 1.38, -0.18), 1.65, 1.98, 0.20, 0.18, segments=10, material_index=3, lobes=6, lobe_amp=0.06
        )
    # Overhead gothic arch beam & crescent moon crest (z=2.65..3.55m)
    add_box(bm, uv, (-1.56, -0.18, 2.65), (1.56, 0.18, 2.95), material_index=1)
    add_box(bm, uv, (-1.10, -0.14, 2.95), (1.10, 0.14, 3.25), material_index=2)
    add_frustum_z(bm, uv, (0.0, 0.0), 3.25, 3.65, 0.36, 0.06, segments=10, material_index=4)

    arch_obj = finalize_mesh_obj(
        f"{asset_id}_ArchStage",
        bm,
        [
            mats["fountain_stone"],
            mats["gate_iron"],
            mats["plaza_brass"],
            mats["jack_orange"],
            mats["lantern_glow"],
        ],
        collection,
        location=(0.0, 0.0, 0.0),
        parent=root_obj,
    )

    stand_marker = create_socket_attachment_mesh(
        f"{asset_id}_StandMarker",
        collection,
        mats["plaza_brass"],
        location=(0.0, 0.0, 0.20),
        parent=arch_obj,
        radius=0.05,
    )
    spot_attach = create_socket_attachment_mesh(
        f"{asset_id}_SpotLightAttach",
        collection,
        mats["lantern_glow"],
        location=(0.0, -1.10, 2.85),
        parent=arch_obj,
        radius=0.04,
    )

    return {
        "asset_id": asset_id,
        "category": "architecture",
        "origin_policy": "ground_center",
        "root": root_obj,
        "all_objs": [root_obj, arch_obj, stand_marker, spot_attach],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": arch_obj.name,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": stand_marker.name,
                "role": "attachment_point",
                "parent_part": arch_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, 0.0, 0.20],
            },
            {
                "part_id": spot_attach.name,
                "role": "attachment_point",
                "parent_part": arch_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, -1.10, 2.85],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [],
            "visual_roots": [arch_obj.name],
            "attachment_points": [stand_marker.name, spot_attach.name],
        },
        "notes": "Dedicated SE plaza photo spot stage & crescent-moon pumpkin arch outside all 4 cardinal sightlines, framing the central fountain and Giant Jack.",
    }


def build_periodic_show_rig(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `APL_PeriodicShowRig_001`: periodic plaza show projector pylons & attachment points (Spec 9.2)."""
    asset_id = "APL_PeriodicShowRig_001"
    root_obj = create_empty(
        asset_id,
        collection,
        location=(0.0, 0.0, 0.0),
        rotation_euler_deg=(0.0, 0.0, 0.0),
        display_type="PLAIN_AXES",
        display_size=0.35,
    )

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    # 4 diagonal show projector pylons at (+/-13.2, +/-8.2, 0.0..3.60m), outside the ring road, photo spot axis, & sightlines
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            px, py = sx * 13.2, sy * 8.2
            add_frustum_z(bm, uv, (px, py), 0.0, 0.45, 0.52, 0.44, segments=8, material_index=0)
            add_frustum_z(bm, uv, (px, py), 0.45, 3.15, 0.26, 0.18, segments=8, material_index=1)
            add_frustum_z(bm, uv, (px, py), 3.15, 3.60, 0.22, 0.34, segments=8, material_index=2)
            add_frustum_z(bm, uv, (px, py), 3.60, 3.92, 0.26, 0.06, segments=8, material_index=3)

    # North outer terrace fireworks mortar battery at (-3.2, 15.8, 0.0..1.20m) beside north bridge
    # Placed at (-3.2, 15.8, 0.0) so North sightline (|x|<=2.0) is 100% clear
    add_box(bm, uv, (-3.7, 15.3, 0.0), (-2.7, 16.3, 0.35), material_index=0)
    add_frustum_z(bm, uv, (-3.2, 15.8), 0.35, 1.20, 0.24, 0.20, segments=10, material_index=2)

    pylons_obj = finalize_mesh_obj(
        f"{asset_id}_Pylons",
        bm,
        [mats["fountain_stone"], mats["gate_iron"], mats["plaza_brass"], mats["water_magic"]],
        collection,
        location=(0.0, 0.0, 0.0),
        parent=root_obj,
    )

    attachment_specs = [
        ("GhostOrbitAttach_N", (0.0, 3.80, 4.80), mats["water_magic"]),
        ("GhostOrbitAttach_E", (3.80, 0.0, 4.80), mats["water_magic"]),
        ("GhostOrbitAttach_S", (0.0, -3.80, 4.80), mats["water_magic"]),
        ("GhostOrbitAttach_W", (-3.80, 0.0, 4.80), mats["water_magic"]),
        ("ShowLightAttach_NE", (13.20, 8.20, 3.95), mats["lantern_glow"]),
        ("ShowLightAttach_NW", (-13.20, 8.20, 3.95), mats["lantern_glow"]),
        ("ShowLightAttach_SE", (13.20, -8.20, 3.95), mats["lantern_glow"]),
        ("ShowLightAttach_SW", (-13.20, -8.20, 3.95), mats["lantern_glow"]),
        ("FireworksLaunchAttach", (-3.20, 15.80, 1.25), mats["jack_glow"]),
        ("FireworksBurstAttach", (0.0, 0.0, 14.50), mats["candy_gold"]),
        ("HappyHalloweenBannerAttach", (0.0, 0.0, 11.20), mats["candy_gold"]),
    ]

    attach_objs: list[bpy.types.Object] = []
    parts_list: list[dict[str, Any]] = [
        {
            "part_id": asset_id,
            "role": "asset_root",
            "parent_part": None,
            "origin_policy": "ground_center",
            "pivot_local": [0.0, 0.0, 0.0],
        },
        {
            "part_id": pylons_obj.name,
            "role": "static_part",
            "parent_part": asset_id,
            "origin_policy": "ground_center",
            "pivot_local": [0.0, 0.0, 0.0],
        },
    ]

    for suffix, loc, mat in attachment_specs:
        part_name = f"{asset_id}_{suffix}"
        a_obj = create_socket_attachment_mesh(
            part_name,
            collection,
            mat,
            location=loc,
            parent=pylons_obj,
            radius=0.04,
        )
        attach_objs.append(a_obj)
        parts_list.append(
            {
                "part_id": part_name,
                "role": "attachment_point",
                "parent_part": pylons_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [round(loc[0], 4), round(loc[1], 4), round(loc[2], 4)],
            }
        )

    return {
        "asset_id": asset_id,
        "category": "gimmick",
        "origin_policy": "ground_center",
        "root": root_obj,
        "all_objs": [root_obj, pylons_obj, *attach_objs],
        "parts": parts_list,
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [],
            "visual_roots": [pylons_obj.name],
            "attachment_points": [o.name for o in attach_objs],
        },
        "motion": {
            "show_id": "Spec_9_2_Periodic_Plaza_Show",
            "type": "periodic_show_attachment_rig",
            "ghost_orbit_attachments": [
                f"{asset_id}_GhostOrbitAttach_N",
                f"{asset_id}_GhostOrbitAttach_E",
                f"{asset_id}_GhostOrbitAttach_S",
                f"{asset_id}_GhostOrbitAttach_W",
            ],
            "show_light_attachments": [
                f"{asset_id}_ShowLightAttach_NE",
                f"{asset_id}_ShowLightAttach_NW",
                f"{asset_id}_ShowLightAttach_SE",
                f"{asset_id}_ShowLightAttach_SW",
            ],
            "fireworks_launch_attachment": f"{asset_id}_FireworksLaunchAttach",
            "fireworks_burst_attachment": f"{asset_id}_FireworksBurstAttach",
            "happy_halloween_banner_attachment": f"{asset_id}_HappyHalloweenBannerAttach",
        },
        "notes": "Periodic plaza show rig (Spec 9.2) with 4 diagonal bastion projector pylons and attachment sockets for ghosts, show lights, fireworks, and HAPPY HALLOWEEN overhead sky banner.",
    }


def build_entrance_gate_proxy(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `APL_EntranceGateProxy_001` (M01 placeholder/proxy at (0.0, -40.0, 0.0), exact 11.0 x 2.622 x 7.739m)."""
    asset_id = "APL_EntranceGateProxy_001"
    root_obj = create_empty(
        asset_id,
        collection,
        location=(0.0, -40.0, 0.0),
        rotation_euler_deg=(0.0, 0.0, 0.0),
        display_type="PLAIN_AXES",
        display_size=0.40,
    )

    bm_arch = bmesh.new()
    uv_arch = bm_arch.loops.layers.uv.new("UVMap")
    # Exact W09 M01 outer envelope: x in [-5.500, +5.500] (11.0m), y in [-1.311, +1.311] (2.622m), z in [0.000, 7.739] (7.739m)
    # Central clear portal opening: x in [-2.180, +2.180] (4.36m wide), z in [0.000, 3.973] (3.973m high)
    for sx in (-1.0, 1.0):
        # Outer stone & wrought-iron wing wall (|x|=3.65..5.50)
        x_out_min = -5.500 if sx < 0 else 3.650
        x_out_max = -3.650 if sx < 0 else 5.500
        add_box(bm_arch, uv_arch, (x_out_min, -1.311, 0.0), (x_out_max, 1.311, 0.85), material_index=0)
        add_box(bm_arch, uv_arch, (x_out_min + 0.15, -0.45, 0.85), (x_out_max - 0.15, 0.45, 3.45), material_index=1)
        # Main gatehouse stone tower pillar (|x|=2.180..3.650, z=0.0..5.15m)
        x_pil_min = -3.650 if sx < 0 else 2.180
        x_pil_max = -2.180 if sx < 0 else 3.650
        add_box(bm_arch, uv_arch, (x_pil_min, -1.20, 0.0), (x_pil_max, 1.20, 4.45), material_index=0)
        add_box(bm_arch, uv_arch, (x_pil_min - 0.08, -1.26, 4.45), (x_pil_max + 0.08, 1.26, 5.10), material_index=2)
        # Pillar pumpkin finial & spire (z=5.10..6.45m)
        add_frustum_z(
            bm_arch,
            uv_arch,
            (sx * 2.915, 0.0),
            5.10,
            5.95,
            0.58,
            0.52,
            segments=12,
            material_index=3,
            lobes=8,
            lobe_amp=0.06,
        )
        add_frustum_z(bm_arch, uv_arch, (sx * 2.915, 0.0), 5.95, 6.60, 0.36, 0.04, segments=8, material_index=1)

    # Overhead wrought-iron & stone gothic arch bridge above z=3.973m (clear of 4.36m x 3.973m portal)
    add_box(bm_arch, uv_arch, (-3.650, -0.88, 3.973), (3.650, 0.88, 5.20), material_index=1)
    add_box(bm_arch, uv_arch, (-2.650, -0.68, 5.20), (2.650, 0.68, 6.35), material_index=2)
    # Central crown pumpkin crest & finial reaching exact z=7.739m
    add_frustum_z(
        bm_arch, uv_arch, (0.0, 0.0), 6.35, 7.20, 0.68, 0.58, segments=14, material_index=3, lobes=8, lobe_amp=0.07
    )
    add_frustum_z(bm_arch, uv_arch, (0.0, 0.0), 7.20, 7.739, 0.38, 0.04, segments=10, material_index=4)

    arch_obj = finalize_mesh_obj(
        f"{asset_id}_Arch",
        bm_arch,
        [
            mats["fountain_stone"],
            mats["gate_iron"],
            mats["plaza_brass"],
            mats["jack_orange"],
            mats["lantern_glow"],
        ],
        collection,
        location=(0.0, 0.0, 0.0),
        parent=root_obj,
    )

    # Left & Right hinged wrought-iron gate leaves (`_DoorLeft`, `_DoorRight`) opened 88 deg into +Y
    # so the 4.36m walkway is completely clear while providing hinged motion_roots
    bm_dl = bmesh.new()
    uv_dl = bm_dl.loops.layers.uv.new("UVMap")
    add_box(bm_dl, uv_dl, (0.0, -0.06, 0.12), (1.15, 0.06, 3.40), material_index=0)
    door_left_obj = finalize_mesh_obj(
        f"{asset_id}_DoorLeft",
        bm_dl,
        [mats["gate_iron"]],
        collection,
        location=(-2.18, 0.0, 0.0),
        rotation_euler_deg=(0.0, 0.0, 88.0),
        parent=root_obj,
    )

    bm_dr = bmesh.new()
    uv_dr = bm_dr.loops.layers.uv.new("UVMap")
    add_box(bm_dr, uv_dr, (-1.15, -0.06, 0.12), (0.0, 0.06, 3.40), material_index=0)
    door_right_obj = finalize_mesh_obj(
        f"{asset_id}_DoorRight",
        bm_dr,
        [mats["gate_iron"]],
        collection,
        location=(2.18, 0.0, 0.0),
        rotation_euler_deg=(0.0, 0.0, -88.0),
        parent=root_obj,
    )

    lantern_left = create_socket_attachment_mesh(
        f"{asset_id}_LanternAttachLeft",
        collection,
        mats["lantern_glow"],
        location=(-2.45, -0.65, 3.60),
        parent=arch_obj,
        radius=0.05,
    )
    lantern_right = create_socket_attachment_mesh(
        f"{asset_id}_LanternAttachRight",
        collection,
        mats["lantern_glow"],
        location=(2.45, -0.65, 3.60),
        parent=arch_obj,
        radius=0.05,
    )
    banner_attach = create_socket_attachment_mesh(
        f"{asset_id}_BannerAttach",
        collection,
        mats["plaza_brass"],
        location=(0.0, -0.65, 5.80),
        parent=arch_obj,
        radius=0.05,
    )

    return {
        "asset_id": asset_id,
        "category": "architecture",
        "origin_policy": "ground_center",
        "root": root_obj,
        "all_objs": [
            root_obj,
            arch_obj,
            door_left_obj,
            door_right_obj,
            lantern_left,
            lantern_right,
            banner_attach,
        ],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": arch_obj.name,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": door_left_obj.name,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [-2.18, 0.0, 0.0],
            },
            {
                "part_id": door_right_obj.name,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "hinge_pivot",
                "pivot_local": [2.18, 0.0, 0.0],
            },
            {
                "part_id": lantern_left.name,
                "role": "attachment_point",
                "parent_part": arch_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [-2.45, -0.65, 3.60],
            },
            {
                "part_id": lantern_right.name,
                "role": "attachment_point",
                "parent_part": arch_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [2.45, -0.65, 3.60],
            },
            {
                "part_id": banner_attach.name,
                "role": "attachment_point",
                "parent_part": arch_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, -0.65, 5.80],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [door_left_obj.name, door_right_obj.name],
            "visual_roots": [arch_obj.name, door_left_obj.name, door_right_obj.name],
            "attachment_points": [lantern_left.name, lantern_right.name, banner_attach.name],
        },
        "motion": {
            "meshy_slot": "M01",
            "type": "double_hinged_gate_doors",
            "clear_opening_width_m": 4.36,
            "clear_opening_height_m": 3.973,
            "door_left_hinge_local": [-2.18, 0.0, 0.0],
            "door_right_hinge_local": [2.18, 0.0, 0.0],
        },
        "replacement": {
            "is_placeholder": True,
            "modifiable": True,
            "notes": "M01 entrance gate arch placeholder/proxy at W09-verified threshold (0, -40, 0), matching W09 dimensions (11.0m x 2.622m x 7.739m) and clear opening (4.36m x 3.973m).",
            "future_target": "M01_EntranceGate",
            "replacement_slot": {
                "meshy_id": "M01",
                "target_asset_id": "MSH_EntranceGate_001",
                "origin_policy": "ground_center",
                "origin_world": [0.0, -40.0, 0.0],
                "front_world": "-Y",
                "raw_glb_rotation_z_deg": 180.0,
                "dimensions_m": {"width": 11.0, "depth": 2.622, "height": 7.739},
                "clear_opening_m": {"width": 4.36, "height": 3.973},
            },
        },
        "notes": "M01 entrance gate arch placeholder/proxy at (0, -40, 0) with separated arch, hinged doors, lantern attachments, and banner attachment.",
    }


def build_entrance_guide_sign(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `APL_EntranceGuideSign_001`: 5-area welcome & directional signpost at (2.85, -37.2, 0.0)."""
    asset_id = "APL_EntranceGuideSign_001"
    root_obj = create_empty(
        asset_id,
        collection,
        location=(2.85, -37.2, 0.0),
        rotation_euler_deg=(0.0, 0.0, -25.0),
        display_type="PLAIN_AXES",
        display_size=0.25,
    )

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    # Stone plinth & wrought-iron post (z=0.0..2.55m)
    add_frustum_z(bm, uv, (0.0, 0.0), 0.0, 0.35, 0.38, 0.32, segments=8, material_index=0)
    add_frustum_z(bm, uv, (0.0, 0.0), 0.35, 2.45, 0.10, 0.08, segments=8, material_index=1)
    # Directional sign boards pointing toward A Plaza (+Y), B Mansion (+Y), C Candy (+X), D Amusement (-Y), E Forest (-X)
    add_box(bm, uv, (-0.65, -0.06, 1.35), (0.65, 0.06, 1.68), material_index=2)
    add_box(bm, uv, (-0.12, -0.58, 1.72), (0.12, 0.58, 1.98), material_index=3)
    add_box(bm, uv, (-0.55, -0.05, 2.02), (0.55, 0.05, 2.28), material_index=2)
    # Mini pumpkin lantern topper at z=2.45..2.75m
    add_frustum_z(
        bm, uv, (0.0, 0.0), 2.45, 2.75, 0.18, 0.14, segments=10, material_index=4, lobes=6, lobe_amp=0.06
    )

    sign_obj = finalize_mesh_obj(
        f"{asset_id}_SignPost",
        bm,
        [
            mats["fountain_stone"],
            mats["gate_iron"],
            mats["plaza_brass"],
            mats["witch_hat"],
            mats["jack_orange"],
        ],
        collection,
        location=(0.0, 0.0, 0.0),
        parent=root_obj,
    )

    light_attach = create_socket_attachment_mesh(
        f"{asset_id}_LightAttach",
        collection,
        mats["lantern_glow"],
        location=(-0.15, -0.22, 2.25),
        parent=sign_obj,
        radius=0.035,
    )

    return {
        "asset_id": asset_id,
        "category": "prop",
        "origin_policy": "ground_center",
        "root": root_obj,
        "all_objs": [root_obj, sign_obj, light_attach],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": sign_obj.name,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": light_attach.name,
                "role": "attachment_point",
                "parent_part": sign_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [-0.15, -0.22, 2.25],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [],
            "visual_roots": [sign_obj.name],
            "attachment_points": [light_attach.name],
        },
        "notes": "South entrance welcome & 5-area directional signpost placed at (2.85, -37.2, 0.0) outside the 4.0m promenade and sightline.",
    }
