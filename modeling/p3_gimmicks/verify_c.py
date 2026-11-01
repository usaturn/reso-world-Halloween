"""W10-C: Resonite で動いている G09（大釜の攪拌と泡・煙）と G11（魔女の巡回）を、時間を空けた観察から検査する。

実行（プロジェクトのディレクトリ。対象のワールドを Resonite の前面に出しておく。背面では駆動が進まない）:
    uv run python modeling/p3_gimmicks/verify_c.py --url ws://localhost:<PORT>/ \\
        --raw-out <Git の外の JSON> --output review/p3_gimmicks/g09_g11_live_checks.json [--windows 2 --gap 300]
    # 外から変えられる値の確認（値を変えて測り、元に戻す。ワールドに書く）
    uv run python modeling/p3_gimmicks/verify_c.py --url ... --raw-out ... --output review/p3_gimmicks/g09_g11_param_checks.json --param-check

観察（窓ごと。--windows の数だけ、--gap 秒あけて繰り返す）
- 構造: 窓の最初と最後に resoloop hierarchy で、魔女の仮モデルの下の M08（素材の宣言の root とその子孫）、大釜・巡回路の子孫が
  宣言と同じパスで同じローカルの変換か（駆動される項目だけは比べない）。中継の Drives が Slot のメンバーを指し有効か。液面の
  MeshRenderer の材質が [専用の材質, マゼンタ] で、ほかの物の材質は元のままか
- 時刻を止めた標本: G09StirFrequency・G11Frequency を 0 にし、位置のずらし（G09StirPhase 0.125、G11Phase 0.25 = 巡回の点 2）
  で Slot そのものの姿勢を読み、式と巡回の点に照合してから値を戻す。窓の間で比べる（同じ位相の位置の差 1 cm 以内）
- 攪拌棒だけを続けて観察（1 回 約 1.5 秒）: 回転の形（Y まわり × ローカル Z まわり）、揺れが W sin 2φ の式どおりか、速さ
- 全部の駆動の値を続けて観察: 魔女・CarrierPivot が経路の上（1 cm 以内）、高さ 9.8〜10.5 m、向きが経路の接線（読み取りの時刻の
  ずれの分を許す）、隣の観察の間に進んだ向きと正面の向きの差、θ の速さ、液面の色・泡と煙の量と色が HMC_P3 の値どおりか
- 窓の間の時刻の基準: 各窓の θ − ω t（t は壁の時計）の平均が窓の間で合うか（θ が時刻から決まり、漂わない）

検査（--param-check）
- 時刻を止めた標本: G11Phase k/8（k = 0〜7）で魔女と CarrierPivot が巡回の点 k に（配置データの値と 1 mm 以内）、向きが式の
  接線に。G09StirPhase 0・0.125・0.3・0.6・0.9 で攪拌棒の回転が式どおり。中継の値と Slot そのものの両方
- 範囲の外の値: G09StirPhase 1.5 → 1（収めないと 180° 回った姿勢）、G11Phase 1.5 → 1（収めないと巡回の点 4）、速さ -1 → 0、
  G09Bubbles 5 → 2・-1 → 0、G09Smoke -1 → 0・5 → 2
- 液面の色: I02 の Magenta（#F53DC7）にすると、液面の AlbedoColor・EmissiveColor と泡・煙の色が式どおりに変わるか
- ゆっくりの時刻（G09StirFrequency・G11Frequency = 0.004）で 20 秒の間に φ・θ が時刻どおり進むか
- どれも元に戻し、戻ったかを確かめる
- 包絡（バンドルのメッシュから。観察ではない）: 攪拌棒が回り揺れても大釜の縁の高さより下で液面の半径の内側、大釜の底より上に
  あるか。魔女（M08）が巡回の全周で W04 の上空の通り道 EX_C_SkyPatrolCorridor の下端より上、M04 の外接箱から 1 m 以上離れるか
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
from modeling.p3_gimmicks.build_content import c_keys  # noqa: E402
from modeling.p3_gimmicks.rest_pose import latest_declaration  # noqa: E402
from modeling.p3_gimmicks.verify_live import (  # noqa: E402
    STATE_DIR, _bundle, _child, _decl_paths, _find_decl, _find_live, _local_points, _same_local, component_id, fit_speed,
    q_of, qmul, qrot, run_json, set_member, timed, wrap_deg)

C_STATE = STATE_DIR / "p2_C_candy.json"
P3_STATE = STATE_DIR / "p3_gimmicks.json"
M08_STATE = STATE_DIR / "p2m_M08.json"
PATH_TOL_M = 0.01            # 魔女・CarrierPivot の位置と経路の距離
ALT_TOL_M = 0.001
HEADING_TOL_DEG = 3.0        # 動いている間の向き（位置と回転は別の中継で、1 回の observe の中で読む時刻がずれる。θ は 8°/s）
TRAVEL_TOL_DEG = 8.0         # 隣の観察の間に進んだ向き（弦）と、2 回の正面の向きの平均の差
OFF_AXIS_TOL = 1e-3
ROD_FORM_TOL = 1e-3          # 攪拌棒の四元数が Y まわり × ローカル Z まわりの形か（|x w − y z|）
ROD_TILT_TOL_DEG = 0.1       # 揺れと W sin 2φ の差（1 つのメンバーなので同じ時刻の値）
FROZEN_POS_TOL_M = 0.001
FROZEN_DEG_TOL = 0.05
FROZEN_Q_TOL = 1e-4
COLOR_TOL = 1e-3
SPEED_TOL = 0.05
MAX_STEP_DEG = 150.0         # 隣の観察の間に進み得る角度の上限（連続にする前提は ±180° 未満）
CLOCK_FREQUENCY = 0.004      # ゆっくりの時刻（Hz）。φ・θ は 1.44°/s
CLOCK_WAIT_S = 20.0
CLOCK_TOL_DEG = 1.0
CLOCK_OFFSET_TOL_DEG = 6.0   # 窓の間の θ − ω t の差（observe の時刻の見積もりのずれ ±0.5 秒 × 8°/s の分）
# 各観察と、角度を連続にして当てはめた直線の差（GPT のレビューの指摘 M-3）。observe の時刻の見積もりのずれの分を許す
# （2026-11-01 の実測で攪拌棒 ±5.1°（60°/s）、巡回 ±1.2°（8°/s））
RESIDUAL_TOL_DEG = {"rod": 15.0, "patrol": 4.0}
CARRIER_PHASE_TOL_DEG = 4.0  # 同じ観察の中の魔女と CarrierPivot の θ の差（実測 1.6〜2.4°。CarrierPivot を後に読む）
DRIFT_TOL_M = 0.01
DRIFT_TOL_DEG = 0.5
LOCAL_TOL = 1e-4
MAGENTA = [0.9607843, 0.2392157, 0.7803922, 1.0]   # I02 の color_presets の MagentaElixir #F53DC7（sRGB）
ROD_ENVELOPE = {"rim_top_m": 1.28, "liquid_radius_m": 0.70, "bottom_m": 0.20}   # C_candy/build.py の大釜（縁の上面・液面の半径・腹の底）
M04_CLEARANCE_M = 1.0


def _clamp(x: float, lo: float, hi: float) -> float:
    return min(max(float(x), lo), hi)


def variables() -> dict[str, dict]:
    return {**gimmicks.G09_VARIABLES, **gimmicks.G11_VARIABLES}


def params_of(raw: dict) -> dict:
    """観察した値を、モジュールと同じ範囲に収めた値にする（色はそのまま）。"""
    v = variables()
    out = {n: _clamp(raw[n], v[n]["min"], v[n]["max"]) for n in v}
    out[gimmicks.G09_COLOR_VARIABLE] = raw[gimmicks.G09_COLOR_VARIABLE]
    return out


def relay_sel(slot_key: str, member: str, gid: str) -> str:
    return f"$member:{district.relay_key(slot_key, member, gid)}.Value"


def selectors(keys: dict[str, str]) -> dict[str, str]:
    g9, g11 = gimmicks.g09(), gimmicks.g11()
    sels = {"rod": relay_sel(keys[g9["stir_pivot"]], "Rotation", "g09"),
            "witch_pos": relay_sel(keys[g11["rider"]], "Position", "g11"),
            "witch_rot": relay_sel(keys[g11["rider"]], "Rotation", "g11"),
            "carrier_pos": relay_sel(keys[g11["carrier"]], "Position", "g11"),
            "carrier_rot": relay_sel(keys[g11["carrier"]], "Rotation", "g11"),
            "albedo": f"$member:{gimmicks.G09_LIQUID_MATERIAL_KEY}.AlbedoColor",
            "emissive": f"$member:{gimmicks.G09_LIQUID_MATERIAL_KEY}.EmissiveColor"}
    for kind, p in gimmicks.G09_PARTICLES.items():
        sels[f"{kind}_rate"] = f"$member:{p['prefix']}emi.Rate"
        sels[f"{kind}_start"] = f"$member:{p['prefix']}col.StartColor"
        sels[f"{kind}_end"] = f"$member:{p['prefix']}col.EndColor"
    return sels


def _rgba(d) -> list[float]:
    if isinstance(d, dict):
        return [float(d[k]) for k in "rgba"]
    return [float(x) for x in d]


# ---- 式 ----------------------------------------------------------------------------------------------------------------

def rod_expected_q(phi: float, wobble_deg: float) -> tuple:
    """攪拌の角度 φ（ラジアン、Blender の +Z まわり）の攪拌棒の回転（Resonite）。Y(−φ) × Z(w)、w = W sin 2φ。"""
    half = math.radians(wobble_deg) / 2.0 * math.sin(2.0 * phi)
    sy, cy = -math.sin(phi / 2.0), math.cos(phi / 2.0)
    sz, cz = math.sin(half), math.cos(half)
    return (sy * sz, sy * cz, cy * sz, cy * cz)


def rod_decompose(q) -> dict:
    """攪拌棒の回転を、攪拌の角度 φ（度、0〜360）・揺れ（度）・形の残差に分ける（rod_expected_q の逆）。"""
    x, y, z, w = q
    phi = (-2.0 * math.degrees(math.atan2(y, w))) % 360.0
    tilt = 2.0 * math.degrees(math.atan2(x * y + z * w, y * y + w * w))
    return {"phi_deg": phi, "tilt_deg": tilt, "form_residual": abs(x * w - y * z)}


def q_close(a, b) -> float:
    """2 つの四元数の差（符号の違いは同じ回転）。"""
    d1 = max(abs(p - q) for p, q in zip(a, b))
    d2 = max(abs(p + q) for p, q in zip(a, b))
    return min(d1, d2)


def r2b(p) -> list[float]:
    """Resonite の (x, y, z) を Blender の (x, z, y) にする（逆も同じ入れ替え）。"""
    return [float(p[0]), float(p[2]), float(p[1])]


def nearest_theta(pb: list[float], g: dict) -> float:
    """Blender の水平の位置に最も近い経路の θ（ラジアン、0〜2π）。粗く探してから細かく詰める。"""
    c = g["coefficients"]

    def d2(t):
        return (gimmicks.trig_eval(c[0], t) - pb[0]) ** 2 + (gimmicks.trig_eval(c[1], t) - pb[1]) ** 2

    n = 720
    best = min(range(n), key=lambda k: d2(2 * math.pi * k / n))
    lo, hi = 2 * math.pi * (best - 1) / n, 2 * math.pi * (best + 1) / n
    for _ in range(60):
        m1, m2 = lo + (hi - lo) / 3.0, hi - (hi - lo) / 3.0
        if d2(m1) < d2(m2):
            hi = m2
        else:
            lo = m1
    return ((lo + hi) / 2.0) % (2 * math.pi)


def heading_deg(q) -> tuple[float, float]:
    """Y まわりの回転の角度（Resonite、度）と、Y 以外の成分の大きさ。"""
    x, y, z, w = q
    if w < 0:
        x, y, z, w = -x, -y, -z, -w
    return math.degrees(2.0 * math.atan2(y, w)), max(abs(x), abs(z))


def rider_pose(pos: dict, rot: dict, g: dict, offset: list[float] | None = None) -> dict:
    """魔女（または CarrierPivot。offset は親の巡回路の root の Blender の原点）の位置・回転を、経路の θ と照合する。"""
    p = [float(pos[k]) for k in "xyz"]
    pb = r2b(p)
    if offset:
        pb = [pb[i] + offset[i] for i in range(3)]
    th = nearest_theta(pb, g)
    want, psi = gimmicks.g11_pose(th, g)
    head, off = heading_deg(q_of(rot))
    return {"theta_deg": math.degrees(th), "path_error_m": math.dist(pb, want), "altitude_m": pb[2],
            "heading_deg": head, "heading_error_deg": wrap_deg(head - math.degrees(psi)), "off_axis": off, "pos_b": pb,
            "forward": list(qrot(q_of(rot), (0.0, 0.0, 1.0)))}


def expected_effects(params: dict, gain: float) -> dict[str, list[float] | float]:
    """液面の色と泡・煙の量・色の、式の値（sRGB の値の成分の積。α は決めた値）。"""
    col = _rgba(params[gimmicks.G09_COLOR_VARIABLE])
    out: dict = {"albedo": col[:3] + [1.0], "emissive": [c * gain for c in col[:3]] + [1.0]}
    amounts = {"bubbles": params["G09Bubbles"], "smoke": params["G09Smoke"]}
    for kind, p in gimmicks.G09_PARTICLES.items():
        out[f"{kind}_rate"] = p["rate"] * amounts[kind]
        out[f"{kind}_start"] = [c * p["color_gain"] for c in col[:3]] + [p["start_alpha"]]
        out[f"{kind}_end"] = [c * p["color_gain"] for c in col[:3]] + [p["end_alpha"]]
    return out


def check_effects(values: dict, params: dict, gain: float) -> list[str]:
    """液面の材質・泡と煙の Rate・色が式どおりか（values は selectors の名前 → 観察の値）。"""
    problems = []
    for name, want in expected_effects(params, gain).items():
        got = values[name]
        if isinstance(want, float):
            if abs(float(got) - want) > COLOR_TOL:
                problems.append(f"{name}: {got} != {want:.4f}")
            continue
        g = _rgba(got)
        if max(abs(a - b) for a, b in zip(g, want)) > COLOR_TOL:
            problems.append(f"{name}: {[round(x, 4) for x in g]} != {[round(x, 4) for x in want]}")
        if isinstance(got, dict) and got.get("profile") not in (None, "sRGB"):
            problems.append(f"{name}: profile {got.get('profile')} is not sRGB")
    return problems


# ---- 1 回の観察 ------------------------------------------------------------------------------------------------------

def read_values(obs_values: dict[str, dict], sels: dict[str, str]) -> dict:
    return {name: obs_values[sel]["member"]["value"] for name, sel in sels.items() if sel in obs_values}


def check_sample(v: dict, params: dict, gain: float, g: dict | None = None) -> dict:
    """動いている間の 1 回の観察（全部の駆動の値）。"""
    g = g or gimmicks.g11()
    lo, hi = g["altitude_m"]
    problems = []
    rod = rod_decompose(q_of(v["rod"]))
    W = gimmicks.g09()["wobble_deg"]
    want_tilt = W * math.sin(2.0 * math.radians(rod["phi_deg"]))
    if rod["form_residual"] > ROD_FORM_TOL:
        problems.append(f"rod: rotation is not yaw x local tilt (residual {rod['form_residual']:.5f})")
    if abs(rod["tilt_deg"] - want_tilt) > ROD_TILT_TOL_DEG or abs(rod["tilt_deg"]) > W + ROD_TILT_TOL_DEG:
        problems.append(f"rod: tilt {rod['tilt_deg']:.3f} deg != W sin 2phi {want_tilt:.3f} deg")
    rows = {"rod": rod}
    for name, offset in (("witch", None), ("carrier", g["loop_origin"])):
        r = rider_pose(v[f"{name}_pos"], v[f"{name}_rot"], g, offset)
        rows[name] = r
        if r["path_error_m"] > PATH_TOL_M:
            problems.append(f"{name}: {r['path_error_m']:.4f} m off the patrol path")
        if not (lo - ALT_TOL_M <= r["altitude_m"] <= hi + ALT_TOL_M):
            problems.append(f"{name}: altitude {r['altitude_m']:.4f} m outside {lo}..{hi}")
        if abs(r["heading_error_deg"]) > HEADING_TOL_DEG or r["off_axis"] > OFF_AXIS_TOL:
            problems.append(f"{name}: heading {r['heading_deg']:.2f} deg is {r['heading_error_deg']:.2f} deg off the path tangent "
                            f"(off axis {r['off_axis']:.4f})")
    problems += check_effects(v, params, gain)
    return {**rows, "problems": problems}


def check_travel(samples: list[dict]) -> dict:
    """隣の観察の間に魔女が進んだ向き（水平の弦）と、2 回の正面（ローカル +Z）の平均の向きの差。前へ進んでいるか。"""
    rows, problems = [], []
    for a, b in zip(samples, samples[1:]):
        pa, pb = a["witch"]["pos_b"], b["witch"]["pos_b"]
        dx, dy = pb[0] - pa[0], pb[1] - pa[1]
        if math.hypot(dx, dy) < 0.05:
            continue
        fa, fb = a["witch"]["forward"], b["witch"]["forward"]
        # 正面は Resonite の (x, z) = Blender の (x, y)
        fx, fy = fa[0] + fb[0], fa[2] + fb[2]
        err = wrap_deg(math.degrees(math.atan2(fx, fy) - math.atan2(dx, dy)))
        rows.append(round(err, 3))
        if abs(err) > TRAVEL_TOL_DEG:
            problems.append(f"witch faces {err:.2f} deg away from the direction it travelled")
    if not rows:
        problems.append("witch did not move between the observations")
    return {"errors_deg": rows, "problems": problems}


def _unwrap(samples: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out, acc, prev = [], 0.0, None
    for t, a in samples:
        acc = a if prev is None else acc + (a - prev + 180.0) % 360.0 - 180.0
        prev = a
        out.append((t, acc))
    return out


def max_residual(samples: list[tuple[float, float]]) -> float:
    """角度を連続にして直線に当てはめたときの、各観察と直線の差の最大（度）。平均の速さだけが合う、時刻から外れた式を見つける
    （GPT のレビューの指摘 M-3）。"""
    u = _unwrap(samples)
    n = len(u)
    mt, ma = sum(t for t, _ in u) / n, sum(a for _, a in u) / n
    slope = sum((t - mt) * (a - ma) for t, a in u) / sum((t - mt) ** 2 for t, _ in u)
    return max(abs(a - (ma + slope * (t - mt))) for t, a in u)


def check_speeds(rod_samples: list[tuple[float, float]], theta_samples: list[tuple[float, float]], params: dict,
                 carrier_samples: list[tuple[float, float]] | None = None) -> dict:
    """攪拌の角度 φ と、魔女・CarrierPivot の巡回の θ の速さ（度/秒）を HMC_P3 の速さと比べ、各観察の直線からの差を見る。
    隣の観察の間の進みが大きすぎれば測れないとする。CarrierPivot も魔女とは別に見る（GPT のレビューの指摘 M-1）。"""
    out: dict = {"problems": []}
    series = [("rod", rod_samples, params["G09StirFrequency"]), ("patrol", theta_samples, params["G11Frequency"])]
    if carrier_samples is not None:
        series.append(("carrier", carrier_samples, params["G11Frequency"]))
    for name, samples, f in series:
        want = 360.0 * f
        if len(samples) < 4:
            out["problems"].append(f"{name}: too few observations ({len(samples)})")
            continue
        steps = [(b[1] - a[1]) % 360.0 for a, b in zip(samples, samples[1:])]
        if max(steps) > MAX_STEP_DEG:
            out["problems"].append(f"{name}: a step of {max(steps):.1f} deg is too large to follow the angle")
        speed = fit_speed(samples)
        resid = max_residual(samples)
        tol = RESIDUAL_TOL_DEG["rod" if name == "rod" else "patrol"]
        out[name] = {"deg_per_s": round(speed, 4), "expected": round(want, 4), "max_step_deg": round(max(steps), 2),
                     "max_residual_deg": round(resid, 3), "samples": len(samples)}
        if want <= 0 or abs(speed - want) > SPEED_TOL * want:
            out["problems"].append(f"{name}: {speed:.3f} deg/s != {want:.3f} deg/s")
        if resid > tol:
            out["problems"].append(f"{name}: an observation is {resid:.2f} deg off the line of the clock (tolerance {tol})")
    return out


def check_carrier_phase(samples: list[dict]) -> dict:
    """同じ観察の中の、魔女と CarrierPivot の θ の差（度）。同じ式なら読み取りの時刻のずれの分だけ（GPT のレビューの指摘 M-1）。"""
    diffs = [wrap_deg(s["witch"]["theta_deg"] - s["carrier"]["theta_deg"]) for s in samples]
    problems = [f"carrier is {max(diffs, key=abs):.2f} deg away from the witch on the path"] if diffs and \
        max(abs(d) for d in diffs) > CARRIER_PHASE_TOL_DEG else []
    return {"diff_deg": [round(min(diffs), 3), round(max(diffs), 3)] if diffs else None, "problems": problems}


def clock_offset(theta_samples: list[tuple[float, float]], f: float) -> float:
    """θ − 360 f t（度、0〜360）の平均（円の平均）。時刻から決まる θ なら、窓が変わっても同じ値。"""
    s = sum(math.sin(math.radians(th - 360.0 * f * t)) for t, th in theta_samples)
    c = sum(math.cos(math.radians(th - 360.0 * f * t)) for t, th in theta_samples)
    return math.degrees(math.atan2(s, c)) % 360.0


# ---- 時刻を止めた標本 ---------------------------------------------------------------------------------------------------

def check_frozen(rod_q, witch: tuple, carrier: tuple, params: dict, what: str = "relay", g: dict | None = None) -> dict:
    """G09StirFrequency = G11Frequency = 0 の姿勢（φ = 2π p9、θ = 2π p11）を式と照合する。witch・carrier は (位置, 回転)。
    θ が巡回の点 k（p11 = k/8）のときは、配置データの巡回の点とも照合する（式の係数の誤りを、式から独立に見つける）。"""
    g = g or gimmicks.g11()
    problems = []
    phi = 2.0 * math.pi * params["G09StirPhase"]
    want_rod = rod_expected_q(phi, gimmicks.g09()["wobble_deg"])
    drod = q_close(q_of(rod_q), want_rod)
    if drod > FROZEN_Q_TOL:
        problems.append(f"{what}: rod rotation {q_of(rod_q)} != {tuple(round(x, 5) for x in want_rod)} at phase {params['G09StirPhase']}")
    th = 2.0 * math.pi * params["G11Phase"]
    want_pos, psi = gimmicks.g11_pose(th, g)
    k = params["G11Phase"] * len(g["waypoints"])
    waypoint = g["waypoints"][round(k) % len(g["waypoints"])] if abs(k - round(k)) < 1e-6 else None
    rows = {"rod_q_error": round(drod, 7)}
    for name, (pos, rot), offset in (("witch", witch, [0.0, 0.0, 0.0]), ("carrier", carrier, g["loop_origin"])):
        pb = [r2b([float(pos[c]) for c in "xyz"])[i] + offset[i] for i in range(3)]
        head, off = heading_deg(q_of(rot))
        dpos = math.dist(pb, want_pos)
        dhead = abs(wrap_deg(head - math.degrees(psi)))
        rows[name] = {"position_error_m": round(dpos, 6), "heading_error_deg": round(dhead, 4)}
        if dpos > FROZEN_POS_TOL_M or dhead > FROZEN_DEG_TOL or off > OFF_AXIS_TOL:
            problems.append(f"{what}: {name} at {[round(x, 4) for x in pb]} heading {head:.3f} != {[round(x, 4) for x in want_pos]} "
                            f"{math.degrees(psi):.3f} at phase {params['G11Phase']}")
        if waypoint is not None:
            dwp = math.dist(pb, waypoint)
            rows[name]["waypoint_error_m"] = round(dwp, 6)
            if dwp > FROZEN_POS_TOL_M:
                problems.append(f"{what}: {name} is {dwp:.4f} m from waypoint {round(k) % len(g['waypoints'])}")
    return {"rows": rows, "problems": problems}


def frozen_slots(hier: dict) -> tuple:
    """hierarchy の観察から、攪拌棒の Pivot の回転と、魔女・CarrierPivot の (位置, 回転)。"""
    g9, g11 = gimmicks.g09(), gimmicks.g11()
    piv = _find_live(hier, g9["stir_pivot"])
    rider = _find_live(hier, g11["rider"])
    carrier = _find_live(hier, g11["carrier"])
    if piv is None or rider is None or carrier is None:
        raise SystemExit("the stir pivot, the witch or the carrier pivot is not observed")
    return piv["rotation"], (rider["position"], rider["rotation"]), (carrier["position"], carrier["rotation"])


# ---- 構造 --------------------------------------------------------------------------------------------------------------

def m08_declaration() -> dict:
    d = sorted((PROJECT_ROOT / "exports" / "p2_meshy").glob("M08-*/p2m.apply.json"))
    if not d:
        raise SystemExit("no exports/p2_meshy/M08-*/p2m.apply.json (copy the p2_bundles first)")
    return json.loads(d[-1].read_text(encoding="utf-8"))


def check_structure(c_root: dict, doc: dict | None = None, m08: dict | None = None) -> dict:
    """大釜・巡回路の子孫と、魔女の仮モデルの下の M08 が、宣言と同じパスで同じローカルの変換か。駆動される項目は比べない
    （攪拌棒の Pivot は回転、魔女・CarrierPivot は位置と回転）。攪拌棒の Pivot の位置と、駆動される Slot の拡縮は比べる。"""
    doc = doc or latest_declaration(gimmicks.g09()["district"])
    m08 = m08 or m08_declaration()
    g9, g11 = gimmicks.g09(), gimmicks.g11()
    driven = {g9["stir_pivot"]: ("rotation",), g11["rider"]: ("position", "rotation"), g11["carrier"]: ("position", "rotation")}
    problems, rows = [], []

    def compare(path: tuple, live: dict | None, slot: dict) -> None:
        name = path[-1]
        if live is None:
            problems.append(f"{'/'.join(path)}: missing at the declared path")
            return
        if name in driven:
            want = {"position": slot.get("position") or [0, 0, 0], "scale": slot.get("scale") or [1, 1, 1]}
            err = max(abs(float(live[f][k]) - v) for f in want if f not in driven[name] for k, v in zip("xyz", want[f]))
        else:
            err = _same_local(live, slot)
        rows.append({"slot": "/".join(path), "local_error": round(err, 6)})
        if err > LOCAL_TOL:
            problems.append(f"{'/'.join(path)}: local transform differs from the declaration ({err})")

    for asset in (g9["asset_id"], g11["loop_asset_id"], g11["rider"]):
        decl = _find_decl(doc, asset)
        live = _child(c_root, asset)
        if decl is None or live is None:
            problems.append(f"{asset}: missing")
            continue
        compare((asset,), live, decl["slot"])
        for path, node in _decl_paths(decl):
            lv = live
            for n in path:
                lv = _child(lv, n)
            compare((asset, *path), lv, node["slot"])
    # M08 の素材の宣言（親は魔女の仮モデル）。root とその子孫
    rider_live = _child(c_root, g11["rider"])
    m08_live = _child(rider_live, m08["slot"]["name"]) if rider_live else None
    compare((g11["rider"], m08["slot"]["name"]), m08_live, m08["slot"])
    for path, node in _decl_paths(m08):
        lv = m08_live
        for n in path:
            lv = _child(lv, n)
        compare((g11["rider"], m08["slot"]["name"], *path), lv, node["slot"])
    return {"rows": rows, "problems": problems}


def c_hierarchy(url: str, depth: int = 5) -> dict:
    return run_json(["resoloop", "hierarchy", "--under", f"{gimmicks.P2_ROOT}/{gimmicks.g09()['district']}", "--depth", str(depth),
                     "--url", url, "--json"])


def check_relays(url: str, keys: dict[str, str]) -> list[str]:
    """中継の Drives が Slot のメンバーを指し、有効か。"""
    g9, g11 = gimmicks.g09(), gimmicks.g11()
    targets = [(g9["stir_pivot"], "Rotation", "g09")]
    targets += [(n, m, "g11") for n in (g11["rider"], g11["carrier"]) for m in ("Position", "Rotation")]
    sels = [f"$member:{district.relay_key(keys[n], m, gid)}.{mem}" for n, m, gid in targets for mem in ("Drives", "Enabled")]
    data = run_json(["resoloop", "observe", *sels, "--state", str(C_STATE), "--url", url, "--json"])["data"]["values"]
    problems = []
    ids: dict[str, dict] = {}
    for n, m, gid in targets:
        if n not in ids:
            ids[n] = run_json(["resoloop", "inspect", f"$slot:{keys[n]}", "--state", str(C_STATE), "--members", "--url", url,
                               "--json"])["data"]["members"]
        sel = f"$member:{district.relay_key(keys[n], m, gid)}"
        elems = data[f"{sel}.Drives"]["member"]["elements"]
        if data[f"{sel}.Enabled"]["member"]["value"] is not True:
            problems.append(f"{n}: relay {m} is disabled")
        if [e.get("targetId") for e in elems] != [ids[n][m]["id"]]:
            problems.append(f"{n}: relay {m} does not drive the Slot {m}")
    return problems


def material_expectations(model: dict, doc: dict) -> dict:
    """材質の照合の基準。G09 を足す前の宣言（同じ export の model.apply.json）から、液面の元の材質（エメラルド・マゼンタ）と、
    それを使う MeshRenderer の材質の並び、元の材質の色を取る（GPT のレビューの指摘 M-2。変更後の宣言から取ると、誤って付け替えた
    MeshRenderer が対象から抜ける）。液面の MeshRenderer だけは [専用の材質, 2 つ目] になる。"""
    g9 = gimmicks.g09()

    def renderers(d: dict) -> dict[str, list[str]]:
        out = {}
        stack = [d]
        while stack:
            n = stack.pop()
            for c in n.get("components", []):
                if c["type"] == "FrooxEngine.MeshRenderer":
                    out[c["key"]] = [m.split(":", 1)[1] for m in c["fields"].get("Materials", [])]
            stack.extend(n.get("children", []))
        return out

    def component(d: dict, key: str) -> dict:
        stack = [d]
        while stack:
            n = stack.pop()
            for c in n.get("components", []):
                if c.get("key") == key:
                    return c
            stack.extend(n.get("children", []))
        raise SystemExit(f"{key} is not declared")

    src = _find_decl(model, g9["liquid"])
    liquid = next(c for c in src["components"] if c["type"] == "FrooxEngine.MeshRenderer")
    sources = [m.split(":", 1)[1] for m in liquid["fields"]["Materials"]]
    base = renderers(model)
    want = {k: ms for k, ms in base.items() if set(ms) & set(sources)}
    want[liquid["key"]] = [gimmicks.G09_LIQUID_MATERIAL_KEY] + sources[1:]
    if renderers(doc).get(liquid["key"]) != want[liquid["key"]]:
        raise SystemExit("C declaration: the liquid renderer is not [dedicated material, second material]")
    colors = {(k, m): [float(x) for x in component(model, k)["fields"][m]] for k in sources for m in ("AlbedoColor", "EmissiveColor")}
    return {"liquid_renderer": liquid["key"], "sources": sources, "renderers": want, "colors": colors}


def compare_materials(exp: dict, observed: dict[str, list[str]], ids: dict[str, str], colors: dict[tuple, dict]) -> list[str]:
    """観察した MeshRenderer の材質の参照（targetId の並び）と、元の材質の色を、基準（material_expectations）と比べる。"""
    problems = []
    for rend, ms in exp["renderers"].items():
        got = observed.get(rend)
        if got != [ids.get(m) for m in ms]:
            problems.append(f"{rend}: materials {got} != {ms}")
    for (mat, member), want in exp["colors"].items():
        got = colors.get((mat, member))
        if got is None or got.get("profile", "sRGB") != "sRGB" or max(abs(float(got[c]) - w) for c, w in zip("rgba", want)) > 1e-4:
            problems.append(f"{mat}.{member}: shared material colour changed {got} != {want}")
    return problems


def check_materials(url: str, doc: dict | None = None) -> dict:
    """液面の MeshRenderer の材質が [専用の材質, 2 つ目]、元の材質を使うほかの MeshRenderer は元の材質のまま、元の材質の色も
    宣言のまま、か。"""
    doc = doc or latest_declaration(gimmicks.g09()["district"])
    model = json.loads((_bundle(gimmicks.g09()["district"]) / "model.apply.json").read_text(encoding="utf-8"))
    exp = material_expectations(model, doc)
    sels = [f"$member:{k}.Materials" for k in exp["renderers"]] + [f"$member:{k}.{m}" for k, m in exp["colors"]]
    data = run_json(["resoloop", "observe", *sels, "--state", str(C_STATE), "--url", url, "--json"])["data"]["values"]
    keys = sorted({m for ms in exp["renderers"].values() for m in ms})
    ids = {k: component_id(f"$member:{k}.Enabled", C_STATE, url) for k in keys}
    observed = {k: [e.get("targetId") for e in data[f"$member:{k}.Materials"]["member"]["elements"]] for k in exp["renderers"]}
    colors = {(k, m): data[f"$member:{k}.{m}"]["member"]["value"] for k, m in exp["colors"]}
    return {"liquid": exp["renderers"][exp["liquid_renderer"]], "sources": exp["sources"],
            "renderers": sorted(exp["renderers"]), "problems": compare_materials(exp, observed, ids, colors)}


# ---- 包絡（バンドルのメッシュから。観察ではない） -----------------------------------------------------------------------

def envelopes(doc: dict | None = None) -> dict:
    doc = doc or latest_declaration(gimmicks.g09()["district"])
    bundle = _bundle(gimmicks.g09()["district"])
    g9, g11 = gimmicks.g09(), gimmicks.g11()
    out: dict = {}
    # G09: 攪拌棒（大釜の root のローカル。Resonite の y が高さ）
    cauldron = _find_decl(doc, g9["asset_id"])
    piv = _find_decl(cauldron, g9["stir_pivot"])
    ppos = piv["slot"].get("position") or [0, 0, 0]
    rod_pts = _local_points(bundle, doc, piv)          # Pivot のローカル
    below, low, outside = [], [], 0
    for k in range(0, 360, 5):
        q = rod_expected_q(math.radians(k), g9["wobble_deg"])
        for v in rod_pts:
            r = qrot(q, v)
            p = (ppos[0] + r[0], ppos[1] + r[1], ppos[2] + r[2])
            if p[1] <= ROD_ENVELOPE["rim_top_m"]:
                below.append(math.hypot(p[0], p[2]))
            low.append(p[1])
            outside += math.hypot(p[0], p[2]) > g9["clear_radius_m"]
    out["G09"] = {"max_radius_below_rim_m": round(max(below), 4), "lowest_m": round(min(low), 4),
                  "points_outside_clear_radius": outside, **ROD_ENVELOPE, "clear_radius_m": g9["clear_radius_m"]}
    # G11: M08（素材の宣言の root のローカルの変換を含む、仮モデルのローカルの頂点）を経路に沿って動かす
    m08 = m08_declaration()
    m08_dir = sorted((PROJECT_ROOT / "exports" / "p2_meshy").glob("M08-*/p2m.apply.json"))[-1].parent
    s = m08["slot"]
    pts = _local_points(m08_dir, m08, m08, tuple(s.get("rotation") or (0, 0, 0, 1)), s.get("position") or (0, 0, 0))
    pts = pts[::max(1, len(pts) // 1500)]
    corridor = next(e for e in json.loads((PROJECT_ROOT / "layout/areas/C_candy.json").read_text(encoding="utf-8"))["Exclusions"]
                    if e["zone_id"] == "EX_C_SkyPatrolCorridor")["bounds"]
    m04 = _m04_box(doc)
    lowest, nearest_m04, outside_xy = math.inf, math.inf, 0
    for k in range(360):
        pos, psi = gimmicks.g11_pose(2 * math.pi * k / 360, g11)
        q = (0.0, math.sin(psi / 2.0), 0.0, math.cos(psi / 2.0))
        for v in pts:
            r = qrot(q, v)
            wb = (pos[0] + r[0], pos[1] + r[2], pos[2] + r[1])   # Blender の世界座標
            lowest = min(lowest, wb[2])
            dx = max(m04["min"][0] - wb[0], 0.0, wb[0] - m04["max"][0])
            dy = max(m04["min"][1] - wb[1], 0.0, wb[1] - m04["max"][1])
            dz = max(m04["min"][2] - wb[2], 0.0, wb[2] - m04["max"][2])
            nearest_m04 = min(nearest_m04, math.sqrt(dx * dx + dy * dy + dz * dz))
            outside_xy += not (corridor["min"][0] <= wb[0] <= corridor["max"][0] and corridor["min"][1] <= wb[1] <= corridor["max"][1])
    out["G11"] = {"lowest_m": round(lowest, 4), "corridor_bottom_m": corridor["min"][2],
                  "points_outside_corridor_xy": outside_xy, "m04_box": m04, "nearest_m04_box_m": round(nearest_m04, 4),
                  "m04_clearance_m": M04_CLEARANCE_M, "samples": 360, "m08_points": len(pts)}
    return out


def _m04_box(doc: dict) -> dict:
    """M04 の素材（バンドルのメッシュ）の、C の root のローカルの外接箱（Blender の座標）。"""
    m04_doc_path = sorted((PROJECT_ROOT / "exports" / "p2_meshy").glob("M04-*/p2m.apply.json"))[-1]
    m04 = json.loads(m04_doc_path.read_text(encoding="utf-8"))
    proxy = _find_decl(doc, "CCD_M04_CandyWorkshopProxy_001")
    ps = proxy["slot"]
    s = m04["slot"]
    pq, pp = tuple(ps.get("rotation") or (0, 0, 0, 1)), ps.get("position") or (0, 0, 0)
    sq, sp = tuple(s.get("rotation") or (0, 0, 0, 1)), s.get("position") or (0, 0, 0)
    rp = qrot(pq, sp)
    pts = _local_points(m04_doc_path.parent, m04, m04, qmul(pq, sq), (pp[0] + rp[0], pp[1] + rp[1], pp[2] + rp[2]))
    b = [r2b(p) for p in pts]
    return {"min": [round(min(p[i] for p in b), 4) for i in range(3)], "max": [round(max(p[i] for p in b), 4) for i in range(3)]}


def envelope_problems(env: dict) -> list[str]:
    problems = []
    e9 = env["G09"]
    if e9["max_radius_below_rim_m"] >= e9["liquid_radius_m"]:
        problems.append(f"G09: the rod reaches {e9['max_radius_below_rim_m']} m from the axis below the rim (liquid radius "
                        f"{e9['liquid_radius_m']} m)")
    if e9["lowest_m"] <= e9["bottom_m"] or e9["points_outside_clear_radius"]:
        problems.append(f"G09: the rod goes below the cauldron bottom ({e9['lowest_m']} m) or outside the clear radius")
    e11 = env["G11"]
    if e11["lowest_m"] < e11["corridor_bottom_m"] or e11["points_outside_corridor_xy"]:
        problems.append(f"G11: the witch leaves the sky patrol corridor (lowest {e11['lowest_m']} m, "
                        f"{e11['points_outside_corridor_xy']} points outside in plan)")
    if e11["nearest_m04_box_m"] < e11["m04_clearance_m"]:
        problems.append(f"G11: the witch comes within {e11['nearest_m04_box_m']} m of the M04 box")
    return problems


# ---- 観察 ------------------------------------------------------------------------------------------------------------

def observe_params(url: str) -> dict:
    v = variables()
    sels = [f"$member:{s['key']}.Value" for s in v.values()] + [f"$member:{gimmicks.G09_COLOR_KEY}.Value"]
    data = run_json(["resoloop", "observe", *sels, "--state", str(P3_STATE), "--url", url, "--json"])["data"]["values"]
    out = {n: float(data[f"$member:{s['key']}.Value"]["member"]["value"]) for n, s in v.items()}
    out[gimmicks.G09_COLOR_VARIABLE] = data[f"$member:{gimmicks.G09_COLOR_KEY}.Value"]["member"]["value"]
    return out


def glow_gain() -> float:
    return gimmicks.g09_liquid_base(latest_declaration(gimmicks.g09()["district"]))["glow_gain"]


def _ids(url: str) -> dict[str, str]:
    v = variables()
    ids = {n: component_id(f"$member:{s['key']}.Value", P3_STATE, url) for n, s in v.items()}
    ids[gimmicks.G09_COLOR_VARIABLE] = component_id(f"$member:{gimmicks.G09_COLOR_KEY}.Value", P3_STATE, url)
    return ids


def _put(ids: dict[str, str], name: str, value, url: str) -> None:
    if isinstance(value, dict):
        value = [value[k] for k in "rgba"]
    set_member(ids[name], "Value", json.dumps(value) if isinstance(value, list) else str(value), url)


def frozen_probe(url: str, raw: list) -> dict:
    """時刻を止めた標本（G09StirFrequency = G11Frequency = 0、G09StirPhase 0.125、G11Phase 0.25 = 巡回の点 2）を Slot そのもので
    取り、値を戻す。窓ごとに取り、窓の間で比べる（check_drift）。"""
    ids = _ids(url)
    before = observe_params(url)
    try:
        for n, val in (("G09StirFrequency", 0.0), ("G11Frequency", 0.0), ("G09StirPhase", 0.125), ("G11Phase", 0.25)):
            _put(ids, n, val, url)
        time.sleep(1.5)
        params = params_of(observe_params(url))
        hier = c_hierarchy(url, depth=3)
        raw.append({"kind": "frozen_probe", "data": hier})
        rod, witch, carrier = frozen_slots(hier["data"])
    finally:
        for n in ("G09StirFrequency", "G11Frequency", "G09StirPhase", "G11Phase"):
            _put(ids, n, before[n], url)
    restored = observe_params(url)
    res = check_frozen(rod, witch, carrier, params, "slot")
    problems = list(res["problems"])
    if restored != before:
        problems.append(f"frozen probe: variables not restored: {restored} != {before}")
    return {"params": {k: v for k, v in params.items() if k != gimmicks.G09_COLOR_VARIABLE}, "rows": res["rows"],
            "slots": {"rod": [round(float(rod[k]), 6) for k in "xyzw"],
                      "witch": [round(float(witch[0][k]), 5) for k in "xyz"], "carrier": [round(float(carrier[0][k]), 5) for k in "xyz"]},
            "problems": problems}


def check_drift(probes: list[dict], offsets: list[float], carrier_offsets: list[float] | None = None) -> dict:
    """窓ごとの時刻を止めた標本を最初の窓と比べ（同じ位相の位置の差 1 cm 以内、攪拌棒の回転の差）、θ − ω t の差も見る
    （魔女と、別に CarrierPivot。GPT のレビューの指摘 M-1）。"""
    rows, problems = [], []
    if len(probes) < 2:
        return {"rows": rows, "problems": ["drift: needs two windows"]}
    base = probes[0]["slots"]
    for i, p in enumerate(probes[1:], start=2):
        if p["params"] != probes[0]["params"]:
            problems.append(f"drift: window {i} was probed with other values {p['params']}")
        for name in ("witch", "carrier"):
            d = math.dist(base[name], p["slots"][name])
            rows.append({"window": i, "slot": name, "position_diff_m": round(d, 6)})
            if d > DRIFT_TOL_M:
                problems.append(f"drift: {name} moved {d:.4f} m at the same phase by window {i}")
        dq = q_close(base["rod"], p["slots"]["rod"])
        rows.append({"window": i, "slot": "rod", "rotation_diff": round(dq, 6)})
        if dq > math.radians(DRIFT_TOL_DEG) / 2.0:
            problems.append(f"drift: rod rotation differs {dq:.5f} at the same phase by window {i}")
    for name, offs in (("witch", offsets), ("carrier", carrier_offsets or [])):
        for i, off in enumerate(offs[1:], start=2):
            d = abs(wrap_deg(off - offs[0]))
            rows.append({"window": i, "slot": name, "clock_offset_diff_deg": round(d, 3)})
            if d > CLOCK_OFFSET_TOL_DEG:
                problems.append(f"drift: {name} theta - omega t moved {d:.2f} deg between windows 1 and {i}")
    return {"rows": rows, "clock_offsets_deg": [round(o, 3) for o in offsets],
            "carrier_clock_offsets_deg": [round(o, 3) for o in carrier_offsets or []], "problems": problems}


def observe_window(url: str, duration: float, rod_duration: float, raw: list) -> dict:
    keys = c_keys(STATE_DIR)
    sels = selectors(keys)
    gain = glow_gain()
    g = gimmicks.g11()
    params_raw = observe_params(url)
    params = params_of(params_raw)
    window: dict = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "params": {k: v for k, v in params_raw.items()}, "samples": [], "problems": []}
    hier = c_hierarchy(url)
    raw.append({"kind": "hierarchy_start", "data": hier})
    window["structure_start"] = check_structure(hier["data"])
    window["relay_problems"] = check_relays(url, keys)
    window["materials"] = check_materials(url)
    window["frozen_probe"] = frozen_probe(url, raw)
    # 攪拌棒だけを続けて観察する（1 回 約 1.5 秒。60°/s の回転を連続にできる間隔）
    rod_samples = []
    t_end = time.time() + rod_duration
    while time.time() < t_end:
        t, obs = timed(["resoloop", "observe", sels["rod"], "--state", str(C_STATE), "--url", url, "--json"])
        raw.append({"kind": "rod", "t": t, "data": obs})
        rod_samples.append((t, rod_decompose(q_of(obs["data"]["values"][sels["rod"]]["member"]["value"]))["phi_deg"]))
    # 全部の駆動の値
    t_end = time.time() + duration
    while time.time() < t_end:
        t, obs = timed(["resoloop", "observe", *sels.values(), "--state", str(C_STATE), "--url", url, "--json"])
        raw.append({"kind": "all", "t": t, "data": obs})
        s = check_sample(read_values(obs["data"]["values"], sels), params, gain, g)
        s["t"] = round(t, 3)
        window["samples"].append(s)
    hier2 = c_hierarchy(url)
    raw.append({"kind": "hierarchy_end", "data": hier2})
    window["structure_end"] = check_structure(hier2["data"])
    smp = window["samples"]
    theta = [(s["t"], s["witch"]["theta_deg"]) for s in smp]
    ctheta = [(s["t"], s["carrier"]["theta_deg"]) for s in smp]
    window["speeds"] = check_speeds(rod_samples, theta, params, ctheta)
    window["travel"] = check_travel(smp)
    window["carrier_phase"] = check_carrier_phase(smp)
    window["clock_offset_deg"] = clock_offset(theta, params["G11Frequency"]) if theta else None
    window["carrier_clock_offset_deg"] = clock_offset(ctheta, params["G11Frequency"]) if ctheta else None
    window["summary"] = {
        "samples": len(smp), "rod_samples": len(rod_samples),
        "rod_tilt_deg": [round(min(s["rod"]["tilt_deg"] for s in smp), 3), round(max(s["rod"]["tilt_deg"] for s in smp), 3)],
        "witch_path_error_m": round(max(s["witch"]["path_error_m"] for s in smp), 5),
        "carrier_path_error_m": round(max(s["carrier"]["path_error_m"] for s in smp), 5),
        "witch_altitude_m": [round(min(s["witch"]["altitude_m"] for s in smp), 4), round(max(s["witch"]["altitude_m"] for s in smp), 4)],
        "witch_heading_error_deg": round(max(abs(s["witch"]["heading_error_deg"]) for s in smp), 3),
        "witch_theta_deg": [round(min(x for _, x in theta), 2), round(max(x for _, x in theta), 2)],
    }
    for s in smp:
        window["problems"].extend(s["problems"])
    window["problems"] += (window["speeds"]["problems"] + window["travel"]["problems"] + window["carrier_phase"]["problems"]
                           + window["relay_problems"]
                           + window["materials"]["problems"] + window["frozen_probe"]["problems"]
                           + window["structure_start"]["problems"] + window["structure_end"]["problems"])
    window["ok"] = not window["problems"]
    return window


# ---- 外から変えられる値の確認 -------------------------------------------------------------------------------------------

def _frozen_case(url: str, label: str, keys: dict[str, str], sels: dict[str, str], gain: float, raw: list) -> dict:
    time.sleep(1.0)
    params_raw = observe_params(url)
    params = params_of(params_raw)
    _, obs = timed(["resoloop", "observe", *sels.values(), "--state", str(C_STATE), "--url", url, "--json"])
    hier = c_hierarchy(url, depth=3)
    raw.append({"kind": f"frozen_{label}", "data": [obs, hier]})
    v = read_values(obs["data"]["values"], sels)
    relay = check_frozen(v["rod"], (v["witch_pos"], v["witch_rot"]), (v["carrier_pos"], v["carrier_rot"]), params, "relay")
    slot = check_frozen(*frozen_slots(hier["data"]), params, "slot")
    eff = check_effects(v, params, gain)
    return {"params": {k: x for k, x in params_raw.items() if k != gimmicks.G09_COLOR_VARIABLE}, "relay": relay["rows"],
            "slot": slot["rows"], "effects": {k: (round(float(x), 4) if isinstance(x, (int, float)) else [round(c, 4) for c in _rgba(x)])
                                              for k, x in v.items() if k in expected_effects(params, gain)},
            "problems": relay["problems"] + slot["problems"] + eff}


def param_check(url: str, raw: list) -> dict:
    out: dict = {"problems": []}
    keys = c_keys(STATE_DIR)
    sels = selectors(keys)
    gain = glow_gain()
    ids = _ids(url)
    before = observe_params(url)
    out["before"] = before

    def put(name: str, value) -> None:
        _put(ids, name, value, url)

    try:
        # 0) 時刻を止めた標本: 巡回の点 0〜7 と点の間、攪拌の位置 5 つ
        put("G09StirFrequency", 0.0)
        put("G11Frequency", 0.0)
        cases = [(0.0, 0.0), (0.125, 0.125), (0.3, 0.25), (0.6, 0.375), (0.9, 0.5), (0.0, 0.625), (0.0, 0.75), (0.0, 0.875),
                 (0.0, 0.0625)]
        for p9, p11 in cases:
            put("G09StirPhase", p9)
            put("G11Phase", p11)
            case = _frozen_case(url, f"stir_{p9}_patrol_{p11}", keys, sels, gain, raw)
            out[f"frozen_stir_{p9}_patrol_{p11}"] = case
            out["problems"].extend(case["problems"])
        # 1) 範囲の外の値。収めないと、攪拌棒は φ = 3π（180° 回った姿勢）、魔女は θ = 3π（巡回の点 4）、泡は毎秒 30 個
        put("G09StirPhase", 1.5)
        put("G11Phase", 1.5)
        put("G09StirFrequency", -1.0)
        put("G11Frequency", -1.0)
        put("G09Bubbles", 5.0)
        put("G09Smoke", -1.0)
        case = _frozen_case(url, "out_of_range_1", keys, sels, gain, raw)
        out["frozen_out_of_range_1"] = case
        out["problems"].extend(case["problems"])
        put("G09Bubbles", -1.0)
        put("G09Smoke", 5.0)
        case = _frozen_case(url, "out_of_range_2", keys, sels, gain, raw)
        out["frozen_out_of_range_2"] = case
        out["problems"].extend(case["problems"])
        put("G09Bubbles", before["G09Bubbles"])
        put("G09Smoke", before["G09Smoke"])
        # 2) 液面の色（I02 の Magenta）
        put("G09StirPhase", 0.0)
        put("G11Phase", 0.0)
        put(gimmicks.G09_COLOR_VARIABLE, MAGENTA)
        case = _frozen_case(url, "color_magenta", keys, sels, gain, raw)
        # 色を変えている間も、共有の材質の色と参照が変わらないこと（GPT のレビューの指摘 M-2）
        case["materials"] = check_materials(url)
        case["problems"] += case["materials"]["problems"]
        out["frozen_color_magenta"] = case
        out["problems"].extend(case["problems"])
    finally:
        for name in before:
            put(name, before[name])
    # 3) ゆっくりの時刻
    try:
        put("G09StirFrequency", CLOCK_FREQUENCY)
        put("G11Frequency", CLOCK_FREQUENCY)
        time.sleep(1.0)
        params = params_of(observe_params(url))
        t1, o1 = timed(["resoloop", "observe", *sels.values(), "--state", str(C_STATE), "--url", url, "--json"])
        time.sleep(CLOCK_WAIT_S)
        t2, o2 = timed(["resoloop", "observe", *sels.values(), "--state", str(C_STATE), "--url", url, "--json"])
        raw.append({"kind": "clock", "t": [t1, t2], "data": [o1, o2]})
        s1 = check_sample(read_values(o1["data"]["values"], sels), params, gain)
        s2 = check_sample(read_values(o2["data"]["values"], sels), params, gain)
        want = 360.0 * CLOCK_FREQUENCY * (t2 - t1)
        dphi = (s2["rod"]["phi_deg"] - s1["rod"]["phi_deg"]) % 360.0
        dth = (s2["witch"]["theta_deg"] - s1["witch"]["theta_deg"]) % 360.0
        out["clock"] = {"dt_s": round(t2 - t1, 3), "expected_deg": round(want, 4), "rod_deg": round(dphi, 4), "patrol_deg": round(dth, 4),
                        "problems": s1["problems"] + s2["problems"]}
        if abs(dphi - want) > CLOCK_TOL_DEG:
            out["clock"]["problems"].append(f"clock: rod advanced {dphi:.3f} deg, expected {want:.3f}")
        if abs(dth - want) > CLOCK_TOL_DEG:
            out["clock"]["problems"].append(f"clock: patrol advanced {dth:.3f} deg, expected {want:.3f}")
        out["problems"].extend(out["clock"]["problems"])
    finally:
        put("G09StirFrequency", before["G09StirFrequency"])
        put("G11Frequency", before["G11Frequency"])
    out["restored"] = observe_params(url)
    if out["restored"] != before:
        out["problems"].append(f"variables not restored: {out['restored']} != {before}")
    out["ok"] = not out["problems"]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", required=True)
    ap.add_argument("--raw-out", type=Path, required=True, help="生の観察の保存先（Git の外。ResoniteLink の ID を含む）")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--windows", type=int, default=1)
    ap.add_argument("--gap", type=float, default=300.0, help="窓と窓の間の秒数")
    ap.add_argument("--duration", type=float, default=40.0, help="全部の駆動の値を観察する秒数")
    ap.add_argument("--rod-duration", type=float, default=20.0, help="攪拌棒だけを観察する秒数")
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
            wins.append(observe_window(args.url, args.duration, args.rod_duration, raw))
        env = envelopes()
        drift = check_drift([w["frozen_probe"] for w in wins], [w["clock_offset_deg"] for w in wins],
                            [w["carrier_clock_offset_deg"] for w in wins])
        result = {"windows": wins, "gap_s": args.gap if args.windows > 1 else None, "drift": drift, "envelopes": env,
                  "envelope_problems": envelope_problems(env),
                  "tolerances": {"path_m": PATH_TOL_M, "heading_deg": HEADING_TOL_DEG, "travel_deg": TRAVEL_TOL_DEG,
                                 "rod_tilt_deg": ROD_TILT_TOL_DEG, "frozen_pos_m": FROZEN_POS_TOL_M, "frozen_deg": FROZEN_DEG_TOL,
                                 "color": COLOR_TOL, "speed": SPEED_TOL, "drift_m": DRIFT_TOL_M, "clock_offset_deg": CLOCK_OFFSET_TOL_DEG,
                                 "residual_deg": RESIDUAL_TOL_DEG, "carrier_phase_deg": CARRIER_PHASE_TOL_DEG,
                                 "local": LOCAL_TOL}}
        drift_problems = drift["problems"] if args.windows > 1 else []
        result["ok"] = all(w["ok"] for w in wins) and not result["envelope_problems"] and not drift_problems
    args.raw_out.parent.mkdir(parents=True, exist_ok=True)
    args.raw_out.write_text(json.dumps(raw, ensure_ascii=False) + "\n", encoding="utf-8")
    if not args.param_check:
        # コミットする記録には観察の列を入れない（要約と問題だけ）。列は --raw-out にある
        for w in result["windows"]:
            w["samples"] = [{"t": s["t"], "rod": {k: round(x, 4) for k, x in s["rod"].items()},
                             "witch": {k: round(s["witch"][k], 4) for k in ("theta_deg", "path_error_m", "altitude_m", "heading_error_deg")},
                             "carrier": {k: round(s["carrier"][k], 4) for k in ("theta_deg", "path_error_m", "heading_error_deg")}}
                            for s in w["samples"]]
            w["structure_start"]["rows"] = len(w["structure_start"]["rows"])
            w["structure_end"]["rows"] = len(w["structure_end"]["rows"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {k: v for k, v in result.items() if k not in ("windows",) and not k.startswith("frozen_")}
    if not args.param_check:
        summary["windows"] = [{"ok": w["ok"], "summary": w["summary"], "speeds": w["speeds"], "problems": w["problems"][:10]}
                              for w in result["windows"]]
    print(json.dumps(summary, ensure_ascii=False, indent=1, default=str)[:6000])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
