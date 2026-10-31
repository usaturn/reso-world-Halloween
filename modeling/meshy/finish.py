"""Common finishing of one received Meshy GLB (W09): placement, texture sizes and an exportable material.

Run (project directory; the output directory must not exist yet and lies outside Git):
    resoloop blender run modeling/meshy/finish.py --arg=--row --arg=M02 \\
        --arg=--name --arg=M02_GiantPumpkin_001 \\
        --arg=--output-dir --arg=/workspaces/reso-world/worlds/reso-world-Halloween-meshy/finished/M02 --json
    Optional: --arg=--color-px --arg=2048 --arg=--data-px --arg=1024 (default: the row's ``budget``)
              --arg=--closeup --arg=<points_local_m name> --arg=--closeup-distance --arg=3.0
              --arg=--closeup-out --arg=review/<key>/<file>.png

Steps (the decisions come from ``assets/meshy/received.json``; nothing is guessed here):

1. Check the copy's SHA-256 against the row, import it and join it into one mesh object.
2. Place it with ``decided``: ``origin_source`` to (0, 0, 0), uniform ``scale`` to metres, ``yaw_deg`` so the front
   faces +Y; the transform is applied to the mesh (object transform stays identity, scale 1).
3. Name the object and mesh ``--name`` (``<M>_<AssetName>_<NNN>``), the material ``MAT_<M>_<AssetName>``, and put
   the object in a collection named after the key (``docs/conventions.md`` §3).
4. Material for ``resoloop blender export --pack-pbr``: the glTF importer feeds metallic and roughness through a
   Separate Color node, which the exporter rejects; the metallicRoughness image is split into a roughness (G) and
   a metallic (B) greyscale Non-Color image, each wired straight to its input. A map whose values span less than
   2/255 becomes the constant (its median) instead of an image. The base colour image is scaled down to
   ``--color-px`` and the data maps to ``--data-px`` (never up). Images are saved as PNG under ``textures/`` and packed.
5. Save ``<name>.blend`` and ``meta.json`` (counts, sizes, UV cover, textures) in the output directory.

Reduction (weld, decimate, new UVs, bake from the source) is not part of this step: every row of the confirmed set
is under its ``budget.triangles_max``. ``docs/meshy-intake.md`` records how to add it if a row needs it.
Export and validation are separate commands (``docs/meshy-intake.md``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import bpy  # type: ignore
import numpy as np
from mathutils import Matrix, Vector  # type: ignore

from modeling.lib.render import render_review_images
from modeling.meshy import meshops, metrics

RECEIVED = PROJECT_ROOT / "assets" / "meshy" / "received.json"
CONSTANT_SPAN = 2.0 / 255.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def place(obj, decided: dict) -> None:
    obj.matrix_world = Matrix(metrics.placement_matrix(decided["origin_source"], decided["yaw_deg"], decided["scale"]).tolist())
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def pixels(image) -> np.ndarray:
    px = np.empty(image.size[0] * image.size[1] * 4, dtype=np.float32)
    image.pixels.foreach_get(px)
    return px.reshape(image.size[1], image.size[0], 4)


def save_png(name: str, data: np.ndarray, colorspace: str, path: Path, size: int) -> object:
    """Write ``data`` (H x W x 4, 0..1) as an 8-bit PNG scaled to at most ``size`` px, reload it and pack it."""
    h, w = data.shape[:2]
    image = bpy.data.images.new(name, w, h, alpha=False)
    image.colorspace_settings.name = colorspace
    image.pixels.foreach_set(data.astype(np.float32).ravel())
    if max(w, h) > size:
        image.scale(size, size)
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    loaded = bpy.data.images.load(str(path), check_existing=False)
    loaded.name = name
    loaded.colorspace_settings.name = colorspace
    loaded.pack()
    return loaded


def principled_of(material):
    tree = material.node_tree
    output = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
    shader = output.inputs["Surface"].links[0].from_node
    if shader.type != "BSDF_PRINCIPLED":
        raise SystemExit(f"{material.name}: surface is {shader.type}, not a Principled BSDF")
    return tree, shader


def linked_image(socket):
    """The image node feeding ``socket`` directly or through one Separate Color node, and that node's output."""
    if not socket.is_linked:
        return None, None
    node = socket.links[0].from_node
    if node.type == "TEX_IMAGE":
        return node, None
    if node.type in {"SEPARATE_COLOR", "SEPARATE_RGB"}:
        src = node.inputs[0].links[0].from_node if node.inputs[0].is_linked else None
        if src is not None and src.type == "TEX_IMAGE":
            return src, socket.links[0].from_socket.name
    raise SystemExit(f"{socket.name}: fed by {node.type}; only an image or Separate Color of an image is handled")


def adapt_material(material, name: str, tex_dir: Path, color_px: int, data_px: int) -> dict:
    tree, bsdf = principled_of(material)
    info: dict = {}
    for node in tree.nodes:
        if node.type == "NORMAL_MAP":
            raise SystemExit(f"{material.name}: has a normal map; the confirmed set has none, extend finish.py first")
    color_node, _ = linked_image(bsdf.inputs["Base Color"])
    if color_node is None:
        raise SystemExit(f"{material.name}: Base Color has no image")
    color = pixels(color_node.image)
    new_color = save_png(f"{name}_color", color, "sRGB", tex_dir / f"{name}_color.png", color_px)
    color_node.image = new_color
    info["color"] = {"file": f"textures/{name}_color.png", "size": list(new_color.size), "source_size": [color.shape[1], color.shape[0]]}

    sources = {}
    for socket in ("Metallic", "Roughness"):
        node, channel = linked_image(bsdf.inputs[socket])
        sources[socket] = (node, channel)
    for socket, (node, channel) in sources.items():
        if node is None:
            info[socket.lower()] = {"constant": round(float(bsdf.inputs[socket].default_value), 4), "source": "constant"}
            continue
        px = pixels(node.image)
        index = {"Red": 0, "Green": 1, "Blue": 2, "R": 0, "G": 1, "B": 2, None: 0}[channel]
        values = px[:, :, index]
        lo, hi = float(values.min()), float(values.max())
        for link in list(bsdf.inputs[socket].links):
            tree.links.remove(link)
        if hi - lo < CONSTANT_SPAN:
            bsdf.inputs[socket].default_value = float(np.median(values))
            info[socket.lower()] = {"constant": round(float(np.median(values)), 4), "source": f"{channel} channel, span {hi - lo:.4f}"}
            continue
        grey = np.repeat(values[:, :, None], 4, axis=2)
        grey[:, :, 3] = 1.0
        role = socket.lower()
        image = save_png(f"{name}_{role}", grey, "Non-Color", tex_dir / f"{name}_{role}.png", data_px)
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.name = tex.label = f"{name}_{role}"
        tex.image = image
        tex.interpolation = "Linear"
        tex.extension = "REPEAT"
        uv_input = color_node.inputs["Vector"]
        if uv_input.is_linked:
            raise SystemExit(f"{material.name}: the colour image has a linked Vector input; handled only unlinked")
        tree.links.new(tex.outputs["Color"], bsdf.inputs[socket])
        info[role] = {"file": f"textures/{name}_{role}.png", "size": list(image.size), "source": f"{channel} channel",
                      "range": [round(lo, 4), round(hi, 4)]}
    for node in list(tree.nodes):
        unused_image = node.type == "TEX_IMAGE" and not any(o.is_linked for o in node.outputs)
        if node.type in {"SEPARATE_COLOR", "SEPARATE_RGB"} or unused_image:
            tree.nodes.remove(node)
    material.name = f"MAT_{name.rsplit('_', 1)[0]}"
    return info


def closeup(obj, point: list[float], distance: float, out: Path) -> Path:
    """A Cycles close-up (``modeling.lib.render``) of ``point`` (local metres), seen from the front side (+Y) at
    ``distance`` m and slightly above."""
    target = Vector(point)
    loc = target + Vector((0.25, 1.0, 0.25)).normalized() * distance
    render_review_images([{"filepath": out, "location": tuple(loc), "target": tuple(target), "lens_mm": 50.0}],
                         width=960, height=720, samples=32)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--row", required=True)
    p.add_argument("--name", required=True, help="object name <M>_<AssetName>_<NNN>")
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--color-px", type=int, default=None)
    p.add_argument("--data-px", type=int, default=None)
    p.add_argument("--closeup", default=None, help="a decided.points_source name to render a close-up of")
    p.add_argument("--closeup-distance", type=float, default=3.0)
    p.add_argument("--closeup-out", type=Path, default=None)
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    rows = {r["row_id"]: r for r in json.loads(RECEIVED.read_text(encoding="utf-8"))["assets"]}
    row = rows[args.row]
    out = args.output_dir.resolve()
    if out.exists():
        raise SystemExit(f"{out} exists; use a new output directory")
    parts = args.name.split("_")
    if len(parts) < 3 or parts[0] != row["key"]:
        raise SystemExit(f"--name must look like {row['key']}_<AssetName>_<NNN>")
    src = Path(row["source"]["copy_path"])
    if sha256(src) != row["source"]["sha256"]:
        raise SystemExit(f"{src}: SHA-256 differs from received.json")
    color_px = args.color_px or row["budget"]["color_px_max"]
    data_px = args.data_px or row["budget"]["data_px_max"]

    obj = meshops.join_meshes(meshops.import_glb(src))
    place(obj, row["decided"])
    obj.name = obj.data.name = args.name
    if len(obj.data.materials) != 1:
        raise SystemExit(f"{args.name}: {len(obj.data.materials)} materials; the confirmed set has one each")
    tex_dir = out / "textures"
    tex_dir.mkdir(parents=True)
    textures = adapt_material(obj.data.materials[0], args.name, tex_dir, color_px, data_px)
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)
    collection = bpy.data.collections.new(row["key"])
    bpy.context.scene.collection.children.link(collection)
    collection.objects.link(obj)
    bpy.context.scene.collection.objects.unlink(obj)

    positions, uv = meshops.triangle_arrays(obj)
    co = meshops.vertex_array(obj)
    lo, hi = co.min(axis=0), co.max(axis=0)
    blend = out / f"{args.name}.blend"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    meta = {
        "row_id": args.row,
        "object": obj.name,
        "collection": collection.name,
        "material": obj.data.materials[0].name,
        "source_sha256": row["source"]["sha256"],
        "triangles": len(positions),
        "triangles_max": row["budget"]["triangles_max"],
        "vertices": len(obj.data.vertices),
        "dimensions_m": [round(float(v), 3) for v in hi - lo],
        "bounds_m": {"min": [round(float(v), 3) for v in lo], "max": [round(float(v), 3) for v in hi]},
        "uv_cover": round(metrics.uv_cover(uv)["area_sum"], 4),
        "textures": textures,
        "placement": {k: row["decided"][k] for k in ("origin_source", "scale", "yaw_deg")},
        "blender": bpy.app.version_string,
    }
    if args.closeup:
        m = metrics.placement_matrix(row["decided"]["origin_source"], row["decided"]["yaw_deg"], row["decided"]["scale"])
        point = metrics.transform_points(m, np.asarray(row["decided"]["points_source"][args.closeup]))[0]
        target = args.closeup_out or out / f"{args.name}_closeup.png"
        if not target.is_absolute():
            target = PROJECT_ROOT / target
        closeup(obj, [float(v) for v in point], args.closeup_distance, target)
        meta["closeup"] = {"point": args.closeup, "distance_m": args.closeup_distance, "image": str(target)}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"finished {args.name}: triangles={meta['triangles']} dims={meta['dimensions_m']} uv_cover={meta['uv_cover']}")


if __name__ == "__main__":
    main()
