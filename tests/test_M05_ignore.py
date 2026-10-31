"""W09-M05 (F∩S): the files ``modeling/M05/build.py`` and ``modeling/M05/export.py`` write stay out of Git.

Damage prevented: the textures (``blender/M05/textures/``) and the export bundle are cut from the user's Meshy model,
which must not be committed to this public repository (the user's rule of 2026-10-31, ``docs/conventions.md`` §8).
If an ignore rule breaks, ``git add`` takes them in without any error, and the pre-push grep of the board only looks
for model extensions (``.blend``, ``.glb`` ...), not for PNG or ``.mesh.json``. ``--pack-pbr`` writes ``pbr_*.png``,
which the top-level ``exports/**/tex_*.png`` rule misses, so ``exports/M05/.gitignore`` covers the bundle.
``report.json`` (committed, ``docs/conventions.md`` §8) and the review images are the cases that must not be ignored.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

GENERATED = [  # one per rule: blender/M05/.gitignore, exports/M05/.gitignore (the root rules have their own owner)
    "blender/M05/textures/M05_Canopy_001_color.png",
    "exports/M05/bundle/pbr_mat_material_MAT_M05_Canopy_1ad5775e_fe48c99c.png",
]
COMMITTED = ["exports/M05/bundle/report.json", "review/M05/M05_views.png"]


def ignored(path: str) -> bool:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}  # judge this checkout, not a caller's
    proc = subprocess.run(["git", "check-ignore", "--quiet", "--no-index", path], cwd=ROOT, env=env, check=False)
    if proc.returncode not in (0, 1):
        pytest.fail(f"git check-ignore failed for {path} (exit {proc.returncode})")
    return proc.returncode == 0


@pytest.mark.parametrize("path", GENERATED)
def test_generated_model_files_are_ignored(path: str) -> None:
    assert ignored(path)


@pytest.mark.parametrize("path", COMMITTED)
def test_committed_outputs_are_not_ignored(path: str) -> None:
    assert not ignored(path)
