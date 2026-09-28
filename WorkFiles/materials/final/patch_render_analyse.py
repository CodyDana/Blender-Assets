from pathlib import Path

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects/Scripts/unreal/materials")


def patch(fname, pairs):
    p = ROOT / fname
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if old not in s:
            raise SystemExit(f"{fname}: NOT FOUND {old[:90]!r}")
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")
    print("patched", fname)


patch("verify/analyse_captures.py", [
    ('''import recolour_common as rc  # noqa: E402''', '''import np_twin as tw  # noqa: E402  (v2 twin: the final-pass graphs, node for node)
import recolour_common as rc  # noqa: E402'''),
    ('''def fabric_model(job, inp, colour):
    p = job["params"]
    n = p["Detail Bias"] + p["Detail Scale"] * inp["d"]
    k = {"mean": p["Detail Mean"], "highlight_ratio": p["Detail Highlight Ratio"],
         "moments_low": p["Detail Moments Low"], "moments_high": p["Detail Moments High"]}
    a, info = rc.tint_detail(n.ravel(), colour, k, strength=1.0, follow=p["Dark Detail Follow"],
                             ceiling=p["Albedo Ceiling"])
    return rc.rolloff(a).reshape(*n.shape, 3), info''', '''def fabric_model(job, inp, colour):
    """v2 twin (np_twin.fabric_albedo) at mip 0: the captures sample mip 0 (one pixel per texel), so K = 1."""
    a, info = tw.fabric_albedo(job["params"], inp["d"], colour, lod=0.0)
    return a, {k: v for k, v in info.items() if isinstance(v, float)}'''),
    ('''def paper_model(job, inp, overrides):
    p = dict(job["params"])
    for key, v in overrides.items():
        p[key] = v
    paper = np.asarray(p["Paper Colour"][:3], np.float64)
    black = np.asarray(p["Black Ink Colour"][:3], np.float64)
    red = np.asarray(p["Red Ink Colour"][:3], np.float64)
    black_dry = (black + (paper - black) * p["Black Ink Dry Paper Mix"]) * np.asarray(p["Black Ink Dry Gain"][:3])
    red_dry = rc.s2l(p["Red Ink Dry Value Scale"] * rc.l2s(red))
    y = float(red @ rc.LUM)
    red_pool = (y + (red - y) * p["Red Ink Pool Saturation"]) * np.asarray(p["Red Ink Pool Gain"][:3])
    w = inp["iw"]
    tot = (paper * inp["pd_rgb"] * p["Paper Weight Scale"] + black * w[..., 0:1] + black_dry * w[..., 1:2]
           + red * w[..., 2:3] + red_dry * w[..., 3:4] + red_pool * inp["pd_a"])
    tot = np.minimum(tot, p["Albedo Ceiling"])
    ao = float(p.get("Baked AO In Colour", 1.0))
    tot = tot * (1.0 + (inp["ao"] - 1.0) * ao)
    der = {"BlackDry": black_dry.tolist(), "RedDry": red_dry.tolist(), "RedPool": red_pool.tolist()}
    return tot, der''', '''def paper_model(job, inp, overrides):
    """v2 twin (np_twin.paper_albedo): paper colour guards, neutral red pool, the art's 0.962 ceiling, AO in colour."""
    p = dict(job["params"])
    for key, v in overrides.items():
        p[key] = v
    tot, _, der = tw.paper_albedo(p, inp, ao_in_colour=float(p.get("Baked AO In Colour", 1.0)))
    return tot, der'''),
])

patch("np_render.py", [
    ('''STRESS = {"white": (0.8, 0.8, 0.8), "saturated_red": (0.8, 0.02, 0.02), "near_black": (0.01, 0.01, 0.01)}''',
     '''# v2: the picks a buyer types first (sRGB hex FFFFFF / FF0000 / 000000 are linear 1 / 0 exactly); the full stress
# (9 colours, mip 4) is WorkFiles/materials/final/recolour/fs_ue_capture.py
STRESS = {"white_FFFFFF": (1.0, 1.0, 1.0), "red_FF0000": (1.0, 0.0, 0.0), "black_000000": (0.0, 0.0, 0.0)}'''),
])
