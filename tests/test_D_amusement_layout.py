"""S-criteria spatial and gimmick safety tests for Area D (`D_amusement`, W05 / Issue #7).

Why these tests exist (create-reso-world AGENTS.md, test criterion S):
- Schema validation (`tools/check_data.py`) only checks field types and ID formats. It does not catch
  silent spatial collisions where an attraction or common prop intrudes into W01's South Entrance
  Spawn Terrace, blocks the 4.0m South Promenade (`Route_South_Entrance_Approach`), blocks the SE/SW
  bridge portals (`Conn_D_East_Side`, `Conn_D_West_Side`), obstructs `LOS_SouthEntrance_To_CentralPlaza`,
  or spills outside Area D's floating island bounds.
- Nor does schema validation catch silent gimmick parameter bugs that would cause runtime visual
  clipping in P3: G14 carousel seats colliding with M05's canopy ornaments (+3.00m above rotating floor),
  or G15's closed-loop track waypoints breaking continuity or rail-top elevation (`z = 0.14m`).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from modeling.D_amusement.layout_data import (
    build_d_amusement_area_layout_dict,
    compute_track_loop_waypoints,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_json(rel_path: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / rel_path).read_text(encoding="utf-8"))


def _circle_overlaps_aabb_xy(cx: float, cy: float, radius: float, box_min: list[float], box_max: list[float]) -> bool:
    """Return True if a horizontal circle (cx, cy, radius) overlaps an XY axis-aligned bounding box."""
    closest_x = max(float(box_min[0]), min(cx, float(box_max[0])))
    closest_y = max(float(box_min[1]), min(cy, float(box_max[1])))
    dx = cx - closest_x
    dy = cy - closest_y
    return (dx * dx + dy * dy) < (radius * radius - 1e-6)


def test_d_amusement_placements_preserve_w01_promenade_spawn_portals_and_los() -> None:
    """Verify Area D placements stay inside Area D bounds and keep W01 spawn, promenade, portals, and LOS clear.

    Also verifies a mutated placement (moving Carousel onto x=0 promenade) is rejected by the same check.
    """
    world = _load_json("layout/world_layout.json")
    area_d_world = next(a for a in world["areas"] if a["area_id"] == "D_amusement")
    w_bounds = area_d_world["bounds"]

    area_layout = build_d_amusement_area_layout_dict()
    assert area_layout["bounds"] == w_bounds

    # Derive keep-out corridors directly from W01's world_layout.json
    spawn_pos = world["spawn"]["position"]
    spawn_r = float(world["spawn"]["clearance_radius_m"])
    spawn_box_min = [spawn_pos[0] - spawn_r, spawn_pos[1] - spawn_r, 0.0]
    spawn_box_max = [spawn_pos[0] + spawn_r, spawn_pos[1] + spawn_r, 6.0]

    # Route_South_Entrance_Approach inside Area D (y from -44 to -20 along x=0, width 4.0m)
    promenade_min = [-2.0, -44.0, 0.0]
    promenade_max = [2.0, -20.0, 6.0]

    # LOS_SouthEntrance_To_CentralPlaza (corridor width 5.0m -> x in [-2.5, +2.5])
    los = next(item for item in world["line_of_sight"] if item["los_id"] == "LOS_SouthEntrance_To_CentralPlaza")
    los_hw = 0.5 * float(los["corridor_width_m"])
    los_min = [-los_hw, -44.0, 0.0]
    los_max = [los_hw, -20.0, 12.0]

    portal_boxes = []
    for conn in area_d_world["connection_points"]:
        cx, cy, _ = conn["position"]
        hw = 0.5 * float(conn["width_m"])
        portal_boxes.append((conn["id"], [cx - hw, cy - hw, 0.0], [cx + hw, cy + hw, 4.0]))

    def check_candidates(placements: list[dict[str, Any]], common_items: list[dict[str, Any]]) -> list[str]:
        violations: list[str] = []
        for pl in placements:
            pid = pl["placement_id"]
            px, py, pz = (float(v) for v in pl["position"])
            rad = float(pl["clearance_radius_m"])
            if not (w_bounds["min"][0] <= px - rad and px + rad <= w_bounds["max"][0]):
                violations.append(f"{pid} X footprint [{px - rad}, {px + rad}] leaves Area D bounds")
            if not (w_bounds["min"][1] <= py - rad and py + rad <= w_bounds["max"][1]):
                violations.append(f"{pid} Y footprint [{py - rad}, {py + rad}] leaves Area D bounds")
            if rad > 0.0:
                if _circle_overlaps_aabb_xy(px, py, rad, spawn_box_min, spawn_box_max):
                    violations.append(f"{pid} intrudes into South Spawn clearance")
                if _circle_overlaps_aabb_xy(px, py, rad, promenade_min, promenade_max):
                    violations.append(f"{pid} blocks Route_South_Entrance_Approach")
                if _circle_overlaps_aabb_xy(px, py, rad, los_min, los_max):
                    violations.append(f"{pid} blocks LOS_SouthEntrance_To_CentralPlaza")
                for cid, pmin, pmax in portal_boxes:
                    if _circle_overlaps_aabb_xy(px, py, rad, pmin, pmax):
                        violations.append(f"{pid} blocks connection portal {cid}")

        for cp in common_items:
            iname = cp["instance_name"]
            cx, cy, _ = (float(v) for v in cp["position"])
            if not (w_bounds["min"][0] <= cx <= w_bounds["max"][0] and w_bounds["min"][1] <= cy <= w_bounds["max"][1]):
                violations.append(f"{iname} outside Area D bounds")
            if _circle_overlaps_aabb_xy(cx, cy, 0.45, promenade_min, promenade_max):
                violations.append(f"{iname} intrudes into Route_South_Entrance_Approach")
            if _circle_overlaps_aabb_xy(cx, cy, 0.45, spawn_box_min, spawn_box_max):
                violations.append(f"{iname} intrudes into South Spawn clearance")
            for cid, pmin, pmax in portal_boxes:
                if _circle_overlaps_aabb_xy(cx, cy, 0.45, pmin, pmax):
                    violations.append(f"{iname} blocks connection portal {cid}")
        return violations

    assert check_candidates(area_layout["placements"], area_layout["Common_Placement"]) == []

    # Guard against a false-positive check: moving Carousel onto x=0 must trigger violations
    bad_placements = [dict(area_layout["placements"][1], position=[0.0, -32.0, 0.0])]
    bad_errors = check_candidates(bad_placements, [])
    assert any("Route_South_Entrance_Approach" in e for e in bad_errors)
    assert any("LOS_SouthEntrance_To_CentralPlaza" in e for e in bad_errors)


def test_g14_carousel_seats_and_g15_closed_loop_track_invariants() -> None:
    """Verify G14 seat oscillation stays below M05 canopy ornament clearance (+3.00m) and G15 loop is closed and flat."""
    area_layout = build_d_amusement_area_layout_dict()
    gimmicks = area_layout["gimmick_specs"]

    g14 = gimmicks["G14_carousel_seats_vertical"]
    amp = float(g14["amplitude_m"])
    assert 0.10 <= amp <= 0.45
    phases = [float(s["phase_offset_deg"]) for s in g14["seats"]]
    assert sorted(phases) == [0.0, 90.0, 180.0, 270.0]

    # Floor top is at z=0.19m in TurnRoot space; M05_Canopy starts at z=3.154m in TurnRoot space (+2.964m above floor).
    # Highest seat point at +amp must remain well below z=3.154m in TurnRoot space.
    for seat in g14["seats"]:
        rest_z = float(seat["rest_local_to_turn_root"][2])
        seat_top_at_peak = rest_z + amp + 0.74  # seat backrest top is +0.74m above SeatRoot
        assert seat_top_at_peak < 2.85, f"{seat['motion_root']} peak {seat_top_at_peak}m risks hitting M05_Canopy"

    g15 = gimmicks["G15_ghost_train_loop"]
    waypoints = compute_track_loop_waypoints(num_arc_samples=8)
    assert len(waypoints) >= 16
    rail_z = float(g15["rail_top_z_world_m"])
    for idx, wp in enumerate(waypoints):
        assert math.isclose(wp["position_local"][2], rail_z, abs_tol=1e-6)
        assert math.isclose(wp["position_world"][2], rail_z, abs_tol=1e-6)
        tx, ty = wp["tangent_xy"]
        assert math.isclose(math.hypot(tx, ty), 1.0, abs_tol=1e-3)
        nxt = waypoints[(idx + 1) % len(waypoints)]
        step_dist = math.hypot(
            nxt["position_local"][0] - wp["position_local"][0],
            nxt["position_local"][1] - wp["position_local"][1],
        )
        assert 0.5 <= step_dist <= 3.0, f"Track loop discontinuity between {idx} and {(idx + 1) % len(waypoints)}"
