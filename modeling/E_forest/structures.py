"""Boardwalks, pond, pond bridge, lookout and rest spot of the E_forest key (walkable static structures)."""

from __future__ import annotations

import math

from mathutils import Matrix, Vector  # type: ignore

from modeling.E_forest import layout as L
from modeling.E_forest.geo import MeshBuilder, Wobble

RAMP_LEN = 1.0
PLANK_PITCH = 0.32


# =============================================================================== boardwalk
def _deck_z(t: float, length: float, ramps: tuple[str, ...], z_top: float) -> float:
    """Deck top at distance ``t`` from the segment start (ramps come down to 0.03 m at a ramp end)."""
    z = z_top
    if "p0" in ramps and t < RAMP_LEN:
        z = 0.03 + (z_top - 0.03) * max(t, 0.0) / RAMP_LEN
    if "p1" in ramps and t > length - RAMP_LEN:
        z = 0.03 + (z_top - 0.03) * max(length - t, 0.0) / RAMP_LEN
    return z


def _in_opening(openings, side: str, t: float) -> bool:
    return any(s == side and a <= t <= b for s, a, b in openings)


def boardwalk(P: dict, length: float, width: float, z_top: float, ramps: tuple[str, ...], openings) -> MeshBuilder:
    """Boardwalk in a local frame running along +X from -length/2 to +length/2 (left = +Y)."""
    mb = MeshBuilder()
    mb.ground = True
    half = length / 2.0
    hw = width / 2.0

    def zt(t: float) -> float:
        return _deck_z(t, length, ramps, z_top)

    n = max(1, int(round(length / PLANK_PITCH)))
    step = length / n
    for i in range(n):
        t = (i + 0.5) * step
        z = zt(t)
        slope = (zt(min(length, t + 0.05)) - zt(max(0.0, t - 0.05))) / 0.1
        mb.obox((t - half, 0.0, z - 0.025), (step - 0.035, width, 0.05), P["plank"], pitch_deg=-math.degrees(math.atan(slope)))
    # Stringers and side skirts follow the deck profile.
    knots = sorted({0.0, length} | ({RAMP_LEN} if "p0" in ramps else set()) | ({length - RAMP_LEN} if "p1" in ramps else set()))
    for a, b in zip(knots, knots[1:]):
        for y in (-hw + 0.15, hw - 0.15):
            mb.beam((a - half, y, max(zt(a) - 0.12, 0.03)), (b - half, y, max(zt(b) - 0.12, 0.03)), 0.12, 0.10, P["plank_dark"])
    for side, y in (("right", -hw - 0.03), ("left", hw + 0.03)):
        cuts = sorted({0.0, length} | {k for k in knots} | {v for s, a, b in openings if s == side for v in (a, b)})
        for a, b in zip(cuts, cuts[1:]):
            mid = 0.5 * (a + b)
            if _in_opening(openings, side, mid) or b - a < 1e-3:
                continue
            za, zb = zt(a) + 0.04, zt(b) + 0.04
            mb.beam((a - half, y, za * 0.5), (b - half, y, zb * 0.5), 0.06, 0.5 * (za + zb), P["plank_dark"])
    # Short edge posts every 2.4 m; every other one carries a small glowing cap.
    k = 0
    t = 0.6
    while t < length - 0.3:
        for side, y in (("right", -hw - 0.12), ("left", hw + 0.12)):
            if _in_opening(openings, side, t):
                continue
            z = zt(t)
            mb.box((t - half - 0.06, y - 0.06, 0.0), (t - half + 0.06, y + 0.06, z + 0.5), P["plank_dark"])
            if k % 2 == 0:
                mb.box((t - half - 0.05, y - 0.05, z + 0.5), (t - half + 0.05, y + 0.05, z + 0.6), P["lantern_glow"])
            else:
                mb.lathe([(0.0, 0.0), (0.09, 0.0), (0.0, 0.12)], P["plank_dark"], segments=4, center=(t - half, y, z + 0.5))
        k += 1
        t += 2.4
    return mb


def walk_frame(p0, p1) -> tuple[tuple[float, float, float], float, float]:
    """(object location, rotation_z_deg, length) of a straight boardwalk from p0 to p1 (XY)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    return ((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0, 0.0), math.degrees(math.atan2(dy, dx)), math.hypot(dx, dy)


# =============================================================================== pond bridge
def pond_bridge(P: dict, length: float, width: float, rise: float) -> MeshBuilder:
    """Arched footbridge along +X (-length/2..+length/2) with 1.05 m handrails on both sides."""
    mb = MeshBuilder()
    mb.ground = True
    half = length / 2.0
    z0 = L.DECK_Z

    def zt(x: float) -> float:
        return z0 + rise * math.cos(math.pi * x / length)

    n = int(round(length / PLANK_PITCH))
    step = length / n
    for i in range(n):
        x = -half + (i + 0.5) * step
        slope = -rise * math.pi / length * math.sin(math.pi * x / length)
        mb.obox((x, 0.0, zt(x) - 0.03), (step - 0.03, width + 0.2, 0.06), P["plank"], pitch_deg=-math.degrees(math.atan(slope)))
    xs = [-half + i * length / 12 for i in range(13)]
    for y in (-0.85, 0.85):
        for a, b in zip(xs, xs[1:]):
            mb.beam((a, y, zt(a) - 0.13), (b, y, zt(b) - 0.13), 0.14, 0.14, P["plank_dark"])
    for y in (-1.22, 1.22):  # arched side ribs down to the banks
        pts = [(x, y, max(0.02, (z0 + rise - 0.22) * math.cos(math.pi * x / length) - 0.05)) for x in xs]
        for a, b in zip(pts, pts[1:]):
            mb.beam(a, b, 0.12, 0.2, P["plank_dark"])
    for sx in (-1.0, 1.0):  # stone abutments on the banks
        mb.box((sx * half - 0.6 if sx > 0 else -half, -1.35, 0.0), (half if sx > 0 else -half + 0.6, 1.35, z0 - 0.06), P["stone"])
    posts = [-half + 0.15 + i * (length - 0.3) / 6 for i in range(7)]
    for y in (-1.2, 1.2):
        for i, x in enumerate(posts):
            top = 1.45 if i in (0, len(posts) - 1) else 1.05
            mb.box((x - 0.06, y - 0.06, zt(x) - 0.06), (x + 0.06, y + 0.06, zt(x) + top), P["plank_dark"])
            if top > 1.1:
                mb.obox((x, y, zt(x) + top + 0.11), (0.2, 0.2, 0.22), P["lantern_glow"], yaw_deg=45.0)
                mb.lathe([(0.0, 0.0), (0.17, 0.0), (0.0, 0.16)], P["iron"], segments=4, center=(x, y, zt(x) + top + 0.22))
        for a, b in zip(posts, posts[1:]):
            mb.beam((a, y, zt(a) + 1.0), (b, y, zt(b) + 1.0), 0.1, 0.08, P["plank"])
            mb.beam((a, y, zt(a) + 0.55), (b, y, zt(b) + 0.55), 0.06, 0.06, P["plank_dark"])
            # Rope swag between the rails.
            mid = (0.5 * (a + b), y, 0.5 * (zt(a) + zt(b)) + 0.72)
            mb.tube([(a, y, zt(a) + 0.95), mid, (b, y, zt(b) + 0.95)], 0.02, P["rope"], segments=4)
    return mb


# =============================================================================== pond
def pond_outline(scale: float = 1.0) -> list[tuple[float, float]]:
    """Counter-clockwise outline relative to the pond centre."""
    a, b = L.POND["semi_axes"]
    w = Wobble(77, freq=1.3)
    pts = []
    for i in range(28):
        t = 2.0 * math.pi * i / 28
        k = 1.0 + 0.06 * w((math.cos(t), math.sin(t), 0.0))
        pts.append((a * k * scale * math.cos(t), b * k * scale * math.sin(t)))
    return pts


def pond_rim(P: dict, bridge_x_local: float) -> MeshBuilder:
    """Mossy bank, stones (left out where the bridge crosses), lily pads, reeds and glowing lilies."""
    mb = MeshBuilder()
    mb.ground = True
    mb.prism(pond_outline(1.13), 0.0, 0.04, P["moss"])
    rim = pond_outline(1.04)
    for i, (x, y) in enumerate(rim):
        if abs(x - bridge_x_local) < 1.7 or i % 2:
            continue
        r = 0.32 + 0.12 * ((i * 37) % 5) / 4.0
        mb.blob((x, y, 0.1), (r, r * 0.8, 0.16 + 0.08 * ((i * 13) % 3) / 2), P["stone" if i % 4 else "moss"], subdiv=2, noise=0.25, seed=900 + i,
                flat_bottom=-0.1)
    for i, (x, y, r) in enumerate(((-2.6, 0.6, 0.32), (-1.9, -0.9, 0.26), (2.4, 0.9, 0.3), (2.9, -0.4, 0.25), (-0.4, 1.4, 0.22), (1.6, -1.3, 0.28))):
        mb.lathe([(0.0, 0.075), (r, 0.075), (r, 0.088), (0.0, 0.088)], P["lily"], segments=10, center=(x, y, 0.0))
        if i % 2 == 0:
            mb.blob((x + 0.05, y, 0.13), (0.09, 0.09, 0.07), P["mush_glow"], subdiv=1, noise=0.2, seed=950 + i)
    for i, (x, y) in enumerate(((-3.9, 1.0), (-3.7, 1.5), (3.6, -1.6), (3.9, -1.1))):
        mb.tube([(x, y, 0.0), (x + 0.05, y, 0.9 + 0.1 * (i % 2))], 0.025, P["moss"], segments=4)
        mb.tube([(x + 0.04, y, 0.62), (x + 0.05, y, 0.85)], 0.05, P["plank_dark"], segments=6)
    return mb


def pond_water(P: dict) -> MeshBuilder:
    mb = MeshBuilder()
    mb.ground = True
    mb.prism(pond_outline(1.0), 0.0, L.POND["water_top"], P["water"])
    return mb


# =============================================================================== lookout
def _rail_run(mb: MeshBuilder, P: dict, a, b, z_a: float, z_b: float, height: float = 1.05) -> None:
    """Handrail from a to b (XY) whose foot follows z_a..z_b: posts every ~1.2 m, top and mid rails."""
    ax, ay = a
    bx, by = b
    length = math.hypot(bx - ax, by - ay)
    n = max(1, int(math.ceil(length / 1.2)))
    for i in range(n + 1):
        t = i / n
        x, y, z = ax + t * (bx - ax), ay + t * (by - ay), z_a + t * (z_b - z_a)
        mb.box((x - 0.06, y - 0.06, z - 0.02), (x + 0.06, y + 0.06, z + height + 0.05), P["plank_dark"])
    mb.beam((ax, ay, z_a + height), (bx, by, z_b + height), 0.1, 0.08, P["plank"])
    mb.beam((ax, ay, z_a + 0.55), (bx, by, z_b + 0.55), 0.06, 0.06, P["plank_dark"])


def lookout(P: dict) -> MeshBuilder:
    """Raised lookout deck (z 0.75) with two ramps, railings, a witch-hat roof and a telescope; local origin = deck centre on the ground."""
    mb = MeshBuilder()
    mb.ground = True
    cx, cy = L.LOOKOUT["center"]
    sx, sy = L.LOOKOUT["size"]
    hx, hy = sx / 2.0, sy / 2.0
    zd = L.LOOKOUT_DECK_Z
    hw = L.WALK_W / 2.0
    # Deck, skirt and posts.
    for i in range(int(round(sx / 0.3))):
        x = -hx + (i + 0.5) * sx / round(sx / 0.3)
        mb.box((x - 0.13, -hy, zd - 0.06), (x + 0.13, hy, zd), P["plank"])
    mb.box((-hx + 0.05, -hy + 0.05, 0.0), (hx - 0.05, hy - 0.05, zd - 0.06), P["plank_dark"])
    for x in (-hx, hx):
        for y in (-hy, 0.0, hy):
            mb.box((x - 0.12, y - 0.12, 0.0), (x + 0.12, y + 0.12, zd + 0.02), P["stone"])
    # Ramps (east: from the north boardwalk; south: down to the west boardwalk).
    e0, e1 = L.LOOKOUT["ramp_east"]["p0"], L.LOOKOUT["ramp_east"]["p1"]
    ex0, ex1 = e0[0] - cx, e1[0] - cx
    s0, s1 = L.LOOKOUT["ramp_south"]["p0"], L.LOOKOUT["ramp_south"]["p1"]
    sy0, sy1 = s0[1] - cy, s1[1] - cy
    n = 14
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        za, zb = L.DECK_Z + (zd - L.DECK_Z) * t0, L.DECK_Z + (zd - L.DECK_Z) * t1
        xa, xb = ex0 + (ex1 - ex0) * t0, ex0 + (ex1 - ex0) * t1
        mb.box((min(xa, xb) + 0.015, -hw, 0.0), (max(xa, xb) - 0.015, hw, 0.5 * (za + zb)), P["plank"])
        ya, yb = sy1 + (sy0 - sy1) * t0, sy1 + (sy0 - sy1) * t1
        mb.box((-hw, min(ya, yb) + 0.015, 0.0), (hw, max(ya, yb) - 0.015, 0.5 * (za + zb)), P["plank"])
    for y in (-hw - 0.08, hw + 0.08):
        _rail_run(mb, P, (ex0, y), (ex1, y), L.DECK_Z, zd)
    for x in (-hw - 0.08, hw + 0.08):
        _rail_run(mb, P, (x, sy1), (x, sy0), L.DECK_Z, zd)
    # Deck railings, leaving the two ramp mouths open.
    _rail_run(mb, P, (-hx, -hy), (-hx, hy), zd, zd)
    _rail_run(mb, P, (-hx, hy), (hx, hy), zd, zd)
    _rail_run(mb, P, (hx, hy), (hx, hw + 0.08), zd, zd)
    _rail_run(mb, P, (hx, -hw - 0.08), (hx, -hy), zd, zd)
    _rail_run(mb, P, (-hx, -hy), (-hw - 0.08, -hy), zd, zd)
    _rail_run(mb, P, (hw + 0.08, -hy), (hx, -hy), zd, zd)
    # Witch-hat roof on four corner posts.
    roof_z = zd + 2.75
    for x in (-hx + 0.22, hx - 0.22):
        for y in (-hy + 0.22, hy - 0.22):
            mb.tube([(x, y, zd), (x, y, roof_z + 0.05)], 0.09, P["plank_dark"], segments=8)
            mb.beam((x, y, roof_z - 0.55), (x * 0.55, y * 0.55, roof_z - 0.02), 0.08, 0.08, P["plank_dark"])
    mb.lathe([(0.0, roof_z), (2.95, roof_z), (2.95, roof_z + 0.1), (2.0, roof_z + 0.2), (0.0, roof_z + 0.22)], P["roof_purple"], segments=20)
    mb.lathe([(0.0, roof_z + 0.18), (1.95, roof_z + 0.18), (1.35, roof_z + 1.2), (0.75, roof_z + 2.15), (0.3, roof_z + 2.85), (0.0, roof_z + 3.1)],
             P["roof_purple"], segments=18, wobble=Wobble(33, freq=1.5), wobble_amp=0.04)
    mb.annulus(0.0, 0.0, 1.62, 1.75, roof_z + 0.45, roof_z + 0.72, P["roof_band"], segments=18)
    mb.tube([(0.0, 0.0, roof_z + 2.95), (0.2, 0.12, roof_z + 3.35), (0.55, 0.32, roof_z + 3.5), (0.8, 0.45, roof_z + 3.35)],
            [0.2, 0.13, 0.07, 0.03], P["roof_purple"], segments=8)
    lantern_top = Vector((0.0, 0.0, roof_z + 0.18))
    mb.tube([lantern_top, lantern_top - Vector((0.0, 0.0, 0.42))], 0.02, P["iron"], segments=4)
    mb.obox((0.0, 0.0, roof_z - 0.42), (0.3, 0.3, 0.38), P["lantern_glow"], yaw_deg=45.0)
    mb.lathe([(0.0, 0.0), (0.26, 0.0), (0.0, 0.18)], P["iron"], segments=6, center=(0.0, 0.0, roof_z - 0.22))
    # Brass telescope on a tripod in the north-west corner, aimed west over the cliff.
    tx, ty = -hx + 0.55, hy - 0.55
    apex = Vector((tx, ty, zd + 1.15))
    for k in range(3):
        a = math.radians(k * 120 + 30)
        mb.tube([(tx + 0.42 * math.cos(a), ty + 0.42 * math.sin(a), zd), apex], 0.025, P["plank_dark"], segments=4)
    mb.tube([apex + Vector((0.32, -0.04, -0.12)), apex + Vector((-0.55, 0.08, 0.2))], [0.08, 0.055], P["brass"], segments=10)
    return mb


# =============================================================================== rest spot
def rest_deck(P: dict) -> MeshBuilder:
    """Round wooden rest deck (z 0.20) with a darker rim and inlaid spokes; origin = centre on the ground."""
    mb = MeshBuilder()
    mb.ground = True
    r = L.REST_SPOT["radius"]
    z = L.REST_DECK_Z
    ring = [(r * 0.955 * math.cos(2 * math.pi * i / 28), r * 0.955 * math.sin(2 * math.pi * i / 28)) for i in range(28)]
    mb.prism(ring, 0.0, z, P["plank"])
    mb.annulus(0.0, 0.0, r * 0.95, r, 0.0, z + 0.04, P["plank_dark"], segments=28)
    for k in range(12):
        a = math.radians(k * 30 + 15)
        mb.beam((0.65 * math.cos(a), 0.65 * math.sin(a), z + 0.004), ((r - 0.25) * math.cos(a), (r - 0.25) * math.sin(a), z + 0.004),
                0.06, 0.012, P["plank_dark"])
    return mb


def flat_matrix(rz_deg: float) -> Matrix:
    return Matrix.Rotation(math.radians(rz_deg), 4, "Z")
