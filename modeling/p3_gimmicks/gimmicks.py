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
    return {
        a["district"]: {p["motion_root"]: a["managed_fields"] for p in a["pumpkins"]},
        d["district"]: {d["motion_root"]: d["managed_fields"]},
    }
