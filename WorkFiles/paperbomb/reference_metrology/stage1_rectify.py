# -*- coding: utf-8 -*-
"""Stage 1: find the TAG quad in each reference, measure rotation + keystone,
build the rectification homography, and cache the rectified tag as .npy in the
scratchpad (NOT in the project) for later stages.

Everything here emits numbers. No reference artwork is written into the project.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pngread as P  # noqa: E402

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
SCRATCH = os.environ.get("PB_SCRATCH", HERE + "/debug/_cache")
os.makedirs(SCRATCH, exist_ok=True)

REFS = {
    "V1": ROOT + "/References/PaperBomb/paperbomb_guide.png",
    "V2": ROOT + "/References/PaperBomb/paperbomb_guide_v2_real_glyphs.png",
}

# rectified resolution: keep V1 near native, V2 upsampled to the same grid so the
# two are directly comparable in tag fractions.
RECT_W, RECT_H = 840, 1872  # 70 x 156 mm * 12 px/mm


def tagness(f):
    """Warmth score: high on cream paper AND on red ink, ~0 on the white/grey
    background and its neutral drop shadow. Black ink also scores ~0 but never
    reaches the paper edge, so the outer boundary scan is unaffected."""
    return f[..., 0] - f[..., 2]


def half_max_threshold(T):
    """Background level from the image corners, paper level from a robust
    interior percentile; threshold at the half-max between them."""
    h, w = T.shape
    k = max(4, int(0.02 * min(h, w)))
    corners = np.concatenate([
        T[:k, :k].ravel(), T[:k, -k:].ravel(),
        T[-k:, :k].ravel(), T[-k:, -k:].ravel()])
    bg = float(np.median(corners))
    inner = T[int(0.10 * h):int(0.90 * h), int(0.15 * w):int(0.85 * w)]
    paper = float(np.percentile(inner, 60))
    return bg, paper, bg + 0.5 * (paper - bg)


def subpix_cross(prof, thr, forward=True):
    """First index where prof crosses thr, linearly interpolated. None if never."""
    n = len(prof)
    rng = range(1, n) if forward else range(n - 2, -1, -1)
    for i in rng:
        a = prof[i - 1] if forward else prof[i + 1]
        bv = prof[i]
        if (a < thr) and (bv >= thr):
            t = (thr - a) / max(bv - a, 1e-9)
            return (i - 1) + t if forward else (i + 1) - t
    return None


def fit_line_robust(t, v, iters=4):
    """v = m*t + c, trimmed least squares. Returns m, c, rms, n_used."""
    t = np.asarray(t, float)
    v = np.asarray(v, float)
    keep = np.ones(len(t), bool)
    m = c = 0.0
    for _ in range(iters):
        if keep.sum() < 8:
            break
        A = np.vstack([t[keep], np.ones(keep.sum())]).T
        sol, *_ = np.linalg.lstsq(A, v[keep], rcond=None)
        m, c = float(sol[0]), float(sol[1])
        res = np.abs(v - (m * t + c))
        s = np.median(res[keep]) * 2.5 + 1e-6
        keep = res < max(s, 0.5)
    res = v[keep] - (m * t[keep] + c)
    return m, c, float(np.sqrt(np.mean(res ** 2))), int(keep.sum())


def intersect(m1, c1, vertical1, m2, c2, vertical2):
    """Lines given as x = m*y + c (vertical=True) or y = m*x + c (vertical=False)."""
    if vertical1 and not vertical2:
        # x = m1*y + c1 ; y = m2*x + c2
        y = (m2 * c1 + c2) / (1 - m2 * m1)
        x = m1 * y + c1
        return x, y
    if vertical2 and not vertical1:
        return intersect(m2, c2, True, m1, c1, False)
    raise ValueError("need one vertical-ish and one horizontal-ish line")


def homography(src, dst):
    """src/dst: 4x2 arrays. Returns 3x3 H mapping src->dst."""
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    A = np.asarray(A, float)
    _, _, Vt = np.linalg.svd(A)
    H = Vt[-1].reshape(3, 3)
    return H / H[2, 2]


def warp(f, H_inv, w, h):
    """Sample source f at the positions that map to each rectified pixel centre.
    H_inv maps rectified -> source. Bilinear."""
    yy, xx = np.mgrid[0:h, 0:w]
    u = (xx + 0.5).ravel()
    v = (yy + 0.5).ravel()
    ones = np.ones_like(u)
    pts = np.vstack([u, v, ones])
    sp = H_inv @ pts
    sx = sp[0] / sp[2]
    sy = sp[1] / sp[2]
    H0, W0 = f.shape[:2]
    sx = np.clip(sx - 0.5, 0, W0 - 1.001)
    sy = np.clip(sy - 0.5, 0, H0 - 1.001)
    x0 = np.floor(sx).astype(np.int32)
    y0 = np.floor(sy).astype(np.int32)
    fx = (sx - x0)[:, None]
    fy = (sy - y0)[:, None]
    p00 = f[y0, x0]
    p10 = f[y0, x0 + 1]
    p01 = f[y0 + 1, x0]
    p11 = f[y0 + 1, x0 + 1]
    top = p00 * (1 - fx) + p10 * fx
    bot = p01 * (1 - fx) + p11 * fx
    return (top * (1 - fy) + bot * fy).reshape(h, w, f.shape[2])


report = {}
for key, path in REFS.items():
    arr, info = P.read_png(path)
    f = P.to_float(arr, info)[..., :3]
    H0, W0 = f.shape[:2]
    T = tagness(f)
    bg_lvl, paper_lvl, thr = half_max_threshold(T)
    print("%s  bg_warm=%.4f paper_warm=%.4f thr=%.4f" % (key, bg_lvl, paper_lvl, thr))

    # ---- left / right edges: scan rows, restricted to the non-chamfered band
    ys = np.arange(H0)
    lefts, rights, yy_keep = [], [], []
    for y in range(H0):
        xl = subpix_cross(T[y], thr, True)
        xr = subpix_cross(T[y], thr, False)
        if xl is None or xr is None or xr - xl < W0 * 0.2:
            lefts.append(np.nan); rights.append(np.nan)
        else:
            lefts.append(xl); rights.append(xr)
    lefts = np.array(lefts); rights = np.array(rights)
    valid = ~np.isnan(lefts)
    y_first, y_last = int(np.argmax(valid)), int(H0 - 1 - np.argmax(valid[::-1]))
    span = y_last - y_first
    band = slice(y_first + int(0.18 * span), y_first + int(0.82 * span))
    yb = ys[band]
    ml, cl, rl, nl = fit_line_robust(yb, lefts[band])   # x = ml*y + cl
    mr, cr, rr, nr = fit_line_robust(yb, rights[band])

    # ---- top / bottom edges: scan columns
    tops, bots = [], []
    for x in range(W0):
        col = T[:, x]
        yt = subpix_cross(col, thr, True)
        yb2 = subpix_cross(col, thr, False)
        if yt is None or yb2 is None or yb2 - yt < H0 * 0.2:
            tops.append(np.nan); bots.append(np.nan)
        else:
            tops.append(yt); bots.append(yb2)
    tops = np.array(tops); bots = np.array(bots)
    validx = ~np.isnan(tops)
    x_first, x_last = int(np.argmax(validx)), int(W0 - 1 - np.argmax(validx[::-1]))
    spanx = x_last - x_first
    bandx = slice(x_first + int(0.22 * spanx), x_first + int(0.78 * spanx))
    xb = np.arange(W0)[bandx]
    mt, ct, rt, nt = fit_line_robust(xb, tops[bandx])   # y = mt*x + ct
    mb, cb, rb, nb = fit_line_robust(xb, bots[bandx])

    # ---- corners of the (un-chamfered) paper rectangle
    TL = intersect(ml, cl, True, mt, ct, False)
    TR = intersect(mr, cr, True, mt, ct, False)
    BR = intersect(mr, cr, True, mb, cb, False)
    BL = intersect(ml, cl, True, mb, cb, False)
    quad = np.array([TL, TR, BR, BL], float)

    # ---- rotation + keystone diagnostics
    ang_l = np.degrees(np.arctan2(ml, 1.0))    # deg of left edge off vertical (+ = leans right going down)
    ang_r = np.degrees(np.arctan2(mr, 1.0))
    ang_t = np.degrees(np.arctan2(mt, 1.0))    # deg of top edge off horizontal
    ang_b = np.degrees(np.arctan2(mb, 1.0))
    w_top = float(np.hypot(*(quad[1] - quad[0])))
    w_bot = float(np.hypot(*(quad[2] - quad[3])))
    h_left = float(np.hypot(*(quad[3] - quad[0])))
    h_right = float(np.hypot(*(quad[2] - quad[1])))

    # ---- chamfer measurement (how far the corner cut runs along each edge)
    def chamfer_run(prof_valid, from_start):
        """How many rows/cols from the tip until the edge becomes straight."""
        idxs = np.where(prof_valid)[0]
        return int(idxs[0]) if from_start else int(idxs[-1])

    # chamfer: distance from corner along the left edge where measured left x
    # departs from the fitted line by < 1 px
    dev_l = lefts - (ml * ys + cl)
    ok_l = np.abs(dev_l) < 1.5
    top_ch_rows = 0
    for y in range(y_first, y_last):
        if ok_l[y]:
            top_ch_rows = y - y_first
            break
    bot_ch_rows = 0
    for y in range(y_last, y_first, -1):
        if ok_l[y]:
            bot_ch_rows = y_last - y
            break

    rec = {
        "source_px": [W0, H0],
        "warmth_background_level": round(bg_lvl, 4),
        "warmth_paper_level": round(paper_lvl, 4),
        "tagness_threshold": round(thr, 4),
        "edge_fits": {
            "left_x_eq_m_y_plus_c": [round(ml, 6), round(cl, 3), round(rl, 3), nl],
            "right_x_eq_m_y_plus_c": [round(mr, 6), round(cr, 3), round(rr, 3), nr],
            "top_y_eq_m_x_plus_c": [round(mt, 6), round(ct, 3), round(rt, 3), nt],
            "bottom_y_eq_m_x_plus_c": [round(mb, 6), round(cb, 3), round(rb, 3), nb],
        },
        "edge_angles_deg": {
            "left_off_vertical": round(ang_l, 4),
            "right_off_vertical": round(ang_r, 4),
            "top_off_horizontal": round(ang_t, 4),
            "bottom_off_horizontal": round(ang_b, 4),
        },
        "corners_px": {"TL": [round(v, 2) for v in TL], "TR": [round(v, 2) for v in TR],
                       "BR": [round(v, 2) for v in BR], "BL": [round(v, 2) for v in BL]},
        "widths_px": {"top": round(w_top, 2), "bottom": round(w_bot, 2),
                      "left_height": round(h_left, 2), "right_height": round(h_right, 2)},
        "keystone": {
            "width_top_over_bottom": round(w_top / w_bot, 5),
            "height_left_over_right": round(h_left / h_right, 5),
            "vertical_convergence_deg": round(ang_r - ang_l, 4),
            "horizontal_convergence_deg": round(ang_b - ang_t, 4),
        },
        "mean_rotation_deg": round(0.5 * (ang_l + ang_r) - 0.5 * (ang_t + ang_b) * 0, 4),
        "aspect_h_over_w": round(0.5 * (h_left + h_right) / (0.5 * (w_top + w_bot)), 5),
        "chamfer_left_edge_rows": {"top": top_ch_rows, "bottom": bot_ch_rows},
    }

    dst = np.array([[0, 0], [RECT_W, 0], [RECT_W, RECT_H], [0, RECT_H]], float)
    Hm = homography(quad, dst)
    Hinv = np.linalg.inv(Hm)
    rect = warp(f, Hinv, RECT_W, RECT_H)
    np.save(os.path.join(SCRATCH, "rect_%s.npy" % key), rect.astype(np.float32))
    rec["homography_src_to_rect"] = [[round(float(v), 8) for v in row] for row in Hm]
    rec["rect_px"] = [RECT_W, RECT_H]
    rec["rect_px_per_mm"] = round(RECT_W / 70.0, 4)
    rec["source_px_per_tag_width"] = round(0.5 * (w_top + w_bot), 2)
    rec["source_px_per_mm"] = round(0.5 * (w_top + w_bot) / 70.0, 4)
    report[key] = rec
    print(key, "quad", rec["corners_px"], "angles", rec["edge_angles_deg"])
    print("   aspect", rec["aspect_h_over_w"], "keystone", rec["keystone"])

with open(HERE + "/debug/stage1_rectify.json", "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1, ensure_ascii=False)
print("wrote stage1_rectify.json; cache in", SCRATCH)
