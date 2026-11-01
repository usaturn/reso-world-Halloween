"""S-criteria tests for ``modeling/p3_gimmicks/verify_c.py`` (W10-C, G09 stirring cauldron and G11 witch patrol).

Why these tests exist (create-reso-world AGENTS.md, test criterion S): ``verify_c.py`` is the evidence that the stirring rod,
the witch, the liquid colour and the particles in the world follow the formulas and the W04 data. If one of its guards
broke, it would report a reversed stir, a witch off the patrol path or facing backwards, a stopped or double-speed motion,
a drift between the two windows, a moved M08, a liquid colour that no longer follows HMC_P3, a carrier pivot that stops or
leaves the witch, an angle that keeps the mean speed but leaves the clock, or a shared material that changed as passing,
with no error (the last three were added after the GPT review, M-1 to M-3).
Each test keeps one guard and also passes the correct state, so an implementation that rejects everything fails.
"""

from __future__ import annotations

import math

from modeling.p3_gimmicks import gimmicks
from modeling.p3_gimmicks import verify_c as v

G11 = gimmicks.g11()
W = gimmicks.g09()["wobble_deg"]
COLOR = {"r": 0.46135613, "g": 0.98220706, "b": 0.74837905, "a": 1.0, "profile": "sRGB"}
GAIN = 1.964626


def _q(t) -> dict:
    return dict(zip("xyzw", (float(c) for c in t)))


def _p(t) -> dict:
    return dict(zip("xyz", (float(c) for c in t)))


def _yaw(psi: float) -> tuple:
    return (0.0, math.sin(psi / 2.0), 0.0, math.cos(psi / 2.0))


def _params(**kw) -> dict:
    p = {n: s["default"] for n, s in v.variables().items()}
    p[gimmicks.G09_COLOR_VARIABLE] = dict(COLOR)
    p.update(kw)
    return p


def _rider(theta: float, shift_m: float = 0.0, heading_off_deg: float = 0.0) -> tuple[dict, dict, dict, dict]:
    """θ の魔女と CarrierPivot の (位置, 回転)（Resonite のローカル）。shift_m は水平に外へずらす量。"""
    pos, psi = gimmicks.g11_pose(theta, G11)
    pos = [pos[0] + shift_m, pos[1], pos[2]]
    rot = _q(_yaw(psi + math.radians(heading_off_deg)))
    witch = _p((pos[0], pos[2], pos[1]))
    o = G11["loop_origin"]
    carrier = _p((pos[0] - o[0], pos[2] - o[2], pos[1] - o[1]))
    return witch, rot, carrier, rot


def _values(theta: float, phi: float, params: dict, **kw) -> dict:
    witch, wrot, carrier, crot = _rider(theta, kw.get("shift_m", 0.0), kw.get("heading_off_deg", 0.0))
    vals = {"rod": _q(kw.get("rod") or v.rod_expected_q(phi, W)), "witch_pos": witch, "witch_rot": wrot,
            "carrier_pos": carrier, "carrier_rot": crot}
    eff = v.expected_effects(params, GAIN)
    for name, x in eff.items():
        vals[name] = x if isinstance(x, float) else dict(zip("rgba", x), profile="sRGB")
    vals.update(kw.get("override", {}))
    return vals


def test_frozen_sample_finds_a_reversed_stir_a_shifted_witch_and_a_wrong_path_formula():
    params = _params(G09StirFrequency=0.0, G11Frequency=0.0, G09StirPhase=0.125, G11Phase=0.25)
    phi, th = 2 * math.pi * 0.125, 2 * math.pi * 0.25
    ok = _values(th, phi, params)
    good = v.check_frozen(ok["rod"], (ok["witch_pos"], ok["witch_rot"]), (ok["carrier_pos"], ok["carrier_rot"]), params, g=G11)
    assert good["problems"] == []
    # 逆向きの攪拌（Y(+φ)）
    x, y, z, w = v.rod_expected_q(phi, W)
    bad = v.check_frozen(_q((x, -y, z, w)), (ok["witch_pos"], ok["witch_rot"]), (ok["carrier_pos"], ok["carrier_rot"]), params, g=G11)
    assert any("rod rotation" in p for p in bad["problems"])
    # 巡回の点 3 にいる（位相のずれ）
    sh = _values(2 * math.pi * 0.375, phi, params)
    bad = v.check_frozen(ok["rod"], (sh["witch_pos"], sh["witch_rot"]), (ok["carrier_pos"], ok["carrier_rot"]), params, g=G11)
    assert any(p.startswith("relay: witch at") for p in bad["problems"])
    # 経路の式の係数の誤り（y の符号が逆）: 式どおりに置かれていても、配置データの巡回の点 2 から外れる
    wrong = dict(G11, coefficients=[G11["coefficients"][0], ([-a for a in G11["coefficients"][1][0]], [-b for b in G11["coefficients"][1][1]]),
                                    G11["coefficients"][2]])
    pos, psi = gimmicks.g11_pose(th, wrong)
    wp = _p((pos[0], pos[2], pos[1]))
    bad = v.check_frozen(ok["rod"], (wp, _q(_yaw(psi))), (ok["carrier_pos"], ok["carrier_rot"]), params, g=wrong)
    assert any("from waypoint 2" in p for p in bad["problems"])


def test_live_sample_finds_a_witch_off_the_path_a_wrong_heading_a_wrong_wobble_and_a_colour_that_does_not_follow():
    params = _params()
    th, phi = 1.1, 2.3
    assert v.check_sample(_values(th, phi, params), params, GAIN, G11)["problems"] == []
    assert any("off the patrol path" in p for p in v.check_sample(_values(th, phi, params, shift_m=0.3), params, GAIN, G11)["problems"])
    assert any("path tangent" in p for p in
               v.check_sample(_values(th, phi, params, heading_off_deg=20.0), params, GAIN, G11)["problems"])
    # 揺れが 1 周に 1 回（sin φ）の式
    half = math.radians(W) / 2.0 * math.sin(phi)
    sy, cy = -math.sin(phi / 2.0), math.cos(phi / 2.0)
    rod = (sy * math.sin(half), sy * math.cos(half), cy * math.sin(half), cy * math.cos(half))
    assert any("tilt" in p for p in v.check_sample(_values(th, phi, params, rod=rod), params, GAIN, G11)["problems"])
    # HMC_P3 を Magenta にしたのに、煙の色がエメラルドのまま
    magenta = _params(**{gimmicks.G09_COLOR_VARIABLE: dict(zip("rgba", v.MAGENTA), profile="sRGB")})
    stale = _values(th, phi, magenta, override={"smoke_start": _values(th, phi, params)["smoke_start"]})
    assert any(p.startswith("smoke_start") for p in v.check_sample(stale, magenta, GAIN, G11)["problems"])


def test_travel_check_finds_a_witch_that_flies_backwards():
    def sample(theta, flip=False):
        pos, psi = gimmicks.g11_pose(theta, G11)
        q = _yaw(psi + (math.pi if flip else 0.0))
        return {"witch": {"pos_b": pos, "forward": list(v.qrot(q, (0.0, 0.0, 1.0)))}}

    assert v.check_travel([sample(0.4), sample(0.6), sample(0.8)])["problems"] == []
    assert v.check_travel([sample(0.4, True), sample(0.6, True)])["problems"]


def test_speed_check_finds_a_stopped_rod_a_double_speed_patrol_a_stopped_carrier_and_an_angle_off_the_clock():
    params = _params()
    rod = [(t * 1.5, (60.0 * t * 1.5) % 360.0) for t in range(10)]
    patrol = [(t * 3.0, (8.0 * t * 3.0) % 360.0) for t in range(11)]
    assert v.check_speeds(rod, patrol, params, patrol)["problems"] == []
    assert v.check_speeds([(t * 1.5, 40.0) for t in range(10)], patrol, params, patrol)["problems"]
    assert v.check_speeds(rod, [(t * 3.0, (16.0 * t * 3.0) % 360.0) for t in range(11)], params, patrol)["problems"]
    # CarrierPivot だけが止まっている（魔女は動く。GPT のレビューの指摘 M-1）
    assert any(p.startswith("carrier") for p in v.check_speeds(rod, patrol, params, [(t * 3.0, 0.0) for t in range(11)])["problems"])
    # 平均の速さは 8°/s だが、時刻から ±20° 外れる式（指摘 M-3 の例）
    wobbly = [(t * 3.0, (8.0 * t * 3.0 + 20.0 * math.cos(2 * math.pi * t * 3.0 / 30.0)) % 360.0) for t in range(11)]
    assert any("off the line of the clock" in p for p in v.check_speeds(rod, wobbly, params, patrol)["problems"])


def test_carrier_phase_check_finds_a_carrier_that_does_not_follow_the_witch():
    same = [{"witch": {"theta_deg": 10.0 * k}, "carrier": {"theta_deg": 10.0 * k - 2.0}} for k in range(5)]
    late = [{"witch": {"theta_deg": 10.0 * k}, "carrier": {"theta_deg": 10.0 * k - 30.0}} for k in range(5)]
    assert v.check_carrier_phase(same)["problems"] == []
    assert v.check_carrier_phase(late)["problems"]


def test_material_check_finds_a_changed_shared_colour_and_a_renderer_moved_to_the_dedicated_material():
    def comp(key, typ, fields):
        return {"key": key, "type": typ, "fields": fields}

    def tree(liquid_mats, stall_mats):
        g9 = gimmicks.g09()
        return {"slot": {"name": "C_candy"}, "components": [
            comp("emerald", "FrooxEngine.PBS_Metallic", {"AlbedoColor": [0.46, 0.98, 0.75, 1.0], "EmissiveColor": [0.9, 1.9, 1.5, 1.0]}),
            comp("magenta", "FrooxEngine.PBS_Metallic", {"AlbedoColor": [0.98, 0.53, 0.9, 1.0], "EmissiveColor": [1.9, 1.0, 1.7, 1.0]})],
            "children": [{"slot": {"name": g9["liquid"]}, "components": [comp("liquid_r", "FrooxEngine.MeshRenderer", {"Materials": liquid_mats})]},
                         {"slot": {"name": "Stall"}, "components": [comp("stall_r", "FrooxEngine.MeshRenderer", {"Materials": stall_mats})]}]}

    model = tree(["$component:emerald", "$component:magenta"], ["$component:emerald"])
    doc = tree([f"$component:{gimmicks.G09_LIQUID_MATERIAL_KEY}", "$component:magenta"], ["$component:emerald"])
    exp = v.material_expectations(model, doc)
    ids = {"emerald": "E", "magenta": "M", gimmicks.G09_LIQUID_MATERIAL_KEY: "L"}
    observed = {"liquid_r": ["L", "M"], "stall_r": ["E"]}
    colors = {(k, m): dict(zip("rgba", vals), profile="sRGB") for (k, m), vals in exp["colors"].items()}
    assert v.compare_materials(exp, observed, ids, colors) == []
    # 宣言の作り方の誤りで屋台の MeshRenderer まで専用の材質に付け替わった（変更後の宣言から対象を取ると、屋台が対象から抜けて見落とす）
    bad_doc = tree([f"$component:{gimmicks.G09_LIQUID_MATERIAL_KEY}", "$component:magenta"], [f"$component:{gimmicks.G09_LIQUID_MATERIAL_KEY}"])
    bad = v.material_expectations(model, bad_doc)
    assert any(p.startswith("stall_r") for p in v.compare_materials(bad, {**observed, "stall_r": ["L"]}, ids, colors))
    # 共有のエメラルドの色が変わった（参照は同じ）
    changed = {**colors, ("emerald", "EmissiveColor"): dict(r=1.9, g=0.47, b=1.5, a=1.0, profile="sRGB")}
    assert any("shared material colour" in p for p in v.compare_materials(exp, observed, ids, changed))


def test_drift_check_finds_a_moved_phase_and_a_clock_offset_between_windows():
    probe = {"params": {"G11Phase": 0.25}, "slots": {"rod": [0.0, -0.38, 0.0, 0.92], "witch": [33.0, 10.4, 9.5],
                                                     "carrier": [0.0, 10.4, 9.5]}}
    moved = {"params": probe["params"], "slots": dict(probe["slots"], witch=[33.02, 10.4, 9.5])}
    assert v.check_drift([probe, probe], [100.0, 101.0], [98.0, 99.0])["problems"] == []
    assert any("witch moved" in p for p in v.check_drift([probe, moved], [100.0, 101.0], [98.0, 99.0])["problems"])
    assert any("witch theta - omega t" in p for p in v.check_drift([probe, probe], [100.0, 120.0], [98.0, 99.0])["problems"])
    assert any("carrier theta - omega t" in p for p in v.check_drift([probe, probe], [100.0, 101.0], [98.0, 130.0])["problems"])


def _live(name, pos=(0, 0, 0), rot=(0, 0, 0, 1), children=None) -> dict:
    return {"name": name, "position": _p(pos), "rotation": _q(rot), "scale": _p((1, 1, 1)), "children": children or []}


def _decl(name, pos=(0, 0, 0), children=None) -> dict:
    return {"slot": {"key": name, "name": name, "position": list(pos), "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]},
            "children": children or []}


def test_structure_check_finds_a_moved_m08_and_a_moved_rod_pivot_but_not_the_driven_witch():
    g9 = gimmicks.g09()
    doc = _decl("C_candy", children=[
        _decl(g9["asset_id"], (34.4, 0, 5.2), [_decl(g9["stir_pivot"], (0, 1.16, 0), [_decl("CCD_MagicCauldron_001_StirRod")])]),
        _decl(G11["loop_asset_id"], (33, 0, 0), [_decl(G11["carrier"], (10.2, 10.2, 0), [_decl("CCD_WitchPatrolLoop_001_CarrierAttach")])]),
        _decl(G11["rider"], (43.2, 10.2, 0))])
    m08 = _decl("M08", children=[_decl("M08_FlyingWitch_001")])

    def world(m08_pos=(0, 0, 0), pivot_pos=(0, 1.16, 0)):
        return _live("C_candy", children=[
            _live(g9["asset_id"], (34.4, 0, 5.2), children=[_live(g9["stir_pivot"], pivot_pos, (0.1, -0.7, 0.07, 0.7),
                                                                  [_live("CCD_MagicCauldron_001_StirRod")])]),
            _live(G11["loop_asset_id"], (33, 0, 0), children=[_live(G11["carrier"], (-4.3, 10.2, 8.8), (0, -0.82, 0, 0.57),
                                                                    [_live("CCD_WitchPatrolLoop_001_CarrierAttach")])]),
            _live(G11["rider"], (28.7, 10.2, 8.8), (0, -0.82, 0, 0.57), [_live("M08", m08_pos, children=[_live("M08_FlyingWitch_001")])])])

    assert v.check_structure(world(), doc, m08)["problems"] == []
    assert any("M08" in p for p in v.check_structure(world(m08_pos=(0, 0.3, 0)), doc, m08)["problems"])
    assert any(g9["stir_pivot"] in p for p in v.check_structure(world(pivot_pos=(0.2, 1.16, 0)), doc, m08)["problems"])


def test_envelope_problems_report_a_rod_outside_the_liquid_and_a_witch_near_m04():
    env = {"G09": {"max_radius_below_rim_m": 0.39, "lowest_m": 0.58, "points_outside_clear_radius": 0, "liquid_radius_m": 0.7,
                   "bottom_m": 0.2},
           "G11": {"lowest_m": 9.2, "corridor_bottom_m": 9.0, "points_outside_corridor_xy": 0, "nearest_m04_box_m": 2.4,
                   "m04_clearance_m": 1.0}}
    assert v.envelope_problems(env) == []
    assert v.envelope_problems({**env, "G09": dict(env["G09"], max_radius_below_rim_m=0.75)})
    assert v.envelope_problems({**env, "G11": dict(env["G11"], nearest_m04_box_m=0.4)})
