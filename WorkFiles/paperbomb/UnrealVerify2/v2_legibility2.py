#!/usr/bin/env python
"""Legibility, part 2: the real glyph cells, found rather than assumed.

Part 1 fenced the hero glyph off with an ellipse and the side column with a rectangle,
which clipped the hero's long horizontals and swept up more than one block in the column.
Here every block is FOUND: within each column's own x band the row-occupancy profile is
split at its minima, and the hero is every black texel inside the ring that is not part of
the ring's own stroke annulus.  Then each real block is converted to on-screen pixels at
the LOD1 threshold and re-measured after the reduction.
"""
import json
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealVerify2"
OUT = HERE / "legibility2.json"
MAPS = {
    "reference_matched_shipped": PROJ / "Exports" / "PaperBomb" / "Textures" / "T_PaperBomb_BC.png",
    "floored": PROJ / "WorkFiles" / "paperbomb" / "ink_floor_compare" / "floored" / "T_PaperBomb_BC.png",
}
PPMM, PAD = 12.923, 16
CARD_W, CARD_H = 70.0, 156.0
ENGINE_R_CM = 8.240522
SS = [1.0, 0.171, 0.0599]
PX_PER_MM_LOD1 = (SS[1] * 1080.0) / (2.0 * ENGINE_R_CM * 10.0)
PX_PER_MM_LOD2 = (SS[2] * 1080.0) / (2.0 * ENGINE_R_CM * 10.0)

# column x bands, from the axes the review measured on this very map
COLUMNS = {
    "upper_left_火遁術":  (12.657, 3, (6.0, 74.0)),
    "upper_right_爆炎陣": (57.231, 3, (6.0, 74.0)),
    "lower_right_焼尽":   (57.156, 2, (90.0, 146.0)),
    "lower_centre_瞬業":  (35.082, 2, (108.0, 146.0)),
}
RING = (35.128, 76.835, 26.81, 29.18)


def load_linear(p):
    img = bpy.data.images.load(str(p))
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    b = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(b)
    a = np.flipud(b.reshape(h, w, 4)[:, :, :3].astype(np.float64))
    bpy.data.images.remove(img)
    return a, np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def luma(x):
    return 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]


def area_resize(a, nw, nh):
    h, w = a.shape[:2]
    sq = a.ndim == 2
    if sq:
        a = a[:, :, None]
    sat = np.zeros((h + 1, w + 1, a.shape[2]), np.float64)
    sat[1:, 1:] = np.cumsum(np.cumsum(a, 0), 1)
    ys = np.arange(nh + 1) * h / nh
    xs = np.arange(nw + 1) * w / nw

    def it(yy, xx):
        y0 = np.clip(np.floor(yy).astype(int), 0, h)
        x0 = np.clip(np.floor(xx).astype(int), 0, w)
        fy = np.clip(yy - y0, 0, 1)[:, None, None]
        fx = np.clip(xx - x0, 0, 1)[None, :, None]
        return (sat[np.ix_(y0, x0)] * (1 - fy) * (1 - fx)
                + sat[np.ix_(y0, np.clip(x0 + 1, 0, w))] * (1 - fy) * fx
                + sat[np.ix_(np.clip(y0 + 1, 0, h), x0)] * fy * (1 - fx)
                + sat[np.ix_(np.clip(y0 + 1, 0, h), np.clip(x0 + 1, 0, w))] * fy * fx)
    S = it(ys, xs)
    tot = S[1:, 1:] - S[:-1, 1:] - S[1:, :-1] + S[:-1, :-1]
    ar = ((ys[1:] - ys[:-1])[:, None] * (xs[1:] - xs[:-1])[None, :])[:, :, None]
    o = tot / np.maximum(ar, 1e-12)
    return o[:, :, 0] if sq else o


def blocks_from_profile(mask, ymm, n_expected):
    """Split a column's ink into n blocks at the deepest minima of its row profile."""
    rows = mask.sum(axis=1).astype(float)
    nz = np.nonzero(rows)[0]
    if nz.size == 0:
        return []
    lo, hi = int(nz.min()), int(nz.max())
    seg = rows[lo:hi + 1]
    # candidate splits: local minima, ranked by depth, keeping them apart
    order = np.argsort(seg)
    picks = []
    span = max(1, (hi - lo) // (n_expected * 3))
    for idx in order:
        if len(picks) >= n_expected - 1:
            break
        if all(abs(idx - p) > span for p in picks) and span < idx < (hi - lo - span):
            picks.append(int(idx))
    cuts = [lo] + sorted(lo + p for p in picks) + [hi + 1]
    out = []
    for i in range(len(cuts) - 1):
        a, b = cuts[i], cuts[i + 1]
        sub = mask[a:b]
        if sub.sum() < 20:
            continue
        yy, xx = np.nonzero(sub)
        out.append({
            "y_mm": [round(float(ymm[a + yy.min(), 0]), 3), round(float(ymm[a + yy.max(), 0]), 3)],
            "h_mm": round(float(yy.max() - yy.min() + 1) / PPMM, 3),
            "w_mm": round(float(xx.max() - xx.min() + 1) / PPMM, 3),
            "ink_mm2": round(float(sub.sum()) / PPMM ** 2, 3),
        })
    return out


def main():
    rep = {"lod1_px_per_mm_at_1080p": round(PX_PER_MM_LOD1, 5),
           "lod2_px_per_mm_at_1080p": round(PX_PER_MM_LOD2, 5),
           "engine_sphere_radius_cm": ENGINE_R_CM}
    res = {}
    for name, path in MAPS.items():
        stored_f, lin_f = load_linear(path)
        w = int(round(CARD_W * PPMM)); h = int(round(CARD_H * PPMM))
        stored = stored_f[PAD:PAD + h, PAD:PAD + w]
        lin = lin_f[PAD:PAD + h, PAD:PAD + w]
        L = luma(lin)
        r, g, b = stored[..., 0], stored[..., 1], stored[..., 2]
        mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b)
        sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
        red = (sat > 0.35) & (r > g + 0.10) & (r > b + 0.10)
        paper = float(np.percentile(L[~red], 75)); floor = float(np.percentile(L[~red], 0.5))
        black = (L < 0.5 * (paper + floor)) & (~red)

        H, W = black.shape
        yy, xx = np.mgrid[0:H, 0:W]
        xmm = (xx + 0.5) / PPMM; ymm = (yy + 0.5) / PPMM
        cx, cy, ax, ay = RING
        rr = np.sqrt(((xmm - cx) / ax) ** 2 + ((ymm - cy) / ay) ** 2)

        rec = {"source": str(path),
               "paper_linear_p75": round(paper, 6), "ink_linear_p005": round(floor, 6),
               "full_res_contrast": round(paper / max(floor, 1e-9), 2)}

        # ---- hero: inside the ring, ring's own stroke annulus removed ----------------
        hero = black & (rr < 0.90)
        hy, hx = np.nonzero(hero)
        hero_box = {"w_mm": round(float(hx.max() - hx.min() + 1) / PPMM, 3),
                    "h_mm": round(float(hy.max() - hy.min() + 1) / PPMM, 3),
                    "x_mm": [round(float(hx.min() + .5) / PPMM, 3), round(float(hx.max() + .5) / PPMM, 3)],
                    "y_mm": [round(float(hy.min() + .5) / PPMM, 3), round(float(hy.max() + .5) / PPMM, 3)],
                    "ink_mm2": round(float(hero.sum()) / PPMM ** 2, 3)}
        rec["hero_inside_ring"] = hero_box
        rec["hero_on_screen_px_lod1"] = [round(hero_box["w_mm"] * PX_PER_MM_LOD1, 2),
                                          round(hero_box["h_mm"] * PX_PER_MM_LOD1, 2)]
        rec["hero_on_screen_px_lod2"] = [round(hero_box["w_mm"] * PX_PER_MM_LOD2, 2),
                                          round(hero_box["h_mm"] * PX_PER_MM_LOD2, 2)]

        # ---- columns -----------------------------------------------------------------
        cols = {}
        for label, (axis, nglyph, (y0, y1)) in COLUMNS.items():
            band = black & (np.abs(xmm - axis) < 7.6) & (ymm > y0) & (ymm < y1) & (rr > 1.10)
            if band.sum() < 50:
                cols[label] = {"error": "no ink"}
                continue
            blks = blocks_from_profile(band, ymm, nglyph)
            widths = [bk["w_mm"] for bk in blks]
            heights = [bk["h_mm"] for bk in blks]
            cell = min(min(widths), min(heights)) if blks else None
            cols[label] = {
                "axis_mm": axis, "glyphs_expected": nglyph, "blocks_found": len(blks),
                "blocks": blks,
                "min_block_w_mm": round(min(widths), 3) if widths else None,
                "min_block_h_mm": round(min(heights), 3) if heights else None,
                "smallest_cell_mm": round(cell, 3) if cell else None,
                "smallest_cell_px_lod1": round(cell * PX_PER_MM_LOD1, 2) if cell else None,
                "smallest_cell_px_lod2": round(cell * PX_PER_MM_LOD2, 2) if cell else None,
            }
        rec["columns"] = cols
        allcells = [c["smallest_cell_mm"] for c in cols.values() if c.get("smallest_cell_mm")]
        rec["narrowest_glyph_cell_mm"] = round(min(allcells), 3) if allcells else None
        rec["narrowest_glyph_cell_px_lod1"] = round(min(allcells) * PX_PER_MM_LOD1, 2) if allcells else None
        rec["narrowest_glyph_cell_px_lod2"] = round(min(allcells) * PX_PER_MM_LOD2, 2) if allcells else None

        # ---- reduce to the LOD1 size and re-measure each region -----------------------
        nw = int(round(CARD_W * PX_PER_MM_LOD1)); nh = int(round(CARD_H * PX_PER_MM_LOD1))
        small = area_resize(lin, nw, nh)
        Ls = luma(small)
        paper_s = float(np.percentile(Ls, 75))

        def region(mask, tag):
            f = area_resize(mask.astype(np.float64), nw, nh)
            sel = f > 0.35
            if sel.sum() < 3:
                sel = f > 0.15
            if sel.sum() < 1:
                return {"error": "vanishes at LOD1 size"}
            v = Ls[sel]
            lo = float(v.min())
            return {"px_at_lod1": int(sel.sum()),
                    "darkest_linear": round(lo, 6),
                    "median_linear": round(float(np.median(v)), 6),
                    "michelson_vs_card_paper": round((paper_s - lo) / max(paper_s + lo, 1e-9), 5),
                    "ratio_paper_over_darkest": round(paper_s / max(lo, 1e-9), 2),
                    "mean_ink_coverage_retained": round(float(f[sel].mean()), 4)}

        rec["lod1_card_px"] = [nw, nh]
        rec["lod1_paper_linear_p75"] = round(paper_s, 6)
        rec["lod1_hero"] = region(hero, "hero")
        # narrowest column, as a mask
        narrow_label = min(cols, key=lambda k: cols[k].get("smallest_cell_mm") or 9e9)
        axis, ng, (y0, y1) = COLUMNS[narrow_label]
        nb = black & (np.abs(xmm - axis) < 7.6) & (ymm > y0) & (ymm < y1) & (rr > 1.10)
        rec["narrowest_column"] = narrow_label
        rec["lod1_narrowest_column"] = region(nb, narrow_label)
        rule = black & (xmm > 2.8) & (xmm < 5.4) & (ymm > 20) & (ymm < 136)
        rec["lod1_left_rule"] = region(rule, "rule")
        rec["lod1_whole_card"] = {
            "paper_p75": round(paper_s, 6), "min": round(float(Ls.min()), 6),
            "p01": round(float(np.percentile(Ls, 1)), 6),
            "contrast_p75_over_min": round(paper_s / max(float(Ls.min()), 1e-9), 2),
            "rms_contrast": round(float(Ls.std() / max(Ls.mean(), 1e-9)), 5)}
        res[name] = rec
    rep["maps"] = res
    OUT.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print("[legibility2] ->", OUT)
    for n, r in res.items():
        print("==", n)
        print("   hero box mm", r["hero_inside_ring"]["w_mm"], "x", r["hero_inside_ring"]["h_mm"],
              "-> px@LOD1", r["hero_on_screen_px_lod1"], " px@LOD2", r["hero_on_screen_px_lod2"])
        print("   narrowest cell", r["narrowest_glyph_cell_mm"], "mm ->",
              r["narrowest_glyph_cell_px_lod1"], "px@LOD1,", r["narrowest_glyph_cell_px_lod2"], "px@LOD2",
              "(", r["narrowest_column"], ")")
        print("   LOD1 hero", json.dumps(r["lod1_hero"]))
        print("   LOD1 col ", json.dumps(r["lod1_narrowest_column"]))
        print("   LOD1 rule", json.dumps(r["lod1_left_rule"]))
        print("   LOD1 card", json.dumps(r["lod1_whole_card"]))
        for k, c in r["columns"].items():
            print("     ", k, "blocks", c.get("blocks_found"), [b["h_mm"] for b in c.get("blocks", [])],
                  "w", [b["w_mm"] for b in c.get("blocks", [])])


main()
