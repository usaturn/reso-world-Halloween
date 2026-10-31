"""Build `blender/E_forest/E_forest.blend`, `review/E_forest/*.png`, `layout/areas/E_forest.json` and `assets/manifest/E_forest.json`.

Run via:
    resoloop blender run modeling/E_forest/build.py --json
    resoloop blender run modeling/E_forest/build.py --json --arg=--no-render   # skip the review renders

The scene is reset first (`reset_scene`), so a second run gives the same objects. Only the E_forest key's
files are written; `blender/world/world.blend` and `blender/common/common.blend` are read, never saved.
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

import bpy  # type: ignore  # noqa: E402
from mathutils import Matrix, Vector  # type: ignore  # noqa: E402

from modeling.E_forest import clock_tower as CT  # noqa: E402
from modeling.E_forest import layout as L  # noqa: E402
from modeling.E_forest import props, structures  # noqa: E402
from modeling.E_forest.geo import MeshBuilder, empty, mesh_object  # noqa: E402
from modeling.E_forest.palette import build_palette  # noqa: E402
from modeling.lib.common_parts import append_common_part  # noqa: E402
from modeling.lib.render import render_review_images  # noqa: E402
from modeling.lib.scene import reset_scene, save_blend  # noqa: E402

KEY = "E_forest"
BLEND_REL_PATH = "blender/E_forest/E_forest.blend"
SCRIPT_REL_PATH = "modeling/E_forest/build.py"
MANIFEST_REL_PATH = "assets/manifest/E_forest.json"
LAYOUT_REL_PATH = "layout/areas/E_forest.json"
REVIEW_DIR = "review/E_forest"
UPDATED_AT = "2026-10-31"
VERSION = "W06-1"
TOL = 0.05  # overlaps thinner than this are abutting edges, not intrusions


# =============================================================================== measuring
def _r(v: float) -> float:
    return round(float(v) + 0.0, 4)


def _vec(v) -> list[float]:
    return [_r(c) for c in v]


def tree_objects(root) -> list:
    return [root] + list(root.children_recursive)


def world_points(objs) -> list[Vector]:
    pts: list[Vector] = []
    for o in objs:
        if o.type == "MESH" and o.data is not None:
            mw = o.matrix_world
            pts.extend(mw @ v.co for v in o.data.vertices)
    return pts


def aabb(points, z_max: float | None = None) -> dict | None:
    pts = [p for p in points if z_max is None or p.z <= z_max]
    if not pts:
        return None
    return {"min": [_r(min(p[i] for p in pts)) for i in range(3)], "max": [_r(max(p[i] for p in pts)) for i in range(3)]}


def overlaps(a: dict | None, b: dict | None, tol: float = TOL) -> bool:
    if a is None or b is None:
        return False
    return all(min(a["max"][i], b["max"][i]) - max(a["min"][i], b["min"][i]) > tol for i in range(3))


def inside(a: dict, b: dict, tol: float = 0.01) -> bool:
    return all(a["min"][i] >= b["min"][i] - tol and a["max"][i] <= b["max"][i] + tol for i in range(3))


def mesh_metrics(objs) -> dict:
    tris = verts = 0
    mats: set[str] = set()
    for o in objs:
        if o.type == "MESH" and o.data is not None:
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
            verts += len(o.data.vertices)
            mats.update(m.name for m in o.data.materials if m is not None)
    return {"measured": True, "measurement_source": "blender_scene", "triangles": tris, "vertices": verts,
            "materials_count": len(mats), "objects_count": len(objs)}, sorted(mats)


# =============================================================================== registry
class Asset:
    def __init__(self, asset_id: str, category: str, root, origin_policy: str = "ground_center", notes: str = "",
                 collider: str = "none", gimmicks: tuple[str, ...] = (), placeholder: bool = False):
        self.asset_id = asset_id
        self.category = category
        self.root = root
        self.origin_policy = origin_policy
        self.notes = notes
        self.collider = collider
        self.gimmicks = list(gimmicks)
        self.placeholder = placeholder
        self.parts: list[tuple[Any, str, str, str]] = [(root, "asset_root", origin_policy, "")]
        self.motions: list[dict] = []
        self.attachments: list[dict] = []
        self.instances: list[Any] = [root]
        self.replacement_slot: dict | None = None
        self.extra: dict = {}

    def part(self, obj, role: str, origin_policy: str, notes: str = "") -> None:
        self.parts.append((obj, role, origin_policy, notes))


ASSETS: list[Asset] = []
PLACEMENT_META: dict[str, dict] = {}  # instance name -> {asset_id, category, role}


def register(asset: Asset) -> Asset:
    ASSETS.append(asset)
    for inst in asset.instances:
        PLACEMENT_META[inst.name] = {"asset_id": asset.asset_id, "category": asset.category, "role": asset.notes}
    return asset


def add_instance(asset: Asset, obj) -> None:
    asset.instances.append(obj)
    PLACEMENT_META[obj.name] = {"asset_id": asset.asset_id, "category": asset.category, "role": asset.notes}


# =============================================================================== building
def build_clock_tower(col, P) -> Asset:
    pos = L.CLOCK_TOWER["position"]
    root = empty("EFR_ClockTower_001", col, pos, (0.0, 0.0, L.CLOCK_TOWER["rotation_z_deg"]), size=2.0)
    body = CT.tower_body(P).to_object("EFR_ClockTower_001_Body", col, parent=root)
    dial = CT.dial(P).to_object("EFR_ClockTower_001_Dial", col, CT.DIAL_CENTRE, parent=root)
    hour_piv = empty("EFR_ClockTower_001_HourHandPivot", col, CT.HOUR_HAND_PIVOT, parent=root, size=0.3)
    hour = CT.hour_hand(P).to_object("EFR_ClockTower_001_HourHand", col, parent=hour_piv)
    min_piv = empty("EFR_ClockTower_001_MinuteHandPivot", col, CT.MINUTE_HAND_PIVOT, parent=root, size=0.3)
    minute = CT.minute_hand(P).to_object("EFR_ClockTower_001_MinuteHand", col, parent=min_piv)
    bracket = CT.bell_bracket(P).to_object("EFR_ClockTower_001_BellBracket", col, parent=root)
    bell_piv = empty("EFR_ClockTower_001_BellPivot", col, CT.BELL_PIVOT, parent=root, size=0.3)
    bell = CT.bell(P).to_object("EFR_ClockTower_001_Bell", col, parent=bell_piv)

    a = Asset("EFR_ClockTower_001", "gimmick", root, notes="M07 magical clock tower placeholder: body, dial, hour and minute hands, bell (G20).",
              collider="separate_fixed_collision", gimmicks=("G20",), placeholder=True)
    a.part(body, "visual_root", "ground_center", "Placeholder body; the M07 finished model replaces this object only.")
    a.part(dial, "visual_root", "attachment_point", "Dial placeholder centred on the clock axis. M07 has its own dial: hide or remove this object when M07 is in.")
    a.part(hour_piv, "motion_root", "hinge_pivot", "Hour hand rotation axis = clock axis.")
    a.part(hour, "visual_root", "hinge_pivot")
    a.part(min_piv, "motion_root", "hinge_pivot", "Minute hand rotation axis = clock axis.")
    a.part(minute, "visual_root", "hinge_pivot")
    a.part(bracket, "static_part", "ground_center", "Bell bracket in front of the belfry; kept when M07 replaces the body.")
    a.part(bell_piv, "motion_root", "hinge_pivot", "Bell hanging point.")
    a.part(bell, "visual_root", "hinge_pivot")
    a.motions += [
        {"pivot": hour_piv, "visual": hour, "gimmick_id": "G20", "motion_type": "rotation", "axis": "-Y", "range": (0.0, 360.0, "deg"),
         "samples": [0, 45, 90, 135, 180, 225, 270, 315],
         "notes": "Rest pose 12:00 (pointing +Z). Positive angle about the pivot's -Y axis = clockwise seen from the front. One turn per 12 h."},
        {"pivot": min_piv, "visual": minute, "gimmick_id": "G20", "motion_type": "rotation", "axis": "-Y", "range": (0.0, 360.0, "deg"),
         "samples": [0, 45, 90, 135, 180, 225, 270, 315],
         "notes": "Rest pose 12:00. Clockwise = positive about -Y. One turn per hour; the bell can ring on the hour."},
        {"pivot": bell_piv, "visual": bell, "gimmick_id": "G20", "motion_type": "oscillation", "axis": "X", "range": (-25.0, 25.0, "deg"),
         "samples": [-25, -12.5, 0, 12.5, 25],
         "notes": "Swings front-back about the hanging point when the clock strikes; rest pose hangs straight down."},
    ]
    a.attachments += [
        {"name": "EFR_ClockTower_001_HourHandPivot", "purpose": "Clock axis (hands, chime sound source).", "obj": hour_piv, "gimmick": "G20"},
        {"name": "EFR_ClockTower_001_BellPivot", "purpose": "Bell ring sound and sparkle effect.", "obj": bell_piv, "gimmick": "G20"},
    ]
    a.replacement_slot = {
        "meshy_id": "M07",
        "visual_root_part": "EFR_ClockTower_001_Body",
        "target_dimensions_m": list(CT.M07_DIMENSIONS),
        "target_bounds_local": {"min": list(CT.M07_BOUNDS["min"]), "max": list(CT.M07_BOUNDS["max"])},
        "forward_axis": "+Y",
        "origin": "ground_center (W09 decided.origin_source; M07 placed with scale 7.3828, yaw 180)",
        "dial_centre_local": list(CT.DIAL_CENTRE),
        "dial_outer_diameter_m": round(CT.DIAL_OUTER_R * 2, 3),
        "keep_separate_parts": ["EFR_ClockTower_001_HourHandPivot", "EFR_ClockTower_001_HourHand", "EFR_ClockTower_001_MinuteHandPivot",
                                "EFR_ClockTower_001_MinuteHand", "EFR_ClockTower_001_BellBracket", "EFR_ClockTower_001_BellPivot",
                                "EFR_ClockTower_001_Bell"],
        "hide_on_replacement": ["EFR_ClockTower_001_Dial"],
        "source": "assets/meshy/received.json (row M07)",
    }
    return register(a)


def build_face_trees(col, P) -> list[Asset]:
    out = []
    for spec in L.FACE_TREES:
        parts = props.build_face_tree(col, P, spec)
        name = spec["id"]
        a = Asset(name, "gimmick", parts["root"], notes=spec["notes"], collider="separate_fixed_collision", gimmicks=("G17",))
        a.part(parts["trunk"], "visual_root", "ground_center", "Trunk with roots, canopy, brows, nose and dark eye sockets.")
        a.part(parts["mouth"], "visual_root", "attachment_point", "Glowing grin (expression part; may glow or be swapped).")
        for side in ("L", "R"):
            piv, br = parts["branches"][side]
            a.part(piv, "motion_root", "hinge_pivot", f"Branch {side} joint with the trunk.")
            a.part(br, "visual_root", "hinge_pivot", f"Moving branch {side} with leaves and a small lantern.")
            a.motions.append({"pivot": piv, "visual": br, "gimmick_id": "G17", "motion_type": "oscillation", "axis": "Y", "range": (-8.0, 8.0, "deg"),
                              "samples": [-8, -4, 0, 4, 8], "notes": "Sway up and down about the joint (pivot-local Y = the tree's front axis)."})
            epiv, eye = parts["eyes"][side]
            a.part(epiv, "motion_root", "hinge_pivot", f"Eye {side} centre; local +Y points out of the trunk.")
            a.part(eye, "visual_root", "hinge_pivot", f"Glowing eye {side} with a dark pupil.")
            a.motions.append({"pivot": epiv, "visual": eye, "gimmick_id": "G17", "motion_type": "scale_or_glow", "axis": "Z", "range": (0.1, 1.0, "ratio"),
                              "samples": [], "notes": "Blink: scale the pivot's local Z from 1.0 (open) to 0.1 (closed) and back; the eye stays centred."})
        out.append(register(a))
    return out


SERIES_NOTES = {
    "EFR_TreeOak": "Reusable broad oak with a teal canopy (canopy bottom ~3.8 m).",
    "EFR_TreePine": "Reusable dark spruce with drooping tiers (lowest tier ~1.6 m).",
    "EFR_TreeTwist": "Reusable twisted tree with purple leaves and a hanging lantern.",
}


def build_series_trees(col, P) -> list[Asset]:
    out = []
    for kind, spots in L.TREES.items():
        mesh = props.tree_mesh(kind, P)
        objs = [mesh_object(f"{kind}_{i + 1:03d}", col, mesh, (x, y, 0.0), (0.0, 0.0, rz)) for i, (x, y, rz) in enumerate(spots)]
        a = Asset(objs[0].name, "vegetation", objs[0], notes=SERIES_NOTES[kind], collider="convex_hull")
        register(a)
        for o in objs[1:]:
            add_instance(a, o)
        out.append(a)
    for kind, spots, mesh, cat, note in (
        ("EFR_Rock", L.ROCKS, props.rock_mesh(P), "prop", "Reusable mossy boulder."),
        ("EFR_Bush", L.BUSHES, props.bush_mesh(P), "vegetation", "Reusable low bush."),
    ):
        objs = [mesh_object(f"{kind}_{i + 1:03d}", col, mesh, (x, y, 0.0), (0.0, 0.0, rz)) for i, (x, y, rz) in enumerate(spots)]
        a = Asset(objs[0].name, cat, objs[0], notes=note, collider="convex_hull" if kind == "EFR_Rock" else "none")
        register(a)
        for o in objs[1:]:
            add_instance(a, o)
        out.append(a)
    return out


def _glow_params(index: int) -> dict:
    """Per-individual glow values (the material stays shared): different periods and phases."""
    period = round(3.2 + (index * 0.83) % 3.4, 2)
    return {"period_s": period, "phase_s": round((index * 1.37) % period, 2), "intensity_min": 0.35, "intensity_max": 1.0}


def build_mushrooms(col, P) -> list[Asset]:
    out: dict[str, Asset] = {}
    counters: dict[str, int] = {}
    glow_index = 0
    entries = [(k, x, y, 0.0, yaw, g) for k, x, y, yaw, g in L.MUSHROOMS]
    gx, gy, gz = L.GIANT_MUSHROOM["position"]
    entries.append(("Giant", gx, gy, gz, L.GIANT_MUSHROOM["yaw"], True))
    for kind, x, y, z, yaw, glow in entries:
        body_mesh, glow_mesh, attach = props.mushroom_meshes(kind, P)
        counters[kind] = counters.get(kind, 0) + 1
        name = f"EFR_Mushroom{kind}_{counters[kind]:03d}"
        body = mesh_object(name, col, body_mesh, (x, y, z), (0.0, 0.0, yaw))
        if kind not in out:
            note = {"Cluster": "Reusable cluster of three small orange mushrooms.", "Medium": "Reusable medium teal mushroom.",
                    "Tall": "Reusable tall purple mushroom (cap underside 1.9 m).",
                    "Giant": "Giant purple mushroom that roofs the rest spot (cap underside 3.1 m)."}[kind]
            a = Asset(name, "vegetation", body, notes=note, collider="convex_hull" if kind in ("Tall", "Giant") else "none", gimmicks=("G18",))
            a.extra["glow_individuals"] = []
            a.extra["shared_materials"] = {"body": sorted({m.name for m in body_mesh.materials}), "glow": "MAT_EFR_MushGlow"}
            out[kind] = register(a)
        else:
            add_instance(out[kind], body)
        a = out[kind]
        if glow:
            gobj = mesh_object(f"{name}_Glow", col, glow_mesh, attach, parent=body)
            params = _glow_params(glow_index)
            glow_index += 1
            a.extra["glow_individuals"].append({"instance": name, "glow_part": gobj.name, "attach_local": list(attach), "obj": gobj, **params})
            if body is a.root:
                a.part(gobj, "attachment_point", "attachment_point", "Glowing gills and spots (G18). Shared material; per-individual values in glow_individuals.")
    return list(out.values())


def build_bats(col, P) -> Asset:
    spec = L.BAT_FLOCK
    root = empty(spec["id"], col, spec["center"], size=0.8)
    motion = empty(f"{spec['id']}_Motion", col, parent=root, size=0.6)
    a = Asset(spec["id"], "gimmick", root, origin_policy="hinge_pivot", notes="Small bat flock; the root is the flight centre (G19).",
              gimmicks=("G19",))
    a.part(motion, "motion_root", "hinge_pivot", "Flock motion centre: circle about local Z within the recorded flight range.")
    r0, r1 = spec["radius_range"]
    for i in range(spec["count"]):
        ang = 360.0 * i / spec["count"] + 11.0
        rad = r0 + (r1 - r0) * ((i * 3) % spec["count"]) / max(1, spec["count"] - 1)
        z = 0.35 * math.sin(i * 1.9)
        loc = (rad * math.cos(math.radians(ang)), rad * math.sin(math.radians(ang)), z)
        bat = props.build_bat(col, P, f"{spec['id']}_Bat{i + 1:02d}", motion, loc, ang)
        a.part(bat["root"], "motion_root", "hinge_pivot", "Individual bob and heading (faces local +Y, the flight direction).")
        a.part(bat["body"], "visual_root", "ground_center")
        for side in ("L", "R"):
            piv, wing = bat["wings"][side]
            a.part(piv, "motion_root", "hinge_pivot", f"Wing {side} shoulder.")
            a.part(wing, "visual_root", "hinge_pivot")
            a.motions.append({"pivot": piv, "visual": wing, "gimmick_id": "G19", "motion_type": "oscillation", "axis": "Y", "range": (-35.0, 35.0, "deg"),
                              "samples": [-35, 0, 35], "notes": "Flap about the shoulder (pivot-local Y = the bat's forward axis)."})
    a.extra["flight_range"] = {"center_world": list(spec["center"]), "radius_m": spec["flight_radius_m"], "vertical_m": spec["flight_vertical_m"],
                               "notes": "Keep the flock within this cylinder (P3). Bats circle about the Motion pivot and bob +-0.25 m each."}
    a.motions.append({"pivot": motion, "visual": None, "gimmick_id": "G19", "motion_type": "path_follow", "axis": "Z", "range": (0.0, 360.0, "deg"),
                      "samples": "flock", "notes": "Circle the flock about the flight centre; add +-0.8 m vertical drift."})
    return register(a)


def build_structures(col, P) -> list[Asset]:
    out = []
    for w in L.WALKS:
        loc, rz, length = structures.walk_frame(w["p0"], w["p1"])
        mb = structures.boardwalk(P, length, L.WALK_W, L.DECK_Z, w["ramp"], w["openings"])
        obj = mb.to_object(w["id"], col, loc, (0.0, 0.0, rz))
        out.append(register(Asset(w["id"], "architecture", obj, notes=w["notes"], collider="box")))
    b = L.POND_BRIDGE
    loc, rz, length = structures.walk_frame(b["p0"], b["p1"])
    obj = structures.pond_bridge(P, length, b["width"], b["rise"]).to_object(b["id"], col, loc, (0.0, 0.0, rz))
    out.append(register(Asset(b["id"], "architecture", obj, notes="Arched footbridge over the pond with 1.05 m handrails (crest +0.42 m).",
                              collider="mesh_static")))
    cx, cy = L.POND["center"]
    bridge_local_x = L.POND_BRIDGE["p0"][0] - cx
    rim = structures.pond_rim(P, bridge_local_x).to_object("EFR_Pond_001", col, (cx, cy, 0.0))
    water = structures.pond_water(P).to_object("EFR_Pond_001_Water", col, parent=rim)
    pond = Asset("EFR_Pond_001", "terrain", rim, notes="Shallow pond: water surface 0.07 m above the ground, no drop; stones left out under the bridge.",
                 collider="box")
    pond.part(water, "visual_root", "ground_center", "Water surface (separate for shader or ripple effects).")
    out.append(register(pond))
    lx, ly = L.LOOKOUT["center"]
    obj = structures.lookout(P).to_object(L.LOOKOUT["id"], col, (lx, ly, 0.0))
    out.append(register(Asset(L.LOOKOUT["id"], "architecture", obj, collider="mesh_static",
                              notes="Lookout deck (0.75 m) with ramps, 1.05 m railings, witch-hat roof, lantern and telescope.")))
    rx, ry = L.REST_SPOT["center"]
    obj = structures.rest_deck(P).to_object(L.REST_SPOT["id"], col, (rx, ry, 0.0))
    out.append(register(Asset(L.REST_SPOT["id"], "architecture", obj, collider="box", notes="Round rest deck (0.20 m) under the giant mushroom.")))
    mesh = props.gate_pillar_mesh(P)
    objs = [mesh_object(g["id"], col, mesh, (g["position"][0], g["position"][1], 0.0), (0.0, 0.0, g["rotation_z_deg"])) for g in L.GATE_PILLARS]
    a = Asset(objs[0].name, "lighting", objs[0], collider="convex_hull", notes="Entrance pillar stump with a hanging lantern and a sign (frames the main road).")
    register(a)
    add_instance(a, objs[1])
    out.append(a)
    return out


def _dedup_materials() -> None:
    suffix = re.compile(r"^(.+)\.[0-9]{3}$")
    for mesh in bpy.data.meshes:
        for i, m in enumerate(mesh.materials):
            if m is None:
                continue
            hit = suffix.match(m.name)
            if hit:
                base = bpy.data.materials.get(hit.group(1))
                if base is not None:
                    mesh.materials[i] = base
                else:
                    m.name = hit.group(1)
    for m in list(bpy.data.materials):
        if suffix.match(m.name):
            bpy.data.materials.remove(m, do_unlink=True)


def place_common(col) -> list[dict]:
    common_blend = PROJECT_ROOT / "blender" / "common" / "common.blend"
    placed = []
    for inst, cid, pos, rz, role in L.COMMON:
        if pos is None:
            pos = L.rest_bench_position(rz)
            rz = L.facing_rz(rz)
        obj = append_common_part(common_blend, cid, inst, col, location=pos, rotation_euler_deg=(0.0, 0.0, rz))
        placed.append({"obj": obj, "common_asset_id": cid, "role": role})
    _dedup_materials()
    return placed


# =============================================================================== motion envelopes
def _axis_vec(axis: str) -> Vector:
    sign = -1.0 if axis.startswith("-") else 1.0
    return Vector({"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[axis[-1]]) * sign


def motion_envelope(m: dict, root) -> dict:
    piv = m["pivot"]
    rest = piv.matrix_basis.copy()
    pts: list[Vector] = []
    try:
        if m["samples"] == "flock":
            objs = tree_objects(piv)
            base = world_points(objs)
            c = piv.matrix_world.translation
            rad = max(math.hypot(p.x - c.x, p.y - c.y) for p in base) + 0.35  # + wing tip at full flap
            zmin = min(p.z for p in base) - L.BAT_FLOCK["flight_vertical_m"] - 0.6
            zmax = max(p.z for p in base) + L.BAT_FLOCK["flight_vertical_m"] + 0.6
            return {"min": [_r(c.x - rad), _r(c.y - rad), _r(zmin)], "max": [_r(c.x + rad), _r(c.y + rad), _r(zmax)]}, None
        samples = m["samples"] or [0.0]
        for ang in samples:
            piv.matrix_basis = rest @ Matrix.Rotation(math.radians(ang), 4, _axis_vec(m["axis"]))
            bpy.context.view_layer.update()
            pts.extend(world_points(tree_objects(piv)))
    finally:
        piv.matrix_basis = rest
        bpy.context.view_layer.update()
    return aabb(pts), aabb(pts, z_max=L.WALK_CLEAR_Z)


# =============================================================================== zones and checks
def walk_corridors() -> list[dict]:
    hw = L.WALK_W / 2.0
    out = []

    def box(p0, p1, zlo, zhi):
        return {"min": [_r(min(p0[0], p1[0]) - (hw if p0[0] == p1[0] else 0.0)), _r(min(p0[1], p1[1]) - (hw if p0[1] == p1[1] else 0.0)), _r(zlo)],
                "max": [_r(max(p0[0], p1[0]) + (hw if p0[0] == p1[0] else 0.0)), _r(max(p0[1], p1[1]) + (hw if p0[1] == p1[1] else 0.0)), _r(zhi)]}

    connects = {
        "EFR_WalkNorth_001": ["EFR_PondBridge_001", "EFR_Lookout_001"],
        "EFR_WalkWest_001": ["EFR_Lookout_001", "EFR_RestSpot_001"],
        "EFR_WalkSouth_001": ["EFR_RestSpot_001", "EFR_WalkSouthSpur_001"],
        "EFR_WalkSouthSpur_001": ["EFR_WalkSouth_001"],
        "EFR_WalkPondSpur_001": ["EFR_PondBridge_001"],
    }
    for w in L.WALKS:
        out.append({"id": w["id"], "kind": "walkway", "p0": w["p0"], "p1": w["p1"], "deck_z": L.DECK_Z,
                    "corridor": box(w["p0"], w["p1"], 0.0, L.DECK_Z + L.WALK_CLEAR_Z - 0.2), "owners": [w["id"]] + connects[w["id"]]})
    b = L.POND_BRIDGE
    out.append({"id": b["id"], "kind": "bridge", "p0": b["p0"], "p1": b["p1"], "deck_z": L.DECK_Z + b["rise"],
                "corridor": box(b["p0"], b["p1"], 0.0, L.DECK_Z + b["rise"] + L.WALK_CLEAR_Z - 0.2),
                "owners": [b["id"], "EFR_WalkPondSpur_001", "EFR_WalkNorth_001", "EFR_Pond_001"]})
    for key, rid in (("ramp_east", "EFR_LookoutRampEast"), ("ramp_south", "EFR_LookoutRampSouth")):
        r = L.LOOKOUT[key]
        out.append({"id": rid, "kind": "slope", "p0": r["p0"], "p1": r["p1"], "deck_z": L.LOOKOUT_DECK_Z,
                    "corridor": box(r["p0"], r["p1"], 0.0, L.LOOKOUT_DECK_Z + L.WALK_CLEAR_Z - 0.2),
                    "owners": [L.LOOKOUT["id"], "EFR_WalkNorth_001", "EFR_WalkWest_001"]})
    return out


def viewpoints() -> list[dict]:
    lx, ly = L.LOOKOUT["center"]
    sx, sy = L.LOOKOUT["size"]
    rx, ry = L.REST_SPOT["center"]
    rr = L.REST_SPOT["radius"]
    return [
        {"id": "EFR_View_Lookout", "bounds": {"min": [_r(lx - sx / 2), _r(ly - sy / 2), L.LOOKOUT_DECK_Z], "max": [_r(lx + sx / 2), _r(ly + sy / 2), _r(L.LOOKOUT_DECK_Z + 2.1)]},
         "owners": [L.LOOKOUT["id"], "EFR_LookoutBench_001"], "notes": "Lookout deck: view west over the cliff and the floating islets."},
        {"id": "EFR_View_RestSpot", "bounds": {"min": [_r(rx - rr), _r(ry - rr), L.REST_DECK_Z], "max": [_r(rx + rr), _r(ry + rr), _r(L.REST_DECK_Z + 2.1)]},
         "owners": [L.REST_SPOT["id"], "EFR_WalkWest_001", "EFR_WalkSouth_001", "EFR_MushroomGiant_001", "EFR_RestBench_001", "EFR_RestBench_002", "EFR_RestBench_003", "EFR_Pumpkin_003"],
         "notes": "Rest deck under the giant mushroom (benches face outward)."},
        {"id": "EFR_View_Forecourt", "bounds": {"min": [-34.6, -1.9, 0.0], "max": [-29.0, 1.9, 2.8]},
         "owners": [], "notes": "Main road end in front of the tower: the place to watch the clock and the bell."},
    ]


def exclusions() -> list[dict]:
    return [
        {"zone_id": "EFR_Excl_MainRoad", "bounds": {"min": [-34.6, -1.9, 0.0], "max": [-20.0, 1.9, 2.8]}, "allowed": [],
         "reason": "W01 main road Route_West_Forest_Bridge (3.8 m) from the east entrance to the tower stairs stays clear."},
        {"zone_id": "EFR_Excl_SightLine", "bounds": {"min": [-34.6, -1.9, 0.0], "max": [-20.0, 1.9, 8.0]}, "allowed": [],
         "reason": "W01 LOS_CentralPlaza_To_WestForest (corridor 3.8 m) towards the clock tower stays open overhead too."},
        {"zone_id": "EFR_Excl_EastEntrance", "bounds": {"min": [-22.0, -2.0, 0.0], "max": [-20.0, 2.0, 2.8]}, "allowed": [],
         "reason": "Conn_E_East_Main / Ent_E_East at (-20, 0): bridge mouth between the cliff walls."},
        {"zone_id": "EFR_Excl_NorthLanding", "bounds": {"min": [-23.6, 14.4, 0.0], "max": [-20.4, 17.6, 2.8]}, "allowed": [],
         "reason": "Conn_E_North_Side at (-22, 16): NW side-bridge landing (2.6 m)."},
        {"zone_id": "EFR_Excl_SouthLanding", "bounds": {"min": [-23.6, -17.6, 0.0], "max": [-20.4, -14.4, 2.8]}, "allowed": [],
         "reason": "Conn_E_South_Side at (-22, -16): SW side-bridge landing (2.6 m)."},
        {"zone_id": "EFR_Excl_TowerStairs", "bounds": {"min": [-35.2, -1.2, 0.0], "max": [-34.6, 1.2, 2.8]}, "allowed": ["EFR_ClockTower_001"],
         "reason": "Foot of the tower stairs (M07 front) stays reachable from the road."},
    ]


def run_checks(placements: list[dict], motions: list[dict], corridors: list[dict], views: list[dict], zones: list[dict]) -> list[str]:
    area = {"min": list(L.AREA_BOUNDS["min"]), "max": list(L.AREA_BOUNDS["max"])}
    errs = []
    for p in placements:
        name = p["instance_name"]
        if not inside(p["footprint_world"], area):
            errs.append(f"{name}: outside area bounds {p['footprint_world']}")
        for z in zones:
            fp = p["footprint_world"] if z["bounds"]["max"][2] > L.WALK_CLEAR_Z + 0.01 else p["footprint_low_world"]
            if name not in z["allowed"] and overlaps(fp, z["bounds"]):
                errs.append(f"{name}: intrudes {z['zone_id']}")
        for c in corridors:
            if name not in c["owners"] and overlaps(p["footprint_low_world"], c["corridor"]):
                errs.append(f"{name}: intrudes walkway {c['id']}")
        for v in views:
            if name not in v["owners"] and overlaps(p["footprint_low_world"], v["bounds"]):
                errs.append(f"{name}: intrudes viewpoint {v['id']}")
    for m in motions:
        if not inside(m["envelope_world"], area):
            errs.append(f"{m['part_name']}: motion envelope outside area bounds")
        for c in corridors + [{"id": v["id"], "corridor": v["bounds"]} for v in views] + [{"id": z["zone_id"], "corridor": z["bounds"]} for z in zones]:
            if overlaps(m["envelope_world"], c["corridor"]):
                errs.append(f"{m['part_name']}: motion envelope intrudes {c['id']}")
    return errs


# =============================================================================== data files
def asset_entry(a: Asset) -> dict:
    root = a.root
    inv = root.matrix_world.inverted()
    objs = tree_objects(root)
    local_pts = [inv @ p for p in world_points(objs)]
    bounds = aabb(local_pts)
    metrics, mats = mesh_metrics(objs)
    names = {o.name for o in objs}
    parts = []
    for obj, role, op, notes in a.parts:
        entry = {"part_id": obj.name, "role": role, "parent_part": obj.parent.name if obj.parent is not None and obj.parent.name in names and obj is not root else None,
                 "origin_policy": op, "pivot_local": _vec(inv @ obj.matrix_world.translation)}
        if notes:
            entry["notes"] = notes
        parts.append(entry)
    motion = []
    for m in a.motions:
        env, env_low = motion_envelope(m, root)
        piv = m["pivot"]
        axis_world = (piv.matrix_world.to_3x3() @ _axis_vec(m["axis"])).normalized()
        lo, hi, unit = m["range"]
        motion.append({
            "part_name": piv.name, "visual_part": m["visual"].name if m["visual"] is not None else None, "gimmick_id": m["gimmick_id"],
            "motion_type": m["motion_type"], "pivot_local": _vec(inv @ piv.matrix_world.translation), "pivot_world": _vec(piv.matrix_world.translation),
            "axis": m["axis"], "axis_frame": "pivot local (Blender)", "axis_world": _vec(axis_world),
            "range": {"min": lo, "max": hi, "unit": unit},
            "rest_pose": {"position": _vec(piv.location), "rotation_euler_deg": _vec(math.degrees(c) for c in piv.rotation_euler), "scale": [1.0, 1.0, 1.0]},
            "envelope_world": env, "envelope_low_world": env_low, "notes": m["notes"],
        })
    attachments = [{"name": t["name"], "purpose": t["purpose"], "local_position": _vec(inv @ t["obj"].matrix_world.translation),
                    "world_position": _vec(t["obj"].matrix_world.translation), "gimmick_or_interaction_id": t["gimmick"]} for t in a.attachments]
    extra = {}
    for k, v in a.extra.items():
        if k == "glow_individuals":
            v = [{kk: vv for kk, vv in g.items() if kk != "obj"} | {"attach_world": _vec(g["obj"].matrix_world.translation)} for g in v]
        extra[k] = v
    dims = [round(bounds["max"][i] - bounds["min"][i], 4) for i in range(3)]
    slot = None
    if a.replacement_slot is not None:
        body = bpy.data.objects[a.replacement_slot["visual_root_part"]]
        bb = aabb([inv @ p for p in world_points([body])])
        slot = dict(a.replacement_slot)
        slot["placeholder_bounds_local"] = bb
        slot["placeholder_dimensions_m"] = [round(bb["max"][i] - bb["min"][i], 4) for i in range(3)]
    return {
        "asset_id": a.asset_id, "key": KEY, "category": a.category, "area_id": KEY, "collection": KEY,
        "blend_file": BLEND_REL_PATH, "script_file": SCRIPT_REL_PATH, "version": VERSION,
        "origin_policy": a.origin_policy, "origin_world": _vec(root.matrix_world.translation),
        "rotation_euler_deg": _vec(math.degrees(c) for c in root.rotation_euler), "forward_axis_local": "+Y", "up_axis": "+Z", "unit": "m",
        "dimensions_m": {"width": dims[0], "depth": dims[1], "height": dims[2]}, "bounds_local": bounds,
        "parts": parts,
        "hierarchy": {"asset_root": root.name, "motion_roots": [p["part_id"] for p in parts if p["role"] == "motion_root"],
                      "visual_roots": [p["part_id"] for p in parts if p["role"] == "visual_root"],
                      "attachment_points": [p["part_id"] for p in parts if p["role"] == "attachment_point"]},
        "materials": mats, "textures": [], "metrics": metrics,
        "export_result": {"status": "unexported", "bundle_dir": None, "apply_plan": None, "report_file": None},
        "replacement": {"is_placeholder": a.placeholder, "modifiable": True, "notes": a.notes, "future_target": None},
        "replacement_slot": slot, "collider_policy": a.collider, "gimmick_ids": a.gimmicks,
        "motion": motion, "attachment_details": attachments,
        "instances": [{"name": o.name, "position": _vec(o.matrix_world.translation), "rotation_z_deg": _r(math.degrees(o.rotation_euler.z))} for o in a.instances],
        "shared_meshes": sorted({o.data.name for o in objs if o.type == "MESH"}),
        "verification_status": "blender_checked; resonite_unverified",
        **extra,
    }


def placement_records(common: list[dict]) -> list[dict]:
    out = []
    tops = [o for o in bpy.data.objects if o.parent is None]
    common_ids = {c["obj"].name: c for c in common}
    for o in sorted(tops, key=lambda x: x.name):
        objs = tree_objects(o)
        pts = world_points(objs)
        fp = aabb(pts)
        low = aabb(pts, z_max=L.WALK_CLEAR_Z)
        meta = PLACEMENT_META.get(o.name)
        if o.name in common_ids:
            c = common_ids[o.name]
            asset_id, key, cat, role = c["common_asset_id"], "common", "lighting" if "Lamp" in c["common_asset_id"] or "Lantern" in c["common_asset_id"] else "prop", c["role"]
        else:
            asset_id, key, cat, role = meta["asset_id"], KEY, meta["category"], meta["role"]
        pos = o.matrix_world.translation
        clear = 0.0
        if low is not None:
            clear = max(math.hypot(x - pos.x, y - pos.y) for x in (low["min"][0], low["max"][0]) for y in (low["min"][1], low["max"][1]))
        out.append({
            "placement_id": "EFR_Place_" + o.name.removeprefix("EFR_"), "asset_id": asset_id, "instance_name": o.name, "source_key": key, "category": cat,
            "position": _vec(pos), "rotation_euler_deg": _vec(math.degrees(c) for c in o.rotation_euler), "scale": [1.0, 1.0, 1.0],
            "forward_axis": "+Y", "origin_policy": "hinge_pivot" if o.name == L.BAT_FLOCK["id"] else "ground_center",
            "clearance_radius_m": _r(clear), "dimensions_m": [_r(fp["max"][i] - fp["min"][i]) for i in range(3)],
            "footprint_world": fp, "footprint_low_world": low, "role": role,
        })
    return out


def write_data(placements, motions_flat, corridors, views, zones, common, violations) -> None:
    manifest = {"schema_version": "1.0", "key": KEY, "updated_at": UPDATED_AT, "assets": [asset_entry(a) for a in ASSETS]}
    (PROJECT_ROOT / MANIFEST_REL_PATH).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    world_layout = json.loads((PROJECT_ROOT / "layout" / "world_layout.json").read_text(encoding="utf-8"))
    area = next(a for a in world_layout["areas"] if a["area_id"] == KEY)
    hero = []
    for a in manifest["assets"]:
        if a["motion"] or a.get("glow_individuals"):
            hero.append({"asset_id": a["asset_id"], "gimmick_ids": a["gimmick_ids"], "motion_roots": a["hierarchy"]["motion_roots"],
                         "visual_roots": a["hierarchy"]["visual_roots"], "attachment_points": a["hierarchy"]["attachment_points"],
                         "interaction_notes": a["replacement"]["notes"]})
    tower_dial = CT.DIAL_CENTRE
    tx, ty, _ = L.CLOCK_TOWER["position"]
    dial_world = (tx + tower_dial[1], ty - tower_dial[0], tower_dial[2])  # rotation_z -90: local +Y -> world +X
    data = {
        "schema_version": "1.0", "area_id": KEY, "key": KEY, "area_code": "E",
        "name": "西・魔法の森 (Enchanted Forest & Magical Clock Tower)",
        "theme": "Cute, lively and a little mysterious night forest: glowing mushrooms, a face tree that winks, bats, a shallow glowing pond and the M07 clock tower.",
        "center": area["center"], "bounds": area["bounds"], "bounds_min": area["bounds"]["min"], "bounds_max": area["bounds"]["max"],
        "entrances": area["entrances"],
        "paths": [{"id": c["id"], "kind": c["kind"], "closed": False, "width_m": L.WALK_W, "has_handrail": c["kind"] != "walkway",
                   "waypoints": [[c["p0"][0], c["p0"][1], c["deck_z"]], [c["p1"][0], c["p1"][1], c["deck_z"]]], "corridor_world": c["corridor"],
                   "owners": c["owners"], "connects": [o for o in c["owners"] if o != c["id"]], "gimmick_id": None} for c in corridors],
        "Anchor": {"anchor_id": "EFR_ClockTower_001", "position": list(L.CLOCK_TOWER["position"]), "dimensions_m": list(CT.M07_DIMENSIONS),
                   "orientation_deg": L.CLOCK_TOWER["rotation_z_deg"], "role": "M07 magical clock tower at the end of the west main road; front (dial, stairs) faces east."},
        "Circulation": {"primary_path_id": "Route_West_Forest_Bridge", "min_walk_width_m": L.WALK_W,
                        "entry_points": [c["position"] for c in area["connection_points"]],
                        "loop_description": "Main road -> pond spur and arched bridge -> north boardwalk -> lookout -> west boardwalk behind the tower -> rest spot -> south boardwalk -> south spur -> main road. The NW and SW side bridges land next to the north and south boardwalk ends."},
        "Framing": {"left_edge": "EFR_GatePillar_001 and EFR_FaceTree_001 (north of the road)", "right_edge": "EFR_GatePillar_002 and the south grove",
                    "focal_target": _vec(dial_world), "view_cone_deg": 60.0},
        "Story_Cluster": [
            {"cluster_id": "EFR_Story_Welcome", "position": [-23.0, 4.0, 0.0], "members": ["EFR_GatePillar_001", "EFR_GatePillar_002", "EFR_FaceTree_001"],
             "story": "Lantern stumps and a grinning old tree welcome visitors off the west bridge."},
            {"cluster_id": "EFR_Story_Pond", "position": [-32.0, 7.7, 0.0], "members": ["EFR_Pond_001", "EFR_PondBridge_001", "EFR_MushroomTall_001", "EFR_MushroomMedium_002"],
             "story": "A glowing shallow pond with lilies under an arched bridge."},
            {"cluster_id": "EFR_Story_ClockForecourt", "position": [-32.5, 0.0, 0.0], "members": ["EFR_ClockTower_001", "EFR_ForecourtLamp_001", "EFR_ForecourtLamp_002", "EFR_Pumpkin_001", "EFR_Pumpkin_002"],
             "story": "Watch the hands move and the bell ring from the end of the road."},
            {"cluster_id": "EFR_Story_RestSpot", "position": [-43.2, -12.6, 0.0], "members": ["EFR_RestSpot_001", "EFR_MushroomGiant_001", "EFR_RestBench_001", "EFR_RestBench_002", "EFR_RestBench_003"],
             "story": "Benches under a giant glowing mushroom at the south-west corner."},
            {"cluster_id": "EFR_Story_Lookout", "position": [-44.4, 12.5, 0.0], "members": ["EFR_Lookout_001", "EFR_LookoutBench_001"],
             "story": "A witch-hat lookout with a telescope over the cliff."},
            {"cluster_id": "EFR_Story_Bats", "position": list(L.BAT_FLOCK["center"]), "members": [L.BAT_FLOCK["id"], "EFR_FaceTree_002"],
             "story": "A small bat flock circles above the south grove."},
        ],
        "Common_Placement": [{"placement_id": "EFR_CP_" + c["obj"].name.removeprefix("EFR_"), "common_asset_id": c["common_asset_id"], "instance_name": c["obj"].name,
                              "position": _vec(c["obj"].location), "rotation_euler_deg": _vec(math.degrees(v) for v in c["obj"].rotation_euler), "role": c["role"]}
                             for c in common],
        "Hero_or_Gimmick": hero,
        "Exclusions": [{"zone_id": z["zone_id"], "bounds": z["bounds"], "reason": z["reason"], "allowed": z["allowed"]} for z in zones],
        "viewpoints": views,
        "walk_clearance_z_m": L.WALK_CLEAR_Z,
        "placements": placements,
        "motion_envelopes": [{"asset_id": m["asset_id"], "part_name": m["part_name"], "gimmick_id": m["gimmick_id"], "envelope_world": m["envelope_world"],
                              "envelope_low_world": m["envelope_low_world"]} for m in motions_flat],
        "check_violations": violations,
    }
    (PROJECT_ROOT / LAYOUT_REL_PATH).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# =============================================================================== review renders
class WorldContext:
    """Temporarily append W01 terrain for review renders and remove every appended datablock afterwards."""

    NAMES = ["WLD_WestIsland_001", "WLD_WestBridge_001", "WLD_CliffSafetyWalls_001", "WLD_OuterLoopPaths_001", "WLD_CentralIsland_001",
             "WLD_CentralRingRoad_001", "WLD_NorthPlateau_001", "WLD_SouthIsland_001"]

    def __enter__(self):
        self.before = {k: set(getattr(bpy.data, k).keys()) for k in ("objects", "meshes", "materials", "images")}
        path = PROJECT_ROOT / "blender" / "world" / "world.blend"
        with bpy.data.libraries.load(str(path), link=False) as (src, dst):
            dst.objects = [n for n in self.NAMES if n in src.objects]
        self.col = bpy.data.collections.new("TMP_Review_World")
        bpy.context.scene.collection.children.link(self.col)
        for o in dst.objects:
            if o is not None:
                self.col.objects.link(o)
        return self

    def __exit__(self, *exc):
        for kind in ("objects", "meshes", "materials", "images"):
            coll = getattr(bpy.data, kind)
            for name in set(coll.keys()) - self.before[kind]:
                block = coll.get(name)
                if block is not None:
                    coll.remove(block, do_unlink=True)
        bpy.data.collections.remove(self.col, do_unlink=True)
        for lib in list(bpy.data.libraries):
            bpy.data.libraries.remove(lib)
        return False


class Markers:
    """Temporary pivot/axis markers for the review renders (removed before saving)."""

    def __init__(self, specs: list[tuple[Vector, Vector | None]]):
        self.specs = specs

    def __enter__(self):
        self.mat = bpy.data.materials.new("TMP_Review_Marker")
        self.mat.use_nodes = True
        bsdf = self.mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (1.0, 0.1, 0.4, 1.0)
        bsdf.inputs["Emission Color"].default_value = (1.0, 0.1, 0.4, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 8.0
        self.col = bpy.data.collections.new("TMP_Review_Markers")
        bpy.context.scene.collection.children.link(self.col)
        mb = MeshBuilder()
        for p, axis in self.specs:
            mb.blob(tuple(p), (0.09, 0.09, 0.09), self.mat, subdiv=1, noise=0.0, seed=0)
            if axis is not None:
                mb.tube([p - axis * 0.9, p + axis * 0.9], 0.025, self.mat, segments=6)
        self.obj = mb.to_object("TMP_Review_MarkerSet", self.col)
        return self

    def __exit__(self, *exc):
        mesh = self.obj.data
        bpy.data.objects.remove(self.obj, do_unlink=True)
        bpy.data.meshes.remove(mesh, do_unlink=True)
        bpy.data.materials.remove(self.mat, do_unlink=True)
        bpy.data.collections.remove(self.col, do_unlink=True)
        return False


def render_reviews() -> list[str]:
    out_dir = PROJECT_ROOT / REVIEW_DIR
    obj = bpy.data.objects.get
    bpy.context.view_layer.update()

    def piv(name: str, axis: str | None = None):
        o = obj(name)
        a = None if axis is None else (o.matrix_world.to_3x3() @ _axis_vec(axis)).normalized()
        return (o.matrix_world.translation.copy(), a)

    tower = [piv("EFR_ClockTower_001_HourHandPivot", "-Y"), piv("EFR_ClockTower_001_MinuteHandPivot", "-Y"), piv("EFR_ClockTower_001_BellPivot", "X")]
    face = [piv("EFR_FaceTree_001_BranchLPivot", "Y"), piv("EFR_FaceTree_001_BranchRPivot", "Y"), piv("EFR_FaceTree_001_EyeLPivot", "Z"),
            piv("EFR_FaceTree_001_EyeRPivot", "Z")]
    flock_c = obj(L.BAT_FLOCK["id"]).matrix_world.translation.copy()
    ring = [(flock_c + Vector((L.BAT_FLOCK["flight_radius_m"] * math.cos(a), L.BAT_FLOCK["flight_radius_m"] * math.sin(a), 0.0)), None)
            for a in [i * math.pi / 6 for i in range(12)]]
    bats = [(flock_c, Vector((0.0, 0.0, 1.0)))] + ring + [piv(f"{L.BAT_FLOCK['id']}_Bat01_WingLPivot", "Y")]
    ft = L.FACE_TREES[0]
    fdir = Vector((-math.sin(math.radians(ft["rotation_z_deg"])), math.cos(math.radians(ft["rotation_z_deg"])), 0.0))
    fpos = Vector((ft["position"][0], ft["position"][1], 0.0))
    views = [
        ("01_forest_overview.png", None, (-6.0, -36.0, 30.0), (-34.0, 0.0, 1.0), 26.0),
        ("02_forest_plan.png", None, (-34.0, -21.0, 62.0), (-34.0, 0.5, 0.0), 30.0),
        ("03_clock_tower.png", None, (-24.0, 1.2, 2.0), (-38.5, 0.0, 7.2), 26.0),
        ("04_clock_pivots.png", tower, (-29.0, -1.5, 9.0), (-38.2, 0.0, 9.3), 40.0),
        ("05_face_tree_pivots.png", face, tuple(fpos + fdir * 8.5 + Vector((0.0, 0.0, 3.4))), tuple(fpos + Vector((0.0, 0.0, 4.2))), 32.0),
        ("06_pond_bridge.png", None, (-24.5, 0.5, 4.2), (-32.0, 8.0, 0.4), 30.0),
        ("07_lookout.png", None, (-36.0, 9.0, 4.2), (-44.4, 12.5, 2.0), 30.0),
        ("08_rest_spot.png", None, (-35.0, -11.0, 3.6), (-43.2, -12.6, 1.6), 30.0),
        ("09_bats_pivots.png", bats, (-19.5, -15.0, 7.5), (-28.8, -6.5, 9.6), 38.0),
    ]
    written = []
    with WorldContext():
        for fname, marks, loc, target, lens in views:
            spec = [{"filepath": out_dir / fname, "location": loc, "target": target, "lens_mm": lens}]
            if marks:
                with Markers(marks):
                    render_review_images(spec, width=1280, height=720, samples=24)
            else:
                render_review_images(spec, width=1280, height=720, samples=24)
            written.append(f"{REVIEW_DIR}/{fname}")
    return written


# =============================================================================== main
def main() -> dict:
    reset_scene(KEY)
    props.reset_cache()
    col = bpy.data.collections[KEY]
    P = build_palette()
    ASSETS.clear()
    PLACEMENT_META.clear()

    build_clock_tower(col, P)
    build_face_trees(col, P)
    build_series_trees(col, P)
    build_mushrooms(col, P)
    build_bats(col, P)
    build_structures(col, P)
    common = place_common(col)
    bpy.context.view_layer.update()

    placements = placement_records(common)
    corridors = walk_corridors()
    views = viewpoints()
    zones = exclusions()
    motions_flat = []
    for a in ASSETS:
        for m in a.motions:
            env, env_low = motion_envelope(m, a.root)
            motions_flat.append({"asset_id": a.asset_id, "part_name": m["pivot"].name, "gimmick_id": m["gimmick_id"], "envelope_world": env,
                                 "envelope_low_world": env_low})
    violations = run_checks(placements, motions_flat, corridors, views, zones)

    renders = [] if any("no-render" in a for a in sys.argv) else render_reviews()
    save_blend(PROJECT_ROOT / BLEND_REL_PATH, pack_images=True)
    write_data(placements, motions_flat, corridors, views, zones, common, violations)

    summary = {
        "key": KEY, "blend_file": BLEND_REL_PATH, "objects_count": len(bpy.data.objects), "meshes_count": len(bpy.data.meshes),
        "materials_count": len(bpy.data.materials), "assets": len(ASSETS), "placements": len(placements),
        "triangles": sum(mesh_metrics([o])[0]["triangles"] for o in bpy.data.objects if o.type == "MESH"),
        "violations": violations, "review_images": renders,
    }
    print("E_FOREST_BUILD_SUMMARY:" + json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    main()
