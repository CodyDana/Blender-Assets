# -*- coding: utf-8 -*-
"""STAGE 7 - corrections: ink-aware grain, the bottom chain split by class,
tight seal boxes, and the top rule's red-to-dark transition. METROLOGY ONLY.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rg_lib as R  # noqa: E402

S1 = json.load(open(os.path.join(HERE, "rg_s1_silhouette.json"), encoding="utf-8"))
S3 = json.load(open(os.path.join(HERE, "rg_s3_geometry.json"), encoding="utf-8"))
XL = S1['sides']['L']['b']; XR = S1['sides']['R']['b']
YT = S1['sides']['T']['b']; YB = S1['sides']['B']['b']
WPX = XR - XL; HPX = YB - YT
PPMM = S1['ppmm']; CARD_W = 70.0; CARD_H = S1['card_h_mm_from_aspect']
OUT = {}


def fxv(x): return (np.asarray(x, float) - XL) / WPX
def fyv(y): return (np.asarray(y, float) - YT) / HPX
def mmx(x): return float(fxv(x) * CARD_W)
def mmy(y): return float(fyv(y) * CARD_H)
def p2mm(p): return float(p) / PPMM
def a2mm2(n): return float(n) / (PPMM * PPMM)


def boxof(sel, nm=""):
    ys, xs = np.nonzero(sel)
    if len(xs) == 0:
        return dict(present=False, name=nm)
    return dict(name=nm, present=True, area_mm2=round(a2mm2(len(xs)), 3),
                x0_mm=round(mmx(xs.min()), 3), x1_mm=round(mmx(xs.max() + 1), 3),
                y0_mm=round(mmy(ys.min()), 3), y1_mm=round(mmy(ys.max() + 1), 3),
                w_mm=round(mmx(xs.max() + 1) - mmx(xs.min()), 3),
                h_mm=round(mmy(ys.max() + 1) - mmy(ys.min()), 3),
                w_f=round(float(fxv(xs.max() + 1) - fxv(xs.min())), 5),
                h_f=round(float(fyv(ys.max() + 1) - fyv(ys.min())), 5),
                cx_mm=round(mmx(xs.mean() + .5), 3), cy_mm=round(mmy(ys.mean() + .5), 3),
                cx_f=round(float(fxv(xs.mean() + .5)), 5), cy_f=round(float(fyv(ys.mean() + .5)), 5))


def wblur(img, wgt, r):
    k = 2 * r + 1

    def bs(v):
        p = np.pad(v, ((r, r), (r, r)), mode='reflect')
        cs = np.pad(np.cumsum(np.cumsum(p, 0), 1), ((1, 0), (1, 0)))
        h2, w2 = v.shape
        return (cs[k:k + h2, k:k + w2] - cs[0:h2, k:k + w2]
                - cs[k:k + h2, 0:w2] + cs[0:h2, 0:w2])
    return bs(img * wgt) / np.maximum(bs(wgt), 1e-6)


def main():
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
    alpha_red = np.clip((rex - p_rex) / (r_rex - p_rex), 0, 1)
    alpha_ink = np.clip((p_lu - lu) / (p_lu - i_lu), 0, 1)
    alpha_any = np.maximum(alpha_red, alpha_ink)

    fl = XL + S3['rules']['L']['inset_px']; fr = XR - 1 - S3['rules']['R']['inset_px']
    ft = YT + S3['rules']['T']['inset_px']; fb = YB - 1 - S3['rules']['B']['inset_px']

    def zm(x0f, x1f, y0f, y1f):
        z = np.zeros((H, W), bool)
        z[int(YT + y0f * HPX):int(YT + y1f * HPX), int(XL + x0f * WPX):int(XL + x1f * WPX)] = True
        return z

    # ------------------------------------------------- INK-AWARE GRAIN, MOTTLE
    clean = tag & ~R.dilate(ink, 4)
    cen = zm(.12, .88, .10, .90)
    base = clean & cen
    wgt = clean.astype(float)
    lo4 = wblur(lu * clean, wgt, 4)
    hp = (lu - lo4)
    g = hp[base]
    OUT['grain'] = dict(
        amplitude_pct=round(100 * float(g.std()) / p_lu, 3),
        amplitude_p05_p95_pct=round(100 * float(np.percentile(g, 95) - np.percentile(g, 5)) / p_lu, 3),
        paper_p05_p95_pct=round(100 * float(np.percentile(lu[base], 95) - np.percentile(lu[base], 5)) / p_lu, 3),
    )

    def ac(axis, nl=8):
        vals = []
        rng = range(int(YT + .15 * HPX), int(YT + .85 * HPX), 2) if axis == 0 \
            else range(int(XL + .15 * WPX), int(XL + .85 * WPX), 2)
        for t in rng:
            line = hp[t] if axis == 0 else hp[:, t]
            msk = base[t] if axis == 0 else base[:, t]
            v = line[msk]
            if len(v) < 40:
                continue
            v = v - v.mean(); d = float((v * v).mean())
            if d <= 0:
                continue
            vals.append([float((v[:-k] * v[k:]).mean()) / d for k in range(1, nl + 1)])
        return np.array(vals).mean(0) if vals else np.zeros(nl)
    ax = ac(0); ay = ac(1)

    def clen(arr):
        prev = 1.0
        for k, v in enumerate(arr, start=1):
            if v < math.e ** -1:
                return k - 1 + (prev - math.e ** -1) / max(prev - v, 1e-9)
            prev = v
        return float(len(arr))
    OUT['grain'].update(acorr_x=[round(float(v), 4) for v in ax],
                        acorr_y=[round(float(v), 4) for v in ay],
                        cell_x_mm=round(clen(ax) / PPMM, 4), cell_y_mm=round(clen(ay) / PPMM, 4),
                        anisotropy=round(max(clen(ax), clen(ay)) / max(1e-6, min(clen(ax), clen(ay))), 3),
                        nyquist_cell_mm=round(2.0 / PPMM, 4),
                        note="cell at or under 0.51 mm is unresolvable here; see HR_subpixel_character")
    b1 = wblur(lu * clean, wgt, 2); b2 = wblur(lu * clean, wgt, 6)
    b3 = wblur(lu * clean, wgt, 18); b4 = wblur(lu * clean, wgt, 40)
    OUT['mottle'] = dict(
        band_0p5_1p5mm_pct=round(100 * float((lu - b1)[base].std()) / p_lu, 3),
        band_1_3mm_pct=round(100 * float((b1 - b2)[base].std()) / p_lu, 3),
        band_3_10mm_pct=round(100 * float((b2 - b3)[base].std()) / p_lu, 3),
        band_10_20mm_pct=round(100 * float((b3 - b4)[base].std()) / p_lu, 3),
    )

    # -------------------------------------------- BOTTOM CHAIN, SPLIT BY CLASS
    xc = XL + .5 * WPX
    hw = 3.4 / CARD_W * WPX
    items = []
    for cls, nm in ((red, 'red'), (black, 'black')):
        strip = np.zeros((H, W), bool)
        strip[int(YT + .655 * HPX):H, int(xc - hw):int(xc + hw)] = True
        m = cls & strip
        lab, comps = R.label(m)          # NATIVE connectivity, no dilation
        for c in comps:
            s = m & (lab == c['label'])
            if a2mm2(int(s.sum())) < .2:
                continue
            b = boxof(s, nm)
            b['kind'] = nm
            if b['h_mm'] < 12 and b['w_mm'] < 8:
                items.append(b)
    items.sort(key=lambda b: b['cy_mm'])
    OUT['centreline_chain'] = items
    # the rule's own gap either side of the black diamond
    yb_ = int(round(fb))
    rowa = alpha_any[max(0, yb_ - 1):yb_ + 2, :].max(0)
    dia = [b for b in items if b['kind'] == 'black' and b['cy_f'] > .93]
    if dia:
        d0 = dia[0]
        x0 = int(round(XL + (d0['x0_mm'] / CARD_W) * WPX))
        x1 = int(round(XL + (d0['x1_mm'] / CARD_W) * WPX))
        gl = 0; x = x0 - 1
        while x > 0 and rowa[x] < .10:
            gl += 1; x -= 1
        gr = 0; x = x1 + 1
        while x < W - 1 and rowa[x] < .10:
            gr += 1; x += 1
        OUT['bottom_rule_gap_each_side_of_diamond_mm'] = [round(p2mm(gl), 3), round(p2mm(gr), 3)]

    # ------------------------------------------------------ SEALS, TIGHT ZONES
    def seal(x0f, x1f, y0f, y1f, nm):
        m = ink & zm(x0f, x1f, y0f, y1f)
        lab, comps = R.label(R.dilate(m, 2))
        main = m & (lab == comps[0]['label'])
        b = boxof(main, nm)
        ys_, xs_ = np.nonzero(main)
        x0, x1 = int(xs_.min()), int(xs_.max()); y0, y1 = int(ys_.min()), int(ys_.max())
        b['red_fill_frac'] = round(float(red[y0:y1 + 1, x0:x1 + 1].mean()), 4)
        iy0 = y0 + int(.25 * (y1 - y0)); iy1 = y1 - int(.25 * (y1 - y0))
        ix0 = x0 + int(.25 * (x1 - x0)); ix1 = x1 - int(.25 * (x1 - x0))
        b['inner50_red_frac'] = round(float(red[iy0:iy1, ix0:ix1].mean()), 4)
        b['inner50_paper_frac'] = round(float((~ink)[iy0:iy1, ix0:ix1].mean()), 4)
        b['device_reversed_out'] = bool(b['inner50_red_frac'] > .5)

        def runs_of(v):
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
            return [round(p2mm(r), 3) for r in out]
        scans = {}
        for f in (.25, .5, .75):
            ym = int(y0 + f * (y1 - y0))
            scans['row_%d' % int(f * 100)] = dict(red=runs_of(red[ym, x0:x1 + 1]),
                                                  gap=runs_of(~ink[ym, x0:x1 + 1]))
        for f in (.25, .5, .75):
            xm = int(x0 + f * (x1 - x0))
            scans['col_%d' % int(f * 100)] = dict(red=runs_of(red[y0:y1 + 1, xm]),
                                                  gap=runs_of(~ink[y0:y1 + 1, xm]))
        b['scans'] = scans
        b['frame_rule_mm'] = scans['row_50']['red'][0] if scans['row_50']['red'] else None
        return b
    OUT['seal_big'] = seal(.05, .36, .745, .925, "seal_big")
    OUT['seal_small'] = seal(.75, .98, .825, .955, "seal_small")

    # ------------------------------------------- TOP RULE: RED vs DARK SECTION
    rr = {}
    for side in ('T', 'B', 'L', 'R'):
        vert = side in ('L', 'R')
        b0, b1 = S3['rules'][side]['band_px']
        b0 = max(0, b0 - 2); b1 = b1 + 2
        if vert:
            t0 = int(round(YT + .075 * HPX)); t1 = int(round(YB - .075 * HPX))
            cols = [int(round(XL + d)) for d in range(b0, b1 + 1)] if side == 'L' \
                else [int(round(XR - 1 - d)) for d in range(b0, b1 + 1)]
            ar = alpha_red[t0:t1][:, cols]; aa_ = alpha_any[t0:t1][:, cols]
        else:
            t0 = int(round(XL + .16 * WPX)); t1 = int(round(XR - .16 * WPX))
            rws = [int(round(YT + d)) for d in range(b0, b1 + 1)] if side == 'T' \
                else [int(round(YB - 1 - d)) for d in range(b0, b1 + 1)]
            ar = alpha_red[rws, t0:t1].T; aa_ = alpha_any[rws, t0:t1].T
        inkw = aa_.sum(1); redw = ar.sum(1)
        share = redw / np.maximum(inkw, 1e-6)
        present = aa_.max(1) >= .10
        dark = present & (share < .35)
        runs = []; cur = 0
        for v in dark:
            if v:
                cur += 1
            else:
                if cur:
                    runs.append(cur)
                cur = 0
        if cur:
            runs.append(cur)
        rr[side] = dict(length_mm=round(p2mm(len(inkw)), 2),
                        red_share_median=round(float(np.median(share[present])), 4),
                        frac_dark_ink=round(float(dark.sum()) / max(1, present.sum()), 4),
                        longest_dark_run_mm=round(p2mm(max(runs)) if runs else 0., 3),
                        n_dark_runs=len(runs))
    OUT['rule_ink_colour'] = rr

    with open(os.path.join(HERE, "rg_s7_fix.json"), "w", encoding="utf-8") as fh:
        json.dump(OUT, fh, indent=1, ensure_ascii=False)
    print(json.dumps(OUT, indent=1, ensure_ascii=False))


main()
