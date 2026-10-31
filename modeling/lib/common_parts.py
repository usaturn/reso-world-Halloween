"""Helper for appending/instancing shared common parts from blender/common/common.blend."""

from __future__ import annotations

from pathlib import Path
import bpy
from mathutils import Vector
from modeling.lib.scene import deg_to_rad_tuple


def append_common_part(
    common_blend_path: str | Path,
    source_object_name: str,
    instance_name: str,
    collection,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_euler_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    parent=None,
):
    """Append a shared mesh/object from common.blend and place an instance with a stable ID.

    Reuses the imported mesh datablock when multiple instances of the same common part
    are placed in an area scene, keeping memory and draw resources shared.
    """
    blend_path = Path(common_blend_path).resolve()
    if not blend_path.is_file():
        raise FileNotFoundError(f"Common blend file not found: {blend_path}")

    cached_mesh_name = f"SharedMesh_{source_object_name}"
    mesh = bpy.data.meshes.get(cached_mesh_name)
    if mesh is None:
        with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
            if source_object_name not in data_from.objects:
                raise KeyError(
                    f"Object '{source_object_name}' not found in {blend_path}. "
                    f"Available: {list(data_from.objects)}"
                )
            data_to.objects = [source_object_name]

        imported_obj = data_to.objects[0]
        if imported_obj.data is not None:
            mesh = imported_obj.data
            mesh.name = cached_mesh_name
        bpy.data.objects.remove(imported_obj, do_unlink=True)

    obj = bpy.data.objects.new(instance_name, mesh)
    obj.location = Vector(location)
    obj.rotation_euler = deg_to_rad_tuple(rotation_euler_deg)
    obj.scale = Vector((1.0, 1.0, 1.0))
    if parent is not None:
        obj.parent = parent
    collection.objects.link(obj)
    return obj
