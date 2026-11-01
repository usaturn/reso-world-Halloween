"""W10: P3 の自動ギミックの定義（どの部品を、どの値で動かすか）。

値は地区の持ち主のデータから読み、ここには写さない（写すと食い違う）。
- G13 メリーゴーラウンドの床の回転: layout/areas/D_amusement.json の gimmick_specs.G13_carousel_rotation（W05）
- G01 小カボチャのダンス: assets/manifest/A_plaza.json の各アセットの motion（W02）

座標: Blender の (x, y, z) は Resonite の (x, z, y)。Blender の Z まわり +θ は Resonite の Y まわり -θ
（docs/p2-static-integration.md 14 章。軸を入れ替えると右手系と左手系が入れ替わるので、回る向きの符号が変わる）。
"""

from __future__ import annotations

import json
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
    b5, b6 = g05(), g06()
    return {
        a["district"]: {p["motion_root"]: a["managed_fields"] for p in a["pumpkins"]},
        d["district"]: {d["motion_root"]: d["managed_fields"]},
        b5["district"]: {**{g["motion_root"]: b5["managed_fields"] for g in b5["ghosts"]},
                         **{h["motion_root"]: b6["managed_fields"] for h in b6["hinges"]}},
    }
