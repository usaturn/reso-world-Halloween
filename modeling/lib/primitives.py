"""Clean bmesh primitives, hierarchies, UV projection, and mesh metric extraction."""

from __future__ import annotations

import bmesh
import bpy
from mathutils import Matrix, Vector
from modeling.lib.scene import deg_to_rad_tuple


def create_empty(
    name: str,
    collection,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_euler_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    parent=None,
    display_type: str = "PLAIN_AXES",
    display_size: float = 0.25,
):
    """Create a named Empty object with unit scale (1, 1, 1)."""
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = display_type
    obj.empty_display_size = display_size
    obj.location = Vector(location)
    obj.rotation_euler = deg_to_rad_tuple(rotation_euler_deg)
    obj.scale = Vector((1.0, 1.0, 1.0))
    if parent is not None:
        obj.parent = parent
    collection.objects.link(obj)
    return obj


def assign_planar_or_box_uvs(bm: bmesh.types.BMesh, uv_layer_name: str = "UVMap") -> None:
    """Assign deterministic UVs to all faces so front (-Y) face maps [0,1]x[0,1] cleanly."""
    uv_layer = bm.loops.layers.uv.get(uv_layer_name)
    if uv_layer is None:
        uv_layer = bm.loops.layers.uv.new(uv_layer_name)

    xs = [v.co.x for v in bm.verts] or [0.0, 1.0]
    ys = [v.co.y for v in bm.verts] or [0.0, 1.0]
    zs = [v.co.z for v in bm.verts] or [0.0, 1.0]
    span_x = max(max(xs) - min(xs), 1e-5)
    span_y = max(max(ys) - min(ys), 1e-5)
    span_z = max(max(zs) - min(zs), 1e-5)
    min_x, min_y, min_z = min(xs), min(ys), min(zs)

    for face in bm.faces:
        nx, ny, nz = face.normal.x, face.normal.y, face.normal.z
        abs_x, abs_y, abs_z = abs(nx), abs(ny), abs(nz)
        for loop in face.loops:
            co = loop.vert.co
            if abs_y >= abs_x and abs_y >= abs_z:
                # Front (-Y) or Back (+Y) face: U along +X (for -Y front), V along +Z
                u = (co.x - min_x) / span_x if ny <= 0 else 1.0 - (co.x - min_x) / span_x
                v = (co.z - min_z) / span_z
            elif abs_x >= abs_y and abs_x >= abs_z:
                # East (+X) or West (-X) face: U along +Y, V along +Z
                u = (co.y - min_y) / span_y if nx >= 0 else 1.0 - (co.y - min_y) / span_y
                v = (co.z - min_z) / span_z
            else:
                # Top (+Z) or Bottom (-Z) face: U along +X, V along +Y
                u = (co.x - min_x) / span_x
                v = (co.y - min_y) / span_y if nz >= 0 else 1.0 - (co.y - min_y) / span_y
            loop[uv_layer].uv = (u, v)


def finalize_bmesh_object(
    bm: bmesh.types.BMesh,
    name: str,
    collection,
    material=None,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_euler_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    parent=None,
):
    """Convert a BMesh into a Blender Mesh object with outward normals, UVs, and unit scale."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    assign_planar_or_box_uvs(bm, "UVMap")

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    if material is not None:
        mesh.materials.append(material)

    obj = bpy.data.objects.new(name, mesh)
    obj.location = Vector(location)
    obj.rotation_euler = deg_to_rad_tuple(rotation_euler_deg)
    obj.scale = Vector((1.0, 1.0, 1.0))
    if parent is not None:
        obj.parent = parent
    collection.objects.link(obj)
    return obj


def create_ground_box(
    name: str,
    collection,
    size_xyz: tuple[float, float, float],
    material=None,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_euler_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    parent=None,
    local_offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
):
    """Create a box whose default local origin is ground-center (bottom face at z=0)."""
    sx, sy, sz = float(size_xyz[0]), float(size_xyz[1]), float(size_xyz[2])
    ox, oy, oz = float(local_offset[0]), float(local_offset[1]), float(local_offset[2])

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    transform = (
        Matrix.Translation((ox, oy, oz + sz * 0.5))
        @ Matrix.Diagonal((sx, sy, sz, 1.0))
    )
    bmesh.ops.transform(bm, matrix=transform, verts=bm.verts)
    return finalize_bmesh_object(
        bm=bm,
        name=name,
        collection=collection,
        material=material,
        location=location,
        rotation_euler_deg=rotation_euler_deg,
        parent=parent,
    )


def collect_mesh_metrics(objects: list) -> dict:
    """Measure exact triangle, vertex, and material counts from a list of Blender objects."""
    total_tris = 0
    total_verts = 0
    materials = set()

    for obj in objects:
        if obj.type != "MESH" or obj.data is None:
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        total_tris += len(mesh.loop_triangles)
        total_verts += len(mesh.vertices)
        for mat in mesh.materials:
            if mat is not None:
                materials.add(mat.name)

    return {
        "measured": True,
        "triangles": int(total_tris),
        "vertices": int(total_verts),
        "materials": int(len(materials)),
    }
