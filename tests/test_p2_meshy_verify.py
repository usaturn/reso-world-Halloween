"""S-criteria tests for the W09R live check (``modeling/p2_meshy/verify_live.py``).

Why these tests exist (create-reso-world AGENTS.md, test criterion S): the live check is the evidence that a placeholder
was replaced correctly, and every later replacement child reuses it. If it compared the asset with values taken from the
same observation, or skipped scale signs, render references, collider settings or a district's other replacements, a
moved, mirrored, invisible or non-colliding asset would be reported as passing and recorded as verified with no error.
The review of PR #45 (GPT) found these paths; each test below keeps one representative case of one guard, and the first
test keeps the correct state passing.
"""

from __future__ import annotations

import copy

import pytest

from modeling.p2_meshy import verify_live


def _slot(name, pos=(0, 0, 0), rot=(0, 0, 0, 1), scale=(1, 1, 1), comps=None, children=None, active=True) -> dict:
    return {"name": name, "isActive": active, "position": dict(zip("xyz", pos)), "rotation": dict(zip("xyzw", rot)),
            "scale": dict(zip("xyz", scale)), "components": comps or [], "children": children or []}


def _comp(cid, short_type, **members) -> dict:
    def m(v):
        if isinstance(v, list):
            return {"kind": "list", "elements": [{"kind": "reference", "targetId": t} for t in v]}
        if isinstance(v, str) and v.startswith("id:"):
            return {"kind": "reference", "targetId": v[3:]}
        return {"kind": "field", "value": v}

    return {"id": cid, "type": f"[FrooxEngine]FrooxEngine.{short_type}", "members": {k: m(v) for k, v in members.items()}}


REP = {"district": "A", "placeholder": "Proxy", "visual_root": "Proxy_Body", "asset_id": "Asset",
       "visual_root_path": "Root/W/A/Proxy/Proxy_Body", "hide": ["Proxy_Body", "Proxy_Eye"],
       "rotation_z_deg": 180.0, "position_local": [0.0, 0.0, 0.0]}
# Blender bounds of the finished asset: front (+Y) deeper than the back, so a wrong yaw also moves the box.
BOUNDS = {"min": [-1.0, -0.5, 0.0], "max": [1.0, 1.5, 2.0]}
VERTICES = [{"position": {"x": x, "y": z, "z": y}} for x in (-1.0, 1.0) for y in (-0.5, 1.5) for z in (0.0, 2.0)]
INPUTS = {"bundle": "exports/p2_meshy/MX-test", "bundle_root_name": "M", "vertices": VERTICES, "bounds_local": BOUNDS,
          "hint_deg": 180.0, "frame_origin_world": [0.0, 0.0, 1.6],
          "placeholder_asset": {"origin_world": [0.0, 0.0, 1.6],
                                "parts": [{"part_id": "Proxy_Eye", "role": "attachment_point", "pivot_local": [0.0, -2.0, 1.0]}]},
          "declared": {"slots": 4, "components": 5}}


def _world() -> dict:
    body = _slot("Proxy_Body", comps=[_comp("m1", "StaticMesh", URL="local://proxy"),
                                      _comp("r1", "MeshRenderer", Enabled=False, Mesh="id:m1", Materials=[])], children=[
        _slot("Proxy_Eye", pos=(0, 1.0, -2.0), comps=[_comp("r2", "MeshRenderer", Enabled=False)]),
        _slot("M", rot=(0, -1, 0, 0), children=[
            _slot("Asset", comps=[_comp("m2", "StaticMesh", URL="local://asset"),
                                  _comp("r3", "MeshRenderer", Enabled=True, Mesh="id:m2", Materials=["p1"])]),
            _slot("Blender_Providers", children=[
                _slot("mat", comps=[_comp("p1", "PBS_Metallic", AlbedoTexture="id:t1")]),
                _slot("tex", comps=[_comp("t1", "StaticTexture2D", URL="local://tex")]),
            ]),
        ]),
    ])
    fixed = _slot("Proxy_Body_FixedCollision", comps=[
        _comp("m3", "StaticMesh", URL="local://proxy"),
        _comp("c1", "MeshCollider", Enabled=True, Type="Static", CharacterCollider=True, Mesh="id:m3")])
    return _slot("W", children=[_slot("A", children=[_slot("Proxy", pos=(0, 1.6, 0), children=[body, fixed])])])


def _find(node: dict, name: str) -> dict:
    if node["name"] == name:
        return node
    for c in node["children"]:
        try:
            return _find(c, name)
        except KeyError:
            pass
    raise KeyError(name)


def _problems(world: dict) -> list[str]:
    return verify_live.check_one(world, "MX", REP, copy.deepcopy(INPUTS))["problems"]


def test_correct_replacement_passes() -> None:
    assert _problems(_world()) == []


def test_placeholder_moved_with_its_children_is_detected() -> None:
    world = _world()
    _find(world, "Proxy")["position"]["x"] = 10.0  # the whole placeholder, so live-relative checks would cancel out
    assert any("frame_origin_world" in p for p in _problems(world))


def test_mirrored_asset_is_detected() -> None:
    world = _world()
    _find(world, "Asset")["scale"]["x"] = -1.0  # left-right mirror: the box (symmetric in x) and the front do not change
    assert any("non-positive scale" in p for p in _problems(world))


def test_asset_that_is_not_drawn_is_detected() -> None:
    world = _world()
    _find(world, "M")["isActive"] = False
    assert any("inactive" in p for p in _problems(world))


def test_collider_that_does_not_collide_is_detected() -> None:
    world = _world()
    collider = next(c for c in _find(world, "Proxy_Body_FixedCollision")["components"] if c["id"] == "c1")
    collider["members"]["Enabled"]["value"] = False
    assert any("FixedCollision" in p for p in _problems(world))


def test_district_counts_include_every_replacement_of_the_district(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(verify_live, "REPLACEMENTS", {"MX": REP, "MY": {**REP, "district": "A"}})
    world = _world()
    slots, comps = verify_live.count_nodes(_find(world, "A"))
    declared = {"MX": {"slots": 2, "components": 3}, "MY": {"slots": 1, "components": 1}}
    w08 = {"A": {"live_slots": slots - 3, "live_components": comps - 4}}
    assert verify_live.check_counts(world, w08, declared)["A"]["ok"]
    _find(world, "Proxy")["children"].append(_slot("Duplicate"))  # one Slot more than W08 + both declarations
    assert not verify_live.check_counts(world, w08, declared)["A"]["ok"]


def test_replacement_without_collision_fails_while_the_placeholder_still_has_one() -> None:
    # W09R-C: M08 (flying) is configured with collision=False, which skips the collider checks. If that flag were set on a
    # placeholder that does have a FixedCollision, the collider checks would be skipped silently and a broken collider
    # would be recorded as verified, so the flag is only accepted when the placeholder really has no FixedCollision.
    rep = {**REP, "collision": False}
    world = _world()
    assert any("configured without collision" in p for p in verify_live.check_one(world, "MX", rep, copy.deepcopy(INPUTS))["problems"])
    proxy = _find(world, "Proxy")
    proxy["children"] = [c for c in proxy["children"] if c["name"] != "Proxy_Body_FixedCollision"]
    assert verify_live.check_one(world, "MX", rep, copy.deepcopy(INPUTS))["problems"] == []


def test_collider_on_the_bundle_root_is_detected_for_a_replacement_without_collision() -> None:
    # PR #51 review (GPT): the scan for colliders under the finished asset skipped the bundle root itself, so a collider
    # placed there passed the collision=False check and the replacement was recorded as verified.
    rep = {**REP, "collision": False}
    world = _world()
    proxy = _find(world, "Proxy")
    proxy["children"] = [c for c in proxy["children"] if c["name"] != "Proxy_Body_FixedCollision"]
    _find(world, "M")["components"].append(_comp("c9", "MeshCollider", Enabled=True))
    assert any("colliders under the finished asset" in p for p in verify_live.check_one(world, "MX", rep, copy.deepcopy(INPUTS))["problems"])


def test_missing_emissive_map_is_detected_for_an_emissive_replacement() -> None:
    # W09R-C: M04's windows glow only through the material's EmissiveMap. If the check accepted a material without it,
    # dark windows would be recorded as verified.
    rep = {**REP, "emissive": True}
    world = _world()
    assert any("emissive map" in p for p in verify_live.check_one(world, "MX", rep, copy.deepcopy(INPUTS))["problems"])
    material = next(c for c in _find(world, "mat")["components"] if c["id"] == "p1")
    material["members"]["EmissiveMap"] = {"kind": "reference", "targetId": "t1"}
    assert verify_live.check_one(world, "MX", rep, copy.deepcopy(INPUTS))["problems"] == []
