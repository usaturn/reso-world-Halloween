"""Materials of the E_forest key (flat Principled BSDF colours; no image textures)."""

from __future__ import annotations

from modeling.lib.materials import create_pbr_material

# name: (base RGBA, metallic, roughness, emission RGBA or None, emission strength)
SPECS: dict[str, tuple] = {
    "bark": ((0.20, 0.13, 0.09, 1.0), 0.0, 0.88, None, 0.0),
    "bark_face": ((0.27, 0.16, 0.10, 1.0), 0.0, 0.85, None, 0.0),
    "face_socket": ((0.04, 0.02, 0.03, 1.0), 0.0, 0.95, None, 0.0),
    "face_glow": ((1.0, 0.62, 0.16, 1.0), 0.0, 0.35, (1.0, 0.52, 0.10, 1.0), 6.0),
    "leaf_teal": ((0.05, 0.24, 0.22, 1.0), 0.0, 0.80, None, 0.0),
    "leaf_purple": ((0.24, 0.10, 0.32, 1.0), 0.0, 0.80, None, 0.0),
    "leaf_pine": ((0.04, 0.17, 0.15, 1.0), 0.0, 0.85, None, 0.0),
    "moss": ((0.12, 0.30, 0.15, 1.0), 0.0, 0.92, None, 0.0),
    "stone": ((0.30, 0.28, 0.35, 1.0), 0.02, 0.86, None, 0.0),
    "mush_stem": ((0.86, 0.80, 0.70, 1.0), 0.0, 0.70, None, 0.0),
    "cap_purple": ((0.42, 0.16, 0.66, 1.0), 0.0, 0.55, None, 0.0),
    "cap_teal": ((0.08, 0.50, 0.52, 1.0), 0.0, 0.55, None, 0.0),
    "cap_orange": ((0.90, 0.40, 0.08, 1.0), 0.0, 0.55, None, 0.0),
    # One shared glow material; per-individual period/phase live in the manifest (Spec §11).
    "mush_glow": ((0.70, 0.92, 1.0, 1.0), 0.0, 0.40, (0.48, 0.86, 1.0, 1.0), 3.2),
    "plank": ((0.42, 0.27, 0.15, 1.0), 0.0, 0.78, None, 0.0),
    "plank_dark": ((0.24, 0.15, 0.09, 1.0), 0.0, 0.82, None, 0.0),
    "rope": ((0.55, 0.42, 0.26, 1.0), 0.0, 0.90, None, 0.0),
    "iron": ((0.12, 0.12, 0.16, 1.0), 0.75, 0.45, None, 0.0),
    "lantern_glow": ((1.0, 0.64, 0.18, 1.0), 0.0, 0.30, (1.0, 0.56, 0.14, 1.0), 5.0),
    "water": ((0.04, 0.32, 0.38, 1.0), 0.0, 0.08, (0.04, 0.42, 0.48, 1.0), 0.7),
    "lily": ((0.10, 0.36, 0.16, 1.0), 0.0, 0.70, None, 0.0),
    "roof_purple": ((0.30, 0.12, 0.46, 1.0), 0.0, 0.65, None, 0.0),
    "roof_band": ((0.92, 0.48, 0.10, 1.0), 0.1, 0.50, None, 0.0),
    "brass": ((0.80, 0.56, 0.22, 1.0), 0.90, 0.35, None, 0.0),
    # Clock tower placeholder (M07 stand-in) and the clock parts kept after the swap.
    "tower_stone": ((0.43, 0.41, 0.48, 1.0), 0.02, 0.82, None, 0.0),
    "tower_rock": ((0.23, 0.21, 0.26, 1.0), 0.0, 0.92, None, 0.0),
    "tower_roof": ((0.30, 0.15, 0.55, 1.0), 0.0, 0.60, None, 0.0),
    "tower_window": ((1.0, 0.70, 0.30, 1.0), 0.0, 0.40, (1.0, 0.60, 0.20, 1.0), 2.5),
    "gold": ((0.88, 0.62, 0.20, 1.0), 0.90, 0.30, None, 0.0),
    "dial_face": ((0.93, 0.87, 0.70, 1.0), 0.0, 0.55, None, 0.0),
    "hand_iron": ((0.07, 0.06, 0.10, 1.0), 0.60, 0.40, None, 0.0),
    "bell_bronze": ((0.72, 0.46, 0.18, 1.0), 0.90, 0.32, None, 0.0),
    "bat_body": ((0.10, 0.07, 0.14, 1.0), 0.0, 0.70, None, 0.0),
    "bat_wing": ((0.24, 0.11, 0.30, 1.0), 0.0, 0.75, None, 0.0),
    "bat_eye": ((1.0, 0.85, 0.30, 1.0), 0.0, 0.30, (1.0, 0.80, 0.25, 1.0), 4.0),
}


def _mat_name(key: str) -> str:
    return "MAT_EFR_" + "".join(part.capitalize() for part in key.split("_"))


def build_palette() -> dict:
    """Create every material once and return them by palette key."""
    out = {}
    for key, (base, metallic, rough, emit, strength) in SPECS.items():
        out[key] = create_pbr_material(
            _mat_name(key),
            base_color=base,
            metallic=metallic,
            roughness=rough,
            emission_color=emit,
            emission_strength=strength,
        )
    return out
