"""Tracer choice by measurement: a reconstruction benchmark with KNOWN answers, scored at 4x.

Ground truth = crisp shapes with the reference's own character (the traced emblem, a column,
a stretch of the ring, the centre glyph, and the left rule as a stroke).  Each is photographed
the way the reference was: exact pixel-box coverage on the 3.917 px/mm grid, the measured
point spread (Gaussian 0.4 px), the measured ink density, the measured paper noise, 8-bit
quantisation.  Every tracer variant reconstructs the shapes from that observation alone and
is scored against the truth on a grid FOUR times finer (15.7 px/mm, above the texture's
12.9): IoU, symmetric edge distance, and tip error.

usage: python pbt_bench_synth.py [--potrace-dir DIR]   (writes pbt_bench_synth.json)
"""
import os, sys, json, time, argparse, types
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_trace as PT

ap = argparse.ArgumentParser()
ap.add_argument("--traced", default=os.path.join(HERE, "pbt_traced_r2.json"))
ap.add_argument("--dump-obs", default="")          # write observations for the potrace run
ap.add_argument("--potrace", default="")           # npz of potrace loops to score
ap.add_argument("--out", default=os.path.join(HERE, "pbt_bench_synth.json"))
args = ap.parse_args()

data = json.load(open(args.traced, encoding="utf-8"))
L = PT.load_layers()
fit = L.fit
H, W = L.black.shape

# ---- measured photography --------------------------------------------------------------
paper = (L.black < 0.5) & (L.red < 0.5) & L.inside
paper = T.erode(paper, 4) & (L.xm > 8) & (L.xm < 62) & (L.ym > 10) & (L.ym < 150)
NOISE = float(np.std(L.black[paper]))
DENS = float(np.median(L.density["black"][T.erode(L.black > 0.5, 2)]))
print("paper alpha noise sd %.4f   ink density %.3f" % (NOISE, DENS))


def mm_curves_to_px(entry):
    out = []
    for cj in entry.get("curves_mm", []):
        pieces = []
        for p in cj["pieces"]:
            p = np.asarray(p, np.float64)
            x, y = fit.mm_to_px(p[:, 0], p[:, 1])
            pieces.append(np.stack([x, y], 1))
        out.append(T.Curve(pieces, bool(cj["periodic"])))
    return out


def group(name, layer):
    return next(g for g in data["groups"] if g["group"] == name and g["layer"] == layer)


cases = {}
cases["emblem"] = [c.sample(0.02) for c in mm_curves_to_px(group("emblem", "black"))]
cases["col_TR"] = [c.sample(0.02) for c in mm_curves_to_px(group("col_TR", "black"))]
cases["centre"] = [c.sample(0.02) for c in mm_curves_to_px(group("centre", "black"))]
cases["ring"] = [c.sample(0.02) for c in mm_curves_to_px(group("ring", "red"))]
fr = group("frame", "red")
stk = [s for s in fr["strokes_mm"] if s["side"] == "L"][0]
c = np.asarray(stk["centre_mm"]); w = np.asarray(stk["width_mm"])
x, y = fit.mm_to_px(c[:, 0], c[:, 1])
cases["rule_L"] = PT.stroke_polys(np.stack([x, y], 1), w * fit.ppmm, PT.RULE_GAP_WIDTH_PX)

rng = np.random.default_rng(20260919)
F4 = 4


def photograph(polys):
    box = T.fill_polys(polys, H, W, ss=16).astype(np.float64)
    ob = T.gauss_blur(box, T.SOURCE_PSF_SIGMA_PX) * DENS
    ob = ob + rng.normal(0.0, NOISE, ob.shape)
    ob = np.round(np.clip(ob, 0, 1) * 255) / 255
    return ob


def fine_truth(polys, win):
    x0, y0, x1, y1 = win
    return T.fill_polys([(p - [x0, y0]) * F4 for p in polys], (y1 - y0) * F4, (x1 - x0) * F4, ss=8).astype(np.float64)


def cpts(f, step=0.1):
    pts = []
    for l in T.marching_squares(f, 0.5):
        if len(l) >= 3:
            pts.append(T.resample_closed(l + 0.5, step))
    return np.vstack(pts) if pts else np.zeros((0, 2))


def tips(polys, thr_deg=100.0):
    """Sharp convex points of the truth (turning > thr over +-0.6 px): tapered tips."""
    out = []
    for p in polys:
        q = T.resample_closed(p, 0.05)
        idx = T.find_corners(q, 0.05, 0.6, thr_deg)
        out += [q[i] for i in idx]
    return np.array(out) if out else np.zeros((0, 2))


def score4(truth4, pred4, tip_pts, pred_polys, win):
    tb = truth4 > 0.5; pb = pred4 > 0.5
    iou = float((tb & pb).sum() / max(1, (tb | pb).sum()))
    ct = cpts(truth4); cp = cpts(pred4)
    d = np.concatenate([PT._nn(ct, cp), PT._nn(cp, ct)])
    d = d[np.isfinite(d)] / F4                       # source px
    res = {"iou_4x": round(iou, 4), "edge_mean_px": round(float(d.mean()), 4),
           "edge_p95_px": round(float(np.percentile(d, 95)), 4),
           "edge_max_px": round(float(d.max()), 4),
           "edge_mean_mm": round(float(d.mean()) / fit.ppmm, 4),
           "edge_p95_mm": round(float(np.percentile(d, 95)) / fit.ppmm, 4)}
    if len(tip_pts) and pred_polys:
        pp = np.vstack([T.resample_closed(p, 0.05) for p in pred_polys if len(p) >= 3])
        td = PT._nn(tip_pts, pp)
        res["tip_err_mean_px"] = round(float(td.mean()), 4)
        res["tip_err_max_px"] = round(float(td.max()), 4)
        res["tips"] = int(len(tip_pts))
    return res


VARIANTS = {
    "A_linear_x1_polygon": dict(factor=1, kind="linear", spline=False, refine=False),
    "B_bspline_x8_polygon": dict(factor=8, kind="bspline", spline=False, refine=False),
    "C_bspline_x8_spline": dict(factor=8, kind="bspline", spline=True, refine=False),
    "D_catmull_x8_spline_refine": dict(factor=8, kind="catmull", spline=True, refine=True),
    "E_bspline_x8_spline_refine": dict(factor=8, kind="bspline", spline=True, refine=True),
    "F_r1_config_knot0.5_onepass": dict(factor=8, kind="bspline", spline=True, refine=True,
                                        extra=dict(knot=0.5, smooth=1e-3, corner_arm=0.6,
                                                   corner_deg=60.0, two_pass=False)),
}

fake = types.SimpleNamespace(density={"k": np.full((H, W), DENS)})
results = {}
obs_dump = {}
for cname, polys in cases.items():
    obs = photograph(polys)
    cov = T.fill_polys(polys, H, W, ss=4) > 0
    region = T.dilate(cov, 3)
    win = PT._window(region, 3, (H, W))
    truth4 = fine_truth(polys, win)
    tp = tips(polys)
    obs_dump[cname] = {"obs": obs, "region": region, "win": np.array(win)}
    results[cname] = {}
    for vname, v in VARIANTS.items():
        t0 = time.time()
        curves, info = PT.trace_contour(fake, "k", region, refine=v["refine"], factor=v["factor"],
                                        kind=v["kind"], spline=v["spline"], field=obs, **v.get("extra", {}))
        polys_p = [c.sample(0.05) if v["spline"] else c.pieces[0] for c in curves]
        x0, y0, x1, y1 = win
        pred4 = T.fill_polys([(p - [x0, y0]) * F4 for p in polys_p], (y1 - y0) * F4, (x1 - x0) * F4, ss=8).astype(np.float64)
        sc = score4(truth4, pred4, tp, polys_p, win)
        sc["secs"] = round(time.time() - t0, 2)
        results[cname][vname] = sc
        print("%-7s %-28s IoU4 %.4f  edge %.3f/%.3f px (%.4f mm)  tip %s" % (
            cname, vname, sc["iou_4x"], sc["edge_mean_px"], sc["edge_p95_px"], sc["edge_mean_mm"],
            sc.get("tip_err_mean_px")))
    if cname == "rule_L":
        # the stroke tracer on the same observation
        t0 = time.time()
        Ls = types.SimpleNamespace(fit=fit, density={"red": np.full((H, W), DENS)},
                                   black=np.zeros((H, W)), red=obs, red_behind=obs)
        r = PT.trace_rule(Ls, "red", "L", region)
        polys_p = PT.stroke_polys(r["centre_px"], r["width_px"], PT.RULE_GAP_WIDTH_PX)
        x0, y0, x1, y1 = win
        pred4 = T.fill_polys([(p - [x0, y0]) * F4 for p in polys_p], (y1 - y0) * F4, (x1 - x0) * F4, ss=8).astype(np.float64)
        sc = score4(truth4, pred4, tp, polys_p, win)
        # does the rule stay unbroken where the truth is unbroken?
        sc["runs_truth"] = len(polys); sc["runs_pred"] = len(polys_p)
        sc["secs"] = round(time.time() - t0, 2)
        results[cname]["S_stroke_integral"] = sc
        print("%-7s %-28s IoU4 %.4f  edge %.3f/%.3f px  runs %d vs truth %d" % (
            cname, "S_stroke_integral", sc["iou_4x"], sc["edge_mean_px"], sc["edge_p95_px"], len(polys_p), len(polys)))
        for vname in ("C_bspline_x8_spline", "E_bspline_x8_spline_refine", "F_r1_config_knot0.5_onepass"):
            v = VARIANTS[vname]
            curves, info = PT.trace_contour(fake, "k", region, refine=v["refine"], field=obs, **v.get("extra", {}))
            results[cname][vname]["runs_pred"] = len(curves)
        results[cname]["runs_truth"] = len(polys)

if args.potrace:
    z = np.load(args.potrace, allow_pickle=True)
    for cname in cases:
        key = "loops_" + cname
        if key not in z:
            continue
        polys_p = list(z[key])
        # potrace's output sits in the image empty's frame; give it its BEST alignment to the
        # truth (uniform scale + translation, ICP on the contours) so it is judged on shape
        tq = np.vstack([T.resample_closed(p, 0.1) for p in cases[cname]])
        cen = tq.mean(0)
        for _ in range(8):
            pp = np.vstack([T.resample_closed(p, 0.1) for p in polys_p if len(p) >= 3])
            # nearest truth point for each pred point
            idx = np.empty(len(pp), int)
            for i0 in range(0, len(pp), 2000):
                d = (pp[i0:i0+2000, None, 0] - tq[None, :, 0]) ** 2 + (pp[i0:i0+2000, None, 1] - tq[None, :, 1]) ** 2
                idx[i0:i0+2000] = d.argmin(1)
            Q = tq[idx]; P = pp - cen
            A = np.zeros((len(P) * 2, 3)); A[0::2, 0] = P[:, 0]; A[1::2, 0] = P[:, 1]; A[0::2, 1] = 1; A[1::2, 2] = 1
            bq = (Q - cen).ravel()
            (sc_, tx, ty), *_ = np.linalg.lstsq(A, bq, rcond=None)
            polys_p = [(p - cen) * sc_ + cen + [tx, ty] for p in polys_p]
        print("potrace calibration", cname, round(float(sc_), 5), round(float(tx), 4), round(float(ty), 4))
        win = tuple(int(v) for v in obs_dump[cname]["win"])
        x0, y0, x1, y1 = win
        truth4 = fine_truth(cases[cname], win)
        pred4 = T.fill_polys([(p - [x0, y0]) * F4 for p in polys_p], (y1 - y0) * F4, (x1 - x0) * F4, ss=8).astype(np.float64)
        sc = score4(truth4, pred4, tips(cases[cname]), polys_p, win)
        results[cname]["P_potrace_blender_x8"] = sc
        print("%-7s %-28s IoU4 %.4f  edge %.3f/%.3f px  tip %s" % (cname, "P_potrace_blender_x8", sc["iou_4x"], sc["edge_mean_px"], sc["edge_p95_px"], sc.get("tip_err_mean_px")))

if args.dump_obs:
    np.savez(args.dump_obs, **{k + "__" + kk: vv for k, d in obs_dump.items() for kk, vv in d.items()})
json.dump({"noise_sd": NOISE, "density": DENS, "grid": "4x source (15.67 px/mm)", "results": results},
          open(args.out, "w", encoding="utf-8"), indent=1)
print("wrote", args.out)
