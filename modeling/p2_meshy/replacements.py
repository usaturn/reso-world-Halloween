"""W09R: 仮モデルを Meshy の仕上げた素材に差し替える設定と、地区の宣言の中の仮モデルの描画を止める処理。

方式（docs/p2-meshy-replacement.md 2 章）
- 仕上げた素材は、地区のバンドルとは別の宣言（exports/p2_meshy/<M>-<UTC>/p2m.apply.json、state も別）で、
  仮モデルの見た目の Slot（visual_root）の子に置く。export_meshy.py が作る
- 地区の宣言（exports/p2_static/<key>-<UTC>/p2.apply.json）では、差し替えた仮モデルの MeshRenderer を
  Enabled = false にするだけで、Slot・メッシュ・当たり判定（<visual_root>_FixedCollision）・取付位置は残す。
  modeling/p2_static/export_p2.py が colliders.compose の後に hide_placeholders を呼ぶので、地区を export し直しても
  仮モデルが再び表示されることはない
- 後続の子は REPLACEMENTS に行を足す（地区の宣言を export し直し、diff の対象が足した仮モデルの描画だけかを確かめる）
- 可動部品を持つ素材（W09R-A の M01 の門扉。docs/p2-meshy-replacement.md 13 章）: 行の moving_parts に書いた素材の子は、
  素材の宣言とは別の宣言で、仮モデルの可動部品の Slot（motion_root）の下に置く（1 つの宣言は 1 つの親の下にしか置けない）。
  地区の宣言では、その motion_root を素材の蝶番の位置・開いた角度に置き直す（repose_motion_roots。Slot は作り直さない）
- 当たり判定を素材のメッシュで作る素材（W09R-B の M03。collision が "finished"。docs/p2-meshy-replacement.md 14 章）:
  素材の宣言で、素材のメッシュの Slot に MeshCollider を付け（export_meshy.py）、地区の宣言では仮モデルの形の
  <visual_root>_FixedCollision の MeshCollider を Enabled = false にする（disable_fixed_collisions。Slot は消さない）
"""

from __future__ import annotations

import json
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
P2_ROOT = "Root/HalloweenMagicalCarnival"

# 差し替えの設定。キーは Meshy の ID（received.json の素材）。
# - district / placeholder / visual_root: handoff/W08.md 3.1 の仮モデルの Slot（visual_root が差し替えの範囲）
# - hide: 地区の宣言で MeshRenderer を Enabled = false にする Slot の名前（visual_root より下の物だけ）
# - blend / asset_id: 仕上げた素材（modeling/<M>/build.py が作る .blend と、その中のオブジェクト）
# - rotation_z_deg / position_local: 仕上げた素材の root を visual_root のローカルでどう置くか（Blender の軸）。
#   回転 = received.json の placement_hint.rotation_z_deg - 仮モデルのアセットの root の世界の回転
REPLACEMENTS: dict[str, dict] = {
    # W09R-A（#47）: A 中央広場の入口
    "M01": {
        "district": "A_plaza",
        "placeholder": "APL_EntranceGateProxy_001",
        "visual_root": "APL_EntranceGateProxy_001_Arch",
        "visual_root_path": f"{P2_ROOT}/A_plaza/APL_EntranceGateProxy_001/APL_EntranceGateProxy_001_Arch",
        # 仮モデルのアーチ・門扉 2 枚と、アーチの子の取付位置の目印 3 つ（発光の部品で M01 の柱と看板の前に出るので、M02 と同じく
        # 描画だけ止める。Slot と位置は残す）
        "hide": [
            "APL_EntranceGateProxy_001_Arch",
            "APL_EntranceGateProxy_001_BannerAttach",
            "APL_EntranceGateProxy_001_LanternAttachLeft",
            "APL_EntranceGateProxy_001_LanternAttachRight",
            "APL_EntranceGateProxy_001_DoorLeft",
            "APL_EntranceGateProxy_001_DoorRight",
        ],
        "blend": "blender/M01/M01.blend",
        "asset_id": "M01_EntranceGate_001",
        "rotation_z_deg": 180.0,  # placement_hint 180 - 仮モデルの root 0（看板の正面を南のスポーンへ）
        "position_local": [0.0, 0.0, 0.0],  # 接地面の中央 = アーチの原点（入口の地面）
        # 門扉 2 枚（M01 の子の motion_root）を、仮モデルの門扉の Slot の下に別の宣言で置く。蝶番と角度は M01 のアセット一覧の
        # leaves（pivot_local・closed_deg・placed_deg）から求め、仮モデルの門扉の Slot をそこへ置き直す（2026-11-01 の利用者の
        # 決定: Slot を M01 の蝶番へ動かし ±88° → ±90° にする。P3 はこの Slot を閉 0°〜開 ±90° で回す）。名前の左右は M01 の
        # ローカル（正面 +Y）で、180° で置くので世界では M01 の Left が仮モデルの DoorLeft（x < 0）に当たる
        "moving_parts": {
            "M01_GateLeafLeft_001": {"motion_root": "APL_EntranceGateProxy_001_DoorLeft", "document": "DoorLeft"},
            "M01_GateLeafRight_001": {"motion_root": "APL_EntranceGateProxy_001_DoorRight", "document": "DoorRight"},
        },
        # 撮影用のカメラ（Resonite の Root の座標）。ゲートの原点は (0, 0, -40)、高さ 7.74 m、幅 11 m、正面（看板）は南（-Z）、
        # 門扉は北（広場の側）へ開く
        "cameras": {
            "m01_front": ([0, 3.6, -47], [0, 3.8, -40], 70),  # 南の柵（z ≈ -47.5）の内側から
            "m01_front_close": ([0, 1.7, -45], [0, 3.0, -40], 70),  # スポーンの近くの目の高さから
            "m01_oblique_sw": ([-10, 6.5, -52], [0, 3.4, -40], 55),
            "m01_back": ([0, 4.5, -25], [0, 3.4, -40], 55),
            "m01_leaves_inside": ([0, 1.7, -34.5], [0, 1.9, -40], 70),  # 広場の側から開いた門扉を
            "m01_hinge_left": ([-0.6, 1.6, -38.2], [-2.2, 1.6, -40], 65),  # 通路から左の蝶番の付近を
            "area_A_entrance": ([0, 9, -62], [0, 2, -36], 60),
            "overview_south": ([0, 48, -92], [0, 0, -4], 60),  # W08 と同じ
        },
    },
    "M02": {
        "district": "A_plaza",
        "placeholder": "APL_GiantJackProxy_001",
        "visual_root": "APL_GiantJackProxy_001_Body",
        "visual_root_path": f"{P2_ROOT}/A_plaza/APL_GiantJackProxy_001/APL_GiantJackProxy_001_Body",
        # 仮モデルの本体と、その子の取付位置の目印 3 つ（M02 の顔の目の間と鼻の上に出るので描画を止める。Slot と位置は残す）
        "hide": [
            "APL_GiantJackProxy_001_Body",
            "APL_GiantJackProxy_001_EyeLightAttach",
            "APL_GiantJackProxy_001_MouthReactionAttach",
            "APL_GiantJackProxy_001_InteriorLightAttach",
        ],
        "blend": "blender/M02/M02.blend",
        "asset_id": "M02_GiantPumpkin_001",
        "rotation_z_deg": 180.0,  # placement_hint 180 - 仮モデルの root 0（顔を南へ）
        "position_local": [0.0, 0.0, 0.0],  # 底の中央 = visual_root の原点（噴水の器の上面）
        # 空洞の中の点光源（2026-10-31 の利用者の要望: 近くの下から見ても目が光って見えるように）。position_local は
        # 素材のローカル（Blender の軸、+Y が顔）。内側の壁は空洞の中心を向いているので、中から照らすと目・口の奥が光る。
        # 影なし（W08 の主要ライトと同じ）。P3 の I03（目の発光の反応）は、この Light の Intensity を動かせる
        "lights": [
            {
                "name": "M02_InteriorGlow",  # Slot のキーは名前から作る（export_meshy.slot_key）
                "position_local": [0.0, 0.8, 1.6],
                "color": [1.0, 0.55, 0.15, 1.0],
                "intensity": 3.0,
                "range": 5.0,
            },
        ],
        # 撮影用のカメラ（Resonite の Root の座標。resoloop capture <p2m.apply.json> --camera <名前>）。
        # M02 の底の中央は (0, 1.6, 0)、高さ 6 m、顔は南（-Z）
        "cameras": {
            "m02_front": ([0, 4.6, -15], [0, 4.4, 0], 50),
            "m02_front_close": ([0, 4.2, -8.5], [0, 4.2, 0], 60),
            "m02_oblique_se": ([10, 7, -10], [0, 4.2, 0], 55),
            "m02_back": ([0, 6, 13], [0, 4.2, 0], 55),
            "m02_eyes_low": ([0, 1.9, -6.5], [0, 3.8, -2.7], 55),  # 器の縁の近くの下から（利用者の要望の確認）
            "m02_eyes_low_side": ([3.0, 1.9, -5.5], [0.3, 3.6, -2.6], 55),
            "area_A_plaza": ([0, 11, -24], [0, 2, 0], 65),  # W08 と同じ
            "overview_south": ([0, 48, -92], [0, 0, -4], 60),  # W08 と同じ
        },
    },
    # W09R-B（#48）: B 北・おばけ屋敷
    "M03": {
        "district": "B_mansion",
        "placeholder": "BMN_MansionPlaceholder_001",
        # 仮モデルはアセットの root がそのまま見た目（W03 の hierarchy.visual_roots）。当たり判定は B の root の下の兄弟
        "visual_root": "BMN_MansionPlaceholder_001",
        "visual_root_path": f"{P2_ROOT}/B_mansion/BMN_MansionPlaceholder_001",
        "hide": ["BMN_MansionPlaceholder_001"],
        "blend": "blender/M03/M03.blend",
        "asset_id": "M03_HauntedMansion_001",
        "rotation_z_deg": 0.0,  # placement_hint 180 - 仮モデルの root 180（ポーチを南の中庭へ）
        "position_local": [0.0, 0.0, 0.0],  # 底面の中央 = 仮モデルの原点（台地の上面 z 1.5）
        # 当たり判定は M03 のメッシュ（2026-11-01 の利用者の決定）。仮モデルの形は M03 と大きく違う（中央のアーチの通路に
        # 見えない柱が 0.33 m はみ出す、ポーチの床が 9.1 cm 低い、正面の張り出しの前に高さ 0.28 m の見えない台座）。
        # 仮モデルの FixedCollision の MeshCollider は Enabled = false にし、Slot は残す
        "collision": "finished",
        # 入口（verify_live.py の検査）: W03 の扉の蝶番の Slot を、M03 の開口の蝶番の線（review/M03/checks.json の
        # door_opening.hinges）に、玄関ホールの原点を開口の中心の床から hall_depth_m 奥に置いたか。名前の左右は W03 の世界
        # （Left が x の小さい側）で、M03 のローカル（正面 +Y）の左右とは逆
        "entrance": {
            "hinges": {
                "BMN_MansionDoubleDoor_001_HingeLeft": "left_viewed_from_front_plus_x",
                "BMN_MansionDoubleDoor_001_HingeRight": "right_viewed_from_front_minus_x",
            },
            "hall": "BMN_EntranceHall_001",
            "hall_depth_m": 1.85,  # W03 の玄関ホールの原点は扉の面の 1.85 m 奥（modeling/B_mansion/build.py の build_entrance_hall）
        },
        # M03 の底の中央は (0, 1.5, 41.5)、幅 15 m・奥行き 10.2 m・高さ 10.6 m、正面（ポーチ）は南（-Z）。開口の中心は
        # (0.7075, 1.87, 39.95)。南の門は z 21.5、中庭の枯れ木は x ±7.2・z 26.5
        "cameras": {
            "m03_front": ([0, 5.5, 25.5], [0, 5.2, 41.5], 60),
            "m03_front_close": ([0.7, 2.6, 33.0], [0.7, 3.2, 40], 60),
            "m03_entrance": ([0.7, 3.4, 36.6], [0.7, 3.1, 40], 70),  # ポーチの段の前から開口と扉の枠
            "m03_door_edge_left": ([-1.0, 2.8, 38.4], [0.2, 3.2, 40], 60),  # 開口の西の縁（枠と壁の切り口）
            "m03_door_edge_right": ([2.4, 2.8, 38.4], [1.2, 3.2, 40], 60),
            "m03_porch_steps": ([3.5, 2.6, 34.2], [0.7, 1.7, 37.3], 60),  # 中庭の石畳から M03 の段への上がり口
            "m03_oblique_se": ([11, 9, 28], [0, 4.5, 41.5], 55),
            "m03_oblique_sw": ([-11, 9, 28], [0, 4.5, 41.5], 55),
            "m03_back": ([0, 9, 56], [0, 4.5, 41.5], 55),
            "area_B_mansion": ([0, 9, 16], [0, 4, 40], 65),  # W08 と同じ
            "overview_south": ([0, 48, -92], [0, 0, -4], 60),  # W08 と同じ
        },
    },
    # W09R-C（#46）: C 東・キャンディストリート
    "M04": {
        "district": "C_candy",
        "placeholder": "CCD_M04_CandyWorkshopProxy_001",
        # 仮モデルはアセットの root がそのまま見た目（W04 の hierarchy.visual_roots）。当たり判定は C の root の下の兄弟
        "visual_root": "CCD_M04_CandyWorkshopProxy_001",
        "visual_root_path": f"{P2_ROOT}/C_candy/CCD_M04_CandyWorkshopProxy_001",
        "hide": ["CCD_M04_CandyWorkshopProxy_001"],
        "blend": "blender/M04/M04.blend",
        "asset_id": "M04_WitchCandyWorkshop_001",
        "rotation_z_deg": 0.0,  # placement_hint 90 - 仮モデルの root 90（正面の扉を西の広場へ）
        "position_local": [0.0, 0.0, 0.0],  # 土台の下面の中央 = 仮モデルの原点（地面）
        "emissive": True,  # 窓の発光の画像（PBS_Metallic の EmissiveMap。handoff/W09-M04.md 8 章）
        # M04 の底の中央は (38, 0, 0)、高さ 7.63 m、正面（扉）は西（-X）。右側面（Blender のローカル +X）は北（+Z）
        "cameras": {
            "m04_front": ([24, 4.2, 0], [38, 3.6, 0], 55),
            "m04_front_close": ([30.5, 2.4, 0], [38, 3.0, 0], 60),
            "m04_oblique_nw": ([27, 8, 9], [38, 3.4, 0], 55),
            "m04_side_north": ([38, 4, 12.5], [38, 3.6, 0], 55),
            "m04_back": ([51, 6, -6], [38, 3.4, 0], 55),
            "area_C_candy": ([16, 9, -14], [36, 2, 0], 65),  # W08 と同じ
        },
    },
    "M08": {
        "district": "C_candy",
        "placeholder": "CCD_M08_FlyingWitchProxy_001",
        "visual_root": "CCD_M08_FlyingWitchProxy_001",
        "visual_root_path": f"{P2_ROOT}/C_candy/CCD_M08_FlyingWitchProxy_001",
        "hide": ["CCD_M08_FlyingWitchProxy_001"],
        "blend": "blender/M08/M08.blend",
        "asset_id": "M08_FlyingWitch_001",
        # placement_hint は null（経路の上）。仮モデルは回転 0 で正面 +Y（巡回の点 0 の接線、W07 の front_world north(+Y)）
        "rotation_z_deg": 0.0,
        "position_local": [0.0, 0.0, 0.0],  # 飛行の動作中心 = 仮モデルの原点（巡回の点 0）
        "collision": False,  # 空を飛ぶ（P3 の G11）。歩行の当たり判定は要らない（handoff/W09-M08.md 8 章）
        # 魔女を照らす点光源 2 つ（2026-11-01 の利用者の確認「暗くて見えにくい」「（前の光源 1 つでは）まだ暗い」への対応）。
        # position_local は素材のローカル（Blender の軸、+Y がほうきの先、原点は飛行の動作中心）。前の光源は顔と体の前を、
        # 下の光源は地上から見上げたときに見える下側（ブーツ・ほうき・服の裾・帽子のつばの裏）を照らす。M08 の Slot の子なので、
        # P3 の G11 で一緒に動く。影なし。範囲は M04 の屋根（光源から 3 m 前後）をほとんど照らさない大きさ
        "lights": [
            {
                "name": "M08_FrontGlow",
                "position_local": [0.0, 1.3, 0.3],
                "color": [1.0, 0.8, 0.6, 1.0],
                "intensity": 3.0,
                "range": 3.0,
            },
            {
                "name": "M08_UnderGlow",
                "position_local": [0.0, 0.2, -1.1],
                "color": [1.0, 0.8, 0.6, 1.0],
                "intensity": 3.0,
                "range": 2.8,
            },
        ],
        # M08 の原点は (43.2, 10.2, 0)、上に 1.89 m・下に 0.61 m、正面（ほうきの先）は北（+Z）
        "cameras": {
            "m08_side_west": ([37.5, 10.8, 0], [43.2, 10.6, 0], 40),
            "m08_front": ([43.2, 10.9, 6.5], [43.2, 10.6, 0], 40),
            "m08_oblique_back": ([47.5, 12, -4.5], [43.2, 10.5, 0], 45),
            "m08_from_street": ([40, 1.6, -14], [43.2, 10.4, 0], 50),  # 地上（M04 の南の通り）から見上げる。M04 の屋根に遮られない位置
        },
    },
}


def resonite_quat_from_blender_z(deg: float) -> list[float]:
    """Blender の Z 軸まわり +deg を Resonite の Y 軸まわり -deg の四元数 (x, y, z, w) にする（docs/conventions.md §1）。"""
    half = math.radians(-deg) / 2.0
    q = [0.0, math.sin(half), 0.0, math.cos(half)]
    return [0.0 if abs(c) < 1e-12 else round(c, 12) for c in q]


def rz(deg: float, v) -> list[float]:
    """Blender の Z 軸まわりに deg 回した点。"""
    a = math.radians(deg)
    return [v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a), v[2]]


def b2r(p) -> list[float]:
    """Blender (x, y, z) -> Resonite (x, z, y)。"""
    return [float(p[0]), float(p[2]), float(p[1])]


def for_district(key: str) -> dict[str, dict]:
    return {m: r for m, r in REPLACEMENTS.items() if r["district"] == key}


def moving_part_poses(meshy_id: str, rep: dict) -> dict[str, dict]:
    """moving_parts の部品ごとに、仮モデルの motion_root の置き直し方と、その下に置く素材の宣言の root の回転を求める。

    値は仕上げた素材のアセット一覧（assets/manifest/<M>.json の leaves）から求め、実測から求めない。座標は visual_root と
    motion_root の共通の親（仮モデルのアセットの root）のローカル（visual_root がそこで回転・移動なしであることは
    repose_motion_roots が確かめる）。
    - motion_root の位置 = position_local + Z(rotation_z_deg)·pivot_local（素材の蝶番）
    - motion_root の回転（Blender の Z 軸まわり）= placed_deg - closed_deg（閉 0°、開いた形 = 基準姿勢）
    - 素材の宣言の root の回転 = rotation_z_deg + closed_deg（root の下の部品は回転・移動なしの閉じた形）
    これで部品の世界の回転は rotation_z_deg + placed_deg（素材のアセット一覧の開いた形）になる。
    """
    parts = rep.get("moving_parts") or {}
    if not parts:
        return {}
    leaves = json.loads((PROJECT_ROOT / f"assets/manifest/{meshy_id}.json").read_text(encoding="utf-8"))["assets"][0]["leaves"]
    out: dict[str, dict] = {}
    for part_id, part in parts.items():
        leaf = leaves[part_id]
        if leaf.get("axis") != "+Z":
            raise ValueError(f"{meshy_id}/{part_id}: hinge axis {leaf.get('axis')!r} is not +Z")
        hinge = [rep["position_local"][i] + rz(rep["rotation_z_deg"], leaf["pivot_local"])[i] for i in range(3)]
        open_deg = float(leaf["placed_deg"]) - float(leaf["closed_deg"])
        root_deg = float(rep["rotation_z_deg"]) + float(leaf["closed_deg"])
        out[part_id] = {
            "motion_root": part["motion_root"],
            "document": part["document"],
            "pivot_local": leaf["pivot_local"],
            "hinge_blender": [round(v, 6) for v in hinge],
            "motion_root_position": [round(v, 6) for v in b2r(hinge)],
            "motion_root_rotation_z_deg": open_deg,
            "motion_root_rotation": resonite_quat_from_blender_z(open_deg),
            "closed_rotation_z_deg": 0.0,
            "part_root_rotation_z_deg": root_deg,
            "part_root_rotation": resonite_quat_from_blender_z(root_deg),
        }
    return out


def _find_children_named(node: dict, chain: list[str], wanted: set[str], hits: dict[str, tuple[list[str], dict]]) -> None:
    for child in node.get("children", []):
        name = child["slot"]["name"]
        here = chain + [name]
        if name in wanted:
            if name in hits:
                raise ValueError(f"{name}: appears more than once in the declaration")
            hits[name] = (here, child)
        _find_children_named(child, here, wanted, hits)


def hide_placeholders(doc: dict, key: str) -> list[dict]:
    """地区の宣言 doc の中で、差し替えた仮モデルの MeshRenderer を Enabled = false にする（doc をその場で変える）。

    対象は REPLACEMENTS の hide に書いた Slot だけで、その Slot が visual_root（またはその子孫）か、moving_parts の
    motion_root（またはその子孫）でなければ止める。見つからない・MeshRenderer が無いときも止める（黙って何もしないと、
    仮モデルが仕上げた素材と重なって表示される）。
    """
    rows: list[dict] = []
    for meshy_id, rep in for_district(key).items():
        wanted = set(rep["hide"])
        hits: dict[str, tuple[list[str], dict]] = {}
        _find_children_named(doc, [doc["slot"]["name"]], wanted, hits)
        missing = wanted - set(hits)
        if missing:
            raise ValueError(f"{meshy_id}: Slot not found in the {key} declaration: {sorted(missing)}")
        ranges = [rep["visual_root"], *(p["motion_root"] for p in (rep.get("moving_parts") or {}).values())]
        for name in rep["hide"]:
            chain, node = hits[name]
            if not any(r in chain for r in ranges):
                raise ValueError(f"{meshy_id}: {name} is outside the replacement range {ranges}")
            renderers = [c for c in node.get("components", []) if c.get("type") == "FrooxEngine.MeshRenderer"]
            if not renderers:
                raise ValueError(f"{meshy_id}: {name} has no MeshRenderer")
            for comp in renderers:
                comp.setdefault("fields", {})["Enabled"] = False
                rows.append({"meshy_id": meshy_id, "slot": "/".join(chain), "component": comp["key"], "Enabled": False})
    return rows


def _is_identity(slot: dict) -> bool:
    pos = slot.get("position") or [0.0, 0.0, 0.0]
    rot = slot.get("rotation") or [0.0, 0.0, 0.0, 1.0]
    scl = slot.get("scale") or [1.0, 1.0, 1.0]
    return all(abs(a - b) < 1e-6 for a, b in zip([*pos, *rot, *scl], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1]))


def repose_motion_roots(doc: dict, key: str) -> list[dict]:
    """地区の宣言 doc の中で、moving_parts の motion_root を素材の蝶番の位置・開いた角度に置き直す（doc をその場で変える）。

    Slot（名前・キー・親・Component）はそのままで、位置と回転だけを変える。motion_root と visual_root が同じ親の子で、
    visual_root がその親のローカルで回転・移動・拡縮なしでなければ止める（moving_part_poses の座標の前提。崩れたまま置き直すと、
    門扉が素材のアーチからずれた所に開いた形で置かれ、エラーにならない）。
    """
    rows: list[dict] = []
    for meshy_id, rep in for_district(key).items():
        poses = moving_part_poses(meshy_id, rep)
        if not poses:
            continue
        names = {rep["visual_root"], *(p["motion_root"] for p in poses.values())}
        hits: dict[str, tuple[list[str], dict]] = {}
        _find_children_named(doc, [doc["slot"]["name"]], names, hits)
        missing = names - set(hits)
        if missing:
            raise ValueError(f"{meshy_id}: Slot not found in the {key} declaration: {sorted(missing)}")
        vr_chain, vr_node = hits[rep["visual_root"]]
        if not _is_identity(vr_node["slot"]):
            raise ValueError(f"{meshy_id}: {rep['visual_root']} is not at the identity of its parent")
        for part_id, pose in poses.items():
            chain, node = hits[pose["motion_root"]]
            if chain[:-1] != vr_chain[:-1]:
                raise ValueError(f"{meshy_id}: {pose['motion_root']} and {rep['visual_root']} have different parents")
            slot = node["slot"]
            before = {"position": slot.get("position"), "rotation": slot.get("rotation")}
            slot["position"] = pose["motion_root_position"]
            slot["rotation"] = pose["motion_root_rotation"]
            rows.append({"meshy_id": meshy_id, "slot": "/".join(chain), "part": part_id, "repose": {
                "from": before, "to": {"position": slot["position"], "rotation": slot["rotation"]},
                "rotation_z_deg": pose["motion_root_rotation_z_deg"], "closed_rotation_z_deg": pose["closed_rotation_z_deg"]}})
    return rows


def disable_fixed_collisions(doc: dict, key: str) -> list[dict]:
    """collision が "finished" の素材について、地区の宣言 doc の中の <visual_root>_FixedCollision の MeshCollider を
    Enabled = false にする（doc をその場で変える。Slot と StaticMesh は残す）。

    FixedCollision は visual_root と同じ親の兄弟（W08 の colliders.compose）。見つからない・MeshCollider が無いときは止める
    （黙って何もしないと、仮モデルの形の見えない当たり判定と素材の当たり判定が重なって残る）。
    """
    rows: list[dict] = []
    for meshy_id, rep in for_district(key).items():
        if rep.get("collision") != "finished":
            continue
        fixed_name = f"{rep['visual_root']}_FixedCollision"
        names = {rep["visual_root"], fixed_name}
        hits: dict[str, tuple[list[str], dict]] = {}
        _find_children_named(doc, [doc["slot"]["name"]], names, hits)
        missing = names - set(hits)
        if missing:
            raise ValueError(f"{meshy_id}: Slot not found in the {key} declaration: {sorted(missing)}")
        chain, node = hits[fixed_name]
        if chain[:-1] != hits[rep["visual_root"]][0][:-1]:
            raise ValueError(f"{meshy_id}: {fixed_name} is not a sibling of {rep['visual_root']}")
        colliders = [c for c in node.get("components", []) if c.get("type") == "FrooxEngine.MeshCollider"]
        if not colliders:
            raise ValueError(f"{meshy_id}: {fixed_name} has no MeshCollider")
        for comp in colliders:
            comp.setdefault("fields", {})["Enabled"] = False
            rows.append({"meshy_id": meshy_id, "slot": "/".join(chain), "component": comp["key"], "Enabled": False,
                         "reason": "collision is the finished asset's own mesh"})
    return rows


def hide_in_file(p2_path: Path, key: str) -> list[dict]:
    """p2.apply.json を読み、hide_placeholders・repose_motion_roots・disable_fixed_collisions を適用して書き戻す
    （対象が無いキーではファイルを変えない）。"""
    if not for_district(key):
        return []
    doc = json.loads(p2_path.read_text(encoding="utf-8"))
    rows = hide_placeholders(doc, key) + repose_motion_roots(doc, key) + disable_fixed_collisions(doc, key)
    p2_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rows
