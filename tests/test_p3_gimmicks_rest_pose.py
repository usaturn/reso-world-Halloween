"""S-criteria tests for ``modeling/p3_gimmicks/rest_pose.py`` (W10).

Why these tests exist (create-reso-world AGENTS.md, test criterion S): the P2 live checks (``modeling/p2_static/verify_live.py``
and ``modeling/p2_meshy/verify_live.py``) now replace the observed local pose of the Slots that P3 drives with their declared
rest pose before measuring. If that replacement reached any other Slot, a part that really moved (a pedestal, a seat, a
Meshy asset root) would be measured at its declared place and the check would report it as passing with no error. If it
did not reach a driven Slot, the check would fail on every run while the ride moves. The first test keeps the driven Slots
replaced; the second keeps a moved non-driven Slot visible to the P2 checks.
"""

from __future__ import annotations

from modeling.p3_gimmicks import gimmicks, rest_pose


def _live(name, pos=(0, 0, 0), rot=(0, 0, 0, 1), children=None) -> dict:
    return {"name": name, "position": dict(zip("xyz", pos)), "rotation": dict(zip("xyzw", rot)),
            "scale": {"x": 1, "y": 1, "z": 1}, "children": children or []}


def _decl(name, pos=(0, 0, 0), rot=(0, 0, 0, 1), children=None) -> dict:
    return {"slot": {"key": name, "name": name, "position": list(pos), "rotation": list(rot)}, "children": children or []}


def _world(moved_pedestal: bool = False) -> tuple[dict, dict]:
    """A のカボチャ 6 体と D の TurnRoot を、駆動された姿勢（動いている途中）で観察した木と、宣言。"""
    g01, g13 = gimmicks.g01(), gimmicks.g13()
    a_live, a_decl = [], []
    for p in g01["pumpkins"]:
        ped_pos = (0.3, 0.0, 0.0) if moved_pedestal else (0.0, 0.0, 0.0)
        a_live.append(_live(p["asset_id"], children=[
            _live(f"{p['asset_id']}_Pedestal", pos=ped_pos),
            _live(p["motion_root"], pos=(0.0, 0.40, 0.0), rot=(0.0, 0.0, 0.1, 0.995),
                  children=[_live(f"{p['asset_id']}_GlowAttach", pos=(0.0, 0.26, -0.22))])]))
        a_decl.append(_decl(p["asset_id"], children=[
            _decl(f"{p['asset_id']}_Pedestal"),
            _decl(p["motion_root"], pos=(0.0, 0.24, 0.0), children=[_decl(f"{p['asset_id']}_GlowAttach", pos=(0.0, 0.26, -0.22))])]))
    d_live = [_live("DAM_Carousel_001", children=[
        _live("DAM_Carousel_001_Base"),
        _live(g13["motion_root"], pos=(0.0, 0.36, 0.0), rot=(0.0, 0.7071, 0.0, 0.7071),
              children=[_live("DAM_Carousel_001_SeatRoot_001", pos=(3.35, 1.05, 0.0))])])]
    d_decl = [_decl("DAM_Carousel_001", children=[
        _decl("DAM_Carousel_001_Base"),
        _decl(g13["motion_root"], pos=(0.0, 0.36, 0.0), children=[_decl("DAM_Carousel_001_SeatRoot_001", pos=(3.35, 1.05, 0.0))])])]
    root = _live("HalloweenMagicalCarnival", children=[_live("A_plaza", children=a_live), _live("D_amusement", children=d_live)])
    decls = {"A_plaza": _decl("A_plaza", children=a_decl), "D_amusement": _decl("D_amusement", children=d_decl)}
    return root, decls


def _find(node: dict, name: str) -> dict:
    if node["name"] == name:
        return node
    for ch in node["children"]:
        try:
            return _find(ch, name)
        except KeyError:
            pass
    raise KeyError(name)


def test_driven_slots_are_put_back_to_their_declared_rest_pose():
    root, decls = _world()
    rows = rest_pose.apply_rest_pose(root, decls)
    driven = {name for names in gimmicks.driven_slots().values() for name in names}
    assert {r["slot"].rsplit("/", 1)[-1] for r in rows} == driven
    for p in gimmicks.g01()["pumpkins"]:
        body = _find(root, p["motion_root"])
        assert body["position"] == {"x": 0.0, "y": 0.24, "z": 0.0}
        assert body["rotation"] == {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
    turn = _find(root, gimmicks.g13()["motion_root"])
    assert turn["rotation"] == {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}


def test_a_moved_slot_that_p3_does_not_drive_keeps_its_observed_pose():
    root, decls = _world(moved_pedestal=True)
    rest_pose.apply_rest_pose(root, decls)
    pedestal = _find(root, f"{gimmicks.g01()['pumpkins'][0]['asset_id']}_Pedestal")
    assert pedestal["position"]["x"] == 0.3
    seat = _find(root, "DAM_Carousel_001_SeatRoot_001")
    assert seat["position"] == {"x": 3.35, "y": 1.05, "z": 0.0}
