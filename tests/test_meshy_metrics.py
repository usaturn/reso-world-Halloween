"""W09: the measurements behind assets/meshy/received.json.

A wrong result here raises no error: the ledger would carry plausible but wrong sizes, openings or UV use, and the
area and finishing children (W02-W06, W09-M01..M08) would build to them.
"""

from __future__ import annotations

import numpy as np

from modeling.meshy import metrics


def test_placement_matrix_puts_origin_at_zero_scales_and_turns_front_to_plus_y() -> None:
    # A Meshy model faces Blender -Y. yaw 180 must turn that front to +Y after moving the origin and scaling.
    origin = [0.5, -0.25, -1.0]
    m = metrics.placement_matrix(origin, 180.0, 2.0)
    pts = metrics.transform_points(m, np.array([origin, [0.5, -1.25, -1.0], [1.5, -0.25, 0.0]]))
    np.testing.assert_allclose(pts[0], [0.0, 0.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(pts[1], [0.0, 2.0, 0.0], atol=1e-12)   # 1 unit in front (-Y) -> 2 m at +Y
    np.testing.assert_allclose(pts[2], [-2.0, 0.0, 2.0], atol=1e-12)  # +X turns to -X, up stays up
    # A quarter turn the other way: the -X nose of M06 must point to +Y with yaw -90.
    nose = metrics.transform_points(metrics.placement_matrix([0, 0, 0], -90.0, 1.0), np.array([[-1.0, 0.0, 0.0]]))
    np.testing.assert_allclose(nose[0], [0.0, 1.0, 0.0], atol=1e-12)


def test_uv_cover_sums_triangle_areas_and_counts_corners_outside() -> None:
    half = [[0, 0], [1, 0], [0, 1]]
    quarter = [[0, 0], [0.5, 0], [0, 0.5]]
    outside = [[1, 1], [2, 1], [1, 2]]
    cover = metrics.uv_cover(np.array([half, quarter, outside], dtype=float))
    assert abs(cover["area_sum"] - (0.5 + 0.125 + 0.5)) < 1e-12
    assert abs(cover["corners_in_unit_square"] - 7 / 9) < 1e-12


def test_occupancy_and_gaps_find_only_the_interior_opening() -> None:
    # Two 1 x 2 posts with a 2-unit passage between them, seen from the front (X across, Z up).
    def box(x0: float, x1: float) -> list:
        return [[[x0, 0, 0], [x1, 0, 0], [x1, 0, 2]], [[x0, 0, 0], [x1, 0, 2], [x0, 0, 2]]]

    tris = np.array(box(0, 1) + box(3, 4), dtype=float)
    grid = metrics.occupancy(tris, (0, 2), (0.0, 0.0), (4.0, 2.0), 0.1)
    spans = metrics.gaps(grid[5], min_pixels=2)
    assert len(spans) == 1
    start, end = spans[0]
    assert abs(start * 0.1 - 1.0) <= 0.15 and abs(end * 0.1 - 3.0) <= 0.15  # within 1.5 pixels
    assert metrics.gaps(np.array([False, True, True, False])) == []  # empty edges are not openings
