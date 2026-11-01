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

W10-B（G05・G06）で足した物:
- content/p3_gimmicks.json に G05・G06 の値 6 つ（HMC_P3/G05Intensity・G05Frequency・G05PhaseSpread・G06Intensity・
  G06Frequency・G06Phase）と、モジュールの配備先 G05_G06_Mansion
- flux/P3MansionMotion.pg: B の 2 体のおばけの位置・回転と、扉の左右の蝶番の回転を出すモジュール
- flux/p3_mansion_motion.flux.json: その出力を B の中継（ValueMultiDriver）の Value へ drive で結ぶマニフェスト（worldState は B の state）

ProtoGraph の式（G05。i は個体、φ_i は gimmicks.G05_PHASE_DEG、lo・hi は gimmicks.G05_BOB_RANGE_M、yaw は W03 の揺れの最大 20°）:
    I = clamp01(G05Intensity)、f = clamp(G05Frequency, 0, 1)、s = clamp01(G05PhaseSpread)
    θ_i = 2π f t + s φ_i
    上下 = I (mid + half sin θ_i)               （Blender の Z = Resonite の Y。mid・half は lo・hi の中央と半幅）
    揺れ = I yaw sin(θ_i / 2)                   （Blender の Z まわり。Resonite の Y まわりは符号が逆）
ProtoGraph の式（G06。H は gimmicks.G06_HOLD、A は W03 の 85°）:
    I = clamp01(G06Intensity)、f = clamp(G06Frequency, 0, 0.2)、p = clamp01(G06Phase)
    θ = 2π (f t + p)、c = (1 − cos θ) / 2、x = clamp01((c − H) / (1 − 2H))
    開き = I A x² (3 − 2x)                      （左は Blender の +Z まわり、右は −Z まわり。どちらも内開き）
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
B_PG = PROJECT_ROOT / "flux" / f"{gimmicks.B_MODULE}.pg"
B_MANIFEST = PROJECT_ROOT / "flux" / "p3_mansion_motion.flux.json"


def b2r(p) -> list[float]:
    return [float(p[0]), float(p[2]), float(p[1])]


def content_doc() -> dict:
    comps = [{"key": "p3_space", "type": "FrooxEngine.DynamicVariableSpace",
              "fields": {"SpaceName": gimmicks.SPACE_NAME, "OnlyDirectBinding": False}}]
    for name, spec in {**gimmicks.G01_VARIABLES, **gimmicks.G03_VARIABLES, **gimmicks.G05_VARIABLES,
                       **gimmicks.G06_VARIABLES}.items():
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
            {"slot": {"key": "p3_g0506", "name": gimmicks.B_FLUX_SLOT,
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
    # G05: 中庭の石畳の南から 2 体のおばけ（(-4.6, *, 28)・(4.6, *, 33)）、近くから 001 と隣のベンチ (-3.8, *, 28.8)
    "g05_ghosts": {"position": [0.0, 4.2, 22.5], "target": [0.0, 2.9, 30.5], "fieldOfView": 60, "width": 1600, "height": 900},
    "g05_ghost_bench": {"position": [-1.2, 2.9, 25.6], "target": [-4.3, 2.4, 28.4], "fieldOfView": 50, "width": 1600, "height": 900},
    # G06: ポーチの段の前から扉と開口（W09R-B の m03_entrance と同じ位置）、玄関ホールの奥から扉の内側
    "g06_doors": {"position": [0.7, 3.4, 36.6], "target": [0.7, 3.1, 40.0], "fieldOfView": 70, "width": 1600, "height": 900},
    "g06_doors_inside": {"position": [0.7, 3.4, 43.2], "target": [0.7, 2.6, 40.0], "fieldOfView": 80, "width": 1600, "height": 900},
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


def b_keys(state_dir: Path) -> dict[str, str]:
    """B の state から、G05 の FloatPivot と G06 の蝶番の Slot のキーを探す（パスで照合し、1 つに決まらなければ止める）。"""
    state = json.loads((state_dir / "p2_B_mansion.json").read_text(encoding="utf-8"))
    rows = [(g["asset_id"], g["motion_root"]) for g in gimmicks.g05()["ghosts"]]
    rows += [(h["asset_id"], h["motion_root"]) for h in gimmicks.g06()["hinges"]]
    keys: dict[str, str] = {}
    for asset_id, part in rows:
        want = f"{gimmicks.P2_ROOT}/{gimmicks.g05()['district']}/{asset_id}/{part}"
        hits = [k for k, v in state["slots"].items() if v.get("path") == want]
        if len(hits) != 1:
            raise SystemExit(f"{want}: {len(hits)} Slots in the B state")
        keys[part] = hits[0]
    return keys


def b_rest(declaration: dict | None = None) -> dict[str, list[float]]:
    """B の最新の宣言の、G05 の FloatPivot と G06 の蝶番の基準の位置（Resonite の親のローカル）。回転が単位でなければ止める
    （式は基準の回転を単位として組んでいる）。"""
    doc = declaration or rest_pose.latest_declaration(gimmicks.g05()["district"])
    names = [g["motion_root"] for g in gimmicks.g05()["ghosts"]] + [h["motion_root"] for h in gimmicks.g06()["hinges"]]
    out: dict[str, list[float]] = {}
    stack = [doc]
    while stack:
        n = stack.pop()
        if n["slot"]["name"] in names:
            if n["slot"]["name"] in out:
                raise SystemExit(f"B declaration: {n['slot']['name']} appears twice")
            rot = n["slot"].get("rotation") or [0.0, 0.0, 0.0, 1.0]
            if max(abs(a - b) for a, b in zip(rot, (0.0, 0.0, 0.0, 1.0))) > 1e-6:
                raise SystemExit(f"B declaration: {n['slot']['name']} rest rotation {rot} is not identity")
            out[n["slot"]["name"]] = [float(x) for x in (n["slot"].get("position") or [0.0, 0.0, 0.0])]
        stack.extend(n.get("children", []))
    missing = [x for x in names if x not in out]
    if missing:
        raise SystemExit(f"B declaration: {missing} not found (export B first)")
    return out


def _neg(var: str, sign: float) -> str:
    """Blender の Z まわり sign × var を Resonite の Y まわりにした式（符号が逆）。"""
    return f"0.0 - {var}" if sign > 0 else var


def protograph_b(rest: dict[str, list[float]]) -> str:
    g5, g6 = gimmicks.g05(), gimmicks.g06()
    v5, v6 = gimmicks.G05_VARIABLES, gimmicks.G06_VARIABLES
    name = gimmicks.SPACE_NAME

    def clamp(var: str, spec: dict) -> str:
        return (f"if {var}0 < {_f(spec['min'])} then {_f(spec['min'])} "
                f"else if {var}0 > {_f(spec['max'])} then {_f(spec['max'])} else {var}0")

    lines = [
        "// Generated by modeling/p3_gimmicks/build_content.py (W10-B, G05 and G06). Do not edit by hand.",
        "// Local presentation: every user evaluates the output Drives from the shared WorldTimeDouble and the",
        "// HMC_P3 dynamic variables. No impulses and no synchronized writes.",
        f"module {gimmicks.B_MODULE}",
    ]
    for i, _ in enumerate(g5["ghosts"], start=1):
        lines += [f"out G{i}Position: float3", f"out G{i}Rotation: floatQ"]
    for i, _ in enumerate(g6["hinges"], start=1):
        lines.append(f"out D{i}Rotation: floatQ")
    lines += [
        "where {",
        "    T = WorldTimeDouble;",
        f'    G05IntensityIn = DynamicVariableValueInput<float>(VariableName = "{name}/G05Intensity");',
        f'    G05FrequencyIn = DynamicVariableValueInput<float>(VariableName = "{name}/G05Frequency");',
        f'    G05SpreadIn = DynamicVariableValueInput<float>(VariableName = "{name}/G05PhaseSpread");',
        f'    G06IntensityIn = DynamicVariableValueInput<float>(VariableName = "{name}/G06Intensity");',
        f'    G06FrequencyIn = DynamicVariableValueInput<float>(VariableName = "{name}/G06Frequency");',
        f'    G06PhaseIn = DynamicVariableValueInput<float>(VariableName = "{name}/G06Phase");',
        "    // A missing variable reads as 0, which keeps the ghosts at their rest pose and the doors closed.",
        "    // G05: floating ghosts (lift along Y, sway about Y at half the speed)",
        "    GI = Clamp01_Float(G05IntensityIn.Value);",
        "    GF0 = G05FrequencyIn.Value;",
        f"    GF = {clamp('GF', v5['G05Frequency'])};",
        "    GS = Clamp01_Float(G05SpreadIn.Value);",
        "    GBase = T * (GF->as<double>) * 6.283185307179586d;",
        "    GSd = GS->as<double>;",
    ]
    for i, g in enumerate(g5["ghosts"], start=1):
        lo, hi = g["bob_m"]
        mid, half = (lo + hi) / 2.0, (hi - lo) / 2.0
        r = rest[g["motion_root"]]
        lines += [
            f"    // {g['asset_id']}: phase {g['phase_deg']} deg, lift {lo}..{hi} m, sway +-{g['yaw_deg']} deg",
            f"    GTh{i} = GBase + GSd * {_f(math.radians(g['phase_deg']))}d;",
            f"    GLift{i} = GI * ({_f(mid)} + {_f(half)} * (Sin_Double(GTh{i})->as<float>));",
            f"    GYaw{i} = GI * {_f(g['yaw_deg'])} * (Sin_Double(GTh{i} * 0.5d)->as<float>);",
            f"    G{i}Position = Pack_Float3({_f(r[0])}, {_f(r[1])} + GLift{i}, {_f(r[2])});",
            f"    G{i}Rotation = FromEuler_floatQ(Pack_Float3(0.0, {_neg(f'GYaw{i}', 1.0)}, 0.0));",
        ]
    hold = gimmicks.G06_HOLD
    open_deg = g6["hinges"][0]["open_deg"]
    lines += [
        "    // G06: double door (closed, opening, open, closing), smoothstep between the holds",
        "    DI = Clamp01_Float(G06IntensityIn.Value);",
        "    DF0 = G06FrequencyIn.Value;",
        f"    DF = {clamp('DF', v6['G06Frequency'])};",
        "    DP = Clamp01_Float(G06PhaseIn.Value);",
        "    DTh = (T * (DF->as<double>) + (DP->as<double>)) * 6.283185307179586d;",
        "    DC = 0.5 - 0.5 * (Cos_Double(DTh)->as<float>);",
        f"    DX = Clamp01_Float((DC - {_f(hold)}) * {_f(1.0 / (1.0 - 2.0 * hold))});",
        "    DOpen = DX * DX * (3.0 - 2.0 * DX);",
        f"    DAng = DI * {_f(open_deg)} * DOpen;",
    ]
    for i, h in enumerate(g6["hinges"], start=1):
        lines += [
            f"    // {h['motion_root']}: opens {'+' if h['open_sign_blender_z'] > 0 else '-'}Z in Blender (inward)",
            f"    D{i}Rotation = FromEuler_floatQ(Pack_Float3(0.0, {_neg('DAng', h['open_sign_blender_z'])}, 0.0));",
        ]
    lines.append("}")
    return "\n".join(lines) + "\n"


def manifest_b(keys: dict[str, str]) -> dict:
    bindings = {}
    for i, g in enumerate(gimmicks.g05()["ghosts"], start=1):
        k = keys[g["motion_root"]]
        bindings[f"G{i}Position"] = {"target": f"$member:{district.relay_key(k, 'Position', 'g05')}.Value", "mode": "drive"}
        bindings[f"G{i}Rotation"] = {"target": f"$member:{district.relay_key(k, 'Rotation', 'g05')}.Value", "mode": "drive"}
    for i, h in enumerate(gimmicks.g06()["hinges"], start=1):
        k = keys[h["motion_root"]]
        bindings[f"D{i}Rotation"] = {"target": f"$member:{district.relay_key(k, 'Rotation', 'g06')}.Value", "mode": "drive"}
    return {
        "schemaVersion": "1",
        "projectDirectory": ".",
        "parent": f"{gimmicks.P3_ROOT_PATH}/{gimmicks.B_FLUX_SLOT}",
        "worldState": "../.resoloop/state/p2_B_mansion.json",
        "deployState": "../.resoloop/flux-state/p3_mansion_motion.json",
        "modules": [{"name": "p3-mansion-motion", "source": B_PG.name, "module": gimmicks.B_MODULE, "bindings": bindings}],
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
    bkeys = b_keys(args.state_dir)
    B_PG.write_text(protograph_b(b_rest()), encoding="utf-8")
    B_MANIFEST.write_text(json.dumps(manifest_b(bkeys), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"content": CONTENT.relative_to(PROJECT_ROOT).as_posix(), "protograph": PG.relative_to(PROJECT_ROOT).as_posix(),
                      "manifest": MANIFEST.relative_to(PROJECT_ROOT).as_posix(), "bodies": keys,
                      "g03_protograph": G03_PG.relative_to(PROJECT_ROOT).as_posix(),
                      "g03_manifest": G03_MANIFEST.relative_to(PROJECT_ROOT).as_posix(), "g03_base_linear": e0,
                      "b_protograph": B_PG.relative_to(PROJECT_ROOT).as_posix(),
                      "b_manifest": B_MANIFEST.relative_to(PROJECT_ROOT).as_posix(), "b_slots": bkeys},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
