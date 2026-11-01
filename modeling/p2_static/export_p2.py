"""W08: P1 の world と 5 地区を、確かめた W08 の root Slot の下へ export し、当たり判定を足した宣言を作る。

実行（プロジェクトのディレクトリ。先に各キーをビルドする。docs/p1-handoff.md 6 章）:
    uv run python modeling/p2_static/export_p2.py --url ws://localhost:<PORT>/            # 6 キー
    uv run python modeling/p2_static/export_p2.py --url ws://localhost:<PORT>/ --key E_forest

キーごとに、新しい出力先 exports/p2_static/<key>-<UTC>/ へ次を行う。
    resoloop blender export blender/<key>/<key>.blend --output <出力先> --parent Root/HalloweenMagicalCarnival \\
        --collection <key> --preserve-hierarchy --json
    resoloop validate <出力先>/model.apply.json --json                     # オフライン
    resoloop validate <出力先>/model.apply.json --strict --url <URL> --json  # ライブの Reflection
    modeling/p2_static/colliders.py で <出力先>/p2.apply.json（当たり判定・ObjectRoot を足した宣言）を作る
    p2.apply.json も同じ 2 つの validate を通す
結果は <出力先>/validate.json と <出力先>/colliders.json に書く（どちらもコミットする。バンドル本体はコミットしない）。
apply は行わない（docs/p2-static-integration.md 7 章の手順で、diff を確かめてから行う）。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from modeling.p2_meshy import replacements  # noqa: E402
from modeling.p2_static import colliders  # noqa: E402
from modeling.p3_gimmicks import district  # noqa: E402

KEYS = ["world", "A_plaza", "B_mansion", "C_candy", "D_amusement", "E_forest"]
PARENT = "Root/HalloweenMagicalCarnival"


def run(args: list[str]) -> tuple[int, dict]:
    proc = subprocess.run(args, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {"unparsed_stdout": proc.stdout[-4000:]}
    if proc.stderr.strip():
        payload["stderr_tail"] = proc.stderr[-2000:]
    return proc.returncode, payload


def validate_both(doc_rel: str, url: str) -> dict:
    off_code, off = run(["resoloop", "validate", doc_rel, "--json"])
    st_code, st = run(["resoloop", "validate", doc_rel, "--strict", "--url", url, "--json"])

    def summary(code: int, payload: dict) -> dict:
        data = payload.get("data", {})
        err = payload.get("error")
        return {
            "exit": code,
            "valid": data.get("valid"),
            "issues": data.get("issues") if data else (err or {}).get("context", {}).get("issues"),
            "error_code": (err or {}).get("code"),
        }

    return {"offline": summary(off_code, off), "strict": summary(st_code, st)}


def export_key(key: str, stamp: str, url: str) -> dict:
    blend = f"blender/{key}/{key}.blend"
    if not (PROJECT_ROOT / blend).is_file():
        return {"key": key, "error": f"{blend} is missing; run resoloop blender run modeling/{key}/build.py --json first"}
    out_rel = f"exports/p2_static/{key}-{stamp}"
    out = PROJECT_ROOT / out_rel
    if out.exists():
        return {"key": key, "error": f"{out_rel} already exists; not reused"}
    out.parent.mkdir(parents=True, exist_ok=True)
    flags = ["--collection", key, "--preserve-hierarchy"]
    exp_code, exp = run(["resoloop", "blender", "export", blend, "--output", out_rel, "--parent", PARENT, *flags, "--json"])
    result: dict = {"key": key, "bundle_dir": out_rel, "parent": PARENT, "flags": flags, "export_exit": exp_code}
    if exp_code != 0 or not (out / "report.json").is_file():
        result["export_error"] = exp
        return result
    result["model"] = validate_both(f"{out_rel}/model.apply.json", url)
    summary = colliders.compose(out / "model.apply.json", out / "p2.apply.json", key)
    (out / "colliders.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # W09R: Meshy の仕上げた素材に差し替えた仮モデルの描画を止める（modeling/p2_meshy/replacements.py）
    hidden = replacements.hide_in_file(out / "p2.apply.json", key)
    if hidden:
        (out / "replacements.json").write_text(json.dumps(hidden, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["hidden_placeholders"] = hidden
    # W10: P3 が駆動する可動部品の managedFields と G13 の Spinner（modeling/p3_gimmicks/district.py）
    drivers = district.add_drivers_in_file(out / "p2.apply.json", key)
    if drivers:
        (out / "p3_drivers.json").write_text(json.dumps(drivers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["p3_drivers"] = drivers
    result["p2"] = validate_both(f"{out_rel}/p2.apply.json", url)
    result["colliders"] = summary["counts"]
    (out / "validate.json").write_text(
        json.dumps(
            {
                "commands": [
                    f"resoloop validate {out_rel}/model.apply.json --json",
                    f"resoloop validate {out_rel}/model.apply.json --strict --url <URL> --json",
                    f"resoloop validate {out_rel}/p2.apply.json --json",
                    f"resoloop validate {out_rel}/p2.apply.json --strict --url <URL> --json",
                ],
                "model": result["model"],
                "p2": result["p2"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    result["report"] = {k: report.get(k) for k in ("triangles", "vertices", "drawSections", "staticOnly", "preserveHierarchy", "providerLayout")}
    result["meshes"] = len(report.get("meshes", []))
    result["materials"] = report.get("materials")
    result["textures"] = len(report.get("textures", []))
    result["warnings"] = report.get("warnings", [])
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", required=True, help="ResoniteLink の URL（resoloop discover で確かめた値）")
    parser.add_argument("--key", action="append", choices=KEYS, help="キー（複数可）。省略すると 6 キーすべて")
    args = parser.parse_args(argv)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results = [export_key(k, stamp, args.url) for k in (args.key or KEYS)]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    ok = all(
        r.get("export_exit") == 0
        and all(r.get(doc, {}).get(mode, {}).get("exit") == 0 for doc in ("model", "p2") for mode in ("offline", "strict"))
        for r in results
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
