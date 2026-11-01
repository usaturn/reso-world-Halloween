"""S-criteria tests for the W10-A live check of G03 (``modeling/p3_gimmicks/verify_g03.py``).

Why these tests exist (create-reso-world AGENTS.md, test criterion S): the live check is the evidence that the fountain water
glow follows its formula at the recorded speed, that the external values are clamped, and that only the water stopped using
the material shared inside A. If a guard stopped working, a glow that is frozen, runs at the wrong speed, follows another
formula, ignores the clamp, or a shared material that changed every object using it would be reported as passing and
recorded as verified with no error. Each test keeps one representative case of one guard; the first case of each keeps the
correct state passing.
"""

from __future__ import annotations

import math

from modeling.p3_gimmicks import verify_g03

E0 = [0.504, 0.99, 1.764]
E1 = [1.2, 0.4, 2.0]
PARAMS = {"G03Intensity": 1.0, "G03Frequency": 0.2, "G03Swing": 1.0}


def _samples(theta_of_t, times, intensity=1.0, swing=1.0, e0=E0, e1=E1):
    return [{"t": t, "linear": verify_g03.model(theta_of_t(t), intensity, swing, e0, e1)} for t in times]


def _times(n=14, step=1.4):
    return [100.0 + i * step for i in range(n)]


def test_window_passes_the_formula_and_rejects_another_formula():
    w = 2.0 * math.pi * 0.2
    summary, problems = verify_g03.check_samples(_samples(lambda t: w * t, _times()), PARAMS, E0, E1)
    assert problems == [] and abs(summary["theta_speed_rad_per_s"] / w - 1.0) < 1e-6
    # 色の移り変わりを脈と同じ速さにした（cos(θ/2) を cos θ にした）グラフ
    def wrong_model(th):
        pulse, mix = 1.0 + 0.5 * math.sin(th), 0.5 - 0.5 * math.cos(th)
        return [pulse * (a + mix * (b - a)) for a, b in zip(E0, E1)]
    wrong = [{"t": t, "linear": wrong_model(w * t)} for t in _times()]
    _, problems = verify_g03.check_samples(wrong, PARAMS, E0, E1)
    assert any("residual" in p for p in problems)


def test_window_rejects_a_frozen_glow():
    _, problems = verify_g03.check_samples(_samples(lambda t: 1.0, _times()), PARAMS, E0, E1)
    assert any("pulse moved only" in p for p in problems)


def test_window_rejects_a_glow_running_at_the_wrong_speed():
    w = 2.0 * math.pi * 0.2 * 0.8   # 20% 遅い
    _, problems = verify_g03.check_samples(_samples(lambda t: w * t, _times()), PARAMS, E0, E1)
    assert len(problems) == 1 and "theta speed" in problems[0]


def test_frozen_sample_requires_the_clamped_intensity():
    assert verify_g03.check_frozen([2.0 * a for a in E0], verify_g03.clamped({**PARAMS, "G03Intensity": 5.0})[0], E0) == []
    # 範囲に収めずに 5 倍で光っている
    assert len(verify_g03.check_frozen([5.0 * a for a in E0], verify_g03.clamped({**PARAMS, "G03Intensity": 5.0})[0], E0)) == 1


def test_clock_rejects_a_theta_that_does_not_follow_the_world_time():
    f = verify_g03.CLOCK_FREQUENCY
    lin1 = verify_g03.model(1.0, 1.0, 1.0, E0, E1)
    good = verify_g03.model(1.0 + 2.0 * math.pi * f * 20.0, 1.0, 1.0, E0, E1)
    assert verify_g03.check_clock(lin1, 0.0, good, 20.0, 1.0, 1.0, E0, E1)[1] == []
    _, problems = verify_g03.check_clock(lin1, 0.0, lin1, 20.0, 1.0, 1.0, E0, E1)
    assert len(problems) == 1 and "advanced" in problems[0]


def _structure():
    decl = {
        "water_renderer": "r_water", "material": "p3_g03_wm", "source": "m_water", "shared_renderers": ["r_attach", "r_pylon"],
        "source_decl": {"fields": {"AlbedoColor": [0.6, 0.8, 0.9, 1.0], "EmissiveColor": [0.74, 1.0, 1.28, 1.0], "Metallic": 0.1}},
        "material_decl": {"fields": {"AlbedoColor": [0.6, 0.8, 0.9, 1.0], "Metallic": 0.1}},
    }
    obs = {
        "materials": {"r_water": ["id_mine"], "r_attach": ["id_src"], "r_pylon": ["id_stone", "id_src"]},
        "ids": {"p3_g03_wm": "id_mine", "m_water": "id_src"},
        "fields": {
            "m_water": {"AlbedoColor": {"r": 0.6, "g": 0.8, "b": 0.9, "a": 1.0}, "EmissiveColor": {"r": 0.74, "g": 1.0, "b": 1.28, "a": 1.0},
                        "Metallic": 0.1},
            "p3_g03_wm": {"AlbedoColor": {"r": 0.6, "g": 0.8, "b": 0.9, "a": 1.0}, "Metallic": 0.1, "Enabled": True},
        },
    }
    return decl, obs


def test_structure_rejects_a_changed_shared_material_or_a_repointed_shared_renderer():
    decl, obs = _structure()
    assert verify_g03.check_structure(obs, decl) == []
    decl, obs = _structure()
    obs["fields"]["m_water"]["EmissiveColor"] = {"r": 0.3, "g": 0.4, "b": 0.9, "a": 1.0}   # 共有の材質を駆動してしまった
    assert len(verify_g03.check_structure(obs, decl)) == 1
    decl, obs = _structure()
    obs["materials"]["r_attach"] = ["id_mine"]   # 取付位置の目印まで専用の材質に付け替えた
    assert len(verify_g03.check_structure(obs, decl)) == 1
