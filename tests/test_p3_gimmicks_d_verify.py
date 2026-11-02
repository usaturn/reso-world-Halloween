"""S-criteria tests for ``modeling/p3_gimmicks/verify_d.py`` (W10-D, G15 ghost train loop).

Why these tests exist (create-reso-world AGENTS.md, test criterion S): ``verify_d.py`` is the evidence that the engine, the
car and the wheels in the world follow the stadium loop of the W05 data, clockwise, at the HMC_P3 speed, with the car
2.75 m behind, the wheels rolling forward, and the swept train staying out of the W01 routes and the boxes of the other
objects. If one of its guards broke, it would report a car at the wrong distance, a wheel that rolls backwards, a loop
formula that misses the W05 waypoints, a train running anticlockwise or facing backwards, a stuck car, a wrong speed or a
train that crosses the main route as passing, with no error.
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


def _samples(speed: float, n: int = 12, dt: float = 2.5, sign: float = 1.0, lag_s: float = 0.25,
             heading_off_deg: float = 0.0, car_stuck: bool = False) -> list[dict]:
    out = []
    for i in range(n):
        t = 1000.0 + i * dt
        ue = G["rest_arc_m"][G["engine"]] + sign * speed * t
        uc = ue - G["arc_offset_m"] + sign * speed * lag_s
        if car_stuck:
            uc = G["rest_arc_m"][G["car"]] + sign * speed * 1000.0
        vals = {}
        vals["engine_pos"], vals["engine_rot"] = _pose(ue, heading_off_deg=heading_off_deg)
        vals["car_pos"], vals["car_rot"] = _pose(uc, heading_off_deg=heading_off_deg)
        for w, spec in G["wheels"].items():
            vals[w] = _q(v.wheel_q(speed * t, spec["radius_m"]))
        s = v.check_sample(vals)
        s["t"] = t
        s["half"] = 0.5
        out.append(s)
    return out


def test_motion_checks_find_an_anticlockwise_or_backward_facing_train_a_stuck_car_and_a_wrong_speed():
    good = _samples(2.2)
    assert v.check_clockwise(good)["problems"] == []
    assert v.check_travel(good)["problems"] == []
    assert v.check_gap(good, G, 2.2)["problems"] == []
    assert v.check_speed([(s["t"], s["engine"]["u_m"]) for s in good], 2.2, L, "engine")["problems"] == []
    # 反時計回り（弧の位置が減る）
    assert v.check_clockwise(_samples(2.2, sign=-1.0))["problems"]
    # 後ろを向いて進む（正面が 180° 逆）。動いている間の向きの検査とは別に、進んだ向きで見つける
    assert v.check_travel(_samples(2.2, heading_off_deg=180.0))["problems"]
    # 客車が止まっている・先へ出ている（同じ観察の中の弧の差が、読み取りの遅れ（0〜実行時間 1 秒）の範囲の外）
    assert v.check_gap(_samples(2.2, car_stuck=True), G, 2.2)["problems"]
    assert v.check_gap(_samples(2.2, lag_s=-0.2), G, 2.2)["problems"]
    # 速さが 2 倍
    fast = _samples(4.4, dt=1.2)
    assert v.check_speed([(s["t"], s["engine"]["u_m"]) for s in fast], 2.2, L, "engine")["problems"]
    # 平均の速さは合うが、途中で時刻から ±3 m 外れる式は外れる。読んだ時刻の見積もりの幅（±0.5 秒 × 2.2 m/s）の中のばらつきは通る
    ts = [1000.0 + 2.5 * i for i in range(16)]
    wobble = [(t, (3.0 + 2.2 * t + 3.0 * math.sin(2 * math.pi * i / 16)) % L) for i, t in enumerate(ts)]
    assert any("off the line of the clock" in p for p in v.check_speed(wobble, 2.2, L, "engine", [0.5] * 16)["problems"])
    jitter = [(t, (3.0 + 2.2 * t + (0.9 if i % 2 else -0.9)) % L) for i, t in enumerate(ts)]
    assert v.check_speed(jitter, 2.2, L, "engine", [0.5] * 16)["problems"] == []


def _clock_series(speed: float, wheel_sign: float) -> list[tuple[float, dict]]:
    out = []
    for i in range(10):
        t = 50.0 + 4.0 * i
        d = speed * t
        vals = {}
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
