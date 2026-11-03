"""S-criteria tests for ``modeling/p3_gimmicks/verify_e.py`` (W10-E, G18 mushroom glow and G20 clock hands and bell).

Why these tests exist (create-reso-world AGENTS.md, test criterion S): ``verify_e.py`` is the evidence that the 14 mushrooms
glow with their own W06 period and phase inside 0.35..1.0 of the P2 glow without changing the hue, that no neighbouring pair
is bound to the same output, that the clock hands follow the viewer's local time clockwise from the front on the M07 dial axis, that the
bell swings within +-25 deg only after each mark and hangs still between marks, that the pond (which shares the glow material)
keeps the shared material, and that the swept hands and bell stay inside the W06 envelope and out of the E zones. If one of
its guards broke, it would report a wrong period or phase, a pair driven by one output, a hand running anticlockwise or on the world
clock instead of the local clock, a bell ringing again between marks or beyond its range, a hand off the dial centre, a
pond that lost its material, a pivot that does not follow its relay, a clock running on UTC instead of the local time zone or
a bell swinging into a viewing spot as passing, with no error. The bell is judged only from observations whose clock window is
at most 0.3 s, and the expected time-zone offset is an input (GPT review of PR #67, M-1 to M-3, m-1).
Each test keeps one guard and also passes the correct state, so an implementation that rejects everything fails.
"""

from __future__ import annotations

import copy
import math

from modeling.p3_gimmicks import gimmicks
from modeling.p3_gimmicks import verify_e as v

G18 = gimmicks.g18()
G20 = gimmicks.g20()
E0 = [1.536, 2.752, 3.2]
DEFAULT = {"G18Intensity": 1.0, "G18Speed": 1.0, "G20BellSwing": 1.0, "G20BellInterval": 3600.0}


def _level(lv: float, hue: float = 0.0) -> tuple[float, float]:
    return (lv, hue)


def _g18_samples(t0: float, *, n: int = 12, spread: float = 0.4) -> list[dict]:
    """各個体を、時計の幅 spread の中点の式の値で読んだ観察。"""
    out = []
    for i in range(n):
        t1 = t0 + 3.7 * i
        t2 = t1 + spread
        levels = {}
        for r in G18["individuals"]:
            levels[r["material_key"]] = _level(gimmicks.g18_level((t1 + t2) / 2.0, r))
        out.append({"t1": t1, "t2": t2, "levels": levels})
    return out


def test_g18_clocked_check_finds_a_pair_bound_to_the_same_output_and_a_changed_hue():
    assert v.check_g18_clocked(_g18_samples(2300.0), DEFAULT)["problems"] == []
    # 近くの組の片方がもう片方と同じ発光を出す（同じ出力に結ばれた）。個体ごとの式（周期・位相）との照合で見つける
    a, b = v.neighbours()[0]
    synced = _g18_samples(2300.0)
    for x in synced:
        x["levels"][b] = x["levels"][a]
    inst = {r["material_key"]: r["instance"] for r in G18["individuals"]}
    assert any(inst[b] in p for p in v.check_g18_clocked(synced, DEFAULT)["problems"])
    # 3 つの成分の倍率が違う（色合いが P2 の発光から変わった）
    s = _g18_samples(2300.0)
    s[0]["levels"][G18["individuals"][0]["material_key"]] = (s[0]["levels"][G18["individuals"][0]["material_key"]][0], 0.05)
    assert any("hue" in p for p in v.check_g18_clocked(s, DEFAULT)["problems"])


def test_g18_frozen_sample_finds_a_wrong_phase_or_intensity():
    params = dict(DEFAULT, G18Speed=0.0, G18Intensity=0.5)
    good = {r["material_key"]: _level(gimmicks.g18_level(0.0, r, 0.5, 0.0)) for r in G18["individuals"]}
    assert v.check_g18_frozen(good, params)["problems"] == []
    bad = dict(good)
    r0 = G18["individuals"][3]
    bad[r0["material_key"]] = _level(gimmicks.g18_level(0.0, dict(r0, phase_s=r0["phase_s"] + 0.4), 0.5, 0.0))
    assert any(r0["instance"] in p for p in v.check_g18_frozen(bad, params)["problems"])
    bad = {k: _level(lv * 2.0) for k, (lv, _) in good.items()}    # G18Intensity を 1 のまま使った
    assert v.check_g18_frozen(bad, params)["problems"]


def test_g18_all_finds_a_level_out_of_range():
    good = [{"levels": {k: lv for k, lv in s["levels"].items()}} for s in _g18_samples(1000.0, n=8, spread=0.0)]
    assert v.check_g18_all(good, DEFAULT)["problems"] == []
    a, _ = v.neighbours()[0]
    high = copy.deepcopy(good)
    high[0]["levels"][a] = (1.2, 0.0)
    assert any("outside" in p for p in v.check_g18_all(high, DEFAULT)["problems"])


def _hand_q(theta_deg: float, sign: float = 1.0) -> dict:
    h = math.radians(theta_deg) / 2.0 * sign
    return {"x": 0.0, "y": 0.0, "z": math.sin(h), "w": math.cos(h)}


def _bell_q(angle_deg: float) -> dict:
    h = math.radians(angle_deg) / 2.0
    return {"x": math.sin(h), "y": 0.0, "z": 0.0, "w": math.cos(h)}


def _g20_samples(s0: float, *, hand_sign: float = 1.0, hand_clock=None, bell=None, n: int = 10, step: float = 2.0,
                 spread: float = 0.25, params: dict | None = None, utc_offset_h: float = 9.0) -> list[dict]:
    """ローカル時刻 s0 から step 秒ごとの、時計の幅 spread の中点の式の値で読んだ観察。hand_clock は針の時刻（既定はローカル時刻）、
    bell は鐘の角度の式（既定は gimmicks.g20_bell_angle）。utc_sod は UTC + utc_offset_h の端末の UTC。"""
    p = params or DEFAULT
    out = []
    for i in range(n):
        s1 = s0 + step * i
        s2 = s1 + spread
        mid = (s1 + s2) / 2.0
        hc = hand_clock(mid) if hand_clock else mid
        b = bell(mid) if bell else gimmicks.g20_bell_angle(mid, p["G20BellSwing"], p["G20BellInterval"])
        out.append({"s1": s1, "s2": s2, "utc_sod": (mid - utc_offset_h * 3600.0) % 86400.0, "half": 1.0,
                    "hour": _hand_q(math.degrees(gimmicks.g20_hand_angle(hc, 43200.0)), hand_sign),
                    "minute": _hand_q(math.degrees(gimmicks.g20_hand_angle(hc, 3600.0)), hand_sign),
                    "bell": _bell_q(b)})
    return out


def test_g20_hands_on_another_clock_are_found():
    good = v.check_g20_clocked(_g20_samples(47525.0), DEFAULT, expected_offset_h=9.0)
    assert good["problems"] == []
    assert good["local_vs_utc"]["offset_hours"] == [9.0]
    # 針がワールドの時刻（セッションの開始から 2317 秒）で進む: 時計のローカル時刻の式から外れる
    world = v.check_g20_clocked(_g20_samples(47525.0, hand_clock=lambda s: s - 47525.0 + 2317.0), DEFAULT)
    assert any("outside the local-time formula" in p for p in world["problems"])
    # ToLocalTime が抜けて、時計も針も UTC のまま動く（日本時間の端末）。針と時計は合うが、期待するタイムゾーンと違う
    utc = v.check_g20_clocked(_g20_samples(47525.0 - 9 * 3600.0, utc_offset_h=0.0), DEFAULT, expected_offset_h=9.0)
    assert any("not the expected local offset" in p for p in utc["problems"])


def test_g20_tip_direction_guard_is_tied_to_the_w06_front():
    # 観察した針の回転を −Z まわり（前から見て反時計回り）にすると、針の先が W06 の「前から見て 3 時 = −X_B」の向きから外れる
    # （針の角度の式の照合とは別の守り。Resonite の +Z まわりの正が前から見て時計回りであることを、W06 の正面と 3 時の向きで決める）
    assert v.clock_tip_local(90.0)[0] < -0.999
    s = _g20_samples(47525.0)
    for x in s:
        for name in ("hour", "minute"):
            x[name] = {k: (-x[name][k] if k == "z" else x[name][k]) for k in "xyzw"}
    bad = v.check_g20_clocked(s, DEFAULT)
    assert any("tip points" in p for p in bad["problems"])


def test_g20_bell_ringing_between_marks_late_or_beyond_its_range_is_found():
    p = dict(DEFAULT, G20BellInterval=20.0)
    marks = _g20_samples(48820.0 - 4.0, n=40, step=1.0, params=p)
    good = v.check_g20_clocked(marks, p)
    assert good["problems"] == [] and good["bell_rung_samples"] > 0 and good["bell_still_samples"] > 0
    assert v.check_bell_marks(marks, p, 2)["problems"] == []
    # 節目の間にもう一度揺れる（τ = 15 秒から）
    again = _g20_samples(48820.0 - 4.0, n=40, step=1.0, params=p,
                         bell=lambda s: gimmicks.g20_bell_angle(s, 1.0, 20.0) + gimmicks.g20_bell_angle(s - 15.0, 1.0, 20.0)
                         * (1.0 if (s % 20.0) >= 15.0 else 0.0))
    assert any("between marks" in r for r in v.check_g20_clocked(again, p)["problems"])
    # 節目から 3 秒遅れて揺れ始める
    late = _g20_samples(48820.0 - 4.0, n=40, step=1.0, params=p, bell=lambda s: gimmicks.g20_bell_angle(s - 3.0, 1.0, 20.0))
    assert v.check_g20_clocked(late, p)["problems"]
    # 節目の後の 12 秒の中で、往復の回数が違う（6 往復のはずが 3 往復）。節目の間は真下のまま
    def three(s: float) -> float:
        x = min(max((s % 20.0) / gimmicks.G20_BELL_DURATION_S, 0.0), 1.0)
        return 25.0 * (1.0 - x) ** 2 * math.sin(2.0 * math.pi * 3 * x)

    # 時計の幅を判定の上限（0.3 秒）にしても見つける。上限より広い観察（GPT のレビュー M-1 の例: 1.85 秒ごと・幅 1.19 秒）は
    # 揺れを判定せず、判定できた観察のある節目が足りないことを問題にする（合格にしない）
    slow = _g20_samples(48820.0 - 1.0, n=40, step=0.25, spread=v.BELL_SPREAD_MAX_S - 0.01, params=p, bell=three)
    assert any("outside the formula" in r for r in v.check_g20_clocked(slow, p)["problems"])
    loose = _g20_samples(48817.35, n=24, step=1.85, spread=1.19, params=p, bell=three)
    assert not any("outside the formula" in r for r in v.check_g20_clocked(loose, p)["problems"])
    assert any("marks were observed" in r for r in v.check_bell_marks(loose, p, 2)["problems"])
    # ±25° を超える（式の 1.5 倍）
    wide = _g20_samples(48820.0 - 1.0, n=40, step=0.25, spread=0.05, params=p,
                        bell=lambda s: 1.5 * gimmicks.g20_bell_angle(s, 1.0, 20.0))
    assert any("beyond" in r for r in v.check_g20_clocked(wide, p)["problems"])
    # 節目の後に揺れない
    silent = _g20_samples(48820.0 - 4.0, n=40, step=1.0, params=p, bell=lambda s: 0.0)
    assert any("did not swing" in r for r in v.check_bell_marks(silent, p, 2)["problems"])


def test_a_pivot_that_does_not_follow_its_relay_is_found():
    # Pivot そのもの（Slot の回転）を時計で挟んで読む。中継の値が正しくても、Pivot が 12 時のまま止まっていれば外れる
    s1, s2 = 50412.0, 50421.5
    mid = (s1 + s2) / 2.0
    good = {"s1": s1, "s2": s2, "hour": _hand_q(math.degrees(gimmicks.g20_hand_angle(mid, 43200.0))),
            "minute": _hand_q(math.degrees(gimmicks.g20_hand_angle(mid, 3600.0))), "bell": _bell_q(0.0)}
    assert v.check_pivots(good, DEFAULT)["problems"] == []
    stopped = dict(good, hour=_hand_q(0.0), minute=_hand_q(0.0))
    assert any("hand pivot" in p for p in v.check_pivots(stopped, DEFAULT)["problems"])


def _tower(hand_dx: float = 0.0) -> tuple[dict, dict]:
    """時計塔の宣言と、観察（針の Pivot は回っている）。hand_dx で時針の Pivot を横にずらす。"""
    names = [G20["hands"]["hour"]["pivot"], G20["hands"]["minute"]["pivot"], G20["bell"]["pivot"]]
    pos = {names[0]: [0.0015, 8.032, 0.419], names[1]: [0.0015, 8.032, 0.459], names[2]: [0.0015, 10.95, 1.45]}

    def slot(n, p, r=(0.0, 0.0, 0.0, 1.0)):
        return {"key": n, "name": n, "position": list(p), "rotation": list(r), "scale": [1, 1, 1]}

    decl = {"slot": slot("E_forest", (0, 0, 0)), "children": [
        {"slot": slot(G20["asset_id"], (-38.5, 0.0, 0.0), (0.0, 0.7071068, 0.0, 0.7071068)),
         "children": [{"slot": slot(n, pos[n]), "children": []} for n in names]}]}

    def live(n, p, r=(0.0, 0.0, 0.0, 1.0), children=()):
        return {"name": n, "position": dict(zip("xyz", p)), "rotation": dict(zip("xyzw", r)), "scale": {"x": 1, "y": 1, "z": 1},
                "children": list(children)}

    kids = []
    for n in names:
        p = list(pos[n])
        if n == names[0]:
            p[0] += hand_dx
        kids.append(live(n, p, (0.0, 0.0, 0.38, 0.92)))
    root = live("E_forest", (0, 0, 0), children=[live(G20["asset_id"], (-38.5, 0.0, 0.0), (0.0, 0.7071068, 0.0, 0.7071068), kids)])
    return root, decl


def test_hand_axis_off_the_m07_dial_centre_is_found():
    centre = [0.0015, 0.3539, 8.032]
    root, decl = _tower()
    assert v.check_tower(root, decl, centre)["problems"] == []
    root, decl = _tower(hand_dx=0.03)
    problems = v.check_tower(root, decl, centre)["problems"]
    assert any("off the M07 dial centre" in p for p in problems)


def _material_docs() -> tuple[dict, dict]:
    """G18 を足す前（model）と後（p2）の宣言。池は共有の発光の材質を使い続ける。"""
    src = {"key": "glow_src", "type": "FrooxEngine.PBS_Metallic",
           "fields": {"AlbedoColor": [0.85, 0.96, 1.0, 1.0], "EmissiveColor": [1.2066, 1.5536, 1.6579, 1.0]}}
    pond = {"key": "pond_r", "type": "FrooxEngine.MeshRenderer", "fields": {"Materials": ["$component:moss", "$component:glow_src"]}}

    def glow_node(r, mat):
        return {"slot": {"name": r["instance"]}, "components": [], "children": [
            {"slot": {"name": r["glow_part"]}, "children": [],
             "components": [{"key": f"rend_{r['material_key']}", "type": "FrooxEngine.MeshRenderer",
                             "fields": {"Materials": [f"$component:{mat}"]}}]}]}

    model = {"slot": {"name": "E_forest"}, "components": [src, pond], "children": [glow_node(r, "glow_src") for r in G18["individuals"]]}
    p2 = copy.deepcopy(model)
    for node, r in zip(p2["children"], G18["individuals"]):
        node["children"][0]["components"][0]["fields"]["Materials"] = [f"$component:{r['material_key']}"]
        node["children"][0]["components"].append({"key": r["material_key"], "type": "FrooxEngine.PBS_Metallic",
                                                  "fields": {"AlbedoColor": [0.85, 0.96, 1.0, 1.0]},
                                                  "initialFields": {"EmissiveColor": [1.2066, 1.5536, 1.6579, 1.0]}})
    return model, p2


def _material_obs(decl: dict, pond_to: str | None = None, src_emissive=None) -> dict:
    ids = {k: f"id_{k}" for k in ["glow_src", "moss", *[r["material_key"] for r in G18["individuals"]]]}
    mats = {r: [ids[k] for k in ks] for r, ks in decl["expected"].items()}
    if pond_to:
        mats["pond_r"] = [ids["moss"], ids[pond_to]]
    fields = {"glow_src": {"AlbedoColor": {"r": 0.85, "g": 0.96, "b": 1.0, "a": 1.0, "profile": "sRGB"},
                           "EmissiveColor": src_emissive or {"r": 1.2066, "g": 1.5536, "b": 1.6579, "a": 1.0, "profile": "sRGB"}}}
    for r in G18["individuals"]:
        fields[r["material_key"]] = {"AlbedoColor": {"r": 0.85, "g": 0.96, "b": 1.0, "a": 1.0, "profile": "sRGB"}, "Enabled": True}
    fields["moss"] = {"Enabled": True}
    return {"materials": mats, "ids": ids, "fields": fields}


def test_the_pond_keeps_the_shared_glow_material_and_the_shared_material_is_unchanged():
    model, p2 = _material_docs()
    decl = v.declared_materials(model, p2)
    assert decl["shared_renderers"] == ["pond_r"]
    assert v.check_materials(_material_obs(decl), decl) == []
    moved = v.check_materials(_material_obs(decl, pond_to=G18["individuals"][0]["material_key"]), decl)
    assert any(p.startswith("pond_r: materials") for p in moved)
    # 共有の材質の発光を変えた宣言を apply した（実物も宣言の後の値）。基準は G18 を足す前の宣言なので外れる（GPT のレビュー m-1）
    changed = copy.deepcopy(p2)
    changed["components"][0]["fields"]["EmissiveColor"] = [0.5, 0.6, 0.7, 1.0]
    decl2 = v.declared_materials(model, changed)
    obs = _material_obs(decl2, src_emissive={"r": 0.5, "g": 0.6, "b": 0.7, "a": 1.0, "profile": "sRGB"})
    assert any("shared" in p for p in v.check_materials(obs, decl2))


def test_envelope_problems_report_a_swing_out_of_the_w06_envelope_or_into_a_zone():
    ok = {"parts": {G20["bell"]["pivot"]: {"beyond_w06_m": 0.0, "lowest_above_walk_m": 7.4, "points_in_zones": {}}}}
    assert v.envelope_problems(ok) == []
    bad = copy.deepcopy(ok)
    bad["parts"][G20["bell"]["pivot"]].update(beyond_w06_m=0.2, points_in_zones={"EFR_View_Forecourt": 3})
    problems = v.envelope_problems(bad)
    assert any("W06 envelope" in p for p in problems) and any("EFR_View_Forecourt" in p for p in problems)
