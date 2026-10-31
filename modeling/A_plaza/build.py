"""Deterministically build `blender/A_plaza/A_plaza.blend`, render `review/A_plaza/`, and emit `A_plaza` layout/manifest JSONs.

Run via:
    resoloop blender run modeling/A_plaza/build.py --json
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
from mathutils import Vector  # type: ignore

from modeling.A_plaza.gimmicks import (
    add_annulus_sector_z,
    add_box,
    add_frustum_z,
    build_dancing_pumpkin_asset,
    build_entrance_gate_proxy,
    build_entrance_guide_sign,
    build_fireworks_switch,
    build_floating_candy_asset,
    build_jack_interaction_pedestal,
    build_periodic_show_rig,
    build_photo_arch,
    build_seq_lantern_asset,
    build_trick_or_treat_stand,
    create_socket_attachment_mesh,
    finalize_mesh_obj,
)
from modeling.A_plaza.layout_data import (
    COMMON_PLACEMENT_SPECS,
    DANCING_PUMPKIN_SPECS,
    FLOATING_CANDY_SPECS,
    SEQ_LANTERN_SPECS,
    build_plaza_area_layout_dict,
)
from modeling.common.build import build_common
from modeling.lib.common_parts import append_common_part
from modeling.lib.materials import create_pbr_material
from modeling.lib.primitives import create_empty
from modeling.lib.render import render_review_images
from modeling.lib.scene import reset_scene, save_blend

KEY = "A_plaza"
BLEND_REL_PATH = "blender/A_plaza/A_plaza.blend"
COMMON_BLEND_REL_PATH = "blender/common/common.blend"
SCRIPT_REL_PATH = "modeling/A_plaza/build.py"
AREA_LAYOUT_REL_PATH = "layout/areas/A_plaza.json"
MANIFEST_REL_PATH = "assets/manifest/A_plaza.json"


def get_plaza_materials() -> dict[str, bpy.types.Material]:
    """Create or retrieve PBR materials (`MAT_APL_*`) for the `A_plaza` scene."""
    return {
        "plaza_stone": create_pbr_material(
            "MAT_APL_PlazaStone",
            base_color=(0.30, 0.25, 0.36, 1.0),
            roughness=0.72,
            metallic=0.05,
        ),
        "plaza_mosaic": create_pbr_material(
            "MAT_APL_PlazaMosaic",
            base_color=(0.44, 0.33, 0.48, 1.0),
            roughness=0.62,
            metallic=0.08,
        ),
        "plaza_brass": create_pbr_material(
            "MAT_APL_PlazaBrass",
            base_color=(0.85, 0.64, 0.22, 1.0),
            roughness=0.32,
            metallic=0.82,
        ),
        "fountain_stone": create_pbr_material(
            "MAT_APL_FountainStone",
            base_color=(0.36, 0.32, 0.42, 1.0),
            roughness=0.68,
            metallic=0.06,
        ),
        "water_magic": create_pbr_material(
            "MAT_APL_MagicWater",
            base_color=(0.34, 0.62, 0.96, 1.0),
            roughness=0.16,
            metallic=0.10,
            emission_color=(0.28, 0.55, 0.98, 1.0),
            emission_strength=1.8,
        ),
        "jack_orange": create_pbr_material(
            "MAT_APL_JackOrange",
            base_color=(0.94, 0.40, 0.06, 1.0),
            roughness=0.46,
            metallic=0.02,
        ),
        "jack_glow": create_pbr_material(
            "MAT_APL_JackGlow",
            base_color=(1.00, 0.82, 0.18, 1.0),
            roughness=0.20,
            metallic=0.0,
            emission_color=(1.00, 0.76, 0.14, 1.0),
            emission_strength=3.6,
        ),
        "witch_hat": create_pbr_material(
            "MAT_APL_WitchHat",
            base_color=(0.20, 0.12, 0.34, 1.0),
            roughness=0.58,
            metallic=0.12,
        ),
        "gate_iron": create_pbr_material(
            "MAT_APL_GateIron",
            base_color=(0.15, 0.14, 0.20, 1.0),
            roughness=0.38,
            metallic=0.85,
        ),
        "lantern_glow": create_pbr_material(
            "MAT_APL_LanternGlow",
            base_color=(1.00, 0.68, 0.16, 1.0),
            roughness=0.22,
            metallic=0.0,
            emission_color=(1.00, 0.64, 0.12, 1.0),
            emission_strength=3.2,
        ),
        "candy_magenta": create_pbr_material(
            "MAT_APL_CandyMagenta",
            base_color=(0.90, 0.22, 0.58, 1.0),
            roughness=0.28,
            metallic=0.08,
            emission_color=(0.85, 0.18, 0.52, 1.0),
            emission_strength=1.1,
        ),
        "candy_gold": create_pbr_material(
            "MAT_APL_CandyGold",
            base_color=(0.98, 0.78, 0.20, 1.0),
            roughness=0.25,
            metallic=0.35,
            emission_color=(0.98, 0.74, 0.18, 1.0),
            emission_strength=1.4,
        ),
        "planter_foliage": create_pbr_material(
            "MAT_APL_PlanterFoliage",
            base_color=(0.28, 0.18, 0.36, 1.0),
            roughness=0.78,
            metallic=0.0,
        ),
    }


def build_plaza_paving(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `APL_PlazaPaving_001`: central plaza cobblestone floor, arcane brass rings, and 4 diagonal planters."""
    asset_id = "APL_PlazaPaving_001"
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")

    # Slot 0: plaza_stone, Slot 1: plaza_mosaic, Slot 2: plaza_brass, Slot 3: fountain_stone, Slot 4: planter_foliage
    # 1. Outer island plaza base disc (R=17.5m, z=0.00..0.04m) and inner ring road border (R=10.75..14.25m, z=0.04..0.06m)
    add_frustum_z(bm, uv, (0.0, 0.0), 0.0, 0.04, 17.5, 17.5, segments=32, material_index=0)
    add_annulus_sector_z(bm, uv, 10.75, 14.25, 0.04, 0.06, 0.0, 360.0, steps=36, material_index=1)
    # Brass inlay rings framing the fountain promenade (R=5.2m..5.45m and R=10.55m..10.75m, z=0.04..0.068m)
    add_annulus_sector_z(bm, uv, 5.20, 5.45, 0.04, 0.068, 0.0, 360.0, steps=32, material_index=2)
    add_annulus_sector_z(bm, uv, 10.55, 10.75, 0.04, 0.068, 0.0, 360.0, steps=36, material_index=2)

    # 2. Four cardinal walkway mosaic carpets (North, South, East, West, width=3.8m, flush at z=0.04..0.065m)
    add_box(bm, uv, (-1.90, 5.45, 0.04), (1.90, 17.40, 0.065), material_index=1)
    add_box(bm, uv, (-1.90, -14.25, 0.04), (1.90, -5.45, 0.065), material_index=1)
    add_box(bm, uv, (5.45, -1.90, 0.04), (17.40, 1.90, 0.065), material_index=1)
    add_box(bm, uv, (-17.40, -1.90, 0.04), (-5.45, 1.90, 0.065), material_index=1)

    # 3. Four curved diagonal flowerbed planters (R=8.4m..10.1m, z=0.04..0.42m) in NE, NW, SW, SE sectors
    # Positioned at 28..62 deg, 118..152 deg, 208..242 deg, 298..332 deg so cardinal walkways & sightlines are 100% clear
    for ang0, ang1 in ((28.0, 62.0), (118.0, 152.0), (208.0, 242.0), (298.0, 332.0)):
        add_annulus_sector_z(bm, uv, 8.40, 10.10, 0.04, 0.42, ang0, ang1, steps=8, material_index=3)
        add_annulus_sector_z(bm, uv, 8.62, 9.88, 0.42, 0.52, ang0 + 1.5, ang1 - 1.5, steps=8, material_index=4)

    obj = finalize_mesh_obj(
        asset_id,
        bm,
        [
            mats["plaza_stone"],
            mats["plaza_mosaic"],
            mats["plaza_brass"],
            mats["fountain_stone"],
            mats["planter_foliage"],
        ],
        collection,
        location=(0.0, 0.0, 0.0),
    )

    return {
        "asset_id": asset_id,
        "category": "architecture",
        "origin_policy": "ground_center",
        "root": obj,
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
        "notes": "Central plaza cobblestone disc, brass arcane rings, 4 cardinal mosaic walkways, and 4 diagonal flowerbed planters.",
    }


def build_fountain(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `APL_Fountain_001` (G03 tiered fountain at (0,0,0), outer D=8.4m, central pedestal top z=1.60m)."""
    asset_id = "APL_Fountain_001"
    root_obj = create_empty(
        asset_id,
        collection,
        location=(0.0, 0.0, 0.0),
        rotation_euler_deg=(0.0, 0.0, 0.0),
        display_type="PLAIN_AXES",
        display_size=0.40,
    )

    # 1. Static stone basin & central pedestal (`_Basin`, outer R=4.20m, pedestal top z=1.60m supporting M02)
    bm_basin = bmesh.new()
    uv_basin = bm_basin.loops.layers.uv.new("UVMap")
    # Outer circular step & basin floor (R=4.20m, z=0.0..0.18m)
    add_frustum_z(bm_basin, uv_basin, (0.0, 0.0), 0.0, 0.18, 4.20, 4.12, segments=24, material_index=0)
    # Outer basin rim wall (R=3.65..4.12m, z=0.18..0.58m)
    add_annulus_sector_z(bm_basin, uv_basin, 3.65, 4.12, 0.18, 0.58, 0.0, 360.0, steps=24, material_index=0)
    add_annulus_sector_z(bm_basin, uv_basin, 3.60, 4.16, 0.58, 0.65, 0.0, 360.0, steps=24, material_index=1)
    # 8 carved pumpkin gargoyle spouts around outer rim at R=3.85m
    for i in range(8):
        ang = math.radians(i * 45.0 + 22.5)
        gx, gy = 3.85 * math.cos(ang), 3.85 * math.sin(ang)
        add_frustum_z(
            bm_basin, uv_basin, (gx, gy), 0.65, 0.92, 0.24, 0.20, segments=10, material_index=2, lobes=6, lobe_amp=0.06
        )
    # Middle tier scalloped bowl (R=2.85m, z=0.18..1.12m)
    add_frustum_z(bm_basin, uv_basin, (0.0, 0.0), 0.18, 0.95, 2.55, 2.85, segments=20, material_index=0)
    add_annulus_sector_z(bm_basin, uv_basin, 2.45, 2.90, 0.95, 1.15, 0.0, 360.0, steps=20, material_index=1)
    # Central M02 support pedestal (R=2.25m, top exactly at z=1.60m)
    add_frustum_z(bm_basin, uv_basin, (0.0, 0.0), 0.95, 1.52, 2.28, 2.18, segments=20, material_index=0)
    add_frustum_z(bm_basin, uv_basin, (0.0, 0.0), 1.52, 1.60, 2.24, 2.20, segments=20, material_index=1)

    basin_obj = finalize_mesh_obj(
        f"{asset_id}_Basin",
        bm_basin,
        [mats["fountain_stone"], mats["plaza_brass"], mats["jack_orange"]],
        collection,
        location=(0.0, 0.0, 0.0),
        parent=root_obj,
    )

    # 2. Separated animated water surface & cascading water veil (`_Water`, motion_root + visual_root)
    bm_water = bmesh.new()
    uv_water = bm_water.loops.layers.uv.new("UVMap")
    # Lower pool glowing water ring (R=2.60..3.64m, z=0.46..0.52m)
    add_annulus_sector_z(bm_water, uv_water, 2.60, 3.64, 0.46, 0.52, 0.0, 360.0, steps=24, material_index=0)
    # Middle pool glowing water ring & waterfall curtain (R=2.18..2.62m, z=0.52..1.08m)
    add_annulus_sector_z(bm_water, uv_water, 2.18, 2.62, 0.52, 1.08, 0.0, 360.0, steps=24, material_index=0)
    # Upper pedestal water crown ring (R=2.12..2.32m, z=1.08..1.55m)
    add_annulus_sector_z(bm_water, uv_water, 2.12, 2.32, 1.08, 1.55, 0.0, 360.0, steps=20, material_index=0)

    water_obj = finalize_mesh_obj(
        f"{asset_id}_Water",
        bm_water,
        [mats["water_magic"]],
        collection,
        location=(0.0, 0.0, 0.0),
        parent=root_obj,
    )

    water_attach = create_socket_attachment_mesh(
        f"{asset_id}_WaterAttach",
        collection,
        mats["water_magic"],
        location=(0.0, 0.0, 1.55),
        parent=basin_obj,
        radius=0.05,
    )
    light_attach = create_socket_attachment_mesh(
        f"{asset_id}_LightAttach",
        collection,
        mats["lantern_glow"],
        location=(0.0, -2.50, 0.65),
        parent=basin_obj,
        radius=0.05,
    )
    sound_attach = create_socket_attachment_mesh(
        f"{asset_id}_SoundAttach",
        collection,
        mats["plaza_brass"],
        location=(0.0, 0.0, 1.10),
        parent=basin_obj,
        radius=0.05,
    )

    return {
        "asset_id": asset_id,
        "category": "gimmick",
        "origin_policy": "ground_center",
        "root": root_obj,
        "all_objs": [root_obj, basin_obj, water_obj, water_attach, light_attach, sound_attach],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": basin_obj.name,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": water_obj.name,
                "role": "motion_root",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": water_attach.name,
                "role": "attachment_point",
                "parent_part": basin_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, 0.0, 1.55],
            },
            {
                "part_id": light_attach.name,
                "role": "attachment_point",
                "parent_part": basin_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, -2.50, 0.65],
            },
            {
                "part_id": sound_attach.name,
                "role": "attachment_point",
                "parent_part": basin_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, 0.0, 1.10],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [water_obj.name],
            "visual_roots": [basin_obj.name, water_obj.name],
            "attachment_points": [water_attach.name, light_attach.name, sound_attach.name],
        },
        "motion": {
            "gimmick_id": "G03",
            "type": "tiered_fountain_water_and_glow",
            "water_mesh_part": water_obj.name,
            "pedestal_top_z_m": 1.60,
            "outer_diameter_m": 8.40,
        },
        "notes": "G03 central tiered fountain with separated static stone basin/pedestal, animated water veil mesh, and water/light/sound attachment points.",
    }


def build_giant_jack_proxy(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `APL_GiantJackProxy_001` (M02 placeholder/proxy at (0, 0, 1.60), exact 6.202 x 5.87 x 6.0m)."""
    asset_id = "APL_GiantJackProxy_001"
    root_obj = create_empty(
        asset_id,
        collection,
        location=(0.0, 0.0, 1.60),
        rotation_euler_deg=(0.0, 0.0, 0.0),
        display_type="PLAIN_AXES",
        display_size=0.45,
    )

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    # Exact W09 M02 local bounds: x in [-3.101, +3.101] (6.202m), y in [-2.935, +2.935] (5.87m), z in [0.0, 6.0] (6.0m)
    # 1. Pumpkin base collar & 16-ribbed giant pumpkin body (z=0.0..3.15m, radius up to 2.75m)
    add_frustum_z(bm, uv, (0.0, 0.0), 0.0, 0.55, 1.85, 2.52, segments=24, material_index=0, lobes=12, lobe_amp=0.05)
    add_frustum_z(bm, uv, (0.0, 0.0), 0.55, 1.65, 2.52, 2.76, segments=24, material_index=0, lobes=12, lobe_amp=0.05)
    add_frustum_z(bm, uv, (0.0, 0.0), 1.65, 2.65, 2.76, 2.48, segments=24, material_index=0, lobes=12, lobe_amp=0.05)
    add_frustum_z(bm, uv, (0.0, 0.0), 2.65, 3.18, 2.48, 1.72, segments=24, material_index=0, lobes=12, lobe_amp=0.04)

    # 2. Expressive glowing jack-o'-lantern face on the South (-Y) front (y=-2.82..-2.42m)
    # Left & Right triangular/angled glowing eyes (z=1.95..2.55m)
    add_box(bm, uv, (-1.18, -2.76, 1.98), (-0.42, -2.35, 2.52), material_index=1)
    add_box(bm, uv, (0.42, -2.76, 1.98), (1.18, -2.35, 2.52), material_index=1)
    # Glowing jack-o'-lantern nose triangle (z=1.58..1.88m)
    add_box(bm, uv, (-0.22, -2.80, 1.58), (0.22, -2.38, 1.88), material_index=1)
    # Wide grinning toothy mouth across -Y (z=0.92..1.48m)
    add_box(bm, uv, (-1.45, -2.78, 0.96), (1.45, -2.35, 1.44), material_index=1)
    add_box(bm, uv, (-1.82, -2.62, 1.15), (-1.35, -2.25, 1.58), material_index=1)
    add_box(bm, uv, (1.35, -2.62, 1.15), (1.82, -2.25, 1.58), material_index=1)

    # 3. Grand Witch Hat with wide brim & brass buckle reaching exact outer bounds:
    # Brim spans x in [-3.101, +3.101] and y in [-2.935, +2.935] at z=2.92..3.32m
    add_box(bm, uv, (-3.101, -0.45, 3.02), (3.101, 0.45, 3.22), material_index=2)
    add_box(bm, uv, (-0.45, -2.935, 3.02), (0.45, 2.935, 3.22), material_index=2)
    add_frustum_z(bm, uv, (0.0, 0.0), 2.95, 3.26, 2.92, 2.84, segments=24, material_index=2)
    # Hat band & golden buckle on South (-Y) front (z=3.26..3.68m)
    add_frustum_z(bm, uv, (0.0, 0.0), 3.26, 3.68, 1.78, 1.62, segments=20, material_index=3)
    add_box(bm, uv, (-0.42, -1.82, 3.28), (0.42, -1.58, 3.72), material_index=4)
    # Tall tapered witch hat cone & curled tip reaching exact z=6.000m (world z=7.600m)
    add_frustum_z(bm, uv, (0.0, 0.0), 3.68, 4.95, 1.62, 0.78, segments=18, material_index=2)
    add_frustum_z(bm, uv, (0.0, 0.12), 4.95, 5.72, 0.78, 0.26, segments=14, material_index=2)
    add_frustum_z(bm, uv, (0.0, 0.28), 5.72, 6.00, 0.26, 0.05, segments=10, material_index=3)

    body_obj = finalize_mesh_obj(
        f"{asset_id}_Body",
        bm,
        [
            mats["jack_orange"],
            mats["jack_glow"],
            mats["witch_hat"],
            mats["plaza_brass"],
            mats["candy_gold"],
        ],
        collection,
        location=(0.0, 0.0, 0.0),
        parent=root_obj,
    )

    eye_attach = create_socket_attachment_mesh(
        f"{asset_id}_EyeLightAttach",
        collection,
        mats["jack_glow"],
        location=(0.0, -2.676, 2.317),
        parent=body_obj,
        radius=0.05,
    )
    mouth_attach = create_socket_attachment_mesh(
        f"{asset_id}_MouthReactionAttach",
        collection,
        mats["jack_glow"],
        location=(0.0, -2.806, 1.372),
        parent=body_obj,
        radius=0.05,
    )
    interior_attach = create_socket_attachment_mesh(
        f"{asset_id}_InteriorLightAttach",
        collection,
        mats["lantern_glow"],
        location=(0.0, 2.409, 0.981),
        parent=body_obj,
        radius=0.05,
    )

    return {
        "asset_id": asset_id,
        "category": "gimmick",
        "origin_policy": "ground_center",
        "root": root_obj,
        "all_objs": [root_obj, body_obj, eye_attach, mouth_attach, interior_attach],
        "parts": [
            {
                "part_id": asset_id,
                "role": "asset_root",
                "parent_part": None,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": body_obj.name,
                "role": "static_part",
                "parent_part": asset_id,
                "origin_policy": "ground_center",
                "pivot_local": [0.0, 0.0, 0.0],
            },
            {
                "part_id": eye_attach.name,
                "role": "attachment_point",
                "parent_part": body_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, -2.676, 2.317],
            },
            {
                "part_id": mouth_attach.name,
                "role": "attachment_point",
                "parent_part": body_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, -2.806, 1.372],
            },
            {
                "part_id": interior_attach.name,
                "role": "attachment_point",
                "parent_part": body_obj.name,
                "origin_policy": "attachment_point",
                "pivot_local": [0.0, 2.409, 0.981],
            },
        ],
        "hierarchy": {
            "asset_root": asset_id,
            "motion_roots": [],
            "visual_roots": [body_obj.name],
            "attachment_points": [eye_attach.name, mouth_attach.name, interior_attach.name],
        },
        "motion": {
            "meshy_slot": "M02",
            "interaction_id": "I03",
            "type": "landmark_reaction_socket_target",
            "trigger_source_asset": "APL_JackInteractionPedestal_001",
            "eye_light_socket": eye_attach.name,
            "mouth_reaction_socket": mouth_attach.name,
            "interior_light_socket": interior_attach.name,
        },
        "replacement": {
            "is_placeholder": True,
            "modifiable": True,
            "notes": "M02 Giant Jack-o'-Lantern with witch hat placeholder/proxy mounted on the G03 fountain pedestal at (0, 0, 1.60), matching W09 dimensions (6.202m x 5.87m x 6.0m, top z=7.60m).",
            "future_target": "M02_GiantJack",
            "replacement_slot": {
                "meshy_id": "M02",
                "target_asset_id": "MSH_GiantJack_001",
                "origin_policy": "ground_center",
                "origin_world": [0.0, 0.0, 1.60],
                "front_world": "-Y",
                "raw_glb_rotation_z_deg": 180.0,
                "dimensions_m": {"width": 6.202, "depth": 5.87, "height": 6.0},
            },
        },
        "notes": "M02 Giant Jack-o'-Lantern with witch hat placeholder/proxy atop the fountain pedestal at (0, 0, 1.60) with eye/mouth/interior reaction attachment points.",
    }


def build_entrance_approach(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build `APL_EntranceApproach_001`: South Entrance spawn medallion at (0,-44,0) and promenade curb to (0,-14.5,0)."""
    asset_id = "APL_EntranceApproach_001"
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")

    # Origin at (0.0, -30.0, 0.0)
    # 1. South Spawn Arrival Terrace medallion at world (0, -44, 0) -> local (0, -14, 0), flush at z=0.0..0.068m
    add_frustum_z(bm, uv, (0.0, -14.0), 0.0, 0.062, 3.20, 3.20, segments=24, material_index=1)
    add_annulus_sector_z_offset(bm, uv, (0.0, -14.0), 2.85, 3.15, 0.062, 0.072, steps=24, material_index=2)
    add_frustum_z(bm, uv, (0.0, -14.0), 0.062, 0.072, 0.95, 0.95, segments=16, material_index=2)

    # 2. Ceremonial 3.8m-wide promenade carpet inlay from world y=-41.0..-14.25 (local y=-11.0..+15.75, z=0.04..0.065m)
    add_box(bm, uv, (-1.90, -11.0, 0.04), (1.90, 15.75, 0.065), material_index=1)
    # Brass edge strips framing the 4.0m walkway at x = +/-1.95m (flush at z=0.04..0.072m)
    add_box(bm, uv, (-2.02, -11.0, 0.04), (-1.88, 15.75, 0.072), material_index=2)
    add_box(bm, uv, (1.88, -11.0, 0.04), (2.02, 15.75, 0.072), material_index=2)

    # 3. M01 Gate threshold stone apron at world y=-40.0m (local y=-10.0m, x=-5.6..+5.6, z=0.0..0.065m)
    add_box(bm, uv, (-5.60, -11.40, 0.0), (5.60, -8.60, 0.062), material_index=0)

    obj = finalize_mesh_obj(
        asset_id,
        bm,
        [mats["plaza_stone"], mats["plaza_mosaic"], mats["plaza_brass"]],
        collection,
        location=(0.0, -30.0, 0.0),
    )

    return {
        "asset_id": asset_id,
        "category": "architecture",
        "origin_policy": "ground_center",
        "root": obj,
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
        "notes": "South Entrance spawn compass medallion at (0, -44, 0), M01 gate threshold apron at (0, -40, 0), and ceremonial promenade inlay leading to the Central Plaza.",
    }


def add_annulus_sector_z_offset(
    bm: bmesh.types.BMesh,
    uv_layer: Any,
    center_xy: tuple[float, float],
    r_inner: float,
    r_outer: float,
    z0: float,
    z1: float,
    steps: int = 24,
    material_index: int = 0,
) -> None:
    """Add a full 360-deg ring centered at `center_xy`."""
    cx, cy = center_xy
    in_bot = []
    in_top = []
    out_bot = []
    out_top = []
    for i in range(steps):
        a = 2.0 * math.pi * i / steps
        ca, sa = math.cos(a), math.sin(a)
        in_bot.append(bm.verts.new((cx + r_inner * ca, cy + r_inner * sa, z0)))
        in_top.append(bm.verts.new((cx + r_inner * ca, cy + r_inner * sa, z1)))
        out_bot.append(bm.verts.new((cx + r_outer * ca, cy + r_outer * sa, z0)))
        out_top.append(bm.verts.new((cx + r_outer * ca, cy + r_outer * sa, z1)))

    uv_quad = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    for i in range(steps):
        jn = (i + 1) % steps
        for verts in (
            [in_top[i], out_top[i], out_top[jn], in_top[jn]],
            [out_bot[i], in_bot[i], in_bot[jn], out_bot[jn]],
            [out_bot[i], out_bot[jn], out_top[jn], out_top[i]],
            [in_bot[jn], in_bot[i], in_top[i], in_top[jn]],
        ):
            f = bm.faces.new(verts)
            f.material_index = material_index
            for loop, uv in zip(f.loops, uv_quad):
                loop[uv_layer].uv = uv


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


def place_plaza_common_parts(collection: bpy.types.Collection, common_blend_path: Path) -> list[bpy.types.Object]:
    """Place reusable common parts from `blender/common/common.blend` into the `A_plaza` collection."""
    placed: list[bpy.types.Object] = []
    for cp in COMMON_PLACEMENT_SPECS:
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


def _make_plaza_manifest_entry(asset_spec: dict[str, Any]) -> dict[str, Any]:
    root_obj: bpy.types.Object = asset_spec["root"]
    all_objs: list[bpy.types.Object] = asset_spec["all_objs"]
    tris, verts = _count_mesh_stats(all_objs)
    bounds = _compute_local_bounds(all_objs, root_obj.location)
    bmin = bounds["min"]
    bmax = bounds["max"]
    width = round(max(0.01, bmax[0] - bmin[0]), 4)
    depth = round(max(0.01, bmax[1] - bmin[1]), 4)
    height = round(max(0.01, bmax[2] - bmin[2]), 4)

    mat_names: list[str] = []
    for obj in all_objs:
        if obj.type == "MESH" and obj.data is not None:
            for m in obj.data.materials:
                if m is not None and m.name not in mat_names:
                    mat_names.append(m.name)

    replacement = asset_spec.get(
        "replacement",
        {
            "is_placeholder": False,
            "modifiable": True,
            "notes": asset_spec["notes"],
            "future_target": None,
        },
    )

    entry: dict[str, Any] = {
        "asset_id": asset_spec["asset_id"],
        "key": KEY,
        "category": asset_spec["category"],
        "area_id": KEY,
        "collection": KEY,
        "blend_file": BLEND_REL_PATH,
        "script_file": SCRIPT_REL_PATH,
        "origin_policy": asset_spec["origin_policy"],
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
        "bounds_local": bounds,
        "parts": asset_spec["parts"],
        "hierarchy": asset_spec["hierarchy"],
        "materials": mat_names,
        "textures": [],
        "metrics": {
            "measured": True,
            "measurement_source": "blender_scene",
            "triangles": tris,
            "vertices": verts,
            "materials_count": len(mat_names),
            "objects_count": len(all_objs),
        },
        "export_result": {
            "status": "unexported",
            "bundle_dir": None,
            "apply_plan": None,
            "report_file": None,
        },
        "replacement": replacement,
    }
    if "motion" in asset_spec:
        entry["motion"] = asset_spec["motion"]
    return entry


def write_plaza_data_files(root: Path, built_assets: list[dict[str, Any]]) -> None:
    """Write `layout/areas/A_plaza.json` and `assets/manifest/A_plaza.json`."""
    area_layout_path = root / AREA_LAYOUT_REL_PATH
    manifest_path = root / MANIFEST_REL_PATH

    area_layout_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    area_layout_data = build_plaza_area_layout_dict()
    manifest_data: dict[str, Any] = {
        "schema_version": "1.0",
        "key": KEY,
        "updated_at": "2026-10-31T12:00:00Z",
        "assets": [_make_plaza_manifest_entry(spec) for spec in built_assets],
    }

    area_layout_path.write_text(
        json.dumps(area_layout_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_plaza() -> dict[str, Any]:
    """Build the `A_plaza` scene, render `review/A_plaza/`, save `blender/A_plaza/A_plaza.blend`, and write JSONs."""
    common_blend_path = PROJECT_ROOT / COMMON_BLEND_REL_PATH
    if not common_blend_path.is_file():
        build_common()

    _scene, plaza_col = reset_scene(KEY, seed=202)
    mats = get_plaza_materials()

    built_assets: list[dict[str, Any]] = [
        build_plaza_paving(plaza_col, mats),
        build_fountain(plaza_col, mats),
        build_giant_jack_proxy(plaza_col, mats),
        build_jack_interaction_pedestal(plaza_col, mats),
    ]

    for dp_spec in DANCING_PUMPKIN_SPECS:
        built_assets.append(build_dancing_pumpkin_asset(dp_spec, plaza_col, mats))

    for fc_spec in FLOATING_CANDY_SPECS:
        built_assets.append(build_floating_candy_asset(fc_spec, plaza_col, mats))

    for sl_spec in SEQ_LANTERN_SPECS:
        built_assets.append(build_seq_lantern_asset(sl_spec, plaza_col, mats))

    built_assets.extend(
        [
            build_trick_or_treat_stand(plaza_col, mats),
            build_fireworks_switch(plaza_col, mats),
            build_photo_arch(plaza_col, mats),
            build_periodic_show_rig(plaza_col, mats),
            build_entrance_gate_proxy(plaza_col, mats),
            build_entrance_approach(plaza_col, mats),
            build_entrance_guide_sign(plaza_col, mats),
        ]
    )

    placed_common = place_plaza_common_parts(plaza_col, common_blend_path)

    overview_png = PROJECT_ROOT / "review" / "A_plaza" / "01_plaza_overview.png"
    fountain_jack_png = PROJECT_ROOT / "review" / "A_plaza" / "02_fountain_giant_jack_i01_i03_i05.png"
    entrance_gate_png = PROJECT_ROOT / "review" / "A_plaza" / "03_south_entrance_gate_m01.png"
    photo_gimmicks_png = PROJECT_ROOT / "review" / "A_plaza" / "04_gimmicks_show_photo_spot.png"

    render_review_images(
        views=[
            {
                "filepath": overview_png,
                "location": (22.0, -28.0, 18.5),
                "target": (0.0, 0.0, 2.5),
                "lens_mm": 26.0,
            },
            {
                "filepath": fountain_jack_png,
                "location": (0.0, -13.2, 2.2),
                "target": (0.0, 0.0, 3.4),
                "lens_mm": 28.0,
            },
            {
                "filepath": entrance_gate_png,
                "location": (0.0, -48.5, 2.6),
                "target": (0.0, -20.0, 2.8),
                "lens_mm": 28.0,
            },
            {
                "filepath": photo_gimmicks_png,
                "location": (15.2, -15.2, 2.6),
                "target": (0.0, 0.0, 2.6),
                "lens_mm": 26.0,
            },
        ],
        width=1280,
        height=720,
        samples=32,
    )

    blend_path = PROJECT_ROOT / BLEND_REL_PATH
    save_blend(blend_path, pack_images=True)

    write_plaza_data_files(PROJECT_ROOT, built_assets)

    summary = {
        "key": KEY,
        "blend_file": BLEND_REL_PATH,
        "objects_count": len(bpy.data.objects),
        "plaza_assets_count": len(built_assets),
        "common_instances_count": len(placed_common),
        "object_names": sorted(o.name for o in bpy.data.objects),
        "meshes_count": len(bpy.data.meshes),
        "materials_count": len(bpy.data.materials),
        "review_images": [
            str(overview_png.relative_to(PROJECT_ROOT)),
            str(fountain_jack_png.relative_to(PROJECT_ROOT)),
            str(entrance_gate_png.relative_to(PROJECT_ROOT)),
            str(photo_gimmicks_png.relative_to(PROJECT_ROOT)),
        ],
    }
    print("A_PLAZA_BUILD_SUMMARY:" + json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    build_plaza()
