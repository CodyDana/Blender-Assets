# -*- coding: utf-8 -*-
"""STAGE 3 - ring, centre glyph, columns, seals, lozenges, flame, rules, corners.
METROLOGY ONLY.  Real-glyph reference is the authority.
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
XL = S1['sides']['L']['b']; XR = S1['sides']['R']['b']
YT = S1['sides']['T']['b']; YB = S1['sides']['B']['b']
WPX = XR - XL; HPX = YB - YT
PPMM = S1['ppmm']
CARD_W = 70.0
CARD_H = S1['card_h_mm_from_aspect']
OUT = {}


def fxv(x): return (np.asarray(x, float) - XL) / WPX
def fyv(y): return (np.asarray(y, float) - YT) / HPX
def mmx(x): return float(fxv(x) * CARD_W)
def mmy(y): return float(fyv(y) * CARD_H)
def p2mm(p): return float(p) / PPMM
def a2mm2(n): return float(n) / (PPMM * PPMM)


def boxof(sel, tagname=""):
    ys, xs = np.nonzero(sel)
    if len(xs) == 0:
        return dict(present=False, name=tagname)
    return dict(name=tagname, present=True, n_px=int(len(xs)), area_mm2=round(a2mm2(len(xs)), 3),
                x0_f=round(float(fxv(xs.min())), 5), x1_f=round(float(fxv(xs.max() + 1)), 5),
                y0_f=round(float(fyv(ys.min())), 5), y1_f=round(float(fyv(ys.max() + 1)), 5),
                x0_mm=round(mmx(xs.min()), 3), x1_mm=round(mmx(xs.max() + 1), 3),
                y0_mm=round(mmy(ys.min()), 3), y1_mm=round(mmy(ys.max() + 1), 3),
                w_mm=round(mmx(xs.max() + 1) - mmx(xs.min()), 3),
                h_mm=round(mmy(ys.max() + 1) - mmy(ys.min()), 3),
                w_f=round(float(fxv(xs.max() + 1) - fxv(xs.min())), 5),
                h_f=round(float(fyv(ys.max() + 1) - fyv(ys.min())), 5),
                cx_f=round(float(fxv(xs.mean() + .5)), 5), cy_f=round(float(fyv(ys.mean() + .5)), 5),
                cx_mm=round(mmx(xs.mean() + .5), 3), cy_mm=round(mmy(ys.mean() + .5), 3))


def main():
    a, _ = R.read_stored(R.RG)
    H, W = a.shape[:2]
    lu = R.luma(a)
    rex = a[..., 0] - 0.5 * (a[..., 1] + a[..., 2])

    P = np.array(S1['octagon_vertices_px'], float)
    yy, xx = np.mgrid[0:H, 0:W]
    inside = np.zeros((H, W), bool)
    n = len(P); j = n - 1
    px_ = xx + .5; py_ = yy + .5
    for i in range(n):
        xi, yi = P[i]; xj, yj = P[j]
        inside ^= (((yi > py_) != (yj > py_)) &
                   (px_ < (xj - xi) * (py_ - yi) / (yj - yi + 1e-12) + xi))
        j = i
    tag = R.erode(inside, 1)

    paper_sel = tag & (rex < 0.22) & (lu > 0.80)
    paper_rex = float(np.median(rex[paper_sel]))
    paper_lu = float(np.median(lu[paper_sel]))
    red_rex = float(np.percentile(rex[tag], 99.5))
    dk = lu[tag]
    ink_lu = float(np.median(dk[dk < np.percentile(dk, 6)]))
    thr_red = .5 * (paper_rex + red_rex)
    thr_ink = .5 * (paper_lu + ink_lu)

    red = tag & (rex > thr_red)
    black = tag & (lu < thr_ink) & ~red
    ink = red | black
    # continuous alphas
    alpha_red = np.clip((rex - paper_rex) / (red_rex - paper_rex), 0, 1)
    alpha_ink = np.clip((paper_lu - lu) / (paper_lu - ink_lu), 0, 1)
    alpha_any = np.maximum(alpha_red, alpha_ink)

    # =================================================================== RULES
    # measured on INK (red OR black): the top rule's centre section is drawn in
    # a DARK, desaturated ink, so a red-only classifier reports a 20 mm gap that
    # a photograph does not show.
    rules = {}
    for side in ('L', 'R', 'T', 'B'):
        vert = side in ('L', 'R')
        if vert:
            lo = int(YT + .30 * HPX); hi = int(YT + .70 * HPX)
            prof = np.array([float(alpha_any[lo:hi, int(round(XL + d if side == 'L' else XR - 1 - d))].mean())
                             for d in range(40)])
        else:
            lo = int(XL + .30 * WPX); hi = int(XL + .70 * WPX)
            prof = np.array([float(alpha_any[int(round(YT + d if side == 'T' else YB - 1 - d)), lo:hi].mean())
                             for d in range(40)])
        peak = int(np.argmax(prof))
        band = [peak]
        d = peak - 1
        while d >= 0 and prof[d] > .30 * prof[peak]:
            band.insert(0, d); d -= 1
        d = peak + 1
        while d < len(prof) and prof[d] > .30 * prof[peak]:
            band.append(d); d += 1
        cen = float(np.sum(np.array(band) * prof[band]) / np.sum(prof[band]))
        far = prof[min(39, band[-1] + 3):]
        rules[side] = dict(inset_px=round(cen, 3), inset_mm=round(p2mm(cen), 3),
                           inset_f=round(cen / (WPX if vert else HPX), 5),
                           peak_alpha=round(float(prof[peak]), 4),
                           band_px=[band[0], band[-1]],
                           second_peak_alpha=round(float(far.max()) if len(far) else 0., 4),
                           profile=[round(float(v), 3) for v in prof[:34]])
    OUT['rules'] = rules

    fl = XL + rules['L']['inset_px']; fr = XR - 1 - rules['R']['inset_px']
    ft = YT + rules['T']['inset_px']; fb = YB - 1 - rules['B']['inset_px']
    OUT['rule_frame'] = dict(x0_mm=round(mmx(fl), 3), x1_mm=round(mmx(fr), 3),
                             y0_mm=round(mmy(ft), 3), y1_mm=round(mmy(fb), 3),
                             w_mm=round(mmx(fr) - mmx(fl), 3), h_mm=round(mmy(fb) - mmy(ft), 3),
                             w_f=round(float(fxv(fr) - fxv(fl)), 5), h_f=round(float(fyv(fb) - fyv(ft)), 5),
                             cx_mm=round(mmx(.5 * (fl + fr)), 3), cy_mm=round(mmy(.5 * (ft + fb)), 3),
                             cx_f=round(float(fxv(.5 * (fl + fr))), 5), cy_f=round(float(fyv(.5 * (ft + fb))), 5))

    # swept width + continuity along each rule, on INK alpha
    cont = {}
    for side in ('L', 'R', 'T', 'B'):
        vert = side in ('L', 'R')
        b0, b1 = rules[side]['band_px']
        b0 = max(0, b0 - 2); b1 = b1 + 2
        if vert:
            t0 = int(round(YT + .075 * HPX)); t1 = int(round(YB - .075 * HPX))
            cols = [int(round(XL + d)) for d in range(b0, b1 + 1)] if side == 'L' \
                else [int(round(XR - 1 - d)) for d in range(b0, b1 + 1)]
            seg = alpha_any[t0:t1][:, cols]
            segr = alpha_red[t0:t1][:, cols]
        else:
            t0 = int(round(XL + .16 * WPX)); t1 = int(round(XR - .16 * WPX))
            rws = [int(round(YT + d)) for d in range(b0, b1 + 1)] if side == 'T' \
                else [int(round(YB - 1 - d)) for d in range(b0, b1 + 1)]
            seg = alpha_any[rws, t0:t1].T
            segr = alpha_red[rws, t0:t1].T
        wid = seg.sum(1)            # swept alpha width in px
        peakalpha = seg.max(1)
        redfrac = segr.sum(1) / np.maximum(wid, 1e-6)
        st = {}
        for thr, key in ((0.10, 'a10'), (0.25, 'a25'), (0.50, 'a50')):
            oc = peakalpha >= thr
            runs = []; cur = 0
            for v in oc:
                if not v:
                    cur += 1
                else:
                    if cur: runs.append(cur)
                    cur = 0
            if cur: runs.append(cur)
            st[key] = dict(occupancy=round(float(oc.mean()), 4),
                           zero_ink_frac=round(float(1 - oc.mean()), 4),
                           n_breaks=len(runs),
                           longest_break_mm=round(p2mm(max(runs)) if runs else 0., 3),
                           breaks_mm=[round(p2mm(r), 2) for r in sorted(runs, reverse=True)[:10]])
        cont[side] = dict(
            length_mm=round(p2mm(len(wid)), 2),
            width_mean_mm=round(p2mm(wid.mean()), 4), width_median_mm=round(p2mm(np.median(wid)), 4),
            width_p05_mm=round(p2mm(np.percentile(wid, 5)), 4),
            width_p95_mm=round(p2mm(np.percentile(wid, 95)), 4),
            width_min_mm=round(p2mm(wid.min()), 4), width_max_mm=round(p2mm(wid.max()), 4),
            width_cv=round(float(wid.std() / max(wid.mean(), 1e-6)), 4),
            red_fraction_of_stroke=round(float(np.median(redfrac)), 4),
            red_fraction_p10=round(float(np.percentile(redfrac, 10)), 4),
            continuity=st)
        cont[side].update(st)
    OUT['rule_continuity'] = cont

    # =========================================================== CORNER ORNAMENT
    corn = {}
    BOX = 9.0
    for nm, cx0, cy0, dx, dy in (('TL', fl, ft, +1, +1), ('TR', fr, ft, -1, +1),
                                 ('BL', fl, fb, +1, -1), ('BR', fr, fb, -1, -1)):
        sx = BOX / CARD_W * WPX; sy = BOX / CARD_H * HPX
        ob = 3.5 / CARD_W * WPX; oby = 3.5 / CARD_H * HPX
        x0 = int(round(cx0 - ob)) if dx > 0 else int(round(cx0 - sx))
        x1 = int(round(cx0 + sx)) if dx > 0 else int(round(cx0 + ob))
        y0 = int(round(cy0 - oby)) if dy > 0 else int(round(cy0 - sy))
        y1 = int(round(cy0 + sy)) if dy > 0 else int(round(cy0 + oby))
        sl = (slice(max(0, y0), min(H, y1)), slice(max(0, x0), min(W, x1)))
        Y, X = np.mgrid[sl[0].start:sl[0].stop, sl[1].start:sl[1].stop]
        zr = red[sl]; zb = black[sl]; zi = zr | zb
        outb = (X < fl - .6) | (X > fr + .6) | (Y < ft - .6) | (Y > fb + .6)
        lab, comps = R.label(R.dilate(zi, 1))
        big = [c for c in comps if (zi & (lab == c['label'])).sum() >= 3]
        dd = np.maximum.reduce([fl - X, X - fr, ft - Y, Y - fb])
        rec = dict(box_mm=[round(mmx(sl[1].start), 2), round(mmx(sl[1].stop), 2),
                           round(mmy(sl[0].start), 2), round(mmy(sl[0].stop), 2)],
                   ink_mm2=round(a2mm2(zi.sum()), 3),
                   red_mm2=round(a2mm2(zr.sum()), 3), black_mm2=round(a2mm2(zb.sum()), 3),
                   black_share=round(float(zb.sum()) / max(1, zi.sum()), 4),
                   outboard_ink_mm2=round(a2mm2((zi & outb).sum()), 3),
                   outboard_red_mm2=round(a2mm2((zr & outb).sum()), 3),
                   outboard_black_mm2=round(a2mm2((zb & outb).sum()), 3),
                   max_outboard_mm=round(p2mm(float(dd[zi].max())) if zi.any() else 0., 3),
                   n_components=len(big),
                   component_mm2=[round(a2mm2(int((zi & (lab == c['label'])).sum())), 3) for c in big[:6]],
                   darkest_luma=round(float(lu[sl][zi].min()) if zi.any() else 1., 4),
                   pool_mm2=round(a2mm2(((lu[sl] < .35) & zi).sum()), 3),
                   mean_luma=round(float(lu[sl][zi].mean()) if zi.any() else 1., 4))
        corn[nm] = rec
    OUT['corner_ornaments'] = corn

    # ======================================================================= RING
    ring_zone = np.zeros((H, W), bool)
    ring_zone[int(YT + .22 * HPX):int(YT + .70 * HPX), int(fl + 4):int(fr - 3)] = True
    rr = red & ring_zone
    lab, comps = R.label(R.dilate(rr, 1))
    ringm = rr & (lab == comps[0]['label'])
    ys, xs = np.nonzero(ringm)
    cx, cy = xs.mean(), ys.mean()
    for _ in range(8):
        r = np.hypot(xs - cx, ys - cy)
        r0 = np.percentile(r, 50)
        ang = np.arctan2(ys - cy, xs - cx)
        # midpoints per angular bin
        NB = 360
        bi = ((ang + math.pi) / (2 * math.pi) * NB).astype(int) % NB
        mids = []
        for b in range(NB):
            sel = bi == b
            if sel.sum() < 2:
                continue
            rv = r[sel]
            mids.append((ang[sel].mean(), .5 * (rv.min() + rv.max())))
        if len(mids) < 100:
            break
        A = np.array([m[0] for m in mids]); Rm = np.array([m[1] for m in mids])
        X = cx + Rm * np.cos(A); Y = cy + Rm * np.sin(A)
        # axis-aligned ellipse fit: a x^2 + c y^2 + d x + e y + f = 0, a=1
        M = np.stack([Y * Y, X, Y, np.ones_like(X)], 1)
        sol, *_ = np.linalg.lstsq(M, -X * X, rcond=None)
        cc, dd_, ee, ff = sol
        ncx = -dd_ / 2.0
        ncy = -ee / (2 * cc)
        k = ncx ** 2 + cc * ncy ** 2 - ff
        if k <= 0 or cc <= 0:
            break
        A_ax = math.sqrt(k); B_ax = math.sqrt(k / cc)
        if abs(ncx - cx) < .02 and abs(ncy - cy) < .02:
            cx, cy = ncx, ncy
            break
        cx, cy = ncx, ncy
    r = np.hypot(xs - cx, ys - cy)
    ang = np.arctan2(ys - cy, xs - cx)

    NA = 720
    bins = ((ang + math.pi) / (2 * math.pi) * NA).astype(int) % NA
    rin = np.full(NA, np.nan); rout = np.full(NA, np.nan); rmid = np.full(NA, np.nan)
    for b in range(NA):
        sel = bins == b
        if sel.sum() < 1:
            continue
        rv = r[sel]
        rin[b] = rv.min(); rout[b] = rv.max(); rmid[b] = .5 * (rv.min() + rv.max())
    ok = ~np.isnan(rmid)
    th = (np.arange(NA) + .5) / NA * 2 * math.pi - math.pi
    # ellipse fit on midline
    Xm = cx + rmid[ok] * np.cos(th[ok]); Ym = cy + rmid[ok] * np.sin(th[ok])
    M = np.stack([Ym * Ym, Xm, Ym, np.ones_like(Xm)], 1)
    sol, *_ = np.linalg.lstsq(M, -Xm * Xm, rcond=None)
    cc, dd_, ee, ff = sol
    ecx = -dd_ / 2.0; ecy = -ee / (2 * cc)
    k = ecx ** 2 + cc * ecy ** 2 - ff
    Aax = math.sqrt(k); Bax = math.sqrt(k / cc)

    sweep = rout - rin
    sweepv = sweep[ok]
    # alpha inside the band, per angle
    band_alpha = []
    for b in range(NA):
        if not ok[b]:
            band_alpha.append(np.nan); continue
        n_s = max(3, int(round(sweep[b])) + 1)
        rs = np.linspace(rin[b], rout[b], n_s)
        px = np.clip((cx + rs * math.cos(th[b])).astype(int), 0, W - 1)
        py = np.clip((cy + rs * math.sin(th[b])).astype(int), 0, H - 1)
        band_alpha.append(float(alpha_red[py, px].mean()))
    band_alpha = np.array(band_alpha)

    # angular coverage at several alpha levels + longest dark run
    cov = {}
    for thr, key in ((0.10, 'a10'), (0.20, 'a20'), (0.35, 'a35')):
        present = np.nan_to_num(band_alpha, nan=0.0) >= thr
        runs = []; cur = 0
        for v in np.concatenate([present, present]):
            if not v: cur += 1
            else:
                if cur: runs.append(cur)
                cur = 0
        runs = [min(r_, NA) for r_ in runs]
        cov[key] = dict(coverage=round(float(present.mean()), 4),
                        longest_gap_deg=round((max(runs) if runs else 0) * 360.0 / NA, 2),
                        n_gaps=len(runs) // 2 if len(runs) else 0)
    # striation: alpha statistics inside the band, and paper-through fraction
    inband = np.zeros((H, W), bool)
    rr_env = np.hypot(xx - cx, yy - cy)
    ang_all = np.arctan2(yy - cy, xx - cx)
    b_all = ((ang_all + math.pi) / (2 * math.pi) * NA).astype(int) % NA
    rin_f = np.nan_to_num(rin, nan=1e9)[b_all]
    rout_f = np.nan_to_num(rout, nan=-1e9)[b_all]
    inband = (rr_env >= rin_f) & (rr_env <= rout_f) & ring_zone
    env_n = int(inband.sum())
    al = alpha_red[inband]
    holes = inband & (alpha_red < .25)
    labh, comph = R.label(holes)
    hsz = [c['n'] for c in comph if c['n'] >= 1]
    OUT['ring'] = dict(
        centre_f=[round(float(fxv(cx)), 5), round(float(fyv(cy)), 5)],
        centre_mm=[round(mmx(cx), 3), round(mmy(cy), 3)],
        ellipse_centre_mm=[round(mmx(ecx), 3), round(mmy(ecy), 3)],
        mid_axis_w_mm=round(p2mm(2 * Aax), 3), mid_axis_h_mm=round(p2mm(2 * Bax), 3),
        mid_axis_w_f=round(float(2 * Aax / WPX), 5), mid_axis_h_f=round(float(2 * Bax / HPX), 5),
        axis_ratio_h_over_w=round(float(Bax / Aax), 4),
        ink_extent_w_mm=round(mmx(xs.max() + 1) - mmx(xs.min()), 3),
        ink_extent_h_mm=round(mmy(ys.max() + 1) - mmy(ys.min()), 3),
        outer_w_mm=round(p2mm(2 * np.nanmax(rout * np.abs(np.cos(th)))) if ok.any() else 0, 3),
        stroke_median_mm=round(p2mm(float(np.median(sweepv))), 3),
        stroke_mean_mm=round(p2mm(float(sweepv.mean())), 3),
        stroke_p05_mm=round(p2mm(float(np.percentile(sweepv, 5))), 3),
        stroke_p95_mm=round(p2mm(float(np.percentile(sweepv, 95))), 3),
        stroke_min_mm=round(p2mm(float(sweepv.min())), 3),
        stroke_max_mm=round(p2mm(float(sweepv.max())), 3),
        stroke_cv=round(float(sweepv.std() / sweepv.mean()), 4),
        angular_coverage=cov,
        band_alpha_mean=round(float(np.nanmean(band_alpha)), 4),
        band_alpha_std=round(float(np.nanstd(band_alpha)), 4),
        envelope_px=env_n,
        envelope_mm2=round(a2mm2(env_n), 2),
        paper_through_frac=round(float((al < .25).mean()), 4),
        paper_through_frac_a50=round(float((al < .50).mean()), 4),
        alpha_in_band_mean=round(float(al.mean()), 4),
        alpha_in_band_std=round(float(al.std()), 4),
        hole_count=len(hsz),
        hole_median_mm=round(p2mm(float(np.median(np.sqrt(np.array(hsz))))) if hsz else 0, 4),
        hole_area_frac=round(float(sum(hsz)) / max(1, env_n), 4),
        ring_ink_mm2=round(a2mm2(int(ringm.sum())), 2),
        n_ring_components=len([c for c in comps if c['n'] > 20]),
    )

    # ============================================================ CENTRE GLYPH
    gz = np.zeros((H, W), bool)
    gz[int(YT + .24 * HPX):int(YT + .72 * HPX), int(fl + 1):int(fr)] = True
    gb = black & gz
    lab, comps = R.label(R.dilate(gb, 1))
    keep = [c for c in comps if a2mm2(int((gb & (lab == c['label'])).sum())) > 3.0]
    glyph = np.zeros((H, W), bool)
    for c in keep:
        glyph |= gb & (lab == c['label'])
    gbox = boxof(glyph, "centre_glyph")
    gbox['n_components_over_3mm2'] = len(keep)
    gbox['component_mm2'] = [round(a2mm2(int((gb & (lab == c['label'])).sum())), 2) for c in keep]
    gbox['w_over_h'] = round(gbox['w_mm'] / gbox['h_mm'], 4)
    OUT['centre_glyph'] = gbox

    # ============================================================== ALL CLUSTERS
    # named zones, measured on the right class
    def zone(x0f, x1f, y0f, y1f, cls):
        z = np.zeros((H, W), bool)
        z[int(YT + y0f * HPX):int(YT + y1f * HPX), int(XL + x0f * WPX):int(XL + x1f * WPX)] = True
        return cls & z

    named = {}
    ZONES = dict(
        col_TL=(0.03, 0.27, 0.02, 0.36, 'black'),
        col_TR=(0.68, 0.97, 0.02, 0.36, 'black'),
        col_BR=(0.68, 0.97, 0.60, 0.84, 'black'),
        col_BC=(0.35, 0.65, 0.68, 0.94, 'black'),
        flame=(0.24, 0.76, 0.08, 0.29, 'black'),
        seal_big=(0.02, 0.40, 0.72, 0.95, 'ink'),
        seal_small=(0.68, 0.99, 0.80, 0.97, 'ink'),
    )
    for nm, (x0f, x1f, y0f, y1f, cls) in ZONES.items():
        m = {'black': black, 'red': red, 'ink': ink}[cls]
        sel = zone(x0f, x1f, y0f, y1f, m)
        b = boxof(sel, nm)
        lab2, cc2 = R.label(R.dilate(sel, 1))
        sub = [dict(mm2=round(a2mm2(int((sel & (lab2 == c['label'])).sum())), 2),
                    **{k: v for k, v in boxof(sel & (lab2 == c['label']), nm).items()
                       if k in ('x0_mm', 'x1_mm', 'y0_mm', 'y1_mm', 'cx_mm', 'cy_mm', 'w_mm', 'h_mm')})
               for c in cc2 if a2mm2(int((sel & (lab2 == c['label'])).sum())) > 1.5]
        b['parts'] = sub[:8]
        b['red_mm2'] = round(a2mm2(int((sel & red).sum())), 2)
        b['black_mm2'] = round(a2mm2(int((sel & black).sum())), 2)
        named[nm] = b
    OUT['named'] = named

    # ================================================================ LOZENGES
    # centreline chain: ink within +-4 mm of the vertical midline, below the ring
    cl = np.zeros((H, W), bool)
    xc = XL + .5 * WPX
    halfw = 4.0 / CARD_W * WPX
    cl[int(YT + .66 * HPX):H, int(xc - halfw):int(xc + halfw)] = True
    cl2 = np.zeros((H, W), bool)
    cl2[int(YT + .66 * HPX):int(YT + .73 * HPX), int(xc - halfw):int(xc + halfw)] = True
    chain = ink & (cl | cl2)
    lab, comps = R.label(R.dilate(chain, 1))
    loz = []
    for c in comps:
        sel = chain & (lab == c['label'])
        if a2mm2(int(sel.sum())) < .25:
            continue
        b = boxof(sel, "lozenge")
        b['red_mm2'] = round(a2mm2(int((sel & red).sum())), 3)
        b['black_mm2'] = round(a2mm2(int((sel & black).sum())), 3)
        b['is_black'] = bool((sel & black).sum() > (sel & red).sum())
        loz.append(b)
    loz = [b for b in loz if b['h_mm'] < 20 and b['w_mm'] < 12]
    loz.sort(key=lambda b: b['cy_mm'])
    OUT['centreline_chain'] = loz

    with open(os.path.join(HERE, "rg_s3_geometry.json"), "w", encoding="utf-8") as fh:
        json.dump(OUT, fh, indent=1, ensure_ascii=False)
    print(json.dumps(OUT, indent=1, ensure_ascii=False)[:14000])


main()
