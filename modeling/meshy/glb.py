"""Read the JSON chunk of a binary glTF (GLB) without Blender.

Used by ``intake_inspect.py`` (inside Blender) and by the tests (plain Python): the importer hides some glTF facts,
for example ``doubleSided`` and the image MIME types, so they are read from the file itself.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

GLB_MAGIC = 0x46546C67  # "glTF"
CHUNK_JSON = 0x4E4F534A  # "JSON"


def read_glb_json(path: str | Path) -> dict[str, Any]:
    """Return the parsed JSON chunk of ``path``. Raises ``ValueError`` for anything but a GLB 2.0 file."""
    with open(path, "rb") as fh:
        header = fh.read(12)
        if len(header) != 12:
            raise ValueError(f"{path}: too short for a GLB header")
        magic, version, _length = struct.unpack("<III", header)
        if magic != GLB_MAGIC or version != 2:
            raise ValueError(f"{path}: not a GLB 2.0 file")
        chunk_length, chunk_type = struct.unpack("<II", fh.read(8))
        if chunk_type != CHUNK_JSON:
            raise ValueError(f"{path}: first chunk is not JSON")
        return json.loads(fh.read(chunk_length).decode("utf-8"))


def summarize(doc: dict[str, Any]) -> dict[str, Any]:
    """The facts W09 records from the glTF JSON: meshes, triangles per the index accessors, materials and images."""
    accessors = doc.get("accessors", [])
    meshes = doc.get("meshes", [])
    triangles = 0
    primitives = 0
    for mesh in meshes:
        for prim in mesh.get("primitives", []):
            primitives += 1
            mode = prim.get("mode", 4)
            if mode != 4:
                raise ValueError(f"primitive mode {mode} is not TRIANGLES")
            if "indices" in prim:
                triangles += accessors[prim["indices"]]["count"] // 3
            else:
                triangles += accessors[prim["attributes"]["POSITION"]]["count"] // 3
    materials = []
    for mat in doc.get("materials", []):
        pbr = mat.get("pbrMetallicRoughness", {})
        materials.append({
            "name": mat.get("name"),
            "doubleSided": bool(mat.get("doubleSided", False)),
            "alphaMode": mat.get("alphaMode", "OPAQUE"),
            "baseColorTexture": "baseColorTexture" in pbr,
            "metallicRoughnessTexture": "metallicRoughnessTexture" in pbr,
            "normalTexture": "normalTexture" in mat,
            "occlusionTexture": "occlusionTexture" in mat,
            "emissiveTexture": "emissiveTexture" in mat,
            "emissiveFactor": mat.get("emissiveFactor", [0.0, 0.0, 0.0]),
        })
    images = [{"name": img.get("name"), "mimeType": img.get("mimeType")} for img in doc.get("images", [])]
    return {
        "meshes": len(meshes),
        "primitives": primitives,
        "nodes": len(doc.get("nodes", [])),
        "triangles": triangles,
        "materials": materials,
        "images": images,
        "generator": doc.get("asset", {}).get("generator"),
    }
