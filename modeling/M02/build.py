"""Rebuild the finished M02 giant jack-o'-lantern (W09-M02, #15) from the received Meshy GLB.

Run in the project directory (``docs/conventions.md`` §7.1):
    resoloop blender run modeling/M02/build.py --json

Outputs (``.blend`` and textures are not committed; ``docs/conventions.md`` §8):
- ``blender/M02/M02.blend`` with one object ``M02_GiantPumpkin_001`` in the collection ``M02``, and its textures in
  ``blender/M02/textures/`` (also packed in the ``.blend``)
- ``review/M02/``: ``M02_views.png`` (four sides, 1.8 m figure), ``M02_compare_source.png`` (close-ups, the source
  on the left and the finished asset on the right), ``M02_uv_layout.png`` (UV cover on the colour image),
  ``M02_backface_culled.png`` (six sides with back faces hidden, as Resonite draws a single-sided material) and
  ``checks.json`` (the measurements the acceptance criteria of #15 ask for)
- ``assets/manifest/M02.json``; ``export_result`` is ``exported`` when ``exports/M02/bundle`` holds an export

Everything is decided by W09 in ``assets/meshy/received.json`` (row ``M02``) and done by W09's common finishing
(``modeling/meshy/finish.py``): placement, naming, texture sizes (colour 2048, data maps 1024) and the material for
``--pack-pbr``. No reduction (the row's ``budget.triangles_max`` is the source count), the original normals are
kept and the mesh stays single-sided (``double_sided``). The hat stays joined to the body (``split_and_attach``).
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

import bpy  # type: ignore
import numpy as np
from mathutils import Matrix, Vector  # type: ignore
from mathutils.bvhtree import BVHTree  # type: ignore

from modeling.lib.render import render_review_images
from modeling.lib.scene import reset_scene, save_blend
from modeling.meshy import finish, meshops, metrics

KEY = "M02"
NAME = "M02_GiantPumpkin_001"
RECEIVED = PROJECT_ROOT / "assets" / "meshy" / "received.json"
BLEND = PROJECT_ROOT / "blender" / KEY / f"{KEY}.blend"
TEX_DIR = PROJECT_ROOT / "blender" / KEY / "textures"
REVIEW = PROJECT_ROOT / "review" / KEY
MANIFEST = PROJECT_ROOT / "assets" / "manifest" / f"{KEY}.json"
BUNDLE = PROJECT_ROOT / "exports" / KEY / "bundle"
FIGURE_HEIGHT = 1.8
# A ray that first hits the mesh deeper than this share of the extent along its axis went into the hollow inside
# (a face opening). An outer surface, even at a grazing angle, is met within the near half.
DEEP_SHARE = 0.6
RAY_STEP = 0.04
BODY_TOP_Z = 2.95  # below the hat brim (hat_brim_bottom_front z = 3.0), so the rays sample the pumpkin body only


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


def import_source(path: Path) -> object:
    """Import the GLB into the current scene and return its one mesh object (the confirmed M02 has one)."""
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


def build_asset(row: dict) -> tuple[object, dict]:
    src = Path(row["source"]["copy_path"])
    if sha256(src) != row["source"]["sha256"]:
        raise SystemExit(f"{src}: SHA-256 differs from received.json")
    _, collection = reset_scene(KEY)
    obj = import_source(src)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    finish.place(obj, row["decided"])
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
    return obj, textures


def ray_grid(bvh, extent_lo: np.ndarray, extent_hi: np.ndarray, side: str) -> dict:
    """Rays from one side of the box, travelling inward on a ``RAY_STEP`` grid over the body (z below the brim).
    ``deep`` counts first hits deeper than ``DEEP_SHARE`` of the box along the ray: rays that entered the hollow."""
    axis = {"front": 1, "back": 1, "right": 0, "left": 0}[side]
    sign = {"front": 1.0, "back": -1.0, "right": 1.0, "left": -1.0}[side]
    across = 1 - axis
    start = (extent_hi if sign > 0 else extent_lo)[axis] + sign * 1.0
    plane = (extent_hi if sign > 0 else extent_lo)[axis]
    length = float(extent_hi[axis] - extent_lo[axis])
    direction = Vector([0.0, 0.0, 0.0])
    direction[axis] = -sign
    rays = hits = deep = deep_front_facing = 0
    deepest = 0.0
    deep_points = []
    for a in np.arange(extent_lo[across] + RAY_STEP / 2, extent_hi[across], RAY_STEP):
        for z in np.arange(RAY_STEP / 2, BODY_TOP_Z, RAY_STEP):
            origin = Vector([0.0, 0.0, float(z)])
            origin[axis] = float(start)
            origin[across] = float(a)
            rays += 1
            loc, normal, _, _ = bvh.ray_cast(origin, direction, length + 2.0)
            if loc is None:
                continue
            hits += 1
            depth = abs(plane - loc[axis])
            deepest = max(deepest, depth)
            if depth > DEEP_SHARE * length:
                deep += 1
                deep_front_facing += int(normal.dot(direction) < 0)
                deep_points.append(tuple(loc))
    out = {"rays": rays, "hits": hits, "deep_hits": deep, "deep_hits_front_facing": deep_front_facing,
           "deepest_first_hit_m": round(deepest, 3), "deep_threshold_m": round(DEEP_SHARE * length, 3)}
    if deep_points:
        pts = np.asarray(deep_points)
        out["deep_hit_location_span_m"] = {"min": [round(float(v), 2) for v in pts.min(axis=0)],
                                           "max": [round(float(v), 2) for v in pts.max(axis=0)]}
    return out


def front_openings(bvh, hi: np.ndarray, length: float, x: float) -> list[list[float]]:
    """Vertical spans (z, m) at ``x`` where a ray from the front (+Y) goes into the hollow (2 cm steps, z 0..3)."""
    spans: list[list[float]] = []
    for z in np.arange(0.01, 3.0, 0.02):
        loc, _, _, _ = bvh.ray_cast(Vector((x, float(hi[1]) + 1.0, float(z))), Vector((0, -1, 0)), length + 2.0)
        if loc is not None and float(hi[1]) - loc[1] > DEEP_SHARE * length:
            if spans and abs(spans[-1][1] - (z - 0.02)) < 1e-6:
                spans[-1][1] = float(z)
            else:
                spans.append([float(z), float(z)])
    return [[round(a, 2), round(b, 2)] for a, b in spans]


def shape_checks(obj, row: dict) -> dict:
    co = meshops.vertex_array(obj)
    lo, hi = co.min(axis=0), co.max(axis=0)
    expected = row["derived"]["bounds_local_m"]
    positions, uv = meshops.triangle_arrays(obj)
    cover = metrics.uv_cover(uv)
    area = metrics.triangle_area_sum(positions)
    color_px = row["budget"]["color_px_max"]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(obj, depsgraph)
    cavities = {}
    for name in ("eye_left_centre_front", "eye_right_centre_front", "mouth_centre_front"):
        p = row["derived"]["points_local_m"][name]
        loc, normal, _, _ = bvh.ray_cast(Vector((p[0], float(hi[1]) + 1.0, p[2])), Vector((0, -1, 0)), 20.0)
        back, _, _, _ = bvh.ray_cast(Vector((p[0], float(lo[1]) - 1.0, p[2])), Vector((0, 1, 0)), 20.0)
        cavities[name] = {
            "point": p,
            "first_hit_from_front_y": round(loc[1], 3) if loc else None,
            "depth_from_point_m": round(p[1] - loc[1], 3) if loc else None,
            "first_hit_faces_viewer": bool(loc is not None and normal.dot(Vector((0, -1, 0))) < 0),
            "first_hit_from_back_y": round(back[1], 3) if back else None,
            "back_hit_depth_m": round(back[1] - float(lo[1]), 3) if back else None,
            "front_opening_z_spans_at_x": front_openings(bvh, hi, float(hi[1] - lo[1]), p[0]),
        }
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
        "bounds_max_abs_diff_m": round(float(max(np.abs(lo - expected["min"]).max(), np.abs(hi - expected["max"]).max())), 4),
        "dimensions_m": {"width_x": round(float(hi[0] - lo[0]), 3), "depth_y": round(float(hi[1] - lo[1]), 3),
                         "height_z": round(float(hi[2] - lo[2]), 3)},
        "origin": {"policy": row["decided"]["origin_policy"], "min_z": round(float(lo[2]), 4),
                   "box_centre_xy": [round(float(v), 4) for v in (lo[:2] + hi[:2]) / 2]},
        "object_transform_identity": bool(np.allclose(np.array(obj.matrix_world), np.eye(4), atol=1e-9)),
        "uv_cover": round(cover["area_sum"], 4),
        "uv_corners_in_unit_square": round(cover["corners_in_unit_square"], 4),
        "surface_area_m2": round(area, 1),
        "texels_per_m_at_color": round(math.sqrt(cover["area_sum"] * color_px * color_px / area), 1),
        "face_openings": cavities,
        "ray_grid": {side: ray_grid(bvh, lo, hi, side) for side in ("front", "back", "right", "left")},
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
    """``render_review_images`` lights from -Y; the face is at +Y, so add a front sun (as ``review_views.py``)."""
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
    for o in figure:
        mesh = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    return grid_sheet([paths[:2], paths[2:]], REVIEW / f"{KEY}_views.png")


CLOSEUPS = [
    # name, camera location, target, lens (local metres; the face is at +Y)
    ("face", (0.9, 7.6, 2.6), (0.0, 2.6, 1.9), 35.0),
    ("eye_left", (1.6, 4.7, 2.7), (1.0, 2.6, 2.3), 50.0),
    ("hat", (-3.6, 6.4, 6.4), (-0.4, 0.6, 4.6), 35.0),
    ("side_skin", (5.4, 1.2, 2.2), (2.9, 0.4, 1.8), 50.0),
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


# backface_check names its views after the Meshy source (its "front" camera is at -Y); this asset's face is at +Y.
# Sheet order (camera side): +Y face, -Y back, +X / -X, top, bottom.
CULLED_TILES = [[("back", "+Y (face)"), ("front", "-Y (back)"), ("right", "+X")],
                [("left", "-X"), ("top", "+Z (top)"), ("bottom", "-Z (bottom)")]]


def backface_sheet(obj, tmp: Path) -> tuple[Path, dict]:
    culling = meshops.backface_check(obj, tmp / "cull")
    culling["view_camera_side"] = {view: side for row in CULLED_TILES for view, side in row}
    sheet = grid_sheet([[tmp / "cull" / f"cull_{view}_1.png" for view, _ in row] for row in CULLED_TILES],
                       REVIEW / f"{KEY}_backface_culled.png")
    return sheet, culling


def manifest(row: dict, checks: dict, textures: dict) -> dict:
    exported = (BUNDLE / "report.json").is_file() and (BUNDLE / "model.apply.json").is_file()
    dims = checks["dimensions_m"]
    points = row["derived"]["points_local_m"]
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
            "script_file": "modeling/M02/build.py",
            "origin_policy": row["decided"]["origin_policy"],
            "origin_world": [0.0, 0.0, 0.0],
            "dimensions_m": {"width": dims["width_x"], "depth": dims["depth_y"], "height": dims["height_z"]},
            "bounds_local": checks["bounds_m"],
            "parts": [{"part_id": NAME, "role": "asset_root", "parent_part": None, "origin_policy": "ground_center",
                       "pivot_local": [0.0, 0.0, 0.0]}],
            "hierarchy": {"asset_root": NAME, "motion_roots": [], "visual_roots": [NAME], "attachment_points": []},
            "materials": [f"MAT_{KEY}_GiantPumpkin"],
            "textures": [info["file"] for info in textures.values() if "file" in info],
            "metrics": {"measured": True, "measurement_source": "blender_scene", "triangles": checks["triangles"],
                        "vertices": checks["vertices"], "materials_count": 1, "objects_count": 1},
            "export_result": {"status": "exported", "bundle_dir": rel(BUNDLE), "apply_plan": rel(BUNDLE / "model.apply.json"),
                              "report_file": rel(BUNDLE / "report.json")} if exported else
                             {"status": "unexported", "bundle_dir": None, "apply_plan": None, "report_file": None},
            "replacement": {
                "is_placeholder": False,
                "modifiable": True,
                "future_target": None,
                "notes": (
                    "Finished Meshy visual for the VisualRoot of the A_plaza giant pumpkin (Spec 6.3); it replaces the "
                    "W02 placeholder (its ID is chosen by W02 #4, not yet made on 2026-10-31) in P2. origin_world is "
                    "the asset-local origin: the world position is W02's (received.json placement_hint: (0, 0, top of "
                    "the fountain bowl), rotation_z 180 so the face looks south). Origin = bottom centre (z=0), front "
                    "= +Y (Resonite +Z). Eye glow (I03) goes inside the hollow, in front of the inner back wall at "
                    f"{points['interior_back_wall']}; eyes at {points['eye_left_centre_front']} and "
                    f"{points['eye_right_centre_front']}; reaction point mouth {points['mouth_centre_front']}. No "
                    "emission is baked into the albedo; no collider is part of this visual."
                ),
            },
        }],
    }


def main() -> None:
    row = load_row()
    obj, textures = build_asset(row)
    checks = shape_checks(obj, row)
    bpy.context.preferences.filepaths.save_version = 0  # no M02.blend1 backup (as finish.py)
    save_blend(BLEND, pack_images=True)
    counts = {k: len(getattr(bpy.data, k)) for k in ("objects", "meshes", "materials", "images", "collections")}

    REVIEW.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        sun = front_sun()
        views = views_sheet(obj, tmp)
        finished = closeup_views("finished", tmp)
        uv_image, uv_texel_share = uv_layout(obj)
        culled, culling = backface_sheet(obj, tmp)
        # The source after everything about the finished object: same placement, original 4096 images.
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
        "budget": row["budget"],
        "textures": textures,
        "uv_texel_share_1024": uv_texel_share,
        "backface_check": culling,
        "blend_counts": counts,
        "blender": bpy.app.version_string,
        "review_images": [rel(p) for p in (views, compare, uv_image, culled)],
        "closeups": [{"name": n, "camera": loc, "target": tgt, "lens_mm": lens} for n, loc, tgt, lens in CLOSEUPS],
    })
    (REVIEW / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest(row, checks, textures), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"built {rel(BLEND)}: triangles={checks['triangles']} dims={checks['dimensions_m']} "
          f"uv_cover={checks['uv_cover']} counts={counts}")


if __name__ == "__main__":
    main()
