"""Rebuild the finished M03 haunted mansion facade (W09-M03, #16) from the received Meshy GLB.

Run in the project directory (``docs/conventions.md`` §7.1):
    resoloop blender run modeling/M03/build.py --json
    Optional: --arg=--skip-review (no review images, for a quick rebuild)
Then export and validate with ``uv run python modeling/M03/export.py``.

Outputs (``.blend`` and textures are not committed; ``docs/conventions.md`` §8):
- ``blender/M03/M03.blend`` with one object ``M03_HauntedMansion_001`` in the collection ``M03``, and its textures in
  ``blender/M03/textures/`` (also packed in the ``.blend``)
- ``review/M03/``: ``M03_views.png`` (four sides, 1.8 m figure), ``M03_compare_source.png`` (close-ups, the source on
  the left and the finished asset on the right), ``M03_door_opening.png`` (the opening with the hinge lines in red,
  the threshold in green and the top in blue, drawn single-sided as Resonite does), ``M03_uv_layout.png`` (UV cover on
  the colour image), ``M03_backface_culled.png`` (six sides with back faces hidden) and ``checks.json`` (the
  measurements the acceptance criteria of #16 ask for)
- ``assets/manifest/M03.json``; ``export_result`` stays ``unexported`` until ``export.py`` fills it

Everything is decided by W09 in ``assets/meshy/received.json`` (row ``M03``) and done by W09's common finishing
(``modeling/meshy/finish.py``): placement, naming, texture sizes (colour 4096, data maps 2048) and the material for
``--pack-pbr``. No reduction (the row's ``budget.triangles_max`` is the source count), the original normals are kept
and the mesh stays single-sided (``double_sided``). The windows stay as they are (``split_and_attach``).

The one change to the shape is the door opening (``split_and_attach`` "入口"): the porch's back wall is a flat,
closed surface facing +Y. The opening keeps W09's width (1.618 m), top (z 2.962) and wall plane, but is centred on the
porch's central arch, measured from the shape (``central_arch``): W09's x put it 0.36 m off the arch, its left part
behind the next column. Its bottom is the wall's own bottom edge on the porch floor, which lies higher than W09's read
of the floor. The user chose both on 2026-10-31 (``checks.json`` ``door_opening.w09_difference``). The wall faces that
cross the two hinge lines and the top are bisected there, and the wall faces between them are deleted. Nothing is
added behind the opening: the entrance hall, the door frame and the leaves are W03's (#5). The build stops if the
rays through the opening do not pass, or the rays just outside it do not hit the wall.
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

import bmesh  # type: ignore
import bpy  # type: ignore
import numpy as np
from mathutils import Matrix, Vector  # type: ignore
from mathutils.bvhtree import BVHTree  # type: ignore

from modeling.lib.render import render_review_images
from modeling.lib.scene import reset_scene, save_blend
from modeling.meshy import finish, meshops, metrics

KEY = "M03"
NAME = "M03_HauntedMansion_001"
MATERIAL = "MAT_M03_HauntedMansion"
RECEIVED = PROJECT_ROOT / "assets" / "meshy" / "received.json"
BLEND = PROJECT_ROOT / "blender" / KEY / f"{KEY}.blend"
TEX_DIR = PROJECT_ROOT / "blender" / KEY / "textures"
REVIEW = PROJECT_ROOT / "review" / KEY
MANIFEST = PROJECT_ROOT / "assets" / "manifest" / f"{KEY}.json"
BUNDLE = PROJECT_ROOT / "exports" / KEY / "bundle"

# The porch's back wall: faces whose normal points to +Y within this band of W09's wall plane (y = 1.55). The wall's
# vertices lie at y 1.541..1.551; other faces near the plane are the floor and the ceiling (normals along z).
WALL_BAND_Y = 0.03
WALL_NORMAL_Y = 0.95
WALL_REACH_BELOW = 0.3  # wall faces may reach this far below W09's bottom (0.279) and still belong to the opening
EDGE_TOLERANCE = 0.002  # a vertex of a deleted face may lie this far outside the opening (after the bisect: ~0)
RAY_INSET = 0.03  # rays inside the opening start this far from its edges; the ring outside lies this far beyond them
SCAN_STEP = 0.002  # the measured edges of the opening (m)
CULL_PIXELS = 640  # backface_check views at 640 px (2.5 cm per pixel over 15 m), so the opening is about 65 px wide
# The cut adds triangles (the bisected faces become a triangle and a quad each); 18 on 2026-10-31. W09's
# budget.triangles_max is the source count, and the user accepted the excess the opening brings (#16, 2026-10-31).
# More than this many means the cut reached faces it should not have.
MAX_TRIANGLES_ADDED_BY_CUT = 40
# The central arch of the porch: rays from in front of the arcade (columns at y about 3.6..4.1) at walking heights.
ARCH_RAY_Y = 6.0
ARCH_SCAN_Z = (0.8, 1.2, 1.6, 2.0)  # below the hanging lanterns beside the arches
ARCH_SCAN_STEP = 0.005
ARCH_SCAN_HALF = 1.6  # x around W09's door centre (-0.335): covers the four columns (-2.13 .. +0.75)
ARCH_CLEAR_RANGE = (1.2, 1.7)  # m; the side arches are about 0.5 m, the central one about 1.4 m


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
    """Import the GLB into the current scene and return its one mesh object (the confirmed M03 has one)."""
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
    if obj.data.materials[0].name != MATERIAL:
        raise SystemExit(f"{NAME}: material is {obj.data.materials[0].name}, expected {MATERIAL}")
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)
    for info in textures.values():
        if "file" in info:
            info["file"] = rel(TEX_DIR.parent / info["file"])
    return obj, textures


# ---------------------------------------------------------------- the door opening


def door_w09(row: dict) -> dict:
    """W09's opening (local metres): x between the two hinge lines, z up to the top, on the wall plane y."""
    pts = row["derived"]["points_local_m"]
    a, b = pts["door_opening_left_bottom"], pts["door_opening_right_top"]
    return {"x_min": min(a[0], b[0]), "x_max": max(a[0], b[0]), "z_bottom_w09": min(a[2], b[2]),
            "z_top": max(a[2], b[2]), "wall_y": (a[1] + b[1]) / 2}


def _first_hit_is_wall(bvh, x: float, z: float, wall_y: float, origin_y: float) -> bool:
    """A ray at (x, z) from ``origin_y`` towards -Y first meets the back wall (within the band of its plane)."""
    loc, _, _, _ = bvh.ray_cast(Vector((x, origin_y, z)), Vector((0.0, -1.0, 0.0)), origin_y - wall_y + 0.3)
    return loc is not None and abs(loc.y - wall_y) <= WALL_BAND_Y


def central_arch(obj, row: dict) -> dict:
    """The clear span of the porch's central arch: rays from in front of the arcade (``ARCH_RAY_Y``) at walking
    heights reach the back wall between the columns. At each height the widest run of such rays is the central arch
    (the side arches are about 0.5 m wide); the clear span is the part common to all heights."""
    w = door_w09(row)
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    centre_w09 = (w["x_min"] + w["x_max"]) / 2
    xs = np.arange(centre_w09 - ARCH_SCAN_HALF, centre_w09 + ARCH_SCAN_HALF, ARCH_SCAN_STEP)
    spans = {}
    for z in ARCH_SCAN_Z:
        reach = [_first_hit_is_wall(bvh, float(x), z, w["wall_y"], ARCH_RAY_Y) for x in xs]
        runs, start = [], None
        for i, ok in enumerate(reach + [False]):
            if ok and start is None:
                start = i
            elif not ok and start is not None:
                runs.append((float(xs[start]), float(xs[i - 1])))
                start = None
        if not runs:
            raise SystemExit(f"{NAME}: no ray reaches the porch's back wall at z {z}")
        lo, hi = max(runs, key=lambda r: r[1] - r[0])
        spans[str(z)] = [round(lo, 4), round(hi, 4)]
    lo = max(v[0] for v in spans.values())
    hi = min(v[1] for v in spans.values())
    if not ARCH_CLEAR_RANGE[0] <= hi - lo <= ARCH_CLEAR_RANGE[1]:
        raise SystemExit(f"{NAME}: central arch clear span {hi - lo:.3f} m is not the arch ({spans})")
    return {"ray_origin_y": ARCH_RAY_Y, "scan_step_m": ARCH_SCAN_STEP, "clear_span_by_z": spans,
            "clear_span": [round(lo, 4), round(hi, 4)], "clear_width": round(hi - lo, 4),
            "centre_x": round((lo + hi) / 2, 4)}


def door_target(row: dict, arch: dict) -> dict:
    """The opening cut: W09's width, top and wall plane, centred on the central arch (the user's choice on
    2026-10-31; W09's x is off the arch by 0.36 m)."""
    w = door_w09(row)
    half = (w["x_max"] - w["x_min"]) / 2
    return {**w, "x_min": arch["centre_x"] - half, "x_max": arch["centre_x"] + half}


def _is_back_wall(face, t: dict) -> bool:
    if face.normal.y < WALL_NORMAL_Y or abs(face.calc_center_median().y - t["wall_y"]) > WALL_BAND_Y:
        return False
    xs = [v.co.x for v in face.verts]
    zs = [v.co.z for v in face.verts]
    return (max(xs) > t["x_min"] and min(xs) < t["x_max"] and max(zs) > t["z_bottom_w09"] - WALL_REACH_BELOW
            and min(zs) < t["z_top"])


def _crosses(face, axis: int, value: float) -> bool:
    vals = [v.co[axis] for v in face.verts]
    return min(vals) < value < max(vals)


def _bisect(bm, faces: list, axis: int, value: float) -> int:
    if not faces:
        return 0
    co = [0.0, 0.0, 0.0]
    no = [0.0, 0.0, 0.0]
    co[axis], no[axis] = value, 1.0
    edges = list({e for f in faces for e in f.edges})
    verts = list({v for f in faces for v in f.verts})
    bmesh.ops.bisect_plane(bm, geom=list(faces) + edges + verts, dist=1e-7, plane_co=co, plane_no=no)
    bm.normal_update()
    return len(faces)


def cut_door_opening(obj, row: dict, arch: dict) -> dict:
    """Bisect the porch's back wall at the opening's sides and top, then delete the wall faces inside the opening."""
    t = door_target(row, arch)
    triangles_before = meshops.triangles(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    wall_before = [f for f in bm.faces if _is_back_wall(f, t)]
    cuts = {}
    for label, axis, value in (("x_min", 0, t["x_min"]), ("x_max", 0, t["x_max"]), ("z_top", 2, t["z_top"])):
        faces = [f for f in bm.faces if _is_back_wall(f, t) and _crosses(f, axis, value)]
        if axis == 2:  # the top cuts only between the hinge lines (the faces were split there just before)
            faces = [f for f in faces if t["x_min"] < f.calc_center_median().x < t["x_max"]]
        cuts[label] = _bisect(bm, faces, axis, value)
    inside = []
    for f in bm.faces:
        c = f.calc_center_median()
        if _is_back_wall(f, t) and t["x_min"] < c.x < t["x_max"] and c.z < t["z_top"]:
            inside.append(f)
    if not inside:
        raise SystemExit(f"{NAME}: no wall face inside the door opening")
    co = np.array([v.co[:] for f in inside for v in f.verts])
    lo, hi = co.min(axis=0), co.max(axis=0)
    if lo[0] < t["x_min"] - EDGE_TOLERANCE or hi[0] > t["x_max"] + EDGE_TOLERANCE or hi[2] > t["z_top"] + EDGE_TOLERANCE:
        raise SystemExit(f"{NAME}: a deleted wall face reaches outside the opening: {lo.round(4)} .. {hi.round(4)}")
    area = sum(f.calc_area() for f in inside)
    bmesh.ops.delete(bm, geom=inside, context="FACES")
    ngons = [f for f in bm.faces if len(f.verts) > 3]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons, quad_method="BEAUTY", ngon_method="BEAUTY")
    degenerate = sum(1 for f in bm.faces if f.calc_area() < 1e-10)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return {
        "target_w09": {k: round(v, 4) for k, v in door_w09(row).items()},
        "target_cut": {k: round(v, 4) for k, v in t.items()},
        "wall_faces_touching_opening_before": len(wall_before),
        "faces_bisected": cuts,
        "faces_deleted": len(inside),
        "area_deleted_m2": round(area, 4),
        "deleted_faces_bounds": {"min": [round(float(v), 4) for v in lo], "max": [round(float(v), 4) for v in hi]},
        "ngons_triangulated": len(ngons),
        "degenerate_triangles_after": degenerate,
        "triangles_before": triangles_before,
        "triangles_after": meshops.triangles(obj),
    }


def _hits_wall(bvh, x: float, z: float, t: dict) -> bool:
    """A ray from the porch (0.3 m in front of the wall) towards -Y at (x, z) first meets the back wall."""
    return _first_hit_is_wall(bvh, x, z, t["wall_y"], t["wall_y"] + 0.3)


def opening_checks(obj, cut: dict, row: dict, arch: dict) -> dict:
    """Rays through the opening pass, rays just outside it meet the wall; the measured edges, threshold and hinges."""
    t = door_target(row, arch)
    w = door_w09(row)
    bottom = cut["deleted_faces_bounds"]["min"][2]
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    inside_x = np.linspace(t["x_min"] + RAY_INSET, t["x_max"] - RAY_INSET, 17)
    inside_z = np.linspace(bottom + RAY_INSET, t["z_top"] - RAY_INSET, 26)
    blocked = [[round(float(x), 3), round(float(z), 3)] for x in inside_x for z in inside_z
               if _hits_wall(bvh, float(x), float(z), t)]
    ring = ([(t["x_min"] - RAY_INSET, float(z)) for z in inside_z] + [(t["x_max"] + RAY_INSET, float(z)) for z in inside_z]
            + [(float(x), t["z_top"] + RAY_INSET) for x in inside_x])
    open_outside = [[round(x, 3), round(z, 3)] for x, z in ring if not _hits_wall(bvh, x, z, t)]

    def scan_x(z: float) -> list[float]:
        xs = np.arange(t["x_min"] - 0.1, t["x_max"] + 0.1, SCAN_STEP)
        passing = [float(x) for x in xs if not _hits_wall(bvh, float(x), z, t)]
        return [round(min(passing), 4), round(max(passing), 4)] if passing else []

    def scan_top(x: float) -> float | None:
        """The last height that passes, going up from inside the opening, before the first ray meets the wall."""
        last = None
        for z in np.arange(t["z_top"] - 0.1, t["z_top"] + 0.1, SCAN_STEP):
            if _hits_wall(bvh, x, float(z), t):
                return round(last, 4) if last is not None else None
            last = float(z)
        return None

    def wall_top(x: float) -> float | None:
        """The top of the wall above the opening (the lintel): going up from the top, the last height on the wall."""
        last = None
        for z in np.arange(t["z_top"] + SCAN_STEP, t["z_top"] + 0.6, SCAN_STEP):
            if not _hits_wall(bvh, x, float(z), t):
                return round(last, 4) if last is not None else None
            last = float(z)
        return round(last, 4) if last is not None else None

    floor = []
    for x in np.linspace(t["x_min"] + RAY_INSET, t["x_max"] - RAY_INSET, 9):
        loc, _, _, _ = bvh.ray_cast(Vector((float(x), t["wall_y"] + 0.02, 2.0)), Vector((0.0, 0.0, -1.0)), 3.0)
        floor.append(round(loc.z, 4) if loc else None)
    wall_y = []
    for z in (bottom + 0.1, (bottom + t["z_top"]) / 2, t["z_top"] - 0.1):
        for x in (t["x_min"] - 0.05, t["x_max"] + 0.05):
            loc, _, _, _ = bvh.ray_cast(Vector((x, t["wall_y"] + 0.3, z)), Vector((0.0, -1.0, 0.0)), 0.6)
            wall_y.append(round(loc.y, 4) if loc else None)
    ceiling, _, _, _ = bvh.ray_cast(Vector(((t["x_min"] + t["x_max"]) / 2, t["wall_y"] + 0.1, 2.0)),
                                    Vector((0.0, 0.0, 1.0)), 5.0)
    hinge_y = round(float(np.mean([y for y in wall_y if y is not None])), 4)
    mid = (bottom + t["z_top"]) / 2
    centre_x = (t["x_min"] + t["x_max"]) / 2
    edges = {"x_at_mid_height": scan_x(mid), "x_at_0.5m_above_bottom": scan_x(bottom + 0.5),
             "x_at_0.2m_below_top": scan_x(t["z_top"] - 0.2), "top_z_at_centre": scan_top(centre_x),
             "top_z_at_hinges": [scan_top(t["x_max"] - 0.05), scan_top(t["x_min"] + 0.05)],
             "wall_top_z_above_hinges": [wall_top(t["x_max"] - 0.05), wall_top(t["x_min"] + 0.05)]}
    hint = row["decided"]["placement_hint"]

    def world(p: list[float]) -> list[float]:  # placement_hint: position + rotation about z (Blender world axes)
        m = metrics.placement_matrix([0.0, 0.0, 0.0], hint["rotation_z_deg"], 1.0)
        q = metrics.transform_points(m, np.asarray([p]))[0] + np.asarray(hint["position"])
        return [round(float(v), 4) for v in q]

    hinges = {}
    for side, x in (("left_viewed_from_front_plus_x", t["x_max"]), ("right_viewed_from_front_minus_x", t["x_min"])):
        a, b = [round(x, 4), hinge_y, round(bottom, 4)], [round(x, 4), hinge_y, round(t["z_top"], 4)]
        hinges[side] = {"local_bottom": a, "local_top": b, "world_bottom_at_placement_hint": world(a),
                        "world_top_at_placement_hint": world(b)}
    width = t["x_max"] - t["x_min"]
    height = t["z_top"] - bottom
    return {
        **cut,
        "opening_local_m": {"x_min": round(t["x_min"], 4), "x_max": round(t["x_max"], 4), "z_bottom": round(bottom, 4),
                            "z_top": round(t["z_top"], 4), "wall_y": hinge_y, "width": round(width, 4),
                            "height": round(height, 4), "centre_x": round(centre_x, 4)},
        "central_arch": arch,
        "hinge_behind_column_m": round(t["x_max"] - arch["clear_span"][1], 4),
        "w09_difference": {
            "centre_x_m": round(centre_x - (w["x_min"] + w["x_max"]) / 2, 4),
            "z_bottom_m": round(bottom - t["z_bottom_w09"], 4),
            "height_m": round(height - (t["z_top"] - t["z_bottom_w09"]), 4),
            "note": ("width, top and wall plane are W09's. The opening is centred on the porch's central arch "
                     "(measured; W09's x put the opening 0.36 m off the arch, behind the next column) and its bottom "
                     "is the wall's bottom edge on the porch floor (W09 read 0.279): both chosen by the user on "
                     "2026-10-31"),
        },
        "threshold_floor_z_in_front": floor,
        "porch_ceiling_z_above_centre": round(ceiling.z, 4) if ceiling else None,
        "wall_y_beside_opening": wall_y,
        "measured_edges": edges,
        "rays_inside": {"count": len(inside_x) * len(inside_z), "blocked": blocked},
        "rays_outside_ring": {"count": len(ring), "open": open_outside},
        "hinges": hinges,
        "placement_hint": hint,
    }


# ---------------------------------------------------------------- measurements


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


# ---------------------------------------------------------------- review images


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
    for o in figure:
        mesh = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    return grid_sheet([paths[:2], paths[2:]], REVIEW / f"{KEY}_views.png")


CLOSEUPS = [
    # name, camera location, target, lens (local metres; the front is at +Y, the door at x -0.70, y 1.55)
    ("porch", (0.5, 10.5, 2.2), (-0.70, 1.55, 1.8), 35.0),
    ("porch_columns", (2.2, 6.6, 1.4), (-0.7, 4.0, 1.5), 28.0),
    ("tower", (6.8, 10.5, 7.2), (4.3, 3.0, 6.4), 50.0),
    ("bay_window", (-3.6, 9.5, 2.8), (-4.5, 3.0, 2.4), 40.0),
    ("gable", (1.2, 12.5, 8.2), (-0.3, 2.0, 6.6), 50.0),
]


def closeup_views(prefix: str, tmp: Path) -> list[Path]:
    views = [{"filepath": tmp / f"{prefix}_{n}.png", "location": loc, "target": tgt, "lens_mm": lens}
             for n, loc, tgt, lens in CLOSEUPS]
    return render_review_images(views, width=640, height=480, samples=32)


def emulate_culling(material) -> None:
    """Cycles draws back faces; mix in a Transparent BSDF on back faces so the render shows what a single-sided
    material in Resonite shows (only for the review renders after the save)."""
    tree = material.node_tree
    output = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
    shader = output.inputs["Surface"].links[0].from_node
    geometry = tree.nodes.new("ShaderNodeNewGeometry")
    transparent = tree.nodes.new("ShaderNodeBsdfTransparent")
    mix = tree.nodes.new("ShaderNodeMixShader")
    tree.links.new(geometry.outputs["Backfacing"], mix.inputs["Fac"])
    tree.links.new(shader.outputs[0], mix.inputs[1])
    tree.links.new(transparent.outputs[0], mix.inputs[2])
    tree.links.new(mix.outputs[0], output.inputs["Surface"])


def marker(name: str, a, b, color) -> object:
    """A thin emissive rod from ``a`` to ``b`` (render-only)."""
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=(b - a).length, location=(a + b) / 2, vertices=12)
    rod = bpy.context.active_object
    rod.name = name
    rod.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    for n in list(tree.nodes):
        tree.nodes.remove(n)
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, 1.0)
    emission.inputs["Strength"].default_value = 4.0
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(emission.outputs[0], out.inputs["Surface"])
    rod.data.materials.append(mat)
    return rod


def door_sheet(obj, opening: dict, tmp: Path) -> Path:
    """The opening seen from the porch, single-sided, with the hinge lines (red), threshold (green) and top (blue)."""
    o = opening["opening_local_m"]
    y = o["wall_y"] + 0.01
    rods = [marker("Review_HingeLeft", (o["x_max"], y, o["z_bottom"]), (o["x_max"], y, o["z_top"]), (1.0, 0.05, 0.05)),
            marker("Review_HingeRight", (o["x_min"], y, o["z_bottom"]), (o["x_min"], y, o["z_top"]), (1.0, 0.05, 0.05)),
            marker("Review_Threshold", (o["x_min"], y, o["z_bottom"]), (o["x_max"], y, o["z_bottom"]), (0.1, 1.0, 0.2)),
            marker("Review_Top", (o["x_min"], y, o["z_top"]), (o["x_max"], y, o["z_top"]), (0.2, 0.4, 1.0))]
    emulate_culling(obj.data.materials[0])
    cx = o["centre_x"]
    views = [{"filepath": tmp / "door_front.png", "location": (cx, 9.0, 1.7), "target": (cx, o["wall_y"], 1.6),
              "lens_mm": 50.0},
             {"filepath": tmp / "door_oblique.png", "location": (o["x_max"] + 0.4, o["wall_y"] + 1.15, 1.7),
              "target": (o["x_min"] + 0.5, o["wall_y"], 1.5), "lens_mm": 18.0}]
    paths = render_review_images(views, width=640, height=480, samples=32)
    for rod in rods:
        mesh, mat = rod.data, rod.data.materials[0]
        bpy.data.objects.remove(rod, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        bpy.data.materials.remove(mat)
    return grid_sheet([paths], REVIEW / f"{KEY}_door_opening.png")


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
CULLED_TILES = [[("back", "+Y (front)"), ("front", "-Y (back)"), ("right", "+X")],
                [("left", "-X"), ("top", "+Z (top)"), ("bottom", "-Z (bottom)")]]


def see_through_location(obj, work: Path, opening: dict) -> dict:
    """Where the see-through pixels of the +Y view lie: inside the door opening or elsewhere. The +Y camera of
    ``backface_check`` is orthographic, looks along -Y with +Z up (so the image's right is -X), and spans
    1.05 x the largest extent around the centre of the bounding box."""
    co = meshops.vertex_array(obj)
    lo, hi = co.min(axis=0), co.max(axis=0)
    centre = (lo + hi) / 2
    scale = float((hi - lo).max()) * 1.05 / CULL_PIXELS
    off = read_png(work / "cull_back_0.png")
    on = read_png(work / "cull_back_1.png")
    through = (off[:, :, 3] > 0.5) & (on[:, :, 3] <= 0.5)
    rows, cols = np.nonzero(through)  # rows bottom-up (Blender pixels)
    x = centre[0] - (cols + 0.5 - CULL_PIXELS / 2) * scale
    z = centre[2] + (rows + 0.5 - CULL_PIXELS / 2) * scale
    o = opening["opening_local_m"]
    margin = 2 * scale
    inside = (x > o["x_min"] - margin) & (x < o["x_max"] + margin) & (z > o["z_bottom"] - margin) & (z < o["z_top"] + margin)
    area = (o["x_max"] - o["x_min"]) * (o["z_top"] - o["z_bottom"]) / scale**2
    out = {"view": "back (camera at +Y, the front)", "pixel_m": round(scale, 4), "see_through_pixels": int(through.sum()),
           "inside_opening": int(inside.sum()), "outside_opening": int((~inside).sum()),
           "opening_area_pixels": round(area, 1)}
    if inside.any():
        out["inside_bounds_m"] = {"x": [round(float(x[inside].min()), 3), round(float(x[inside].max()), 3)],
                                  "z": [round(float(z[inside].min()), 3), round(float(z[inside].max()), 3)]}
    if (~inside).any():
        out["outside_bounds_m"] = {"x": [round(float(x[~inside].min()), 3), round(float(x[~inside].max()), 3)],
                                   "z": [round(float(z[~inside].min()), 3), round(float(z[~inside].max()), 3)]}
    return out


def backface_sheet(obj, tmp: Path, opening: dict) -> tuple[Path, dict]:
    culling = meshops.backface_check(obj, tmp / "cull", size=CULL_PIXELS)
    culling["view_camera_side"] = {view: side for row in CULLED_TILES for view, side in row}
    culling["front_see_through_location"] = see_through_location(obj, tmp / "cull", opening)
    sheet = grid_sheet([[tmp / "cull" / f"cull_{view}_1.png" for view, _ in row] for row in CULLED_TILES],
                       REVIEW / f"{KEY}_backface_culled.png")
    return sheet, culling


# ---------------------------------------------------------------- manifest


def manifest(row: dict, checks: dict, textures: dict, opening: dict) -> dict:
    dims = checks["dimensions_m"]
    o = opening["opening_local_m"]
    h = opening["hinges"]
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
            "script_file": "modeling/M03/build.py",
            "origin_policy": row["decided"]["origin_policy"],
            "origin_world": [0.0, 0.0, 0.0],
            "dimensions_m": {"width": dims["width_x"], "depth": dims["depth_y"], "height": dims["height_z"]},
            "bounds_local": checks["bounds_m"],
            "parts": [{"part_id": NAME, "role": "asset_root", "parent_part": None, "origin_policy": "ground_center",
                       "pivot_local": [0.0, 0.0, 0.0]}],
            "hierarchy": {"asset_root": NAME, "motion_roots": [], "visual_roots": [NAME], "attachment_points": []},
            "materials": [MATERIAL],
            "textures": [info["file"] for info in textures.values() if "file" in info],
            "metrics": {"measured": True, "measurement_source": "blender_scene", "triangles": checks["triangles"],
                        "vertices": checks["vertices"], "materials_count": 1, "objects_count": 1},
            "export_result": {"status": "unexported", "bundle_dir": None, "apply_plan": None, "report_file": None},
            "replacement": {
                "is_placeholder": False,
                "modifiable": True,
                "future_target": None,
                "notes": (
                    "Finished Meshy visual for the VisualRoot of the B_mansion haunted mansion facade (Spec 6.3); it "
                    "replaces the W03 placeholder BMN_MansionPlaceholder_001 (W03 #5 names M03_HauntedMansion_001 "
                    "as its future_meshy_target; the W03 ID is not on main on 2026-10-31) in P2. origin_world is the "
                    "asset-local origin: the world position is W03's (received.json placement_hint: (0, 41.5, 1.5), "
                    "rotation_z 180 so the front looks south). Origin = bottom centre (z=0), front = +Y (Resonite +Z). "
                    f"Door opening (local): x {o['x_min']}..{o['x_max']} (width {o['width']}), z {o['z_bottom']}.."
                    f"{o['z_top']} (height {o['height']}) in the porch's back wall at y {o['wall_y']}, centred on the "
                    "porch's central arch (W09's x was 0.36 m off it) with its bottom on the porch floor (higher than "
                    "W09's 0.279). Hinge lines (local, W03's double doors): "
                    f"{h['left_viewed_from_front_plus_x']['local_bottom']} up to z {o['z_top']} and "
                    f"{h['right_viewed_from_front_minus_x']['local_bottom']} up to z {o['z_top']}. The opening is a "
                    "clean cut with no reveal or frame (W03's frame covers the paper-thin edge) and nothing behind it "
                    "(W03's entrance hall closes the view; the shell's inside is culled). No emission is baked into "
                    "the albedo; no collider is part of this visual."
                ),
            },
        }],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--skip-review", action="store_true")
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    row = load_row()
    obj, textures = build_asset(row)
    arch = central_arch(obj, row)
    cut = cut_door_opening(obj, row, arch)
    opening = opening_checks(obj, cut, row, arch)
    if opening["rays_inside"]["blocked"] or opening["rays_outside_ring"]["open"]:
        raise SystemExit(f"{NAME}: the door opening is not clean: {json.dumps(opening['rays_inside'])} "
                         f"{json.dumps(opening['rays_outside_ring'])}")
    checks = shape_checks(obj, row)
    added = checks["triangles"] - cut["triangles_before"]
    if cut["triangles_before"] != row["measured"]["triangles"] or not 0 <= added <= MAX_TRIANGLES_ADDED_BY_CUT:
        raise SystemExit(f"{NAME}: {cut['triangles_before']} -> {checks['triangles']} triangles; the source has "
                         f"{row['measured']['triangles']} and the cut may add up to {MAX_TRIANGLES_ADDED_BY_CUT}")
    checks["triangle_budget"] = {
        "triangles_max_w09": row["budget"]["triangles_max"],
        "triangles": checks["triangles"],
        "over_budget": max(0, checks["triangles"] - row["budget"]["triangles_max"]),
        "added_by_door_opening": added,
        "decision": ("accepted by the user on 2026-10-31 (#16): W09's limit is the source count (no reduction), the "
                     "opening adds triangles where the bisect splits the wall faces, and nothing else is reduced to "
                     "make up for it"),
    }
    bpy.context.preferences.filepaths.save_version = 0  # no M03.blend1 backup (as finish.py)
    save_blend(BLEND, pack_images=True)
    counts = {k: len(getattr(bpy.data, k)) for k in ("objects", "meshes", "materials", "images", "collections")}

    review = {}
    if not args.skip_review:
        REVIEW.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            sun = front_sun()
            views = views_sheet(obj, tmp)
            finished = closeup_views("finished", tmp)
            uv_image, uv_texel_share = uv_layout(obj)
            culled, culling = backface_sheet(obj, tmp, opening)
            # The source after everything about the finished object: same placement, original 4096 images.
            source = import_source(Path(row["source"]["copy_path"]))
            finish.place(source, row["decided"])
            obj.hide_render = True
            original = closeup_views("source", tmp)
            compare = grid_sheet([[s, f] for s, f in zip(original, finished)], REVIEW / f"{KEY}_compare_source.png")
            source.hide_render = True
            obj.hide_render = False
            door = door_sheet(obj, opening, tmp)  # last: it changes the material (after the save)
            bpy.data.objects.remove(sun, do_unlink=True)
        review = {"uv_texel_share_1024": uv_texel_share, "backface_check": culling,
                  "review_images": [rel(p) for p in (views, compare, door, uv_image, culled)],
                  "closeups": [{"name": n, "camera": loc, "target": tgt, "lens_mm": lens} for n, loc, tgt, lens in CLOSEUPS]}

    checks.update({
        "row_id": KEY,
        "object": NAME,
        "source": {"copy_path": row["source"]["copy_path"], "sha256": row["source"]["sha256"],
                   "copy_sha256_ok": True, "original_path": row["source"]["original_path"],
                   "original_sha256_ok": sha256(Path(row["source"]["original_path"])) == row["source"]["sha256"]},
        "budget": row["budget"],
        "textures": textures,
        "door_opening": opening,
        "double_sided": row["double_sided"]["decision"],
        "blend_counts": counts,
        "blender": bpy.app.version_string,
        **review,
    })
    if not args.skip_review:
        (REVIEW / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(manifest(row, checks, textures, opening), ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    o = opening["opening_local_m"]
    print(f"built {rel(BLEND)}: triangles={checks['triangles']} dims={checks['dimensions_m']} "
          f"uv_cover={checks['uv_cover']} opening={o['width']}x{o['height']} counts={counts}")


if __name__ == "__main__":
    main()
