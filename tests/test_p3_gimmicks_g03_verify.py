"""S-criteria tests for the W10-A live check of G03 (``modeling/p3_gimmicks/verify_g03.py``).

Why these tests exist (create-reso-world AGENTS.md, test criterion S): the live check is the evidence that the fountain water
glow follows its formula at the recorded speed, that the external values are clamped, and that only the water stopped using
the material shared inside A. If a guard stopped working, a glow that is frozen, runs at the wrong speed, follows another
formula, ignores the clamp, or a shared material that changed every object using it would be reported as passing and
recorded as verified with no error. Each test keeps one representative case of one guard; the first case of each keeps the
correct state passing.
"""

from __future__ import annotations

import copy
import math

from modeling.p3_gimmicks import district, verify_g03

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


def test_window_rejects_a_time_formula_that_only_matches_the_mean_speed():
    w = 2.0 * math.pi * 0.2
    _, problems = verify_g03.check_samples(_samples(lambda t: w * t + 0.8 * math.sin(w * t), _times(22)), PARAMS, E0, E1)
    assert len(problems) == 1 and "straight line" in problems[0]


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


def _docs():
    """G03 を足す前の宣言（model）と、district.add_g03_material で足した後の宣言（p2）。"""
    mat = {"AlbedoColor": [0.6, 0.8, 0.9, 1.0], "EmissiveColor": [0.74, 1.0, 1.28, 1.0], "Metallic": 0.1}
    def renderer(key, mats):
        return {"key": key, "type": "FrooxEngine.MeshRenderer", "fields": {"Materials": [f"$component:{m}" for m in mats]}}
    def slot(name, comps=(), children=()):
        return {"slot": {"name": name}, "components": list(comps), "children": list(children)}
    model = slot("A_plaza", children=[
        slot("Blender_Providers", [{"key": "m_water", "type": "FrooxEngine.PBS_Metallic", "fields": dict(mat)},
                                   {"key": "m_stone", "type": "FrooxEngine.PBS_Metallic", "fields": {"Metallic": 0.0}}]),
        slot("APL_Fountain_001", children=[slot("APL_Fountain_001_Water", [renderer("r_water", ["m_water"])]),
                                           slot("APL_Fountain_001_WaterAttach", [renderer("r_attach", ["m_water"])])]),
        slot("Pylons", [renderer("r_pylon", ["m_stone", "m_water"])]),
    ])
    p2 = copy.deepcopy(model)
    district.add_g03_material(p2, "A_plaza")
    return model, p2


def _observe(p2):
    """宣言どおりに apply された観察（ID は id_<キー>、色は sRGB の profile 付き）。"""
    obs = {"materials": {r: [f"id_{m}" for m in ms] for r, ms in verify_g03.renderer_materials(p2).items()},
           "ids": {}, "fields": {}}
    stack = [p2]
    while stack:
        n = stack.pop()
        for c in n["components"]:
            if c["type"] == "FrooxEngine.PBS_Metallic":
                obs["ids"][c["key"]] = f"id_{c['key']}"
                obs["fields"][c["key"]] = {k: ({"r": v[0], "g": v[1], "b": v[2], "a": v[3], "profile": "sRGB"} if isinstance(v, list) else v)
                                           for k, v in c["fields"].items()} | {"Enabled": True}
        stack.extend(n["children"])
    return obs


def test_structure_rejects_a_changed_shared_material():
    model, p2 = _docs()
    decl = verify_g03.declared_materials(model, p2)
    assert decl["shared_renderers"] == ["r_attach", "r_pylon"] and verify_g03.check_structure(_observe(p2), decl) == []
    obs = _observe(p2)
    obs["fields"]["m_water"]["EmissiveColor"] = {"r": 0.3, "g": 0.4, "b": 0.9, "a": 1.0, "profile": "sRGB"}   # 共有の材質を駆動してしまった
    assert len(verify_g03.check_structure(obs, decl)) == 1
    obs = _observe(p2)
    obs["fields"]["m_water"]["EmissiveColor"]["profile"] = "Linear"   # 数値は同じでも、線形にすると明るさが変わる
    assert len(verify_g03.check_structure(obs, decl)) == 1


def test_structure_rejects_a_repointed_renderer_even_when_the_declaration_was_repointed_too():
    model, p2 = _docs()
    # 宣言でも取付位置の目印を専用の材質へ付け替え、そのとおりに apply された（基準は G03 を足す前の宣言）
    attach = p2["children"][1]["children"][1]["components"][0]
    attach["fields"]["Materials"] = ["$component:p3_g03_wm"]
    decl = verify_g03.declared_materials(model, p2)
    problems = verify_g03.check_structure(_observe(p2), decl)
    assert any(p.startswith("declaration r_attach") for p in problems) and any(p.startswith("r_attach:") for p in problems)
    # ショーの装置の材質の並びが減った（元の水の材質は残っている）
    model, p2 = _docs()
    obs = _observe(p2)
    obs["materials"]["r_pylon"] = ["id_m_water"]
    assert len(verify_g03.check_structure(obs, verify_g03.declared_materials(model, p2))) == 1
