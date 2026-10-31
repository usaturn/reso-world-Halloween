"""Rebuild the finished M06 ghost train engine shell (W09-M06, #19) from the received Meshy GLB.

Run in the project directory (``docs/conventions.md`` §7.1):
    resoloop blender run modeling/M06/build.py --json
then ``uv run python modeling/M06/export.py`` for the export and validate (a rebuild resets ``export_result``).

Outputs (``.blend`` and textures are not committed; ``docs/conventions.md`` §8):
- ``blender/M06/M06.blend`` with one object ``M06_GhostTrainEngine_001`` in the collection ``M06``, and its textures
  in ``blender/M06/textures/`` (also packed in the ``.blend``)
- ``review/M06/``: ``M06_views.png`` (four sides, 1.8 m figure), ``M06_w05_fit.png`` (the engine on W05's rails with
  W05's wheels: side and front, low), ``M06_compare_source.png`` (close-ups, the placed source on the left and the
  finished asset on the right), ``M06_uv_layout.png`` (UV cover on the colour image), ``M06_backface_culled.png``
  (six sides with back faces hidden, as Resonite draws a single-sided material) and ``checks.json`` (the
  measurements the acceptance criteria of #19 ask for)
- ``assets/manifest/M06.json`` (``export_result`` is ``unexported``; ``export.py`` fills it)

W09 decided everything in ``assets/meshy/received.json`` (row ``M06``) and W09's common finishing does it
(``modeling/meshy/finish.py``): placement (origin between the wheel arches on the ground plane, +Y = travel
direction), naming, texture sizes (colour 1024, data maps 512) and the material for ``--pack-pbr``. No reduction,
the original normals are kept and the mesh stays single-sided (``double_sided``). Wheels, passenger car, track and
smoke are not part of this asset (W05 has the wheels and the car; ``split_and_attach``).

Two edits of the mesh, both allowed by W09:
- the two floating slivers (1-2 triangles each, ``measured.topology``) are deleted (``docs/meshy-intake.md`` §2)
- the cowcatcher's lower edge is lifted by ``LIFT`` m: W05 put the rail top at the engine's origin height and the
  cowcatcher (1.07 m wide, wider than the 0.69 m between the rails) reaches that plane, touching the rails
  (``split_and_attach``: "重なるなら W09-M06 が排障器の下端を少し上げる"). The lift fades out linearly up to
  ``LIFT_BAND`` m, so nothing above that height moves. ``checks.json`` records the clearance along W05's loop.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import bmesh  # type: ignore
import bpy  # type: ignore
import numpy as np
from mathutils import Matrix, Vector, kdtree  # type: ignore
from mathutils.bvhtree import BVHTree  # type: ignore

from modeling.D_amusement import layout_data as w05  # read only: W05's loop (pure Python constants)
from modeling.lib.render import render_review_images
from modeling.lib.scene import reset_scene, save_blend
from modeling.meshy import finish, meshops, metrics

KEY = "M06"
NAME = "M06_GhostTrainEngine_001"
RECEIVED = PROJECT_ROOT / "assets" / "meshy" / "received.json"
W05_MANIFEST = PROJECT_ROOT / "assets" / "manifest" / "D_amusement.json"  # read only (W05's placeholder)
W05_ASSET = "DAM_GhostTrain_001"
W05_SHELL = f"{W05_ASSET}_M06_EngineShell"
BLEND = PROJECT_ROOT / "blender" / KEY / f"{KEY}.blend"
TEX_DIR = PROJECT_ROOT / "blender" / KEY / "textures"
REVIEW = PROJECT_ROOT / "review" / KEY
MANIFEST = PROJECT_ROOT / "assets" / "manifest" / f"{KEY}.json"
BUNDLE = PROJECT_ROOT / "exports" / KEY / "bundle"

FLOATING_SHARE = 0.005  # a piece further than this share of the largest extent from the rest floats (meshops.topology)
LIFT = 0.03  # m: clearance of the cowcatcher over the rail top after the lift
LIFT_BAND = 0.11  # m: the lift fades to 0 at this height (the rest of the underside is at 0.117 m or higher)
COWCATCHER_Y_MIN = 1.40  # m: the lifted vertices are all in front of this (the cowcatcher starts at y = 1.418)

# W05's track and wheels (modeling/D_amusement/assets_rides.py; not in W05's layout constants or manifest)
RAIL_WIDTH = 0.075
GUIDE_HALF_WIDTH = 0.05
GUIDE_TOP_Z = 0.11  # LoopGuide: 0.07 + 0.04 in the track's frame (rail top 0.14)
WHEEL_RADIUS = 0.21
WHEEL_DISC_X = (0.35, 0.45)  # |x| of the two discs of each wheel set
AXLE_RADIUS = 0.045
AXLE_HALF_X = 0.44
POSE_STEP = 0.05  # m along the loop
SAMPLE_DIV = 5  # barycentric subdivisions per triangle for the clearance samples
LOW_Z = 0.6  # m: triangles reaching below this are sampled (cowcatcher, frame, wheel arches)


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_row() -> dict:
    rows = {r["row_id"]: r for r in json.loads(RECEIVED.read_text(encoding="utf-8"))["assets"]}
    return rows[KEY]


def load_w05() -> dict:
    for asset in json.loads(W05_MANIFEST.read_text(encoding="utf-8"))["assets"]:
        if asset["asset_id"] == W05_ASSET:
            return asset
    raise SystemExit(f"{rel(W05_MANIFEST)}: {W05_ASSET} is missing")


def w05_part(w05_asset: dict, suffix: str) -> list[float]:
    name = f"{W05_ASSET}_{suffix}"
    for part in w05_asset["parts"]:
        if part["part_id"] == name:
            return part["pivot_local"]
    raise SystemExit(f"{rel(W05_MANIFEST)}: part {name} is missing")


def import_source(path: Path) -> object:
    """Import the GLB into the current scene and return its one mesh object (the confirmed M06 has one)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    if len(meshes) != 1 or len(new) != 1:
        raise SystemExit(f"{path.name}: expected one mesh object, got {[o.name for o in new]}")
    obj = meshes[0]
    if obj.animation_data or obj.constraints or obj.data.shape_keys or obj.modifiers:
        raise SystemExit(f"{obj.name}: not a static mesh")
    return obj


def bounds(obj) -> dict:
    co = meshops.vertex_array(obj)
    return {"min": [round(float(v), 4) for v in co.min(axis=0)], "max": [round(float(v), 4) for v in co.max(axis=0)]}


def remove_floating(obj) -> list[dict]:
    """Delete the pieces (faces joined by edges after welding) lying further than ``FLOATING_SHARE`` of the largest
    extent from every other piece. The mesh itself is not welded (the UV seams stay)."""
    co = meshops.vertex_array(obj)
    extent = float((co.max(axis=0) - co.min(axis=0)).max())
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    layer = bm.faces.layers.int.new("m06_source_face")
    for i, f in enumerate(bm.faces):
        f[layer] = i
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=meshops.WELD_DISTANCE)
    bm.verts.index_update()
    bm.faces.index_update()
    bm.verts.ensure_lookup_table()
    seen: set[int] = set()
    groups = []
    for face in bm.faces:
        if face.index in seen:
            continue
        stack, group = [face], []
        seen.add(face.index)
        while stack:
            f = stack.pop()
            group.append(f)
            for edge in f.edges:
                for g in edge.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        groups.append(group)
    groups.sort(key=len, reverse=True)
    removed, info = [], []
    for g in groups[1:]:
        own = {v.index for f in g for v in f.verts}
        tree = kdtree.KDTree(len(bm.verts) - len(own))
        for v in bm.verts:
            if v.index not in own:
                tree.insert(v.co, v.index)
        tree.balance()
        gap = min(tree.find(bm.verts[i].co)[2] for i in own)
        if gap <= FLOATING_SHARE * extent:
            continue
        pts = np.array([bm.verts[i].co[:] for i in own])
        removed += [f[layer] for f in g]
        info.append({"triangles": sum(len(f.verts) - 2 for f in g),
                     "centre_m": [round(float(v), 3) for v in (pts.min(axis=0) + pts.max(axis=0)) / 2],
                     "size_m": [round(float(v), 3) for v in pts.max(axis=0) - pts.min(axis=0)],
                     "gap_m": round(float(gap), 4)})
    bm.free()
    if removed:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in removed], context="FACES")
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
    return info


def lift_cowcatcher(obj) -> dict:
    """``z' = z + LIFT * (1 - z / LIFT_BAND)`` for the vertices below ``LIFT_BAND``; all of them must be in front of
    ``COWCATCHER_Y_MIN`` (the cowcatcher), otherwise the band would cut through another part."""
    co = meshops.vertex_array(obj)
    low = co[:, 2] < LIFT_BAND
    outside = low & (co[:, 1] <= COWCATCHER_Y_MIN)
    if outside.any():
        raise SystemExit(f"{int(outside.sum())} vertices below {LIFT_BAND} m behind y={COWCATCHER_Y_MIN}; "
                         "the cowcatcher lift would move another part")
    behind = co[co[:, 1] <= COWCATCHER_Y_MIN]
    z = co[low, 2]
    co[low, 2] = z + LIFT * (1.0 - z / LIFT_BAND)
    obj.data.vertices.foreach_set("co", co.ravel())
    obj.data.update()
    sel = co[low]
    return {"lift_m": LIFT, "band_m": LIFT_BAND, "vertices": int(low.sum()),
            "region_m": {"min": [round(float(v), 3) for v in sel.min(axis=0)],
                         "max": [round(float(v), 3) for v in sel.max(axis=0)]},
            "lowest_z_before_m": round(float(z.min()), 4),
            "lowest_z_after_m": round(float(co[low, 2].min()), 4),
            "lowest_z_behind_region_m": round(float(behind[:, 2].min()), 4)}


def build_asset(row: dict, w05_asset: dict) -> tuple[object, dict, dict]:
    src = Path(row["source"]["copy_path"])
    if sha256(src) != row["source"]["sha256"]:
        raise SystemExit(f"{src}: SHA-256 differs from received.json")
    _, collection = reset_scene(KEY)
    obj = import_source(src)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    finish.place(obj, row["decided"])
    edits = {"placed_bounds_m": bounds(obj), "placed_triangles": meshops.triangles(obj)}
    edits["floating_removed"] = remove_floating(obj)
    axle_half = abs(w05_part(w05_asset, "EngineWheelFront")[1])
    edits["w05_track_before_lift"] = track_clearance(surface_samples(obj, LOW_Z), axle_half)
    edits["cowcatcher"] = lift_cowcatcher(obj)
    obj.name = obj.data.name = NAME
    if len(obj.data.uv_layers) != 1:
        raise SystemExit(f"{NAME}: {len(obj.data.uv_layers)} UV maps; expected one")
    obj.data.uv_layers[0].name = "UVMap"
    if len(obj.data.materials) != 1:
        raise SystemExit(f"{NAME}: {len(obj.data.materials)} materials; expected one")
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    textures = finish.adapt_material(obj.data.materials[0], NAME, TEX_DIR, row["budget"]["color_px_max"],
                                     row["budget"]["data_px_max"])
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)
    for info in textures.values():
        if "file" in info:
            info["file"] = rel(TEX_DIR.parent / info["file"])
    return obj, textures, edits


def surface_samples(obj, below: float) -> np.ndarray:
    """Points on every triangle reaching below ``below`` m (barycentric grid with ``SAMPLE_DIV`` steps)."""
    positions, _ = meshops.triangle_arrays(obj)
    tris = positions.reshape(-1, 3, 3)
    tris = tris[tris[:, :, 2].min(axis=1) < below]
    weights = np.array([(i, j, SAMPLE_DIV - i - j) for i in range(SAMPLE_DIV + 1) for j in range(SAMPLE_DIV + 1 - i)],
                       dtype=float) / SAMPLE_DIV
    return np.einsum("wk,tkd->twd", weights, tris).reshape(-1, 3)


def loop_point(s: np.ndarray) -> np.ndarray:
    """W05's loop centre line (``layout_data.compute_track_loop_waypoints``, track-local XY) at arc length ``s``."""
    r, hy = w05.TRACK_RADIUS_M, w05.TRACK_STRAIGHT_HALF_Y_M
    length = 4 * hy + 2 * math.pi * r
    s = np.mod(s, length)
    out = np.empty((len(s), 2))
    a = s < 2 * hy
    out[a] = np.stack([np.full(a.sum(), -r), -hy + s[a]], axis=1)
    b = (s >= 2 * hy) & (s < 2 * hy + math.pi * r)
    th = math.pi - (s[b] - 2 * hy) / r
    out[b] = np.stack([r * np.cos(th), hy + r * np.sin(th)], axis=1)
    c = (s >= 2 * hy + math.pi * r) & (s < 4 * hy + math.pi * r)
    out[c] = np.stack([np.full(c.sum(), r), hy - (s[c] - 2 * hy - math.pi * r)], axis=1)
    d = s >= 4 * hy + math.pi * r
    th = -(s[d] - 4 * hy - math.pi * r) / r
    out[d] = np.stack([r * np.cos(th), -hy + r * np.sin(th)], axis=1)
    return out


def track_clearance(samples: np.ndarray, axle_half: float) -> dict:
    """Run the engine round W05's loop and measure how far the samples stay above the rails and the LoopGuide.

    The engine origin sits at the rail top (W05's EngineRoot), so the rail top is local z = 0. Two ways to follow the
    loop are tried, as P3 has not chosen one: ``tangent`` (origin on the centre line, +Y along its tangent) and
    ``chord`` (both wheel sets, ``axle_half`` m before and behind the origin, on the centre line)."""
    r, hy = w05.TRACK_RADIUS_M, w05.TRACK_STRAIGHT_HALF_Y_M
    half_gauge = w05.TRACK_RAIL_GAUGE_M / 2
    rail_lo, rail_hi = half_gauge - RAIL_WIDTH / 2, half_gauge + RAIL_WIDTH / 2
    guide_top = GUIDE_TOP_Z - w05.TRACK_RAIL_TOP_Z_M
    length = 4 * hy + 2 * math.pi * r
    poses = np.arange(0.0, length, POSE_STEP)

    def straight(s: float) -> bool:
        return (s % length < 2 * hy) or (2 * hy + math.pi * r <= s % length < 4 * hy + math.pi * r)

    out = {}
    for model in ("tangent", "chord"):
        if model == "tangent":
            origin = loop_point(poses)
            heading = loop_point(poses + 1e-4) - loop_point(poses - 1e-4)
        else:
            front, rear = loop_point(poses + axle_half), loop_point(poses - axle_half)
            origin = (front + rear) / 2
            heading = front - rear
        heading /= np.linalg.norm(heading, axis=1, keepdims=True)
        worst = {"rail": None, "guide": None}
        for i, s in enumerate(poses):
            h = heading[i]
            right = np.array([h[1], -h[0]])
            wx = origin[i, 0] + samples[:, 0] * right[0] + samples[:, 1] * h[0]
            wy = origin[i, 1] + samples[:, 0] * right[1] + samples[:, 1] * h[1]
            offset = np.abs(np.hypot(wx, wy - np.clip(wy, -hy, hy)) - r)
            for kind, mask, top in (("rail", (offset >= rail_lo) & (offset <= rail_hi), 0.0),
                                    ("guide", offset <= GUIDE_HALF_WIDTH, guide_top)):
                if not mask.any():
                    continue
                j = int(np.argmin(np.where(mask, samples[:, 2], np.inf)))
                gap = float(samples[j, 2] - top)
                if worst[kind] is None or gap < worst[kind]["clearance_m"]:
                    worst[kind] = {"clearance_m": round(gap, 4), "pose_s_m": round(float(s), 2),
                                   "on": "straight" if straight(s) else "curve",
                                   "point_local_m": [round(float(v), 3) for v in samples[j]],
                                   "lateral_offset_m": round(float(offset[j]), 3)}
        out[model] = worst
    out["rail_strip_offset_m"] = [round(rail_lo, 4), round(rail_hi, 4)]
    out["guide_top_local_z_m"] = round(guide_top, 3)
    out["poses"] = len(poses)
    return out


def wheel_fit(samples: np.ndarray, wheels: dict) -> dict:
    """W05's wheel sets (two discs and an axle each) against the shell: the smallest gap between a disc rim and the
    shell within the disc's x range, and samples inside a disc or the axle (negative gap = overlap)."""
    out = {}
    ax = np.abs(samples[:, 0])
    for name, (wy, wz) in wheels.items():
        rad = np.hypot(samples[:, 1] - wy, samples[:, 2] - wz)
        in_disc = (ax >= WHEEL_DISC_X[0]) & (ax <= WHEEL_DISC_X[1])
        j = int(np.argmin(np.where(in_disc, rad, np.inf)))
        out[name] = {"centre_local_m": [0.0, wy, wz],
                     "disc_rim_gap_m": round(float(rad[j] - WHEEL_RADIUS), 4),
                     "nearest_point_local_m": [round(float(v), 3) for v in samples[j]],
                     "samples_inside_discs": int((in_disc & (rad < WHEEL_RADIUS)).sum()),
                     "samples_inside_axle": int(((ax <= AXLE_HALF_X) & (rad < AXLE_RADIUS)).sum())}
    return out


def ray_hit(bvh, origin: tuple, direction: tuple) -> dict:
    loc, normal, _, _ = bvh.ray_cast(Vector(origin), Vector(direction), 20.0)
    if loc is None:
        return {"hit": None}
    return {"hit": [round(v, 4) for v in loc], "faces_ray": bool(normal.dot(Vector(direction)) < 0)}


def profile(bvh, x: float, y_from: float, direction: float, z_range: tuple[float, float]) -> list[list[float | None]]:
    """First-hit y of rays along y (``direction`` +1 or -1) at ``x``, every 2 cm in ``z_range``: [z, y or None]."""
    out = []
    for z in np.arange(z_range[0], z_range[1] + 1e-9, 0.02):
        loc, _, _, _ = bvh.ray_cast(Vector((x, y_from, float(z))), Vector((0, direction, 0)), 20.0)
        out.append([round(float(z), 2), round(loc[1], 3) if loc else None])
    return out


def shape_checks(obj, row: dict, w05_asset: dict) -> dict:
    co = meshops.vertex_array(obj)
    lo, hi = co.min(axis=0), co.max(axis=0)
    expected = row["derived"]["bounds_local_m"]
    positions, uv = meshops.triangle_arrays(obj)
    cover = metrics.uv_cover(uv)
    area = metrics.triangle_area_sum(positions)
    color_px = row["budget"]["color_px_max"]
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    points = row["derived"]["points_local_m"]
    coupler = points["rear_coupler_candidate"]
    w05_coupler = w05_part(w05_asset, "Att_CouplerRear")
    headlamp = w05_part(w05_asset, "Att_Headlamp")
    low = co[co[:, 2] < float(lo[2]) + 0.02]  # the cowcatcher's lower edge
    samples = surface_samples(obj, LOW_Z)
    wheels = {"EngineWheelFront": tuple(w05_part(w05_asset, "EngineWheelFront")[1:]),
              "EngineWheelRear": tuple(w05_part(w05_asset, "EngineWheelRear")[1:])}
    welded = obj.copy()
    welded.data = obj.data.copy()
    bpy.context.scene.collection.objects.link(welded)
    meshops.weld(welded)
    topo = meshops.topology(welded, float((hi - lo).max()))
    mesh = welded.data
    bpy.data.objects.remove(welded, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return {
        "triangles": len(positions),
        "vertices": len(obj.data.vertices),
        "bounds_m": {"min": [round(float(v), 4) for v in lo], "max": [round(float(v), 4) for v in hi]},
        "bounds_expected_m": expected,
        "bounds_diff_m": {"min": [round(float(a - b), 4) for a, b in zip(lo, expected["min"])],
                          "max": [round(float(a - b), 4) for a, b in zip(hi, expected["max"])]},
        "dimensions_m": {"width_x": round(float(hi[0] - lo[0]), 3), "depth_y": round(float(hi[1] - lo[1]), 3),
                         "height_z": round(float(hi[2] - lo[2]), 3)},
        "dimensions_expected_m": row["derived"]["dimensions_m"],
        "origin": {"policy": row["decided"]["origin_policy"], "note": row["decided"]["origin_note"],
                   "ground_plane_z": 0.0, "lowest_point_z": round(float(lo[2]), 4),
                   "box_centre_x": round(float(lo[0] + hi[0]) / 2, 4),
                   "wheel_arch_tops_local_m": [points["front_wheel_arch_top"], points["rear_wheel_arch_top"]],
                   "arch_midpoint_y": round((points["front_wheel_arch_top"][1] + points["rear_wheel_arch_top"][1]) / 2, 4)},
        "front": {"local": "+Y", "meaning": row["decided"]["front_meaning"],
                  "cowcatcher_low_vertices_y_range": [round(float(low[:, 1].min()), 3), round(float(low[:, 1].max()), 3)],
                  "lowest_vertex_y": round(float(co[int(np.argmin(co[:, 2])), 1]), 3)},
        "coupler_rear": {"point_local_m": coupler, "w05_attachment_local_m": w05_coupler,
                         "rear_face_hit_from_behind": ray_hit(bvh, (coupler[0], float(lo[1]) - 1.0, coupler[2]), (0, 1, 0)),
                         "rearmost_vertex_m": [round(float(v), 3) for v in co[int(np.argmin(co[:, 1]))]],
                         "rear_profile_x0": profile(bvh, 0.0, float(lo[1]) - 1.0, 1.0, (0.30, 0.62))},
        "headlamp": {"w05_attachment_local_m": headlamp,
                     "front_hit_at_w05_height": ray_hit(bvh, (headlamp[0], float(hi[1]) + 1.0, headlamp[2]), (0, -1, 0)),
                     "front_profile_x0": profile(bvh, 0.0, float(hi[1]) + 1.0, -1.0, (1.20, 1.66))},
        "object_transform_identity": bool(np.allclose(np.array(obj.matrix_world), np.eye(4), atol=1e-9)),
        "uv_cover": round(cover["area_sum"], 4),
        "uv_corners_in_unit_square": round(cover["corners_in_unit_square"], 4),
        "surface_area_m2": round(area, 1),
        "texels_per_m_at_color": round(math.sqrt(cover["area_sum"] * color_px * color_px / area), 1),
        "w05_track": track_clearance(samples, abs(wheels["EngineWheelFront"][0])),
        "w05_wheels": wheel_fit(samples, wheels),
        "topology_welded": topo,
    }


def read_png(path: Path) -> np.ndarray:
    img = bpy.data.images.load(str(path), check_existing=False)
    px = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    out = px.reshape(img.size[1], img.size[0], 4).copy()
    bpy.data.images.remove(img)
    return out


def write_png(data: np.ndarray, out: Path) -> Path:
    """``data`` is H x W x 4 with Blender's bottom-up rows; written as an 8-bit RGB PNG."""
    data = data.copy()
    data[:, :, 3] = 1.0
    h, w = data.shape[:2]
    image = bpy.data.images.new("Review_Sheet", w, h, alpha=False)
    image.pixels.foreach_set(data.astype(np.float32).ravel())
    image.filepath_raw = str(out)
    image.file_format = "PNG"
    bpy.context.scene.render.image_settings.color_mode = "RGB"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save()
    bpy.data.images.remove(image)
    return out


def grid_sheet(rows: list[list[Path]], out: Path, gap: int = 6) -> Path:
    """Tiles of equal size, ``rows[0]`` at the top, separated by a light ``gap``."""
    tiles = [[read_png(p) for p in row] for row in rows]
    h = tiles[0][0].shape[0]
    sep_v = np.full((h, gap, 4), 0.85, dtype=np.float32)
    lines = []
    for row in tiles:
        parts = []
        for i, t in enumerate(row):
            parts += ([sep_v] if i else []) + [t]
        lines.append(np.concatenate(parts, axis=1))
    sep_h = np.full((gap, lines[0].shape[1], 4), 0.85, dtype=np.float32)
    stacked = []
    for i, line in enumerate(reversed(lines)):  # bottom-up rows: the last row goes first
        stacked += ([sep_h] if i else []) + [line]
    return write_png(np.concatenate(stacked, axis=0), out)


def front_sun() -> object:
    """``render_review_images`` lights from -Y; the front is at +Y, so add a front sun (as ``review_views.py``)."""
    sun = bpy.data.objects.new("Review_FrontSun", bpy.data.lights.new("Review_FrontSun", type="SUN"))
    sun.data.energy = 2.5
    sun.rotation_euler = Matrix.Rotation(math.radians(-35), 4, "X").to_euler()
    bpy.context.scene.collection.objects.link(sun)
    return sun


def views_sheet(obj, tmp: Path) -> Path:
    """Four sides (+Y front, +X, -Y back, -X) with a 1.8 m figure off the front-right corner."""
    from modeling.meshy.review_views import add_figure

    co = meshops.vertex_array(obj)
    lo, hi = co.min(axis=0), co.max(axis=0)
    figure = add_figure(float(hi[0]) + 0.6, float(hi[1]) + 0.6, 0.0)
    lens = 85.0
    half_fov = math.atan(18.0 / lens)
    span = {0: (float(lo[0]), float(hi[0]) + 0.85), 1: (float(lo[1]), float(hi[1]) + 0.85)}
    views = []
    for name, direction, across, depth in (("front", (0, 1, 0), 0, 1), ("right", (1, 0, 0), 1, 0),
                                           ("back", (0, -1, 0), 0, 1), ("left", (-1, 0, 0), 1, 0)):
        a0, a1 = span[across]
        extent = max(a1 - a0, float(hi[2])) * 1.08
        centre = np.zeros(3)
        centre[across] = (a0 + a1) / 2
        centre[depth] = (float(lo[depth]) + float(hi[depth])) / 2
        centre[2] = float(hi[2]) / 2
        distance = extent / 2 / math.tan(half_fov) + float(hi[depth] - lo[depth]) / 2
        views.append({"filepath": tmp / f"view_{name}.png", "location": tuple(centre + np.asarray(direction) * distance),
                      "target": tuple(centre), "lens_mm": lens})
    paths = render_review_images(views, width=640, height=640, samples=32)
    remove_objects(figure)
    return grid_sheet([paths[:2], paths[2:]], REVIEW / f"{KEY}_views.png")


def remove_objects(objects: list) -> None:
    for o in objects:
        mesh = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def context_material(name: str, rgb: tuple) -> object:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.6
    bsdf.inputs["Roughness"].default_value = 0.45
    return mat


def add_w05_context(wheels: dict) -> list:
    """Render-only stand-ins of W05's straight rails (top at z = 0), LoopGuide and engine wheel discs."""
    rail = context_material("Review_W05_Rail", (0.35, 0.36, 0.4))
    wheel = context_material("Review_W05_Wheel", (0.75, 0.45, 0.12))
    objs = []
    half_gauge = w05.TRACK_RAIL_GAUGE_M / 2
    for x in (-half_gauge, half_gauge):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, 0.5, -0.0375), scale=(RAIL_WIDTH, 6.0, 0.075))
        objs.append(bpy.context.active_object)
        objs[-1].data.materials.append(rail)
    guide_top = GUIDE_TOP_Z - w05.TRACK_RAIL_TOP_Z_M
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.5, guide_top - 0.02), scale=(2 * GUIDE_HALF_WIDTH, 6.0, 0.04))
    objs.append(bpy.context.active_object)
    objs[-1].data.materials.append(context_material("Review_W05_Guide", (0.8, 0.6, 0.15)))
    for wy, wz in wheels.values():
        for sign in (-1.0, 1.0):
            x = sign * (WHEEL_DISC_X[0] + WHEEL_DISC_X[1]) / 2
            bpy.ops.mesh.primitive_cylinder_add(radius=WHEEL_RADIUS, depth=WHEEL_DISC_X[1] - WHEEL_DISC_X[0],
                                                location=(x, wy, wz), rotation=(0.0, math.pi / 2, 0.0), vertices=32)
            objs.append(bpy.context.active_object)
            objs[-1].data.materials.append(wheel)
    return objs


FIT_VIEWS = [
    # name, camera location, target, lens (local metres; +Y is the front). The rail top is z = 0.
    ("side_low", (3.4, 0.4, 0.07), (0.0, 0.4, 0.3), 30.0),
    ("cowcatcher_gap", (1.25, 1.75, 0.025), (0.0, 1.7, 0.04), 50.0),
    ("front_low", (0.9, 4.3, 0.22), (0.0, 1.6, 0.12), 50.0),
]


def fit_sheet(wheels: dict, tmp: Path) -> Path:
    context = add_w05_context(wheels)
    views = [{"filepath": tmp / f"fit_{n}.png", "location": loc, "target": tgt, "lens_mm": lens}
             for n, loc, tgt, lens in FIT_VIEWS]
    paths = render_review_images(views, width=640, height=480, samples=32)
    remove_objects(context)
    return grid_sheet([paths], REVIEW / f"{KEY}_w05_fit.png")


CLOSEUPS = [
    # name, camera location, target, lens (local metres; +Y is the front, the pumpkin emblem is on -X)
    ("ghost_face", (0.6, 4.3, 1.2), (0.0, 1.35, 1.05), 40.0),
    ("cowcatcher", (1.2, 2.8, 0.45), (0.0, 1.62, 0.2), 40.0),
    ("headlamp_chimney", (1.0, 2.7, 2.2), (0.0, 0.95, 1.65), 45.0),
    ("pumpkin_side", (-2.6, 0.6, 1.05), (-0.55, 0.3, 0.95), 45.0),
    ("cab_rear", (1.5, -3.2, 1.6), (0.0, -0.75, 1.05), 40.0),
]


def closeup_views(prefix: str, tmp: Path) -> list[Path]:
    views = [{"filepath": tmp / f"{prefix}_{n}.png", "location": loc, "target": tgt, "lens_mm": lens}
             for n, loc, tgt, lens in CLOSEUPS]
    return render_review_images(views, width=640, height=480, samples=32)


def uv_layout(obj) -> tuple[Path, float]:
    """The colour image at 1024 px with the texels no UV triangle covers darkened."""
    _, uv = meshops.triangle_arrays(obj)
    size = 1024
    occupied = metrics.occupancy(uv, (0, 1), (0.0, 0.0), (1.0, 1.0), 1.0 / size)[:size, :size]
    color = read_png(TEX_DIR / f"{NAME}_color.png")
    img = bpy.data.images.new("Review_UV", color.shape[1], color.shape[0], alpha=False)
    img.pixels.foreach_set(color.ravel())
    img.scale(size, size)
    px = np.empty(size * size * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    px = px.reshape(size, size, 4)
    px[~occupied, :3] = px[~occupied, :3] * 0.15 + np.array([0.35, 0.0, 0.35]) * 0.85
    return write_png(px, REVIEW / f"{KEY}_uv_layout.png"), round(float(occupied.mean()), 4)


# backface_check names its views after the Meshy source (its "front" camera is at -Y); this asset's front is at +Y.
# Sheet order (camera side): +Y front, -Y back, +X / -X, top, bottom.
CULLED_TILES = [[("back", "+Y (front, ghost)"), ("front", "-Y (back, cab)"), ("right", "+X")],
                [("left", "-X"), ("top", "+Z (top)"), ("bottom", "-Z (bottom)")]]


def backface_sheet(obj, tmp: Path) -> tuple[Path, dict]:
    culling = meshops.backface_check(obj, tmp / "cull")
    culling["view_camera_side"] = {view: side for row in CULLED_TILES for view, side in row}
    sheet = grid_sheet([[tmp / "cull" / f"cull_{view}_1.png" for view, _ in row] for row in CULLED_TILES],
                       REVIEW / f"{KEY}_backface_culled.png")
    return sheet, culling


def manifest(row: dict, checks: dict, textures: dict, w05_asset: dict) -> dict:
    dims = checks["dimensions_m"]
    coupler = checks["coupler_rear"]["point_local_m"]
    hint = row["decided"]["placement_hint"]
    keep = [p["part_id"] for p in w05_asset["parts"]
            if p["part_id"] in (f"{W05_ASSET}_EngineWheelFront", f"{W05_ASSET}_EngineWheelRear", f"{W05_ASSET}_CarRoot_001")]
    return {
        "schema_version": "1.0",
        "key": KEY,
        "updated_at": datetime.datetime.now(datetime.UTC).date().isoformat(),
        "assets": [{
            "asset_id": NAME,
            "key": KEY,
            "category": "prop",
            "area_id": row["decided"]["area_id"],
            "collection": KEY,
            "blend_file": rel(BLEND),
            "script_file": "modeling/M06/build.py",
            "origin_policy": row["decided"]["origin_policy"],
            "origin_world": [0.0, 0.0, 0.0],
            "placement_hint": hint,
            "forward_local": "+Y",
            "dimensions_m": {"width": dims["width_x"], "depth": dims["depth_y"], "height": dims["height_z"]},
            "bounds_local": checks["bounds_m"],
            "parts": [{"part_id": NAME, "role": "asset_root", "parent_part": None,
                       "origin_policy": row["decided"]["origin_policy"], "pivot_local": [0.0, 0.0, 0.0]}],
            "hierarchy": {"asset_root": NAME, "motion_roots": [], "visual_roots": [NAME], "attachment_points": []},
            "coupler_rear": {"local_m": coupler, "w05_attachment": f"{W05_ASSET}_Att_CouplerRear",
                             "rear_face_local_m": checks["coupler_rear"]["rear_face_hit_from_behind"]["hit"],
                             "note": ("形は無い。連結点は W09 の rear_coupler_candidate（後端の張り出しと同じ y、W05 の取付点と同じ）。"
                                      "その高さの後面（梁）は rear_face_local_m なので、連結器の棒を作るならそこから連結点まで。"
                                      "客車側は W05 が合わせる")},
            "materials": [f"MAT_{KEY}_GhostTrainEngine"],
            "textures": [info["file"] for info in textures.values() if "file" in info],
            "metrics": {"measured": True, "measurement_source": "blender_scene", "triangles": checks["triangles"],
                        "vertices": checks["vertices"], "materials_count": 1, "objects_count": 1},
            "export_result": {"status": "unexported", "bundle_dir": None, "apply_plan": None, "report_file": None},
            "replacement": {
                "is_placeholder": False,
                "modifiable": True,
                "future_target": None,
                "replaces_placeholder": {"manifest": rel(W05_MANIFEST), "asset_id": W05_ASSET,
                                         "visual_root_part": W05_SHELL,
                                         "attachment_point": f"{W05_ASSET}_Att_M06_Engine",
                                         "keep_separate_parts": keep},
                "notes": (
                    "Meshy の M06 を仕上げた差し替え用の見た目（Spec §6.3 の VisualRoot に入れる静的なモデル）。P2（W08 の後）で "
                    f"W05 の仮モデル {W05_SHELL}（親 {W05_ASSET}_EngineRoot、取付点 {W05_ASSET}_Att_M06_Engine）と差し替え、"
                    "前後の車輪と客車は W05 の部品を残す。原点は前後の車輪のアーチの中点の真下の接地面（線路の上面、EngineRoot の原点）、"
                    f"正面（進む向き、おばけの顔と排障器）は +Y（Resonite の +Z）。後ろの連結点は {coupler}（形は無い）。"
                    f"排障器の下端は線路に触れないよう {LIFT} m 上げた。発光（前照灯・ランタン・カボチャ）は焼き込まず、"
                    "コライダーも含めない（P2・P3 で Resonite 側に付ける）"
                ),
            },
        }],
    }


def main() -> None:
    row = load_row()
    w05_asset = load_w05()
    obj, textures, edits = build_asset(row, w05_asset)
    checks = shape_checks(obj, row, w05_asset)
    bpy.context.preferences.filepaths.save_version = 0  # no M06.blend1 backup (as finish.py)
    save_blend(BLEND, pack_images=True)
    counts = {k: len(getattr(bpy.data, k)) for k in ("objects", "meshes", "materials", "images", "collections")}

    REVIEW.mkdir(parents=True, exist_ok=True)
    wheels = {"EngineWheelFront": tuple(w05_part(w05_asset, "EngineWheelFront")[1:]),
              "EngineWheelRear": tuple(w05_part(w05_asset, "EngineWheelRear")[1:])}
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        sun = front_sun()
        views = views_sheet(obj, tmp)
        fit = fit_sheet(wheels, tmp)
        finished = closeup_views("finished", tmp)
        uv_image, uv_texel_share = uv_layout(obj)
        culled, culling = backface_sheet(obj, tmp)
        # The source after everything about the finished object: same placement, original 4096 images, no edits.
        source = import_source(Path(row["source"]["copy_path"]))
        finish.place(source, row["decided"])
        obj.hide_render = True
        original = closeup_views("source", tmp)
        compare = grid_sheet([[s, f] for s, f in zip(original, finished)], REVIEW / f"{KEY}_compare_source.png")
        bpy.data.objects.remove(sun, do_unlink=True)

    checks.update({
        "row_id": KEY,
        "object": NAME,
        "source": {"copy_path": row["source"]["copy_path"], "sha256": row["source"]["sha256"],
                   "copy_sha256_ok": True, "original_path": row["source"]["original_path"],
                   "original_sha256_ok": sha256(Path(row["source"]["original_path"])) == row["source"]["sha256"]},
        "edits": edits,
        "budget": row["budget"],
        "textures": textures,
        "uv_texel_share_1024": uv_texel_share,
        "backface_check": culling,
        "blend_counts": counts,
        "blender": bpy.app.version_string,
        "review_images": [rel(p) for p in (views, fit, compare, uv_image, culled)],
        "fit_views": [{"name": n, "camera": loc, "target": tgt, "lens_mm": lens} for n, loc, tgt, lens in FIT_VIEWS],
        "closeups": [{"name": n, "camera": loc, "target": tgt, "lens_mm": lens} for n, loc, tgt, lens in CLOSEUPS],
    })
    (REVIEW / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest(row, checks, textures, w05_asset), ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    track = checks["w05_track"]
    print(f"built {rel(BLEND)}: triangles={checks['triangles']} dims={checks['dimensions_m']} "
          f"uv_cover={checks['uv_cover']} rail_clearance={[track[m]['rail']['clearance_m'] for m in ('tangent', 'chord')]} "
          f"counts={counts}")


if __name__ == "__main__":
    main()
