"""S-criteria tests for the W10-B live check of G05 and G06 (``modeling/p3_gimmicks/verify_b.py``).

Why these tests exist (create-reso-world AGENTS.md, test criterion S): the live check is the evidence that the ghosts float
within their range with the recorded phases, that the double door opens inward, symmetrically and at the recorded speed,
that the parts under the ghosts and the doors stay where they are declared, and that the swept volumes stay out of the
porch and the main corridor. If a guard stopped working, an outward or one-sided door, ghosts swapped or out of range, a
frozen cycle, a cycle at the wrong speed, a leaf or a hinge moved off the M03 opening, or a door that swings onto the
porch would be reported as passing and recorded as verified with no error. Each test keeps one representative case of one
guard; the first case of each keeps the correct state passing.
"""

from __future__ import annotations

import copy
import json
import math

from modeling.p3_gimmicks import gimmicks, verify_b

PARAMS = {"G05Intensity": 1.0, "G05Frequency": 0.25, "G05PhaseSpread": 1.0,
          "G06Intensity": 1.0, "G06Frequency": 1.0 / 24.0, "G06Phase": 0.0}
GHOSTS = gimmicks.g05()["ghosts"]
HINGES = gimmicks.g06()["hinges"]
KEYS = {g["motion_root"]: f"k{i}" for i, g in enumerate(GHOSTS)} | {h["motion_root"]: f"h{i}" for i, h in enumerate(HINGES)}
REST = {g["motion_root"]: [0.0, 0.0, 0.0] for g in GHOSTS} | {h["motion_root"]: [-0.809 if i == 0 else 0.809, 0.0, 0.0]
                                                                for i, h in enumerate(HINGES)}


def _yq(deg: float) -> dict:
    h = math.radians(deg) / 2.0
    return {"x": 0.0, "y": math.sin(h), "z": 0.0, "w": math.cos(h)}


def _values(ghost_theta: dict[str, float], door_open: float, params=PARAMS, door_sign=1.0) -> dict:
    """中継の observe の values を、式（Blender の上下・揺れ・開き）から作る。door_sign = -1 は外へ開くグラフ。"""
    out = {}
    for g in GHOSTS:
        lift, sway = verify_b.expected_ghost(params, g, ghost_theta[g["asset_id"]])
        k = KEYS[g["motion_root"]]
        out[verify_b.relay_sel(k, "Position", "g05")] = {"member": {"value": {"x": 0.0, "y": lift, "z": 0.0}}}
        out[verify_b.relay_sel(k, "Rotation", "g05")] = {"member": {"value": _yq(-sway)}}
    for h in HINGES:
        out[verify_b.relay_sel(KEYS[h["motion_root"]], "Rotation", "g06")] = {
            "member": {"value": _yq(-h["open_sign_blender_z"] * door_sign * door_open)}}
    return out


def _frozen_theta(params=PARAMS) -> dict[str, float]:
    return {g["asset_id"]: math.radians(params["G05PhaseSpread"] * g["phase_deg"]) for g in GHOSTS}


def test_frozen_sample_passes_the_formula_and_rejects_swapped_ghosts_or_an_outward_door():
    params = dict(PARAMS, G05Frequency=0.0, G06Frequency=0.0, G06Phase=0.5)
    want_open = verify_b.expected_door(params, HINGES[0]["open_deg"])
    assert abs(want_open - 85.0) < 1e-9
    good = verify_b.read_sample(_values(_frozen_theta(params), want_open, params), KEYS, REST)
    assert verify_b.check_frozen(good, params)["problems"] == []
    th = _frozen_theta(params)
    swapped = {GHOSTS[0]["asset_id"]: th[GHOSTS[1]["asset_id"]], GHOSTS[1]["asset_id"]: th[GHOSTS[0]["asset_id"]]}
    bad = verify_b.read_sample(_values(swapped, want_open, params), KEYS, REST)
    assert len(verify_b.check_frozen(bad, params)["problems"]) == 2
    outward = verify_b.read_sample(_values(_frozen_theta(params), want_open, params, door_sign=-1.0), KEYS, REST)
    assert len(verify_b.check_frozen(outward, params)["problems"]) == 2


def test_frozen_slots_reject_a_door_that_the_relay_does_not_turn():
    params = dict(PARAMS, G05Frequency=0.0, G06Frequency=0.0, G06Phase=0.25)
    want_open = verify_b.expected_door(params, HINGES[0]["open_deg"])
    sample = verify_b.read_sample(_values(_frozen_theta(params), want_open, params), KEYS, REST)

    def live(open_left: float) -> dict:
        kids = []
        for g in GHOSTS:
            s = sample["ghosts"][g["asset_id"]]
            kids.append({"name": g["asset_id"], "children": [{"name": g["motion_root"], "position": {"x": 0.0, "y": s["lift_m"], "z": 0.0},
                                                              "rotation": _yq(-s["sway_deg"]), "children": []}]})
        door = []
        for i, h in enumerate(HINGES):
            ang = open_left if i == 0 else want_open
            door.append({"name": h["motion_root"], "position": dict(zip("xyz", REST[h["motion_root"]])),
                         "rotation": _yq(-h["open_sign_blender_z"] * ang), "children": []})
        kids.append({"name": HINGES[0]["asset_id"], "children": door})
        return {"name": "B_mansion", "children": kids}

    assert verify_b.check_frozen(verify_b.read_slots(live(want_open), REST), params, "slot")["problems"] == []
    problems = verify_b.check_frozen(verify_b.read_slots(live(0.0), REST), params, "slot")["problems"]
    assert len(problems) == 1 and HINGES[0]["motion_root"] in problems[0]


def test_live_sample_rejects_a_ghost_out_of_range_or_a_door_beyond_85_degrees():
    th = {g["asset_id"]: math.radians(90.0) for g in GHOSTS}   # 上下の最大
    good = verify_b.read_sample(_values(th, 85.0), KEYS, REST)
    assert verify_b.check_sample(good, PARAMS) == []
    high = _values(th, 85.0)
    high[verify_b.relay_sel(KEYS[GHOSTS[0]["motion_root"]], "Position", "g05")]["member"]["value"]["y"] = 0.40
    assert len(verify_b.check_sample(verify_b.read_sample(high, KEYS, REST), PARAMS)) == 1
    wide = verify_b.read_sample(_values(th, 95.0), KEYS, REST)
    assert len(verify_b.check_sample(wide, PARAMS)) == 2


def _door_formula(t: float, f: float) -> float:
    c = 0.5 - 0.5 * math.cos(2.0 * math.pi * f * t)
    x = min(max((c - gimmicks.G06_HOLD) / (1.0 - 2.0 * gimmicks.G06_HOLD), 0.0), 1.0)
    return 85.0 * x * x * (3.0 - 2.0 * x)


def _window(f_door: float, ghosts_move: bool = True, n: int = 24, step: float = 2.1) -> list[dict]:
    out = []
    for i in range(n):
        t = 1000.0 + i * step
        th = {g["asset_id"]: (2.0 * math.pi * 0.25 * t if ghosts_move else 0.0) + math.radians(g["phase_deg"]) for g in GHOSTS}
        s = verify_b.read_sample(_values(th, _door_formula(t, f_door)), KEYS, REST)
        s["t"] = t
        out.append(s)
    return out


def test_window_rejects_frozen_ghosts_or_doors_that_never_open():
    assert verify_b.check_variation(_window(1.0 / 24.0), PARAMS) == []
    assert len(verify_b.check_variation(_window(1.0 / 24.0, ghosts_move=False), PARAMS)) == 2
    shut = _window(1.0 / 24.0)
    for s in shut:
        for d in s["doors"].values():
            d["open_deg"] = 0.0
    assert len(verify_b.check_variation(shut, PARAMS)) == 2


def test_door_clock_rejects_a_cycle_at_the_wrong_speed():
    res = verify_b.check_door_clock(_window(1.0 / 24.0), PARAMS)
    assert res["problems"] == [] and len(res["crossings"]) >= 3
    fast = verify_b.check_door_clock(_window(1.0 / 12.0), PARAMS)   # 2 倍の速さで回るグラフ
    assert fast["problems"] and all("apart" in p for p in fast["problems"])


def _tree(hinge_dx: float = 0.0, leaf_under_hinge: bool = True) -> tuple[dict, dict]:
    def live(name, pos=(0, 0, 0), rot=(0, 0, 0, 1), children=None):
        return {"name": name, "position": dict(zip("xyz", pos)), "rotation": dict(zip("xyzw", rot)),
                "scale": {"x": 1, "y": 1, "z": 1}, "children": children or []}

    def decl(name, pos=(0, 0, 0), children=None):
        return {"slot": {"name": name, "position": list(pos), "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]}, "children": children or []}

    d_kids, l_kids = [], []
    for g in GHOSTS:
        body = f"{g['asset_id']}_GhostBody"
        d_kids.append(decl(g["asset_id"], (1, 2, 3), [decl(g["motion_root"], children=[decl(body)])]))
        l_kids.append(live(g["asset_id"], (1, 2, 3), children=[live(g["motion_root"], (0, 0.2, 0), (0, 0.1, 0, 0.995),
                                                                    [live(body)])]))
    door = HINGES[0]["asset_id"]
    d_door, l_door = [], []
    for i, h in enumerate(HINGES):
        leaf = h["motion_root"].replace("Hinge", "Leaf")
        x = REST[h["motion_root"]][0]
        d_door.append(decl(h["motion_root"], (x, 0, 0), [decl(leaf)]))
        moved = hinge_dx if i == 0 else 0.0
        kids = [live(leaf)] if (leaf_under_hinge or i) else []
        l_door.append(live(h["motion_root"], (x + moved, 0, 0), (0, -0.67, 0, 0.74), kids))
    if not leaf_under_hinge:
        l_door.append(live(HINGES[0]["motion_root"].replace("Hinge", "Leaf")))
    d_kids.append(decl(door, (0.7, 1.87, 39.95), d_door))
    l_kids.append(live(door, (0.7, 1.87, 39.95), children=l_door))
    return live("B_mansion", children=l_kids), decl("B_mansion", children=d_kids)


def test_structure_rejects_a_moved_hinge_or_a_leaf_taken_off_its_hinge():
    root, doc = _tree()
    assert verify_b.check_structure(root, doc)["problems"] == []
    root, doc = _tree(hinge_dx=0.37)
    assert len(verify_b.check_structure(root, doc)["problems"]) == 1
    root, doc = _tree(leaf_under_hinge=False)
    assert len(verify_b.check_structure(root, doc)["problems"]) == 1


def test_envelope_rejects_a_door_that_swings_onto_the_porch(tmp_path, monkeypatch):
    """扉の葉（蝶番のローカルで +x に 0.8 m、厚み ±0.05 m）を動かした範囲。開く向きを逆にしたデータは外へ振れる。"""
    leaf = [{"position": {"x": x, "y": y, "z": z}} for x in (0.0, 0.8) for y in (0.0, 2.5) for z in (-0.05, 0.05)]
    ghost = [{"position": {"x": x, "y": y, "z": 0.0}} for x in (-0.4, 0.4) for y in (-0.4, 1.0)]
    (tmp_path / "leaf.json").write_text(json.dumps({"vertices": leaf}), encoding="utf-8")
    (tmp_path / "ghost.json").write_text(json.dumps({"vertices": ghost}), encoding="utf-8")

    def mesh(asset):
        return [{"type": "FrooxEngine.StaticMesh", "fields": {"URL": f"$asset:{asset}"}}]

    def node(name, pos=(0, 0, 0), comps=None, children=None):
        return {"slot": {"name": name, "position": list(pos), "rotation": [0, 0, 0, 1]}, "components": comps or [],
                "children": children or []}

    kids = [node(g["asset_id"], (-4.6 if i == 0 else 4.6, 2.6, 28.0 + 5 * i),
                 children=[node(g["motion_root"], children=[node("body", comps=mesh("ghost"))])]) for i, g in enumerate(GHOSTS)]
    hinges = [node(h["motion_root"], (-0.809, 0, 0) if i == 0 else (0.809, 0, 0),
                   children=[node("leaf", (0, 0, 0) if i == 0 else (-0.8, 0, 0), comps=mesh("leaf"))]) for i, h in enumerate(HINGES)]
    kids.append(node(HINGES[0]["asset_id"], (0.7075, 1.87, 39.95), children=hinges))
    doc = {"slot": {"name": "B_mansion"}, "children": kids,
           "assets": {"leaf": {"source": "leaf.json"}, "ghost": {"source": "ghost.json"}}}
    layout = {"Exclusions": [
        {"zone_id": "Excl_B_CentralSightlineCorridor", "bounds": {"min": [-2.0, 20.0, 1.5], "max": [2.0, 37.424, 6.0]}},
        {"zone_id": "Excl_B_DoorSwingAndPorch", "bounds": {"min": [-0.9775, 37.4, 1.87], "max": [2.2225, 41.2, 4.6]}}],
        "placements": [{"asset_id": g["asset_id"], "clearance_radius_m": 1.0} for g in GHOSTS]}
    assert verify_b.envelope_problems(verify_b.envelopes(doc, tmp_path, layout)) == []
    flipped = copy.deepcopy(gimmicks.g06())
    for h in flipped["hinges"]:
        h["open_sign_blender_z"] = -h["open_sign_blender_z"]
    monkeypatch.setattr(verify_b.gimmicks, "g06", lambda: flipped)
    problems = verify_b.envelope_problems(verify_b.envelopes(doc, tmp_path, layout))
    assert len(problems) == 2 and all("toward the porch" in p for p in problems)



def _clock_sample(t: float, f: float, lift_speed: float = 1.0, params=PARAMS) -> dict:
    """ゆっくりの時刻の観察。lift_speed = 2 は上下だけが 2 倍の速さで動くグラフ（揺れは正しい）。"""
    out = {"ghosts": {}, "doors": {}}
    for g in GHOSTS:
        th = 2.0 * math.pi * f * t + math.radians(g["phase_deg"])
        lift, _ = verify_b.expected_ghost(params, g, lift_speed * th - (lift_speed - 1.0) * math.radians(g["phase_deg"]))
        _, sway = verify_b.expected_ghost(params, g, th)
        out["ghosts"][g["asset_id"]] = {"lift_m": lift, "sway_deg": sway, "horizontal_m": 0.0, "off_axis": 0.0}
    return out


def test_clock_rejects_a_lift_that_runs_at_another_speed_than_the_sway():
    params = dict(PARAMS, G05Frequency=0.004)
    good = verify_b.check_clock(_clock_sample(17.0, 0.004), 17.0, _clock_sample(37.0, 0.004), 37.0, params)
    assert good["problems"] == [] and len(good["advance"]) == 2
    bad = verify_b.check_clock(_clock_sample(17.0, 0.004, 2.0), 17.0, _clock_sample(37.0, 0.004, 2.0), 37.0, params)
    assert bad["problems"] and all("does not match the sway phase" in p for p in bad["problems"])


def test_drift_rejects_a_ghost_that_moved_at_the_same_phase_between_windows():
    def probe(dlift: float) -> dict:
        return {"params": PARAMS, "slots": {"ghosts": {g["asset_id"]: {"lift_m": 0.125 + (dlift if i == 0 else 0.0), "sway_deg": 0.0}
                                                       for i, g in enumerate(GHOSTS)},
                                            "doors": {h["motion_root"]: {"open_deg": 0.0} for h in HINGES}}}
    assert verify_b.check_drift([probe(0.0), probe(0.004)])["problems"] == []
    problems = verify_b.check_drift([probe(0.0), probe(0.02)])["problems"]
    assert len(problems) == 1 and GHOSTS[0]["asset_id"] in problems[0]
