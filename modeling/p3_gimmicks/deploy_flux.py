"""W10: flux/p3_plaza_dance.flux.json を配備する（resoloop flux deploy-manifest）。

実行（プロジェクトのディレクトリ。content/p3_gimmicks.json と A の地区の宣言を apply した後）:
    uv run python modeling/p3_gimmicks/deploy_flux.py --url ws://localhost:<PORT>/ --report <Git の外の JSON>
    # W10-A（G03）: --manifest flux/p3_fountain_glow.flux.json（既定は G01 の flux/p3_plaza_dance.flux.json）

- マニフェストの worldState・deployState は、親の checkout から見た相対パス（flux/ から ../.resoloop/...）。worktree から
  配備するときも state を親の checkout に置くため（プロジェクトの AGENTS.md）、--state-dir の絶対パスに直した一時の
  マニフェストを mktemp のディレクトリに作り、それを配備する（source・projectDirectory もこの checkout の絶対パスにする）
- 配備先（parent）は P3 の宣言の Slot のパス。A の state には無いので --parent で渡す
- Flux-SDK のビルドに要る Resonite の DLL は、環境変数 RESONITE_MANAGED_DATA_PATH をこのコマンドだけに付けて渡す
  （deploy-manifest に --library-path は無い）。既定は共有の managed data の最新の版
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_DIR = Path("/workspaces/reso-world/worlds/reso-world-Halloween/.resoloop")
MANAGED_DATA_ROOT = Path.home() / ".local/share/create-reso-world/resonite-managed-data"
MANIFEST = PROJECT_ROOT / "flux" / "p3_plaza_dance.flux.json"


def managed_data_default() -> Path | None:
    if not MANAGED_DATA_ROOT.is_dir():
        return None
    versions = sorted(p for p in MANAGED_DATA_ROOT.iterdir() if p.is_dir())
    return versions[-1] if versions else None


def resolved_manifest(resoloop_dir: Path, manifest: Path = MANIFEST) -> dict:
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    flux_dir = manifest.parent
    for field in ("worldState", "deployState"):
        rel = Path(doc[field])
        if rel.parts[:2] != ("..", ".resoloop"):
            raise SystemExit(f"{field} must start with ../.resoloop: {doc[field]}")
        doc[field] = str(resoloop_dir.joinpath(*rel.parts[2:]))
    doc["projectDirectory"] = str((flux_dir / doc.get("projectDirectory", ".")).resolve())
    for module in doc["modules"]:
        module["source"] = str((flux_dir / module["source"]).resolve())
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", required=True)
    ap.add_argument("--report", type=Path, required=True, help="deploy-manifest の出力の保存先（Git の外。新しいファイル）")
    ap.add_argument("--resoloop-dir", type=Path, default=DEFAULT_STATE_DIR, help="state・flux-state を置く .resoloop")
    ap.add_argument("--managed-data", type=Path, default=managed_data_default())
    ap.add_argument("--manifest", type=Path, default=MANIFEST, help="配備するマニフェスト（flux/ の下）")
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args(argv)
    if args.report.exists():
        raise SystemExit(f"{args.report} already exists")
    if args.managed_data is None or not args.managed_data.is_dir():
        raise SystemExit("managed data is not found; pass --managed-data")
    manifest_path = args.manifest.resolve()
    if manifest_path.parent != MANIFEST.parent:
        raise SystemExit(f"{args.manifest} is not under {MANIFEST.parent}")
    doc = resolved_manifest(args.resoloop_dir, manifest_path)
    Path(doc["deployState"]).parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "RESONITE_MANAGED_DATA_PATH": str(args.managed_data)}
    with tempfile.TemporaryDirectory(prefix="p3-flux-") as tmp:
        manifest = Path(tmp) / manifest_path.name
        manifest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        steps = [["resoloop", "flux", "validate-manifest", str(manifest), "--json"]]
        if not args.validate_only:
            steps.append(["resoloop", "flux", "deploy-manifest", str(manifest), "--parent", doc["parent"],
                          "--state", doc["worldState"], "--url", args.url, "--json"])
        results = []
        code = 0
        for cmd in steps:
            proc = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, check=False)
            results.append({"command": cmd[:3], "exit": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr[-4000:]})
            code = proc.returncode
            if code != 0:
                break
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for r in results:
        print(r["command"], "exit", r["exit"], r["stdout"][-1500:], r["stderr"][-800:])
    return code


if __name__ == "__main__":
    sys.exit(main())
