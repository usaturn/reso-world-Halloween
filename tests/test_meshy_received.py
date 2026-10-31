"""W09: assets/meshy/received.json stays consistent with what was measured and with the originals.

- Stale derived values: editing ``decided`` without rerunning ``modeling/meshy/intake_inspect.py`` leaves sizes and
  points that no longer follow from the decision; the area and finishing children would build to them silently.
- The originals (F∩S): the copies outside Git are the user's Meshy downloads and must not change (#13 forbids
  editing them; Meshy deletes its downloads after a few days). The hashes are the confirmed set of
  https://github.com/usaturn/reso-world-Halloween/issues/13#issuecomment-6542207249 . Skipped where the copies are
  absent (another machine).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from modeling.meshy import metrics

ROOT = Path(__file__).resolve().parents[1]
RECEIVED = json.loads((ROOT / "assets" / "meshy" / "received.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("row", RECEIVED["assets"], ids=lambda r: r["row_id"])
def test_derived_points_follow_the_decided_placement(row: dict) -> None:
    d = row["decided"]
    m = metrics.placement_matrix(d["origin_source"], d["yaw_deg"], d["scale"])
    assert set(row["derived"]["points_local_m"]) == set(d["points_source"])
    for name, src in d["points_source"].items():
        expected = metrics.transform_points(m, np.asarray(src))[0]
        np.testing.assert_allclose(row["derived"]["points_local_m"][name], expected, atol=0.002, err_msg=name)


@pytest.mark.parametrize("row", RECEIVED["assets"], ids=lambda r: r["row_id"])
def test_copy_outside_git_matches_the_confirmed_original(row: dict) -> None:
    copy = Path(row["source"]["copy_path"])
    if not copy.exists():
        pytest.skip(f"{copy} is not on this machine")
    h = hashlib.sha256()
    with open(copy, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    assert h.hexdigest() == row["source"]["sha256"]
    assert copy.stat().st_size == row["source"]["bytes"]
