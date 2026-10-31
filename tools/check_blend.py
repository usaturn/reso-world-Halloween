"""Inspect .blend files for unresolved external files, negative/non-uniform scale, shear, and invalid names."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ID_PATTERN = re.compile(r"^[A-Za-z0-9]+(_[A-Za-z0-9]+)+$")
COLLECTION_NAME_PATTERN = re.compile(
    r"^(probe|world|common|A_plaza|B_mansion|C_candy|D_amusement|E_forest|overview|meshy|M0[1-8]"
    r"|[A-Za-z0-9]+(_[A-Za-z0-9]+)+)$"
)
NUMERIC_SUFFIX_PATTERN = re.compile(r"\.[0-9]{3}$")

FORBIDDEN_DEFAULT_NAMES = frozenset({
    "Cube",
    "Cylinder",
    "Sphere",
    "Icosphere",
    "Plane",
    "Cone",
    "Torus",
    "Grid",
    "Monkey",
    "Suzanne",
    "Empty",
    "Light",
    "Point",
    "Sun",
    "Spot",
    "Area",
    "Camera",
    "Material",
    "Collection",
    "Text",
    "Armature",
    "Lattice",
    "Curve",
    "BezierCurve",
    "NurbsCurve",
})

SCALE_TOL = 1e-4
SHEAR_COS_TOL = 1e-4


def check_name_conventions(name: str, kind: str = "object") -> list[str]:
    """Validate an object, material, or collection name against project naming rules."""
    errors: list[str] = []
    if not isinstance(name, str) or not name.strip():
        return [f"[{kind}] Empty name is not allowed"]

    if NUMERIC_SUFFIX_PATTERN.search(name):
        errors.append(f"[{kind}:{name}] Duplicate numeric suffix (.NNN) is prohibited")

    if name in FORBIDDEN_DEFAULT_NAMES:
        errors.append(f"[{kind}:{name}] Default Blender name is prohibited")

    if kind == "collection":
        if not COLLECTION_NAME_PATTERN.match(name):
            errors.append(
                f"[{kind}:{name}] Collection name does not match allowed key orPrefix_Name pattern"
            )
    else:
        if not ID_PATTERN.match(name):
            errors.append(
                f"[{kind}:{name}] Name does not match required pattern '^[A-Za-z0-9]+(_[A-Za-z0-9]+)+$'"
            )

    return errors


def _vec_norm(v: tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _vec_dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _mat3_det(
    c0: tuple[float, float, float],
    c1: tuple[float, float, float],
    c2: tuple[float, float, float],
) -> float:
    return (
        c0[0] * (c1[1] * c2[2] - c1[2] * c2[1])
        - c1[0] * (c0[1] * c2[2] - c0[2] * c2[1])
        + c2[0] * (c0[1] * c1[2] - c0[2] * c1[1])
    )


def check_transform_matrix_and_scale(
    obj_name: str,
    local_scale: tuple[float, float, float],
    matrix_world_3x3: list[list[float]] | tuple[tuple[float, ...], ...],
    matrix_local_3x3: list[list[float]] | tuple[tuple[float, ...], ...] | None = None,
) -> list[str]:
    """Check an object's local scale and 3x3 transform matrices for negative scale, non-uniform scale, and shear."""
    errors: list[str] = []
    sx, sy, sz = float(local_scale[0]), float(local_scale[1]), float(local_scale[2])

    # 1. Local negative or zero scale
    if sx <= 0.0 or sy <= 0.0 or sz <= 0.0:
        errors.append(
            f"[object:{obj_name}] Negative or zero local scale detected: ({sx:.6g}, {sy:.6g}, {sz:.6g})"
        )

    # 2. Local non-uniform scale
    if abs(sx - sy) > SCALE_TOL or abs(sy - sz) > SCALE_TOL or abs(sx - sz) > SCALE_TOL:
        errors.append(
            f"[object:{obj_name}] Non-uniform local scale detected: ({sx:.6g}, {sy:.6g}, {sz:.6g})"
        )

    # 3. Inspect 3x3 matrices (columns are basis vectors)
    matrices_to_check = [("world", matrix_world_3x3)]
    if matrix_local_3x3 is not None:
        matrices_to_check.append(("local", matrix_local_3x3))

    for space_label, m in matrices_to_check:
        c0 = (float(m[0][0]), float(m[1][0]), float(m[2][0]))
        c1 = (float(m[0][1]), float(m[1][1]), float(m[2][1]))
        c2 = (float(m[0][2]), float(m[1][2]), float(m[2][2]))

        n0, n1, n2 = _vec_norm(c0), _vec_norm(c1), _vec_norm(c2)
        det = _mat3_det(c0, c1, c2)

        if det <= 1e-10 or n0 <= 1e-8 or n1 <= 1e-8 or n2 <= 1e-8:
            errors.append(
                f"[object:{obj_name}] Negative or degenerate {space_label} transform matrix (det={det:.6g})"
            )
            continue

        # Check world non-uniform scale
        if (
            abs(n0 - n1) > SCALE_TOL
            or abs(n1 - n2) > SCALE_TOL
            or abs(n0 - n2) > SCALE_TOL
        ):
            errors.append(
                f"[object:{obj_name}] Non-uniform {space_label} scale in transform matrix: "
                f"({n0:.6g}, {n1:.6g}, {n2:.6g})"
            )

        # Check orthogonality of basis columns (shear)
        u0 = (c0[0] / n0, c0[1] / n0, c0[2] / n0)
        u1 = (c1[0] / n1, c1[1] / n1, c1[2] / n1)
        u2 = (c2[0] / n2, c2[1] / n2, c2[2] / n2)

        d01 = abs(_vec_dot(u0, u1))
        d12 = abs(_vec_dot(u1, u2))
        d02 = abs(_vec_dot(u0, u2))
        if d01 > SHEAR_COS_TOL or d12 > SHEAR_COS_TOL or d02 > SHEAR_COS_TOL:
            errors.append(
                f"[object:{obj_name}] Shear detected in {space_label} transform matrix "
                f"(axis cosines: xy={d01:.6g}, yz={d12:.6g}, xz={d02:.6g})"
            )

    return errors


def inspect_blender_scene() -> dict[str, Any]:
    """Inspect the currently open Blender scene (`bpy`) and return validation report."""
    import bpy  # type: ignore

    errors: list[str] = []
    blend_filepath = bpy.data.filepath or "<unsaved>"

    # Ensure scene view_layer is up to date so matrix_world is accurate
    try:
        bpy.context.view_layer.update()
    except Exception:
        pass

    # 1. Check external images
    checked_images = 0
    for img in bpy.data.images:
        if img.name in ("Render Result", "Viewer Node"):
            continue
        if getattr(img, "source", "") in ("GENERATED", "VIEWER"):
            continue
        raw_path = getattr(img, "filepath", "") or getattr(img, "filepath_raw", "")
        if not raw_path:
            if getattr(img, "packed_file", None) is not None:
                checked_images += 1
                continue
            errors.append(f"[image:{img.name}] External image has empty filepath")
            continue
        abs_path = Path(bpy.path.abspath(raw_path, library=img.library)).resolve()
        checked_images += 1
        if not abs_path.is_file():
            errors.append(
                f"[image:{img.name}] Missing external image file: {raw_path!r} (resolved: {abs_path})"
            )

    # 2. Check external linked libraries
    checked_libraries = 0
    for lib in bpy.data.libraries:
        raw_path = getattr(lib, "filepath", "")
        abs_path = Path(bpy.path.abspath(raw_path)).resolve()
        checked_libraries += 1
        if not abs_path.is_file():
            errors.append(
                f"[library:{lib.name}] Missing linked library file: {raw_path!r} (resolved: {abs_path})"
            )

    # 3. Check collections
    checked_collections = 0
    for col in bpy.data.collections:
        if col.name in ("Scene Collection", "Master Collection"):
            continue
        checked_collections += 1
        errors.extend(check_name_conventions(col.name, kind="collection"))

    # 4. Check materials
    checked_materials = 0
    for mat in bpy.data.materials:
        if mat.name == "Dots Stroke":
            continue
        checked_materials += 1
        errors.extend(check_name_conventions(mat.name, kind="material"))

    # 5. Check objects (names, scale, shear)
    checked_objects = 0
    if len(bpy.data.objects) == 0:
        errors.append(f"[{blend_filepath}] Scene contains 0 objects")

    for obj in bpy.data.objects:
        checked_objects += 1
        errors.extend(check_name_conventions(obj.name, kind="object"))

        local_scale = (float(obj.scale[0]), float(obj.scale[1]), float(obj.scale[2]))
        mw = [[float(obj.matrix_world[r][c]) for c in range(3)] for r in range(3)]
        ml = [[float(obj.matrix_local[r][c]) for c in range(3)] for r in range(3)]
        errors.extend(check_transform_matrix_and_scale(obj.name, local_scale, mw, ml))

    return {
        "ok": len(errors) == 0,
        "blend_file": blend_filepath,
        "counts": {
            "objects": checked_objects,
            "collections": checked_collections,
            "materials": checked_materials,
            "images": checked_images,
            "libraries": checked_libraries,
        },
        "errors": errors,
    }


def inspect_blend_file_via_resoloop(blend_path: Path, root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Run this script inside headless Blender via `resoloop blender run` on `blend_path`."""
    if not blend_path.is_file():
        return {
            "ok": False,
            "blend_file": str(blend_path),
            "counts": {},
            "errors": [f"[file] .blend file does not exist: {blend_path}"],
        }

    script_path = Path(__file__).resolve()
    cmd = [
        "resoloop",
        "blender",
        "run",
        str(script_path),
        "--blend",
        str(blend_path.resolve()),
        "--json",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )

    # Extract our marker JSON from stdout or parse resoloop's JSON output
    report: dict[str, Any] | None = None
    for raw_stream in (proc.stdout, proc.stderr):
        if not raw_stream or not raw_stream.strip():
            continue
        try:
            outer = json.loads(raw_stream)
            stdout_text = ""
            if isinstance(outer, dict):
                data = outer.get("data")
                if isinstance(data, dict):
                    stdout_text = data.get("standardOutput", "") or data.get("stdout", "") or ""
                if not stdout_text:
                    err_obj = outer.get("error")
                    if isinstance(err_obj, dict):
                        ctx = err_obj.get("context")
                        if isinstance(ctx, dict) and isinstance(ctx.get("result"), dict):
                            stdout_text = ctx["result"].get("standardOutput", "") or ""
            for line in stdout_text.splitlines():
                if line.startswith("CHECK_BLEND_JSON:"):
                    report = json.loads(line[len("CHECK_BLEND_JSON:") :])
                    break
            if report is not None:
                break
        except Exception:
            continue

    if report is not None:
        return report

    return {
        "ok": False,
        "blend_file": str(blend_path),
        "counts": {},
        "errors": [
            f"[blender] Failed to inspect {blend_path} (exit={proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        ],
    }


def discover_blend_files(root: Path, key: str | None = None, explicit_files: list[Path] | None = None) -> list[Path]:
    """Find target .blend files to inspect."""
    if explicit_files:
        return [p if p.is_absolute() else (root / p) for p in explicit_files]
    if key is not None:
        return [root / "blender" / key / f"{key}.blend"]
    blender_dir = root / "blender"
    if not blender_dir.is_dir():
        return []
    return sorted(blender_dir.glob("*/*.blend"))


def _running_inside_blender() -> bool:
    try:
        import bpy  # type: ignore  # noqa: F401

        return True
    except ImportError:
        return False


def main(argv: list[str] | None = None) -> int:
    if _running_inside_blender():
        report = inspect_blender_scene()
        print("CHECK_BLEND_JSON:" + json.dumps(report, ensure_ascii=False))
        if not report["ok"]:
            for err in report["errors"]:
                print(f"ERROR: {err}", file=sys.stderr)
            raise RuntimeError(f"Blend check failed with {len(report['errors'])} error(s)")
        return 0

    parser = argparse.ArgumentParser(description="Inspect .blend files for project convention compliance.")
    parser.add_argument("files", nargs="*", type=Path, help="Explicit .blend file paths")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT, help="Project root directory")
    parser.add_argument("--key", type=str, default=None, help="Key to inspect (e.g. probe, A_plaza)")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    targets = discover_blend_files(root, key=args.key, explicit_files=args.files)
    if not targets:
        msg = f"No .blend files found under {root / 'blender'}"
        if args.json:
            print(json.dumps({"ok": False, "reports": [], "errors": [msg]}, indent=2, ensure_ascii=False))
        else:
            print(f"ERROR: {msg}", file=sys.stderr)
        return 1

    reports: list[dict[str, Any]] = []
    all_errors: list[str] = []
    for target in targets:
        rep = inspect_blend_file_via_resoloop(target, root=root)
        reports.append(rep)
        for err in rep.get("errors", []):
            all_errors.append(f"{target.name}: {err}")

    ok = len(all_errors) == 0
    if args.json:
        print(
            json.dumps(
                {"ok": ok, "reports": reports, "errors": all_errors},
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        if ok:
            print(f"OK: inspected {len(reports)} .blend file(s) with 0 errors.")
        else:
            for err in all_errors:
                print(f"ERROR: {err}", file=sys.stderr)
            print(f"FAILED with {len(all_errors)} error(s) across {len(reports)} file(s).", file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
