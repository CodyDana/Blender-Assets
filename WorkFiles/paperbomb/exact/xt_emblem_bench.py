# -*- coding: utf-8 -*-
"""Benchmark tracer variants on the flame emblem against V2 at V2's own grid.

Run with Blender's bundled python (numpy):
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" xt_emblem_bench.py
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "Scripts", "props"))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
from props_lib import trace as T  # noqa: E402
import xt_io  # noqa: E402

WIN = (98, 82, 208, 184)       # x0, y0, x1, y1 in V2 px (the emblem and nothing else black)


def component_mask(ak, win, thr=0.5, min_px=6):
    x0, y0, x1, y1 = win
    sub = ak[y0:y1, x0:x1] > thr
    lab, n = T.label(sub)
    keep = np.zeros_like(sub)
    for i in range(1, n + 1):
        m = lab == i
        if m.sum() >= min_px:
            keep |= m
    return keep


def contour_points(field, iso=0.5, step=0.1):
    """Contour a field at 1x (bilinear marching squares, nodes at pixel centres)."""
    loops = T.marching_squares(field, iso)
    pts = []
    for l in loops:
        if len(l) < 3:
            continue
        q = T.resample_closed(l + 0.5, step)
        pts.append(q)
    return np.vstack(pts) if pts else np.zeros((0, 2))


def nn_dist(a, b):
    out = np.empty(len(a))
    for i in range(0, len(a), 2000):
        d = np.hypot(a[i:i + 2000, None, 0] - b[None, :, 0], a[i:i + 2000, None, 1] - b[None, :, 1])
        out[i:i + 2000] = d.min(1)
    return out


def score(pred, obs, weight_mask):
    """pred/obs: coverage fields on the same V2 window; weight_mask: bool region scored."""
    p = np.where(weight_mask, pred, 0.0)
    o = np.where(weight_mask, obs, 0.0)
    pb = p > 0.5; ob = o > 0.5
    iou = (pb & ob).sum() / max(1, (pb | ob).sum())
    soft = np.minimum(p, o).sum() / max(1e-9, np.maximum(p, o).sum())
    mae = np.abs(p - o)[weight_mask].mean()
    cp = contour_points(p); co = contour_points(o)
    d1 = nn_dist(co, cp); d2 = nn_dist(cp, co)
    d = np.concatenate([d1, d2])
    return {"iou": round(float(iou), 4), "soft_iou": round(float(soft), 4),
            "mae": round(float(mae), 4),
            "edge_mean_px": round(float(d.mean()), 4), "edge_p95_px": round(float(np.percentile(d, 95)), 4),
            "edge_max_px": round(float(d.max()), 4),
            "edge_mean_mm": round(float(d.mean()) / 3.917, 4)}


def trace_variant(ak, keep, kind, factor, knot, iso=0.5, corner_deg=60.0, spline=True):
    x0, y0, x1, y1 = WIN
    field = np.zeros_like(ak)
    region = np.zeros_like(ak, bool)
    region[y0:y1, x0:x1] = T.dilate(keep, 2)
    field = np.where(region, ak, 0.0)
    if factor == 1 and kind == "linear":
        f = field[y0:y1, x0:x1]
        loops = T.marching_squares(f, iso)
        loops = [l + np.array([x0 + 0.5, y0 + 0.5]) for l in loops]
    else:
        fine, gx0, gy0, st = T.upsample_window(field, x0, y0, x1, y1, factor, kind)
        loops = T.marching_squares(fine, iso)
        loops = [np.stack([gx0 + l[:, 0] * st, gy0 + l[:, 1] * st], 1) for l in loops]
    loops = [l for l in loops if abs(T.signed_area(l)) > 0.3]
    curves = []
    stats = []
    for l in loops:
        if spline:
            c, s = T.fit_loop(l, knot, corner_deg=corner_deg)
            curves.append(c)
            stats.append(s)
        else:
            curves.append(T.Curve([l], True))
    return loops, curves, stats


def render(curves, H, W, scale=1, spline=True, step=0.02):
    polys = []
    for c in curves:
        if spline:
            p = c.sample(step)
        else:
            p = c.pieces[0]
        polys.append(p * scale)
    return T.fill_polys(polys, H * scale, W * scale, ss=16)


def main():
    src = T.read_source()
    fit = T.fit_card(src)
    ak, behind, unm = T.ink_layers(src, fit)
    x0, y0, x1, y1 = WIN
    keep = component_mask(ak, WIN)
    scored = np.zeros_like(ak, bool)
    scored[y0:y1, x0:x1] = T.dilate(keep, 3)
    obs = np.where(scored, ak, 0.0)
    H, W = ak.shape
    results = {}
    variants = [("linear", 1, None, False)]
    for kind in ("linear", "catmull", "bspline", "lanczos3"):
        variants.append((kind, 8, None, False))
    for kind in ("catmull", "bspline"):
        for knot in (0.35, 0.5, 0.75, 1.0):
            variants.append((kind, 8, knot, True))
    best = None
    for kind, factor, knot, spline in variants:
        t = time.time()
        loops, curves, stats = trace_variant(ak, keep, kind, factor, knot or 0.5, spline=spline)
        pred = render(curves, H, W, spline=spline)
        sc = score(pred[y0:y1, x0:x1], obs[y0:y1, x0:x1], scored[y0:y1, x0:x1])
        sc["loops"] = len(loops)
        sc["secs"] = round(time.time() - t, 2)
        if spline:
            sc["ctrl_pts"] = int(sum(sum(len(p) for p in c.pieces) for c in curves))
            sc["corners"] = int(sum(s["corners"] for s in stats))
            sc["fit_rms_px"] = round(float(np.mean([s["rms_px"] for s in stats])), 4)
        name = "%s_x%d%s" % (kind, factor, ("_knot%.2f" % knot) if spline else "_poly")
        results[name] = sc
        print(name, json.dumps(sc))
    with open(os.path.join(HERE, "emblem_bench.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)


if __name__ == "__main__":
    main()
