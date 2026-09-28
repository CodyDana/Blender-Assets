# -*- coding: utf-8 -*-
"""Re-measure the SHIPPED base-colour map with a raster-only instrument.

Written to reproduce the fourth measuring pass's method as closely as its report
describes it, so the build's own figures can be checked against a second one:
rule occupancy over the FULL run at several band widths, the red raster boxes of
both chops, and whether the hero glyph is welded to the lower-right column.
Reads only our own export - never a guide.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "reference_metrology"))
import pngread  # noqa: E402
import lib_metro as L  # noqa: E402

BC = r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png"
OUT = os.path.join(HERE, "independent_check.json")
PPMM = 12.923
OX = OY = 16
CARD_W, CARD_H = 70.0, 156.0
# the fitted rule rectangle, from the build's own frame_sides measurement
RULE = dict(left=3.985, right=65.89, top=6.616, bottom=148.688)


def main():
    a, _ = pngread.read_png(BC)
    arr = a.astype(np.float64) / (65535.0 if a.dtype == np.uint16 else 255.0)
    card = arr[OY:OY + int(round(CARD_H * PPMM)), OX:OX + int(round(CARD_W * PPMM)), :3]
    r, g, b = card[..., 0], card[..., 1], card[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx = card.max(axis=2); mn = card.min(axis=2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    red = (r - b > 0.22) & (sat > 0.35)
    black = (~red) & (lum < 0.38)
    out = {"red_area_fraction": round(float(red.mean()), 5),
           "black_area_fraction": round(float(black.mean()), 5),
           "total_ink_fraction": round(float((red | black).mean()), 5),
           "black_over_red": round(float(black.sum() / max(red.sum(), 1)), 4)}

    # --- contrast, on the same classes
    def lin(x):
        return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    lin_lum = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    paper = ~(red | black)
    out["paper_linear_median"] = round(float(np.median(lin_lum[paper])), 5)
    out["black_linear_median"] = round(float(np.median(lin_lum[black])), 6)
    out["contrast_ratio"] = round(out["paper_linear_median"] / max(out["black_linear_median"], 1e-9), 1)
    out["black_stored_min"] = round(float(np.min(lum[black])), 4)

    # --- rule occupancy, FULL run, several band widths
    occ = {}
    for half in (1.2, 1.6, 2.2, 3.0):
        side = {}
        for name in ("left", "right", "top", "bottom"):
            at = RULE[name]
            if name in ("left", "right"):
                lo, hi = RULE["top"], RULE["bottom"]
                rows = range(int(lo * PPMM), int(hi * PPMM))
                xs = slice(int((at - half) * PPMM), int((at + half) * PPMM))
                hits = [bool(red[y, xs].any()) for y in rows]
            else:
                lo, hi = RULE["left"], RULE["right"]
                cols = range(int(lo * PPMM), int(hi * PPMM))
                ys = slice(int((at - half) * PPMM), int((at + half) * PPMM))
                hits = [bool(red[ys, x].any()) for x in cols]
            side[name] = round(float(np.mean(hits)), 4)
        occ["half_%.1f" % half] = side
    out["rule_occupancy"] = occ
    out["rule_occupancy_min"] = round(min(v for s in occ.values() for v in s.values()), 4)

    # --- red raster components round both chops
    lab, comps = L.label_components(red)
    comps.sort(key=lambda c: -c["n"])
    def box(c):
        return dict(x0=round(c["x0"] / PPMM, 2), x1=round(c["x1"] / PPMM, 2),
                    y0=round(c["y0"] / PPMM, 2), y1=round(c["y1"] / PPMM, 2),
                    w=round((c["x1"] - c["x0"]) / PPMM, 3),
                    h=round((c["y1"] - c["y0"]) / PPMM, 3),
                    area_mm2=round(c["n"] / PPMM / PPMM, 2))
    # a chop is every red component that lies INSIDE its own frame box plus 2 mm - a
    # component that runs outside that (a rule, a bracket fused to the chop) is taken
    # whole, which is the point: a weld shows up as a box far too big.
    FRAMES = {"big": (5.79, 116.78, 23.71, 143.46), "small": (54.91, 123.55, 63.88, 141.41)}
    seals = {"big": [], "small": []}
    for c in comps:
        bx = box(c)
        if bx["area_mm2"] < 1.0:
            continue
        for k, (fx0, fy0, fx1, fy1) in FRAMES.items():
            inside = (bx["x0"] >= fx0 - 2.0 and bx["x1"] <= fx1 + 2.0
                      and bx["y0"] >= fy0 - 2.0 and bx["y1"] <= fy1 + 2.0)
            touches = not (bx["x1"] < fx0 or bx["x0"] > fx1
                           or bx["y1"] < fy0 or bx["y0"] > fy1)
            if touches and inside:
                seals[k].append(bx)
            elif touches and not inside:
                seals[k].append(bx)      # a welded neighbour: kept, and it will show
    for k, v in seals.items():
        if v:
            out["%s_seal_red_union_mm" % k] = [
                round(max(p["x1"] for p in v) - min(p["x0"] for p in v), 3),
                round(max(p["y1"] for p in v) - min(p["y0"] for p in v), 3)]
            out["%s_seal_red_extent_mm" % k] = [
                round(min(p["x0"] for p in v), 2), round(min(p["y0"] for p in v), 2),
                round(max(p["x1"] for p in v), 2), round(max(p["y1"] for p in v), 2)]
            out["%s_seal_parts" % k] = len(v)

    # --- the hero glyph, and whether a column is welded to it
    labb, bcomps = L.label_components(black)
    bcomps.sort(key=lambda c: -c["n"])
    hero = []
    for c in bcomps:
        bx = box(c)
        cx = 0.5 * (bx["x0"] + bx["x1"]); cy = 0.5 * (bx["y0"] + bx["y1"])
        if bx["area_mm2"] >= 15.0 and 15.0 < cx < 58.0 and 59.0 < cy < 96.0:
            hero.append((c, bx))
    if hero:
        x0 = min(b["x0"] for _c, b in hero); x1 = max(b["x1"] for _c, b in hero)
        y0 = min(b["y0"] for _c, b in hero); y1 = max(b["y1"] for _c, b in hero)
        out["hero_components"] = len(hero)
        out["hero_box_mm"] = [round(x1 - x0, 3), round(y1 - y0, 3)]
        out["hero_extent_mm"] = [x0, y0, x1, y1]
        out["hero_component_areas_mm2"] = [b["area_mm2"] for _c, b in hero]
        pair = sorted(hero, key=lambda t: t[1]["x0"])[:2]
        if len(pair) == 2:
            out["hero_bbox_overlap_mm"] = round(pair[0][1]["x1"] - pair[1][1]["x0"], 3)
    # the lower-right corridor, broken down the way the fourth pass broke it down
    corridor = black[:, int(49.5 * PPMM):int(65.0 * PPMM)]
    bands = [(88, 96), (96, 108.8), (108.8, 122), (122, 130)]
    out["lower_right_corridor_mm2"] = {
        "%g-%g" % (a0, a1): round(float(corridor[int(a0 * PPMM):int(a1 * PPMM)].sum())
                                  / PPMM / PPMM, 1) for a0, a1 in bands}
    # how many separate marks the lower-right column shows
    cells = []
    for c in bcomps:
        bx = box(c)
        cx = 0.5 * (bx["x0"] + bx["x1"]); cy = 0.5 * (bx["y0"] + bx["y1"])
        if bx["area_mm2"] >= 10.0 and 50.0 < cx < 65.0 and 96.0 < cy < 126.0:
            cells.append(bx)
    out["lower_right_marks"] = len(cells)
    out["lower_right_mark_boxes"] = cells[:4]

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
