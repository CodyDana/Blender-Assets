"""VERIFY LANDSCAPE ROUND: my own look numbers on the final captures (fix/caps, read only) vs the references.
Out: verify/look.json. Luma = Rec.709 on sRGB codes. Boxes for CAM_LandscapeRef are the builder's region boxes in the
reference frame (1024 x 1536; ours resized to it) - I re-measure, I do not copy its numbers."""
import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image

R = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
CAPS = R / "WorkFiles/dojo/build/landscape/fix/caps"
REF = R / "References/Dojo"
OUT = R / "WorkFiles/dojo/build/landscape/verify/look.json"


def load(p, size=None):
    im = Image.open(p).convert("RGB")
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im).astype(np.float64)


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def glob_stats(a):
    y = luma(a)
    return {"under40_pct": round(100 * float((y < 40).mean()), 2), "near_black_lt10_pct": round(100 * float((y < 10).mean()), 2),
            "mean": round(float(y.mean()), 1), "p10": round(float(np.percentile(y, 10)), 1),
            "p50": round(float(np.percentile(y, 50)), 1), "p90": round(float(np.percentile(y, 90)), 1),
            "clipped_ge250_pct": round(100 * float((y >= 250).mean()), 2)}


def region(a, boxes):
    px = np.concatenate([a[y0:y1, x0:x1].reshape(-1, 3) for (x0, y0, x1, y1) in boxes])
    m = np.median(px, axis=0)
    h, l, s = colorsys.rgb_to_hls(*(m / 255.0))
    return {"median_srgb": [int(v) for v in m], "hue_deg": round(h * 360, 1), "sat_hls": round(s, 3), "light": round(l, 3),
            "r_over_b": round(float(m[0] / max(m[2], 1)), 3)}


def foam(a, boxes):
    px = np.concatenate([a[y0:y1, x0:x1].reshape(-1, 3) for (x0, y0, x1, y1) in boxes])
    y = luma(px)
    mx, mn = px.max(1), px.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    f = (y > 140) & (sat < 0.28)
    w = f | ((px[:, 1] > px[:, 0]) & (px[:, 2] > px[:, 0]))
    return {"foam_pct_of_water": round(100 * float(f.sum()) / max(int(w.sum()), 1), 1), "water_px": int(w.sum())}


BOX = json.loads((CAPS / "json/measure_landscape.json").read_text(encoding="utf-8"))["boxes"]
out = {}
ref = load(REF / "dojo_landscape_ref.png")
ours = load(CAPS / "CAM_LandscapeRef.png", (ref.shape[1], ref.shape[0]))
out["CAM_LandscapeRef_vs_landscape_ref"] = {
    "frame": [ref.shape[1], ref.shape[0]], "reference": glob_stats(ref), "ours": glob_stats(ours),
    "regions": {k: {"reference": region(ref, v), "ours": region(ours, v)} for k, v in BOX.items()},
    "foam": {"reference": foam(ref, BOX["foam"]), "ours": foam(ours, BOX["foam"])},
    "mean_abs_diff_srgb": round(float(np.abs(ref - ours).mean()), 1)}
r2 = load(REF / "dojo1_reference2.png")
o2 = load(CAPS / "CAM_Ref2Match.png", (r2.shape[1], r2.shape[0]))
out["CAM_Ref2Match_vs_ref2"] = {"frame": [r2.shape[1], r2.shape[0]], "reference": glob_stats(r2), "ours": glob_stats(o2)}
# health of every final still
health = {}
for p in sorted(CAPS.glob("C*_*.png")):
    a = load(p)
    health[p.stem] = {"size": [a.shape[1], a.shape[0]], **glob_stats(a)}
out["health"] = health
# the earlier stage (fxlight) vs final, per camera, for drift
prev = R / "WorkFiles/dojo/build/landscape/fxlight/caps"
drift = {}
for p in sorted(CAPS.glob("CAM_*.png")):
    q = prev / p.name
    if q.exists():
        a, b = load(p), load(q)
        if a.shape == b.shape:
            drift[p.stem] = {"mean_luma_fx_stage": round(float(luma(b).mean()), 1), "mean_luma_final": round(float(luma(a).mean()), 1)}
out["vs_fxlight_stage"] = drift
OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out["CAM_LandscapeRef_vs_landscape_ref"]["reference"]), json.dumps(out["CAM_LandscapeRef_vs_landscape_ref"]["ours"]))
print("foam", out["CAM_LandscapeRef_vs_landscape_ref"]["foam"])
for k, v in out["CAM_LandscapeRef_vs_landscape_ref"]["regions"].items():
    print(k, v["reference"]["median_srgb"], v["ours"]["median_srgb"], v["ours"]["hue_deg"])
print("ref2", out["CAM_Ref2Match_vs_ref2"])
for k, v in health.items():
    print(k, v)
