# -*- coding: utf-8 -*-
"""Measure the paper-bomb guide PNGs.

Run headless:
  blender -b --factory-startup --python measure_guide.py -- <out.json>

Reads the two guide images as RAW stored sRGB (colorspace forced to Non-Color so
image.pixels returns the stored byte values / 255, not a linear conversion), builds
masks for card / red ink / black ink, labels connected components at quarter
resolution, refines their boxes at full resolution and writes every number as a
fraction of the CARD's width and height.

Nothing is copied out of the images: only scalar measurements and colour statistics.
"""
from __future__ import annotations

import json
import os
import sys

import bpy
import numpy as np

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"
IMAGES = [
    ("v1", os.path.join(REF, "paperbomb_guide.png")),
    ("v2", os.path.join(REF, "paperbomb_guide_v2_real_glyphs.png")),
]


def load_raw(path):
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    a = buf.reshape(h, w, 4)[::-1]  # row 0 = top
    bpy.data.images.remove(img)
    return a, w, h


def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def label(mask):
    """Two-pass connected components (8-neighbour) on a small boolean mask."""
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=np.int32)
    parent = [0]

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    nxt = 1
    m = mask
    for y in range(h):
        row = m[y]
        if not row.any():
            continue
        prev = lab[y - 1] if y > 0 else None
        for x in np.nonzero(row)[0]:
            n = []
            if x > 0 and lab[y, x - 1]:
                n.append(lab[y, x - 1])
            if prev is not None:
                for dx in (-1, 0, 1):
                    xx = x + dx
                    if 0 <= xx < w and prev[xx]:
                        n.append(prev[xx])
            if not n:
                parent.append(nxt)
                lab[y, x] = nxt
                nxt += 1
            else:
                mn = min(n)
                lab[y, x] = mn
                for v in n:
                    union(mn, v)
    out = {}
    for y in range(h):
        for x in np.nonzero(lab[y])[0]:
            r = find(lab[y, x])
            b = out.get(r)
            if b is None:
                out[r] = [x, y, x, y, 1]
            else:
                if x < b[0]:
                    b[0] = x
                if y < b[1]:
                    b[1] = y
                if x > b[2]:
                    b[2] = x
                if y > b[3]:
                    b[3] = y
                b[4] += 1
    return out


def refine(full_mask, box, s):
    """box is (x0,y0,x1,y1) at 1/s resolution -> exact box at full res."""
    x0, y0, x1, y1 = box
    X0, Y0 = max(0, x0 * s - s), max(0, y0 * s - s)
    X1 = min(full_mask.shape[1], (x1 + 2) * s)
    Y1 = min(full_mask.shape[0], (y1 + 2) * s)
    sub = full_mask[Y0:Y1, X0:X1]
    ys, xs = np.nonzero(sub)
    if len(xs) == 0:
        return None
    return (
        int(X0 + xs.min()),
        int(Y0 + ys.min()),
        int(X0 + xs.max()),
        int(Y0 + ys.max()),
        int(sub.sum()),
    )


def analyse(tag, path):
    a, W, H = load_raw(path)
    rgb = a[:, :, :3].astype(np.float64)
    R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    luma = 0.2126 * R + 0.7152 * G + 0.0722 * B
    sat = rgb.max(axis=2) - rgb.min(axis=2)

    # ---- card mask -------------------------------------------------------
    card = (sat > 0.06) | (luma < 0.70)
    # keep only columns/rows with a real run of card pixels (kills the soft shadow)
    colc = card.sum(axis=0)
    rowc = card.sum(axis=1)
    cx = np.nonzero(colc > 0.05 * H)[0]
    ry = np.nonzero(rowc > 0.05 * W)[0]
    cx0, cx1 = int(cx.min()), int(cx.max())
    cy0, cy1 = int(ry.min()), int(ry.max())
    CW = cx1 - cx0 + 1
    CH = cy1 - cy0 + 1

    def fx(v):
        return round((v - cx0) / CW, 4)

    def fy(v):
        return round((v - cy0) / CH, 4)

    def frac_box(bx):
        x0, y0, x1, y1, n = bx
        return {
            "x0": fx(x0), "y0": fy(y0), "x1": fx(x1 + 1), "y1": fy(y1 + 1),
            "cx": round((fx(x0) + fx(x1 + 1)) / 2, 4),
            "cy": round((fy(y0) + fy(y1 + 1)) / 2, 4),
            "w": round(fx(x1 + 1) - fx(x0), 4),
            "h": round(fy(y1 + 1) - fy(y0), 4),
            "px": [int(x0), int(y0), int(x1), int(y1)],
            "area_px": int(n),
        }

    # ---- corner clip: first card column per row near the top -------------
    clip = {}
    sub = card[cy0:cy1 + 1, cx0:cx1 + 1]
    # top-left: for each of the first rows, index of first True
    first = []
    for y in range(0, int(0.12 * CH)):
        nz = np.nonzero(sub[y])[0]
        first.append(int(nz.min()) if len(nz) else CW)
    first = np.array(first, dtype=float)
    # the clip ends where the leading edge reaches x ~ 0
    reach = np.nonzero(first <= 2)[0]
    clip["top_left_clip_h_frac"] = round(float(reach[0]) / CH, 4) if len(reach) else None
    clip["top_left_clip_w_frac"] = round(float(first[0]) / CW, 4)
    # bottom-left
    firstb = []
    for y in range(CH - 1, CH - 1 - int(0.12 * CH), -1):
        nz = np.nonzero(sub[y])[0]
        firstb.append(int(nz.min()) if len(nz) else CW)
    firstb = np.array(firstb, dtype=float)
    reachb = np.nonzero(firstb <= 2)[0]
    clip["bottom_left_clip_h_frac"] = round(float(reachb[0]) / CH, 4) if len(reachb) else None
    clip["bottom_left_clip_w_frac"] = round(float(firstb[0]) / CW, 4)

    # ---- ink masks -------------------------------------------------------
    red = (R - G > 0.25) & (R > 0.22)
    black = (luma < 0.38) & ~red
    inside = np.zeros_like(card)
    inside[cy0:cy1 + 1, cx0:cx1 + 1] = True
    red &= inside
    black &= inside

    # ---- red border: column / row histograms of red -----------------------
    rc = red[cy0:cy1 + 1, cx0:cx1 + 1].sum(axis=0).astype(float) / CH
    rr = red[cy0:cy1 + 1, cx0:cx1 + 1].sum(axis=1).astype(float) / CW

    def peaks(prof, thresh):
        out = []
        run = None
        for i, v in enumerate(prof):
            if v >= thresh:
                if run is None:
                    run = [i, i]
                else:
                    run[1] = i
            else:
                if run is not None:
                    out.append(run)
                    run = None
        if run is not None:
            out.append(run)
        return out

    border = {
        "red_col_runs_over_0.35": [[round(p[0] / CW, 4), round((p[1] + 1) / CW, 4)]
                                   for p in peaks(rc, 0.35)],
        "red_row_runs_over_0.35": [[round(p[0] / CH, 4), round((p[1] + 1) / CH, 4)]
                                   for p in peaks(rr, 0.35)],
        "red_col_runs_over_0.15": [[round(p[0] / CW, 4), round((p[1] + 1) / CW, 4)]
                                   for p in peaks(rc, 0.15)],
        "red_row_runs_over_0.15": [[round(p[0] / CH, 4), round((p[1] + 1) / CH, 4)]
                                   for p in peaks(rr, 0.15)],
    }

    # ---- components -------------------------------------------------------
    s = 4 if W > 600 else 2
    comps = {}
    for name, mask in (("red", red), ("black", black)):
        small = mask[: (H // s) * s, : (W // s) * s].reshape(H // s, s, W // s, s)
        small = small.any(axis=(1, 3))
        boxes = label(small)
        got = []
        for b in boxes.values():
            if b[4] * s * s < 0.00018 * CW * CH:
                continue
            rb = refine(mask, (b[0], b[1], b[2], b[3]), s)
            if rb:
                got.append(frac_box(rb))
        got.sort(key=lambda d: -d["area_px"])
        comps[name] = got[:28]

    # ---- red ring: red pixels in the middle band, ignoring the border -----
    inner = np.zeros_like(red)
    m0, m1 = cy0 + int(0.22 * CH), cy0 + int(0.72 * CH)
    n0, n1 = cx0 + int(0.12 * CW), cx0 + int(0.88 * CW)
    inner[m0:m1, n0:n1] = True
    ring = red & inner
    ys, xs = np.nonzero(ring)
    ring_stats = None
    if len(xs) > 200:
        rx0, rx1, ry0, ry1 = xs.min(), xs.max(), ys.min(), ys.max()
        rcx, rcy = (rx0 + rx1) / 2.0, (ry0 + ry1) / 2.0
        rr_ = np.hypot(xs - rcx, ys - rcy)
        ring_stats = {
            "centre": [fx(rcx), fy(rcy)],
            "bbox": {"x0": fx(rx0), "y0": fy(ry0), "x1": fx(rx1 + 1), "y1": fy(ry1 + 1)},
            "outer_d_frac_w": round((rx1 - rx0 + 1) / CW, 4),
            "outer_d_frac_h": round((ry1 - ry0 + 1) / CH, 4),
            "r_p95_frac_w": round(float(np.percentile(rr_, 95)) * 2 / CW, 4),
            "r_p05_frac_w": round(float(np.percentile(rr_, 5)) * 2 / CW, 4),
            "stroke_w_frac_w": round(float(np.percentile(rr_, 95) - np.percentile(rr_, 5)) / CW, 4),
            "coverage_of_annulus": round(float(len(xs)) /
                                         (np.pi * (np.percentile(rr_, 95) ** 2 -
                                                   np.percentile(rr_, 5) ** 2)), 3),
        }

    # ---- colours ---------------------------------------------------------
    pap = card.copy()
    pap &= ~red
    pap &= ~black
    pap &= inside
    # clear interior sample: central 60% minus ink
    ci = np.zeros_like(pap)
    ci[cy0 + int(0.15 * CH):cy0 + int(0.85 * CH), cx0 + int(0.15 * CW):cx0 + int(0.85 * CW)] = True
    edge = np.zeros_like(pap)
    edge[cy0:cy1 + 1, cx0:cx1 + 1] = True
    edge[cy0 + int(0.04 * CH):cy0 + int(0.96 * CH), cx0 + int(0.06 * CW):cx0 + int(0.94 * CW)] = False

    def stat(mask, label_):
        sel = rgb[mask]
        if len(sel) < 50:
            return None
        p = {q: [round(float(v), 4) for v in np.percentile(sel, q, axis=0)] for q in (5, 50, 95)}
        lin = srgb_to_linear(p[50])
        return {
            "n_px": int(len(sel)),
            "stored_srgb_p05": p[5], "stored_srgb_p50": p[50], "stored_srgb_p95": p[95],
            "linear_p50": [round(float(v), 4) for v in lin],
            "linear_luma_p50": round(float(0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]), 4),
            "stored_luma_p05": round(float(np.percentile(0.2126 * sel[:, 0] + 0.7152 * sel[:, 1] + 0.0722 * sel[:, 2], 5)), 4),
            "stored_luma_p95": round(float(np.percentile(0.2126 * sel[:, 0] + 0.7152 * sel[:, 1] + 0.0722 * sel[:, 2], 95)), 4),
        }

    colours = {
        "paper_interior": stat(pap & ci, "paper"),
        "paper_edge_band": stat(pap & edge, "edge"),
        "red_ink": stat(red, "red"),
        "black_ink_core": stat(black & (luma < 0.20), "black"),
        "black_ink_all": stat(black, "blackall"),
    }

    # paper mottle: std of luma inside a clean block
    blk = luma[cy0 + int(0.30 * CH):cy0 + int(0.40 * CH), cx0 + int(0.08 * CW):cx0 + int(0.18 * CW)]
    colours["paper_block_luma_mean"] = round(float(blk.mean()), 4)
    colours["paper_block_luma_std"] = round(float(blk.std()), 4)

    # ink coverage
    cov = {
        "red_frac_of_card": round(float(red.sum()) / (CW * CH), 4),
        "black_frac_of_card": round(float(black.sum()) / (CW * CH), 4),
    }

    return {
        "file": os.path.basename(path),
        "image_px": [W, H],
        "card_px": [CW, CH],
        "card_bbox_px": [cx0, cy0, cx1, cy1],
        "card_aspect_w_over_h": round(CW / CH, 4),
        "card_aspect_h_over_w": round(CH / CW, 4),
        "corner_clip": clip,
        "border_profiles": border,
        "red_ring": ring_stats,
        "components": comps,
        "colours": colours,
        "coverage": cov,
    }


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[0] if argv else os.path.join(os.path.dirname(__file__), "guide_measure.json")
    res = {}
    for tag, p in IMAGES:
        res[tag] = analyse(tag, p)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print("WROTE", out)


main()
