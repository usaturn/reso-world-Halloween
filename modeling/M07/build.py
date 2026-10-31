"""Rebuild the finished M07 magical clock tower (W09-M07, #20) from the received Meshy GLB.

Run in the project directory (``docs/conventions.md`` §7.1):
    resoloop blender run modeling/M07/build.py --json
then ``uv run python modeling/M07/export.py`` for the export and validate (a rebuild resets ``export_result``).

Outputs (``.blend`` and textures are not committed; ``docs/conventions.md`` §8):
- ``blender/M07/M07.blend`` with one object ``M07_ClockTower_001`` in the collection ``M07``, and its textures in
  ``blender/M07/textures/`` (also packed in the ``.blend``)
- ``review/M07/``: ``M07_views.png`` (four sides, 1.8 m figure), ``M07_dial_textured.png`` (the dial straight on:
  Cycles with the textures, and the colour image unlit with the measured rim circle and centre drawn on it),
  ``M07_dial_shape.png`` (the same dial as shape only: straight on and at a grazing angle), ``M07_compare_source.png``
  (close-ups, the source on the left and the finished asset on the right), ``M07_uv_layout.png`` (UV cover on the
  colour image), ``M07_backface_culled.png`` (six sides with back faces hidden, as Resonite draws a single-sided
  material) and ``checks.json`` (the measurements the acceptance criteria of #20 ask for)
- ``assets/manifest/M07.json`` (``export_result`` is ``unexported``; ``export.py`` fills it)

Everything is decided by W09 in ``assets/meshy/received.json`` (row ``M07``) and done by W09's common finishing
(``modeling/meshy/finish.py``): placement, naming, texture sizes (colour 2048, data maps 1024) and the material for
``--pack-pbr``. No reduction (the row's ``budget.triangles_max`` is the source count), the original normals are
kept and the mesh stays single-sided (``double_sided``). The dial stays joined to the tower and has no hands; the
hands and the bell are W06's separate parts (``split_and_attach``), so this script measures the dial for them.
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

KEY = "M07"
NAME = "M07_ClockTower_001"
RECEIVED = PROJECT_ROOT / "assets" / "meshy" / "received.json"
W06_MANIFEST = PROJECT_ROOT / "assets" / "manifest" / "E_forest.json"  # read only (W06's placeholder and hands)
W06_ASSET = "EFR_ClockTower_001"
BLEND = PROJECT_ROOT / "blender" / KEY / f"{KEY}.blend"
TEX_DIR = PROJECT_ROOT / "blender" / KEY / "textures"
REVIEW = PROJECT_ROOT / "review" / KEY
MANIFEST = PROJECT_ROOT / "assets" / "manifest" / f"{KEY}.json"
BUNDLE = PROJECT_ROOT / "exports" / KEY / "bundle"

# Dial measurement (local metres, the clock axis is horizontal along +Y). Rays travel -Y from in front of the box.
INNER_DISC = (0.12, 0.50)  # the flat disc between the hub and the numerals ring (seen in the dial close-ups)
NUMERALS_RING = (0.55, 1.00)
EDGE_SEARCH = (0.95, 1.45)  # the outer edge of the dial is looked for along radial lines in this range
EDGE_DROP = 0.08  # a first hit this far behind the face plane is the wall around the dial, not the dial
EDGE_STEP = 0.002
EDGE_ANGLES = 120
RING_SEARCH = (0.40, 0.80)  # the step from the flat inner disc up to the numerals ring is looked for in this range
RING_RAISE = 0.006
FIT_TOLERANCE = 0.01  # circle fits leave out points this far off (numerals touching the ring), refitting until stable
SECTOR_HALF_DEG = 30.0
HUB_SEARCH = 0.12
HUB_RAISE = 0.02
GRID = 0.01
RELIEF_LIMIT = 0.005  # a hand on the inner disc would stand out more than this from the face plane
STREAK_ANGLES = 72
STREAK_COLOUR = 0.15  # a texel differs from the disc colour by more than this (max over RGB) -> part of a streak
DIAL_VIEW = 3.0  # width (m) of the straight-on dial close-ups
FIGURE_HEIGHT = 1.8


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


def load_w06() -> dict | None:
    """W06's clock tower placeholder (``assets/manifest/E_forest.json``), or None if W06's manifest lacks it."""
    if not W06_MANIFEST.is_file():
        return None
    for asset in json.loads(W06_MANIFEST.read_text(encoding="utf-8"))["assets"]:
        if asset["asset_id"] == W06_ASSET:
            return asset
    return None


def import_source(path: Path) -> object:
    """Import the GLB into the current scene and return its one mesh object (the confirmed M07 has one)."""
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


def grid_sheet(rows: list[list], out: Path, gap: int = 6) -> Path:
    """Tiles of equal size (paths or H x W x 4 arrays), ``rows[0]`` at the top, separated by a light ``gap``."""
    tiles = [[read_png(p) if isinstance(p, Path) else p for p in row] for row in rows]
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


class Surface:
    """Ray casts against the evaluated loop triangles, with the UV of each hit (for sampling the colour image)."""

    def __init__(self, obj) -> None:
        self.positions, self.uv = meshops.triangle_arrays(obj)
        verts = [tuple(v) for v in self.positions.reshape(-1, 3)]
        polys = [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(self.positions))]
        self.bvh = BVHTree.FromPolygons(verts, polys)
        co = self.positions.reshape(-1, 3)
        self.lo, self.hi = co.min(axis=0), co.max(axis=0)

    def front_hit(self, x: float, z: float):
        """First hit of a ray from in front of the box (+Y) travelling -Y: (location, normal, triangle) or None."""
        loc, normal, index, _ = self.bvh.ray_cast(Vector((x, float(self.hi[1]) + 1.0, z)), Vector((0, -1, 0)),
                                                  float(self.hi[1] - self.lo[1]) + 2.0)
        return None if loc is None else (loc, normal, index)

    def hit_uv(self, loc, index: int) -> np.ndarray:
        a, b, c = self.positions[index]
        p = np.asarray(loc)
        v0, v1, v2 = b - a, c - a, p - a
        d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
        d20, d21 = v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        w1 = (d11 * d20 - d01 * d21) / den
        w2 = (d00 * d21 - d01 * d20) / den
        ua, ub, uc = self.uv[index]
        return (1 - w1 - w2) * ua + w1 * ub + w2 * uc


def fit_circle(pts: np.ndarray) -> tuple[np.ndarray, float]:
    """Least-squares circle (Kasa) through 2-D points: (centre, radius)."""
    a = np.column_stack([2 * pts[:, 0], 2 * pts[:, 1], np.ones(len(pts))])
    b = (pts ** 2).sum(axis=1)
    (u, v, w), *_ = np.linalg.lstsq(a, b, rcond=None)
    return np.array([u, v]), float(math.sqrt(w + u * u + v * v))


def trimmed_circle(pts: np.ndarray) -> tuple[np.ndarray, float, np.ndarray, np.ndarray]:
    """Circle fit that leaves out points more than ``FIT_TOLERANCE`` off and refits until the kept set is stable.
    Returns (centre, radius, kept mask, signed distance of every point from the circle)."""
    keep = np.ones(len(pts), dtype=bool)
    for _ in range(20):
        centre, radius = fit_circle(pts[keep])
        off = np.hypot(pts[:, 0] - centre[0], pts[:, 1] - centre[1]) - radius
        new = np.abs(off) <= FIT_TOLERANCE
        if (new == keep).all() or new.sum() < 3:
            break
        keep = new
    return centre, radius, keep, off


def dial_checks(surface: Surface, row: dict, color: np.ndarray, w06: dict | None) -> dict:
    """The dial, measured on the finished mesh: face plane, rim circle, hub, relief and colour streaks on the inner
    disc (a clock hand would be a raised or coloured streak from the hub), and W06's hands and bell against it."""
    w09 = row["derived"]["points_local_m"]["dial_centre_face"]
    cx0, cz0 = float(w09[0]), float(w09[2])

    # Face plane: y = a x + b z + c over the inner disc.
    disc = []
    for x in np.arange(cx0 - INNER_DISC[1], cx0 + INNER_DISC[1] + 1e-9, GRID):
        for z in np.arange(cz0 - INNER_DISC[1], cz0 + INNER_DISC[1] + 1e-9, GRID):
            r = math.hypot(x - cx0, z - cz0)
            if INNER_DISC[0] <= r <= INNER_DISC[1]:
                hit = surface.front_hit(float(x), float(z))
                if hit is not None:
                    disc.append((float(x), hit[0][1], float(z)))
    disc_pts = np.asarray(disc)
    coef, *_ = np.linalg.lstsq(np.column_stack([disc_pts[:, 0], disc_pts[:, 2], np.ones(len(disc_pts))]),
                               disc_pts[:, 1], rcond=None)
    a, b, c = (float(v) for v in coef)
    residual = disc_pts[:, 1] - (a * disc_pts[:, 0] + b * disc_pts[:, 2] + c)
    normal = np.array([-a, 1.0, -b]) / math.sqrt(a * a + 1.0 + b * b)

    def plane_y(x: float, z: float) -> float:
        return a * x + b * z + c

    def radial_edges(cx: float, cz: float, r_range: tuple[float, float], crossed) -> list[tuple[float, float, float]]:
        """On ``EDGE_ANGLES`` radial lines from (cx, cz): the first radius where ``crossed(hit, x, z)`` holds, as
        (angle in degrees, x, z) at the middle of the step. Lines where it never holds are left out."""
        found = []
        for k in range(EDGE_ANGLES):
            t = 2 * math.pi * k / EDGE_ANGLES
            last = None
            for r in np.arange(r_range[0], r_range[1], EDGE_STEP):
                x, z = cx + r * math.cos(t), cz + r * math.sin(t)
                if crossed(surface.front_hit(x, z), x, z):
                    if last is not None:
                        re = (last + r) / 2
                        found.append((360.0 * k / EDGE_ANGLES, cx + re * math.cos(t), cz + re * math.sin(t)))
                    break
                last = float(r)
        return found

    # Centre: the circle where the flat inner disc steps up to the numerals ring (a clean, unobstructed edge).
    ring = radial_edges(cx0, cz0, RING_SEARCH,
                        lambda hit, x, z: hit is not None and hit[0][1] > plane_y(x, z) + RING_RAISE)
    ring_pts = np.asarray([(x, z) for _, x, z in ring])
    centre, ring_r, ring_keep, ring_off = trimmed_circle(ring_pts)
    xc, zc = float(centre[0]), float(centre[1])
    face_y = plane_y(xc, zc)

    # Outer edge: the first hit falls behind the face plane (the wall around the dial). Below the dial a sill
    # continues the dial's front, so the edge is reported per direction around the measured centre.
    outer = radial_edges(xc, zc, EDGE_SEARCH,
                         lambda hit, x, z: hit is None or hit[0][1] < plane_y(x, z) - EDGE_DROP)
    outer_r = {round(a, 1): math.hypot(x - xc, z - zc) for a, x, z in outer}
    sectors = {}
    for name, mid in (("+X", 0.0), ("top", 90.0), ("-X", 180.0), ("bottom", 270.0)):
        rs = [r for a, r in outer_r.items() if abs((a - mid + 180.0) % 360.0 - 180.0) <= SECTOR_HALF_DEG]
        sectors[name] = {"lines": len(rs), "median_r_m": round(float(np.median(rs)), 4) if rs else None}

    # Hub (the small boss at the centre) and the relief of the rings.
    hub = []
    for x in np.arange(xc - HUB_SEARCH, xc + HUB_SEARCH + 1e-9, 0.002):
        for z in np.arange(zc - HUB_SEARCH, zc + HUB_SEARCH + 1e-9, 0.002):
            hit = surface.front_hit(float(x), float(z))
            if hit is not None and hit[0][1] > plane_y(x, z) + HUB_RAISE:
                hub.append((float(x), hit[0][1], float(z)))
    hub_pts = np.asarray(hub) if hub else np.zeros((0, 3))

    def ring_max_y(r0: float, r1: float, step: float = GRID) -> tuple[float, float]:
        best_y, best_raise = -1e9, -1e9
        for x in np.arange(xc - r1, xc + r1 + 1e-9, step):
            for z in np.arange(zc - r1, zc + r1 + 1e-9, step):
                if r0 <= math.hypot(x - xc, z - zc) <= r1:
                    hit = surface.front_hit(float(x), float(z))
                    if hit is not None:
                        best_y = max(best_y, hit[0][1])
                        best_raise = max(best_raise, hit[0][1] - plane_y(x, z))
        return round(best_y, 4), round(best_raise, 4)

    radius = (sectors["+X"]["median_r_m"] + sectors["-X"]["median_r_m"]) / 2  # the sides are clear of the sill
    numerals_y, numerals_raise = ring_max_y(*NUMERALS_RING)
    rim_y, rim_raise = ring_max_y(NUMERALS_RING[1], radius - 0.01)
    sweep_y, _ = ring_max_y(0.0, radius - 0.01)

    # Colour streaks on the inner disc: share of each radial line whose texels differ from the disc colour.
    h, w = color.shape[:2]
    samples = []  # (angle index, rgb)
    for k in range(STREAK_ANGLES):
        t = 2 * math.pi * k / STREAK_ANGLES
        for r in np.arange(INNER_DISC[0], INNER_DISC[1] + 1e-9, 0.01):
            hit = surface.front_hit(xc + r * math.cos(t), zc + r * math.sin(t))
            if hit is None:
                continue
            u, v = surface.hit_uv(hit[0], hit[2])
            px = color[min(max(int(v * h), 0), h - 1), min(max(int(u * w), 0), w - 1), :3]
            samples.append((k, px))
    rgb = np.asarray([s[1] for s in samples])
    median = np.median(rgb, axis=0)
    differs = np.abs(rgb - median).max(axis=1) > STREAK_COLOUR
    per_angle = np.zeros(STREAK_ANGLES)
    counts = np.zeros(STREAK_ANGLES)
    for (k, _), d in zip(samples, differs):
        per_angle[k] += d
        counts[k] += 1
    share = per_angle / np.maximum(counts, 1)

    out = {
        "method": ("rays from +Y travelling -Y on the finished mesh. Face plane: least squares over the inner disc "
                   f"(r {INNER_DISC[0]}..{INNER_DISC[1]} m, {GRID * 100:.0f} cm grid). Centre: on {EDGE_ANGLES} radial lines "
                   f"the first radius where the surface rises {RING_RAISE} m above the face plane (the step up to the "
                   f"numerals ring), circle fit leaving out points over {FIT_TOLERANCE} m off. Outer edge: the first radius "
                   f"where the first hit falls {EDGE_DROP} m behind the face plane, median per {2 * SECTOR_HALF_DEG:.0f}° "
                   "sector around the centre; the diameter is the +X and -X sectors (a sill continues the dial's "
                   "front below it)"),
        "centre_local_m": [round(xc, 4), round(face_y, 4), round(zc, 4)],
        "outer_diameter_m": round(2 * radius, 4),
        "inner_ring_fit": {"lines": EDGE_ANGLES, "edge_points": len(ring_pts), "kept": int(ring_keep.sum()),
                           "radius_m": round(float(ring_r), 4),
                           "rms_kept_m": round(float(np.sqrt((ring_off[ring_keep] ** 2).mean())), 4),
                           "max_abs_kept_m": round(float(np.abs(ring_off[ring_keep]).max()), 4)},
        "outer_edge": {"lines_with_edge": len(outer), "sectors": sectors,
                       "vertical_diameter_m": (round(sectors["top"]["median_r_m"] + sectors["bottom"]["median_r_m"], 4)
                                               if sectors["top"]["median_r_m"] and sectors["bottom"]["median_r_m"] else None)},
        "face_normal_local": [round(float(v), 5) for v in normal],
        "face_tilt_from_plus_y_deg": round(math.degrees(math.acos(min(1.0, float(normal[1])))), 3),
        "face_plane_y_at_centre_m": round(face_y, 4),
        "inner_disc_relief": {"points": len(disc_pts), "max_abs_residual_m": round(float(np.abs(residual).max()), 4),
                              "share_over_limit": round(float((np.abs(residual) > RELIEF_LIMIT).mean()), 4),
                              "limit_m": RELIEF_LIMIT},
        "hub": {"points_2mm": len(hub_pts),
                "centre_xz_m": [round(float(v), 4) for v in hub_pts[:, [0, 2]].mean(axis=0)] if len(hub_pts) else None,
                "equivalent_radius_m": round(math.sqrt(len(hub_pts) * 0.002 ** 2 / math.pi), 4) if len(hub_pts) else None,
                "front_y_m": round(float(hub_pts[:, 1].max()), 4) if len(hub_pts) else None,
                "offset_from_centre_xz_m": ([round(float(hub_pts[:, 0].mean()) - xc, 4), round(float(hub_pts[:, 2].mean()) - zc, 4)]
                                            if len(hub_pts) else None)},
        "numerals_ring": {"r_m": list(NUMERALS_RING), "max_front_y_m": numerals_y, "max_raise_m": numerals_raise},
        "rim": {"r_m": [NUMERALS_RING[1], round(radius - 0.01, 3)], "max_front_y_m": rim_y, "max_raise_m": rim_raise},
        "max_front_y_within_dial_m": sweep_y,
        "inner_disc_colour": {"samples": len(rgb), "median_rgb": [round(float(v), 3) for v in median],
                              "differ_threshold": STREAK_COLOUR, "share_differs": round(float(differs.mean()), 4),
                              "radial_lines": STREAK_ANGLES, "max_share_on_one_line": round(float(share.max()), 4),
                              "line_of_max_deg": round(360.0 * int(share.argmax()) / STREAK_ANGLES, 1)},
        "w09": {"dial_centre_face": w09, "outer_diameter_m": 2.29,
                "centre_diff_m": [round(xc - w09[0], 4), round(face_y - w09[1], 4), round(zc - w09[2], 4)],
                "rim_top_front": row["derived"]["points_local_m"]["dial_rim_top_front"]},
    }
    if w06 is not None:
        parts = {p["part_id"]: p for p in w06["parts"]}
        hour = parts.get(f"{W06_ASSET}_HourHandPivot", {}).get("pivot_local")
        minute = parts.get(f"{W06_ASSET}_MinuteHandPivot", {}).get("pivot_local")
        bell = parts.get(f"{W06_ASSET}_BellPivot", {}).get("pivot_local")
        bell_column = []
        if bell is not None:
            for x in np.arange(bell[0] - 0.25, bell[0] + 0.25 + 1e-9, 0.05):
                for z in np.arange(10.5, 11.5 + 1e-9, 0.05):
                    hit = surface.front_hit(float(x), float(z))
                    if hit is not None:
                        bell_column.append(hit[0][1])
        out["w06"] = {
            "manifest": rel(W06_MANIFEST),
            "hour_hand_pivot": hour,
            "minute_hand_pivot": minute,
            "axis_offset_xz_m": ([round(hour[0] - xc, 4), round(hour[2] - zc, 4)] if hour else None),
            "axis_offset_m": (round(math.hypot(hour[0] - xc, hour[2] - zc), 4) if hour else None),
            "hour_pivot_in_front_of_dial_face_m": (round(hour[1] - face_y, 4) if hour else None),
            "hour_pivot_in_front_of_max_dial_y_m": (round(hour[1] - sweep_y, 4) if hour else None),
            "minute_pivot_in_front_of_max_dial_y_m": (round(minute[1] - sweep_y, 4) if minute else None),
            "placeholder_dial_outer_diameter_m": w06.get("replacement_slot", {}).get("dial_outer_diameter_m"),
            "bell_pivot": bell,
            "m07_front_y_behind_bell_m": ({"x_m": [round(bell[0] - 0.25, 3), round(bell[0] + 0.25, 3)], "z_m": [10.5, 11.5],
                                           "min": round(min(bell_column), 3), "max": round(max(bell_column), 3)}
                                          if bell_column else None),
        }
    return out


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
        "origin": {"policy": row["decided"]["origin_policy"], "min_z": round(float(lo[2]), 4),
                   "box_centre_xy": [round(float(v), 4) for v in (lo[:2] + hi[:2]) / 2]},
        "object_transform_identity": bool(np.allclose(np.array(obj.matrix_world), np.eye(4), atol=1e-9)),
        "uv_cover": round(cover["area_sum"], 4),
        "uv_corners_in_unit_square": round(cover["corners_in_unit_square"], 4),
        "surface_area_m2": round(area, 1),
        "texels_per_m_at_color": round(math.sqrt(cover["area_sum"] * color_px * color_px / area), 1),
        "topology_welded": topo,
    }


def front_sun() -> object:
    """``render_review_images`` lights from -Y; the dial is at +Y, so add a front sun (as ``review_views.py``)."""
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


def workbench(path: Path, camera: dict, color_type: str, light: str, size: int = 640) -> np.ndarray:
    """One Workbench render. ``camera``: location, target, and lens_mm or ortho_scale. Returns the pixels."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.film_transparent = False
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    shading = scene.display.shading
    shading.color_type = color_type
    shading.light = light
    shading.single_color = (0.8, 0.8, 0.8)
    shading.show_cavity = color_type == "SINGLE"
    shading.cavity_type = "BOTH"
    shading.show_shadows = False
    shading.show_backface_culling = False
    shading.background_type = "VIEWPORT"
    shading.background_color = (0.05, 0.04, 0.09)
    data = bpy.data.cameras.new("Review_WB")
    cam = bpy.data.objects.new("Review_WB", data)
    scene.collection.objects.link(cam)
    previous = scene.camera
    scene.camera = cam
    try:
        if "ortho_scale" in camera:
            data.type = "ORTHO"
            data.ortho_scale = camera["ortho_scale"]
        else:
            data.lens = camera["lens_mm"]
        data.clip_end = 200.0
        cam.location = Vector(camera["location"])
        cam.rotation_euler = (Vector(camera["target"]) - Vector(camera["location"])).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
    finally:
        scene.camera = previous
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(data, do_unlink=True)
    return read_png(path)


def draw_marks(px: np.ndarray, dial: dict, w06_axis: list[float] | None, ortho_centre: tuple[float, float]) -> np.ndarray:
    """Marks on a straight-on orthographic tile: the measured centre (magenta cross), the outer diameter and the
    inner ring circles around it (magenta), the hub's centre (yellow dot) and W06's hand axis (cyan dot). The camera
    looks -Y with +Z up, so the image's right is local -X."""
    h, w = px.shape[:2]
    ppm = w / DIAL_VIEW
    cx, cz = ortho_centre

    def to_px(x: float, z: float) -> tuple[float, float]:
        return w / 2 - (x - cx) * ppm, h / 2 + (z - cz) * ppm

    out = px.copy()
    yy, xx = np.mgrid[0:h, 0:w]
    col, row = to_px(dial["centre_local_m"][0], dial["centre_local_m"][2])
    dist = np.hypot(xx - col, yy - row)
    rings = np.zeros((h, w), dtype=bool)
    for r_m in (dial["outer_diameter_m"] / 2, dial["inner_ring_fit"]["radius_m"]):
        rings |= np.abs(dist - r_m * ppm) <= 1.5
    cross = ((np.abs(xx - col) <= 1) & (np.abs(yy - row) <= 14)) | ((np.abs(yy - row) <= 1) & (np.abs(xx - col) <= 14))
    out[rings | cross, :3] = (1.0, 0.1, 0.9)
    for point, colour in ((dial["hub"]["centre_xz_m"], (1.0, 0.9, 0.0)),
                          (None if w06_axis is None else [w06_axis[0], w06_axis[2]], (0.1, 0.95, 1.0))):
        if point is not None:
            c2, r2 = to_px(point[0], point[1])
            out[np.hypot(xx - c2, yy - r2) <= 4, :3] = colour
    return out


def dial_sheets(dial: dict, w06_axis: list[float] | None, tmp: Path) -> tuple[Path, Path, list[dict]]:
    """The two dial close-ups the acceptance criteria ask for: textured (Cycles, and the colour image unlit with the
    measured circle) and shape only (straight on, and at a grazing angle that shows anything standing off the face)."""
    xc, yc, zc = dial["centre_local_m"]
    lens = 50.0
    distance = DIAL_VIEW / 2 / math.tan(math.atan(18.0 / lens))
    front = {"location": (xc, yc + distance, zc), "target": (xc, yc, zc), "lens_mm": lens}
    grazing = {"location": (xc + 2.6, yc + 2.0, zc + 0.9), "target": (xc, yc, zc), "lens_mm": lens}
    ortho = {"location": (xc, yc + 6.0, zc), "target": (xc, yc, zc), "ortho_scale": DIAL_VIEW}
    cycles = render_review_images([{"filepath": tmp / "dial_cycles.png", **front}], width=640, height=640, samples=48)[0]
    flat = workbench(tmp / "dial_flat.png", ortho, "TEXTURE", "FLAT")
    flat = draw_marks(flat, dial, w06_axis, (xc, zc))
    textured = grid_sheet([[cycles, flat]], REVIEW / f"{KEY}_dial_textured.png")
    shape_front = workbench(tmp / "dial_shape_front.png", front, "SINGLE", "STUDIO")
    shape_grazing = workbench(tmp / "dial_shape_grazing.png", grazing, "SINGLE", "STUDIO")
    shape = grid_sheet([[shape_front, shape_grazing]], REVIEW / f"{KEY}_dial_shape.png")
    cameras = [{"image": rel(textured), "tiles": ["Cycles, front", "Workbench FLAT texture, orthographic, marks"],
                "front": front, "orthographic": ortho},
               {"image": rel(shape), "tiles": ["Workbench SINGLE + cavity, front", "Workbench SINGLE + cavity, grazing"],
                "front": front, "grazing": grazing}]
    return textured, shape, cameras


CLOSEUPS = [
    # name, camera location, target, lens (local metres; the dial and the stairs are at +Y)
    ("dial", (1.3, 6.0, 8.8), (0.0, 0.35, 8.1), 50.0),
    ("entrance", (1.8, 10.0, 3.2), (0.0, 2.0, 2.0), 35.0),
    ("orbit_ring", (6.5, 6.5, 9.0), (1.5, 0.5, 7.6), 35.0),
    ("spire", (3.5, 8.0, 14.0), (0.0, 0.0, 12.0), 35.0),
    ("rock_base", (7.5, 7.0, 2.2), (3.0, 2.5, 0.8), 35.0),
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
CULLED_TILES = [[("back", "+Y (front, dial)"), ("front", "-Y (back)"), ("right", "+X")],
                [("left", "-X"), ("top", "+Z (top)"), ("bottom", "-Z (bottom)")]]


def backface_sheet(obj, tmp: Path) -> tuple[Path, dict]:
    culling = meshops.backface_check(obj, tmp / "cull")
    culling["view_camera_side"] = {view: side for row in CULLED_TILES for view, side in row}
    sheet = grid_sheet([[tmp / "cull" / f"cull_{view}_1.png" for view, _ in row] for row in CULLED_TILES],
                       REVIEW / f"{KEY}_backface_culled.png")
    return sheet, culling


def manifest(row: dict, checks: dict, textures: dict, w06: dict | None) -> dict:
    dims = checks["dimensions_m"]
    dial = checks["dial"]
    hint = row["decided"]["placement_hint"]
    placeholder = None
    if w06 is not None:
        slot = w06.get("replacement_slot", {})
        placeholder = {"manifest": rel(W06_MANIFEST), "asset_id": W06_ASSET,
                       "visual_root_part": slot.get("visual_root_part"),
                       "hide_on_replacement": slot.get("hide_on_replacement", []),
                       "keep_separate_parts": slot.get("keep_separate_parts", [])}
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
            "script_file": "modeling/M07/build.py",
            "origin_policy": row["decided"]["origin_policy"],
            "origin_world": [0.0, 0.0, 0.0],
            "placement_hint": hint,
            "forward_local": "+Y",
            "dimensions_m": {"width": dims["width_x"], "depth": dims["depth_y"], "height": dims["height_z"]},
            "bounds_local": checks["bounds_m"],
            "parts": [{"part_id": NAME, "role": "asset_root", "parent_part": None, "origin_policy": "ground_center",
                       "pivot_local": [0.0, 0.0, 0.0]}],
            "hierarchy": {"asset_root": NAME, "motion_roots": [], "visual_roots": [NAME], "attachment_points": []},
            "dial": {"centre_local_m": dial["centre_local_m"], "outer_diameter_m": dial["outer_diameter_m"],
                     "face_normal_local": dial["face_normal_local"], "hands": "none (W06 parts)",
                     "source": "review/M07/checks.json dial"},
            "materials": [f"MAT_{KEY}_ClockTower"],
            "textures": [info["file"] for info in textures.values() if "file" in info],
            "metrics": {"measured": True, "measurement_source": "blender_scene", "triangles": checks["triangles"],
                        "vertices": checks["vertices"], "materials_count": 1, "objects_count": 1},
            "export_result": {"status": "unexported", "bundle_dir": None, "apply_plan": None, "report_file": None},
            "replacement": {
                "is_placeholder": False,
                "modifiable": True,
                "future_target": None,
                "replaces_placeholder": placeholder,
                "notes": (
                    "Meshy の M07 を仕上げた差し替え用の見た目（Spec §6.3 の VisualRoot に入れる静的なモデル）。P2（W08 の後）で "
                    f"W06 の仮モデル {W06_ASSET} の本体（replaces_placeholder.visual_root_part）だけと差し替え、仮の文字盤は隠し、"
                    "針・鐘・腕木は W06 の部品を残す。origin_world はアセットのローカル原点で、ワールドの位置と向きは W06 の配置"
                    f"（W09 の推奨 placement_hint: {hint['position']}、Z {hint['rotation_z_deg']}°）。原点は岩の台座の底面の中央（z=0）、"
                    f"正面（文字盤と階段）は +Y（Resonite の +Z）。文字盤の中心は {dial['centre_local_m']}、外径 "
                    f"{dial['outer_diameter_m']} m、面の法線 {dial['face_normal_local']}（針は形にも画像にも無い）。発光（窓・ランタン）"
                    "は焼き込まず、コライダーも含めない（P2・P3 で Resonite 側に付ける）"
                ),
            },
        }],
    }


def main() -> None:
    row = load_row()
    w06 = load_w06()
    obj, textures = build_asset(row)
    checks = shape_checks(obj, row)
    color = read_png(TEX_DIR / f"{NAME}_color.png")
    checks["dial"] = dial_checks(Surface(obj), row, color, w06)
    bpy.context.preferences.filepaths.save_version = 0  # no M07.blend1 backup (as finish.py)
    save_blend(BLEND, pack_images=True)
    counts = {k: len(getattr(bpy.data, k)) for k in ("objects", "meshes", "materials", "images", "collections")}

    REVIEW.mkdir(parents=True, exist_ok=True)
    w06_axis = None
    if w06 is not None:
        w06_axis = next((p["pivot_local"] for p in w06["parts"] if p["part_id"] == f"{W06_ASSET}_HourHandPivot"), None)
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        sun = front_sun()
        views = views_sheet(obj, tmp)
        dial_textured, dial_shape, dial_cameras = dial_sheets(checks["dial"], w06_axis, tmp)
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
        "review_images": [rel(p) for p in (views, dial_textured, dial_shape, compare, uv_image, culled)],
        "dial_cameras": dial_cameras,
        "closeups": [{"name": n, "camera": loc, "target": tgt, "lens_mm": lens} for n, loc, tgt, lens in CLOSEUPS],
    })
    (REVIEW / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest(row, checks, textures, w06), ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"built {rel(BLEND)}: triangles={checks['triangles']} dims={checks['dimensions_m']} "
          f"uv_cover={checks['uv_cover']} dial={checks['dial']['centre_local_m']} d={checks['dial']['outer_diameter_m']} "
          f"counts={counts}")


if __name__ == "__main__":
    main()
