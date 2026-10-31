"""W09R (F∩S): the bundles ``modeling/p2_meshy/export_meshy.py`` writes stay out of Git, its records do not.

Damage prevented: the bundle images are cut from the user's Meshy model, which must not be committed to this public
repository (the user's rule of 2026-10-31, ``docs/conventions.md`` §8). ``--pack-pbr`` writes ``pbr_*.png``, which the
top-level rules miss, so ``exports/p2_meshy/.gitignore`` covers the bundle. If it breaks, ``git add`` takes the image in
without any error, and the pre-push grep of the board only looks for model extensions. The records (``report.json``,
``validate.json``, ``placement.json``) are committed and must not be ignored.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = "exports/p2_meshy/M02-20261031T000000Z"
GENERATED = [f"{BUNDLE}/pbr_mat_material_MAT_M02_GiantPumpkin_c7cfe6_6912602f.png"]
COMMITTED = [f"{BUNDLE}/report.json", f"{BUNDLE}/validate.json", f"{BUNDLE}/placement.json"]


def ignored(path: str) -> bool:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}  # judge this checkout, not a caller's
    proc = subprocess.run(["git", "check-ignore", "--quiet", "--no-index", path], cwd=ROOT, env=env, check=False)
    if proc.returncode not in (0, 1):
        pytest.fail(f"git check-ignore failed for {path} (exit {proc.returncode})")
    return proc.returncode == 0


@pytest.mark.parametrize("path", GENERATED)
def test_bundle_images_are_ignored(path: str) -> None:
    assert ignored(path)


@pytest.mark.parametrize("path", COMMITTED)
def test_records_are_not_ignored(path: str) -> None:
    assert not ignored(path)
