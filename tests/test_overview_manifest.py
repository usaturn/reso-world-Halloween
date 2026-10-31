"""S-criteria test for the W07 integrated asset list (`modeling/overview/manifest_merge.py`).

Why this test exists (create-reso-world AGENTS.md, test criterion S): `assets/manifest.json` is the single list
P2 reads to find each asset's file and export bundle. If the merge dropped a key's assets, pointed a key's assets at
another key's bundle, or kept an older export after a newer one was made, `tools/check_data.py` would still pass
(every referenced path exists) and P2 would apply the wrong or a stale bundle without any error.
"""

from __future__ import annotations

from pathlib import Path

from modeling.overview.manifest_merge import merge, newest_exports


def _manifest(key: str, ids: list[str], updated: str) -> dict:
    return {"schema_version": "1.0", "key": key, "updated_at": updated,
            "assets": [{"asset_id": i, "key": key, "export_result": {"status": "unexported", "bundle_dir": None,
                                                                    "apply_plan": None, "report_file": None}}
                       for i in ids]}


def _export(root: Path, name: str, report: bool = True) -> None:
    d = root / name
    d.mkdir(parents=True)
    if report:
        (d / "report.json").write_text("{}", encoding="utf-8")


def test_merge_keeps_every_asset_and_points_each_key_at_its_newest_export(tmp_path: Path) -> None:
    root = tmp_path / "exports" / "p1"
    _export(root, "A_plaza-20261031T140000Z")
    _export(root, "A_plaza-20261031T150000Z")
    _export(root, "A_plaza-20261031T160000Z", report=False)  # failed export: no report.json, must not win
    _export(root, "B_mansion-20261031T140500Z")
    _export(root, "notes")
    manifests = {
        "A_plaza": _manifest("A_plaza", ["APL_Fountain_001", "APL_Bench_001"], "2026-10-31T12:00:00Z"),
        "B_mansion": _manifest("B_mansion", ["BMN_Gate_001"], "2026-10-31T13:00:00Z"),
        "common": _manifest("common", ["CMN_Bench_001"], "2026-10-31T09:00:00Z"),
    }

    exports = newest_exports(root)
    assert exports == {"A_plaza": "A_plaza-20261031T150000Z", "B_mansion": "B_mansion-20261031T140500Z"}

    out = merge(manifests, ["common", "A_plaza", "B_mansion"], exports, "exports/p1", "overview", "x.py")
    got = {a["asset_id"]: (a["key"], a["export_result"]) for a in out["assets"]}
    assert sorted(got) == ["APL_Bench_001", "APL_Fountain_001", "BMN_Gate_001", "CMN_Bench_001"]
    assert len(out["assets"]) == 4
    assert got["APL_Fountain_001"][1]["bundle_dir"] == "exports/p1/A_plaza-20261031T150000Z"
    assert got["APL_Bench_001"][1]["report_file"] == "exports/p1/A_plaza-20261031T150000Z/report.json"
    assert got["BMN_Gate_001"][1]["apply_plan"] == "exports/p1/B_mansion-20261031T140500Z/model.apply.json"
    assert got["CMN_Bench_001"][1]["status"] == "unexported"  # no export of its own: keeps its manifest's value
    assert out["updated_at"] == "2026-10-31T13:00:00Z"
    # the source manifests are not modified
    assert manifests["A_plaza"]["assets"][0]["export_result"]["status"] == "unexported"
