"""Rebuild the finished M04 witch's candy workshop exterior (W09-M04, #17) from the received Meshy GLB.

Run in the project directory (``docs/conventions.md`` §7.1):
    resoloop blender run modeling/M04/build.py --json

Outputs (``.blend`` and textures are not committed; ``docs/conventions.md`` §8):
- ``blender/M04/M04.blend`` with one object ``M04_WitchCandyWorkshop_001`` in the collection ``M04``, and its textures in
  ``blender/M04/textures/`` (also packed in the ``.blend``)
- ``review/M04/``: ``M04_views.png`` (four sides, 1.8 m figure), ``M04_compare_source.png`` (close-ups, the source on
  the left and the finished asset on the right, both without emission), ``M04_night_glow.png`` (four sides at night:
  only the windows glow), ``M04_night_closeups.png`` (the window close-ups at night), ``M04_emission_uv.png`` (the
  emission image over the darkened colour image), ``M04_uv_layout.png`` (UV cover on the colour image),
  ``M04_backface_culled.png`` (six sides with back faces hidden, as Resonite draws a single-sided material) and
  ``checks.json`` (the measurements the acceptance criteria of #17 ask for)
- ``assets/manifest/M04.json``; ``export_result`` is ``exported`` when ``exports/M04/bundle`` holds an export

Placement, naming, texture sizes (colour 2048, data maps 1024) and the material for ``--pack-pbr`` come from W09
(``assets/meshy/received.json`` row ``M04``, ``modeling/meshy/finish.py``). No reduction (the row's
``budget.triangles_max`` is the source count), the original normals are kept and the mesh stays single-sided
(``double_sided``). The door is a relief and is not separated (``split_and_attach``).

Window glow (``split_and_attach``: the windows are relief and image, so the glow is an emission image painted only
on the window glass): every pane in ``WINDOWS`` is a rectangle with an elliptical arch on top, measured on
orthographic views of the placed source (local metres, seen from its side), with the depth range of the glass along
the side's outward axis. A texel of the emission image glows when its surface point lies inside a pane's outline and
depth range and is the first surface a ray from that side meets (columns, icing and the awning in front stay dark).
Within a pane, bright wood mullions glow at ``MULLION_WEIGHT``. The glow colour is warm amber mixed with the albedo,
so the candies behind the glass keep their tint. The emission image is ``EMISSION_PX`` px (sRGB) on the Principled
BSDF's Emission Color with Emission Strength 1; Resonite controls the glow through the material's EmissiveColor.
"""

from __future__ import annotations

import colorsys
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

KEY = "M04"
NAME = "M04_WitchCandyWorkshop_001"  # the ID W04 (#6) wrote as future_target of CCD_M04_CandyWorkshopProxy_001
PLACEHOLDER = "CCD_M04_CandyWorkshopProxy_001"  # W04's stand-in in assets/manifest/C_candy.json
RECEIVED = PROJECT_ROOT / "assets" / "meshy" / "received.json"
BLEND = PROJECT_ROOT / "blender" / KEY / f"{KEY}.blend"
TEX_DIR = PROJECT_ROOT / "blender" / KEY / "textures"
REVIEW = PROJECT_ROOT / "review" / KEY
MANIFEST = PROJECT_ROOT / "assets" / "manifest" / f"{KEY}.json"
BUNDLE = PROJECT_ROOT / "exports" / KEY / "bundle"

EMISSION_PX = 1024  # 48.7 px/m on this asset; the glow needs no finer detail than the 2 cm mullions
EMISSION_STRENGTH = 1.0
SUPERSAMPLE = 2  # sub-samples per texel side, for soft pane outlines
VISIBLE_TOLERANCE = 0.015  # m: a texel point is visible when the first hit from its side is this close to it
MULLION_WEIGHT = 0.15
GLOW_AMBER = np.array([1.0, 0.62, 0.22])
GUTTER_DILATION = 2  # px the glow spreads into texels no UV triangle covers (mip-map seams)

# side -> (depth axis, outward sign, across axis). "front" is +Y (Resonite +Z), "right" is +X.
SIDES = {"front": (1, 1.0, 0), "back": (1, -1.0, 0), "right": (0, 1.0, 1), "left": (0, -1.0, 1)}

# Window panes (local metres after placement). across = x on front/back, y on right/left; z_spring is where the arch
# starts (equal to z_top for a flat top); depth = the glass's range along the side's outward axis (sign * coordinate),
# from the first-hit depths on a 2 cm grid inside the outline (columns, icing drips and the awning lie outside it).
WINDOWS = [
    # id, side, across (lo, hi), z_bottom, z_spring, z_top, depth (lo, hi)
    ("front_bay_left", "front", (2.661, 2.895), 0.755, 1.561, 1.810, (1.60, 2.26)),
    ("front_bay_centre", "front", (1.811, 2.500), 0.748, 1.517, 1.861, (2.15, 2.50)),
    ("front_bay_right", "front", (1.211, 1.606), 0.755, 1.561, 1.810, (2.00, 2.50)),
    ("front_shop", "front", (-2.770, -1.740), 0.790, 1.400, 1.400, (1.95, 2.20)),
    ("front_upper_a", "front", (2.350, 2.624), 2.866, 3.213, 3.349, (1.10, 1.45)),
    ("front_upper_main", "front", (1.130, 1.669), 2.916, 3.410, 3.685, (1.70, 1.95)),
    ("front_upper_b", "front", (0.043, 0.416), 2.866, 3.125, 3.312, (1.80, 2.00)),
    ("front_dormer", "front", (-2.471, -2.105), 3.124, 3.607, 3.732, (1.65, 1.86)),
    ("back_left", "back", (-2.114, -1.624), 0.837, 1.496, 1.730, (2.00, 2.20)),
    ("back_right", "back", (1.106, 1.641), 0.837, 1.481, 1.708, (2.00, 2.20)),
    ("right_bay_1", "right", (-0.547, -0.075), 0.758, 1.527, 1.768, (3.05, 3.56)),
    ("right_bay_2", "right", (0.090, 0.480), 0.758, 1.527, 1.790, (3.20, 3.42)),
    ("right_bay_3", "right", (0.957, 1.584), 0.747, 1.516, 1.812, (2.80, 3.10)),
    ("right_bay_4", "right", (1.781, 2.155), 0.747, 1.548, 1.801, (2.55, 2.97)),
    ("right_upper_a", "right", (-0.188, 0.186), 2.842, 3.201, 3.318, (3.00, 3.25)),
    ("right_upper_b", "right", (1.248, 1.453), 2.842, 3.100, 3.200, (2.25, 2.65)),
    ("left_side", "left", (0.018, 0.450), 0.814, 1.517, 1.751, (3.35, 3.60)),
]
# W09's window points (received.json derived.points_local_m) and the pane each one belongs to
W09_POINTS = {"bay_window_centre": "front_bay_centre", "shop_window_centre": "front_shop",
              "upper_window_centre": "front_upper_main", "dormer_window_centre": "front_dormer"}


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
    """Import the GLB into the current scene and return its one mesh object (the confirmed M04 has one)."""
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


# --- window glow ----------------------------------------------------------------------------------------------------


def inside_outline(across: np.ndarray, z: np.ndarray, window: tuple) -> np.ndarray:
    _, _, (a0, a1), zb, zs, zt, _ = window
    inside = (across >= a0) & (across <= a1) & (z >= zb) & (z <= zt)
    if zt > zs:
        arch = z > zs
        ac, hw = (a0 + a1) / 2, (a1 - a0) / 2
        ellipse = ((across - ac) / hw) ** 2 + ((z - zs) / (zt - zs)) ** 2 <= 1.0
        inside &= ~arch | ellipse
    return inside


def glass_weight(rgb: np.ndarray) -> np.ndarray:
    """1 on glass, the candies behind it and the dark wood; ``MULLION_WEIGHT`` on the bright tan wood of the mullions
    (warm hue, saturation 0.3..0.62, brightness ramping from 0.74 to 0.86). The pale candies (saturation below 0.3)
    keep 1. Nothing else is judged by colour: columns, icing and the awning are left out by the depth range and the
    visibility test."""
    hsv = np.array([colorsys.rgb_to_hsv(*c) for c in rgb]) if len(rgb) else np.zeros((0, 3))
    hue, sat, val = hsv[:, 0] * 360.0, hsv[:, 1], hsv[:, 2]
    tan = (hue >= 15) & (hue <= 45) & (sat >= 0.3) & (sat < 0.62)
    mullion = tan * np.clip((val - 0.74) / 0.12, 0.0, 1.0)
    return 1.0 - (1.0 - MULLION_WEIGHT) * mullion


def glow_colour(rgb: np.ndarray) -> np.ndarray:
    return np.clip(rgb * 1.4 + GLOW_AMBER * 0.35, 0.0, 1.0)


def colour_at_emission_px(color_px: np.ndarray) -> np.ndarray:
    """The colour image (H x W x 4, bottom-up) averaged down to ``EMISSION_PX`` (same texel grid)."""
    h, w = color_px.shape[:2]
    f = h // EMISSION_PX
    return color_px[:, :, :3].reshape(EMISSION_PX, f, EMISSION_PX, f, 3).mean(axis=(1, 3))


def window_glow(obj, color_px: np.ndarray) -> tuple[np.ndarray, dict]:
    """The emission image (``EMISSION_PX`` square, bottom-up rows, RGB 0..1) and per-pane statistics."""
    positions, uv = meshops.triangle_arrays(obj)
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    co = meshops.vertex_array(obj)
    reach = float(np.abs(co).max()) + 1.0
    colour = colour_at_emission_px(color_px)
    n = EMISSION_PX
    s = SUPERSAMPLE
    acc = np.zeros((n, n), dtype=np.float64)  # sub-samples that glow, weighted
    stats = {}
    offsets = (np.arange(s) + 0.5) / s
    tri_lo, tri_hi = positions.min(axis=1), positions.max(axis=1)
    for window in WINDOWS:
        wid, side, (a0, a1), zb, _, zt, (d0, d1) = window
        axis, sign, across = SIDES[side]
        depth_lo = np.minimum(sign * tri_lo[:, axis], sign * tri_hi[:, axis])
        depth_hi = np.maximum(sign * tri_lo[:, axis], sign * tri_hi[:, axis])
        near = ((tri_hi[:, across] >= a0) & (tri_lo[:, across] <= a1) & (tri_hi[:, 2] >= zb) & (tri_lo[:, 2] <= zt)
                & (depth_hi >= d0) & (depth_lo <= d1))
        texels = set()
        samples = glowing = 0
        for t in np.nonzero(near)[0]:
            tri_uv = uv[t] * n
            i0, j0 = np.floor(tri_uv.min(axis=0)).astype(int)
            i1, j1 = np.floor(tri_uv.max(axis=0)).astype(int)
            gi, gj = np.meshgrid(np.arange(max(i0, 0), min(i1, n - 1) + 1), np.arange(max(j0, 0), min(j1, n - 1) + 1))
            if gi.size == 0:
                continue
            si = (gi[..., None, None] + offsets[None, None, :, None]).repeat(s, axis=3).reshape(-1)
            sj = (gj[..., None, None] + offsets[None, None, None, :]).repeat(s, axis=2).reshape(-1)
            ti = np.repeat(gi.reshape(-1), s * s)
            tj = np.repeat(gj.reshape(-1), s * s)
            p = np.stack([si, sj], axis=1)
            v0, v1, v2 = tri_uv
            den = (v1[1] - v2[1]) * (v0[0] - v2[0]) + (v2[0] - v1[0]) * (v0[1] - v2[1])
            if abs(den) < 1e-12:
                continue
            b0 = ((v1[1] - v2[1]) * (p[:, 0] - v2[0]) + (v2[0] - v1[0]) * (p[:, 1] - v2[1])) / den
            b1 = ((v2[1] - v0[1]) * (p[:, 0] - v2[0]) + (v0[0] - v2[0]) * (p[:, 1] - v2[1])) / den
            b2 = 1.0 - b0 - b1
            inside = (b0 >= -1e-6) & (b1 >= -1e-6) & (b2 >= -1e-6)
            if not inside.any():
                continue
            bary = np.stack([b0, b1, b2], axis=1)[inside]
            pts = bary @ positions[t]
            ti, tj = ti[inside], tj[inside]
            depth = sign * pts[:, axis]
            keep = inside_outline(pts[:, across], pts[:, 2], window) & (depth >= d0) & (depth <= d1)
            for k in np.nonzero(keep)[0]:
                origin = Vector(pts[k].tolist())
                origin[axis] = sign * reach
                direction = Vector((0.0, 0.0, 0.0))
                direction[axis] = -sign
                loc, _, _, _ = bvh.ray_cast(origin, direction, 2 * reach)
                samples += 1
                if loc is None or abs(sign * loc[axis] - depth[k]) > VISIBLE_TOLERANCE:
                    continue
                glowing += 1
                acc[tj[k], ti[k]] += 1.0
                texels.add((int(tj[k]), int(ti[k])))
        stats[wid] = {"side": side, "triangles_near": int(near.sum()), "samples_inside_outline": samples,
                      "samples_visible": glowing, "texels": len(texels)}
    coverage = np.clip(acc / (s * s), 0.0, 1.0)
    painted = coverage > 0
    weight = np.zeros((n, n))
    weight[painted] = glass_weight(colour[painted])
    emission = np.zeros((n, n, 3))
    emission[painted] = glow_colour(colour[painted]) * (coverage[painted] * weight[painted])[:, None]
    # gutter: spread into texels no UV triangle covers, so mip-maps do not darken the window edges
    occupied = metrics.occupancy(uv * 1.0, (0, 1), (0.0, 0.0), (1.0, 1.0), 1.0 / n)[:n, :n]
    for _ in range(GUTTER_DILATION):
        grown = emission.copy()
        free = ~occupied & (emission.max(axis=2) == 0)
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            shifted = np.roll(np.roll(emission, dj, axis=0), di, axis=1)
            grown[free] = np.maximum(grown[free], shifted[free])
        emission = grown
    summary = {
        "texels_glowing": int(painted.sum()),
        "texel_share": round(float(painted.mean()), 5),
        "mean_weight_on_painted": round(float(weight[painted].mean()), 3) if painted.any() else 0.0,
        "panes": stats,
    }
    return emission, summary


def add_emission(material, emission: np.ndarray) -> dict:
    """Save the emission image and wire it straight to Emission Color (the exporter's direct sRGB image)."""
    tree, bsdf = finish.principled_of(material)
    data = np.concatenate([emission, np.ones(emission.shape[:2] + (1,))], axis=2)
    path = TEX_DIR / f"{NAME}_emission.png"
    image = finish.save_png(f"{NAME}_emission", data, "sRGB", path, EMISSION_PX)
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.name = tex.label = f"{NAME}_emission"
    tex.image = image
    tex.interpolation = "Linear"
    tex.extension = "REPEAT"
    tree.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = EMISSION_STRENGTH
    return {"file": rel(path), "size": list(image.size), "strength": EMISSION_STRENGTH,
            "source": "window panes painted by modeling/M04/build.py (WINDOWS)"}


def set_emission_strength(obj, value: float) -> None:
    _, bsdf = finish.principled_of(obj.data.materials[0])
    bsdf.inputs["Emission Strength"].default_value = value


# --- build ----------------------------------------------------------------------------------------------------------


def build_asset(row: dict) -> tuple[object, dict, dict]:
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
    material = obj.data.materials[0]
    textures = finish.adapt_material(material, NAME, TEX_DIR, row["budget"]["color_px_max"], row["budget"]["data_px_max"])
    color_node, _ = finish.linked_image(finish.principled_of(material)[1].inputs["Base Color"])
    emission, glow = window_glow(obj, finish.pixels(color_node.image).copy())
    textures["emission"] = add_emission(material, emission)
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)
    for role, info in textures.items():
        if "file" in info and role != "emission":
            info["file"] = rel(TEX_DIR.parent / info["file"])
    return obj, textures, glow


def shape_checks(obj, row: dict) -> dict:
    co = meshops.vertex_array(obj)
    lo, hi = co.min(axis=0), co.max(axis=0)
    expected = row["derived"]["bounds_local_m"]
    positions, uv = meshops.triangle_arrays(obj)
    cover = metrics.uv_cover(uv)
    area = metrics.triangle_area_sum(positions)
    color_px = row["budget"]["color_px_max"]
    points = row["derived"]["points_local_m"]
    windows = {w[0]: w for w in WINDOWS}
    w09_points = {}
    for name, pane in W09_POINTS.items():
        p = points[name]
        window = windows[pane]
        axis, sign, across = SIDES[window[1]]
        w09_points[name] = {"point": p, "pane": pane,
                            "inside_outline": bool(inside_outline(np.array([p[across]]), np.array([p[2]]), window)[0])}
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
        "texels_per_m_at_emission": round(math.sqrt(cover["area_sum"] * EMISSION_PX * EMISSION_PX / area), 1),
        "w09_window_points": w09_points,
        "topology_welded": topo,
    }


# --- review images --------------------------------------------------------------------------------------------------


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


def side_views(obj, tmp: Path, prefix: str, figure_offset: float = 0.85) -> list[dict]:
    """Cameras for the four sides (+Y front, +X, -Y back, -X), framing the asset and a figure off the front-right."""
    co = meshops.vertex_array(obj)
    lo, hi = co.min(axis=0), co.max(axis=0)
    lens = 85.0
    half_fov = math.atan(18.0 / lens)
    span = {0: (float(lo[0]), float(hi[0]) + figure_offset), 1: (float(lo[1]), float(hi[1]) + figure_offset)}
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
        views.append({"filepath": tmp / f"{prefix}_{name}.png", "location": tuple(centre + np.asarray(direction) * distance),
                      "target": tuple(centre), "lens_mm": lens})
    return views


def views_sheet(obj, tmp: Path) -> Path:
    """Four sides (+Y front, +X, -Y back, -X) with a 1.8 m figure off the front-right corner."""
    from modeling.meshy.review_views import add_figure

    co = meshops.vertex_array(obj)
    hi = co.max(axis=0)
    figure = add_figure(float(hi[0]) + 0.6, float(hi[1]) + 0.6, 0.0)
    paths = render_review_images(side_views(obj, tmp, "view"), width=640, height=640, samples=32)
    for o in figure:
        mesh = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    return grid_sheet([paths[:2], paths[2:]], REVIEW / f"{KEY}_views.png")


def night_render(views: list[dict], size: tuple[int, int]) -> list[Path]:
    """Cycles under a faint moon and a dark sky, so only the emission (the windows) is bright."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    if hasattr(scene.cycles, "use_denoising"):
        scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    prev_world, prev_camera = scene.world, scene.camera
    world = bpy.data.worlds.new("Review_Night")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.01, 0.012, 0.03, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    scene.world = world
    moon = bpy.data.objects.new("Review_Moon", bpy.data.lights.new("Review_Moon", type="SUN"))
    moon.data.energy = 0.08
    moon.data.color = (0.6, 0.7, 1.0)
    moon.rotation_euler = (math.radians(50), 0.0, math.radians(30))
    scene.collection.objects.link(moon)
    cam = bpy.data.objects.new("Review_NightCamera", bpy.data.cameras.new("Review_NightCamera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    paths = []
    try:
        for view in views:
            cam.data.lens = view["lens_mm"]
            cam.location = Vector(view["location"])
            cam.rotation_euler = (Vector(view["target"]) - cam.location).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str(view["filepath"])
            bpy.ops.render.render(write_still=True)
            paths.append(Path(view["filepath"]))
    finally:
        scene.world, scene.camera = prev_world, prev_camera
        for o, store in ((moon, bpy.data.lights), (cam, bpy.data.cameras)):
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            store.remove(data)
        bpy.data.worlds.remove(world)
    return paths


def night_sheets(obj, tmp: Path) -> tuple[Path, Path]:
    """The four sides at night, and the window close-ups (``CLOSEUPS`` without the hat) at night."""
    sides = night_render(side_views(obj, tmp, "night", figure_offset=0.0), (640, 640))
    near = [{"filepath": tmp / f"night_{n}.png", "location": loc, "target": tgt, "lens_mm": lens}
            for n, loc, tgt, lens in CLOSEUPS if n != "hat"]
    close = night_render(near, (640, 480))
    return (grid_sheet([sides[:2], sides[2:]], REVIEW / f"{KEY}_night_glow.png"),
            grid_sheet([close[i:i + 2] for i in range(0, len(close), 2)], REVIEW / f"{KEY}_night_closeups.png"))


CLOSEUPS = [
    # name, camera location, target, lens (local metres; the front is at +Y)
    ("door", (0.5, 6.6, 1.4), (0.0, 2.1, 1.1), 40.0),
    ("bay_window", (2.6, 5.0, 1.4), (2.1, 2.4, 1.2), 40.0),
    ("upper_windows", (1.0, 5.6, 3.4), (1.2, 1.9, 3.2), 40.0),
    ("dormer_shop", (-2.4, 6.4, 2.4), (-2.3, 2.2, 2.2), 30.0),
    ("hat", (1.5, 9.0, 7.6), (0.6, 0.5, 5.4), 35.0),
    ("right_bay", (6.8, 0.9, 1.6), (3.2, 0.8, 1.3), 35.0),
    ("back_windows", (0.0, -8.0, 1.8), (0.0, -2.6, 1.3), 30.0),
]


def closeup_views(prefix: str, tmp: Path) -> list[Path]:
    views = [{"filepath": tmp / f"{prefix}_{n}.png", "location": loc, "target": tgt, "lens_mm": lens}
             for n, loc, tgt, lens in CLOSEUPS]
    return render_review_images(views, width=640, height=480, samples=32)


def scaled(path: Path, size: int) -> np.ndarray:
    img = bpy.data.images.load(str(path), check_existing=False)
    img.scale(size, size)
    px = np.empty(size * size * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(size, size, 4)


def uv_layout(obj) -> tuple[Path, float]:
    """The colour image at 1024 px with the texels no UV triangle covers darkened."""
    _, uv = meshops.triangle_arrays(obj)
    size = 1024
    occupied = metrics.occupancy(uv, (0, 1), (0.0, 0.0), (1.0, 1.0), 1.0 / size)[:size, :size]
    px = scaled(TEX_DIR / f"{NAME}_color.png", size)
    px[~occupied, :3] = px[~occupied, :3] * 0.15 + np.array([0.35, 0.0, 0.35]) * 0.85
    return write_png(px, REVIEW / f"{KEY}_uv_layout.png"), round(float(occupied.mean()), 4)


def emission_uv() -> Path:
    """The emission image added to the colour image darkened to 25 %: where on the texture the windows glow."""
    size = EMISSION_PX
    base = scaled(TEX_DIR / f"{NAME}_color.png", size)
    glow = scaled(TEX_DIR / f"{NAME}_emission.png", size)
    base[:, :, :3] = np.clip(base[:, :, :3] * 0.25 + glow[:, :, :3], 0.0, 1.0)
    return write_png(base, REVIEW / f"{KEY}_emission_uv.png")


# backface_check names its views after the Meshy source (its "front" camera is at -Y); this asset's front is at +Y.
CULLED_TILES = [[("back", "+Y (front)"), ("front", "-Y (back)"), ("right", "+X")],
                [("left", "-X"), ("top", "+Z (top)"), ("bottom", "-Z (bottom)")]]


def backface_sheet(obj, tmp: Path) -> tuple[Path, dict]:
    culling = meshops.backface_check(obj, tmp / "cull")
    culling["view_camera_side"] = {view: side for row in CULLED_TILES for view, side in row}
    sheet = grid_sheet([[tmp / "cull" / f"cull_{view}_1.png" for view, _ in row] for row in CULLED_TILES],
                       REVIEW / f"{KEY}_backface_culled.png")
    return sheet, culling


# --- manifest -------------------------------------------------------------------------------------------------------


def manifest(row: dict, checks: dict, textures: dict) -> dict:
    exported = (BUNDLE / "report.json").is_file() and (BUNDLE / "model.apply.json").is_file()
    dims = checks["dimensions_m"]
    points = row["derived"]["points_local_m"]
    hint = row["decided"]["placement_hint"]
    return {
        "schema_version": "1.0",
        "key": KEY,
        "updated_at": datetime.datetime.now(datetime.UTC).date().isoformat(),
        "assets": [{
            "asset_id": NAME,
            "key": KEY,
            "category": "architecture",
            "area_id": row["decided"]["area_id"],
            "collection": KEY,
            "blend_file": rel(BLEND),
            "script_file": "modeling/M04/build.py",
            "origin_policy": row["decided"]["origin_policy"],
            "origin_world": [0.0, 0.0, 0.0],
            "dimensions_m": {"width": dims["width_x"], "depth": dims["depth_y"], "height": dims["height_z"]},
            "bounds_local": checks["bounds_m"],
            "parts": [{"part_id": NAME, "role": "asset_root", "parent_part": None, "origin_policy": "ground_center",
                       "pivot_local": [0.0, 0.0, 0.0]}],
            "hierarchy": {"asset_root": NAME, "motion_roots": [], "visual_roots": [NAME], "attachment_points": []},
            "materials": [f"MAT_{KEY}_WitchCandyWorkshop"],
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
                    "Finished Meshy visual for the VisualRoot of the C_candy witch's candy workshop exterior (Spec 6.3); "
                    f"in P2 it replaces W04's placeholder {PLACEHOLDER} (assets/manifest/C_candy.json, whose "
                    f"future_target is {NAME}). origin_world is the asset-local origin: the world position is W04's "
                    f"({PLACEHOLDER} at {hint['position']}, rotation_z {hint['rotation_z_deg']}, as received.json "
                    "placement_hint; the front looks west to the plaza). "
                    "Origin = bottom centre (z=0), front = +Y (Resonite +Z). Building exterior only: no stalls, "
                    "display, cauldron, candy machines or brooms (W04). The door is a relief and does not open "
                    f"(door bottom {points['door_bottom_centre']}). Window glow: one material, the emission image "
                    f"{NAME}_emission.png paints only the 17 window panes (modeling/M04/build.py WINDOWS); control it "
                    "with the material's EmissiveColor in Resonite (black = off). No collider is part of this visual."
                ),
            },
        }],
    }


def main() -> None:
    row = load_row()
    obj, textures, glow = build_asset(row)
    checks = shape_checks(obj, row)
    bpy.context.preferences.filepaths.save_version = 0  # no M04.blend1 backup (as finish.py)
    save_blend(BLEND, pack_images=True)
    counts = {k: len(getattr(bpy.data, k)) for k in ("objects", "meshes", "materials", "images", "collections")}

    REVIEW.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        night, night_close = night_sheets(obj, tmp)
        sun = front_sun()
        views = views_sheet(obj, tmp)
        uv_image, uv_texel_share = uv_layout(obj)
        glow_uv = emission_uv()
        culled, culling = backface_sheet(obj, tmp)
        set_emission_strength(obj, 0.0)  # compare the shape and the colour with the source, without the glow
        finished = closeup_views("finished", tmp)
        set_emission_strength(obj, EMISSION_STRENGTH)
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
        "window_glow": glow,
        "uv_texel_share_1024": uv_texel_share,
        "backface_check": culling,
        "blend_counts": counts,
        "blender": bpy.app.version_string,
        "review_images": [rel(p) for p in (views, compare, night, night_close, glow_uv, uv_image, culled)],
        "closeups": [{"name": n, "camera": loc, "target": tgt, "lens_mm": lens} for n, loc, tgt, lens in CLOSEUPS],
    })
    (REVIEW / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest(row, checks, textures), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"built {rel(BLEND)}: triangles={checks['triangles']} dims={checks['dimensions_m']} "
          f"uv_cover={checks['uv_cover']} glow_texels={glow['texels_glowing']} counts={counts}")


if __name__ == "__main__":
    main()
