"""v2 reference measurements (system Python: PIL + numpy): heights from the 1.8 m figure, trunk girth per panel.

    py -3 -B Scripts/dojo/pines/measure_ref_v2.py [--debug DIR]

Task (pines v2, owner-approved method): heights come from the sheet's 1.8 m figure, not the old spec (2.5/4.5/7/4 m);
girth comes from the sheet per panel: trunk width at 1/4 of the tree height (base to apex) against the crown width,
and against the figure height. The judges flipped twice on girth, so the sheet is the only authority (P49).

Trunk width: on each of 7 rows around the 1/4-height row, start at the traced trunk centre and walk left and right
while the pixel is bark (colour distance > 28 from the background, not needle green, gaps of <= 2 px bridged: pale
bark plates sit close to the grey). The median over the rows is the width. The debug crops draw the measured span so
the number can be checked by eye (study 6.2: pixels, never eyeballing; then look).
Pine D: height = ground to apex (rock included, as the asset is measured); the girth row is at 1/4 of the TREE above
the trunk's entry into the rock.
Writes WorkFiles/dojo/build/pines/ref_measure_v2.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "Scripts" / "vegetation"))
import measure_tree as mt  # noqa: E402
import pines_trace as pt  # noqa: E402
import ref_panels as rp  # noqa: E402

OUT = ROOT / "WorkFiles" / "dojo" / "build" / "pines" / "ref_measure_v2.json"


def trunk_x_at(trace, y):
    P = np.asarray(trace, float)
    o = np.argsort(P[:, 1])
    return float(np.interp(y, P[o, 1], P[o, 0]))


def bark_run(arr, bg, x, y, max_px=80, gap=2):
    row = arr[y]
    d = np.linalg.norm(row - bg[None, :], axis=1)
    hue, sat, val = mt.hsv(row[None, :, :])
    green = (hue[0] >= 60) & (hue[0] <= 200) & (sat[0] > 0.18)
    bark = (d > 28) & ~green
    xi = int(round(x))
    # start on bark: nearest bark pixel within 4 px of the trace
    if not bark[xi]:
        for k in range(1, 5):
            if xi + k < len(bark) and bark[xi + k]:
                xi += k
                break
            if bark[xi - k]:
                xi -= k
                break
    ends = []
    for sgn in (-1, 1):
        k, miss, last = 0, 0, 0
        while k < max_px:
            k += 1
            j = xi + sgn * k
            if j < 0 or j >= len(bark):
                break
            if bark[j]:
                last = k
                miss = 0
            else:
                miss += 1
                if miss > gap:
                    break
        ends.append(xi + sgn * last)
    return ends[0], ends[1]


def measure_panel(sheet, bg, name):
    p = rp.PANELS[name]
    x0, y0, x1, y1 = p["box"]
    a = sheet.copy()
    for (ex0, ey0, ex1, ey1) in p.get("exclude", []):
        a[ey0:ey1, ex0:ex1] = bg
    crop = a[y0:y1, x0:x1]
    m = mt.masks(crop, None, bg=bg)
    fig_px = p["figure"][1] - p["figure"][0]
    pxm = fig_px / rp.FIGURE_M
    tree = (m["foliage"] | m["wood"]) & ~m["figure"]
    bx, by = p["base"]
    tree[by - y0:, :] = False
    ys = np.nonzero(tree.any(1))[0]
    apex = y0 + int(ys.min())
    ground = p["ground"] if p["pine"] == 4 else by
    tr = pt.TRACE[name]["trunk"]
    tree_h_px = by - apex
    yq = int(round(by - 0.25 * tree_h_px))
    widths, spans = [], []
    for dy in range(-3, 4):
        yy = yq + dy
        xc = trunk_x_at(tr, yy)
        l, r = bark_run(a, bg, xc, yy)
        widths.append(r - l + 1)
        spans.append((l, r, yy))
    w_px = float(np.median(widths))
    fol = m["foliage"].copy()
    fol[by - y0:, :] = False
    fxs = np.nonzero(fol.any(0))[0]
    crown_px = float(fxs.max() - fxs.min() + 1)
    return {"panel": name, "pine": p["pine"], "view": p["view"], "figure_px": fig_px, "px_per_m": round(pxm, 3),
            "apex_y": apex, "base_y": by, "ground_y": ground,
            "height_m": round((ground - apex) / pxm, 3), "tree_h_m": round(tree_h_px / pxm, 3),
            "crown_w_m": round(crown_px / pxm, 3),
            "trunk_row_y": yq, "trunk_w_px": w_px, "trunk_w_px_rows": widths,
            "trunk_w_m": round(w_px / pxm, 3),
            "trunk_over_crown": round(w_px / crown_px, 4),
            "trunk_over_figure": round(w_px / fig_px, 4),
            "spans": spans}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", default=str(ROOT / "WorkFiles" / "dojo" / "build" / "pines" / "v2work"))
    a = ap.parse_args()
    sheet = mt.load_rgb(str(ROOT / rp.SHEET))
    bg = mt.background_colour(sheet[20:60, 300:700])
    out = {}
    img = Image.open(ROOT / rp.SHEET).convert("RGB")
    d = ImageDraw.Draw(img)
    for name in rp.PANELS:
        r = measure_panel(sheet, bg, name)
        out[name] = r
        for (l, rr, yy) in r["spans"]:
            d.line([(l, yy), (rr, yy)], fill=(255, 0, 255), width=1)
        x0, y0, x1, y1 = rp.PANELS[name]["box"]
        d.line([(x0, r["apex_y"]), (x1, r["apex_y"])], fill=(0, 200, 255), width=1)
        print(f"{name}: H {r['height_m']} m (tree {r['tree_h_m']}), crown {r['crown_w_m']} m, trunk@1/4 "
              f"{r['trunk_w_m']} m ({r['trunk_w_px']} px, rows {r['trunk_w_px_rows']}), trunk/crown "
              f"{r['trunk_over_crown']}, trunk/figure {r['trunk_over_figure']}")
    # per pine summary (front panels for variant 1, 3/4 panels for variant 2)
    out["_by_variant"] = {}
    for v, (fp, sp) in pt.VARIANTS.items():
        out["_by_variant"][v] = {"panel": fp, "height_m": out[fp]["height_m"], "tree_h_m": out[fp]["tree_h_m"],
                                 "trunk_w_m": out[fp]["trunk_w_m"], "trunk_over_crown": out[fp]["trunk_over_crown"],
                                 "trunk_over_figure": out[fp]["trunk_over_figure"],
                                 "side_panel": sp, "side_trunk_w_m": out[sp]["trunk_w_m"]}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    dbg = Path(a.debug)
    dbg.mkdir(parents=True, exist_ok=True)
    img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
    img.save(dbg / "ref_girth_rows.png")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
