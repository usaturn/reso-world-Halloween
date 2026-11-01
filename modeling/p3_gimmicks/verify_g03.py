"""W10-A: Resonite で動いている G03（噴水の水と光の周期変化）を、時間を空けた観察から検査する。

実行（プロジェクトのディレクトリ。対象のワールドを Resonite の前面に出しておく。背面では drive が進まない）:
    uv run python modeling/p3_gimmicks/verify_g03.py --url ws://localhost:<PORT>/ \\
        --raw-out <Git の外の JSON> --output review/p3_gimmicks/g03_live_checks.json [--windows 2 --gap 300]
    # 外から変えられる値の確認（値を変えて測り、元に戻す。ワールドに書く）
    uv run python modeling/p3_gimmicks/verify_g03.py --url ... --raw-out ... --output review/p3_gimmicks/g03_param_checks.json --param-check

式（build_content.py の G03 と同じ。E0 は P2 の水の発光、E1 は紫。どちらも線形の値）:
    θ = 2π f t、脈 = 1 + 0.5 A sin θ、混ぜ = A (1 − cos(θ/2)) / 2、発光 = I 脈 ((1 − 混ぜ) E0 + 混ぜ E1)

検査
- 構造: 基準は G03 を足す前の宣言（同じ export の model.apply.json）。A のすべての MeshRenderer の Materials を基準の並びと順番まで
  比べる（水だけは専用の材質 p3_g03_wm 1 つ）。G03 を足した後の宣言そのものも基準と比べる。元の材質の値（色・発光・金属・滑らかさ）は
  宣言のまま（色は profile を考慮して線形の値で比べる）。専用の材質の駆動しない値は元の材質と同じ。G03 と G01 のモジュールがある
- 動いている間（窓ごと）: 発光の色は 1 つの Component の 1 つの値なので、1 回の観察の 3 つの成分は同じ時刻の値。各観察から θ を
  求め（0〜4π の探索）、式との残差が小さいか（式の確認）。観察の時刻で θ を連続にして直線に当てはめた傾きが 2π f と 5% 以内か
  （時刻の速さ）。各観察の θ がその直線から 0.4 rad 以内か（平均の速さだけが合う、時刻に対して曲がった式を合格にしない）。窓の中で脈が 0.3 A 以上動くか（止まったグラフを合格にしない）。窓どうしで同じ式・速さか（値が積み上がらない）
- --param-check: G03Frequency = 0・−1（0 に収まる。時刻を止める。θ = 0）で発光が I E0 になるか、G03Intensity を 0.5・0・5（2 に収まる）・
  −1（0 に収まる）にして I 倍になるか、G03Swing = 0・−1（0 に収まる）で P2 の発光のまま一定か、G03Swing = 5（1 に収まる）で動いている
  間の観察が A = 1 の式に合うか、G03Frequency をゆっくり（0.004 Hz）にして 20 秒の間に θ が時刻どおり進むか。どれも元に戻し、戻した値が
  変える前と同じかを確かめる。G03Frequency の上限（1 Hz）は、観察の間隔（約 1.4 秒）では θ を連続にできないので実測しない
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from modeling.p3_gimmicks import build_content, gimmicks  # noqa: E402
from modeling.p3_gimmicks.verify_live import component_id, run_json, set_member, timed  # noqa: E402

STATE_DIR = Path("/workspaces/reso-world/worlds/reso-world-Halloween/.resoloop/state")
RESIDUAL_TOL = 0.01      # 式との残差（線形の値の各成分の差の最大）。float の計算と観察の丸めは 1e-5 程度
SPEED_TOL = 0.05         # 当てはめた θ の速さと 2π f の比の許容
LINEARITY_TOL_RAD = 0.4  # 各観察の θ と、当てはめた直線（ω t + 位相）との差の許容。観察の時刻のずれで実測は最大 0.13 rad
MAX_STEP_RAD = 1.8 * math.pi   # 隣の観察の間の θ の進みの上限（4π の周期の中で連続にできる範囲）
VARIATION = 0.3          # 窓の中で脈（1 + 0.5 A sin θ）が動くべき幅の、A に対する割合
VALUE_TOL = 1e-4         # 時刻を止めた標本の発光と I E0 の差の許容
CLOCK_FREQUENCY = 0.004  # ゆっくりの時刻の G03Frequency（Hz）。θ は 0.025 rad/s
CLOCK_WAIT_S = 20.0
CLOCK_TOL_RAD = 0.05
MATERIAL_TOL = 1e-5
OBSERVE_LIMIT = 64          # resoloop observe の 1 回の $member: の数の上限


def clamp(x: float, lo: float, hi: float) -> float:
    return min(max(float(x), lo), hi)


def clamped(params: dict[str, float]) -> tuple[float, float, float]:
    v = gimmicks.G03_VARIABLES
    return tuple(clamp(params[n], v[n]["min"], v[n]["max"]) for n in ("G03Intensity", "G03Frequency", "G03Swing"))


def model(theta: float, intensity: float, swing: float, e0, e1) -> list[float]:
    pulse = 1.0 + gimmicks.G03_PULSE_DEPTH * swing * math.sin(theta)
    mix = swing * (0.5 - 0.5 * math.cos(theta / 2.0))
    return [intensity * pulse * (a + mix * (b - a)) for a, b in zip(e0, e1)]


def to_linear(value: dict) -> list[float]:
    """観察した colorX（r・g・b・profile）を線形の [r, g, b] にする。"""
    rgb = [float(value[c]) for c in "rgb"]
    profile = value.get("profile")
    if profile == "Linear":
        return rgb
    if profile == "sRGB":
        return [gimmicks.srgb_to_linear(c) for c in rgb]
    raise ValueError(f"unknown color profile {profile}")


def fit_theta(obs: list[float], intensity: float, swing: float, e0, e1, steps: int = 4000) -> tuple[float, float]:
    """観察した発光に最も合う θ（0〜4π）と、そのときの残差（成分の差の最大）。"""
    def err(t: float) -> float:
        return max(abs(a - b) for a, b in zip(model(t, intensity, swing, e0, e1), obs))

    period = 4.0 * math.pi
    best = min((err(i * period / steps), i * period / steps) for i in range(steps))
    lo, hi = best[1] - period / steps, best[1] + period / steps
    for _ in range(60):
        m1, m2 = lo + (hi - lo) / 3.0, hi - (hi - lo) / 3.0
        if err(m1) <= err(m2):
            hi = m2
        else:
            lo = m1
    t = ((lo + hi) / 2.0) % period
    return t, err(t)


def check_samples(samples: list[dict], params: dict[str, float], e0, e1) -> tuple[dict, list[str]]:
    """動いている間の観察（{"t": 時刻, "linear": [r, g, b]}）の検査。"""
    problems: list[str] = []
    intensity, freq, swing = clamped(params)
    fits = []
    for s in samples:
        theta, res = fit_theta(s["linear"], intensity, swing, e0, e1)
        fits.append({"t": s["t"], "theta": theta, "residual": res})
        if res > RESIDUAL_TOL:
            problems.append(f"G03 sample at {s['t']:.2f}: residual {res:.4f} > {RESIDUAL_TOL} (the glow does not follow the formula)")
    out: dict = {"samples": len(samples), "max_residual": max((f["residual"] for f in fits), default=None)}
    if len(fits) < 3:
        problems.append(f"G03: only {len(fits)} samples")
        return out, problems
    unwrapped = [fits[0]["theta"]]
    for prev, cur in zip(fits, fits[1:]):
        step = (cur["theta"] - prev["theta"]) % (4.0 * math.pi)
        dt = cur["t"] - prev["t"]
        if 2.0 * math.pi * freq * dt > MAX_STEP_RAD:
            problems.append(f"G03: samples {dt:.2f} s apart; theta may advance more than {MAX_STEP_RAD:.2f} rad")
        unwrapped.append(unwrapped[-1] + step)
    ts = [f["t"] for f in fits]
    tm, um = sum(ts) / len(ts), sum(unwrapped) / len(unwrapped)
    den = sum((t - tm) ** 2 for t in ts)
    slope = sum((t - tm) * (u - um) for t, u in zip(ts, unwrapped)) / den if den else 0.0
    expected = 2.0 * math.pi * freq
    deviation = max(abs(u - (um + slope * (t - tm))) for t, u in zip(ts, unwrapped))
    out.update({"theta_speed_rad_per_s": slope, "expected_rad_per_s": expected, "max_theta_deviation_rad": deviation})
    if expected > 0 and abs(slope / expected - 1.0) > SPEED_TOL:
        problems.append(f"G03: theta speed {slope:.4f} rad/s, expected {expected:.4f} (tolerance {SPEED_TOL:.0%})")
    if deviation > LINEARITY_TOL_RAD:
        problems.append(f"G03: theta leaves the straight line w*t+phase by {deviation:.3f} rad (tolerance {LINEARITY_TOL_RAD})")
    pulses = [1.0 + gimmicks.G03_PULSE_DEPTH * swing * math.sin(f["theta"]) for f in fits]
    lum = [0.2126 * s["linear"][0] + 0.7152 * s["linear"][1] + 0.0722 * s["linear"][2] for s in samples]
    out.update({"pulse_min": min(pulses), "pulse_max": max(pulses), "luminance_min": min(lum), "luminance_max": max(lum)})
    if swing > 0 and max(pulses) - min(pulses) < VARIATION * swing:
        problems.append(f"G03: pulse moved only {max(pulses) - min(pulses):.3f} in the window (expected at least {VARIATION * swing:.3f})")
    return out, problems


def check_frozen(linear: list[float], intensity: float, e0) -> list[str]:
    """時刻を止めた（θ = 0）標本: 発光は I E0（G03Intensity を収めた値）。"""
    want = [intensity * a for a in e0]
    diff = max(abs(a - b) for a, b in zip(linear, want))
    return [] if diff <= VALUE_TOL else [f"G03 frozen: emissive {linear} != I*E0 {want} (diff {diff:.5f})"]


def check_clock(lin1: list[float], t1: float, lin2: list[float], t2: float, intensity: float, swing: float, e0, e1) -> tuple[dict, list[str]]:
    th1, r1 = fit_theta(lin1, intensity, swing, e0, e1)
    th2, r2 = fit_theta(lin2, intensity, swing, e0, e1)
    step = (th2 - th1 + 2.0 * math.pi) % (4.0 * math.pi) - 2.0 * math.pi
    want = 2.0 * math.pi * CLOCK_FREQUENCY * (t2 - t1)
    out = {"dt_s": t2 - t1, "theta_step_rad": step, "expected_rad": want, "residuals": [r1, r2]}
    problems = []
    if max(r1, r2) > RESIDUAL_TOL:
        problems.append(f"G03 clock: residual {max(r1, r2):.4f} > {RESIDUAL_TOL}")
    if abs(step - want) > CLOCK_TOL_RAD:
        problems.append(f"G03 clock: theta advanced {step:.4f} rad in {t2 - t1:.1f} s, expected {want:.4f}")
    return out, problems


# --- 構造（宣言と観察の照合） ---

def renderer_materials(doc: dict) -> dict[str, list[str]]:
    """宣言の MeshRenderer ごとの Materials（材質の Component のキーの並び）。"""
    out: dict[str, list[str]] = {}
    stack = [doc]
    while stack:
        n = stack.pop()
        for c in n.get("components", []):
            if c["type"] == "FrooxEngine.MeshRenderer":
                out[c["key"]] = [str(m).split(":", 1)[1] if str(m).startswith("$component:") else str(m)
                                 for m in c["fields"].get("Materials") or []]
        stack.extend(n.get("children", []))
    return out


def declared_materials(model_doc: dict, p2_doc: dict) -> dict:
    """基準は G03 を足す前の宣言（同じ export の model.apply.json。district.add_g03_material の前）。

    水の MeshRenderer は基準で元の材質 1 つだけを指し、ほかの MeshRenderer は基準と同じ並びのままであるべき。
    G03 を足した後の宣言（p2.apply.json）が基準と違う所は decl_problems に書く（宣言そのものの付け替えの誤り）。
    """
    g = gimmicks.g03()
    comps: dict[str, tuple[str, dict]] = {}
    stack = [(p2_doc, p2_doc["slot"]["name"])]
    while stack:
        n, path = stack.pop()
        for c in n.get("components", []):
            comps[c["key"]] = (path, c)
        stack.extend((ch, f"{path}/{ch['slot']['name']}") for ch in n.get("children", []))
    water = [k for k, (path, c) in comps.items() if c["type"] == "FrooxEngine.MeshRenderer" and path.endswith("/" + g["water_slot"])]
    if len(water) != 1:
        raise ValueError(f"expected one water MeshRenderer, found {water}")
    baseline = renderer_materials(model_doc)
    if water[0] not in baseline or len(baseline[water[0]]) != 1:
        raise ValueError(f"the water MeshRenderer must use one material before G03: {baseline.get(water[0])}")
    source = baseline[water[0]][0]
    expected = {r: ([gimmicks.G03_MATERIAL_KEY] if r == water[0] else ms) for r, ms in baseline.items()}
    after = renderer_materials(p2_doc)
    decl_problems = [f"declaration {r}: {after.get(r)} != expected {ms}" for r, ms in expected.items() if after.get(r) != ms]
    decl_problems += [f"declaration {r}: not in the baseline" for r in after if r not in expected]
    shared = sorted(r for r, ms in baseline.items() if source in ms and r != water[0])
    return {"water_renderer": water[0], "material": gimmicks.G03_MATERIAL_KEY, "material_decl": comps[gimmicks.G03_MATERIAL_KEY][1],
            "source": source, "source_decl": comps[source][1], "shared_renderers": shared, "expected": expected,
            "decl_problems": decl_problems}


def latest_export_dir() -> Path:
    key = gimmicks.g03()["district"]
    dirs = [d for d in sorted((PROJECT_ROOT / "exports" / "p2_static").glob(f"{key}-*"))
            if (d / "p2.apply.json").is_file() and (d / "model.apply.json").is_file()]
    return dirs[-1]


def _color_linear(c) -> list[float]:
    """色を線形の [r, g, b, a] にする。観察は profile 付きの dict、宣言の配列は sRGB（resoloop の colorX の既定）。"""
    if isinstance(c, dict):
        return to_linear(c) + [float(c.get("a", 1.0))]
    return [gimmicks.srgb_to_linear(x) for x in c[:3]] + [float(x) for x in c[3:4]]


def _close(a, b) -> bool:
    if isinstance(b, (list, tuple)):
        a, b = _color_linear(a), _color_linear(b)
        return len(a) == len(b) and all(abs(x - y) <= MATERIAL_TOL for x, y in zip(a, b))
    return abs(float(a) - float(b)) <= MATERIAL_TOL


def check_structure(obs: dict, decl: dict) -> list[str]:
    """obs: {"materials": {renderer: [targetId...]}, "ids": {key: componentId}, "fields": {key: {member: value}}}。

    A のすべての MeshRenderer の Materials を、G03 を足す前の宣言の並び（水だけは専用の材質）と順番まで比べる。
    """
    problems: list[str] = list(decl.get("decl_problems", []))
    for r, keys in decl["expected"].items():
        want = [obs["ids"].get(k, f"<unobserved {k}>") for k in keys]
        if obs["materials"].get(r) != want:
            problems.append(f"{r}: materials {obs['materials'].get(r)} != expected {keys}")
    for member, want in decl["source_decl"]["fields"].items():
        if not _close(obs["fields"][decl["source"]][member], want):
            problems.append(f"shared material {decl['source']}.{member} changed: {obs['fields'][decl['source']][member]} != {want}")
    for member, want in decl["material_decl"]["fields"].items():
        if not _close(obs["fields"][decl["material"]][member], want):
            problems.append(f"{decl['material']}.{member} differs from the shared material: {obs['fields'][decl['material']][member]} != {want}")
    if obs["fields"][decl["material"]].get("Enabled") is not True:
        problems.append(f"{decl['material']} is not enabled")
    return problems


# --- 観察 ---

def a_state() -> Path:
    return STATE_DIR / "p2_A_plaza.json"


def observe_params(url: str) -> dict[str, float]:
    sels = [f"$member:{v['key']}.Value" for v in gimmicks.G03_VARIABLES.values()]
    data = run_json(["resoloop", "observe", *sels, "--state", str(STATE_DIR / "p3_gimmicks.json"), "--url", url, "--json"])
    return {n: float(data["data"]["values"][f"$member:{v['key']}.Value"]["member"]["value"]) for n, v in gimmicks.G03_VARIABLES.items()}


def observe_emissive(url: str, raw: list) -> dict:
    sel = f"$member:{gimmicks.G03_MATERIAL_KEY}.EmissiveColor"
    t, data = timed(["resoloop", "observe", sel, "--state", str(a_state()), "--url", url, "--json"])
    value = data["data"]["values"][sel]["member"]["value"]
    raw.append({"t": t, "emissive": value})
    return {"t": t, "value": value, "linear": to_linear(value)}


def observe_structure(url: str, decl: dict) -> dict:
    sels = [f"$member:{r}.Materials" for r in decl["expected"]]
    members = {decl["source"]: list(decl["source_decl"]["fields"]), decl["material"]: [*decl["material_decl"]["fields"], "Enabled"]}
    for k in sorted({m for ms in decl["expected"].values() for m in ms}):
        members.setdefault(k, ["Enabled"])
    sels += [f"$member:{k}.{m}" for k, ms in members.items() for m in ms]
    vals: dict = {}
    for i in range(0, len(sels), OBSERVE_LIMIT):   # resoloop observe は 1 回に 64 個まで（OBSERVE_LIMIT）
        chunk = sels[i:i + OBSERVE_LIMIT]
        vals |= run_json(["resoloop", "observe", *chunk, "--state", str(a_state()), "--url", url, "--json"])["data"]["values"]
    obs: dict = {"materials": {}, "ids": {}, "fields": {k: {} for k in members}}
    for sel, v in vals.items():
        key, member = sel[len("$member:"):].rsplit(".", 1)
        if member == "Materials":
            obs["materials"][key] = [e.get("targetId") for e in v["member"]["elements"]]
        else:
            obs["ids"][key] = v["componentId"]
            obs["fields"][key][member] = v["member"]["value"]
    return obs


def observe_modules(url: str) -> dict:
    data = run_json(["resoloop", "hierarchy", "--under", gimmicks.P3_ROOT_PATH, "--depth", "2", "--url", url, "--json"])["data"]
    out = {}
    for child in data.get("children") or []:
        out[child["name"]] = [c["name"] for c in child.get("children") or []]
    return out


def ids_free(obs: dict, keep: set[str]) -> dict:
    """記録用に ResoniteLink の ID を外し、参照先が専用の材質か元の材質かだけを書く。"""
    ids = {v: k for k, v in obs["ids"].items()}
    shown = {r: ts for r, ts in obs["materials"].items() if r in keep}
    return {"renderers_compared": len(obs["materials"]),
            "materials": {r: [ids.get(t, "unknown") for t in ts] for r, ts in shown.items()},
            "fields": {k: v for k, v in obs["fields"].items() if v and set(v) != {"Enabled"}}}


def window(url: str, duration: float, decl: dict, e0, e1, raw: list) -> dict:
    params = observe_params(url)
    struct = observe_structure(url, decl)
    modules = observe_modules(url)
    problems = check_structure(struct, decl)
    if gimmicks.G03_MODULE not in modules.get(gimmicks.G03_FLUX_SLOT, []):
        problems.append(f"{gimmicks.G03_MODULE} is not under {gimmicks.G03_FLUX_SLOT}: {modules}")
    if gimmicks.G01_MODULE not in modules.get(gimmicks.G01_FLUX_SLOT, []):
        problems.append(f"{gimmicks.G01_MODULE} is not under {gimmicks.G01_FLUX_SLOT}: {modules}")
    samples = []
    end = time.time() + duration
    while time.time() < end:
        samples.append(observe_emissive(url, raw))
    summary, p = check_samples(samples, params, e0, e1)
    problems += p
    return {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(samples[0]["t"])), "params": params,
            "structure": ids_free(struct, {decl["water_renderer"], *decl["shared_renderers"]}), "modules": modules, "g03": summary, "problems": problems}


def param_check(url: str, e0, e1, raw: list) -> dict:
    out: dict = {"problems": []}
    p3_state = STATE_DIR / "p3_gimmicks.json"
    before = observe_params(url)
    cids = {n: component_id(f"$member:{v['key']}.Value", p3_state, url) for n, v in gimmicks.G03_VARIABLES.items()}

    def put(name: str, value: float) -> None:
        set_member(cids[name], "Value", repr(float(value)), url)

    try:
        frozen = []
        # 時刻を止める: G03Frequency = 0 と、範囲の下へはみ出した −1（0 に収まる）
        for freq, intensity in ((0.0, before["G03Intensity"]), (0.0, 0.5), (0.0, 0.0), (0.0, 5.0), (0.0, -1.0), (-1.0, before["G03Intensity"])):
            put("G03Frequency", freq)
            put("G03Intensity", intensity)
            time.sleep(1.0)
            params = observe_params(url)
            want_i, want_f, _ = clamped(params)
            reads = [observe_emissive(url, raw) for _ in range(2)]
            problems = [] if want_f == 0.0 else [f"G03Frequency {params['G03Frequency']} is not clamped to 0 by the check"]
            problems += [q for r in reads for q in check_frozen(r["linear"], want_i, e0)]
            frozen.append({"G03Frequency": params["G03Frequency"], "G03Intensity": params["G03Intensity"], "clamped_intensity": want_i,
                           "linear": [r["linear"] for r in reads], "problems": problems})
            out["problems"] += problems
        out["frozen"] = frozen
        put("G03Intensity", before["G03Intensity"])
        put("G03Frequency", before["G03Frequency"])
        # G03Swing = 0 と −1（0 に収まる）: 動いている間も P2 の発光のまま一定
        out["swing_zero"] = []
        for swing in (0.0, -1.0):
            put("G03Swing", swing)
            time.sleep(1.0)
            params = observe_params(url)
            reads = [observe_emissive(url, raw) for _ in range(3)]
            problems = [q for r in reads for q in check_frozen(r["linear"], clamped(params)[0], e0)]
            out["swing_zero"].append({"G03Swing": params["G03Swing"], "linear": [r["linear"] for r in reads], "problems": problems})
            out["problems"] += problems
        # G03Swing = 5（1 に収まる）: 動いている間の観察が A = 1 の式に合うか（収めていなければ脈が 1 ± 2.5 になり残差で外れる）
        put("G03Swing", 5.0)
        time.sleep(1.0)
        params = observe_params(url)
        samples = []
        end = time.time() + 12.0
        while time.time() < end:
            samples.append(observe_emissive(url, raw))
        summary, problems = check_samples(samples, params, e0, e1)
        out["swing_over"] = {"G03Swing": params["G03Swing"], "clamped": clamped(params)[2], "g03": summary, "problems": problems}
        out["problems"] += problems
        put("G03Swing", before["G03Swing"])
        put("G03Frequency", CLOCK_FREQUENCY)
        time.sleep(1.0)
        intensity, _, swing = clamped(observe_params(url))
        r1 = observe_emissive(url, raw)
        time.sleep(CLOCK_WAIT_S)
        r2 = observe_emissive(url, raw)
        clock, problems = check_clock(r1["linear"], r1["t"], r2["linear"], r2["t"], intensity, swing, e0, e1)
        out["clock"] = clock | {"problems": problems}
        out["problems"] += problems
    finally:
        for name, value in before.items():
            put(name, value)
    time.sleep(1.0)
    after = observe_params(url)
    out["before"], out["restored"] = before, after
    if any(abs(after[n] - before[n]) > 1e-6 for n in before):
        out["problems"].append(f"G03 values were not restored: {after} != {before}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", required=True)
    ap.add_argument("--raw-out", type=Path, required=True, help="生の観察の保存先（Git の外）")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--windows", type=int, default=1)
    ap.add_argument("--gap", type=float, default=300.0)
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--param-check", action="store_true")
    args = ap.parse_args(argv)
    if args.raw_out.exists():
        raise SystemExit(f"{args.raw_out} already exists")
    export = latest_export_dir()
    doc = json.loads((export / "p2.apply.json").read_text(encoding="utf-8"))
    decl = declared_materials(json.loads((export / "model.apply.json").read_text(encoding="utf-8")), doc)
    e0 = build_content.g03_base_linear(doc)
    e1 = list(gimmicks.G03_SHIFT_EMISSIVE_LINEAR)
    raw: list = []
    result: dict = {"tool": "modeling/p3_gimmicks/verify_g03.py", "export": latest_export_dir().name,
                    "e0_linear": e0, "e1_linear": e1, "shared_renderers": decl["shared_renderers"],
                    "material": decl["material"], "source_material": decl["source"]}
    if args.param_check:
        result["param_check"] = param_check(args.url, e0, e1, raw)
        problems = result["param_check"]["problems"]
    else:
        result["windows"] = []
        for i in range(args.windows):
            if i:
                time.sleep(args.gap)
            result["windows"].append(window(args.url, args.duration, decl, e0, e1, raw))
        problems = [p for w in result["windows"] for p in w["problems"]]
        speeds = [w["g03"].get("theta_speed_rad_per_s") for w in result["windows"]]
        result["speeds_rad_per_s"] = speeds
    result["ok"] = not problems
    args.raw_out.parent.mkdir(parents=True, exist_ok=True)
    args.raw_out.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "problems": problems}, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
