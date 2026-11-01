"""Asset builders for Area D (`D_amusement`) rides, plaza, and carnival stalls."""

from __future__ import annotations

import math

import bmesh  # type: ignore
import bpy  # type: ignore

from modeling.D_amusement.layout_data import (
    CARNIVAL_STALL_ORIGIN,
    CAROUSEL_ORIGIN,
    CAROUSEL_POLE_COLLAR_Z_M,
    CAROUSEL_POLE_TOP_Z_M,
    GHOST_TRAIN_HEADLAMP_LOCAL,
    GHOST_TRAIN_ORIGIN,
    PLAZA_ORIGIN,
    PUMPKIN_CUPS_ORIGIN,
    TICKET_BOOTH_ORIGIN,
    TRACK_RADIUS_M,
    TRACK_RAIL_GAUGE_M,
    TRACK_STRAIGHT_HALF_Y_M,
    TRAIN_TRACK_ORIGIN,
    compute_track_loop_waypoints,
)
from modeling.D_amusement.mesh_helpers import (
    add_annulus_z,
    add_box,
    add_cylinder_x,
    add_cylinder_y,
    add_frustum_z,
    add_oriented_beam,
    create_attachment_socket,
    create_empty_node,
    finalize_mesh_obj,
)


def build_amusement_plaza(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Build `DAM_AmusementPlaza_001`: South Promenade, West/East carnival courts, and curbs."""
    root = create_empty_node("DAM_AmusementPlaza_001", collection, location=PLAZA_ORIGIN, display_size=0.8)
    mat_list = [
        mats["plaza_stone"],      # 0
        mats["carnival_purple"],  # 1
        mats["carnival_gold"],    # 2
        mats["pumpkin_orange"],   # 3
        mats["amber_glow"],       # 4
    ]

    bm_prom = bmesh.new()
    uv_prom = bm_prom.loops.layers.uv.new("UVMap")
    add_box(bm_prom, uv_prom, (-2.15, -7.4, 0.0), (2.15, 13.0, 0.04), material_index=0)
    add_box(bm_prom, uv_prom, (-2.45, -7.4, 0.0), (-2.16, 13.0, 0.09), material_index=2)
    add_box(bm_prom, uv_prom, (2.16, -7.4, 0.0), (2.45, 13.0, 0.09), material_index=2)
    for idx in range(6):
        yc = -6.0 + idx * 3.5
        add_box(bm_prom, uv_prom, (-1.6, yc - 0.7, 0.041), (1.6, yc + 0.7, 0.055), material_index=1 if idx % 2 == 0 else 3)
        add_box(bm_prom, uv_prom, (-2.35, yc - 0.14, 0.091), (-2.20, yc + 0.14, 0.13), material_index=4)
        add_box(bm_prom, uv_prom, (2.20, yc - 0.14, 0.091), (2.35, yc + 0.14, 0.13), material_index=4)
    add_frustum_z(bm_prom, uv_prom, (0.0, -9.90), 0.0, 0.04, 2.45, 2.40, segments=20, material_index=2, top_material_index=1)
    finalize_mesh_obj("DAM_AmusementPlaza_001_Promenade", bm_prom, collection, mat_list, parent=root)

    bm_west = bmesh.new()
    uv_west = bm_west.loops.layers.uv.new("UVMap")
    add_frustum_z(bm_west, uv_west, (-10.5, 1.0), 0.0, 0.035, 6.35, 6.25, segments=24, material_index=2, top_material_index=2)
    add_frustum_z(bm_west, uv_west, (-10.5, 1.0), 0.036, 0.055, 6.00, 5.95, segments=24, material_index=0, top_material_index=1)
    add_box(bm_west, uv_west, (-4.10, -0.8, 0.0), (-2.46, 2.8, 0.04), material_index=0)
    add_box(bm_west, uv_west, (-12.5, -11.5, 0.0), (-5.2, -6.5, 0.04), material_index=0)
    finalize_mesh_obj("DAM_AmusementPlaza_001_WestCourt", bm_west, collection, mat_list, parent=root)

    bm_east = bmesh.new()
    uv_east = bm_east.loops.layers.uv.new("UVMap")
    add_box(bm_east, uv_east, (2.46, -5.0, 0.0), (18.2, 9.2, 0.04), material_index=0)
    add_box(bm_east, uv_east, (3.2, -1.2, 0.041), (6.4, 4.2, 0.08), material_index=1)
    add_frustum_z(bm_east, uv_east, (11.5, -9.5), 0.0, 0.05, 4.25, 4.15, segments=20, material_index=2, top_material_index=1)
    add_box(bm_east, uv_east, (2.46, -11.2, 0.0), (7.15, -7.8, 0.04), material_index=0)
    finalize_mesh_obj("DAM_AmusementPlaza_001_EastCourt", bm_east, collection, mat_list, parent=root)
    return root


def build_carousel(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Build `DAM_Carousel_001` with G13 TurnRoot, G14 4 SeatRoots, and M05 CenterCasing/Canopy."""
    root = create_empty_node("DAM_Carousel_001", collection, location=CAROUSEL_ORIGIN, display_size=0.8)
    mat_list = [
        mats["pumpkin_orange"],    # 0
        mats["pumpkin_dark_rib"],  # 1
        mats["pumpkin_stem"],      # 2
        mats["carnival_purple"],   # 3
        mats["carnival_gold"],     # 4
        mats["carnival_cream"],    # 5
        mats["warm_wood"],         # 6
        mats["iron_steel"],        # 7
        mats["amber_glow"],        # 8
    ]

    bm_base = bmesh.new()
    uv_base = bm_base.loops.layers.uv.new("UVMap")
    add_frustum_z(bm_base, uv_base, (0.0, 0.0), 0.0, 0.18, 5.20, 5.10, segments=24, material_index=3, top_material_index=4)
    add_frustum_z(bm_base, uv_base, (0.0, 0.0), 0.18, 0.36, 4.92, 4.84, segments=24, material_index=6, top_material_index=3)
    add_box(bm_base, uv_base, (4.70, -1.25, 0.0), (5.55, 1.25, 0.18), material_index=4)
    finalize_mesh_obj("DAM_Carousel_001_Base", bm_base, collection, mat_list, parent=root)

    turn_root = create_empty_node("DAM_Carousel_001_TurnRoot", collection, location=(0.0, 0.0, 0.36), parent=root, display_size=0.6)

    bm_floor = bmesh.new()
    uv_floor = bm_floor.loops.layers.uv.new("UVMap")
    add_frustum_z(bm_floor, uv_floor, (0.0, 0.0), 0.0, 0.19, 4.68, 4.62, segments=24, material_index=6, top_material_index=5)
    add_annulus_z(bm_floor, uv_floor, 4.48, 4.68, 0.15, 0.22, segments=24, material_index=4)
    finalize_mesh_obj("DAM_Carousel_001_Floor", bm_floor, collection, mat_list, parent=turn_root)

    bm_poles = bmesh.new()
    uv_poles = bm_poles.loops.layers.uv.new("UVMap")
    for idx in range(8):
        ang = idx * (math.pi / 4.0)
        r_pole = 3.35 if idx % 2 == 0 else 4.15
        px, py = r_pole * math.cos(ang), r_pole * math.sin(ang)
        # W09R-D: the shaft reaches into the M05 canopy, the collar sits below its fringe (layout_data.py)
        add_frustum_z(bm_poles, uv_poles, (px, py), 0.19, CAROUSEL_POLE_TOP_Z_M[idx], 0.055, 0.055, segments=10, material_index=4)
        add_frustum_z(bm_poles, uv_poles, (px, py), 0.19, 0.36, 0.13, 0.09, segments=10, material_index=3)
        add_frustum_z(bm_poles, uv_poles, (px, py), *CAROUSEL_POLE_COLLAR_Z_M, 0.09, 0.14, segments=10, material_index=4)
    finalize_mesh_obj("DAM_Carousel_001_Poles", bm_poles, collection, mat_list, parent=turn_root)

    create_attachment_socket("DAM_Carousel_001_Att_M05_CenterCasing", collection, mats["carnival_gold"], location=(0.0, 0.0, 0.19), parent=turn_root)
    bm_casing = bmesh.new()
    uv_casing = bm_casing.loops.layers.uv.new("UVMap")
    add_frustum_z(bm_casing, uv_casing, (0.0, 0.0), 0.0, 0.48, 0.91, 0.84, segments=16, material_index=3, top_material_index=4)
    add_frustum_z(bm_casing, uv_casing, (0.0, 0.0), 0.48, 2.52, 0.76, 0.72, segments=16, material_index=5, top_material_index=4)
    for k in range(8):
        ak = k * (math.pi / 4.0)
        add_frustum_z(bm_casing, uv_casing, (0.76 * math.cos(ak), 0.76 * math.sin(ak)), 0.52, 2.48, 0.07, 0.07, segments=8, material_index=4 if k % 2 == 0 else 8)
    add_frustum_z(bm_casing, uv_casing, (0.0, 0.0), 2.52, 2.964, 0.84, 0.93, segments=16, material_index=4, top_material_index=3)
    add_frustum_z(bm_casing, uv_casing, (0.0, 0.0), 2.964, 3.400, 0.62, 0.56, segments=12, material_index=7)
    finalize_mesh_obj("DAM_Carousel_001_M05_CenterCasing", bm_casing, collection, mat_list, location=(0.0, 0.0, 0.19), parent=turn_root)

    create_attachment_socket("DAM_Carousel_001_Att_M05_Canopy", collection, mats["carnival_gold"], location=(0.0, 0.0, 3.154), parent=turn_root)
    bm_canopy = bmesh.new()
    uv_canopy = bm_canopy.loops.layers.uv.new("UVMap")
    add_annulus_z(bm_canopy, uv_canopy, 3.95, 4.657, 0.0, 0.52, segments=24, material_index=3, ry_scale=1.02)
    add_frustum_z(bm_canopy, uv_canopy, (0.0, 0.0), 0.52, 1.35, 4.657, 4.42, segments=24, material_index=0, top_material_index=4, ry_scale=1.02)
    add_frustum_z(bm_canopy, uv_canopy, (0.0, 0.0), 1.35, 3.10, 4.42, 3.55, segments=24, material_index=0, top_material_index=1, ry_scale=1.02)
    add_frustum_z(bm_canopy, uv_canopy, (0.0, 0.0), 3.10, 4.55, 3.55, 1.45, segments=24, material_index=1, top_material_index=0, ry_scale=1.02)
    add_frustum_z(bm_canopy, uv_canopy, (0.0, 0.0), 4.55, 5.45, 1.45, 0.42, segments=16, material_index=2)
    add_frustum_z(bm_canopy, uv_canopy, (0.0, 0.0), 5.45, 6.387, 0.42, 0.06, segments=12, material_index=2, top_material_index=4)
    for k in range(12):
        ak = k * (math.pi / 6.0)
        add_frustum_z(bm_canopy, uv_canopy, (4.52 * math.cos(ak), 4.60 * math.sin(ak)), 0.05, 0.35, 0.14, 0.10, segments=8, material_index=8 if k % 2 == 0 else 4)
    finalize_mesh_obj("DAM_Carousel_001_M05_Canopy", bm_canopy, collection, mat_list, location=(0.0, 0.0, 3.154), parent=turn_root)

    seat_specs = [
        ("001", (3.35, 0.0, 1.05), (0.0, 0.0, 0.0)),
        ("002", (0.0, 3.35, 1.05), (0.0, 0.0, 90.0)),
        ("003", (-3.35, 0.0, 1.05), (0.0, 0.0, 180.0)),
        ("004", (0.0, -3.35, 1.05), (0.0, 0.0, -90.0)),
    ]
    for suffix, loc, rot_deg in seat_specs:
        seat_root = create_empty_node(
            f"DAM_Carousel_001_SeatRoot_{suffix}",
            collection,
            location=loc,
            rotation_euler_deg=rot_deg,
            parent=turn_root,
            display_size=0.4,
        )
        bm_seat = bmesh.new()
        uv_seat = bm_seat.loops.layers.uv.new("UVMap")
        add_frustum_z(bm_seat, uv_seat, (0.0, 0.0), -0.38, 0.05, 0.56, 0.72, segments=14, material_index=0, top_material_index=1, ry_scale=1.18)
        add_frustum_z(bm_seat, uv_seat, (0.0, 0.0), 0.05, 0.32, 0.72, 0.62, segments=14, material_index=1, top_material_index=5, ry_scale=1.18)
        add_box(bm_seat, uv_seat, (-0.38, -0.35, 0.18), (0.38, 0.25, 0.36), material_index=3)
        add_box(bm_seat, uv_seat, (-0.36, -0.58, 0.32), (0.36, -0.34, 0.74), material_index=3)
        add_frustum_z(bm_seat, uv_seat, (0.0, 0.52), 0.18, 0.58, 0.22, 0.16, segments=10, material_index=0, top_material_index=2)
        add_box(bm_seat, uv_seat, (-0.22, 0.30, 0.52), (0.22, 0.42, 0.58), material_index=4)
        finalize_mesh_obj(f"DAM_Carousel_001_Seat_{suffix}", bm_seat, collection, mat_list, parent=seat_root)

    return root


def build_train_track(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Build `DAM_TrainTrack_001`: flat closed-loop stadium track with Sleepers, Rails, and LoopGuide."""
    root = create_empty_node("DAM_TrainTrack_001", collection, location=TRAIN_TRACK_ORIGIN, display_size=0.8)
    mat_list = [
        mats["warm_wood"],      # 0
        mats["iron_steel"],     # 1
        mats["carnival_gold"],  # 2
        mats["amber_glow"],     # 3
    ]
    waypoints = compute_track_loop_waypoints(num_arc_samples=12)
    n = len(waypoints)
    half_gauge = 0.5 * TRACK_RAIL_GAUGE_M

    bm_sleepers = bmesh.new()
    uv_sleepers = bm_sleepers.loops.layers.uv.new("UVMap")
    for wp in waypoints:
        xl, yl, _ = wp["position_local"]
        tx, ty = wp["tangent_xy"]
        rx, ry = ty, -tx
        p0 = (xl - rx * 0.62, yl - ry * 0.62, 0.0)
        p1 = (xl + rx * 0.62, yl + ry * 0.62, 0.0)
        add_oriented_beam(bm_sleepers, uv_sleepers, p0, p1, width=0.22, thickness=0.07, material_index=0)
    finalize_mesh_obj("DAM_TrainTrack_001_Sleepers", bm_sleepers, collection, mat_list, parent=root)

    bm_rails = bmesh.new()
    uv_rails = bm_rails.loops.layers.uv.new("UVMap")
    bm_guide = bmesh.new()
    uv_guide = bm_guide.loops.layers.uv.new("UVMap")

    for i in range(n):
        wp0 = waypoints[i]
        wp1 = waypoints[(i + 1) % n]
        x0, y0, _ = wp0["position_local"]
        x1, y1, _ = wp1["position_local"]
        tx0, ty0 = wp0["tangent_xy"]
        tx1, ty1 = wp1["tangent_xy"]
        rx0, ry0 = ty0, -tx0
        rx1, ry1 = ty1, -tx1

        for sign in (-1.0, 1.0):
            p0 = (x0 + sign * half_gauge * rx0, y0 + sign * half_gauge * ry0, 0.065)
            p1 = (x1 + sign * half_gauge * rx1, y1 + sign * half_gauge * ry1, 0.065)
            add_oriented_beam(bm_rails, uv_rails, p0, p1, width=0.075, thickness=0.075, material_index=1)

        g0 = (x0, y0, 0.07)
        g1 = (x1, y1, 0.07)
        add_oriented_beam(bm_guide, uv_guide, g0, g1, width=0.10, thickness=0.04, material_index=2 if i % 2 == 0 else 3)

    finalize_mesh_obj("DAM_TrainTrack_001_Rails", bm_rails, collection, mat_list, parent=root)
    finalize_mesh_obj("DAM_TrainTrack_001_LoopGuide", bm_guide, collection, mat_list, parent=root)
    return root


def build_ghost_train(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Build `DAM_GhostTrain_001` with M06 lead engine shell, separated wheel axles, and coupled Car_001."""
    root = create_empty_node("DAM_GhostTrain_001", collection, location=GHOST_TRAIN_ORIGIN, display_size=0.8)
    mat_list = [
        mats["ghost_white"],       # 0
        mats["witch_hat_black"],   # 1
        mats["pumpkin_orange"],    # 2
        mats["carnival_purple"],   # 3
        mats["carnival_gold"],     # 4
        mats["iron_steel"],        # 5
        mats["amber_glow"],        # 6
        mats["warm_wood"],         # 7
    ]

    # EngineRoot sits on the West straight rail top at local (0.0, 1.0, 0.14) -> world (7.5, -30.5, 0.14), +Y forward
    engine_root = create_empty_node("DAM_GhostTrain_001_EngineRoot", collection, location=(0.0, 1.0, 0.14), parent=root, display_size=0.5)
    create_attachment_socket("DAM_GhostTrain_001_Att_M06_Engine", collection, mats["carnival_gold"], location=(0.0, 0.0, 0.0), parent=engine_root)
    create_attachment_socket("DAM_GhostTrain_001_Att_CouplerRear", collection, mats["carnival_gold"], location=(0.0, -1.125, 0.394), parent=engine_root)
    create_attachment_socket("DAM_GhostTrain_001_Att_Headlamp", collection, mats["carnival_gold"], location=GHOST_TRAIN_HEADLAMP_LOCAL, parent=engine_root)

    # M06_EngineShell: matches W09 M06 bounds [-0.605, -1.125, 0.0] .. [0.606, 1.875, 1.905] (1.211 x 3.000 x 1.905 m)
    bm_eng = bmesh.new()
    uv_eng = bm_eng.loops.layers.uv.new("UVMap")
    add_box(bm_eng, uv_eng, (-0.58, -1.125, 0.18), (0.58, 1.55, 0.44), material_index=5)
    add_box(bm_eng, uv_eng, (-0.605, 1.45, 0.06), (0.606, 1.875, 0.36), material_index=4)
    add_box(bm_eng, uv_eng, (-0.56, -1.06, 0.44), (0.56, -0.05, 1.52), material_index=3)
    add_box(bm_eng, uv_eng, (-0.605, -1.125, 1.48), (0.606, 0.05, 1.62), material_index=1)
    add_cylinder_y(bm_eng, uv_eng, (0.0, 0.88), -0.05, 1.38, 0.48, 0.45, segments=16, material_index=0, front_cap_material_index=6)
    add_frustum_z(bm_eng, uv_eng, (0.0, 0.88), 1.25, 1.54, 0.56, 0.24, segments=12, material_index=1, top_material_index=4)
    add_frustum_z(bm_eng, uv_eng, (0.0, 0.88), 1.54, 1.905, 0.24, 0.04, segments=10, material_index=1)
    add_cylinder_y(bm_eng, uv_eng, (0.0, 1.498), 1.10, 1.28, 0.14, 0.16, segments=12, material_index=4, front_cap_material_index=6)
    add_box(bm_eng, uv_eng, (-0.12, -1.24, 0.32), (0.12, -1.08, 0.45), material_index=5)
    finalize_mesh_obj("DAM_GhostTrain_001_M06_EngineShell", bm_eng, collection, mat_list, parent=engine_root)

    # Separated Front & Rear Wheel Axles under EngineRoot (wheel arch tops at y=±0.414, z=0.431/0.434 -> axle center z=0.21m, radius=0.21m)
    for w_name, wy in (("DAM_GhostTrain_001_EngineWheelFront", 0.414), ("DAM_GhostTrain_001_EngineWheelRear", -0.414)):
        bm_w = bmesh.new()
        uv_w = bm_w.loops.layers.uv.new("UVMap")
        add_cylinder_x(bm_w, uv_w, (0.0, 0.0), -0.44, 0.44, 0.045, segments=10, material_index=5)
        add_cylinder_x(bm_w, uv_w, (0.0, 0.0), -0.45, -0.35, 0.21, segments=16, material_index=5, cap_material_index=4)
        add_cylinder_x(bm_w, uv_w, (0.0, 0.0), 0.35, 0.45, 0.21, segments=16, material_index=5, cap_material_index=4)
        finalize_mesh_obj(w_name, bm_w, collection, mat_list, location=(0.0, wy, 0.21), parent=engine_root)

    # CarRoot_001 trails EngineRoot by 2.75m along the West straight -> local (0.0, -1.75, 0.14), total consist length = 1.875 - (-4.125) = 6.00m
    car_root = create_empty_node("DAM_GhostTrain_001_CarRoot_001", collection, location=(0.0, -1.75, 0.14), parent=root, display_size=0.5)
    bm_car = bmesh.new()
    uv_car = bm_car.loops.layers.uv.new("UVMap")
    add_box(bm_car, uv_car, (-0.56, -1.375, 0.16), (0.56, 1.25, 0.40), material_index=5)
    add_box(bm_car, uv_car, (-0.10, 1.20, 0.30), (0.10, 1.52, 0.42), material_index=5)
    add_frustum_z(bm_car, uv_car, (0.0, -0.06), 0.38, 1.18, 0.62, 0.68, segments=16, material_index=2, top_material_index=7, ry_scale=1.95)
    add_box(bm_car, uv_car, (-0.42, -0.82, 0.55), (0.42, -0.32, 0.92), material_index=3)
    add_box(bm_car, uv_car, (-0.42, 0.18, 0.55), (0.42, 0.68, 0.92), material_index=3)
    add_box(bm_car, uv_car, (-0.54, -1.10, 1.12), (0.54, 0.98, 1.24), material_index=4)
    finalize_mesh_obj("DAM_GhostTrain_001_CarBody_001", bm_car, collection, mat_list, parent=car_root)

    for w_name, wy in (("DAM_GhostTrain_001_CarWheelFront_001", 0.68), ("DAM_GhostTrain_001_CarWheelRear_001", -0.78)):
        bm_cw = bmesh.new()
        uv_cw = bm_cw.loops.layers.uv.new("UVMap")
        add_cylinder_x(bm_cw, uv_cw, (0.0, 0.0), -0.44, 0.44, 0.04, segments=10, material_index=5)
        add_cylinder_x(bm_cw, uv_cw, (0.0, 0.0), -0.44, -0.35, 0.20, segments=16, material_index=5, cap_material_index=4)
        add_cylinder_x(bm_cw, uv_cw, (0.0, 0.0), 0.35, 0.44, 0.20, segments=16, material_index=5, cap_material_index=4)
        finalize_mesh_obj(w_name, bm_cw, collection, mat_list, location=(0.0, wy, 0.20), parent=car_root)

    return root


def build_pumpkin_cups(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Build `DAM_PumpkinCups_001` (G16): main turntable + 3 independently spinning pumpkin teacups."""
    root = create_empty_node("DAM_PumpkinCups_001", collection, location=PUMPKIN_CUPS_ORIGIN, display_size=0.7)
    mat_list = [
        mats["pumpkin_orange"],    # 0
        mats["pumpkin_dark_rib"],  # 1
        mats["pumpkin_stem"],      # 2
        mats["carnival_purple"],   # 3
        mats["carnival_gold"],     # 4
        mats["witch_hat_black"],   # 5
        mats["amber_glow"],        # 6
    ]

    bm_base = bmesh.new()
    uv_base = bm_base.loops.layers.uv.new("UVMap")
    add_frustum_z(bm_base, uv_base, (0.0, 0.0), 0.0, 0.22, 3.25, 3.15, segments=24, material_index=3, top_material_index=4)
    finalize_mesh_obj("DAM_PumpkinCups_001_Base", bm_base, collection, mat_list, parent=root)

    turn_root = create_empty_node("DAM_PumpkinCups_001_TurnRoot", collection, location=(0.0, 0.0, 0.22), parent=root, display_size=0.55)
    bm_tt = bmesh.new()
    uv_tt = bm_tt.loops.layers.uv.new("UVMap")
    add_frustum_z(bm_tt, uv_tt, (0.0, 0.0), 0.0, 0.10, 2.95, 2.90, segments=24, material_index=4, top_material_index=3)
    add_frustum_z(bm_tt, uv_tt, (0.0, 0.0), 0.10, 1.15, 0.45, 0.52, segments=14, material_index=0, top_material_index=1)
    add_frustum_z(bm_tt, uv_tt, (0.0, 0.0), 1.15, 1.38, 0.72, 0.30, segments=14, material_index=5, top_material_index=4)
    add_frustum_z(bm_tt, uv_tt, (0.0, 0.0), 1.38, 2.15, 0.30, 0.05, segments=12, material_index=5, top_material_index=6)
    finalize_mesh_obj("DAM_PumpkinCups_001_Turntable", bm_tt, collection, mat_list, parent=turn_root)
    create_attachment_socket("DAM_PumpkinCups_001_Att_CenterTop", collection, mats["carnival_gold"], location=(0.0, 0.0, 2.15), parent=turn_root)

    for idx, deg in enumerate((30.0, 150.0, 270.0), start=1):
        rad = math.radians(deg)
        cx = round(1.72 * math.cos(rad), 4)
        cy = round(1.72 * math.sin(rad), 4)
        cup_root = create_empty_node(
            f"DAM_PumpkinCups_001_CupRoot_{idx:03d}",
            collection,
            location=(cx, cy, 0.10),
            parent=turn_root,
            display_size=0.4,
        )
        bm_cup = bmesh.new()
        uv_cup = bm_cup.loops.layers.uv.new("UVMap")
        add_frustum_z(bm_cup, uv_cup, (0.0, 0.0), 0.0, 0.10, 0.92, 0.85, segments=16, material_index=4)
        add_frustum_z(bm_cup, uv_cup, (0.0, 0.0), 0.10, 0.65, 0.68, 0.92, segments=16, material_index=0, top_material_index=1)
        add_annulus_z(bm_cup, uv_cup, 0.68, 0.92, 0.65, 0.98, segments=16, material_index=0)
        add_frustum_z(bm_cup, uv_cup, (0.0, 0.0), 0.12, 0.82, 0.10, 0.08, segments=10, material_index=4)
        add_frustum_z(bm_cup, uv_cup, (0.0, 0.0), 0.82, 0.90, 0.34, 0.34, segments=14, material_index=5, top_material_index=4)
        add_box(bm_cup, uv_cup, (0.85, -0.10, 0.32), (1.12, 0.10, 0.82), material_index=2)
        finalize_mesh_obj(f"DAM_PumpkinCups_001_Cup_{idx:03d}", bm_cup, collection, mat_list, parent=cup_root)

    return root


def build_ticket_booth(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Build `DAM_TicketBooth_001`: whimsical pumpkin-roofed ticket kiosk next to the Ghost Train station."""
    root = create_empty_node("DAM_TicketBooth_001", collection, location=TICKET_BOOTH_ORIGIN, display_size=0.6)
    mat_list = [
        mats["warm_wood"],        # 0
        mats["carnival_purple"],  # 1
        mats["carnival_gold"],    # 2
        mats["pumpkin_orange"],   # 3
        mats["witch_hat_black"],  # 4
        mats["amber_glow"],       # 5
    ]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    add_frustum_z(bm, uv, (0.0, 0.0), 0.0, 0.16, 1.25, 1.20, segments=8, material_index=0, top_material_index=2)
    add_frustum_z(bm, uv, (0.0, 0.0), 0.16, 1.15, 1.05, 1.05, segments=8, material_index=1, top_material_index=2)
    add_frustum_z(bm, uv, (0.0, 0.0), 1.15, 2.25, 0.96, 0.98, segments=8, material_index=5, top_material_index=1)
    add_box(bm, uv, (-1.15, -0.58, 1.05), (-0.88, 0.58, 1.22), material_index=2)
    add_frustum_z(bm, uv, (0.0, 0.0), 2.25, 2.95, 1.38, 0.52, segments=12, material_index=3, top_material_index=4)
    add_frustum_z(bm, uv, (0.0, 0.0), 2.95, 3.65, 0.52, 0.06, segments=10, material_index=4, top_material_index=2)
    finalize_mesh_obj("DAM_TicketBooth_001_Body", bm, collection, mat_list, parent=root)
    create_attachment_socket("DAM_TicketBooth_001_Att_Sign", collection, mats["carnival_gold"], location=(-1.10, 0.0, 2.40), parent=root)
    create_attachment_socket("DAM_TicketBooth_001_Att_Lantern", collection, mats["carnival_gold"], location=(-1.18, 0.65, 2.15), parent=root)
    return root


def build_carnival_stall(
    collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Build `DAM_CarnivalStall_001`: festive pumpkin ring-toss & candy carnival stall."""
    root = create_empty_node("DAM_CarnivalStall_001", collection, location=CARNIVAL_STALL_ORIGIN, display_size=0.6)
    mat_list = [
        mats["warm_wood"],        # 0
        mats["carnival_purple"],  # 1
        mats["carnival_gold"],    # 2
        mats["pumpkin_orange"],   # 3
        mats["carnival_cream"],   # 4
        mats["amber_glow"],       # 5
    ]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    add_box(bm, uv, (-1.75, -1.15, 0.0), (1.75, 1.15, 0.14), material_index=0)
    add_box(bm, uv, (-1.65, 0.65, 0.14), (1.65, 1.05, 1.05), material_index=1)
    add_box(bm, uv, (-1.72, 0.58, 1.05), (1.72, 1.12, 1.16), material_index=2)
    add_box(bm, uv, (-1.65, -1.05, 0.14), (1.65, -0.82, 2.25), material_index=0)
    for sx in (-1.55, 1.55):
        for sy in (-0.95, 0.95):
            add_box(bm, uv, (sx - 0.08, sy - 0.08, 0.14), (sx + 0.08, sy + 0.08, 2.35), material_index=2)
    add_box(bm, uv, (-1.88, -1.25, 2.30), (1.88, 1.32, 2.68), material_index=3)
    add_box(bm, uv, (-1.45, -0.95, 2.68), (1.45, 0.95, 3.15), material_index=1)
    for px in (-1.0, -0.35, 0.35, 1.0):
        add_frustum_z(bm, uv, (px, 0.85), 1.16, 1.48, 0.20, 0.15, segments=10, material_index=3, top_material_index=5)
    finalize_mesh_obj("DAM_CarnivalStall_001_Body", bm, collection, mat_list, parent=root)
    create_attachment_socket("DAM_CarnivalStall_001_Att_Sign", collection, mats["carnival_gold"], location=(0.0, 1.32, 2.75), parent=root)
    create_attachment_socket("DAM_CarnivalStall_001_Att_Lantern", collection, mats["carnival_gold"], location=(1.75, 1.15, 2.20), parent=root)
    return root
