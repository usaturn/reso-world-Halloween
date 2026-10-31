"""Pure-Python layout and gimmick specification data for Area D (`D_amusement`)."""

from __future__ import annotations

import math
from typing import Any

KEY = "D_amusement"
AREA_ID = "D_amusement"

# Fixed world coordinates of Area D major assets
PLAZA_ORIGIN: tuple[float, float, float] = (0.0, -33.0, 0.0)
CAROUSEL_ORIGIN: tuple[float, float, float] = (-10.5, -32.0, 0.0)
TRAIN_TRACK_ORIGIN: tuple[float, float, float] = (12.0, -31.5, 0.0)
GHOST_TRAIN_ORIGIN: tuple[float, float, float] = (7.5, -31.5, 0.0)
PUMPKIN_CUPS_ORIGIN: tuple[float, float, float] = (11.5, -42.5, 0.0)
TICKET_BOOTH_ORIGIN: tuple[float, float, float] = (4.7, -31.5, 0.0)
CARNIVAL_STALL_ORIGIN: tuple[float, float, float] = (-8.8, -42.2, 0.0)

# G15 Closed-Loop Track geometry constants (relative to TRAIN_TRACK_ORIGIN = (12.0, -31.5, 0.0))
TRACK_RADIUS_M: float = 4.5
TRACK_STRAIGHT_HALF_Y_M: float = 2.0
TRACK_RAIL_GAUGE_M: float = 0.76
TRACK_RAIL_TOP_Z_M: float = 0.14


def compute_track_loop_waypoints(num_arc_samples: int = 8) -> list[dict[str, Any]]:
    """Compute ordered closed-loop waypoints (local to `DAM_TrainTrack_001` and world) for G15.

    The track is a flat stadium oval at rail-top height `z = 0.14m` with:
      - West straight: x_local = -4.5m, y_local from -2.0m to +2.0m (direction +Y, yaw = 0 deg)
      - North semicircle: center (0.0, +2.0), radius 4.5m, angle pi -> 0 (clockwise)
      - East straight: x_local = +4.5m, y_local from +2.0m to -2.0m (direction -Y, yaw = 180 deg)
      - South semicircle: center (0.0, -2.0), radius 4.5m, angle 0 -> -pi (clockwise)
    """
    r = TRACK_RADIUS_M
    hy = TRACK_STRAIGHT_HALF_Y_M
    rz = TRACK_RAIL_TOP_Z_M
    ox, oy, oz = TRAIN_TRACK_ORIGIN

    raw_pts: list[tuple[float, float, float, float]] = []

    # 1. West straight (+Y direction, tangent = (0, 1))
    for frac in (0.0, 0.5):
        yl = -hy + frac * (2.0 * hy)
        raw_pts.append((-r, yl, 0.0, 1.0))

    # 2. North semicircle (clockwise from angle=pi to angle=0 around (0, +hy))
    for i in range(num_arc_samples):
        theta = math.pi * (1.0 - i / num_arc_samples)
        xl = r * math.cos(theta)
        yl = hy + r * math.sin(theta)
        # Clockwise tangent for d(theta) < 0 is (sin(theta), -cos(theta))
        tx = math.sin(theta)
        ty = -math.cos(theta)
        raw_pts.append((xl, yl, tx, ty))

    # 3. East straight (-Y direction, tangent = (0, -1))
    for frac in (0.0, 0.5):
        yl = hy - frac * (2.0 * hy)
        raw_pts.append((r, yl, 0.0, -1.0))

    # 4. South semicircle (clockwise from angle=0 to angle=-pi around (0, -hy))
    for i in range(num_arc_samples):
        theta = -math.pi * (i / num_arc_samples)
        xl = r * math.cos(theta)
        yl = -hy + r * math.sin(theta)
        tx = math.sin(theta)
        ty = -math.cos(theta)
        raw_pts.append((xl, yl, tx, ty))

    waypoints: list[dict[str, Any]] = []
    cum_s = 0.0
    n = len(raw_pts)
    for idx, (xl, yl, tx, ty) in enumerate(raw_pts):
        if idx > 0:
            px, py, _, _ = raw_pts[idx - 1]
            cum_s += math.hypot(xl - px, yl - py)
        # In Blender (+Y forward), yaw around +Z for tangent (tx, ty) is atan2(-tx, ty)
        yaw_deg = math.degrees(math.atan2(-tx, ty))
        waypoints.append(
            {
                "index": idx,
                "distance_m": round(cum_s, 4),
                "position_local": [round(xl, 4), round(yl, 4), round(rz, 4)],
                "position_world": [round(ox + xl, 4), round(oy + yl, 4), round(oz + rz, 4)],
                "tangent_xy": [round(tx, 4), round(ty, 4)],
                "yaw_z_deg": round(yaw_deg, 2),
            }
        )
    return waypoints


def build_d_amusement_common_placements() -> list[dict[str, Any]]:
    """Return `Common_Placement` entries for `D_amusement` using shared assets from `common.blend`."""
    return [
        # Streetlamps framing the West Carousel Plaza & East Ghost Train / Pumpkin Cups Plaza
        {
            "instance_name": "DAM_StreetLamp_001",
            "common_asset_id": "CMN_StreetLamp_001",
            "position": [-4.6, -26.5, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_StreetLamp_002",
            "common_asset_id": "CMN_StreetLamp_001",
            "position": [-4.6, -37.8, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_StreetLamp_003",
            "common_asset_id": "CMN_StreetLamp_001",
            "position": [6.2, -25.2, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 180.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_StreetLamp_004",
            "common_asset_id": "CMN_StreetLamp_001",
            "position": [6.8, -40.5, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 90.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_StreetLamp_005",
            "common_asset_id": "CMN_StreetLamp_001",
            "position": [-16.2, -28.0, 0.0],
            "rotation_euler_deg": [0.0, 0.0, -45.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_StreetLamp_006",
            "common_asset_id": "CMN_StreetLamp_001",
            "position": [18.2, -31.5, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 180.0],
            "scale": [1.0, 1.0, 1.0],
        },
        # Festive Garland Flags welcoming visitors into the West & East carnival courts
        {
            "instance_name": "DAM_GarlandFlag_001",
            "common_asset_id": "CMN_GarlandFlag_001",
            "position": [-4.8, -32.0, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 90.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_GarlandFlag_002",
            "common_asset_id": "CMN_GarlandFlag_001",
            "position": [-10.5, -25.5, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_GarlandFlag_003",
            "common_asset_id": "CMN_GarlandFlag_001",
            "position": [11.5, -38.4, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
        },
        # Low decorative iron fences protecting the outer side of the Ghost Train loop
        {
            "instance_name": "DAM_Fence_001",
            "common_asset_id": "CMN_Fence_001",
            "position": [18.2, -28.8, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 90.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_Fence_002",
            "common_asset_id": "CMN_Fence_001",
            "position": [18.2, -34.2, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 90.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_Fence_003",
            "common_asset_id": "CMN_Fence_001",
            "position": [-16.8, -32.0, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 90.0],
            "scale": [1.0, 1.0, 1.0],
        },
        # Spectator benches facing the Carousel and Pumpkin Cups
        {
            "instance_name": "DAM_Bench_001",
            "common_asset_id": "CMN_Bench_001",
            "position": [-4.8, -29.2, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 90.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_Bench_002",
            "common_asset_id": "CMN_Bench_001",
            "position": [-4.8, -34.8, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 90.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_Bench_003",
            "common_asset_id": "CMN_Bench_001",
            "position": [7.4, -42.5, 0.0],
            "rotation_euler_deg": [0.0, 0.0, -90.0],
            "scale": [1.0, 1.0, 1.0],
        },
        # Ground lanterns and small jack-o'-lantern clusters near booths & steps
        {
            "instance_name": "DAM_Lantern_001",
            "common_asset_id": "CMN_Lantern_001",
            "position": [-5.2, -30.6, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_Lantern_002",
            "common_asset_id": "CMN_Lantern_001",
            "position": [-5.2, -33.4, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_SmallPumpkin_001",
            "common_asset_id": "CMN_SmallPumpkin_001",
            "position": [-6.6, -40.8, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 25.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_SmallPumpkin_002",
            "common_asset_id": "CMN_SmallPumpkin_001",
            "position": [3.5, -29.5, 0.0],
            "rotation_euler_deg": [0.0, 0.0, -40.0],
            "scale": [1.0, 1.0, 1.0],
        },
        {
            "instance_name": "DAM_SmallPumpkin_003",
            "common_asset_id": "CMN_SmallPumpkin_001",
            "position": [8.2, -45.2, 0.0],
            "rotation_euler_deg": [0.0, 0.0, 15.0],
            "scale": [1.0, 1.0, 1.0],
        },
    ]


def build_d_amusement_area_layout_dict() -> dict[str, Any]:
    """Build `layout/areas/D_amusement.json` conforming to `tools/check_data.py` and `docs/conventions.md`."""
    waypoints = compute_track_loop_waypoints(num_arc_samples=8)
    total_loop_length_m = round(2.0 * (2.0 * TRACK_STRAIGHT_HALF_Y_M) + 2.0 * math.pi * TRACK_RADIUS_M, 4)

    return {
        "schema_version": "1.0",
        "area_id": AREA_ID,
        "key": KEY,
        "name": "Area D — South Trick Amusement & Entrance",
        "theme": "Festive Halloween pumpkin amusement park with rotating Pumpkin Carousel (G13/G14), Ghost Train flat loop ride (G15), Spinning Pumpkin Cups (G16), and carnival stalls framing the South Entrance Promenade",
        "bounds": {
            "min": [-22.0, -48.0, 0.0],
            "max": [22.0, -20.0, 18.0],
        },
        "Anchor": {
            "anchor_id": "DAM_Carousel_001",
            "position": list(CAROUSEL_ORIGIN),
            "dimensions_m": [10.4, 10.2, 9.901],
            "orientation_deg": 0.0,
            "role": "Primary Area D landmark (~10m diameter Pumpkin Carousel on the West court, framing the South Promenade while preserving the central sightline to Area A)",
        },
        "Circulation": {
            "primary_path_id": "Route_South_Entrance_Approach",
            "min_walk_width_m": 4.0,
            "entry_points": [
                [0.0, -44.0, 0.0],
                [0.0, -20.0, 0.0],
                [16.0, -22.0, 0.0],
                [-16.0, -22.0, 0.0],
            ],
            "loop_description": "4.0m-wide straight South Promenade along x=0 from South Spawn (y=-44m) to South Causeway Bridge (y=-20m), flanked by West Carousel/Stall court (x in [-18.5, -2.5]) and East Ghost Train/Pumpkin Cups court (x in [2.5, 19.5]), connecting to SE/SW outer loop bridges at (±16, -22, 0).",
        },
        "Framing": {
            "left_edge": "DAM_Carousel_001 (-10.5, -32.0, 0.0) & DAM_CarnivalStall_001 (-8.8, -42.2, 0.0) on West carnival court",
            "right_edge": "DAM_TicketBooth_001 (4.7, -31.5, 0.0), DAM_GhostTrain_001 (7.5, -31.5, 0.0) & DAM_PumpkinCups_001 (11.5, -42.5, 0.0) on East carnival court",
            "focal_target": "North along Route_South_Entrance_Approach (x=0.0m) toward Central Pumpkin Tower (A_plaza)",
            "view_cone_deg": 65.0,
        },
        "Story_Cluster": [
            {
                "cluster_id": "DAM_Cluster_WestCarouselCourt",
                "center": [-10.0, -34.0, 0.0],
                "radius_m": 10.5,
                "intent": "Grand Pumpkin Carousel (G13 turntable, G14 4-phase oscillating seats, M05 CenterCasing & Canopy replacement targets) paired with the Pumpkin Ring-Toss Carnival Stall and spectator benches.",
                "asset_ids": [
                    "DAM_Carousel_001",
                    "DAM_CarnivalStall_001",
                    "DAM_AmusementPlaza_001",
                ],
            },
            {
                "cluster_id": "DAM_Cluster_EastTrainStation",
                "center": [10.5, -31.5, 0.0],
                "radius_m": 9.5,
                "intent": "Flat closed-loop Ghost Train ride (G15) with M06 lead engine shell, separated wheel axles, coupled passenger car (~6.0m total consist length), and the adjacent Ticket & Treat Booth.",
                "asset_ids": [
                    "DAM_TrainTrack_001",
                    "DAM_GhostTrain_001",
                    "DAM_TicketBooth_001",
                ],
            },
            {
                "cluster_id": "DAM_Cluster_SouthEastPumpkinCups",
                "center": [11.5, -42.5, 0.0],
                "radius_m": 5.5,
                "intent": "Spinning Pumpkin Cups attraction (G16) with main turntable, central witch-hat pumpkin totem, and 3 independently rotating jack-o'-lantern teacups.",
                "asset_ids": [
                    "DAM_PumpkinCups_001",
                    "DAM_AmusementPlaza_001",
                ],
            },
        ],
        "Common_Placement": build_d_amusement_common_placements(),
        "Hero_or_Gimmick": [
            {
                "asset_id": "DAM_Carousel_001",
                "motion_roots": [
                    "DAM_Carousel_001_TurnRoot",
                    "DAM_Carousel_001_SeatRoot_001",
                    "DAM_Carousel_001_SeatRoot_002",
                    "DAM_Carousel_001_SeatRoot_003",
                    "DAM_Carousel_001_SeatRoot_004",
                ],
                "visual_roots": [
                    "DAM_Carousel_001_Base",
                    "DAM_Carousel_001_Floor",
                    "DAM_Carousel_001_Poles",
                    "DAM_Carousel_001_M05_CenterCasing",
                    "DAM_Carousel_001_M05_Canopy",
                    "DAM_Carousel_001_Seat_001",
                    "DAM_Carousel_001_Seat_002",
                    "DAM_Carousel_001_Seat_003",
                    "DAM_Carousel_001_Seat_004",
                ],
                "attachment_points": [
                    "DAM_Carousel_001_Att_M05_CenterCasing",
                    "DAM_Carousel_001_Att_M05_Canopy",
                ],
                "interaction_notes": "G13: DAM_Carousel_001_TurnRoot at local [0, 0, 0.36] (world [-10.5, -32.0, 0.36]) rotates continuously around +Z (0..360 deg, recommended 18 deg/s). G14: DAM_Carousel_001_SeatRoot_001..004 at r=3.35m, z=1.05m relative to TurnRoot oscillate vertically along +Z by ±0.28m with phase offsets [0, 90, 180, 270] deg. M05 replacement: DAM_Carousel_001_M05_CenterCasing at TurnRoot+[0,0,0.19] (world z=0.55m) and DAM_Carousel_001_M05_Canopy at TurnRoot+[0,0,3.154] (world z=3.514m, +2.964m above CenterCasing origin).",
            },
            {
                "asset_id": "DAM_GhostTrain_001",
                "motion_roots": [
                    "DAM_GhostTrain_001_EngineRoot",
                    "DAM_GhostTrain_001_CarRoot_001",
                ],
                "visual_roots": [
                    "DAM_GhostTrain_001_M06_EngineShell",
                    "DAM_GhostTrain_001_EngineWheelFront",
                    "DAM_GhostTrain_001_EngineWheelRear",
                    "DAM_GhostTrain_001_CarBody_001",
                    "DAM_GhostTrain_001_CarWheelFront_001",
                    "DAM_GhostTrain_001_CarWheelRear_001",
                ],
                "attachment_points": [
                    "DAM_GhostTrain_001_Att_M06_Engine",
                    "DAM_GhostTrain_001_Att_CouplerRear",
                    "DAM_GhostTrain_001_Att_Headlamp",
                ],
                "interaction_notes": "G15: Train consist (total length 6.00m) follows the flat closed loop on DAM_TrainTrack_001 at constant rail-top elevation z=0.14m. EngineRoot is at rest at world [7.5, -30.5, 0.14] (+Y forward); CarRoot_001 trails by arc distance 2.75m (rest world [7.5, -33.25, 0.14]). Wheels rotate around local +X axle (radius 0.21m engine / 0.20m car). M06 replaces DAM_GhostTrain_001_M06_EngineShell at EngineRoot origin [0,0,0].",
            },
            {
                "asset_id": "DAM_PumpkinCups_001",
                "motion_roots": [
                    "DAM_PumpkinCups_001_TurnRoot",
                    "DAM_PumpkinCups_001_CupRoot_001",
                    "DAM_PumpkinCups_001_CupRoot_002",
                    "DAM_PumpkinCups_001_CupRoot_003",
                ],
                "visual_roots": [
                    "DAM_PumpkinCups_001_Base",
                    "DAM_PumpkinCups_001_Turntable",
                    "DAM_PumpkinCups_001_Cup_001",
                    "DAM_PumpkinCups_001_Cup_002",
                    "DAM_PumpkinCups_001_Cup_003",
                ],
                "attachment_points": [
                    "DAM_PumpkinCups_001_Att_CenterTop",
                ],
                "interaction_notes": "G16: Main turntable DAM_PumpkinCups_001_TurnRoot at local [0, 0, 0.22] (world [11.5, -42.5, 0.22]) rotates around +Z (0..360 deg, recommended 24 deg/s), while each teacup DAM_PumpkinCups_001_CupRoot_001..003 at r=1.72m counter-rotates around its own local +Z axis (0..360 deg, recommended -60 deg/s).",
            },
        ],
        "gimmick_specs": {
            "G13_carousel_rotation": {
                "gimmick_id": "G13",
                "asset_id": "DAM_Carousel_001",
                "motion_root": "DAM_Carousel_001_TurnRoot",
                "pivot_local": [0.0, 0.0, 0.36],
                "pivot_world": [-10.5, -32.0, 0.36],
                "axis_local": "+Z",
                "motion_type": "continuous_rotation",
                "range_deg": [0.0, 360.0],
                "recommended_speed_deg_per_sec": 18.0,
                "rest_euler_deg": [0.0, 0.0, 0.0],
            },
            "G14_carousel_seats_vertical": {
                "gimmick_id": "G14",
                "asset_id": "DAM_Carousel_001",
                "parent_motion_root": "DAM_Carousel_001_TurnRoot",
                "axis_local": "+Z",
                "motion_type": "sinusoidal_translation",
                "amplitude_m": 0.28,
                "range_offset_m": [-0.28, 0.28],
                "recommended_frequency_hz": 0.45,
                "clearance_note": "Max seat+rider top stays below +2.60m above rotating floor (< +3.00m M05_Canopy ornament limit).",
                "seats": [
                    {
                        "motion_root": "DAM_Carousel_001_SeatRoot_001",
                        "visual_root": "DAM_Carousel_001_Seat_001",
                        "rest_local_to_turn_root": [3.35, 0.0, 1.05],
                        "rest_rotation_euler_deg": [0.0, 0.0, 0.0],
                        "phase_offset_deg": 0.0,
                    },
                    {
                        "motion_root": "DAM_Carousel_001_SeatRoot_002",
                        "visual_root": "DAM_Carousel_001_Seat_002",
                        "rest_local_to_turn_root": [0.0, 3.35, 1.05],
                        "rest_rotation_euler_deg": [0.0, 0.0, 90.0],
                        "phase_offset_deg": 90.0,
                    },
                    {
                        "motion_root": "DAM_Carousel_001_SeatRoot_003",
                        "visual_root": "DAM_Carousel_001_Seat_003",
                        "rest_local_to_turn_root": [-3.35, 0.0, 1.05],
                        "rest_rotation_euler_deg": [0.0, 0.0, 180.0],
                        "phase_offset_deg": 180.0,
                    },
                    {
                        "motion_root": "DAM_Carousel_001_SeatRoot_004",
                        "visual_root": "DAM_Carousel_001_Seat_004",
                        "rest_local_to_turn_root": [0.0, -3.35, 1.05],
                        "rest_rotation_euler_deg": [0.0, 0.0, -90.0],
                        "phase_offset_deg": 270.0,
                    },
                ],
            },
            "G15_ghost_train_loop": {
                "gimmick_id": "G15",
                "track_asset_id": "DAM_TrainTrack_001",
                "train_asset_id": "DAM_GhostTrain_001",
                "loop_guide_part": "DAM_TrainTrack_001_LoopGuide",
                "track_center_world": list(TRAIN_TRACK_ORIGIN),
                "rail_top_z_world_m": TRACK_RAIL_TOP_Z_M,
                "loop_shape": "stadium_oval_clockwise",
                "curve_radius_m": TRACK_RADIUS_M,
                "straight_length_m": 2.0 * TRACK_STRAIGHT_HALF_Y_M,
                "total_loop_length_m": total_loop_length_m,
                "recommended_speed_m_per_sec": 2.2,
                "consist_total_length_m": 6.0,
                "engine_to_car_arc_offset_m": 2.75,
                "forward_axis_local": "+Y",
                "up_axis_local": "+Z",
                "wheel_spin_axis_local": "+X",
                "waypoints": waypoints,
            },
            "G16_pumpkin_cups_spin": {
                "gimmick_id": "G16",
                "asset_id": "DAM_PumpkinCups_001",
                "main_turntable_root": "DAM_PumpkinCups_001_TurnRoot",
                "main_pivot_local": [0.0, 0.0, 0.22],
                "main_pivot_world": [11.5, -42.5, 0.22],
                "main_axis_local": "+Z",
                "main_range_deg": [0.0, 360.0],
                "main_recommended_speed_deg_per_sec": 24.0,
                "cups": [
                    {
                        "motion_root": "DAM_PumpkinCups_001_CupRoot_001",
                        "visual_root": "DAM_PumpkinCups_001_Cup_001",
                        "pivot_local_to_turn_root": [
                            round(1.72 * math.cos(math.radians(30.0)), 4),
                            round(1.72 * math.sin(math.radians(30.0)), 4),
                            0.10,
                        ],
                        "axis_local": "+Z",
                        "range_deg": [0.0, 360.0],
                        "recommended_speed_deg_per_sec": -60.0,
                    },
                    {
                        "motion_root": "DAM_PumpkinCups_001_CupRoot_002",
                        "visual_root": "DAM_PumpkinCups_001_Cup_002",
                        "pivot_local_to_turn_root": [
                            round(1.72 * math.cos(math.radians(150.0)), 4),
                            round(1.72 * math.sin(math.radians(150.0)), 4),
                            0.10,
                        ],
                        "axis_local": "+Z",
                        "range_deg": [0.0, 360.0],
                        "recommended_speed_deg_per_sec": 65.0,
                    },
                    {
                        "motion_root": "DAM_PumpkinCups_001_CupRoot_003",
                        "visual_root": "DAM_PumpkinCups_001_Cup_003",
                        "pivot_local_to_turn_root": [
                            round(1.72 * math.cos(math.radians(270.0)), 4),
                            round(1.72 * math.sin(math.radians(270.0)), 4),
                            0.10,
                        ],
                        "axis_local": "+Z",
                        "range_deg": [0.0, 360.0],
                        "recommended_speed_deg_per_sec": -55.0,
                    },
                ],
            },
        },
        "Exclusions": [
            {
                "zone_id": "DAM_Excl_SouthSpawnClearance",
                "bounds": {
                    "min": [-4.5, -47.0, 0.0],
                    "max": [4.5, -40.0, 6.0],
                },
                "reason": "Keep South Entrance Spawn Terrace (y=-44m) and M01 Gate threshold (y=-40m) completely unobstructed.",
            },
            {
                "zone_id": "DAM_Excl_CentralPromenadeLOS",
                "bounds": {
                    "min": [-3.5, -44.0, 0.0],
                    "max": [3.5, -20.0, 12.0],
                },
                "reason": "Preserve 4.0m main walkway and sightline corridor (LOS_SouthEntrance_To_CentralPlaza) along x=0.",
            },
            {
                "zone_id": "DAM_Excl_EastSideBridgePortal",
                "bounds": {
                    "min": [13.5, -24.0, 0.0],
                    "max": [18.5, -20.0, 4.0],
                },
                "reason": "Keep SE diagonal bridge portal at (16, -22, 0) clear for inter-area loop circulation.",
            },
            {
                "zone_id": "DAM_Excl_WestSideBridgePortal",
                "bounds": {
                    "min": [-18.5, -24.0, 0.0],
                    "max": [-13.5, -20.0, 4.0],
                },
                "reason": "Keep SW diagonal bridge portal at (-16, -22, 0) clear for inter-area loop circulation.",
            },
        ],
        "placements": [
            {
                "placement_id": "DAM_Place_AmusementPlaza_001",
                "asset_id": "DAM_AmusementPlaza_001",
                "source_key": KEY,
                "category": "architecture",
                "position": list(PLAZA_ORIGIN),
                "rotation_euler_deg": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "origin_policy": "ground_center",
                "clearance_radius_m": 0.0,
            },
            {
                "placement_id": "DAM_Place_Carousel_001",
                "asset_id": "DAM_Carousel_001",
                "source_key": KEY,
                "category": "gimmick",
                "position": list(CAROUSEL_ORIGIN),
                "rotation_euler_deg": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "origin_policy": "ground_center",
                "clearance_radius_m": 5.0,
            },
            {
                "placement_id": "DAM_Place_TrainTrack_001",
                "asset_id": "DAM_TrainTrack_001",
                "source_key": KEY,
                "category": "architecture",
                "position": list(TRAIN_TRACK_ORIGIN),
                "rotation_euler_deg": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "origin_policy": "ground_center",
                "clearance_radius_m": 1.5,
            },
            {
                "placement_id": "DAM_Place_GhostTrain_001",
                "asset_id": "DAM_GhostTrain_001",
                "source_key": KEY,
                "category": "gimmick",
                "position": list(GHOST_TRAIN_ORIGIN),
                "rotation_euler_deg": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "origin_policy": "ground_center",
                "clearance_radius_m": 1.5,
            },
            {
                "placement_id": "DAM_Place_PumpkinCups_001",
                "asset_id": "DAM_PumpkinCups_001",
                "source_key": KEY,
                "category": "gimmick",
                "position": list(PUMPKIN_CUPS_ORIGIN),
                "rotation_euler_deg": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "origin_policy": "ground_center",
                "clearance_radius_m": 3.2,
            },
            {
                "placement_id": "DAM_Place_TicketBooth_001",
                "asset_id": "DAM_TicketBooth_001",
                "source_key": KEY,
                "category": "architecture",
                "position": list(TICKET_BOOTH_ORIGIN),
                "rotation_euler_deg": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "origin_policy": "ground_center",
                "clearance_radius_m": 1.4,
            },
            {
                "placement_id": "DAM_Place_CarnivalStall_001",
                "asset_id": "DAM_CarnivalStall_001",
                "source_key": KEY,
                "category": "architecture",
                "position": list(CARNIVAL_STALL_ORIGIN),
                "rotation_euler_deg": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "origin_policy": "ground_center",
                "clearance_radius_m": 1.8,
            },
        ],
    }
