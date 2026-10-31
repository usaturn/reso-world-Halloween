"""Inspect the received Meshy GLBs (W09, Issue #13) and write the measured values into ``assets/meshy/received.json``.

Run (project directory):
    resoloop blender run modeling/meshy/intake_inspect.py --json
    resoloop blender run modeling/meshy/intake_inspect.py --arg=--rows --arg=M01,M02 --arg=--previews --arg=<dir> --json

Each row's GLB is read from ``source.copy_path`` (the copy outside Git) after its SHA-256 is checked against the
row. Only the ``measured`` and ``derived`` blocks of each row are replaced; the hand-written blocks (``source``,
``decided``, ``budget``, ``split_and_attach``, ``double_sided``) stay as they are.

- ``measured``: values in the GLB's own units and Blender axes after the glTF import (+Z up; a Meshy model's front,
  glTF +Z, is Blender -Y), plus ``backface_check`` (what a single-sided material hides)
- ``derived``: the decided placement (``decided.origin_source``, ``scale``, ``yaw_deg``) applied to the real vertices:
  size and bounds in metres, the named points of ``decided.points_source`` in the asset's local metres, the surface
  area and the texel density each texture size would give

``--previews DIR`` also writes Workbench previews (front, right, back, left, top, 3/4) to ``DIR`` for inspection.
They are not the review images (``review_views.py`` renders those at the decided size).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import bpy  # type: ignore
import numpy as np

from modeling.meshy import glb, meshops, metrics

RECEIVED = PROJECT_ROOT / "assets" / "meshy" / "received.json"
GAP_HEIGHTS = (0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
SILHOUETTE_PIXELS = 480  # along the longest side


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def r(v: float, n: int = 4) -> float:
    return round(float(v), n)


def images_and_materials(obj) -> tuple[list[dict], list[dict]]:
    materials = []
    users: dict[str, list[str]] = {}
    for mat in obj.data.materials:
        materials.append({
            "name": mat.name,
            "blend_method": getattr(mat, "surface_render_method", None),
            "use_backface_culling": bool(mat.use_backface_culling),
        })
        for name, sockets in meshops.image_users(mat).items():
            users.setdefault(name, []).extend(sockets)
    images = []
    for img in bpy.data.images:
        if img.name in {"Render Result", "Viewer Node"}:
            continue
        info = {
            "name": img.name,
            "size": [int(img.size[0]), int(img.size[1])],
            "channels": int(img.channels),
            "colorspace": img.colorspace_settings.name,
            "format": img.file_format,
            "used_by": sorted(set(users.get(img.name, []))),
        }
        if "Base Color" in info["used_by"] and img.channels == 4:
            px = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
            img.pixels.foreach_get(px)
            info["alpha_min"] = r(px[3::4].min(), 3)
        images.append(info)
    return images, materials


def silhouette(positions: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> dict:
    """Interior empty spans (openings) in the front (X across, Z up) and side (Y across, Z up) silhouettes."""
    extent = float((hi - lo).max())
    pixel = extent / SILHOUETTE_PIXELS
    out = {"pixel": r(pixel, 5)}
    for name, axis in (("front_x", 0), ("side_y", 1)):
        grid = metrics.occupancy(positions, (axis, 2), (lo[axis], lo[2]), (hi[axis], hi[2]), pixel)
        rows = {}
        for frac in GAP_HEIGHTS:
            row = min(grid.shape[0] - 1, int(np.rint(frac * (hi[2] - lo[2]) / pixel)))
            spans = metrics.gaps(grid[row], min_pixels=max(2, int(0.02 * grid.shape[1])))
            rows[f"{frac:.2f}"] = [[r(lo[axis] + a * pixel), r(lo[axis] + b * pixel)] for a, b in spans]
        out[name] = rows
    return out


def outline(co: np.ndarray, bands: int = 20) -> list:
    """[x min, x max, y min, y max] of the vertices in each of ``bands`` slices of the height, bottom first."""
    lo, hi = co[:, 2].min(), co[:, 2].max()
    k = np.minimum(((co[:, 2] - lo) / (hi - lo) * bands).astype(int), bands - 1)
    res = []
    for band in range(bands):
        s = co[k == band]
        res.append([r(v) for v in (s[:, 0].min(), s[:, 0].max(), s[:, 1].min(), s[:, 1].max())] if len(s) else None)
    return res


TEXEL_SIZES = (1024, 2048, 4096)


def derive(row: dict, obj, positions: np.ndarray, uv_area: float) -> dict:
    d = row["decided"]
    matrix = metrics.placement_matrix(d["origin_source"], d["yaw_deg"], d["scale"])
    co = metrics.transform_points(matrix, meshops.vertex_array(obj))
    lo, hi = co.min(axis=0), co.max(axis=0)
    area = metrics.triangle_area_sum(positions) * float(d["scale"]) ** 2
    points = {name: [r(v, 3) for v in metrics.transform_points(matrix, np.asarray(p))[0]]
              for name, p in d.get("points_source", {}).items()}
    return {
        "tool": "modeling/meshy/intake_inspect.py",
        "dimensions_m": {"width_x": r(hi[0] - lo[0], 3), "depth_y": r(hi[1] - lo[1], 3), "height_z": r(hi[2] - lo[2], 3)},
        "bounds_local_m": {"min": [r(v, 3) for v in lo], "max": [r(v, 3) for v in hi]},
        "points_local_m": points,
        "surface_area_m2": r(area, 1),
        "texels_per_m": {str(px): r(px * (uv_area / area) ** 0.5, 1) for px in TEXEL_SIZES},
    }


def inspect_row(row: dict, previews: Path | None) -> dict:
    path = Path(row["source"]["copy_path"])
    digest = sha256(path)
    if digest != row["source"]["sha256"]:
        raise SystemExit(f"{row['row_id']}: SHA-256 {digest} does not match received.json")
    gl = glb.summarize(glb.read_glb_json(path))
    meshes = meshops.import_glb(path)
    imported_objects = len(bpy.context.scene.objects)
    obj = meshops.join_meshes(meshes)
    vertices_imported = len(obj.data.vertices)
    tris = meshops.triangles(obj)
    images, materials = images_and_materials(obj)
    positions, uv = meshops.triangle_arrays(obj)
    cover = metrics.uv_cover(uv)
    removed = meshops.weld(obj)
    co = meshops.vertex_array(obj)
    lo, hi = co.min(axis=0), co.max(axis=0)
    extent = float((hi - lo).max())
    topo = meshops.topology(obj, extent)
    with tempfile.TemporaryDirectory() as tmp:
        culling = meshops.backface_check(obj, Path(tmp))
    if previews is not None:
        meshops.ortho_views(obj, previews, row["row_id"])
    derived = derive(row, obj, positions, cover["area_sum"]) if "decided" in row else None
    return derived, {
        "tool": "modeling/meshy/intake_inspect.py",
        "blender": bpy.app.version_string,
        "measured_on": dt.date.today().isoformat(),
        "units": "GLB units (Meshy normalises the longest side to about 1.9); Blender axes after glTF import",
        "glb": gl,
        "objects_imported": imported_objects,
        "mesh_objects": len(meshes),
        "bounds_blender": {"min": [r(v) for v in lo], "max": [r(v) for v in hi], "size": [r(v) for v in hi - lo]},
        "triangles": tris,
        "vertices_imported": vertices_imported,
        "vertices_welded": vertices_imported - removed,
        "materials": materials,
        "images": images,
        "uv": {"layers": len(obj.data.uv_layers), "area_sum": r(cover["area_sum"]),
               "corners_in_unit_square": r(cover["corners_in_unit_square"])},
        "topology": topo,
        "outline_20": outline(co),
        "openings": silhouette(positions, lo, hi),
        "backface_check": culling,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rows", default="", help="comma-separated row_id values (default: every row)")
    p.add_argument("--previews", type=Path, default=None)
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    wanted = {x for x in args.rows.split(",") if x}
    doc = json.loads(RECEIVED.read_text(encoding="utf-8"))
    for row in doc["assets"]:
        if wanted and row["row_id"] not in wanted:
            continue
        derived, row["measured"] = inspect_row(row, args.previews)
        if derived is not None:
            row["derived"] = derived
        m = row["measured"]
        print(f"{row['row_id']}: tris={m['triangles']} size={m['bounds_blender']['size']} "
              f"components={m['topology']['components']} floating={m['topology']['floating_pieces']}")
        RECEIVED.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
