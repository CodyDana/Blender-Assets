# -*- coding: utf-8 -*-
"""Third pass: border structure, ring as an ellipse, clean glyph boxes, mottle.

Prints coarse ASCII occupancy maps (measurement aid only) and writes JSON.
blender -b --factory-startup --python measure_guide3.py -- <out.json>
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
import numpy as np

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"
IMAGES = [("v1", os.path.join(REF, "paperbomb_guide.png")),
          ("v2", os.path.join(REF, "paperbomb_guide_v2_real_glyphs.png"))]


def load(path):
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    a = buf.reshape(h, w, 4)[::-1].astype(np.float64)
    bpy.data.images.remove(img)
    return a, w, h


def analyse(tag, path):
    a, W, H = load(path)
    rgb = a[:, :, :3]
    R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    luma = 0.2126 * R + 0.7152 * G + 0.0722 * B
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    card = (sat > 0.06) | (luma < 0.70)
    cx = np.nonzero(card.sum(axis=0) > 0.05 * H)[0]
    ry = np.nonzero(card.sum(axis=1) > 0.05 * W)[0]
    cx0, cx1, cy0, cy1 = int(cx.min()), int(cx.max()), int(ry.min()), int(ry.max())
    CW, CH = cx1 - cx0 + 1, cy1 - cy0 + 1
    red = (R - G > 0.25) & (R > 0.22)
    black = (luma < 0.38) & ~red
    C = card[cy0:cy1 + 1, cx0:cx1 + 1]
    RD = red[cy0:cy1 + 1, cx0:cx1 + 1]
    BK = black[cy0:cy1 + 1, cx0:cx1 + 1]
    LU = luma[cy0:cy1 + 1, cx0:cx1 + 1]
    out = {"file": os.path.basename(path), "card_px": [CW, CH],
           "aspect_w_over_h": round(CW / CH, 4)}

    # ---- ascii map ----------------------------------------------------
    def ascii_map(rmask, bmask, cmask, nx, ny, x0=0.0, x1=1.0, y0=0.0, y1=1.0):
        lines = []
        for j in range(ny):
            ya = int((y0 + (y1 - y0) * j / ny) * CH)
            yb = max(ya + 1, int((y0 + (y1 - y0) * (j + 1) / ny) * CH))
            row = ""
            for i in range(nx):
                xa = int((x0 + (x1 - x0) * i / nx) * CW)
                xb = max(xa + 1, int((x0 + (x1 - x0) * (i + 1) / nx) * CW))
                rr = rmask[ya:yb, xa:xb].mean()
                bb = bmask[ya:yb, xa:xb].mean()
                cc = cmask[ya:yb, xa:xb].mean()
                if cc < 0.4:
                    row += " "
                elif bb > 0.35:
                    row += "#"
                elif rr > 0.35:
                    row += "R"
                elif bb > 0.10:
                    row += "+"
                elif rr > 0.10:
                    row += "r"
                else:
                    row += "."
            lines.append(row)
        return lines

    print("=== %s whole card 44x92 (#=black R=red .=paper)" % tag)
    for ln in ascii_map(RD, BK, C, 44, 92):
        print("   " + ln)
    print("=== %s top-left corner, x0-0.30 y0-0.16, 40x40" % tag)
    for ln in ascii_map(RD, BK, C, 40, 40, 0.0, 0.30, 0.0, 0.16):
        print("   " + ln)
    print("=== %s bottom strip x0-1 y0.88-1.0, 60x22" % tag)
    for ln in ascii_map(RD, BK, C, 60, 22, 0.0, 1.0, 0.88, 1.0):
        print("   " + ln)

    # ---- border: red column histogram over clean rows ------------------
    left = RD[:, :int(0.22 * CW)]
    hist = left.sum(axis=0) / CH
    out["left_border_red_col_coverage"] = [[round(i / CW, 4), round(float(v), 3)]
                                           for i, v in enumerate(hist) if v > 0.05]
    right = RD[:, int(0.78 * CW):]
    histr = right.sum(axis=0) / CH
    out["right_border_red_col_coverage"] = [[round((i + int(0.78 * CW)) / CW, 4), round(float(v), 3)]
                                            for i, v in enumerate(histr) if v > 0.05]
    top = RD[:int(0.14 * CH), :]
    histt = top.sum(axis=1) / CW
    out["top_border_red_row_coverage"] = [[round(i / CH, 4), round(float(v), 3)]
                                          for i, v in enumerate(histt) if v > 0.05]
    bot = RD[int(0.86 * CH):, :]
    histb = bot.sum(axis=1) / CW
    out["bottom_border_red_row_coverage"] = [[round((i + int(0.86 * CH)) / CH, 4), round(float(v), 3)]
                                             for i, v in enumerate(histb) if v > 0.05]

    # ---- corner clip: leading edge of the card, top-left ----------------
    pts = []
    for y in range(0, int(0.10 * CH)):
        nz = np.nonzero(C[y])[0]
        if len(nz):
            pts.append((y, int(nz.min())))
    if len(pts) > 5:
        ys = np.array([p[0] for p in pts], dtype=float)
        xs = np.array([p[1] for p in pts], dtype=float)
        onslope = xs > 2
        if onslope.sum() > 5:
            k = np.polyfit(ys[onslope], xs[onslope], 1)
            out["corner_clip"] = {
                "slope_dx_per_dy_px": round(float(k[0]), 4),
                "angle_from_vertical_deg": round(math.degrees(math.atan(-k[0])), 2),
                "clip_run_x_px": round(float(xs[0]), 1),
                "clip_rise_y_px": round(float(ys[onslope].max()), 1),
                "clip_run_frac_w": round(float(xs[0]) / CW, 4),
                "clip_rise_frac_h": round(float(ys[onslope].max()) / CH, 4),
                "clip_run_mm_per_100mm_w": round(100.0 * float(xs[0]) / CW, 2),
            }

    # ---- ring as an ellipse --------------------------------------------
    m = np.zeros_like(RD)
    m[int(0.25 * CH):int(0.74 * CH), int(0.13 * CW):int(0.93 * CW)] = True
    ring = RD & m
    ys, xs = np.nonzero(ring)
    if len(xs) > 200:
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        ecx, ecy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        ax, ay = (x1 - x0) / 2.0, (y1 - y0) / 2.0
        t = np.arctan2((ys - ecy) / ay, (xs - ecx) / ax)
        rr = np.hypot((xs - ecx) / ax, (ys - ecy) / ay)
        bins = np.floor((t + math.pi) / (2 * math.pi) * 180).astype(int) % 180
        present = np.array([(bins == b).sum() for b in range(180)])
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
        # horizontal / vertical stroke widths
        rowm = ring[int(ecy), :]
        colm = ring[:, int(ecx)]

        def runs(v):
            o, r = [], None
            for i, q in enumerate(v):
                if q:
                    r = [i, i] if r is None else [r[0], i]
                else:
                    if r is not None:
                        o.append(r)
                    r = None
            if r is not None:
                o.append(r)
            return o
        out["ring"] = {
            "bbox_frac": {"x0": round(x0 / CW, 4), "x1": round((x1 + 1) / CW, 4),
                          "y0": round(y0 / CH, 4), "y1": round((y1 + 1) / CH, 4)},
            "centre_frac": [round(ecx / CW, 4), round(ecy / CH, 4)],
            "outer_w_frac_w": round((x1 - x0 + 1) / CW, 4),
            "outer_h_frac_h": round((y1 - y0 + 1) / CH, 4),
            "outer_w_px": int(x1 - x0 + 1), "outer_h_px": int(y1 - y0 + 1),
            "ellipse_h_over_w": round((y1 - y0 + 1) / (x1 - x0 + 1), 4),
            "norm_r_p05": round(float(np.percentile(rr, 5)), 3),
            "norm_r_p50": round(float(np.percentile(rr, 50)), 3),
            "norm_r_p95": round(float(np.percentile(rr, 95)), 3),
            "horiz_runs_at_centre_frac_w": [[round(r[0] / CW, 4), round((r[1] + 1) / CW, 4),
                                             round((r[1] + 1 - r[0]) / CW, 4)] for r in runs(rowm)],
            "vert_runs_at_centre_frac_h": [[round(r[0] / CH, 4), round((r[1] + 1) / CH, 4),
                                            round((r[1] + 1 - r[0]) / CH, 4)] for r in runs(colm)],
            "angular_coverage": round(float((present >= 3).sum()) / 180, 3),
            "gap_runs_deg": [[round(g[0] * 2 - 180, 1), round((g[1] + 1) * 2 - 180, 1)] for g in gaps],
            "fill_of_bbox": round(float(len(xs)) / ((x1 - x0 + 1) * (y1 - y0 + 1)), 3),
        }

    # ---- glyph boxes, tight windows (black only, borders excluded) ------
    def gbox(fx0, fx1, fy0, fy1):
        x0, x1 = int(fx0 * CW), int(fx1 * CW)
        y0, y1 = int(fy0 * CH), int(fy1 * CH)
        sub = BK[y0:y1, x0:x1]
        ys_, xs_ = np.nonzero(sub)
        if len(xs_) < 20:
            return None
        return {"x0": round((x0 + xs_.min()) / CW, 4), "x1": round((x0 + xs_.max() + 1) / CW, 4),
                "y0": round((y0 + ys_.min()) / CH, 4), "y1": round((y0 + ys_.max() + 1) / CH, 4),
                "w_frac_w": round((xs_.max() + 1 - xs_.min()) / CW, 4),
                "h_frac_h": round((ys_.max() + 1 - ys_.min()) / CH, 4),
                "h_frac_w": round((ys_.max() + 1 - ys_.min()) / CW, 4),
                "cx": round((x0 + (xs_.min() + xs_.max() + 1) / 2) / CW, 4),
                "cy": round((y0 + (ys_.min() + ys_.max() + 1) / 2) / CH, 4),
                "ink_density": round(float(sub.sum()) /
                                     ((xs_.max() + 1 - xs_.min()) * (ys_.max() + 1 - ys_.min())), 3)}

    out["glyphs"] = {
        "centre_big": gbox(0.10, 0.90, 0.30, 0.70),
        "flame_emblem": gbox(0.34, 0.66, 0.06, 0.33),
        "ul_c1": gbox(0.03, 0.33, 0.03, 0.135),
        "ul_c2": gbox(0.03, 0.33, 0.135, 0.235),
        "ul_c3": gbox(0.03, 0.33, 0.235, 0.345),
        "ur_c1": gbox(0.66, 0.93, 0.03, 0.135),
        "ur_c2": gbox(0.66, 0.93, 0.135, 0.235),
        "ur_c3": gbox(0.66, 0.93, 0.235, 0.345),
        "lr_c1": gbox(0.66, 0.93, 0.56, 0.665),
        "lr_c2": gbox(0.66, 0.93, 0.665, 0.82),
        "lc_c1": gbox(0.35, 0.68, 0.69, 0.81),
        "lc_c2": gbox(0.35, 0.68, 0.81, 0.93),
    }

    # ---- mottle by high pass -------------------------------------------
    paper = C & ~RD & ~BK
    lu = np.where(paper, LU, np.nan)
    n = max(4, CW // 24)
    hh, ww = (CH // n) * n, (CW // n) * n
    tile = lu[:hh, :ww].reshape(hh // n, n, ww // n, n)
    with np.errstate(invalid="ignore"):
        coarse = np.nanmean(tile, axis=(1, 3))
    big = np.repeat(np.repeat(coarse, n, axis=0), n, axis=1)
    hp = lu[:hh, :ww] - big
    ok = ~np.isnan(hp)
    out["mottle"] = {
        "highpass_block_px": n,
        "highpass_std": round(float(np.nanstd(hp[ok])), 4),
        "coarse_field_std": round(float(np.nanstd(coarse)), 4),
        "coarse_p05": round(float(np.nanpercentile(coarse, 5)), 4),
        "coarse_p50": round(float(np.nanpercentile(coarse, 50)), 4),
        "coarse_p95": round(float(np.nanpercentile(coarse, 95)), 4),
        "paper_luma_p01": round(float(np.nanpercentile(lu, 1)), 4),
        "paper_luma_p99": round(float(np.nanpercentile(lu, 99)), 4),
    }
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = argv[0] if argv else os.path.join(os.path.dirname(__file__), "guide_measure3.json")
    res = {t: analyse(t, p) for t, p in IMAGES}
    with open(o, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print("WROTE", o)


main()
