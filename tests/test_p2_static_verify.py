"""S-criteria test for the W08 live check (`modeling/p2_static/verify_live.py`).

Why this test exists (create-reso-world AGENTS.md, test criterion S): the live check reports the 78 motion pivots,
placeholders and landmarks as matching by composing the observed local transforms into world positions. If the
composition ignored a parent's rotation or scale, a moved or mirrored part could still be reported as "within 1 cm"
and the Issue would record an unverified state as verified, with no error anywhere.
"""

from __future__ import annotations

import math

from modeling.p2_static.verify_live import world_transforms


def _node(name: str, pos, rot=(0.0, 0.0, 0.0, 1.0), scale=(1.0, 1.0, 1.0), children=None) -> dict:
    return {"name": name, "position": dict(zip("xyz", pos)), "rotation": dict(zip("xyzw", rot)),
            "scale": dict(zip("xyz", scale)), "children": children or []}


def test_world_position_uses_parent_rotation_and_scale() -> None:
    s = math.sqrt(0.5)
    # Parent at (10, 0, 0), turned +90 degrees about Y, scaled 2. A child at local (1, 0, 0) ends at (10, 0, -2):
    # +90 about Y maps +X to -Z (left-handed Y-up, Resonite), and the parent's scale doubles the offset.
    tree = _node("root", (0, 0, 0), children=[
        _node("parent", (10, 0, 0), rot=(0.0, s, 0.0, s), scale=(2, 2, 2), children=[_node("child", (1, 0, 0))])
    ])
    got = {path[-1]: wpos for path, wpos, _, _ in world_transforms(tree)}
    assert all(abs(a - b) < 1e-9 for a, b in zip(got["child"], (10.0, 0.0, -2.0)))
    assert all(abs(a - b) < 1e-9 for a, b in zip(got["parent"], (10.0, 0.0, 0.0)))
