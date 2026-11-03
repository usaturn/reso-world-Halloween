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
- G09・G11（W10-C）: C の攪拌棒の Pivot に回転の中継 1 つ（managedFields ["position", "scale"]）、魔女の仮モデルの root
  （M08 の素材の宣言の親）と巡回路の CarrierPivot に位置・回転の中継 2 つずつ（managedFields ["scale"]）。液面の専用の材質と
  泡・煙の粒子（add_g09_effects）。それぞれを ProtoFlux（flux/P3CandyStreet.pg）が drive する
- G15（W10-D）: D の列車の先頭車の root（M06 の素材の宣言の親の親）と客車の root に位置・回転の中継 2 つずつ（managedFields
  ["scale"]）、4 つの車輪に回転の中継 1 つずつ（managedFields ["position", "scale"]）。それぞれを ProtoFlux（flux/P3GhostTrain.pg）が
  drive する。G13 の Spinner は変えない。検査用の時計（add_g15_clock）を列車と線路の asset root に 1 つずつ足す
- G18・G20（W10-E）: E のキノコ 14 個の発光の部品（_Glow）に、共有の発光の材質を写した個体ごとの材質を足し、各 _Glow の
  MeshRenderer だけをそれに付け替える（add_g18_materials。同じ材質を使う池は変えない）。時計塔の時針・分針・鐘の Pivot に回転の
  中継 1 つずつ（managedFields ["position", "scale"]）。検査用の時計（add_g20_clock）を時計塔の asset root と鐘の腕木に 1 つずつ足す。
  それぞれを ProtoFlux（flux/P3ForestClock.pg）が drive する
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
    if key == gimmicks.g09()["district"]:
        if name == gimmicks.g09()["stir_pivot"]:
            return "g09", ["Rotation"]
        if name in {gimmicks.g11()["rider"], gimmicks.g11()["carrier"]}:
            return "g11", ["Position", "Rotation"]
    if key == gimmicks.g15()["district"]:
        g15 = gimmicks.g15()
        if name in {g15["engine"], g15["car"]}:
            return "g15", ["Position", "Rotation"]
        if name in g15["wheels"]:
            return "g15", ["Rotation"]   # 車輪は軸まわりの回転だけ（位置は静的な apply が管理し続ける）
    if key == gimmicks.g20()["district"]:
        g20 = gimmicks.g20()
        if name in {h["pivot"] for h in g20["hands"].values()} | {g20["bell"]["pivot"]}:
            return "g20", ["Rotation"]   # 針と鐘は軸まわりの回転だけ（位置は静的な apply が管理し続ける）
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


PD = "[FrooxEngine]FrooxEngine.PhotonDust."


def _with_alpha(rgba: list[float], gain: float, alpha: float) -> list[float]:
    return [float(rgba[0]) * gain, float(rgba[1]) * gain, float(rgba[2]) * gain, float(alpha)]


def particle_components(kind: str, base: list[float]) -> list[dict]:
    """W10-C（G09）: 泡・煙の PhotonDust の Component（gimmicks.G09_PARTICLES の kind）。base は液面の色（sRGB の [r, g, b, a]）。

    ParticleSystem → ParticleStyle（描画と、寿命・速さ・大きさ・大きさの変化・色の変化・乱流・位置の計算のモジュール）、
    CircleEmitter（取付位置の水平の円から上へ）。描画は小さな球（IcoSphereMesh）を UnlitMaterial（白、半透明）で描き、
    色と透明度は ColorOverLifetimeStartEnd が液面の色から決める（ProtoFlux が drive するので initialFields）。量は
    CircleEmitter の Rate（同じく drive）。2026-11-01 の試し（ResoLoop_Test_W10C_Particles）で、粒子が動くには
    PositionSimulatorModule が要り、粒子の色の変化が UnlitMaterial の色にかかって透明度も効くことを確かめた
    """
    p = gimmicks.G09_PARTICLES[kind]
    k = p["prefix"]
    modules = ["lif", "spd", "siz", "gro", "col"] + (["trb"] if p["turbulence"] else []) + ["sim"]
    comps = [
        {"key": f"{k}ps", "type": PD + "ParticleSystem", "fields": {"MaxParticleCount": p["max"], "Style": f"$component:{k}sty"}},
        {"key": f"{k}sty", "type": PD + "ParticleStyle",
         "fields": {"Renderer": f"$component:{k}rnd", "Modules": [f"$component:{k}{m}" for m in modules]}},
        {"key": f"{k}rnd", "type": PD + "MeshParticleRenderer", "fields": {"Mesh": f"$component:{k}msh", "Material": f"$component:{k}mat"}},
        {"key": f"{k}msh", "type": "[FrooxEngine]FrooxEngine.IcoSphereMesh", "fields": {"Radius": 0.5, "Subdivisions": 1}},
        {"key": f"{k}mat", "type": "[FrooxEngine]FrooxEngine.UnlitMaterial",
         "fields": {"TintColor": [1.0, 1.0, 1.0, 1.0], "BlendMode": "Alpha", "ZWrite": "Off"}},
        {"key": f"{k}emi", "type": PD + "CircleEmitter",
         "fields": {"System": f"$component:{k}ps", "Radius": p["radius"], "CircleAlignment": "XZ", "DirectionMode": "Fixed",
                    "Direction": [0.0, 1.0, 0.0]},
         "initialFields": {"Rate": p["rate"]}},
        {"key": f"{k}lif", "type": PD + "LifetimeRangeInitializer", "fields": {"MinValue": p["lifetime"][0], "MaxValue": p["lifetime"][1]}},
        {"key": f"{k}spd", "type": PD + "SpeedRangeInitializer", "fields": {"MinValue": p["speed"][0], "MaxValue": p["speed"][1]}},
        {"key": f"{k}siz", "type": PD + "UniformSizeRangeInitializer", "fields": {"MinValue": p["size"][0], "MaxValue": p["size"][1]}},
        {"key": f"{k}gro", "type": PD + "UniformSizeOverLifetimeStartEnd", "fields": {"StartSize": p["grow"][0], "EndSize": p["grow"][1]}},
        {"key": f"{k}col", "type": PD + "ColorOverLifetimeStartEnd",
         "initialFields": {"StartColor": _with_alpha(base, p["color_gain"], p["start_alpha"]),
                           "EndColor": _with_alpha(base, p["color_gain"], p["end_alpha"])}},
    ]
    if p["turbulence"]:
        comps.append({"key": f"{k}trb", "type": PD + "SimplexTurbulentForce", "fields": {"Strength": p["turbulence"]}})
    comps.append({"key": f"{k}sim", "type": PD + "PositionSimulatorModule", "fields": {}})
    return comps


def add_g09_effects(doc: dict, key: str) -> list[dict]:
    """W10-C（G09）: 液面の 1 つ目の材質を専用の材質に替え、泡・煙の取付位置に粒子を足す。

    - 液面の Slot（gimmicks.g09 の liquid）に、1 つ目の材質（P2 のエメラルド。取付位置の目印・I02 の台座・屋台も使う）を写した
      専用の PBS_Metallic（キー G09_LIQUID_MATERIAL_KEY）を足し、液面の MeshRenderer の 1 つ目の材質だけをそれに付け替える。
      2 つ目（マゼンタの盛り上がり）と元の材質は変えない。AlbedoColor・EmissiveColor は ProtoFlux が液面の色（HMC_P3）から
      drive するので initialFields（元の値）に置く（G03 と同じ）
    - 泡・煙の取付位置の Slot に particle_components を足す（Slot は足さない）
    - 液面の MeshRenderer が 1 つでない、材質が 2 つでない、すでに足してあるときは止める
    """
    g = gimmicks.g09()
    if key != g["district"]:
        return []
    names = {g["liquid"], *g["attach"].values()}
    hits: dict[str, list[tuple[list[str], dict]]] = {}
    _find_named(doc, [doc["slot"]["name"]], names, hits)
    for n in names:
        if len(hits.get(n, [])) != 1:
            raise ValueError(f"{key}: expected one Slot named {n}, found {len(hits.get(n, []))}")
    chain, node = hits[g["liquid"]][0]
    comps = node.setdefault("components", [])
    if any(c.get("key") == gimmicks.G09_LIQUID_MATERIAL_KEY for c in comps):
        raise ValueError(f"{key}: {gimmicks.G09_LIQUID_MATERIAL_KEY} is already declared")
    renderers = [c for c in comps if c.get("type") == "FrooxEngine.MeshRenderer"]
    if len(renderers) != 1:
        raise ValueError(f"{key}/{g['liquid']}: expected one MeshRenderer, found {len(renderers)}")
    renderer = renderers[0]
    mats = renderer["fields"]["Materials"]
    if len(mats) != 2 or not all(str(m).startswith("$component:") for m in mats):
        raise ValueError(f"{key}/{g['liquid']}: expected two material references, found {mats}")
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
    driven = {m: src_fields.pop(m) for m in ("AlbedoColor", "EmissiveColor")}
    comps.append({"key": gimmicks.G09_LIQUID_MATERIAL_KEY, "type": "FrooxEngine.PBS_Metallic", "fields": src_fields,
                  "initialFields": driven})
    renderer["fields"]["Materials"] = [_component_ref(gimmicks.G09_LIQUID_MATERIAL_KEY), mats[1]]
    rows = [{"slot": "/".join(chain), "g09_material": gimmicks.G09_LIQUID_MATERIAL_KEY, "copied_from": source_key,
             "renderer": renderer["key"], "fields": src_fields, "initialFields": driven}]
    for kind, name in g["attach"].items():
        chain, node = hits[name][0]
        comps = node.setdefault("components", [])
        new = particle_components(kind, driven["AlbedoColor"])
        if any(c.get("key") == n["key"] for c in comps for n in new):
            raise ValueError(f"{key}/{name}: G09 particles are already declared")
        comps.extend(new)
        rows.append({"slot": "/".join(chain), "g09_particles": kind, "components": [c["key"] for c in new]})
    return rows


def add_g15_clock(doc: dict, key: str) -> list[dict]:
    """W10-D（G15）: 検査用の時計（ValueField<double>。gimmicks.G15_CLOCK_KEYS）を、列車の asset root と線路の asset root に 1 つずつ
    足す（同じ Slot に同じ型を 2 つ置くと、再接続の後に見分ける手掛かりが無い。resoloop の APPLY_COMPONENT_IDENTITY_RISK）。
    ProtoFlux（flux/P3GhostTrain.pg）が WorldTimeDouble を drive するので Value は initialFields。動く物ではなく、見た目も変えない。"""
    g = gimmicks.g15()
    if key != g["district"]:
        return []
    owners = (g["asset_id"], g["track_asset_id"])
    hits: dict[str, list[tuple[list[str], dict]]] = {}
    _find_named(doc, [doc["slot"]["name"]], set(owners), hits)
    rows = []
    for owner, k in zip(owners, gimmicks.G15_CLOCK_KEYS):
        found = hits.get(owner, [])
        if len(found) != 1:
            raise ValueError(f"{key}: expected one Slot named {owner}, found {len(found)}")
        chain, node = found[0]
        comps = node.setdefault("components", [])
        if any(c.get("key") == k for c in comps):
            raise ValueError(f"{key}: {k} is already declared")
        comps.append({"key": k, "type": "[FrooxEngine]FrooxEngine.ValueField<double>", "initialFields": {"Value": 0.0}})
        rows.append({"slot": "/".join(chain), "g15_clock": k})
    return rows


def add_g18_materials(doc: dict, key: str) -> list[dict]:
    """W10-E（G18）: キノコの個体ごとに、発光の部品（_Glow）の MeshRenderer だけへ、共有の発光の材質を写した専用の材質を付ける。

    - 各 _Glow の Slot に PBS_Metallic（キー gimmicks.g18 の material_key、p3_g18_01〜）を足す。fields は元の材質と同じ値（見た目は
      P2 と同じ）。EmissiveColor は ProtoFlux（flux/P3ForestClock.pg）が drive するので、元の値を initialFields に置く（G03 と同じ）
    - _Glow の MeshRenderer の Materials の、元の材質への参照だけを専用の材質へ付け替える。同じ材質を使うほかの MeshRenderer（池の
      EFR_Pond_001 の睡蓮）と元の材質（Blender_Providers の下）は変えない
    - _Glow の Slot が 1 つでない、MeshRenderer・材質が 1 つでない、個体ごとに元の材質が違う、すでに足してあるときは止める
    """
    g = gimmicks.g18()
    if key != g["district"]:
        return []
    names = {r["glow_part"] for r in g["individuals"]}
    hits: dict[str, list[tuple[list[str], dict]]] = {}
    _find_named(doc, [doc["slot"]["name"]], names, hits)
    rows: list[dict] = []
    source_key = None
    for r in g["individuals"]:
        found = hits.get(r["glow_part"], [])
        if len(found) != 1:
            raise ValueError(f"{key}: expected one Slot named {r['glow_part']}, found {len(found)}")
        chain, node = found[0]
        comps = node.setdefault("components", [])
        if any(c.get("key") == r["material_key"] for c in comps):
            raise ValueError(f"{key}: {r['material_key']} is already declared")
        renderers = [c for c in comps if c.get("type") == "FrooxEngine.MeshRenderer"]
        if len(renderers) != 1:
            raise ValueError(f"{key}/{r['glow_part']}: expected one MeshRenderer, found {len(renderers)}")
        mats = renderers[0]["fields"]["Materials"]
        if len(mats) != 1 or not str(mats[0]).startswith("$component:"):
            raise ValueError(f"{key}/{r['glow_part']}: expected one material reference, found {mats}")
        this = mats[0].split(":", 1)[1]
        if source_key not in (None, this):
            raise ValueError(f"{key}/{r['glow_part']}: glow material {this} differs from {source_key}")
        source_key = this
        rows.append({"slot": "/".join(chain), "g18_material": r["material_key"], "renderer": renderers[0]["key"], "node": node})
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
    for row in rows:
        node = row.pop("node")
        node["components"].append({"key": row["g18_material"], "type": "FrooxEngine.PBS_Metallic", "fields": dict(src_fields),
                                   "initialFields": {"EmissiveColor": emissive}})
        renderer = next(c for c in node["components"] if c.get("key") == row["renderer"])
        renderer["fields"]["Materials"] = [_component_ref(row["g18_material"])]
        row.update({"copied_from": source_key, "fields": src_fields, "initialFields": {"EmissiveColor": emissive}})
    return rows


def add_g20_clock(doc: dict, key: str) -> list[dict]:
    """W10-E（G20）: 検査用の時計（ValueField<double2>。gimmicks.G20_CLOCK_KEYS）を、時計塔の asset root と鐘の腕木に 1 つずつ足す
    （W10-D の add_g15_clock と同じ理由で別の Slot）。ProtoFlux（flux/P3ForestClock.pg）が (WorldTimeDouble, ローカル時刻の 0 時から
    の秒) を drive するので Value は initialFields。動く物ではなく、見た目も変えない。"""
    g = gimmicks.g20()
    if key != g["district"]:
        return []
    owners = (g["asset_id"], g["bracket"])
    hits: dict[str, list[tuple[list[str], dict]]] = {}
    _find_named(doc, [doc["slot"]["name"]], set(owners), hits)
    rows = []
    for owner, k in zip(owners, gimmicks.G20_CLOCK_KEYS):
        found = hits.get(owner, [])
        if len(found) != 1:
            raise ValueError(f"{key}: expected one Slot named {owner}, found {len(found)}")
        chain, node = found[0]
        comps = node.setdefault("components", [])
        if any(c.get("key") == k for c in comps):
            raise ValueError(f"{key}: {k} is already declared")
        comps.append({"key": k, "type": "[FrooxEngine]FrooxEngine.ValueField<double2>", "initialFields": {"Value": [0.0, 0.0]}})
        rows.append({"slot": "/".join(chain), "g20_clock": k})
    return rows


def add_drivers_in_file(p2_path: Path, key: str) -> list[dict]:
    """p2.apply.json を読み、add_drivers・add_g03_material・add_g09_effects・add_g15_clock・add_g18_materials・add_g20_clock を
    適用して書き戻す（対象が無いキーではファイルを変えない）。"""
    if key not in gimmicks.driven_slots() and key != gimmicks.g03()["district"]:
        return []
    doc = json.loads(p2_path.read_text(encoding="utf-8"))
    rows = (add_drivers(doc, key) + add_g03_material(doc, key) + add_g09_effects(doc, key) + add_g15_clock(doc, key)
            + add_g18_materials(doc, key) + add_g20_clock(doc, key))
    p2_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rows
