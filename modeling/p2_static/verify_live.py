"""W08: Resonite に apply した静的ワールドを、1 回の観察（resoloop hierarchy）から実測して検査する。

実行（プロジェクトのディレクトリ）:
    uv run python modeling/p2_static/verify_live.py --url ws://localhost:<PORT>/ \\
        --raw-out <Git の外の JSON> --output review/p2_static/live_checks.json

- 観察: resoloop hierarchy --under Root/HalloweenMagicalCarnival --depth 16 --json。生の出力（ResoniteLink の ID を含む）は
  --raw-out に置き、コミットしない。--output には ID を含まない要約だけを書く
- 世界座標: 観察したローカルの位置・回転・拡縮を、W08 の root Slot から順にかけて求める（root の親は Root）
- 検査（docs/p2-static-integration.md 8 章）
  - キーごとの Slot・Component の数と、宣言（exports/p2_static/<key>-*/p2.apply.json の最新）の数
  - .blend のオブジェクト（バンドルの Slot。Blender_Providers と FixedCollision を除く）がすべて同じ階層の名前で存在するか
  - 可動部品 78 個（review/overview/checks.json の motion_parts）の原点（Blender の pivot_world を (x, z, y) に直した値）との差
  - Meshy の仮モデル 9 行の位置、ランドマーク 5 つの建てた物の位置（checks.json の built_origin）との差
  - 当たり判定: MeshCollider の数（colliders.json）と、可動部品の下・取付位置に当たり判定が無いこと
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_PATH = "Root/HalloweenMagicalCarnival"
KEYS = ["world", "A_plaza", "B_mansion", "C_candy", "D_amusement", "E_forest"]
TOL_M = 0.01


def b2r(p: list[float]) -> list[float]:
    """Blender (x, y, z) -> Resonite (x, z, y)。"""
    return [p[0], p[2], p[1]]


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def qrot(q, v):
    x, y, z, w = q
    r = qmul(qmul(q, (v[0], v[1], v[2], 0.0)), (-x, -y, -z, w))
    return r[:3]


def _vec(d: dict, keys: str) -> tuple:
    return tuple(float(d[k]) for k in keys)


def world_transforms(node: dict, parent=((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0)), path=()):
    """(パスの名前のタプル, 世界の位置, 世界の回転, ノード) を順に返す。"""
    ppos, prot, pscl = parent
    lpos = _vec(node["position"], "xyz")
    lrot = _vec(node["rotation"], "xyzw")
    lscl = _vec(node["scale"], "xyz")
    scaled = (lpos[0] * pscl[0], lpos[1] * pscl[1], lpos[2] * pscl[2])
    r = qrot(prot, scaled)
    wpos = (ppos[0] + r[0], ppos[1] + r[1], ppos[2] + r[2])
    wrot = qmul(prot, lrot)
    wscl = (pscl[0] * lscl[0], pscl[1] * lscl[1], pscl[2] * lscl[2])
    here = path + (node["name"],)
    yield here, wpos, wrot, node
    for child in node.get("children") or []:
        yield from world_transforms(child, (wpos, wrot, wscl), here)


def count_nodes(node: dict) -> tuple[int, int]:
    slots, comps = 1, len(node.get("components") or [])
    for child in node.get("children") or []:
        s, c = count_nodes(child)
        slots += s
        comps += c
    return slots, comps


def declared_counts(doc: dict) -> tuple[int, int, int]:
    """宣言の Slot・Component の数と、resoloop が自動で足す AI_GeneratedContent の数（ownership root と ObjectRoot の Slot）。"""
    auto = 0

    def walk(n: dict, is_root: bool) -> tuple[int, int]:
        nonlocal auto
        comps = n.get("components") or []
        if is_root or any(c.get("type") == "FrooxEngine.ObjectRoot" for c in comps):
            auto += 1
        s, c = 1, len(comps)
        for ch in n.get("children") or []:
            ss, cc = walk(ch, False)
            s += ss
            c += cc
        return s, c

    s, c = walk({"components": doc.get("components"), "children": doc.get("children")}, True)
    return s, c, auto


def latest_bundle(key: str) -> Path:
    dirs = sorted((PROJECT_ROOT / "exports" / "p2_static").glob(f"{key}-*"))
    dirs = [d for d in dirs if (d / "p2.apply.json").is_file()]
    if not dirs:
        raise SystemExit(f"no exports/p2_static/{key}-*/p2.apply.json")
    return dirs[-1]


def bundle_names(doc: dict) -> list[tuple[str, ...]]:
    out = []

    def walk(n: dict, path: tuple[str, ...]):
        name = n["slot"]["name"]
        if name == "Blender_Providers" or name.endswith("_FixedCollision"):
            return
        here = path + (name,)
        out.append(here)
        for ch in n.get("children") or []:
            walk(ch, here)

    for ch in doc.get("children") or []:
        walk(ch, (doc["slot"]["name"],))
    return out


def observe(url: str) -> dict:
    proc = subprocess.run(
        ["resoloop", "hierarchy", "--under", ROOT_PATH, "--depth", "16", "--include-components", "--url", url, "--json"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"resoloop hierarchy failed ({proc.returncode}): {proc.stdout[-2000:]} {proc.stderr[-2000:]}")
    return json.loads(proc.stdout)


def dist(a, b) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def run_checks(live: dict) -> dict:
    root = live["data"]
    checks = json.loads((PROJECT_ROOT / "review" / "overview" / "checks.json").read_text(encoding="utf-8"))
    by_path: dict[tuple[str, ...], tuple] = {}
    by_key_name: dict[tuple[str, str], list] = {}
    for path, wpos, wrot, node in world_transforms(root):
        by_path[path] = (wpos, wrot, node)
        if len(path) >= 3:
            by_key_name.setdefault((path[1], path[-1]), []).append((path, wpos, wrot, node))

    result: dict = {"root": ROOT_PATH, "tolerance_m": TOL_M, "keys": {}, "problems": []}
    top_children = [c["name"] for c in root.get("children") or []]
    result["root_children"] = top_children

    # 1. 数と 2. オブジェクトの有無
    for key in KEYS:
        bundle = latest_bundle(key)
        doc = json.loads((bundle / "p2.apply.json").read_text(encoding="utf-8"))
        decl_slots, decl_comps, auto = declared_counts(doc)
        live_node = next((c for c in root.get("children") or [] if c["name"] == key), None)
        entry: dict = {"bundle": bundle.relative_to(PROJECT_ROOT).as_posix(), "declared_slots": decl_slots,
                       "declared_components": decl_comps, "auto_ai_generated_content": auto}
        if live_node is None:
            entry["missing"] = True
            result["problems"].append(f"{key}: key root Slot is missing")
            result["keys"][key] = entry
            continue
        ls, lc = count_nodes(live_node)
        entry.update({"live_slots": ls, "live_components": lc})
        if ls != decl_slots or lc != decl_comps + auto:
            result["problems"].append(f"{key}: live {ls} Slots / {lc} Components != declared {decl_slots} / {decl_comps}+{auto}")
        names = bundle_names(doc)
        missing = [("/".join(p)) for p in names if (ROOT_PATH.split("/")[-1],) + p not in by_path]
        entry["objects_declared"] = len(names)
        entry["objects_missing"] = missing
        if missing:
            result["problems"].append(f"{key}: {len(missing)} objects missing")
        colliders = json.loads((bundle / "colliders.json").read_text(encoding="utf-8"))
        live_mc = sum(
            1 for _, _, _, n in world_transforms(live_node) for c in n.get("components") or [] if c["type"].endswith("FrooxEngine.MeshCollider")
        )
        exp_mc = colliders["counts"]["mesh"] + colliders["counts"]["fixed_collision"]
        entry["mesh_colliders"] = {"live": live_mc, "expected": exp_mc}
        if live_mc != exp_mc:
            result["problems"].append(f"{key}: MeshCollider {live_mc} != {exp_mc}")
        result["keys"][key] = entry

    # 3. 可動部品
    motion_rows = []
    for key, parts in checks["motion_parts"].items():
        for part in parts:
            name = part["motion_root"]
            hits = by_key_name.get((key, name), [])
            row = {"key": key, "motion_root": name, "expected_resonite": [round(v, 4) for v in b2r(part["pivot_world"])]}
            if len(hits) != 1:
                row["error"] = f"{len(hits)} Slots named {name}"
                result["problems"].append(f"motion {key}/{name}: {row['error']}")
            else:
                path, wpos, _, node = hits[0]
                d = dist(wpos, row["expected_resonite"])
                row["live_world"] = [round(v, 4) for v in wpos]
                row["diff_m"] = round(d, 5)
                colliders_below = [
                    "/".join(p) for p, _, _, n in world_transforms(node, path=path[:-1])
                    if any(c["type"].endswith("Collider") for c in n.get("components") or [])
                ]
                row["colliders_below"] = colliders_below
                if d > TOL_M:
                    result["problems"].append(f"motion {key}/{name}: {d:.4f} m")
                if colliders_below:
                    result["problems"].append(f"motion {key}/{name}: colliders below {colliders_below}")
            motion_rows.append(row)
    result["motion_parts"] = {"count": len(motion_rows), "max_diff_m": max((r.get("diff_m", 0) for r in motion_rows), default=None),
                              "rows": motion_rows}

    # 4. 仮モデルとランドマーク
    def find_any(name: str):
        hits = [v for (k, n), v in by_key_name.items() if n == name]
        flat = [h for group in hits for h in group]
        return flat

    ph_rows = []
    for row_key, ph in checks["placeholders"].items():
        hits = find_any(ph["placeholder"])
        exp = b2r(ph["frame_origin_world"])
        row = {"row": row_key, "placeholder": ph["placeholder"], "expected_resonite": exp}
        if len(hits) != 1:
            row["error"] = f"{len(hits)} Slots"
            result["problems"].append(f"placeholder {row_key}: {row['error']}")
        else:
            row["live_world"] = [round(v, 4) for v in hits[0][1]]
            row["diff_m"] = round(dist(hits[0][1], exp), 5)
            if row["diff_m"] > TOL_M:
                result["problems"].append(f"placeholder {row_key}: {row['diff_m']} m")
            fixed = [p for p in by_path if p[-1].startswith(ph["placeholder"]) and p[-1].endswith("_FixedCollision")]
            row["fixed_collision_slot"] = "/".join(fixed[0]) if fixed else None
        ph_rows.append(row)
    result["placeholders"] = ph_rows

    lm_rows = []
    for lm_id, lm in checks["landmarks"].items():
        hits = find_any(lm["built_asset"])
        exp = b2r(lm["built_origin"])
        row = {"landmark": lm_id, "built_asset": lm["built_asset"], "expected_resonite": exp}
        if len(hits) != 1:
            row["error"] = f"{len(hits)} Slots"
            result["problems"].append(f"landmark {lm_id}: {row['error']}")
        else:
            row["live_world"] = [round(v, 4) for v in hits[0][1]]
            row["diff_m"] = round(dist(hits[0][1], exp), 5)
            if row["diff_m"] > TOL_M:
                result["problems"].append(f"landmark {lm_id}: {row['diff_m']} m")
        lm_rows.append(row)
    result["landmarks"] = lm_rows

    # 5. 取付位置に当たり判定が無いこと
    att_with_collider = []
    for key in KEYS[1:]:
        man = json.loads((PROJECT_ROOT / "assets" / "manifest" / f"{key}.json").read_text(encoding="utf-8"))
        for asset in man["assets"]:
            for att in (asset.get("hierarchy") or {}).get("attachment_points") or []:
                for path, _, _, node in by_key_name.get((key, att), []):
                    if any(c["type"].endswith("Collider") for c in node.get("components") or []):
                        att_with_collider.append("/".join(path))
    result["attachment_points_with_collider"] = att_with_collider
    if att_with_collider:
        result["problems"].append(f"{len(att_with_collider)} attachment points have colliders")

    # 6. 寸法: 取り込んだメッシュ（バンドルの mesh.json）の頂点を、観察した世界の変換で置いた外接箱
    dims = []
    for key, name, axis, expected in DIMENSION_CHECKS:
        hits = by_key_name.get((key, name), [])
        row = {"key": key, "object": name, "axis": axis, "expected_m": expected}
        if len(hits) != 1:
            row["error"] = f"{len(hits)} Slots"
            result["problems"].append(f"dimension {name}: {row['error']}")
            dims.append(row)
            continue
        _, wpos, wrot, node = hits[0]
        lo, hi = live_mesh_bounds(key, name, wpos, wrot)
        row["bounds_min"] = [round(v, 4) for v in lo]
        row["bounds_max"] = [round(v, 4) for v in hi]
        i = "xyz".index(axis[0])
        measured = hi[i] - lo[i] if axis.endswith("size") else (lo[i] if axis.endswith("min") else hi[i])
        row["measured_m"] = round(measured, 4)
        if expected is not None:
            row["diff_m"] = round(measured - expected, 4)
            if abs(measured - expected) > TOL_M:
                result["problems"].append(f"dimension {name} {axis}: {measured:.4f} != {expected}")
        dims.append(row)
    result["dimensions"] = dims
    result["ok"] = not result["problems"]
    return result


# (キー, オブジェクト, 軸, 期待値 m)。軸は Resonite の x/y/z に size（長さ）・min・max。期待値が None なら記録だけ。
DIMENSION_CHECKS = [
    ("B_mansion", "BMN_MansionPlaceholder_001", "x size", 15.0),          # M03 の仮モデルの幅（received.json）
    ("B_mansion", "BMN_MansionPlaceholder_001", "y size", 10.607),        # 同じく高さ
    ("E_forest", "EFR_ClockTower_001_Body", "y size", 14.0),              # 時計塔の高さ
    ("E_forest", "EFR_ClockTower_001_Body", "x max", -34.711),            # 時計塔の東の面
    ("world", "WLD_WestBridge_001", "x min", -34.711),                    # 西の主動線の床の西の端（W08 で時計塔の東の面まで）
    ("world", "WLD_SouthPromenade_001", "x size", None),                  # 南の主動線（記録だけ）
    ("world", "WLD_NorthBridge_001", "x size", 4.0),                      # 北の主動線の幅（Spec §4.1）
    ("world", "WLD_EastBridge_001", "z size", 4.0),                       # 東の主動線の幅
    ("A_plaza", "APL_EntranceGateProxy_001_Arch", "x size", 11.0),        # M01 の仮モデルの幅
]


def live_mesh_bounds(key: str, name: str, wpos, wrot) -> tuple[list[float], list[float]]:
    bundle = latest_bundle(key)
    doc = json.loads((bundle / "p2.apply.json").read_text(encoding="utf-8"))
    src = None

    def walk(n: dict):
        nonlocal src
        if n["slot"]["name"] == name:
            for c in n.get("components") or []:
                if c.get("type") == "FrooxEngine.StaticMesh":
                    src = doc["assets"][c["fields"]["URL"].removeprefix("$asset:")]["source"]
        for ch in n.get("children") or []:
            walk(ch)

    for ch in doc.get("children") or []:
        walk(ch)
    if src is None:
        raise SystemExit(f"{name}: no StaticMesh in {bundle}")
    mesh = json.loads((bundle / src).read_text(encoding="utf-8"))
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    for v in mesh["vertices"]:
        p = v["position"]
        w = qrot(wrot, (p["x"], p["y"], p["z"]))
        for i in range(3):
            c = wpos[i] + w[i]
            lo[i] = min(lo[i], c)
            hi[i] = max(hi[i], c)
    return lo, hi


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", help="ResoniteLink の URL。--raw-in を使うときは不要")
    ap.add_argument("--raw-in", type=Path, help="保存済みの hierarchy の出力から検査する")
    ap.add_argument("--raw-out", type=Path, help="観察した hierarchy の出力の保存先（コミットしない）")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.raw_in:
        live = json.loads(args.raw_in.read_text(encoding="utf-8"))
    else:
        if not args.url:
            ap.error("--url or --raw-in is required")
        live = observe(args.url)
        if args.raw_out:
            args.raw_out.parent.mkdir(parents=True, exist_ok=True)
            args.raw_out.write_text(json.dumps(live, ensure_ascii=False), encoding="utf-8")
    result = run_checks(live)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "problems": result["problems"][:20],
                      "motion_max_diff_m": result["motion_parts"]["max_diff_m"],
                      "keys": {k: {kk: v.get(kk) for kk in ("live_slots", "declared_slots", "live_components", "declared_components",
                                                             "auto_ai_generated_content", "mesh_colliders")}
                               for k, v in result["keys"].items()}}, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
