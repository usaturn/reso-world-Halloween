"""W10-D: Resonite で動いている G15（おばけ列車の周回）を、時間を空けた観察から検査する。

実行（プロジェクトのディレクトリ。対象のワールドを Resonite の前面に出しておく。背面では駆動が進まない）:
    uv run python modeling/p3_gimmicks/verify_d.py --url ws://localhost:<PORT>/ \\
        --raw-out <Git の外の JSON> --output review/p3_gimmicks/g15_live_checks.json [--windows 2 --gap 300]
    # 外から変えられる値の確認（値を変えて測り、元に戻す。ワールドに書く）
    uv run python modeling/p3_gimmicks/verify_d.py --url ... --raw-out ... --output review/p3_gimmicks/g15_param_checks.json --param-check

観察（窓ごと。--windows の数だけ、--gap 秒あけて繰り返す）
- 構造: 窓の最初と最後に resoloop hierarchy で、列車の asset root の子孫（先頭車・客車の root の下の車輪・取付位置・仮の車体、
  M06 の素材の宣言の root とその子孫）が宣言と同じパスで同じローカルの変換か（駆動される項目だけは比べない）。線路も。中継の
  Drives が Slot のメンバーを指し有効か
- 時刻を止めた標本: G15Speed を 0、G15Phase を 0.5 にし、先頭車・客車・車輪の Slot そのものの姿勢を読み、式に照合してから値を
  戻す。窓の間で比べる（同じ位相の位置の差 1 cm 以内）
- 先頭車の中継の位置だけを続けて観察（1 回 約 1.5 秒）: 経路の弧の位置 u の速さ、各観察と直線の差
- 全部の駆動の値を続けて観察: 先頭車・客車が経路の上（1 cm 以内）・レールの上面の高さ、向きが経路の接線（読み取りの時刻のずれの
  分を許す）、進んだ向きと正面の向き、上から見て時計回り、先頭車と客車の弧の差、車輪が +X まわりだけで回っているか
- 窓の間の時刻の基準: 各窓の u − V t（t は壁の時計）が窓の間で合うか（u が時刻から決まり、漂わない）

検査（--param-check）
- 時刻を止めた標本: G15Phase を、先頭車か客車が W05 の経路点に来る値にし、位置・向きを経路点のデータと（中継の値と Slot そのもの
  の両方で）照合する。車輪の回転は進んだ距離 G15Phase × L ÷ 半径
- 範囲の外の値: G15Phase 1.5 → 1（収めないと周の反対側）・-1 → 0、G15Speed -1 → 0（止まる）・10 → 3 m/s
- 速さを変える: G15Speed 1.1 m/s（既定の半分）で測った速さ
- ゆっくりの時刻（G15Speed = 0.05 m/s）で、先頭車・客車の進みと車輪の回転の進み（+X まわりの正 = 前へ転がる）が、時刻と半径の
  とおりか
- どれも元に戻し、戻ったかを確かめる
- 包絡（バンドルのメッシュから。観察ではない）: M06・仮モデルの客車と車輪・取付位置を経路に沿って動かし、W01 の主動線・連絡橋、
  D の除外範囲、ほかの物（線路と床を除く）の外接箱に入らないか
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
from modeling.p3_gimmicks.build_content import d_keys  # noqa: E402
from modeling.p3_gimmicks.rest_pose import latest_declaration  # noqa: E402
from modeling.p3_gimmicks.verify_c import heading_deg, q_close  # noqa: E402
from modeling.p3_gimmicks.verify_live import (  # noqa: E402
    STATE_DIR, _bundle, _child, _decl_paths, _find_decl, _local_points, _same_local, component_id, q_of, qmul, qrot,
    run_json, set_member, wrap_deg)

D_STATE = STATE_DIR / "p2_D_amusement.json"
P3_STATE = STATE_DIR / "p3_gimmicks.json"
PATH_TOL_M = 0.01            # 先頭車・客車の位置と経路の距離
HEIGHT_TOL_M = 0.001
HEADING_TOL_DEG = 6.0        # 動いている間の向き（位置と回転は別の中継で、1 回の observe の中で読む時刻がずれる）
# 隣の観察の間に進んだ向き（弦）と、2 回の正面の向きの平均の差。円弧・直線の上なら弦は 2 つの接線の平均の向きに一致し、
# 直線と曲線をまたぐ弦だけがずれる。後ろ向き・横向きに進む式（180°・90°）を見つけるための許容
TRAVEL_TOL_DEG = 30.0
OFF_AXIS_TOL = 1e-3
FROZEN_POS_TOL_M = 0.001
FROZEN_DEG_TOL = 0.05
FROZEN_Q_TOL = 1e-4
SPEED_TOL = 0.05
MAX_STEP_M = 15.0            # 隣の観察の間に進み得る弧の長さの上限（周 36.27 m を連続にする前提は半周未満）
# 各観察と、弧の位置を連続にして当てはめた直線の差の許容。observe の時刻は前後の中点で見積もるので、読んだ時刻は中点から最大で
# 実行時間の半分ずれる。観察ごとに「実行時間の半分 × 速さ + RESIDUAL_MARGIN_M」を許す（2026-11-02 の窓 2 は 1 回 最大 約 4.8 秒で、
# 一律 1.0 m の許容を 1.32 m で超えた）。平均の速さだけが合い、途中で時刻から外れる式を見つける
RESIDUAL_MARGIN_M = 0.3
# 同じ観察の中の先頭車と客車の弧の差。客車を後に読むので、読む時刻の差 × 速さだけ 2.75 m より短く見える（2026-11-02 の実測で
# 多くは 0.48〜0.64 m = 約 0.25 秒、遅い回に 1.10 m = 約 0.5 秒）。読む時刻の差はそのコマンドの実行時間を超えないので、短く見える分が
# 0〜速さ × 実行時間（と GAP_TOL_M）の中かを見る（止まった・遅れた・先へ出た客車を見つける）。正確な弧の差は時刻を止めた標本で見る
GAP_TOL_M = 0.05
CLOCK_SPEED = 0.05           # ゆっくりの時刻（m/秒）。車輪は 約 0.24 rad/秒
# ゆっくりの時刻の観察の長さ。observe の時刻は前後の中点で見積もるので、1 回にかかる時間が変わる（2026-11-02 の試しで 3.6 → 2.3 秒）
# と傾きがずれる（20 秒の試しで −5%）。40 秒にして、先頭車・客車の速さは 5% 以内、車輪の回る速さは同じ観察の先頭車の速さ ÷ 半径と
# 1% 以内で比べる（時刻の見積もりに左右されない関係）
CLOCK_WAIT_S = 40.0
CLOCK_TOL = 0.05
WHEEL_RATIO_TOL = 0.01
CLOCK_OFFSET_TOL_M = 1.6     # 窓の間の u − V t の差（observe の時刻の見積もりのずれ ±0.7 秒 × 2.2 m/s の分）
DRIFT_TOL_M = 0.01
DRIFT_TOL_DEG = 0.5
LOCAL_TOL = 1e-4
SPEED_CASES = (1.1, 10.0)    # 速さを変える確認（10 は 3 m/s に収まる）


def _clamp(x: float, lo: float, hi: float) -> float:
    return min(max(float(x), lo), hi)


def params_of(raw: dict) -> dict:
    """観察した値を、モジュールと同じ範囲に収めた値にする。"""
    v = gimmicks.G15_VARIABLES
    return {n: _clamp(raw[n], v[n]["min"], v[n]["max"]) for n in v}


def relay_sel(slot_key: str, member: str) -> str:
    return f"$member:{district.relay_key(slot_key, member, 'g15')}.Value"


def selectors(keys: dict[str, str], g: dict | None = None) -> dict[str, str]:
    g = g or gimmicks.g15()
    sels = {"engine_pos": relay_sel(keys[g["engine"]], "Position"), "engine_rot": relay_sel(keys[g["engine"]], "Rotation"),
            "car_pos": relay_sel(keys[g["car"]], "Position"), "car_rot": relay_sel(keys[g["car"]], "Rotation")}
    for w in g["wheels"]:
        sels[w] = relay_sel(keys[w], "Rotation")
    return sels


# ---- 式と照合 ------------------------------------------------------------------------------------------------------------

def car_pose(pos: dict, rot: dict, g: dict) -> dict:
    """先頭車か客車の root の位置・回転（asset root のローカル）を、経路の弧の位置 u と照合する。"""
    p = [float(pos[k]) for k in "xyz"]
    cx, cy = g["center_local_blender"]
    tx, ty = p[0] - cx, p[2] - cy
    u, _ = gimmicks.stadium_arc(tx, ty, g["radius_m"], g["straight_m"])
    want, th = gimmicks.g15_car_pose(u, g)
    head, axis = heading_deg(q_of(rot))
    return {"u_m": u, "path_error_m": math.dist([want[0], want[2]], [p[0], p[2]]), "height_error_m": abs(p[1] - g["rail_local_z"]),
            "heading_deg": head, "heading_error_deg": wrap_deg(head - math.degrees(th)), "off_axis": axis,
            "plan": [tx, ty], "forward": list(qrot(q_of(rot), (0.0, 0.0, 1.0)))}


def wheel_angle(q) -> tuple[float, float]:
    """車輪の回転を +X まわりの角度（度、−180〜180）と、X 以外の成分の大きさに分ける。"""
    x, y, z, w = q
    if w < 0:
        x, y, z, w = -x, -y, -z, -w
    return math.degrees(2.0 * math.atan2(x, w)), max(abs(y), abs(z))


def wheel_q(distance_m: float, radius_m: float) -> tuple:
    """進んだ距離の車輪の回転（Resonite の +X まわりに距離 ÷ 半径。上端が前（+Z）へ進む = 前へ転がる）。"""
    h = distance_m / radius_m / 2.0
    return (math.sin(h), 0.0, 0.0, math.cos(h))


def check_sample(v: dict, g: dict | None = None) -> dict:
    """動いている間の 1 回の観察（全部の駆動の値）。"""
    g = g or gimmicks.g15()
    problems, rows = [], {}
    for name in ("engine", "car"):
        r = car_pose(v[f"{name}_pos"], v[f"{name}_rot"], g)
        rows[name] = r
        if r["path_error_m"] > PATH_TOL_M or r["height_error_m"] > HEIGHT_TOL_M:
            problems.append(f"{name}: {r['path_error_m']:.4f} m off the loop, height off {r['height_error_m']:.4f} m")
        if abs(r["heading_error_deg"]) > HEADING_TOL_DEG or r["off_axis"] > OFF_AXIS_TOL:
            problems.append(f"{name}: heading {r['heading_deg']:.2f} deg is {r['heading_error_deg']:.2f} deg off the loop tangent "
                            f"(off axis {r['off_axis']:.4f})")
    rows["gap_m"] = (rows["engine"]["u_m"] - rows["car"]["u_m"]) % g["length_m"]
    rows["wheels"] = {}
    for w in g["wheels"]:
        ang, off = wheel_angle(q_of(v[w]))
        rows["wheels"][w] = ang
        if off > OFF_AXIS_TOL:
            problems.append(f"{w}: wheel rotation is not about +X only ({off:.4f})")
    return {**rows, "problems": problems}


def unwrap_loop(samples: list[tuple[float, float]], length: float) -> list[tuple[float, float]]:
    """(時刻, 弧の位置) の弧の位置を、周の長さで連続にする（隣の差は半周未満を前提）。"""
    out, acc, prev = [], 0.0, None
    for t, u in samples:
        acc = u if prev is None else acc + (u - prev + length / 2.0) % length - length / 2.0
        prev = u
        out.append((t, acc))
    return out


def fit_line(series: list[tuple[float, float]]) -> tuple[float, list[float]]:
    """直線の当てはめの傾きと、各点と直線の差（符号付き）。"""
    n = len(series)
    mt, ma = sum(t for t, _ in series) / n, sum(a for _, a in series) / n
    slope = sum((t - mt) * (a - ma) for t, a in series) / sum((t - mt) ** 2 for t, _ in series)
    return slope, [a - (ma + slope * (t - mt)) for t, a in series]


def timed_span(args: list[str]) -> tuple[float, float, dict]:
    """コマンドの前後の中点の時刻と、実行時間の半分（読んだ時刻の見積もりの幅）。"""
    t0 = time.time()
    data = run_json(args)
    t1 = time.time()
    return (t0 + t1) / 2.0, (t1 - t0) / 2.0, data


def check_speed(samples: list[tuple[float, float]], want: float, length: float, name: str,
                halves: list[float] | None = None) -> dict:
    """弧の位置の速さ（m/秒）を HMC_P3 の速さと比べ、各観察の直線からの差を、その観察の時刻の見積もりの幅（halves の秒 × 速さ）
    と RESIDUAL_MARGIN_M の和と比べる。隣の観察の間の進みが大きすぎれば測れないとする。"""
    out: dict = {"problems": []}
    if len(samples) < 4:
        return {"problems": [f"{name}: too few observations ({len(samples)})"]}
    halves = halves or [0.0] * len(samples)
    steps = [(b[1] - a[1]) % length for a, b in zip(samples, samples[1:])]
    if max(steps) > MAX_STEP_M:
        out["problems"].append(f"{name}: a step of {max(steps):.2f} m is too large to follow the loop")
    speed, resid = fit_line(unwrap_loop(samples, length))
    bounds = [max(want, 0.0) * h + RESIDUAL_MARGIN_M for h in halves]
    worst = max(range(len(resid)), key=lambda i: abs(resid[i]) / bounds[i])
    out.update({"m_per_s": round(speed, 4), "expected": round(want, 4), "max_step_m": round(max(steps), 3),
                "max_residual_m": round(max(abs(r) for r in resid), 3), "max_residual_over_bound": round(abs(resid[worst]) / bounds[worst], 3),
                "max_read_half_s": round(max(halves), 3), "samples": len(samples)})
    if want <= 0 or abs(speed - want) > SPEED_TOL * want:
        out["problems"].append(f"{name}: {speed:.3f} m/s != {want:.3f} m/s")
    if abs(resid[worst]) > bounds[worst]:
        out["problems"].append(f"{name}: an observation is {abs(resid[worst]):.2f} m off the line of the clock "
                               f"(tolerance {bounds[worst]:.2f} m for a read window of +-{halves[worst]:.2f} s)")
    return out


def check_clockwise(samples: list[dict]) -> dict:
    """先頭車の水平の位置の、線路の中心まわりの角度が減っていくか（上から見て時計回り。Blender の x・y、z が上）。経路の式（u）に
    よらず、観察した位置だけから決める。"""
    angs = [math.degrees(math.atan2(s["engine"]["plan"][1], s["engine"]["plan"][0])) for s in samples]
    total = sum(wrap_deg(b - a) for a, b in zip(angs, angs[1:]))
    problems = [] if total < -1.0 else [f"engine turned {total:.1f} deg about the loop centre (expected clockwise, negative)"]
    return {"turned_deg": round(total, 2), "problems": problems}


def check_travel(samples: list[dict]) -> dict:
    """隣の観察の間に先頭車・客車が進んだ向き（水平の弦）と、2 回の正面（ローカル +Z）の平均の向きの差。前へ進んでいるか。"""
    rows, problems = [], []
    for name in ("engine", "car"):
        for a, b in zip(samples, samples[1:]):
            pa, pb = a[name]["plan"], b[name]["plan"]
            dx, dy = pb[0] - pa[0], pb[1] - pa[1]
            if math.hypot(dx, dy) < 0.05:
                continue   # 止まっている
            fa, fb = a[name]["forward"], b[name]["forward"]
            fx, fy = fa[0] + fb[0], fa[2] + fb[2]   # 正面は Resonite の (x, z) = Blender の (x, y)
            err = wrap_deg(math.degrees(math.atan2(fx, fy) - math.atan2(dx, dy)))
            rows.append(round(err, 3))
            if abs(err) > TRAVEL_TOL_DEG:
                problems.append(f"{name} faces {err:.2f} deg away from the direction it travelled")
    if not rows:
        problems.append("the train did not move a measurable chord between the observations")
    return {"errors_deg": rows, "problems": problems}


def check_gap(samples: list[dict], g: dict, speed: float) -> dict:
    """同じ観察の中の先頭車と客車の弧の差（m）。同じ式なら W05 の 2.75 m より、客車を後に読む時刻の差 × 速さだけ短く見える。
    短く見える分（lag）が 0〜speed × その観察の実行時間（2 × half）の中か（客車が止まった・遅れた・先へ出た式を見つける）。"""
    rows = [(g["arc_offset_m"] - s["gap_m"], speed * 2.0 * s.get("half", 0.0) + GAP_TOL_M) for s in samples]
    bad = [(x, hi) for x, hi in rows if not (-GAP_TOL_M <= x <= hi)]
    problems = [f"engine-car arc gap is {g['arc_offset_m'] - bad[0][0]:.3f} m (expected {g['arc_offset_m']} m less 0..{bad[0][1]:.2f} m "
                f"of read lag)"] if bad else []
    lags = [x for x, _ in rows]
    return {"lag_m": [round(min(lags), 4), round(max(lags), 4)] if lags else None,
            "lag_over_bound": round(max(x / hi for x, hi in rows), 3) if rows else None, "problems": problems}


def check_wheels_turn(samples: list[dict], g: dict) -> dict:
    """動いている間に車輪の角度が変わっているか（止まった車輪を見つける。速さと向きはゆっくりの時刻で見る）。"""
    problems = []
    spread = {}
    for w in g["wheels"]:
        angs = [s["wheels"][w] for s in samples]
        spread[w] = round(max(abs(wrap_deg(b - a)) for a, b in zip(angs, angs[1:])), 2) if len(angs) > 1 else 0.0
        if spread[w] < 1.0:
            problems.append(f"{w}: wheel did not turn while the train moved")
    return {"max_step_deg": spread, "problems": problems}


def clock_offset(samples: list[tuple[float, float]], speed: float, length: float) -> float:
    """u − V t（m、0〜L）の円の平均。時刻から決まる u なら、窓が変わっても同じ値。"""
    k = 2.0 * math.pi / length
    s = sum(math.sin(k * (u - speed * t)) for t, u in samples)
    c = sum(math.cos(k * (u - speed * t)) for t, u in samples)
    return (math.atan2(s, c) / k) % length


# ---- 時刻を止めた標本 ---------------------------------------------------------------------------------------------------

def check_frozen(engine: tuple, car: tuple, wheels: dict[str, dict], params: dict, what: str = "relay",
                 g: dict | None = None) -> dict:
    """G15Speed = 0 の姿勢（進んだ距離 D = G15Phase × L）を式と照合する。engine・car は (位置, 回転)、wheels は部品 → 回転。
    先頭車か客車の弧の位置が W05 の経路点にあるときは、経路点のデータ（位置と向き）とも照合する（式から独立に見つける）。"""
    g = g or gimmicks.g15()
    problems, rows = [], {}
    dist = params["G15Phase"] * g["length_m"]
    cx, cy = g["center_local_blender"]
    for name, (pos, rot) in (("engine", engine), ("car", car)):
        root = g[name]
        u = (g["rest_arc_m"][root] + dist) % g["length_m"]
        want, th = gimmicks.g15_car_pose(u, g)
        p = [float(pos[k]) for k in "xyz"]
        head, off = heading_deg(q_of(rot))
        dpos = math.dist(p, want)
        dhead = abs(wrap_deg(head - math.degrees(th)))
        rows[name] = {"u_m": round(u, 4), "position_error_m": round(dpos, 6), "heading_error_deg": round(dhead, 4)}
        if dpos > FROZEN_POS_TOL_M or dhead > FROZEN_DEG_TOL or off > OFF_AXIS_TOL:
            problems.append(f"{what}: {name} at {[round(x, 4) for x in p]} heading {head:.3f} != {[round(x, 4) for x in want]} "
                            f"{math.degrees(th):.3f} at phase {params['G15Phase']}")
        hit = [k for k, a in enumerate(g["waypoint_arc_m"]) if abs((u - a + g["length_m"] / 2) % g["length_m"] - g["length_m"] / 2) < 1e-4]
        if hit:
            wp = g["waypoints"][hit[0]]
            wpos = [cx + float(wp["position_local"][0]), float(wp["position_local"][2]) - g["origin_world"][2],
                    cy + float(wp["position_local"][1])]
            dwp = math.dist(p, wpos)
            dyaw = abs(wrap_deg(head + float(wp["yaw_z_deg"])))   # Blender の Z まわり = Resonite の Y まわりの負
            rows[name].update({"waypoint": hit[0], "waypoint_error_m": round(dwp, 6), "waypoint_yaw_error_deg": round(dyaw, 4)})
            if dwp > FROZEN_POS_TOL_M or dyaw > FROZEN_DEG_TOL:
                problems.append(f"{what}: {name} is {dwp:.4f} m / {dyaw:.3f} deg from waypoint {hit[0]}")
    for w, spec in g["wheels"].items():
        want = wheel_q(dist, spec["radius_m"])
        d = q_close(q_of(wheels[w]), want)
        rows[w] = {"q_error": round(d, 7)}
        if d > FROZEN_Q_TOL:
            problems.append(f"{what}: {w} rotation {q_of(wheels[w])} != {tuple(round(x, 5) for x in want)} at phase {params['G15Phase']}")
    return {"rows": rows, "problems": problems}


def frozen_slots(hier: dict, g: dict | None = None) -> tuple:
    """hierarchy の観察（D の root）から、先頭車・客車の (位置, 回転) と、車輪の回転。"""
    g = g or gimmicks.g15()
    asset = _child(hier, g["asset_id"])
    out = {}
    for name in ("engine", "car"):
        node = _child(asset, g[name])
        if node is None:
            raise SystemExit(f"{g[name]} is not observed under {g['asset_id']}")
        out[name] = (node["position"], node["rotation"])
    wheels = {}
    for w, spec in g["wheels"].items():
        node = _child(_child(asset, spec["parent"]), w)
        if node is None:
            raise SystemExit(f"{w} is not observed under {spec['parent']}")
        wheels[w] = node["rotation"]
    return out["engine"], out["car"], wheels


# ---- 構造 --------------------------------------------------------------------------------------------------------------

def m06_declaration() -> dict:
    d = sorted((PROJECT_ROOT / "exports" / "p2_meshy").glob("M06-*/p2m.apply.json"))
    if not d:
        raise SystemExit("no exports/p2_meshy/M06-*/p2m.apply.json (copy the p2_bundles first)")
    return json.loads(d[-1].read_text(encoding="utf-8"))


def check_structure(d_root: dict, doc: dict | None = None, m06: dict | None = None) -> dict:
    """列車と線路の子孫と、仮の車体の下の M06 が、宣言と同じパスで同じローカルの変換か。駆動される項目は比べない（先頭車・
    客車の root は位置と回転、車輪は回転）。車輪の位置と、駆動される Slot の拡縮は比べる。"""
    g = gimmicks.g15()
    doc = doc or latest_declaration(g["district"])
    m06 = m06 or m06_declaration()
    driven = {g["engine"]: ("position", "rotation"), g["car"]: ("position", "rotation"), **{w: ("rotation",) for w in g["wheels"]}}
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

    for asset in (g["asset_id"], g["track_asset_id"]):
        decl = _find_decl(doc, asset)
        live = _child(d_root, asset)
        if decl is None or live is None:
            problems.append(f"{asset}: missing")
            continue
        compare((asset,), live, decl["slot"])
        for path, node in _decl_paths(decl):
            lv = live
            for n in path:
                lv = _child(lv, n)
            compare((asset, *path), lv, node["slot"])
    # M06 の素材の宣言（親は先頭車の root の下の仮の車体）。root とその子孫
    parent = m06["slot"]["parent"].split("/")
    shell = _child(_child(_child(d_root, g["asset_id"]), g["engine"]), parent[-1])
    base = (g["asset_id"], g["engine"], parent[-1])
    m06_live = _child(shell, m06["slot"]["name"])
    compare((*base, m06["slot"]["name"]), m06_live, m06["slot"])
    for path, node in _decl_paths(m06):
        lv = m06_live
        for n in path:
            lv = _child(lv, n)
        compare((*base, m06["slot"]["name"], *path), lv, node["slot"])
    return {"rows": rows, "problems": problems}


def d_hierarchy(url: str, depth: int = 6) -> dict:
    return run_json(["resoloop", "hierarchy", "--under", f"{gimmicks.P2_ROOT}/{gimmicks.g15()['district']}", "--depth", str(depth),
                     "--url", url, "--json"])


def check_relays(url: str, keys: dict[str, str]) -> list[str]:
    """中継の Drives が Slot のメンバーを指し、有効か。"""
    g = gimmicks.g15()
    targets = [(n, m) for n in (g["engine"], g["car"]) for m in ("Position", "Rotation")] + [(w, "Rotation") for w in g["wheels"]]
    sels = [f"$member:{district.relay_key(keys[n], m, 'g15')}.{mem}" for n, m in targets for mem in ("Drives", "Enabled")]
    data = run_json(["resoloop", "observe", *sels, "--state", str(D_STATE), "--url", url, "--json"])["data"]["values"]
    problems = []
    ids: dict[str, dict] = {}
    for n, m in targets:
        if n not in ids:
            ids[n] = run_json(["resoloop", "inspect", f"$slot:{keys[n]}", "--state", str(D_STATE), "--members", "--url", url,
                               "--json"])["data"]["members"]
        sel = f"$member:{district.relay_key(keys[n], m, 'g15')}"
        elems = data[f"{sel}.Drives"]["member"]["elements"]
        if data[f"{sel}.Enabled"]["member"]["value"] is not True:
            problems.append(f"{n}: relay {m} is disabled")
        if [e.get("targetId") for e in elems] != [ids[n][m]["id"]]:
            problems.append(f"{n}: relay {m} does not drive the Slot {m}")
    return problems


# ---- 包絡（バンドルのメッシュから。観察ではない） -----------------------------------------------------------------------

def _world_points(bundle: Path, doc: dict, node: dict, parent_q=(0.0, 0.0, 0.0, 1.0), parent_t=(0.0, 0.0, 0.0)) -> list[tuple]:
    s = node["slot"]
    q = tuple(s.get("rotation") or (0, 0, 0, 1))
    p = s.get("position") or (0, 0, 0)
    rp = qrot(parent_q, p)
    return _local_points(bundle, doc, node, qmul(parent_q, q), (parent_t[0] + rp[0], parent_t[1] + rp[1], parent_t[2] + rp[2]))


def train_points(doc: dict, g: dict) -> dict[str, list[tuple]]:
    """先頭車・客車の root のローカルの頂点（Resonite）。仮の車体（描画を止めている）の代わりに M06 の素材のメッシュ。"""
    bundle = _bundle(g["district"])
    asset = _find_decl(doc, g["asset_id"])
    m06 = m06_declaration()
    m06_dir = sorted((PROJECT_ROOT / "exports" / "p2_meshy").glob("M06-*/p2m.apply.json"))[-1].parent
    shell_name = m06["slot"]["parent"].split("/")[-1]
    out = {}
    for name in ("engine", "car"):
        root = next(c for c in asset["children"] if c["slot"]["name"] == g[name])
        pts = []
        for ch in root.get("children", []):
            if ch["slot"]["name"] == shell_name:
                s = ch["slot"]
                sq, sp = tuple(s.get("rotation") or (0, 0, 0, 1)), s.get("position") or (0, 0, 0)
                pts += _world_points(m06_dir, m06, m06, sq, sp)
            else:
                pts += _world_points(bundle, doc, ch)
        out[name] = pts[::max(1, len(pts) // 1200)]
    return out


def _routes() -> list[dict]:
    w = json.loads((PROJECT_ROOT / "layout" / "world_layout.json").read_text(encoding="utf-8"))
    return [r for r in w["routes"] if "D_amusement" in (r.get("from_area"), r.get("to_area"))]


def _in_corridor(p: tuple, route: dict) -> bool:
    """Blender の水平の位置 p が、経路の折れ線から幅の半分の内側にあるか。"""
    half = float(route["width_m"]) / 2.0
    pts = route["waypoints"]
    for a, b in zip(pts, pts[1:]):
        ax, ay, bx, by = float(a[0]), float(a[1]), float(b[0]), float(b[1])
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
        if math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy) <= half:
            return True
    return False


def box_distance(b: dict, p: tuple) -> float:
    """点 p と外接箱 b（min・max）の距離。箱の中なら 0。"""
    return math.sqrt(sum(max(b["min"][k] - p[k], 0.0, p[k] - b["max"][k]) ** 2 for k in range(3)))


def static_boxes(doc: dict, g: dict) -> dict[str, dict]:
    """D の root の直下の物（列車・線路・広場の床を除く）の、バンドルのメッシュの外接箱（Blender の世界座標）。"""
    bundle = _bundle(g["district"])
    skip = {g["asset_id"], g["track_asset_id"], "Blender_Providers"}
    out = {}
    for ch in doc.get("children", []):
        name = ch["slot"]["name"]
        if name in skip or name.endswith("_FixedCollision"):
            continue
        pts = _world_points(bundle, doc, ch)
        if not pts:
            continue
        b = [(x, z, y) for x, y, z in pts]
        out[name] = {"min": [min(p[i] for p in b) for i in range(3)], "max": [max(p[i] for p in b) for i in range(3)]}
    return out


def envelopes(doc: dict | None = None, step_m: float = 0.2) -> dict:
    g = gimmicks.g15()
    doc = doc or latest_declaration(g["district"])
    pts = train_points(doc, g)
    asset = _find_decl(doc, g["asset_id"])
    ap = asset["slot"].get("position") or [0, 0, 0]          # Resonite の (x, y, z)。回転は単位（列車の asset root）
    excl = json.loads((PROJECT_ROOT / "layout" / "areas" / f"{g['district']}.json").read_text(encoding="utf-8"))["Exclusions"]
    routes = _routes()
    boxes = static_boxes(doc, g)
    # 広場の床は列車の下にも広がる（外接箱の上面は別の場所の縁石）。床・線路との交差は Blender の三角形の確かめで見る
    boxes.pop(next(n for n in boxes if n.startswith("DAM_AmusementPlaza")))
    # 線路のまわり（曲線の中心から 8 m）の外接箱だけを見る（遠い物は入り得ない）
    tc = (ap[0] + g["center_local_blender"][0], ap[2] + g["center_local_blender"][1])
    reach = g["radius_m"] + 3.5
    boxes = {k: b for k, b in boxes.items() if b["min"][0] <= tc[0] + reach and b["max"][0] >= tc[0] - reach
             and b["min"][1] <= tc[1] + g["straight_m"] / 2 + reach and b["max"][1] >= tc[1] - g["straight_m"] / 2 - reach}
    near: dict[str, float] = {}
    inside: dict[str, int] = {}
    in_route: dict[str, int] = {}
    in_excl: dict[str, int] = {}
    lowest = math.inf
    cx, cy = g["center_local_blender"]
    out_r, in_r = 0.0, math.inf
    n = round(g["length_m"] / step_m)
    for i in range(n):
        for name in ("engine", "car"):
            u = g["rest_arc_m"][g[name]] + i * step_m
            pos, th = gimmicks.g15_car_pose(u, g)
            q = (0.0, math.sin(th / 2.0), 0.0, math.cos(th / 2.0))
            for v in pts[name]:
                r = qrot(q, v)
                wb = (ap[0] + pos[0] + r[0], ap[2] + pos[2] + r[2], ap[1] + pos[1] + r[1])   # Blender の世界座標
                lowest = min(lowest, wb[2])
                tx, ty = wb[0] - ap[0] - cx, wb[1] - ap[2] - cy
                ry = ty - math.copysign(min(abs(ty), g["straight_m"] / 2.0), ty)
                d = math.hypot(tx, ry)
                out_r, in_r = max(out_r, d), min(in_r, d)
                for rt in routes:
                    if _in_corridor(wb, rt):
                        in_route[rt["route_id"]] = in_route.get(rt["route_id"], 0) + 1
                for e in excl:
                    lo, hi = e["bounds"]["min"], e["bounds"]["max"]
                    if all(lo[k] <= wb[k] <= hi[k] for k in range(3)):
                        in_excl[e["zone_id"]] = in_excl.get(e["zone_id"], 0) + 1
                for bn, b in boxes.items():
                    dd = box_distance(b, wb)
                    if dd < near.get(bn, math.inf):
                        near[bn] = dd
                    if dd == 0.0:
                        inside[bn] = inside.get(bn, 0) + 1
    nearest = sorted(near.items(), key=lambda kv: kv[1])[:8]
    return {"step_m": step_m, "positions": n, "points": {k: len(v) for k, v in pts.items()}, "static_boxes": sorted(boxes),
            "swept_radius_from_curve_centres_m": [round(in_r, 4), round(out_r, 4)], "lowest_m": round(lowest, 4),
            "points_in_routes": in_route, "points_in_exclusions": in_excl,
            "points_in_static_boxes": inside, "nearest_static_boxes_m": [[k, round(v, 4)] for k, v in nearest]}


def envelope_problems(env: dict) -> list[str]:
    problems = []
    if env["points_in_routes"]:
        problems.append(f"G15: the train enters a W01 route {env['points_in_routes']}")
    if env["points_in_exclusions"]:
        problems.append(f"G15: the train enters a D exclusion zone {env['points_in_exclusions']}")
    if env["points_in_static_boxes"]:
        problems.append(f"G15: the train enters the bounding box of {env['points_in_static_boxes']}")
    return problems


# ---- 観察 ------------------------------------------------------------------------------------------------------------

def observe_params(url: str) -> dict:
    v = gimmicks.G15_VARIABLES
    sels = [f"$member:{s['key']}.Value" for s in v.values()]
    data = run_json(["resoloop", "observe", *sels, "--state", str(P3_STATE), "--url", url, "--json"])["data"]["values"]
    return {n: float(data[f"$member:{s['key']}.Value"]["member"]["value"]) for n, s in v.items()}


def _ids(url: str) -> dict[str, str]:
    return {n: component_id(f"$member:{s['key']}.Value", P3_STATE, url) for n, s in gimmicks.G15_VARIABLES.items()}


def read_values(obs_values: dict[str, dict], sels: dict[str, str]) -> dict:
    return {name: obs_values[sel]["member"]["value"] for name, sel in sels.items() if sel in obs_values}


def frozen_probe(url: str, raw: list, phase: float = 0.5) -> dict:
    """時刻を止めた標本（G15Speed = 0、G15Phase = phase）を Slot そのもので取り、値を戻す。窓ごとに取り、窓の間で比べる。"""
    ids = _ids(url)
    before = observe_params(url)
    try:
        set_member(ids["G15Speed"], "Value", "0", url)
        set_member(ids["G15Phase"], "Value", str(phase), url)
        time.sleep(1.5)
        params = params_of(observe_params(url))
        hier = d_hierarchy(url, depth=4)
        raw.append({"kind": "frozen_probe", "data": hier})
        engine, car, wheels = frozen_slots(hier["data"])
    finally:
        for n in ("G15Speed", "G15Phase"):
            set_member(ids[n], "Value", str(before[n]), url)
    restored = observe_params(url)
    res = check_frozen(engine, car, wheels, params, "slot")
    problems = list(res["problems"])
    if restored != before:
        problems.append(f"frozen probe: variables not restored: {restored} != {before}")
    return {"params": params, "rows": res["rows"],
            "slots": {"engine": [round(float(engine[0][k]), 5) for k in "xyz"], "car": [round(float(car[0][k]), 5) for k in "xyz"],
                      "wheels": {w: [round(float(q[k]), 6) for k in "xyzw"] for w, q in wheels.items()}},
            "problems": problems}


def check_drift(probes: list[dict], offsets: list[float], length: float) -> dict:
    """窓ごとの時刻を止めた標本を最初の窓と比べ（同じ位相の位置の差 1 cm 以内、車輪の回転の差）、u − V t の差も見る。"""
    rows, problems = [], []
    if len(probes) < 2:
        return {"rows": rows, "problems": ["drift: needs two windows"]}
    base = probes[0]["slots"]
    for i, p in enumerate(probes[1:], start=2):
        if p["params"] != probes[0]["params"]:
            problems.append(f"drift: window {i} was probed with other values {p['params']}")
        for name in ("engine", "car"):
            d = math.dist(base[name], p["slots"][name])
            rows.append({"window": i, "slot": name, "position_diff_m": round(d, 6)})
            if d > DRIFT_TOL_M:
                problems.append(f"drift: {name} moved {d:.4f} m at the same phase by window {i}")
        for w, q in base["wheels"].items():
            dq = q_close(q, p["slots"]["wheels"][w])
            if dq > math.radians(DRIFT_TOL_DEG) / 2.0:
                problems.append(f"drift: {w} rotation differs {dq:.5f} at the same phase by window {i}")
    for i, off in enumerate(offsets[1:], start=2):
        d = abs((off - offsets[0] + length / 2.0) % length - length / 2.0)
        rows.append({"window": i, "clock_offset_diff_m": round(d, 3)})
        if d > CLOCK_OFFSET_TOL_M:
            problems.append(f"drift: u - V t moved {d:.2f} m between windows 1 and {i}")
    return {"rows": rows, "clock_offsets_m": [round(o, 3) for o in offsets], "problems": problems}


def observe_window(url: str, duration: float, engine_duration: float, raw: list) -> dict:
    g = gimmicks.g15()
    keys = d_keys(STATE_DIR)
    sels = selectors(keys, g)
    params_raw = observe_params(url)
    params = params_of(params_raw)
    window: dict = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "params": params_raw, "samples": [],
                    "problems": []}
    hier = d_hierarchy(url)
    raw.append({"kind": "hierarchy_start", "data": hier})
    window["structure_start"] = check_structure(hier["data"])
    window["relay_problems"] = check_relays(url, keys)
    window["frozen_probe"] = frozen_probe(url, raw)
    # 先頭車の位置だけを続けて観察する（1 回 約 1.5 秒）
    eng, eng_half = [], []
    t_end = time.time() + engine_duration
    while time.time() < t_end:
        t, half, obs = timed_span(["resoloop", "observe", sels["engine_pos"], "--state", str(D_STATE), "--url", url, "--json"])
        raw.append({"kind": "engine", "t": t, "half": half, "data": obs})
        pos = obs["data"]["values"][sels["engine_pos"]]["member"]["value"]
        cx, cy = g["center_local_blender"]
        eng.append((t, gimmicks.stadium_arc(float(pos["x"]) - cx, float(pos["z"]) - cy, g["radius_m"], g["straight_m"])[0]))
        eng_half.append(half)
    # 全部の駆動の値
    t_end = time.time() + duration
    while time.time() < t_end:
        t, half, obs = timed_span(["resoloop", "observe", *sels.values(), "--state", str(D_STATE), "--url", url, "--json"])
        raw.append({"kind": "all", "t": t, "half": half, "data": obs})
        s = check_sample(read_values(obs["data"]["values"], sels), g)
        s["t"] = round(t, 3)
        s["half"] = round(half, 3)
        window["samples"].append(s)
    hier2 = d_hierarchy(url)
    raw.append({"kind": "hierarchy_end", "data": hier2})
    window["structure_end"] = check_structure(hier2["data"])
    smp = window["samples"]
    speed = params["G15Speed"]
    halves = [s["half"] for s in smp]
    window["speeds"] = {"engine_only": check_speed(eng, speed, g["length_m"], "engine", eng_half),
                        "engine": check_speed([(s["t"], s["engine"]["u_m"]) for s in smp], speed, g["length_m"], "engine (all)", halves),
                        "car": check_speed([(s["t"], s["car"]["u_m"]) for s in smp], speed, g["length_m"], "car (all)", halves)}
    window["clockwise"] = check_clockwise(smp)
    window["travel"] = check_travel(smp)
    window["gap"] = check_gap(smp, g, speed)
    window["wheels"] = check_wheels_turn(smp, g)
    window["clock_offset_m"] = clock_offset(eng, speed, g["length_m"]) if eng else None
    window["summary"] = {
        "samples": len(smp), "engine_samples": len(eng),
        "path_error_m": round(max(max(s["engine"]["path_error_m"], s["car"]["path_error_m"]) for s in smp), 5),
        "height_error_m": round(max(max(s["engine"]["height_error_m"], s["car"]["height_error_m"]) for s in smp), 6),
        "heading_error_deg": round(max(max(abs(s["engine"]["heading_error_deg"]), abs(s["car"]["heading_error_deg"])) for s in smp), 3),
        "engine_u_m": [round(min(s["engine"]["u_m"] for s in smp), 2), round(max(s["engine"]["u_m"] for s in smp), 2)],
    }
    for s in smp:
        window["problems"].extend(s["problems"])
    for part in ("engine_only", "engine", "car"):
        window["problems"] += window["speeds"][part]["problems"]
    window["problems"] += (window["clockwise"]["problems"] + window["travel"]["problems"] + window["gap"]["problems"]
                           + window["wheels"]["problems"] + window["relay_problems"] + window["frozen_probe"]["problems"]
                           + window["structure_start"]["problems"] + window["structure_end"]["problems"])
    window["ok"] = not window["problems"]
    return window


# ---- 外から変えられる値の確認 -------------------------------------------------------------------------------------------

def _frozen_case(url: str, label: str, sels: dict[str, str], raw: list) -> dict:
    time.sleep(1.0)
    params_raw = observe_params(url)
    params = params_of(params_raw)
    _, _, obs = timed_span(["resoloop", "observe", *sels.values(), "--state", str(D_STATE), "--url", url, "--json"])
    hier = d_hierarchy(url, depth=4)
    raw.append({"kind": f"frozen_{label}", "data": [obs, hier]})
    v = read_values(obs["data"]["values"], sels)
    g = gimmicks.g15()
    relay = check_frozen((v["engine_pos"], v["engine_rot"]), (v["car_pos"], v["car_rot"]), {w: v[w] for w in g["wheels"]}, params,
                         "relay")
    slot = check_frozen(*frozen_slots(hier["data"]), params, "slot")
    return {"params": params_raw, "relay": relay["rows"], "slot": slot["rows"], "problems": relay["problems"] + slot["problems"]}


def _series(url: str, sels: dict[str, str], names: list[str], seconds: float, raw: list, label: str) -> list[tuple[float, dict]]:
    out = []
    t_end = time.time() + seconds
    while time.time() < t_end:
        t, half, obs = timed_span(["resoloop", "observe", *[sels[n] for n in names], "--state", str(D_STATE), "--url", url, "--json"])
        raw.append({"kind": label, "t": t, "half": half, "data": obs})
        out.append((t, read_values(obs["data"]["values"], sels), half))
    return out


def _arc(pos: dict, g: dict) -> float:
    cx, cy = g["center_local_blender"]
    return gimmicks.stadium_arc(float(pos["x"]) - cx, float(pos["z"]) - cy, g["radius_m"], g["straight_m"])[0]


def check_clock(series: list[tuple[float, dict]], speed: float, g: dict) -> dict:
    """ゆっくりの時刻の観察の列から、先頭車・客車の弧の速さを HMC_P3 の速さと、車輪の +X まわりの回る速さ（rad/秒）を、同じ観察の
    列で測った先頭車（客車の車輪は客車）の速さ ÷ 半径と比べる。車輪の角度が増える（+X まわりの正 = 上端が前へ進む）ことで、前へ
    転がる向きを確かめる。"""
    out: dict = {"problems": []}
    for name in ("engine", "car"):
        u = unwrap_loop([(t, _arc(v[f"{name}_pos"], g)) for t, v, *_ in series], g["length_m"])
        sp, _ = fit_line(u)
        out[name] = {"m_per_s": round(sp, 5), "advance_m": round(u[-1][1] - u[0][1], 4)}
        out[f"_{name}_speed"] = sp
        if abs(sp - speed) > CLOCK_TOL * speed:
            out["problems"].append(f"clock: {name} moved at {sp:.4f} m/s, expected {speed}")
    for w, spec in g["wheels"].items():
        angs, acc, prev = [], 0.0, None
        for t, v, *_ in series:
            a = math.radians(wheel_angle(q_of(v[w]))[0])
            acc = a if prev is None else acc + (a - prev + math.pi) % (2 * math.pi) - math.pi
            prev = a
            angs.append((t, acc))
        rate, _ = fit_line(angs)
        moved = out["_engine_speed"] if spec["parent"] == g["engine"] else out["_car_speed"]
        want = moved / spec["radius_m"]
        out[w] = {"rad_per_s": round(rate, 5), "expected_from_measured_speed": round(want, 5)}
        if want <= 0 or abs(rate - want) > WHEEL_RATIO_TOL * want:
            out["problems"].append(f"clock: {w} turned at {rate:.4f} rad/s about +X, expected {want:.4f} (rolling forward)")
    out.pop("_engine_speed")
    out.pop("_car_speed")
    return out


def param_check(url: str, raw: list) -> dict:
    out: dict = {"problems": []}
    g = gimmicks.g15()
    keys = d_keys(STATE_DIR)
    sels = selectors(keys, g)
    ids = _ids(url)
    before = observe_params(url)
    out["before"] = before
    length = g["length_m"]

    def put(name: str, value: float) -> None:
        set_member(ids[name], "Value", str(value), url)

    try:
        # 0) 時刻を止めた標本: 先頭車か客車が W05 の経路点に来る位相（点 0・3・6・10・13・16・19 と、客車が点 6・16）
        put("G15Speed", 0.0)
        cases = [("engine", k) for k in (0, 3, 6, 10, 13, 16, 19)] + [("car", 6), ("car", 16)]
        for who, k in cases:
            phase = ((g["waypoint_arc_m"][k] - g["rest_arc_m"][g[who]]) % length) / length
            put("G15Phase", phase)
            case = _frozen_case(url, f"{who}_waypoint_{k}", sels, raw)
            out[f"frozen_{who}_waypoint_{k}"] = case
            out["problems"].extend(case["problems"])
        # 1) 範囲の外の位相。収めないと 1.5 は周の反対側、-1 は車輪が逆に回った姿勢
        for value, label in ((1.5, "phase_1.5"), (-1.0, "phase_-1")):
            put("G15Phase", value)
            case = _frozen_case(url, label, sels, raw)
            out[f"frozen_{label}"] = case
            out["problems"].extend(case["problems"])
        put("G15Phase", before["G15Phase"])
        # 2) 範囲の外の速さ -1（止まる）: 3 秒あけた 2 回の観察が同じ
        put("G15Speed", -1.0)
        time.sleep(1.0)
        s = _series(url, sels, ["engine_pos"], 4.0, raw, "speed_-1")
        moved = max(math.dist([float(a["engine_pos"][k]) for k in "xyz"], [float(b["engine_pos"][k]) for k in "xyz"])
                    for (_, a, _), (_, b, _) in zip(s, s[1:])) if len(s) > 1 else math.inf
        out["speed_-1"] = {"max_move_m": round(moved, 6), "samples": len(s)}
        if moved > 1e-4:
            out["problems"].append(f"G15Speed -1: the train moved {moved:.4f} m (expected to stop)")
        # 3) 速さを変える（1.1 は既定の半分、10 は 3 m/s に収まる）
        for value in SPEED_CASES:
            put("G15Speed", value)
            time.sleep(1.0)
            want = params_of({**before, "G15Speed": value})["G15Speed"]
            s = _series(url, sels, ["engine_pos"], 12.0, raw, f"speed_{value}")
            res = check_speed([(t, _arc(v["engine_pos"], g)) for t, v, _ in s], want, length, f"G15Speed {value}", [h for *_, h in s])
            out[f"speed_{value}"] = res
            out["problems"].extend(res["problems"])
    finally:
        for name in before:
            put(name, before[name])
    # 4) ゆっくりの時刻
    try:
        put("G15Speed", CLOCK_SPEED)
        time.sleep(1.0)
        s = _series(url, sels, ["engine_pos", "car_pos", *g["wheels"]], CLOCK_WAIT_S, raw, "clock")
        out["clock"] = check_clock(s, CLOCK_SPEED, g)
        out["clock"]["samples"] = len(s)
        out["problems"].extend(out["clock"]["problems"])
    finally:
        put("G15Speed", before["G15Speed"])
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
    ap.add_argument("--engine-duration", type=float, default=20.0, help="先頭車の位置だけを観察する秒数")
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
            wins.append(observe_window(args.url, args.duration, args.engine_duration, raw))
        env = envelopes()
        drift = check_drift([w["frozen_probe"] for w in wins], [w["clock_offset_m"] for w in wins], gimmicks.g15()["length_m"])
        result = {"windows": wins, "gap_s": args.gap if args.windows > 1 else None, "drift": drift, "envelopes": env,
                  "envelope_problems": envelope_problems(env),
                  "tolerances": {"path_m": PATH_TOL_M, "height_m": HEIGHT_TOL_M, "heading_deg": HEADING_TOL_DEG,
                                 "travel_deg": TRAVEL_TOL_DEG, "frozen_pos_m": FROZEN_POS_TOL_M, "frozen_deg": FROZEN_DEG_TOL,
                                 "speed": SPEED_TOL, "residual_margin_m": RESIDUAL_MARGIN_M, "gap_m": GAP_TOL_M, "drift_m": DRIFT_TOL_M,
                                 "clock_offset_m": CLOCK_OFFSET_TOL_M, "local": LOCAL_TOL}}
        drift_problems = drift["problems"] if args.windows > 1 else []
        result["ok"] = all(w["ok"] for w in wins) and not result["envelope_problems"] and not drift_problems
    args.raw_out.parent.mkdir(parents=True, exist_ok=True)
    args.raw_out.write_text(json.dumps(raw, ensure_ascii=False) + "\n", encoding="utf-8")
    if not args.param_check:
        # コミットする記録には観察の列を入れない（要約と問題だけ）。列は --raw-out にある
        for w in result["windows"]:
            w["samples"] = [{"t": s["t"], "half_s": s["half"], "gap_m": round(s["gap_m"], 4),
                             **{n: {k: round(s[n][k], 4) for k in ("u_m", "path_error_m", "heading_error_deg")} for n in ("engine", "car")}}
                            for s in w["samples"]]
            w["structure_start"]["rows"] = len(w["structure_start"]["rows"])
            w["structure_end"]["rows"] = len(w["structure_end"]["rows"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {k: v for k, v in result.items() if k not in ("windows",) and not k.startswith("frozen_")}
    if not args.param_check:
        summary["windows"] = [{"ok": w["ok"], "summary": w["summary"], "speeds": w["speeds"], "gap": w["gap"],
                               "clockwise": w["clockwise"], "problems": w["problems"][:10]} for w in result["windows"]]
    print(json.dumps(summary, ensure_ascii=False, indent=1, default=str)[:6000])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
