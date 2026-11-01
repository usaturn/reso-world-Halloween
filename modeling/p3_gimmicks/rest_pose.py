"""W10: P2 の検査（modeling/p2_static/verify_live.py・modeling/p2_meshy/verify_live.py）が、P3 の駆動で動いている
可動部品を「ずれた」と誤って判定しないように、観察（resoloop hierarchy）の中の駆動される Slot だけを基準姿勢に戻す。

- 対象は gimmicks.driven_slots() の Slot（G13 の TurnRoot、G01 の 6 体の Body）だけ。ローカルの位置・回転を、最新の
  地区の宣言（exports/p2_static/<key>-*/p2.apply.json）のその Slot の値に置き換える。拡縮と、ほかの Slot は変えない
- 置き換えた Slot の子孫（座席・M05・取付位置など）は、基準姿勢の親の下で今までどおり検査される。駆動された値そのものの
  検査は modeling/p3_gimmicks/verify_live.py が行う
- 宣言に無い・観察に無い・同じ名前が複数あるときは止める（黙って置き換えずに進むと、動いている物の位置で P2 の検査が
  失敗するか、別の Slot を置き換えて本当のずれを隠す）
"""

from __future__ import annotations

import json
from pathlib import Path

from modeling.p3_gimmicks import gimmicks

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def latest_declaration(key: str) -> dict:
    dirs = [d for d in sorted((PROJECT_ROOT / "exports" / "p2_static").glob(f"{key}-*")) if (d / "p2.apply.json").is_file()]
    if not dirs:
        raise SystemExit(f"no exports/p2_static/{key}-*/p2.apply.json")
    return json.loads((dirs[-1] / "p2.apply.json").read_text(encoding="utf-8"))


def _find(node: dict, name: str, name_of, children_of, path: tuple = ()) -> list[tuple[tuple, dict]]:
    hits = []
    here = path + (name_of(node),)
    if name_of(node) == name:
        hits.append((here, node))
    for ch in children_of(node):
        hits.extend(_find(ch, name, name_of, children_of, here))
    return hits


def _xyz(v, keys: str) -> dict:
    return {k: float(x) for k, x in zip(keys, v)}


def p3_additions(key: str, doc: dict | None = None) -> tuple[int, int]:
    """最新の地区の宣言の中で P3 が足した Slot・Component の数（キーが p3_ で始まる物。district.add_drivers）。"""
    doc = doc or latest_declaration(key)
    slots = comps = 0
    stack = [doc]
    while stack:
        node = stack.pop()
        if str(node["slot"].get("key", "")).startswith("p3_"):
            slots += 1
        comps += sum(1 for c in node.get("components", []) if str(c.get("key", "")).startswith("p3_"))
        stack.extend(node.get("children", []))
    return slots, comps


def apply_rest_pose(root: dict, declarations: dict[str, dict] | None = None) -> list[dict]:
    """root（W08 の root の観察のノード。name・position・rotation・children）をその場で変え、置き換えた Slot の一覧を返す。

    declarations は地区のキー → 宣言（テスト用。省略すると最新の export を読む）。
    """
    rows: list[dict] = []
    for key, names in gimmicks.driven_slots().items():
        district = next((c for c in root.get("children") or [] if c["name"] == key), None)
        if district is None:
            raise ValueError(f"{key}: district root is not observed")
        doc = (declarations or {}).get(key) or latest_declaration(key)
        for name in names:
            live = _find(district, name, lambda n: n["name"], lambda n: n.get("children") or [])
            decl = _find(doc, name, lambda n: n["slot"]["name"], lambda n: n.get("children") or [])
            if len(live) != 1 or len(decl) != 1:
                raise ValueError(f"{key}/{name}: observed {len(live)}, declared {len(decl)}")
            node = live[0][1]
            slot = decl[0][1]["slot"]
            rest_pos = _xyz(slot.get("position") or [0, 0, 0], "xyz")
            rest_rot = _xyz(slot.get("rotation") or [0, 0, 0, 1], "xyzw")
            rows.append({"slot": "/".join(live[0][0]), "live": {"position": node["position"], "rotation": node["rotation"]},
                         "rest": {"position": rest_pos, "rotation": rest_rot}})
            node["position"] = rest_pos
            node["rotation"] = rest_rot
    return rows
