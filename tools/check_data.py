"""Validate layout and asset manifest JSON files against project conventions and schemas."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ID_PATTERN = re.compile(r"^[A-Za-z0-9]+(_[A-Za-z0-9]+)+$")
NUMERIC_SUFFIX_PATTERN = re.compile(r"\.[0-9]{3}$")

# One key per Meshy asset, `M01`-`M08` (W09-M01 to W09-M08). The shared Meshy intake key `meshy` (W09) is listed below.
MESHY_ASSET_KEYS = frozenset(f"M{n:02d}" for n in range(1, 9))

VALID_KEYS = frozenset({
    "probe",
    "world",
    "common",
    "A_plaza",
    "B_mansion",
    "C_candy",
    "D_amusement",
    "E_forest",
    "overview",
    "meshy",
}) | MESHY_ASSET_KEYS

VALID_AREA_IDS = frozenset({
    "probe",
    "world",
    "common",
    "A_plaza",
    "B_mansion",
    "C_candy",
    "D_amusement",
    "E_forest",
    "meshy",
}) | MESHY_ASSET_KEYS

VALID_CATEGORIES = frozenset({
    "probe",
    "terrain",
    "architecture",
    "prop",
    "vegetation",
    "lighting",
    "gimmick",
    "sky_boundary",
})

VALID_ORIGIN_POLICIES = frozenset({
    "ground_center",
    "hinge_pivot",
    "attachment_point",
    "world_origin",
})

VALID_PART_ROLES = frozenset({
    "asset_root",
    "static_part",
    "motion_root",
    "visual_root",
    "attachment_point",
})

VALID_EXPORT_STATUSES = frozenset({
    "unexported",
    "exported",
    "verified_resonite",
})

VALID_MEASUREMENT_SOURCES = frozenset({
    "blender_scene",
    "resoloop_export_report",
})


def _is_finite_number(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(float(val))


def _is_non_neg_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool) and val >= 0


def _is_vec3(val: Any) -> bool:
    return isinstance(val, list) and len(val) == 3 and all(_is_finite_number(x) for x in val)


def _is_valid_id(val: Any) -> bool:
    if not isinstance(val, str) or not val:
        return False
    if NUMERIC_SUFFIX_PATTERN.search(val):
        return False
    return bool(ID_PATTERN.match(val))


def _is_safe_rel_path(val: Any) -> bool:
    if not isinstance(val, str) or not val.strip():
        return False
    p = Path(val)
    if p.is_absolute():
        return False
    if ".." in p.parts:
        return False
    return True


def validate_schemas_exist(root: Path) -> list[str]:
    """Ensure schema files exist and are valid JSON."""
    errors: list[str] = []
    required_schemas = [
        root / "layout" / "schema" / "world_layout.schema.json",
        root / "layout" / "schema" / "area_layout.schema.json",
        root / "assets" / "schema" / "manifest.schema.json",
    ]
    for schema_path in required_schemas:
        if not schema_path.is_file():
            errors.append(f"[schema] Missing schema file: {schema_path}")
            continue
        try:
            data = json.loads(schema_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "$schema" not in data:
                errors.append(f"[schema] Invalid JSON schema root in {schema_path}")
        except Exception as exc:
            errors.append(f"[schema] Failed to parse {schema_path}: {exc}")
    return errors


def validate_world_layout_data(data: Any, source_label: str = "world_layout.json") -> list[str]:
    """Validate world_layout.json dictionary structure and constraints."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"[{source_label}] Root must be a JSON object"]

    if data.get("schema_version") != "1.0":
        errors.append(f"[{source_label}] schema_version must be '1.0'")
    if data.get("project") != "reso-world-Halloween":
        errors.append(f"[{source_label}] project must be 'reso-world-Halloween'")
    if data.get("unit") != "m":
        errors.append(f"[{source_label}] unit must be 'm'")

    axes = data.get("axes")
    if not isinstance(axes, dict):
        errors.append(f"[{source_label}] axes must be an object")
    else:
        if axes.get("right") != "+X" or axes.get("forward") != "+Y" or axes.get("up") != "+Z":
            errors.append(f"[{source_label}] axes must be right=+X, forward=+Y, up=+Z")
        if axes.get("ground_z") != 0.0:
            errors.append(f"[{source_label}] axes.ground_z must be 0.0")

    if data.get("world_origin") != [0.0, 0.0, 0.0] and data.get("world_origin") != [0, 0, 0]:
        errors.append(f"[{source_label}] world_origin must be [0.0, 0.0, 0.0]")

    # Areas
    areas = data.get("areas")
    defined_area_ids: set[str] = set()
    if not isinstance(areas, list) or len(areas) == 0:
        errors.append(f"[{source_label}] areas must be a non-empty array")
    else:
        for idx, area in enumerate(areas):
            prefix = f"[{source_label}:areas[{idx}]]"
            if not isinstance(area, dict):
                errors.append(f"{prefix} must be an object")
                continue
            area_id = area.get("area_id")
            if not isinstance(area_id, str) or area_id not in VALID_AREA_IDS:
                errors.append(f"{prefix} invalid area_id: {area_id!r}")
            elif area_id in defined_area_ids:
                errors.append(f"{prefix} duplicate area_id: {area_id!r}")
            else:
                defined_area_ids.add(area_id)

            key = area.get("key")
            if key not in VALID_KEYS:
                errors.append(f"{prefix} invalid key: {key!r}")

            if not _is_vec3(area.get("center")):
                errors.append(f"{prefix} center must be vec3")

            bounds = area.get("bounds")
            if not isinstance(bounds, dict) or not _is_vec3(bounds.get("min")) or not _is_vec3(bounds.get("max")):
                errors.append(f"{prefix} bounds must contain vec3 min and max")
            else:
                bmin = bounds["min"]
                bmax = bounds["max"]
                if not (bmin[0] <= bmax[0] and bmin[1] <= bmax[1] and bmin[2] <= bmax[2]):
                    errors.append(f"{prefix} bounds.min must be <= bounds.max")

            if not _is_finite_number(area.get("ground_elevation_m")):
                errors.append(f"{prefix} ground_elevation_m must be a finite number")

            conns = area.get("connections")
            if not isinstance(conns, list) or len(conns) == 0:
                errors.append(f"{prefix} connections must be a non-empty list")

        # Validate area connections refer to defined areas
        for idx, area in enumerate(areas):
            if isinstance(area, dict) and isinstance(area.get("connections"), list):
                for conn in area["connections"]:
                    if conn not in defined_area_ids:
                        errors.append(
                            f"[{source_label}:areas[{idx}]] connection {conn!r} not in defined areas"
                        )

    # Routes
    routes = data.get("routes")
    seen_routes: set[str] = set()
    if not isinstance(routes, list) or len(routes) == 0:
        errors.append(f"[{source_label}] routes must be a non-empty array")
    else:
        for idx, route in enumerate(routes):
            prefix = f"[{source_label}:routes[{idx}]]"
            if not isinstance(route, dict):
                errors.append(f"{prefix} must be an object")
                continue
            route_id = route.get("route_id")
            if not _is_valid_id(route_id):
                errors.append(f"{prefix} invalid route_id: {route_id!r}")
            elif route_id in seen_routes:
                errors.append(f"{prefix} duplicate route_id: {route_id!r}")
            else:
                seen_routes.add(route_id)

            for endpoint in ("from_area", "to_area"):
                val = route.get(endpoint)
                if val not in defined_area_ids:
                    errors.append(f"{prefix} {endpoint} {val!r} not in defined areas")

            kind = route.get("kind")
            width_m = route.get("width_m")
            if kind not in ("main_road", "ring_road", "bridge", "side_path"):
                errors.append(f"{prefix} invalid kind: {kind!r}")
            elif not _is_finite_number(width_m):
                errors.append(f"{prefix} width_m must be a number")
            else:
                min_w = 3.0 if kind in ("main_road", "ring_road") else 2.0
                if float(width_m) < min_w:
                    errors.append(f"{prefix} width_m ({width_m}) must be >= {min_w} for kind {kind!r}")

            waypoints = route.get("waypoints")
            if not isinstance(waypoints, list) or len(waypoints) < 2 or not all(_is_vec3(w) for w in waypoints):
                errors.append(f"{prefix} waypoints must be an array of at least 2 vec3 points")

            slope = route.get("max_slope_deg")
            if not _is_finite_number(slope) or float(slope) < 0.0 or float(slope) > 30.0:
                errors.append(f"{prefix} max_slope_deg must be between 0 and 30")

    # Landmarks
    landmarks = data.get("landmarks")
    seen_landmarks: set[str] = set()
    if not isinstance(landmarks, list) or len(landmarks) == 0:
        errors.append(f"[{source_label}] landmarks must be a non-empty array")
    else:
        for idx, lm in enumerate(landmarks):
            prefix = f"[{source_label}:landmarks[{idx}]]"
            if not isinstance(lm, dict):
                errors.append(f"{prefix} must be an object")
                continue
            lm_id = lm.get("landmark_id")
            if not _is_valid_id(lm_id):
                errors.append(f"{prefix} invalid landmark_id: {lm_id!r}")
            elif lm_id in seen_landmarks:
                errors.append(f"{prefix} duplicate landmark_id: {lm_id!r}")
            else:
                seen_landmarks.add(lm_id)
            if lm.get("area_id") not in defined_area_ids:
                errors.append(f"{prefix} area_id {lm.get('area_id')!r} not in defined areas")
            if not _is_vec3(lm.get("position")) or not _is_vec3(lm.get("target_point")):
                errors.append(f"{prefix} position and target_point must be vec3")

    # Line of sight
    los_list = data.get("line_of_sight")
    seen_los: set[str] = set()
    if not isinstance(los_list, list) or len(los_list) == 0:
        errors.append(f"[{source_label}] line_of_sight must be a non-empty array")
    else:
        for idx, los in enumerate(los_list):
            prefix = f"[{source_label}:line_of_sight[{idx}]]"
            if not isinstance(los, dict):
                errors.append(f"{prefix} must be an object")
                continue
            los_id = los.get("los_id")
            if not _is_valid_id(los_id):
                errors.append(f"{prefix} invalid los_id: {los_id!r}")
            elif los_id in seen_los:
                errors.append(f"{prefix} duplicate los_id: {los_id!r}")
            else:
                seen_los.add(los_id)
            if not _is_vec3(los.get("from_point")) or not _is_vec3(los.get("to_point")):
                errors.append(f"{prefix} from_point and to_point must be vec3")
            cw = los.get("corridor_width_m")
            if not _is_finite_number(cw) or float(cw) <= 0.0:
                errors.append(f"{prefix} corridor_width_m must be > 0")

    # Spawn
    spawn = data.get("spawn")
    if not isinstance(spawn, dict):
        errors.append(f"[{source_label}] spawn must be an object")
    else:
        if spawn.get("area_id") not in defined_area_ids:
            errors.append(f"[{source_label}:spawn] area_id {spawn.get('area_id')!r} not in defined areas")
        if not _is_vec3(spawn.get("position")) or not _is_vec3(spawn.get("forward")):
            errors.append(f"[{source_label}:spawn] position and forward must be vec3")
        cr = spawn.get("clearance_radius_m")
        if not _is_finite_number(cr) or float(cr) < 1.5:
            errors.append(f"[{source_label}:spawn] clearance_radius_m must be >= 1.5")

    return errors


def validate_area_layout_data(
    data: Any,
    source_label: str = "area_layout.json",
    known_assets_by_key: dict[str, set[str]] | None = None,
    require_all_manifest_refs: bool = False,
) -> list[str]:
    """Validate an area_layout JSON dictionary."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"[{source_label}] Root must be a JSON object"]

    if data.get("schema_version") != "1.0":
        errors.append(f"[{source_label}] schema_version must be '1.0'")

    area_id = data.get("area_id")
    if area_id not in VALID_AREA_IDS:
        errors.append(f"[{source_label}] invalid area_id: {area_id!r}")

    key = data.get("key")
    if key not in VALID_KEYS:
        errors.append(f"[{source_label}] invalid key: {key!r}")

    for field in ("name", "theme"):
        if not isinstance(data.get(field), str) or not data.get(field).strip():
            errors.append(f"[{source_label}] {field} must be a non-empty string")

    bounds = data.get("bounds")
    if not isinstance(bounds, dict) or not _is_vec3(bounds.get("min")) or not _is_vec3(bounds.get("max")):
        errors.append(f"[{source_label}] bounds must have vec3 min and max")
    else:
        bmin, bmax = bounds["min"], bounds["max"]
        if not (bmin[0] <= bmax[0] and bmin[1] <= bmax[1] and bmin[2] <= bmax[2]):
            errors.append(f"[{source_label}] bounds.min must be <= bounds.max")

    # 7 required spatial composition categories
    for section in (
        "Anchor",
        "Circulation",
        "Framing",
        "Story_Cluster",
        "Common_Placement",
        "Hero_or_Gimmick",
        "Exclusions",
    ):
        if section not in data:
            errors.append(f"[{source_label}] missing required section {section!r}")

    anchor = data.get("Anchor")
    if isinstance(anchor, dict):
        if not _is_valid_id(anchor.get("anchor_id")):
            errors.append(f"[{source_label}:Anchor] invalid anchor_id: {anchor.get('anchor_id')!r}")
        if not _is_vec3(anchor.get("position")) or not _is_vec3(anchor.get("dimensions_m")):
            errors.append(f"[{source_label}:Anchor] position and dimensions_m must be vec3")
        if not _is_finite_number(anchor.get("orientation_deg")):
            errors.append(f"[{source_label}:Anchor] orientation_deg must be a finite number")

    circulation = data.get("Circulation")
    if isinstance(circulation, dict):
        mw = circulation.get("min_walk_width_m")
        if not _is_finite_number(mw) or float(mw) < 2.0:
            errors.append(f"[{source_label}:Circulation] min_walk_width_m must be >= 2.0")
        if not isinstance(circulation.get("entry_points"), list) or len(circulation.get("entry_points", [])) == 0:
            errors.append(f"[{source_label}:Circulation] entry_points must be a non-empty list")

    placements = data.get("placements")
    seen_placement_ids: set[str] = set()
    if not isinstance(placements, list) or len(placements) == 0:
        errors.append(f"[{source_label}] placements must be a non-empty array")
    else:
        for idx, pl in enumerate(placements):
            prefix = f"[{source_label}:placements[{idx}]]"
            if not isinstance(pl, dict):
                errors.append(f"{prefix} must be an object")
                continue

            pid = pl.get("placement_id")
            if not _is_valid_id(pid):
                errors.append(f"{prefix} invalid placement_id: {pid!r}")
            elif pid in seen_placement_ids:
                errors.append(f"{prefix} duplicate placement_id: {pid!r}")
            else:
                seen_placement_ids.add(pid)

            aid = pl.get("asset_id")
            if not _is_valid_id(aid):
                errors.append(f"{prefix} invalid asset_id: {aid!r}")

            skey = pl.get("source_key")
            if skey not in VALID_KEYS:
                errors.append(f"{prefix} invalid source_key: {skey!r}")

            if pl.get("category") not in VALID_CATEGORIES:
                errors.append(f"{prefix} invalid category: {pl.get('category')!r}")

            if not _is_vec3(pl.get("position")) or not _is_vec3(pl.get("rotation_euler_deg")):
                errors.append(f"{prefix} position and rotation_euler_deg must be vec3")

            scale = pl.get("scale")
            if not _is_vec3(scale):
                errors.append(f"{prefix} scale must be vec3")
            else:
                sx, sy, sz = float(scale[0]), float(scale[1]), float(scale[2])
                if sx <= 0.0 or sy <= 0.0 or sz <= 0.0:
                    errors.append(f"{prefix} scale must be strictly positive, got {scale}")
                elif abs(sx - sy) > 1e-4 or abs(sy - sz) > 1e-4 or abs(sx - sz) > 1e-4:
                    errors.append(f"{prefix} non-uniform scale is prohibited: {scale}")

            if pl.get("origin_policy") not in VALID_ORIGIN_POLICIES:
                errors.append(f"{prefix} invalid origin_policy: {pl.get('origin_policy')!r}")

            cr = pl.get("clearance_radius_m")
            if not _is_finite_number(cr) or float(cr) < 0.0:
                errors.append(f"{prefix} clearance_radius_m must be >= 0")

            # Cross-reference check against loaded manifests
            if known_assets_by_key is not None and isinstance(skey, str) and isinstance(aid, str):
                if skey in known_assets_by_key:
                    if aid not in known_assets_by_key[skey]:
                        errors.append(
                            f"{prefix} asset_id {aid!r} not found in manifest for source_key {skey!r}"
                        )
                elif require_all_manifest_refs:
                    errors.append(
                        f"{prefix} manifest for source_key {skey!r} is missing (referenced by {aid!r})"
                    )

    # Also check Common_Placement references if common manifest is loaded
    common_placements = data.get("Common_Placement")
    if isinstance(common_placements, list):
        for idx, cp in enumerate(common_placements):
            prefix = f"[{source_label}:Common_Placement[{idx}]]"
            if not isinstance(cp, dict):
                errors.append(f"{prefix} must be an object")
                continue
            cid = cp.get("common_asset_id")
            if not _is_valid_id(cid):
                errors.append(f"{prefix} invalid common_asset_id: {cid!r}")
            elif known_assets_by_key is not None:
                if "common" in known_assets_by_key and cid not in known_assets_by_key["common"]:
                    errors.append(f"{prefix} common_asset_id {cid!r} not found in common manifest")
                elif require_all_manifest_refs and "common" not in known_assets_by_key:
                    errors.append(f"{prefix} common manifest not loaded to verify {cid!r}")

    return errors


def validate_manifest_data(
    data: Any,
    source_label: str = "manifest.json",
    root: Path = PROJECT_ROOT,
    seen_global_asset_ids: dict[str, str] | None = None,
    check_files_exist: bool = True,
) -> list[str]:
    """Validate an asset manifest JSON dictionary against Spec §6.4 and project rules."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"[{source_label}] Root must be a JSON object"]

    if data.get("schema_version") != "1.0":
        errors.append(f"[{source_label}] schema_version must be '1.0'")

    manifest_key = data.get("key")
    if manifest_key not in VALID_KEYS:
        errors.append(f"[{source_label}] invalid key: {manifest_key!r}")

    if not isinstance(data.get("updated_at"), str) or not data.get("updated_at").strip():
        errors.append(f"[{source_label}] updated_at must be an ISO-8601 string")

    assets = data.get("assets")
    if not isinstance(assets, list) or len(assets) == 0:
        errors.append(f"[{source_label}] assets must be a non-empty array")
        return errors

    local_asset_ids: set[str] = set()

    for idx, asset in enumerate(assets):
        prefix = f"[{source_label}:assets[{idx}]]"
        if not isinstance(asset, dict):
            errors.append(f"{prefix} must be an object")
            continue

        asset_id = asset.get("asset_id")
        if not _is_valid_id(asset_id):
            errors.append(f"{prefix} invalid asset_id (must match ID regex and have no .001): {asset_id!r}")
        else:
            if asset_id in local_asset_ids:
                errors.append(f"{prefix} duplicate asset_id within manifest: {asset_id!r}")
            local_asset_ids.add(asset_id)
            if seen_global_asset_ids is not None:
                if asset_id in seen_global_asset_ids:
                    errors.append(
                        f"{prefix} duplicate asset_id {asset_id!r} (already defined in {seen_global_asset_ids[asset_id]})"
                    )
                else:
                    seen_global_asset_ids[asset_id] = source_label

        akey = asset.get("key")
        if akey not in VALID_KEYS:
            errors.append(f"{prefix} invalid key: {akey!r}")
        elif manifest_key not in ("overview", None) and akey != manifest_key:
            errors.append(f"{prefix} asset key {akey!r} does not match manifest key {manifest_key!r}")

        if asset.get("category") not in VALID_CATEGORIES:
            errors.append(f"{prefix} invalid category: {asset.get('category')!r}")

        if asset.get("area_id") not in VALID_AREA_IDS:
            errors.append(f"{prefix} invalid area_id: {asset.get('area_id')!r}")

        collection = asset.get("collection")
        if not isinstance(collection, str) or not collection.strip() or NUMERIC_SUFFIX_PATTERN.search(collection):
            errors.append(f"{prefix} invalid collection name: {collection!r}")

        # File paths
        for path_field in ("blend_file", "script_file"):
            rel_val = asset.get(path_field)
            if not _is_safe_rel_path(rel_val):
                errors.append(f"{prefix} {path_field} must be a safe relative path: {rel_val!r}")
            elif check_files_exist and not (root / rel_val).is_file():
                errors.append(f"{prefix} {path_field} does not exist on disk: {rel_val!r}")

        if asset.get("origin_policy") not in VALID_ORIGIN_POLICIES:
            errors.append(f"{prefix} invalid origin_policy: {asset.get('origin_policy')!r}")

        if not _is_vec3(asset.get("origin_world")):
            errors.append(f"{prefix} origin_world must be vec3")

        dims = asset.get("dimensions_m")
        if not isinstance(dims, dict):
            errors.append(f"{prefix} dimensions_m must be an object")
        else:
            for dim_key in ("width", "depth", "height"):
                val = dims.get(dim_key)
                if not _is_finite_number(val) or float(val) <= 0.0:
                    errors.append(f"{prefix} dimensions_m.{dim_key} must be > 0, got {val!r}")

        bounds_local = asset.get("bounds_local")
        if (
            not isinstance(bounds_local, dict)
            or not _is_vec3(bounds_local.get("min"))
            or not _is_vec3(bounds_local.get("max"))
        ):
            errors.append(f"{prefix} bounds_local must have vec3 min and max")
        else:
            bmin, bmax = bounds_local["min"], bounds_local["max"]
            if not (bmin[0] <= bmax[0] and bmin[1] <= bmax[1] and bmin[2] <= bmax[2]):
                errors.append(f"{prefix} bounds_local.min must be <= bounds_local.max")

        # Parts & hierarchy
        parts = asset.get("parts")
        part_ids: set[str] = set()
        part_parents: dict[str, str | None] = {}
        if not isinstance(parts, list) or len(parts) == 0:
            errors.append(f"{prefix} parts must be a non-empty array")
        else:
            for pidx, part in enumerate(parts):
                pprefix = f"{prefix}:parts[{pidx}]"
                if not isinstance(part, dict):
                    errors.append(f"{pprefix} must be an object")
                    continue
                pid = part.get("part_id")
                if not _is_valid_id(pid):
                    errors.append(f"{pprefix} invalid part_id: {pid!r}")
                elif pid in part_ids:
                    errors.append(f"{pprefix} duplicate part_id: {pid!r}")
                else:
                    part_ids.add(pid)

                if part.get("role") not in VALID_PART_ROLES:
                    errors.append(f"{pprefix} invalid role: {part.get('role')!r}")

                parent_part = part.get("parent_part")
                if parent_part is not None and not isinstance(parent_part, str):
                    errors.append(f"{pprefix} parent_part must be string or null")
                elif isinstance(pid, str):
                    part_parents[pid] = parent_part

                if part.get("origin_policy") not in VALID_ORIGIN_POLICIES:
                    errors.append(f"{pprefix} invalid origin_policy: {part.get('origin_policy')!r}")

                if not _is_vec3(part.get("pivot_local")):
                    errors.append(f"{pprefix} pivot_local must be vec3")

            # Verify parent_part references exist in part_ids and have no cycles
            for pid, parent_id in part_parents.items():
                if parent_id is not None:
                    if parent_id not in part_ids:
                        errors.append(
                            f"{prefix} part {pid!r} references missing parent_part {parent_id!r}"
                        )
                    elif parent_id == pid:
                        errors.append(f"{prefix} part {pid!r} cannot be its own parent")
                    else:
                        visited = {pid}
                        curr: str | None = parent_id
                        while curr is not None:
                            if curr in visited:
                                errors.append(f"{prefix} cycle detected in part hierarchy at {pid!r}")
                                break
                            visited.add(curr)
                            curr = part_parents.get(curr)

        hierarchy = asset.get("hierarchy")
        if not isinstance(hierarchy, dict):
            errors.append(f"{prefix} hierarchy must be an object")
        else:
            aroot = hierarchy.get("asset_root")
            if not isinstance(aroot, str) or aroot not in part_ids:
                errors.append(f"{prefix} hierarchy.asset_root {aroot!r} not in parts")
            for hfield in ("motion_roots", "visual_roots", "attachment_points"):
                hlist = hierarchy.get(hfield)
                if not isinstance(hlist, list):
                    errors.append(f"{prefix} hierarchy.{hfield} must be an array")
                else:
                    for item in hlist:
                        if not isinstance(item, str) or item not in part_ids:
                            errors.append(
                                f"{prefix} hierarchy.{hfield} reference {item!r} not in parts"
                            )

        # Materials & textures
        materials = asset.get("materials")
        if not isinstance(materials, list):
            errors.append(f"{prefix} materials must be an array")
        else:
            for mat in materials:
                if not isinstance(mat, str) or not mat.strip() or NUMERIC_SUFFIX_PATTERN.search(mat):
                    errors.append(f"{prefix} invalid material name: {mat!r}")

        textures = asset.get("textures")
        if not isinstance(textures, list):
            errors.append(f"{prefix} textures must be an array")
        else:
            for tex in textures:
                if not _is_safe_rel_path(tex):
                    errors.append(f"{prefix} texture path must be safe relative path: {tex!r}")
                elif check_files_exist and not (root / tex).is_file():
                    errors.append(f"{prefix} texture file does not exist on disk: {tex!r}")

        # Metrics (measured vs unmeasured strict rules)
        metrics = asset.get("metrics")
        if not isinstance(metrics, dict):
            errors.append(f"{prefix} metrics must be an object")
        else:
            measured = metrics.get("measured")
            if not isinstance(measured, bool):
                errors.append(f"{prefix} metrics.measured must be a boolean")
            elif measured is False:
                for mfield in ("triangles", "vertices", "materials_count", "objects_count"):
                    if metrics.get(mfield) is not None:
                        errors.append(
                            f"{prefix} metrics.{mfield} must be null when measured is false (got {metrics.get(mfield)!r})"
                        )
                reason = metrics.get("unmeasured_reason")
                if not isinstance(reason, str) or not reason.strip():
                    errors.append(
                        f"{prefix} metrics.unmeasured_reason must be a non-empty string when measured is false"
                    )
            else:
                for mfield in ("triangles", "vertices", "materials_count", "objects_count"):
                    val = metrics.get(mfield)
                    if not _is_non_neg_int(val):
                        errors.append(
                            f"{prefix} metrics.{mfield} must be a non-negative integer when measured is true (got {val!r})"
                        )
                if _is_non_neg_int(metrics.get("objects_count")) and metrics["objects_count"] == 0:
                    errors.append(f"{prefix} metrics.objects_count must be >= 1 when measured is true")
                msource = metrics.get("measurement_source")
                if msource not in VALID_MEASUREMENT_SOURCES:
                    errors.append(
                        f"{prefix} metrics.measurement_source must be one of {sorted(VALID_MEASUREMENT_SOURCES)} when measured is true"
                    )

        # Export result
        export_res = asset.get("export_result")
        if not isinstance(export_res, dict):
            errors.append(f"{prefix} export_result must be an object")
        else:
            status = export_res.get("status")
            if status not in VALID_EXPORT_STATUSES:
                errors.append(f"{prefix} export_result.status invalid: {status!r}")
            elif status == "unexported":
                for efield in ("bundle_dir", "apply_plan", "report_file"):
                    if export_res.get(efield) is not None:
                        errors.append(
                            f"{prefix} export_result.{efield} must be null when status is 'unexported'"
                        )
            else:
                for efield in ("bundle_dir", "apply_plan", "report_file"):
                    eval_path = export_res.get(efield)
                    if not _is_safe_rel_path(eval_path):
                        errors.append(
                            f"{prefix} export_result.{efield} must be a relative path when status is {status!r}"
                        )
                    elif check_files_exist:
                        target_p = root / eval_path
                        if efield == "bundle_dir" and not target_p.is_dir():
                            errors.append(
                                f"{prefix} export_result.bundle_dir directory does not exist: {eval_path!r}"
                            )
                        elif efield == "report_file" and not target_p.is_file():
                            errors.append(
                                f"{prefix} export_result.{efield} file does not exist: {eval_path!r}"
                            )

        # Replacement
        replacement = asset.get("replacement")
        if not isinstance(replacement, dict):
            errors.append(f"{prefix} replacement must be an object")
        else:
            if not isinstance(replacement.get("is_placeholder"), bool):
                errors.append(f"{prefix} replacement.is_placeholder must be boolean")
            if not isinstance(replacement.get("modifiable"), bool):
                errors.append(f"{prefix} replacement.modifiable must be boolean")
            if not isinstance(replacement.get("notes"), str):
                errors.append(f"{prefix} replacement.notes must be string")
            ft = replacement.get("future_target")
            if ft is not None and not _is_valid_id(ft):
                errors.append(f"{prefix} replacement.future_target must be null or valid ID, got {ft!r}")

    return errors


def run_validation(
    root: Path = PROJECT_ROOT,
    key: str | None = None,
    world_layout_paths: list[Path] | None = None,
    area_layout_paths: list[Path] | None = None,
    manifest_paths: list[Path] | None = None,
    require_all_manifest_refs: bool = False,
    check_files_exist: bool = True,
) -> tuple[bool, list[str], dict[str, int]]:
    """Run validation across discovered or specified files."""
    errors: list[str] = []
    counts = {"world_layouts": 0, "area_layouts": 0, "manifests": 0}

    errors.extend(validate_schemas_exist(root))

    explicit_mode = any(
        x is not None for x in (world_layout_paths, area_layout_paths, manifest_paths)
    )

    w_paths: list[Path] = []
    a_paths: list[Path] = []
    m_paths: list[Path] = []

    if explicit_mode:
        w_paths = list(world_layout_paths or [])
        a_paths = list(area_layout_paths or [])
        m_paths = list(manifest_paths or [])
    elif key is not None:
        if key not in VALID_KEYS:
            errors.append(f"[args] Unknown key: {key!r}")
            return False, errors, counts
        if key == "probe":
            p_layout = root / "modeling" / "probe" / "probe_layout.json"
            p_manifest = root / "modeling" / "probe" / "probe_manifest.json"
            if p_layout.is_file():
                a_paths.append(p_layout)
            else:
                errors.append(f"[probe] Missing {p_layout}")
            if p_manifest.is_file():
                m_paths.append(p_manifest)
            else:
                errors.append(f"[probe] Missing {p_manifest}")
        elif key == "world":
            wl = root / "layout" / "world_layout.json"
            if wl.is_file():
                w_paths.append(wl)
            else:
                errors.append(f"[world] Missing {wl}")
            wm = root / "assets" / "manifest" / "world.json"
            if wm.is_file():
                m_paths.append(wm)
        elif key == "common":
            cm = root / "assets" / "manifest" / "common.json"
            if cm.is_file():
                m_paths.append(cm)
            else:
                errors.append(f"[common] Missing {cm}")
        elif key == "overview":
            om = root / "assets" / "manifest.json"
            if om.is_file():
                m_paths.append(om)
            else:
                errors.append(f"[overview] Missing {om}")
        else:
            al = root / "layout" / "areas" / f"{key}.json"
            am = root / "assets" / "manifest" / f"{key}.json"
            if al.is_file():
                a_paths.append(al)
            if am.is_file():
                m_paths.append(am)
            cm = root / "assets" / "manifest" / "common.json"
            if cm.is_file():
                m_paths.append(cm)
            if not al.is_file() and not am.is_file():
                errors.append(f"[{key}] Neither {al} nor {am} exists")
    else:
        # Auto-discover all existing data files
        wl = root / "layout" / "world_layout.json"
        if wl.is_file():
            w_paths.append(wl)
        areas_dir = root / "layout" / "areas"
        if areas_dir.is_dir():
            a_paths.extend(sorted(areas_dir.glob("*.json")))
        manifest_dir = root / "assets" / "manifest"
        if manifest_dir.is_dir():
            m_paths.extend(sorted(manifest_dir.glob("*.json")))
        probe_layout = root / "modeling" / "probe" / "probe_layout.json"
        if probe_layout.is_file():
            a_paths.append(probe_layout)
        probe_manifest = root / "modeling" / "probe" / "probe_manifest.json"
        if probe_manifest.is_file():
            m_paths.append(probe_manifest)

        # If nothing exists yet, check example world layout
        if not w_paths and not a_paths and not m_paths:
            ex = root / "layout" / "schema" / "world_layout.example.json"
            if ex.is_file():
                w_paths.append(ex)
            else:
                errors.append("[discover] No layout or manifest files found to validate")

    # 1. Validate manifests first so we can cross-reference asset_ids in area layouts
    seen_global_asset_ids: dict[str, str] = {}
    known_assets_by_key: dict[str, set[str]] = {}

    for mp in m_paths:
        counts["manifests"] += 1
        if not mp.is_file():
            errors.append(f"[manifest] File not found: {mp}")
            continue
        try:
            mdata = json.loads(mp.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"[{mp.name}] Invalid JSON: {exc}")
            continue
        m_errors = validate_manifest_data(
            mdata,
            source_label=str(mp.relative_to(root) if mp.is_relative_to(root) else mp),
            root=root,
            seen_global_asset_ids=seen_global_asset_ids,
            check_files_exist=check_files_exist,
        )
        errors.extend(m_errors)
        if isinstance(mdata, dict) and isinstance(mdata.get("assets"), list):
            for asset in mdata["assets"]:
                if isinstance(asset, dict):
                    akey = asset.get("key")
                    aid = asset.get("asset_id")
                    if isinstance(akey, str) and isinstance(aid, str):
                        known_assets_by_key.setdefault(akey, set()).add(aid)

    #Also validate integrated assets/manifest.json if it exists in default discovery mode
    integrated_manifest = root / "assets" / "manifest.json"
    if not explicit_mode and key is None and integrated_manifest.is_file():
        counts["manifests"] += 1
        try:
            idata = json.loads(integrated_manifest.read_text(encoding="utf-8"))
            errors.extend(
                validate_manifest_data(
                    idata,
                    source_label="assets/manifest.json",
                    root=root,
                    seen_global_asset_ids=None,  # Integrated manifest aggregates per-key manifests
                    check_files_exist=check_files_exist,
                )
            )
        except Exception as exc:
            errors.append(f"[assets/manifest.json] Invalid JSON: {exc}")

    # 2. Validate world_layout files
    for wp in w_paths:
        counts["world_layouts"] += 1
        if not wp.is_file():
            errors.append(f"[world_layout] File not found: {wp}")
            continue
        try:
            wdata = json.loads(wp.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"[{wp.name}] Invalid JSON: {exc}")
            continue
        errors.extend(
            validate_world_layout_data(
                wdata,
                source_label=str(wp.relative_to(root) if wp.is_relative_to(root) else wp),
            )
        )

    # 3. Validate area_layout files
    strict_refs = require_all_manifest_refs or (explicit_mode and bool(manifest_paths))
    for ap in a_paths:
        counts["area_layouts"] += 1
        if not ap.is_file():
            errors.append(f"[area_layout] File not found: {ap}")
            continue
        try:
            adata = json.loads(ap.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"[{ap.name}] Invalid JSON: {exc}")
            continue
        errors.extend(
            validate_area_layout_data(
                adata,
                source_label=str(ap.relative_to(root) if ap.is_relative_to(root) else ap),
                known_assets_by_key=known_assets_by_key if (known_assets_by_key or strict_refs) else None,
                require_all_manifest_refs=strict_refs,
            )
        )

    return len(errors) == 0, errors, counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate layout and manifest JSON files.")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT, help="Project root directory")
    parser.add_argument("--key", type=str, default=None, help="Specific key to validate (e.g. probe, A_plaza)")
    parser.add_argument("--world-layout", type=Path, action="append", default=None, help="Explicit world_layout.json path")
    parser.add_argument("--area-layout", type=Path, action="append", default=None, help="Explicit area_layout.json path")
    parser.add_argument("--manifest", type=Path, action="append", default=None, help="Explicit manifest.json path")
    parser.add_argument(
        "--require-manifests",
        action="store_true",
        help="Require all source_key manifests referenced by area layouts to exist",
    )
    parser.add_argument(
        "--no-file-check",
        action="store_true",
        help="Skip checking existence of referenced .blend, script, and texture files on disk",
    )
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args(argv)

    ok, errors, counts = run_validation(
        root=args.root.resolve(),
        key=args.key,
        world_layout_paths=args.world_layout,
        area_layout_paths=args.area_layout,
        manifest_paths=args.manifest,
        require_all_manifest_refs=args.require_manifests,
        check_files_exist=not args.no_file_check,
    )

    if args.json:
        print(json.dumps({"ok": ok, "counts": counts, "errors": errors}, indent=2, ensure_ascii=False))
    else:
        if ok:
            print(
                f"OK: validated {counts['world_layouts']} world_layout(s), "
                f"{counts['area_layouts']} area_layout(s), {counts['manifests']} manifest(s)."
            )
        else:
            for err in errors:
                print(f"ERROR: {err}", file=sys.stderr)
            print(f"FAILED with {len(errors)} error(s).", file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
