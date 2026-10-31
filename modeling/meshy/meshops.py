"""Blender helpers shared by ``intake_inspect.py`` and ``finish.py`` (run inside Blender only)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import bmesh  # type: ignore
import bpy  # type: ignore
import numpy as np
from mathutils import Matrix, Vector, kdtree  # type: ignore

WELD_DISTANCE = 1e-6


def empty_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"


def import_glb(path: Path) -> list[Any]:
    """Import ``path`` into an empty scene. Returns the mesh objects; refuses anything but a static mesh hierarchy."""
    empty_scene()
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = list(bpy.context.scene.objects)
    meshes = [o for o in objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"{path.name}: no mesh")
    for obj in objects:
        if obj.type not in {"MESH", "EMPTY"} or obj.animation_data or obj.constraints:
            raise RuntimeError(f"{obj.name}: not a static mesh hierarchy ({obj.type})")
        if obj.type == "MESH" and (obj.data.shape_keys or obj.modifiers):
            raise RuntimeError(f"{obj.name}: shape keys or modifiers")
    return meshes


def join_meshes(meshes: list[Any]) -> Any:
    """Join the imported meshes into one object with all transforms applied; other objects are removed."""
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    for other in list(bpy.context.scene.objects):
        if other is not obj:
            bpy.data.objects.remove(other, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return obj


def vertex_array(obj: Any) -> np.ndarray:
    co = np.empty(len(obj.data.vertices) * 3, dtype=np.float64)
    obj.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def triangle_arrays(obj: Any) -> tuple[np.ndarray, np.ndarray]:
    """(positions F x 3 x 3, uvs F x 3 x 2) of the evaluated loop triangles of the active UV map."""
    me = obj.data
    me.calc_loop_triangles()
    count = len(me.loop_triangles)
    verts = np.empty(count * 3, dtype=np.int64)
    loops = np.empty(count * 3, dtype=np.int64)
    me.loop_triangles.foreach_get("vertices", verts)
    me.loop_triangles.foreach_get("loops", loops)
    co = vertex_array(obj)
    positions = co[verts].reshape(-1, 3, 3)
    uv = np.zeros((count * 3, 2), dtype=np.float64)
    if me.uv_layers.active is not None:
        all_uv = np.empty(len(me.loops) * 2, dtype=np.float64)
        me.uv_layers.active.data.foreach_get("uv", all_uv)
        uv = all_uv.reshape(-1, 2)[loops]
    return positions, uv.reshape(-1, 3, 2)


def triangles(obj: Any) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def weld(obj: Any, dist: float = WELD_DISTANCE) -> int:
    """Weld coincident vertices (glTF splits a vertex at every UV or normal seam). UVs stay per face corner, so the
    seams survive. Returns the number of vertices removed."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    before = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    removed = before - len(bm.verts)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return removed


def _components(bm: Any) -> list[list[Any]]:
    """Faces grouped by edge connectivity."""
    bm.faces.ensure_lookup_table()
    seen: set[int] = set()
    groups = []
    for face in bm.faces:
        if face.index in seen:
            continue
        stack = [face]
        seen.add(face.index)
        group = []
        while stack:
            f = stack.pop()
            group.append(f)
            for edge in f.edges:
                for g in edge.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        groups.append(group)
    groups.sort(key=len, reverse=True)
    return groups


def _boundary_loops(bm: Any) -> int:
    boundary = [e for e in bm.edges if e.is_boundary]
    seen: set[int] = set()
    loops = 0
    for edge in boundary:
        if edge.index in seen:
            continue
        loops += 1
        stack = [edge]
        seen.add(edge.index)
        while stack:
            e = stack.pop()
            for v in e.verts:
                for f in v.link_edges:
                    if f.is_boundary and f.index not in seen:
                        seen.add(f.index)
                        stack.append(f)
    return loops


def topology(obj: Any, extent: float, detail_limit: int = 40) -> dict[str, Any]:
    """Holes, loose pieces and flipped normals of a welded mesh (the object is not changed).

    - ``boundary_edges``/``boundary_loops``: open edges after welding and the holes they form
    - ``components``: pieces joined by edges; for up to ``detail_limit`` pieces after the largest, the gap to the
      nearest vertex of any other piece; a piece further than 0.5 % of the largest extent is ``floating``
    - normals: ``bmesh.ops.recalc_face_normals`` makes each piece consistent (outward when closed); a piece it turns
      almost entirely is counted as ``components_inside_out``, single turned faces as ``faces_inconsistent``
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    for i, e in enumerate(bm.edges):
        e.index = i
    boundary_edges = sum(1 for e in bm.edges if e.is_boundary)
    nonmanifold_edges = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    wire_edges = sum(1 for e in bm.edges if not e.link_faces)
    loops = _boundary_loops(bm)
    groups = _components(bm)
    tri_counts = [sum(len(f.verts) - 2 for f in g) for g in groups]
    total_tris = sum(tri_counts)

    before = {f.index: f.normal.copy() for f in bm.faces}
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    inside_out = 0
    inconsistent = 0
    for g in groups:
        flips = sum(1 for f in g if f.normal.dot(before[f.index]) < 0)
        if flips >= 0.9 * len(g) and flips > 0:
            inside_out += 1
        else:
            inconsistent += flips

    pieces = []
    threshold = 0.005 * extent
    for rank, g in enumerate(groups[1 : 1 + detail_limit], start=1):
        own = {v.index for f in g for v in f.verts}
        tree = kdtree.KDTree(len(bm.verts) - len(own))
        for v in bm.verts:
            if v.index not in own:
                tree.insert(v.co, v.index)
        tree.balance()
        gap = min(tree.find(bm.verts[i].co)[2] for i in own)
        co = np.array([bm.verts[i].co[:] for i in own])
        pieces.append({
            "rank": rank,
            "triangles": tri_counts[rank],
            "center": [round(float(x), 4) for x in (co.min(axis=0) + co.max(axis=0)) / 2],
            "size": [round(float(x), 4) for x in co.max(axis=0) - co.min(axis=0)],
            "gap_to_other_pieces": round(float(gap), 5),
            "floating": bool(gap > threshold),
        })
    bm.free()
    return {
        "boundary_edges": boundary_edges,
        "boundary_loops": loops,
        "nonmanifold_edges": nonmanifold_edges,
        "wire_edges": wire_edges,
        "components": len(groups),
        "largest_component_triangle_share": round(tri_counts[0] / total_tris, 4) if total_tris else None,
        "pieces_after_largest": pieces,
        "pieces_not_detailed": max(0, len(groups) - 1 - detail_limit),
        "floating_pieces": sum(1 for p in pieces if p["floating"]),
        "floating_threshold": round(threshold, 5),
        "components_inside_out": inside_out,
        "faces_inconsistent": inconsistent,
    }


def image_users(material: Any) -> dict[str, list[str]]:
    """Image name -> the Principled BSDF inputs it reaches (through Separate Color and Normal Map nodes)."""
    tree = material.node_tree
    found: dict[str, list[str]] = {}

    def walk(node: Any, path: list[str]) -> None:
        for out in node.outputs:
            for link in out.links:
                to = link.to_node
                if to.type == "BSDF_PRINCIPLED":
                    found.setdefault(path[0], []).append(link.to_socket.name)
                elif to.type in {"SEPARATE_COLOR", "SEPARATE_RGB", "NORMAL_MAP", "MATH", "MIX", "MIX_RGB"}:
                    walk(to, path)
                elif to.type == "OUTPUT_MATERIAL":
                    found.setdefault(path[0], []).append(f"output:{link.to_socket.name}")

    for node in tree.nodes:
        if node.type == "TEX_IMAGE" and node.image is not None:
            walk(node, [node.image.name])
    return {k: sorted(set(v)) for k, v in found.items()}


def ortho_views(obj: Any, out_dir: Path, prefix: str, size: int = 640) -> list[Path]:
    """Workbench previews with the texture colours: front (-Y), right (+X), back (+Y), left (-X), top, and a 3/4 view.
    For inspection only (the committed review images use Cycles)."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "TEXTURE"
    shading.show_backface_culling = False
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.image_settings.file_format = "PNG"
    lo = vertex_array(obj).min(axis=0)
    hi = vertex_array(obj).max(axis=0)
    centre = Vector(((lo + hi) / 2).tolist())
    extent = float((hi - lo).max())
    cam_data = bpy.data.cameras.new("Inspect_Camera")
    cam = bpy.data.objects.new("Inspect_Camera", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    views = [
        ("front", Vector((0, -1, 0))),
        ("right", Vector((1, 0, 0))),
        ("back", Vector((0, 1, 0))),
        ("left", Vector((-1, 0, 0))),
        ("top", Vector((0, 0, 1))),
        ("threequarter", Vector((0.7, -1.0, 0.55)).normalized()),
    ]
    paths = []
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        for name, direction in views:
            cam_data.type = "PERSP" if name == "threequarter" else "ORTHO"
            cam_data.ortho_scale = extent * 1.1
            cam_data.lens = 40.0
            cam_data.clip_end = extent * 20
            distance = extent * (2.4 if name == "threequarter" else 3.0)
            cam.location = centre + direction * distance
            cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
            if name == "top":
                cam.rotation_euler = (0.0, 0.0, 0.0)
            path = out_dir / f"{prefix}_{name}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            paths.append(path)
    finally:
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cam_data, do_unlink=True)
    return paths


def _render_pixels(path: Path) -> np.ndarray:
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(path), check_existing=False)
    px = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(-1, 4)


def backface_check(obj: Any, work_dir: Path, size: int = 320) -> dict[str, Any]:
    """What a single-sided material (Resonite's default; the exporter drops glTF ``doubleSided``) hides.

    Six orthographic Workbench views (front -Y, back +Y, left -X, right +X, top, bottom) are rendered twice, without
    and with backface culling. ``see_through`` counts pixels that show the object without culling and the empty
    background with it (a hole you can look through); ``changed`` counts pixels whose colour changes while something
    stays visible (a back face was in front of another surface). Both are shares of the object's pixels.
    """
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.film_transparent = True
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "TEXTURE"
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    co = vertex_array(obj)
    lo, hi = co.min(axis=0), co.max(axis=0)
    centre = Vector(((lo + hi) / 2).tolist())
    extent = float((hi - lo).max())
    cam_data = bpy.data.cameras.new("Cull_Camera")
    cam = bpy.data.objects.new("Cull_Camera", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = extent * 1.05
    cam_data.clip_end = extent * 20
    work_dir.mkdir(parents=True, exist_ok=True)
    views = {"front": (0, -1, 0), "back": (0, 1, 0), "left": (-1, 0, 0), "right": (1, 0, 0),
             "top": (0, 0, 1), "bottom": (0, 0, -1)}
    result: dict[str, Any] = {"method": "Workbench orthographic, culling off vs on", "pixels": size, "views": {}}
    try:
        for name, d in views.items():
            direction = Vector(d)
            cam.location = centre + direction * extent * 3
            up = "Y" if name not in {"top", "bottom"} else "X"
            cam.rotation_euler = (-direction).to_track_quat("-Z", up).to_euler()
            out = []
            for cull in (False, True):
                shading.show_backface_culling = cull
                path = work_dir / f"cull_{name}_{int(cull)}.png"
                scene.render.filepath = str(path)
                out.append(_render_pixels(path))
            off, on = out
            visible = off[:, 3] > 0.5
            count = int(visible.sum())
            through = visible & (on[:, 3] <= 0.5)
            changed = visible & (on[:, 3] > 0.5) & (np.abs(off[:, :3] - on[:, :3]).max(axis=1) > 0.08)
            result["views"][name] = {
                "object_pixels": count,
                "see_through": round(float(through.sum()) / max(count, 1), 5),
                "changed": round(float(changed.sum()) / max(count, 1), 5),
            }
    finally:
        shading.show_backface_culling = False
        scene.render.film_transparent = False
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cam_data, do_unlink=True)
    worst = max(result["views"].values(), key=lambda v: v["see_through"])
    result["max_see_through"] = worst["see_through"]
    result["max_changed"] = max(v["changed"] for v in result["views"].values())
    return result


def rotation_z(deg: float) -> Matrix:
    return Matrix.Rotation(math.radians(deg), 4, "Z")
