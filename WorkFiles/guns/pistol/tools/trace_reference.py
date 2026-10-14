"""HP01 (Heavy Pistol HP-01): trace and measure References/Guns/Pistol/pistol_sheetA.webp.

numpy + scipy + Pillow only; paths from this file's location. Run:
    py -3 -B WorkFiles/guns/pistol/tools/trace_reference.py
Writes hp01_measured.json, traces/*_outline.json, traces/*.png, HP01_TRACE_OVERLAY.png and scratch QA crops.

Frame of the numbers ("F", mm): +X = muzzle, +Z = up, X = 0 at the muzzle face of the slide/barrel group,
Z = 0 on the bore axis (side views). Converted to the build frame (origin = Grip) in make_spec.py.
Hand reads (seams, part boundaries a silhouette cannot give) are in READS below, in sheet px on the LEFT panel,
read on 4x gridded zooms (tools/gridzoom.py); +-1 px unless noted.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import refimg  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SHEET = os.path.join(ROOT, "References", "Guns", "Pistol", "pistol_sheetA.webp")
OUT = os.path.abspath(os.path.join(HERE, ".."))
TR = os.path.join(OUT, "traces")
SC = os.path.join(OUT, "scratch")

# Real-pattern scale (GUN_BUILDING_STUDY 3.5, [E49]): the 6 in large-frame gas-operated class.
REAL = {"overall_mm": 273.0, "barrel_mm": 152.0, "height_mm": 159.0, "mass_kg": 2.0, "width_mm": 32.0}
LABELS = {0: "LEFT", 1: "RIGHT", 2: "TOP", 3: "34FL"}


def lum_chroma(rgb):
    f = rgb.astype(float)
    L = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
    S = f.max(axis=2) - f.min(axis=2)
    return L, S


def silhouette(rgb, box, exclude_rows=None):
    x0, y0, x1, y1 = box
    crop = rgb[y0:y1 + 1, x0:x1 + 1]
    L, S = lum_chroma(crop)
    excl = np.zeros(L.shape, bool)
    if exclude_rows is not None:
        excl[exclude_rows - y0:, :] = True          # ruler strip
    bg, sd = refimg.fit_background(L, S, deg=4, exclude=excl)
    F = refimg.soft_field(L, S, bg, dl=26.0, ds=20.0, db=22.0)
    F[excl] = 0.0
    m_soft = ndi.binary_opening(F > 0.5, iterations=1)
    # steel flats can match the backdrop luma: add the luma-gradient envelope (edges closed, filled, eroded back
    # by the sobel half-width), then re-open enclosed regions that are backdrop (guard opening, grip-hammer gap)
    gs = ndi.gaussian_filter(L, 0.6)
    mag = np.hypot(ndi.sobel(gs, 0), ndi.sobel(gs, 1)) / 8.0
    e = (mag > 6.0) & ~excl
    me = ndi.binary_fill_holes(ndi.binary_closing(e, iterations=3))
    me = ndi.binary_erosion(me, iterations=1)
    m = refimg.largest_component(ndi.binary_opening(m_soft | me, iterations=2))
    filled = ndi.binary_fill_holes(m)
    lab, n = ndi.label(filled & ~ndi.binary_dilation(e, iterations=1) & ~m_soft)
    flat = (np.abs(L - bg) < 6.0) & (S < 6) & (mag < 3.0)
    for k in range(1, n + 1):
        h = lab == k
        if h.sum() > 150 and flat[h].mean() > 0.6:
            filled &= ~ndi.binary_dilation(h, iterations=1)
    m = refimg.largest_component(filled)
    F = np.where(m, np.maximum(F, 0.75), np.minimum(F, 0.25))
    return crop, L, bg, sd, F, m


def ruler(rgb, box, y_band):
    """Tick x positions on the ruler strip (dark thin verticals), major ticks every 5 cm (labelled 0..25)."""
    x0, y0, x1, y1 = box
    g = rgb[y_band[0]:y_band[1], x0:x1].astype(float).mean(axis=2)
    dark = (g > 170).sum(axis=0)
    xs = np.nonzero(dark >= 2)[0]
    runs = refimg._runs(dark >= 2)
    cents = [x0 + 0.5 * (a + b) for a, b in runs]
    heights = [int(dark[a:b + 1].max()) for a, b in runs]
    return cents, heights


def to_list(P, nd=2):
    return [[round(float(a), nd), round(float(b), nd)] for a, b in P]


def rings_of(F, m, tol=0.3):
    G = F.copy()
    G[~ndi.binary_dilation(m, iterations=2)] = 0.0
    rings = [r for r in refimg.marching_squares(G, 0.5) if abs(refimg.signed_area(r)) > 30]
    rings = [refimg.dp_simplify(r, tol) for r in rings]
    rings.sort(key=lambda r: -abs(refimg.signed_area(r)))
    return rings


def main():
    rgb = np.array(Image.open(SHEET).convert("RGB"))
    panels = refimg.find_panels(rgb)
    assert len(panels) == 4, panels
    res = {"sheet": os.path.relpath(SHEET, ROOT).replace("\\", "/"), "size": list(rgb.shape[1::-1]),
           "panels": {LABELS[i]: list(map(int, b)) for i, b in enumerate(panels)}}

    # ---------------------------------------------------------------- side silhouettes (ruler strip excluded)
    side = {}
    for i in (0, 1):
        box = panels[i]
        crop, L, bg, sd, F, m = silhouette(rgb, box, exclude_rows=box[1] + 500)
        ys, xs = np.nonzero(m)
        side[i] = dict(crop=crop, F=F, m=m, box=box, bgsd=sd,
                       bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())])
    # ruler
    rul = {}
    for i in (0, 1):
        box = panels[i]
        c, h = ruler(rgb, box, (box[1] + 513, box[1] + 537))
        major = [x for x, hh in zip(c, h) if hh >= max(h) - 2]
        rul[LABELS[i]] = {"ticks_x": [round(x, 2) for x in c], "tick_h": h, "major_x": [round(x, 2) for x in major]}
    res["ruler"] = rul

    # mirror test: RIGHT flipped vs LEFT, best integer shift
    mL = side[0]["m"]
    mR = side[1]["m"][:, ::-1]
    H = min(mL.shape[0], mR.shape[0])
    W = min(mL.shape[1], mR.shape[1])
    best = (0, 0, 0.0)
    for dy in range(-6, 7):
        for dx in range(-12, 13):
            a = mL[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)]
            b = mR[max(0, -dy):H - max(0, dy), max(0, -dx):W - max(0, dx)]
            h2, w2 = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
            v = refimg.iou(a[:h2, :w2], b[:h2, :w2])
            if v > best[2]:
                best = (dx, dy, v)
    dx, dy, v = best
    # pixel similarity of the interiors after alignment (is RIGHT a pixel mirror of LEFT?)
    cL = side[0]["crop"].astype(float).mean(axis=2)
    cR = side[1]["crop"][:, ::-1].astype(float).mean(axis=2)
    a = cL[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)]
    b = cR[max(0, -dy):H - max(0, dy), max(0, -dx):W - max(0, dx)]
    h2, w2 = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    a, b = a[:h2, :w2], b[:h2, :w2]
    inside = (mL[max(0, dy):, max(0, dx):][:h2, :w2]) & (mR[max(0, -dy):, max(0, -dx):][:h2, :w2])
    corr = float(np.corrcoef(a[inside], b[inside])[0, 1])
    mad = float(np.median(np.abs(a[inside] - b[inside])))
    res["mirror_test"] = {"right_flipped_vs_left_iou": round(v, 4), "shift_px": [dx, dy],
                          "interior_luma_corr": round(corr, 4), "interior_median_abs_diff": round(mad, 2),
                          "reading": "IoU ~0.97+ and correlated interiors: RIGHT is a mirrored redraw of LEFT, not a "
                                     "pixel copy (texture differs) and carries no handed feature"}

    # ---------------------------------------------------------------- TOP and 3/4 silhouettes
    top = {}
    for i in (2, 3):
        crop, L, bg, sd, F, m = silhouette(rgb, panels[i])
        ys, xs = np.nonzero(m)
        top[i] = dict(crop=crop, F=F, m=m, box=panels[i], bgsd=sd,
                      bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())])

    for k, d in list(side.items()) + list(top.items()):
        res.setdefault("silhouette_bbox_panel_px", {})[LABELS[k]] = d["bbox"]
        res.setdefault("backdrop_resid_sd", {})[LABELS[k]] = round(d["bgsd"], 2)
        Image.fromarray((d["m"] * 255).astype(np.uint8)).save(os.path.join(TR, "%s_silhouette.png" % LABELS[k]))

    np.savez_compressed(os.path.join(SC, "masks.npz"), **{LABELS[k]: d["m"] for k, d in
                                                         list(side.items()) + list(top.items())},
                        **{LABELS[k] + "_F": d["F"].astype(np.float32) for k, d in
                           list(side.items()) + list(top.items())})
    json.dump(res, open(os.path.join(SC, "stage1.json"), "w"), indent=1)
    import stage2 as st2
    st2.stage2(rgb, res, side, top, OUT, TR, SC, REAL)


#STAGE2
if __name__ == "__main__":
    main()
