"""W09R: Meshy の仕上げた素材に差し替えた仮モデルを、1 回の観察（resoloop hierarchy）から実測して検査する。

実行（プロジェクトのディレクトリ）:
    uv run python modeling/p2_meshy/verify_live.py --url ws://localhost:<PORT>/ \\
        --raw-out <Git の外の JSON> --output review/p2_meshy/live_checks.json

- 観察は W08 と同じ（modeling/p2_static/verify_live.py の observe）。生の出力（ResoniteLink の ID を含む）は --raw-out に置き、
  コミットしない。--output には ID と資産の URL を含まない要約だけを書く
- 期待値は実測から求めず、データから求める（親ごと動いた・回った状態を成功と判定しないため）: 仮モデルの見た目の Slot の
  世界の原点は review/overview/checks.json の placeholders の frame_origin_world、素材の世界の向きは received.json の
  placement_hint.rotation_z_deg、取付位置は地区のアセット一覧の origin_world と pivot_local
- 検査（replacements.py の REPLACEMENTS の行ごと。docs/p2-meshy-replacement.md 5.3 章）
  - 位置: visual_root の世界の原点と、素材のメッシュの外接箱（1 cm 以内）
  - 正面と鏡像: 素材の Slot の前方（ローカルの +Z）を、拡縮を含む完全な変換で世界に置いた向き。祖先の拡縮はすべて正
  - 描画: 素材の Slot と祖先が有効、素材の MeshRenderer が有効で、同じ Slot の StaticMesh と、色の画像を持つ材質を参照する。
    hide に書いた仮モデルの MeshRenderer は Enabled = false
  - 取付位置: 仮モデルのアセットの取付位置（attachment_point）が、データの位置にある
  - 当たり判定: <visual_root>_FixedCollision が有効で、visual_root と同じ変換、MeshCollider が有効・Static・CharacterCollider で、
    同じ Slot の StaticMesh（visual_root と同じメッシュの資産）を参照する。REPLACEMENTS の collision が False の素材（空を飛ぶ
    M08 など）は、<visual_root>_FixedCollision が無いことを確かめる（あれば設定の誤りとして失敗にし、検査を黙って飛ばさない）
  - 発光: REPLACEMENTS の emissive が True の素材（M04）は、材質の EmissiveMap が URL のある画像を参照する
  - 向き: received.json の placement_hint に回転が無い素材（経路の上の M06・M08）は、W07 の review/overview/checks.json の
    placeholders.<M>.front_world（仮モデルの正面の世界の向き）から期待値を求める（W09R-C で追加）
  - 数: 地区ごとに、Slot・Component の数が W08 の実測（review/p2_static/live_checks.json）に、その地区のすべての差し替えの
    宣言の数を足した値と一致する
  - 可動部品（W09R-A で追加。REPLACEMENTS の moving_parts。M01 の門扉）: 外接箱は素材のすべてのメッシュ（素材の Slot の子孫と、
    motion_root の下の部品の宣言）を合わせた物。仮モデルの motion_root と部品の原点が素材の蝶番（received.json の向きと
    アセット一覧の leaves の pivot_local から求める）と 1 cm 以内、motion_root の回転が閉 0° からの開いた角度、部品の世界の向きが
    開いた形。部品ごとの外接箱が、部品のメッシュをデータの蝶番・向きで置いた物と 1 cm 以内（縮尺・形の誤りを全体の外接箱は
    見落とす）。部品の宣言にメッシュがあり、描画され、部品の下に当たり判定が無い。hide の対象は motion_root の下も探す
  - 素材のメッシュの当たり判定（W09R-B で追加。REPLACEMENTS の collision が "finished"。M03）: 仮モデルの
    <visual_root>_FixedCollision の MeshCollider が Enabled = false（残っていると、見えない仮モデルの形と素材の形の両方に
    当たる）。素材のすべてのメッシュの Slot に、有効・Static・CharacterCollider の MeshCollider があり、同じ Slot の StaticMesh を
    参照し、Offset が 0（見た目からずれた当たり判定を見落とさない。PR #53 の GPT のレビュー）。素材のバンドルの中で、
    それ以外の Slot に当たり判定が無い
  - 入口（W09R-B で追加。REPLACEMENTS の entrance。M03）: 地区の扉の蝶番の Slot の原点が、素材の開口の蝶番の線の下端
    （review/M03/checks.json の door_opening.hinges の local_bottom を、データの原点と向きで置いた点）と 1 cm 以内で、
    蝶番の Slot の前方が建物の奥（素材の正面の逆向き）を向く（閉じた扉が壁の面にある。回った扉を見落とさない）。玄関ホールの
    原点が、開口の中心の床から hall_depth_m 奥と 1 cm 以内で、ホールの前方も建物の奥を向く。扉とホールのアセットの root から
    下のすべての Slot と、地区の root からの祖先の拡縮が 1（原点が合っていても扉やホールの形が縮む・伸びるのを見落とさない。
    PR #53 の GPT のレビュー）
  - 素材の子 1 つだけを置く行（W09R-D で追加。REPLACEMENTS の source・export_root。M05 の柱と屋根）: アセット一覧と review は
    素材のキー（source）から読み、外接箱の期待値は review/<source>/checks.json の parts の bounds_m（子のローカル）
  - 取付位置の期待値は、アセット一覧の親の部品の pivot_local を足した位置（W09R-D で修正。D の取付位置は TurnRoot・EngineRoot の子）
  - 組み立て（W09R-D で追加。REPLACEMENTS の assembly_with。M05 の屋根）: この行の素材の原点と assembly_with の行の素材の原点の
    差が、アセット一覧の pivot_local の差を素材の向きで回した物と 1 cm 以内
  - 支柱（W09R-D で追加。REPLACEMENTS の poles。M05 の屋根）: 地区の宣言の支柱のメッシュ（8 本）の上端が、どの支柱でも素材の
    屋根の下面以上で、先が屋根の閉じた殻の中にある（軸の上で先より下の屋根の面の数が奇数）。check_poles。測った支柱と屋根の
    メッシュがワールドに表示されている物か（Slot が有効、MeshRenderer が有効で同じ Slot の StaticMesh を参照し、その URL が
    apply の state の記録と同じで、state の sourceHash がバンドルのファイルと同じ）も確かめる（check_measured_mesh_is_shown。
    PR #54 の GPT のレビュー）。state は --state-dir（既定は親の checkout の .resoloop/state）
  - 前照灯（W09R-D で追加。REPLACEMENTS の lens_attachment。M06）: 地区の取付位置が、素材のレンズの前面（review/M06/checks.json
    の headlamp.front_profile_x0）の前 max_gap_m 以内で、レンズの高さにある。check_lens_attachment
  - 隠す兄弟（W09R-E で追加。M07 の仮の文字盤）: hide の対象は、visual_root の兄弟のうち地区のアセット一覧の
    replacement_slot.hide_on_replacement に書いてある物も探す（replacements.owner_hide_on_replacement と同じ値）
  - 針（W09R-E で追加。REPLACEMENTS の dial_hands。M07）: 地区の時針・分針の回転軸が、素材の文字盤の中心（review/M07/checks.json の
    dial.centre_local_m をデータの原点と向きで置いた点）を通る軸の上 TOL_M 以内で、文字盤より前にある。針の頂点の前後の範囲と
    回る半径の中に素材の三角形が無い（めり込まない。針は 360° 回るので回す位置によらない）。測った針と文字盤のメッシュが
    ワールドに表示されている物か（check_measured_mesh_is_shown）。check_dial_hands
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from modeling.p2_meshy.export_meshy import part_document_name  # noqa: E402
from modeling.p2_meshy.replacements import REPLACEMENTS  # noqa: E402
from modeling.p2_static.verify_live import (  # noqa: E402
    TOL_M,
    b2r,
    chain_for,
    count_nodes,
    declared_counts,
    dist,
    mesh_bounds_world,
    observe,
    to_world,
)


# apply の state の置き場（親の checkout。AGENTS.md）。--state-dir で変えられる
STATE_DIR = Path("/workspaces/reso-world/worlds/reso-world-Halloween/.resoloop/state")


def applied_mesh(state_file: str, bundle: Path, doc: dict, key: str) -> dict:
    """宣言の資産 key のメッシュのファイルが、apply の state に記録された物（sourceHash）と同じかと、その取り込み先の URL。
    検査に使うローカルのバンドルのメッシュと、ワールドが表示しているメッシュが同じ物かを確かめるために使う（PR #54 の GPT のレビュー）。"""
    rec = (json.loads((STATE_DIR / state_file).read_text(encoding="utf-8")).get("assets") or {}).get(key) or {}
    sha = hashlib.sha256((bundle / doc["assets"][key]["source"]).read_bytes()).hexdigest()
    return {"state": state_file, "asset": key, "bundle_matches_state": rec.get("sourceHash", "").lower() == sha, "url": rec.get("url")}


def _load(rel: str) -> dict:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def latest_meshy_bundle(meshy_id: str) -> Path:
    dirs = [d for d in sorted((PROJECT_ROOT / "exports" / "p2_meshy").glob(f"{meshy_id}-*")) if (d / "p2m.apply.json").is_file()]
    if not dirs:
        raise SystemExit(f"no exports/p2_meshy/{meshy_id}-*/p2m.apply.json")
    return dirs[-1]


# W07 の checks.json の front_world（仮モデルの正面の世界の向き）を、Blender の Z 軸まわりの回転（+Y が 0°）にする
FRONT_WORLD_DEG = {"north(+Y)": 0.0, "west(-X)": 90.0, "south(-Y)": 180.0, "east(+X)": -90.0}


def expected_yaw_deg(meshy_id: str, received: dict, placeholders: dict) -> tuple[float, str]:
    """素材の世界の向きの期待値（Blender の Z 軸まわりの度）と、その出典。"""
    hint = (received["decided"].get("placement_hint") or {}).get("rotation_z_deg")
    if hint is not None:
        return float(hint), "received.json placement_hint.rotation_z_deg"
    front = (placeholders.get(meshy_id) or {}).get("front_world")
    if front not in FRONT_WORLD_DEG:
        raise SystemExit(f"{meshy_id}: no placement_hint rotation and no usable front_world in review/overview/checks.json ({front!r})")
    return FRONT_WORLD_DEG[front], f"review/overview/checks.json placeholders.{meshy_id}.front_world = {front}"


def _mesh_slots(node: dict, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], str]]:
    """宣言の node とその子孫のうち StaticMesh を持つ Slot の（node からの名前のパス, メッシュの資産のキー）。"""
    out = []
    mesh = next((c for c in node.get("components", []) if c["type"] == "FrooxEngine.StaticMesh"), None)
    if mesh is not None:
        out.append((path, mesh["fields"]["URL"].removeprefix("$asset:")))
    for ch in node.get("children", []):
        out.extend(_mesh_slots(ch, path + (ch["slot"]["name"],)))
    return out


def _vertices(bundle: Path, doc: dict, key: str) -> list[dict]:
    return json.loads((bundle / doc["assets"][key]["source"]).read_text(encoding="utf-8"))["vertices"]


def _mesh(bundle: Path, doc: dict, key: str) -> dict:
    """メッシュの資産の頂点（Resonite の軸）と三角形（頂点の番号の組）。"""
    data = json.loads((bundle / doc["assets"][key]["source"]).read_text(encoding="utf-8"))
    tris = [tuple(sm["vertexIndices"][i:i + 3]) for sm in data["submeshes"] for i in range(0, len(sm["vertexIndices"]), 3)]
    return {"vertices": [[v["position"][k] for k in "xyz"] for v in data["vertices"]], "triangles": tris}


def _find_decl(node: dict, name: str) -> dict | None:
    if node["slot"]["name"] == name:
        return node
    for ch in node.get("children", []):
        hit = _find_decl(ch, name)
        if hit is not None:
            return hit
    return None


def load_inputs(meshy_id: str, rep: dict) -> dict:
    """検査に使うデータ（実測ではない物）を読む。テストはこの dict を直接作る。"""
    bundle = latest_meshy_bundle(meshy_id)
    doc = json.loads((bundle / "p2m.apply.json").read_text(encoding="utf-8"))
    asset_slot = next(ch for ch in doc["children"] if ch["slot"]["name"] == rep["asset_id"])
    meshes = [{"path": list(path), "vertices": _vertices(bundle, doc, key)} for path, key in _mesh_slots(asset_slot)]
    received = next(a for a in _load("assets/meshy/received.json")["assets"] if a["row_id"] == meshy_id)
    ds, dc, auto = declared_counts(doc)
    # 素材の子 1 つだけを置く行（W09R-D の M05）: アセット一覧と review は素材のキー（source）。外接箱は素材の仕上げの検査
    # （review/<source>/checks.json の parts の bounds_m。子のローカル）から求める
    source = rep.get("source", meshy_id)
    manifest = _load(f"assets/manifest/{source}.json")["assets"][0]
    bounds_local = manifest["bounds_local"]
    if rep.get("export_root"):
        part_checks = _load(f"review/{source}/checks.json")["parts"][meshy_id]
        if part_checks["object"] != rep["asset_id"]:
            raise SystemExit(f"{meshy_id}: review/{source}/checks.json parts.{meshy_id} is {part_checks['object']}, not {rep['asset_id']}")
        bounds_local = part_checks["bounds_m"]
    pivots = {p["part_id"]: p["pivot_local"] for p in manifest["parts"]}
    assembly = None
    if rep.get("assembly_with"):
        # 組み立て（W09R-D の M05 の屋根と柱）: 期待値は素材のアセット一覧の pivot_local の差（実測と配置の値から求めない）
        other = REPLACEMENTS[rep["assembly_with"]]
        other_doc = json.loads((latest_meshy_bundle(rep["assembly_with"]) / "p2m.apply.json").read_text(encoding="utf-8"))
        assembly = {"with": rep["assembly_with"],
                    "other_path": [*other["visual_root_path"].split("/")[1:], other_doc["slot"]["name"], other["asset_id"]],
                    "offset_local": [pivots[rep["asset_id"]][i] - pivots[other["asset_id"]][i] for i in range(3)]}
    poles = None
    if rep.get("poles"):
        # 支柱（W09R-D）: 地区の宣言のメッシュ（最新の exports/p2_static/<地区>-*）と、素材のメッシュ（三角形を含む）から測る
        dbundle = sorted((PROJECT_ROOT / "exports" / "p2_static").glob(f"{rep['district']}-*/p2.apply.json"))[-1].parent
        ddoc = json.loads((dbundle / "p2.apply.json").read_text(encoding="utf-8"))
        pnode = _find_decl(ddoc, rep["poles"])
        pkey = next(c for c in pnode["components"] if c["type"] == "FrooxEngine.StaticMesh")["fields"]["URL"].removeprefix("$asset:")
        (cpath, ckey), = _mesh_slots(asset_slot)
        poles = {"slot": rep["poles"], "district_bundle": dbundle.relative_to(PROJECT_ROOT).as_posix(),
                 "pole_mesh": _mesh(dbundle, ddoc, pkey), "canopy_path": list(cpath), "canopy_mesh": _mesh(bundle, doc, ckey),
                 "pole_applied": applied_mesh(f"p2_{rep['district']}.json", dbundle, ddoc, pkey),
                 "canopy_applied": applied_mesh(f"p2m_{meshy_id}.json", bundle, doc, ckey)}
    lens = None
    if rep.get("lens_attachment"):
        # 前照灯（W09R-D の M06）: レンズの前面の形は素材の仕上げの検査（review/<source>/checks.json の headlamp）から
        lens = {**rep["lens_attachment"], "front_profile": _load(f"review/{source}/checks.json")["headlamp"]["front_profile_x0"]}
    hands = None
    if rep.get("dial_hands"):
        # 針（W09R-E の M07）: 文字盤の中心は素材の仕上げの検査（review/<source>/checks.json の dial）から、針の形は地区の宣言の
        # メッシュ（最新の exports/p2_static/<地区>-*）から、文字盤の形は素材のメッシュから
        dbundle = sorted((PROJECT_ROOT / "exports" / "p2_static").glob(f"{rep['district']}-*/p2.apply.json"))[-1].parent
        ddoc = json.loads((dbundle / "p2.apply.json").read_text(encoding="utf-8"))
        rows_h = {}
        for pivot, hand in rep["dial_hands"].items():
            hnode = _find_decl(ddoc, hand)
            hkey = next(c for c in hnode["components"] if c["type"] == "FrooxEngine.StaticMesh")["fields"]["URL"].removeprefix("$asset:")
            rows_h[pivot] = {"hand": hand, "mesh": _mesh(dbundle, ddoc, hkey), "applied": applied_mesh(f"p2_{rep['district']}.json", dbundle, ddoc, hkey)}
        (dpath, dkey), = _mesh_slots(asset_slot)
        hands = {"centre_local": _load(f"review/{source}/checks.json")["dial"]["centre_local_m"], "hands": rows_h,
                 "district_bundle": dbundle.relative_to(PROJECT_ROOT).as_posix(), "dial_path": list(dpath),
                 "dial_mesh": _mesh(bundle, doc, dkey), "dial_applied": applied_mesh(f"p2m_{meshy_id}.json", bundle, doc, dkey)}
    # 可動部品（W09R-A）: 部品ごとの宣言（motion_root の下）。期待値はアセット一覧の leaves から直接求める（moving_part_poses の
    # 計算を通さない。置き方の計算の誤りを、同じ計算で求めた期待値で合格にしないため）
    moving = {}
    for part_id, part in (rep.get("moving_parts") or {}).items():
        pdoc = json.loads((bundle / part_document_name(part["document"])).read_text(encoding="utf-8"))
        pslot = next(ch for ch in pdoc["children"] if ch["slot"]["name"] == part_id)
        ps, pc, pa = declared_counts(pdoc)
        ds, dc, auto = ds + ps, dc + pc, auto + pa
        leaf = manifest["leaves"][part_id]
        moving[part_id] = {"motion_root": part["motion_root"], "bundle_root_name": pdoc["slot"]["name"],
                           "pivot_local": leaf["pivot_local"], "closed_deg": float(leaf["closed_deg"]), "placed_deg": float(leaf["placed_deg"]),
                           "meshes": [{"path": list(path), "vertices": _vertices(bundle, pdoc, key)} for path, key in _mesh_slots(pslot)]}
    placeholders = _load("review/overview/checks.json")["placeholders"]
    hint_deg, hint_source = expected_yaw_deg(meshy_id, received, placeholders)
    # 入口（W09R-B）: 期待値は素材の仕上げの検査（review/<M>/checks.json の door_opening）から求め、地区の配置データから求めない
    entrance = None
    if rep.get("entrance"):
        opening = _load(f"review/{meshy_id}/checks.json")["door_opening"]
        entrance = {"hinges": {slot: opening["hinges"][name]["local_bottom"] for slot, name in rep["entrance"]["hinges"].items()},
                    "hall": rep["entrance"]["hall"], "hall_depth_m": float(rep["entrance"]["hall_depth_m"]),
                    "opening_centre_floor_local": [opening["opening_local_m"]["centre_x"], opening["opening_local_m"]["wall_y"],
                                                   opening["opening_local_m"]["z_bottom"]]}
    return {
        "bundle": bundle.relative_to(PROJECT_ROOT).as_posix(),
        "bundle_root_name": doc["slot"]["name"],
        "meshes": meshes,
        "bounds_local": bounds_local,
        "assembly": assembly,
        "poles": poles,
        "lens_attachment": lens,
        "dial_hands": hands,
        "hint_deg": hint_deg,
        "hint_source": hint_source,
        "frame_origin_world": placeholders[meshy_id]["frame_origin_world"],
        "placeholder_asset": next(a for a in _load(f"assets/manifest/{rep['district']}.json")["assets"] if a["asset_id"] == rep["placeholder"]),
        "moving_parts": moving,
        "entrance": entrance,
        "declared": {"slots": ds, "components": dc + auto},
    }


def find_path(root: dict, path: tuple[str, ...]) -> list[dict] | None:
    try:
        return chain_for(root, path)
    except StopIteration:
        return None


def component(node: dict | None, short_type: str) -> dict | None:
    if node is None:
        return None
    return next((c for c in node.get("components") or [] if c.get("type", "").endswith(f"FrooxEngine.{short_type}")), None)


def member(comp: dict | None, name: str):
    """値（field）か参照先の ID（reference）か、参照のリストなら ID のリスト。無ければ None。"""
    if comp is None:
        return None
    m = (comp.get("members") or {}).get(name) or {}
    if m.get("kind") == "list":
        return [e.get("targetId") for e in m.get("elements") or []]
    return m.get("value", m.get("targetId"))


def component_index(root: dict) -> dict[str, tuple[dict, dict]]:
    """Component の ID -> (Component, その Slot)。"""
    out: dict[str, tuple[dict, dict]] = {}

    def walk(n: dict) -> None:
        for c in n.get("components") or []:
            out[c["id"]] = (c, n)
        for ch in n.get("children") or []:
            walk(ch)

    walk(root)
    return out


def rz(deg: float, v) -> list[float]:
    a = math.radians(deg)
    return [v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a), v[2]]


def expected_bounds(bounds_local: dict, deg: float, origin_resonite) -> tuple[list[float], list[float]]:
    """アセットのローカルの外接箱（Blender）を世界の Z 軸まわりに deg 回し、Resonite の軸で origin に置いた外接箱。"""
    lo, hi = bounds_local["min"], bounds_local["max"]
    corners = [rz(deg, [x, y, z]) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    pts = [[origin_resonite[i] + b2r(c)[i] for i in range(3)] for c in corners]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def to_local(chain: list[dict], p) -> list[float]:
    """世界の点 p を chain の最後の Slot のローカル（Resonite の軸）にする（祖先の拡縮は正で、軸は直交する前提）。"""
    o = to_world(chain, (0.0, 0.0, 0.0))
    out = []
    for axis in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)):
        e = [a - b for a, b in zip(to_world(chain, axis), o)]
        out.append(sum((p[i] - o[i]) * e[i] for i in range(3)) / sum(c * c for c in e))
    return out


def pivot_in_asset(asset: dict, part_id: str) -> list[float]:
    """アセット一覧の部品の、アセットの root からの位置（Blender の軸）。pivot_local は親の部品からの位置なので、
    アセットの root までの親の pivot_local を足す（W09R-D: D の取付位置は TurnRoot・EngineRoot の子。親は回転なしの前提）。"""
    by = {p["part_id"]: p for p in asset["parts"]}
    off, p = [0.0, 0.0, 0.0], by[part_id]
    while True:
        off = [off[i] + float(p["pivot_local"][i]) for i in range(3)]
        parent = by.get(p.get("parent_part") or "")
        if parent is None or parent["role"] == "asset_root":
            return off
        p = parent


def _up_hits(mesh: dict, x: float, z: float) -> list[float]:
    """メッシュ（ローカル、Resonite の軸）を、点 (x, z) を通る鉛直（ローカルの y）の線が通る高さ（小さい順）。"""
    if "_bb" not in mesh:
        vs = mesh["vertices"]
        mesh["_bb"] = [(min(vs[a][0], vs[b][0], vs[c][0]), max(vs[a][0], vs[b][0], vs[c][0]),
                        min(vs[a][2], vs[b][2], vs[c][2]), max(vs[a][2], vs[b][2], vs[c][2])) for a, b, c in mesh["triangles"]]
    vs, hits = mesh["vertices"], []
    for (a, b, c), (x0, x1, z0, z1) in zip(mesh["triangles"], mesh["_bb"]):
        if x < x0 or x > x1 or z < z0 or z > z1:
            continue
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = vs[a], vs[b], vs[c]
        d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
        if abs(d) < 1e-12:
            continue
        l1 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / d
        l2 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / d
        l3 = 1.0 - l1 - l2
        if min(l1, l2, l3) >= -1e-9:
            hits.append(l1 * ay + l2 * by + l3 * cy)
    return sorted(hits)


def check_poles(pole_chain: list[dict], pole_mesh: dict, canopy_chain: list[dict], canopy_mesh: dict) -> tuple[list[dict], list[str]]:
    """W05 の支柱（1 つのメッシュに 8 本）が素材の屋根の下面に届き、先が屋根の殻の中にあるか（W09R-D の M05）。

    支柱は頂点を水平の距離 0.3 m でまとめた塊ごと。上端は塊の最も高い頂点、太さは上端の頂点の軸からの距離。上端の高さで、
    軸と、軸のまわりの 16 点を屋根のローカルへ移し、鉛直の線が最初に屋根に当たる高さ（下面）を測る。どの点でも上端が下面
    以上（隙間が見えない）で、軸の上で上端より下にある屋根の面の数が奇数（先が閉じた殻の中にあり、上に突き抜けない）。
    """
    clusters: list[list[list[float]]] = []
    for v in pole_mesh["vertices"]:
        for cl in clusters:
            if (v[0] - cl[0][0]) ** 2 + (v[2] - cl[0][2]) ** 2 < 0.09:
                cl.append(v)
                break
        else:
            clusters.append([v])
    rows, problems = [], []
    for k, cl in enumerate(sorted(clusters, key=lambda c: math.atan2(sum(v[2] for v in c), sum(v[0] for v in c)))):
        cx, cz = sum(v[0] for v in cl) / len(cl), sum(v[2] for v in cl) / len(cl)
        top = max(v[1] for v in cl)
        radius = max(math.hypot(v[0] - cx, v[2] - cz) for v in cl if v[1] > top - 1e-4)
        firsts, misses, below = [], 0, None
        for j in range(17):
            px, pz = (cx, cz) if j == 0 else (cx + radius * math.cos(j * math.pi / 8), cz + radius * math.sin(j * math.pi / 8))
            q = to_local(canopy_chain, to_world(pole_chain, (px, top, pz)))
            hits = _up_hits(canopy_mesh, q[0], q[2])
            if not hits:
                misses += 1
                continue
            firsts.append(hits[0] - q[1])  # 下面の上端からの高さ（正なら隙間）
            if j == 0:
                below = sum(1 for h in hits if h < q[1])
        row = {"pole": k, "centre_local": [round(cx, 3), round(cz, 3)], "top_local_y": round(top, 4),
               "max_gap_m": round(max(firsts), 4) if firsts else None, "misses": misses}
        if misses:
            problems.append(f"pole {k}: no canopy above {misses} of 17 points")
        elif max(firsts) > 1e-3:
            problems.append(f"pole {k}: ends {max(firsts):.3f} m below the canopy underside")
        elif below is None or below % 2 == 0:
            problems.append(f"pole {k}: the tip is outside the canopy shell ({below} surfaces below it)")
        row["surfaces_below_tip"] = below
        rows.append(row)
    return rows, problems


def check_measured_mesh_is_shown(chain: list[dict], applied: dict) -> list[str]:
    """検査で測るメッシュ（ローカルのバンドル）が、chain の最後の Slot に表示されている物か: Slot と祖先が有効、MeshRenderer が
    有効で同じ Slot の StaticMesh を参照し、その URL が apply の state の記録と同じで、state の記録がバンドルのファイルと同じ
    （PR #54 の GPT のレビュー: 支柱のメッシュの更新を apply していない・支柱を隠した状態でも、新しいバンドルの形で合格していた）。"""
    node, problems = chain[-1], []
    inactive = [n["name"] for n in chain if n.get("isActive") is False]
    if inactive:
        problems.append(f"{node['name']}: inactive Slot on the path: {inactive}")
    renderer, mesh = component(node, "MeshRenderer"), component(node, "StaticMesh")
    if member(renderer, "Enabled") is not True or mesh is None or member(renderer, "Mesh") != mesh["id"]:
        problems.append(f"{node['name']}: not drawn with its own StaticMesh")
    if not applied["bundle_matches_state"]:
        problems.append(f"{node['name']}: the measured bundle mesh {applied['asset']} is not the one recorded in {applied['state']}")
    elif mesh is None or not applied["url"] or member(mesh, "URL") != applied["url"]:
        problems.append(f"{node['name']}: StaticMesh.URL is not the applied {applied['asset']} of {applied['state']}")
    return problems


def check_lens_attachment(att_chain: list[dict], asset_chain: list[dict], lens: dict) -> tuple[dict, list[str]]:
    """前照灯の取付位置（W05 の Att_Headlamp）が、素材のレンズの前面の前 max_gap_m 以内で、レンズの高さにあるか（W09R-D の M06）。
    レンズの前面は素材の仕上げの検査の、x = 0 の断面（z ごとの最も前の y。素材のローカル、Blender の軸）から補間する。"""
    loc = to_local(asset_chain, to_world(att_chain, (0.0, 0.0, 0.0)))
    x, y, z = loc[0], loc[2], loc[1]  # Blender の軸
    prof = sorted(lens["front_profile"])
    front = None
    for (z0, y0), (z1, y1) in zip(prof, prof[1:]):
        if z0 <= z <= z1:
            front = y0 + (y1 - y0) * (z - z0) / (z1 - z0)
    row = {"slot": lens["slot"], "local_blender": [round(x, 4), round(y, 4), round(z, 4)],
           "lens_front_y": None if front is None else round(front, 4), "gap_m": None if front is None else round(y - front, 4)}
    problems = []
    lo, hi = lens["lens_z_m"]
    if abs(x) > TOL_M or not lo <= z <= hi or front is None:
        problems.append(f"{lens['slot']}: not at the lens (local {row['local_blender']}, lens z {lo}-{hi})")
    elif not 0.0 < y - front <= lens["max_gap_m"]:
        problems.append(f"{lens['slot']}: {y - front:+.4f} m from the lens front (expected in front, within {lens['max_gap_m']} m)")
    return row, problems


def _clip_slab(poly: list[tuple[float, float, float]], lo: float, hi: float) -> list[tuple[float, float, float]]:
    """(a, u, v) の多角形を lo <= a <= hi で切り取る（Sutherland–Hodgman）。"""
    for keep in (lambda q: q[0] - lo, lambda q: hi - q[0]):
        out = []
        for i, cur in enumerate(poly):
            prev = poly[i - 1]
            dc, dp = keep(cur), keep(prev)
            if dc >= 0:
                if dp < 0:
                    t = dp / (dp - dc)
                    out.append(tuple(prev[k] + (cur[k] - prev[k]) * t for k in range(3)))
                out.append(cur)
            elif dp >= 0:
                t = dp / (dp - dc)
                out.append(tuple(prev[k] + (cur[k] - prev[k]) * t for k in range(3)))
        poly = out
        if not poly:
            return []
    return poly


def _dist_to_polygon_2d(pts: list[tuple[float, float]]) -> float:
    """原点から凸多角形（面の上の 2 次元、退化して線分・点でもよい）までの距離。中にあれば 0。"""
    n = len(pts)
    if n >= 3:
        cross = [pts[i][0] * pts[(i + 1) % n][1] - pts[i][1] * pts[(i + 1) % n][0] for i in range(n)]
        area2 = sum(cross)
        if abs(area2) > 1e-12 and all(c * area2 >= -1e-12 for c in cross):
            return 0.0
    best = math.inf
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        ll = dx * dx + dy * dy
        t = 0.0 if ll < 1e-18 else max(0.0, min(1.0, -(x0 * dx + y0 * dy) / ll))
        best = min(best, math.hypot(x0 + dx * t, y0 + dy * t))
    return best


def check_dial_hands(hands: list[dict], dial_chain: list[dict], dial_mesh: dict, centre: list[float], axis: list[float]) -> tuple[list[dict], list[str]]:
    """時計の針が素材の文字盤の前で回るか（W09R-E の M07）。centre は文字盤の中心、axis は文字盤の面の前向き（どちらも世界）。

    hands は針ごとに {"pivot": 名前, "pivot_chain", "hand_chain", "mesh"}（mesh は地区の宣言の針のメッシュ、ローカル）。
    - 回転軸: 回転軸の Slot の原点が、文字盤の中心を通る軸の上（軸からの距離 TOL_M 以内）で、文字盤の面より前。回転軸の Slot と
      針の Slot の前方（ローカルの +Z。W06 の針の回転軸）が文字盤の軸と平行で、針の Slot の原点が回転軸の Slot の原点にある
      （PR #55 の GPT のレビュー: 回転軸の Slot だけを見ると、針の Slot がずれた・傾いた状態を合格にした）
    - めり込み: 針の頂点の、軸に沿った前後の範囲（後ろの面〜前の面）と、軸からの最も遠い距離（針が回る半径）を求める。素材の
      三角形を前後の範囲で切り取り、残りを文字盤の面へ移した形が、回る半径の円と重ならない（針は軸のまわりに 360° 回るので、
      回した位置のどこでもめり込まない。三角形の頂点などの点だけで選ぶと、大きな三角形が円を横切るのを見落とす。PR #55 の
      GPT のレビュー）。前後の範囲より後ろにあり、面へ移した形が円と重なる三角形のうち最も前の物と、針の後ろの面の隙間を返す
    """
    ref = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.9 else (0.0, 1.0, 0.0)
    e1 = [ref[1] * axis[2] - ref[2] * axis[1], ref[2] * axis[0] - ref[0] * axis[2], ref[0] * axis[1] - ref[1] * axis[0]]
    n1 = math.sqrt(sum(c * c for c in e1))
    e1 = [c / n1 for c in e1]
    e2 = [axis[1] * e1[2] - axis[2] * e1[1], axis[2] * e1[0] - axis[0] * e1[2], axis[0] * e1[1] - axis[1] * e1[0]]

    def auv(p) -> tuple[float, float, float]:
        d = [p[i] - centre[i] for i in range(3)]
        return (sum(d[i] * axis[i] for i in range(3)), sum(d[i] * e1[i] for i in range(3)), sum(d[i] * e2[i] for i in range(3)))

    def forward(chain: list[dict]) -> list[float]:
        o, f = to_world(chain, (0.0, 0.0, 0.0)), to_world(chain, (0.0, 0.0, 1.0))
        n = math.sqrt(sum((f[i] - o[i]) ** 2 for i in range(3))) or 1.0
        return [(f[i] - o[i]) / n for i in range(3)]

    wp = [auv(to_world(dial_chain, v)) for v in dial_mesh["vertices"]]
    tris = [(wp[a], wp[b], wp[c]) for a, b, c in dial_mesh["triangles"]]
    rows, problems = [], []
    for h in hands:
        po = to_world(h["pivot_chain"], (0.0, 0.0, 0.0))
        along, pu, pv = auv(po)
        radial = math.hypot(pu, pv)
        hand_off = dist(to_world(h["hand_chain"], (0.0, 0.0, 0.0)), po)
        tilt = {k: sum(fw[i] * axis[i] for i in range(3)) for k, fw in (("pivot", forward(h["pivot_chain"])), ("hand", forward(h["hand_chain"])))}
        hv = [auv(to_world(h["hand_chain"], v)) for v in h["mesh"]["vertices"]]
        rear, front = min(q[0] for q in hv), max(q[0] for q in hv)
        reach = max(math.hypot(q[1], q[2]) for q in hv)
        inside, behind, near = 0, [], 0
        for tri in tris:
            amin, amax = min(q[0] for q in tri), max(q[0] for q in tri)
            if amin > front:
                continue
            if any(all(q[k] > reach for q in tri) or all(q[k] < -reach for q in tri) for k in (1, 2)):
                continue  # 面へ移した形の外接箱が円の外
            if amax < rear:
                if _dist_to_polygon_2d([(q[1], q[2]) for q in tri]) <= reach:
                    near += 1
                    behind.append(amax)
                continue
            clipped = _clip_slab(list(tri), rear, front)
            if clipped and _dist_to_polygon_2d([(q[1], q[2]) for q in clipped]) <= reach:
                inside += 1
        gap = rear - max(behind) if behind else None
        row = {"pivot": h["pivot"], "pivot_off_axis_m": round(radial, 4), "pivot_in_front_of_dial_centre_m": round(along, 4),
               "hand_origin_off_pivot_m": round(hand_off, 4), "axis_alignment": {k: round(v, 6) for k, v in tilt.items()},
               "hand_rear_m": round(rear, 4), "hand_front_m": round(front, 4), "reach_m": round(reach, 4),
               "triangles_behind_within_reach": near, "triangles_in_hand_slab": inside, "gap_to_dial_m": None if gap is None else round(gap, 4)}
        rows.append(row)
        if radial > TOL_M:
            problems.append(f"{h['pivot']}: {radial:.4f} m off the dial centre axis")
        if along <= 0.0:
            problems.append(f"{h['pivot']}: not in front of the dial face ({along:+.4f} m)")
        if hand_off > TOL_M:
            problems.append(f"{h['pivot']}: the hand is {hand_off:.4f} m off its pivot")
        bad_tilt = [k for k, v in tilt.items() if v < 1.0 - 1e-3]
        if bad_tilt:
            problems.append(f"{h['pivot']}: {bad_tilt} forward is not parallel to the dial axis")
        if inside:
            problems.append(f"{h['pivot']}: {inside} triangles of the dial are inside the swept hand ({rear:.4f}..{front:.4f} m)")
        elif gap is None:
            problems.append(f"{h['pivot']}: no dial surface behind the hand")
    return rows, problems


def _descendants(node: dict):
    for c in node.get("children") or []:
        yield c
        yield from _descendants(c)


def _same_transform(a: dict, b: dict) -> bool:
    return all(abs(float(a[f][k]) - float(b[f][k])) < 1e-6 for f, keys in (("position", "xyz"), ("rotation", "xyzw"), ("scale", "xyz")) for k in keys)


def check_rendering(chain: list[dict], index: dict, emissive: bool = False) -> list[str]:
    """素材の Slot（chain の最後）が描画されるか: 祖先を含めて有効、MeshRenderer が同じ Slot の StaticMesh と、
    色の画像（URL のある StaticTexture2D）を持つ材質を参照する。emissive なら発光の画像（EmissiveMap）も確かめる。"""
    problems = []
    node = chain[-1]
    inactive = [n["name"] for n in chain if n.get("isActive") is False]
    if inactive:
        problems.append(f"inactive Slot on the path: {inactive}")
    renderer, mesh = component(node, "MeshRenderer"), component(node, "StaticMesh")
    if member(renderer, "Enabled") is not True:
        problems.append(f"{node['name']}: MeshRenderer.Enabled is {member(renderer, 'Enabled')!r}")
    if mesh is None or member(renderer, "Mesh") != mesh["id"] or not member(mesh, "URL"):
        problems.append(f"{node['name']}: MeshRenderer does not use this Slot's StaticMesh with a URL")
    materials = member(renderer, "Materials") or []
    if not materials:
        problems.append(f"{node['name']}: MeshRenderer has no material")
    for mid in materials:
        mat = index.get(mid, (None, None))[0] if mid else None
        tex = index.get(member(mat, "AlbedoTexture") or "", (None, None))[0]
        if mat is None or not mat.get("type", "").endswith("PBS_Metallic") or tex is None or not member(tex, "URL"):
            problems.append(f"{node['name']}: material {mid!r} has no albedo texture with a URL")
        elif emissive:
            etex = index.get(member(mat, "EmissiveMap") or "", (None, None))[0]
            if etex is None or not member(etex, "URL"):
                problems.append(f"{node['name']}: material {mid!r} has no emissive map with a URL")
    return problems


def check_one(root: dict, meshy_id: str, rep: dict, inp: dict) -> dict:
    problems: list[str] = []
    out: dict = {"meshy_id": meshy_id, "visual_root": rep["visual_root_path"], "bundle": inp["bundle"]}
    rel_parts = tuple(rep["visual_root_path"].split("/")[1:])  # Root を除き、W08 の root の名前から
    vr_chain = find_path(root, rel_parts)
    if vr_chain is None:
        return {**out, "problems": [f"visual_root not found: {rep['visual_root_path']}"]}
    vr = vr_chain[-1]
    m_chain = find_path(root, rel_parts + (inp["bundle_root_name"], rep["asset_id"]))
    if m_chain is None:
        return {**out, "problems": [f"{inp['bundle_root_name']}/{rep['asset_id']} not found under the visual_root"]}
    index = component_index(root)
    proxy_yaw = inp["hint_deg"] - rep["rotation_z_deg"]  # replacements.py の回転の定義

    # 位置（データの原点と、データの向きで置いた外接箱）
    vr_live = to_world(vr_chain, (0.0, 0.0, 0.0))
    vr_exp = b2r(inp["frame_origin_world"])
    out["front_source"] = inp.get("hint_source", "received.json placement_hint.rotation_z_deg")
    out["visual_root_world"] = {"live": [round(v, 4) for v in vr_live], "expected": vr_exp, "diff_m": round(dist(vr_live, vr_exp), 4)}
    if dist(vr_live, vr_exp) > TOL_M:
        problems.append(f"visual_root is {dist(vr_live, vr_exp):.4f} m away from frame_origin_world")
    origin_exp = [vr_exp[i] + b2r(rz(proxy_yaw, rep["position_local"]))[i] for i in range(3)]
    # 外接箱は素材のすべてのメッシュ（素材の Slot とその子孫、可動部品の宣言の部品）を合わせた物（W09R-A: M01 はメッシュが
    # 子のアーチと、motion_root の下の門扉 2 枚にある。アセット一覧の bounds_local は開いた門扉を含む）
    placeholder_parts = rel_parts[:-1]
    meshes = inp.get("meshes") or [{"path": [], "vertices": inp["vertices"]}]
    main_meshes, part_meshes = [], []
    for mesh in meshes:
        chain = find_path(root, rel_parts + (inp["bundle_root_name"], rep["asset_id"], *mesh["path"]))
        if chain is None:
            problems.append(f"mesh Slot {'/'.join(mesh['path']) or rep['asset_id']} not found")
        else:
            main_meshes.append((chain, mesh["vertices"]))
    moving = inp.get("moving_parts") or {}
    part_chains: dict[str, dict] = {}
    for part_id, mp in moving.items():
        mr_chain = find_path(root, placeholder_parts + (mp["motion_root"],))
        p_chain = find_path(root, placeholder_parts + (mp["motion_root"], mp["bundle_root_name"], part_id))
        if mr_chain is None or p_chain is None:
            problems.append(f"{mp['motion_root']}/{mp['bundle_root_name']}/{part_id} not found")
            continue
        part_chains[part_id] = {"motion_root": mr_chain, "part": p_chain, "meshes": []}
        for mesh in mp["meshes"]:
            chain = find_path(root, placeholder_parts + (mp["motion_root"], mp["bundle_root_name"], part_id, *mesh["path"]))
            if chain is None:
                problems.append(f"mesh Slot {part_id}/{'/'.join(mesh['path'])} not found")
            else:
                part_chains[part_id]["meshes"].append((mesh, chain))
                part_meshes.append((chain, mesh["vertices"]))
    if not main_meshes:
        out["problems"] = problems + ["no mesh of the finished asset was found"]
        return out
    boxes = [mesh_bounds_world(c, v) for c, v in main_meshes + part_meshes]
    lo = [min(b[0][i] for b in boxes) for i in range(3)]
    hi = [max(b[1][i] for b in boxes) for i in range(3)]
    elo, ehi = expected_bounds(inp["bounds_local"], inp["hint_deg"], origin_exp)
    bdiff = max(max(abs(lo[i] - elo[i]), abs(hi[i] - ehi[i])) for i in range(3))
    out["bounds_world"] = {"live": {"min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi]},
                           "expected": {"min": [round(v, 4) for v in elo], "max": [round(v, 4) for v in ehi]},
                           "size_live": [round(hi[i] - lo[i], 4) for i in range(3)], "max_diff_m": round(bdiff, 4)}
    if bdiff > TOL_M:
        problems.append(f"bounds differ by {bdiff:.4f} m")

    # 正面（拡縮を含む完全な変換）と鏡像
    o, f = to_world(m_chain, (0.0, 0.0, 0.0)), to_world(m_chain, (0.0, 0.0, 1.0))
    n = math.sqrt(sum((f[i] - o[i]) ** 2 for i in range(3))) or 1.0
    fwd_live = [(f[i] - o[i]) / n for i in range(3)]
    fwd_exp = b2r(rz(inp["hint_deg"], [0.0, 1.0, 0.0]))
    out["front"] = {"live": [round(v, 4) for v in fwd_live], "expected": [round(v, 4) for v in fwd_exp], "diff": round(dist(fwd_live, fwd_exp), 4)}
    if dist(fwd_live, fwd_exp) > 1e-3:
        problems.append("front direction differs")
    on_paths = {id(x): x for c in [m_chain, *(c for c, _ in main_meshes + part_meshes)] for x in c}
    mirrored = [x["name"] for x in on_paths.values() if any(float(x["scale"][k]) <= 0 for k in "xyz")]
    if mirrored:
        problems.append(f"non-positive scale on the path: {mirrored}")

    # 可動部品（W09R-A）: 仮モデルの motion_root の原点が素材の蝶番にあり、その回転が開いた形（閉 0° からの角度）で、
    # 部品が蝶番の位置に開いた形で置かれている。期待値はアセット一覧の leaves と placement_hint から求める
    moving_out = {}
    for part_id, mp in moving.items():
        if part_id not in part_chains:
            continue
        mr_chain, p_chain = part_chains[part_id]["motion_root"], part_chains[part_id]["part"]
        hinge_exp = [origin_exp[i] + b2r(rz(inp["hint_deg"], mp["pivot_local"]))[i] for i in range(3)]
        row: dict = {"motion_root": mp["motion_root"], "hinge_expected": [round(v, 4) for v in hinge_exp],
                     "open_deg_from_closed": mp["placed_deg"] - mp["closed_deg"]}
        for label, chain, yaw in (("motion_root", mr_chain, proxy_yaw + mp["placed_deg"] - mp["closed_deg"]),
                                  ("part", p_chain, inp["hint_deg"] + mp["placed_deg"])):
            o2, f2 = to_world(chain, (0.0, 0.0, 0.0)), to_world(chain, (0.0, 0.0, 1.0))
            n2 = math.sqrt(sum((f2[i] - o2[i]) ** 2 for i in range(3))) or 1.0
            fwd2 = [(f2[i] - o2[i]) / n2 for i in range(3)]
            fexp2 = b2r(rz(yaw, [0.0, 1.0, 0.0]))
            row[label] = {"origin_world": [round(v, 4) for v in o2], "origin_diff_m": round(dist(o2, hinge_exp), 4),
                          "front": [round(v, 4) for v in fwd2], "front_expected": [round(v, 4) for v in fexp2], "front_diff": round(dist(fwd2, fexp2), 4)}
            if dist(o2, hinge_exp) > TOL_M:
                problems.append(f"{part_id}: {label} origin is {dist(o2, hinge_exp):.4f} m away from the hinge")
            if dist(fwd2, fexp2) > 1e-3:
                problems.append(f"{part_id}: {label} is not in the opened pose")
        # 部品ごとの外接箱（PR #52 の GPT のレビュー）: 全体の外接箱はアーチともう一方の門扉で決まるので、門扉の縮尺・形の
        # 誤りを見落とす。部品のメッシュの頂点を、データの蝶番・向き（拡縮なし）で置いた外接箱と比べる。部品の宣言に
        # メッシュが無ければ、検査の対象から消えないように失敗にする
        if not mp["meshes"]:
            problems.append(f"{part_id}: the part declaration has no mesh to check")
        row["bounds_world"] = []
        for mesh, chain in part_chains[part_id]["meshes"]:
            if mesh["path"]:
                problems.append(f"{part_id}: mesh Slot {'/'.join(mesh['path'])} below the part is not supported by the check")
                continue
            plo, phi = mesh_bounds_world(chain, mesh["vertices"])
            pts = [[hinge_exp[i] + b2r(rz(inp["hint_deg"] + mp["placed_deg"], [v["position"]["x"], v["position"]["z"], v["position"]["y"]]))[i]
                    for i in range(3)] for v in mesh["vertices"]]
            elo2, ehi2 = [min(q[i] for q in pts) for i in range(3)], [max(q[i] for q in pts) for i in range(3)]
            pdiff = max(max(abs(plo[i] - elo2[i]), abs(phi[i] - ehi2[i])) for i in range(3))
            row["bounds_world"].append({"slot": chain[-1]["name"], "live": {"min": [round(v, 4) for v in plo], "max": [round(v, 4) for v in phi]},
                                        "expected": {"min": [round(v, 4) for v in elo2], "max": [round(v, 4) for v in ehi2]}, "max_diff_m": round(pdiff, 4)})
            if pdiff > TOL_M:
                problems.append(f"{part_id}: {chain[-1]['name']} bounds differ by {pdiff:.4f} m")
        moving_out[part_id] = row
    if moving:
        out["moving_parts"] = moving_out

    # 描画
    renderers = {}
    hide_scope = [vr, *_descendants(vr)]
    for part in part_chains.values():
        hide_scope += [part["motion_root"][-1], *_descendants(part["motion_root"][-1])]
    # visual_root の兄弟で、地区の持ち主が差し替えのときに隠すと書いた物（W09R-E の M07 の仮の文字盤。replacements の
    # owner_hide_on_replacement と同じアセット一覧の値）
    owner_hide = set((inp["placeholder_asset"].get("replacement_slot") or {}).get("hide_on_replacement") or [])
    hide_scope += [x for x in vr_chain[-2].get("children") or [] if x["name"] in owner_hide]
    for name in rep["hide"]:
        node = next((x for x in hide_scope if x["name"] == name), None)
        enabled = member(component(node, "MeshRenderer"), "Enabled")
        renderers[name] = enabled
        if enabled is not False:
            problems.append(f"{name}: MeshRenderer.Enabled is {enabled!r}, expected False")
    for chain, _ in main_meshes + part_meshes:
        render_problems = check_rendering(chain, index, emissive=bool(rep.get("emissive")))
        renderers[chain[-1]["name"]] = not render_problems
        problems.extend(render_problems)
    out["renderers_enabled"] = renderers

    # 取付位置（データの原点と pivot_local）
    asset = inp["placeholder_asset"]
    attach = []
    for part in asset["parts"]:
        if part["role"] != "attachment_point":
            continue
        node_chain = next((chain_for(root, p) for p in _paths_named(vr_chain[-2], part["part_id"], tuple(x["name"] for x in vr_chain[:-1]))), None)
        if node_chain is None:
            problems.append(f"attachment {part['part_id']} not found")
            continue
        live = to_world(node_chain, (0.0, 0.0, 0.0))
        exp = [b2r(asset["origin_world"])[i] + b2r(rz(proxy_yaw, pivot_in_asset(asset, part["part_id"])))[i] for i in range(3)]
        d = dist(live, exp)
        attach.append({"part": part["part_id"], "live_world": [round(v, 4) for v in live], "expected": [round(v, 4) for v in exp], "diff_m": round(d, 4)})
        if d > TOL_M:
            problems.append(f"attachment {part['part_id']} is {d:.4f} m off")
    out["attachment_points"] = attach

    # 組み立て（W09R-D の M05）: この行の素材の原点と、assembly_with の行の素材の原点の差が、アセット一覧の pivot_local の差を
    # 素材の向きで回した物と 1 cm 以内（屋根が柱の上に乗っている。それぞれの行の外接箱の検査は、仮モデルの間の高さの誤りを見落とす）
    asm = inp.get("assembly")
    if asm:
        other = find_path(root, tuple(asm["other_path"]))
        if other is None:
            problems.append(f"assembly: {'/'.join(asm['other_path'])} not found")
        else:
            live = [a - b for a, b in zip(to_world(m_chain, (0.0, 0.0, 0.0)), to_world(other, (0.0, 0.0, 0.0)))]
            exp = b2r(rz(inp["hint_deg"], asm["offset_local"]))
            out["assembly"] = {"with": asm["with"], "live_offset": [round(v, 4) for v in live], "expected": [round(v, 4) for v in exp],
                               "diff_m": round(dist(live, exp), 4)}
            if dist(live, exp) > TOL_M:
                problems.append(f"assembly with {asm['with']} differs by {dist(live, exp):.4f} m")

    # 支柱（W09R-D の M05 の屋根）: 地区の支柱が屋根の下面に届き、先が屋根の殻の中にある
    poles = inp.get("poles")
    if poles:
        pole_chain = next((chain_for(root, p) for p in _paths_named(vr_chain[-2], poles["slot"], tuple(x["name"] for x in vr_chain[:-1]))), None)
        canopy_chain = find_path(root, rel_parts + (inp["bundle_root_name"], rep["asset_id"], *poles["canopy_path"]))
        if pole_chain is None or canopy_chain is None:
            problems.append(f"poles: {poles['slot']} or the canopy mesh not found")
        else:
            rows_p, probs_p = check_poles(pole_chain, poles["pole_mesh"], canopy_chain, poles["canopy_mesh"])
            shown = check_measured_mesh_is_shown(pole_chain, poles["pole_applied"]) + check_measured_mesh_is_shown(canopy_chain, poles["canopy_applied"])
            out["poles"] = {"slot": poles["slot"], "district_bundle": poles.get("district_bundle"), "poles": rows_p,
                            "measured_meshes_shown": not shown}
            problems.extend(shown)
            if len(rows_p) != 8:
                problems.append(f"poles: {len(rows_p)} poles found, expected 8")
            problems.extend(probs_p)

    # 前照灯（W09R-D の M06）: 地区の取付位置が素材のレンズの前にある
    lens = inp.get("lens_attachment")
    if lens:
        att_chain = next((chain_for(root, p) for p in _paths_named(vr_chain[-2], lens["slot"], tuple(x["name"] for x in vr_chain[:-1]))), None)
        if att_chain is None:
            problems.append(f"{lens['slot']} not found")
        else:
            row_l, probs_l = check_lens_attachment(att_chain, m_chain, lens)
            out["lens_attachment"] = row_l
            problems.extend(probs_l)

    # 針（W09R-E の M07）: 地区の時計の針が、素材の文字盤の中心の軸の上で、文字盤にめり込まずに回るか
    dh = inp.get("dial_hands")
    if dh:
        district_node, district_prefix = vr_chain[-2], tuple(x["name"] for x in vr_chain[:-1])
        dial_chain = find_path(root, rel_parts + (inp["bundle_root_name"], rep["asset_id"], *dh["dial_path"]))
        centre = [origin_exp[i] + b2r(rz(inp["hint_deg"], dh["centre_local"]))[i] for i in range(3)]
        axis = b2r(rz(inp["hint_deg"], [0.0, 1.0, 0.0]))
        hands, shown = [], []
        for pivot, hand in dh["hands"].items():
            pchain = next((chain_for(root, p) for p in _paths_named(district_node, pivot, district_prefix)), None)
            hchain = None if pchain is None else next(
                (chain_for(root, p) for p in _paths_named(pchain[-1], hand["hand"], tuple(x["name"] for x in pchain))), None)
            if hchain is None:
                problems.append(f"dial hands: {pivot}/{hand['hand']} not found")
                continue
            hands.append({"pivot": pivot, "pivot_chain": pchain, "hand_chain": hchain, "mesh": hand["mesh"]})
            shown += check_measured_mesh_is_shown(hchain, hand["applied"])
        if dial_chain is None:
            problems.append("dial hands: the finished asset's dial mesh not found")
        else:
            shown += check_measured_mesh_is_shown(dial_chain, dh["dial_applied"])
            rows_h, probs_h = check_dial_hands(hands, dial_chain, dh["dial_mesh"], centre, axis)
            out["dial_hands"] = {"centre_world": [round(v, 4) for v in centre], "axis_world": [round(v, 4) for v in axis],
                                 "district_bundle": dh["district_bundle"], "hands": rows_h, "measured_meshes_shown": not shown}
            problems.extend(probs_h)
        problems.extend(shown)

    # 入口（W09R-B）: 地区の扉の蝶番と玄関ホールが、素材の開口に合っているか
    ent = inp.get("entrance")
    if ent:
        front_world = b2r(rz(inp["hint_deg"], [0.0, 1.0, 0.0]))
        inward = [-v for v in front_world]  # 建物の奥（素材の正面の逆向き）
        district_node, district_prefix = vr_chain[-2], tuple(x["name"] for x in vr_chain[:-1])
        ent_out: dict = {"hinges": []}

        def facing(chain: list[dict]) -> float:
            o3, f3 = to_world(chain, (0.0, 0.0, 0.0)), to_world(chain, (0.0, 0.0, 1.0))
            n3 = math.sqrt(sum((f3[i] - o3[i]) ** 2 for i in range(3))) or 1.0
            return sum((f3[i] - o3[i]) / n3 * inward[i] for i in range(3))

        def non_unit_scale(nodes: list[dict]) -> list[str]:
            return [x["name"] for x in nodes if any(abs(float(x["scale"][k]) - 1.0) > 1e-4 for k in "xyz")]

        scaled: set[str] = set()
        for slot_name, local in ent["hinges"].items():
            chain = next((chain_for(root, p) for p in _paths_named(district_node, slot_name, district_prefix)), None)
            if chain is None:
                problems.append(f"entrance {slot_name} not found")
                continue
            live = to_world(chain, (0.0, 0.0, 0.0))
            exp = [origin_exp[i] + b2r(rz(inp["hint_deg"], local))[i] for i in range(3)]
            face = facing(chain)
            ent_out["hinges"].append({"slot": slot_name, "live_world": [round(v, 4) for v in live], "expected": [round(v, 4) for v in exp],
                                      "diff_m": round(dist(live, exp), 4), "facing_inward": round(face, 4)})
            if dist(live, exp) > TOL_M:
                problems.append(f"entrance {slot_name} is {dist(live, exp):.4f} m away from the opening's hinge line")
            if face < 1.0 - 1e-3:
                problems.append(f"entrance {slot_name}: the closed door is not in the wall plane (facing {face:.4f})")
            scaled.update(non_unit_scale(chain[:-1] + [chain[-2], *_descendants(chain[-2])]))
        chain = next((chain_for(root, p) for p in _paths_named(district_node, ent["hall"], district_prefix)), None)
        if chain is None:
            problems.append(f"entrance {ent['hall']} not found")
        else:
            live = to_world(chain, (0.0, 0.0, 0.0))
            centre = [origin_exp[i] + b2r(rz(inp["hint_deg"], ent["opening_centre_floor_local"]))[i] for i in range(3)]
            exp = [centre[i] - front_world[i] * ent["hall_depth_m"] for i in range(3)]
            face = facing(chain)
            ent_out["hall"] = {"slot": ent["hall"], "live_world": [round(v, 4) for v in live], "expected": [round(v, 4) for v in exp],
                               "diff_m": round(dist(live, exp), 4), "facing_inward": round(face, 4)}
            if dist(live, exp) > TOL_M:
                problems.append(f"entrance {ent['hall']} is {dist(live, exp):.4f} m away from behind the opening")
            if face < 1.0 - 1e-3:
                problems.append(f"entrance {ent['hall']} does not face into the building (facing {face:.4f})")
            scaled.update(non_unit_scale(chain[:-1] + [chain[-1], *_descendants(chain[-1])]))
        ent_out["non_unit_scale"] = sorted(scaled)
        if scaled:
            problems.append(f"entrance: non-unit scale on {sorted(scaled)}")
        out["entrance"] = ent_out

    # 当たり判定
    fixed_name = f"{rep['visual_root']}_FixedCollision"
    fixed = next((x for x in vr_chain[-2].get("children") or [] if x["name"] == fixed_name), None)
    # 素材のバンドルの root（m_chain[-2]）自身とその子孫（GPT のレビュー、PR #51: root 自身を見落としていた）
    bundle_root = m_chain[-2]
    out["colliders_under_finished_asset"] = [x["name"] for x in [bundle_root, *_descendants(bundle_root)] if component(x, "MeshCollider")]
    # 可動部品には当たり判定を付けない（動く部品。W09R-A の M01 の門扉）
    part_roots = [part["part"][-2] for part in part_chains.values()]
    out["colliders_under_moving_parts"] = [x["name"] for r in part_roots for x in [r, *_descendants(r)] if component(x, "MeshCollider")]
    if out["colliders_under_moving_parts"]:
        problems.append(f"colliders under the moving parts: {out['colliders_under_moving_parts']}")
    if rep.get("collision", True) == "finished":
        # 素材のメッシュが当たり判定（W09R-B の M03）: 仮モデルの FixedCollision は Slot を残して MeshCollider を止め、素材の
        # すべてのメッシュの Slot に MeshCollider がある。素材のバンドルの中のそれ以外の Slot に当たり判定は無い
        fcol = component(fixed, "MeshCollider")
        out["fixed_collision"] = {"slot": fixed_name, "exists": fixed is not None, "collider_enabled": member(fcol, "Enabled")}
        if fixed is None or fcol is None:
            problems.append(f"{fixed_name} or its MeshCollider is missing (expected to be kept and disabled)")
        elif member(fcol, "Enabled") is not False:
            problems.append(f"{fixed_name}: MeshCollider.Enabled is {member(fcol, 'Enabled')!r}, expected False")
        mesh_slots = {id(c[-1]) for c, _ in main_meshes}
        rows = []
        for chain, _ in main_meshes:
            node = chain[-1]
            col, mesh = component(node, "MeshCollider"), component(node, "StaticMesh")
            offset = member(col, "Offset")
            ok = {"collider_enabled": member(col, "Enabled") is True,
                  "static_character_collider": member(col, "Type") == "Static" and member(col, "CharacterCollider") is True,
                  "uses_own_static_mesh": mesh is not None and col is not None and member(col, "Mesh") == mesh["id"],
                  "zero_offset": isinstance(offset, dict) and all(abs(float(offset.get(k, 1.0))) < 1e-6 for k in "xyz")}
            rows.append({"slot": node["name"], **ok})
            bad = [k for k, v in ok.items() if not v]
            if bad:
                problems.append(f"{node['name']}: finished-asset collider fails {bad}")
        out["finished_colliders"] = rows
        extra = [x["name"] for x in [bundle_root, *_descendants(bundle_root)] if component(x, "MeshCollider") and id(x) not in mesh_slots]
        if extra:
            problems.append(f"colliders on non-mesh Slots under the finished asset: {extra}")
        out["problems"] = problems
        return out
    if rep.get("collision", True) is False:
        # 空を飛ぶ・動く物: 当たり判定を付けない方針。仮モデルに FixedCollision があるのに False と書いたなら設定の誤り
        out["fixed_collision"] = {"slot": fixed_name, "expected": False, "exists": fixed is not None}
        if fixed is not None:
            problems.append(f"{fixed_name} exists although the replacement is configured without collision")
        if out["colliders_under_finished_asset"]:
            problems.append(f"colliders under the finished asset: {out['colliders_under_finished_asset']}")
        out["problems"] = problems
        return out
    collider, fmesh = component(fixed, "MeshCollider"), component(fixed, "StaticMesh")
    checks = {
        "exists": fixed is not None,
        "active": bool(fixed) and fixed.get("isActive") is not False,
        "same_transform_as_visual_root": bool(fixed) and _same_transform(fixed, vr),
        "collider_enabled": member(collider, "Enabled") is True,
        "static_character_collider": member(collider, "Type") == "Static" and member(collider, "CharacterCollider") is True,
        "uses_own_static_mesh": fmesh is not None and member(collider, "Mesh") == fmesh["id"],
        "same_mesh_as_visual_root": fmesh is not None and bool(member(fmesh, "URL")) and member(fmesh, "URL") == member(component(vr, "StaticMesh"), "URL"),
    }
    out["fixed_collision"] = {"slot": fixed_name, **checks}
    bad = [k for k, v in checks.items() if not v]
    if bad:
        problems.append(f"FixedCollision fails: {bad}")
    out["problems"] = problems
    return out


def _paths_named(node: dict, name: str, prefix: tuple[str, ...]):
    """node（prefix の最後の Slot）の下で name の Slot のパス（root からの名前のタプル）。"""
    def walk(n: dict, path: tuple[str, ...]):
        here = path + (n["name"],)
        if n["name"] == name:
            yield here
        for c in n.get("children") or []:
            yield from walk(c, here)

    for c in node.get("children") or []:
        yield from walk(c, prefix)


def check_counts(root: dict, w08_keys: dict, declared_by_meshy: dict[str, dict]) -> dict:
    """地区ごとに、実測の Slot・Component の数 = W08 の実測 + その地区のすべての差し替えの宣言の数。"""
    out = {}
    districts = sorted({REPLACEMENTS[m]["district"] for m in declared_by_meshy})
    for district in districts:
        node = chain_for(root, (root["name"], district))[-1]
        live = count_nodes(node)
        members = [m for m in declared_by_meshy if REPLACEMENTS[m]["district"] == district]
        exp = (w08_keys[district]["live_slots"] + sum(declared_by_meshy[m]["slots"] for m in members),
               w08_keys[district]["live_components"] + sum(declared_by_meshy[m]["components"] for m in members))
        out[district] = {"live": list(live), "expected": list(exp), "replacements": members, "ok": tuple(live) == exp}
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", required=True)
    parser.add_argument("--raw-out", required=True, help="生の観察の保存先（Git の外）")
    parser.add_argument("--output", required=True, help="要約の保存先（例 review/p2_meshy/live_checks.json）")
    parser.add_argument("--state-dir", type=Path, help="apply の state の置き場（既定は親の checkout の .resoloop/state）")
    args = parser.parse_args(argv)
    if args.state_dir:
        globals()["STATE_DIR"] = args.state_dir
    live = observe(args.url)
    Path(args.raw_out).write_text(json.dumps(live, ensure_ascii=False) + "\n", encoding="utf-8")
    root = live["data"]
    total_s, total_c = count_nodes(root)
    inputs = {m: load_inputs(m, r) for m, r in sorted(REPLACEMENTS.items())}
    rows = [check_one(root, m, REPLACEMENTS[m], inp) for m, inp in inputs.items()]
    counts = check_counts(root, _load("review/p2_static/live_checks.json")["keys"], {m: inp["declared"] for m, inp in inputs.items()})
    summary = {"root": "Root/" + root["name"], "tolerance_m": TOL_M, "root_live": {"slots": total_s, "components": total_c},
               "replacements": rows, "district_counts": counts,
               "ok": all(not r["problems"] for r in rows) and all(c["ok"] for c in counts.values())}
    Path(args.output).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": summary["ok"], "root_live": summary["root_live"], "problems": {r["meshy_id"]: r["problems"] for r in rows},
                      "district_counts": {k: v["ok"] for k, v in counts.items()}}, ensure_ascii=False))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
