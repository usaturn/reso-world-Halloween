"""Area layout (`layout/areas/A_plaza.json`) and placement specifications for `A_plaza` (W02 / Issue #4)."""

from __future__ import annotations

from typing import Any

# G01: 6 independent dancing pumpkins around the outer fountain rim (R = 4.75m, clear of 3.5m ring road & sightlines)
DANCING_PUMPKIN_SPECS: list[dict[str, Any]] = [
    {
        "asset_id": "APL_DancingPumpkin_001",
        "position": [-2.72, -3.89, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 35.0],
        "phase_deg": 0.0,
        "hat_tilt_deg": 10.0,
    },
    {
        "asset_id": "APL_DancingPumpkin_002",
        "position": [2.72, -3.89, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -35.0],
        "phase_deg": 60.0,
        "hat_tilt_deg": -10.0,
    },
    {
        "asset_id": "APL_DancingPumpkin_003",
        "position": [4.59, -1.23, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -75.0],
        "phase_deg": 120.0,
        "hat_tilt_deg": 8.0,
    },
    {
        "asset_id": "APL_DancingPumpkin_004",
        "position": [-4.59, -1.23, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 75.0],
        "phase_deg": 180.0,
        "hat_tilt_deg": -8.0,
    },
    {
        "asset_id": "APL_DancingPumpkin_005",
        "position": [3.36, 3.36, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -135.0],
        "phase_deg": 240.0,
        "hat_tilt_deg": 12.0,
    },
    {
        "asset_id": "APL_DancingPumpkin_006",
        "position": [-3.36, 3.36, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 135.0],
        "phase_deg": 300.0,
        "hat_tilt_deg": -12.0,
    },
]

# G02: 4 independent floating candies hovering over the fountain basin (R = 3.40m, z = 2.45..2.55m)
FLOATING_CANDY_SPECS: list[dict[str, Any]] = [
    {
        "asset_id": "APL_FloatingCandy_001",
        "position": [-2.40, -2.40, 2.45],
        "rotation_euler_deg": [0.0, 0.0, 45.0],
        "style": "swirl_lollipop",
        "orbit_angle_deg": 225.0,
    },
    {
        "asset_id": "APL_FloatingCandy_002",
        "position": [2.40, -2.40, 2.45],
        "rotation_euler_deg": [0.0, 0.0, -45.0],
        "style": "wrapped_star",
        "orbit_angle_deg": 315.0,
    },
    {
        "asset_id": "APL_FloatingCandy_003",
        "position": [2.40, 2.40, 2.55],
        "rotation_euler_deg": [0.0, 0.0, -135.0],
        "style": "swirl_lollipop",
        "orbit_angle_deg": 45.0,
    },
    {
        "asset_id": "APL_FloatingCandy_004",
        "position": [-2.40, 2.40, 2.55],
        "rotation_euler_deg": [0.0, 0.0, 135.0],
        "style": "wrapped_star",
        "orbit_angle_deg": 135.0,
    },
]

# G04: 8 sequential-lighting plaza lanterns in an octagonal ring at R = 9.80m flanking the 4 cardinal entrances
SEQ_LANTERN_SPECS: list[dict[str, Any]] = [
    {
        "asset_id": "APL_SeqLantern_001",
        "sequence_index": 1,
        "position": [-3.75, -9.05, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 22.5],
        "sector": "SW_SouthLeft",
    },
    {
        "asset_id": "APL_SeqLantern_002",
        "sequence_index": 2,
        "position": [3.75, -9.05, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -22.5],
        "sector": "SE_SouthRight",
    },
    {
        "asset_id": "APL_SeqLantern_003",
        "sequence_index": 3,
        "position": [9.05, -3.75, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -67.5],
        "sector": "SE_EastRight",
    },
    {
        "asset_id": "APL_SeqLantern_004",
        "sequence_index": 4,
        "position": [9.05, 3.75, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -112.5],
        "sector": "NE_EastLeft",
    },
    {
        "asset_id": "APL_SeqLantern_005",
        "sequence_index": 5,
        "position": [3.75, 9.05, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -157.5],
        "sector": "NE_NorthRight",
    },
    {
        "asset_id": "APL_SeqLantern_006",
        "sequence_index": 6,
        "position": [-3.75, 9.05, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 157.5],
        "sector": "NW_NorthLeft",
    },
    {
        "asset_id": "APL_SeqLantern_007",
        "sequence_index": 7,
        "position": [-9.05, 3.75, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 112.5],
        "sector": "NW_WestRight",
    },
    {
        "asset_id": "APL_SeqLantern_008",
        "sequence_index": 8,
        "position": [-9.05, -3.75, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 67.5],
        "sector": "SW_WestLeft",
    },
]

# Common parts placed in A_plaza (complementing `world.json` without overlapping any WLD_* instances)
COMMON_PLACEMENT_SPECS: list[dict[str, Any]] = [
    {
        "placement_id": "APL_CP_PortalLamp_NorthEast_001",
        "common_asset_id": "CMN_StreetLamp_001",
        "instance_name": "APL_PortalLamp_NorthEast_001",
        "position": [2.3, 14.2, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 0.0],
        "role": "North bridge portal east streetlamp (paired with WLD_PortalLamp_North_001)",
    },
    {
        "placement_id": "APL_CP_PortalLamp_EastSouth_001",
        "common_asset_id": "CMN_StreetLamp_001",
        "instance_name": "APL_PortalLamp_EastSouth_001",
        "position": [14.2, -2.3, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -90.0],
        "role": "East bridge portal south streetlamp (paired with WLD_PortalLamp_East_001)",
    },
    {
        "placement_id": "APL_CP_PortalLamp_SouthWest_001",
        "common_asset_id": "CMN_StreetLamp_001",
        "instance_name": "APL_PortalLamp_SouthWest_001",
        "position": [-2.3, -14.2, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 180.0],
        "role": "South bridge portal west streetlamp (paired with WLD_PortalLamp_South_001)",
    },
    {
        "placement_id": "APL_CP_PortalLamp_WestNorth_001",
        "common_asset_id": "CMN_StreetLamp_001",
        "instance_name": "APL_PortalLamp_WestNorth_001",
        "position": [-14.2, 2.3, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 90.0],
        "role": "West bridge portal north streetlamp (paired with WLD_PortalLamp_West_001)",
    },
    {
        "placement_id": "APL_CP_EntranceLamp_GateLeft_001",
        "common_asset_id": "CMN_StreetLamp_001",
        "instance_name": "APL_EntranceLamp_GateLeft_001",
        "position": [-3.4, -38.0, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 90.0],
        "role": "South entrance M01 gate north-west approach streetlamp",
    },
    {
        "placement_id": "APL_CP_EntranceLamp_GateRight_001",
        "common_asset_id": "CMN_StreetLamp_001",
        "instance_name": "APL_EntranceLamp_GateRight_001",
        "position": [3.4, -38.0, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -90.0],
        "role": "South entrance M01 gate north-east approach streetlamp",
    },
    {
        "placement_id": "APL_CP_PlazaBench_NW_001",
        "common_asset_id": "CMN_Bench_001",
        "instance_name": "APL_PlazaBench_NW_001",
        "position": [-7.2, 7.2, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -45.0],
        "role": "NW inner plaza viewing bench facing the central fountain and Giant Jack",
    },
    {
        "placement_id": "APL_CP_PlazaBench_NE_001",
        "common_asset_id": "CMN_Bench_001",
        "instance_name": "APL_PlazaBench_NE_001",
        "position": [7.2, 7.2, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 45.0],
        "role": "NE inner plaza viewing bench facing the central fountain and Giant Jack",
    },
    {
        "placement_id": "APL_CP_PlazaBench_SW_001",
        "common_asset_id": "CMN_Bench_001",
        "instance_name": "APL_PlazaBench_SW_001",
        "position": [-7.2, -7.2, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -135.0],
        "role": "SW inner plaza viewing bench facing the central fountain and Giant Jack",
    },
    {
        "placement_id": "APL_CP_PortalGarland_North_001",
        "common_asset_id": "CMN_GarlandFlag_001",
        "instance_name": "APL_PortalGarland_North_001",
        "position": [0.0, 14.5, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 0.0],
        "role": "North portal festive bunting arch toward Area B Haunted Mansion",
    },
    {
        "placement_id": "APL_CP_PortalGarland_East_001",
        "common_asset_id": "CMN_GarlandFlag_001",
        "instance_name": "APL_PortalGarland_East_001",
        "position": [14.5, 0.0, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 90.0],
        "role": "East portal festive bunting arch toward Area C Candy Market",
    },
    {
        "placement_id": "APL_CP_PortalGarland_West_001",
        "common_asset_id": "CMN_GarlandFlag_001",
        "instance_name": "APL_PortalGarland_West_001",
        "position": [-14.5, 0.0, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -90.0],
        "role": "West portal festive bunting arch toward Area E Witch's Forest",
    },
    {
        "placement_id": "APL_CP_ClusterPumpkin_GateWest_001",
        "common_asset_id": "CMN_SmallPumpkin_001",
        "instance_name": "APL_ClusterPumpkin_GateWest_001",
        "position": [-3.1, -41.4, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 20.0],
        "role": "Decorative pumpkin cluster at south-west base of M01 entrance gate",
    },
    {
        "placement_id": "APL_CP_ClusterPumpkin_GateEast_001",
        "common_asset_id": "CMN_SmallPumpkin_001",
        "instance_name": "APL_ClusterPumpkin_GateEast_001",
        "position": [3.1, -41.4, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -25.0],
        "role": "Decorative pumpkin cluster at south-east base of M01 entrance gate",
    },
    {
        "placement_id": "APL_CP_PhotoSpotLantern_001",
        "common_asset_id": "CMN_Lantern_001",
        "instance_name": "APL_PhotoSpotLantern_001",
        "position": [9.8, -12.4, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 45.0],
        "role": "Warm accent lantern beside the SE photo spot arch stage",
    },
    {
        "placement_id": "APL_CP_OuterFence_NW_001",
        "common_asset_id": "CMN_Fence_001",
        "instance_name": "APL_OuterFence_NW_001",
        "position": [-10.6, 10.6, 0.0],
        "rotation_euler_deg": [0.0, 0.0, 45.0],
        "role": "Ornamental wrought-iron fence backing the NW plaza planter",
    },
    {
        "placement_id": "APL_CP_OuterFence_NE_001",
        "common_asset_id": "CMN_Fence_001",
        "instance_name": "APL_OuterFence_NE_001",
        "position": [10.6, 10.6, 0.0],
        "rotation_euler_deg": [0.0, 0.0, -45.0],
        "role": "Ornamental wrought-iron fence backing the NE plaza planter",
    },
]


def build_plaza_area_layout_dict() -> dict[str, Any]:
    """Return the complete `layout/areas/A_plaza.json` dictionary conforming to `area_layout.schema.json`."""
    common_category_by_id: dict[str, tuple[str, float]] = {
        "CMN_StreetLamp_001": ("lighting", 0.50),
        "CMN_Fence_001": ("architecture", 1.50),
        "CMN_GarlandFlag_001": ("prop", 1.85),
        "CMN_Bench_001": ("prop", 0.90),
        "CMN_Lantern_001": ("lighting", 0.30),
        "CMN_SmallPumpkin_001": ("prop", 0.35),
    }

    placements: list[dict[str, Any]] = [
        {
            "placement_id": "APL_PL_PlazaPaving_001",
            "asset_id": "APL_PlazaPaving_001",
            "source_key": "A_plaza",
            "category": "architecture",
            "origin_policy": "ground_center",
            "position": [0.0, 0.0, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
            "clearance_radius_m": 0.0,
            "notes": "Central plaza radial mosaic paving, arcane brass inlay, and 4 diagonal flowerbed planters.",
        },
        {
            "placement_id": "APL_PL_Fountain_001",
            "asset_id": "APL_Fountain_001",
            "source_key": "A_plaza",
            "category": "gimmick",
            "origin_policy": "ground_center",
            "position": [0.0, 0.0, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
            "clearance_radius_m": 4.20,
            "notes": "G03 tiered central fountain (outer basin D=8.4m, pedestal top z=1.60m supporting M02).",
        },
        {
            "placement_id": "APL_PL_GiantJackProxy_001",
            "asset_id": "APL_GiantJackProxy_001",
            "source_key": "A_plaza",
            "category": "gimmick",
            "origin_policy": "ground_center",
            "position": [0.0, 0.0, 1.60],
            "rotation_euler_deg": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
            "clearance_radius_m": 3.10,
            "notes": "M02 placeholder/proxy (6.202m x 5.87m x 6.0m, top z=7.60m) facing South (-Y) on the fountain pedestal. Raw M02 asset has front_local=+Y and uses rotation_z_deg=180.0.",
        },
        {
            "placement_id": "APL_PL_JackInteractionPedestal_001",
            "asset_id": "APL_JackInteractionPedestal_001",
            "source_key": "A_plaza",
            "category": "gimmick",
            "origin_policy": "ground_center",
            "position": [0.0, -4.65, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
            "clearance_radius_m": 0.50,
            "notes": "I03 reachable player interaction pedestal at south rim of fountain, linked to Giant Jack eye/mouth reaction sockets.",
        },
    ]

    for idx, dp in enumerate(DANCING_PUMPKIN_SPECS, start=1):
        placements.append(
            {
                "placement_id": f"APL_PL_DancingPumpkin_{idx:03d}",
                "asset_id": dp["asset_id"],
                "source_key": "A_plaza",
                "category": "gimmick",
                "origin_policy": "ground_center",
                "position": list(dp["position"]),
                "rotation_euler_deg": list(dp["rotation_euler_deg"]),
                "scale": [1.0, 1.0, 1.0],
                "clearance_radius_m": 0.55,
                "notes": f"G01 dancing pumpkin #{idx} around fountain rim (phase={dp['phase_deg']} deg).",
            }
        )

    for idx, fc in enumerate(FLOATING_CANDY_SPECS, start=1):
        placements.append(
            {
                "placement_id": f"APL_PL_FloatingCandy_{idx:03d}",
                "asset_id": fc["asset_id"],
                "source_key": "A_plaza",
                "category": "gimmick",
                "origin_policy": "hinge_pivot",
                "position": list(fc["position"]),
                "rotation_euler_deg": list(fc["rotation_euler_deg"]),
                "scale": [1.0, 1.0, 1.0],
                "clearance_radius_m": 0.55,
                "notes": f"G02 floating candy #{idx} ({fc['style']}) orbiting fountain at R=3.4m.",
            }
        )

    for idx, sl in enumerate(SEQ_LANTERN_SPECS, start=1):
        placements.append(
            {
                "placement_id": f"APL_PL_SeqLantern_{idx:03d}",
                "asset_id": sl["asset_id"],
                "source_key": "A_plaza",
                "category": "lighting",
                "origin_policy": "ground_center",
                "position": list(sl["position"]),
                "rotation_euler_deg": list(sl["rotation_euler_deg"]),
                "scale": [1.0, 1.0, 1.0],
                "clearance_radius_m": 0.45,
                "notes": f"G04 sequential-lighting lantern #{idx} (sector={sl['sector']}, R=9.80m).",
            }
        )

    placements.extend(
        [
            {
                "placement_id": "APL_PL_TrickOrTreatStand_001",
                "asset_id": "APL_TrickOrTreatStand_001",
                "source_key": "A_plaza",
                "category": "gimmick",
                "origin_policy": "ground_center",
                "position": [-4.80, -6.20, 0.0],
                "rotation_euler_deg": [0.0, 0.0, 35.0],
                "scale": [1.0, 1.0, 1.0],
                "clearance_radius_m": 0.60,
                "notes": "I01 Trick-or-Treat interactive button stand with candy/pumpkin pop-up attachment point.",
            },
            {
                "placement_id": "APL_PL_FireworksSwitch_001",
                "asset_id": "APL_FireworksSwitch_001",
                "source_key": "A_plaza",
                "category": "gimmick",
                "origin_policy": "ground_center",
                "position": [4.80, -6.20, 0.0],
                "rotation_euler_deg": [0.0, 0.0, -35.0],
                "scale": [1.0, 1.0, 1.0],
                "clearance_radius_m": 0.60,
                "notes": "I05 fireworks launch lever switch stand with sky launch signal attachment point.",
            },
            {
                "placement_id": "APL_PL_PhotoArch_001",
                "asset_id": "APL_PhotoArch_001",
                "source_key": "A_plaza",
                "category": "architecture",
                "origin_policy": "ground_center",
                "position": [11.20, -11.20, 0.0],
                "rotation_euler_deg": [0.0, 0.0, 45.0],
                "scale": [1.0, 1.0, 1.0],
                "clearance_radius_m": 1.85,
                "notes": "Dedicated photo spot stage & crescent-moon pumpkin arch in SE alcove, framing the central fountain and Giant Jack outside all 4 cardinal sightlines.",
            },
            {
                "placement_id": "APL_PL_PeriodicShowRig_001",
                "asset_id": "APL_PeriodicShowRig_001",
                "source_key": "A_plaza",
                "category": "gimmick",
                "origin_policy": "ground_center",
                "position": [0.0, 0.0, 0.0],
                "rotation_euler_deg": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "clearance_radius_m": 0.55,
                "notes": "Periodic plaza show rig (Spec 9.2) with 4 diagonal projector pylons and attachment sockets for ghosts, show lights, fireworks, and HAPPY HALLOWEEN overhead banner.",
            },
            {
                "placement_id": "APL_PL_EntranceGateProxy_001",
                "asset_id": "APL_EntranceGateProxy_001",
                "source_key": "A_plaza",
                "category": "architecture",
                "origin_policy": "ground_center",
                "position": [0.0, -40.0, 0.0],
                "rotation_euler_deg": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "clearance_radius_m": 5.50,
                "notes": "M01 entrance gate arch placeholder/proxy at W09-verified threshold (0, -40, 0), 11.0m x 2.622m x 7.739m with 4.36m x 3.973m clear portal.",
            },
            {
                "placement_id": "APL_PL_EntranceApproach_001",
                "asset_id": "APL_EntranceApproach_001",
                "source_key": "A_plaza",
                "category": "architecture",
                "origin_policy": "ground_center",
                "position": [0.0, -30.0, 0.0],
                "rotation_euler_deg": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "clearance_radius_m": 0.0,
                "notes": "South entrance spawn medallion at (0, -44, 0) and ceremonial approach paving curb along the 4.0m promenade to the Central Plaza.",
            },
            {
                "placement_id": "APL_PL_EntranceGuideSign_001",
                "asset_id": "APL_EntranceGuideSign_001",
                "source_key": "A_plaza",
                "category": "prop",
                "origin_policy": "ground_center",
                "position": [2.85, -37.2, 0.0],
                "rotation_euler_deg": [0.0, 0.0, -25.0],
                "scale": [1.0, 1.0, 1.0],
                "clearance_radius_m": 0.65,
                "notes": "5-area directional signpost & welcome board just north of the M01 gate on the east apron (outside the 4.0m walkway and sightlines).",
            },
        ]
    )

    for cp in COMMON_PLACEMENT_SPECS:
        cat, clear_r = common_category_by_id.get(cp["common_asset_id"], ("prop", 0.50))
        placements.append(
            {
                "placement_id": cp["placement_id"],
                "asset_id": cp["common_asset_id"],
                "source_key": "common",
                "category": cat,
                "origin_policy": "ground_center",
                "position": list(cp["position"]),
                "rotation_euler_deg": list(cp["rotation_euler_deg"]),
                "scale": [1.0, 1.0, 1.0],
                "clearance_radius_m": clear_r,
                "notes": cp["role"],
            }
        )

    return {
        "schema_version": "1.0",
        "area_id": "A_plaza",
        "key": "A_plaza",
        "name": "Central Pumpkin Plaza & South Entrance",
        "theme": "Magical Halloween plaza hub with tiered fountain, Giant Jack-o'-Lantern landmark (M02), interactive gimmicks (G01-G04, I01/I03/I05), periodic plaza show rig, photo spot arch, and South Entrance Gate (M01)",
        "bounds": {
            "min": [-18.0, -47.0, 0.0],
            "max": [18.0, 18.0, 16.0],
        },
        "Anchor": {
            "anchor_id": "APL_GiantJackProxy_001",
            "position": [0.0, 0.0, 1.60],
            "dimensions_m": [6.202, 5.87, 6.0],
            "orientation_deg": 0.0,
            "role": "Central landmark Giant Jack-o'-Lantern with witch hat (M02 slot) mounted atop the G03 tiered fountain pedestal at (0, 0, 1.60), reaching z=7.60m and visible along all 4 cardinal sightlines.",
        },
        "Circulation": {
            "primary_path_id": "Route_Central_Ring_Road",
            "min_walk_width_m": 3.5,
            "entry_points": [
                [0.0, -44.0, 0.0],
                [0.0, -40.0, 0.0],
                [0.0, -14.5, 0.0],
                [0.0, 14.5, 0.0],
                [14.5, 0.0, 0.0],
                [-14.5, 0.0, 0.0],
            ],
            "loop_description": "4.0m-wide South Entrance approach from spawn (0, -44, 0) through the M01 gate (0, -40, 0) and South Bridge (0, -14.5, 0) into the 3.5m-wide Central Ring Road (R=10.75m..14.25m) and 3.0m-wide inner fountain promenade (R=4.8m..9.2m), branching to North (0, 14.5, 0), East (14.5, 0, 0), and West (-14.5, 0, 0).",
        },
        "Framing": {
            "left_edge": "West sequential lanterns (APL_SeqLantern_001/006/007/008), I01 Trick-or-Treat stand (-4.8, -6.2, 0), and M01 west gate pillar (-3.8, -40.0, 0)",
            "right_edge": "East sequential lanterns (APL_SeqLantern_002/003/004/005), I05 Fireworks switch (4.8, -6.2, 0), SE Photo Arch (11.2, -11.2, 0), and M01 east gate pillar (3.8, -40.0, 0)",
            "focal_target": "APL_Fountain_001 and APL_GiantJackProxy_001 at (0.0, 0.0, 1.60..7.60)",
            "view_cone_deg": 65.0,
        },
        "Story_Cluster": [
            {
                "cluster_id": "APL_Cluster_CentralFountainAndJack",
                "center": [0.0, 0.0, 0.0],
                "radius_m": 6.0,
                "intent": "Central magical fountain (G03) crowned by the Giant Jack-o'-Lantern (M02), surrounded by 6 dancing pumpkins (G01), 4 floating candies (G02), and the reachable I03 reaction pedestal at (0, -4.65, 0).",
                "asset_ids": [
                    "APL_Fountain_001",
                    "APL_GiantJackProxy_001",
                    "APL_JackInteractionPedestal_001",
                    "APL_DancingPumpkin_001",
                    "APL_DancingPumpkin_002",
                    "APL_DancingPumpkin_003",
                    "APL_DancingPumpkin_004",
                    "APL_DancingPumpkin_005",
                    "APL_DancingPumpkin_006",
                    "APL_FloatingCandy_001",
                    "APL_FloatingCandy_002",
                    "APL_FloatingCandy_003",
                    "APL_FloatingCandy_004",
                ],
            },
            {
                "cluster_id": "APL_Cluster_SouthPlazaInteractionsAndPhoto",
                "center": [3.5, -8.5, 0.0],
                "radius_m": 9.5,
                "intent": "Interactive south plaza apron combining the I01 Trick-or-Treat stand, I05 Fireworks launch switch, G04 sequential lantern ring, and the SE photo spot arch framing the central landmark.",
                "asset_ids": [
                    "APL_TrickOrTreatStand_001",
                    "APL_FireworksSwitch_001",
                    "APL_PhotoArch_001",
                    "APL_PeriodicShowRig_001",
                    "APL_SeqLantern_001",
                    "APL_SeqLantern_002",
                    "APL_SeqLantern_003",
                ],
            },
            {
                "cluster_id": "APL_Cluster_SouthEntranceThreshold",
                "center": [0.0, -40.0, 0.0],
                "radius_m": 6.5,
                "intent": "Grand South Entrance arrival threshold featuring the M01 wrought-iron & stone gate arch at (0, -40, 0), spawn medallion at (0, -44, 0), and 5-area directional guide sign at (2.85, -37.2, 0).",
                "asset_ids": [
                    "APL_EntranceGateProxy_001",
                    "APL_EntranceApproach_001",
                    "APL_EntranceGuideSign_001",
                    "CMN_StreetLamp_001",
                    "CMN_SmallPumpkin_001",
                ],
            },
        ],
        "Common_Placement": COMMON_PLACEMENT_SPECS,
        "Hero_or_Gimmick": {
            "asset_id": "APL_Fountain_001",
            "motion_roots": [
                "APL_Fountain_001_Water",
            ],
            "visual_roots": [
                "APL_Fountain_001_Basin",
                "APL_Fountain_001_Water",
            ],
            "attachment_points": [
                "APL_Fountain_001_WaterAttach",
                "APL_Fountain_001_LightAttach",
                "APL_Fountain_001_SoundAttach",
            ],
            "interaction_notes": "Central tiered stone fountain (G03) with separated static basin/pedestal and animated water veil mesh, supporting the M02 Giant Jack-o'-Lantern at z=1.60m and paired with the reachable I03 pedestal at (0, -4.65, 0), I01 Trick-or-Treat stand at (-4.8, -6.2, 0), I05 Fireworks switch at (4.8, -6.2, 0), G01 dancing pumpkins, G02 floating candies, G04 sequential lantern ring, and APL_PeriodicShowRig_001.",
        },
        "Exclusions": [
            {
                "zone_id": "APL_Excl_SouthSpawnCircle",
                "bounds": {
                    "min": [-3.5, -47.5, 0.0],
                    "max": [3.5, -40.5, 3.5],
                },
                "reason": "Keep South Entrance Gate spawn circle (0, -44, 0, R=3.5m) completely unobstructed above ground.",
            },
            {
                "zone_id": "APL_Excl_PlazaSouthSpawn",
                "bounds": {
                    "min": [-3.0, -15.75, 0.0],
                    "max": [3.0, -9.75, 3.5],
                },
                "reason": "Keep Central Plaza south ring arrival candidate (0, -12.75, 0, R=3.0m) unobstructed.",
            },
            {
                "zone_id": "APL_Excl_LOS_SouthToNorthCorridor",
                "bounds": {
                    "min": [-2.0, -44.0, 0.15],
                    "max": [2.0, -5.2, 3.8],
                },
                "reason": "Preserve LOS_SouthEntrance_To_CentralPlaza along the 4.0m South Promenade and through the 4.36m x 3.973m M01 gate opening.",
            },
            {
                "zone_id": "APL_Excl_LOS_NorthMansionCorridor",
                "bounds": {
                    "min": [-2.0, 5.2, 0.15],
                    "max": [2.0, 18.0, 4.5],
                },
                "reason": "Preserve LOS_CentralPlaza_To_NorthMansion along the 4.0m North axial walkway and bridge portal.",
            },
            {
                "zone_id": "APL_Excl_LOS_EastCandyCorridor",
                "bounds": {
                    "min": [5.2, -2.0, 0.15],
                    "max": [18.0, 2.0, 4.0],
                },
                "reason": "Preserve LOS_CentralPlaza_To_EastCandy along the 4.0m East axial walkway and bridge portal.",
            },
            {
                "zone_id": "APL_Excl_LOS_WestForestCorridor",
                "bounds": {
                    "min": [-18.0, -1.9, 0.15],
                    "max": [-5.2, 1.9, 4.0],
                },
                "reason": "Preserve LOS_CentralPlaza_To_WestForest along the 3.8m West axial walkway and bridge portal.",
            },
        ],
        "placements": placements,
    }
