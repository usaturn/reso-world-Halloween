"""Deterministic scene initialization, collection management, and .blend saving."""

from __future__ import annotations

import math
import random
from pathlib import Path
import bpy


def reset_scene(collection_name: str, seed: int = 42):
    """Clear all datablocks in bpy.data for deterministic, idempotent rebuilds."""
    random.seed(seed)
    scene = bpy.context.scene

    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh, do_unlink=True)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat, do_unlink=True)
    for img in list(bpy.data.images):
        if img.name not in {"Render Result", "Viewer Node"}:
            bpy.data.images.remove(img, do_unlink=True)
    for cam in list(bpy.data.cameras):
        bpy.data.cameras.remove(cam, do_unlink=True)
    for lgt in list(bpy.data.lights):
        bpy.data.lights.remove(lgt, do_unlink=True)
    for curve in list(bpy.data.curves):
        bpy.data.curves.remove(curve, do_unlink=True)

    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    target_col = bpy.data.collections.new(collection_name)
    scene.collection.children.link(target_col)
    return scene, target_col


def ensure_collection(name: str, parent=None):
    """Get or create a collection and link it under parent (or scene root)."""
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        if parent is None:
            bpy.context.scene.collection.children.link(col)
        else:
            parent.children.link(col)
    return col


def deg_to_rad_tuple(euler_deg: tuple[float, float, float] | list[float]) -> tuple[float, float, float]:
    """Convert (rx, ry, rz) in degrees to radians."""
    return (
        math.radians(float(euler_deg[0])),
        math.radians(float(euler_deg[1])),
        math.radians(float(euler_deg[2])),
    )


def save_blend(filepath: str | Path, pack_images: bool = True) -> Path:
    """Save the current Blender scene deterministically to filepath."""
    out_path = Path(filepath).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if pack_images:
        for img in bpy.data.images:
            if img.name in {"Render Result", "Viewer Node"}:
                continue
            if img.packed_file is None and img.filepath:
                img.pack()

    bpy.ops.wm.save_as_mainfile(filepath=str(out_path), check_existing=False, relative_remap=False)
    return out_path
