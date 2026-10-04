"""t7 (2026-10-03, judge r6 item 1: change the method): trace the user's photo's skirt hems lobe by lobe in the photo's
fitted camera (photo_cam.py = t4/ref_profile.json, viewing the +Y ring handle) and unproject the trace onto our collar,
in the drum's DESIGN units. The build (taiko_skirt.py) reads the result from Scripts/dojo/props/taiko/skirt_trace_t7.json.

  hems     upper skirt (the +X head, up in the photo): the hem's lower edge = the first wood row below the hide, per
           column; lower skirt (-X head): its upper edge = the first row of a 4-row hide run scanning down from row 770
           (the lacquer above). Hide = R/G < 1.45 and luminance > 60 (wood is R/G 1.9-3.6 or near black). Slit columns
           bridged, median-filtered (7 px).
  slits    picked by eye on 3x crops (the dark open V interiors / tube ends), each refined to the darkest column within
           +-6 px in the 22 rows on the hem side.
  unproject each hem column's ray hits the surface of revolution r = body_r(x) + N_VIS (the rolled lip's visible edge,
           about the lip's centre-line height) -> (x, lathe angle th); the slits the same at their hem row.
  ears     the photo outline (fg mask) per row on both sides through the skirt rows (kept as pixels: the build's
           skirt is checked against them in the same camera by check_skirt_t7.py).
Writes t7/skirt_trace.json, t7/skirt_trace_debug.png and Scripts/dojo/props/taiko/skirt_trace_t7.json.
Run: py -3 trace_skirt_t7.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_fill_holes, median_filter

T7 = Path(__file__).resolve().parent
ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
OUT_T7 = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko" / "t7"
SCRIPTS = Path(sys.argv[sys.argv.index("--scripts") + 1]) if "--scripts" in sys.argv else ROOT / "Scripts" / "dojo" / "props" / "taiko"
sys.path.insert(0, str(T7))
sys.path.insert(0, str(SCRIPTS))
import photo_cam as PC  # noqa: E402
import taiko_uv as UVL  # noqa: E402

img = Image.open(ROOT / "References" / "Dojo" / "taiko_tacks_ref_user.webp").convert("RGB")
a = np.asarray(img).astype(float)
lum = a.mean(2)
rg = a[..., 0] / np.maximum(a[..., 1], 1)
fg = binary_fill_holes(a.min(2) < 240)
hide = (rg < 1.45) & (lum > 60) & fg
N_VIS = 0.012                  # design: the visible lip edge's height above the wood
SLITS = {"upper": [153, 197, 290, 340, 357, 412, 565, 620, 640, 693, 797, 847],
         "lower": [245, 337, 393, 456, 575, 633, 683, 775, 825]}
U = np.arange(110, 915)


def hem_upper(u):
    for v in range(250, 380):
        if fg[v, u] and not hide[v:v + 6, u].any():
            return v
    return np.nan


def hem_lower(u):
    for v in range(770, 915):
        if hide[v:v + 4, u].all():
            return v
    return np.nan


def clean(raw, slits, half=6):
    h = np.array(raw, float)
    for s in slits:                                   # bridge the slit columns
        h[(U >= s - half) & (U <= s + half)] = np.nan
    ok = ~np.isnan(h)
    h = np.interp(U, U[ok], h[ok])
    return median_filter(h, 7, mode="nearest")


res = {"camera": "t4/ref_profile.json camera_fit (photo_cam.py, t7: the +Y handle side)", "n_vis_design_m": N_VIS,
       "x_sk_design": UVL.X_SK}
dbg = img.copy()
d = ImageDraw.Draw(dbg)
for key, fn, s, u_lo, u_hi in (("upper", hem_upper, 1, 160, 880), ("lower", hem_lower, -1, 200, 840)):
    raw = [fn(u) for u in U]
    h0 = clean(raw, SLITS[key])
    # refine the slits: the darkest column within +-6 px over the 22 rows on the hide side of the hem
    sl_px = []
    for u0 in SLITS[key]:
        v0 = float(np.interp(u0, U, h0))
        best = None
        for u in range(u0 - 6, u0 + 7):
            rows = range(int(v0) - 22, int(v0) - 2) if s > 0 else range(int(v0) + 2, int(v0) + 22)
            m = float(np.mean([lum[v, u] for v in rows]))
            if best is None or m < best[0]:
                best = (m, u)
        sl_px.append(best[1])
    h = clean(raw, sl_px)
    keep = (U >= u_lo) & (U <= u_hi)                  # the front, clear of the silhouette ears
    rf = lambda x: UVL.body_r(np.abs(x)) + N_VIS      # noqa: E731
    xr = (0.30, 0.70) if s > 0 else (-0.70, -0.30)
    pts = []
    for u, v in zip(U[keep], h[keep]):
        hit = PC.hit_revolution(u, v, rf, *xr)
        if hit:
            x, r, th = hit
            pts.append((int(u), round(float(v), 1), round(abs(x), 5), round(th, 5)))
            d.point((u, v), fill=(0, 255, 0) if s > 0 else (0, 255, 255))
    sl = []
    for u in sl_px:
        v = float(np.interp(u, U, h))
        hit = PC.hit_revolution(u, v, rf, *xr)
        if hit:
            sl.append((int(u), round(v, 1), round(abs(hit[0]), 5), round(hit[2], 5)))
            d.line([(u, v - 30 * s), (u, v + 4 * s)], fill=(255, 0, 0), width=1)
    th = [p[3] for p in pts]
    hx = [p[2] for p in pts]
    widths = [round(1000 * (UVL.body_r(0.5 * (a_[2] + b_[2])) + N_VIS) * abs(b_[3] - a_[3]), 1) for a_, b_ in zip(sl, sl[1:])]
    res[key] = {"head": s, "hem_samples_u_v_x_th": pts, "slits_u_v_x_th": sl, "lobe_widths_design_mm": widths,
                "hem_x_design_min_max": [round(min(hx), 4), round(max(hx), 4)],
                "hem_depth_below_X_SK_design_mm_min_max": [round(1000 * (UVL.X_SK - max(hx)), 1),
                                                            round(1000 * (UVL.X_SK - min(hx)), 1)],
                "th_range_deg": [round(math.degrees(min(th)), 1), round(math.degrees(max(th)), 1)]}

# the silhouette outline per row through the skirt rows (pixels), both sides
sil = {}
for key, rows in (("upper", range(150, 330)), ("lower", range(660, 830))):
    for side in (-1, 1):
        out = []
        for v in rows:
            xs = np.where(fg[v])[0]
            if not len(xs):
                continue
            u = xs.min() - 0.5 if side < 0 else xs.max() + 0.5
            out.append((v, round(float(u), 1)))
            d.point((u, v), fill=(255, 0, 255))
        sil[f"{key}_{'left' if side < 0 else 'right'}"] = out
res["silhouette_rows_v_u"] = sil
OUT_T7.mkdir(parents=True, exist_ok=True)
(OUT_T7 / "skirt_trace.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
(SCRIPTS / "skirt_trace_t7.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
dbg.save(OUT_T7 / "skirt_trace_debug.png")
for key in ("upper", "lower"):
    r_ = res[key]
    print(key, "hem depth mm", r_["hem_depth_below_X_SK_design_mm_min_max"], "th deg", r_["th_range_deg"])
    print("  slits", [(u, round(math.degrees(t), 1), round(1000 * (UVL.X_SK - x), 1)) for u, v, x, t in r_["slits_u_v_x_th"]])
    print("  lobe widths mm", r_["lobe_widths_design_mm"])
