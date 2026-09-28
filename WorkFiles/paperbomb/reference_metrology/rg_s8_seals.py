# -*- coding: utf-8 -*-
"""STAGE 8 - the two seals, isolated on their own native components.
METROLOGY ONLY.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rg_lib as R  # noqa: E402

S1 = json.load(open(os.path.join(HERE, "rg_s1_silhouette.json"), encoding="utf-8"))
XL = S1['sides']['L']['b']; XR = S1['sides']['R']['b']
YT = S1['sides']['T']['b']; YB = S1['sides']['B']['b']
WPX = XR - XL; HPX = YB - YT
PPMM = S1['ppmm']; CARD_W = 70.0; CARD_H = S1['card_h_mm_from_aspect']


def mmx(x): return float((np.asarray(x, float) - XL) / WPX * CARD_W)
def mmy(y): return float((np.asarray(y, float) - YT) / HPX * CARD_H)
def fx(x): return float((np.asarray(x, float) - XL) / WPX)
def fy(y): return float((np.asarray(y, float) - YT) / HPX)
def p2mm(p): return float(p) / PPMM
def a2mm2(n): return float(n) / (PPMM * PPMM)


a, _ = R.read_stored(R.RG)
H, W = a.shape[:2]
lu = R.luma(a)
rex = a[..., 0] - .5 * (a[..., 1] + a[..., 2])
poly = np.array(S1['octagon_vertices_px'], float)
yy, xx = np.mgrid[0:H, 0:W]
inside = np.zeros((H, W), bool); n = len(poly); j = n - 1
px_ = xx + .5; py_ = yy + .5
for i in range(n):
    xi, yi = poly[i]; xj, yj = poly[j]
    inside ^= (((yi > py_) != (yj > py_)) &
               (px_ < (xj - xi) * (py_ - yi) / (yj - yi + 1e-12) + xi))
    j = i
tag = R.erode(inside, 1)
ps = tag & (rex < .22) & (lu > .80)
p_rex = float(np.median(rex[ps])); p_lu = float(np.median(lu[ps]))
r_rex = float(np.percentile(rex[tag], 99.5))
dkk = lu[tag]; i_lu = float(np.median(dkk[dkk < np.percentile(dkk, 6)]))
red = tag & (rex > .5 * (p_rex + r_rex))
black = tag & (lu < .5 * (p_lu + i_lu)) & ~red
ink = red | black

OUT = {}
for nm, (x0, x1, y0, y1) in (("seal_big", (18, 100, 470, 600)),
                             ("seal_small", (212, 272, 525, 605))):
    z = np.zeros((H, W), bool); z[y0:y1, x0:x1] = True
    m = red & z
    lab, comps = R.label(R.dilate(m, 2))
    main = m & (lab == comps[0]['label'])
    ys_, xs_ = np.nonzero(main)
    bx0, bx1 = int(xs_.min()), int(xs_.max()); by0, by1 = int(ys_.min()), int(ys_.max())
    sub_red = red[by0:by1 + 1, bx0:bx1 + 1]
    sub_ink = ink[by0:by1 + 1, bx0:bx1 + 1]
    rec = dict(
        outer_box_mm=[round(mmx(bx0), 3), round(mmx(bx1 + 1), 3),
                      round(mmy(by0), 3), round(mmy(by1 + 1), 3)],
        w_mm=round(mmx(bx1 + 1) - mmx(bx0), 3), h_mm=round(mmy(by1 + 1) - mmy(by0), 3),
        w_f=round(fx(bx1 + 1) - fx(bx0), 5), h_f=round(fy(by1 + 1) - fy(by0), 5),
        cx_mm=round(mmx(.5 * (bx0 + bx1 + 1)), 3), cy_mm=round(mmy(.5 * (by0 + by1 + 1)), 3),
        cx_f=round(fx(.5 * (bx0 + bx1 + 1)), 5), cy_f=round(fy(.5 * (by0 + by1 + 1)), 5),
        red_mm2=round(a2mm2(int(main.sum())), 2),
        red_fill_of_box=round(float(sub_red.mean()), 4),
        paper_fill_of_box=round(float((~sub_ink).mean()), 4),
    )
    # the solid panel: largest hole-filled red region eroded
    filled = R.fill_holes(main)
    inner = R.erode(filled, 3)
    if inner.any():
        iy, ix = np.nonzero(inner)
        rec['panel_box_mm'] = [round(mmx(ix.min()), 3), round(mmx(ix.max() + 1), 3),
                               round(mmy(iy.min()), 3), round(mmy(iy.max() + 1), 3)]
        rec['panel_w_mm'] = round(mmx(ix.max() + 1) - mmx(ix.min()), 3)
        rec['panel_h_mm'] = round(mmy(iy.max() + 1) - mmy(iy.min()), 3)
        pr = red[iy.min():iy.max() + 1, ix.min():ix.max() + 1]
        rec['panel_red_frac'] = round(float(pr.mean()), 4)
        rec['device_reversed_out'] = bool(pr.mean() > .55)
        rec['device_paper_mm2'] = round(a2mm2(int((~pr).sum())), 2)
    # rule thickness: first red run inward on 5 scan lines each way
    def runs(v):
        out = []; cur = 0
        for t in v:
            if t:
                cur += 1
            else:
                if cur:
                    out.append(cur)
                cur = 0
        if cur:
            out.append(cur)
        return out
    firsts = []
    for f in (.2, .35, .5, .65, .8):
        ym = int(by0 + f * (by1 - by0))
        rl = runs(red[ym, bx0:bx1 + 1])
        rr = runs(red[ym, bx0:bx1 + 1][::-1])
        if rl:
            firsts.append(rl[0])
        if rr:
            firsts.append(rr[0])
        xm = int(bx0 + f * (bx1 - bx0))
        ct = runs(red[by0:by1 + 1, xm])
        cb = runs(red[by0:by1 + 1, xm][::-1])
        if ct:
            firsts.append(ct[0])
        if cb:
            firsts.append(cb[0])
    rec['frame_rule_mm_median'] = round(p2mm(float(np.median(firsts))), 3)
    rec['frame_rule_mm_all'] = [round(p2mm(f), 2) for f in firsts]
    # gap between outer rule and panel
    gaps = []
    for f in (.35, .5, .65):
        ym = int(by0 + f * (by1 - by0))
        row = red[ym, bx0:bx1 + 1]
        g = runs(~row)
        if g:
            gaps.append(g[0])
    rec['outer_gap_mm'] = round(p2mm(float(np.median(gaps))), 3) if gaps else None
    OUT[nm] = rec

with open(os.path.join(HERE, "rg_s8_seals.json"), "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, ensure_ascii=False)
print(json.dumps(OUT, indent=1, ensure_ascii=False))
