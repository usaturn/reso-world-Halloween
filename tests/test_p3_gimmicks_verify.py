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
