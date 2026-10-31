"""Vegetation, mushrooms, face trees, bats and entrance pillars of the E_forest key.

Shapes are built in local coordinates (origin = ground centre or pivot, front = +Y). Reusable shapes are
cached meshes so that every individual of a series shares one mesh datablock.
"""

from __future__ import annotations

import math
from typing import Any

from mathutils import Matrix, Vector  # type: ignore

from modeling.E_forest.geo import MeshBuilder, Wobble, empty, mesh_object

_MESH_CACHE: dict[str, Any] = {}


def reset_cache() -> None:
    _MESH_CACHE.clear()


def _cached(name: str, factory):
    mesh = _MESH_CACHE.get(name)
    if mesh is None:
        mb = factory()
        mesh = mb.finish(name)
        _MESH_CACHE[name] = mesh
    return mesh


def _lantern(mb: MeshBuilder, P: dict, top: Vector, drop: float, size: float = 0.22) -> None:
    """Small hanging lantern: chain from ``top`` down ``drop`` metres, glowing body and iron cap."""
    body_c = top - Vector((0.0, 0.0, drop + size * 0.6))
    mb.tube([top, body_c + Vector((0.0, 0.0, size * 0.75))], 0.015, P["iron"], segments=4)
    mb.lathe([(0.0, 0.0), (size * 0.62, 0.0), (size * 0.12, size * 0.32), (0.0, size * 0.36)], P["iron"], segments=6,
             center=(body_c.x, body_c.y, body_c.z + size * 0.55))
    mb.obox(tuple(body_c), (size, size, size * 1.15), P["lantern_glow"], yaw_deg=45.0)
    mb.obox(tuple(body_c - Vector((0.0, 0.0, size * 0.62))), (size * 0.8, size * 0.8, 0.05), P["iron"], yaw_deg=45.0)


# =============================================================================== trees
def _tree_oak(P: dict) -> MeshBuilder:
    mb = MeshBuilder()
    mb.ground = True
    w = Wobble(11, freq=2.5)
    mb.tube([(0, 0, 0), (0.02, 0.0, 0.6), (0.08, 0.04, 1.6), (0.14, 0.06, 2.6), (0.12, 0.1, 3.4)],
            [0.48, 0.40, 0.34, 0.30, 0.25], P["bark"], segments=10, wobble=w, wobble_amp=0.10)
    for k in range(5):
        a = math.radians(k * 72 + 10)
        c, s = math.cos(a), math.sin(a)
        mb.tube([(0.15 * c, 0.15 * s, 0.45), (0.7 * c, 0.7 * s, 0.14), (1.2 * c, 1.2 * s, 0.06)], [0.17, 0.11, 0.05], P["bark"], segments=6)
    start = Vector((0.12, 0.08, 2.9))
    for end in ((1.7, 0.6, 4.6), (-1.5, 0.9, 4.8), (0.3, -1.6, 4.5), (-0.4, 1.3, 5.3)):
        e = Vector(end)
        mid = start * 0.4 + e * 0.6 + Vector((0.0, 0.0, 0.3))
        mb.tube([start, mid, e], [0.17, 0.12, 0.07], P["bark"], segments=6)
    for i, (c, r) in enumerate((
        ((0.0, 0.0, 6.1), (2.1, 2.0, 1.5)),
        ((1.8, 0.7, 5.2), (1.5, 1.4, 1.1)),
        ((-1.6, 0.9, 5.4), (1.5, 1.5, 1.1)),
        ((0.3, -1.7, 5.1), (1.5, 1.3, 1.1)),
        ((-0.5, 1.5, 6.0), (1.3, 1.2, 1.0)),
        ((1.0, -0.6, 6.6), (1.2, 1.2, 0.9)),
    )):
        mb.blob(c, r, P["leaf_teal"], subdiv=2, noise=0.16, seed=100 + i)
    return mb


def _tree_pine(P: dict) -> MeshBuilder:
    mb = MeshBuilder()
    mb.ground = True
    mb.tube([(0, 0, 0.3), (0, 0, 8.0)], [0.24, 0.06], P["bark"], segments=8)
    mb.lathe([(0.0, 0.0), (0.42, 0.0), (0.28, 0.35), (0.0, 0.55)], P["bark"], segments=8)
    for i in range(5):
        zb = 1.7 + i * 1.3
        rb = 1.75 - i * 0.29
        ht = 2.1 - i * 0.1
        mb.lathe(
            [(0.0, zb + 0.15), (rb * 0.85, zb - 0.12), (rb, zb + 0.02), (rb * 0.55, zb + ht * 0.45), (rb * 0.2, zb + ht * 0.82), (0.0, zb + ht)],
            P["leaf_pine"], segments=14, jitter=0.28, wobble=Wobble(200 + i, freq=1.8), wobble_amp=0.06,
        )
    return mb


def _tree_twist(P: dict) -> MeshBuilder:
    mb = MeshBuilder()
    mb.ground = True
    pts, radii = [], []
    for t in range(9):
        z = t * 0.55
        pts.append((0.32 * math.sin(t * 0.7), 0.32 * math.cos(t * 0.7) - 0.32, z))
        radii.append(0.38 - t * 0.03)
    mb.tube(pts, radii, P["bark"], segments=9, wobble=Wobble(31, freq=3.0), wobble_amp=0.1)
    for k in range(4):
        a = math.radians(k * 90 + 30)
        c, s = math.cos(a), math.sin(a)
        mb.tube([(0.12 * c, 0.12 * s, 0.35), (0.6 * c, 0.6 * s, 0.1), (0.95 * c, 0.95 * s, 0.05)], [0.14, 0.08, 0.04], P["bark"], segments=6)
    top = Vector(pts[-1])
    for end in ((1.3, 0.4, 3.7), (-1.0, 0.3, 4.6), (0.4, -0.9, 4.9)):
        e = Vector(end)
        mid = top * 0.5 + e * 0.5 + Vector((0.0, 0.0, 0.35))
        mb.tube([top - Vector((0, 0, 0.6)), mid, e], [0.13, 0.09, 0.05], P["bark"], segments=6)
    for i, (c, r) in enumerate((((0.2, -0.3, 5.0), (1.4, 1.3, 1.0)), ((-0.9, 0.2, 4.6), (1.0, 0.9, 0.8)), ((0.8, 0.5, 4.4), (0.9, 0.9, 0.7)))):
        mb.blob(c, r, P["leaf_purple"], subdiv=2, noise=0.18, seed=300 + i)
    _lantern(mb, P, Vector((1.25, 0.4, 3.62)), drop=0.25)
    return mb


def tree_mesh(kind: str, P: dict):
    factory = {"EFR_TreeOak": _tree_oak, "EFR_TreePine": _tree_pine, "EFR_TreeTwist": _tree_twist}[kind]
    return _cached(f"{kind}_Mesh", lambda: factory(P))


def rock_mesh(P: dict):
    def make() -> MeshBuilder:
        mb = MeshBuilder()
        mb.ground = True
        mb.blob((0.0, 0.0, 0.28), (0.85, 0.65, 0.5), P["stone"], subdiv=2, noise=0.28, seed=41, flat_bottom=-0.28)
        mb.blob((0.05, 0.0, 0.55), (0.6, 0.45, 0.17), P["moss"], subdiv=2, noise=0.3, seed=42)
        mb.blob((0.7, 0.35, 0.14), (0.32, 0.28, 0.2), P["stone"], subdiv=1, noise=0.25, seed=43, flat_bottom=-0.14)
        return mb

    return _cached("EFR_Rock_Mesh", make)


def bush_mesh(P: dict):
    def make() -> MeshBuilder:
        mb = MeshBuilder()
        mb.ground = True
        for i, (c, r, m) in enumerate((
            ((0.0, 0.0, 0.45), (0.7, 0.6, 0.5), "leaf_teal"),
            ((0.45, 0.2, 0.36), (0.5, 0.45, 0.38), "moss"),
            ((-0.42, 0.25, 0.34), (0.45, 0.4, 0.36), "leaf_teal"),
        )):
            mb.blob(c, r, P[m], subdiv=2, noise=0.2, seed=50 + i, flat_bottom=-c[2])
        return mb

    return _cached("EFR_Bush_Mesh", make)


# =============================================================================== mushrooms
MUSHROOM_TYPES = {
    # stem height h, stem radius rs, cap radius R, cap material, frill
    "Cluster": None,
    "Medium": (0.80, 0.11, 0.45, "cap_teal", False),
    "Tall": (1.90, 0.22, 1.00, "cap_purple", True),
    "Giant": (3.10, 0.38, 2.70, "cap_purple", True),
}
CLUSTER_MEMBERS = [((0.0, 0.0), 0.34, 0.06, 0.19), ((0.20, 0.10), 0.24, 0.045, 0.14), ((-0.13, 0.16), 0.19, 0.04, 0.11)]


def _cap_profile(h: float, R: float) -> list[tuple[float, float]]:
    return [(0.0, h - 0.02), (R * 0.92, h + 0.06 * R), (R, h + 0.16 * R), (R * 0.97, h + 0.26 * R), (R * 0.82, h + 0.48 * R),
            (R * 0.55, h + 0.66 * R), (R * 0.25, h + 0.74 * R), (0.0, h + 0.76 * R)]


def _cap_surface(h: float, R: float, r: float) -> tuple[float, float]:
    """(z, slope angle) of the cap's upper surface at radius ``r`` (piecewise linear on the profile)."""
    prof = list(reversed(_cap_profile(h, R)[2:]))  # top -> rim, radius increasing
    for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
        if r0 <= r <= r1:
            t = (r - r0) / max(r1 - r0, 1e-6)
            return z0 + t * (z1 - z0), math.atan2(z0 - z1, r1 - r0)
    return prof[-1][1], 0.0


def _mushroom_body(mb: MeshBuilder, P: dict, cx: float, cy: float, h: float, rs: float, R: float, cap: str, frill: bool) -> None:
    mb.lathe([(0.0, 0.0), (rs * 1.35, 0.0), (rs * 1.15, 0.08 * h), (rs, 0.35 * h), (rs * 0.92, 0.75 * h), (rs * 0.85, h), (0.0, h)],
             P["mush_stem"], segments=12, center=(cx, cy, 0.0))
    if frill:
        mb.lathe([(0.0, 0.58 * h), (rs * 1.9, 0.6 * h), (rs * 2.05, 0.64 * h), (0.0, 0.7 * h)], P["mush_stem"], segments=14, center=(cx, cy, 0.0))
    mb.lathe(_cap_profile(h, R), P[cap], segments=20, center=(cx, cy, 0.0))


def _mushroom_glow(mb: MeshBuilder, P: dict, cx: float, cy: float, h: float, R: float, seed: int, base_z: float) -> None:
    """Glowing gills under the cap and spots on it, relative to an origin at (0, 0, base_z)."""
    z = h - base_z
    mb.lathe([(0.0, z - 0.03), (R * 0.3, z - 0.025 + 0.02 * R), (R * 0.86, z - 0.02 + 0.07 * R), (R * 0.86, z - 0.005 + 0.072 * R), (0.0, z - 0.012)],
             P["mush_glow"], segments=18, center=(cx, cy, 0.0))
    rng_angles = [(0.0, 0.0), (0.45, 20.0), (0.5, 140.0), (0.55, 255.0), (0.78, 80.0), (0.8, 200.0), (0.76, 320.0)]
    for i, (f, adeg) in enumerate(rng_angles):
        r = R * f
        zc, slope = _cap_surface(h, R, r)
        a = math.radians(adeg + seed * 17)
        n = Vector((math.sin(slope) * math.cos(a), math.sin(slope) * math.sin(a), math.cos(slope)))
        size = R * (0.16 if f < 0.1 else 0.12)
        mb.blob((cx + r * math.cos(a), cy + r * math.sin(a), zc - base_z + 0.004), (size, size, max(0.012, size * 0.3)), P["mush_glow"],
                subdiv=1, noise=0.1, seed=seed * 10 + i, normal=tuple(n))


def mushroom_meshes(kind: str, P: dict) -> tuple[Any, Any, tuple[float, float, float]]:
    """(body mesh, glow mesh, glow origin in body-local coordinates) for a mushroom series."""
    if kind == "Cluster":
        attach = (0.0, 0.0, CLUSTER_MEMBERS[0][1])

        def body() -> MeshBuilder:
            mb = MeshBuilder()
            mb.ground = True
            for (x, y), h, rs, R in CLUSTER_MEMBERS:
                _mushroom_body(mb, P, x, y, h, rs, R, "cap_orange", False)
            return mb

        def glow() -> MeshBuilder:
            mb = MeshBuilder()
            for i, ((x, y), h, rs, R) in enumerate(CLUSTER_MEMBERS):
                _mushroom_glow(mb, P, x, y, h, R, seed=60 + i, base_z=attach[2])
            return mb
    else:
        h, rs, R, cap, frill = MUSHROOM_TYPES[kind]
        attach = (0.0, 0.0, h)

        def body() -> MeshBuilder:
            mb = MeshBuilder()
            mb.ground = True
            _mushroom_body(mb, P, 0.0, 0.0, h, rs, R, cap, frill)
            return mb

        def glow() -> MeshBuilder:
            mb = MeshBuilder()
            _mushroom_glow(mb, P, 0.0, 0.0, h, R, seed=70, base_z=h)
            return mb

    return _cached(f"EFR_Mushroom{kind}_Mesh", body), _cached(f"EFR_Mushroom{kind}Glow_Mesh", glow), attach


# =============================================================================== face tree (G17)
FACE_R = 0.92  # trunk radius at the face


def _on_trunk(x: float, z: float, lift: float) -> tuple[float, float, float]:
    return (x, math.sqrt(max((FACE_R + lift) ** 2 - x * x, 0.0)), z)


def _face_trunk(P: dict) -> MeshBuilder:
    mb = MeshBuilder()
    mb.ground = True
    w = Wobble(5, freq=2.0)
    mb.tube([(0, 0, 0), (0, 0.02, 0.7), (0, 0.04, 1.8), (0, 0.02, 2.9), (0, -0.06, 3.9), (0, -0.18, 4.8)],
            [1.15, 0.98, 0.92, 0.90, 0.82, 0.66], P["bark_face"], segments=16, wobble=w, wobble_amp=0.03)
    for k in range(7):
        a = math.radians(k * 51.4 + 115)
        c, s = math.cos(a), math.sin(a)
        mb.tube([(0.5 * c, 0.5 * s, 0.75), (1.3 * c, 1.3 * s, 0.3), (2.1 * c, 2.1 * s, 0.09)], [0.36, 0.24, 0.08], P["bark_face"], segments=7)
    start = Vector((0.0, -0.2, 4.5))
    for end in ((1.4, -1.2, 7.2), (-1.3, -1.0, 7.0), (0.1, -1.6, 7.6), (0.4, 0.2, 7.4)):
        e = Vector(end)
        mb.tube([start, start * 0.4 + e * 0.6 + Vector((0, 0, 0.2)), e], [0.38, 0.26, 0.14], P["bark_face"], segments=8)
    for i, (c, r, m) in enumerate((
        ((0.0, -0.8, 8.3), (2.4, 2.1, 1.6), "leaf_teal"),
        ((1.9, -0.9, 7.3), (1.7, 1.5, 1.2), "leaf_teal"),
        ((-1.9, -0.7, 7.4), (1.7, 1.5, 1.2), "leaf_teal"),
        ((0.2, -2.1, 7.2), (1.6, 1.4, 1.2), "leaf_purple"),
        ((0.9, 0.3, 8.0), (1.3, 1.2, 1.0), "leaf_teal"),
        ((-0.8, 0.2, 8.7), (1.3, 1.2, 1.0), "leaf_purple"),
    )):
        mb.blob(c, r, P[m], subdiv=2, noise=0.16, seed=500 + i)
    # Face: brow ridges, knot nose and dark eye sockets (the glowing eyes and mouth are separate objects).
    for s in (-1.0, 1.0):
        mb.tube([_on_trunk(s * 0.10, 3.36, 0.03), _on_trunk(s * 0.33, 3.30, 0.05), _on_trunk(s * 0.55, 3.14, 0.03)], [0.06, 0.08, 0.05],
                P["bark_face"], segments=6)
        x = s * 0.33
        n = Vector((x / FACE_R, math.sqrt(FACE_R**2 - x * x) / FACE_R, 0.0))
        mb.blob(_on_trunk(x, 3.0, 0.0), (0.24, 0.19, 0.08), P["face_socket"], subdiv=2, noise=0.05, seed=600 + int(s), normal=tuple(n))
    mb.blob(_on_trunk(0.0, 2.68, 0.02), (0.11, 0.15, 0.09), P["bark_face"], subdiv=1, noise=0.1, seed=610, normal=(0.0, 1.0, 0.0))
    return mb


def _face_eye(P: dict) -> MeshBuilder:
    """Eye in its pivot frame: +Y out of the trunk, blinks by scaling local Z."""
    mb = MeshBuilder()
    mb.blob((0.0, 0.0, 0.0), (0.16, 0.06, 0.13), P["face_glow"], subdiv=2, noise=0.0, seed=0)
    mb.blob((0.0, 0.052, -0.01), (0.06, 0.022, 0.065), P["face_socket"], subdiv=2, noise=0.0, seed=0)
    return mb


MOUTH_ORIGIN = (0.0, FACE_R + 0.05, 2.24)


def _face_mouth(P: dict) -> MeshBuilder:
    mb = MeshBuilder()
    o = Vector(MOUTH_ORIGIN)
    pts, radii = [], []
    for i in range(9):
        t = -1.0 + i * 0.25
        x = 0.40 * t
        pts.append(Vector(_on_trunk(x, 2.16 + 0.13 * t * t, 0.05)) - o)
        radii.append(0.085 - 0.03 * abs(t))
    mb.tube(pts, radii, P["face_glow"], segments=8, flatten=0.55)
    return mb


def _face_branch(P: dict, s: float) -> MeshBuilder:
    """Moving branch in its pivot frame (s = -1 left / +1 right). Pivot = junction with the trunk."""
    mb = MeshBuilder()
    mb.tube([(-s * 0.25, 0.0, -0.05), (s * 0.6, 0.05, 0.25), (s * 1.4, 0.12, 0.6), (s * 2.1, 0.1, 1.0), (s * 2.6, 0.05, 1.45)],
            [0.24, 0.2, 0.15, 0.1, 0.06], P["bark_face"], segments=8)
    mb.tube([(s * 1.4, 0.12, 0.6), (s * 1.9, 0.6, 0.7), (s * 2.2, 0.8, 0.95)], [0.07, 0.05, 0.03], P["bark_face"], segments=5)
    mb.blob((s * 2.55, 0.1, 1.75), (0.95, 0.85, 0.75), P["leaf_purple"], subdiv=2, noise=0.18, seed=700 + int(s))
    mb.blob((s * 2.15, 0.85, 1.15), (0.45, 0.4, 0.35), P["leaf_teal"], subdiv=2, noise=0.18, seed=710 + int(s))
    _lantern(mb, P, Vector((s * 1.75, 0.12, 0.72)), drop=0.35)
    return mb


BRANCH_PIVOTS = {"L": (-0.80, -0.05, 4.0), "R": (0.80, -0.05, 4.25)}
EYE_X = 0.33
EYE_Z = 3.0


def eye_pivot(s: float) -> tuple[tuple[float, float, float], float]:
    x = s * EYE_X
    y = math.sqrt((FACE_R + 0.09) ** 2 - x * x)
    yaw = math.degrees(math.atan2(-x, y))
    return (x, y, EYE_Z), yaw


def build_face_tree(col, P: dict, spec: dict) -> dict:
    """Face tree assembly: root Empty, trunk, two branch pivots, two eye pivots and the mouth."""
    name = spec["id"]
    x, y = spec["position"]
    root = empty(name, col, (x, y, 0.0), (0.0, 0.0, spec["rotation_z_deg"]), size=1.0)
    trunk_mesh = _cached("EFR_FaceTreeTrunk_Mesh", lambda: _face_trunk(P))
    eye_mesh = _cached("EFR_FaceTreeEye_Mesh", lambda: _face_eye(P))
    mouth_mesh = _cached("EFR_FaceTreeMouth_Mesh", lambda: _face_mouth(P))
    trunk = mesh_object(f"{name}_Trunk", col, parent=root, mesh=trunk_mesh)
    mouth = mesh_object(f"{name}_Mouth", col, location=MOUTH_ORIGIN, parent=root, mesh=mouth_mesh)
    parts = {"root": root, "trunk": trunk, "mouth": mouth, "branches": {}, "eyes": {}}
    for side, s in (("L", -1.0), ("R", 1.0)):
        bmesh_ = _cached(f"EFR_FaceTreeBranch{side}_Mesh", lambda s=s: _face_branch(P, s))
        piv = empty(f"{name}_Branch{side}Pivot", col, BRANCH_PIVOTS[side], parent=root, size=0.4)
        br = mesh_object(f"{name}_Branch{side}", col, parent=piv, mesh=bmesh_)
        parts["branches"][side] = (piv, br)
        loc, yaw = eye_pivot(s)
        epiv = empty(f"{name}_Eye{side}Pivot", col, loc, (0.0, 0.0, yaw), parent=root, size=0.2)
        eye = mesh_object(f"{name}_Eye{side}", col, parent=epiv, mesh=eye_mesh)
        parts["eyes"][side] = (epiv, eye)
    return parts


# =============================================================================== bats (G19)
BAT_SCALE = 1.1
WING_OUTLINE = [(0.0, 0.07), (-0.18, 0.13), (-0.40, 0.12), (-0.58, 0.04), (-0.52, -0.04), (-0.44, -0.02), (-0.36, -0.10),
                (-0.26, -0.05), (-0.16, -0.12), (-0.06, -0.05), (0.0, -0.05)]
WING_PIVOT_X = 0.10


def _bat_body(P: dict) -> MeshBuilder:
    k = BAT_SCALE
    mb = MeshBuilder()
    mb.blob((0.0, 0.0, 0.0), (0.13 * k, 0.15 * k, 0.16 * k), P["bat_body"], subdiv=2, noise=0.04, seed=80)
    mb.blob((0.0, 0.10 * k, 0.14 * k), (0.11 * k, 0.10 * k, 0.10 * k), P["bat_body"], subdiv=2, noise=0.03, seed=81)
    for s in (-1.0, 1.0):
        mb.lathe([(0.0, 0.0), (0.04 * k, 0.0), (0.0, 0.11 * k)], P["bat_wing"], segments=6, center=(s * 0.06 * k, 0.09 * k, 0.21 * k))
        mb.blob((s * 0.045 * k, 0.19 * k, 0.16 * k), (0.024 * k, 0.012 * k, 0.026 * k), P["bat_eye"], subdiv=1, noise=0.0, seed=0)
    return mb


def _bat_wing(P: dict, s: float) -> MeshBuilder:
    """Wing in its pivot frame (shoulder); s = -1 left (extends -X) / +1 right. Flaps about local +Y."""
    k = BAT_SCALE
    mb = MeshBuilder()
    poly = [(s * x * k, y * k) for x, y in WING_OUTLINE]
    if s > 0:
        poly = list(reversed(poly))
    mb.prism(poly, -0.012, 0.012, P["bat_wing"])
    mb.tube([(s * x * k, y * k, 0.01) for x, y in WING_OUTLINE[:4]], 0.016, P["bat_body"], segments=5)
    return mb


def build_bat(col, P: dict, name: str, parent, location, yaw_deg: float) -> dict:
    body_mesh = _cached("EFR_BatBody_Mesh", lambda: _bat_body(P))
    root = empty(name, col, location, (0.0, 0.0, yaw_deg), parent=parent, size=0.2)
    body = mesh_object(f"{name}_Body", col, parent=root, mesh=body_mesh)
    wings = {}
    for side, s in (("L", -1.0), ("R", 1.0)):
        wmesh = _cached(f"EFR_BatWing{side}_Mesh", lambda s=s: _bat_wing(P, s))
        piv = empty(f"{name}_Wing{side}Pivot", col, (s * WING_PIVOT_X * BAT_SCALE, 0.0, 0.04), parent=root, size=0.1)
        wing = mesh_object(f"{name}_Wing{side}", col, parent=piv, mesh=wmesh)
        wings[side] = (piv, wing)
    return {"root": root, "body": body, "wings": wings}


# =============================================================================== entrance pillars
def gate_pillar_mesh(P: dict):
    def make() -> MeshBuilder:
        mb = MeshBuilder()
        mb.ground = True
        w = Wobble(91, freq=3.0)
        mb.tube([(0, 0, 0), (0.05, 0.02, 0.8), (-0.04, 0.05, 1.6), (0.02, 0.0, 2.4), (0.1, -0.05, 2.75)],
                [0.42, 0.32, 0.28, 0.24, 0.18], P["bark"], segments=10, wobble=w, wobble_amp=0.12)
        for k in range(4):
            a = math.radians(k * 90 + 45)
            c, s = math.cos(a), math.sin(a)
            mb.tube([(0.2 * c, 0.2 * s, 0.4), (0.6 * c, 0.6 * s, 0.1), (0.85 * c, 0.85 * s, 0.05)], [0.16, 0.09, 0.04], P["bark"], segments=6)
        mb.tube([(0.1, -0.05, 2.6), (0.05, 0.35, 2.95), (0.0, 0.62, 2.85), (0.0, 0.66, 2.62)], [0.1, 0.08, 0.06, 0.05], P["bark"], segments=6)
        _lantern(mb, P, Vector((0.0, 0.66, 2.62)), drop=0.12, size=0.24)
        for sx in (-1.0, 1.0):  # sign boards on both sides (east-facing whichever way the pillar turns)
            mb.obox((sx * 0.36, 0.0, 1.55), (0.06, 0.78, 0.42), P["plank"])
            mb.blob((sx * 0.40, 0.0, 1.57), (0.03, 0.14, 0.14), P["lantern_glow"], subdiv=1, noise=0.0, seed=0, normal=(sx, 0.0, 0.0))
        for (x, y), h, rs, R in ((( 0.45, 0.35), 0.30, 0.05, 0.17), ((0.62, 0.18), 0.22, 0.04, 0.12), ((-0.5, -0.35), 0.26, 0.05, 0.15)):
            _mushroom_body(mb, P, x, y, h, rs, R, "cap_orange", False)
        return mb

    return _cached("EFR_GatePillar_Mesh", make)
