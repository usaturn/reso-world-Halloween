"""W08: export した地区のバンドルに、歩行用の当たり判定と ObjectRoot を足した宣言（p2.apply.json）を作る。

export_p2.py から呼ぶ。入力の model.apply.json は変えない。方針は docs/p2-static-integration.md 6 章。

- 当たり判定は、メッシュを持つ Slot ごとに 1 つの FrooxEngine.MeshCollider（Type Static、CharacterCollider true、
  Sidedness DualSided）。参照するメッシュは、その Slot の StaticMesh（同じメッシュの資産）
- 付けない物: 可動部品（アセット一覧の motion_roots とその子孫）、取付位置（attachment_points）、
  E_forest のアセット一覧で collider_policy が none のシリーズ、NO_COLLIDER の物
- Meshy の仮モデル（review/overview/checks.json の placeholders）の静的な部分は、差し替えの範囲の外に置く。
  仮モデルの Slot と同じ親・同じ変換の兄弟 Slot（<名前>_FixedCollision）を作り、同じメッシュの資産を参照する
  自分の StaticMesh と MeshCollider を置く（差し替えの子が見た目を替えても当たり判定は残る。Spec §6.3）
- ObjectRoot: キーの root Slot と、その直下の物（Blender_Providers を除く）に付ける（resonite-build スキル）
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

COLLIDER_FIELDS = {"Type": "Static", "CharacterCollider": True, "Sidedness": "DualSided"}

# 当たり判定を付けない静的なメッシュと理由（キーごと）。
NO_COLLIDER = {
    "WLD_FloatingIslets_001": "遠景の浮き岩。歩いて届かない",
    "CCD_WitchPatrolLoop_001_GuideRing": "魔女の巡回路の目印の輪（高さ 10 m の空中）",
    "CCD_M08_FlyingWitchProxy_001": "M08 の仮モデル。空中を飛ぶ物で、P3 で動く",
    "CCD_MagicCauldron_001_Liquid": "大釜の液面。器（Body）に当たり判定がある",
    "EFR_Pond_001_Water": "池の水面。池の底（EFR_Pond_001）に当たり判定がある",
    "EFR_ClockTower_001_Dial": "高さ 8 m の仮の文字盤（M07 の差し替えの範囲）。手が届かない",
}

SERIES_RE = re.compile(r"^(?P<series>.+?)_(?P<num>\d{3})(?P<rest>(_.*)?)$")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_sets(key: str) -> dict:
    man = _load(PROJECT_ROOT / "assets" / "manifest" / f"{key}.json")
    motion, attach = set(), set()
    none_series: set[str] = set()
    for asset in man.get("assets", []):
        h = asset.get("hierarchy") or {}
        motion.update(h.get("motion_roots") or [])
        attach.update(h.get("attachment_points") or [])
        if asset.get("collider_policy") == "none":
            m = SERIES_RE.match(asset["asset_id"])
            none_series.add(m.group("series") if m else asset["asset_id"])
    return {"motion": motion, "attachment": attach, "none_series": none_series}


def placeholder_names() -> dict[str, str]:
    checks = _load(PROJECT_ROOT / "review" / "overview" / "checks.json")
    return {v["placeholder"]: k for k, v in checks["placeholders"].items()}


def _mesh_component(node: dict) -> dict | None:
    for comp in node.get("components", []):
        if comp.get("type") == "FrooxEngine.StaticMesh":
            return comp
    return None


def _has_renderer(node: dict) -> bool:
    return any(c.get("type") == "FrooxEngine.MeshRenderer" for c in node.get("components", []))


def _series(name: str) -> str | None:
    m = SERIES_RE.match(name)
    return m.group("series") if m else None


def classify(name: str, chain: list[str], sets: dict, placeholders: dict[str, str]) -> tuple[str, str]:
    """(policy, 理由) を返す。policy は none / mesh / fixed_collision。chain は root からこの Slot までの名前。"""
    if any(n in sets["motion"] for n in chain):
        return "none", "可動部品（motion_roots とその子孫）。Spec §8・§11"
    if name in sets["attachment"]:
        return "none", "取付位置（attachment_points）"
    if name in NO_COLLIDER:
        return "none", NO_COLLIDER[name]
    for n in chain:
        s = _series(n)
        if s and s in sets["none_series"]:
            return "none", f"E_forest のアセット一覧の collider_policy が none（{s}）"
    hit = [n for n in chain if n in placeholders]
    if hit:
        return "fixed_collision", f"Meshy の仮モデル {placeholders[hit[-1]]} の静的な部分。差し替えの範囲の外の兄弟 Slot に置く"
    return "mesh", "静的なメッシュ"


def compose(model_path: Path, out_path: Path, key: str) -> dict:
    doc = _load(model_path)
    out = copy.deepcopy(doc)
    sets = manifest_sets(key)
    placeholders = placeholder_names()
    rows: list[dict] = []

    out.setdefault("components", [])
    out["components"].append({"key": f"objroot_{key}", "type": "FrooxEngine.ObjectRoot"})
    object_roots = 1

    def visit(node: dict, chain: list[str]) -> list[dict]:
        """node の子を処理し、node の子に足す兄弟（FixedCollision）を返す。"""
        extra_children: list[dict] = []
        for child in node.get("children", []):
            name = child["slot"]["name"]
            if name == "Blender_Providers":
                continue
            child_chain = chain + [name]
            if _has_renderer(child):
                policy, reason = classify(name, child_chain, sets, placeholders)
                mesh = _mesh_component(child)
                if mesh is None:
                    raise ValueError(f"{name}: MeshRenderer without StaticMesh")
                suffix = mesh["key"].removeprefix("mesh_")
                row = {"slot": "/".join(child_chain), "policy": policy, "reason": reason}
                if policy == "mesh":
                    child.setdefault("components", []).append(
                        {"key": f"collider_{suffix}", "type": "FrooxEngine.MeshCollider",
                         "fields": {"Mesh": f"$component:{mesh['key']}", **COLLIDER_FIELDS}}
                    )
                    row["collider_slot"] = row["slot"]
                elif policy == "fixed_collision":
                    s = child["slot"]
                    fixed_slot = {"key": f"fixedcol_{s['key']}", "name": f"{name}_FixedCollision"}
                    for f in ("position", "rotation", "scale"):
                        if f in s:
                            fixed_slot[f] = s[f]
                    extra_children.append({
                        "slot": fixed_slot,
                        "components": [
                            {"key": f"fixedcol_mesh_{suffix}", "type": "FrooxEngine.StaticMesh",
                             "fields": {"URL": mesh["fields"]["URL"]}},
                            {"key": f"fixedcol_collider_{suffix}", "type": "FrooxEngine.MeshCollider",
                             "fields": {"Mesh": f"$component:fixedcol_mesh_{suffix}", **COLLIDER_FIELDS}},
                        ],
                    })
                    row["collider_slot"] = "/".join(chain + [fixed_slot["name"]])
                rows.append(row)
            sib = visit(child, child_chain)
            if sib:
                child.setdefault("children", []).extend(sib)
        return extra_children

    root_name = out["slot"]["name"]
    top_extra = visit(out, [root_name])
    out["children"].extend(top_extra)

    for child in out["children"]:
        if child["slot"]["name"] in ("Blender_Providers",) or child["slot"]["name"].endswith("_FixedCollision"):
            continue
        child.setdefault("components", []).append({"key": f"objroot_{child['slot']['key']}", "type": "FrooxEngine.ObjectRoot"})
        object_roots += 1

    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {p: sum(1 for r in rows if r["policy"] == p) for p in ("mesh", "fixed_collision", "none")}
    counts["mesh_slots"] = len(rows)
    counts["object_roots"] = object_roots
    return {"key": key, "source": model_path.name, "output": out_path.name, "collider_fields": COLLIDER_FIELDS,
            "counts": counts, "objects": rows}
