"""Headless Cycles CPU review image rendering utilities."""

from __future__ import annotations

from pathlib import Path
import bpy
from mathutils import Vector


def render_review_images(
    views: list[dict],
    bg_color: tuple[float, float, float, float] = (0.05, 0.04, 0.09, 1.0),
    width: int = 960,
    height: int = 540,
    samples: int = 24,
) -> list[Path]:
    """Render one or more review views using Cycles CPU and clean up temporary camera/lights.

    Each entry in `views` is a dict:
      - filepath: str | Path
      - location: (x, y, z)
      - target: (tx, ty, tz)
      - lens_mm: float (optional, default 35.0)
    """
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(samples)
    if hasattr(scene.cycles, "use_denoising"):
        scene.cycles.use_denoising = False
    scene.render.resolution_x = int(width)
    scene.render.resolution_y = int(height)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    # Temporary world lighting
    prev_world = scene.world
    world = bpy.data.worlds.new("Temp_Review_World")
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node is not None:
        bg_node.inputs[0].default_value = bg_color
        bg_node.inputs[1].default_value = 1.2
    scene.world = world

    # Temporary sun + fill lights
    key_light_data = bpy.data.lights.new("Temp_Review_KeyLight", type="SUN")
    key_light_data.energy = 3.5
    key_light_data.color = (1.0, 0.95, 0.88)
    key_light_obj = bpy.data.objects.new("Temp_Review_KeyLight", key_light_data)
    key_light_obj.location = Vector((6.0, -8.0, 10.0))
    key_dir = Vector((0.0, 0.0, 0.0)) - key_light_obj.location
    key_light_obj.rotation_euler = key_dir.to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(key_light_obj)

    fill_light_data = bpy.data.lights.new("Temp_Review_FillLight", type="SUN")
    fill_light_data.energy = 1.5
    fill_light_data.color = (0.75, 0.82, 1.0)
    fill_light_obj = bpy.data.objects.new("Temp_Review_FillLight", fill_light_data)
    fill_light_obj.location = Vector((-6.0, 6.0, 7.0))
    fill_dir = Vector((0.0, 0.0, 0.0)) - fill_light_obj.location
    fill_light_obj.rotation_euler = fill_dir.to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill_light_obj)

    cam_data = bpy.data.cameras.new("Temp_Review_Camera")
    cam_obj = bpy.data.objects.new("Temp_Review_Camera", cam_data)
    scene.collection.objects.link(cam_obj)
    prev_camera = scene.camera
    scene.camera = cam_obj

    rendered_paths: list[Path] = []
    try:
        for view in views:
            out_path = Path(view["filepath"]).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            loc = Vector(view["location"])
            target = Vector(view["target"])
            cam_data.lens = float(view.get("lens_mm", 35.0))
            cam_obj.location = loc
            direction = target - loc
            cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str(out_path)
            bpy.ops.render.render(write_still=True)
            rendered_paths.append(out_path)
    finally:
        scene.camera = prev_camera
        scene.world = prev_world
        bpy.data.objects.remove(cam_obj, do_unlink=True)
        bpy.data.cameras.remove(cam_data, do_unlink=True)
        bpy.data.objects.remove(key_light_obj, do_unlink=True)
        bpy.data.lights.remove(key_light_data, do_unlink=True)
        bpy.data.objects.remove(fill_light_obj, do_unlink=True)
        bpy.data.lights.remove(fill_light_data, do_unlink=True)
        bpy.data.worlds.remove(world, do_unlink=True)

    return rendered_paths
