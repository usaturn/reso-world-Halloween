"""S-criteria tests for ``modeling/p3_gimmicks/verify_d.py`` (W10-D, G15 ghost train loop).

Why these tests exist (create-reso-world AGENTS.md, test criterion S): ``verify_d.py`` is the evidence that the engine, the
car and the wheels in the world follow the stadium loop of the W05 data, clockwise, at the HMC_P3 speed, with the car
2.75 m behind, the wheels rolling forward, and the swept train staying out of the W01 routes and the boxes of the other
objects. If one of its guards broke, it would report a car at the wrong distance, a wheel that rolls backwards, a loop
formula that misses the W05 waypoints, a train running anticlockwise or facing backwards, a car gap that shrinks only in
motion, a speed that only matches on average, a wrong speed or a train that crosses the main route as passing, with no
error. The live positions are judged against the world clock read in the same observe (two clock fields driven with
WorldTimeDouble around the train's relays), because the wall-clock estimate of the read time was too loose (GPT review of
PR #66, M-1 and M-2).
Each test keeps one guard and also passes the correct state, so an implementation that rejects everything fails.
"""

from __future__ import annotations

import copy
import math

from modeling.p3_gimmicks import gimmicks
from modeling.p3_gimmicks import verify_d as v

G = gimmicks.g15()
L = G["length_m"]


def _q(t) -> dict:
    return dict(zip("xyzw", (float(c) for c in t)))


def _p(t) -> dict:
    return dict(zip("xyz", (float(c) for c in t)))


def _pose(u: float, g: dict = G, heading_off_deg: float = 0.0) -> tuple[dict, dict]:
    pos, th = gimmicks.g15_car_pose(u, g)
    th += math.radians(heading_off_deg)
    return _p(pos), _q((0.0, math.sin(th / 2.0), 0.0, math.cos(th / 2.0)))


def _frozen(phase: float, car_gap: float | None = None, wheel_sign: float = 1.0, g: dict = G) -> tuple:
    d = phase * L
    ue = G["rest_arc_m"][G["engine"]] + d
    uc = ue - (G["arc_offset_m"] if car_gap is None else car_gap)
    wheels = {w: _q(v.wheel_q(wheel_sign * d, spec["radius_m"])) for w, spec in G["wheels"].items()}
    return _pose(ue, g), _pose(uc, g), wheels


def test_frozen_sample_finds_a_wrong_car_gap_a_reversed_wheel_and_a_loop_formula_off_the_waypoints():
    params = {"G15Speed": 0.0, "G15Phase": 0.3}
    good = v.check_frozen(*_frozen(0.3), params)
    assert good["problems"] == []
    bad = v.check_frozen(*_frozen(0.3, car_gap=2.0), params)
    assert any(p.startswith("relay: car at") for p in bad["problems"])
    bad = v.check_frozen(*_frozen(0.3, wheel_sign=-1.0), params)
    assert any("Wheel" in p and "rotation" in p for p in bad["problems"])
    # 経路の式の誤り（曲線の半径 4.4 m）: 式どおりに置かれていても、W05 の経路点 6 から外れる
    wrong = copy.deepcopy(G)
    wrong["radius_m"] = 4.4
    wrong["length_m"] = 2 * wrong["straight_m"] + 2 * math.pi * 4.4
    phase = (G["waypoint_arc_m"][6] - G["rest_arc_m"][G["engine"]]) / L
    ok = v.check_frozen(*_frozen(phase), {"G15Speed": 0.0, "G15Phase": phase})
    assert ok["problems"] == [] and ok["rows"]["engine"]["waypoint"] == 6
    e, c, w = _frozen(phase)
    e = _pose(G["waypoint_arc_m"][6], wrong)
    off = v.check_frozen(e, c, w, {"G15Speed": 0.0, "G15Phase": phase}, g={**wrong, "length_m": L})
    assert any("from waypoint 6" in p for p in off["problems"])


def _samples(speed: float, n: int = 12, dt: float = 2.5, sign: float = 1.0, heading_off_deg: float = 0.0) -> list[dict]:
    """動いている間の全部の駆動の値の観察（check_sample）。"""
    out = []
    for i in range(n):
        t = 1000.0 + i * dt
        ue = G["rest_arc_m"][G["engine"]] + sign * speed * t
        uc = ue - G["arc_offset_m"]
        vals = {}
        vals["engine_pos"], vals["engine_rot"] = _pose(ue, heading_off_deg=heading_off_deg)
        vals["car_pos"], vals["car_rot"] = _pose(uc, heading_off_deg=heading_off_deg)
        for w, spec in G["wheels"].items():
            vals[w] = _q(v.wheel_q(speed * t, spec["radius_m"]))
        s = v.check_sample(vals)
        s["t"] = t
        out.append(s)
    return out


def _clocked(speed: float, n: int = 16, step: float = 0.115, engine_err=None, car_err=None,
             formula_speed: float | None = None) -> list[dict]:
    """「時計 1 → 先頭車 → 客車 → 時計 2」を、1 つ step 秒ずつ順に読んだ観察（2026-11-02 の実測の読み方）。engine_err・car_err は
    ワールドの時刻 t の位置の誤差（m）の関数。formula_speed はモジュールの速さ（既定は speed）。"""
    out = []
    fs = speed if formula_speed is None else formula_speed
    for i in range(n):
        t1 = 8000.0 + 1.5 * i
        te, tc, t2 = t1 + step, t1 + 2 * step, t1 + 3 * step
        ue = G["rest_arc_m"][G["engine"]] + fs * te + (engine_err(te) if engine_err else 0.0)
        uc = G["rest_arc_m"][G["car"]] + fs * tc + (car_err(tc) if car_err else 0.0)
        vals = {"ck1": t1, "ck2": t2, "engine_pos": _pose(ue)[0], "car_pos": _pose(uc)[0]}
        out.append(v.clocked_sample(vals))
    return out


def test_motion_checks_find_an_anticlockwise_or_backward_facing_train():
    good = _samples(2.2)
    assert v.check_clockwise(good)["problems"] == []
    assert v.check_travel(good)["problems"] == []
    # 反時計回り（弧の位置が減る）
    assert v.check_clockwise(_samples(2.2, sign=-1.0))["problems"]
    # 後ろを向いて進む（正面が 180° 逆）。動いている間の向きの検査とは別に、進んだ向きで見つける
    assert v.check_travel(_samples(2.2, heading_off_deg=180.0))["problems"]


def test_clocked_check_finds_a_car_gap_that_shrinks_in_motion_a_periodic_speed_and_a_wrong_speed():
    params = {"G15Speed": 2.2, "G15Phase": 0.0}
    good = v.check_clocked(_clocked(2.2), params)
    assert good["problems"] == [] and good["judged"] == 16
    # 客車の式に +0.5 × V（動いている間だけ車間が 1.1 m 縮む。PR #66 の GPT のレビュー M-1）
    m1 = v.check_clocked(_clocked(2.2, car_err=lambda t: 0.5 * 2.2), params)
    assert any(p.startswith("car: arc") for p in m1["problems"])
    # 客車の式に −0.5 × V（動いている間だけ遅れて車間が広がる）
    lag = v.check_clocked(_clocked(2.2, car_err=lambda t: -0.5 * 2.2), params)
    assert any(p.startswith("car: arc") for p in lag["problems"])
    # 平均の速さは合うが周期的に揺れる距離 D = V (t + 0.4 cos(2πt/20))（M-2）
    m2 = v.check_clocked(_clocked(2.2, engine_err=lambda t: 2.2 * 0.4 * math.cos(2 * math.pi * t / 20.0),
                                  car_err=lambda t: 2.2 * 0.4 * math.cos(2 * math.pi * t / 20.0)), params)
    assert any(p.startswith(("engine: arc", "car: arc")) for p in m2["problems"])
    # 速さが 2 倍
    assert v.check_clocked(_clocked(2.2, formula_speed=4.4), params)["problems"]
    # 時計の幅が広すぎる観察（1 つ 0.4 秒）は判定せず、判定できた観察が足りなければ問題にする（黙って合格にしない）
    wide = v.check_clocked(_clocked(2.2, step=0.4), params)
    assert wide["judged"] == 0 and any("clock window" in p for p in wide["problems"])


def _clock_series(speed: float, wheel_sign: float) -> list[tuple[float, dict]]:
    out = []
    for i in range(10):
        t = 50.0 + 4.0 * i
        d = speed * t
        vals = {"ck1": t - 0.4, "ck2": t + 0.4}
        vals["engine_pos"], _ = _pose(G["rest_arc_m"][G["engine"]] + d)
        vals["car_pos"], _ = _pose(G["rest_arc_m"][G["car"]] + d)
        for w, spec in G["wheels"].items():
            vals[w] = _q(v.wheel_q(wheel_sign * d, spec["radius_m"]))
        out.append((t, vals))
    return out


def test_slow_clock_finds_wheels_that_roll_backwards():
    assert v.check_clock(_clock_series(0.05, 1.0), 0.05, G)["problems"] == []
    bad = v.check_clock(_clock_series(0.05, -1.0), 0.05, G)["problems"]
    assert len(bad) == len(G["wheels"])


def test_envelope_finds_a_point_on_the_main_route_or_in_an_object_box():
    route = next(r for r in v._routes() if r["route_id"] == "Route_South_Entrance_Approach")
    assert v._in_corridor((1.5, -33.0, 0.5), route)
    assert not v._in_corridor((2.5, -33.0, 0.5), route)
    box = {"min": [9.65, -39.4, 0.0], "max": [13.35, -39.1, 3.2]}
    assert v.box_distance(box, (12.0, -39.2, 1.0)) == 0.0
    assert v.box_distance(box, (12.0, -38.9, 1.0)) > 0.19
