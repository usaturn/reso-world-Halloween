"""W08: content/main.json（W08 の root Slot・夜の空・照明・スポーン・撮影用カメラ）を作る。

実行: uv run python modeling/p2_static/build_content.py

座標は Resonite の (x, y 上, z)。Blender の (x, y, z) は Resonite の (x, z, y)（docs/conventions.md §1）。
値の理由は docs/p2-static-integration.md の 3〜5 章。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
OUTPUT = PROJECT / "content" / "main.json"
LAYOUT = PROJECT / "layout" / "world_layout.json"

ROOT_NAME = "HalloweenMagicalCarnival"
OWNERSHIP_KEY = "halloween_magical_carnival"


def blender_to_resonite(p: list[float]) -> list[float]:
    x, y, z = p
    return [x, z, y]


def _qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def _q_axis(axis, angle):
    s = math.sin(angle / 2)
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(angle / 2))


def moon_light_rotation(azimuth_deg: float, elevation_deg: float) -> list[float]:
    """月の方位（北 = +Z から東 = +X へ）と高度から、光が進む向き（Slot の +Z）の回転を作る。"""
    az = math.radians(azimuth_deg)
    el = math.radians(elevation_deg)
    toward_moon = (math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el))
    fwd = tuple(-c for c in toward_moon)
    yaw = math.atan2(fwd[0], fwd[2])
    pitch = -math.asin(fwd[1])
    q = _qmul(_q_axis((0, 1, 0), yaw), _q_axis((1, 0, 0), pitch))
    return [round(c, 6) for c in q]




def point_light(key: str, name: str, blender_pos: list[float], color: list[float], intensity: float, range_m: float) -> dict:
    return {
        "slot": {"key": key, "name": name, "position": blender_to_resonite(blender_pos)},
        "components": [
            {
                "key": f"{key}_light",
                "type": "FrooxEngine.Light",
                "fields": {
                    "LightType": "Point",
                    "Intensity": intensity,
                    "Color": color,
                    "ShadowType": "None",
                    "Range": range_m,
                },
            }
        ],
    }


# 主要ライト（影なし）。位置は Blender の座標で書く（ランドマークと C の Light_Anchor の近く）。
KEY_LIGHTS = [
    # key, name, Blender の位置, 色 (sRGB), 強さ, 範囲 m
    ("light_plaza", "PlazaPumpkinLight", [0.0, 0.0, 9.5], [1.0, 0.62, 0.28, 1.0], 1.6, 20.0),
    ("light_entrance", "SouthEntranceLight", [0.0, -42.5, 5.0], [1.0, 0.7, 0.35, 1.0], 1.4, 12.0),
    ("light_mansion", "MansionPorchLight", [0.7, 34.5, 4.6], [0.62, 0.45, 1.0, 1.0], 1.4, 13.0),
    ("light_candy_arch", "CandyArchLight", [33.0, 0.0, 5.6], [1.0, 0.70, 0.28, 1.0], 1.5, 12.0),
    ("light_carousel", "CarouselLight", [-10.5, -32.0, 7.0], [1.0, 0.55, 0.3, 1.0], 1.5, 13.0),
    ("light_clock_tower", "ClockTowerLight", [-35.0, 0.0, 6.5], [0.55, 1.0, 0.65, 1.0], 1.3, 14.0),
]

# スポーン: W01 の spawn (0, -44, 0) の床（A の入口の舗装の上面 z 0.072）の少し上。
# 半径 2.0 m の円の中に出す（ベンチの内側の縁まで 2.86 m。アバターの幅を見込んで 0.86 m 空ける）。
SPAWN_BLENDER = [0.0, -44.0, 0.08]
SPAWN_RADIUS_M = 2.0

CAMERAS = {
    # name: (position, target, fov)。Resonite の座標。
    "overview_south": ([0, 48, -92], [0, 0, -4], 60),
    "overview_northwest": ([-72, 46, 72], [0, 0, 0], 60),
    "spawn_view": ([0, 1.7, -44], [0, 2.2, 0], 70),
    "entrance_gate": ([0, 3.0, -53], [0, 3.0, -40], 70),
    "area_A_plaza": ([0, 11, -24], [0, 2, 0], 65),
    "area_B_mansion": ([0, 9, 16], [0, 4, 40], 65),
    "area_C_candy": ([16, 9, -14], [36, 2, 0], 65),
    "area_D_amusement": ([14, 11, -52], [-2, 1, -32], 65),
    "area_E_forest": ([-16, 10, 14], [-36, 4, 0], 65),
    "bridge_NE": ([30, 5, 8], [19, 1, 19], 65),
    "bridge_NW": ([-30, 5, 8], [-19, 1, 19], 65),
}


def build() -> dict:
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    moon = layout["sky_moon"]
    sky = {
        "slot": {"key": "night_sky", "name": "NightSky", "position": [0, 0, 0]},
        "components": [
            {
                "key": "sky_material",
                "type": "FrooxEngine.ProceduralSkyMaterial",
                "fields": {
                    "SunQuality": "HighQuality",
                    "SunSize": 0.03,
                    "Sun": "$component:moon_light",
                    "AtmosphereThickness": 0.6,
                    "SkyTint": [0.62, 0.3, 0.6, 1.0],
                    "GroundColor": [0.07, 0.05, 0.11, 1.0],
                    "Exposure": 0.35,
                },
            },
            {"key": "skybox", "type": "FrooxEngine.Skybox", "fields": {"Material": "$component:sky_material"}},
            # 環境光と反射は、ワールドの既定の空と同じ形で夜の空から作る。
            # 反射プローブ（空だけを、空の材質が変わったときに描く）→ ReflectionProbeSH2 → ValueCopy → AmbientLightSH2。
            # SphericalHarmonicsL2 の値は resoloop が書けない（VALUE_TYPE_UNSUPPORTED）ので、参照だけで組む。
            {
                "key": "sky_probe",
                "type": "FrooxEngine.ReflectionProbe",
                "fields": {
                    "ProbeType": "OnChanges",
                    "Importance": 1,
                    "BoxSize": [1000000, 1000000, 1000000],
                    "ChangesSources": ["$component:sky_material"],
                    "Resolution": 64,
                    "HDR": True,
                    "ClearFlags": "Skybox",
                    "SkyboxOnly": True,
                },
            },
            {
                "key": "sky_probe_sh",
                "type": "FrooxEngine.ReflectionProbeSH2",
                "fields": {"Probe": "$component:sky_probe", "Order0Scale": 1.5, "Order1Scale": 0.5, "Order2Scale": 0.5},
            },
            {"key": "ambient", "type": "FrooxEngine.AmbientLightSH2"},
            {
                "key": "ambient_copy",
                "type": "[FrooxEngine]FrooxEngine.ValueCopy<[Elements.Core]Elements.Core.SphericalHarmonicsL2<colorX>>",
                "fields": {"Source": "$member:sky_probe_sh.AmbientLight", "Target": "$member:ambient.AmbientLight"},
            },
        ],
    }
    moon_slot = {
        "slot": {
            "key": "moon",
            "name": "MoonLight",
            "position": [0, 30, 0],
            "rotation": moon_light_rotation(moon["moon_azimuth_deg"], moon["moon_elevation_deg"]),
        },
        "components": [
            {
                "key": "moon_light",
                "type": "FrooxEngine.Light",
                "fields": {
                    "LightType": "Directional",
                    "Intensity": 0.45,
                    "Color": [0.72, 0.74, 1.0, 1.0],
                    "ShadowType": "Soft",
                    "ShadowStrength": 0.8,
                },
            }
        ],
    }
    key_lights = {
        "slot": {"key": "key_lights", "name": "KeyLights", "position": [0, 0, 0]},
        "children": [point_light(*args) for args in KEY_LIGHTS],
    }
    spawn = {
        "slot": {
            "key": "spawn",
            "name": "SouthEntranceSpawn",
            "position": blender_to_resonite(SPAWN_BLENDER),
            "rotation": [0, 0, 0, 1],
        },
        "components": [
            {"key": "spawn_points", "type": "FrooxEngine.CirclePointGenerator", "fields": {"Radius": SPAWN_RADIUS_M}},
            {
                "key": "spawn_area",
                "type": "FrooxEngine.CommonSpawnArea",
                "fields": {"SpawnPointGenerator": "$component:spawn_points", "OrientUser": True},
            },
        ],
    }
    cameras = {}
    for i, (name, (pos, target, fov)) in enumerate(CAMERAS.items()):
        cam = {"position": pos, "target": target, "fieldOfView": fov, "width": 1600, "height": 900}
        if i == 0:
            cam["representative"] = True
        cameras[name] = cam
    return {
        "schemaVersion": "1",
        "ownership": {"key": OWNERSHIP_KEY},
        "slot": {
            "key": "root",
            "name": ROOT_NAME,
            "parent": "Root",
            "position": [0, 0, 0],
            "rotation": [0, 0, 0, 1],
            "scale": [1, 1, 1],
        },
        "components": [{"key": "root_object", "type": "FrooxEngine.ObjectRoot"}],
        "children": [
            {"slot": {"key": "environment", "name": "Environment", "position": [0, 0, 0]}, "children": [sky, moon_slot, key_lights]},
            spawn,
        ],
        "cameras": cameras,
        "tests": [
            {
                "name": "w08-root-structure",
                "assertions": [
                    {"target": "$slot:root", "exists": True},
                    {"target": "$slot:spawn", "exists": True},
                    {"target": "$component:spawn_area", "exists": True},
                    {"target": "$component:skybox", "exists": True},
                    {"target": "$component:moon_light", "exists": True},
                ],
            },
            # 夜の空と環境光を、ワールドで使う空・環境光にする（Skybox / AmbientLightSH2 の SetActive）。
            # `resoloop test content/main.json --state <p2_root.json> --probe --yes` のときだけ実行される。
            # 既定の空（Root/Skybox）は消さずに残るので、戻すときは既定の側の SetActive を呼ぶ。
            {"name": "w08-activate-night-sky", "assertions": [{"target": "$component:skybox", "exists": True}], "probe": {"kind": "method", "target": "$component:skybox", "method": "SetActive", "safe": True}},
            {"name": "w08-activate-night-ambient", "assertions": [{"target": "$component:ambient", "exists": True}], "probe": {"kind": "method", "target": "$component:ambient", "method": "SetActive", "safe": True}},
        ],
    }


def main() -> None:
    OUTPUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
