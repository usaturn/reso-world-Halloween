"""Build the integrated asset list `assets/manifest.json` from the per-key manifests (W07). No `bpy`.

`export_result` of every asset of a key points to the newest `exports/p1/<key>-<UTC>/` that holds a
`report.json`; keys without one keep the value of their own manifest.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path

EXPORT_DIR = re.compile(r"^(?P<key>[A-Za-z0-9_]+)-(?P<stamp>\d{8}T\d{6}Z)$")


def newest_exports(export_root: Path) -> dict[str, str]:
    """Map each key to the name of its newest export directory under `export_root` that has a report.json."""
    found: dict[str, tuple[str, str]] = {}
    if export_root.is_dir():
        for d in export_root.iterdir():
            m = EXPORT_DIR.match(d.name)
            if not m or not d.is_dir() or not (d / "report.json").is_file():
                continue
            key, stamp = m.group("key"), m.group("stamp")
            if key not in found or stamp > found[key][0]:
                found[key] = (stamp, d.name)
    return {k: v[1] for k, v in found.items()}


def merge(manifests: dict[str, dict], keys: list[str], exports: dict[str, str], export_rel: str,
          key: str, generated_by: str) -> dict:
    """Return the integrated manifest of `keys` (in that order). Each asset is copied, never shared."""
    assets = []
    for k in keys:
        man = manifests[k]
        if man.get("key") != k:
            raise ValueError(f"manifest for {k!r} declares key {man.get('key')!r}")
        for asset in man["assets"]:
            if asset.get("key") != k:
                raise ValueError(f"asset {asset.get('asset_id')!r} in the {k!r} manifest has key {asset.get('key')!r}")
            a = copy.deepcopy(asset)
            if k in exports:
                d = f"{export_rel}/{exports[k]}"
                a["export_result"] = {"status": "exported", "bundle_dir": d, "apply_plan": f"{d}/model.apply.json",
                                      "report_file": f"{d}/report.json"}
            assets.append(a)
    return {
        "schema_version": "1.0",
        "key": key,
        "updated_at": max(manifests[k]["updated_at"] for k in keys),
        "generated_by": generated_by,
        "sources": {k: f"assets/manifest/{k}.json" for k in keys},
        "export_dirs": {k: f"{export_rel}/{v}" for k, v in sorted(exports.items()) if k in keys},
        "assets": assets,
    }
