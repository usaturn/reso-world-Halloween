"""Export each P1 district for the record and validate the bundle offline (W07, Issue #9).

Run (project directory, after the keys are built; see `docs/p1-handoff.md`):
    uv run python modeling/overview/export_p1.py                 # world and the five districts
    uv run python modeling/overview/export_p1.py --key C_candy   # one key

For every key it runs, with a new output directory `exports/p1/<key>-<UTC>` (resoloop needs a new one):
    resoloop blender export blender/<key>/<key>.blend --output exports/p1/<key>-<UTC> \\
        --parent Root/ResoLoop_Test_W07_<key> --collection <key> --preserve-hierarchy --json
    resoloop validate exports/p1/<key>-<UTC>/model.apply.json --json        # offline (no --strict)
and writes `exports/p1/<key>-<UTC>/validate.json` next to resoloop's `report.json`. Only these two files are
committed; the bundle itself (`*.apply.json`, `*.mesh.json`, images) is ignored (`docs/conventions.md` §8).

`--parent` is an unverified test path. resoloop 0.2.0 requires the option, but nothing is applied here:
P2 exports again under the Slot it has verified in the live world (`docs/p1-export-report.md`).
No Resonite connection is made and an earlier export directory is never removed or reused.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
KEYS = ["world", "A_plaza", "B_mansion", "C_candy", "D_amusement", "E_forest"]
PARENT = "Root/ResoLoop_Test_W07_{key}"


def run(args: list[str]) -> tuple[int, dict]:
    proc = subprocess.run(args, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {"unparsed_stdout": proc.stdout[-4000:]}
    if proc.stderr.strip():
        payload["stderr_tail"] = proc.stderr[-2000:]
    return proc.returncode, payload


def export_key(key: str, stamp: str) -> dict:
    blend = f"blender/{key}/{key}.blend"
    if not (PROJECT_ROOT / blend).is_file():
        return {"key": key, "error": f"{blend} is missing; run resoloop blender run modeling/{key}/build.py --json first"}
    out_rel = f"exports/p1/{key}-{stamp}"
    out = PROJECT_ROOT / out_rel
    if out.exists():
        return {"key": key, "error": f"{out_rel} already exists; not reused"}
    out.parent.mkdir(parents=True, exist_ok=True)
    parent = PARENT.format(key=key)
    flags = ["--collection", key, "--preserve-hierarchy"]
    exp_code, exp = run(["resoloop", "blender", "export", blend, "--output", out_rel, "--parent", parent, *flags, "--json"])
    result: dict = {"key": key, "bundle_dir": out_rel, "parent": parent, "flags": flags, "export_exit": exp_code,
                    "export_ok": exp.get("ok")}
    if exp_code != 0 or not (out / "report.json").is_file():
        result["export_error"] = exp
        return result
    val_code, val = run(["resoloop", "validate", f"{out_rel}/model.apply.json", "--json"])
    (out / "validate.json").write_text(json.dumps({"command": f"resoloop validate {out_rel}/model.apply.json --json",
                                                   "exit": val_code, "result": val}, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    data = val.get("data", val)
    result.update({
        "validate_exit": val_code,
        "valid": data.get("valid"),
        "issues": data.get("issues"),
        "report": {k: report.get(k) for k in ("triangles", "vertices", "materials", "drawSections", "staticOnly",
                                              "preserveHierarchy", "providerLayout")},
        "meshes": len(report.get("meshes", [])),
        "textures": len(report.get("textures", [])),
        "warnings": report.get("warnings", []),
    })
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--key", choices=KEYS, action="append", help="key to export (default: all)")
    args = parser.parse_args(argv)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results = [export_key(k, stamp) for k in (args.key or KEYS)]
    print(json.dumps({"stamp": stamp, "results": results}, ensure_ascii=False, indent=2))
    failed = [r["key"] for r in results if r.get("error") or r.get("export_exit") != 0 or r.get("validate_exit") != 0
              or r.get("valid") is not True]
    if failed:
        print(f"FAILED: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
