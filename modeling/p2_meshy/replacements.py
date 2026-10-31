"""W09R: 仮モデルを Meshy の仕上げた素材に差し替える設定と、地区の宣言の中の仮モデルの描画を止める処理。

方式（docs/p2-meshy-replacement.md 2 章）
- 仕上げた素材は、地区のバンドルとは別の宣言（exports/p2_meshy/<M>-<UTC>/p2m.apply.json、state も別）で、
  仮モデルの見た目の Slot（visual_root）の子に置く。export_meshy.py が作る
- 地区の宣言（exports/p2_static/<key>-<UTC>/p2.apply.json）では、差し替えた仮モデルの MeshRenderer を
  Enabled = false にするだけで、Slot・メッシュ・当たり判定（<visual_root>_FixedCollision）・取付位置は残す。
  modeling/p2_static/export_p2.py が colliders.compose の後に hide_placeholders を呼ぶので、地区を export し直しても
  仮モデルが再び表示されることはない
- 後続の子は REPLACEMENTS に行を足す（地区の宣言を export し直し、diff の対象が足した仮モデルの描画だけかを確かめる）
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
}


def resonite_quat_from_blender_z(deg: float) -> list[float]:
    """Blender の Z 軸まわり +deg を Resonite の Y 軸まわり -deg の四元数 (x, y, z, w) にする（docs/conventions.md §1）。"""
    half = math.radians(-deg) / 2.0
    q = [0.0, math.sin(half), 0.0, math.cos(half)]
    return [0.0 if abs(c) < 1e-12 else round(c, 12) for c in q]


def for_district(key: str) -> dict[str, dict]:
    return {m: r for m, r in REPLACEMENTS.items() if r["district"] == key}


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

    対象は REPLACEMENTS の hide に書いた Slot だけで、その Slot が visual_root（またはその子孫）でなければ止める。
    見つからない・MeshRenderer が無いときも止める（黙って何もしないと、仮モデルが仕上げた素材と重なって表示される）。
    """
    rows: list[dict] = []
    for meshy_id, rep in for_district(key).items():
        wanted = set(rep["hide"])
        hits: dict[str, tuple[list[str], dict]] = {}
        _find_children_named(doc, [doc["slot"]["name"]], wanted, hits)
        missing = wanted - set(hits)
        if missing:
            raise ValueError(f"{meshy_id}: Slot not found in the {key} declaration: {sorted(missing)}")
        for name in rep["hide"]:
            chain, node = hits[name]
            if rep["visual_root"] not in chain:
                raise ValueError(f"{meshy_id}: {name} is outside the replacement range {rep['visual_root']}")
            renderers = [c for c in node.get("components", []) if c.get("type") == "FrooxEngine.MeshRenderer"]
            if not renderers:
                raise ValueError(f"{meshy_id}: {name} has no MeshRenderer")
            for comp in renderers:
                comp.setdefault("fields", {})["Enabled"] = False
                rows.append({"meshy_id": meshy_id, "slot": "/".join(chain), "component": comp["key"], "Enabled": False})
    return rows


def hide_in_file(p2_path: Path, key: str) -> list[dict]:
    """p2.apply.json を読み、hide_placeholders を適用して書き戻す（対象が無いキーではファイルを変えない）。"""
    if not for_district(key):
        return []
    doc = json.loads(p2_path.read_text(encoding="utf-8"))
    rows = hide_placeholders(doc, key)
    p2_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rows
