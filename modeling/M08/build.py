"""Rebuild the finished M08 witch on a broom (W09-M08, #21) from the received Meshy GLB.

Run in the project directory (``docs/conventions.md`` §7.1):
    resoloop blender run modeling/M08/build.py --json
Then ``uv run python modeling/M08/export.py`` exports and validates the bundle (a rebuild resets ``export_result``).

Outputs (``.blend`` and textures are not committed; ``docs/conventions.md`` §8):
- ``blender/M08/M08.blend`` with one object ``M08_FlyingWitch_001`` in the collection ``M08``, and its textures in
  ``blender/M08/textures/`` (also packed in the ``.blend``)
- ``review/M08/``: ``M08_views.png`` (four sides, 1.8 m figure), ``M08_origin_axis.png`` (the origin, the
  broom axis W09 decided, +Y and the measured handle centres), ``M08_compare_source.png`` (close-ups and one view
  from 12 m; the source on the left of each pair, the finished asset on the right), ``M08_uv_layout.png`` (UV cover
  on the colour image), ``M08_backface_culled.png`` (six sides with back faces hidden, as Resonite draws a
  single-sided material) and ``checks.json`` (the measurements the acceptance criteria of #21 ask for)
- ``assets/manifest/M08.json`` (``export_result`` is ``unexported`` until ``export.py`` runs)

Everything is decided by W09 in ``assets/meshy/received.json`` (row ``M08``) and done by W09's common finishing
(``modeling/meshy/finish.py``): placement (origin = the flight centre on the broom axis, the broom tip towards +Y),
naming, texture sizes (colour 1024, data maps 512, the far-view budget) and the material for ``--pack-pbr``. No
reduction (the row's ``budget.triangles_max`` is the source count), the original normals are kept and the mesh stays
single-sided (``double_sided``). Witch, broom and cat bag stay one static piece without a rig (``split_and_attach``).
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
from mathutils import Vector  # type: ignore

from modeling.lib.render import render_review_images
from modeling.lib.scene import reset_scene, save_blend
from modeling.meshy import finish, meshops, metrics

KEY = "M08"
NAME = "M08_FlyingWitch_001"  # the replacement target W04 #6 names for CCD_M08_FlyingWitchProxy_001 (in progress)
RECEIVED = PROJECT_ROOT / "assets" / "meshy" / "received.json"
BLEND = PROJECT_ROOT / "blender" / KEY / f"{KEY}.blend"
TEX_DIR = PROJECT_ROOT / "blender" / KEY / "textures"
REVIEW = PROJECT_ROOT / "review" / KEY
MANIFEST = PROJECT_ROOT / "assets" / "manifest" / f"{KEY}.json"
BUNDLE = PROJECT_ROOT / "exports" / KEY / "bundle"
# The handle ahead of the hands (they hold it at y 0.30-0.56): plane sections here meet the handle only.
HANDLE_FRONT_Y = (0.60, 0.65, 0.70, 0.75, 0.80, 0.85)
HANDLE_RADIUS = 0.12  # section segments within this distance (x, z) of the decided axis belong to the handle
BRISTLE_RADIUS = 0.30  # ... and of the bristle bundle at the bristle end


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
    """Import the GLB into the current scene and return its one mesh object (the confirmed M08 has one)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    if len(meshes) != 1 or len(new) != 1:
        raise SystemExit(f"{path.name}: expected one mesh object, got {[o.name for o in new]}")
    obj = meshes[0]
    if obj.animation_data or obj.constraints or obj.data.shape_keys or obj.modifiers or obj.vertex_groups:
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


def plane_section(positions: np.ndarray, y0: float) -> np.ndarray:
    """Segments (N x 2 x 3) where the triangles (F x 3 x 3) cross the plane y = ``y0``."""
    d = positions[:, :, 1] - y0
    below = d < 0
    crossing = below.any(axis=1) & ~below.all(axis=1)
    tris, dd, bb = positions[crossing], d[crossing], below[crossing]
    segs = []
    for tri, di, bi in zip(tris, dd, bb):
        pts = [tri[a] + di[a] / (di[a] - di[b]) * (tri[b] - tri[a]) for a, b in ((0, 1), (1, 2), (2, 0)) if bi[a] != bi[b]]
        if len(pts) == 2:
            segs.append(pts)
    return np.asarray(segs).reshape(-1, 2, 3)


def section_centre(positions: np.ndarray, y0: float, near: np.ndarray, radius: float) -> dict:
    """Length-weighted centre of the section segments at ``y0`` whose midpoints lie within ``radius`` (x, z) of
    ``near``: the centre of the handle (or bristle bundle) cross-section."""
    segs = plane_section(positions, y0)
    mid = segs.mean(axis=1)
    keep = np.linalg.norm(mid[:, [0, 2]] - near[[0, 2]], axis=1) < radius
    part = segs[keep]
    if len(part) == 0:
        raise SystemExit(f"no section at y={y0} within {radius} m of {near.tolist()}")
    length = np.linalg.norm(part[:, 1] - part[:, 0], axis=1)
    centre = (part.mean(axis=1) * length[:, None]).sum(axis=0) / length.sum()
    pts = part.reshape(-1, 3)
    return {"y": round(y0, 3), "centre": [round(float(v), 4) for v in centre], "perimeter_m": round(float(length.sum()), 3),
            "span_x_m": round(float(np.ptp(pts[:, 0])), 3), "span_z_m": round(float(np.ptp(pts[:, 2])), 3)}


def point_line_distance(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    d = (b - a) / np.linalg.norm(b - a)
    v = p - a
    return float(np.linalg.norm(v - (v @ d) * d))


def nearest_on_line(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = (b - a) / np.linalg.norm(b - a)
    return a + ((p - a) @ d) * d


def heading(a: np.ndarray, b: np.ndarray) -> dict:
    """Direction from ``a`` to ``b``: the horizontal angle from +Y (positive towards -X, as Blender's yaw) and the
    rise above the horizontal."""
    v = b - a
    return {"yaw_from_plus_y_deg": round(math.degrees(math.atan2(-v[0], v[1])), 2),
            "pitch_deg": round(math.degrees(math.atan2(v[2], math.hypot(v[0], v[1]))), 2)}


def broom_checks(positions: np.ndarray, lo: np.ndarray, hi: np.ndarray, row: dict) -> dict:
    """The decided origin and front against the mesh: W09's axis (bristle end centre -> broom tip, read by eye
    from the source), and the handle measured from plane sections of the finished mesh."""
    pts = row["derived"]["points_local_m"]
    tip, bristle = np.asarray(pts["broom_tip"], float), np.asarray(pts["bristle_end_centre"], float)
    box_centre = (lo + hi) / 2
    origin = np.zeros(3)

    def axis_at(y: float) -> np.ndarray:
        return bristle + (y - bristle[1]) / (tip[1] - bristle[1]) * (tip - bristle)

    front = [section_centre(positions, y, axis_at(y), HANDLE_RADIUS) for y in HANDLE_FRONT_Y]
    c = np.asarray([s["centre"] for s in front])
    fit_x = np.polyfit(c[:, 1], c[:, 0], 1)
    fit_z = np.polyfit(c[:, 1], c[:, 2], 1)
    fit_residual = float(np.abs(np.c_[np.polyval(fit_x, c[:, 1]) - c[:, 0], np.polyval(fit_z, c[:, 1]) - c[:, 2]]).max())
    bristle_section = section_centre(positions, float(bristle[1]), bristle, BRISTLE_RADIUS)
    m_bristle = np.asarray(bristle_section["centre"])
    m_tip = c[-1]
    w09_near = nearest_on_line(box_centre, bristle, tip)
    m_near = nearest_on_line(box_centre, m_bristle, m_tip)
    tip_vertex_y = float(hi[1])
    return {
        "method": ("Plane sections y = const of the finished triangles; a section centre is the length-weighted mean "
                   f"of the segments within {HANDLE_RADIUS} m (handle) or {BRISTLE_RADIUS} m (bristle bundle) of W09's "
                   "axis in x and z. The handle ahead of the hands (y 0.60-0.85) is fitted with a straight line."),
        "w09_axis": {"bristle_end_centre": pts["bristle_end_centre"], "broom_tip": pts["broom_tip"],
                     **heading(bristle, tip),
                     "origin_distance_m": round(point_line_distance(origin, bristle, tip), 4),
                     "nearest_point_to_box_centre": [round(float(v), 4) for v in w09_near],
                     "nearest_point_offset_from_origin_m": round(float(np.linalg.norm(w09_near)), 4)},
        "handle_front_sections": front,
        "handle_front_line": {**heading(np.array([np.polyval(fit_x, 0.0), 0.0, np.polyval(fit_z, 0.0)]),
                                        np.array([np.polyval(fit_x, 1.0), 1.0, np.polyval(fit_z, 1.0)])),
                              "x_at_tip_section_m": round(float(np.polyval(fit_x, HANDLE_FRONT_Y[-1])), 4),
                              "max_fit_residual_m": round(fit_residual, 4)},
        "bristle_end_section": bristle_section,
        "measured_axis": {"from": "bristle_end_section centre", "to": f"handle section centre at y {HANDLE_FRONT_Y[-1]}",
                          **heading(m_bristle, m_tip),
                          "origin_distance_m": round(point_line_distance(origin, m_bristle, m_tip), 4),
                          "nearest_point_to_box_centre": [round(float(v), 4) for v in m_near]},
        "differences_from_w09_m": {
            "tip_section_centre_minus_w09_axis": [round(float(v), 4) for v in m_tip - axis_at(HANDLE_FRONT_Y[-1])],
            "bristle_section_centre_minus_w09_point": [round(float(v), 4) for v in m_bristle - bristle],
        },
        "frontmost_vertex_y": round(tip_vertex_y, 4),
    }


def shape_checks(obj, row: dict) -> dict:
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
        "triangles": len(positions),
        "vertices": len(obj.data.vertices),
        "bounds_m": {"min": [round(float(v), 4) for v in lo], "max": [round(float(v), 4) for v in hi]},
        "bounds_expected_m": expected,
        "bounds_max_abs_diff_m": round(float(max(np.abs(lo - expected["min"]).max(), np.abs(hi - expected["max"]).max())), 4),
        "dimensions_m": {"width_x": round(float(hi[0] - lo[0]), 3), "depth_y": round(float(hi[1] - lo[1]), 3),
                         "height_z": round(float(hi[2] - lo[2]), 3)},
        "dimensions_expected_m": row["derived"]["dimensions_m"],
        "origin": {"policy": row["decided"]["origin_policy"], "note": row["decided"]["origin_note"],
                   "extent_from_origin_m": {"down": round(float(-lo[2]), 3), "up": round(float(hi[2]), 3),
                                            "front_plus_y": round(float(hi[1]), 3), "back": round(float(-lo[1]), 3),
                                            "plus_x": round(float(hi[0]), 3), "minus_x": round(float(-lo[0]), 3)},
                   "box_centre": [round(float(v), 4) for v in (lo + hi) / 2]},
        "broom": broom_checks(positions, lo, hi, row),
        "object_transform_identity": bool(np.allclose(np.array(obj.matrix_world), np.eye(4), atol=1e-9)),
        "uv_cover": round(cover["area_sum"], 4),
        "uv_corners_in_unit_square": round(cover["corners_in_unit_square"], 4),
        "surface_area_m2": round(area, 1),
        "texels_per_m_at_color": round(math.sqrt(cover["area_sum"] * color_px * color_px / area), 1),
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


def face_sun() -> object:
    """``render_review_images`` lights from -Y; the witch turns her face to -X (and the front, +Y), so add a sun
    from that side."""
    sun = bpy.data.objects.new("Review_FaceSun", bpy.data.lights.new("Review_FaceSun", type="SUN"))
    sun.data.energy = 2.5
    sun.rotation_euler = Vector((0.8, -0.5, -0.6)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(sun)
    return sun


def remove_objects(objects: list) -> None:
    for o in objects:
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if isinstance(data, bpy.types.Mesh) and data.users == 0:
            bpy.data.meshes.remove(data)


def views_sheet(obj, tmp: Path) -> Path:
    """Four sides (+Y front, +X, -Y back, -X) with a 1.8 m figure off the front-right corner, standing level with
    the lowest point (the boots)."""
    from modeling.meshy.review_views import add_figure

    co = meshops.vertex_array(obj)
    lo, hi = co.min(axis=0), co.max(axis=0)
    figure = add_figure(float(hi[0]) + 0.5, float(hi[1]) + 0.5, float(lo[2]))
    lens = 85.0
    half_fov = math.atan(18.0 / lens)
    span = {0: (float(lo[0]), float(hi[0]) + 0.75), 1: (float(lo[1]), float(hi[1]) + 0.75)}
    views = []
    for name, direction, across, depth in (("front", (0, 1, 0), 0, 1), ("right", (1, 0, 0), 1, 0),
                                           ("back", (0, -1, 0), 0, 1), ("left", (-1, 0, 0), 1, 0)):
        a0, a1 = span[across]
        extent = max(a1 - a0, float(hi[2] - lo[2])) * 1.08
        centre = np.zeros(3)
        centre[across] = (a0 + a1) / 2
        centre[depth] = (float(lo[depth]) + float(hi[depth])) / 2
        centre[2] = (float(lo[2]) + float(hi[2])) / 2
        distance = extent / 2 / math.tan(half_fov) + float(hi[depth] - lo[depth]) / 2
        views.append({"filepath": tmp / f"view_{name}.png", "location": tuple(centre + np.asarray(direction) * distance),
                      "target": tuple(centre), "lens_mm": lens})
    paths = render_review_images(views, width=640, height=640, samples=32)
    remove_objects(figure)
    return grid_sheet([paths[:2], paths[2:]], REVIEW / f"{KEY}_views.png")


def marker(name: str, kind: str, location, colour, size: float, end=None) -> object:
    """A render-only helper: a sphere at ``location`` or a rod from ``location`` to ``end``."""
    if kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=size, location=tuple(location), segments=16, ring_count=8)
    else:
        a, b = Vector(location), Vector(end)
        bpy.ops.mesh.primitive_cylinder_add(radius=size, depth=(b - a).length, location=tuple((a + b) / 2), vertices=12)
        bpy.context.active_object.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    o = bpy.context.active_object
    o.name = name
    o.color = (*colour, 1.0)
    return o


def origin_axis_sheet(obj, broom: dict, tmp: Path) -> Path:
    """Orthographic Workbench views (-X face side, +Z top with +Y up, +Y front) of the origin (red), W09's broom axis
    (cyan), +Y from the origin (yellow) and the measured handle and bristle section centres (green). The helpers are
    drawn in front of the mesh, so the hidden parts (the origin under the skirt) show."""
    w = broom["w09_axis"]
    helpers = [
        marker("Review_W09Axis", "rod", w["bristle_end_centre"], (0.1, 0.9, 1.0), 0.01, w["broom_tip"]),
        marker("Review_PlusY", "rod", (0, 0, 0), (1.0, 0.85, 0.1), 0.014, (0, 0.7, 0)),
        marker("Review_PlusYHead", "sphere", (0, 0.7, 0), (1.0, 0.85, 0.1), 0.035),
        marker("Review_Origin", "sphere", (0, 0, 0), (1.0, 0.1, 0.1), 0.045),
    ]
    for i, s in enumerate(broom["handle_front_sections"] + [broom["bristle_end_section"]]):
        helpers.append(marker(f"Review_Section_{i}", "sphere", s["centre"], (0.1, 0.9, 0.2), 0.025))
    for o in helpers:
        o.show_in_front = True
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "OBJECT"
    obj.color = (0.62, 0.62, 0.66, 1.0)
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.image_settings.file_format = "PNG"
    co = meshops.vertex_array(obj)
    lo, hi = co.min(axis=0), co.max(axis=0)
    centre = Vector(((lo + hi) / 2).tolist())
    cam_data = bpy.data.cameras.new("Review_AxisCamera")
    cam = bpy.data.objects.new("Review_AxisCamera", cam_data)
    scene.collection.objects.link(cam)
    prev_camera = scene.camera
    scene.camera = cam
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = float((hi - lo).max()) * 1.1
    cam_data.clip_end = 100.0
    paths = []
    try:
        for name, d in (("minus_x", (-1, 0, 0)), ("top", (0, 0, 1)), ("front", (0, 1, 0))):
            direction = Vector(d)
            cam.location = centre + direction * 10.0
            cam.rotation_euler = (0.0, 0.0, 0.0) if name == "top" else (-direction).to_track_quat("-Z", "Y").to_euler()
            path = tmp / f"axis_{name}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            paths.append(path)
    finally:
        shading.color_type = "TEXTURE"
        scene.camera = prev_camera
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cam_data, do_unlink=True)
        remove_objects(helpers)
    return grid_sheet([paths], REVIEW / f"{KEY}_origin_axis.png")


CLOSEUPS = [
    # name, camera location, target, lens (local metres; the broom tip is at +Y, the witch turns her face to -X)
    ("face", (-1.55, 0.95, 1.2), (-0.12, 0.12, 1.0), 50.0),
    ("hat", (-1.6, 0.9, 2.1), (-0.05, -0.15, 1.42), 40.0),
    ("cat_bag", (-1.45, 0.05, 0.6), (-0.33, -0.33, 0.42), 50.0),
    ("hands_handle", (-1.1, 1.25, 0.45), (-0.05, 0.55, 0.12), 50.0),
    ("bristles", (-1.6, -0.45, 0.2), (0.0, -0.9, -0.28), 50.0),
    # A viewer on the street with the path about 10 m up, 12.5 m away. The 135 mm lens gives about 190 px/m on the
    # tile, as fine as the colour image (182 texels/m): coarser views show even less of the 1024 px difference.
    ("from_12m_below", (-7.0, 6.0, -7.6), (0.13, -0.15, 0.64), 135.0),
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
    if color.shape[0] != size or color.shape[1] != size:
        img.scale(size, size)
    px = np.empty(size * size * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    px = px.reshape(size, size, 4)
    px[~occupied, :3] = px[~occupied, :3] * 0.15 + np.array([0.35, 0.0, 0.35]) * 0.85
    return write_png(px, REVIEW / f"{KEY}_uv_layout.png"), round(float(occupied.mean()), 4)


# backface_check names its views after the Meshy source (its "front" camera is at -Y); this asset's front is +Y.
# Sheet order (camera side): +Y front, -Y back, +X / -X, top, bottom.
CULLED_TILES = [[("back", "+Y (front, broom tip)"), ("front", "-Y (back, bristles)"), ("right", "+X")],
                [("left", "-X (face side)"), ("top", "+Z (top)"), ("bottom", "-Z (bottom)")]]


def backface_sheet(obj, tmp: Path) -> tuple[Path, dict]:
    culling = meshops.backface_check(obj, tmp / "cull")
    culling["view_camera_side"] = {view: side for row in CULLED_TILES for view, side in row}
    sheet = grid_sheet([[tmp / "cull" / f"cull_{view}_1.png" for view, _ in row] for row in CULLED_TILES],
                       REVIEW / f"{KEY}_backface_culled.png")
    return sheet, culling


def manifest(row: dict, checks: dict, textures: dict) -> dict:
    dims = checks["dimensions_m"]
    w09 = checks["broom"]["w09_axis"]
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
            "script_file": "modeling/M08/build.py",
            "origin_policy": row["decided"]["origin_policy"],
            "origin_world": [0.0, 0.0, 0.0],
            "dimensions_m": {"width": dims["width_x"], "depth": dims["depth_y"], "height": dims["height_z"]},
            "bounds_local": checks["bounds_m"],
            "parts": [{"part_id": NAME, "role": "asset_root", "parent_part": None,
                       "origin_policy": row["decided"]["origin_policy"], "pivot_local": [0.0, 0.0, 0.0]}],
            "hierarchy": {"asset_root": NAME, "motion_roots": [], "visual_roots": [NAME], "attachment_points": []},
            "materials": [f"MAT_{KEY}_FlyingWitch"],
            "textures": [info["file"] for info in textures.values() if "file" in info],
            "metrics": {"measured": True, "measurement_source": "blender_scene", "triangles": checks["triangles"],
                        "vertices": checks["vertices"], "materials_count": 1, "objects_count": 1},
            "export_result": {"status": "unexported", "bundle_dir": None, "apply_plan": None, "report_file": None},
            "flight": {
                "origin": "flight centre: on W09's broom axis (bristle end centre -> broom tip), the point nearest "
                          "the bounding-box centre (below the seat)",
                "front": "+Y = the broom tip, the direction of travel (Resonite +Z)",
                "broom_axis_w09": {"bristle_end_centre": w09["bristle_end_centre"], "broom_tip": w09["broom_tip"],
                                   "pitch_deg": w09["pitch_deg"]},
                "extent_from_origin_m": checks["origin"]["extent_from_origin_m"],
            },
            "replacement": {
                "is_placeholder": False,
                "modifiable": True,
                "future_target": None,
                "replaces_placeholder": {
                    "manifest": "assets/manifest/C_candy.json",
                    "asset_id": "CCD_M08_FlyingWitchProxy_001",
                    "status": "named by W04 #6 (in progress; not on main on 2026-10-31). Confirm against main in P2.",
                },
                "notes": (
                    "Finished Meshy visual for the VisualRoot of the flying witch (Spec 6.3) on the G11 patrol loop "
                    "above C_candy; it replaces W04's rider placeholder in P2 (after W08). One static piece (witch, "
                    "broom, cat bag), no rig. origin_world is the asset-local origin: the flight centre on the broom "
                    "axis; put it on the patrol path and point +Y (Resonite +Z) along the path tangent. The broom tip "
                    f"rises {w09['pitch_deg']} deg (W09 axis); keep it as the pose. Trails, glow and motion are "
                    "Resonite-side (G11). No emission is baked into the albedo; no collider is part of this visual."
                ),
            },
        }],
    }


def main() -> None:
    row = load_row()
    obj, textures = build_asset(row)
    checks = shape_checks(obj, row)
    bpy.context.preferences.filepaths.save_version = 0  # no M08.blend1 backup (as finish.py)
    save_blend(BLEND, pack_images=True)
    counts = {k: len(getattr(bpy.data, k)) for k in ("objects", "meshes", "materials", "images", "collections")}

    REVIEW.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        axis = origin_axis_sheet(obj, checks["broom"], tmp)
        sun = face_sun()
        views = views_sheet(obj, tmp)
        finished = closeup_views("finished", tmp)
        uv_image, uv_texel_share = uv_layout(obj)
        culled, culling = backface_sheet(obj, tmp)
        # The source after everything about the finished object: same placement, original 4096 images.
        source = import_source(Path(row["source"]["copy_path"]))
        finish.place(source, row["decided"])
        obj.hide_render = True
        original = closeup_views("source", tmp)
        pairs = [[s, f] for s, f in zip(original, finished)]
        compare = grid_sheet([pairs[i] + pairs[i + 1] for i in range(0, len(pairs), 2)],
                             REVIEW / f"{KEY}_compare_source.png")
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
        "review_images": [rel(p) for p in (views, axis, compare, uv_image, culled)],
        "closeups": [{"name": n, "camera": loc, "target": tgt, "lens_mm": lens} for n, loc, tgt, lens in CLOSEUPS],
        "compare_layout": "rows of two pairs; each pair is source (4096 images) | finished",
    })
    (REVIEW / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest(row, checks, textures), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"built {rel(BLEND)}: triangles={checks['triangles']} dims={checks['dimensions_m']} "
          f"uv_cover={checks['uv_cover']} counts={counts}")


if __name__ == "__main__":
    main()
