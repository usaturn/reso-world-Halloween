"""W10: P3 の宣言・ProtoGraph・Flux のマニフェストを作る。

実行（プロジェクトのディレクトリ。A の地区の宣言を apply した後。Body の Slot のキーを A の state から読む）:
    uv run python modeling/p3_gimmicks/build_content.py
    uv run python modeling/p3_gimmicks/build_content.py --state-dir <apply の state の置き場>   # 既定は親の checkout

作る物（どれもコミットする）:
- content/p3_gimmicks.json: W08 の root の下の P3_Gimmicks（DynamicVariableSpace「HMC_P3」と G01 の値 3 つ、
  G01 のモジュールの配備先 G01_Dance）。state は親の checkout の .resoloop/state/p3_gimmicks.json
- flux/P3PlazaDance.pg: G01 の 6 体の位置と回転を、共有の時刻（WorldTimeDouble）と HMC_P3 の値から出すモジュール
- flux/p3_plaza_dance.flux.json: 出力を A の Body の中継（ValueMultiDriver）の Value へ drive で結ぶマニフェスト（worldState は A の state）

ProtoGraph の式（G01。i は個体、φ_i は W02 の phase_deg）:
    I = clamp01(G01Intensity)、f = clamp(G01Frequency, 0, 2)、s = clamp01(G01PhaseSpread)
    θ_i = 2π f t + s φ_i                       （t は WorldTimeDouble、秒）
    上下 = I (mid + half sin θ_i)              （mid・half は W02 の bounce_z_range_m の中央と半幅。範囲は I 倍の中に収まる）
    傾き = I tilt sin(θ_i / 2)                 （tilt は W02 の tilt_roll_deg_range の最大。顔の向き＝ローカル Z まわり）

W10-A（G03）で足した物:
- content/p3_gimmicks.json に G03 の値 3 つ（HMC_P3/G03Intensity・G03Frequency・G03Swing）と、モジュールの配備先 G03_Fountain
- flux/P3FountainGlow.pg: 噴水の水の専用の材質（A の宣言の p3_g03_wm）の EmissiveColor を出すモジュール
- flux/p3_fountain_glow.flux.json: その出力を drive で結ぶマニフェスト（worldState は A の state）

ProtoGraph の式（G03。E0 は P2 の水の発光、E1 は G03_SHIFT_EMISSIVE_LINEAR。どちらも線形の値）:
    I = clamp(G03Intensity, 0, 2)、f = clamp(G03Frequency, 0, 1)、A = clamp01(G03Swing)
    θ = 2π f t
    脈 = 1 + 0.5 A sin θ                      （明るさ。A = 1 で 0.5〜1.5 倍）
    混ぜ = A (1 − cos(θ / 2)) / 2             （色。0 で青、A で紫寄り。脈の半分の速さ）
    発光 = I × 脈 × ((1 − 混ぜ) E0 + 混ぜ E1)  （Linear の colorX。A = 0・I = 1 で P2 の発光と同じ）
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from modeling.p3_gimmicks import district, gimmicks, rest_pose  # noqa: E402

DEFAULT_STATE_DIR = Path("/workspaces/reso-world/worlds/reso-world-Halloween/.resoloop/state")
CONTENT = PROJECT_ROOT / "content" / "p3_gimmicks.json"
PG = PROJECT_ROOT / "flux" / f"{gimmicks.G01_MODULE}.pg"
MANIFEST = PROJECT_ROOT / "flux" / "p3_plaza_dance.flux.json"
G03_PG = PROJECT_ROOT / "flux" / f"{gimmicks.G03_MODULE}.pg"
G03_MANIFEST = PROJECT_ROOT / "flux" / "p3_fountain_glow.flux.json"


def b2r(p) -> list[float]:
    return [float(p[0]), float(p[2]), float(p[1])]


def content_doc() -> dict:
    comps = [{"key": "p3_space", "type": "FrooxEngine.DynamicVariableSpace",
              "fields": {"SpaceName": gimmicks.SPACE_NAME, "OnlyDirectBinding": False}}]
    for name, spec in {**gimmicks.G01_VARIABLES, **gimmicks.G03_VARIABLES}.items():
        comps.append({
            "key": spec["key"],
            "type": "[FrooxEngine]FrooxEngine.DynamicValueVariable<float>",
            "fields": {"VariableName": f"{gimmicks.SPACE_NAME}/{name}"},
            # 同じ Slot に同じ型が 3 つあるので、変えない VariableName で見分ける（resonite-build スキル）
            "identityFields": ["VariableName"],
            # 値は Resonite の中で変えてよい（ショーなど）。apply し直しても戻さない
            "initialFields": {"Value": spec["default"]},
        })
    return {
        "schemaVersion": "1",
        "ownership": {"key": gimmicks.P3_OWNERSHIP},
        "slot": {"key": "p3_root", "name": gimmicks.P3_ROOT_NAME, "parent": gimmicks.P2_ROOT,
                 "position": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]},
        "components": comps,
        "children": [
            {"slot": {"key": "p3_g01_dance", "name": gimmicks.G01_FLUX_SLOT,
                      "position": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]}},
            {"slot": {"key": "p3_g03", "name": gimmicks.G03_FLUX_SLOT,
                      "position": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]}},
        ],
        # 撮影のカメラ（resoloop capture の bookmark。ワールドには何も作らない）。座標は Resonite の世界座標
        "cameras": CAMERAS,
    }


CAMERAS = {
    # G13: 東と上からメリーゴーラウンド（中心は (-10.5, *, -32)。W09R-D の M05 の撮影で遮られなかった位置を基にした）
    "g13_carousel": {"position": [4.0, 6.0, -32.0], "target": [-10.5, 2.5, -32.0], "fieldOfView": 50, "width": 1600, "height": 900,
                     "representative": True},
    "g13_carousel_top": {"position": [2.0, 17.0, -42.0], "target": [-10.5, 2.0, -32.0], "fieldOfView": 50, "width": 1600, "height": 900},
    # G01: 南から噴水のまわりの 6 体、近くから南の 2 体（001・002。(+-2.72, *, -3.89)）
    "g01_ring": {"position": [0.0, 2.6, -12.0], "target": [0.0, 0.6, -1.0], "fieldOfView": 32, "width": 1600, "height": 900},
    "g01_close": {"position": [0.0, 1.3, -8.0], "target": [0.0, 0.75, -3.89], "fieldOfView": 50, "width": 1600, "height": 900},
    # G03: 南東から噴水（水の輪 3 段・M02・同じ水の材質の I03 の台座 (0, *, -4.65)）、南西から水の輪の近く
    "g03_fountain": {"position": [7.5, 3.4, -9.0], "target": [0.0, 1.0, -0.5], "fieldOfView": 45, "width": 1600, "height": 900},
    "g03_water": {"position": [-4.2, 2.3, -5.6], "target": [0.0, 0.8, 0.0], "fieldOfView": 50, "width": 1600, "height": 900},
}


def body_keys(state_dir: Path) -> dict[str, str]:
    """A の state から、G01 の各 Body の Slot のキーを探す（パスで照合し、1 つに決まらなければ止める）。"""
    state = json.loads((state_dir / "p2_A_plaza.json").read_text(encoding="utf-8"))
    keys: dict[str, str] = {}
    for p in gimmicks.g01()["pumpkins"]:
        want = f"{gimmicks.P2_ROOT}/A_plaza/{p['asset_id']}/{p['motion_root']}"
        hits = [k for k, v in state["slots"].items() if v.get("path") == want]
        if len(hits) != 1:
            raise SystemExit(f"{want}: {len(hits)} Slots in the A state")
        keys[p["motion_root"]] = hits[0]
    return keys


def _f(x: float) -> str:
    return repr(float(x))


def protograph() -> str:
    g = gimmicks.g01()
    v = gimmicks.G01_VARIABLES
    lines = [
        "// Generated by modeling/p3_gimmicks/build_content.py (W10, G01). Do not edit by hand.",
        "// Local presentation: every user evaluates the output Drives from the shared WorldTimeDouble and the",
        "// HMC_P3 dynamic variables. No impulses and no synchronized writes.",
        f"module {gimmicks.G01_MODULE}",
    ]
    for i, _ in enumerate(g["pumpkins"], start=1):
        lines += [f"out B{i}Position: float3", f"out B{i}Rotation: floatQ"]
    lines += [
        "where {",
        "    T = WorldTimeDouble;",
        f'    IntensityIn = DynamicVariableValueInput<float>(VariableName = "{gimmicks.SPACE_NAME}/G01Intensity");',
        f'    FrequencyIn = DynamicVariableValueInput<float>(VariableName = "{gimmicks.SPACE_NAME}/G01Frequency");',
        f'    SpreadIn = DynamicVariableValueInput<float>(VariableName = "{gimmicks.SPACE_NAME}/G01PhaseSpread");',
        "    // A missing variable reads as 0, which keeps every pumpkin at its rest pose.",
        "    I = Clamp01_Float(IntensityIn.Value);",
        "    F0 = FrequencyIn.Value;",
        (f"    F = if F0 < {_f(v['G01Frequency']['min'])} then {_f(v['G01Frequency']['min'])} "
         f"else if F0 > {_f(v['G01Frequency']['max'])} then {_f(v['G01Frequency']['max'])} else F0;"),
        "    S = Clamp01_Float(SpreadIn.Value);",
        "    Base = T * (F->as<double>) * 6.283185307179586d;",
        "    Sd = S->as<double>;",
    ]
    for i, p in enumerate(g["pumpkins"], start=1):
        lo, hi = p["bounce_m"]
        mid, half = (lo + hi) / 2.0, (hi - lo) / 2.0
        tilt = max(abs(t) for t in p["tilt_deg"])
        rest = b2r(p["rest_local_blender"])
        phase = math.radians(p["phase_deg"])
        lines += [
            f"    // {p['asset_id']}: phase {p['phase_deg']} deg, lift {lo}..{hi} m, tilt +-{tilt} deg",
            f"    Th{i} = Base + Sd * {_f(phase)}d;",
            f"    Lift{i} = I * ({_f(mid)} + {_f(half)} * (Sin_Double(Th{i})->as<float>));",
            f"    Tilt{i} = I * {_f(tilt)} * (Sin_Double(Th{i} * 0.5d)->as<float>);",
            f"    B{i}Position = Pack_Float3({_f(rest[0])}, {_f(rest[1])} + Lift{i}, {_f(rest[2])});",
            f"    B{i}Rotation = FromEuler_floatQ(Pack_Float3(0.0, 0.0, Tilt{i}));",
        ]
    lines.append("}")
    return "\n".join(lines) + "\n"


def g03_base_linear(declaration: dict | None = None) -> list[float]:
    """P2 の水の発光（A の宣言の専用の材質の EmissiveColor の初期値、sRGB）を線形にした [r, g, b]。"""
    srgb = gimmicks.g03_base_emissive(declaration or rest_pose.latest_declaration(gimmicks.g03()["district"]))
    return [gimmicks.srgb_to_linear(c) for c in srgb[:3]]


def protograph_g03(e0: list[float]) -> str:
    v = gimmicks.G03_VARIABLES
    e0 = [round(float(x), 6) for x in e0]
    e1 = gimmicks.G03_SHIFT_EMISSIVE_LINEAR
    name = gimmicks.SPACE_NAME

    def clamp(var: str, spec: dict) -> str:
        return (f"if {var}0 < {_f(spec['min'])} then {_f(spec['min'])} "
                f"else if {var}0 > {_f(spec['max'])} then {_f(spec['max'])} else {var}0")

    lines = [
        "// Generated by modeling/p3_gimmicks/build_content.py (W10-A, G03). Do not edit by hand.",
        "// Local presentation: every user evaluates the output Drive from the shared WorldTimeDouble and the",
        "// HMC_P3 dynamic variables. No impulses and no synchronized writes.",
        f"// E0 (P2 water glow, linear) = {tuple(e0)}, E1 (violet, linear) = {e1}",
        f"module {gimmicks.G03_MODULE}",
        "out WaterEmissive: colorX",
        "where {",
        "    T = WorldTimeDouble;",
        f'    IntensityIn = DynamicVariableValueInput<float>(VariableName = "{name}/G03Intensity");',
        f'    FrequencyIn = DynamicVariableValueInput<float>(VariableName = "{name}/G03Frequency");',
        f'    SwingIn = DynamicVariableValueInput<float>(VariableName = "{name}/G03Swing");',
        "    // A missing variable reads as 0: intensity 0 turns the water glow off.",
        "    I0 = IntensityIn.Value;",
        f"    I = {clamp('I', v['G03Intensity'])};",
        "    F0 = FrequencyIn.Value;",
        f"    F = {clamp('F', v['G03Frequency'])};",
        "    A0 = SwingIn.Value;",
        f"    A = {clamp('A', v['G03Swing'])};",
        "    Th = T * (F->as<double>) * 6.283185307179586d;",
        f"    Pulse = 1.0 + {_f(gimmicks.G03_PULSE_DEPTH)} * A * (Sin_Double(Th)->as<float>);",
        "    Mix = A * (0.5 - 0.5 * (Cos_Double(Th * 0.5d)->as<float>));",
        "    K = I * Pulse;",
    ]
    for ch, a, b in zip("RGB", e0, e1):
        lines.append(f"    {ch} = K * ({_f(a)} + Mix * {_f(round(b - a, 6))});")
    lines += [
        "    WaterEmissive = Pack_ColorX(R, G, B, 1.0, ColorProfile.Linear);",
        "}",
    ]
    return "\n".join(lines) + "\n"


def manifest_g03() -> dict:
    return {
        "schemaVersion": "1",
        "projectDirectory": ".",
        "parent": f"{gimmicks.P3_ROOT_PATH}/{gimmicks.G03_FLUX_SLOT}",
        "worldState": "../.resoloop/state/p2_A_plaza.json",
        "deployState": "../.resoloop/flux-state/p3_fountain_glow.json",
        "modules": [{"name": "p3-fountain-glow", "source": G03_PG.name, "module": gimmicks.G03_MODULE,
                     "bindings": {"WaterEmissive": {"target": f"$member:{gimmicks.G03_MATERIAL_KEY}.EmissiveColor", "mode": "drive"}}}],
    }


def manifest(keys: dict[str, str]) -> dict:
    bindings = {}
    for i, p in enumerate(gimmicks.g01()["pumpkins"], start=1):
        # A の宣言の Body の中継（ValueMultiDriver）の Value。中継が Slot の Position・Rotation を駆動する（district.py）
        k = keys[p["motion_root"]]
        bindings[f"B{i}Position"] = {"target": f"$member:{district.relay_key(k, 'Position')}.Value", "mode": "drive"}
        bindings[f"B{i}Rotation"] = {"target": f"$member:{district.relay_key(k, 'Rotation')}.Value", "mode": "drive"}
    return {
        "schemaVersion": "1",
        "projectDirectory": ".",
        # 配備先は P3 の宣言の Slot（A の state には無いので、deploy-manifest の --parent にパスで渡す。docs/p3-gimmicks.md 4 章）
        "parent": f"{gimmicks.P3_ROOT_PATH}/{gimmicks.G01_FLUX_SLOT}",
        # 親の checkout から見た相対パス（manifest の置き場の flux/ から）。worktree では deploy_flux.py が絶対パスに直す
        "worldState": "../.resoloop/state/p2_A_plaza.json",
        "deployState": "../.resoloop/flux-state/p3_plaza_dance.json",
        "modules": [{"name": "p3-plaza-dance", "source": PG.name, "module": gimmicks.G01_MODULE, "bindings": bindings}],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    args = ap.parse_args(argv)
    keys = body_keys(args.state_dir)
    e0 = g03_base_linear()
    CONTENT.write_text(json.dumps(content_doc(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PG.write_text(protograph(), encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest(keys), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    G03_PG.write_text(protograph_g03(e0), encoding="utf-8")
    G03_MANIFEST.write_text(json.dumps(manifest_g03(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"content": CONTENT.relative_to(PROJECT_ROOT).as_posix(), "protograph": PG.relative_to(PROJECT_ROOT).as_posix(),
                      "manifest": MANIFEST.relative_to(PROJECT_ROOT).as_posix(), "bodies": keys,
                      "g03_protograph": G03_PG.relative_to(PROJECT_ROOT).as_posix(),
                      "g03_manifest": G03_MANIFEST.relative_to(PROJECT_ROOT).as_posix(), "g03_base_linear": e0},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
