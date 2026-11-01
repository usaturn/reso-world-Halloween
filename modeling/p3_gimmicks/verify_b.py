"""W10-B: Resonite で動いている G05（おばけの浮遊）と G06（屋敷の扉の開閉）を、時間を空けた観察から検査する。

実行（プロジェクトのディレクトリ。対象のワールドを Resonite の前面に出しておく。背面では駆動が進まない）:
    uv run python modeling/p3_gimmicks/verify_b.py --url ws://localhost:<PORT>/ \\
        --raw-out <Git の外の JSON> --output review/p3_gimmicks/g05_g06_live_checks.json [--windows 2 --gap 300]
    # 外から変えられる値の確認（値を変えて測り、元に戻す。ワールドに書く）
    uv run python modeling/p3_gimmicks/verify_b.py --url ... --raw-out ... --output review/p3_gimmicks/g05_g06_param_checks.json --param-check

観察（窓ごと。--windows の数だけ、--gap 秒あけて繰り返す）
- 中継 6 個（おばけ 2 体の位置・回転、扉の蝶番 2 つの回転）の Value を 1 回の resoloop observe で読み、--duration 秒続ける。
  中継の Drives が FloatPivot・蝶番の Slot の Position・Rotation を指し、有効かも見る
- 時刻を止めた標本: 窓の最初に G05Frequency・G06Frequency を 0 にして（θ = s φ・2π p の姿勢）、FloatPivot・蝶番の Slot そのものの
  姿勢を読み、速さを戻す。式と照合し、窓の間で比べる（同じ位相の上下の差 1 cm 以内、揺れ・開きの差 0.5° 以内。漂わないか）
- 構造: 窓の最初と最後に resoloop hierarchy で、おばけと扉のアセットの子孫が宣言と同じパスで同じローカルの変換か
  （FloatPivot は位置・回転、蝶番は回転が駆動されるので、そこだけは比べない。蝶番の位置と拡縮は比べる）

検査
- G05: 位置は基準から上下だけ（水平のずれ 1 mm 以内）、上下は I × G05_BOB_RANGE_M の中、回転は Y 軸まわりだけで I × 20° の中。
  各個体の上下・揺れの幅が範囲の 15% 未満なら「動いていない」とする
- G06: 回転は Y 軸まわりだけで、開き（内開きを正）が 0〜I × 85° の中。左右の開きの差は 10° 以内（1 回の observe の中の
  読み取りの時刻のずれの分。時刻を止めた標本では 0.05° 以内）。窓の中で 0.9 × I × 85° まで開き、0.1 × I × 85° まで閉じること。
  半分開いた角度を通る時刻の間隔が、周期の半分（1 / (2 f)）と 1.5 秒以内で合うこと（時刻の項の速さの確認）
- --param-check: 時刻を止めた標本（G05Frequency・G06Frequency = 0）で、中継の値と Slot そのものが式の値と一致するか
  （G05 は位相の倍率 1・0.5・0、G06 は周期の位置 0・0.2・0.25・0.5 と強さ 0.5）。範囲の外の値（強さ 5・-1、速さ -1、位相の
  倍率 1.5、周期の位置 1.5。収めない場合と姿勢が区別できる値）が範囲に収まるか。G05Frequency をゆっくり（0.004 Hz）にして
  20 秒の間に θ/2 が時刻どおり進むか（2 体とも測れるときは位相差も）、揺れから求めた θ の式の上下が観察と合うか。G05Intensity 0.5・0 で範囲が縮むか。どれも元に戻し、
  戻ったかを確かめる。速さの上限（G05Frequency 1 Hz・G06Frequency 0.2 Hz）は観察の間隔では測れないので見ない
- 包絡（バンドルのメッシュから。観察ではない）: おばけの動く範囲が W03 の配置の余裕（clearance_radius_m）の中で、中央の通路
  （Excl_B_CentralSightlineCorridor）に入らないか。扉の葉が開く間に W03 の扉の振れる範囲（Excl_B_DoorSwingAndPorch）の中に
  収まり、閉じた形より手前（ポーチ側）に出ないか。外れたら最終の判定を不合格にする
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
from modeling.p3_gimmicks.build_content import b_keys  # noqa: E402
from modeling.p3_gimmicks.rest_pose import latest_declaration  # noqa: E402
from modeling.p3_gimmicks.verify_live import (  # noqa: E402
    STATE_DIR, _bundle, _child, _decl_paths, _find_decl, _find_live, _local_points, _same_local, component_id, q_of,
    qmul, qrot, run_json, set_member, timed, wrap_deg)

B_STATE = STATE_DIR / "p2_B_mansion.json"
P3_STATE = STATE_DIR / "p3_gimmicks.json"
LIFT_TOL_M = 0.002
DEG_TOL = 0.2
HORIZ_TOL_M = 0.001
OFF_AXIS_TOL = 1e-3          # 回転の四元数の X・Z の成分（Y 軸まわりだけか）
FROZEN_LIFT_TOL_M = 0.0005
FROZEN_DEG_TOL = 0.05
LIVE_SYMMETRY_DEG = 10.0     # 動いている間の左右の扉の開きの差（1 回の observe の中の読み取りの時刻のずれ。最大の速さ約 32°/s）
CLOCK_TOL_DEG = 2.0
CLOCK_FREQUENCY = 0.004      # ゆっくりの時刻の G05Frequency（Hz）。θ/2 は 0.72°/s
CLOCK_WAIT_S = 20.0
CLOCK_LIFT_TOL_M = 0.005     # ゆっくりの時刻で、揺れから求めた θ の式の上下と観察した上下の差（GPT のレビューの指摘 M-1）
DRIFT_TOL_M = 0.01           # 窓ごとの時刻を止めた標本の、窓の間の上下の差（#59 の受け入れ基準「同じ位相の位置の差が 1 cm 以内」）
DRIFT_TOL_DEG = 0.5          # 同じく揺れ・扉の開きの差
VARIATION = 0.15
DOOR_REACH = 0.9             # 窓の中で、開きが I × 85° のこの割合まで開き、(1 - この割合) まで閉じること
CROSS_TOL_S = 1.5            # 半分開いた角度を通る時刻の間隔と、周期の半分の差の許容
LOCAL_TOL = 1e-4
DOOR_PORCH_TOL_M = 1e-3


def _clamp(x: float, lo: float, hi: float) -> float:
    return min(max(float(x), lo), hi)


def variables() -> dict[str, dict]:
    return {**gimmicks.G05_VARIABLES, **gimmicks.G06_VARIABLES}


def params_of(raw: dict[str, float]) -> dict[str, float]:
    """観察した値を、モジュールと同じ範囲に収めた値にする。"""
    v = variables()
    return {n: _clamp(raw[n], v[n]["min"], v[n]["max"]) for n in v}


def relay_sel(slot_key: str, member: str, gid: str) -> str:
    return f"$member:{district.relay_key(slot_key, member, gid)}.Value"


def relay_selectors(keys: dict[str, str]) -> list[str]:
    sels = []
    for g in gimmicks.g05()["ghosts"]:
        sels += [relay_sel(keys[g["motion_root"]], m, "g05") for m in ("Position", "Rotation")]
    for h in gimmicks.g06()["hinges"]:
        sels.append(relay_sel(keys[h["motion_root"]], "Rotation", "g06"))
    return sels


def rest_positions(doc: dict | None = None) -> dict[str, list[float]]:
    doc = doc or latest_declaration(gimmicks.g05()["district"])
    out = {}
    for name in [g["motion_root"] for g in gimmicks.g05()["ghosts"]] + [h["motion_root"] for h in gimmicks.g06()["hinges"]]:
        node = _find_decl(doc, name)
        out[name] = [float(x) for x in (node["slot"].get("position") or [0.0, 0.0, 0.0])]
    return out


def yaw_of(q) -> tuple[float, float]:
    """Y 軸まわりの回転の角度（Resonite、度）と、Y 軸以外の成分の大きさ。"""
    x, y, z, w = q
    if w < 0:
        x, y, z, w = -x, -y, -z, -w
    return math.degrees(2.0 * math.atan2(y, w)), max(abs(x), abs(z))


# ---- 1 回の観察 ------------------------------------------------------------------------------------------------------

def ghost_pose(pos: dict, rot: dict, rest: list[float]) -> dict:
    """FloatPivot の位置・回転から、上下・水平のずれ・揺れ（Blender の Z まわり。Resonite の Y まわりの符号を逆にした値）。"""
    yaw_r, off = yaw_of(q_of(rot))
    return {"lift_m": float(pos["y"]) - rest[1], "horizontal_m": math.hypot(float(pos["x"]) - rest[0], float(pos["z"]) - rest[2]),
            "sway_deg": -yaw_r, "off_axis": off}


def door_open(rot: dict, sign: float) -> tuple[float, float]:
    """蝶番の回転から、開き（内開きを正、度）と Y 軸以外の成分。左（Blender の +Z に開く）は Resonite の Y まわりの負。"""
    yaw_r, off = yaw_of(q_of(rot))
    return sign * -yaw_r, off


def read_sample(values: dict[str, dict], keys: dict[str, str], rest: dict[str, list[float]]) -> dict:
    """observe の values（中継の Value）を、個体ごとの姿勢にする。"""
    out = {"ghosts": {}, "doors": {}}
    for g in gimmicks.g05()["ghosts"]:
        k = keys[g["motion_root"]]
        out["ghosts"][g["asset_id"]] = ghost_pose(values[relay_sel(k, "Position", "g05")]["member"]["value"],
                                                  values[relay_sel(k, "Rotation", "g05")]["member"]["value"], rest[g["motion_root"]])
    for h in gimmicks.g06()["hinges"]:
        k = keys[h["motion_root"]]
        ang, off = door_open(values[relay_sel(k, "Rotation", "g06")]["member"]["value"], h["open_sign_blender_z"])
        out["doors"][h["motion_root"]] = {"open_deg": ang, "off_axis": off}
    return out


def read_slots(hier: dict, rest: dict[str, list[float]]) -> dict:
    """hierarchy の観察から、FloatPivot・蝶番の Slot そのものの姿勢（read_sample と同じ形）。見つからない物は入れない。"""
    out = {"ghosts": {}, "doors": {}}
    for g in gimmicks.g05()["ghosts"]:
        n = _find_live(hier, g["motion_root"])
        if n is not None:
            out["ghosts"][g["asset_id"]] = ghost_pose(n["position"], n["rotation"], rest[g["motion_root"]])
    for h in gimmicks.g06()["hinges"]:
        n = _find_live(hier, h["motion_root"])
        if n is not None:
            ang, off = door_open(n["rotation"], h["open_sign_blender_z"])
            pos_err = max(abs(float(n["position"][c]) - v) for c, v in zip("xyz", rest[h["motion_root"]]))
            out["doors"][h["motion_root"]] = {"open_deg": ang, "off_axis": off, "position_error_m": pos_err}
    return out


def check_sample(sample: dict, params: dict[str, float]) -> list[str]:
    """動いている間の 1 回の観察。範囲・軸・左右の対称（読み取りの時刻のずれの分は許す）。"""
    problems = []
    I5, I6 = params["G05Intensity"], params["G06Intensity"]
    for g in gimmicks.g05()["ghosts"]:
        s = sample["ghosts"][g["asset_id"]]
        lo, hi = g["bob_m"]
        if not (I5 * lo - LIFT_TOL_M <= s["lift_m"] <= I5 * hi + LIFT_TOL_M):
            problems.append(f"{g['asset_id']}: lift {s['lift_m']:.4f} m outside {I5 * lo:.3f}..{I5 * hi:.3f}")
        if abs(s["sway_deg"]) > I5 * g["yaw_deg"] + DEG_TOL:
            problems.append(f"{g['asset_id']}: sway {s['sway_deg']:.2f} deg beyond +-{I5 * g['yaw_deg']:.2f}")
        if s["horizontal_m"] > HORIZ_TOL_M or s["off_axis"] > OFF_AXIS_TOL:
            problems.append(f"{g['asset_id']}: moved sideways {s['horizontal_m']:.4f} m or turned off the Y axis {s['off_axis']:.4f}")
    opens = []
    for h in gimmicks.g06()["hinges"]:
        d = sample["doors"][h["motion_root"]]
        opens.append(d["open_deg"])
        if not (-DEG_TOL <= d["open_deg"] <= I6 * h["open_deg"] + DEG_TOL):
            problems.append(f"{h['motion_root']}: open {d['open_deg']:.2f} deg outside 0..{I6 * h['open_deg']:.2f} (inward)")
        if d["off_axis"] > OFF_AXIS_TOL:
            problems.append(f"{h['motion_root']}: turned off the Y axis {d['off_axis']:.4f}")
    if abs(opens[0] - opens[1]) > LIVE_SYMMETRY_DEG:
        problems.append(f"doors are not symmetric: {opens[0]:.2f} vs {opens[1]:.2f} deg")
    return problems


# ---- 式（時刻を止めた標本・ゆっくりの時刻） -------------------------------------------------------------------------------

def expected_ghost(params: dict[str, float], g: dict, theta: float) -> tuple[float, float]:
    lo, hi = g["bob_m"]
    I = params["G05Intensity"]
    return I * ((lo + hi) / 2.0 + (hi - lo) / 2.0 * math.sin(theta)), I * g["yaw_deg"] * math.sin(theta / 2.0)


def expected_door(params: dict[str, float], open_deg: float) -> float:
    """G06Frequency = 0 のときの開き（θ = 2π p）。"""
    th = 2.0 * math.pi * params["G06Phase"]
    c = 0.5 - 0.5 * math.cos(th)
    x = _clamp((c - gimmicks.G06_HOLD) / (1.0 - 2.0 * gimmicks.G06_HOLD), 0.0, 1.0)
    return params["G06Intensity"] * open_deg * x * x * (3.0 - 2.0 * x)


def check_frozen(sample: dict, params: dict[str, float], what: str = "relay") -> dict:
    """G05Frequency = 0・G06Frequency = 0 の観察（中継の値か、Slot そのもの）が式の値と一致するか。"""
    rows, problems = [], []
    for g in gimmicks.g05()["ghosts"]:
        s = sample["ghosts"].get(g["asset_id"])
        want_l, want_s = expected_ghost(params, g, math.radians(params["G05PhaseSpread"] * g["phase_deg"]))
        if s is None:
            problems.append(f"{g['asset_id']}: {what} is not observed")
            continue
        rows.append({"asset_id": g["asset_id"], "lift_m": round(s["lift_m"], 5), "expected_lift_m": round(want_l, 5),
                     "sway_deg": round(s["sway_deg"], 4), "expected_sway_deg": round(want_s, 4)})
        if (abs(s["lift_m"] - want_l) > FROZEN_LIFT_TOL_M or abs(s["sway_deg"] - want_s) > FROZEN_DEG_TOL
                or s["horizontal_m"] > HORIZ_TOL_M or s["off_axis"] > OFF_AXIS_TOL):
            problems.append(f"{g['asset_id']} {what}: lift {s['lift_m']:.4f} (want {want_l:.4f}), sway {s['sway_deg']:.3f} (want {want_s:.3f})")
    for h in gimmicks.g06()["hinges"]:
        d = sample["doors"].get(h["motion_root"])
        want = expected_door(params, h["open_deg"])
        if d is None:
            problems.append(f"{h['motion_root']}: {what} is not observed")
            continue
        rows.append({"hinge": h["motion_root"], "open_deg": round(d["open_deg"], 4), "expected_open_deg": round(want, 4)})
        if abs(d["open_deg"] - want) > FROZEN_DEG_TOL or d["off_axis"] > OFF_AXIS_TOL:
            problems.append(f"{h['motion_root']} {what}: open {d['open_deg']:.3f} (want {want:.3f})")
        if d.get("position_error_m", 0.0) > LOCAL_TOL:
            problems.append(f"{h['motion_root']} {what}: hinge moved {d['position_error_m']:.5f} m")
    return {"rows": rows, "problems": problems}


def ghost_half_angles(sample: dict, params: dict[str, float]) -> dict[str, float]:
    """各おばけの θ/2（度）。sin(θ/2) は揺れから、sin θ は上下から。|sin(θ/2)| が小さい個体は除く。"""
    I = params["G05Intensity"]
    out = {}
    for g in gimmicks.g05()["ghosts"]:
        s = sample["ghosts"][g["asset_id"]]
        lo, hi = g["bob_m"]
        sh = _clamp(s["sway_deg"] / (I * g["yaw_deg"]), -1.0, 1.0)
        if abs(sh) < 0.2:
            continue
        sin_t = (s["lift_m"] / I - (lo + hi) / 2.0) / ((hi - lo) / 2.0)
        c = _clamp(sin_t / (2.0 * sh), -1.0, 1.0)
        out[g["asset_id"]] = math.degrees(math.atan2(sh, math.copysign(math.sqrt(max(0.0, 1.0 - sh * sh)), c)))
    return out


def check_clock(s1: dict, t1: float, s2: dict, t2: float, params: dict[str, float]) -> dict:
    """ゆっくりの時刻の 2 回の観察。θ/2 が π f Δt 進み、2 体の θ/2 の差が s (φ1 - φ2) / 2 か。

    θ/2 は揺れ（sin(θ/2)）から求め、上下からは cos(θ/2) の符号だけを使うので、測った各観察で、その θ の式の上下と観察した
    上下が合うかも見る（上下だけが別の速さ・位相のグラフを見逃さない。GPT のレビューの指摘 M-1）。
    """
    f, S = params["G05Frequency"], params["G05PhaseSpread"]
    a1, a2 = ghost_half_angles(s1, params), ghost_half_angles(s2, params)
    want = 180.0 * f * (t2 - t1)
    rows, problems = [], []
    lift_rows = []
    for label, sample, angles in (("first", s1, a1), ("second", s2, a2)):
        for g in gimmicks.g05()["ghosts"]:
            if g["asset_id"] not in angles:
                continue
            want_l, _ = expected_ghost(params, g, 2.0 * math.radians(angles[g["asset_id"]]))
            got_l = sample["ghosts"][g["asset_id"]]["lift_m"]
            lift_rows.append({"observation": label, "asset_id": g["asset_id"], "lift_m": round(got_l, 5),
                              "lift_from_sway_m": round(want_l, 5)})
            if abs(got_l - want_l) > CLOCK_LIFT_TOL_M:
                problems.append(f"{g['asset_id']} ({label}): lift {got_l:.4f} m does not match the sway phase ({want_l:.4f} m)")
    both = [g["asset_id"] for g in gimmicks.g05()["ghosts"] if g["asset_id"] in a1 and g["asset_id"] in a2]
    if not both:
        problems.append("G05 clock: no ghost can be measured")
    for a in both:
        got = wrap_deg(a2[a] - a1[a])
        err = abs(wrap_deg(got - want))
        rows.append({"asset_id": a, "half_angle_advance_deg": round(got, 3), "expected_deg": round(want, 3), "error_deg": round(err, 3)})
        if err > CLOCK_TOL_DEG:
            problems.append(f"{a}: half angle advanced {got:.2f} deg in {t2 - t1:.1f} s (want {want:.2f})")
    ghosts = gimmicks.g05()["ghosts"]
    pair = None
    if all(g["asset_id"] in a1 for g in ghosts):
        a, b = ghosts[0]["asset_id"], ghosts[1]["asset_id"]
        err = abs(wrap_deg(wrap_deg(a1[a] - a1[b]) - S * (ghosts[0]["phase_deg"] - ghosts[1]["phase_deg"]) / 2.0))
        pair = {"pair": [a, b], "error_deg": round(err, 3)}
        if err > CLOCK_TOL_DEG:
            problems.append(f"{a}-{b}: phase difference off by {err:.2f} deg")
    return {"advance": rows, "phase_pair": pair, "lift_consistency": lift_rows, "seconds": round(t2 - t1, 3), "problems": problems}


# ---- 窓のまとめ ------------------------------------------------------------------------------------------------------

def check_variation(samples: list[dict], params: dict[str, float]) -> list[str]:
    """動いている間の列で、おばけが上下・揺れ、扉が開いて閉じたか（時刻の項が止まった一定の姿勢を合格にしない）。"""
    problems = []
    I5, f5 = params["G05Intensity"], params["G05Frequency"]
    if I5 >= 0.05 and f5 > 0.0:
        for g in gimmicks.g05()["ghosts"]:
            lifts = [s["ghosts"][g["asset_id"]]["lift_m"] for s in samples]
            sways = [s["ghosts"][g["asset_id"]]["sway_deg"] for s in samples]
            lo, hi = g["bob_m"]
            if (len(lifts) < 4 or max(lifts) - min(lifts) < VARIATION * I5 * (hi - lo)
                    or max(sways) - min(sways) < VARIATION * I5 * 2 * g["yaw_deg"]):
                problems.append(f"{g['asset_id']}: not moving enough over {len(lifts)} samples")
    I6, f6 = params["G06Intensity"], params["G06Frequency"]
    if I6 >= 0.05 and f6 > 0.0:
        for h in gimmicks.g06()["hinges"]:
            opens = [s["doors"][h["motion_root"]]["open_deg"] for s in samples]
            full = I6 * h["open_deg"]
            if not opens or max(opens) < DOOR_REACH * full or min(opens) > (1.0 - DOOR_REACH) * full:
                problems.append(f"{h['motion_root']}: did not open and close within the window "
                                f"({min(opens, default=0):.1f}..{max(opens, default=0):.1f} deg)")
    return problems


def half_open_crossings(times: list[float], opens: list[float], half: float) -> list[tuple[float, str]]:
    """開きが half を通る時刻（隣の観察の間を直線で補う）と向き（up = 開く、down = 閉じる）。"""
    out = []
    for (t0, a0), (t1, a1) in zip(zip(times, opens), zip(times[1:], opens[1:])):
        if (a0 - half) * (a1 - half) < 0:
            out.append((t0 + (half - a0) / (a1 - a0) * (t1 - t0), "up" if a1 > a0 else "down"))
    return out


def check_door_clock(samples: list[dict], params: dict[str, float]) -> dict:
    """半分開いた角度を通る時刻の間隔が、周期の半分（θ = π/2 と 3π/2 の間）と合うか。開く・閉じるが交互か。"""
    I6, f6 = params["G06Intensity"], params["G06Frequency"]
    if I6 < 0.05 or f6 <= 0.0:
        return {"skipped": True, "problems": []}
    h = gimmicks.g06()["hinges"][0]
    times = [s["t"] for s in samples]
    opens = [s["doors"][h["motion_root"]]["open_deg"] for s in samples]
    cross = half_open_crossings(times, opens, I6 * h["open_deg"] / 2.0)
    want = 0.5 / f6
    intervals = [b[0] - a[0] for a, b in zip(cross, cross[1:])]
    problems = []
    if len(cross) < 2:
        problems.append(f"G06: only {len(cross)} half-open crossings in the window (need 2; the window must cover half a cycle)")
    for (ta, da), (tb, db) in zip(cross, cross[1:]):
        if da == db:
            problems.append(f"G06: two {da} crossings in a row at {ta:.1f} and {tb:.1f}")
        if abs((tb - ta) - want) > CROSS_TOL_S:
            problems.append(f"G06: half-open crossings {tb - ta:.2f} s apart (want {want:.2f} s)")
    return {"crossings": [{"t": round(t, 3), "direction": d} for t, d in cross], "intervals_s": [round(x, 3) for x in intervals],
            "expected_interval_s": round(want, 3), "problems": problems}


def check_structure(root: dict, doc: dict | None = None) -> dict:
    """おばけと扉のアセットの子孫を、宣言と同じパスでたどってローカルの変換を比べる。FloatPivot は位置・回転、蝶番は回転が
    駆動されるので比べない（蝶番の位置と拡縮、FloatPivot の拡縮は比べる）。"""
    doc = doc or latest_declaration(gimmicks.g05()["district"])
    # root は B の地区の Slot（b_hierarchy の起点）か、その親（W08 の root）
    district_live = root if root.get("name") == gimmicks.g05()["district"] else _child(root, gimmicks.g05()["district"])
    pivots = {g["motion_root"] for g in gimmicks.g05()["ghosts"]}
    hinges = {h["motion_root"] for h in gimmicks.g06()["hinges"]}
    assets = [g["asset_id"] for g in gimmicks.g05()["ghosts"]] + sorted({h["asset_id"] for h in gimmicks.g06()["hinges"]})
    rows, problems = [], []
    for asset_id in assets:
        decl_root = _find_decl(doc, asset_id)
        live_root = _child(district_live, asset_id)
        if decl_root is None or live_root is None:
            problems.append(f"{asset_id}: missing")
            continue
        err = _same_local(live_root, decl_root["slot"])
        if err > LOCAL_TOL:
            problems.append(f"{asset_id}: asset root local transform differs ({err})")
        for path, decl in _decl_paths(decl_root):
            live = live_root
            for name in path:
                live = _child(live, name)
            slot = decl["slot"]
            if live is None:
                err = math.inf
            elif path[-1] in pivots or path[-1] in hinges:
                fields = [("scale", "xyz", slot.get("scale") or [1, 1, 1])]
                if path[-1] in hinges:
                    fields.append(("position", "xyz", slot.get("position") or [0, 0, 0]))
                err = max(abs(float(live[f][c]) - v) for f, comps, want in fields for c, v in zip(comps, want))
            else:
                err = _same_local(live, slot)
            rows.append({"slot": "/".join((asset_id, *path)), "local_error": round(err, 6)})
            if err > LOCAL_TOL:
                problems.append(f"{'/'.join((asset_id, *path))}: missing at the declared path or local transform differs ({err})")
    return {"rows": rows, "problems": problems}


# ---- 包絡（バンドルのメッシュから。観察ではない） -----------------------------------------------------------------------

def _yq(deg: float) -> tuple:
    h = math.radians(deg) / 2.0
    return (0.0, math.sin(h), 0.0, math.cos(h))


def _to_district(asset: dict, pts: list[tuple]) -> list[tuple]:
    s = asset["slot"]
    q = tuple(s.get("rotation") or (0, 0, 0, 1))
    p = s.get("position") or (0, 0, 0)
    out = []
    for v in pts:
        r = qrot(q, v)
        out.append((p[0] + r[0], p[1] + r[1], p[2] + r[2]))
    return out


def _in_box_res(pt: tuple, box: dict) -> bool:
    """Blender の座標の箱（layout の Exclusions の bounds）の中か。pt は Resonite の (x, y, z) = Blender の (x, z, y)。"""
    x, y, z = pt
    lo, hi = box["min"], box["max"]
    return lo[0] < x < hi[0] and lo[1] < z < hi[1] and lo[2] < y < hi[2]


def envelopes(doc: dict | None = None, bundle: Path | None = None, layout: dict | None = None) -> dict:
    key = gimmicks.g05()["district"]
    bundle = bundle or _bundle(key)
    doc = doc or json.loads((bundle / "p2.apply.json").read_text(encoding="utf-8"))
    layout = layout or json.loads((PROJECT_ROOT / "layout" / "areas" / f"{key}.json").read_text(encoding="utf-8"))
    excl = {e["zone_id"]: e for e in layout["Exclusions"]}
    clearance = {p["asset_id"]: p.get("clearance_radius_m") for p in layout["placements"]}
    out: dict = {"G05": [], "G06": []}
    corridor = excl["Excl_B_CentralSightlineCorridor"]["bounds"]
    for g in gimmicks.g05()["ghosts"]:
        asset = _find_decl(doc, g["asset_id"])
        pivot = _find_decl(asset, g["motion_root"])
        rest = pivot["slot"].get("position") or [0, 0, 0]
        lo, hi = g["bob_m"]
        pts: list[tuple] = []
        radius = 0.0
        for k in range(-4, 5):
            yaw = -g["yaw_deg"] * k / 4.0            # Resonite の Y まわり（Blender の Z まわりの逆）
            for lift in (lo, 0.0, hi):
                local = _local_points(bundle, doc, pivot, _yq(yaw), (rest[0], rest[1] + lift, rest[2]))
                radius = max([radius] + [math.hypot(x - rest[0], z - rest[2]) for x, _, z in local])
                pts += _to_district(asset, local)
        in_corridor = sum(1 for p in pts if _in_box_res(p, corridor))
        out["G05"].append({"asset_id": g["asset_id"], "moving_radius_m": round(radius, 4), "clearance_radius_m": clearance.get(g["asset_id"]),
                           "within_clearance": clearance.get(g["asset_id"]) is not None and radius <= clearance[g["asset_id"]] + 1e-6,
                           "lowest_m": round(min(p[1] for p in pts), 4), "points_in_central_corridor": in_corridor})
    swing = excl["Excl_B_DoorSwingAndPorch"]["bounds"]
    for h in gimmicks.g06()["hinges"]:
        asset = _find_decl(doc, h["asset_id"])
        hinge = _find_decl(asset, h["motion_root"])
        hp = hinge["slot"].get("position") or [0, 0, 0]
        closed_front = None
        porch_out = 0.0
        outside = 0
        for k in range(0, 18):
            ang = h["open_deg"] * k / 17.0
            yaw = -h["open_sign_blender_z"] * ang
            pts = _to_district(asset, _local_points(bundle, doc, hinge, _yq(yaw), hp))
            front = min(p[2] for p in pts)
            if closed_front is None:
                closed_front = front
            porch_out = max(porch_out, closed_front - front)
            outside += sum(1 for p in pts if not (swing["min"][0] - 1e-6 <= p[0] <= swing["max"][0] + 1e-6
                                                 and swing["min"][1] - 1e-6 <= p[2] <= swing["max"][1] + 1e-6))
        out["G06"].append({"hinge": h["motion_root"], "closed_front_z": round(closed_front, 4),
                           "beyond_closed_front_toward_porch_m": round(porch_out, 4), "points_outside_swing_zone": outside})
    return out


def envelope_problems(env: dict) -> list[str]:
    problems = []
    for r in env["G05"]:
        if not r["within_clearance"]:
            problems.append(f"{r['asset_id']}: moving radius {r['moving_radius_m']} m exceeds the W03 clearance {r['clearance_radius_m']} m")
        if r["points_in_central_corridor"]:
            problems.append(f"{r['asset_id']}: {r['points_in_central_corridor']} points enter the central corridor")
    for r in env["G06"]:
        if r["beyond_closed_front_toward_porch_m"] > DOOR_PORCH_TOL_M:
            problems.append(f"{r['hinge']}: swings {r['beyond_closed_front_toward_porch_m']} m toward the porch")
        if r["points_outside_swing_zone"]:
            problems.append(f"{r['hinge']}: {r['points_outside_swing_zone']} points leave the W03 door swing zone")
    return problems


# ---- 観察 ------------------------------------------------------------------------------------------------------------

def observe_params(url: str) -> dict[str, float]:
    v = variables()
    sels = [f"$member:{s['key']}.Value" for s in v.values()]
    data = run_json(["resoloop", "observe", *sels, "--state", str(P3_STATE), "--url", url, "--json"])
    return {n: float(data["data"]["values"][f"$member:{s['key']}.Value"]["member"]["value"]) for n, s in v.items()}


def b_hierarchy(url: str, depth: int = 4) -> dict:
    return run_json(["resoloop", "hierarchy", "--under", f"{gimmicks.P2_ROOT}/{gimmicks.g05()['district']}", "--depth", str(depth),
                     "--url", url, "--json"])


def check_relays(url: str, keys: dict[str, str]) -> list[str]:
    """中継の Drives が FloatPivot・蝶番の Slot のメンバーを指し、有効か。"""
    targets = [(g["motion_root"], m, "g05") for g in gimmicks.g05()["ghosts"] for m in ("Position", "Rotation")]
    targets += [(h["motion_root"], "Rotation", "g06") for h in gimmicks.g06()["hinges"]]
    sels = [f"$member:{district.relay_key(keys[n], m, gid)}.{mem}" for n, m, gid in targets for mem in ("Drives", "Enabled")]
    data = run_json(["resoloop", "observe", *sels, "--state", str(B_STATE), "--url", url, "--json"])["data"]["values"]
    problems = []
    ids: dict[str, dict] = {}
    for n, m, gid in targets:
        if n not in ids:
            ids[n] = run_json(["resoloop", "inspect", f"$slot:{keys[n]}", "--state", str(B_STATE), "--members", "--url", url,
                               "--json"])["data"]["members"]
        sel = f"$member:{district.relay_key(keys[n], m, gid)}"
        elems = data[f"{sel}.Drives"]["member"]["elements"]
        if data[f"{sel}.Enabled"]["member"]["value"] is not True:
            problems.append(f"{n}: relay {m} is disabled")
        if [e.get("targetId") for e in elems] != [ids[n][m]["id"]]:
            problems.append(f"{n}: relay {m} does not drive the Slot {m}")
    return problems


def frozen_probe(url: str, keys: dict[str, str], rest: dict, raw: list) -> dict:
    """時刻を止めた標本（G05Frequency・G06Frequency = 0 で θ = s φ・2π p の姿勢）を Slot そのもので取り、速さを戻す。

    窓ごとに取り、窓の間で比べる（同じ位相の位置が数分の間にずれないか。check_drift）。式とも照合する。
    """
    v = variables()
    ids = {n: component_id(f"$member:{v[n]['key']}.Value", P3_STATE, url) for n in ("G05Frequency", "G06Frequency")}
    before = observe_params(url)
    try:
        for n in ids:
            set_member(ids[n], "Value", "0", url)
        time.sleep(1.5)
        params = params_of(observe_params(url))
        hier = b_hierarchy(url, depth=2)
        raw.append({"kind": "frozen_probe", "data": hier})
        slots = read_slots(hier["data"], rest)
    finally:
        for n in ids:
            set_member(ids[n], "Value", str(before[n]), url)
    restored = observe_params(url)
    res = check_frozen(slots, params, "slot")
    problems = list(res["problems"])
    if restored != before:
        problems.append(f"frozen probe: variables not restored: {restored} != {before}")
    return {"params": params, "slots": {"ghosts": {a: {"lift_m": round(g["lift_m"], 5), "sway_deg": round(g["sway_deg"], 4)}
                                                   for a, g in slots["ghosts"].items()},
                                        "doors": {n: {"open_deg": round(d["open_deg"], 4)} for n, d in slots["doors"].items()}},
            "problems": problems}


def check_drift(probes: list[dict]) -> dict:
    """窓ごとの時刻を止めた標本を、最初の窓と比べる。同じ位相の上下の差 1 cm 以内、揺れ・扉の開きの差 0.5° 以内。"""
    rows, problems = [], []
    if len(probes) < 2:
        return {"rows": rows, "problems": ["drift: needs two windows"]}
    base = probes[0]["slots"]
    for i, p in enumerate(probes[1:], start=2):
        if p["params"] != probes[0]["params"]:
            problems.append(f"drift: window {i} was probed with other values {p['params']}")
        for a, g in base["ghosts"].items():
            o = p["slots"]["ghosts"].get(a)
            if o is None:
                problems.append(f"drift: {a} is not observed in window {i}")
                continue
            dl, ds = abs(o["lift_m"] - g["lift_m"]), abs(o["sway_deg"] - g["sway_deg"])
            rows.append({"window": i, "asset_id": a, "lift_diff_m": round(dl, 5), "sway_diff_deg": round(ds, 4)})
            if dl > DRIFT_TOL_M or ds > DRIFT_TOL_DEG:
                problems.append(f"drift: {a} moved {dl:.4f} m / {ds:.3f} deg at the same phase by window {i}")
        for n, d in base["doors"].items():
            o = p["slots"]["doors"].get(n)
            if o is None:
                problems.append(f"drift: {n} is not observed in window {i}")
                continue
            dd = abs(o["open_deg"] - d["open_deg"])
            rows.append({"window": i, "hinge": n, "open_diff_deg": round(dd, 4)})
            if dd > DRIFT_TOL_DEG:
                problems.append(f"drift: {n} opened {dd:.3f} deg more or less at the same phase by window {i}")
    return {"rows": rows, "problems": problems}


def observe_window(url: str, duration: float, raw: list) -> dict:
    keys = b_keys(STATE_DIR)
    rest = rest_positions()
    sels = relay_selectors(keys)
    params_raw = observe_params(url)
    params = params_of(params_raw)
    window: dict = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "params": params_raw, "samples": [], "problems": []}
    hier = b_hierarchy(url)
    raw.append({"kind": "hierarchy_start", "data": hier})
    window["structure_start"] = check_structure(hier["data"])
    window["relay_problems"] = check_relays(url, keys)
    window["frozen_probe"] = frozen_probe(url, keys, rest, raw)
    t_end = time.time() + duration
    while time.time() < t_end:
        t, obs = timed(["resoloop", "observe", *sels, "--state", str(B_STATE), "--url", url, "--json"])
        raw.append({"kind": "relays", "t": t, "data": obs})
        s = read_sample(obs["data"]["values"], keys, rest)
        s["t"] = round(t, 3)
        s["problems"] = check_sample(s, params)
        window["samples"].append(s)
    hier2 = b_hierarchy(url)
    raw.append({"kind": "hierarchy_end", "data": hier2})
    window["structure_end"] = check_structure(hier2["data"])
    smp = window["samples"]
    window["summary"] = {
        "samples": len(smp),
        "ghosts": {g["asset_id"]: {"lift_m": [round(min(s["ghosts"][g["asset_id"]]["lift_m"] for s in smp), 4),
                                              round(max(s["ghosts"][g["asset_id"]]["lift_m"] for s in smp), 4)],
                                   "sway_deg": [round(min(s["ghosts"][g["asset_id"]]["sway_deg"] for s in smp), 3),
                                                round(max(s["ghosts"][g["asset_id"]]["sway_deg"] for s in smp), 3)]}
                   for g in gimmicks.g05()["ghosts"]},
        "doors": {h["motion_root"]: [round(min(s["doors"][h["motion_root"]]["open_deg"] for s in smp), 3),
                                     round(max(s["doors"][h["motion_root"]]["open_deg"] for s in smp), 3)]
                  for h in gimmicks.g06()["hinges"]},
        "max_door_asymmetry_deg": round(max(abs(s["doors"][gimmicks.g06()["hinges"][0]["motion_root"]]["open_deg"]
                                                - s["doors"][gimmicks.g06()["hinges"][1]["motion_root"]]["open_deg"]) for s in smp), 3),
    }
    for s in smp:
        window["problems"].extend(s["problems"])
    window["variation_problems"] = check_variation(smp, params)
    window["door_clock"] = check_door_clock(smp, params)
    window["problems"] += (window["variation_problems"] + window["door_clock"]["problems"] + window["relay_problems"]
                           + window["frozen_probe"]["problems"]
                           + window["structure_start"]["problems"] + window["structure_end"]["problems"])
    window["ok"] = not window["problems"]
    return window


# ---- 外から変えられる値の確認 -------------------------------------------------------------------------------------------

def _frozen_case(url: str, label: str, keys: dict[str, str], rest: dict, sels: list[str], raw: list) -> dict:
    time.sleep(1.0)
    params_raw = observe_params(url)
    params = params_of(params_raw)
    res = []
    for _ in range(2):
        _, obs = timed(["resoloop", "observe", *sels, "--state", str(B_STATE), "--url", url, "--json"])
        hier = b_hierarchy(url, depth=2)
        raw.append({"kind": f"frozen_{label}", "data": [obs, hier]})
        res.append(check_frozen(read_sample(obs["data"]["values"], keys, rest), params, "relay"))
        res.append(check_frozen(read_slots(hier["data"], rest), params, "slot"))
    return {"params": params_raw, "rows": res[-2]["rows"], "slot_rows": res[-1]["rows"], "problems": [p for r in res for p in r["problems"]]}


def param_check(url: str, raw: list) -> dict:
    out: dict = {"problems": []}
    keys = b_keys(STATE_DIR)
    rest = rest_positions()
    sels = relay_selectors(keys)
    v = variables()
    ids = {n: component_id(f"$member:{s['key']}.Value", P3_STATE, url) for n, s in v.items()}
    before = observe_params(url)
    out["before"] = before

    def put(name: str, value: float) -> None:
        set_member(ids[name], "Value", str(value), url)

    try:
        # 0) 時刻を止めた標本
        put("G05Frequency", 0.0)
        put("G06Frequency", 0.0)
        for spread in (before["G05PhaseSpread"], 0.5, 0.0):
            put("G05PhaseSpread", spread)
            for phase in (0.0, 0.2, 0.25, 0.5):
                put("G06Phase", phase)
                case = _frozen_case(url, f"spread_{spread}_phase_{phase}", keys, rest, sels, raw)
                out[f"frozen_spread_{spread}_phase_{phase}"] = case
                out["problems"].extend(case["problems"])
                if spread != before["G05PhaseSpread"]:
                    break   # 位相の倍率を変えた標本は扉の位置 1 つで足りる
        put("G05PhaseSpread", before["G05PhaseSpread"])
        put("G06Phase", 0.5)
        put("G06Intensity", 0.5)
        case = _frozen_case(url, "g06_intensity_0.5", keys, rest, sels, raw)
        out["frozen_G06Intensity_0.5"] = case
        out["problems"].extend(case["problems"])
        # 範囲の外の値: 強さ 5 → 1（扉は全開の位置で見る）、位相の倍率 1.5 → 1、速さ -1 → 0（止まる）。収めないと、おばけは
        # 5 倍の上下、002 は θ = 1.5π の姿勢（上下 -0.10 m・揺れ 14.1°）、扉は 425°（65° に見える）になり、式の値から外れる
        put("G05Intensity", 5.0)
        put("G05PhaseSpread", 1.5)
        put("G06Intensity", 5.0)
        put("G06Phase", 0.5)
        put("G05Frequency", -1.0)
        put("G06Frequency", -1.0)
        case = _frozen_case(url, "out_of_range_high", keys, rest, sels, raw)
        out["frozen_out_of_range_high"] = case
        out["problems"].extend(case["problems"])
        # 周期の位置 1.5 → 1（閉じる）。収めないと θ = 3π で全開になる
        put("G06Phase", 1.5)
        case = _frozen_case(url, "out_of_range_phase", keys, rest, sels, raw)
        out["frozen_out_of_range_phase"] = case
        out["problems"].extend(case["problems"])
        put("G05Intensity", -1.0)
        put("G06Intensity", -1.0)
        put("G06Phase", 0.5)
        case = _frozen_case(url, "out_of_range_low", keys, rest, sels, raw)
        out["frozen_out_of_range_low"] = case
        out["problems"].extend(case["problems"])
    finally:
        for name in v:
            put(name, before[name])
    # 1) ゆっくりの時刻（G05）
    try:
        put("G05Frequency", CLOCK_FREQUENCY)
        time.sleep(1.0)
        params = params_of(observe_params(url))
        t1, o1 = timed(["resoloop", "observe", *sels, "--state", str(B_STATE), "--url", url, "--json"])
        time.sleep(CLOCK_WAIT_S)
        t2, o2 = timed(["resoloop", "observe", *sels, "--state", str(B_STATE), "--url", url, "--json"])
        raw.append({"kind": "relays_clock", "t": [t1, t2], "data": [o1, o2]})
        out["G05_clock"] = {"params": params, **check_clock(read_sample(o1["data"]["values"], keys, rest), t1,
                                                            read_sample(o2["data"]["values"], keys, rest), t2, params)}
        out["problems"].extend(out["G05_clock"]["problems"])
    finally:
        put("G05Frequency", before["G05Frequency"])
    # 2) G05Intensity 0.5・0 で範囲が縮む
    try:
        for value in (0.5, 0.0):
            put("G05Intensity", value)
            params = params_of(observe_params(url))
            samples = []
            for _ in range(8):
                _, obs = timed(["resoloop", "observe", *sels, "--state", str(B_STATE), "--url", url, "--json"])
                raw.append({"kind": f"relays_g05_intensity_{value}", "data": obs})
                s = read_sample(obs["data"]["values"], keys, rest)
                s["problems"] = check_sample(s, params)
                samples.append(s)
                time.sleep(0.6)
            lifts = [s["ghosts"][a]["lift_m"] for s in samples for a in s["ghosts"]]
            sways = [abs(s["ghosts"][a]["sway_deg"]) for s in samples for a in s["ghosts"]]
            out[f"G05Intensity_{value}"] = {"lift_range_m": [round(min(lifts), 5), round(max(lifts), 5)],
                                            "sway_abs_max_deg": round(max(sways), 4),
                                            "problems": [p for s in samples for p in s["problems"]]}
            out["problems"].extend(out[f"G05Intensity_{value}"]["problems"])
    finally:
        put("G05Intensity", before["G05Intensity"])
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
    ap.add_argument("--duration", type=float, default=50.0, help="1 つの窓の観察の秒数（扉の周期の半分を 2 回以上含む長さ）")
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
            wins.append(observe_window(args.url, args.duration, raw))
        env = envelopes()
        drift = check_drift([w["frozen_probe"] for w in wins])
        result = {"windows": wins, "gap_s": args.gap if args.windows > 1 else None, "drift": drift, "envelopes": env,
                  "envelope_problems": envelope_problems(env),
                  "tolerances": {"lift_m": LIFT_TOL_M, "deg": DEG_TOL, "horizontal_m": HORIZ_TOL_M, "off_axis": OFF_AXIS_TOL,
                                 "live_symmetry_deg": LIVE_SYMMETRY_DEG, "cross_s": CROSS_TOL_S, "frozen_lift_m": FROZEN_LIFT_TOL_M,
                                 "frozen_deg": FROZEN_DEG_TOL, "local": LOCAL_TOL}}
        # 漂いの判定は 2 つ以上の窓が要る（1 つの窓の試しでは問題にしない）
        drift_problems = drift["problems"] if args.windows > 1 else []
        result["ok"] = all(w["ok"] for w in wins) and not result["envelope_problems"] and not drift_problems
    args.raw_out.parent.mkdir(parents=True, exist_ok=True)
    args.raw_out.write_text(json.dumps(raw, ensure_ascii=False) + "\n", encoding="utf-8")
    if not args.param_check:
        # コミットする記録には観察の列を入れない（要約と問題だけ）。列は --raw-out にある
        for w in result["windows"]:
            w["samples"] = [{"t": s["t"], "ghosts": {a: {k: round(x, 5) for k, x in g.items()} for a, g in s["ghosts"].items()},
                             "doors": {n: {k: round(x, 4) for k, x in d.items()} for n, d in s["doors"].items()}} for s in w["samples"]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {k: v for k, v in result.items() if k not in ("windows",)}
    if not args.param_check:
        summary["windows"] = [{"ok": w["ok"], "summary": w["summary"], "door_clock": {k: w["door_clock"].get(k) for k in
                                                                                      ("intervals_s", "expected_interval_s")},
                               "problems": w["problems"][:10]} for w in result["windows"]]
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
