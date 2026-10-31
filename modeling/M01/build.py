"""Build the finished M01 entrance gate (W09-M01, #14) from the received Meshy GLB.

Run (project directory):
    resoloop blender run modeling/M01/build.py --json
    Optional: --arg=--skip-review (no review images, for a quick rebuild)
Then export and validate with ``uv run python modeling/M01/export.py``.

Outputs:
- ``blender/M01/M01.blend`` and ``blender/M01/textures/*.png`` (packed into the ``.blend``). Neither is committed
  (3D models stay out of Git; ``blender/M01/.gitignore``)
- ``assets/manifest/M01.json`` (``export_result`` stays ``unexported`` until ``export.py`` fills it)
- ``review/M01/*.png``

Every decision comes from ``assets/meshy/received.json`` (W09). Steps:

1. Check the copy's SHA-256, import it, join it into one mesh and place it with ``decided`` (``modeling/meshy/finish.py``:
   origin to (0, 0, 0), scale to metres, front to +Y). ``meshops.import_glb`` starts from Blender's factory settings,
   so a second run starts from the same empty scene. Adapt the material for ``--pack-pbr`` and scale the images to the
   row's ``budget`` (``finish.adapt_material``).
2. Cut the gate leaves free (``split_and_attach``: open them): bisect the faces that cross the hinge lines (the vertical
   lines of ``opening_left_ground`` / ``opening_right_ground``, below the finials of the posts by the pillars) and
   the centre line between the two leaves, and the
   centre bar between the leaves and the arch above at ``CENTRE_BAR_CUT_Z``. Each leaf is the set of faces reached from
   a seed on the leaf through edges that do not lie on a cut (vertices compared by position, because the GLB splits
   them at UV seams). The mesh is not welded.
3. Make the leaves double-sided (``double_sided``: only the leaves): duplicate their faces, reverse the copies and
   give them the negated corner normals.
4. Open the leaves 90 degrees inwards (-Y), as close to the pillars as ``PILLAR_GAP`` so the passage stays as wide as
   the leaves allow (``open_leaf``). Each leaf's origin is the pivot of that rotation (its hinge). The mesh keeps the
   closed pose; the object rotation (+90 / -90 degrees about Z) opens it, so rotation 0 closes it again. The leaves
   must not intersect the arch or each other.
5. Hierarchy (``docs/conventions.md`` §4.2): the empty ``M01_EntranceGate_001`` (asset root, ground centre) holds the
   arch and the two leaves. Save the ``.blend``, then render the review images and measure what a single-sided
   material hides (W09's ``backface_check``), and write the manifest (all after the save, so nothing of the review
   scene reaches the ``.blend``).

"Left" and "right" are seen from the front (standing on the +Y side, facing the sign): the left leaf is on +X.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
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
from modeling.lib.scene import save_blend
from modeling.meshy import meshops, metrics
from modeling.meshy.finish import adapt_material, place, sha256
from modeling.meshy.review_views import add_figure

KEY = "M01"
ASSET_ID = "M01_EntranceGate_001"
ARCH_ID = "M01_GateArch_001"
LEAF_IDS = {"left": "M01_GateLeafLeft_001", "right": "M01_GateLeafRight_001"}
BLEND_REL = "blender/M01/M01.blend"
TEX_REL = "blender/M01/textures"
SCRIPT_REL = "modeling/M01/build.py"
MANIFEST_REL = "assets/manifest/M01.json"
REVIEW_REL = "review/M01"
RECEIVED = PROJECT_ROOT / "assets" / "meshy" / "received.json"

CUT_BAND_Y = 0.6  # |y| of the faces the hinge and centre lines cut; the leaves lie within |y| < 0.19
CENTRE_BAR_CUT_Z = 4.20  # only the thin centre bar stands here: above the tips of the leaves' spikes (up to 4.11) and below
# the bar's star (from 4.30); the stub left on the arch stays above W09's passage height (3.973)
CENTRE_BAR_HALF_WIDTH = 0.4  # |x - centre| of the faces the cut at CENTRE_BAR_CUT_Z reaches
HINGE_CUT_TOP_Z = 3.30  # the hinge lines cut only below the finials (3.33 to 3.85) of the posts by the pillars, which stay whole
HINGE_SPILL = 0.08  # how far past its hinge line a leaf (or a piece joined to it) may reach
LEAF_SEED_Z = 1.0
PILLAR_GAP = 0.005  # the opened leaf to the arch, at least
OPEN_DEG = 90.0
HINGE_SETBACKS = np.round(np.arange(0.0, 0.31, 0.01), 2)  # candidate distances of the opened leaf's hinge end behind the gate plane
GRID_Y, GRID_STEP = (-3.0, 1.5), 0.05  # cells in which the arch's surface nearest the passage is measured
GRID_Z, GRID_STEP_Z = (0.0, 4.25), 0.05
PASSAGE_Z = (0.05, 2.5)  # walking heights over which the passage width is measured
PASSAGE_Z_FULL = (0.05, 3.9)  # up to just below W09's passage height (3.973)
CORE_HALF_WIDTH = 1.8  # |x - centre| of the passage core whose lowest overhead point gives the passage height
SAMPLE_STEP = 0.02
KEY_SCALE = 1e5  # vertex positions compared at 0.01 mm


# ---------------------------------------------------------------- geometry helpers


def world_triangles(obj) -> np.ndarray:
    me = obj.data
    me.calc_loop_triangles()
    idx = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
    me.loop_triangles.foreach_get("vertices", idx)
    m = np.array(obj.matrix_world)
    co = meshops.vertex_array(obj) @ m[:3, :3].T + m[:3, 3]
    return co[idx].reshape(-1, 3, 3)


def surface_points(tris: np.ndarray, step: float = SAMPLE_STEP) -> np.ndarray:
    """Points on the triangles, at most ``step`` apart along each triangle's longest edge (capped at 64 steps)."""
    edges = np.linalg.norm(tris[:, [1, 2, 0]] - tris, axis=2).max(axis=1)
    counts = np.clip(np.ceil(edges / step).astype(int) + 1, 1, 64)
    out = []
    for n in np.unique(counts):
        bary = np.array([(i / n, j / n, (n - i - j) / n) for i in range(n + 1) for j in range(n + 1 - i)])
        out.append(np.einsum("pk,tkd->tpd", bary, tris[counts == n]).reshape(-1, 3))
    return np.concatenate(out)


def bounds(objs) -> tuple[np.ndarray, np.ndarray]:
    co = np.concatenate([world_triangles(o).reshape(-1, 3) for o in objs])
    return co.min(axis=0), co.max(axis=0)


def _key(co) -> tuple[int, int, int]:
    return (round(co[0] * KEY_SCALE), round(co[1] * KEY_SCALE), round(co[2] * KEY_SCALE))


def _crosses(face, axis: int, value: float) -> bool:
    vals = [v.co[axis] for v in face.verts]
    return min(vals) < value < max(vals)


def _bisect(bm, faces, co, no, cut_keys: set) -> int:
    if not faces:
        return 0
    bm.verts.index_update()
    bm.edges.index_update()
    edges = sorted({e for f in faces for e in f.edges}, key=lambda e: e.index)
    verts = sorted({v for f in faces for v in f.verts}, key=lambda v: v.index)
    res = bmesh.ops.bisect_plane(bm, geom=list(faces) + edges + verts, dist=1e-7, plane_co=co, plane_no=no)
    for el in res["geom_cut"]:
        if isinstance(el, bmesh.types.BMVert):
            cut_keys.add(_key(el.co))
    return len(faces)


# ---------------------------------------------------------------- step 2: cut the leaves free


def split_leaves(obj, xl: float, xr: float, xc: float) -> dict:
    """Label every face 0 (arch), 1 (left leaf, +X) or 2 (right leaf, -X) in the face attribute ``m01_part``."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    cut_keys: set = set()
    cut = {}

    def centre(f):
        return f.calc_center_median()

    faces = [f for f in bm.faces if _crosses(f, 2, CENTRE_BAR_CUT_Z) and abs(centre(f).x - xc) < CENTRE_BAR_HALF_WIDTH
             and abs(centre(f).y) < CUT_BAND_Y]
    cut["centre_bar_top"] = _bisect(bm, faces, (0.0, 0.0, CENTRE_BAR_CUT_Z), (0.0, 0.0, 1.0), cut_keys)
    for name, x, top in (("hinge_left", xl, HINGE_CUT_TOP_Z), ("hinge_right", xr, HINGE_CUT_TOP_Z),
                         ("centre", xc, CENTRE_BAR_CUT_Z)):
        faces = [f for f in bm.faces if _crosses(f, 0, x) and centre(f).z < top and abs(centre(f).y) < CUT_BAND_Y]
        cut[name] = _bisect(bm, faces, (x, 0.0, 0.0), (1.0, 0.0, 0.0), cut_keys)

    bm.verts.index_update()
    bm.faces.index_update()
    bm.faces.ensure_lookup_table()
    vkey = [_key(v.co) for v in bm.verts]
    by_edge: dict = defaultdict(list)
    for f in bm.faces:
        for e in f.edges:
            a, b = vkey[e.verts[0].index], vkey[e.verts[1].index]
            if a in cut_keys and b in cut_keys:
                continue  # an edge on a cut: the two sides stay apart
            by_edge[(a, b) if a < b else (b, a)].append(f.index)
    neighbours: dict = defaultdict(set)
    for group in by_edge.values():
        for i in group:
            neighbours[i].update(group)

    centres = np.array([centre(f)[:] for f in bm.faces])

    def flood(seed: int, blocked: set) -> set:
        seen, stack = {seed}, [seed]
        while stack:
            for j in neighbours[stack.pop()]:
                if j not in seen and j not in blocked:
                    seen.add(j)
                    stack.append(j)
        return seen

    labels = np.zeros(len(bm.faces), dtype=np.int64)
    leaves = {}
    for label, side, seed_x in ((1, "left", (xc + xl) / 2), (2, "right", (xc + xr) / 2)):
        target = np.array([seed_x, 0.0, LEAF_SEED_Z])
        dist = np.linalg.norm(centres - target, axis=1)
        seed = int(np.argmin(dist))
        if dist[seed] > 0.3:
            raise SystemExit(f"{side} leaf: no face within 0.3 m of the seed {target.tolist()}")
        members = flood(seed, set(np.flatnonzero(labels).tolist()))
        co = np.array([v.co[:] for i in members for v in bm.faces[i].verts])
        lo, hi = co.min(axis=0), co.max(axis=0)
        x_lo, x_hi = (xc, xl) if side == "left" else (xr, xc)
        inside = (lo[0] >= x_lo - HINGE_SPILL and hi[0] <= x_hi + HINGE_SPILL and np.abs(co[:, 1]).max() < CUT_BAND_Y
                  and hi[2] <= CENTRE_BAR_CUT_Z + 1e-4 and len(members) > 500)
        if not inside:
            raise SystemExit(f"{side} leaf: {len(members)} faces reaching {lo.round(3).tolist()}..{hi.round(3).tolist()}, "
                             "outside the opening; the split is wrong")
        labels[sorted(members)] = label
        leaves[side] = {"faces": len(members), "min": lo.round(3).tolist(), "max": hi.round(3).tolist()}

    # Small pieces inside the opening below the cut, cut off from both leaves, would float where the leaves were.
    rest = set(np.flatnonzero(labels == 0).tolist())
    leaf_faces = set(np.flatnonzero(labels).tolist())
    stray = []
    while rest:
        seed = rest.pop()
        group = flood(seed, leaf_faces)
        rest -= group
        co = np.array([v.co[:] for i in group for v in bm.faces[i].verts])
        lo, hi = co.min(axis=0), co.max(axis=0)
        if lo[0] > xr - HINGE_SPILL and hi[0] < xl + HINGE_SPILL and np.abs(co[:, 1]).max() < CUT_BAND_Y and hi[2] < CENTRE_BAR_CUT_Z:
            side = 1 if (lo[0] + hi[0]) / 2 > xc else 2
            labels[sorted(group)] = side
            stray.append({"faces": len(group), "to": "left" if side == 1 else "right",
                          "min": lo.round(3).tolist(), "max": hi.round(3).tolist()})

    layer = bm.faces.layers.int.new("m01_part")
    for f in bm.faces:
        f[layer] = int(labels[f.index])
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return {"bisected_faces": cut, "leaves": leaves, "stray_pieces_joined_to_leaves": stray,
            "cut_planes": {"hinge_left_x": round(xl, 4), "hinge_right_x": round(xr, 4), "hinge_below_z": HINGE_CUT_TOP_Z,
                           "centre_x": round(xc, 4), "centre_bar_z": CENTRE_BAR_CUT_Z}}


def separate(obj, collection) -> dict:
    """One object per ``m01_part`` label; the arch keeps ``obj``."""
    out = {}
    for label, name in ((1, LEAF_IDS["left"]), (2, LEAF_IDS["right"]), (0, ARCH_ID)):
        if label == 0:
            target = obj
        else:
            target = obj.copy()
            target.data = obj.data.copy()
            collection.objects.link(target)
        bm = bmesh.new()
        bm.from_mesh(target.data)
        layer = bm.faces.layers.int.get("m01_part")
        drop = [f for f in bm.faces if f[layer] != label]
        bmesh.ops.delete(bm, geom=drop, context="FACES")
        bm.faces.layers.int.remove(layer)
        bm.to_mesh(target.data)
        bm.free()
        target.data.update()
        target.name = target.data.name = name
        out[label] = target
    return out


# ---------------------------------------------------------------- step 3: double-sided leaves


def corner_normals(me) -> np.ndarray:
    n = np.empty(len(me.loops) * 3, dtype=np.float64)
    me.corner_normals.foreach_get("vector", n)
    return n.reshape(-1, 3)


def make_double_sided(obj) -> int:
    """Add a reversed copy of every face, with the negated corner normal of the same face corner. Returns the faces added."""
    me = obj.data
    normals = corner_normals(me)
    lookup = {}
    for p in me.polygons:
        for li in p.loop_indices:
            lookup[(p.index, me.loops[li].vertex_index)] = normals[li]
    poly_count = len(me.polygons)
    bm = bmesh.new()
    bm.from_mesh(me)
    src_face = bm.faces.layers.int.new("m01_src_face")
    src_vert = bm.verts.layers.int.new("m01_src_vert")
    for f in bm.faces:
        f[src_face] = f.index
    for v in bm.verts:
        v[src_vert] = v.index
    originals = list(bm.faces)
    res = bmesh.ops.duplicate(bm, geom=list(bm.verts) + list(bm.edges) + originals)
    copies = [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=copies)
    bm.to_mesh(me)
    bm.free()
    face_src = np.empty(len(me.polygons), dtype=np.int64)
    me.attributes["m01_src_face"].data.foreach_get("value", face_src)
    vert_src = np.empty(len(me.vertices), dtype=np.int64)
    me.attributes["m01_src_vert"].data.foreach_get("value", vert_src)
    new_normals = np.zeros((len(me.loops), 3))
    for p in me.polygons:
        sign = -1.0 if p.index >= poly_count else 1.0
        for li in p.loop_indices:
            new_normals[li] = sign * lookup[(int(face_src[p.index]), int(vert_src[me.loops[li].vertex_index]))]
    me.attributes.remove(me.attributes["m01_src_face"])
    me.attributes.remove(me.attributes["m01_src_vert"])
    me.normals_split_custom_set(new_normals.tolist())
    me.update()
    check = corner_normals(me)
    if not np.allclose(check, new_normals, atol=1e-2):  # stored compressed; 0.01 is about 0.6 degrees
        raise SystemExit(f"{obj.name}: corner normals were not kept ({np.abs(check - new_normals).max():.4f})")
    return len(me.polygons) - poly_count


# ---------------------------------------------------------------- step 4: open the leaves


def arch_inner_grid(arch_pts: np.ndarray, xc: float, sign: float) -> np.ndarray:
    """Per cell of ``GRID_Y`` x ``GRID_Z`` (and its 8 neighbours), the arch's nearest surface to the passage on one side,
    as the mirrored x (``sign`` * x; inf where the arch has nothing)."""
    side = arch_pts[sign * (arch_pts[:, 0] - xc) > 1.0]
    ny = int(round((GRID_Y[1] - GRID_Y[0]) / GRID_STEP))
    nz = int(round((GRID_Z[1] - GRID_Z[0]) / GRID_STEP_Z))
    iy = np.floor((side[:, 1] - GRID_Y[0]) / GRID_STEP).astype(int)
    iz = np.floor((side[:, 2] - GRID_Z[0]) / GRID_STEP_Z).astype(int)
    ok = (iy >= 0) & (iy < ny) & (iz >= 0) & (iz < nz)
    cells = np.full((ny, nz), np.inf)
    np.minimum.at(cells, (iy[ok], iz[ok]), sign * side[ok, 0])
    padded = np.pad(cells, 1, constant_values=np.inf)
    return np.min([padded[1 + dy : 1 + dy + ny, 1 + dz : 1 + dz + nz] for dy in (-1, 0, 1) for dz in (-1, 0, 1)], axis=0)


def open_leaf(leaf, side: str, arch_pts: np.ndarray, xc: float) -> dict:
    """Turn the leaf 90 degrees about Z so that its free end points to -Y, as close to the pillar as ``PILLAR_GAP``.

    In mirrored coordinates (x' = sign * x, so both leaves look like the left one) the opened leaf is
    ``x'_new = A - y`` and ``y_new = B + x'``. ``B`` sets how far behind the gate plane the hinge end stands
    (``HINGE_SETBACKS``); for each, ``A`` is the largest value that keeps every point of the leaf ``PILLAR_GAP`` off
    the arch's nearest surface in its cell (``arch_inner_grid``), and the setback with the largest ``A`` (the widest
    passage) wins. The pivot is the point this rotation keeps fixed: ``y_h = (A + B) / 2``, ``x_h = sign * (A - B) / 2``.
    """
    sign = 1.0 if side == "left" else -1.0
    pts = surface_points(world_triangles(leaf))
    xp, y, z = sign * pts[:, 0], pts[:, 1], pts[:, 2]
    inner = arch_inner_grid(arch_pts, xc, sign)
    iz = np.clip(np.floor((z - GRID_Z[0]) / GRID_STEP_Z).astype(int), 0, inner.shape[1] - 1)
    best = None
    for setback in HINGE_SETBACKS:
        b = -setback - float(xp.max())
        iy = np.floor((b + xp - GRID_Y[0]) / GRID_STEP).astype(int)
        limit = np.full(len(pts), np.inf)
        ok = (iy >= 0) & (iy < inner.shape[0])
        limit[ok] = inner[iy[ok], iz[ok]]
        k = int(np.argmin(limit + y))
        a = float(limit[k] + y[k]) - PILLAR_GAP
        if best is None or a > best[0] + 1e-9:
            best = (a, b, float(setback), k, float(limit[k]))
    a, b, setback, k, arch_x = best
    x_h, y_h = sign * (a - b) / 2, (a + b) / 2
    angle = sign * OPEN_DEG
    pivot = Vector((x_h, y_h, 0.0))
    leaf.data.transform(Matrix.Translation(-pivot))
    leaf.data.update()
    leaf.location = pivot
    leaf.rotation_mode = "XYZ"  # the glTF import leaves QUATERNION, which ignores rotation_euler
    leaf.rotation_euler = (0.0, 0.0, math.radians(angle))
    return {"pivot_local": [round(x_h, 4), round(y_h, 4), 0.0], "axis": "+Z", "closed_deg": 0.0,
            "placed_deg": angle, "hinge_end_behind_gate_plane_m": round(setback, 3),
            "binding": {"leaf_point_closed": [round(float(v), 3) for v in pts[k]], "arch_surface_x": round(sign * arch_x, 3),
                        "gap_m": PILLAR_GAP}}


def tree(obj) -> BVHTree:
    tris = world_triangles(obj)
    verts = tris.reshape(-1, 3).tolist()
    polys = [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tris))]
    return BVHTree.FromPolygons(verts, polys)


def passage(objs, arch_obj, xc: float, depth: tuple[float, float], w09_height_x: float) -> dict:
    """Clear width (between the nearest surfaces on either side of the centre line) per 5 cm slice of y, over the
    walking heights ``PASSAGE_Z`` and up to ``PASSAGE_Z_FULL``, and the lowest overhead point above the passage core
    (``|x - centre| < CORE_HALF_WIDTH`` within the arch's depth)."""
    pts = surface_points(np.concatenate([world_triangles(o) for o in objs]))
    arch = surface_points(world_triangles(arch_obj))

    def widths(z_range) -> dict:
        band = pts[(pts[:, 2] > z_range[0]) & (pts[:, 2] < z_range[1])]
        rows = []
        for y0 in np.arange(-2.4, 1.4, 0.05):
            s_ = band[(band[:, 1] >= y0) & (band[:, 1] < y0 + 0.05)]
            lp, rn = s_[s_[:, 0] > xc][:, 0], s_[s_[:, 0] < xc][:, 0]
            if len(lp) and len(rn):
                rows.append((round(float(y0), 2), round(float(lp.min()), 3), round(float(rn.max()), 3),
                             round(float(lp.min() - rn.max()), 3)))

        def narrowest(lo_y, hi_y):
            sel = [r for r in rows if lo_y <= r[0] < hi_y]
            if not sel:
                return None
            r = min(sel, key=lambda r: r[3])
            return {"width_m": r[3], "at_y": r[0], "left_x": r[1], "right_x": r[2]}

        return {
            "z_range_m": list(z_range),
            "gate_plane": narrowest(-0.05, 0.05),
            "in_front_of_gate_plane": narrowest(0.05, depth[1]),
            "behind_gate_plane_within_arch": narrowest(depth[0], -0.05),
            "behind_arch_along_opened_leaves": narrowest(-2.4, depth[0]),
        }

    # Heights over the arch only: the opened leaves stand at the sides, behind the gate plane.
    inside = (arch[:, 1] > depth[0]) & (arch[:, 1] < depth[1]) & (arch[:, 2] > 0.3)
    core = arch[inside & (np.abs(arch[:, 0] - xc) < CORE_HALF_WIDTH)]
    low = core[np.argmin(core[:, 2])]
    at_w09 = arch[inside & (np.abs(arch[:, 0] - w09_height_x) < 0.05)]
    floor = arch[(np.abs(arch[:, 0] - xc) < CORE_HALF_WIDTH) & (arch[:, 1] > depth[0]) & (arch[:, 1] < depth[1])
                 & (arch[:, 2] > 0.02) & (arch[:, 2] <= 0.3)]
    return {
        "walking": widths(PASSAGE_Z),
        "full_height": widths(PASSAGE_Z_FULL),
        "height_lowest_over_core_m": round(float(low[2]), 3),
        "height_lowest_over_core_at": [round(float(v), 3) for v in low],
        "core_half_width_m": CORE_HALF_WIDTH,
        "height_at_w09_point_m": round(float(at_w09[:, 2].min()), 3),
        "w09_point_x_m": w09_height_x,
        "core_points_between_0.02_and_0.3m": int(len(floor)),
    }


# ---------------------------------------------------------------- review images


def load_pixels(path: Path) -> np.ndarray:
    img = bpy.data.images.load(str(path), check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)


def save_pixels(sheet: np.ndarray, out: Path) -> None:
    sheet = sheet.copy()
    sheet[:, :, 3] = 1.0
    h, w = sheet.shape[:2]
    image = bpy.data.images.new("Review_Sheet", w, h, alpha=False)
    image.pixels.foreach_set(sheet.astype(np.float32).ravel())
    image.filepath_raw = str(out)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def grid(tiles: list[list[np.ndarray]], out: Path) -> None:
    """Tiles row by row from the top left (Blender pixel rows run bottom-up)."""
    rows = [np.concatenate(r, axis=1) for r in tiles]
    save_pixels(np.concatenate(rows[::-1], axis=0), out)


def view(name: str, tmp: Path, loc, target, lens: float = 35.0) -> dict:
    return {"filepath": tmp / f"{name}.png", "location": tuple(float(v) for v in loc),
            "target": tuple(float(v) for v in target), "lens_mm": lens}


def render_reviews(parts: dict, xc: float, original: Path, decided: dict, uv: np.ndarray, color_image) -> list[str]:
    out_dir = PROJECT_ROOT / REVIEW_REL
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = tempfile.TemporaryDirectory()
    tmp = Path(tmp_dir.name)
    written = []
    lo, hi = bounds(parts.values())
    add_figure(float(hi[0]) + 0.6, float(hi[1]) + 0.6, 0.0)
    # render_review_images lights from -Y; the front faces +Y, so add a front sun (as review_views.py does).
    sun = bpy.data.objects.new("Review_FrontSun", bpy.data.lights.new("Review_FrontSun", type="SUN"))
    sun.data.energy = 2.5
    sun.rotation_euler = Matrix.Rotation(math.radians(-35), 4, "X").to_euler()
    bpy.context.scene.collection.objects.link(sun)
    try:
        # 1. Overview: front, front three-quarter, back (the opened leaves), top.
        mid_z = (hi[2] + lo[2]) / 2
        views = [
            view("front", tmp, (xc, 19.0, mid_z), (xc, 0.0, mid_z), 50),
            view("threequarter", tmp, (xc - 9.0, 9.5, 1.6), (xc, -0.5, 3.2), 30),
            view("back", tmp, (xc, -19.0, mid_z), (xc, 0.0, mid_z), 50),
            view("top", tmp, (xc, -0.6, 17.0), (xc, -0.6, 0.0), 50),
        ]
        paths = render_review_images(views, width=640, height=640, samples=24)
        tiles = [load_pixels(p) for p in paths]
        grid([[tiles[0], tiles[1]], [tiles[2], tiles[3]]], out_dir / "M01_views.png")
        written.append(f"{REVIEW_REL}/M01_views.png")

        # 2. Close-ups of the finished model only.
        left = parts[1]
        piv = Vector(left.location)
        views = [
            view("sign", tmp, (xc, 4.6, 1.6), (xc, 0.3, 5.35), 50),  # from the walking height, 4 m in front
            view("leaf_inside", tmp, (xc - 1.2, -3.6, 1.7), (piv.x, -1.1, 1.6), 35),  # the opened left leaf
            view("hinge", tmp, (xc + 0.3, -1.6, 1.7), (piv.x, piv.y - 0.1, 2.6), 30),  # the left hinge from the passage
            view("passage", tmp, (xc, 5.5, 1.6), (xc, -2.5, 1.8), 28),  # walking in through the gate
        ]
        paths = render_review_images(views, width=960, height=720, samples=32)
        for p in paths:
            target = out_dir / f"M01_closeup_{p.stem}.png"
            save_pixels(load_pixels(p), target)
            written.append(f"{REVIEW_REL}/{target.name}")

        # 3. The original next to the finished model: the front, the sign close-up and the left leaf's front. The
        # leaf's camera turns with the leaf (closed point p -> matrix_world @ (p - pivot)), so both show the same face.
        def opened(p):
            return tuple(left.matrix_world @ (Vector(p) - piv))

        leaf_cam, leaf_target = (xc + 1.0, 3.2, 1.3), (xc + 1.0, 0.0, 1.3)
        cams = [view("cmp_front", tmp, (xc, 19.0, mid_z), (xc, 0.0, mid_z), 50),
                view("cmp_sign", tmp, (xc, 4.6, 1.6), (xc, 0.3, 5.35), 50)]
        finished = [load_pixels(p) for p in render_review_images(
            cams + [view("cmp_leaf", tmp, opened(leaf_cam), opened(leaf_target), 50)], width=640, height=480, samples=32)]
        cams.append(view("cmp_leaf", tmp, leaf_cam, leaf_target, 50))
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(original))
        imported = [o for o in bpy.data.objects if o not in before]
        m = Matrix(metrics.placement_matrix(decided["origin_source"], decided["yaw_deg"], decided["scale"]).tolist())
        for o in imported:
            if o.parent is None:
                o.matrix_world = m @ o.matrix_world
        for o in parts.values():
            o.hide_render = True
        src = [load_pixels(p) for p in render_review_images(cams, width=640, height=480, samples=32)]
        for o in parts.values():
            o.hide_render = False
        grid([[src[i], finished[i]] for i in range(len(cams))], out_dir / "M01_compare.png")
        written.append(f"{REVIEW_REL}/M01_compare.png")

        # 4. UV use: the colour image where the UV triangles cover it, darkened elsewhere.
        size = 512
        occ = metrics.occupancy(uv, (0, 1), (0.0, 0.0), (1.0, 1.0), 1.0 / size)[:size, :size]
        color = np.empty(color_image.size[0] * color_image.size[1] * 4, dtype=np.float32)
        color_image.pixels.foreach_get(color)
        color = color.reshape(color_image.size[1], color_image.size[0], 4)
        step = color.shape[0] // size
        small = color[::step, ::step][:size, :size].copy()
        small[~occ, :3] *= 0.15
        small[~occ, 2] += 0.25
        save_pixels(small, out_dir / "M01_uv.png")
        written.append(f"{REVIEW_REL}/M01_uv.png")
    finally:
        tmp_dir.cleanup()
    return written


def backface(parts: dict) -> dict:
    """W09's measure (``meshops.backface_check``) on the whole finished gate, joined into one object with the leaves
    opened: the share of its pixels that show through when back faces are culled (the exporter keeps no doubleSided)."""
    joined = meshops.join_meshes(list(parts.values()))  # removes every other object (the root, the review scene)
    with tempfile.TemporaryDirectory() as tmp:
        result = meshops.backface_check(joined, Path(tmp))
    result["object"] = "arch and both opened leaves, joined"
    return result


# ---------------------------------------------------------------- manifest


def write_manifest(payload: dict) -> None:
    path = PROJECT_ROOT / MANIFEST_REL
    previous = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if previous is not None:
        keep = {k: v for k, v in previous.items() if k != "updated_at"}
        old_asset = keep["assets"][0] if keep.get("assets") else {}
        # export.py fills export_result after an export; a rebuild resets it (the bundle may no longer match).
        same = {k: v for k, v in old_asset.items() if k != "export_result"} == {
            k: v for k, v in payload["assets"][0].items() if k != "export_result"}
        if same and old_asset.get("export_result") == payload["assets"][0]["export_result"]:
            stamp = previous["updated_at"]
    payload = {"schema_version": "1.0", "key": KEY, "updated_at": stamp, **payload}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- main


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--skip-review", action="store_true")
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    row = next(r for r in json.loads(RECEIVED.read_text(encoding="utf-8"))["assets"] if r["row_id"] == KEY)
    decided, budget, derived = row["decided"], row["budget"], row["derived"]
    src = Path(row["source"]["copy_path"])
    if sha256(src) != row["source"]["sha256"]:
        raise SystemExit(f"{src}: SHA-256 differs from received.json")

    # 1. import, place, material
    obj = meshops.join_meshes(meshops.import_glb(src))
    place(obj, decided)
    if len(obj.data.materials) != 1:
        raise SystemExit(f"{len(obj.data.materials)} materials; the confirmed GLB has one")
    source_triangles = meshops.triangles(obj)
    lo, hi = bounds([obj])
    placed = {
        "bounds_m": {"min": [round(float(v), 4) for v in lo], "max": [round(float(v), 4) for v in hi]},
        "w09_bounds_m": derived["bounds_local_m"],
        "difference_m": {"min": [round(float(a - b), 4) for a, b in zip(lo, derived["bounds_local_m"]["min"])],
                         "max": [round(float(a - b), 4) for a, b in zip(hi, derived["bounds_local_m"]["max"])]},
    }
    tex_dir = PROJECT_ROOT / TEX_REL
    tex_dir.mkdir(parents=True, exist_ok=True)
    textures = adapt_material(obj.data.materials[0], ASSET_ID, tex_dir, budget["color_px_max"], budget["data_px_max"])
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)
    material = obj.data.materials[0]

    collection = bpy.data.collections.new(KEY)
    bpy.context.scene.collection.children.link(collection)
    collection.objects.link(obj)
    bpy.context.scene.collection.objects.unlink(obj)

    # 2. cut the leaves free and separate
    pts = derived["points_local_m"]
    xl, xr = pts["opening_left_ground"][0], pts["opening_right_ground"][0]
    xc = (xl + xr) / 2
    split = split_leaves(obj, xl, xr, xc)
    parts = separate(obj, collection)
    _, uv_arch = meshops.triangle_arrays(parts[0])
    uv_all = np.concatenate([uv_arch] + [meshops.triangle_arrays(parts[k])[1] for k in (1, 2)])
    uv_cover = metrics.uv_cover(uv_all)["area_sum"]

    # 3. double-sided leaves
    added = {LEAF_IDS["left"]: make_double_sided(parts[1]), LEAF_IDS["right"]: make_double_sided(parts[2])}

    # 4. open the leaves
    arch_pts = surface_points(world_triangles(parts[0]))
    motion = {LEAF_IDS["left"]: open_leaf(parts[1], "left", arch_pts, xc),
              LEAF_IDS["right"]: open_leaf(parts[2], "right", arch_pts, xc)}
    bpy.context.view_layer.update()
    trees = {k: tree(o) for k, o in parts.items()}
    tris = {k: world_triangles(o) for k, o in parts.items()}
    overlaps, where = {}, {}
    for name, a, b in (("left_leaf_vs_arch", 1, 0), ("right_leaf_vs_arch", 2, 0), ("left_leaf_vs_right_leaf", 1, 2)):
        pairs = trees[a].overlap(trees[b])
        overlaps[name] = len(pairs)
        where[name] = [[tris[a][i].mean(axis=0).round(3).tolist(), tris[b][j].mean(axis=0).round(3).tolist()]
                       for i, j in pairs[:4]]
    if any(overlaps.values()):
        raise SystemExit(f"opened leaves intersect: {overlaps} at {where}")

    # 5. hierarchy, save
    root = bpy.data.objects.new(ASSET_ID, None)
    root.empty_display_type = "PLAIN_AXES"
    collection.objects.link(root)
    for o in parts.values():
        o.parent = root
    bpy.context.view_layer.update()
    lo, hi = bounds(parts.values())
    passage_info = passage(parts.values(), parts[0], xc, (float(derived["bounds_local_m"]["min"][1]), float(derived["bounds_local_m"]["max"][1])),
                           float(pts["opening_overhang_lowest"][0]))
    triangles = {o.name: meshops.triangles(o) for o in parts.values()}
    vertices = {o.name: len(o.data.vertices) for o in parts.values()}
    color_image = next(n.image for n in material.node_tree.nodes if n.type == "TEX_IMAGE" and n.image.name.endswith("_color"))
    bpy.context.preferences.filepaths.save_version = 0  # no M01.blend1 backup (as finish.py)
    blend = save_blend(PROJECT_ROOT / BLEND_REL, pack_images=True)

    total = sum(triangles.values())
    tex_files = [f"{TEX_REL}/{Path(t['file']).name}" for t in textures.values() if "file" in t]
    leaf_record = {
        name: {**motion[name], "double_sided_faces_added": added[name]} for name in motion
    }
    asset = {
        "asset_id": ASSET_ID,
        "key": KEY,
        "category": "architecture",
        "area_id": decided["area_id"],
        "collection": KEY,
        "blend_file": BLEND_REL,
        "script_file": SCRIPT_REL,
        "origin_policy": decided["origin_policy"],
        "origin_world": [0.0, 0.0, 0.0],
        "placement_hint": decided["placement_hint"],
        "forward_local": "+Y",
        "dimensions_m": {"width": round(float(hi[0] - lo[0]), 3), "depth": round(float(hi[1] - lo[1]), 3),
                         "height": round(float(hi[2] - lo[2]), 3)},
        "bounds_local": {"min": [round(float(v), 3) for v in lo], "max": [round(float(v), 3) for v in hi]},
        "parts": [
            {"part_id": ASSET_ID, "role": "asset_root", "parent_part": None, "origin_policy": "ground_center",
             "pivot_local": [0.0, 0.0, 0.0]},
            {"part_id": ARCH_ID, "role": "visual_root", "parent_part": ASSET_ID, "origin_policy": "ground_center",
             "pivot_local": [0.0, 0.0, 0.0]},
            *[{"part_id": name, "role": "motion_root", "parent_part": ASSET_ID, "origin_policy": "hinge_pivot",
               "pivot_local": motion[name]["pivot_local"]} for name in (LEAF_IDS["left"], LEAF_IDS["right"])],
        ],
        "hierarchy": {"asset_root": ASSET_ID, "motion_roots": [LEAF_IDS["left"], LEAF_IDS["right"]],
                      "visual_roots": [ARCH_ID, LEAF_IDS["left"], LEAF_IDS["right"]], "attachment_points": []},
        "leaves": leaf_record,
        "materials": [material.name],
        "textures": tex_files,
        "texture_details": textures,
        "metrics": {"measured": True, "measurement_source": "blender_scene", "triangles": total,
                    "vertices": sum(vertices.values()), "materials_count": 1, "objects_count": len(collection.objects),
                    "triangles_by_object": triangles, "vertices_by_object": vertices,
                    "source_triangles": source_triangles, "budget_triangles_max": budget["triangles_max"],
                    "uv_cover": round(float(uv_cover), 4), "texels_per_m_at_color": budget["texels_per_m_at_color"]},
        "placement_check": placed,
        "split": split,
        "overlaps_after_opening": overlaps,
        "passage": passage_info,
        "w09_keep_clear": next(s["keep_clear"] for s in row["split_and_attach"] if "keep_clear" in s),
        "source": {"row_id": row["row_id"], "copy_path": row["source"]["copy_path"], "sha256": row["source"]["sha256"]},
        "export_result": {"status": "unexported", "bundle_dir": None, "apply_plan": None, "report_file": None},
        "replacement": {
            "is_placeholder": False,
            "modifiable": True,
            "notes": ("Meshy の M01 を仕上げた差し替え用の見た目（Spec §6.3 の VisualRoot に入れる静的なモデル）。"
                      "P2（W08 の後）で W02（#4）が作る入口の仮モデルと差し替える。仮モデルの ID は W02 が決める（2026-10-31 時点で未作成）。"
                      "origin_world はアセットのローカル原点で、ワールドの位置と向きは W02 が決める（W09 の推奨は placement_hint）。"
                      "原点は接地面の中央（z=0）、正面は +Y（Resonite の +Z）。門扉 2 枚は蝶番を原点にした別オブジェクトで、"
                      "回転 0 で閉じ、±90° で開いた形（leaves）。発光（ランタン・看板）とコライダーは含めず、P2・P3 で Resonite 側に付ける"),
            "future_target": None,
            "replaces_placeholder": None,
        },
    }
    (PROJECT_ROOT / REVIEW_REL).mkdir(parents=True, exist_ok=True)
    if not args.skip_review:
        written = render_reviews(parts, xc, src, decided, uv_all, color_image)
        print(json.dumps({"review": written}))
    # Last, as it joins the parts into one object (the .blend is saved): what the single-sided material hides.
    asset["backface_check"] = backface(parts)
    write_manifest({"assets": [asset]})
    print(json.dumps({"blend": str(blend.relative_to(PROJECT_ROOT)), "triangles": triangles, "split": split,
                      "overlaps": overlaps, "passage": asset["passage"], "placement_check": placed,
                      "leaves": leaf_record, "uv_cover": asset["metrics"]["uv_cover"],
                      "backface_check": asset["backface_check"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
