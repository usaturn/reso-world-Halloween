"""Export ``blender/M06/M06.blend``, validate the bundle and record the result in ``assets/manifest/M06.json`` (W09-M06).

Run (project directory, after ``resoloop blender run modeling/M06/build.py --json``):
    uv run python modeling/M06/export.py

It runs (``docs/conventions.md`` §7.5; resoloop 0.2.0 takes ``--parent`` instead of ``--root-path``, and the metallic
and roughness images need ``--pack-pbr``):
    resoloop blender export blender/M06/M06.blend --output exports/M06/bundle --parent Root/ResoLoop_Test_W09_M06 \\
        --collection M06 --preserve-hierarchy --pack-pbr --json
    resoloop validate exports/M06/bundle/model.apply.json --json

The export needs a new output directory, so an earlier ``exports/M06/bundle`` (and only that directory) is removed
first. ``--parent`` is a test Slot: P2 exports again under the verified VisualRoot (``handoff/W09-M06.md``).
A rebuild resets ``export_result`` to ``unexported``, so run this after the last build.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLEND_REL = "blender/M06/M06.blend"
BUNDLE_REL = "exports/M06/bundle"
MANIFEST_REL = "assets/manifest/M06.json"
PARENT = "Root/ResoLoop_Test_W09_M06"


def run(args: list[str]) -> dict:
    proc = subprocess.run(args, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise SystemExit(f"{' '.join(args[:3])}: exit {proc.returncode}, no JSON\n{proc.stdout}\n{proc.stderr}") from None
    if proc.returncode != 0 or not out.get("ok"):
        raise SystemExit(f"{' '.join(args[:3])}: exit {proc.returncode}\n{json.dumps(out, ensure_ascii=False)[:4000]}")
    return out


def main() -> None:
    blend = PROJECT_ROOT / BLEND_REL
    if not blend.is_file():
        raise SystemExit(f"{BLEND_REL} is missing; run resoloop blender run modeling/M06/build.py --json first")
    bundle = PROJECT_ROOT / BUNDLE_REL
    if bundle.is_symlink() or (bundle.exists() and not bundle.is_dir()):
        raise SystemExit(f"{BUNDLE_REL} is not a plain directory; not removing it")
    if bundle.is_dir():
        shutil.rmtree(bundle)
    exported = run(["resoloop", "blender", "export", BLEND_REL, "--output", BUNDLE_REL, "--parent", PARENT,
                    "--collection", "M06", "--preserve-hierarchy", "--pack-pbr", "--json"])
    validated = run(["resoloop", "validate", f"{BUNDLE_REL}/model.apply.json", "--json"])
    report = json.loads((bundle / "report.json").read_text(encoding="utf-8"))
    v = validated.get("data", validated)
    result = {
        "status": "exported",
        "bundle_dir": BUNDLE_REL,
        "apply_plan": f"{BUNDLE_REL}/model.apply.json",
        "report_file": f"{BUNDLE_REL}/report.json",
        "parent": PARENT,
        "flags": ["--collection M06", "--preserve-hierarchy", "--pack-pbr"],
        "report": {k: report.get(k) for k in ("triangles", "vertices", "materials", "drawSections", "staticOnly",
                                              "preserveHierarchy", "warnings")},
        "meshes": [{k: m.get(k) for k in ("name", "vertices", "triangles", "submeshes")} for m in report.get("meshes", [])],
        "textures": [{k: t.get(k) for k in ("name", "width", "height", "rgba8MipBytesEstimate")} for t in report.get("textures", [])],
        "validate": {k: v.get(k) for k in ("valid", "strict", "slots", "components", "references", "issues")},
    }
    path = PROJECT_ROOT / MANIFEST_REL
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["assets"][0]["export_result"] = result
    manifest["updated_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"export": exported.get("data", {}).get("outputDirectory", BUNDLE_REL), "export_result": result},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
