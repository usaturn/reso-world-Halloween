"""W09R: Meshy の仕上げた素材に差し替えた仮モデルを、1 回の観察（resoloop hierarchy）から実測して検査する。

実行（プロジェクトのディレクトリ）:
    uv run python modeling/p2_meshy/verify_live.py --url ws://localhost:<PORT>/ \\
        --raw-out <Git の外の JSON> --output review/p2_meshy/live_checks.json

- 観察は W08 と同じ（modeling/p2_static/verify_live.py の observe）。生の出力（ResoniteLink の ID を含む）は --raw-out に置き、
  コミットしない。--output には ID と資産の URL を含まない要約だけを書く
- 検査（replacements.py の REPLACEMENTS の行ごと。docs/p2-meshy-replacement.md 5 章）
  - 仕上げた素材の外接箱: バンドルのメッシュの頂点を、観察した変換で世界に置いた外接箱と、アセット一覧（assets/manifest/<M>.json）の
    bounds_local を visual_root の位置と rotation_z_deg で置いた外接箱の差（1 cm 以内）
  - 正面: 素材の Slot の前方（ローカルの +Z）が、received.json の placement_hint.rotation_z_deg で回した +Y（Blender）と一致する
  - 描画: hide に書いた Slot の MeshRenderer が Enabled = false、素材の MeshRenderer が Enabled = true、材質に色の画像がある
  - 取付位置: 仮モデルのアセットの取付位置（地区のアセット一覧の attachment_point）が、アセットの root からの pivot_local の位置にある
  - 当たり判定: <visual_root>_FixedCollision があり、MeshCollider と、visual_root と同じメッシュの資産を参照する StaticMesh を持つ
  - 数: 地区の Slot・Component の数が、W08 の実測（review/p2_static/live_checks.json）に差し替えの宣言の数を足した値と一致する
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from modeling.p2_meshy.replacements import REPLACEMENTS  # noqa: E402
from modeling.p2_static.verify_live import (  # noqa: E402
    TOL_M,
    _vec,
    b2r,
    chain_for,
    count_nodes,
    declared_counts,
    dist,
    mesh_bounds_world,
    observe,
    qmul,
    qrot,
    to_world,
)


def _load(rel: str) -> dict:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def latest_meshy_bundle(meshy_id: str) -> Path:
    dirs = [d for d in sorted((PROJECT_ROOT / "exports" / "p2_meshy").glob(f"{meshy_id}-*")) if (d / "p2m.apply.json").is_file()]
    if not dirs:
        raise SystemExit(f"no exports/p2_meshy/{meshy_id}-*/p2m.apply.json")
    return dirs[-1]


def find_path(root: dict, path: tuple[str, ...]) -> list[dict] | None:
    try:
        return chain_for(root, path)
    except StopIteration:
        return None


def component(node: dict, short_type: str) -> dict | None:
    return next((c for c in node.get("components") or [] if c.get("type", "").endswith(f"FrooxEngine.{short_type}")), None)


def member(comp: dict | None, name: str):
    if comp is None:
        return None
    m = (comp.get("members") or {}).get(name) or {}
    return m.get("value", m.get("targetId"))


def world_rotation(chain: list[dict]) -> tuple:
    q = (0.0, 0.0, 0.0, 1.0)
    for n in chain:
        q = qmul(q, _vec(n["rotation"], "xyzw"))
    return q


def rz(deg: float, v: list[float]) -> list[float]:
    a = math.radians(deg)
    return [v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a), v[2]]


def expected_bounds(manifest_bounds: dict, deg: float, origin_resonite: tuple) -> tuple[list[float], list[float]]:
    """アセットのローカルの外接箱（Blender）を Z 軸まわりに deg 回し、Resonite の軸で origin に置いた外接箱。"""
    lo, hi = manifest_bounds["min"], manifest_bounds["max"]
    corners = [rz(deg, [x, y, z]) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    pts = [[origin_resonite[i] + b2r(c)[i] for i in range(3)] for c in corners]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def check_one(root: dict, meshy_id: str, rep: dict) -> dict:
    problems: list[str] = []
    out: dict = {"meshy_id": meshy_id, "visual_root": rep["visual_root_path"]}
    rel_parts = tuple(rep["visual_root_path"].split("/")[1:])  # Root を除き、W08 の root の名前から
    vr_chain = find_path(root, rel_parts)
    if vr_chain is None:
        return {**out, "problems": [f"visual_root not found: {rep['visual_root_path']}"]}
    vr = vr_chain[-1]
    vr_world = to_world(vr_chain, (0.0, 0.0, 0.0))

    # 仕上げた素材の Slot
    bundle = latest_meshy_bundle(meshy_id)
    doc = json.loads((bundle / "p2m.apply.json").read_text(encoding="utf-8"))
    m_root_name = doc["slot"]["name"]
    m_chain = find_path(root, rel_parts + (m_root_name, rep["asset_id"]))
    if m_chain is None:
        return {**out, "problems": [f"{m_root_name}/{rep['asset_id']} not found under the visual_root"]}
    asset_node = m_chain[-1]
    out["bundle"] = bundle.relative_to(PROJECT_ROOT).as_posix()

    # 外接箱
    mesh_key = next(c for c in next(ch for ch in doc["children"] if ch["slot"]["name"] == rep["asset_id"])["components"]
                    if c["type"] == "FrooxEngine.StaticMesh")["fields"]["URL"].removeprefix("$asset:")
    vertices = json.loads((bundle / doc["assets"][mesh_key]["source"]).read_text(encoding="utf-8"))["vertices"]
    lo, hi = mesh_bounds_world(m_chain, vertices)
    man = _load(f"assets/manifest/{meshy_id}.json")["assets"][0]
    elo, ehi = expected_bounds(man["bounds_local"], rep["rotation_z_deg"], vr_world)
    bdiff = max(max(abs(lo[i] - elo[i]), abs(hi[i] - ehi[i])) for i in range(3))
    out["bounds_world"] = {"live": {"min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi]},
                           "expected": {"min": [round(v, 4) for v in elo], "max": [round(v, 4) for v in ehi]},
                           "size_live": [round(hi[i] - lo[i], 4) for i in range(3)], "max_diff_m": round(bdiff, 4)}
    if bdiff > TOL_M:
        problems.append(f"bounds differ by {bdiff:.4f} m")

    # 正面（素材のローカルの +Z = Blender の +Y）
    received = next(a for a in _load("assets/meshy/received.json")["assets"] if a["row_id"] == meshy_id)
    hint_deg = received["decided"]["placement_hint"]["rotation_z_deg"]
    fwd_live = qrot(world_rotation(m_chain), (0.0, 0.0, 1.0))
    fwd_exp = b2r(rz(hint_deg, [0.0, 1.0, 0.0]))
    fdiff = dist(fwd_live, fwd_exp)
    out["front"] = {"live": [round(v, 4) for v in fwd_live], "expected": [round(v, 4) for v in fwd_exp], "diff": round(fdiff, 4)}
    if fdiff > 1e-3:
        problems.append("front direction differs")

    # 描画
    renderers = {}
    for name in rep["hide"]:
        node = next((n for n in [vr, *_descendants(vr)] if n["name"] == name), None)
        enabled = member(component(node, "MeshRenderer"), "Enabled") if node else None
        renderers[name] = enabled
        if enabled is not False:
            problems.append(f"{name}: MeshRenderer.Enabled is {enabled!r}, expected False")
    asset_enabled = member(component(asset_node, "MeshRenderer"), "Enabled")
    renderers[rep["asset_id"]] = asset_enabled
    if asset_enabled is not True:
        problems.append(f"{rep['asset_id']}: MeshRenderer.Enabled is {asset_enabled!r}")
    materials = [n for n in _descendants(m_chain[-2]) if component(n, "PBS_Metallic")]
    albedo = [member(component(n, "PBS_Metallic"), "AlbedoTexture") for n in materials]
    out["material"] = {"pbs_metallic": len(materials), "albedo_texture_set": all(albedo) and bool(albedo)}
    if not out["material"]["albedo_texture_set"]:
        problems.append("material has no AlbedoTexture")
    out["renderers_enabled"] = renderers

    # 取付位置（仮モデルのアセットの root から pivot_local の位置）
    district_man = _load(f"assets/manifest/{rep['district']}.json")
    asset = next(a for a in district_man["assets"] if a["asset_id"] == rep["placeholder"])
    ar_chain = find_path(root, tuple(rep["visual_root_path"].split("/")[1:-1]))
    attach = []
    for part in asset["parts"]:
        if part["role"] != "attachment_point":
            continue
        node_chain = next((chain_for(root, p) for p in _paths_named(root, part["part_id"])), None)
        if node_chain is None:
            problems.append(f"attachment {part['part_id']} not found")
            continue
        live = to_world(node_chain, (0.0, 0.0, 0.0))
        exp = to_world(ar_chain, b2r(part["pivot_local"]))
        d = dist(live, exp)
        attach.append({"part": part["part_id"], "live_world": [round(v, 4) for v in live], "expected": [round(v, 4) for v in exp], "diff_m": round(d, 4)})
        if d > TOL_M:
            problems.append(f"attachment {part['part_id']} moved {d:.4f} m")
    out["attachment_points"] = attach

    # 当たり判定
    fixed_name = f"{rep['visual_root']}_FixedCollision"
    fixed = next((n for n in vr_chain[-2].get("children") or [] if n["name"] == fixed_name), None)
    fixed_ok = bool(fixed and component(fixed, "MeshCollider") and member(component(fixed, "StaticMesh"), "URL") == member(component(vr, "StaticMesh"), "URL"))
    out["fixed_collision"] = {"slot": fixed_name, "mesh_collider": bool(fixed and component(fixed, "MeshCollider")), "same_mesh_as_visual_root": fixed_ok}
    if not fixed_ok:
        problems.append("FixedCollision is missing or does not use the visual_root mesh")
    asset_colliders = [n["name"] for n in _descendants(m_chain[-2]) if component(n, "MeshCollider")]
    out["colliders_under_finished_asset"] = asset_colliders

    # 数（地区の Slot・Component）
    district_node = chain_for(root, (root["name"], rep["district"]))[-1]
    live_s, live_c = count_nodes(district_node)
    w08 = _load("review/p2_static/live_checks.json")["keys"][rep["district"]]
    ds, dc, auto = declared_counts(doc)
    out["counts"] = {"district_live_slots": live_s, "district_live_components": live_c,
                     "w08_live": [w08["live_slots"], w08["live_components"]],
                     "replacement_declared": {"slots": ds, "components": dc, "auto_ai_generated_content": auto}}
    others = [m for m, r in REPLACEMENTS.items() if r["district"] == rep["district"] and m != meshy_id]
    if not others and (live_s, live_c) != (w08["live_slots"] + ds, w08["live_components"] + dc + auto):
        problems.append(f"district counts {live_s}/{live_c} != W08 {w08['live_slots']}/{w08['live_components']} + declared {ds}/{dc + auto}")
    out["problems"] = problems
    return out


def _descendants(node: dict):
    for c in node.get("children") or []:
        yield c
        yield from _descendants(c)


def _paths_named(root: dict, name: str):
    def walk(n: dict, path: tuple[str, ...]):
        here = path + (n["name"],)
        if n["name"] == name:
            yield here
        for c in n.get("children") or []:
            yield from walk(c, here)

    yield from walk(root, ())


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
    rows = [check_one(root, m, r) for m, r in sorted(REPLACEMENTS.items())]
    summary = {"root": "Root/" + root["name"], "tolerance_m": TOL_M, "root_live": {"slots": total_s, "components": total_c},
               "replacements": rows, "ok": all(not r["problems"] for r in rows)}
    Path(args.output).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": summary["ok"], "root_live": summary["root_live"], "problems": {r["meshy_id"]: r["problems"] for r in rows}}, ensure_ascii=False))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
