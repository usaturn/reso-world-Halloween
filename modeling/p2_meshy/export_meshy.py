"""W09R: 仕上げた Meshy 素材を、仮モデルの見た目の Slot（visual_root）の子として置く宣言を作る。

実行（プロジェクトのディレクトリ。先に modeling/<M>/build.py で .blend を作る）:
    uv run python modeling/p2_meshy/export_meshy.py --url ws://localhost:<PORT>/ --meshy M02

素材ごとに、新しい出力先 exports/p2_meshy/<M>-<UTC>/ へ次を行う。
    resoloop blender export <blend> --output <出力先> --parent <visual_root のパス> --preserve-hierarchy --pack-pbr --json
    バンドルの root Slot に、visual_root のローカルでの置き方（replacements.py の rotation_z_deg・position_local を
    Resonite の軸に直した値）を書いた p2m.apply.json を作る（model.apply.json は変えない）
    resoloop validate p2m.apply.json --json と --strict --url <URL> --json
結果は <出力先>/validate.json と <出力先>/placement.json に書く（どちらもコミットする。バンドル本体と画像はコミットしない）。
apply は行わない（docs/p2-meshy-replacement.md の手順で、diff を確かめてから --texture-transfer data で行う）。
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from modeling.p2_meshy.replacements import REPLACEMENTS, moving_part_poses, resonite_quat_from_blender_z  # noqa: E402
from modeling.p2_static.export_p2 import run, validate_both  # noqa: E402


def slot_key(name: str) -> str:
    """Slot の名前から宣言のキーを作る（例 M02_InteriorGlow -> m02_interior_glow）。"""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()


def b2r(p: list[float]) -> list[float]:
    return [float(p[0]), float(p[2]), float(p[1])]


def part_document_name(document: str) -> str:
    """可動部品の宣言のファイル名（例 DoorLeft -> p2m_DoorLeft.apply.json）。state は p2m_<M>_<document>.json。"""
    return f"p2m_{document}.apply.json"


def _component_refs(value) -> set[str]:
    """fields の中の $component:<key> の参照先のキー。"""
    if isinstance(value, str):
        return {value.removeprefix("$component:")} if value.startswith("$component:") else set()
    if isinstance(value, list):
        return set().union(*(_component_refs(v) for v in value)) if value else set()
    if isinstance(value, dict):
        return set().union(*(_component_refs(v) for v in value.values())) if value else set()
    return set()


def _asset_refs(value) -> set[str]:
    if isinstance(value, str):
        return {value.removeprefix("$asset:")} if value.startswith("$asset:") else set()
    if isinstance(value, list):
        return set().union(*(_asset_refs(v) for v in value)) if value else set()
    if isinstance(value, dict):
        return set().union(*(_asset_refs(v) for v in value.values())) if value else set()
    return set()


def split_part(doc: dict, rep: dict, meshy_id: str, part_id: str, pose: dict, motion_root_path: str) -> dict:
    """素材の宣言 doc（変えない）から、可動部品 part_id だけを motion_root の下に置く宣言を作る。

    部品の Slot は回転・移動なしの閉じた形で root の子に置き、root に pose の回転（rotation_z_deg + closed_deg）を書く。
    材質と画像は、部品の MeshRenderer が参照する物だけを Blender_Providers ごと写す（宣言の外の Component は参照できない）。
    export の部品の位置・回転が、アセット一覧の蝶番・開いた角度と違えば止める（違うまま閉じた形に戻すと、門扉が蝶番から
    ずれた所に置かれる）。
    """
    asset = next(c for c in doc["children"] if c["slot"]["name"] == rep["asset_id"])
    node = next((c for c in asset.get("children", []) if c["slot"]["name"] == part_id), None)
    if node is None:
        raise ValueError(f"{part_id} is not a child of {rep['asset_id']}")
    if not _is_identity_slot(asset["slot"]):
        raise ValueError(f"{rep['asset_id']} is not at the identity of the bundle root")
    exp_pos = b2r(pose["pivot_local"])
    placed = pose["motion_root_rotation_z_deg"] + pose["part_root_rotation_z_deg"] - float(rep["rotation_z_deg"])
    exp_rot = resonite_quat_from_blender_z(placed)
    pos, rot = node["slot"].get("position") or [0, 0, 0], node["slot"].get("rotation") or [0, 0, 0, 1]
    if max(abs(a - b) for a, b in zip(pos, exp_pos)) > 1e-3 or min(
            max(abs(a - b) for a, b in zip(rot, exp_rot)), max(abs(a + b) for a, b in zip(rot, exp_rot))) > 1e-4:
        raise ValueError(f"{part_id}: exported pose {pos} {rot} differs from the manifest hinge {exp_pos} / {placed} deg")
    part = copy.deepcopy(node)
    part["slot"]["position"] = [0.0, 0.0, 0.0]
    part["slot"]["rotation"] = [0.0, 0.0, 0.0, 1.0]
    part["slot"]["scale"] = [1.0, 1.0, 1.0]
    # 部品の Component が参照する Component を、Blender_Providers の中から推移的に集める
    providers = next(c for c in doc["children"] if c["slot"]["name"] == "Blender_Providers")
    by_key = {comp["key"]: (child, comp) for child in providers.get("children", []) for comp in child.get("components", [])}
    wanted: set[str] = set()
    todo = set().union(*(_component_refs(c.get("fields", {})) for c in part.get("components", [])))
    while todo:
        key = todo.pop()
        if key in wanted or key not in by_key:
            continue
        wanted.add(key)
        todo |= _component_refs(by_key[key][1].get("fields", {}))
    prov = copy.deepcopy(providers)
    prov["children"] = [c for c in prov.get("children", []) if any(comp["key"] in wanted for comp in c.get("components", []))]
    assets = _asset_refs([c.get("fields", {}) for n in (part, prov) for c in _all_components(n)])
    return {
        "schemaVersion": doc["schemaVersion"],
        "ownership": {"key": f"{doc['ownership']['key']}_{pose['document'].lower()}"},
        "slot": {"key": "root", "name": doc["slot"]["name"], "parent": motion_root_path, "position": [0.0, 0.0, 0.0],
                 "rotation": pose["part_root_rotation"], "scale": [1.0, 1.0, 1.0]},
        "assets": {k: v for k, v in doc["assets"].items() if k in assets},
        "components": [],
        "children": [part, prov],
    }


def _all_components(node: dict):
    yield from node.get("components", [])
    for c in node.get("children", []):
        yield from _all_components(c)


def _is_identity_slot(slot: dict) -> bool:
    pos = slot.get("position") or [0.0, 0.0, 0.0]
    rot = slot.get("rotation") or [0.0, 0.0, 0.0, 1.0]
    scl = slot.get("scale") or [1.0, 1.0, 1.0]
    return all(abs(a - b) < 1e-6 for a, b in zip([*pos, *rot, *scl], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1]))


def compose(model_path: Path, out_path: Path, rep: dict, meshy_id: str | None = None) -> dict:
    doc = json.loads(model_path.read_text(encoding="utf-8"))
    out = copy.deepcopy(doc)
    root = out["slot"]
    if root.get("parent") != rep["visual_root_path"]:
        raise ValueError(f"bundle parent {root.get('parent')!r} != {rep['visual_root_path']!r}")
    names = [c["slot"]["name"] for c in out.get("children", [])]
    if rep["asset_id"] not in names:
        raise ValueError(f"{rep['asset_id']} is not a child of the bundle root (children: {names})")
    root["position"] = b2r(rep["position_local"])
    root["rotation"] = resonite_quat_from_blender_z(rep["rotation_z_deg"])
    root["scale"] = [1.0, 1.0, 1.0]
    # 可動部品は別の宣言（motion_root の下）に分け、この宣言からは外す（13 章）
    parts_out = []
    poses = moving_part_poses(meshy_id, rep) if meshy_id else {}
    if poses:
        placeholder_path = rep["visual_root_path"].rsplit("/", 1)[0]
        asset = next(c for c in out["children"] if c["slot"]["name"] == rep["asset_id"])
        for part_id, pose in poses.items():
            motion_root_path = f"{placeholder_path}/{pose['motion_root']}"
            part_doc = split_part(doc, rep, meshy_id, part_id, pose, motion_root_path)
            part_path = out_path.parent / part_document_name(pose["document"])
            part_path.write_text(json.dumps(part_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            asset["children"] = [c for c in asset["children"] if c["slot"]["name"] != part_id]
            parts_out.append({"part": part_id, "document": part_path.name, "state": f"p2m_{meshy_id}_{pose['document']}.json",
                              "parent": motion_root_path, "root_slot": {k: part_doc["slot"].get(k) for k in ("name", "key", "parent", "position", "rotation", "scale")},
                              "ownership": part_doc["ownership"]["key"], "assets": sorted(part_doc["assets"]),
                              "motion_root_repose": {k: pose[k] for k in ("motion_root", "hinge_blender", "motion_root_position", "motion_root_rotation", "motion_root_rotation_z_deg", "closed_rotation_z_deg")}})
        used = _asset_refs([c.get("fields", {}) for c in _all_components({"components": out.get("components", []), "children": out["children"]})])
        out["assets"] = {k: v for k, v in out["assets"].items() if k in used}
    for light in rep.get("lights", []):
        key = slot_key(light["name"])
        out.setdefault("children", []).append({
            "slot": {"key": key, "name": light["name"], "position": b2r(light["position_local"]),
                     "rotation": [0.0, 0.0, 0.0, 1.0], "scale": [1.0, 1.0, 1.0]},
            "components": [{
                "key": f"{key}_light",
                "type": "FrooxEngine.Light",
                "fields": {"LightType": "Point", "Intensity": light["intensity"], "Color": light["color"],
                           "ShadowType": "None", "Range": light["range"]},
            }],
        })
    cameras = {}
    for i, (name, (pos, target, fov)) in enumerate(rep.get("cameras", {}).items()):
        cameras[name] = {"position": pos, "target": target, "fieldOfView": fov, "width": 1600, "height": 900}
        if i == 0:
            cameras[name]["representative"] = True
    if cameras:
        out["cameras"] = cameras
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "root_slot": {k: root.get(k) for k in ("name", "key", "parent", "position", "rotation", "scale")},
        "children": names,
        "assets": sorted(out.get("assets", {})),
        "moving_parts": parts_out,
    }


def export_one(meshy_id: str, stamp: str, url: str, recompose: str | None = None) -> dict:
    rep = REPLACEMENTS[meshy_id]
    flags = ["--preserve-hierarchy", "--pack-pbr"]
    if recompose:
        # 既存のバンドルの model.apply.json はそのままに、p2m.apply.json・placement.json・validate.json だけを作り直す。
        # export し直すとメッシュの接線が 1e-7 程度変わり、apply でメッシュの資産を取り込み直すので、配置・光源・カメラだけを
        # 変えるときはこちらを使う（docs/p2-meshy-replacement.md 4 章）
        out = (PROJECT_ROOT / recompose).resolve()
        out_rel = out.relative_to(PROJECT_ROOT).as_posix()
        if not (out / "model.apply.json").is_file() or not out_rel.startswith(f"exports/p2_meshy/{meshy_id}-"):
            return {"meshy_id": meshy_id, "error": f"{recompose} is not an exports/p2_meshy/{meshy_id}-* bundle"}
        result: dict = {"meshy_id": meshy_id, "bundle_dir": out_rel, "parent": rep["visual_root_path"], "flags": flags,
                        "export_exit": 0, "recomposed": True}
        return _compose_and_validate(meshy_id, rep, out, out_rel, url, result)
    blend = rep["blend"]
    if not (PROJECT_ROOT / blend).is_file():
        return {"meshy_id": meshy_id, "error": f"{blend} is missing; run resoloop blender run modeling/{meshy_id}/build.py --json first"}
    out_rel = f"exports/p2_meshy/{meshy_id}-{stamp}"
    out = PROJECT_ROOT / out_rel
    if out.exists():
        return {"meshy_id": meshy_id, "error": f"{out_rel} already exists; not reused"}
    out.parent.mkdir(parents=True, exist_ok=True)
    exp_code, exp = run(["resoloop", "blender", "export", blend, "--output", out_rel, "--parent", rep["visual_root_path"], *flags, "--json"])
    result = {"meshy_id": meshy_id, "bundle_dir": out_rel, "parent": rep["visual_root_path"], "flags": flags, "export_exit": exp_code}
    if exp_code != 0 or not (out / "report.json").is_file():
        result["export_error"] = exp
        return result
    return _compose_and_validate(meshy_id, rep, out, out_rel, url, result)


def _compose_and_validate(meshy_id: str, rep: dict, out: Path, out_rel: str, url: str, result: dict) -> dict:
    placement = compose(out / "model.apply.json", out / "p2m.apply.json", rep, meshy_id)
    placement.update({k: rep[k] for k in ("district", "placeholder", "visual_root", "visual_root_path", "asset_id", "rotation_z_deg", "position_local")})
    (out / "placement.json").write_text(json.dumps(placement, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    docs = ["p2m.apply.json", *(p["document"] for p in placement["moving_parts"])]
    result["p2m"] = validate_both(f"{out_rel}/p2m.apply.json", url)
    for part in placement["moving_parts"]:
        result.setdefault("parts", {})[part["document"]] = validate_both(f"{out_rel}/{part['document']}", url)
    commands = [c for d in docs for c in (f"resoloop validate {out_rel}/{d} --json", f"resoloop validate {out_rel}/{d} --strict --url <URL> --json")]
    record = {"commands": commands, "p2m": result["p2m"]}
    if result.get("parts"):
        record["parts"] = result["parts"]
    (out / "validate.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    result["report"] = {k: report.get(k) for k in ("triangles", "vertices", "materials", "drawSections", "preserveHierarchy")}
    result["textures"] = [{k: t.get(k) for k in ("name", "width", "height", "rgba8MipBytesEstimate")} for t in report.get("textures", [])]
    result["warnings"] = report.get("warnings", [])
    result["placement"] = placement["root_slot"]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", required=True, help="ResoniteLink の URL（resoloop discover で確かめた値）")
    parser.add_argument("--meshy", action="append", choices=sorted(REPLACEMENTS), help="素材（複数可）。省略すると REPLACEMENTS のすべて")
    parser.add_argument("--recompose", metavar="BUNDLE_DIR", help="export せずに、この既存のバンドルの宣言だけを作り直す（--meshy 1 つと併用）")
    args = parser.parse_args(argv)
    if args.recompose and len(args.meshy or []) != 1:
        parser.error("--recompose needs exactly one --meshy")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results = [export_one(m, stamp, args.url, args.recompose) for m in (args.meshy or sorted(REPLACEMENTS))]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    ok = all(r.get("export_exit") == 0 and all(v.get(m, {}).get("exit") == 0 for v in (r.get("p2m", {}), *r.get("parts", {}).values()) for m in ("offline", "strict")) for r in results)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
