"""S-criteria invariant tests for W01 world layout, route connectivity, geometric slopes, and area key mapping.

Why these tests exist (AGENTS.md S-criteria):
- `tools/check_data.py` validates individual field types and ranges (e.g. `0 <= max_slope_deg <= 30`),
  but does not verify:
  1. Graph reachability: every area can reach `A_plaza` via defined `routes` and return.
  2. Geometric waypoint slope: the actual 3D slope between consecutive route `waypoints` is <= 30 deg
     and has no unbridged vertical step to the connected area elevations.
  3. Spawn containment: `spawn.position` lies inside its declared `spawn.area_id` bounds at walkable elevation.
  4. Area key mapping consistency: both Issue #1 keys (`A_plaza`, `B_mansion`, `C_candy`, `D_amusement`, `E_forest`)
     and `check_data.py` schema keys (`A_plaza`, `B_alley`, `C_park`, `D_mansion`, `E_forest`) resolve bijectively
     to the 5 areas so W02-W07 builders never select the wrong area.
"""

from __future__ import annotations

import json
import math
from collections import deque
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORLD_LAYOUT_PATH = PROJECT_ROOT / "layout" / "world_layout.json"


def _load_world_layout() -> dict:
    return json.loads(WORLD_LAYOUT_PATH.read_text(encoding="utf-8"))


def test_all_areas_can_reach_central_plaza_via_routes() -> None:
    """Prevent silent disconnection where an area has valid syntax but no traversable route back to A_plaza."""
    data = _load_world_layout()
    area_ids = {area["area_id"] for area in data["areas"]}
    assert "A_plaza" in area_ids
    assert len(area_ids) == 5

    adj: dict[str, set[str]] = {aid: set() for aid in area_ids}
    for route in data["routes"]:
        u = route["from_area"]
        v = route["to_area"]
        if u in adj and v in adj:
            adj[u].add(v)
            adj[v].add(u)

    # Every non-central area must have a direct route to A_plaza (Central Ring Road / Radial Bridges)
    for aid in area_ids - {"A_plaza"}:
        assert "A_plaza" in adj[aid], f"Area {aid} has no direct route connecting to A_plaza"

    # Full graph BFS reachability from A_plaza
    visited = {"A_plaza"}
    queue = deque(["A_plaza"])
    while queue:
        curr = queue.popleft()
        for nxt in adj[curr]:
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)

    assert visited == area_ids, f"Unreachable areas from A_plaza: {area_ids - visited}"


def test_route_waypoint_geometry_matches_slope_and_elevation_limits() -> None:
    """Prevent silent unwalkable cliffs where declared max_slope_deg is <= 30 but actual 3D waypoints exceed 30 deg."""
    data = _load_world_layout()
    area_elevations = {area["area_id"]: float(area["ground_elevation_m"]) for area in data["areas"]}

    for route in data["routes"]:
        rid = route["route_id"]
        waypoints = route["waypoints"]
        declared_max_slope = float(route["max_slope_deg"])

        computed_max_slope = 0.0
        for p0, p1 in zip(waypoints, waypoints[1:]):
            dx = float(p1[0]) - float(p0[0])
            dy = float(p1[1]) - float(p0[1])
            dz = abs(float(p1[2]) - float(p0[2]))
            horiz = math.hypot(dx, dy)
            assert horiz > 1e-4, f"Route {rid} has a vertical step (zero horizontal run) between {p0} and {p1}"
            seg_slope_deg = math.degrees(math.atan2(dz, horiz))
            computed_max_slope = max(computed_max_slope, seg_slope_deg)

        assert computed_max_slope <= 30.0, (
            f"Route {rid} actual waypoint slope {computed_max_slope:.2f} deg exceeds 30 deg limit"
        )
        assert computed_max_slope <= declared_max_slope + 1.0, (
            f"Route {rid} actual slope {computed_max_slope:.2f} deg exceeds declared max_slope_deg {declared_max_slope}"
        )

        # Endpoint elevations must match the connected area ground elevations within road deck thickness (<= 0.15m)
        from_z = area_elevations[route["from_area"]]
        to_z = area_elevations[route["to_area"]]
        assert abs(float(waypoints[0][2]) - from_z) <= 0.15, (
            f"Route {rid} start z={waypoints[0][2]} does not match {route['from_area']} elevation {from_z}"
        )
        assert abs(float(waypoints[-1][2]) - to_z) <= 0.15, (
            f"Route {rid} end z={waypoints[-1][2]} does not match {route['to_area']} elevation {to_z}"
        )


def test_spawn_lies_inside_declared_south_entrance_area_bounds() -> None:
    """Prevent silent out-of-bounds or mid-air player spawn."""
    data = _load_world_layout()
    areas_by_id = {area["area_id"]: area for area in data["areas"]}
    spawn = data["spawn"]
    spawn_area = areas_by_id[spawn["area_id"]]

    sx, sy, sz = (float(c) for c in spawn["position"])
    bmin = spawn_area["bounds"]["min"]
    bmax = spawn_area["bounds"]["max"]
    clearance = float(spawn["clearance_radius_m"])

    assert bmin[0] + clearance <= sx <= bmax[0] - clearance, (
        f"Spawn X={sx} with clearance {clearance} falls outside area bounds [{bmin[0]}, {bmax[0]}]"
    )
    assert bmin[1] + clearance <= sy <= bmax[1] - clearance, (
        f"Spawn Y={sy} with clearance {clearance} falls outside area bounds [{bmin[1]}, {bmax[1]}]"
    )
    assert abs(sz - float(spawn_area["ground_elevation_m"])) <= 0.15, (
        f"Spawn Z={sz} does not lie on area ground elevation {spawn_area['ground_elevation_m']}"
    )


def test_area_key_mapping_bijection_for_downstream_areas() -> None:
    """Ensure W02-W06 builders can look up all 5 areas by either Issue #1 keys or check_data.py VALID_AREA_IDS."""
    data = _load_world_layout()
    mapping = data["area_key_mapping"]
    issue_to_schema = mapping["issue_to_schema_area_id"]
    schema_to_issue = mapping["schema_to_issue_area_id"]

    expected_issue_keys = {"A_plaza", "B_mansion", "C_candy", "D_amusement", "E_forest"}
    expected_schema_keys = {"A_plaza", "B_alley", "C_park", "D_mansion", "E_forest"}

    assert set(issue_to_schema.keys()) == expected_issue_keys
    assert set(issue_to_schema.values()) == expected_schema_keys
    assert set(schema_to_issue.keys()) == expected_schema_keys
    assert set(schema_to_issue.values()) == expected_issue_keys

    for ikey, skey in issue_to_schema.items():
        assert schema_to_issue[skey] == ikey

    areas_by_schema = {area["area_id"]: area for area in data["areas"]}
    areas_by_issue = {area["issue_key"]: area for area in data["areas"]}
    assert set(areas_by_schema.keys()) == expected_schema_keys
    assert set(areas_by_issue.keys()) == expected_issue_keys
