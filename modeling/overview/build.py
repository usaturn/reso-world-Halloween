"""Build the P1 overview scene `blender/overview/overview.blend` (W07, Issue #9).

Run (project directory, after every source key has been built; see `docs/p1-handoff.md`):
    resoloop blender run modeling/overview/build.py --json
    resoloop blender run modeling/overview/build.py --json --arg=--no-render   # skip the review renders

What it does:
1. Appends (copies, no library link) the root collection of `world`, `A_plaza`, `B_mansion`, `C_candy`,
   `D_amusement` and `E_forest` from `blender/<key>/<key>.blend` under the `overview` collection. The
   `common` key is not placed: its parts are already instanced inside the districts, and its own file is a
   line-up, not a world placement.
2. Merges the copies of the shared `MAT_CMN_*` materials and `SharedMesh_CMN_*` meshes that every district
   carries, so the scene has no `.001` names. A copy whose content differs is kept under `<name>_<key>`.
3. Checks the assembled world and writes `review/overview/checks.json`: the floor along every W01 route and at
   the spawn, the Meshy placeholders against `assets/meshy/received.json`, the movable parts of every
   manifest (separate object, pivot, recorded range) and the W01 landmarks against what was built.
4. Renders `review/overview/*.png` (whole world, entrance, five districts, route samples, the placeholders of
   M01-M08 and three groups of movable parts with their pivots marked), then removes the temporary markers.
5. Writes the integrated asset list `assets/manifest.json` (the manifests of `world`, `common` and the five
   districts; `export_result` taken from the newest `exports/p1/<key>-<UTC>/report.json`, if any).

Only `blender/overview/`, `review/overview/` and `assets/manifest.json` are written. The source `.blend`
files, their manifests and the Meshy files are read, never saved. The scene is reset first, so a second run
gives the same objects.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import bmesh  # type: ignore  # noqa: E402
import bpy  # type: ignore  # noqa: E402
from mathutils import Matrix, Vector  # type: ignore  # noqa: E402

from modeling.lib.render import render_review_images  # noqa: E402
from modeling.lib.scene import reset_scene, save_blend  # noqa: E402
from modeling.overview.manifest_merge import merge, newest_exports  # noqa: E402

KEY = "overview"
BLEND_REL = "blender/overview/overview.blend"
SCRIPT_REL = "modeling/overview/build.py"
REVIEW_REL = "review/overview"
CHECKS_REL = "review/overview/checks.json"
MANIFEST_REL = "assets/manifest.json"
SOURCE_KEYS = ["world", "A_plaza", "B_mansion", "C_candy", "D_amusement", "E_forest"]
MANIFEST_KEYS = ["world", "common", "A_plaza", "B_mansion", "C_candy", "D_amusement", "E_forest"]
SUFFIX = re.compile(r"^(?P<base>.+)\.(?P<num>\d{3})$")

# Floor sampling along the W01 routes (m).
FLOOR_BELOW = 0.25  # a floor may sit this far below the route's waypoint height
FLOOR_ABOVE = 0.35  # ... or this far above it (decks, curbs, paving)
HEAD_CLEARANCE = 2.0
SAMPLE_STEP = 1.0
LANE_MARGIN = 0.3

# Meshy rows -> the placeholder built for it (object name, whether its children belong to the shape).
PLACEHOLDERS = {
    "M01": ("APL_EntranceGateProxy_001", True),
    "M02": ("APL_GiantJackProxy_001", True),
    "M03": ("BMN_MansionPlaceholder_001", True),
    "M04": ("CCD_M04_CandyWorkshopProxy_001", True),
    "M05_CenterCasing": ("DAM_Carousel_001_M05_CenterCasing", False),
    "M05_Canopy": ("DAM_Carousel_001_M05_Canopy", False),
    "M06": ("DAM_GhostTrain_001_M06_EngineShell", False),
    "M07": ("EFR_ClockTower_001_Body", False),
    "M08": ("CCD_M08_FlyingWitchProxy_001", True),
}
# W01 landmarks -> the asset that was built in their place.
LANDMARK_ASSETS = {
    "LM_A_PumpkinTower_001": "APL_GiantJackProxy_001",
    "LM_B_HauntedMansion_001": "BMN_MansionPlaceholder_001",
    "LM_C_CandyArch_001": "CCD_CandyArch_001",
    "LM_D_CarouselGate_001": "DAM_Carousel_001",
    "LM_E_ClockTower_001": "EFR_ClockTower_001",  # was LM_E_WitchWorkshop_001 (renamed by W07)
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def r3(v) -> list[float]:
    return [round(float(c), 3) for c in v]


def read_json(rel_path: str) -> Any:
    return json.loads((PROJECT_ROOT / rel_path).read_text(encoding="utf-8"))


# =============================================================================== assembly
def mesh_signature(mesh) -> str:
    h = hashlib.sha256()
    h.update(f"{len(mesh.vertices)}/{len(mesh.polygons)}".encode())
    for v in mesh.vertices:
        h.update(("%.4f,%.4f,%.4f;" % tuple(v.co)).encode())
    h.update(",".join(m.name.split(".")[0] if m else "-" for m in mesh.materials).encode())
    return h.hexdigest()


def material_signature(mat) -> str:
    parts = [mat.name.split(".")[0]]
    if mat.use_nodes and mat.node_tree:
        for node in sorted(mat.node_tree.nodes, key=lambda n: n.name):
            parts.append(node.bl_idname)
            for sock in node.inputs:
                if hasattr(sock, "default_value") and not sock.is_linked:
                    val = sock.default_value
                    try:
                        parts.append(",".join("%.4f" % float(c) for c in val))
                    except TypeError:
                        parts.append("%.4f" % float(val) if isinstance(val, float) else str(val))
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def merge_duplicates(key: str, report: dict) -> None:
    """Merge `<name>.NNN` copies made by appending `key` into `<name>`, or rename them `<name>_<key>`."""
    for kind, coll, sig in (("materials", bpy.data.materials, material_signature), ("meshes", bpy.data.meshes, mesh_signature)):
        for block in sorted(coll, key=lambda b: b.name):
            m = SUFFIX.match(block.name)
            if not m:
                continue
            base = coll.get(m.group("base"))
            if base is not None and sig(base) == sig(block):
                block.user_remap(base)
                coll.remove(block)
                report.setdefault(kind, {}).setdefault("merged", []).append(f"{m.group('base')}@{key}")
            else:
                new = f"{m.group('base')}_{key}"
                block.name = new
                report.setdefault(kind, {}).setdefault("renamed", []).append(new)


def append_key(key: str, root_col, report: dict) -> dict:
    path = PROJECT_ROOT / "blender" / key / f"{key}.blend"
    if not path.is_file():
        raise SystemExit(f"{rel(path)} is missing; build it first: resoloop blender run modeling/{key}/build.py --json")
    before = set(bpy.data.objects)
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        if key not in src.collections:
            raise SystemExit(f"{rel(path)} has no collection {key!r}: {list(src.collections)}")
        dst.collections = [key]
    col = dst.collections[0]
    if col.name != key:
        raise SystemExit(f"appended collection was renamed to {col.name!r}; a name collides")
    root_col.children.link(col)
    merge_duplicates(key, report)
    added = [o for o in bpy.data.objects if o not in before]
    collided = sorted(o.name for o in added if SUFFIX.match(o.name))
    return {"blend_file": rel(path), "objects": len(added), "objects_all_objects": len(col.all_objects),
            "renamed_by_collision": collided}


def drop_library_records() -> int:
    """Remove the Library records that appending leaves behind, after making sure no data is still linked."""
    linked = []
    for attr in dir(bpy.data):
        coll = getattr(bpy.data, attr, None)
        if not isinstance(coll, bpy.types.bpy_prop_collection) or attr == "libraries":
            continue
        for idb in coll:
            if isinstance(idb, bpy.types.ID) and idb.library is not None:
                linked.append(f"{attr}:{idb.name}")
    if linked:
        raise SystemExit(f"data still linked to a library after append: {linked[:20]}")
    count = len(bpy.data.libraries)
    for lib in list(bpy.data.libraries):
        bpy.data.libraries.remove(lib)
    return count


# =============================================================================== geometry helpers
def mesh_world_points(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    for obj in objs:
        if obj.type != "MESH":
            continue
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
        mw = obj.matrix_world
        for v in me.vertices:
            yield mw @ v.co
        ev.to_mesh_clear()


def subtree(obj, include_children: bool):
    return [obj, *obj.children_recursive] if include_children else [obj]


def bounds_in(frame: Matrix, objs) -> tuple[list[float], list[float]] | None:
    inv = frame.inverted()
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    any_point = False
    for p in mesh_world_points(objs):
        q = inv @ p
        any_point = True
        for i in range(3):
            lo[i] = min(lo[i], q[i])
            hi[i] = max(hi[i], q[i])
    return (lo, hi) if any_point else None


def ray(origin: Vector, direction: Vector, distance: float):
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, _n, _i, obj, _m = bpy.context.scene.ray_cast(dg, origin, direction, distance=distance)
    return (loc, obj.name) if hit else (None, None)


# =============================================================================== checks
def probe_point(x: float, y: float, z: float) -> dict:
    """Classify one point of a walkway whose floor should be near height z (W01's waypoint height)."""
    out: dict[str, Any] = {}
    loc, name = ray(Vector((x, y, z + 0.5)), Vector((0, 0, -1)), 0.5 + 3.0)
    if loc is None or loc.z < z - FLOOR_BELOW:
        out["gap"] = True
        return out
    if loc.z > z + FLOOR_ABOVE:
        out["obstacle"] = name
        out["floor_z"] = loc.z
        return out
    floor = loc.z
    out["floor_z"] = floor
    top, tname = ray(Vector((x, y, floor + 1.9)), Vector((0, 0, -1)), 1.9 - 0.05)
    if top is not None and top.z > floor + FLOOR_ABOVE:
        out["obstacle"] = tname
    up, uname = ray(Vector((x, y, floor + 0.05)), Vector((0, 0, 1)), HEAD_CLEARANCE - 0.05)
    if up is not None:
        out["low_headroom"] = uname
    return out


def clear_width(x: float, y: float, floor: float, side: Vector, reach: float) -> tuple[float, str | None]:
    """Free width at 1 m above the floor, measured from the route centre to both sides (capped at `reach`)."""
    total = 0.0
    hit_names = []
    for sgn in (1.0, -1.0):
        loc, name = ray(Vector((x, y, floor + 1.0)), side * sgn, reach)
        total += reach if loc is None else (loc - Vector((x, y, floor + 1.0))).length
        if name:
            hit_names.append(name)
    return total, (", ".join(sorted(set(hit_names))) or None)


MIN_CLEAR = {"main_road": 3.0, "ring_road": 3.0, "bridge": 2.0, "side_path": 2.0}
STEP_SLOPE = math.tan(math.radians(30.0))


def check_routes(world_layout: dict) -> tuple[dict, list[tuple[Vector, str]]]:
    results: dict[str, Any] = {}
    markers: list[tuple[Vector, str]] = []
    for route in world_layout["routes"]:
        pts = [Vector(p) for p in route["waypoints"]]
        width = float(route["width_m"])
        need = MIN_CLEAR.get(route["kind"], 2.0)
        lanes = [0.0, -(width / 2 - LANE_MARGIN), width / 2 - LANE_MARGIN]
        counts = {"samples": 0, "floor": 0, "gap": 0, "obstacle": 0, "low_headroom": 0, "step": 0, "narrow": 0}
        problems: list[dict] = []
        last: dict[float, tuple[Vector, float]] = {}
        min_clear = (math.inf, None, None)
        for a, b in zip(pts, pts[1:]):
            seg = b - a
            flat = Vector((seg.x, seg.y, 0.0))
            length = flat.length
            if length < 1e-6:
                continue
            fwd = flat.normalized()
            side = Vector((-fwd.y, fwd.x, 0.0))
            steps = max(1, int(math.ceil(length / SAMPLE_STEP)))
            for s in range(steps + 1):
                c = a + seg * (s / steps)
                worst = "floor"
                for off in lanes:
                    p = c + side * off
                    res = probe_point(p.x, p.y, c.z)
                    counts["samples"] += 1
                    kinds = [k for k in ("gap", "obstacle", "low_headroom") if res.get(k)]
                    fz = res.get("floor_z")
                    if fz is not None and off in last:
                        q, qz = last[off]
                        dist = math.hypot(p.x - q.x, p.y - q.y)
                        if dist > 1e-6 and abs(fz - qz) > STEP_SLOPE * dist + 0.1:
                            kinds.append("step")
                            res["step"] = f"{qz:.2f}->{fz:.2f} over {dist:.2f} m"
                    if fz is not None:
                        last[off] = (p.copy(), fz)
                    if off == 0.0 and fz is not None and not res.get("gap"):
                        cw, cname = clear_width(p.x, p.y, fz, side, width / 2 + 0.6)
                        if cw < min_clear[0]:
                            min_clear = (cw, r3(p), cname)
                        if cw < need:
                            kinds.append("narrow")
                            res["narrow"] = f"{cw:.2f} m ({cname})"
                    for k in kinds:
                        counts[k] += 1
                    if not kinds:
                        counts["floor"] += 1
                        continue
                    for k in kinds:
                        problems.append({"at": r3(p), "lane_offset_m": round(off, 2), "kind": k,
                                         "object": res.get("obstacle") if k == "obstacle" else res.get("low_headroom") if k == "low_headroom"
                                         else res.get(k) if k in ("step", "narrow") else None})
                    rank = ["floor", "low_headroom", "narrow", "obstacle", "step", "gap"]
                    worst = max([worst, *kinds], key=rank.index)
                markers.append((Vector((c.x, c.y, c.z + 0.6)), worst))
        uniq: dict[tuple, dict] = {}
        for pr in problems:
            label = pr["object"] if pr["kind"] in ("obstacle", "low_headroom") else None
            entry = uniq.setdefault((pr["kind"], label), {"kind": pr["kind"], "object": label, "count": 0, "first_at": pr["at"],
                                                           "first_detail": pr["object"]})
            entry["count"] += 1
        results[route["route_id"]] = {
            "kind": route["kind"], "width_m": width, "required_clear_width_m": need, **counts,
            "min_clear_width_at_1m": {"width_m": round(min_clear[0], 3), "at": min_clear[1], "limited_by": min_clear[2]},
            "problems": sorted(uniq.values(), key=lambda d: (d["kind"], str(d["object"]))),
        }
    return results, markers


def check_spawns(world_layout: dict) -> dict:
    out = {}
    for sp in [{"spawn_id": "spawn", **world_layout["spawn"]}, *world_layout.get("spawn_candidates", [])]:
        cx, cy, cz = sp["position"]
        r = float(sp["clearance_radius_m"])
        counts = {"samples": 0, "floor": 0, "gap": 0, "obstacle": 0, "low_headroom": 0}
        objects: dict[str, int] = {}
        n = int(r / 0.5)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                x, y = cx + i * 0.5, cy + j * 0.5
                if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
                    continue
                res = probe_point(x, y, cz)
                counts["samples"] += 1
                kind = "gap" if res.get("gap") else "obstacle" if res.get("obstacle") else "low_headroom" if res.get("low_headroom") else "floor"
                counts[kind] += 1
                if kind != "floor":
                    nm = res.get("obstacle") or res.get("low_headroom") or "<none>"
                    objects[f"{kind}:{nm}"] = objects.get(f"{kind}:{nm}", 0) + 1
        out[sp["spawn_id"]] = {"position": sp["position"], "clearance_radius_m": r, **counts, "by_object": dict(sorted(objects.items()))}
    return out


def front_name(v: Vector) -> str:
    ang = math.degrees(math.atan2(v.y, v.x))
    return {0: "east(+X)", 90: "north(+Y)", 180: "west(-X)", -180: "west(-X)", -90: "south(-Y)"}.get(int(round(ang / 90.0)) * 90, f"{ang:.1f}deg")


def check_placeholders(received: dict) -> tuple[dict, dict[str, tuple[Vector, Vector, float]]]:
    rows = {r["row_id"]: r for r in received["assets"]}
    out: dict[str, Any] = {}
    views: dict[str, tuple[Vector, Vector, float]] = {}
    for row_id, (name, with_children) in PLACEHOLDERS.items():
        row = rows.get(row_id)
        obj = bpy.data.objects.get(name)
        entry: dict[str, Any] = {"placeholder": name}
        if row is None or obj is None:
            entry["error"] = "missing received.json row" if row is None else "placeholder object not found"
            out[row_id] = entry
            continue
        frame = obj.matrix_world.copy()
        b = bounds_in(frame, subtree(obj, with_children))
        want = row["derived"]["bounds_local_m"]
        if b is None:
            entry["error"] = "placeholder has no mesh"
            out[row_id] = entry
            continue
        lo, hi = b
        same = max(max(abs(lo[i] - want["min"][i]), abs(hi[i] - want["max"][i])) for i in range(3))
        # A placeholder may be modelled facing local -Y (front turned by 180 deg about Z).
        flip = max(max(abs(-hi[i] - want["min"][i]), abs(-lo[i] - want["max"][i])) for i in range(2))
        flip = max(flip, abs(lo[2] - want["min"][2]), abs(hi[2] - want["max"][2]))
        flipped = flip < same
        symmetric = abs(flip - same) < 0.005  # the bounds cannot tell +Y from -Y
        local_front = Vector((0, -1, 0)) if flipped else Vector((0, 1, 0))
        front_world = (frame.to_3x3() @ local_front)
        front_world.z = 0.0
        hint = row["decided"].get("placement_hint") or {}
        hint_rot = hint.get("rotation_z_deg")
        hint_front = None
        if hint_rot is not None:
            rz = math.radians(float(hint_rot))
            hint_front = Vector((-math.sin(rz), math.cos(rz), 0.0))
        if symmetric:
            front_world = hint_front.copy() if hint_front is not None else Vector((0.0, 0.0, 0.0))
        dims = [round(hi[i] - lo[i], 3) for i in range(3)]
        want_dims = [round(want["max"][i] - want["min"][i], 3) for i in range(3)]
        entry.update({
            "frame_origin_world": r3(frame.translation),
            "placement_hint_position": hint.get("position"),
            "bounds_local": {"min": r3(lo), "max": r3(hi)},
            "received_bounds_local": want,
            "dimensions_m": dims,
            "received_dimensions_m": want_dims,
            "max_bound_diff_m": round(min(same, flip), 4),
            "modelled_facing_local": ("not determined by the bounds (symmetric in x and y); see the area handoff"
                                      if symmetric else "-Y (180 deg from the finished model)" if flipped else "+Y"),
            "front_world": None if symmetric else front_name(front_world),
            "placement_hint_front": front_name(hint_front) if hint_front is not None else None,
            "front_matches_hint": None if (hint_front is None or symmetric) else bool(front_world.normalized().dot(hint_front) > 0.99),
        })
        if hint.get("position"):
            hp = hint["position"]
            entry["origin_diff_to_hint_m"] = round(max(abs(frame.translation[i] - hp[i]) for i in range(3) if hp[i] is not None), 4)
        out[row_id] = entry
        world_pts = list(mesh_world_points(subtree(obj, with_children)))
        wlo = Vector([min(p[i] for p in world_pts) for i in range(3)])
        whi = Vector([max(p[i] for p in world_pts) for i in range(3)])
        centre = (wlo + whi) / 2
        size = max(whi - wlo)
        views[row_id] = (centre, front_world.normalized() if front_world.length > 1e-6 else Vector((0, -1, 0)), size)
    return out, views


def walk_json(node, ancestors=()):
    if isinstance(node, dict):
        yield node, ancestors
        for v in node.values():
            yield from walk_json(v, ancestors + (node,))
    elif isinstance(node, list):
        for v in node:
            yield from walk_json(v, ancestors)


RANGE_WORDS = ("range", "stroke", "waypoints", "loop_length", "orbit_radius")


def _has_range_key(d: dict) -> bool:
    return any(any(w in k for w in RANGE_WORDS) for k in d.keys())


def range_recorded(names: tuple[str, ...], docs: list[Any]) -> str | None:
    """Where a movement range (angle/translation range, stroke or path) is recorded for one of `names`.

    A record counts when a dict that names the part (or its asset) holds a range-like key itself, in one of its two
    parent dicts, or in one of its direct child dicts. `range_recorded_under` in checks.json says which name matched,
    so an asset-level record (e.g. one path for a two-car train) can be told from a per-part one.
    """
    for doc in docs:
        for d, anc in walk_json(doc):
            hit = next((n for n in names if n in d or any(v == n for v in d.values() if isinstance(v, str))), None)
            if hit is None:
                continue
            holders = [d, *anc[-2:], *(v for v in d.values() if isinstance(v, dict))]
            if hit in d and isinstance(d[hit], dict):
                holders.append(d[hit])
            for h in holders:
                if _has_range_key(h):
                    return hit
    return None


def check_motion(manifests: dict[str, dict]) -> tuple[dict, list[Vector]]:
    out: dict[str, Any] = {}
    pivots: list[Vector] = []
    for key, man in manifests.items():
        if key in ("world", "common"):
            continue
        docs = [man]
        lay = PROJECT_ROOT / "layout" / "areas" / f"{key}.json"
        if lay.is_file():
            docs.append(json.loads(lay.read_text(encoding="utf-8")))
        rows = []
        for asset in man["assets"]:
            parts = {p["part_id"]: p for p in asset["parts"]}
            root_obj = bpy.data.objects.get(asset["hierarchy"]["asset_root"])
            for mr in asset["hierarchy"]["motion_roots"]:
                obj = bpy.data.objects.get(mr)
                row: dict[str, Any] = {"asset_id": asset["asset_id"], "motion_root": mr}
                if obj is None:
                    row["error"] = "object not found"
                    rows.append(row)
                    continue
                meshes = [o for o in subtree(obj, True) if o.type == "MESH"]
                part = parts.get(mr, {})
                want = Vector(part.get("pivot_local", (0, 0, 0)))
                par = bpy.data.objects.get(part.get("parent_part") or "")
                cands = []
                for ref in (par, root_obj):
                    if ref is not None:
                        cands.append((ref.matrix_world.inverted() @ obj.matrix_world.translation - want).length)
                row.update({
                    "object_type": obj.type,
                    "mesh_objects_moved": len(meshes),
                    "pivot_world": r3(obj.matrix_world.translation),
                    "pivot_local_matches_manifest": bool(cands) and min(cands) < 0.01,
                })
                found = range_recorded((mr, asset["asset_id"]), docs)
                row["range_recorded"] = found is not None
                row["range_recorded_under"] = found
                pivots.append(obj.matrix_world.translation.copy())
                rows.append(row)
        out[key] = {
            "motion_roots": len(rows),
            "missing": [r["motion_root"] for r in rows if "error" in r],
            "without_mesh": [r["motion_root"] for r in rows if r.get("mesh_objects_moved") == 0],
            "pivot_mismatch": [r["motion_root"] for r in rows if r.get("pivot_local_matches_manifest") is False],
            "range_not_found": [r["motion_root"] for r in rows if r.get("range_recorded") is False],
            "parts": rows,
        }
    return out, pivots


COPLANAR_TOL = 0.001  # two upward faces closer than this lie on the same plane (z-fighting in Resonite)
GRID_STEP = 0.5


def check_coplanar_tops(source_of: dict[str, str], extent: float = 50.0) -> list[dict]:
    """Find places where the two topmost surfaces seen from above belong to different keys and lie at the same height.

    Each mesh object is ray-cast on its own (BVH in object space), so a face exactly under another one is still
    found. Only pairs from different source keys are reported: those are integration overlaps that no single
    district build could see.
    """
    from mathutils.bvhtree import BVHTree  # type: ignore

    dg = bpy.context.evaluated_depsgraph_get()
    entries = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.name not in source_of:
            continue
        pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        lo = (min(p.x for p in pts), min(p.y for p in pts))
        hi = (max(p.x for p in pts), max(p.y for p in pts))
        entries.append((obj, BVHTree.FromObject(obj, dg), obj.matrix_world.inverted(), lo, hi))
    pairs: dict[tuple[str, str], dict] = {}
    n = int(extent / GRID_STEP)
    down = Vector((0.0, 0.0, -1.0))
    for i in range(-n, n + 1):
        x = i * GRID_STEP + 0.013  # off the exact grid so rays do not run along modelled edges
        for j in range(-n, n + 1):
            y = j * GRID_STEP + 0.017
            tops = []
            for obj, bvh, inv, lo, hi in entries:
                if not (lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1]):
                    continue
                o = inv @ Vector((x, y, 60.0))
                d = (inv.to_3x3() @ down).normalized()
                loc, nrm, _idx, _dist = bvh.ray_cast(o, d, 120.0)
                if loc is None:
                    continue
                wloc = obj.matrix_world @ loc
                wn = (obj.matrix_world.to_3x3() @ nrm).normalized()
                tops.append((wloc.z, obj.name, abs(wn.z)))
            if len(tops) < 2:
                continue
            tops.sort(reverse=True)
            (z1, a, n1), (z2, b, n2) = tops[0], tops[1]
            if z1 - z2 > COPLANAR_TOL or n1 < 0.9 or n2 < 0.9 or source_of[a] == source_of[b]:
                continue
            key = tuple(sorted((a, b)))
            e = pairs.setdefault(key, {"objects": list(key), "keys": [source_of[key[0]], source_of[key[1]]], "samples": 0,
                                       "z": round(z1, 3), "first_at": [round(x, 2), round(y, 2)]})
            e["samples"] += 1
    out = sorted(pairs.values(), key=lambda e: -e["samples"])
    for e in out:
        e["area_m2_approx"] = round(e["samples"] * GRID_STEP * GRID_STEP, 2)
    return out


def check_landmarks(world_layout: dict) -> dict:
    out = {}
    for lm in world_layout["landmarks"]:
        name = LANDMARK_ASSETS.get(lm["landmark_id"])
        obj = bpy.data.objects.get(name or "")
        entry = {"planned_position": lm["position"], "planned_height_m": lm["height_m"], "built_asset": name}
        if obj is not None:
            pts = list(mesh_world_points(subtree(obj, True)))
            lo = [min(p[i] for p in pts) for i in range(3)]
            hi = [max(p[i] for p in pts) for i in range(3)]
            entry.update({"built_origin": r3(obj.matrix_world.translation),
                          "built_bbox_centre_xy": [round((lo[0] + hi[0]) / 2, 3), round((lo[1] + hi[1]) / 2, 3)],
                          "built_top_z": round(hi[2], 3),
                          "built_height_above_ground_m": round(hi[2] - lm["position"][2], 3)})
            entry["xy_offset_m"] = round(math.dist(entry["built_bbox_centre_xy"], lm["position"][:2]), 3)
        out[lm["landmark_id"]] = entry
    return out


# =============================================================================== markers and renders
class Markers:
    """Temporary emissive marker spheres; removed on exit so nothing is saved."""

    COLOURS = {"pivot": (1.0, 0.1, 0.8), "floor": (0.1, 0.9, 0.2), "gap": (1.0, 0.05, 0.05),
               "obstacle": (1.0, 0.55, 0.0), "low_headroom": (1.0, 0.95, 0.1), "step": (0.6, 0.0, 1.0),
               "narrow": (0.1, 0.6, 1.0)}

    def __init__(self, points: list[tuple[Vector, str]], radius: float):
        self.points = points
        self.radius = radius
        self.objs = []
        self.mats = []
        self.meshes = []

    def __enter__(self):
        groups: dict[str, list[Vector]] = {}
        for p, kind in self.points:
            groups.setdefault(kind, []).append(p)
        for kind, pts in groups.items():
            mat = bpy.data.materials.new(f"TMP_Marker_{kind}")
            mat.use_nodes = True
            nt = mat.node_tree
            nt.nodes.clear()
            em = nt.nodes.new("ShaderNodeEmission")
            em.inputs[0].default_value = (*self.COLOURS.get(kind, (1, 1, 1)), 1.0)
            em.inputs[1].default_value = 6.0
            outn = nt.nodes.new("ShaderNodeOutputMaterial")
            nt.links.new(em.outputs[0], outn.inputs[0])
            bm = bmesh.new()
            for p in pts:
                bmesh.ops.create_icosphere(bm, subdivisions=1, radius=self.radius, matrix=Matrix.Translation(p))
            me = bpy.data.meshes.new(f"TMP_Marker_{kind}")
            bm.to_mesh(me)
            bm.free()
            me.materials.append(mat)
            ob = bpy.data.objects.new(f"TMP_Marker_{kind}", me)
            bpy.context.scene.collection.objects.link(ob)
            self.objs.append(ob)
            self.mats.append(mat)
            self.meshes.append(me)
        return self

    def __exit__(self, *exc):
        for ob in self.objs:
            bpy.data.objects.remove(ob, do_unlink=True)
        for me in self.meshes:
            bpy.data.meshes.remove(me, do_unlink=True)
        for mat in self.mats:
            bpy.data.materials.remove(mat, do_unlink=True)
        return False


def render(views: list[tuple], markers: list[tuple[Vector, str]] | None, radius: float, size=(1280, 720)) -> list[str]:
    spec = [{"filepath": PROJECT_ROOT / REVIEW_REL / f, "location": loc, "target": tgt, "lens_mm": lens} for f, loc, tgt, lens in views]
    if markers:
        with Markers(markers, radius):
            render_review_images(spec, width=size[0], height=size[1], samples=24)
    else:
        render_review_images(spec, width=size[0], height=size[1], samples=24)
    return [f"{REVIEW_REL}/{v[0]}" for v in views]


def render_all(route_markers, pivots, ph_views) -> list[str]:
    written: list[str] = []
    pivot_marks = [(p, "pivot") for p in pivots]
    written += render([
        ("01_world_aerial_from_south.png", (0.0, -96.0, 62.0), (0.0, -2.0, 0.0), 30.0),
        ("02_world_aerial_from_northwest.png", (-78.0, 70.0, 55.0), (0.0, 0.0, 0.0), 30.0),
        ("03_spawn_to_plaza.png", (0.0, -47.5, 1.7), (0.0, -10.0, 3.0), 26.0),
    ], None, 0.0)
    written += render([("04_route_samples_plan.png", (0.0, -14.0, 168.0), (0.0, 0.0, 0.0), 35.0)], route_markers, 0.45)
    written += render([
        ("14_side_bridge_NE_landing.png", (26.0, 12.5, 4.2), (18.0, 20.0, 1.0), 30.0),
        ("15_side_bridge_NW_landing.png", (-26.0, 12.5, 4.2), (-18.0, 20.0, 1.0), 30.0),
    ], route_markers, 0.12)
    written += render([
        ("05_area_A_plaza.png", (17.0, -21.0, 15.0), (0.0, 0.0, 2.0), 30.0),
        ("06_area_B_mansion.png", (15.0, 13.0, 15.0), (0.0, 34.0, 4.0), 30.0),
        ("07_area_C_candy.png", (15.0, -17.0, 15.0), (34.0, 0.0, 3.0), 30.0),
        ("08_area_D_amusement.png", (19.0, -12.0, 16.0), (0.0, -34.0, 2.0), 30.0),
        ("09_area_E_forest.png", (-15.0, -19.0, 16.0), (-34.0, 0.0, 3.0), 30.0),
    ], pivot_marks, 0.22)
    written += render([
        ("10_parts_A_fountain_pumpkins.png", (6.5, -12.5, 5.5), (0.0, 0.0, 2.2), 32.0),
        ("11_parts_B_doors_windows_bell.png", (3.5, 30.0, 5.0), (0.0, 39.0, 3.8), 30.0),
        ("12_parts_C_cauldron_machine.png", (26.0, -1.5, 6.5), (34.4, 0.0, 1.2), 22.0),
        ("13_parts_D_carousel_train_cups.png", (2.5, -40.0, 8.0), (2.0, -33.0, 1.5), 22.0),
    ], pivot_marks, 0.12)
    ph = []
    for row_id, (centre, front, size) in ph_views.items():
        dist = 1.3 * size + 3.5
        view_dir = Matrix.Rotation(math.radians(25.0), 3, "Z") @ front  # a little off the front axis
        loc = centre + view_dir * dist + Vector((0.0, 0.0, 0.45 * size + 1.5))
        if row_id == "M01":
            loc = centre + front * dist + Vector((0.0, 0.0, 1.0))
        ph.append((f"20_placeholder_{row_id}.png", tuple(loc), tuple(centre), 35.0))
    written += render(ph, pivot_marks, 0.10, size=(960, 540))
    return written


# =============================================================================== integrated manifest
def write_integrated_manifest(manifests: dict[str, dict]) -> dict:
    exports = newest_exports(PROJECT_ROOT / "exports" / "p1")
    data = merge(manifests, MANIFEST_KEYS, exports, "exports/p1", KEY, SCRIPT_REL)
    (PROJECT_ROOT / MANIFEST_REL).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"assets": len(data["assets"]), "exported_keys": sorted(data["export_dirs"])}


# =============================================================================== main
def main() -> dict:
    no_render = any("no-render" in a for a in sys.argv)
    _scene, root = reset_scene(KEY)
    merge_report: dict[str, Any] = {}
    sources = {k: append_key(k, root, merge_report) for k in SOURCE_KEYS}
    merge_report["library_records_removed"] = drop_library_records()
    bpy.context.view_layer.update()

    world_layout = read_json("layout/world_layout.json")
    received = read_json("assets/meshy/received.json")
    manifests = {k: read_json(f"assets/manifest/{k}.json") for k in MANIFEST_KEYS}

    routes, route_markers = check_routes(world_layout)
    spawns = check_spawns(world_layout)
    placeholders, ph_views = check_placeholders(received)
    motion, pivots = check_motion(manifests)
    landmarks = check_landmarks(world_layout)
    source_of = {o.name: k for k in SOURCE_KEYS for o in bpy.data.collections[k].all_objects}
    coplanar = check_coplanar_tops(source_of)

    renders = [] if no_render else render_all(route_markers, pivots, ph_views)
    leftovers = sorted(o.name for o in bpy.data.objects if o.name.startswith("TMP_") or o.name.startswith("Temp_"))
    if leftovers:
        raise SystemExit(f"temporary objects left before save: {leftovers}")
    save_blend(PROJECT_ROOT / BLEND_REL, pack_images=True)
    manifest_info = write_integrated_manifest(manifests)

    checks = {
        "key": KEY,
        "script": SCRIPT_REL,
        "blend_file": BLEND_REL,
        "sources": sources,
        "merged_duplicates": merge_report,
        "objects": len(bpy.data.objects),
        "meshes": len(bpy.data.meshes),
        "materials": len(bpy.data.materials),
        "images": len([i for i in bpy.data.images if i.name not in {"Render Result", "Viewer Node"}]),
        "libraries": [lib.filepath for lib in bpy.data.libraries],
        "routes": routes,
        "spawns": spawns,
        "placeholders": placeholders,
        "motion": {k: {kk: vv for kk, vv in v.items() if kk != "parts"} for k, v in motion.items()},
        "motion_parts": {k: v["parts"] for k, v in motion.items()},
        "landmarks": landmarks,
        "coplanar_tops_between_keys": coplanar,
        "integrated_manifest": manifest_info,
        "review_images": renders if renders else "not rendered in this run (--no-render)",
    }
    checks_path = PROJECT_ROOT / CHECKS_REL
    if no_render and checks_path.is_file():
        checks["review_images"] = json.loads(checks_path.read_text(encoding="utf-8")).get("review_images")
    checks_path.parent.mkdir(parents=True, exist_ok=True)
    checks_path.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {k: checks[k] for k in ("objects", "meshes", "materials", "images", "libraries")}
    summary["sources"] = {k: v["objects"] for k, v in sources.items()}
    summary["route_problems"] = {k: {kk: v[kk] for kk in ("gap", "step", "obstacle", "narrow", "low_headroom") if v[kk]}
                                 for k, v in routes.items()}
    summary["route_min_clear_width"] = {k: v["min_clear_width_at_1m"]["width_m"] for k, v in routes.items()}
    summary["coplanar_tops_between_keys"] = [(e["objects"], e["samples"]) for e in coplanar]
    summary["renders"] = len(renders)
    print("OVERVIEW_BUILD_SUMMARY:" + json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    main()
