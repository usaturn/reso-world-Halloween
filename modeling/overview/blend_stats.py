"""Print the counts and external dependencies of the opened `.blend` (W07).

Run inside Blender on an existing file, e.g.:
    resoloop blender run modeling/overview/blend_stats.py --blend blender/A_plaza/A_plaza.blend --json

It prints one line `BLEND_STATS:<json>` and changes nothing (the file is not saved). The fields are used to
compare two builds of the same key (the counts and the sorted object names must not change) and to confirm
that a re-opened file has no missing image or library.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import bpy  # type: ignore

SUFFIX = re.compile(r"\.\d{3}$")
SKIP_IMAGES = {"Render Result", "Viewer Node"}


def stats() -> dict:
    objects = sorted(bpy.data.objects, key=lambda o: o.name)
    by_type: dict[str, int] = {}
    triangles = 0
    vertices = 0
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        by_type[obj.type] = by_type.get(obj.type, 0) + 1
        if obj.type == "MESH":
            ev = obj.evaluated_get(depsgraph)
            mesh = ev.to_mesh()
            mesh.calc_loop_triangles()
            triangles += len(mesh.loop_triangles)
            vertices += len(mesh.vertices)
            ev.to_mesh_clear()

    images = []
    missing_images = []
    for img in bpy.data.images:
        if img.name in SKIP_IMAGES:
            continue
        packed = img.packed_file is not None
        path = bpy.path.abspath(img.filepath) if img.filepath else ""
        exists = bool(path) and Path(path).is_file()
        images.append({"name": img.name, "packed": packed, "size": list(img.size)})
        if not packed and not exists and img.source == "FILE":
            missing_images.append(img.name)

    libraries = [{"name": lib.name, "filepath": lib.filepath} for lib in bpy.data.libraries]
    names = [o.name for o in objects]
    suffixed = sorted(
        n
        for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.collections)
        for n in (d.name for d in coll)
        if SUFFIX.search(n)
    )
    return {
        "blend_file": bpy.data.filepath,
        "objects": len(objects),
        "objects_by_type": dict(sorted(by_type.items())),
        "meshes": len(bpy.data.meshes),
        "materials": len(bpy.data.materials),
        "images": len(images),
        "images_packed": sum(1 for i in images if i["packed"]),
        "missing_images": missing_images,
        "libraries": libraries,
        "collections": sorted(c.name for c in bpy.data.collections),
        "triangles": triangles,
        "vertices": vertices,
        "object_names_sha256": hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest(),
        "suffixed_names": suffixed,
    }


if __name__ == "__main__":
    print("BLEND_STATS:" + json.dumps(stats(), ensure_ascii=False))
