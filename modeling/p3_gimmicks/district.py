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
- G03（W10-A）: 噴水の水の Slot に、共有の水の材質を写した専用の材質を足し、水の MeshRenderer だけをそれに付け替える
  （add_g03_material）。その EmissiveColor を ProtoFlux（flux/P3FountainGlow.pg）が drive する。水は動かさないので
  managedFields は付けない
- G05・G06（W10-B）: B の 2 体のおばけの FloatPivot に G01 と同じ中継 2 つ（位置・回転。managedFields ["scale"]）、扉の蝶番 2 つに
  回転の中継 1 つ（managedFields ["position", "scale"]。B を再 apply しても閉じた形に戻さない）。それぞれの Value を ProtoFlux
  （flux/P3MansionMotion.pg）が drive する
"""

from __future__ import annotations

import json
from pathlib import Path

from modeling.p3_gimmicks import gimmicks

SPINNER_TYPE = "FrooxEngine.Spinner"
RELAY_TYPES = {"Position": "[FrooxEngine]FrooxEngine.ValueMultiDriver<float3>",
               "Rotation": "[FrooxEngine]FrooxEngine.ValueMultiDriver<floatQ>"}


def relay_key(slot_key: str, member: str, gimmick: str = "g01") -> str:
    """中継（ValueMultiDriver）の Component のキー。flux のマニフェストの drive の先（G01 は p3_g01_、W10-B は p3_g05_・p3_g06_）。"""
    return f"p3_{gimmick}_{member.lower()}_{slot_key}"


def relay_members(key: str, name: str) -> tuple[str, list[str]] | None:
    """地区 key の Slot name に足す中継の（ギミックの接頭辞, 駆動するメンバー）。中継を使わない Slot は None。

    G01・G05 は位置と回転（上下と傾き・揺れ）、G06 は回転だけ（蝶番。位置は静的な apply が管理し続ける）。
    """
    if key == gimmicks.g01()["district"]:
        return "g01", ["Position", "Rotation"]
    if key == gimmicks.g05()["district"]:
        if name in {g["motion_root"] for g in gimmicks.g05()["ghosts"]}:
            return "g05", ["Position", "Rotation"]
        if name in {h["motion_root"] for h in gimmicks.g06()["hinges"]}:
            return "g06", ["Rotation"]
    return None


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
        relays = relay_members(key, name)
        if relays is not None:
            gid, members = relays
            rest = {"Position": slot.get("position") or [0.0, 0.0, 0.0], "Rotation": slot.get("rotation") or [0.0, 0.0, 0.0, 1.0]}
            row["relays"] = []
            for member in members:
                type_name = RELAY_TYPES[member]
                comp_key = relay_key(slot["key"], member, gid)
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


def _component_ref(key: str) -> str:
    return f"$component:{key}"


def add_g03_material(doc: dict, key: str) -> list[dict]:
    """W10-A（G03）: 噴水の水の MeshRenderer だけに、共有の水の材質を写した専用の材質を付ける。

    - 水の Slot（gimmicks.g03 の water_slot）に PBS_Metallic（キー G03_MATERIAL_KEY）を足す。fields は元の材質と同じ値
      （見た目は P2 と同じ）。EmissiveColor は ProtoFlux（flux/P3FountainGlow.pg）が drive するので、元の値を initialFields に置く
      （fields に書くと apply が駆動と競う。モジュールが無いときは P2 の発光のまま）
    - 水の MeshRenderer の Materials の、元の材質への参照だけを専用の材質へ付け替える。同じ材質を使うほかの MeshRenderer
      （取付位置の目印、I03 の台座、ショーの装置）と元の材質（Blender_Providers の下）は変えない
    - 水の MeshRenderer が 1 つでない、元の材質が 1 つに決まらない、すでに足してあるときは止める
    """
    g = gimmicks.g03()
    if key != g["district"]:
        return []
    hits: dict[str, list[tuple[list[str], dict]]] = {}
    _find_named(doc, [doc["slot"]["name"]], {g["water_slot"]}, hits)
    found = hits.get(g["water_slot"], [])
    if len(found) != 1:
        raise ValueError(f"{key}: expected one Slot named {g['water_slot']}, found {len(found)}")
    chain, node = found[0]
    comps = node.setdefault("components", [])
    if any(c.get("key") == gimmicks.G03_MATERIAL_KEY for c in comps):
        raise ValueError(f"{key}: {gimmicks.G03_MATERIAL_KEY} is already declared")
    renderers = [c for c in comps if c.get("type") == "FrooxEngine.MeshRenderer"]
    if len(renderers) != 1:
        raise ValueError(f"{key}/{g['water_slot']}: expected one MeshRenderer, found {len(renderers)}")
    renderer = renderers[0]
    mats = renderer["fields"]["Materials"]
    if len(mats) != 1 or not str(mats[0]).startswith("$component:"):
        raise ValueError(f"{key}/{g['water_slot']}: expected one material reference, found {mats}")
    source_key = mats[0].split(":", 1)[1]
    sources = []
    stack = [doc]
    while stack:
        n = stack.pop()
        sources += [c for c in n.get("components", []) if c.get("key") == source_key]
        stack.extend(n.get("children", []))
    if len(sources) != 1 or sources[0].get("type") != "FrooxEngine.PBS_Metallic":
        raise ValueError(f"{key}: material {source_key} is not one PBS_Metallic ({len(sources)} found)")
    src_fields = dict(sources[0]["fields"])
    if "EmissiveColor" not in src_fields:
        raise ValueError(f"{key}: material {source_key} has no EmissiveColor")
    emissive = src_fields.pop("EmissiveColor")
    comps.append({
        "key": gimmicks.G03_MATERIAL_KEY,
        "type": "FrooxEngine.PBS_Metallic",
        "fields": src_fields,
        "initialFields": {"EmissiveColor": emissive},
    })
    renderer["fields"]["Materials"] = [_component_ref(gimmicks.G03_MATERIAL_KEY)]
    return [{"slot": "/".join(chain), "g03_material": gimmicks.G03_MATERIAL_KEY, "copied_from": source_key,
             "renderer": renderer["key"], "fields": src_fields, "initialFields": {"EmissiveColor": emissive}}]


def add_drivers_in_file(p2_path: Path, key: str) -> list[dict]:
    """p2.apply.json を読み、add_drivers と add_g03_material を適用して書き戻す（対象が無いキーではファイルを変えない）。"""
    if key not in gimmicks.driven_slots() and key != gimmicks.g03()["district"]:
        return []
    doc = json.loads(p2_path.read_text(encoding="utf-8"))
    rows = add_drivers(doc, key) + add_g03_material(doc, key)
    p2_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rows
