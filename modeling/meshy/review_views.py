"""Render the four-direction review image of each received Meshy GLB at the size decided in ``received.json`` (W09).

Run (project directory):
    resoloop blender run modeling/meshy/review_views.py --json
    resoloop blender run modeling/meshy/review_views.py --arg=--rows --arg=M01 --json

Output: ``review/meshy/<row_id>_views.png`` (1024 x 1024). Each GLB is placed with ``decided`` (origin to
(0, 0, 0), uniform scale to metres, yaw so the front faces +Y) and rendered with ``modeling.lib.render``
(Cycles CPU, ``docs/conventions.md`` §7.4) from four directions:

    top left: from +Y (the front)   top right: from +X
    bottom left: from -Y (the back) bottom right: from -X

A grey 1.8 m figure (a capsule; render only) stands off the front-right corner for scale, on the asset's lowest point. A sun
from the front side is added to the lights of ``render_review_images``, whose key light comes from -Y.
Nothing is saved to a ``.blend``.
"""

from __future__ import annotations

import argparse
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
from mathutils import Matrix  # type: ignore

from modeling.lib.render import render_review_images
from modeling.meshy import meshops, metrics

RECEIVED = PROJECT_ROOT / "assets" / "meshy" / "received.json"
OUT_DIR = PROJECT_ROOT / "review" / "meshy"
VIEW_PX = 512
LENS_MM = 85.0
FIGURE_HEIGHT = 1.8


def place(obj, decided: dict) -> None:
    obj.matrix_world = Matrix(metrics.placement_matrix(decided["origin_source"], decided["yaw_deg"], decided["scale"]).tolist())
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def add_figure(x: float, y: float, z: float) -> list:
    """A 1.8 m capsule standing at (x, y, z): render-only scale reference."""
    mat = bpy.data.materials.new("Review_Figure")
    mat.diffuse_color = (0.55, 0.55, 0.55, 1.0)
    radius = 0.22
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=FIGURE_HEIGHT - 2 * radius,
                                        location=(x, y, z + FIGURE_HEIGHT / 2))
    body = bpy.context.active_object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(x, y, z + FIGURE_HEIGHT - radius))
    head = bpy.context.active_object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(x, y, z + radius))
    foot = bpy.context.active_object
    for o in (body, head, foot):
        o.data.materials.append(mat)
    return [body, head, foot]


def compose(paths: list[Path], out: Path) -> None:
    tiles = []
    for p in paths:
        img = bpy.data.images.load(str(p), check_existing=False)
        px = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        tiles.append(px.reshape(img.size[1], img.size[0], 4))
        bpy.data.images.remove(img)
    # Blender rows run bottom-up: the first tile goes top left.
    top = np.concatenate([tiles[0], tiles[1]], axis=1)
    bottom = np.concatenate([tiles[2], tiles[3]], axis=1)
    sheet = np.concatenate([bottom, top], axis=0)
    sheet[:, :, 3] = 1.0
    h, w = sheet.shape[:2]
    image = bpy.data.images.new("Review_Sheet", w, h, alpha=False)
    image.pixels.foreach_set(sheet.ravel())
    image.filepath_raw = str(out)
    image.file_format = "PNG"
    bpy.context.scene.render.image_settings.color_mode = "RGB"
    image.save()
    bpy.data.images.remove(image)


def render_row(row: dict, out_dir: Path) -> Path:
    meshes = meshops.import_glb(Path(row["source"]["copy_path"]))
    obj = meshops.join_meshes(meshes)
    place(obj, row["decided"])
    co = meshops.vertex_array(obj)
    lo, hi = co.min(axis=0), co.max(axis=0)
    fx, fy = float(hi[0]) + 0.6, float(hi[1]) + 0.6
    add_figure(fx, fy, float(lo[2]))
    # render_review_images lights from -Y (its key sun); the fronts face +Y, so add a front sun of the same kind.
    sun = bpy.data.objects.new("Review_FrontSun", bpy.data.lights.new("Review_FrontSun", type="SUN"))
    sun.data.energy = 2.5
    sun.rotation_euler = Matrix.Rotation(math.radians(-35), 4, "X").to_euler()
    bpy.context.scene.collection.objects.link(sun)
    # The figure stands off the front-right corner, so no view puts it in front of the asset.
    span = {0: (float(lo[0]), fx + 0.25), 1: (float(lo[1]), fy + 0.25)}
    z0, z1 = float(lo[2]), max(float(hi[2]), float(lo[2]) + FIGURE_HEIGHT)
    half_fov = math.atan(18.0 / LENS_MM)
    views = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, direction, across, depth in (("front", (0, 1, 0), 0, 1), ("right", (1, 0, 0), 1, 0),
                                               ("back", (0, -1, 0), 0, 1), ("left", (-1, 0, 0), 1, 0)):
            a0, a1 = span[across]
            extent = max(a1 - a0, z1 - z0) * 1.08
            centre = np.zeros(3)
            centre[across] = (a0 + a1) / 2
            centre[depth] = (float(lo[depth]) + float(hi[depth])) / 2
            centre[2] = (z0 + z1) / 2
            distance = extent / 2 / math.tan(half_fov) + float(hi[depth] - lo[depth]) / 2
            loc = centre + np.asarray(direction, dtype=np.float64) * distance
            views.append({"filepath": Path(tmp) / f"{name}.png", "location": tuple(loc), "target": tuple(centre),
                          "lens_mm": LENS_MM})
        paths = render_review_images(views, width=VIEW_PX, height=VIEW_PX, samples=24)
        out = out_dir / f"{row['row_id']}_views.png"
        compose(paths, out)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rows", default="")
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    wanted = {x for x in args.rows.split(",") if x}
    doc = json.loads(RECEIVED.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for row in doc["assets"]:
        if wanted and row["row_id"] not in wanted:
            continue
        print(f"{row['row_id']}: {render_row(row, OUT_DIR).relative_to(PROJECT_ROOT)}", flush=True)


if __name__ == "__main__":
    main()
