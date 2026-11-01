"""S-criteria tests for the W10 live check (``modeling/p3_gimmicks/verify_live.py``).

Why these tests exist (create-reso-world AGENTS.md, test criterion S): the live check is the evidence that G13 turns at the
recorded speed in the recorded direction and that G01 follows its formula and phases within the recorded range; later P3
children reuse it. If a guard stopped working, a carousel turning the wrong way, pumpkins leaving their range or pumpkins
wired to the wrong relay (wrong phase) would be reported as passing and recorded as verified with no error. Each test keeps
one representative case of one guard; the first case of each keeps the correct state passing.
"""

from __future__ import annotations

import math

from modeling.p3_gimmicks import district, gimmicks, verify_live

PARAMS = {"G01Intensity": 1.0, "G01Frequency": 0.0, "G01PhaseSpread": 1.0}


def _values(poses: dict[str, tuple[float, float]]) -> tuple[dict, dict]:
    """個体ごとの（上下, 傾きの度）から、observe の values と Body のキーを作る。"""
    values, keys = {}, {}
    for p in gimmicks.g01()["pumpkins"]:
        k = f"key_{p['asset_id']}"
        keys[p["motion_root"]] = k
        lift, tilt = poses[p["asset_id"]]
        half = math.radians(tilt) / 2.0
        values[f"$member:{district.relay_key(k, 'Position')}.Value"] = {"member": {"value": {"x": 0.0, "y": 0.24 + lift, "z": 0.0}}}
        values[f"$member:{district.relay_key(k, 'Rotation')}.Value"] = {
            "member": {"value": {"x": 0.0, "y": 0.0, "z": math.sin(half), "w": math.cos(half)}}}
    return values, keys


def _formula() -> dict[str, tuple[float, float]]:
    out = {}
    for p in gimmicks.g01()["pumpkins"]:
        th = math.radians(p["phase_deg"])
        out[p["asset_id"]] = (0.08 + 0.10 * math.sin(th), 12.0 * math.sin(th / 2.0))
    return out


def test_frozen_check_passes_the_formula_and_rejects_swapped_phases():
    pumpkins = gimmicks.g01()["pumpkins"]
    values, keys = _values(_formula())
    assert verify_live.check_g01_frozen(values, PARAMS, pumpkins, keys)["problems"] == []
    poses = _formula()
    a, b = pumpkins[1]["asset_id"], pumpkins[2]["asset_id"]   # 位相 60° と 120°（上下は同じ、傾きが違う）
    poses[a], poses[b] = poses[b], poses[a]
    values, keys = _values(poses)
    assert len(verify_live.check_g01_frozen(values, PARAMS, pumpkins, keys)["problems"]) == 2


def test_moving_sample_rejects_a_lift_beyond_the_recorded_range():
    pumpkins = gimmicks.g01()["pumpkins"]
    params = {**PARAMS, "G01Frequency": 0.8}
    poses = {p["asset_id"]: (0.18, 0.0) for p in pumpkins}
    values, keys = _values(poses)
    assert verify_live.check_g01_sample(values, params, pumpkins, keys)["problems"] == []
    poses[pumpkins[0]["asset_id"]] = (0.19, 0.0)
    values, keys = _values(poses)
    assert len(verify_live.check_g01_sample(values, params, pumpkins, keys)["problems"]) == 1


def test_g13_check_rejects_the_opposite_direction():
    def samples(speed):
        return [{"t": float(i), "yaw_deg": verify_live.wrap_deg(speed * i), "off_axis": 0.0} for i in range(30)]

    expected = gimmicks.g13()["speed_deg_per_sec_blender_z"]
    assert verify_live.check_g13(samples(expected), expected)[1] == []
    assert verify_live.check_g13(samples(-expected), expected)[1] != []


def test_g13_check_rejects_samples_too_far_apart_to_unwrap():
    expected = gimmicks.g13()["speed_deg_per_sec_blender_z"]
    sparse = [{"t": 9.0 * i, "yaw_deg": verify_live.wrap_deg(expected * 9.0 * i), "off_axis": 0.0} for i in range(6)]
    assert any("apart" in p for p in verify_live.check_g13(sparse, expected)[1])


def test_frozen_check_compares_the_body_itself_not_only_the_relays():
    pumpkins = gimmicks.g01()["pumpkins"]
    values, keys = _values(_formula())
    bodies = {p["motion_root"]: {"position": values[f"$member:{district.relay_key(keys[p['motion_root']], 'Position')}.Value"]["member"]["value"],
                                 "rotation": values[f"$member:{district.relay_key(keys[p['motion_root']], 'Rotation')}.Value"]["member"]["value"]}
              for p in pumpkins}
    assert verify_live.check_g01_frozen(values, PARAMS, pumpkins, keys, bodies)["problems"] == []
    stuck = dict(bodies)
    stuck[pumpkins[3]["motion_root"]] = {"position": {"x": 0.0, "y": 0.24, "z": 0.0}, "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}}
    assert len(verify_live.check_g01_frozen(values, PARAMS, pumpkins, keys, stuck)["problems"]) == 1


def test_clock_check_rejects_a_time_term_that_does_not_advance():
    pumpkins = gimmicks.g01()["pumpkins"]
    params = {**PARAMS, "G01Frequency": 0.01}

    def at(seconds):
        poses = {}
        for p in pumpkins:
            th = 2 * math.pi * 0.01 * seconds + math.radians(p["phase_deg"])
            poses[p["asset_id"]] = (0.08 + 0.10 * math.sin(th), 12.0 * math.sin(th / 2.0))
        return _values(poses)

    (v1, keys), (v2, _) = at(100.0), at(110.0)
    assert verify_live.check_g01_clock(v1, 100.0, v2, 110.0, params, pumpkins, keys)["problems"] == []
    assert verify_live.check_g01_clock(v1, 100.0, v1, 110.0, params, pumpkins, keys)["problems"] != []


def test_variation_check_rejects_pumpkins_frozen_in_place():
    pumpkins = gimmicks.g01()["pumpkins"]
    params = {**PARAMS, "G01Frequency": 0.8}
    moving = [{"pumpkins": [{"asset_id": p["asset_id"], "lift_m": 0.18 if i % 2 else -0.02, "tilt_deg": 12.0 if i % 2 else -12.0}
                            for p in pumpkins]} for i in range(6)]
    assert verify_live.check_g01_variation(moving, params, pumpkins) == []
    frozen = [{"pumpkins": [{"asset_id": p["asset_id"], "lift_m": 0.08, "tilt_deg": 6.0} for p in pumpkins]} for _ in range(6)]
    assert len(verify_live.check_g01_variation(frozen, params, pumpkins)) == len(pumpkins)


def test_envelope_problems_report_a_pumpkin_beyond_the_w02_envelope():
    env = {"G01": [{"asset_id": "A", "moving_radius_m": 0.43, "w02_envelope_radius_m": 0.55, "within_w02_envelope": True}],
           "G13": {"low_parts_within_base": True, "swept_radius_below_head_m": 4.68, "base_radius_m": 5.69}}
    assert verify_live.envelope_problems(env) == []
    env["G01"][0].update({"moving_radius_m": 0.6, "within_w02_envelope": False})
    assert len(verify_live.envelope_problems(env)) == 1


def _live(name, pos=(0, 0, 0), children=None) -> dict:
    return {"name": name, "position": dict(zip("xyz", pos)), "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
            "scale": {"x": 1, "y": 1, "z": 1}, "children": children or []}


def _decl(name, pos=(0, 0, 0), children=None) -> dict:
    return {"slot": {"name": name, "position": list(pos), "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]}, "children": children or []}


def test_structure_check_rejects_an_attachment_moved_out_of_the_body():
    g01, g13 = gimmicks.g01(), gimmicks.g13()

    def world(glow_under_body: bool):
        a_live = []
        for p in g01["pumpkins"]:
            glow = _live(f"{p['asset_id']}_GlowAttach", pos=(0, 0.26, -0.22))
            body = _live(p["motion_root"], pos=(0, 0.3, 0), children=[glow] if glow_under_body else [])
            a_live.append(_live(p["asset_id"], children=[_live(f"{p['asset_id']}_Pedestal"), body] + ([] if glow_under_body else [glow])))
        turn = _live(g13["motion_root"], pos=(0, 0.36, 0), children=[_live("DAM_Carousel_001_Floor")])
        return _live("HalloweenMagicalCarnival", children=[_live("A_plaza", children=a_live),
                                                          _live("D_amusement", children=[_live("DAM_Carousel_001", children=[turn])])])

    decls = {
        "A_plaza": _decl("A_plaza", children=[
            _decl(p["asset_id"], children=[_decl(f"{p['asset_id']}_Pedestal"),
                                           _decl(p["motion_root"], pos=(0, 0.24, 0),
                                                 children=[_decl(f"{p['asset_id']}_GlowAttach", pos=(0, 0.26, -0.22))])])
            for p in g01["pumpkins"]]),
        "D_amusement": _decl("D_amusement", children=[_decl("DAM_Carousel_001", children=[
            _decl(g13["motion_root"], pos=(0, 0.36, 0), children=[_decl("DAM_Carousel_001_Floor")])])]),
    }
    assert verify_live.check_structure(world(True), decls)["problems"] == []
    assert len(verify_live.check_structure(world(False), decls)["problems"]) == len(g01["pumpkins"])
