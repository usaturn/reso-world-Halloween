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
"""

from __future__ import annotations

import argparse
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


def load_inputs(meshy_id: str, rep: dict) -> dict:
    """検査に使うデータ（実測ではない物）を読む。テストはこの dict を直接作る。"""
    bundle = latest_meshy_bundle(meshy_id)
    doc = json.loads((bundle / "p2m.apply.json").read_text(encoding="utf-8"))
    asset_slot = next(ch for ch in doc["children"] if ch["slot"]["name"] == rep["asset_id"])
    meshes = [{"path": list(path), "vertices": _vertices(bundle, doc, key)} for path, key in _mesh_slots(asset_slot)]
    received = next(a for a in _load("assets/meshy/received.json")["assets"] if a["row_id"] == meshy_id)
    ds, dc, auto = declared_counts(doc)
    manifest = _load(f"assets/manifest/{meshy_id}.json")["assets"][0]
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
    return {
        "bundle": bundle.relative_to(PROJECT_ROOT).as_posix(),
        "bundle_root_name": doc["slot"]["name"],
        "meshes": meshes,
        "bounds_local": manifest["bounds_local"],
        "hint_deg": hint_deg,
        "hint_source": hint_source,
        "frame_origin_world": placeholders[meshy_id]["frame_origin_world"],
        "placeholder_asset": next(a for a in _load(f"assets/manifest/{rep['district']}.json")["assets"] if a["asset_id"] == rep["placeholder"]),
        "moving_parts": moving,
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
        exp = [b2r(asset["origin_world"])[i] + b2r(rz(proxy_yaw, part["pivot_local"]))[i] for i in range(3)]
        d = dist(live, exp)
        attach.append({"part": part["part_id"], "live_world": [round(v, 4) for v in live], "expected": [round(v, 4) for v in exp], "diff_m": round(d, 4)})
        if d > TOL_M:
            problems.append(f"attachment {part['part_id']} is {d:.4f} m off")
    out["attachment_points"] = attach

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
    args = parser.parse_args(argv)
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
