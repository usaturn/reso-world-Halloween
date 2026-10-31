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

from modeling.p2_meshy.replacements import REPLACEMENTS, resonite_quat_from_blender_z  # noqa: E402
from modeling.p2_static.export_p2 import run, validate_both  # noqa: E402


def slot_key(name: str) -> str:
    """Slot の名前から宣言のキーを作る（例 M02_InteriorGlow -> m02_interior_glow）。"""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()


def b2r(p: list[float]) -> list[float]:
    return [float(p[0]), float(p[2]), float(p[1])]


def compose(model_path: Path, out_path: Path, rep: dict) -> dict:
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
    placement = compose(out / "model.apply.json", out / "p2m.apply.json", rep)
    placement.update({k: rep[k] for k in ("district", "placeholder", "visual_root", "visual_root_path", "asset_id", "rotation_z_deg", "position_local")})
    (out / "placement.json").write_text(json.dumps(placement, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["p2m"] = validate_both(f"{out_rel}/p2m.apply.json", url)
    (out / "validate.json").write_text(
        json.dumps(
            {
                "commands": [
                    f"resoloop validate {out_rel}/p2m.apply.json --json",
                    f"resoloop validate {out_rel}/p2m.apply.json --strict --url <URL> --json",
                ],
                "p2m": result["p2m"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
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
    ok = all(r.get("export_exit") == 0 and all(r.get("p2m", {}).get(m, {}).get("exit") == 0 for m in ("offline", "strict")) for r in results)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
