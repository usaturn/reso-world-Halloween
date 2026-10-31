"""Deterministic bmesh builder for the E_forest key (one builder = one mesh object, several material slots)."""

from __future__ import annotations

import math
import random
from typing import Iterable, Sequence

import bmesh  # type: ignore
import bpy  # type: ignore
from mathutils import Matrix, Vector  # type: ignore

Vec3 = Sequence[float]


class Wobble:
    """Smooth deterministic 3D noise made of a few seeded sine waves (no global RNG state)."""

    def __init__(self, seed: int, freq: float = 1.0, octaves: int = 4) -> None:
        rng = random.Random(seed)
        self.waves = []
        norm = 0.0
        for k in range(octaves):
            d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
            if d.length < 1e-3:
                d = Vector((1.0, 0.0, 0.0))
            d.normalize()
            amp = 1.0 / (k + 1)
            norm += amp
            self.waves.append((d, freq * (1.6**k) * rng.uniform(0.85, 1.25), rng.uniform(0.0, 2.0 * math.pi), amp))
        self.norm = norm

    def __call__(self, p: Vec3) -> float:
        v = Vector(p)
        return sum(a * math.sin(f * d.dot(v) + ph) for d, f, ph, a in self.waves) / self.norm


class MeshBuilder:
    """Accumulates closed primitives into one bmesh with per-face material slots."""

    def __init__(self) -> None:
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.materials: list = []
        self.ground = False  # True: clamp z < 0 to 0 so a ground_center shape sits exactly on z = 0

    # ------------------------------------------------------------------ basics
    def mat(self, material) -> int:
        for i, m in enumerate(self.materials):
            if m == material:
                return i
        self.materials.append(material)
        return len(self.materials) - 1

    def _faces(self, rings_faces: Iterable, material) -> None:
        mi = self.mat(material)
        for f in rings_faces:
            f.material_index = mi

    def _new_face(self, verts, material):
        f = self.bm.faces.new(verts)
        f.material_index = self.mat(material)
        return f

    # ------------------------------------------------------------- primitives
    def box(self, mn: Vec3, mx: Vec3, material, matrix: Matrix | None = None) -> None:
        """Axis-aligned box (optionally transformed by ``matrix``)."""
        x0, y0, z0 = mn
        x1, y1, z1 = mx
        pts = [
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
        ]
        if matrix is not None:
            pts = [tuple(matrix @ Vector(p)) for p in pts]
        v = [self.bm.verts.new(p) for p in pts]
        for idx in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7)):
            self._new_face([v[i] for i in idx], material)

    def obox(self, center: Vec3, size: Vec3, material, yaw_deg: float = 0.0, pitch_deg: float = 0.0, roll_deg: float = 0.0) -> None:
        """Box of ``size`` centred at ``center`` rotated by roll (X), pitch (Y), then yaw (Z)."""
        m = (
            Matrix.Translation(Vector(center))
            @ Matrix.Rotation(math.radians(yaw_deg), 4, "Z")
            @ Matrix.Rotation(math.radians(pitch_deg), 4, "Y")
            @ Matrix.Rotation(math.radians(roll_deg), 4, "X")
        )
        sx, sy, sz = (s * 0.5 for s in size)
        self.box((-sx, -sy, -sz), (sx, sy, sz), material, matrix=m)

    def beam(self, p0: Vec3, p1: Vec3, width: float, thickness: float, material) -> None:
        """Rectangular bar from ``p0`` to ``p1``; ``width`` is horizontal, ``thickness`` vertical-ish."""
        a, b = Vector(p0), Vector(p1)
        d = b - a
        length = d.length
        if length < 1e-6:
            return
        fwd = d.normalized()
        up = Vector((0.0, 0.0, 1.0))
        side = fwd.cross(up)
        if side.length < 1e-4:
            side = Vector((1.0, 0.0, 0.0))
        side.normalize()
        up2 = side.cross(fwd).normalized()
        m = Matrix(
            (
                (fwd.x, side.x, up2.x, a.x),
                (fwd.y, side.y, up2.y, a.y),
                (fwd.z, side.z, up2.z, a.z),
                (0.0, 0.0, 0.0, 1.0),
            )
        )
        self.box((0.0, -width / 2, -thickness / 2), (length, width / 2, thickness / 2), material, matrix=m)

    def tube(
        self,
        points: Sequence[Vec3],
        radii: Sequence[float] | float,
        material,
        segments: int = 8,
        cap_start: bool = True,
        cap_end: bool = True,
        wobble: Wobble | None = None,
        wobble_amp: float = 0.0,
        flatten: float = 1.0,
    ) -> None:
        """Tube along a polyline using parallel-transport frames; ``flatten`` < 1 squashes the binormal axis."""
        pts = [Vector(p) for p in points]
        n = len(pts)
        if isinstance(radii, (int, float)):
            radii = [float(radii)] * n
        tangents = []
        for i in range(n):
            if i == 0:
                t = pts[1] - pts[0]
            elif i == n - 1:
                t = pts[-1] - pts[-2]
            else:
                t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
            tangents.append(t.normalized())
        ref = Vector((0.0, 0.0, 1.0)) if abs(tangents[0].z) < 0.9 else Vector((1.0, 0.0, 0.0))
        normal = tangents[0].cross(ref).normalized()
        rings = []
        for i in range(n):
            if i > 0:
                axis = tangents[i - 1].cross(tangents[i])
                if axis.length > 1e-6:
                    ang = tangents[i - 1].angle(tangents[i])
                    normal = (Matrix.Rotation(ang, 3, axis.normalized()) @ normal).normalized()
            binormal = tangents[i].cross(normal).normalized()
            ring = []
            for s in range(segments):
                a = 2.0 * math.pi * s / segments
                off = normal * math.cos(a) + binormal * (math.sin(a) * flatten)
                r = radii[i]
                if wobble is not None and wobble_amp > 0.0:
                    r *= 1.0 + wobble_amp * wobble(pts[i] + off)
                ring.append(self.bm.verts.new(pts[i] + off * r))
            rings.append(ring)
        for i in range(n - 1):
            for s in range(segments):
                s2 = (s + 1) % segments
                self._new_face([rings[i][s], rings[i][s2], rings[i + 1][s2], rings[i + 1][s]], material)
        if cap_start:
            self._new_face(list(reversed(rings[0])), material)
        if cap_end:
            self._new_face(rings[-1], material)

    def lathe(
        self,
        profile: Sequence[tuple[float, float]],
        material,
        segments: int = 16,
        center: Vec3 = (0.0, 0.0, 0.0),
        jitter: float = 0.0,
        matrix: Matrix | None = None,
        wobble: Wobble | None = None,
        wobble_amp: float = 0.0,
    ) -> None:
        """Surface of revolution about local +Z. Profile is (radius, z) from bottom to top; r == 0 makes a pole.

        A profile that starts and ends on the axis is closed. ``jitter`` scales every other
        segment's radius by (1 - jitter) (drooping-branch silhouettes).
        """
        cx, cy, cz = center
        rows = []
        for r, z in profile:
            if r <= 1e-6:
                p = Vector((cx, cy, cz + z))
                if matrix is not None:
                    p = matrix @ p
                rows.append(self.bm.verts.new(p))
                continue
            ring = []
            for s in range(segments):
                a = 2.0 * math.pi * s / segments
                rr = r * (1.0 - jitter if (jitter and s % 2) else 1.0)
                p = Vector((cx + rr * math.cos(a), cy + rr * math.sin(a), cz + z))
                if wobble is not None and wobble_amp > 0.0:
                    p = Vector((cx, cy, cz + z)) + (p - Vector((cx, cy, cz + z))) * (1.0 + wobble_amp * wobble(p))
                if matrix is not None:
                    p = matrix @ p
                ring.append(self.bm.verts.new(p))
            rows.append(ring)
        for i in range(len(rows) - 1):
            a, b = rows[i], rows[i + 1]
            if isinstance(a, list) and isinstance(b, list):
                for s in range(segments):
                    s2 = (s + 1) % segments
                    self._new_face([a[s], a[s2], b[s2], b[s]], material)
            elif isinstance(a, list):
                for s in range(segments):
                    self._new_face([a[s], a[(s + 1) % segments], b], material)
            elif isinstance(b, list):
                for s in range(segments):
                    self._new_face([a, b[(s + 1) % segments], b[s]], material)
        if isinstance(rows[0], list):
            self._new_face(list(reversed(rows[0])), material)
        if isinstance(rows[-1], list):
            self._new_face(rows[-1], material)

    def blob(
        self,
        center: Vec3,
        radii: Vec3,
        material,
        subdiv: int = 2,
        noise: float = 0.15,
        seed: int = 0,
        freq: float = 2.2,
        flat_bottom: float | None = None,
        normal: Vec3 | None = None,
    ) -> None:
        """Lumpy ellipsoid (canopy, rock). ``flat_bottom`` clamps vertices below that local z.

        ``normal`` turns the ellipsoid's local +Z towards that direction (spots lying on a curved cap).
        """
        res = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=1.0, matrix=Matrix.Identity(4), calc_uvs=False)
        verts = res["verts"]
        w = Wobble(seed, freq=freq)
        c = Vector(center)
        rot = None
        if normal is not None:
            rot = Vector((0.0, 0.0, 1.0)).rotation_difference(Vector(normal).normalized()).to_matrix()
        for v in verts:
            p = v.co.copy()
            k = 1.0 + noise * w(p)
            q = Vector((p.x * radii[0] * k, p.y * radii[1] * k, p.z * radii[2] * k))
            if flat_bottom is not None and q.z < flat_bottom:
                q.z = flat_bottom
            if rot is not None:
                q = rot @ q
            v.co = c + q
        faces = {f for v in verts for f in v.link_faces}
        self._faces(faces, material)

    def mark(self) -> int:
        """Current vertex count; pass to ``transform_since`` to move everything built afterwards."""
        return len(self.bm.verts)

    def transform_since(self, mark: int, matrix: Matrix) -> None:
        self.bm.verts.ensure_lookup_table()
        for i in range(mark, len(self.bm.verts)):
            v = self.bm.verts[i]
            v.co = matrix @ v.co

    def prism(self, polygon: Sequence[tuple[float, float]], z0: float, z1: float, material, side_material=None) -> None:
        """Extrude a counter-clockwise XY polygon from z0 to z1 (closed)."""
        bot = [self.bm.verts.new((x, y, z0)) for x, y in polygon]
        top = [self.bm.verts.new((x, y, z1)) for x, y in polygon]
        n = len(polygon)
        self._new_face(list(reversed(bot)), material)
        self._new_face(top, material)
        sm = side_material if side_material is not None else material
        for i in range(n):
            j = (i + 1) % n
            self._new_face([bot[i], bot[j], top[j], top[i]], sm)

    def annulus(self, cx: float, cy: float, r0: float, r1: float, z0: float, z1: float, material, segments: int = 24) -> None:
        """Flat ring (r0 inner, r1 outer) from z0 to z1."""
        rings = []
        for r, z in ((r0, z0), (r1, z0), (r1, z1), (r0, z1)):
            rings.append(
                [self.bm.verts.new((cx + r * math.cos(2 * math.pi * s / segments), cy + r * math.sin(2 * math.pi * s / segments), z)) for s in range(segments)]
            )
        for k in range(4):
            a, b = rings[k], rings[(k + 1) % 4]
            for s in range(segments):
                s2 = (s + 1) % segments
                self._new_face([a[s], a[s2], b[s2], b[s]], material)

    # ----------------------------------------------------------------- output
    def to_object(self, name: str, collection, location: Vec3 = (0.0, 0.0, 0.0), rotation_deg: Vec3 = (0.0, 0.0, 0.0), parent=None):
        """Finish the bmesh into a mesh datablock and link a unit-scale object."""
        return mesh_object(name, collection, self.finish(f"{name}_Mesh"), location, rotation_deg, parent)

    def finish(self, mesh_name: str):
        """Recalculate outward normals, assign box-projected UVs (metres / 2) and build the mesh datablock."""
        bm = self.bm
        if self.ground:
            for v in bm.verts:
                if v.co.z < 0.0:
                    v.co.z = 0.0
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for face in bm.faces:
            n = face.normal
            ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
            for loop in face.loops:
                co = loop.vert.co
                if az >= ax and az >= ay:
                    uv = (co.x * 0.5, co.y * 0.5)
                elif ax >= ay:
                    uv = (co.y * 0.5, co.z * 0.5)
                else:
                    uv = (co.x * 0.5, co.z * 0.5)
                loop[self.uv].uv = uv
        mesh = bpy.data.meshes.new(mesh_name)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        for m in self.materials:
            mesh.materials.append(m)
        return mesh


def mesh_object(name: str, collection, mesh, location: Vec3 = (0.0, 0.0, 0.0), rotation_deg: Vec3 = (0.0, 0.0, 0.0), parent=None):
    """Link a unit-scale object that uses ``mesh`` (shared meshes give one series one datablock)."""
    obj = bpy.data.objects.new(name, mesh)
    obj.location = Vector(location)
    obj.rotation_euler = tuple(math.radians(a) for a in rotation_deg)
    obj.scale = (1.0, 1.0, 1.0)
    if parent is not None:
        obj.parent = parent
    collection.objects.link(obj)
    return obj


def empty(name: str, collection, location: Vec3 = (0.0, 0.0, 0.0), rotation_deg: Vec3 = (0.0, 0.0, 0.0), parent=None, size: float = 0.3):
    """Named unit-scale Empty (a Resonite Slot when it has mesh descendants)."""
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = size
    obj.location = Vector(location)
    obj.rotation_euler = tuple(math.radians(a) for a in rotation_deg)
    obj.scale = (1.0, 1.0, 1.0)
    if parent is not None:
        obj.parent = parent
    collection.objects.link(obj)
    return obj
