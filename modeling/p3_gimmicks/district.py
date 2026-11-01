"""W10: 地区の宣言（exports/p2_static/<key>-<UTC>/p2.apply.json）に、P3 が動かす可動部品の設定を足す。

modeling/p2_static/export_p2.py から、当たり判定（colliders.compose）と Meshy の差し替え（replacements.hide_in_file）の後に呼ぶ。

- P3 が位置・回転を駆動する Slot（gimmicks.driven_slots）に managedFields を付け、静的な apply が駆動された値を
  基準姿勢へ戻さないようにする（docs/p2-static-integration.md 11 章の 2 つ目の案。docs/p3-gimmicks.md 2 章）。
  基準姿勢（宣言の position・rotation）は、Slot を作るときの値として宣言に残す
- G13: TurnRoot に FrooxEngine.Spinner を足し、TurnRoot の Rotation を駆動する。_offset は宣言の基準姿勢の回転、
  _speed は initialFields（apply し直しても、Resonite の中で変えた速さを戻さない）
- G01: 各 Body に ValueMultiDriver<float3>（Position を駆動）と ValueMultiDriver<floatQ>（Rotation を駆動）を足す。
  それぞれの Value を ProtoFlux（flux/P3PlazaDance.pg）が drive する。Flux のマニフェストの drive は Component の
  メンバーしか結べない（$slot-member: は FLUX_BINDING_TARGET_INVALID）ための中継。Value の初期値は基準姿勢で、
  モジュールが無いときは基準姿勢に止まる
"""

from __future__ import annotations

import json
from pathlib import Path

from modeling.p3_gimmicks import gimmicks

SPINNER_TYPE = "FrooxEngine.Spinner"
RELAY_TYPES = {"Position": "[FrooxEngine]FrooxEngine.ValueMultiDriver<float3>",
               "Rotation": "[FrooxEngine]FrooxEngine.ValueMultiDriver<floatQ>"}


def relay_key(slot_key: str, member: str) -> str:
    """G01 の中継（ValueMultiDriver）の Component のキー。flux のマニフェストの drive の先。"""
    return f"p3_g01_{member.lower()}_{slot_key}"


def _find_named(node: dict, chain: list[str], wanted: set[str], hits: dict[str, list[tuple[list[str], dict]]]) -> None:
    for child in node.get("children", []):
        name = child["slot"]["name"]
        child_chain = chain + [name]
        if name in wanted:
            hits.setdefault(name, []).append((child_chain, child))
        _find_named(child, child_chain, wanted, hits)


def add_drivers(doc: dict, key: str) -> list[dict]:
    """doc（地区の宣言）をその場で変え、変えた所の一覧を返す。対象の Slot が無い・同じ名前が複数あるときは止める。"""
    targets = gimmicks.driven_slots().get(key, {})
    if not targets:
        return []
    hits: dict[str, list[tuple[list[str], dict]]] = {}
    _find_named(doc, [doc["slot"]["name"]], set(targets), hits)
    rows: list[dict] = []
    for name, managed in targets.items():
        found = hits.get(name, [])
        if len(found) != 1:
            raise ValueError(f"{key}: expected one Slot named {name} in the declaration, found {len(found)}")
        chain, node = found[0]
        slot = node["slot"]
        slot["managedFields"] = list(managed)
        row = {"slot": "/".join(chain), "managedFields": list(managed),
               "rest": {"position": slot.get("position"), "rotation": slot.get("rotation")}}
        g13 = gimmicks.g13()
        comps = node.setdefault("components", [])
        if key == gimmicks.g01()["district"]:
            rest = {"Position": slot.get("position") or [0.0, 0.0, 0.0], "Rotation": slot.get("rotation") or [0.0, 0.0, 0.0, 1.0]}
            row["relays"] = []
            for member, type_name in RELAY_TYPES.items():
                comp_key = relay_key(slot["key"], member)
                if any(c.get("key") == comp_key for c in comps):
                    raise ValueError(f"{key}: {comp_key} is already declared")
                comps.append({
                    "key": comp_key,
                    "type": type_name,
                    "fields": {"Drives": [f"$slot-member:{slot['key']}.{member}"]},
                    # Value は ProtoFlux が drive する（宣言の fields に書くと apply が駆動と競う）
                    "initialFields": {"Value": rest[member]},
                })
                row["relays"].append(comp_key)
        if key == g13["district"] and name == g13["motion_root"]:
            comp_key = f"p3_spinner_{slot['key']}"
            if any(c.get("key") == comp_key for c in comps):
                raise ValueError(f"{key}: {comp_key} is already declared")
            comps.append({
                "key": comp_key,
                "type": SPINNER_TYPE,
                "fields": {"_target": f"$slot-member:{slot['key']}.Rotation",
                           "_offset": slot.get("rotation") or [0.0, 0.0, 0.0, 1.0]},
                "initialFields": {"_speed": g13["spinner_speed"]},
            })
            row["spinner"] = {"component": comp_key, "_speed": g13["spinner_speed"]}
        rows.append(row)
    return rows


def add_drivers_in_file(p2_path: Path, key: str) -> list[dict]:
    """p2.apply.json を読み、add_drivers を適用して書き戻す（対象が無いキーではファイルを変えない）。"""
    if key not in gimmicks.driven_slots():
        return []
    doc = json.loads(p2_path.read_text(encoding="utf-8"))
    rows = add_drivers(doc, key)
    p2_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rows
