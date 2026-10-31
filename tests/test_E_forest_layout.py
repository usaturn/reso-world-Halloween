"""S-criteria tests for the W06 E_forest layout (`layout/areas/E_forest.json`, `assets/manifest/E_forest.json`).

Why these tests exist (create-reso-world AGENTS.md, test criterion S):
- `modeling/E_forest/build.py` records every placement's measured footprint and every moving part's swept
  envelope, but nothing fails when a later edit moves a tree onto the main road, closes a side-bridge landing,
  lets a swinging branch hang into a boardwalk or pushes a canopy over the cliff edge. `tools/check_data.py`
  only validates fields. Such a layout still builds, exports and looks plausible, so the damage stays unnoticed
  until people walk the world in P2.
- The keep-out zones are derived from W01's `layout/world_layout.json` (main route, connection points, line of
  sight), not from the E_forest file, so the E_forest build cannot redefine them away.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOL = 0.05  # overlaps thinner than this are abutting edges


def _load(rel: str) -> dict:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def _overlaps(a: dict | None, b: dict) -> bool:
    if a is None:
        return False
    return all(min(a["max"][i], b["max"][i]) - max(a["min"][i], b["min"][i]) > TOL for i in range(3))


def _contains_point(box: dict, p: list[float]) -> bool:
    return all(box["min"][i] <= p[i] <= box["max"][i] for i in range(3))


def _w01_keep_outs(clear_z: float) -> list[tuple[str, dict, list[float] | None]]:
    """(name, box, target point or None) for W01's main route, connection points and line of sight inside area E."""
    world = _load("layout/world_layout.json")
    area = next(a for a in world["areas"] if a["area_id"] == "E_forest")
    zones: list[tuple[str, dict, list[float] | None]] = []
    for route in world["routes"]:
        if route["route_id"] != "Route_West_Forest_Bridge":
            continue
        pts = [p for p in route["waypoints"] if p[0] <= area["bounds"]["max"][0]]
        hw = route["width_m"] / 2.0
        zones.append((route["route_id"], {"min": [min(p[0] for p in pts), -hw, 0.0], "max": [max(p[0] for p in pts), hw, clear_z]}, None))
    for conn in area["connection_points"]:
        x, y, _ = conn["position"]
        hw = conn["width_m"] / 2.0
        zones.append((conn["id"], {"min": [x - hw, y - hw, 0.0], "max": [x + hw, y + hw, clear_z]}, None))
    for los in world["line_of_sight"]:
        if los["to_area"] != "E_forest":
            continue
        hw = los["corridor_width_m"] / 2.0
        target = los["to_point"]
        zones.append((los["los_id"], {"min": [target[0], -hw, 0.0], "max": [area["bounds"]["max"][0], hw, target[2] + hw]}, target))
    return zones


def test_placements_stay_in_area_and_off_w01_routes_landings_and_sightline() -> None:
    """Prevent silently blocking the main road, a side-bridge landing or the view to the clock tower, or spilling over the cliff."""
    layout = _load("layout/areas/E_forest.json")
    bounds = layout["bounds"]
    clear_z = layout["walk_clearance_z_m"]
    placements = layout["placements"]
    assert placements

    zones = _w01_keep_outs(clear_z)
    assert {name for name, _, _ in zones} >= {"Route_West_Forest_Bridge", "Conn_E_East_Main", "Conn_E_North_Side", "Conn_E_South_Side"}
    problems = []
    for p in placements:
        fp = p["footprint_world"]
        if not all(bounds["min"][i] - 0.01 <= fp["min"][i] and fp["max"][i] <= bounds["max"][i] + 0.01 for i in range(3)):
            problems.append(f"{p['instance_name']} leaves the area bounds: {fp}")
        for name, box, target in zones:
            if target is not None:
                if _overlaps(fp, box) and not _contains_point(fp, target):
                    problems.append(f"{p['instance_name']} blocks {name}")
            elif _overlaps(p["footprint_low_world"], box):
                problems.append(f"{p['instance_name']} blocks {name}")
    assert not problems, "\n".join(problems)


def test_walkways_and_viewpoints_stay_clear_of_placements_and_moving_parts() -> None:
    """Prevent props or swinging branches, hands, bells and bats from hanging into boardwalks, bridges, ramps or viewing spots."""
    layout = _load("layout/areas/E_forest.json")
    manifest = _load("assets/manifest/E_forest.json")
    corridors = [(c["id"], c["corridor_world"], set(c["owners"])) for c in layout["paths"]]
    corridors += [(v["id"], v["bounds"], set(v["owners"])) for v in layout["viewpoints"]]
    w01 = [(name, box, set()) for name, box, target in _w01_keep_outs(layout["walk_clearance_z_m"]) if target is None]
    envelopes = [m for a in manifest["assets"] for m in a["motion"]]
    assert corridors and envelopes

    problems = []
    for p in layout["placements"]:
        for cid, box, owners in corridors:
            if p["instance_name"] not in owners and _overlaps(p["footprint_low_world"], box):
                problems.append(f"{p['instance_name']} intrudes {cid}")
    for m in envelopes:
        for cid, box, _ in corridors + w01:  # boxes reach deck height + headroom, so a 3D overlap means a hit
            if _overlaps(m["envelope_world"], box):
                problems.append(f"{m['part_name']} ({m['gimmick_id']}) sweeps into {cid}")
    assert not problems, "\n".join(problems)
