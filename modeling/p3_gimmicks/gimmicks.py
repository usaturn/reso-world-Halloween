"""W10: P3 の自動ギミックの定義（どの部品を、どの値で動かすか）。

値は地区の持ち主のデータから読み、ここには写さない（写すと食い違う）。
- G13 メリーゴーラウンドの床の回転: layout/areas/D_amusement.json の gimmick_specs.G13_carousel_rotation（W05）
- G01 小カボチャのダンス: assets/manifest/A_plaza.json の各アセットの motion（W02）
- G09 大釜の攪拌と泡・煙、G11 魔女の巡回（W10-C）: layout/areas/C_candy.json の Hero_or_Gimmick と assets/manifest/C_candy.json（W04）

座標: Blender の (x, y, z) は Resonite の (x, z, y)。Blender の Z まわり +θ は Resonite の Y まわり -θ
（docs/p2-static-integration.md 14 章。軸を入れ替えると右手系と左手系が入れ替わるので、回る向きの符号が変わる）。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
P2_ROOT = "Root/HalloweenMagicalCarnival"

# P3 の宣言（content/p3_gimmicks.json）の root。W08 の root の直下に置く。値の置き場（DynamicVariableSpace）と、
# ProtoFlux のモジュールの配備先を持つ
P3_ROOT_NAME = "P3_Gimmicks"
P3_OWNERSHIP = "hmc_p3"   # content/p3_gimmicks.json の ownership.key。state は親の checkout の .resoloop/state/p3_gimmicks.json
P3_ROOT_PATH = f"{P2_ROOT}/{P3_ROOT_NAME}"
SPACE_NAME = "HMC_P3"

# G01 の外から変えられる値（DynamicValueVariable<float> の名前・宣言の Component のキー・既定値）。モジュールの中で範囲に収める。
# 宣言のキー・ownership のキーは 10 文字未満にする（Gitleaks の generic-api-key は "key": "<10 文字以上の識別子>" に当たる）
G01_VARIABLES = {
    "G01Intensity": {"key": "g01_amp", "default": 1.0, "min": 0.0, "max": 1.0,
                     "meaning": "上下・傾きの大きさ（1 で W02 の範囲いっぱい、0 で基準姿勢に止まる）"},
    "G01Frequency": {"key": "g01_freq", "default": 0.8, "min": 0.0, "max": 2.0,
                     "meaning": "上下の速さ（Hz）。傾きはその半分の速さで左右に振れる"},
    "G01PhaseSpread": {"key": "g01_phase", "default": 1.0, "min": 0.0, "max": 1.0,
                       "meaning": "個体ごとの位相（W02 の phase_deg）にかける倍率。0 で 6 体がそろって踊る"},
}
G01_FLUX_SLOT = "G01_Dance"          # P3_Gimmicks の子。G01 のモジュールの配備先
G01_MODULE = "P3PlazaDance"

# W10-A: G03 噴水の水と光の周期変化。水のメッシュ（W02 の APL_Fountain_001_Water）だけに、A の共有の材質
# （MAT_APL_MagicWater）を写した専用の材質を付け、その EmissiveColor を ProtoFlux が drive する（docs/p3-gimmicks.md 16 章）
G03_VARIABLES = {
    "G03Intensity": {"key": "g03_amp", "default": 1.0, "min": 0.0, "max": 2.0,
                     "meaning": "発光の強さの倍率（1 で P2 の発光を中心に変化、0 で発光なし、2 は定期ショーの盛り上がり）"},
    "G03Frequency": {"key": "g03_freq", "default": 0.2, "min": 0.0, "max": 1.0,
                     "meaning": "明るさの脈の速さ（Hz）。色の移り変わりはその半分の速さ。0 で時刻を止める"},
    "G03Swing": {"key": "g03_swing", "default": 1.0, "min": 0.0, "max": 1.0,
                 "meaning": "変化の深さ（0 で P2 の色のまま一定、1 で明るさ 0.5〜1.5 倍・色は紫まで）"},
}
G03_FLUX_SLOT = "G03_Fountain"       # P3_Gimmicks の子。G03 のモジュールの配備先
G03_MODULE = "P3FountainGlow"
G03_MATERIAL_KEY = "p3_g03_wm"        # A の宣言に足す水の専用の材質（PBS_Metallic）の Component のキー（10 文字未満）
G03_PULSE_DEPTH = 0.5                 # 明るさの脈の半幅（G03Swing = 1 で 1 ± 0.5 倍）
# 色の移り変わりの先（線形の値。HDR）。P2 の水の青（線形 (0.504, 0.99, 1.764)）から、ハロウィンの魔法の紫へ
G03_SHIFT_EMISSIVE_LINEAR = (1.2, 0.4, 2.0)


# W10-B: G05 おばけの浮遊・G06 屋敷の扉の開閉（B 北・おばけ屋敷）。部品・範囲は W03 の layout/areas/B_mansion.json の
# Hero_or_Gimmick.gimmicks から読む。ProtoFlux のモジュールは B 用に 1 つ（worldState は B の state。docs/p3-gimmicks.md 17 章）
G05_VARIABLES = {
    "G05Intensity": {"key": "g05_amp", "default": 1.0, "min": 0.0, "max": 1.0,
                     "meaning": "上下・揺れの大きさ（1 で G05_BOB_RANGE_M・W03 の揺れの範囲いっぱい、0 で基準姿勢に止まる）"},
    "G05Frequency": {"key": "g05_freq", "default": 0.25, "min": 0.0, "max": 1.0,
                     "meaning": "上下の速さ（Hz）。左右の揺れはその半分の速さ"},
    "G05PhaseSpread": {"key": "g05_phase", "default": 1.0, "min": 0.0, "max": 1.0,
                       "meaning": "個体ごとの位相（G05_PHASE_DEG）にかける倍率。0 で 2 体がそろう（I04 の一斉の挨拶）"},
}
# 上下の範囲（Blender の Z、基準からの m）。W03 の translation_range_m（-0.35〜+0.35）の中の部分。001 は下げ幅が -0.18 m より
# 下だと、手提げのランタンが隣のベンチ BMN_CMN_Bench_001 の背もたれ（上端 z 2.45）に入る（Blender での確認。#59 の
# issuecomment-6557581300）。-0.10 でベンチとの隙間は 8 cm 以上
G05_BOB_RANGE_M = (-0.10, 0.35)
# 2 体の位相（度）。W03 のデータに位相は無いので、この子で決めた（上下が逆向き、揺れは 90° ずれる）
G05_PHASE_DEG = {"BMN_FloatingGhost_001": 0.0, "BMN_FloatingGhost_002": 180.0}
G06_VARIABLES = {
    "G06Intensity": {"key": "g06_amp", "default": 1.0, "min": 0.0, "max": 1.0,
                     "meaning": "開く角度の割合（1 で W03 の 85° まで、0 で閉じたまま）"},
    "G06Frequency": {"key": "g06_freq", "default": 1.0 / 24.0, "min": 0.0, "max": 0.2,
                     "meaning": "開閉の 1 周期の速さ（Hz。既定は 24 秒で 1 回）。0 で時刻を止める"},
    "G06Phase": {"key": "g06_phase", "default": 0.0, "min": 0.0, "max": 1.0,
                 "meaning": "開閉の周期の中の位置のずらし（周期の割合、0〜1）"},
}
# 開閉の形: c = (1 - cos θ) / 2 を、c < HOLD で閉じたまま、c > 1 - HOLD で開いたまま、その間を滑らかに（smoothstep）動く。
# HOLD 0.25 で、閉じたまま・開いたままが周期の 1/3 ずつ、開く・閉じるが 1/6 ずつ（24 秒の周期で 8 秒・4 秒）
G06_HOLD = 0.25
B_FLUX_SLOT = "G05_G06_Mansion"      # P3_Gimmicks の子。B のモジュールの配備先
B_MODULE = "P3MansionMotion"


# W10-C: G09 大釜の攪拌と泡・煙、G11 魔女の巡回（C 東・キャンディストリート）。部品・範囲は W04 の layout/areas/C_candy.json の
# Hero_or_Gimmick（G09・G11）と assets/manifest/C_candy.json から読む。ProtoFlux のモジュールは C 用に 1 つ（worldState は C の
# state。docs/p3-gimmicks.md 18 章）
G09_VARIABLES = {
    "G09StirFrequency": {"key": "g09_freq", "default": 1.0 / 6.0, "min": 0.0, "max": 1.0,
                         "meaning": "攪拌棒の回る速さ（回/秒。既定は 6 秒で 1 周）。0 で時刻を止める"},
    "G09StirPhase": {"key": "g09_phase", "default": 0.0, "min": 0.0, "max": 1.0,
                     "meaning": "攪拌棒の回転の位置のずらし（1 周の割合、0〜1）"},
    "G09Bubbles": {"key": "g09_bub", "default": 1.0, "min": 0.0, "max": 2.0,
                   "meaning": "泡の量の倍率（1 で毎秒 G09_PARTICLES の bubbles.rate 個、0 で出ない）"},
    "G09Smoke": {"key": "g09_smk", "default": 1.0, "min": 0.0, "max": 2.0,
                 "meaning": "煙の量の倍率（1 で毎秒 G09_PARTICLES の smoke.rate 個、0 で出ない）"},
}
# 液面の色（colorX。I02（W11）が書く）。既定は P2 の液面のエメラルドの材質の AlbedoColor（C の宣言から読む。g09_liquid_base）
G09_COLOR_VARIABLE = "G09LiquidColor"
G09_COLOR_KEY = "g09_color"
G09_LIQUID_MATERIAL_KEY = "p3_g09_lm"   # C の宣言に足す液面の専用の材質（PBS_Metallic）の Component のキー（10 文字未満）
# 泡・煙（PhotonDust）。rate は量の倍率 1 のときの毎秒の数。max は MaxParticleCount（rate × 寿命の最大 × 倍率の上限 2 より多め）。
# color_gain・start_alpha・end_alpha は液面の色にかける明るさと、生まれたとき・消えるときの透明度（ColorOverLifetimeStartEnd）
G09_PARTICLES = {
    "bubbles": {"attach": "bubble_emitter_attach", "prefix": "p3_gb_", "rate": 6.0, "max": 16, "radius": 0.4,
                "lifetime": (0.6, 1.2), "speed": (0.15, 0.35), "size": (0.05, 0.1), "grow": (0.6, 1.4),
                "color_gain": 1.6, "start_alpha": 0.9, "end_alpha": 0.6, "turbulence": 0.0},
    "smoke": {"attach": "smoke_audio_attach", "prefix": "p3_gs_", "rate": 3.0, "max": 24, "radius": 0.25,
              "lifetime": (2.5, 3.5), "speed": (0.25, 0.4), "size": (0.16, 0.24), "grow": (0.6, 2.2),
              "color_gain": 1.1, "start_alpha": 0.45, "end_alpha": 0.0, "turbulence": 0.3},
}
G11_VARIABLES = {
    "G11Frequency": {"key": "g11_freq", "default": 1.0 / 45.0, "min": 0.0, "max": 0.1,
                     "meaning": "巡回の速さ（周/秒。既定は 45 秒で 1 周、平均 約 1.36 m/s）。0 で時刻を止める"},
    "G11Phase": {"key": "g11_phase", "default": 0.0, "min": 0.0, "max": 1.0,
                 "meaning": "巡回の位置のずらし（1 周の割合、0〜1。k/8 で巡回の点 k）"},
}
C_FLUX_SLOT = "G09_G11_Candy"        # P3_Gimmicks の子。C のモジュールの配備先
C_MODULE = "P3CandyStreet"


# W10-D: G15 おばけ列車の周回（D 南・パンプキン遊園地）。経路（スタジアム型）・推奨の速さ・先頭車と客車の弧の差は W05 の
# layout/areas/D_amusement.json の gimmick_specs.G15_ghost_train_loop、部品は assets/manifest/D_amusement.json から読む。
# ProtoFlux のモジュールは D 用に 1 つ（worldState は D の state。G13 の Spinner と同じ地区。docs/p3-gimmicks.md 19 章）
G15_VARIABLES = {
    # 既定は W05 の recommended_speed_m_per_sec（g15() が食い違いを止める）
    "G15Speed": {"key": "g15_speed", "default": 2.2, "min": 0.0, "max": 3.0,
                 "meaning": "周回の速さ（m/秒。既定は W05 の推奨 2.2 m/s で 1 周 約 16.5 秒）。0 で止まる"},
    "G15Phase": {"key": "g15_phase", "default": 0.0, "min": 0.0, "max": 1.0,
                 "meaning": "周回の位置のずらし（1 周の割合、0〜1。0 で W05 の基準の位置）"},
}
D_FLUX_SLOT = "G15_GhostTrain"       # P3_Gimmicks の子。D のモジュールの配備先
D_MODULE = "P3GhostTrain"


def _c_gimmick(gid: str) -> dict:
    hits = [g for g in _load("layout/areas/C_candy.json")["Hero_or_Gimmick"] if g["gimmick_id"] == gid]
    if len(hits) != 1:
        raise ValueError(f"C_candy: expected one {gid}, found {len(hits)}")
    return hits[0]


def g09() -> dict:
    """G09 の大釜。攪拌棒の Pivot（回転は Blender の +Z まわり、揺れは W04 の wobble_tilt_deg）、液面、泡・煙の取付位置。"""
    g = _c_gimmick("G09")
    rest = g["rest_pose"]
    lo, hi = rest["wobble_tilt_deg"]
    if g["motion_axis"] != "+Z" or any(abs(x) > 1e-9 for x in rest["stir_rod_rotation_deg"]) or abs(lo + hi) > 1e-9:
        raise ValueError(f"G09: unsupported motion {g['motion_axis']} {rest}")
    parts = g["sub_parts"]
    return {"gimmick_id": "G09", "district": "C_candy", "asset_id": g["asset_id"], "stir_pivot": parts["stir_rod_pivot"],
            "liquid": parts["liquid_surface"], "attach": {k: parts[v["attach"]] for k, v in G09_PARTICLES.items()},
            "wobble_deg": hi, "clear_radius_m": g["clear_radius_m"], "managed_fields": ["position", "scale"]}


def trig_coefficients(values: list[float]) -> tuple[list[float], list[float]]:
    """閉じた N 点（N は偶数）を等間隔の角度 2πk/N で通る三角補間の係数 a_n・b_n（n = 0〜N/2）。
    x(θ) = Σ a_n cos nθ + b_n sin nθ。θ = 2πk/N で値 k を通る。"""
    n_pts = len(values)
    if n_pts < 4 or n_pts % 2:
        raise ValueError(f"trig interpolation needs an even number of points, got {n_pts}")
    half = n_pts // 2
    a = [2.0 / n_pts * sum(v * math.cos(2 * math.pi * n * k / n_pts) for k, v in enumerate(values)) for n in range(half + 1)]
    b = [2.0 / n_pts * sum(v * math.sin(2 * math.pi * n * k / n_pts) for k, v in enumerate(values)) for n in range(half + 1)]
    a[0] /= 2.0
    a[half] /= 2.0
    b[0] = b[half] = 0.0
    return a, b


def trig_eval(coef: tuple[list[float], list[float]], theta: float, derivative: bool = False) -> float:
    a, b = coef
    if derivative:
        return sum(n * (-a[n] * math.sin(n * theta) + b[n] * math.cos(n * theta)) for n in range(len(a)))
    return sum(a[n] * math.cos(n * theta) + b[n] * math.sin(n * theta) for n in range(len(a)))


def g11() -> dict:
    """G11 の巡回。8 点の経路（Blender の世界座標）を三角補間の係数にし、高さは W04 の範囲に収める。

    乗せる物は仮モデル CCD_M08_FlyingWitchProxy_001（M08 の素材の宣言の親。M08 と点光源 2 つはその子）と、巡回路の
    CarrierPivot（W04 の motion_root。取付位置 CarrierAttach の親）。どちらも同じ姿勢で動かす。
    """
    g = _c_gimmick("G11")
    wps = [[float(c) for c in w] for w in g["patrol_loop_waypoints_m"]]
    if not g.get("patrol_loop_closed") or len(wps) != 8:
        raise ValueError(f"G11: expected a closed loop of 8 waypoints, got {len(wps)}")
    loop = next(a for a in _load("assets/manifest/C_candy.json")["assets"] if a["asset_id"] == g["asset_id"])
    roots = loop["hierarchy"]["motion_roots"]
    if len(roots) != 1:
        raise ValueError(f"G11: expected one carrier pivot, got {roots}")
    carrier = next(p for p in loop["parts"] if p["part_id"] == roots[0])
    origin = [float(c) for c in loop["origin_world"]]
    rider = g["rider_asset_id"]
    coef = [trig_coefficients([w[i] for w in wps]) for i in range(3)]
    lo, hi = float(g["min_altitude_m"]), float(g["max_altitude_m"])
    if any(not (lo - 1e-9 <= w[2] <= hi + 1e-9) for w in wps):
        raise ValueError("G11: a waypoint is outside the altitude range")
    # 仮モデルの基準姿勢は巡回の点 0 で、正面（+Y）が点 0 の接線の向き（θ = 0 の接線は +Y）
    pivot_world = [origin[i] + float(carrier["pivot_local"][i]) for i in range(3)]
    if max(abs(pivot_world[i] - wps[0][i]) for i in range(3)) > 1e-6:
        raise ValueError(f"G11: carrier pivot {pivot_world} is not at waypoint 0 {wps[0]}")
    return {"gimmick_id": "G11", "district": "C_candy", "loop_asset_id": g["asset_id"], "loop_origin": origin,
            "carrier": carrier["part_id"], "rider": rider, "waypoints": wps, "altitude_m": [lo, hi], "coefficients": coef,
            "managed_fields": ["scale"]}


def g11_pose(theta: float, g: dict | None = None) -> tuple[list[float], float]:
    """θ（ラジアン）の位置（Blender の世界座標、高さは範囲に収める）と、進む向き（Resonite の Y まわりの角度、ラジアン。
    ローカル +Z（= Blender の +Y、魔女の正面）が (sin ψ, cos ψ) を向く）。"""
    g = g or g11()
    c = g["coefficients"]
    lo, hi = g["altitude_m"]
    x, y = trig_eval(c[0], theta), trig_eval(c[1], theta)
    z = min(max(trig_eval(c[2], theta), lo), hi)
    return [x, y, z], math.atan2(trig_eval(c[0], theta, True), trig_eval(c[1], theta, True))


def g09_liquid_base(declaration: dict) -> dict:
    """C の宣言の液面の 1 つ目の材質（P2 のエメラルド）の AlbedoColor と、EmissiveColor との比（sRGB の値の 3 成分の平均）。"""
    g = g09()
    found = []
    stack = [declaration]
    while stack:
        n = stack.pop()
        if n["slot"]["name"] == g["liquid"]:
            found.append(n)
        stack.extend(n.get("children", []))
    if len(found) != 1:
        raise ValueError(f"C declaration: expected one {g['liquid']}, found {len(found)}")
    comps = found[0].get("components", [])
    mine = [c for c in comps if c.get("key") == G09_LIQUID_MATERIAL_KEY]
    if len(mine) == 1:
        albedo = [float(x) for x in mine[0]["initialFields"]["AlbedoColor"]]
        emissive = [float(x) for x in mine[0]["initialFields"]["EmissiveColor"]]
    else:
        raise ValueError(f"C declaration: expected one {G09_LIQUID_MATERIAL_KEY} (export C with the G09 material first)")
    gain = sum(e / a for e, a in zip(emissive[:3], albedo[:3])) / 3.0
    return {"albedo": albedo, "emissive": emissive, "glow_gain": gain}


def _b_gimmick(gid: str) -> dict:
    return _load("layout/areas/B_mansion.json")["Hero_or_Gimmick"]["gimmicks"][gid]


def g05() -> dict:
    """G05 の 2 体。FloatPivot（motion_root）・範囲・位相。上下は Blender の Z、揺れは Z まわり（W03 のデータ）。"""
    rows = []
    for m in _b_gimmick("G05")["motion_roots"]:
        if m["translation_axis"] != "Z" or m["rotation_axis"] != "Z" or any(abs(x) > 1e-9 for x in m["rest_pose_euler_deg"]):
            raise ValueError(f"G05 {m['part_id']}: unsupported motion {m}")
        lo, hi = m["translation_range_m"]
        if not (lo - 1e-9 <= G05_BOB_RANGE_M[0] < 0.0 < G05_BOB_RANGE_M[1] <= hi + 1e-9):
            raise ValueError(f"G05 {m['part_id']}: bob range {G05_BOB_RANGE_M} is outside the W03 range {m['translation_range_m']}")
        rlo, rhi = m["rotation_range_deg"]
        if abs(rlo + rhi) > 1e-9:
            raise ValueError(f"G05 {m['part_id']}: unsupported rotation range {m['rotation_range_deg']}")
        rows.append({"asset_id": m["asset_id"], "motion_root": m["part_id"], "bob_m": list(G05_BOB_RANGE_M),
                     "w03_bob_m": [lo, hi], "yaw_deg": rhi, "phase_deg": G05_PHASE_DEG[m["asset_id"]]})
    if len(rows) != 2:
        raise ValueError(f"G05: expected 2 floating ghosts, found {len(rows)}")
    return {"gimmick_id": "G05", "district": "B_mansion", "ghosts": rows, "managed_fields": ["scale"]}


def g06() -> dict:
    """G06 の左右の扉。蝶番（motion_root）と、開く向き（Blender の Z まわりの符号）。範囲は 0 から ±85°（W03 のデータ）。"""
    rows = []
    for m in _b_gimmick("G06")["motion_roots"]:
        lo, hi = m["rotation_range_deg"]
        if m["rotation_axis"] != "Z" or any(abs(x) > 1e-9 for x in m["rest_pose_euler_deg"]) or min(abs(lo), abs(hi)) > 1e-9:
            raise ValueError(f"G06 {m['part_id']}: unsupported motion {m}")
        sign = 1.0 if hi > 0 else -1.0
        rows.append({"asset_id": m["asset_id"], "motion_root": m["part_id"], "open_sign_blender_z": sign,
                     "open_deg": max(abs(lo), abs(hi))})
    if len(rows) != 2 or {r["open_sign_blender_z"] for r in rows} != {1.0, -1.0} or len({r["open_deg"] for r in rows}) != 1:
        raise ValueError(f"G06: expected a symmetric double door, found {rows}")
    return {"gimmick_id": "G06", "district": "B_mansion", "hinges": rows, "managed_fields": ["position", "scale"]}


def g03() -> dict:
    """G03 の対象。水のメッシュの部品は W02 のアセット一覧の motion から読む（ここに写さない）。"""
    hits = [a for a in _load("assets/manifest/A_plaza.json")["assets"] if (a.get("motion") or {}).get("gimmick_id") == "G03"]
    if len(hits) != 1:
        raise ValueError(f"G03: expected one asset, found {len(hits)}")
    asset = hits[0]
    motion = asset["motion"]
    water = motion["water_mesh_part"]
    if water not in asset["hierarchy"]["motion_roots"]:
        raise ValueError(f"G03 {asset['asset_id']}: {water} is not a motion root")
    return {"gimmick_id": "G03", "district": "A_plaza", "asset_id": asset["asset_id"], "water_slot": water,
            "motion_type": motion["type"]}


def srgb_to_linear(c: float) -> float:
    """sRGB の符号化の値を線形にする（1 を超える HDR の値も同じ式を延ばす。P2 の export の値の作り方と同じ）。"""
    c = float(c)
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def g03_base_emissive(declaration: dict) -> list[float]:
    """A の宣言の水の専用の材質（district.add_g03_material）の EmissiveColor の初期値（sRGB の [r, g, b, a]）。"""
    found = []
    stack = [declaration]
    while stack:
        n = stack.pop()
        found += [c for c in n.get("components", []) if c.get("key") == G03_MATERIAL_KEY]
        stack.extend(n.get("children", []))
    if len(found) != 1:
        raise ValueError(f"A declaration: expected one {G03_MATERIAL_KEY}, found {len(found)} (export A with the G03 material first)")
    return [float(x) for x in found[0]["initialFields"]["EmissiveColor"]]


def _load(rel: str) -> dict:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def g13() -> dict:
    """G13 の駆動の設定。Spinner の _speed は Resonite の軸の度/秒。"""
    spec = _load("layout/areas/D_amusement.json")["gimmick_specs"]["G13_carousel_rotation"]
    if spec["axis_local"] != "+Z" or spec["motion_type"] != "continuous_rotation":
        raise ValueError(f"G13: unsupported motion {spec['axis_local']} {spec['motion_type']}")
    speed = float(spec["recommended_speed_deg_per_sec"])
    return {
        "gimmick_id": "G13",
        "district": "D_amusement",
        "motion_root": spec["motion_root"],
        "speed_deg_per_sec_blender_z": speed,
        # Blender の +Z まわり（上から見て反時計回り）= Resonite の Y まわりの負の向き
        "spinner_speed": [0.0, -speed, 0.0],
        "managed_fields": ["position", "scale"],   # 回転は Spinner が駆動する
    }


def stadium_pose(u: float, radius: float, straight: float) -> tuple[float, float, float]:
    """スタジアム型の閉じた経路の、始点からの弧の長さ u（0〜周の長さ）の位置と向き。

    線路の中心のローカル（Blender の x・y）で、始点は西の直線の南の端 (−R, −S/2)。西の直線を +Y へ → 北の半円 → 東の直線を −Y へ
    → 南の半円の順（上から見て時計回り。W05 の stadium_oval_clockwise）。各区間の進み具合を 0〜1 に収めて足すので、区間の分岐が
    要らない（ProtoFlux の式も同じ形。build_content.protograph_d）:
        d1 = S·clamp01(u/S)、β1 = π·clamp01((u − S)/πR)、d2 = S·clamp01((u − S − πR)/S)、β2 = π·clamp01((u − 2S − πR)/πR)
        x = −R − R cos β1 + R cos β2、y = −S/2 + d1 + R sin β1 − d2 − R sin β2
    返す 3 つ目は進む向き θ = β1 + β2（ラジアン）。正面（Blender の +Y = Resonite の +Z）を Resonite の Y まわりに θ 回した向き
    （Blender の Z まわりは −θ。W05 の yaw_z_deg）。
    """
    r, s = float(radius), float(straight)
    half = math.pi * r

    def c01(x: float) -> float:
        return min(max(x, 0.0), 1.0)

    d1 = s * c01(u / s)
    b1 = math.pi * c01((u - s) / half)
    d2 = s * c01((u - s - half) / s)
    b2 = math.pi * c01((u - 2.0 * s - half) / half)
    x = -r - r * math.cos(b1) + r * math.cos(b2)
    y = -s / 2.0 + d1 + r * math.sin(b1) - d2 - r * math.sin(b2)
    return x, y, b1 + b2


def stadium_arc(x: float, y: float, radius: float, straight: float) -> tuple[float, float]:
    """stadium_pose の逆。線路の中心のローカルの水平の位置に最も近い経路の点の弧の位置 u と、経路からの距離。"""
    r, s = float(radius), float(straight)
    half = math.pi * r
    if y > s / 2.0:            # 北の半円（中心 (0, S/2)）。β1 = π − α
        a = math.atan2(y - s / 2.0, x)
        return s + r * (math.pi - a), abs(math.hypot(x, y - s / 2.0) - r)
    if y < -s / 2.0:           # 南の半円（中心 (0, −S/2)）。β2 = −α
        a = math.atan2(y + s / 2.0, x)
        return 2.0 * s + half + r * (-a), abs(math.hypot(x, y + s / 2.0) - r)
    if x < 0.0:                # 西の直線（+Y へ）
        return y + s / 2.0, abs(x + r)
    return s + half + (s / 2.0 - y), abs(x - r)   # 東の直線（−Y へ）


def g15() -> dict:
    """G15 のおばけ列車。経路（スタジアム型）・速さ・先頭車と客車の弧の差と、駆動する Slot（先頭車・客車の root と 4 つの車輪）。

    - 経路の式（stadium_pose）が W05 の経路点 20 個（位置と向き）と周の長さに合わなければ止める（式とデータの食い違い）
    - 位置は列車の asset root（DAM_GhostTrain_001）のローカル。線路の中心の asset root からの差（Blender）と、レールの上面の高さ
    - 先頭車・客車の基準の弧の位置は、アセット一覧の pivot_local（基準姿勢）を経路に照らして求める（build_content が宣言とも照合する）
    - 車輪は先頭車・客車の root の子で名前に Wheel を含む部品。root の原点はレールの上面なので、軸の高さ（pivot_local の z）が半径
    """
    spec = _load("layout/areas/D_amusement.json")["gimmick_specs"]["G15_ghost_train_loop"]
    if (spec["loop_shape"] != "stadium_oval_clockwise" or spec["forward_axis_local"] != "+Y" or spec["up_axis_local"] != "+Z"
            or spec["wheel_spin_axis_local"] != "+X"):
        raise ValueError(f"G15: unsupported loop {spec['loop_shape']} {spec['forward_axis_local']} {spec['wheel_spin_axis_local']}")
    r, s = float(spec["curve_radius_m"]), float(spec["straight_length_m"])
    length = 2.0 * s + 2.0 * math.pi * r
    if abs(length - float(spec["total_loop_length_m"])) > 1e-3:
        raise ValueError(f"G15: loop length {length} != {spec['total_loop_length_m']}")
    # 経路点の位置・向きは弧の上（曲線は 22.5° ごと）。distance_m は曲線を弦で足した値なので使わない（弧の長さとの差は最大
    # 約 0.18 m。周の長さ total_loop_length_m は弧の長さ）。位置から弧の位置を求め、式の位置・向きと照合する
    arcs = []
    for w in spec["waypoints"]:
        px, py = (float(c) for c in w["position_local"][:2])
        u, off = stadium_arc(px, py, r, s)
        x, y, th = stadium_pose(u, r, s)
        dyaw = (math.degrees(-th) - float(w["yaw_z_deg"]) + 180.0) % 360.0 - 180.0
        if off > 1e-3 or math.hypot(x - px, y - py) > 1e-3 or abs(dyaw) > 0.01 \
                or abs(float(w["position_local"][2]) - float(spec["rail_top_z_world_m"])) > 1e-6:
            raise ValueError(f"G15: waypoint {w['index']} {w['position_local']} {w['yaw_z_deg']} is not on the loop "
                             f"(u {u}, off {off}, yaw {-math.degrees(th)})")
        arcs.append(u)
    if arcs != sorted(arcs) or arcs[0] > 1e-6:
        raise ValueError(f"G15: waypoints are not in the travel order from the start {arcs}")
    speed = float(spec["recommended_speed_m_per_sec"])
    if abs(G15_VARIABLES["G15Speed"]["default"] - speed) > 1e-9:
        raise ValueError(f"G15: G15Speed default {G15_VARIABLES['G15Speed']['default']} != W05 {speed}")
    asset = next(a for a in _load("assets/manifest/D_amusement.json")["assets"] if a["asset_id"] == spec["train_asset_id"])
    roots = asset["hierarchy"]["motion_roots"]
    if len(roots) != 2:
        raise ValueError(f"G15: expected the engine and one car, got {roots}")
    parts = {p["part_id"]: p for p in asset["parts"]}
    engine, car = (next(r_ for r_ in roots if "Engine" in r_), next(r_ for r_ in roots if "Car" in r_))
    origin = [float(c) for c in asset["origin_world"]]
    center = [float(spec["track_center_world"][i]) - origin[i] for i in range(2)]
    rail = float(spec["rail_top_z_world_m"]) - origin[2]
    rest_arc = {}
    for name in (engine, car):
        p = parts[name]["pivot_local"]
        if abs(float(p[2]) - rail) > 1e-6:
            raise ValueError(f"G15: {name} rest height {p[2]} is not the rail top {rail}")
        # 基準姿勢は西の直線の上（x = −R、向き +Y）。弧の位置 u = y + S/2
        tx, ty = float(p[0]) - center[0], float(p[1]) - center[1]
        u = ty + s / 2.0
        x, y, _ = stadium_pose(u, r, s)
        if not (0.0 <= u <= s) or math.hypot(x - tx, y - ty) > 1e-6:
            raise ValueError(f"G15: {name} rest {p} is not on the west straight")
        rest_arc[name] = u
    gap = rest_arc[engine] - rest_arc[car]
    if abs(gap - float(spec["engine_to_car_arc_offset_m"])) > 1e-6:
        raise ValueError(f"G15: rest arc gap {gap} != {spec['engine_to_car_arc_offset_m']}")
    wheels = {}
    for pid, p in parts.items():
        if "Wheel" in pid and p["parent_part"] in (engine, car):
            wheels[pid] = {"parent": p["parent_part"], "radius_m": float(p["pivot_local"][2]),
                           "rest_local_blender": [float(c) for c in p["pivot_local"]]}
    if sorted(w["parent"] for w in wheels.values()) != sorted([engine, engine, car, car]):
        raise ValueError(f"G15: expected two wheels on the engine and the car, got {sorted(wheels)}")
    return {"gimmick_id": "G15", "district": "D_amusement", "asset_id": asset["asset_id"], "track_asset_id": spec["track_asset_id"],
            "engine": engine, "car": car, "wheels": dict(sorted(wheels.items())), "radius_m": r, "straight_m": s, "length_m": length,
            "center_local_blender": center, "rail_local_z": rail, "rest_arc_m": rest_arc, "arc_offset_m": gap, "speed_m_s": speed,
            "waypoints": spec["waypoints"], "waypoint_arc_m": arcs, "origin_world": origin,
            "managed_fields": ["scale"], "wheel_managed_fields": ["position", "scale"]}


def g15_car_pose(u: float, g: dict | None = None) -> tuple[list[float], float]:
    """弧の位置 u の、列車の asset root のローカルの位置（Resonite の (x, y, z)）と、Resonite の Y まわりの向き（ラジアン）。"""
    g = g or g15()
    x, y, th = stadium_pose(u % g["length_m"], g["radius_m"], g["straight_m"])
    c = g["center_local_blender"]
    return [c[0] + x, g["rail_local_z"], c[1] + y], th


def g01() -> dict:
    """G01 の 6 体。motion_root（_Body）・基準姿勢・範囲・位相。"""
    rows = []
    for asset in _load("assets/manifest/A_plaza.json")["assets"]:
        motion = asset.get("motion") or {}
        if motion.get("gimmick_id") != "G01":
            continue
        roots = asset["hierarchy"]["motion_roots"]
        if len(roots) != 1:
            raise ValueError(f"G01 {asset['asset_id']}: expected one motion root, got {roots}")
        rows.append({
            "asset_id": asset["asset_id"],
            "motion_root": roots[0],
            "rest_local_blender": motion["rest_pose_local"],
            "bounce_m": motion["bounce_z_range_m"],
            "tilt_deg": motion["tilt_roll_deg_range"],
            "phase_deg": float(motion["phase_deg"]),
            "envelope_radius_m": motion["envelope_radius_m"],
        })
    if len(rows) != 6:
        raise ValueError(f"G01: expected 6 dancing pumpkins, found {len(rows)}")
    for row in rows:
        lo, hi = row["bounce_m"]
        tlo, thi = row["tilt_deg"]
        if lo > 0 or hi <= 0 or abs(tlo + thi) > 1e-9:
            raise ValueError(f"G01 {row['asset_id']}: unsupported ranges {row['bounce_m']} {row['tilt_deg']}")
    return {"gimmick_id": "G01", "district": "A_plaza", "pumpkins": rows, "managed_fields": ["scale"]}


def driven_slots() -> dict[str, dict[str, list[str]]]:
    """地区ごとの、P3 が位置・回転を駆動する Slot の名前と、静的な apply が管理し続ける変換（managedFields）。"""
    a = g01()
    d = g13()
    d15 = g15()
    b5, b6 = g05(), g06()
    c9, c11 = g09(), g11()
    if d15["district"] != d["district"]:
        raise ValueError("G13 and G15 are expected in the same district")
    return {
        a["district"]: {p["motion_root"]: a["managed_fields"] for p in a["pumpkins"]},
        # G13 は TurnRoot の回転だけ、G15 は先頭車・客車の root の位置と回転と、4 つの車輪の回転だけ
        d["district"]: {d["motion_root"]: d["managed_fields"], d15["engine"]: d15["managed_fields"], d15["car"]: d15["managed_fields"],
                        **{w: d15["wheel_managed_fields"] for w in d15["wheels"]}},
        b5["district"]: {**{g["motion_root"]: b5["managed_fields"] for g in b5["ghosts"]},
                         **{h["motion_root"]: b6["managed_fields"] for h in b6["hinges"]}},
        # G09 は攪拌棒の Pivot の回転だけ、G11 は仮モデルの root と CarrierPivot の位置と回転
        c9["district"]: {c9["stir_pivot"]: c9["managed_fields"], c11["rider"]: c11["managed_fields"],
                         c11["carrier"]: c11["managed_fields"]},
    }
