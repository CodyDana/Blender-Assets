"""Emblem: tracer regularisation grid on the REAL reference.
For each (knot, smooth, corner arm, corner deg): re-render score against the source, sub-pixel
ripple (RMS normal deviation of the traced edge from its own 1.5 px arc-length smoothing,
away from sharp points), sharp-tip count.  The source cannot hold detail finer than ~1 px,
so ripple at that scale is fitting noise.
usage: python pbt_emblem_grid.py [group] [layer]"""
import os, sys, json, time, itertools
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_trace as PT

grp = sys.argv[1] if len(sys.argv) > 1 else "emblem"
layer = sys.argv[2] if len(sys.argv) > 2 else "black"
L = PT.load_layers()
H, W = L.black.shape
masks = PT.group_masks(L)
regions = PT.group_regions(L, masks)
region = regions[(grp, layer)]
obs = np.where(region, PT.layer_field(L, layer, True), 0.0)


def ripple(polys, step=0.05):
    """Band-passed edge wobble: RMS normal distance between the edge smoothed at 0.25 px and
    at 0.8 px (arc length), i.e. wiggles of ~0.7-3 px wavelength, away from sharp points."""
    devs = []
    sharp = 0
    def gs(a, sig):
        r = int(3 * sig / step)
        k = np.exp(-0.5 * (np.arange(-r, r + 1) * step / sig) ** 2); k /= k.sum()
        ext = np.concatenate([a[-r:], a, a[:r]])
        return np.convolve(ext, k, "valid")
    for p in polys:
        q = T.resample_closed(p, step)
        n = len(q)
        if n < 80:
            continue
        cs = T.find_corners(q, step, 1.5, 100.0)
        sharp += len(cs)
        a1 = np.stack([gs(q[:, 0], 0.25), gs(q[:, 1], 0.25)], 1)
        a2 = np.stack([gs(q[:, 0], 0.8), gs(q[:, 1], 0.8)], 1)
        tg = T._tangents(a2, True)
        nrm = np.stack([tg[:, 1], -tg[:, 0]], 1)
        d = ((a1 - a2) * nrm).sum(1)
        keep = np.ones(n, bool)
        w = int(round(2.0 / step))
        for c in cs:
            keep[(np.arange(c - w, c + w + 1)) % n] = False
        devs.append(d[keep])
    d = np.concatenate(devs) if devs else np.zeros(1)
    return float(np.sqrt((d ** 2).mean())), sharp


# the raw data: half-level contour of the 8x field, no fit
field = PT.layer_field(L, layer, True)
f = np.where(region, field / L.density[layer], 0.0)
win = PT._window(region, 3, f.shape)
fine, gx0, gy0, st = T.upsample_window(f, *win, 8, "bspline")
raw = [np.stack([gx0 + l[:, 0] * st, gy0 + l[:, 1] * st], 1) for l in T.marching_squares(fine, 0.5)]
raw = [l for l in raw if abs(T.signed_area(l)) > 0.35]
print("raw half-level contour ripple %.4f px, sharp %d" % ripple(raw))

knots = [0.5, 1.0, 1.5, 2.0]
smooths = [1e-3, 1e-1]
arms = [(0.6, 60.0), (1.5, 80.0)]
if len(sys.argv) > 3:
    knots = [float(v) for v in sys.argv[3].split(",")]
res = {}
for knot, sm, (arm, deg) in itertools.product(knots, smooths, arms):
    t0 = time.time()
    curves, info = PT.trace_contour(L, layer, region, refine=True, knot=knot, smooth=sm,
                                    corner_arm=arm, corner_deg=deg)
    polys = [c.sample(0.05) for c in curves]
    box = T.fill_polys(polys, H, W, ss=16).astype(np.float64)
    pred = T.gauss_blur(box, T.SOURCE_PSF_SIGMA_PX) * L.density[layer]
    sc = PT.score_fields(pred, obs, region, L.fit.ppmm)
    rp, sharp = ripple(polys)
    key = "knot%.1f_s%g_arm%.1f_deg%d" % (knot, sm, arm, deg)
    res[key] = dict(sc, ripple_px=round(rp, 4), sharp=sharp, corners=info["corners"],
                    resid=info["refine_residual"][-1], secs=round(time.time() - t0, 1))
    print("%-28s IoU %.4f soft %.4f band %.4f edge %.4f/%.4f  ripple %.4f  sharp %d corners %d  resid %.4f" % (
        key, sc["iou"], sc["soft_iou"], sc["band_mae"], sc["edge_mean_px"], sc["edge_p95_px"], rp, sharp,
        info["corners"], info["refine_residual"][-1]))
json.dump(res, open(os.path.join(HERE, "pbt_grid_%s_%s.json" % (grp, layer)), "w"), indent=1)
