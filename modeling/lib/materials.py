"""Exporter-compatible Principled BSDF materials and procedural test texture generation."""

from __future__ import annotations

from pathlib import Path
import struct
import zlib
import bpy


def write_rgba_png(filepath: str | Path, width: int, height: int, rgba_bytes: bytes) -> Path:
    """Write raw RGBA8 top-to-bottom scanlines to a valid PNG file using stdlib only."""
    out_path = Path(filepath).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    raw_rows = bytearray()
    stride = width * 4
    for y in range(height):
        raw_rows.append(0)  # Filter type 0 (None)
        row_start = y * stride
        raw_rows.extend(rgba_bytes[row_start : row_start + stride])

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type)
        crc = zlib.crc32(data, crc) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw_rows), level=9)
    png_data = (
        b"\x89PNG\r\n\x1a\n"
        + make_chunk(b"IHDR", ihdr)
        + make_chunk(b"IDAT", idat)
        + make_chunk(b"IEND", b"")
    )
    out_path.write_bytes(png_data)
    return out_path


def generate_asymmetric_test_png(filepath: str | Path, width: int = 256, height: int = 256) -> Path:
    """Create an asymmetric test texture to verify UV orientation (Top/Bottom/Left/Right).

    Image coordinates (top-to-bottom scanlines, UV (0,1) at top-left, UV (1,0) at bottom-right):
    - Top-Left (U < 0.5, V >= 0.5): Halloween Orange (245, 120, 30)
    - Top-Right (U >= 0.5, V >= 0.5): Magical Purple (115, 50, 210)
    - Bottom-Left (U < 0.5, V < 0.5): Emerald Green (20, 185, 130)
    - Bottom-Right (U >= 0.5, V < 0.5): Midnight Navy (30, 35, 70)
    - Asymmetric marker: Bright Gold upward arrow near top-left and horizontal bar toward right (+U),
      plus a white border frame so orientation/flipping is immediately visible.
    """
    buf = bytearray(width * height * 4)
    for py in range(height):
        # py=0 is top (V=1.0), py=height-1 is bottom (V=0.0)
        u_top = py < (height // 2)
        v = 1.0 - (py + 0.5) / height
        for px in range(width):
            u_left = px < (width // 2)
            u = (px + 0.5) / width

            if u_top and u_left:
                r, g, b = 245, 120, 30
            elif u_top and not u_left:
                r, g, b = 115, 50, 210
            elif not u_top and u_left:
                r, g, b = 20, 185, 130
            else:
                r, g, b = 30, 35, 70

            # Outer border
            if px < 6 or px >= width - 6 or py < 6 or py >= height - 6:
                r, g, b = 245, 240, 225

            # Upward arrow in center-left (u in [0.20, 0.40], v in [0.25, 0.85])
            # Shaft: u in [0.28, 0.32], v in [0.25, 0.70]
            if 0.28 <= u <= 0.32 and 0.25 <= v <= 0.72:
                r, g, b = 255, 230, 60
            # Arrowhead pointing UP (+V): v in [0.68, 0.86], |u - 0.30| <= (0.86 - v) * 0.75
            if 0.68 <= v <= 0.86 and abs(u - 0.30) <= (0.86 - v) * 0.75:
                r, g, b = 255, 230, 60
            # Asymmetric arm pointing RIGHT (+U) at bottom of F/L shape: v in [0.50, 0.55], u in [0.32, 0.78]
            if 0.50 <= v <= 0.56 and 0.32 <= u <= 0.78:
                r, g, b = 255, 230, 60
            # Small dot in top-right quadrant (u=0.75, v=0.75)
            if (u - 0.75) ** 2 + (v - 0.75) ** 2 <= 0.06**2:
                r, g, b = 255, 255, 255

            idx = (py * width + px) * 4
            buf[idx] = r
            buf[idx + 1] = g
            buf[idx + 2] = b
            buf[idx + 3] = 255

    return write_rgba_png(filepath, width, height, bytes(buf))


def create_pbr_material(
    name: str,
    base_color: tuple[float, float, float, float] = (0.8, 0.8, 0.8, 1.0),
    metallic: float = 0.0,
    roughness: float = 0.5,
    emission_color: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
    base_color_image_path: str | Path | None = None,
):
    """Create a Principled BSDF material compatible with resoloop blender export -> PBS_Metallic."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    out_node = nodes.new(type="ShaderNodeOutputMaterial")
    out_node.location = (300, 0)

    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Metallic"].default_value = float(metallic)
    bsdf.inputs["Roughness"].default_value = float(roughness)

    if emission_color is not None and emission_strength > 0.0:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = emission_color
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = float(emission_strength)

    links.new(bsdf.outputs["BSDF"], out_node.inputs["Surface"])

    if base_color_image_path is not None:
        img_path = Path(base_color_image_path).resolve()
        img = bpy.data.images.load(str(img_path), check_existing=True)
        img.colorspace_settings.name = "sRGB"
        img.pack()

        tex_node = nodes.new(type="ShaderNodeTexImage")
        tex_node.location = (-320, 0)
        tex_node.image = img
        tex_node.projection = "FLAT"
        tex_node.extension = "REPEAT"
        tex_node.interpolation = "Linear"
        links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])

    return mat
