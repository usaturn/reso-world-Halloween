"""W10-E: Resonite で動いている G18（キノコの発光）・G20（時計の針と鐘）を、時間を空けた観察から検査する。

実行（プロジェクトのディレクトリ。対象のワールドを Resonite の前面に出しておく。背面では駆動が進まない）:
    uv run python modeling/p3_gimmicks/verify_e.py --url ws://localhost:<PORT>/ \\
        --raw-out <Git の外の JSON> --output review/p3_gimmicks/g18_g20_live_checks.json [--windows 2 --gap 300]
    # 外から変えられる値の確認（値を変えて測り、元に戻す。ワールドに書く）
    uv run python modeling/p3_gimmicks/verify_e.py --url ... --raw-out ... --output review/p3_gimmicks/g18_g20_param_checks.json --param-check

時刻の基準: G18 は WorldTimeDouble（ワールドの時刻）、G20 は見る人の端末のローカル時刻（ToLocalTime(UtcNow) の 0 時からの秒）。
どちらも、モジュールが時計塔の asset root と鐘の腕木の検査用の時計（ValueField<double2> = (ワールドの時刻, ローカル時刻の秒)）に
drive するので、1 回の observe で「時計 1 → 対象 → 時計 2」を読み、対象を読んだ時刻を挟んで式と照合する（W10-D と同じ）。

観察（窓ごと。--windows の数だけ、--gap 秒あけて繰り返す）
- 構造: 窓の最初と最後に、E のすべての MeshRenderer の Materials が、G18 を足す前の宣言（同じ export の model.apply.json）の並びと
  同じか（キノコの 14 個の _Glow だけは個体ごとの材質）。共有の発光の材質と個体ごとの材質の値が宣言どおりか。時計塔の子孫が宣言と
  同じパスで同じローカルの変換か（Pivot の回転は比べない）。針の Pivot が M07 の文字盤の中心の軸から 1 cm 以内か。中継の Drives が
  Pivot の Rotation を指し有効か
- 時刻を止めた標本（G18Speed = 0）: 14 個の発光が、個体ごとの位相・強さの範囲の式の値か（窓の間で比べる）。値は戻す
- G18（時計で挟む）: 2 個ずつ「時計 1 → 発光 → 発光 → 時計 2」を読み、発光の倍率が、時計の幅のワールドの時刻の式の値の範囲の中か。
  3 つの成分の倍率が同じ（色合いが P2 のまま）か
- G18（14 個を続けて）: どの個体も強さの範囲（W06 の 0.35〜1.0 × G18Intensity）の中か。近くの組の倍率の差は記録だけ（周期の
  近い組は W06 のデータどおりに揃って見える時間があり、その割合と長さは sync_report がデータから求める。同じ出力に結ばれた組は、
  個体ごとの式で照合する G18 の時計で挟んだ照合が見つける）
- G20（時計で挟む）: 「時計 1 → 時針 → 分針 → 鐘 → 時計 2」を読み、針の角度がローカル時刻の式（時針 0.5°/分、分針 6°/分）の
  値の範囲の中か、針の先が前から見て時計回りの向き（W06: 3 時 = Pivot のローカル −X_B）か、回転が Pivot の Z（Blender の Y）軸の
  まわりだけか。鐘が節目の式の値の範囲の中か（節目の間は真下）、±25° 以内か。ローカル時刻が、この端末の UTC に 15 分の倍数を
  足した値と合うか（タイムゾーンの差と残り）

検査（--param-check）
- G18: G18Speed = 0 で G18Intensity 0.5・3（2 に収まる）・−1（0 に収まる。消える）の値を式と照合。ゆっくりの時刻（G18Speed 0.05）と
  速い時刻（2）で、時計で挟んだ照合（周期・位相を細かく見る）
- G20: G20BellInterval 20 秒で、鐘が節目ごとに式どおり揺れて止まり、節目の間に鳴り直さないか。G20BellSwing 3（1 に収まる）・0.5、
  G20BellInterval 5（20 に収まる）も同じ照合
- どれも元に戻し、戻ったかを確かめる

包絡（バンドルのメッシュから。観察ではない）: 時針・分針を 1 周、鐘を ±25° 回した点が、W06 の包絡（motion_envelopes）の中、
歩く高さ（walk_clearance_z_m）より上、E の除外範囲・鑑賞位置の外か。キノコは動かない（発光だけ）。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from modeling.p3_gimmicks import district, gimmicks  # noqa: E402
from modeling.p3_gimmicks.build_content import e_keys, e_rest  # noqa: E402
from modeling.p3_gimmicks.verify_g03 import OBSERVE_LIMIT, _close, renderer_materials, to_linear  # noqa: E402
from modeling.p3_gimmicks.verify_live import (  # noqa: E402
    STATE_DIR, _bundle, _child, _decl_paths, _find_decl, _local_points, _same_local, component_id, qmul, qrot,
    run_json, set_member)

E_STATE = STATE_DIR / "p2_E_forest.json"
P3_STATE = STATE_DIR / "p3_gimmicks.json"
LEVEL_TOL = 0.003            # 発光の倍率（線形の色 ÷ P2 の発光）と式の差
HUE_TOL = 1e-3               # 3 つの成分の倍率の差（色合いが変わらない）
FROZEN_LEVEL_TOL = 1e-4
FRAME_SLACK_S = 0.034        # 2 フレーム（60 fps）。駆動の評価と読み取りのフレームのずれの分
CLOCK_SPREAD_MAX_S = 1.2     # 時計の幅がこれより広い観察は判定しない（2026-11-03 は 1 つの Component に 約 0.15 秒）
MIN_JUDGED = 4
HAND_TOL_DEG = 0.05          # 針の角度と時計の幅のローカル時刻の式の範囲の差
TIP_TOL_DEG = 0.1            # 針の先の向きと、前から見て時計回りの向きの差
AXIS_TOL = 1e-4              # 回転の軸以外の成分
BELL_TOL_DEG = 0.3
STILL_TOL_DEG = 1e-3         # 節目の間の鐘（真下）
DIAL_AXIS_TOL_M = 0.01       # 針の Pivot と M07 の文字盤の中心の軸
TZ_RESIDUAL_MAX_S = 5.0      # ローカル時刻 − (この端末の UTC + 15 分の倍数)
SYNC_MIN_DIFF = 0.1          # 近くの個体との倍率の差の最大がこれ未満なら「揃って変わる」
LOCAL_TOL = 1e-4
ENVELOPE_SLACK_M = 0.01
SLOW_SPEED = 0.05            # G18 のゆっくりの時刻（倍率の変化は 1/20）
STEPS_PER_S = 200            # 時計の幅の中の式の範囲を求める刻み


def _clamp(x: float, lo: float, hi: float) -> float:
    return min(max(float(x), lo), hi)


def variables() -> dict:
    return {**gimmicks.G18_VARIABLES, **gimmicks.G20_VARIABLES}


def params_of(raw: dict) -> dict:
    """観察した値を、モジュールと同じ範囲に収めた値にする。"""
    v = variables()
    return {n: _clamp(raw[n], v[n]["min"], v[n]["max"]) for n in v}


# ---- 式と照合 ------------------------------------------------------------------------------------------------------------

def level_of(color: dict, e0: list[float]) -> tuple[float, float]:
    """観察した発光の色（profile 付き）の、P2 の発光 e0（線形）に対する倍率と、3 つの成分の倍率の差。"""
    lin = to_linear(color)
    ks = [c / b for c, b in zip(lin, e0)]
    return sum(ks) / 3.0, max(ks) - min(ks)


def _range(f, t1: float, t2: float) -> tuple[float, float]:
    """関数 f の [t1, t2] の値の最小と最大（STEPS_PER_S の刻みと両端）。"""
    n = max(2, int(math.ceil((t2 - t1) * STEPS_PER_S)) + 1)
    vals = [f(t1 + (t2 - t1) * i / (n - 1)) for i in range(n)]
    return min(vals), max(vals)


def _spread_ok(t1: float, t2: float, what: str, problems: list[str]) -> bool:
    if t2 < t1:
        problems.append(f"{what}: clock 2 ({t2:.3f}) is earlier than clock 1 ({t1:.3f}): the reads are out of order")
        return False
    return t2 - t1 <= CLOCK_SPREAD_MAX_S


def check_g18_clocked(samples: list[dict], params: dict, g: dict | None = None) -> dict:
    """samples: [{"t1", "t2", "levels": {material_key: (倍率, 成分の差)}}]（t はワールドの時刻）。各個体の倍率が、時計 1・2 の間の
    ワールドの時刻の式（gimmicks.g18_level）の値の範囲（と LEVEL_TOL・FRAME_SLACK_S の分）の中か。"""
    g = g or gimmicks.g18()
    inds = {r["material_key"]: r for r in g["individuals"]}
    problems, judged = [], []
    seen: dict[str, list[float]] = {}
    for s in samples:
        if not _spread_ok(s["t1"], s["t2"], "G18", problems):
            continue
        judged.append(s["t2"] - s["t1"])
        for key, (lv, hue) in s["levels"].items():
            ind = inds[key]
            lo, hi = _range(lambda t: gimmicks.g18_level(t, ind, params["G18Intensity"], params["G18Speed"]),
                            s["t1"] - FRAME_SLACK_S, s["t2"] + FRAME_SLACK_S)
            seen.setdefault(key, []).append(lv)
            if not (lo - LEVEL_TOL <= lv <= hi + LEVEL_TOL):
                problems.append(f"G18 {ind['instance']}: level {lv:.4f} outside the world-clock formula {lo:.4f}..{hi:.4f} "
                                f"(clock {s['t1']:.3f}..{s['t2']:.3f})")
            if hue > HUE_TOL:
                problems.append(f"G18 {ind['instance']}: the colour channels scale differently ({hue:.4f}); the hue changed")
    if len(judged) < MIN_JUDGED:
        problems.append(f"G18: only {len(judged)} observations had a clock window of {CLOCK_SPREAD_MAX_S} s or less")
    missing = sorted(set(inds) - set(seen))
    if missing:
        problems.append(f"G18: {missing} were never judged")
    return {"samples": len(samples), "judged": len(judged),
            "clock_window_s": [round(min(judged), 4), round(max(judged), 4)] if judged else None,
            "levels_seen": {inds[k]["instance"]: [round(min(v), 4), round(max(v), 4)] for k, v in sorted(seen.items())},
            "problems": problems}


def neighbours(g: dict | None = None) -> list[tuple[str, str]]:
    """各個体と、発光の部品が最も近い別の個体の組（W06 の attach_world）。"""
    g = g or gimmicks.g18()
    rows = {}
    for a in gimmicks._load("assets/manifest/E_forest.json")["assets"]:
        for ind in a.get("glow_individuals") or []:
            rows[ind["instance"]] = [float(c) for c in ind["attach_world"]]
    keys = {r["instance"]: r["material_key"] for r in g["individuals"]}
    out = set()
    for n, p in rows.items():
        other = min((m for m in rows if m != n), key=lambda m: math.dist(p, rows[m]))
        out.add(tuple(sorted((keys[n], keys[other]))))
    return sorted(out)


def check_g18_all(samples: list[dict], params: dict, g: dict | None = None) -> dict:
    """samples: [{"levels": {material_key: (倍率, 成分の差)}}]（14 個を 1 回の observe で読んだ列）。どの個体も強さの範囲の中か。
    近くの組の観察した倍率の差の最大も記録する（判定はしない。同じ出力に結ばれた組は、個体ごとの式で照合する check_g18_clocked が
    見つける。周期の近い組は W06 のデータどおりに揃って見える時間があり、その長さは sync_report がデータから求める）。"""
    g = g or gimmicks.g18()
    inds = {r["material_key"]: r for r in g["individuals"]}
    i_mul = params["G18Intensity"]
    problems = []
    for s in samples:
        for key, (lv, _) in s["levels"].items():
            lo, hi = inds[key]["intensity"]
            if not (lo * i_mul - LEVEL_TOL <= lv <= hi * i_mul + LEVEL_TOL):
                problems.append(f"G18 {inds[key]['instance']}: level {lv:.4f} outside {lo * i_mul:.3f}..{hi * i_mul:.3f}")
    pairs = []
    for a, b in neighbours(g):
        diffs = [abs(s["levels"][a][0] - s["levels"][b][0]) for s in samples if a in s["levels"] and b in s["levels"]]
        pairs.append({"pair": [inds[a]["instance"], inds[b]["instance"]], "max_level_diff": round(max(diffs), 4) if diffs else None})
    return {"samples": len(samples), "neighbour_pairs": pairs, "problems": problems}


def sync_report(window_s: float = 20.0, step_s: float = 0.1, g: dict | None = None) -> list[dict]:
    """W06 のデータ（周期・位相・強さの範囲）から、近くの組ごとに、window_s 秒の間ずっと倍率の差が SYNC_MIN_DIFF 未満（揃って
    見える）になる時間の割合と、その最長の長さ、2 つの位相の差が一巡する時間（うなりの周期）。観察ではない。"""
    g = g or gimmicks.g18()
    inds = {r["material_key"]: r for r in g["individuals"]}
    out = []
    for a, b in neighbours(g):
        ra, rb = inds[a], inds[b]
        df = abs(1.0 / ra["period_s"] - 1.0 / rb["period_s"])
        beat = 1.0 / df if df else math.inf
        span = 2.0 * beat if math.isfinite(beat) else 400.0
        n = int(span / step_s)
        diff = [abs(gimmicks.g18_level(i * step_s, ra) - gimmicks.g18_level(i * step_s, rb)) for i in range(n + int(window_s / step_s))]
        w = int(window_s / step_s)
        synced = [max(diff[i:i + w]) < SYNC_MIN_DIFF for i in range(n)]
        longest = run = 0
        for x in synced:
            run = run + 1 if x else 0
            longest = max(longest, run)
        out.append({"pair": [ra["instance"], rb["instance"]], "periods_s": [ra["period_s"], rb["period_s"]],
                    "beat_period_s": round(beat, 1), "share_synced": round(sum(synced) / n, 3),
                    "longest_synced_s": round(longest * step_s + window_s, 1) if longest else 0.0})
    return out


def check_g18_frozen(levels: dict[str, tuple[float, float]], params: dict, g: dict | None = None) -> dict:
    """時刻を止めた標本（G18Speed = 0）: 各個体の倍率が、式の t によらない値 I (lo + (hi − lo)(0.5 + 0.5 sin(2π φ / T))) か。"""
    g = g or gimmicks.g18()
    problems, rows = [], []
    for r in g["individuals"]:
        want = gimmicks.g18_level(0.0, r, params["G18Intensity"], 0.0)
        got, hue = levels[r["material_key"]]
        rows.append({"instance": r["instance"], "level": round(got, 5), "expected": round(want, 5)})
        if abs(got - want) > FROZEN_LEVEL_TOL or hue > HUE_TOL:
            problems.append(f"G18 frozen {r['instance']}: level {got:.5f} != {want:.5f} (channels differ {hue:.5f})")
    return {"rows": rows, "problems": problems}


def hand_angle_deg(q: dict) -> tuple[float, float]:
    """Pivot の回転（Resonite のローカル）の、+Z まわりの角度（度、0〜360）と、Z 以外の成分の最大。"""
    return math.degrees(2.0 * math.atan2(float(q["z"]), float(q["w"]))) % 360.0, max(abs(float(q["x"])), abs(float(q["y"])))


def bell_angle_deg(q: dict) -> tuple[float, float]:
    """鐘の Pivot の回転の、+X まわりの角度（度、−180〜180）と、X 以外の成分の最大。"""
    a = math.degrees(2.0 * math.atan2(float(q["x"]), float(q["w"])))
    return (a + 180.0) % 360.0 - 180.0, max(abs(float(q["y"])), abs(float(q["z"])))


def clock_tip_local(theta_deg: float) -> tuple[float, float, float]:
    """前から見て 12 時から時計回りに theta の針の先の向き（Resonite の Pivot のローカル）。W06: 正面は Blender の +Y（Resonite の
    +Z）、12 時は +Z_B（+Y_R）、前から見た右（3 時）は −X_B（−X_R）。"""
    t = math.radians(theta_deg)
    return (-math.sin(t), math.cos(t), 0.0)


def _q(d: dict) -> tuple:
    return (float(d["x"]), float(d["y"]), float(d["z"]), float(d["w"]))


def _between_deg(a: float, lo: float, hi: float, tol: float) -> bool:
    """角度 a（度）が lo から hi（lo から正の向きに進んだ範囲。360 未満）の中か（tol の分を許す）。"""
    span = (hi - lo) % 360.0
    d = (a - lo + tol) % 360.0
    return d <= span + 2.0 * tol


def judge_bell(s: dict, swing: float, interval: float, max_deg: float, problems: list[str]) -> tuple[float, bool]:
    """時計で挟んだ 1 回の観察の鐘: 時計の幅の式の範囲の中か（範囲が 0 だけなら真下か）、±max_deg × swing 以内か、X 軸のまわり
    だけか。問題を problems に足し、(角度, 節目の間か) を返す。"""
    ang, off = bell_angle_deg(s["bell"])
    lo, hi = _range(lambda x: gimmicks.g20_bell_angle(x, swing, interval, max_deg), s["s1"] - FRAME_SLACK_S, s["s2"] + FRAME_SLACK_S)
    still = lo == hi == 0.0
    if still:
        if abs(ang) > STILL_TOL_DEG:
            problems.append(f"G20 bell at {ang:.3f} deg between marks (local {s['s1']:.3f} s): it should hang still")
    elif not (lo - BELL_TOL_DEG <= ang <= hi + BELL_TOL_DEG):
        problems.append(f"G20 bell at {ang:.3f} deg outside the formula {lo:.3f}..{hi:.3f} (local {s['s1']:.3f}..{s['s2']:.3f} s)")
    if abs(ang) > max_deg * swing + BELL_TOL_DEG:
        problems.append(f"G20 bell at {ang:.3f} deg is beyond +-{max_deg * swing}")
    if off > AXIS_TOL:
        problems.append(f"G20 bell turns off its hanging axis ({off:.5f})")
    return ang, still


def check_g20_clocked(samples: list[dict], params: dict, g: dict | None = None) -> dict:
    """samples: [{"s1", "s2"（ローカル時刻の秒）, "hour", "minute", "bell"（回転）, "utc_sod", "half"}]。

    針: 角度が時計 1・2 の間のローカル時刻の式の範囲の中か、先の向きが前から見て時計回りか、Z 軸のまわりだけか。
    鐘: 角度が時計の幅の式（gimmicks.g20_bell_angle）の範囲の中か、±max_deg 以内か、X 軸のまわりだけか。
    ローカル時刻: この端末の UTC（壁の時計）との差が 15 分の倍数 ± TZ_RESIDUAL_MAX_S か。"""
    g = g or gimmicks.g20()
    swing, interval, max_deg = params["G20BellSwing"], params["G20BellInterval"], g["bell"]["max_deg"]
    problems, judged, offsets, bell_max, rung, still = [], [], [], 0.0, 0, 0
    hand_err = {"hour": 0.0, "minute": 0.0}
    tip_err = 0.0
    for s in samples:
        if not _spread_ok(s["s1"], s["s2"], "G20", problems):
            continue
        judged.append(s["s2"] - s["s1"])
        for name in ("hour", "minute"):
            period = g["hands"][name]["period_s"]
            ang, off = hand_angle_deg(s[name])
            lo = math.degrees(gimmicks.g20_hand_angle(s["s1"] - FRAME_SLACK_S, period))
            hi = math.degrees(gimmicks.g20_hand_angle(s["s2"] + FRAME_SLACK_S, period))
            mid = math.degrees(gimmicks.g20_hand_angle((s["s1"] + s["s2"]) / 2.0, period))
            hand_err[name] = max(hand_err[name], abs((ang - mid + 180.0) % 360.0 - 180.0))
            if not _between_deg(ang, lo, hi, HAND_TOL_DEG):
                problems.append(f"G20 {name} hand at {ang:.3f} deg is outside the local-time formula {lo:.3f}..{hi:.3f} "
                                f"(local {s['s1']:.3f}..{s['s2']:.3f} s)")
            if off > AXIS_TOL:
                problems.append(f"G20 {name} hand turns off the dial axis ({off:.5f})")
            tip = qrot(_q(s[name]), (0.0, 1.0, 0.0))
            want = clock_tip_local(mid)
            e = math.degrees(math.acos(max(-1.0, min(1.0, sum(a * b for a, b in zip(tip, want))))))
            tip_err = max(tip_err, e)
            if e > TIP_TOL_DEG + (hi - lo) % 360.0:
                problems.append(f"G20 {name} hand tip points {e:.3f} deg away from clockwise-from-the-front at {mid:.3f} deg")
        ang, is_still = judge_bell(s, swing, interval, max_deg, problems)
        bell_max = max(bell_max, abs(ang))
        still, rung = still + is_still, rung + (not is_still)
        if "utc_sod" in s:
            d = ((s["s1"] + s["s2"]) / 2.0 - s["utc_sod"]) % 86400.0
            d = d - 86400.0 if d > 43200.0 else d
            q = round(d / 900.0) * 900.0
            offsets.append((q, d - q, s.get("half", 0.0)))
    if len(judged) < MIN_JUDGED:
        problems.append(f"G20: only {len(judged)} observations had a clock window of {CLOCK_SPREAD_MAX_S} s or less")
    tz = None
    if offsets:
        zones = sorted({o[0] for o in offsets})
        resid = [o[1] for o in offsets]
        tz = {"offset_hours": [z / 3600.0 for z in zones], "residual_s": [round(min(resid), 3), round(max(resid), 3)]}
        if len(zones) != 1:
            problems.append(f"G20: the local time jumps between time-zone offsets {zones}")
        if max(abs(r) - h for r, (_, _, h) in zip(resid, offsets)) > TZ_RESIDUAL_MAX_S:
            problems.append(f"G20: local time is {resid} s off this machine's UTC plus a quarter-hour offset")
    return {"samples": len(samples), "judged": len(judged),
            "clock_window_s": [round(min(judged), 4), round(max(judged), 4)] if judged else None,
            "hand_error_deg": {k: round(v, 4) for k, v in hand_err.items()}, "tip_error_deg": round(tip_err, 4),
            "bell_max_deg": round(bell_max, 3), "bell_rung_samples": rung, "bell_still_samples": still, "local_vs_utc": tz,
            "problems": problems}


def bell_marks(samples: list[dict], params: dict) -> list[float]:
    """観察の範囲の中の、鐘の節目（ローカル時刻の秒が間隔の倍数）。"""
    n = _clamp(params["G20BellInterval"], gimmicks.G20_VARIABLES["G20BellInterval"]["min"],
               gimmicks.G20_VARIABLES["G20BellInterval"]["max"])
    s0, s1 = min(s["s1"] for s in samples), max(s["s2"] for s in samples)
    return [k * n for k in range(int(math.ceil(s0 / n)), int(math.floor(s1 / n)) + 1)]


def check_bell_marks(samples: list[dict], params: dict, min_marks: int = 1) -> dict:
    """節目ごとに、節目から DURATION 秒の間に揺れた観察（角度が 1° を超える）があり、その後と節目の前は真下か。"""
    problems, rows = [], []
    marks = bell_marks(samples, params)
    for m in marks:
        during = [s for s in samples if m <= s["s1"] and s["s2"] <= m + gimmicks.G20_BELL_DURATION_S]
        swung = max((abs(bell_angle_deg(s["bell"])[0]) for s in during), default=0.0)
        rows.append({"mark_local_s": m, "observed_during": len(during), "max_deg": round(swung, 3)})
        if during and params["G20BellSwing"] > 0 and swung < 1.0:
            problems.append(f"G20 bell did not swing after the mark at local {m:.0f} s")
    covered = [r for r in rows if r["observed_during"]]
    if len(covered) < min_marks:
        problems.append(f"G20 bell: only {len(covered)} marks were observed while swinging (needs {min_marks})")
    return {"marks": rows, "problems": problems}


# ---- 構造 --------------------------------------------------------------------------------------------------------------

def latest_export_dir() -> Path:
    key = gimmicks.g18()["district"]
    dirs = [d for d in sorted((PROJECT_ROOT / "exports" / "p2_static").glob(f"{key}-*"))
            if (d / "p2.apply.json").is_file() and (d / "model.apply.json").is_file()]
    return dirs[-1]


def declared_materials(model_doc: dict, p2_doc: dict, g: dict | None = None) -> dict:
    """基準は G18 を足す前の宣言（同じ export の model.apply.json）。キノコの 14 個の _Glow の MeshRenderer は基準で共有の発光の
    材質 1 つだけを指し、G18 の後は個体ごとの材質を指す。ほかの MeshRenderer は基準と同じ並びのまま。"""
    g = g or gimmicks.g18()
    comps: dict[str, tuple[str, dict]] = {}
    stack = [(p2_doc, p2_doc["slot"]["name"])]
    while stack:
        n, path = stack.pop()
        for c in n.get("components", []):
            comps[c["key"]] = (path, c)
        stack.extend((ch, f"{path}/{ch['slot']['name']}") for ch in n.get("children", []))
    baseline = renderer_materials(model_doc)
    glow: dict[str, str] = {}
    for r in g["individuals"]:
        hits = [k for k, (path, c) in comps.items() if c["type"] == "FrooxEngine.MeshRenderer" and path.endswith("/" + r["glow_part"])]
        if len(hits) != 1:
            raise ValueError(f"expected one MeshRenderer on {r['glow_part']}, found {hits}")
        glow[hits[0]] = r["material_key"]
    sources = {tuple(baseline.get(k, [])) for k in glow}
    if len(sources) != 1 or len(next(iter(sources))) != 1:
        raise ValueError(f"the glow MeshRenderers must share one material before G18: {sources}")
    source = next(iter(sources))[0]
    expected = {r: ([glow[r]] if r in glow else ms) for r, ms in baseline.items()}
    after = renderer_materials(p2_doc)
    decl_problems = [f"declaration {r}: {after.get(r)} != expected {ms}" for r, ms in expected.items() if after.get(r) != ms]
    decl_problems += [f"declaration {r}: not in the baseline" for r in after if r not in expected]
    shared = sorted(r for r, ms in baseline.items() if source in ms and r not in glow)
    return {"glow_renderers": glow, "source": source, "source_decl": comps[source][1],
            "material_decls": {k: comps[k][1] for k in glow.values()}, "shared_renderers": shared, "expected": expected,
            "decl_problems": decl_problems}


def check_materials(obs: dict, decl: dict) -> list[str]:
    """obs: {"materials": {renderer: [targetId...]}, "ids": {key: componentId}, "fields": {key: {member: value}}}。"""
    problems: list[str] = list(decl.get("decl_problems", []))
    for r, keys in decl["expected"].items():
        want = [obs["ids"].get(k, f"<unobserved {k}>") for k in keys]
        if obs["materials"].get(r) != want:
            problems.append(f"{r}: materials {obs['materials'].get(r)} != expected {keys}")
    for member, want in decl["source_decl"]["fields"].items():
        if not _close(obs["fields"][decl["source"]][member], want):
            problems.append(f"shared material {decl['source']}.{member} changed: {obs['fields'][decl['source']][member]} != {want}")
    for key, mdecl in decl["material_decls"].items():
        for member, want in mdecl["fields"].items():
            if not _close(obs["fields"][key][member], want):
                problems.append(f"{key}.{member} differs from the shared material: {obs['fields'][key][member]} != {want}")
        if obs["fields"][key].get("Enabled") is not True:
            problems.append(f"{key} is not enabled")
    return problems


def observe_materials(url: str, decl: dict) -> dict:
    sels = [f"$member:{r}.Materials" for r in decl["expected"]]
    members = {decl["source"]: list(decl["source_decl"]["fields"])}
    for k, mdecl in decl["material_decls"].items():
        members[k] = [*mdecl["fields"], "Enabled"]
    for k in sorted({m for ms in decl["expected"].values() for m in ms}):
        members.setdefault(k, ["Enabled"])
    sels += [f"$member:{k}.{m}" for k, ms in members.items() for m in ms]
    vals: dict = {}
    for i in range(0, len(sels), OBSERVE_LIMIT):
        chunk = sels[i:i + OBSERVE_LIMIT]
        vals |= run_json(["resoloop", "observe", *chunk, "--state", str(E_STATE), "--url", url, "--json"])["data"]["values"]
    obs: dict = {"materials": {}, "ids": {}, "fields": {k: {} for k in members}}
    for sel, v in vals.items():
        key, member = sel[len("$member:"):].rsplit(".", 1)
        if member == "Materials":
            obs["materials"][key] = [e.get("targetId") for e in v["member"]["elements"]]
        else:
            obs["ids"][key] = v["componentId"]
            obs["fields"][key][member] = v["member"]["value"]
    return obs


def m07_dial_centre() -> list[float]:
    """M07 の文字盤の中心（時計塔のローカル、Blender。review/M07/checks.json の W09-M07 の実測）。"""
    return [float(c) for c in json.loads((PROJECT_ROOT / "review" / "M07" / "checks.json").read_text(encoding="utf-8"))["dial"]["centre_local_m"]]


def check_tower(e_root: dict, doc: dict, centre: list[float] | None = None) -> dict:
    """時計塔の子孫が宣言と同じパスで同じローカルの変換か（Pivot の回転は比べない）。針の Pivot の軸（Resonite のローカル x・y =
    Blender の x・z）が M07 の文字盤の中心から DIAL_AXIS_TOL_M 以内か。"""
    g = gimmicks.g20()
    centre = centre or m07_dial_centre()
    driven = {h["pivot"] for h in g["hands"].values()} | {g["bell"]["pivot"]}
    problems, rows = [], []
    decl = _find_decl(doc, g["asset_id"])
    live = _child(e_root, g["asset_id"])
    if decl is None or live is None:
        return {"rows": rows, "problems": [f"{g['asset_id']}: missing"]}

    def compare(path: tuple, lv: dict | None, slot: dict) -> None:
        if lv is None:
            problems.append(f"{'/'.join(path)}: missing at the declared path")
            return
        if path[-1] in driven:
            want = {"position": slot.get("position") or [0, 0, 0], "scale": slot.get("scale") or [1, 1, 1]}
            err = max(abs(float(lv[f][k]) - v) for f in want for k, v in zip("xyz", want[f]))
        else:
            err = _same_local(lv, slot)
        rows.append({"slot": "/".join(path), "local_error": round(err, 6)})
        if err > LOCAL_TOL:
            problems.append(f"{'/'.join(path)}: local transform differs from the declaration ({err})")

    compare((g["asset_id"],), live, decl["slot"])
    for path, node in _decl_paths(decl):
        lv = live
        for n in path:
            lv = _child(lv, n)
        compare((g["asset_id"], *path), lv, node["slot"])
    axis = {}
    for name, h in g["hands"].items():
        lv = _child(live, h["pivot"])
        if lv is None:
            continue
        dx, dz = float(lv["position"]["x"]) - centre[0], float(lv["position"]["y"]) - centre[2]
        axis[name] = round(math.hypot(dx, dz), 5)
        if axis[name] > DIAL_AXIS_TOL_M:
            problems.append(f"G20 {name} hand axis is {axis[name]:.4f} m off the M07 dial centre")
    return {"rows": rows, "dial_axis_offset_m": axis, "problems": problems}


def e_hierarchy(url: str, depth: int = 4) -> dict:
    return run_json(["resoloop", "hierarchy", "--under", f"{gimmicks.P2_ROOT}/{gimmicks.g20()['district']}", "--depth", str(depth),
                     "--url", url, "--json"])


def check_relays(url: str, keys: dict[str, str]) -> list[str]:
    """中継の Drives が Pivot の Rotation を指し、有効か。"""
    problems = []
    for part, k in keys.items():
        sel = f"$member:{district.relay_key(k, 'Rotation', 'g20')}"
        data = run_json(["resoloop", "observe", f"{sel}.Drives", f"{sel}.Enabled", "--state", str(E_STATE), "--url", url,
                         "--json"])["data"]["values"]
        members = run_json(["resoloop", "inspect", f"$slot:{k}", "--state", str(E_STATE), "--members", "--url", url, "--json"])["data"]["members"]
        if data[f"{sel}.Enabled"]["member"]["value"] is not True:
            problems.append(f"{part}: relay is disabled")
        if [e.get("targetId") for e in data[f"{sel}.Drives"]["member"]["elements"]] != [members["Rotation"]["id"]]:
            problems.append(f"{part}: relay does not drive the Slot Rotation")
    return problems


# ---- 包絡（バンドルのメッシュから。観察ではない） -----------------------------------------------------------------------

def envelopes(doc: dict | None = None) -> dict:
    """時針・分針を 1 周（5° ごと）、鐘を ±max_deg（1° ごと）回した点（Blender の世界座標）が、W06 の包絡の中、歩く高さより上、
    E の除外範囲・鑑賞位置の外か。"""
    g = gimmicks.g20()
    doc = doc or json.loads((latest_export_dir() / "p2.apply.json").read_text(encoding="utf-8"))
    bundle = _bundle(g["district"])
    tower = _find_decl(doc, g["asset_id"])
    tq = tuple(tower["slot"].get("rotation") or (0, 0, 0, 1))
    tp = tower["slot"].get("position") or (0, 0, 0)
    layout = json.loads((PROJECT_ROOT / "layout" / "areas" / f"{g['district']}.json").read_text(encoding="utf-8"))
    env_w06 = {e["part_name"]: e["envelope_world"] for e in layout["motion_envelopes"] if e["gimmick_id"] == "G20"}
    zones = [(e["zone_id"], e["bounds"]) for e in layout["Exclusions"]] + [(v["id"], v["bounds"]) for v in layout["viewpoints"]]
    walk = float(layout["walk_clearance_z_m"])
    parts = {g["hands"]["hour"]["pivot"]: ("Z", range(0, 360, 5)), g["hands"]["minute"]["pivot"]: ("Z", range(0, 360, 5)),
             g["bell"]["pivot"]: ("X", range(-int(g["bell"]["max_deg"]), int(g["bell"]["max_deg"]) + 1))}
    out: dict = {}
    for part, (axis, angles) in parts.items():
        node = next(c for c in tower.get("children", []) if c["slot"]["name"] == part)
        pq = tuple(node["slot"].get("rotation") or (0, 0, 0, 1))
        pp = node["slot"].get("position") or (0, 0, 0)
        local = _local_points(bundle, doc, node, (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0))
        lo, hi = [math.inf] * 3, [-math.inf] * 3
        in_zone: dict[str, int] = {}
        for a in angles:
            h = math.radians(a) / 2.0
            rq = (0.0, 0.0, math.sin(h), math.cos(h)) if axis == "Z" else (math.sin(h), 0.0, 0.0, math.cos(h))
            q = qmul(tq, qmul(pq, rq))
            ppw = qrot(tq, pp)
            for v in local:
                r = qrot(q, v)
                w = (tp[0] + ppw[0] + r[0], tp[2] + ppw[2] + r[2], tp[1] + ppw[1] + r[1])   # Blender の世界座標
                for k in range(3):
                    lo[k], hi[k] = min(lo[k], w[k]), max(hi[k], w[k])
                for zid, b in zones:
                    if all(b["min"][k] <= w[k] <= b["max"][k] for k in range(3)):
                        in_zone[zid] = in_zone.get(zid, 0) + 1
        w06 = env_w06.get(part)
        outside = None
        if w06:
            outside = round(max(max(w06["min"][k] - lo[k], hi[k] - w06["max"][k]) for k in range(3)), 4)
        out[part] = {"points": len(local), "box_world": {"min": [round(x, 4) for x in lo], "max": [round(x, 4) for x in hi]},
                     "w06_envelope": w06, "beyond_w06_m": outside, "lowest_above_walk_m": round(lo[2] - walk, 4),
                     "points_in_zones": in_zone}
    return {"walk_clearance_z_m": walk, "parts": out}


def envelope_problems(env: dict) -> list[str]:
    problems = []
    for part, r in env["parts"].items():
        if r["beyond_w06_m"] is None or r["beyond_w06_m"] > ENVELOPE_SLACK_M:
            problems.append(f"G20 {part}: the swept points leave the W06 envelope by {r['beyond_w06_m']} m")
        if r["lowest_above_walk_m"] <= 0:
            problems.append(f"G20 {part}: the swept points come down to walking height ({r['lowest_above_walk_m']} m)")
        if r["points_in_zones"]:
            problems.append(f"G20 {part}: the swept points enter {r['points_in_zones']}")
    return problems


# ---- 観察 ------------------------------------------------------------------------------------------------------------

def observe_params(url: str) -> dict:
    sels = [f"$member:{s['key']}.Value" for s in variables().values()]
    data = run_json(["resoloop", "observe", *sels, "--state", str(P3_STATE), "--url", url, "--json"])["data"]["values"]
    return {n: float(data[f"$member:{s['key']}.Value"]["member"]["value"]) for n, s in variables().items()}


def _ids(url: str) -> dict[str, str]:
    return {n: component_id(f"$member:{s['key']}.Value", P3_STATE, url) for n, s in variables().items()}


def timed_span(args: list[str]) -> tuple[float, float, dict]:
    t0 = time.time()
    data = run_json(args)
    t1 = time.time()
    return (t0 + t1) / 2.0, (t1 - t0) / 2.0, data


def _utc_sod(t: float) -> float:
    return t % 86400.0


def clock_sels() -> list[str]:
    return [f"$member:{k}.Value" for k in gimmicks.G20_CLOCK_KEYS]


def _observe(url: str, middle: list[str], raw: list, label: str) -> tuple[dict, dict]:
    """「時計 1 → middle → 時計 2」を 1 回の observe で読む。"""
    ck1, ck2 = clock_sels()
    t, half, obs = timed_span(["resoloop", "observe", ck1, *middle, ck2, "--state", str(E_STATE), "--url", url, "--json"])
    raw.append({"kind": label, "t": t, "half": half, "data": obs})
    vals = obs["data"]["values"]
    c1, c2 = vals[ck1]["member"]["value"], vals[ck2]["member"]["value"]
    clocks = {"t1": float(c1["x"]), "t2": float(c2["x"]), "s1": float(c1["y"]), "s2": float(c2["y"]),
              "utc_sod": _utc_sod(t), "half": half}
    return clocks, vals


def g18_series(url: str, seconds: float, raw: list, e0: list[float], per: int = 2) -> list[dict]:
    """per 個ずつ「時計 1 → 発光 → 時計 2」を seconds 秒の間、個体を順に回して読む。"""
    keys = [r["material_key"] for r in gimmicks.g18()["individuals"]]
    out, i = [], 0
    t_end = time.time() + seconds
    while time.time() < t_end or i % len(keys):
        group = [keys[(i + j) % len(keys)] for j in range(per)]
        i += per
        sels = [f"$member:{k}.EmissiveColor" for k in group]
        clocks, vals = _observe(url, sels, raw, "g18_clocked")
        out.append({**clocks, "levels": {k: level_of(vals[s]["member"]["value"], e0) for k, s in zip(group, sels)}})
    return out


def g18_all_series(url: str, seconds: float, raw: list, e0: list[float]) -> list[dict]:
    keys = [r["material_key"] for r in gimmicks.g18()["individuals"]]
    sels = [f"$member:{k}.EmissiveColor" for k in keys]
    out = []
    t_end = time.time() + seconds
    while time.time() < t_end:
        t, half, obs = timed_span(["resoloop", "observe", *sels, "--state", str(E_STATE), "--url", url, "--json"])
        raw.append({"kind": "g18_all", "t": t, "half": half, "data": obs})
        vals = obs["data"]["values"]
        out.append({"t": t, "levels": {k: level_of(vals[s]["member"]["value"], e0) for k, s in zip(keys, sels)}})
    return out


def g20_sels(keys: dict[str, str]) -> dict[str, str]:
    g = gimmicks.g20()
    return {"hour": f"$member:{district.relay_key(keys[g['hands']['hour']['pivot']], 'Rotation', 'g20')}.Value",
            "minute": f"$member:{district.relay_key(keys[g['hands']['minute']['pivot']], 'Rotation', 'g20')}.Value",
            "bell": f"$member:{district.relay_key(keys[g['bell']['pivot']], 'Rotation', 'g20')}.Value"}


def g20_series(url: str, seconds: float, raw: list, keys: dict[str, str], names=("hour", "minute", "bell")) -> list[dict]:
    sels = g20_sels(keys)
    out = []
    t_end = time.time() + seconds
    while time.time() < t_end:
        clocks, vals = _observe(url, [sels[n] for n in names], raw, "g20_clocked")
        out.append({**clocks, **{n: vals[sels[n]]["member"]["value"] for n in names}})
    return out


def frozen_g18(url: str, raw: list, e0: list[float], ids: dict[str, str], intensity: float | None = None,
               speed: str = "0") -> dict:
    """G18Speed = speed（既定 0。範囲の外の値は 0 に収まる）と G18Intensity にして 14 個の発光を読み、時刻を止めた式と照合する。
    値は呼び出し側が戻す。"""
    set_member(ids["G18Speed"], "Value", speed, url)
    if intensity is not None:
        set_member(ids["G18Intensity"], "Value", str(intensity), url)
    time.sleep(1.0)
    params = params_of(observe_params(url))
    keys = [r["material_key"] for r in gimmicks.g18()["individuals"]]
    sels = [f"$member:{k}.EmissiveColor" for k in keys]
    _, _, obs = timed_span(["resoloop", "observe", *sels, "--state", str(E_STATE), "--url", url, "--json"])
    raw.append({"kind": "g18_frozen", "params": params, "data": obs})
    levels = {k: level_of(obs["data"]["values"][s]["member"]["value"], e0) for k, s in zip(keys, sels)}
    res = check_g18_frozen(levels, params)
    return {"params": params, "levels": {k: round(v[0], 6) for k, v in levels.items()}, **res}


def restore(url: str, ids: dict[str, str], before: dict) -> list[str]:
    for n, v in before.items():
        set_member(ids[n], "Value", repr(float(v)), url)
    after = observe_params(url)
    return [] if after == before else [f"variables not restored: {after} != {before}"]


def structure(url: str, decl: dict, doc: dict, raw: list, label: str) -> dict:
    hier = e_hierarchy(url)
    raw.append({"kind": f"hierarchy_{label}", "data": hier})
    tower = check_tower(hier["data"], doc)
    mats = check_materials(observe_materials(url, decl), decl)
    return {"tower": {"rows": len(tower["rows"]), "dial_axis_offset_m": tower["dial_axis_offset_m"]},
            "problems": tower["problems"] + mats}


def observe_window(url: str, g18_seconds: float, all_seconds: float, g20_seconds: float, raw: list) -> dict:
    ed = latest_export_dir()
    doc = json.loads((ed / "p2.apply.json").read_text(encoding="utf-8"))
    decl = declared_materials(json.loads((ed / "model.apply.json").read_text(encoding="utf-8")), doc)
    e0 = e_rest(doc)["glow_linear"]
    keys = e_keys(STATE_DIR)
    ids = _ids(url)
    before = observe_params(url)
    params = params_of(before)
    window: dict = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "params": before, "problems": []}
    window["structure_start"] = structure(url, decl, doc, raw, "start")
    window["relay_problems"] = check_relays(url, keys)
    try:
        window["frozen_probe"] = frozen_g18(url, raw, e0, ids)
    finally:
        window["frozen_probe_restore"] = restore(url, ids, before)
    window["g18_clocked"] = check_g18_clocked(g18_series(url, g18_seconds, raw, e0), params)
    window["g18_all"] = check_g18_all(g18_all_series(url, all_seconds, raw, e0), params)
    g20 = g20_series(url, g20_seconds, raw, keys)
    window["g20_clocked"] = check_g20_clocked(g20, params)
    window["structure_end"] = structure(url, decl, doc, raw, "end")
    for k in ("structure_start", "frozen_probe", "g18_clocked", "g18_all", "g20_clocked", "structure_end"):
        window["problems"] += window[k]["problems"]
    window["problems"] += window["relay_problems"] + window["frozen_probe_restore"]
    window["ok"] = not window["problems"]
    return window


def check_drift(probes: list[dict]) -> dict:
    """窓ごとの時刻を止めた標本（G18）を最初の窓と比べる（式は t によらないので、同じ値のはず）。"""
    problems, rows = [], []
    if len(probes) < 2:
        return {"rows": rows, "problems": ["drift: needs two windows"]}
    for i, p in enumerate(probes[1:], start=2):
        d = max(abs(p["levels"][k] - probes[0]["levels"][k]) for k in p["levels"])
        rows.append({"window": i, "max_level_diff": round(d, 6)})
        if d > FROZEN_LEVEL_TOL:
            problems.append(f"drift: the frozen G18 levels differ by {d:.6f} in window {i}")
    return {"rows": rows, "problems": problems}


# ---- 外から変えられる値の確認 -------------------------------------------------------------------------------------------

def param_check(url: str, raw: list) -> dict:
    ed = latest_export_dir()
    doc = json.loads((ed / "p2.apply.json").read_text(encoding="utf-8"))
    e0 = e_rest(doc)["glow_linear"]
    keys = e_keys(STATE_DIR)
    ids = _ids(url)
    before = observe_params(url)
    out: dict = {"before": before, "cases": [], "problems": []}

    def case(label: str, res: dict) -> None:
        out["cases"].append({"case": label, **res})
        out["problems"] += [f"{label}: {p}" for p in res["problems"]]

    try:
        for i in (0.5, 3.0, -1.0):
            res = frozen_g18(url, raw, e0, ids, intensity=i)
            case(f"G18Intensity {i} (G18Speed 0)", {"params": res["params"], "problems": res["problems"],
                                                     "levels_range": [round(min(res["levels"].values()), 5), round(max(res["levels"].values()), 5)]})
        set_member(ids["G18Intensity"], "Value", repr(before["G18Intensity"]), url)
        for sp, secs in ((SLOW_SPEED, 25.0), (2.0, 15.0), (-1.0, 0.0)):
            set_member(ids["G18Speed"], "Value", str(sp), url)
            time.sleep(1.0)
            params = params_of(observe_params(url))
            if secs:
                res = check_g18_clocked(g18_series(url, secs, raw, e0, per=1), params)
                case(f"G18Speed {sp} (clocked)", {"params": params, **{k: res[k] for k in ("judged", "clock_window_s", "problems")}})
            else:
                res = frozen_g18(url, raw, e0, ids, speed=str(sp))
                case(f"G18Speed {sp} (clamped to 0, frozen)", {"params": res["params"], "problems": res["problems"]})
        set_member(ids["G18Speed"], "Value", repr(before["G18Speed"]), url)
        # 鐘: 間隔を 20 秒にして、節目ごとの揺れと、節目の間の静止を見る
        for swing, interval, secs, marks in ((3.0, 20.0, 45.0, 2), (0.5, 20.0, 25.0, 1), (1.0, 5.0, 25.0, 1)):
            set_member(ids["G20BellSwing"], "Value", str(swing), url)
            set_member(ids["G20BellInterval"], "Value", str(interval), url)
            time.sleep(1.0)
            params = params_of(observe_params(url))
            series = g20_series(url, secs, raw, keys, names=("bell",))
            res = check_bell_only(series, params)
            res_m = check_bell_marks(series, params, marks)
            case(f"G20BellSwing {swing}, G20BellInterval {interval}",
                 {"params": params, "judged": res["judged"], "bell_max_deg": res["bell_max_deg"], "marks": res_m["marks"],
                  "problems": res["problems"] + res_m["problems"]})
    finally:
        out["restore_problems"] = restore(url, ids, before)
    out["problems"] += out["restore_problems"]
    out["ok"] = not out["problems"]
    return out


def check_bell_only(samples: list[dict], params: dict) -> dict:
    """鐘だけを読んだ観察（時計 1 → 鐘 → 時計 2）の照合。check_g20_clocked の鐘の項目と同じ判定。"""
    g = gimmicks.g20()
    problems, judged, mx = [], 0, 0.0
    for s in samples:
        if not _spread_ok(s["s1"], s["s2"], "G20", problems):
            continue
        judged += 1
        ang, _ = judge_bell(s, params["G20BellSwing"], params["G20BellInterval"], g["bell"]["max_deg"], problems)
        mx = max(mx, abs(ang))
    if judged < MIN_JUDGED:
        problems.append(f"G20 bell: only {judged} observations had a clock window of {CLOCK_SPREAD_MAX_S} s or less")
    return {"judged": judged, "bell_max_deg": round(mx, 3), "problems": problems}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", required=True)
    ap.add_argument("--raw-out", type=Path, required=True, help="生の観察の保存先（Git の外。ResoniteLink の ID を含む）")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--windows", type=int, default=1)
    ap.add_argument("--gap", type=float, default=300.0, help="窓と窓の間の秒数")
    ap.add_argument("--g18-duration", type=float, default=30.0, help="時計で挟んだ G18 の観察の秒数")
    ap.add_argument("--all-duration", type=float, default=20.0, help="14 個を続けて読む秒数")
    ap.add_argument("--g20-duration", type=float, default=30.0, help="時計で挟んだ G20 の観察の秒数")
    ap.add_argument("--param-check", action="store_true")
    args = ap.parse_args(argv)
    if args.raw_out.exists():
        raise SystemExit(f"{args.raw_out} already exists")
    raw: list = []
    if args.param_check:
        result = param_check(args.url, raw)
    else:
        wins = []
        for i in range(args.windows):
            if i:
                time.sleep(args.gap)
            wins.append(observe_window(args.url, args.g18_duration, args.all_duration, args.g20_duration, raw))
        env = envelopes()
        drift = check_drift([w["frozen_probe"] for w in wins])
        result = {"windows": wins, "gap_s": args.gap if args.windows > 1 else None, "drift": drift, "envelopes": env,
                  "g18_neighbour_sync": sync_report(),
                  "envelope_problems": envelope_problems(env),
                  "tolerances": {"level": LEVEL_TOL, "hue": HUE_TOL, "frozen_level": FROZEN_LEVEL_TOL, "frame_slack_s": FRAME_SLACK_S,
                                 "clock_spread_max_s": CLOCK_SPREAD_MAX_S, "min_judged": MIN_JUDGED, "hand_deg": HAND_TOL_DEG,
                                 "tip_deg": TIP_TOL_DEG, "axis": AXIS_TOL, "bell_deg": BELL_TOL_DEG, "still_deg": STILL_TOL_DEG,
                                 "dial_axis_m": DIAL_AXIS_TOL_M, "tz_residual_s": TZ_RESIDUAL_MAX_S, "sync_min_diff": SYNC_MIN_DIFF,
                                 "local": LOCAL_TOL, "envelope_m": ENVELOPE_SLACK_M}}
        drift_problems = drift["problems"] if args.windows > 1 else []
        result["ok"] = all(w["ok"] for w in wins) and not result["envelope_problems"] and not drift_problems
    args.raw_out.parent.mkdir(parents=True, exist_ok=True)
    args.raw_out.write_text(json.dumps(raw, ensure_ascii=False) + "\n", encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {k: v for k, v in result.items() if k not in ("windows", "cases", "envelopes")}
    if args.param_check:
        summary["cases"] = [{k: c[k] for k in ("case", "problems")} for c in result["cases"]]
    else:
        summary["windows"] = [{"ok": w["ok"], "g18": {k: w["g18_clocked"][k] for k in ("judged", "clock_window_s")},
                               "g20": {k: w["g20_clocked"][k] for k in ("judged", "hand_error_deg", "tip_error_deg", "bell_max_deg",
                                                                         "local_vs_utc")},
                               "problems": w["problems"][:10]} for w in result["windows"]]
    print(json.dumps(summary, ensure_ascii=False, indent=1, default=str)[:6000])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
