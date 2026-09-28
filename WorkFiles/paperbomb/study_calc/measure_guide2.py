# -*- coding: utf-8 -*-
"""Targeted second pass on the paper-bomb guide PNGs.

Windowed element boxes, per-character splits in the kanji columns, the red
double-border scanline, the broken ring's radius / stroke / angular coverage,
and the paper's edge-darkening and mottle profiles.

blender -b --factory-startup --python measure_guide2.py -- <out.json>
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
import numpy as np

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"
IMAGES = [
    ("v1", os.path.join(REF, "paperbomb_guide.png")),
    ("v2", os.path.join(REF, "paperbomb_guide_v2_real_glyphs.png")),
]

# element windows, fractions of the CARD box: (mask, x0, x1, y0, y1)
WINDOWS = {
    "flame_emblem":   ("black", 0.33, 0.67, 0.05, 0.33),
    "upper_left_col": ("black", 0.02, 0.34, 0.02, 0.37),
    "upper_right_col": ("black", 0.66, 0.98, 0.02, 0.37),
    "centre_glyph":   ("black", 0.08, 0.96, 0.36, 0.70),
    "lower_centre_col": ("black", 0.32, 0.70, 0.68, 0.98),
    "lower_right_col": ("black", 0.66, 0.98, 0.58, 0.86),
    "seal_box_big":   ("red", 0.03, 0.42, 0.70, 0.96),
    "seal_box_small": ("red", 0.74, 0.97, 0.72, 0.95),
    "top_diamond":    ("red", 0.42, 0.58, 0.015, 0.09),
    "bottom_diamond": ("red", 0.42, 0.58, 0.91, 0.995),
}

COLUMNS = ["upper_left_col", "upper_right_col", "lower_centre_col", "lower_right_col"]


def load_raw(path):
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    a = buf.reshape(h, w, 4)[::-1].astype(np.float64)
    bpy.data.images.remove(img)
    return a, w, h


def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def analyse(path):
    a, W, H = load_raw(path)
    rgb = a[:, :, :3]
    R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    luma = 0.2126 * R + 0.7152 * G + 0.0722 * B
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    card = (sat > 0.06) | (luma < 0.70)
    colc = card.sum(axis=0)
    rowc = card.sum(axis=1)
    cx = np.nonzero(colc > 0.05 * H)[0]
    ry = np.nonzero(rowc > 0.05 * W)[0]
    cx0, cx1, cy0, cy1 = int(cx.min()), int(cx.max()), int(ry.min()), int(ry.max())
    CW, CH = cx1 - cx0 + 1, cy1 - cy0 + 1

    red = (R - G > 0.25) & (R > 0.22)
    black = (luma < 0.38) & ~red
    masks = {"red": red, "black": black}

    def win(m, fx0, fx1, fy0, fy1):
        x0 = cx0 + int(fx0 * CW); x1 = cx0 + int(fx1 * CW)
        y0 = cy0 + int(fy0 * CH); y1 = cy0 + int(fy1 * CH)
        return masks[m][y0:y1, x0:x1], x0, y0

    def box(sub, ox, oy):
        ys, xs = np.nonzero(sub)
        if len(xs) < 20:
            return None
        X0, X1 = ox + int(xs.min()), ox + int(xs.max())
        Y0, Y1 = oy + int(ys.min()), oy + int(ys.max())
        return {
            "x0": round((X0 - cx0) / CW, 4), "x1": round((X1 + 1 - cx0) / CW, 4),
            "y0": round((Y0 - cy0) / CH, 4), "y1": round((Y1 + 1 - cy0) / CH, 4),
            "cx": round((X0 + X1 + 1 - 2 * cx0) / (2 * CW), 4),
            "cy": round((Y0 + Y1 + 1 - 2 * cy0) / (2 * CH), 4),
            "w": round((X1 + 1 - X0) / CW, 4), "h": round((Y1 + 1 - Y0) / CH, 4),
            "w_over_cardw": round((X1 + 1 - X0) / CW, 4),
            "h_over_cardw": round((Y1 + 1 - Y0) / CW, 4),
            "ink_frac_of_box": round(float(sub.sum()) / max(1, (X1 + 1 - X0) * (Y1 + 1 - Y0)), 3),
            "px": [X0, Y0, X1, Y1],
        }

    elements = {}
    for name, (m, fx0, fx1, fy0, fy1) in WINDOWS.items():
        sub, ox, oy = win(m, fx0, fx1, fy0, fy1)
        elements[name] = box(sub, ox, oy)

    # ---- per-character split inside each column ---------------------------
    chars = {}
    for name in COLUMNS:
        m, fx0, fx1, fy0, fy1 = WINDOWS[name]
        sub, ox, oy = win(m, fx0, fx1, fy0, fy1)
        prof = sub.sum(axis=1)
        thr = max(1.0, 0.02 * prof.max())
        runs, run = [], None
        for i, v in enumerate(prof):
            if v >= thr:
                run = [i, i] if run is None else [run[0], i]
            else:
                if run is not None and run[1] - run[0] > 0.01 * CH:
                    runs.append(run)
                run = None
        if run is not None and run[1] - run[0] > 0.01 * CH:
            runs.append(run)
        # merge runs separated by less than 1.2% of card height
        merged = []
        for r in runs:
            if merged and r[0] - merged[-1][1] < 0.012 * CH:
                merged[-1][1] = r[1]
            else:
                merged.append(list(r))
        out = []
        for r in merged:
            seg = sub[r[0]:r[1] + 1]
            b = box(seg, ox, oy + r[0])
            if b and b["h"] > 0.02:
                out.append(b)
        # pitch
        cys = [b["cy"] for b in out]
        chars[name] = {
            "n": len(out),
            "boxes": out,
            "pitch_frac_h": [round(cys[i + 1] - cys[i], 4) for i in range(len(cys) - 1)],
        }

    # ---- red border scanlines ---------------------------------------------
    def scan_runs(mask_row, origin, denom):
        runs, run = [], None
        for i, v in enumerate(mask_row):
            if v:
                run = [i, i] if run is None else [run[0], i]
            else:
                if run is not None:
                    runs.append(run)
                run = None
        if run is not None:
            runs.append(run)
        return [[round((origin + r[0]) / denom, 4), round((origin + r[1] + 1) / denom, 4),
                 round((r[1] + 1 - r[0]) / denom, 5)] for r in runs]

    border = {}
    for fy in (0.42, 0.50, 0.58):
        y = cy0 + int(fy * CH)
        row = red[y, cx0:cx0 + int(0.16 * CW)]
        border["left_at_y%.2f" % fy] = scan_runs(row, 0, CW)
        row2 = red[y, cx0 + int(0.84 * CW):cx1 + 1]
        border["right_at_y%.2f" % fy] = [[round(v[0] + 0.84, 4), round(v[1] + 0.84, 4), v[2]]
                                         for v in scan_runs(row2, 0, CW)]
    for fx in (0.35, 0.50, 0.65):
        x = cx0 + int(fx * CW)
        col = red[cy0:cy0 + int(0.12 * CH), x]
        border["top_at_x%.2f" % fx] = scan_runs(col, 0, CH)
        col2 = red[cy1 - int(0.12 * CH):cy1 + 1, x]
        off = (cy1 - int(0.12 * CH) - cy0)
        border["bottom_at_x%.2f" % fx] = scan_runs(col2, off, CH)

    # ---- the broken red ring ----------------------------------------------
    ring_mask = np.zeros_like(red)
    ring_mask[cy0 + int(0.25 * CH):cy0 + int(0.72 * CH),
              cx0 + int(0.12 * CW):cx0 + int(0.92 * CW)] = True
    ring = red & ring_mask
    ys, xs = np.nonzero(ring)
    ring_stats = None
    if len(xs) > 200:
        # robust centre: median of the extreme radii search -> use bbox centre, refine
        cxr, cyr = (xs.min() + xs.max()) / 2.0, (ys.min() + ys.max()) / 2.0
        for _ in range(12):
            rr = np.hypot(xs - cxr, ys - cyr)
            th = np.arctan2(ys - cyr, xs - cxr)
            # push centre so radius is uniform in angle
            bins = np.floor((th + math.pi) / (2 * math.pi) * 36).astype(int) % 36
            means = np.array([rr[bins == b].mean() if (bins == b).any() else np.nan
                              for b in range(36)])
            ang = (np.arange(36) + 0.5) / 36 * 2 * math.pi - math.pi
            ok = ~np.isnan(means)
            dx = np.nansum(np.cos(ang[ok]) * (means[ok] - np.nanmean(means))) / max(1, ok.sum())
            dy = np.nansum(np.sin(ang[ok]) * (means[ok] - np.nanmean(means))) / max(1, ok.sum())
            cxr += dx * 1.5
            cyr += dy * 1.5
        rr = np.hypot(xs - cxr, ys - cyr)
        th = np.arctan2(ys - cyr, xs - cxr)
        bins = np.floor((th + math.pi) / (2 * math.pi) * 180).astype(int) % 180
        present = np.array([(bins == b).sum() for b in range(180)])
        ring_stats = {
            "centre_frac": [round((cxr - cx0) / CW, 4), round((cyr - cy0) / CH, 4)],
            "r_mean_frac_w": round(float(rr.mean()) / CW, 4),
            "r_p10_frac_w": round(float(np.percentile(rr, 10)) / CW, 4),
            "r_p90_frac_w": round(float(np.percentile(rr, 90)) / CW, 4),
            "outer_d_frac_w": round(float(np.percentile(rr, 99)) * 2 / CW, 4),
            "inner_d_frac_w": round(float(np.percentile(rr, 1)) * 2 / CW, 4),
            "stroke_w_frac_w": round(float(np.percentile(rr, 90) - np.percentile(rr, 10)) / CW, 4),
            "angular_bins_2deg_total": 180,
            "angular_bins_empty": int((present < 3).sum()),
            "angular_coverage": round(float((present >= 3).sum()) / 180, 3),
            "gap_runs_deg": None,
        }
        gaps, run = [], None
        for i in range(180):
            if present[i] < 3:
                run = [i, i] if run is None else [run[0], i]
            else:
                if run is not None:
                    gaps.append(run)
                run = None
        if run is not None:
            gaps.append(run)
        ring_stats["gap_runs_deg"] = [[round(g[0] * 2 - 180, 1), round((g[1] + 1) * 2 - 180, 1)]
                                      for g in gaps]

    # ---- paper: edge darkening profile and mottle -------------------------
    paper = card & ~red & ~black
    prof = []
    for k in range(20):
        f0, f1 = k / 200.0, (k + 1) / 200.0   # 0 to 10% in from the edge
        band = np.zeros_like(paper)
        x0, x1 = cx0 + int(f0 * CW), cx0 + int(f1 * CW)
        band[cy0 + int(0.15 * CH):cy0 + int(0.85 * CH), x0:max(x0 + 1, x1)] = True
        sel = luma[band & paper]
        if len(sel) > 30:
            prof.append([round(f0, 4), round(float(np.median(sel)), 4)])
    centre_band = np.zeros_like(paper)
    centre_band[cy0 + int(0.15 * CH):cy0 + int(0.85 * CH),
                cx0 + int(0.40 * CW):cx0 + int(0.60 * CW)] = True
    csel = luma[centre_band & paper]
    edge_prof = {
        "left_edge_luma_by_inset_frac_w": prof,
        "centre_median_luma": round(float(np.median(csel)), 4) if len(csel) else None,
    }
    # mottle: luma std in clean blocks at several block sizes
    blk = luma[cy0 + int(0.28 * CH):cy0 + int(0.42 * CH), cx0 + int(0.07 * CW):cx0 + int(0.20 * CW)]
    mot = {"block_px": list(blk.shape), "std": round(float(blk.std()), 4),
           "p05": round(float(np.percentile(blk, 5)), 4),
           "p50": round(float(np.percentile(blk, 50)), 4),
           "p95": round(float(np.percentile(blk, 95)), 4)}
    for n in (2, 4, 8, 16):
        h2, w2 = blk.shape[0] // n * n, blk.shape[1] // n * n
        if h2 and w2:
            d = blk[:h2, :w2].reshape(h2 // n, n, w2 // n, n).mean(axis=(1, 3))
            mot["std_downsampled_%dx" % n] = round(float(d.std()), 4)

    # ---- colours as linear albedo ----------------------------------------
    def stat(mask):
        sel = rgb[mask]
        if len(sel) < 50:
            return None
        p50 = np.percentile(sel, 50, axis=0)
        p05 = np.percentile(sel, 5, axis=0)
        p95 = np.percentile(sel, 95, axis=0)
        out = {}
        for tag, v in (("p05", p05), ("p50", p50), ("p95", p95)):
            lin = srgb_to_linear(v)
            out["stored_" + tag] = [round(float(x), 4) for x in v]
            out["linear_" + tag] = [round(float(x), 4) for x in lin]
            out["linear_luma_" + tag] = round(float(0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]), 4)
        out["n_px"] = int(len(sel))
        return out

    ci = np.zeros_like(paper)
    ci[cy0 + int(0.15 * CH):cy0 + int(0.85 * CH), cx0 + int(0.15 * CW):cx0 + int(0.85 * CW)] = True
    eb = np.zeros_like(paper)
    eb[cy0:cy1 + 1, cx0:cx1 + 1] = True
    eb[cy0 + int(0.03 * CH):cy0 + int(0.97 * CH), cx0 + int(0.05 * CW):cx0 + int(0.95 * CW)] = False
    colours = {
        "paper_interior": stat(paper & ci),
        "paper_edge_3pct": stat(paper & eb),
        "red_ink": stat(red),
        "red_ink_dense": stat(red & (luma < 0.32)),
        "black_ink_core": stat(black & (luma < 0.16)),
        "black_ink_all": stat(black),
    }

    return {
        "file": os.path.basename(path),
        "image_px": [W, H],
        "card_px": [CW, CH],
        "card_aspect_w_over_h": round(CW / CH, 4),
        "elements": elements,
        "columns": chars,
        "border_scanlines": border,
        "ring": ring_stats,
        "paper_profile": edge_prof,
        "paper_mottle": mot,
        "colours": colours,
    }


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[0] if argv else os.path.join(os.path.dirname(__file__), "guide_measure2.json")
    res = {t: analyse(p) for t, p in IMAGES}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print("WROTE", out)


main()
