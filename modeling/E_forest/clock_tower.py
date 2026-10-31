"""M07 magical clock tower placeholder (G20) in the tower's local frame (front = +Y, origin = ground centre).

The outline follows W09's decided M07 values (`assets/meshy/received.json`): 8.239 x 7.578 x 14.0 m, rocky
pedestal, castle base with front stairs and door, tower shaft, clock storey, belfry and a spire set back to
y ~ -0.8, plus the tilted orbit ring. The dial centre (clock axis) is W09's ``dial_centre_face``.
The body is the only part M07 replaces; the dial placeholder, hands and bell stay separate objects.
"""

from __future__ import annotations

import math

from mathutils import Matrix, Vector  # type: ignore

from modeling.E_forest.geo import MeshBuilder, Wobble

# W09 decided values (placed local, metres).
M07_DIMENSIONS = (8.239, 7.578, 14.0)
M07_BOUNDS = {"min": (-4.119, -3.789, 0.0), "max": (4.12, 3.789, 14.0)}
DIAL_CENTRE = (0.001, 0.364, 8.095)  # dial_centre_face: clock axis on the dial face, axis along +Y
DIAL_OUTER_R = 1.144  # 2.29 m outer diameter (rim front at y 0.556)
DIAL_RIM_FRONT_Y = 0.556
HOUR_HAND_PIVOT = (DIAL_CENTRE[0], DIAL_CENTRE[1] + 0.055, DIAL_CENTRE[2])
MINUTE_HAND_PIVOT = (DIAL_CENTRE[0], DIAL_CENTRE[1] + 0.095, DIAL_CENTRE[2])
BELL_PIVOT = (DIAL_CENTRE[0], 1.45, 10.95)

RX_TO_FRONT = Matrix.Rotation(math.radians(-90.0), 4, "X")  # local +Z -> +Y (lathe axis to the dial axis)
RX_PLATE = Matrix.Rotation(math.radians(90.0), 4, "X")  # XY polygon -> XZ plane, extrusion -Z -> +Y


def _fit_xy(mb: MeshBuilder, mark: int, bounds: dict) -> None:
    """Scale and shift the vertices built since ``mark`` in X and Y so their extent equals ``bounds``."""
    mb.bm.verts.ensure_lookup_table()
    vs = [mb.bm.verts[i] for i in range(mark, len(mb.bm.verts))]
    for axis in (0, 1):
        lo, hi = min(v.co[axis] for v in vs), max(v.co[axis] for v in vs)
        tlo, thi = bounds["min"][axis], bounds["max"][axis]
        k = (thi - tlo) / (hi - lo)
        for v in vs:
            v.co[axis] = tlo + (v.co[axis] - lo) * k


def tower_body(P: dict) -> MeshBuilder:
    mb = MeshBuilder()
    mb.ground = True
    # Rocky pedestal with boulders, then fitted to the decided M07 footprint (x -4.119..4.12, y -3.789..3.789).
    mark = mb.mark()
    mb.lathe([(0.0, 0.0), (1.0, 0.0), (0.97, 0.45), (0.9, 1.0), (0.78, 1.55), (0.0, 1.62)], P["tower_rock"], segments=18,
             matrix=Matrix.Diagonal((3.98, 3.68, 1.0, 1.0)), wobble=Wobble(401, freq=2.5), wobble_amp=0.03)
    for i in range(9):
        a = math.radians(i * 40 + 12)
        if abs(math.degrees(a) % 360 - 90) < 25:  # keep the stairs clear
            continue
        c = (3.15 * math.cos(a), 2.85 * math.sin(a), 0.55)
        mb.blob(c, (0.85, 0.75, 0.6), P["tower_rock"], subdiv=2, noise=0.22, seed=410 + i, flat_bottom=-0.55)
    _fit_xy(mb, mark, M07_BOUNDS)
    for i, (x, y) in enumerate(((-2.6, 1.6), (2.4, 1.8), (-3.0, -1.2), (2.9, -0.8), (0.4, -2.9))):
        mb.blob((x, y, 1.5), (0.8, 0.6, 0.12), P["moss"], subdiv=2, noise=0.25, seed=430 + i)
    # Castle base with cornice, battlements, door and lit windows.
    stone, roof, glow, gold = P["tower_stone"], P["tower_roof"], P["tower_window"], P["gold"]
    mb.box((-3.0, -2.3, 1.45), (3.0, 0.9, 4.9), stone)
    mb.box((-3.15, -2.45, 4.75), (3.15, 1.05, 4.95), stone)
    for i in range(8):
        x = -2.8 + i * 0.8
        mb.box((x - 0.17, 0.82, 4.95), (x + 0.17, 1.05, 5.28), stone)
        mb.box((x - 0.17, -2.45, 4.95), (x + 0.17, -2.22, 5.28), stone)
    mb.obox((0.0, 0.92, 2.35), (1.3, 0.1, 1.8), stone)
    mb.obox((0.0, 0.97, 2.22), (0.95, 0.06, 1.45), P["plank_dark"])
    mb.lathe([(0.0, 0.0), (0.48, 0.0), (0.48, 0.06), (0.0, 0.06)], P["plank_dark"], segments=12, center=(0.0, 0.0, 0.0),
             matrix=Matrix.Translation((0.0, 0.94, 2.95)) @ RX_TO_FRONT)
    mb.blob((0.0, 1.02, 2.3), (0.06, 0.03, 0.06), gold, subdiv=1, noise=0.0, seed=0)
    for x in (-1.75, 1.75):
        mb.obox((x, 0.93, 3.3), (0.45, 0.06, 0.8), glow)
        mb.obox((x, 0.92, 3.3), (0.62, 0.05, 1.0), stone)
    # Front stairs down to the ground.
    for i in range(8):
        y0 = 0.95 + 0.35 * i
        mb.box((-1.0, y0, 0.0), (1.0, y0 + 0.35, 1.5 - i * 0.1875), stone)
    for x in (-1.12, 1.12):
        mb.beam((x, 0.95, 1.75), (x, 3.55, 0.45), 0.22, 0.42, stone)
    # Corner turrets with pointed roofs.
    for x in (-2.75, 2.75):
        for y in (0.62, -2.0):
            mb.lathe([(0.0, 1.45), (0.55, 1.45), (0.55, 5.2), (0.68, 5.25), (0.68, 5.45), (0.0, 5.45)], stone, segments=12, center=(x, y, 0.0))
            mb.lathe([(0.0, 5.45), (0.75, 5.45), (0.32, 6.3), (0.0, 6.95)], roof, segments=12, center=(x, y, 0.0))
            mb.tube([(x, y, 6.9), (x, y, 7.25)], 0.03, gold, segments=4)
            if y > 0:
                mb.obox((x, y + 0.55, 3.6), (0.18, 0.06, 0.5), glow)
    # Shaft with banner, clock storey, gable, belfry and spire.
    mb.box((-1.5, -2.0, 4.9), (1.5, 0.22, 7.0), stone)
    for x in (-1.5, 1.5):
        mb.box((x - 0.15, 0.1, 4.9), (x + 0.15, 0.32, 7.0), stone)
    mb.obox((0.0, 0.25, 5.9), (0.8, 0.04, 1.6), roof)
    mb.blob((0.0, 0.29, 6.1), (0.18, 0.03, 0.18), gold, subdiv=1, noise=0.0, seed=0)
    mb.box((-1.85, -1.95, 7.0), (1.85, 0.30, 9.6), stone)
    mb.box((-1.95, -2.05, 9.5), (1.95, 0.4, 9.66), stone)
    mark = mb.mark()
    mb.prism([(-1.85, 0.0), (1.85, 0.0), (0.0, 1.0)], -0.2, 0.0, stone)
    mb.transform_since(mark, Matrix.Translation((0.0, 0.30 - 0.2, 9.66)) @ RX_PLATE)
    for sx in (-1.0, 1.0):
        mb.obox((sx * 0.98, -0.8, 10.12), (2.15, 2.75, 0.14), roof, pitch_deg=sx * 28.0)
    mb.box((-1.45, -1.8, 9.66), (1.45, 0.2, 11.3), stone)
    mb.obox((0.0, 0.22, 10.5), (0.7, 0.04, 1.0), P["face_socket"])
    for x in (-1.47, 1.47):
        mb.obox((x, -0.8, 10.5), (0.04, 0.7, 1.0), P["face_socket"])
    for x in (-1.45, 1.45):
        for y in (0.2, -1.8):
            mb.lathe([(0.0, 11.3), (0.22, 11.3), (0.0, 12.2)], roof, segments=8, center=(x, y, 0.0))
    mb.lathe([(0.0, 11.3), (1.35, 11.3), (1.35, 11.45), (1.05, 11.55), (0.6, 12.6), (0.25, 13.3), (0.0, 13.75)], roof, segments=16,
             center=(0.0, -0.8, 0.0))
    mb.tube([(0.0, -0.8, 13.6), (0.0, -0.8, 14.0)], 0.05, gold, segments=6)
    mb.blob((0.0, -0.8, 13.82), (0.09, 0.09, 0.09), gold, subdiv=1, noise=0.0, seed=0)
    # Tilted orbit ring with floating orbs.
    ring = []
    tilt = Matrix.Rotation(math.radians(18.0), 3, "X")
    for i in range(41):
        a = 2.0 * math.pi * i / 40
        ring.append(Vector((0.0, -0.8, 6.6)) + tilt @ Vector((3.4 * math.cos(a), 2.7 * math.sin(a), 0.0)))
    mb.tube(ring, 0.06, gold, segments=6, cap_start=False, cap_end=False)
    for adeg in (30.0, 150.0, 260.0):
        a = math.radians(adeg)
        mb.blob(tuple(Vector((0.0, -0.8, 6.6)) + tilt @ Vector((3.4 * math.cos(a), 2.7 * math.sin(a), -0.32))), (0.26, 0.26, 0.26), roof,
                subdiv=2, noise=0.0, seed=0)
    return mb


def dial(P: dict) -> MeshBuilder:
    """Dial placeholder in its own frame (origin = clock axis on the dial face, +Y out of the face)."""
    mb = MeshBuilder()
    mb.lathe([(0.0, -0.03), (1.07, -0.03), (1.07, 0.02), (0.0, 0.02)], P["dial_face"], segments=32, matrix=RX_TO_FRONT)
    mark = mb.mark()
    mb.annulus(0.0, 0.0, 1.04, DIAL_OUTER_R, 0.0, DIAL_RIM_FRONT_Y - DIAL_CENTRE[1], P["gold"], segments=32)
    mb.annulus(0.0, 0.0, 0.76, 0.79, 0.0, 0.03, P["gold"], segments=32)
    mb.transform_since(mark, RX_TO_FRONT)
    for k in range(12):
        a = math.radians(k * 30)
        big = k % 3 == 0
        mb.obox((-0.9 * math.sin(a), 0.03, 0.9 * math.cos(a)), (0.1 if big else 0.06, 0.03, 0.24 if big else 0.16), P["hand_iron"],
                pitch_deg=-k * 30.0)
    mb.lathe([(0.0, 0.0), (0.07, 0.0), (0.07, 0.05), (0.0, 0.05)], P["gold"], segments=12, matrix=RX_TO_FRONT)
    return mb


def _hand(P: dict, outline: list[tuple[float, float]], tail_orb: bool) -> MeshBuilder:
    """Clock hand in its pivot frame: pointing +Z (12 o'clock), 22 mm thick towards +Y."""
    mb = MeshBuilder()
    mark = mb.mark()
    mb.prism(outline, -0.022, 0.0, P["hand_iron"])
    mb.transform_since(mark, RX_PLATE)
    mb.lathe([(0.0, 0.0), (0.06, 0.0), (0.06, 0.03), (0.0, 0.03)], P["gold"], segments=10, matrix=RX_TO_FRONT)
    if tail_orb:
        mb.blob((0.0, 0.011, -0.25), (0.07, 0.02, 0.07), P["gold"], subdiv=1, noise=0.0, seed=0)
    return mb


def hour_hand(P: dict) -> MeshBuilder:
    return _hand(P, [(-0.045, -0.16), (0.045, -0.16), (0.06, 0.3), (0.12, 0.44), (0.0, 0.62), (-0.12, 0.44), (-0.06, 0.3)], False)


def minute_hand(P: dict) -> MeshBuilder:
    return _hand(P, [(-0.035, -0.2), (0.035, -0.2), (0.045, 0.55), (0.09, 0.72), (0.0, 0.93), (-0.09, 0.72), (-0.045, 0.55)], True)


def bell_bracket(P: dict) -> MeshBuilder:
    """Iron bracket that holds the bell in front of the belfry (root frame; stays when M07 replaces the body)."""
    mb = MeshBuilder()
    x = BELL_PIVOT[0]
    iron = P["iron"]
    mb.obox((x, 0.68, 10.85), (0.5, 0.08, 0.7), iron)
    mb.beam((x, 0.7, 11.05), (x, 1.62, 11.05), 0.08, 0.1, iron)
    mb.beam((x, 0.7, 10.6), (x, 1.3, 11.02), 0.06, 0.06, iron)
    curl = [(x, 1.62 + 0.1 * math.sin(math.radians(a)), 11.15 - 0.1 * math.cos(math.radians(a))) for a in range(0, 300, 30)]
    mb.tube(curl, 0.025, iron, segments=5)
    mb.tube([(x, BELL_PIVOT[1], 11.05), (x, BELL_PIVOT[1], BELL_PIVOT[2] + 0.02)], 0.022, iron, segments=5)
    mb.lathe([(0.0, 11.12), (0.45, 11.12), (0.0, 11.5)], P["tower_roof"], segments=10, center=(x, BELL_PIVOT[1], 0.0))
    return mb


def bell(P: dict) -> MeshBuilder:
    """Bell in its pivot frame (hanging point); swings about local X."""
    mb = MeshBuilder()
    mb.obox((0.0, 0.0, -0.02), (0.36, 0.12, 0.1), P["iron"])
    mb.lathe([(0.0, -0.04), (0.1, -0.05), (0.16, -0.12), (0.19, -0.25), (0.23, -0.42), (0.32, -0.58), (0.36, -0.66), (0.30, -0.66), (0.0, -0.6)],
             P["bell_bronze"], segments=18)
    mb.annulus(0.0, 0.0, 0.265, 0.295, -0.52, -0.48, P["gold"], segments=18)
    mb.tube([(0.0, 0.0, -0.1), (0.0, 0.0, -0.6)], 0.02, P["iron"], segments=5)
    mb.blob((0.0, 0.0, -0.63), (0.065, 0.065, 0.065), P["iron"], subdiv=1, noise=0.0, seed=0)
    return mb
