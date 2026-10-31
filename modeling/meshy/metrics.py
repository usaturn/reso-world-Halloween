"""Measurements on plain arrays (NumPy only), shared by the Blender scripts and the tests.

- ``uv_cover``: the share of the texture the UV triangles cover, as the sum of their areas (asakusa01's measure:
  overlapping islands count twice, so a value above 1 means overlap). The finishing aims at 0.6 or more.
- ``occupancy`` and ``gaps``: an orthographic silhouette of the triangles and the empty spans in one row of it, to
  measure openings such as a gate's passage without trusting a render by eye.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np

MAX_SAMPLES_PER_EDGE = 96


def uv_cover(uv: np.ndarray) -> dict[str, float]:
    """``uv`` is (F, 3, 2), one UV per triangle corner. Returns the summed UV area and the corner share in 0..1."""
    uv = np.asarray(uv, dtype=np.float64).reshape(-1, 3, 2)
    e1 = uv[:, 1] - uv[:, 0]
    e2 = uv[:, 2] - uv[:, 0]
    area = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) / 2.0
    corners = uv.reshape(-1, 2)
    inside = np.all((corners >= -1e-6) & (corners <= 1.0 + 1e-6), axis=1)
    return {"area_sum": float(area.sum()), "corners_in_unit_square": float(inside.mean()) if len(inside) else 1.0}


def _barycentric_grid(n: int) -> np.ndarray:
    """All (a, b, c) with a + b + c = 1 on an ``n``-step grid, (n+1)(n+2)/2 rows."""
    rows = [(i / n, j / n, (n - i - j) / n) for i in range(n + 1) for j in range(n + 1 - i)]
    return np.asarray(rows, dtype=np.float64)


def occupancy(
    tris: np.ndarray,
    axes: tuple[int, int],
    lo: tuple[float, float],
    hi: tuple[float, float],
    pixel: float,
) -> np.ndarray:
    """A boolean image of the triangles projected on ``axes`` (column axis, row axis), rows from ``lo[1]`` upward.

    Each triangle is sampled on a barycentric grid fine enough that neighbouring samples fall at most one pixel apart,
    so no pixel inside a triangle is missed.
    """
    tris = np.asarray(tris, dtype=np.float64)[:, :, list(axes)]
    width = max(1, int(np.ceil((hi[0] - lo[0]) / pixel)) + 1)
    height = max(1, int(np.ceil((hi[1] - lo[1]) / pixel)) + 1)
    grid = np.zeros((height, width), dtype=bool)
    edges = np.stack([tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 1], tris[:, 0] - tris[:, 2]], axis=1)
    longest = np.sqrt((edges**2).sum(axis=2)).max(axis=1) / pixel
    steps = np.clip(np.ceil(longest).astype(int) + 1, 1, MAX_SAMPLES_PER_EDGE)
    for n in np.unique(steps):
        sel = tris[steps == n]
        bary = _barycentric_grid(int(n))
        pts = np.einsum("pk,tkd->tpd", bary, sel).reshape(-1, 2)
        cols = np.clip(((pts[:, 0] - lo[0]) / pixel).round().astype(int), 0, width - 1)
        rows = np.clip(((pts[:, 1] - lo[1]) / pixel).round().astype(int), 0, height - 1)
        grid[rows, cols] = True
    return grid


def placement_matrix(origin: list[float] | np.ndarray, yaw_deg: float, scale: float) -> np.ndarray:
    """The 4 x 4 matrix W09 applies to a source GLB: move ``origin`` (GLB units, Blender axes after the glTF import)
    to (0, 0, 0), scale uniformly to metres, then turn ``yaw_deg`` about +Z (counter-clockwise seen from above)."""
    yaw = np.radians(float(yaw_deg))
    c, s = np.cos(yaw), np.sin(yaw)
    rot = np.array([[c, -s, 0.0, 0.0], [s, c, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]])
    scl = np.diag([float(scale), float(scale), float(scale), 1.0])
    move = np.eye(4)
    move[:3, 3] = -np.asarray(origin, dtype=np.float64)
    return rot @ scl @ move


def transform_points(matrix: np.ndarray, points: np.ndarray) -> np.ndarray:
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 3)
    return pts @ matrix[:3, :3].T + matrix[:3, 3]


def triangle_area_sum(tris: np.ndarray) -> float:
    tris = np.asarray(tris, dtype=np.float64).reshape(-1, 3, 3)
    return float(np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1).sum() / 2.0)


def gaps(row: np.ndarray, min_pixels: int = 1) -> list[tuple[int, int]]:
    """Empty spans ``[start, end)`` of ``row`` that have occupied pixels on both sides (interior gaps only)."""
    filled = np.flatnonzero(row)
    if len(filled) < 2:
        return []
    out = []
    for left, right in pairwise(filled):
        if right - left - 1 >= min_pixels:
            out.append((int(left) + 1, int(right)))
    return out
