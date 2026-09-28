"""Knot / smoothing choice by measurement with a SMOOTH known truth, scored at 4x.

Truth: each group traced from the real source with a deliberately stiff fit (knot 2.5 px,
smooth 0.1) - smooth edges, sharp tips, the reference's shapes.  It is photographed like the
reference (pixel box + Gaussian 0.4 px, density, paper noise, 8-bit), re-traced with each
candidate fit, and scored against the truth on the 4x grid: IoU, edge distance and the
pixel-grid ripple (spectral power of the edge's normal wobble at 0.6-1.6 px wavelength) -
the staircase a fine fit copies from the half-level contour of an aliased edge.

usage: python pbt_bench_knot.py [groups]   -> pbt_bench_knot.json
"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_trace as PT
import types

groups = (sys.argv[1].split(",") if len(sys.argv) > 1 else ["emblem", "col_TR", "centre", "ring"])
L = PT.load_layers()
H, W = L.black.shape
masks = PT.group_masks(L)
regions = PT.group_regions(L, masks)
paper = T.erode((L.black < 0.5) & (L.red < 0.5) & L.inside, 4)
NOISE = float(np.std(L.black[paper & (L.xm > 8) & (L.xm < 62) & (L.ym > 10) & (L.ym < 150)]))
DENS = 0.986
F4 = 4
rng = np.random.default_rng(20260919)


def grid_ripple(polys, step=0.05):
    """RMS normal wobble at 0.6-1.6 px wavelengths (FFT of the deviation from a 1 px
    arc-length smoothing, per closed loop)."""
    tot = 0.0; n_all = 0
    for p in polys:
        q = T.resample_closed(p, step)
        n = len(q)
        if n < 64:
            continue
        r = int(3 * 1.0 / step)
        k = np.exp(-0.5 * (np.arange(-r, r + 1) * step / 1.0) ** 2); k /= k.sum()
        ext = np.vstack([q[-r:], q, q[:r]])
        sm = np.stack([np.convolve(ext[:, 0], k, "valid"), np.convolve(ext[:, 1], k, "valid")], 1)
        tg = T._tangents(sm, True)
        d = ((q - sm) * np.stack([tg[:, 1], -tg[:, 0]], 1)).sum(1)
        S = np.fft.rfft(d)
        freq = np.fft.rfftfreq(n, step)          # cycles per px
        band = (freq >= 1 / 1.6) & (freq <= 1 / 0.6)
        tot += float((np.abs(S[band]) ** 2).sum()) * 2 / n ** 2 * n
        n_all += n
    return float(np.sqrt(tot / max(n_all, 1)))


def render4(polys, win):
    x0, y0, x1, y1 = win
    return T.fill_polys([(p - [x0, y0]) * F4 for p in polys], (y1 - y0) * F4, (x1 - x0) * F4, ss=8).astype(np.float64)


def cpts(f):
    pts = [T.resample_closed(l + 0.5, 0.1) for l in T.marching_squares(f, 0.5) if len(l) >= 3]
    return np.vstack(pts) if pts else np.zeros((0, 2))


CANDS = [(0.5, 1e-3), (1.0, 1e-3), (1.0, 0.1), (1.5, 1e-3), (1.5, 0.1), (2.0, 0.1)]
out = {"noise_sd": NOISE, "truth": "knot 2.5 px, smooth 0.1, refined, traced from the source", "results": {}}
for g in groups:
    layer = "red" if g in ("ring", "seal_big", "small_seal") else "black"
    region = regions[(g, layer)]
    tc, _ = PT.trace_contour(L, layer, region, knot=2.5, smooth=0.1)
    truth = [c.sample(0.02) for c in tc]
    box = T.fill_polys(truth, H, W, ss=16).astype(np.float64)
    obs = np.round(np.clip(T.gauss_blur(box, T.SOURCE_PSF_SIGMA_PX) * DENS + rng.normal(0, NOISE, box.shape), 0, 1) * 255) / 255
    reg = T.dilate(box > 0.02, 3)
    win = PT._window(reg, 3, (H, W))
    t4 = render4(truth, win)
    ct = cpts(t4)
    fake = types.SimpleNamespace(density={"k": np.full((H, W), DENS)})
    res = {"truth_ripple_px": round(grid_ripple(truth), 5)}
    for knot, sm in CANDS:
        t0 = time.time()
        cur, info = PT.trace_contour(fake, "k", reg, field=obs, knot=knot, smooth=sm)
        pp = [c.sample(0.02) for c in cur]
        p4 = render4(pp, win)
        tb = t4 > 0.5; pb = p4 > 0.5
        iou = float((tb & pb).sum() / max(1, (tb | pb).sum()))
        cp = cpts(p4)
        d = np.concatenate([PT._nn(ct, cp), PT._nn(cp, ct)]) / F4
        key = "knot%.1f_s%g" % (knot, sm)
        res[key] = {"iou_4x": round(iou, 4), "edge_mean_px": round(float(d.mean()), 4),
                    "edge_p95_px": round(float(np.percentile(d, 95)), 4),
                    "ripple_px": round(grid_ripple(pp), 5), "secs": round(time.time() - t0, 1)}
        print("%-7s %-14s IoU4 %.4f edge %.4f/%.4f ripple %.5f (truth %.5f)" % (
            g, key, iou, d.mean(), np.percentile(d, 95), res[key]["ripple_px"], res["truth_ripple_px"]))
    out["results"][g] = res
# the real source's own half-level contour, for scale
json.dump(out, open(os.path.join(HERE, "pbt_bench_knot.json"), "w"), indent=1)
