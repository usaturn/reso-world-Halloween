"""Placement data of the E_forest key (pure Python, world coordinates in metres; Blender +X east, +Y north, +Z up).

The W01 frame (`layout/world_layout.json`): area E spans x -48..-20, y -20..20, ground z 0. The W01 main road
deck (`WLD_WestBridge_001`) runs along y = 0 (width 3.8) from the bridge to x = -42.25; the route ends at
(-33, 0, 0). Cliff guard walls stand at x = -47.5, y = +-19.5 and x = -20.4 (open at |y| < 2.4 and 14 < |y| < 19.5).
Side bridges land at (-22.5, +-15.5).
"""

from __future__ import annotations

KEY = "E_forest"
AREA_BOUNDS = {"min": (-48.0, -20.0, 0.0), "max": (-20.0, 20.0, 16.0)}

DECK_Z = 0.18  # boardwalk deck top
WALK_W = 2.2  # boardwalk clear width (side paths >= 2.0 m, Spec §4.1)
REST_DECK_Z = 0.20
LOOKOUT_DECK_Z = 0.75
WALK_CLEAR_Z = 2.8  # nothing may hang lower than this over a walkway or viewing spot

# M07 clock tower: W09 placement_hint (`assets/meshy/received.json`), front (+Y local) turned to the east.
CLOCK_TOWER = {"position": (-38.5, 0.0, 0.0), "rotation_z_deg": -90.0}

# ------------------------------------------------------------------ walkways
# Straight boardwalk segments. ``ramp`` names the ends that come down to the ground; ``openings`` are
# (side, from, to) stretches along the segment (metres from p0) where edge posts are left out for a junction.
WALKS = [
    {
        "id": "EFR_WalkNorth_001",
        "p0": (-24.0, 12.5),
        "p1": (-37.6, 12.5),
        "ramp": ("p0",),
        "openings": [("left", 5.8, 8.2)],
        "notes": "North boardwalk from the NW side-bridge landing to the lookout ramp; the pond bridge joins from the south at x = -31.",
    },
    {
        "id": "EFR_WalkWest_001",
        "p0": (-44.4, 6.0),
        "p1": (-44.4, -9.65),
        "ramp": (),
        "openings": [],
        "notes": "West boardwalk behind the clock tower, from the lookout's south ramp to the rest spot.",
    },
    {
        "id": "EFR_WalkSouth_001",
        "p0": (-40.0, -12.5),
        "p1": (-24.0, -12.5),
        "ramp": ("p1",),
        "openings": [("left", 10.8, 13.2)],
        "notes": "South boardwalk from the rest spot to the SW side-bridge landing; the south spur joins from the north at x = -28.",
    },
    {
        "id": "EFR_WalkSouthSpur_001",
        "p0": (-28.0, -1.95),
        "p1": (-28.0, -11.4),
        "ramp": ("p0",),
        "openings": [],
        "notes": "Spur from the main road down to the south boardwalk (closes the south loop).",
    },
    {
        "id": "EFR_WalkPondSpur_001",
        "p0": (-31.0, 1.95),
        "p1": (-31.0, 4.0),
        "ramp": ("p0",),
        "openings": [],
        "notes": "Spur from the main road to the pond bridge.",
    },
]

POND = {"center": (-32.0, 7.7), "semi_axes": (4.1, 2.45), "water_top": 0.07}
POND_BRIDGE = {"id": "EFR_PondBridge_001", "p0": (-31.0, 4.0), "p1": (-31.0, 11.4), "rise": 0.42, "width": WALK_W}

LOOKOUT = {
    "id": "EFR_Lookout_001",
    "center": (-44.4, 12.5),
    "size": (4.4, 4.6),
    "ramp_east": {"p0": (-37.6, 12.5), "p1": (-42.2, 12.5)},
    "ramp_south": {"p0": (-44.4, 10.2), "p1": (-44.4, 6.0)},
}

REST_SPOT = {"id": "EFR_RestSpot_001", "center": (-43.2, -12.6), "radius": 3.3}

# ------------------------------------------------------------------ hero trees with faces (G17)
FACE_TREES = [
    {"id": "EFR_FaceTree_001", "position": (-25.2, 6.8), "rotation_z_deg": -152.0,
     "notes": "Greets visitors arriving over the west bridge; looks south-south-east at the main road."},
    {"id": "EFR_FaceTree_002", "position": (-36.6, -8.0), "rotation_z_deg": -34.0,
     "notes": "Watches the tower forecourt and the south spur from the south-west."},
]

# ------------------------------------------------------------------ reusable trees, rocks, bushes
TREES = {
    "EFR_TreeOak": [(-26.5, 16.2, 20.0), (-36.0, 16.2, 140.0), (-28.0, -16.2, 75.0), (-34.6, -16.2, 210.0), (-23.8, -8.6, 300.0)],
    "EFR_TreePine": [(-45.0, 17.6, 0.0), (-31.0, 17.4, 40.0), (-31.5, -17.4, 95.0), (-37.8, -17.6, 160.0), (-22.7, -4.6, 250.0)],
    "EFR_TreeTwist": [(-39.0, 6.6, 30.0), (-32.4, -5.6, 200.0), (-24.5, -16.6, 120.0)],
}
ROCKS = [(-21.9, 9.6, 15.0), (-25.8, -3.4, 250.0), (-37.2, 9.6, 70.0)]
BUSHES = [(-21.6, -10.6, 130.0), (-21.6, 12.8, 200.0), (-41.0, -17.3, 280.0), (-25.6, -16.8, 30.0)]

# ------------------------------------------------------------------ mushrooms (G18)
# (type, x, y, yaw_deg, glow); glowing individuals get their own period/phase (Spec §11).
MUSHROOMS = [
    ("Tall", -36.8, 5.6, 0.0, True),
    ("Tall", -41.6, -6.4, 40.0, True),
    ("Tall", -25.8, 10.2, 80.0, True),
    ("Tall", -33.0, -9.6, 120.0, True),
    ("Tall", -41.0, 16.6, 160.0, True),
    ("Medium", -27.4, 3.0, 0.0, True),
    ("Medium", -34.2, 10.8, 50.0, True),
    ("Medium", -30.4, -9.8, 100.0, True),
    ("Medium", -46.3, 1.6, 150.0, False),
    ("Medium", -21.4, -6.0, 200.0, False),
    ("Medium", -38.2, -15.0, 250.0, False),
    ("Cluster", -21.6, 4.6, 0.0, True),
    ("Cluster", -33.6, 4.6, 45.0, True),
    ("Cluster", -44.4, 16.4, 90.0, False),
    ("Cluster", -24.2, -2.8, 135.0, True),
    ("Cluster", -35.6, -10.4, 180.0, False),
    ("Cluster", -46.9, -8.9, 225.0, True),
    ("Cluster", -29.0, 11.0, 270.0, False),
    ("Cluster", -33.2, -3.6, 315.0, True),
]
GIANT_MUSHROOM = {"id": "EFR_MushroomGiant_001", "position": (-43.2, -12.6, REST_DECK_Z), "yaw": 15.0}

# ------------------------------------------------------------------ bats (G19)
BAT_FLOCK = {"id": "EFR_BatFlock_001", "center": (-28.8, -6.5, 10.4), "count": 5, "radius_range": (1.1, 2.0),
             "flight_radius_m": 2.6, "flight_vertical_m": 0.8}

# ------------------------------------------------------------------ entrance framing
GATE_PILLARS = [
    {"id": "EFR_GatePillar_001", "position": (-21.5, 2.9), "rotation_z_deg": 180.0},
    {"id": "EFR_GatePillar_002", "position": (-21.5, -2.9), "rotation_z_deg": 0.0},
]

# ------------------------------------------------------------------ common parts (W01 key `common`)
COMMON = [
    # (instance_name, common_asset_id, (x, y, z), rz_deg, role)
    ("EFR_ForecourtLamp_001", "CMN_StreetLamp_001", (-33.9, 2.75, 0.0), -90.0, "Tower forecourt lamp, north of the stairs"),
    ("EFR_ForecourtLamp_002", "CMN_StreetLamp_001", (-33.9, -2.75, 0.0), 90.0, "Tower forecourt lamp, south of the stairs"),
    ("EFR_PathLantern_001", "CMN_Lantern_001", (-28.2, 13.95, 0.0), 0.0, "North boardwalk lantern"),
    ("EFR_PathLantern_002", "CMN_Lantern_001", (-35.4, 13.95, 0.0), 0.0, "North boardwalk lantern"),
    ("EFR_PathLantern_003", "CMN_Lantern_001", (-45.85, 2.0, 0.0), 0.0, "West boardwalk lantern"),
    ("EFR_PathLantern_004", "CMN_Lantern_001", (-45.85, -5.0, 0.0), 0.0, "West boardwalk lantern"),
    ("EFR_PathLantern_005", "CMN_Lantern_001", (-28.6, -13.95, 0.0), 0.0, "South boardwalk lantern"),
    ("EFR_PathLantern_006", "CMN_Lantern_001", (-35.8, -13.95, 0.0), 0.0, "South boardwalk lantern"),
    ("EFR_PathLantern_007", "CMN_Lantern_001", (-26.55, -6.0, 0.0), 0.0, "South spur lantern"),
    ("EFR_RestBench_001", "CMN_Bench_001", None, 160.0, "Rest spot bench (faces outward)"),
    ("EFR_RestBench_002", "CMN_Bench_001", None, 220.0, "Rest spot bench (faces outward)"),
    ("EFR_RestBench_003", "CMN_Bench_001", None, 280.0, "Rest spot bench (faces outward)"),
    ("EFR_LookoutBench_001", "CMN_Bench_001", (-45.9, 12.5, LOOKOUT_DECK_Z), 90.0, "Lookout bench facing west over the cliff"),
    ("EFR_Pumpkin_001", "CMN_SmallPumpkin_001", (-32.9, 2.4, 0.0), 30.0, "Forecourt pumpkin (face turned to the road)"),
    ("EFR_Pumpkin_002", "CMN_SmallPumpkin_001", (-32.9, -2.4, 0.0), 150.0, "Forecourt pumpkin (face turned to the road)"),
    ("EFR_Pumpkin_003", "CMN_SmallPumpkin_001", (-41.2, -10.8, REST_DECK_Z), 200.0, "Rest spot pumpkin"),
]
REST_BENCH_RADIUS = 2.25


def rest_bench_position(angle_deg: float) -> tuple[float, float, float]:
    """Bench on the rest-spot deck at ``angle_deg`` (from +X) around the centre."""
    import math

    cx, cy = REST_SPOT["center"]
    a = math.radians(angle_deg)
    return (cx + REST_BENCH_RADIUS * math.cos(a), cy + REST_BENCH_RADIUS * math.sin(a), REST_DECK_Z)


def facing_rz(angle_deg: float) -> float:
    """Z rotation that turns local +Y towards the direction ``angle_deg`` (from +X)."""
    return angle_deg - 90.0
