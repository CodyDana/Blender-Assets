# -*- coding: utf-8 -*-
"""STAGE 2 - every content element of the real-glyph reference. METROLOGY ONLY.

Emits boxes, centroids, areas, the ring's geometry, the border rules and their
breaks, the corner ornaments, the columns, the seals, the lozenges and leaves.
All in tag fractions; millimetres are computed at the SINGLE uniform scale that
falls out of stage 1 (width pinned at 70 mm, height from the measured aspect).
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rg_lib as R  # noqa: E402

S1 = json.load(open(os.path.join(HERE, "rg_s1_silhouette.json"), encoding="utf-8"))
XL = S1['sides']['L']['b']
XR = S1['sides']['R']['b']
YT = S1['sides']['T']['b']
YB = S1['sides']['B']['b']
WPX = XR - XL
HPX = YB - YT
PPMM = S1['ppmm']
CARD_W = 70.0
CARD_H = S1['card_h_mm_from_aspect']

OUT = dict(_scale=dict(xL=XL, xR=XR, yT=YT, yB=YB, w_px=WPX, h_px=HPX,
                       ppmm=PPMM, card_w_mm=CARD_W, card_h_mm=CARD_H))


def fx(x):
    return (np.asarray(x, float) - XL) / WPX


def fy(y):
    return (np.asarray(y, float) - YT) / HPX


def mmx(x):
    return fx(x) * CARD_W


def mmy(y):
    return fy(y) * CARD_H


def px2mm(p):
    return float(p) / PPMM


def area_mm2(npx):
    return float(npx) / (PPMM * PPMM)


def box(sel_mask, name):
    ys, xs = np.nonzero(sel_mask)
    if len(xs) == 0:
        return dict(name=name, present=False)
    return dict(
        name=name, present=True, n_px=int(len(xs)),
        area_mm2=round(area_mm2(len(xs)), 3),
        x0_f=round(float(fx(xs.min())), 5), x1_f=round(float(fx(xs.max() + 1)), 5),
        y0_f=round(float(fy(ys.min())), 5), y1_f=round(float(fy(ys.max() + 1)), 5),
        x0_mm=round(float(mmx(xs.min())), 3), x1_mm=round(float(mmx(xs.max() + 1)), 3),
        y0_mm=round(float(mmy(ys.min())), 3), y1_mm=round(float(mmy(ys.max() + 1)), 3),
        w_mm=round(float(mmx(xs.max() + 1) - mmx(xs.min())), 3),
        h_mm=round(float(mmy(ys.max() + 1) - mmy(ys.min())), 3),
        cx_f=round(float(fx(xs.mean() + 0.5)), 5), cy_f=round(float(fy(ys.mean() + 0.5)), 5),
        cx_mm=round(float(mmx(xs.mean() + 0.5)), 3), cy_mm=round(float(mmy(ys.mean() + 0.5)), 3),
    )


def main():
    a, _ = R.read_stored(R.RG)
    H, W = a.shape[:2]
    lu = R.luma(a)
    rex = a[..., 0] - 0.5 * (a[..., 1] + a[..., 2])
    hue, sat, val = R.hsv(a)

    # tag interior mask (inside the octagon, 1 px in)
    P = np.array(S1['octagon_vertices_px'], float)
    yy, xx = np.mgrid[0:H, 0:W]
    inside = np.zeros((H, W), bool)
    n = len(P)
    j = n - 1
    px_ = xx + 0.5
    py_ = yy + 0.5
    for i in range(n):
        xi, yi = P[i]; xj, yj = P[j]
        cond = ((yi > py_) != (yj > py_)) & (px_ < (xj - xi) * (py_ - yi) / (yj - yi + 1e-12) + xi)
        inside ^= cond
        j = i
    tag = R.erode(inside, 1)

    # ---- paper level and classification ---------------------------------
    paper_sel = tag & (rex < 0.22) & (lu > 0.80)
    paper_rgb = np.array([float(np.median(a[..., c][paper_sel])) for c in range(3)])
    OUT['paper_stored_rgb'] = [round(v, 4) for v in paper_rgb]
    OUT['paper_hex'] = '#%02X%02X%02X' % tuple(int(round(v * 255)) for v in paper_rgb)
    ph, ps, pv = R.hsv(paper_rgb[None, None, :])
    OUT['paper_hsv'] = [round(float(ph[0, 0]), 2), round(float(ps[0, 0]), 4), round(float(pv[0, 0]), 4)]

    paper_rex = float(np.median(rex[paper_sel]))
    red_rex = float(np.percentile(rex[tag], 99.5))
    thr_red = 0.5 * (paper_rex + red_rex)
    paper_lu = float(np.median(lu[paper_sel]))
    dark = lu[tag]
    ink_lu = float(np.median(dark[dark < np.percentile(dark, 6)]))
    thr_ink = 0.5 * (paper_lu + ink_lu)
    OUT['thresholds'] = dict(paper_rex=round(paper_rex, 4), red_rex=round(red_rex, 4),
                             thr_red=round(thr_red, 4), paper_lu=round(paper_lu, 4),
                             ink_lu=round(ink_lu, 4), thr_ink=round(thr_ink, 4))

    red = tag & (rex > thr_red)
    black = tag & (lu < thr_ink) & ~red
    ink = red | black
    OUT['coverage'] = dict(tag_px=int(tag.sum()),
                           red_frac=round(float(red.sum()) / tag.sum(), 5),
                           black_frac=round(float(black.sum()) / tag.sum(), 5),
                           ink_frac=round(float(ink.sum()) / tag.sum(), 5),
                           black_over_red=round(float(black.sum()) / max(1, red.sum()), 4))

    # ---- BORDER RULES ----------------------------------------------------
    # profile of red occupancy as a function of distance from each tag edge
    rules = {}
    for side in ('L', 'R', 'T', 'B'):
        vert = side in ('L', 'R')
        if vert:
            lo = int(YT + 0.30 * HPX); hi = int(YT + 0.70 * HPX)
            prof = []
            for d in range(0, 40):
                x = int(round(XL + d)) if side == 'L' else int(round(XR - 1 - d))
                if 0 <= x < W:
                    prof.append(float(red[lo:hi, x].mean()))
                else:
                    prof.append(0.0)
        else:
            lo = int(XL + 0.30 * WPX); hi = int(XL + 0.70 * WPX)
            prof = []
            for d in range(0, 40):
                y = int(round(YT + d)) if side == 'T' else int(round(YB - 1 - d))
                if 0 <= y < H:
                    prof.append(float(red[y, lo:hi].mean()))
                else:
                    prof.append(0.0)
        prof = np.array(prof)
        peak = int(np.argmax(prof))
        # sub-pixel centroid of the peak band
        band = [peak]
        d = peak - 1
        while d >= 0 and prof[d] > 0.30 * prof[peak]:
            band.insert(0, d); d -= 1
        d = peak + 1
        while d < len(prof) and prof[d] > 0.30 * prof[peak]:
            band.append(d); d += 1
        wts = prof[band]
        cen = float(np.sum(np.array(band) * wts) / np.sum(wts))
        # FWHM
        half = 0.5 * prof[peak]
        lo_e = peak
        while lo_e > 0 and prof[lo_e] > half:
            lo_e -= 1
        hi_e = peak
        while hi_e < len(prof) - 1 and prof[hi_e] > half:
            hi_e += 1
        fw = (hi_e - lo_e)
        # any SECOND rule further in?
        far = prof[min(len(prof) - 1, band[-1] + 3):]
        rules[side] = dict(
            inset_px=round(cen, 3), inset_mm=round(px2mm(cen), 3),
            inset_f=round(cen / (WPX if vert else HPX), 5),
            peak_occupancy=round(float(prof[peak]), 4),
            fwhm_px=round(float(fw), 3), fwhm_mm=round(px2mm(fw), 3),
            band_px=[band[0], band[-1]],
            profile=[round(float(v), 3) for v in prof[:24]],
            second_peak=round(float(far.max()) if len(far) else 0.0, 4),
        )
    OUT['rules'] = rules

    # occupancy + break statistics ALONG each rule (band = the peak band)
    breaks = {}
    for side in ('L', 'R', 'T', 'B'):
        vert = side in ('L', 'R')
        b0, b1 = rules[side]['band_px']
        b0 = max(0, b0 - 1); b1 = b1 + 1
        # run the rule between the chamfer ends
        if vert:
            t0 = int(round(YT + 0.075 * HPX)); t1 = int(round(YB - 0.075 * HPX))
            occ = []
            for t in range(t0, t1):
                xs = [int(round(XL + d)) for d in range(b0, b1 + 1)] if side == 'L' \
                    else [int(round(XR - 1 - d)) for d in range(b0, b1 + 1)]
                xs = [x for x in xs if 0 <= x < W]
                occ.append(bool(red[t, xs].any()))
        else:
            t0 = int(round(XL + 0.16 * WPX)); t1 = int(round(XR - 0.16 * WPX))
            occ = []
            for t in range(t0, t1):
                ys_ = [int(round(YT + d)) for d in range(b0, b1 + 1)] if side == 'T' \
                    else [int(round(YB - 1 - d)) for d in range(b0, b1 + 1)]
                ys_ = [y for y in ys_ if 0 <= y < H]
                occ.append(bool(red[ys_, t].any()))
        occ = np.array(occ)
        runs = []
        cur = 0
        for v in occ:
            if not v:
                cur += 1
            else:
                if cur:
                    runs.append(cur)
                cur = 0
        if cur:
            runs.append(cur)
        breaks[side] = dict(
            length_px=len(occ), occupancy=round(float(occ.mean()), 4),
            zero_ink_frac=round(float(1 - occ.mean()), 4),
            n_breaks=len(runs),
            longest_break_px=int(max(runs)) if runs else 0,
            longest_break_mm=round(px2mm(max(runs)) if runs else 0.0, 3),
            break_lengths_px=sorted(runs, reverse=True)[:12],
        )
    OUT['rule_breaks'] = breaks

    # rule THINNING: per-station swept width, to prove it thins but never lifts
    thin = {}
    for side in ('L', 'R', 'T', 'B'):
        vert = side in ('L', 'R')
        b0, b1 = rules[side]['band_px']
        b0 = max(0, b0 - 2); b1 = b1 + 2
        widths = []
        if vert:
            t0 = int(round(YT + 0.075 * HPX)); t1 = int(round(YB - 0.075 * HPX))
            for t in range(t0, t1):
                if side == 'L':
                    seg = np.array([rex[t, int(round(XL + d))] for d in range(b0, b1 + 1)])
                else:
                    seg = np.array([rex[t, int(round(XR - 1 - d))] for d in range(b0, b1 + 1)])
                widths.append(float(np.clip((seg - paper_rex) / (red_rex - paper_rex), 0, 1).sum()))
        else:
            t0 = int(round(XL + 0.16 * WPX)); t1 = int(round(XR - 0.16 * WPX))
            for t in range(t0, t1):
                if side == 'T':
                    seg = np.array([rex[int(round(YT + d)), t] for d in range(b0, b1 + 1)])
                else:
                    seg = np.array([rex[int(round(YB - 1 - d)), t] for d in range(b0, b1 + 1)])
                widths.append(float(np.clip((seg - paper_rex) / (red_rex - paper_rex), 0, 1).sum()))
        wv = np.array(widths)
        thin[side] = dict(
            mean_mm=round(px2mm(wv.mean()), 4), median_mm=round(px2mm(np.median(wv)), 4),
            p05_mm=round(px2mm(np.percentile(wv, 5)), 4),
            p95_mm=round(px2mm(np.percentile(wv, 95)), 4),
            min_mm=round(px2mm(wv.min()), 4), max_mm=round(px2mm(wv.max()), 4),
            frac_below_0p10mm=round(float((wv < 0.10 * PPMM).mean()), 4),
            frac_below_0p05mm=round(float((wv < 0.05 * PPMM).mean()), 4),
            longest_run_below_0p10mm_mm=0.0,
        )
        cur = 0; best = 0
        for v in wv:
            if v < 0.10 * PPMM:
                cur += 1; best = max(best, cur)
            else:
                cur = 0
        thin[side]['longest_run_below_0p10mm_mm'] = round(px2mm(best), 3)
    OUT['rule_thinning'] = thin

    # rule rectangle (frame) from the four insets
    fl = XL + rules['L']['inset_px']; fr = XR - 1 - rules['R']['inset_px']
    ft = YT + rules['T']['inset_px']; fb = YB - 1 - rules['B']['inset_px']
    OUT['rule_frame'] = dict(
        x0_mm=round(float(mmx(fl)), 3), x1_mm=round(float(mmx(fr)), 3),
        y0_mm=round(float(mmy(ft)), 3), y1_mm=round(float(mmy(fb)), 3),
        w_mm=round(float(mmx(fr) - mmx(fl)), 3), h_mm=round(float(mmy(fb) - mmy(ft)), 3),
        cx_mm=round(float(mmx(0.5 * (fl + fr))), 3), cy_mm=round(float(mmy(0.5 * (ft + fb))), 3),
        w_f=round(float(fx(fr) - fx(fl)), 5), h_f=round(float(fy(fb) - fy(ft)), 5))

    # ---- CORNER ORNAMENTS -------------------------------------------------
    # ink within a 14 mm x 14 mm square at each rule-frame corner, split into
    # inboard-of-frame and outboard-of-frame, red and black.
    corn = {}
    S = 14.0  # mm box
    sx = S / CARD_W * WPX
    sy = S / CARD_H * HPX
    for nm, cx0, cy0, dirx, diry in (('TL', fl, ft, +1, +1), ('TR', fr, ft, -1, +1),
                                     ('BL', fl, fb, +1, -1), ('BR', fr, fb, -1, -1)):
        x0 = int(round(min(cx0, cx0 + dirx * sx) - (0 if dirx > 0 else 0)))
        x1 = int(round(max(cx0, cx0 + dirx * sx)))
        y0 = int(round(min(cy0, cy0 + diry * sy)))
        y1 = int(round(max(cy0, cy0 + diry * sy)))
        # extend 4 mm outboard of the frame as well
        ob = 4.0 / CARD_W * WPX
        if dirx > 0:
            x0 = int(round(cx0 - ob))
        else:
            x1 = int(round(cx0 + ob))
        if diry > 0:
            y0 = int(round(cy0 - ob))
        else:
            y1 = int(round(cy0 + ob))
        sub = (slice(max(0, y0), min(H, y1)), slice(max(0, x0), min(W, x1)))
        zr = red[sub]; zb = black[sub]
        Y, X = np.mgrid[sub[0].start:sub[0].stop, sub[1].start:sub[1].stop]
        outb = ((X < fl) | (X > fr) | (Y < ft) | (Y > fb))
        # "outboard" ink: strictly outside the rule frame rectangle by >0.6 px
        outb2 = ((X < fl - 0.6) | (X > fr + 0.6) | (Y < ft - 0.6) | (Y > fb + 0.6))
        corn[nm] = dict(
            red_mm2=round(area_mm2(zr.sum()), 3),
            black_mm2=round(area_mm2(zb.sum()), 3),
            red_outboard_mm2=round(area_mm2((zr & outb2).sum()), 3),
            black_outboard_mm2=round(area_mm2((zb & outb2).sum()), 3),
            darkest_lum=round(float(lu[sub][zr | zb].min()) if (zr | zb).any() else 1.0, 4),
            dark_knot_mm2=round(area_mm2(((lu[sub] < 0.30) & (zr | zb)).sum()), 3),
            n_components=0,
        )
        lab, comps = R.label(zr | zb)
        corn[nm]['n_components'] = len([c for c in comps if c['n'] >= 3])
        corn[nm]['component_areas_mm2'] = [round(area_mm2(c['n']), 3) for c in comps[:6]]
        # outboard reach: max distance outside the frame
        if (zr | zb).any():
            m = zr | zb
            dd = np.maximum.reduce([fl - X, X - fr, ft - Y, Y - fb])
            corn[nm]['max_outboard_px'] = round(float(dd[m].max()), 3)
            corn[nm]['max_outboard_mm'] = round(px2mm(float(dd[m].max())), 3)
    OUT['corner_ornaments'] = corn

    # ---- ALL INK CLUSTERS (the honest inventory) --------------------------
    # exclude the rule frame band so the rules do not weld everything together
    fr_band = np.zeros((H, W), bool)
    for side, (cen, vert) in (('L', (fl, True)), ('R', (fr, True)), ('T', (ft, False)), ('B', (fb, False))):
        if vert:
            x = int(round(cen))
            fr_band[:, max(0, x - 3):x + 4] = True
        else:
            y = int(round(cen))
            fr_band[max(0, y - 3):y + 4, :] = True
    content = ink & ~fr_band
    lab, comps = R.label(R.dilate(content, 1))
    inv = []
    for c in comps:
        sel = content & (lab == c['label'])
        if sel.sum() < 6:
            continue
        b = box(sel, 'cluster')
        b['red_mm2'] = round(area_mm2((sel & red).sum()), 3)
        b['black_mm2'] = round(area_mm2((sel & black).sum()), 3)
        inv.append(b)
    inv.sort(key=lambda d: -d['area_mm2'])
    OUT['ink_inventory'] = inv[:40]

    with open(os.path.join(HERE, "rg_s2_elements.json"), "w", encoding="utf-8") as fh:
        json.dump(OUT, fh, indent=1, ensure_ascii=False)

    vis = a.copy()
    vis[red] = [1.0, 0.0, 1.0]
    vis[black & ~red] = [0.0, 0.4, 1.0]
    R.save_debug(vis, "s2_classes", scale=2)
    print(json.dumps({k: OUT[k] for k in ('paper_stored_rgb', 'paper_hex', 'paper_hsv',
                                          'thresholds', 'coverage', 'rules', 'rule_breaks',
                                          'rule_thinning', 'rule_frame', 'corner_ornaments')},
                     indent=1))
    print("INVENTORY")
    for b in inv[:34]:
        print("  %7.2f mm2  x %6.2f-%6.2f  y %7.2f-%7.2f  c(%6.2f,%7.2f)  R%6.2f B%6.2f"
              % (b['area_mm2'], b['x0_mm'], b['x1_mm'], b['y0_mm'], b['y1_mm'],
                 b['cx_mm'], b['cy_mm'], b['red_mm2'], b['black_mm2']))


main()
