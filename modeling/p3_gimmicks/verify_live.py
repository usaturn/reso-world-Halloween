"""W10: Resonite で動いている G13（メリーゴーラウンドの床の回転）と G01（小カボチャのダンス）を、時間を空けた観察から検査する。

実行（プロジェクトのディレクトリ。対象のワールドを Resonite の前面に出しておく。背面では駆動が進まない）:
    uv run python modeling/p3_gimmicks/verify_live.py --url ws://localhost:<PORT>/ \\
        --raw-out <Git の外の JSON> --output review/p3_gimmicks/live_checks.json [--windows 2 --gap 300]
    # 外から変えられる値の確認（値を変えて測り、元に戻す。ワールドに書く）
    uv run python modeling/p3_gimmicks/verify_live.py --url ... --raw-out ... --output review/p3_gimmicks/param_checks.json --param-check

観察（窓ごと。--windows の数だけ、--gap 秒あけて繰り返す）
- G13: TurnRoot の回転（resoloop inspect）を待ち時間なしで --duration 秒（1 回 約 2 秒）。観察の前後の時刻の中点を時刻にする。
  隣の観察の間に 150° を超えて回り得るほど間があいたら問題にする（角度を連続にできない）
- G01: G13 の後に --duration 秒、6 体の中継（ValueMultiDriver）の Value 12 個を 1 回の resoloop observe で読む（Component
  ごとの読み取りは順番だが 0.3 秒ほどで終わる）。中継の Drives が Body の Position・Rotation を指していることも observe で確かめる
- 構造: 窓の最初と最後に resoloop hierarchy で、TurnRoot の子・Body の子・台座のローカルの変換が宣言のままか

検査
- G13: 回転は Y 軸まわりだけ。回した +X 軸の向きの角度（東 → 北が正。上から見て反時計回り）を時刻で直線に当てはめた傾きが、
  W05 の速さ（Blender の +Z まわり、上から見て反時計回り）と 5% 以内。TurnRoot の位置と、子のローカルの変換が宣言どおり
- G01: 位置は基準から上下だけ（水平のずれ 1 mm 以内）、上下は I×W02 の範囲、回転はローカル Z まわりだけで I×W02 の傾きの範囲。
  I は HMC_P3 の値を観察して使う。上下と傾きは別の Component で読む時刻がずれるので、動いている間は式との一致を見ない。
  各個体の上下・傾きの幅が範囲の 15% 未満なら「動いていない」とする（時刻の項が止まったグラフを合格にしない）。中継が有効か
- --param-check: G01Frequency = 0（時刻を止める）で各個体の中継の値と Body の Slot そのものが式（θ = s φ）の値と一致するか、
  G01PhaseSpread = 0 で全員が θ = 0 か（式・位相・中継の結び先と、中継が Body を駆動していることの確認）。G01Frequency を
  ゆっくり（0.004 Hz）にして 20 秒の間に θ/2 が時刻どおり進むか、位相差が W02 の値か。G01Intensity 0.5・0 で範囲が縮むか。G13 の速さを半分にして測り直す。
  Spinner を 8 秒止めて再開した角度が、止める前の時刻の延長上にあるか（ワールドの時刻から角度を決めているか）。どれも元に戻す
- 包絡: 動く物の水平の広がり（バンドルのメッシュから計算。観察ではない）を記録し、G01 は W02 の envelope_radius_m と、
  G13 は人の高さより下の部分が台座（Base）の半径の内側かを比べる。外れたら最終の判定を不合格にする
- 構造: TurnRoot の子孫と各カボチャの台座・取付位置を、宣言と同じパス（親子関係）でたどってローカルの変換を比べる
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from modeling.p3_gimmicks import district, gimmicks  # noqa: E402
from modeling.p3_gimmicks.rest_pose import latest_declaration  # noqa: E402

STATE_DIR = Path("/workspaces/reso-world/worlds/reso-world-Halloween/.resoloop/state")
SPEED_TOL = 0.05
MAX_STEP_DEG = 150.0   # G13 の隣の観察の間に回り得る角度の上限（角度を連続にする前提は ±180° 未満）
LIFT_TOL_M = 0.002
TILT_TOL_DEG = 0.2
HORIZ_TOL_M = 0.001
FROZEN_LIFT_TOL_M = 0.0005
FROZEN_TILT_TOL_DEG = 0.05
CLOCK_TOL_DEG = 2.0      # ゆっくりの時刻での θ/2 の進みと位相差の許容
CLOCK_FREQUENCY = 0.004  # ゆっくりの時刻の G01Frequency（Hz）。θ/2 は 0.72°/s で、1 回の observe の中の読み取りのずれ（約 1 秒）が 1° 未満
CLOCK_WAIT_S = 20.0      # ゆっくりの時刻の 2 回の観察の間（θ/2 は約 14° 進む）
VARIATION = 0.15         # 動いている間、各個体の上下・傾きの幅が範囲のこの割合より小さければ「動いていない」
LOCAL_TOL = 1e-4
HEAD_HEIGHT_M = 2.2   # G13 の包絡: 床の上面からこの高さまでの回る部分を、人がぶつかり得る部分とする


def run_json(args: list[str]) -> dict:
    proc = subprocess.run(args, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    out = proc.stdout
    start = out.find("{")
    if proc.returncode != 0 or start < 0:
        raise SystemExit(f"{' '.join(args[:3])} failed ({proc.returncode}): {out[-1500:]} {proc.stderr[-800:]}")
    return json.loads(out[start:])


def timed(args: list[str]) -> tuple[float, dict]:
    t0 = time.time()
    data = run_json(args)
    return (t0 + time.time()) / 2.0, data


# ---- 幾何 -------------------------------------------------------------------------------------------------------

def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qrot(q, v):
    x, y, z, w = q
    r = qmul(qmul(q, (v[0], v[1], v[2], 0.0)), (-x, -y, -z, w))
    return r[:3]


def q_of(d: dict) -> tuple:
    return (float(d["x"]), float(d["y"]), float(d["z"]), float(d["w"]))


def yaw_deg(q) -> float:
    """回した +X 軸の水平の向き。atan2(z, x) の度（東 = 0、北 = 90）。"""
    v = qrot(q, (1.0, 0.0, 0.0))
    return math.degrees(math.atan2(v[2], v[0]))


def fit_speed(samples: list[tuple[float, float]]) -> float:
    """(時刻, 角度) の角度を連続にしてから直線に当てはめた傾き（度/秒）。隣の差は ±180° 未満を前提にする。"""
    ts, angs = [], []
    prev = None
    acc = 0.0
    for t, a in samples:
        if prev is not None:
            d = (a - prev + 180.0) % 360.0 - 180.0
            acc += d
        else:
            acc = a
        prev = a
        ts.append(t)
        angs.append(acc)
    n = len(ts)
    mt, ma = sum(ts) / n, sum(angs) / n
    return sum((t - mt) * (a - ma) for t, a in zip(ts, angs)) / sum((t - mt) ** 2 for t in ts)


def wrap_deg(a: float) -> float:
    return (a + 180.0) % 360.0 - 180.0


# ---- G01 の 1 回の観察の検査 ----------------------------------------------------------------------------------------

def _g01_pose(values: dict[str, dict], p: dict, k: str) -> tuple[float, float, float, float]:
    """中継の値から（上下, 水平のずれ, 傾きの度, Z 軸以外の回転の成分の最大）を返す。"""
    pos = values[f"$member:{district.relay_key(k, 'Position')}.Value"]["member"]["value"]
    rot = q_of(values[f"$member:{district.relay_key(k, 'Rotation')}.Value"]["member"]["value"])
    rest = [p["rest_local_blender"][0], p["rest_local_blender"][2], p["rest_local_blender"][1]]
    lift = float(pos["y"]) - rest[1]
    horiz = math.hypot(float(pos["x"]) - rest[0], float(pos["z"]) - rest[2])
    tilt = math.degrees(2.0 * math.atan2(rot[2], rot[3]))
    return lift, horiz, tilt, max(abs(rot[0]), abs(rot[1]))


def check_g01_sample(values: dict[str, dict], params: dict[str, float], pumpkins: list[dict], keys: dict[str, str]) -> dict:
    """動いている間の 1 回の観察。個体ごとに、上下と傾きが I 倍の範囲の中、位置は上下だけ、回転はローカル Z まわりだけ。

    上下（位置の中継）と傾き（回転の中継）は別の Component で、1 回の observe の中でも読む時刻がずれる（Component ごとに
    順番に読む）。そのため動いている間は式との一致を見ず、式と位相は check_g01_frozen（G01Frequency = 0）で確かめる。
    """
    I = min(max(params["G01Intensity"], 0.0), 1.0)
    rows, problems = [], []
    for p in pumpkins:
        lift, horiz, tilt, off_axis = _g01_pose(values, p, keys[p["motion_root"]])
        lo, hi = p["bounce_m"]
        tilt_max = max(abs(t) for t in p["tilt_deg"])
        rows.append({"asset_id": p["asset_id"], "lift_m": round(lift, 4), "tilt_deg": round(tilt, 3), "horizontal_m": round(horiz, 5)})
        if horiz > HORIZ_TOL_M:
            problems.append(f"{p['asset_id']}: horizontal offset {horiz:.4f} m")
        if not (I * lo - LIFT_TOL_M <= lift <= I * hi + LIFT_TOL_M):
            problems.append(f"{p['asset_id']}: lift {lift:.4f} m outside {I * lo:.3f}..{I * hi:.3f}")
        if off_axis > LOCAL_TOL * 10:
            problems.append(f"{p['asset_id']}: rotation is not about local Z ({off_axis:.5f})")
        if abs(tilt) > I * tilt_max + TILT_TOL_DEG:
            problems.append(f"{p['asset_id']}: tilt {tilt:.2f} deg outside +-{I * tilt_max:.2f}")
    return {"pumpkins": rows, "problems": problems}


def _body_values(bodies: dict[str, dict], p: dict, k: str) -> dict[str, dict]:
    """観察した Body の Slot（name・position・rotation）を、中継の observe の values と同じ形にする。"""
    b = bodies[p["motion_root"]]
    return {f"$member:{district.relay_key(k, 'Position')}.Value": {"member": {"value": b["position"]}},
            f"$member:{district.relay_key(k, 'Rotation')}.Value": {"member": {"value": b["rotation"]}}}


def check_g01_frozen(values: dict[str, dict], params: dict[str, float], pumpkins: list[dict], keys: dict[str, str],
                     bodies: dict[str, dict] | None = None) -> dict:
    """G01Frequency = 0（時刻を止めた状態）の観察。θ_i = s φ_i なので、各個体の上下と傾きが式の値と一致する。

    上下 = I (mid + half sin θ_i)、傾き = I tilt sin(θ_i / 2)。式・位相・中継の結び先がすべて正しいときだけ一致する。
    bodies（Body の Slot の観察。名前 → ノード）を渡すと、中継の値だけでなく Body そのものの位置・回転も照合する
    （中継が無効・別の Slot を駆動しているとき、中継の値が正しくても Body は動かない）。
    """
    I = min(max(params["G01Intensity"], 0.0), 1.0)
    S = min(max(params["G01PhaseSpread"], 0.0), 1.0)
    rows, problems = [], []
    for p in pumpkins:
        lift, horiz, tilt, off_axis = _g01_pose(values, p, keys[p["motion_root"]])
        lo, hi = p["bounce_m"]
        tilt_max = max(abs(t) for t in p["tilt_deg"])
        th = math.radians(S * p["phase_deg"])
        want_lift = I * ((lo + hi) / 2.0 + (hi - lo) / 2.0 * math.sin(th))
        want_tilt = I * tilt_max * math.sin(th / 2.0)
        err_l, err_t = abs(lift - want_lift), abs(tilt - want_tilt)
        rows.append({"asset_id": p["asset_id"], "phase_deg": p["phase_deg"], "lift_m": round(lift, 5), "expected_lift_m": round(want_lift, 5),
                     "tilt_deg": round(tilt, 4), "expected_tilt_deg": round(want_tilt, 4)})
        if err_l > FROZEN_LIFT_TOL_M or err_t > FROZEN_TILT_TOL_DEG or horiz > HORIZ_TOL_M or off_axis > LOCAL_TOL * 10:
            problems.append(f"{p['asset_id']}: frozen pose lift {lift:.4f} (want {want_lift:.4f}), tilt {tilt:.3f} (want {want_tilt:.3f})")
        if bodies is not None:
            if p["motion_root"] not in bodies:
                problems.append(f"{p['asset_id']}: Body is not observed")
                continue
            b_lift, b_horiz, b_tilt, b_off = _g01_pose(_body_values(bodies, p, keys[p["motion_root"]]), p, keys[p["motion_root"]])
            rows[-1].update({"body_lift_m": round(b_lift, 5), "body_tilt_deg": round(b_tilt, 4)})
            if (abs(b_lift - want_lift) > FROZEN_LIFT_TOL_M or abs(b_tilt - want_tilt) > FROZEN_TILT_TOL_DEG
                    or b_horiz > HORIZ_TOL_M or b_off > LOCAL_TOL * 10):
                problems.append(f"{p['asset_id']}: Body pose lift {b_lift:.4f} (want {want_lift:.4f}), tilt {b_tilt:.3f} (want {want_tilt:.3f})")
    return {"pumpkins": rows, "problems": problems}


def g01_half_angles(values: dict[str, dict], params: dict[str, float], pumpkins: list[dict], keys: dict[str, str]) -> dict[str, float]:
    """中継の値から各個体の θ/2（度）を求める。sin(θ/2) は傾きから、sin θ は上下から。|sin(θ/2)| が小さい個体は除く。"""
    I = min(max(params["G01Intensity"], 0.0), 1.0)
    out = {}
    for p in pumpkins:
        lift, _, tilt, _ = _g01_pose(values, p, keys[p["motion_root"]])
        lo, hi = p["bounce_m"]
        tilt_max = max(abs(x) for x in p["tilt_deg"])
        s = max(-1.0, min(1.0, tilt / (I * tilt_max)))
        if abs(s) < 0.2:
            continue
        sin_t = (lift / I - (lo + hi) / 2.0) / ((hi - lo) / 2.0)
        c = max(-1.0, min(1.0, sin_t / (2.0 * s)))
        out[p["asset_id"]] = math.degrees(math.atan2(s, math.copysign(math.sqrt(max(0.0, 1.0 - s * s)), c)))
    return out


def check_g01_clock(v1: dict, t1: float, v2: dict, t2: float, params: dict[str, float], pumpkins: list[dict],
                    keys: dict[str, str]) -> dict:
    """ゆっくりの時刻（G01Frequency を小さくした状態）の 2 回の観察。θ/2 が時刻どおり（π f Δt）進み、個体の位相差が s φ/2。

    遅い周期なら、上下と傾きを読む時刻のずれの影響が小さく、θ を求められる。時刻の項が止まっている・速さが違う・位相が違う
    グラフは、ここで外れる。
    """
    f = min(max(params["G01Frequency"], 0.0), 2.0)
    S = min(max(params["G01PhaseSpread"], 0.0), 1.0)
    a1 = g01_half_angles(v1, params, pumpkins, keys)
    a2 = g01_half_angles(v2, params, pumpkins, keys)
    want = 180.0 * f * (t2 - t1)
    rows, problems = [], []
    both = [p["asset_id"] for p in pumpkins if p["asset_id"] in a1 and p["asset_id"] in a2]
    if len(both) < 3:
        problems.append(f"G01 clock: only {len(both)} pumpkins can be measured")
    for a in both:
        got = wrap_deg(a2[a] - a1[a])
        err = abs(wrap_deg(got - want))
        rows.append({"asset_id": a, "half_angle_advance_deg": round(got, 3), "expected_deg": round(want, 3), "error_deg": round(err, 3)})
        if err > CLOCK_TOL_DEG:
            problems.append(f"{a}: half angle advanced {got:.2f} deg in {t2 - t1:.1f} s (want {want:.2f})")
    phases = {p["asset_id"]: p["phase_deg"] for p in pumpkins}
    pairs = []
    ids = sorted(a1)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            err = abs(wrap_deg(wrap_deg(a1[a] - a1[b]) - S * (phases[a] - phases[b]) / 2.0))
            pairs.append({"pair": [a, b], "error_deg": round(err, 3)})
            if err > CLOCK_TOL_DEG:
                problems.append(f"{a}-{b}: phase difference off by {err:.2f} deg")
    return {"advance": rows, "phase_pairs": pairs, "seconds": round(t2 - t1, 3), "problems": problems}


def check_g01_variation(samples: list[dict], params: dict[str, float], pumpkins: list[dict]) -> list[str]:
    """動いている間の観察の列で、各個体の上下と傾きが実際に変わっているか（時刻の項が止まった一定の姿勢を合格にしない）。"""
    I = min(max(params["G01Intensity"], 0.0), 1.0)
    f = min(max(params["G01Frequency"], 0.0), 2.0)
    if I < 0.05 or f <= 0.0:
        return []
    problems = []
    for p in pumpkins:
        lifts = [r["lift_m"] for s in samples for r in s["pumpkins"] if r["asset_id"] == p["asset_id"]]
        tilts = [r["tilt_deg"] for s in samples for r in s["pumpkins"] if r["asset_id"] == p["asset_id"]]
        lo, hi = p["bounce_m"]
        tilt_max = max(abs(x) for x in p["tilt_deg"])
        if len(lifts) < 4 or max(lifts) - min(lifts) < VARIATION * I * (hi - lo) or max(tilts) - min(tilts) < VARIATION * I * 2 * tilt_max:
            problems.append(f"{p['asset_id']}: not moving enough over {len(lifts)} samples")
    return problems


def check_g13(samples: list[dict], expected: float) -> tuple[dict, list[str]]:
    """TurnRoot の観察（t・yaw_deg・off_axis）から、速さと向き（正 = 東 → 北、上から見て反時計回り）と軸を判定する。

    expected は W05 の速さ（Blender の +Z まわり = 上から見て反時計回り）。向きが逆なら傾きの符号が逆になり、外れる。
    """
    speed = fit_speed([(s["t"], s["yaw_deg"]) for s in samples])
    summary = {"fitted_speed_deg_per_s": round(speed, 3), "expected_deg_per_s": expected,
               "direction": "counterclockwise_from_above" if speed > 0 else "clockwise_from_above",
               "max_off_axis": max(s["off_axis"] for s in samples)}
    problems = []
    gap = max(b["t"] - a["t"] for a, b in zip(samples, samples[1:]))
    summary["max_sample_gap_s"] = round(gap, 3)
    if gap * expected > MAX_STEP_DEG:
        problems.append(f"G13 samples are {gap:.1f} s apart: up to {gap * expected:.0f} deg per step cannot be unwrapped")
    if abs(speed - expected) > SPEED_TOL * expected:
        problems.append(f"G13 speed {speed:.2f} deg/s (expected {expected} counterclockwise from above)")
    if summary["max_off_axis"] > LOCAL_TOL * 10:
        problems.append(f"G13 rotation is not about Y ({summary['max_off_axis']})")
    return summary, problems


# ---- 構造（宣言どおりか） -------------------------------------------------------------------------------------------

def _find_live(node: dict, name: str) -> dict | None:
    if node["name"] == name:
        return node
    for ch in node.get("children") or []:
        hit = _find_live(ch, name)
        if hit is not None:
            return hit
    return None


def _find_decl(node: dict, name: str) -> dict | None:
    if node["slot"]["name"] == name:
        return node
    for ch in node.get("children", []):
        hit = _find_decl(ch, name)
        if hit is not None:
            return hit
    return None


def _same_local(live: dict, slot: dict) -> float:
    vals = [*(float(live["position"][k]) for k in "xyz"), *(float(live["rotation"][k]) for k in "xyzw"),
            *(float(live["scale"][k]) for k in "xyz")]
    want = [*(slot.get("position") or [0, 0, 0]), *(slot.get("rotation") or [0, 0, 0, 1]), *(slot.get("scale") or [1, 1, 1])]
    qa, qb = vals[3:7], want[3:7]
    if sum(a * b for a, b in zip(qa, qb)) < 0:
        want[3:7] = [-x for x in qb]
    return max(abs(a - b) for a, b in zip(vals, want))


def _child(node: dict | None, name: str) -> dict | None:
    """直接の子だけを名前で探す（観察のノード）。"""
    if node is None:
        return None
    return next((c for c in node.get("children") or [] if c["name"] == name), None)


def _decl_paths(node: dict, prefix: tuple = ()) -> list[tuple[tuple, dict]]:
    """宣言の node の子孫を、node からの名前のパスとともに返す。"""
    out = []
    for ch in node.get("children", []):
        path = prefix + (ch["slot"]["name"],)
        out.append((path, ch))
        out.extend(_decl_paths(ch, path))
    return out


def check_structure(root: dict, declarations: dict[str, dict] | None = None) -> dict:
    """TurnRoot の子孫（床・支柱・座席・M05 の visual_root など）と、各カボチャの台座・取付位置が、宣言と同じパス（親子関係）で
    同じローカルの変換か。名前だけで探すと、親を付け替えた Slot（例 Body の外へ出た取付位置）を見落とす。

    declarations は地区のキー → 宣言（テスト用。省略すると最新の export を読む）。
    """
    problems, rows = [], []
    g13, g01 = gimmicks.g13(), gimmicks.g01()
    d_doc = (declarations or {}).get(g13["district"]) or latest_declaration(g13["district"])
    a_doc = (declarations or {}).get(g01["district"]) or latest_declaration(g01["district"])
    turn_decl = _find_decl(d_doc, g13["motion_root"])
    turn_live = _find_live(_child(root, g13["district"]) or {}, g13["motion_root"]) if _child(root, g13["district"]) else None
    if turn_decl is None or turn_live is None:
        return {"rows": [], "problems": ["TurnRoot is missing"]}
    rest = turn_decl["slot"]["position"]
    pos_err = max(abs(float(turn_live["position"][k]) - v) for k, v in zip("xyz", rest))
    rows.append({"slot": g13["motion_root"], "position_error_m": round(pos_err, 6)})
    if pos_err > LOCAL_TOL:
        problems.append(f"TurnRoot moved {pos_err:.5f} m")

    def compare(base_name: str, decl_root: dict, live_root: dict | None, skip: set[str]) -> None:
        for path, decl in _decl_paths(decl_root):
            if path[-1] in skip:
                continue
            live = live_root
            for name in path:
                live = _child(live, name)
            err = math.inf if live is None else _same_local(live, decl["slot"])
            rows.append({"slot": "/".join((base_name, *path)), "local_error": round(err, 6)})
            if err > LOCAL_TOL:
                problems.append(f"{'/'.join((base_name, *path))}: missing at the declared path or local transform differs ({err})")

    compare(g13["motion_root"], turn_decl, turn_live, set())
    district_live = _child(root, g01["district"])
    for p in g01["pumpkins"]:
        asset_decl = _find_decl(a_doc, p["asset_id"])
        asset_live = _find_live(district_live, p["asset_id"]) if district_live else None
        # 駆動される Body そのものは G01 の検査で見る（子の取付位置は Body の下のパスで照合する）
        compare(p["asset_id"], asset_decl, asset_live, {p["motion_root"]})
    return {"rows": rows, "problems": problems}


# ---- 包絡（バンドルのメッシュから。観察ではない） -----------------------------------------------------------------------

def _bundle(key: str) -> Path:
    dirs = [d for d in sorted((PROJECT_ROOT / "exports" / "p2_static").glob(f"{key}-*")) if (d / "p2.apply.json").is_file()]
    return dirs[-1]


def _mesh_vertices(bundle: Path, doc: dict, node: dict) -> list[list[float]]:
    mesh = next((c for c in node.get("components", []) if c["type"] == "FrooxEngine.StaticMesh"), None)
    if mesh is None:
        return []
    src = doc["assets"][mesh["fields"]["URL"].removeprefix("$asset:")]["source"]
    data = json.loads((bundle / src).read_text(encoding="utf-8"))
    return [[v["position"][k] for k in "xyz"] for v in data["vertices"]]


def _local_points(bundle: Path, doc: dict, node: dict, q=(0.0, 0.0, 0.0, 1.0), t=(0.0, 0.0, 0.0)) -> list[tuple]:
    """node とその子孫のメッシュの頂点を、node の親の座標（node のローカルの変換 q・t を含む）で返す。"""
    out = []

    def visit(n: dict, rot, pos):
        for v in _mesh_vertices(bundle, doc, n):
            r = qrot(rot, v)
            out.append((pos[0] + r[0], pos[1] + r[1], pos[2] + r[2]))
        for ch in n.get("children", []):
            s = ch["slot"]
            cq = tuple(s.get("rotation") or (0, 0, 0, 1))
            cp = s.get("position") or (0, 0, 0)
            rp = qrot(rot, cp)
            visit(ch, qmul(rot, cq), (pos[0] + rp[0], pos[1] + rp[1], pos[2] + rp[2]))

    visit(node, q, t)
    return out


def _radius_in_parent(bundle: Path, doc: dict, node: dict) -> float:
    """node（とその子孫）のメッシュの、node の親の座標での原点からの水平の最大距離。"""
    s = node["slot"]
    pts = _local_points(bundle, doc, node, tuple(s.get("rotation") or (0, 0, 0, 1)), s.get("position") or (0, 0, 0))
    return max((math.hypot(x, z) for x, _, z in pts), default=0.0)


def envelope_problems(env: dict) -> list[str]:
    """包絡の判定（envelopes の結果）を問題の一覧にする。"""
    problems = [f"{r['asset_id']}: moving radius {r['moving_radius_m']} m exceeds the W02 envelope {r['w02_envelope_radius_m']} m"
                for r in env["G01"] if not r["within_w02_envelope"]]
    g = env["G13"]
    if g.get("missing_meshy_bundles"):
        problems.append(f"G13 envelope misses Meshy bundles {g['missing_meshy_bundles']}")
    if not g.get("low_parts_within_base"):
        problems.append(f"G13 parts below head height reach {g.get('swept_radius_below_head_m')} m beyond the base {g.get('base_radius_m')} m")
    return problems


def envelopes() -> dict:
    out: dict = {"G01": [], "G13": {}}
    g01 = gimmicks.g01()
    a_bundle = _bundle(g01["district"])
    a_doc = json.loads((a_bundle / "p2.apply.json").read_text(encoding="utf-8"))
    for p in g01["pumpkins"]:
        body = _find_decl(a_doc, p["motion_root"])
        rest = body["slot"]["position"]
        tilt_max = max(abs(t) for t in p["tilt_deg"])
        radius = 0.0
        for deg in [tilt_max * k / 6.0 for k in range(-6, 7)]:
            half = math.radians(deg) / 2.0
            q = (0.0, 0.0, math.sin(half), math.cos(half))
            for x, _, z in _local_points(a_bundle, a_doc, body, q, rest):
                radius = max(radius, math.hypot(x, z))
        pedestal = _find_decl(a_doc, f"{p['asset_id']}_Pedestal")
        ped_r = _radius_in_parent(a_bundle, a_doc, pedestal)
        out["G01"].append({"asset_id": p["asset_id"], "moving_radius_m": round(radius, 4), "pedestal_radius_m": round(ped_r, 4),
                           "w02_envelope_radius_m": p["envelope_radius_m"], "within_w02_envelope": radius <= p["envelope_radius_m"] + 1e-6})
    g13 = gimmicks.g13()
    d_bundle = _bundle(g13["district"])
    d_doc = json.loads((d_bundle / "p2.apply.json").read_text(encoding="utf-8"))
    turn = _find_decl(d_doc, g13["motion_root"])
    pts = _local_points(d_bundle, d_doc, turn, (0, 0, 0, 1), (0, 0, 0))   # TurnRoot のローカル（回転の軸が原点）
    # M05 の柱と屋根（Meshy の素材の宣言。visual_root の下）
    from modeling.p2_meshy.replacements import REPLACEMENTS
    for mid, rep in REPLACEMENTS.items():
        if rep["district"] != g13["district"] or g13["motion_root"] not in rep["visual_root_path"]:
            continue
        mdirs = [d for d in sorted((PROJECT_ROOT / "exports" / "p2_meshy").glob(f"{mid}-*")) if (d / "p2m.apply.json").is_file()]
        if not mdirs:
            out["G13"].setdefault("missing_meshy_bundles", []).append(mid)
            continue
        mdoc = json.loads((mdirs[-1] / "p2m.apply.json").read_text(encoding="utf-8"))
        vr = _find_decl(turn, rep["visual_root"])
        vq = tuple(vr["slot"].get("rotation") or (0, 0, 0, 1))
        vp = vr["slot"].get("position") or (0, 0, 0)
        mq = tuple(mdoc["slot"].get("rotation") or (0, 0, 0, 1))
        mp = qrot(vq, mdoc["slot"].get("position") or (0, 0, 0))
        pts += _local_points(mdirs[-1], mdoc, mdoc, qmul(vq, mq), (vp[0] + mp[0], vp[1] + mp[1], vp[2] + mp[2]))
    low = [math.hypot(x, z) for x, y, z in pts if y <= HEAD_HEIGHT_M]
    base = _find_decl(d_doc, "DAM_Carousel_001_Base")
    base_r = _radius_in_parent(d_bundle, d_doc, base)
    turn_pos = turn["slot"].get("position") or (0, 0, 0)
    out["G13"].update({
        "swept_radius_all_m": round(max(math.hypot(x, z) for x, _, z in pts), 4),
        "swept_radius_below_head_m": round(max(low), 4) if low else None,
        "head_height_above_turn_root_m": HEAD_HEIGHT_M,
        "base_radius_m": round(base_r, 4),
        "base_offset_from_axis_m": round(math.hypot(turn_pos[0], turn_pos[2]), 4),
        "low_parts_within_base": bool(low) and max(low) <= base_r + 1e-6,
    })
    return out


# ---- 窓ごとの観察 ----------------------------------------------------------------------------------------------------

def observe_params(url: str) -> dict[str, float]:
    sels = [f"$member:{v['key']}.Value" for v in gimmicks.G01_VARIABLES.values()]
    data = run_json(["resoloop", "observe", *sels, "--state", str(STATE_DIR / "p3_gimmicks.json"), "--url", url, "--json"])
    return {n: float(data["data"]["values"][f"$member:{v['key']}.Value"]["member"]["value"]) for n, v in gimmicks.G01_VARIABLES.items()}


def observe_spinner(url: str) -> dict:
    g13 = gimmicks.g13()
    state = json.loads((STATE_DIR / "p2_D_amusement.json").read_text(encoding="utf-8"))
    comp = next(k for k in state["components"] if k.startswith("p3_spinner_"))
    sels = [f"$member:{comp}.{m}" for m in ("_speed", "_offset", "_target", "Enabled")]
    data = run_json(["resoloop", "observe", *sels, "--state", str(STATE_DIR / "p2_D_amusement.json"), "--url", url, "--json"])
    vals = data["data"]["values"]
    sel, st = turn_root_selector()
    rot_id = run_json(["resoloop", "inspect", sel, "--state", st, "--members", "--url", url, "--json"])["data"]["members"]["Rotation"]["id"]
    # ResoniteLink の ID はセッション限りなので書かず、TurnRoot の Rotation を指しているかだけを書く
    return {"component": comp, "speed": vals[sels[0]]["member"]["value"], "offset": vals[sels[1]]["member"]["value"],
            "target_is_turn_root_rotation": vals[sels[2]]["member"].get("targetId") == rot_id,
            "enabled": vals[sels[3]]["member"]["value"], "expected_speed": g13["spinner_speed"]}


def turn_root_selector() -> tuple[str, str]:
    state = json.loads((STATE_DIR / "p2_D_amusement.json").read_text(encoding="utf-8"))
    g13 = gimmicks.g13()
    key = next(k for k, v in state["slots"].items() if v.get("path", "").endswith("/" + g13["motion_root"]))
    return f"$slot:{key}", str(STATE_DIR / "p2_D_amusement.json")


def body_keys() -> dict[str, str]:
    state = json.loads((STATE_DIR / "p2_A_plaza.json").read_text(encoding="utf-8"))
    out = {}
    for p in gimmicks.g01()["pumpkins"]:
        want = f"{gimmicks.P2_ROOT}/A_plaza/{p['asset_id']}/{p['motion_root']}"
        out[p["motion_root"]] = next(k for k, v in state["slots"].items() if v.get("path") == want)
    return out


def observe_window(url: str, duration: float, interval: float, raw: list) -> dict:
    sel, st = turn_root_selector()
    keys = body_keys()
    pumpkins = gimmicks.g01()["pumpkins"]
    relay_sels = [f"$member:{district.relay_key(keys[p['motion_root']], m)}.Value" for p in pumpkins for m in ("Position", "Rotation")]
    drive_sels = [f"$member:{district.relay_key(keys[p['motion_root']], m)}.{mem}" for p in pumpkins for m in ("Position", "Rotation")
                  for mem in ("Drives", "Enabled")]
    params = observe_params(url)
    spinner = observe_spinner(url)
    window: dict = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "params": params, "spinner": spinner,
                    "g13": {"samples": []}, "g01": {"samples": []}, "problems": []}
    # 中継の Drives が Body の Position・Rotation を指しているか
    drives = run_json(["resoloop", "observe", *drive_sels, "--state", str(STATE_DIR / "p2_A_plaza.json"), "--url", url, "--json"])
    hier = run_json(["resoloop", "hierarchy", "--under", f"{gimmicks.P2_ROOT}", "--depth", "5", "--url", url, "--json"])
    raw.append({"kind": "hierarchy_start", "data": hier})
    window["structure_start"] = check_structure(hier["data"])
    targets_ok = True
    for p in pumpkins:
        live_body = _find_live(hier["data"], p["motion_root"])
        member_ids = {}
        info = run_json(["resoloop", "inspect", f"$slot:{keys[p['motion_root']]}", "--state", str(STATE_DIR / "p2_A_plaza.json"),
                         "--members", "--url", url, "--json"])["data"]["members"]
        member_ids = {"Position": info["Position"]["id"], "Rotation": info["Rotation"]["id"]}
        for m in ("Position", "Rotation"):
            elems = drives["data"]["values"][f"$member:{district.relay_key(keys[p['motion_root']], m)}.Drives"]["member"]["elements"]
            enabled = drives["data"]["values"][f"$member:{district.relay_key(keys[p['motion_root']], m)}.Enabled"]["member"]["value"]
            if enabled is not True:
                targets_ok = False
                window["problems"].append(f"{p['asset_id']}: relay {m} is disabled")
            if [e.get("targetId") for e in elems] != [member_ids[m]]:
                targets_ok = False
                window["problems"].append(f"{p['asset_id']}: relay {m} drives {[e.get('targetId') for e in elems]}, not the Body {m}")
        _ = live_body
    window["relay_targets_ok"] = targets_ok
    # G13: TurnRoot を待ち時間なしで続けて観察する（1 回 約 2 秒 = 約 36°。角度を連続にするには隣の差が ±180° 未満の必要がある）
    t_end = time.time() + duration
    while time.time() < t_end:
        t, data = timed(["resoloop", "inspect", sel, "--state", st, "--url", url, "--json"])
        q = q_of(data["data"]["rotation"])
        window["g13"]["samples"].append({"t": round(t, 3), "yaw_deg": round(yaw_deg(q), 3),
                                         "off_axis": round(max(abs(q[0]), abs(q[2])), 6)})
    # G01: 中継の値 12 個を 1 回の observe で読む
    t_end = time.time() + duration
    while time.time() < t_end:
        t2, obs = timed(["resoloop", "observe", *relay_sels, "--state", str(STATE_DIR / "p2_A_plaza.json"), "--url", url, "--json"])
        raw.append({"kind": "relays", "t": t2, "data": obs})
        res = check_g01_sample(obs["data"]["values"], params, pumpkins, keys)
        res["t"] = round(t2, 3)
        window["g01"]["samples"].append(res)
        time.sleep(interval)
    hier2 = run_json(["resoloop", "hierarchy", "--under", f"{gimmicks.P2_ROOT}", "--depth", "5", "--url", url, "--json"])
    raw.append({"kind": "hierarchy_end", "data": hier2})
    window["structure_end"] = check_structure(hier2["data"])
    # G13 のまとめ
    summary, problems = check_g13(window["g13"]["samples"], gimmicks.g13()["speed_deg_per_sec_blender_z"])
    window["g13"].update(summary)
    window["problems"].extend(problems)
    if [round(x, 6) for x in spinner["speed"].values()] != [round(x, 6) for x in spinner["expected_speed"]]:
        window["problems"].append(f"G13 Spinner speed {spinner['speed']} != {spinner['expected_speed']}")
    if not spinner["target_is_turn_root_rotation"] or not spinner["enabled"]:
        window["problems"].append("G13 Spinner does not drive the TurnRoot Rotation or is disabled")
    # G01 のまとめ
    s = window["g01"]["samples"]
    window["g01"]["summary"] = {
        p["asset_id"]: {
            "lift_min_m": min(r["lift_m"] for smp in s for r in smp["pumpkins"] if r["asset_id"] == p["asset_id"]),
            "lift_max_m": max(r["lift_m"] for smp in s for r in smp["pumpkins"] if r["asset_id"] == p["asset_id"]),
            "tilt_min_deg": min(r["tilt_deg"] for smp in s for r in smp["pumpkins"] if r["asset_id"] == p["asset_id"]),
            "tilt_max_deg": max(r["tilt_deg"] for smp in s for r in smp["pumpkins"] if r["asset_id"] == p["asset_id"]),
        } for p in pumpkins}
    for smp in s:
        window["problems"].extend(smp["problems"])
    window["g01"]["variation_problems"] = check_g01_variation(s, params, pumpkins)
    window["problems"].extend(window["g01"]["variation_problems"])
    window["problems"].extend(window["structure_start"]["problems"] + window["structure_end"]["problems"])
    window["ok"] = not window["problems"]
    return window


# ---- 外から変えられる値の確認 -------------------------------------------------------------------------------------------

def component_id(selector: str, state: Path, url: str) -> str:
    data = run_json(["resoloop", "observe", selector, "--state", str(state), "--url", url, "--json"])
    return next(iter(data["data"]["values"].values()))["componentId"]


def set_member(cid: str, member: str, value: str, url: str) -> None:
    run_json(["resoloop", "component", "set", cid, member, value, "--url", url, "--json"])


def param_check(url: str, raw: list) -> dict:
    out: dict = {"problems": []}
    p3_state = STATE_DIR / "p3_gimmicks.json"
    keys = body_keys()
    pumpkins = gimmicks.g01()["pumpkins"]
    relay_sels = [f"$member:{district.relay_key(keys[p['motion_root']], m)}.Value" for p in pumpkins for m in ("Position", "Rotation")]
    a_state = str(STATE_DIR / "p2_A_plaza.json")
    before = observe_params(url)
    # 0) 時刻を止めた標本: G01Frequency = 0 で各個体が式の値（θ = s φ）にあるか。続けて G01PhaseSpread = 0 で全員が θ = 0
    fid = component_id(f"$member:{gimmicks.G01_VARIABLES['G01Frequency']['key']}.Value", p3_state, url)
    sid = component_id(f"$member:{gimmicks.G01_VARIABLES['G01PhaseSpread']['key']}.Value", p3_state, url)
    try:
        set_member(fid, "Value", "0", url)
        for spread in (before["G01PhaseSpread"], 0.0):
            set_member(sid, "Value", str(spread), url)
            time.sleep(1.0)
            params = observe_params(url)
            res = []
            for _ in range(2):
                _, obs = timed(["resoloop", "observe", *relay_sels, "--state", a_state, "--url", url, "--json"])
                raw.append({"kind": f"relays_frozen_spread_{spread}", "data": obs})
                hier = run_json(["resoloop", "hierarchy", "--under", f"{gimmicks.P2_ROOT}/{gimmicks.g01()['district']}", "--depth", "2",
                                 "--url", url, "--json"])
                raw.append({"kind": f"bodies_frozen_spread_{spread}", "data": hier})
                bodies = {p["motion_root"]: _find_live(hier["data"], p["motion_root"]) for p in pumpkins}
                bodies = {k: v for k, v in bodies.items() if v is not None}
                res.append(check_g01_frozen(obs["data"]["values"], params, pumpkins, keys, bodies))
            out[f"G01_frozen_spread_{spread}"] = {"params": params, "pumpkins": res[-1]["pumpkins"],
                                                  "problems": [p for r in res for p in r["problems"]]}
            out["problems"].extend(out[f"G01_frozen_spread_{spread}"]["problems"])
    finally:
        set_member(sid, "Value", str(before["G01PhaseSpread"]), url)
        set_member(fid, "Value", str(before["G01Frequency"]), url)
    # 0b) ゆっくりの時刻: G01Frequency = CLOCK_FREQUENCY で、CLOCK_WAIT_S 秒の間に θ/2 が時刻どおり進むか、個体の位相差が s φ/2 か
    try:
        set_member(fid, "Value", str(CLOCK_FREQUENCY), url)
        time.sleep(1.0)
        params = observe_params(url)
        t1, o1 = timed(["resoloop", "observe", *relay_sels, "--state", a_state, "--url", url, "--json"])
        time.sleep(CLOCK_WAIT_S)
        t2, o2 = timed(["resoloop", "observe", *relay_sels, "--state", a_state, "--url", url, "--json"])
        raw.append({"kind": "relays_clock", "t": [t1, t2], "data": [o1, o2]})
        out["G01_clock"] = {"params": params, **check_g01_clock(o1["data"]["values"], t1, o2["data"]["values"], t2, params, pumpkins, keys)}
        out["problems"].extend(out["G01_clock"]["problems"])
    finally:
        set_member(fid, "Value", str(before["G01Frequency"]), url)
    # 1) G01Intensity を 0.5 に → 範囲が半分 → 0 に → 基準姿勢 → 1 に戻す
    cid = component_id(f"$member:{gimmicks.G01_VARIABLES['G01Intensity']['key']}.Value", p3_state, url)
    try:
        for value in (0.5, 0.0):
            set_member(cid, "Value", str(value), url)
            params = observe_params(url)
            rows = []
            for _ in range(8):
                _, obs = timed(["resoloop", "observe", *relay_sels, "--state", a_state, "--url", url, "--json"])
                raw.append({"kind": f"relays_intensity_{value}", "data": obs})
                rows.append(check_g01_sample(obs["data"]["values"], params, pumpkins, keys))
                time.sleep(0.6)
            lifts = [r["lift_m"] for res in rows for r in res["pumpkins"]]
            tilts = [abs(r["tilt_deg"]) for res in rows for r in res["pumpkins"]]
            out[f"G01Intensity_{value}"] = {"lift_range_m": [min(lifts), max(lifts)], "tilt_abs_max_deg": max(tilts),
                                            "problems": [p for res in rows for p in res["problems"]]}
            out["problems"].extend(out[f"G01Intensity_{value}"]["problems"])
    finally:
        set_member(cid, "Value", str(before["G01Intensity"]), url)
    out["G01_restored"] = observe_params(url)
    if out["G01_restored"] != before:
        out["problems"].append(f"G01 variables not restored: {out['G01_restored']} != {before}")
    # 2) G13 の速さを半分に → 測る → 戻す。続けて、Spinner を 8 秒止めて再開したときの角度が時刻の延長上にあるか
    spinner = observe_spinner(url)
    sel, st = turn_root_selector()
    scid = component_id(f"$member:{spinner['component']}._speed", STATE_DIR / "p2_D_amusement.json", url)
    orig = spinner["speed"]
    try:
        set_member(scid, "_speed", json.dumps([0.0, orig["y"] / 2.0, 0.0]), url)
        smp = []
        for _ in range(8):
            t, data = timed(["resoloop", "inspect", sel, "--state", st, "--url", url, "--json"])
            smp.append((t, yaw_deg(q_of(data["data"]["rotation"]))))
            time.sleep(1.0)
        out["G13_half_speed_deg_per_s"] = round(fit_speed(smp), 3)
        if abs(out["G13_half_speed_deg_per_s"] - gimmicks.g13()["speed_deg_per_sec_blender_z"] / 2.0) > SPEED_TOL * gimmicks.g13()["speed_deg_per_sec_blender_z"]:
            out["problems"].append(f"G13 half speed {out['G13_half_speed_deg_per_s']}")
    finally:
        set_member(scid, "_speed", json.dumps([orig["x"], orig["y"], orig["z"]]), url)
    out["G13_speed_restored"] = observe_spinner(url)["speed"]
    if out["G13_speed_restored"] != orig:
        out["problems"].append(f"G13 speed not restored: {out['G13_speed_restored']} != {orig}")
    smp = []
    for _ in range(6):
        t, data = timed(["resoloop", "inspect", sel, "--state", st, "--url", url, "--json"])
        smp.append((t, yaw_deg(q_of(data["data"]["rotation"]))))
        time.sleep(1.0)
    speed = fit_speed(smp)
    t_ref, a_ref = smp[-1]
    expected = gimmicks.g13()["speed_deg_per_sec_blender_z"]
    if abs(speed - expected) > SPEED_TOL * expected:
        out["problems"].append(f"G13 is not turning at {expected} deg/s before the pause ({speed:.2f}); is the world in front?")
    try:
        set_member(scid, "Enabled", "false", url)
        time.sleep(8.0)
    finally:
        set_member(scid, "Enabled", "true", url)
    time.sleep(1.0)
    t, data = timed(["resoloop", "inspect", sel, "--state", st, "--url", url, "--json"])
    got = yaw_deg(q_of(data["data"]["rotation"]))
    predicted = a_ref + speed * (t - t_ref)
    err = abs(wrap_deg(got - predicted))
    out["G13_spinner_time_base"] = {"paused_s": 8.0, "angle_after_deg": round(got, 2), "predicted_by_clock_deg": round(wrap_deg(predicted), 2),
                                    "error_deg": round(err, 2),
                                    "lag_if_accumulating_deg": round(abs(speed) * 8.0, 1),
                                    "follows_world_time": err < 10.0}
    if not out["G13_spinner_time_base"]["follows_world_time"]:
        out["problems"].append(f"G13 Spinner does not follow the world time ({err:.1f} deg off after the pause)")
    out["G13_spinner_enabled_restored"] = observe_spinner(url)["enabled"]
    if out["G13_spinner_enabled_restored"] is not spinner["enabled"]:
        out["problems"].append(f"G13 Spinner Enabled not restored: {out['G13_spinner_enabled_restored']}")
    out["ok"] = not out["problems"]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", required=True)
    ap.add_argument("--raw-out", type=Path, required=True, help="生の観察の保存先（Git の外。ResoniteLink の ID を含む）")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--windows", type=int, default=1)
    ap.add_argument("--gap", type=float, default=300.0, help="窓と窓の間の秒数")
    ap.add_argument("--duration", type=float, default=40.0, help="1 つの窓の観察の秒数")
    ap.add_argument("--interval", type=float, default=1.0, help="G01 の観察の間の秒数")
    ap.add_argument("--param-check", action="store_true")
    args = ap.parse_args(argv)
    raw: list = []
    if args.param_check:
        result = param_check(args.url, raw)
    else:
        wins = []
        for i in range(args.windows):
            if i:
                time.sleep(args.gap)
            wins.append(observe_window(args.url, args.duration, args.interval, raw))
        env = envelopes()
        result = {"windows": wins, "gap_s": args.gap if args.windows > 1 else None, "envelopes": env,
                  "envelope_problems": envelope_problems(env),
                  "tolerances": {"speed": SPEED_TOL, "lift_m": LIFT_TOL_M, "tilt_deg": TILT_TOL_DEG, "horizontal_m": HORIZ_TOL_M,
                                 "frozen_lift_m": FROZEN_LIFT_TOL_M, "frozen_tilt_deg": FROZEN_TILT_TOL_DEG, "local": LOCAL_TOL}}
        result["ok"] = all(w["ok"] for w in wins) and not result["envelope_problems"]
    args.raw_out.parent.mkdir(parents=True, exist_ok=True)
    args.raw_out.write_text(json.dumps(raw, ensure_ascii=False) + "\n", encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = result if args.param_check else {
        "ok": result["ok"],
        "windows": [{"ok": w["ok"], "g13": {k: w["g13"][k] for k in ("fitted_speed_deg_per_s", "direction", "max_off_axis")},
                     "g01_summary": w["g01"]["summary"], "relay_targets_ok": w["relay_targets_ok"],
                     "problems": w["problems"][:10]} for w in result["windows"]],
        "envelopes": result["envelopes"], "envelope_problems": result["envelope_problems"]}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
