"""S-criteria tests for the W08 collider composition (`modeling/p2_static/colliders.py`).

Why these tests exist (create-reso-world AGENTS.md, test criterion S): the composed `p2.apply.json` validates and
applies without any error even when the classification is wrong. A collider on a moving part would silently fight
the P3 drivers (Spec §8/§11), a collider inside a Meshy placeholder would be deleted with the placeholder when the
replacement child swaps the visual (Spec §6.3), and a component key that changes between two exports of the same
bundle would make the next apply create duplicate colliders in the live world (Spec §10.1).
"""

from __future__ import annotations

import json
from pathlib import Path

from modeling.p2_static.colliders import compose


def _mesh_node(key: str, name: str, children: list[dict] | None = None, position=(0.0, 0.0, 0.0)) -> dict:
    return {
        "slot": {"key": f"object_{key}", "name": name, "position": list(position), "rotation": [0, 1, 0, 0], "scale": [1, 1, 1]},
        "components": [
            {"key": f"mesh_{key}", "type": "FrooxEngine.StaticMesh", "fields": {"URL": f"$asset:mesh_{key}"}},
            {"key": f"renderer_{key}", "type": "FrooxEngine.MeshRenderer",
             "fields": {"Mesh": f"$component:mesh_{key}", "Materials": []}},
        ],
        "children": children or [],
    }


def _empty(key: str, name: str, children: list[dict]) -> dict:
    return {"slot": {"key": f"object_{key}", "name": name, "position": [0, 0, 0]}, "children": children}


def _bundle() -> dict:
    # Names are real B_mansion names: the mansion is the M03 placeholder (review/overview/checks.json), the
    # tombstone hinge is a motion root and the gate hooks are attachment points (assets/manifest/B_mansion.json).
    return {
        "schemaVersion": "1",
        "ownership": {"key": "blender_B_mansion_test"},
        "slot": {"key": "root", "name": "B_mansion", "parent": "Root/HalloweenMagicalCarnival"},
        "components": [],
        "assets": {},
        "children": [
            _mesh_node("ground", "BMN_CourtyardGround_001"),
            _mesh_node("mansion", "BMN_MansionPlaceholder_001", position=(0.0, 1.5, 41.5)),
            _empty("tomb", "BMN_Tombstone_001", [
                _mesh_node("tomb_base", "BMN_Tombstone_001_StaticBase"),
                _empty("tomb_hinge", "BMN_Tombstone_001_TiltHinge", [_mesh_node("tomb_slab", "BMN_Tombstone_001_Slab")]),
            ]),
            _empty("gate", "BMN_FrontGate_001", [
                _mesh_node("gate_arch", "BMN_FrontGate_001_Arch"),
                _mesh_node("gate_hook", "BMN_FrontGate_001_HookWest"),
            ]),
            {"slot": {"key": "blender_providers", "name": "Blender_Providers"}, "children": []},
        ],
    }


def _walk(node: dict, path: tuple[str, ...] = ()):
    here = path + (node["slot"]["name"],)
    yield here, node
    for child in node.get("children") or []:
        yield from _walk(child, here)


def _colliders(doc: dict) -> dict[tuple[str, ...], list[dict]]:
    out = {}
    for path, node in _walk(doc):
        found = [c for c in node.get("components") or [] if c["type"] == "FrooxEngine.MeshCollider"]
        if found:
            out[path] = found
    return out


def test_colliders_skip_moving_parts_and_attachments_and_stay_outside_the_placeholder(tmp_path: Path) -> None:
    src = tmp_path / "model.apply.json"
    src.write_text(json.dumps(_bundle()), encoding="utf-8")
    original = src.read_bytes()
    compose(src, tmp_path / "p2.apply.json", "B_mansion")
    doc = json.loads((tmp_path / "p2.apply.json").read_text(encoding="utf-8"))
    colliders = _colliders(doc)
    paths = {"/".join(p) for p in colliders}

    # Static meshes get a collider on their own Slot that uses their own mesh.
    ground = colliders[("B_mansion", "BMN_CourtyardGround_001")][0]["fields"]
    assert ground["Mesh"] == "$component:mesh_ground"
    assert ground["Type"] == "Static" and ground["CharacterCollider"] is True
    assert "B_mansion/BMN_Tombstone_001/BMN_Tombstone_001_StaticBase" in paths
    assert "B_mansion/BMN_FrontGate_001/BMN_FrontGate_001_Arch" in paths

    # Moving parts (the motion root and everything below it) and attachment points get none.
    assert not any("BMN_Tombstone_001_TiltHinge" in p for p in paths)
    assert "B_mansion/BMN_FrontGate_001/BMN_FrontGate_001_HookWest" not in paths

    # The placeholder itself carries no collider; a sibling outside it does, with the same pose and mesh asset.
    assert not any(p.startswith("B_mansion/BMN_MansionPlaceholder_001/") or p == "B_mansion/BMN_MansionPlaceholder_001"
                   for p in paths)
    fixed = [n for p, n in _walk(doc) if p == ("B_mansion", "BMN_MansionPlaceholder_001_FixedCollision")]
    assert len(fixed) == 1
    assert fixed[0]["slot"]["position"] == [0.0, 1.5, 41.5] and fixed[0]["slot"]["rotation"] == [0, 1, 0, 0]
    mesh = next(c for c in fixed[0]["components"] if c["type"] == "FrooxEngine.StaticMesh")
    assert mesh["fields"]["URL"] == "$asset:mesh_mansion"
    assert fixed[0]["components"][1]["fields"]["Mesh"] == f"$component:{mesh['key']}"

    # The exported bundle is left untouched.
    assert src.read_bytes() == original


def test_composing_the_same_bundle_twice_gives_the_same_keys(tmp_path: Path) -> None:
    src = tmp_path / "model.apply.json"
    src.write_text(json.dumps(_bundle()), encoding="utf-8")
    compose(src, tmp_path / "a.json", "B_mansion")
    compose(src, tmp_path / "b.json", "B_mansion")
    assert (tmp_path / "a.json").read_bytes() == (tmp_path / "b.json").read_bytes()
    doc = json.loads((tmp_path / "a.json").read_text(encoding="utf-8"))
    keys = [c["key"] for _, n in _walk(doc) for c in n.get("components") or []] + [n["slot"]["key"] for _, n in _walk(doc)]
    assert len(keys) == len(set(keys))
