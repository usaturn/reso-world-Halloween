"""Rebuild the finished M05 pumpkin carousel roof and centre casing (W09-M05, #18) from the received Meshy GLBs.

Run in the project directory (``docs/conventions.md`` §7.1):
    resoloop blender run modeling/M05/build.py --json
    (``--arg=--skip-review`` leaves out the review images, for a quick check)

Outputs (``.blend`` and textures are not committed; ``docs/conventions.md`` §8):
- ``blender/M05/M05.blend``: in the collection ``M05``, the empty ``M05_PumpkinCarousel_001`` (asset root: the
  rotation axis at the bottom of the casing) with two children, ``M05_CenterCasing_001`` (at the root) and
  ``M05_Canopy_001`` (on the same axis, ``cap_top_on_axis`` above the root). Each object's origin is on the axis, its
  mesh is placed by W09's decision and its textures are in ``blender/M05/textures/`` (also packed in the ``.blend``)
- ``review/M05/``: ``M05_views.png`` (four sides, 1.8 m figure), ``M05_compare_source.png`` (close-ups, the source on
  the left and the finished asset on the right), ``M05_uv_layout.png`` (UV cover on the colour images: casing on the
  left, roof on the right; uncovered texels are teal),
  ``M05_backface_culled.png`` (six sides of each object with back faces hidden, as Resonite draws a single-sided
  material) and ``checks.json`` (the measurements the acceptance criteria of #18 ask for)
- ``assets/manifest/M05.json`` with ``export_result`` ``unexported``; ``modeling/M05/export.py`` exports, validates
  and records the result

Everything is decided by W09 in ``assets/meshy/received.json`` (rows ``M05_Canopy`` and ``M05_CenterCasing``) and done
by W09's common finishing (``modeling/meshy/finish.py``): placement, naming, texture sizes and the material for
``--pack-pbr``. No reduction (each row's ``budget.triangles_max`` is the source count), the original normals are kept
and both meshes stay single-sided (``double_sided``). No rotation or lift mechanism is made (P3): W05's turn root
carries both objects.
"""

from __future__ import annotations

import argparse
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

import bpy  # type: ignore
import numpy as np
from mathutils import Matrix, Vector  # type: ignore
from mathutils.bvhtree import BVHTree  # type: ignore

from modeling.lib.render import render_review_images
from modeling.lib.scene import reset_scene, save_blend
from modeling.meshy import finish, meshops, metrics

KEY = "M05"
ROOT_ID = "M05_PumpkinCarousel_001"
CASING, CANOPY = "M05_CenterCasing", "M05_Canopy"  # received.json row ids
NAMES = {CASING: "M05_CenterCasing_001", CANOPY: "M05_Canopy_001"}
CAP_POINT = "cap_top_on_axis"  # the casing point the roof origin sits on (received.json split_and_attach)
RECEIVED = PROJECT_ROOT / "assets" / "meshy" / "received.json"
BLEND = PROJECT_ROOT / "blender" / KEY / f"{KEY}.blend"
TEX_DIR = PROJECT_ROOT / "blender" / KEY / "textures"
REVIEW = PROJECT_ROOT / "review" / KEY
MANIFEST = PROJECT_ROOT / "assets" / "manifest" / f"{KEY}.json"
SCRIPT_REL = "modeling/M05/build.py"
# Fringe pendants hang below the roof's ring; anything this far from the axis is outside the hub (radius 1.68 m).
FRINGE_MIN_RADIUS = 2.0
GAP_GRID_STEP = 0.05
CAP_DEPTH = 0.05  # casing vertices this close below the roof base belong to the cap the hub sits on
# W05's placeholders this asset replaces in P2 (``assets/manifest/D_amusement.json``, ``handoff/W05.md`` 7.3).
PLACEHOLDERS = {NAMES[CASING]: "DAM_Carousel_001_M05_CenterCasing", NAMES[CANOPY]: "DAM_Carousel_001_M05_Canopy"}


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_rows() -> dict:
    rows = {r["row_id"]: r for r in json.loads(RECEIVED.read_text(encoding="utf-8"))["assets"]}
    return {CASING: rows[CASING], CANOPY: rows[CANOPY]}


def import_source(path: Path) -> object:
    """Import the GLB into the current scene and return its one mesh object (each confirmed M05 file has one)."""
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


def build_part(row: dict, collection, name: str) -> tuple[object, dict]:
    src = Path(row["source"]["copy_path"])
    if sha256(src) != row["source"]["sha256"]:
        raise SystemExit(f"{src}: SHA-256 differs from received.json")
    obj = import_source(src)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    finish.place(obj, row["decided"])
    obj.name = obj.data.name = name
    if len(obj.data.uv_layers) != 1:
        raise SystemExit(f"{name}: {len(obj.data.uv_layers)} UV maps; expected one")
    obj.data.uv_layers[0].name = "UVMap"
    if len(obj.data.materials) != 1:
        raise SystemExit(f"{name}: {len(obj.data.materials)} materials; expected one")
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    textures = finish.adapt_material(obj.data.materials[0], name, TEX_DIR, row["budget"]["color_px_max"],
                                     row["budget"]["data_px_max"])
    for info in textures.values():
        if "file" in info:
            info["file"] = rel(TEX_DIR.parent / info["file"])
    return obj, textures


# --- measurements -------------------------------------------------------------------------------------------------

def world_vertices(obj) -> np.ndarray:
    m = np.array(obj.matrix_world)
    return meshops.vertex_array(obj) @ m[:3, :3].T + m[:3, 3]


def world_bvh(obj) -> BVHTree:
    m = obj.matrix_world
    return BVHTree.FromPolygons([m @ v.co for v in obj.data.vertices], [tuple(p.vertices) for p in obj.data.polygons])


def r3(values) -> list[float]:
    return [round(float(v), 3) for v in values]


def fit_circle(xy: np.ndarray) -> dict:
    """Least-squares circle (x - a)^2 + (y - b)^2 = r^2 through the points ``xy`` (N x 2)."""
    a = np.column_stack([xy[:, 0], xy[:, 1], np.ones(len(xy))])
    sol, *_ = np.linalg.lstsq(a, -(xy ** 2).sum(axis=1), rcond=None)
    centre = -sol[:2] / 2
    radius = math.sqrt(float(centre @ centre) - float(sol[2]))
    rms = float(np.sqrt(((np.linalg.norm(xy - centre, axis=1) - radius) ** 2).mean()))
    return {"centre_xy": r3(centre), "radius_m": round(radius, 3), "rms_m": round(rms, 4), "points": int(len(xy))}


def part_checks(obj, row: dict) -> dict:
    """The object's own mesh (its local coordinates) against W09's decided bounds."""
    co = meshops.vertex_array(obj)
    lo, hi = co.min(axis=0), co.max(axis=0)
    expected = row["derived"]["bounds_local_m"]
    positions, uv = meshops.triangle_arrays(obj)
    cover = metrics.uv_cover(uv)
    area = metrics.triangle_area_sum(positions)
    color_px = row["budget"]["color_px_max"]
    welded = obj.copy()
    welded.data = obj.data.copy()
    bpy.context.scene.collection.objects.link(welded)
    meshops.weld(welded)
    topo = meshops.topology(welded, float((hi - lo).max()))
    mesh = welded.data
    bpy.data.objects.remove(welded, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return {
        "row_id": row["row_id"],
        "object": obj.name,
        "triangles": len(positions),
        "triangles_max": row["budget"]["triangles_max"],
        "vertices": len(obj.data.vertices),
        "bounds_m": {"min": [round(float(v), 4) for v in lo], "max": [round(float(v), 4) for v in hi]},
        "bounds_expected_m": expected,
        "bounds_max_abs_diff_m": round(float(max(np.abs(lo - expected["min"]).max(),
                                                 np.abs(hi - expected["max"]).max())), 4),
        "dimensions_m": {"width_x": round(float(hi[0] - lo[0]), 3), "depth_y": round(float(hi[1] - lo[1]), 3),
                         "height_z": round(float(hi[2] - lo[2]), 3)},
        "dimensions_expected_m": row["derived"]["dimensions_m"],
        "origin": {"policy": row["decided"]["origin_policy"], "min_z": round(float(lo[2]), 4),
                   "box_centre_xy": [round(float(v), 4) for v in (lo[:2] + hi[:2]) / 2]},
        "object_location": r3(obj.location),
        "object_rotation_scale_identity": bool(np.allclose(np.array(obj.matrix_local)[:3, :3], np.eye(3), atol=1e-9)),
        "uv_cover": round(cover["area_sum"], 4),
        "uv_corners_in_unit_square": round(cover["corners_in_unit_square"], 4),
        "surface_area_m2": round(area, 1),
        "texels_per_m_at_color": round(math.sqrt(cover["area_sum"] * color_px * color_px / area), 1),
        "topology_welded": topo,
    }


def axis_checks(casing, canopy, base_z: float, rows: dict) -> dict:
    """Both rotation axes in the asset frame: circles fitted to the casing's bottom ring and to the roof's hub rim and
    decorated ring (W09 put the roof axis at the ring's centre). They should all be at (0, 0)."""
    cv = world_vertices(casing)
    rv = world_vertices(canopy)
    bottom = cv[cv[:, 2] < 0.03]
    bottom_r = np.linalg.norm(bottom[:, :2], axis=1)
    out = {"casing_bottom_ring": fit_circle(bottom[bottom_r > 0.8 * bottom_r.max()][:, :2])}
    r_xy = np.linalg.norm(rv[:, :2], axis=1)
    hub = rv[(rv[:, 2] < base_z + 0.03) & (r_xy > 1.0)]
    out["canopy_hub_rim"] = fit_circle(hub[:, :2])
    ring_z = base_z + rows[CANOPY]["derived"]["points_local_m"]["fringe_ring_front"][2]
    ring = rv[(np.abs(rv[:, 2] - ring_z) < 0.06) & (r_xy > 4.3) & (r_xy < 4.75)]
    out["canopy_decorated_ring"] = fit_circle(ring[:, :2])
    out["canopy_decorated_ring"]["z_m"] = round(ring_z, 3)
    centres = np.array([v["centre_xy"] for v in out.values()])
    out["max_centre_offset_from_axis_m"] = round(float(np.linalg.norm(centres, axis=1).max()), 4)
    out["max_centre_spread_m"] = round(float(max(np.linalg.norm(a - b) for a in centres for b in centres)), 4)
    out["canopy_origin_world"] = r3(canopy.matrix_world.translation)
    out["casing_origin_world"] = r3(casing.matrix_world.translation)
    return out


def crossings(bvh, origin: Vector, direction: Vector, limit: int = 64) -> int:
    n = 0
    while n < limit:
        loc, _, _, _ = bvh.ray_cast(origin, direction)
        if loc is None:
            break
        n += 1
        origin = loc + direction * 1e-4
    return n


def junction_checks(casing, canopy, base_z: float) -> dict:
    """Where the casing meets the roof: the stem above the roof's base must stay inside the roof, and the hub should sit
    on the cap without air between them."""
    bc, br = world_bvh(casing), world_bvh(canopy)
    up = Vector((0.0, 0.0, 1.0))
    cv = world_vertices(casing)
    above = cv[cv[:, 2] > base_z + 0.005]
    exposed, inside_normal, odd = [], 0, 0
    for p in above:
        o = Vector(p.tolist())
        loc, normal, _, _ = br.ray_cast(o, up)
        if loc is None:
            exposed.append(p)
            continue
        inside_normal += int(normal.dot(up) > 0)
        odd += crossings(br, o, up) % 2
    pairs = bc.overlap(br)
    polys = casing.data.polygons
    m = np.array(casing.matrix_world)
    zs = [float((m @ np.append(np.array(polys[i].center), 1.0))[2]) for i, _ in pairs]
    cap = cv[cv[:, 2] > base_z - CAP_DEPTH]
    cap_radius = float(np.linalg.norm(cap[:, :2], axis=1).max())
    gaps, outside = [], 0
    for x in np.arange(-cap_radius, cap_radius + 1e-9, GAP_GRID_STEP):
        for y in np.arange(-cap_radius, cap_radius + 1e-9, GAP_GRID_STEP):
            if math.hypot(x, y) > cap_radius:
                continue
            top, _, _, _ = bc.ray_cast(Vector((x, y, base_z + 10.0)), -up)
            under, _, _, _ = br.ray_cast(Vector((x, y, base_z - 2.0)), up)
            if top is None or under is None:
                continue
            if top[2] < base_z - CAP_DEPTH:
                outside += 1  # the cap's edge is not round: the ray passed it and fell to the bottom ring
                continue
            gaps.append((math.hypot(x, y), under[2] - top[2]))
    g = np.array(gaps)
    edge = g[g[:, 0] > float(g[:, 0].max()) - 0.1]
    return {
        "roof_base_z": round(base_z, 4),
        "casing_vertices_above_roof_base": int(len(above)),
        "casing_top_z": round(float(cv[:, 2].max()), 4),
        "exposed_above_roof": int(len(exposed)),
        "inside_by_first_hit_normal": inside_normal,
        "inside_by_odd_crossings": odd,
        "overlapping_polygon_pairs": len(pairs),
        "overlap_casing_z_span": [round(min(zs), 3), round(max(zs), 3)] if zs else None,
        "cap_to_hub_gap_grid": {
            "step_m": GAP_GRID_STEP,
            "cap_radius_m": round(cap_radius, 3),
            "points": int(len(g)),
            "points_off_the_cap": outside,
            "max_gap_m": round(float(g[:, 1].max()), 4),
            "points_with_gap_over_1cm": int((g[:, 1] > 0.01).sum()),
            "cap_edge_band_max_gap_m": round(float(edge[:, 1].max()), 4) if len(edge) else None,
            "note": ("vertical lines within the cap's largest radius whose first casing hit from above is the cap (less "
                     "than CAP_DEPTH below the roof base): gap = roof underside z - cap top z; negative where the stem "
                     "goes into the roof; the edge band is the outer 0.1 m of those lines"),
        },
    }


def fringe_checks(canopy, rows: dict, base_z: float) -> dict:
    rv = world_vertices(canopy)
    r_xy = np.linalg.norm(rv[:, :2], axis=1)
    outer = rv[r_xy > FRINGE_MIN_RADIUS]
    k = int(np.argmin(outer[:, 2]))
    low = outer[k]
    w09 = next(s for s in rows[CANOPY]["split_and_attach"] if s["part"] == "垂れ飾り")
    return {
        "lowest_point_outside_hub": r3(low),
        "lowest_point_radius_m": round(float(np.hypot(low[0], low[1])), 3),
        "lowest_z_above_roof_base_m": round(float(low[2] - base_z), 3),
        "lowest_z_above_casing_origin_m": round(float(low[2]), 3),
        "roof_lowest_z_m": round(float(rv[:, 2].min()), 4),
        "w09": w09,
    }


# --- review images ------------------------------------------------------------------------------------------------

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


def review_suns() -> list:
    """``render_review_images`` lights from -Y and high above; the faces are at +Y and the casing stands under a closed
    roof 9.3 m wide. A low sun from the front reaches under the roof's edge, and a weak one from below lights the
    underside a rider looks up at. Both are for the review images only."""
    suns = []
    for name, angle, energy in (("Review_FrontSun", -70.0, 2.5), ("Review_UnderSun", -160.0, 1.0)):
        sun = bpy.data.objects.new(name, bpy.data.lights.new(name, type="SUN"))
        sun.data.energy = energy
        sun.rotation_euler = Matrix.Rotation(math.radians(angle), 4, "X").to_euler()
        bpy.context.scene.collection.objects.link(sun)
        suns.append(sun)
    return suns


def views_sheet(objs: list, tmp: Path) -> Path:
    """Four sides (+Y front, +X, -Y back, -X) of the assembly with a 1.8 m figure off the front-right corner."""
    from modeling.meshy.review_views import add_figure

    co = np.concatenate([world_vertices(o) for o in objs])
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
    for o in figure:
        mesh = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    return grid_sheet([paths[:2], paths[2:]], REVIEW / f"{KEY}_views.png")


CLOSEUPS = [
    # name, camera location, target, lens (asset metres: casing origin at 0, roof base at z 2.964, faces at +Y)
    ("roof_face", (1.0, 11.5, 6.6), (0.0, 3.8, 6.0), 45.0),
    ("roof_fringe", (2.6, 7.4, 3.3), (1.4, 4.4, 3.8), 35.0),
    ("rider_looking_up", (2.4, 1.4, 1.6), (-0.6, 3.2, 3.5), 16.0),
    ("roof_hat", (-2.6, 8.0, 10.2), (0.0, 0.6, 8.3), 35.0),
    ("casing_emblem", (0.4, 3.6, 1.7), (0.0, 0.8, 1.6), 35.0),
    ("casing_cap_and_hub", (1.9, 2.5, 2.2), (0.0, 0.0, 2.9), 28.0),
]


def closeup_views(prefix: str, tmp: Path) -> list[Path]:
    views = [{"filepath": tmp / f"{prefix}_{n}.png", "location": loc, "target": tgt, "lens_mm": lens}
             for n, loc, tgt, lens in CLOSEUPS]
    return render_review_images(views, width=640, height=480, samples=32)


def uv_tile(obj, color_png: Path, out: Path, size: int = 1024) -> tuple[Path, float]:
    """The colour image at ``size`` px with the texels no UV triangle covers darkened."""
    _, uv = meshops.triangle_arrays(obj)
    occupied = metrics.occupancy(uv, (0, 1), (0.0, 0.0), (1.0, 1.0), 1.0 / size)[:size, :size]
    color = read_png(color_png)
    img = bpy.data.images.new("Review_UV", color.shape[1], color.shape[0], alpha=False)
    img.pixels.foreach_set(color.ravel())
    img.scale(size, size)
    px = np.empty(size * size * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    px = px.reshape(size, size, 4)
    px[~occupied, :3] = px[~occupied, :3] * 0.15 + np.array([0.0, 0.55, 0.55]) * 0.85  # teal: unlike orange and purple
    return write_png(px, out), round(float(occupied.mean()), 4)


# backface_check names its views after the Meshy source (its "front" camera is at -Y); these faces are at +Y.
CULLED_TILES = [[("back", "+Y (face)"), ("front", "-Y (back)"), ("right", "+X")],
                [("left", "-X"), ("top", "+Z (top)"), ("bottom", "-Z (bottom)")]]


def backface_sheet(objs: dict, tmp: Path) -> tuple[Path, dict]:
    """Each object alone (the other hidden), since a hidden face is about that object's own shell."""
    result, rows = {}, []
    for name, obj in objs.items():
        others = [o for o in objs.values() if o is not obj]
        for o in others:
            o.hide_render = True
        try:
            result[name] = meshops.backface_check(obj, tmp / f"cull_{name}")
        finally:
            for o in others:
                o.hide_render = False
        result[name]["view_camera_side"] = {view: side for row in CULLED_TILES for view, side in row}
        rows += [[tmp / f"cull_{name}" / f"cull_{view}_1.png" for view, _ in row] for row in CULLED_TILES]
    return grid_sheet(rows, REVIEW / f"{KEY}_backface_culled.png"), result


# --- manifest -----------------------------------------------------------------------------------------------------

def manifest(rows: dict, checks: dict, textures: dict, materials: dict) -> dict:
    parts, base_z = checks["parts"], checks["junction"]["roof_base_z"]
    a = checks["assembly"]
    casing, canopy = NAMES[CASING], NAMES[CANOPY]
    hint = rows[CANOPY]["decided"]["placement_hint"]
    fringe = checks["fringe"]
    return {
        "schema_version": "1.0",
        "key": KEY,
        "updated_at": datetime.datetime.now(datetime.UTC).date().isoformat(),
        "assets": [{
            "asset_id": ROOT_ID,
            "key": KEY,
            "category": "gimmick",
            "area_id": rows[CANOPY]["decided"]["area_id"],
            "collection": KEY,
            "blend_file": rel(BLEND),
            "script_file": SCRIPT_REL,
            "origin_policy": "hinge_pivot",
            "origin_world": [0.0, 0.0, 0.0],
            "placement_hint": {"position": hint["position"], "rotation_z_deg": hint["rotation_z_deg"],
                               "note": rows[CASING]["decided"]["placement_hint"]["note"]},
            "forward_local": "+Y",
            "dimensions_m": {"width": a["dimensions_m"]["width_x"], "depth": a["dimensions_m"]["depth_y"],
                             "height": a["dimensions_m"]["height_z"]},
            "bounds_local": a["bounds_m"],
            "parts": [
                {"part_id": ROOT_ID, "role": "asset_root", "parent_part": None, "origin_policy": "hinge_pivot",
                 "pivot_local": [0.0, 0.0, 0.0]},
                {"part_id": casing, "role": "visual_root", "parent_part": ROOT_ID, "origin_policy": "hinge_pivot",
                 "pivot_local": [0.0, 0.0, 0.0]},
                {"part_id": canopy, "role": "visual_root", "parent_part": ROOT_ID, "origin_policy": "hinge_pivot",
                 "pivot_local": [0.0, 0.0, round(base_z, 4)]},
            ],
            "hierarchy": {"asset_root": ROOT_ID, "motion_roots": [], "visual_roots": [casing, canopy],
                          "attachment_points": []},
            "materials": [materials[CASING], materials[CANOPY]],
            "textures": [info["file"] for t in (textures[CASING], textures[CANOPY]) for info in t.values() if "file" in info],
            "texture_details": {casing: textures[CASING], canopy: textures[CANOPY]},
            "metrics": {"measured": True, "measurement_source": "blender_scene",
                        "triangles": parts[CASING]["triangles"] + parts[CANOPY]["triangles"],
                        "vertices": parts[CASING]["vertices"] + parts[CANOPY]["vertices"],
                        "materials_count": 2, "objects_count": checks["blend_counts"]["objects"],
                        "triangles_by_object": {casing: parts[CASING]["triangles"], canopy: parts[CANOPY]["triangles"]},
                        "budget_triangles_max": {casing: parts[CASING]["triangles_max"],
                                                 canopy: parts[CANOPY]["triangles_max"]}},
            "source": [{"row_id": r["row_id"], "copy_path": r["source"]["copy_path"], "sha256": r["source"]["sha256"]}
                       for r in (rows[CASING], rows[CANOPY])],
            "export_result": {"status": "unexported", "bundle_dir": None, "apply_plan": None, "report_file": None},
            "replacement": {
                "is_placeholder": False,
                "modifiable": True,
                "future_target": None,
                "replaces_placeholder": dict(PLACEHOLDERS),
                "notes": (
                    "Meshy の M05 を仕上げた差し替え用の見た目（Spec §6.3 の VisualRoot に入れる静的なモデル）。"
                    "P2（W08 の後）で W05（#7）のメリーゴーラウンド DAM_Carousel_001 の仮モデルと差し替える（対応は replaces_placeholder。"
                    "W05 の取付点は TurnRoot の下の DAM_Carousel_001_Att_M05_CenterCasing（z 0.19）と DAM_Carousel_001_Att_M05_Canopy（z 3.154））。"
                    f"アセットの原点は回転軸上の柱の底（回転床の上面に置く）。{casing} は原点そのまま、{canopy} は同じ軸の {base_z} m 上が原点（ハブの下面）。"
                    "正面（ジャック・オー・ランタンの顔と柱の紋章）は +Y（Resonite の +Z）。回転・上下動の仕組みは含めず、P3 で W05 の回転床の TurnRoot と一緒に回す。"
                    f"垂れ飾りの最下点は柱の原点から {fringe['lowest_z_above_casing_origin_m']} m。発光とコライダーは含めない"
                ),
            },
        }],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--skip-review", action="store_true")
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    rows = load_rows()
    _, collection = reset_scene(KEY)
    casing, tex_casing = build_part(rows[CASING], collection, NAMES[CASING])
    canopy, tex_canopy = build_part(rows[CANOPY], collection, NAMES[CANOPY])
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)
    cap = rows[CASING]["derived"]["points_local_m"][CAP_POINT]
    base_z = float(cap[2])
    canopy.location = (float(cap[0]), float(cap[1]), base_z)
    root = bpy.data.objects.new(ROOT_ID, None)
    root.empty_display_type = "PLAIN_AXES"
    collection.objects.link(root)
    for o in (casing, canopy):
        o.parent = root
    bpy.context.view_layer.update()

    objs = {CASING: casing, CANOPY: canopy}
    co = np.concatenate([world_vertices(o) for o in objs.values()])
    lo, hi = co.min(axis=0), co.max(axis=0)
    checks = {
        "key": KEY,
        "asset_root": ROOT_ID,
        "parts": {name: part_checks(o, rows[name]) for name, o in objs.items()},
        "assembly": {
            "bounds_m": {"min": r3(lo), "max": r3(hi)},
            "dimensions_m": {"width_x": round(float(hi[0] - lo[0]), 3), "depth_y": round(float(hi[1] - lo[1]), 3),
                             "height_z": round(float(hi[2] - lo[2]), 3)},
            "w09_roof_top_above_casing_origin_m": 9.35,
        },
        "axes": axis_checks(casing, canopy, base_z, rows),
        "junction": junction_checks(casing, canopy, base_z),
        "fringe": fringe_checks(canopy, rows, base_z),
    }
    materials = {name: o.data.materials[0].name for name, o in objs.items()}
    bpy.context.preferences.filepaths.save_version = 0  # no M05.blend1 backup (as finish.py)
    save_blend(BLEND, pack_images=True)
    checks["blend_counts"] = {k: len(getattr(bpy.data, k)) for k in ("objects", "meshes", "materials", "images",
                                                                     "collections")}

    REVIEW.mkdir(parents=True, exist_ok=True)
    review_images = []
    if not args.skip_review:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            suns = review_suns()
            review_images.append(views_sheet(list(objs.values()), tmp))
            finished = closeup_views("finished", tmp)
            tiles, shares = [], {}
            for name, o in objs.items():
                tile, shares[name] = uv_tile(o, TEX_DIR / f"{NAMES[name]}_color.png", tmp / f"uv_{name}.png")
                tiles.append(tile)
            review_images.append(grid_sheet([tiles], REVIEW / f"{KEY}_uv_layout.png"))
            culled, culling = backface_sheet(objs, tmp)
            review_images.append(culled)
            # The sources after everything about the finished objects: same placement, original 4096 images.
            for name, o in objs.items():
                src = import_source(Path(rows[name]["source"]["copy_path"]))
                finish.place(src, rows[name]["decided"])
                src.location = o.matrix_world.translation
                o.hide_render = True
            original = closeup_views("source", tmp)
            review_images.insert(1, grid_sheet([[s, f] for s, f in zip(original, finished)],
                                               REVIEW / f"{KEY}_compare_source.png"))
            for sun in suns:
                bpy.data.objects.remove(sun, do_unlink=True)
        checks["uv_texel_share_1024"] = shares
        checks["backface_check"] = culling

    checks.update({
        "source": {name: {"copy_path": r["source"]["copy_path"], "sha256": r["source"]["sha256"],
                          "copy_sha256_ok": True, "original_path": r["source"]["original_path"],
                          "original_sha256_ok": sha256(Path(r["source"]["original_path"])) == r["source"]["sha256"]}
                   for name, r in rows.items()},
        "budget": {name: r["budget"] for name, r in rows.items()},
        "textures": {NAMES[CASING]: tex_casing, NAMES[CANOPY]: tex_canopy},
        "materials": materials,
        "blender": bpy.app.version_string,
        "review_images": [rel(p) for p in review_images],
        "closeups": [{"name": n, "camera": loc, "target": tgt, "lens_mm": lens} for n, loc, tgt, lens in CLOSEUPS],
    })
    (REVIEW / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest(rows, checks, {CASING: tex_casing, CANOPY: tex_canopy}, materials),
                                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"blend": rel(BLEND), "triangles": {n: c["triangles"] for n, c in checks["parts"].items()},
                      "assembly": checks["assembly"], "axes_max_offset": checks["axes"]["max_centre_offset_from_axis_m"],
                      "junction": checks["junction"], "fringe_lowest": checks["fringe"]["lowest_z_above_casing_origin_m"],
                      "counts": checks["blend_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
