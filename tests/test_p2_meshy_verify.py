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


# W09R-A (#47): a finished asset whose moving part (M01's gate leaf) sits in its own declaration under the placeholder's
# motion root. If these guards broke, a leaf hinged 15 cm off the axis P3 rotates, a closed leaf, an invisible leaf or a
# leaf with a collider would be recorded as verified with no error. The first test also keeps the correct state passing.
REP_MOVING = {**REP, "visual_root": "Proxy_Arch", "visual_root_path": "Root/W/A/Proxy/Proxy_Arch",
              "hide": ["Proxy_Arch", "Proxy_DoorL"],
              "moving_parts": {"Leaf": {"motion_root": "Proxy_DoorL", "document": "DoorL"}}}
INPUTS_MOVING = {**INPUTS, "meshes": [{"path": ["ArchMesh"], "vertices": VERTICES}],
                 "placeholder_asset": {"origin_world": [0.0, 0.0, 1.6], "parts": []},
                 "moving_parts": {"Leaf": {"motion_root": "Proxy_DoorL", "bundle_root_name": "M", "pivot_local": [1.0, -0.2, 0.0],
                                           "closed_deg": 0.0, "placed_deg": 90.0,
                                           # the hinge and a point of the closed leaf (Resonite axes), inside the arch's box
                                           "meshes": [{"path": [], "vertices": [{"position": {"x": 0.0, "y": 0.0, "z": 0.0}},
                                                                                 {"position": {"x": -0.25, "y": 1.0, "z": 0.0}}]}]}}}
Q90 = (0, -0.7071067811865476, 0, 0.7071067811865476)  # Blender Z +90 deg as a Resonite rotation


def _world_moving() -> dict:
    def providers(mat, tex):
        return _slot("Blender_Providers", children=[
            _slot("mat", comps=[_comp(mat, "PBS_Metallic", AlbedoTexture=f"id:{tex}")]),
            _slot("tex", comps=[_comp(tex, "StaticTexture2D", URL="local://tex")]),
        ])

    arch = _slot("Proxy_Arch", comps=[_comp("m1", "StaticMesh", URL="local://proxy"),
                                      _comp("r1", "MeshRenderer", Enabled=False, Mesh="id:m1", Materials=[])], children=[
        _slot("M", rot=(0, -1, 0, 0), children=[
            _slot("Asset", children=[_slot("ArchMesh", comps=[_comp("m2", "StaticMesh", URL="local://arch"),
                                                              _comp("r3", "MeshRenderer", Enabled=True, Mesh="id:m2", Materials=["p1"])])]),
            providers("p1", "t1"),
        ]),
    ])
    # hinge (1.0, -0.2) of the asset turned 180 deg -> (-1.0, 0.2) in Blender -> Resonite (-1.0, 0, 0.2); opened +90 deg
    door = _slot("Proxy_DoorL", pos=(-1.0, 0, 0.2), rot=Q90, comps=[_comp("r4", "MeshRenderer", Enabled=False)], children=[
        _slot("M", rot=(0, -1, 0, 0), children=[
            _slot("Leaf", comps=[_comp("m5", "StaticMesh", URL="local://leaf"),
                                 _comp("r5", "MeshRenderer", Enabled=True, Mesh="id:m5", Materials=["p2"])]),
            providers("p2", "t2"),
        ]),
    ])
    fixed = _slot("Proxy_Arch_FixedCollision", comps=[
        _comp("m3", "StaticMesh", URL="local://proxy"),
        _comp("c1", "MeshCollider", Enabled=True, Type="Static", CharacterCollider=True, Mesh="id:m3")])
    return _slot("W", children=[_slot("A", children=[_slot("Proxy", pos=(0, 1.6, 0), children=[arch, door, fixed])])])


def _problems_moving(world: dict) -> list[str]:
    return verify_live.check_one(world, "MX", REP_MOVING, copy.deepcopy(INPUTS_MOVING))["problems"]


def test_moving_part_motion_root_off_the_hinge_is_detected() -> None:
    assert _problems_moving(_world_moving()) == []
    world = _world_moving()
    _find(world, "Proxy_DoorL")["position"]["x"] = -1.15  # the placeholder's own hinge, 15 cm from the asset's
    assert any("away from the hinge" in p for p in _problems_moving(world))


def test_moving_part_that_is_not_in_the_opened_pose_is_detected() -> None:
    world = _world_moving()
    _find(world, "Proxy_DoorL")["rotation"] = dict(zip("xyzw", (0, 0, 0, 1)))  # closed leaf
    assert any("not in the opened pose" in p for p in _problems_moving(world))


def test_moving_part_that_is_not_drawn_is_detected() -> None:
    world = _world_moving()
    next(c for c in _find(world, "Leaf")["components"] if c["id"] == "r5")["members"]["Enabled"]["value"] = False
    assert any("Leaf: MeshRenderer.Enabled" in p for p in _problems_moving(world))


def test_collider_under_a_moving_part_is_detected() -> None:
    world = _world_moving()
    _find(world, "Leaf")["components"].append(_comp("c9", "MeshCollider", Enabled=True))
    assert any("colliders under the moving parts" in p for p in _problems_moving(world))


def test_moving_part_with_a_wrong_scale_is_detected() -> None:
    # PR #52 review (GPT): the whole box is set by the arch and the other leaf, so a leaf shrunk to half passed every check.
    world = _world_moving()
    _find(world, "Leaf")["scale"] = dict(zip("xyz", (0.5, 0.5, 0.5)))
    assert any("Leaf bounds differ" in p for p in _problems_moving(world))


def test_moving_part_declaration_without_a_mesh_is_detected() -> None:
    # PR #52 review (GPT): the meshes to check come from the part declaration, so a declaration that lost its mesh left
    # nothing to check and an invisible leaf passed.
    inputs = copy.deepcopy(INPUTS_MOVING)
    inputs["moving_parts"]["Leaf"]["meshes"] = []
    assert any("has no mesh" in p for p in verify_live.check_one(_world_moving(), "MX", REP_MOVING, inputs)["problems"])


# W09R-B (#48): M03's collision is its own mesh, and the placeholder's FixedCollision stays as a Slot with its collider
# disabled (collision="finished"). If these guards broke, an invisible placeholder-shaped collider (a column in the
# central arch, a 0.28 m ledge in front of the bays) left enabled, or a mansion without any collider (walk-through
# walls), would be recorded as verified with no error. The first test also keeps the correct state passing.
REP_FINISHED = {**REP, "collision": "finished"}


def _world_finished() -> dict:
    world = _world()
    next(c for c in _find(world, "Proxy_Body_FixedCollision")["components"] if c["id"] == "c1")["members"]["Enabled"]["value"] = False
    _find(world, "Asset")["components"].append(_comp("c2", "MeshCollider", Enabled=True, Type="Static", CharacterCollider=True, Mesh="id:m2"))
    return world


def _problems_finished(world: dict) -> list[str]:
    return verify_live.check_one(world, "MX", REP_FINISHED, copy.deepcopy(INPUTS))["problems"]


def test_placeholder_collider_left_enabled_is_detected_for_a_finished_asset_collision() -> None:
    assert _problems_finished(_world_finished()) == []
    world = _world_finished()
    next(c for c in _find(world, "Proxy_Body_FixedCollision")["components"] if c["id"] == "c1")["members"]["Enabled"]["value"] = True
    assert any("expected False" in p for p in _problems_finished(world))


def test_finished_asset_without_its_collider_is_detected() -> None:
    world = _world_finished()
    asset = _find(world, "Asset")
    asset["components"] = [c for c in asset["components"] if c["id"] != "c2"]
    assert any("finished-asset collider fails" in p for p in _problems_finished(world))


# W09R-B (#48): the district's door hinges and entrance hall must sit on the finished asset's door opening. The expected
# values come from the asset's opening (review/<M>/checks.json), not from the district layout, so a door left at the P1
# position (0.37 m off the opening) or a hall that did not follow it is reported instead of being recorded as verified.
INPUTS_ENTRANCE = {**INPUTS, "entrance": {"hinges": {"HingeL": [0.5, 1.0, 0.2]}, "hall": "Hall", "hall_depth_m": 1.5,
                                          "opening_centre_floor_local": [0.0, 1.0, 0.2]}}


def _world_entrance() -> dict:
    # asset origin (0, 1.6, 0) turned 180 deg: hinge (0.5, 1.0, 0.2) -> Resonite (-0.5, 1.8, -1.0); the opening centre on the
    # floor -> (0, 1.8, -1.0) and 1.5 m behind the wall (+Z, opposite to the asset's front -Z) -> (0, 1.8, 0.5)
    world = _world()
    proxy = _find(world, "Proxy")
    proxy["children"] += [_slot("Door", pos=(0, 0.2, -1.0), children=[_slot("HingeL", pos=(-0.5, 0, 0))]),
                          _slot("Hall", pos=(0, 0.2, 0.5))]
    return world


def _problems_entrance(world: dict) -> list[str]:
    return verify_live.check_one(world, "MX", REP, copy.deepcopy(INPUTS_ENTRANCE))["problems"]


def test_entrance_door_off_the_opening_is_detected() -> None:
    assert _problems_entrance(_world_entrance()) == []
    world = _world_entrance()
    _find(world, "Door")["position"]["x"] = -0.3725  # the P1 position relative to the finished opening
    assert any("HingeL is" in p and "hinge line" in p for p in _problems_entrance(world))


def test_entrance_hall_off_the_opening_is_detected() -> None:
    world = _world_entrance()
    _find(world, "Hall")["position"]["x"] = -0.3725
    assert any("Hall is" in p for p in _problems_entrance(world))
