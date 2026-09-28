# -*- coding: utf-8 -*-
"""STAGE 3b - the ring and the hero glyph, done properly. METROLOGY ONLY.

Stage 3's first cut took only the LARGEST red component as "the ring" and the
ring is broken into ten arcs, so it measured a third of a ring.  It also let the
side columns into the hero glyph's zone.  Both are fixed here.
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
                x0_f=round(float(fxv(xs.min())), 5), x1_f=round(float(fxv(xs.max() + 1)), 5),
                y0_f=round(float(fyv(ys.min())), 5), y1_f=round(float(fyv(ys.max() + 1)), 5),
                x0_mm=round(mmx(xs.min()), 3), x1_mm=round(mmx(xs.max() + 1), 3),
                y0_mm=round(mmy(ys.min()), 3), y1_mm=round(mmy(ys.max() + 1), 3),
                w_mm=round(mmx(xs.max() + 1) - mmx(xs.min()), 3),
                h_mm=round(mmy(ys.max() + 1) - mmy(ys.min()), 3),
                w_f=round(float(fxv(xs.max() + 1) - fxv(xs.min())), 5),
                h_f=round(float(fyv(ys.max() + 1) - fyv(ys.min())), 5),
                cx_mm=round(mmx(xs.mean() + .5), 3), cy_mm=round(mmy(ys.mean() + .5), 3),
                cx_f=round(float(fxv(xs.mean() + .5)), 5), cy_f=round(float(fyv(ys.mean() + .5)), 5))


def main():
    a, _ = R.read_stored(R.RG)
    H, W = a.shape[:2]
    lu = R.luma(a)
    rex = a[..., 0] - 0.5 * (a[..., 1] + a[..., 2])
    P = np.array(S1['octagon_vertices_px'], float)
    yy, xx = np.mgrid[0:H, 0:W]
    inside = np.zeros((H, W), bool); n = len(P); j = n - 1
    px_ = xx + .5; py_ = yy + .5
    for i in range(n):
        xi, yi = P[i]; xj, yj = P[j]
        inside ^= (((yi > py_) != (yj > py_)) &
                   (px_ < (xj - xi) * (py_ - yi) / (yj - yi + 1e-12) + xi))
        j = i
    tag = R.erode(inside, 1)
    paper_sel = tag & (rex < .22) & (lu > .80)
    paper_rex = float(np.median(rex[paper_sel])); paper_lu = float(np.median(lu[paper_sel]))
    red_rex = float(np.percentile(rex[tag], 99.5))
    dk = lu[tag]; ink_lu = float(np.median(dk[dk < np.percentile(dk, 6)]))
    thr_red = .5 * (paper_rex + red_rex); thr_ink = .5 * (paper_lu + ink_lu)
    red = tag & (rex > thr_red); black = tag & (lu < thr_ink) & ~red
    alpha_red = np.clip((rex - paper_rex) / (red_rex - paper_rex), 0, 1)

    fl = XL + S3['rules']['L']['inset_px']; fr = XR - 1 - S3['rules']['R']['inset_px']
    ft = YT + S3['rules']['T']['inset_px']; fb = YB - 1 - S3['rules']['B']['inset_px']

    # ---------------------------------------------------------------- RING
    zone = np.zeros((H, W), bool)
    zone[int(YT + .21 * HPX):int(YT + .685 * HPX), int(fl + 4):int(fr - 3)] = True
    rr = red & zone
    ys, xs = np.nonzero(rr)
    cx, cy = float(xs.mean()), float(ys.mean())
    Aax = Bax = 0.0
    for it in range(14):
        r = np.hypot(xs - cx, ys - cy)
        rmed = float(np.median(r))
        sel = (r > .55 * rmed) & (r < 1.55 * rmed)
        X0, Y0 = xs[sel].astype(float), ys[sel].astype(float)
        ang = np.arctan2(Y0 - cy, X0 - cx)
        NB = 360
        bi = ((ang + math.pi) / (2 * math.pi) * NB).astype(int) % NB
        rv = np.hypot(X0 - cx, Y0 - cy)
        mids = []
        for b in range(NB):
            s = bi == b
            if s.sum() < 2:
                continue
            mids.append(((b + .5) / NB * 2 * math.pi - math.pi, .5 * (rv[s].min() + rv[s].max())))
        if len(mids) < 80:
            break
        A_ = np.array([m[0] for m in mids]); Rm = np.array([m[1] for m in mids])
        Xm = cx + Rm * np.cos(A_); Ym = cy + Rm * np.sin(A_)
        M = np.stack([Ym * Ym, Xm, Ym, np.ones_like(Xm)], 1)
        sol, *_ = np.linalg.lstsq(M, -Xm * Xm, rcond=None)
        cc, d_, e_, f_ = sol
        if cc <= 0:
            break
        ncx = -d_ / 2.0; ncy = -e_ / (2 * cc)
        k = ncx ** 2 + cc * ncy ** 2 - f_
        if k <= 0:
            break
        Aax = math.sqrt(k); Bax = math.sqrt(k / cc)
        moved = math.hypot(ncx - cx, ncy - cy)
        cx, cy = ncx, ncy
        if moved < .01:
            break
    # final ring mask = red inside the elliptical annulus
    er = np.sqrt(((xx - cx) / Aax) ** 2 + ((yy - cy) / Bax) ** 2)
    annulus = (er > .72) & (er < 1.30) & zone
    ringm = red & annulus
    NA = 720
    ang_all = np.arctan2(yy - cy, xx - cx)
    r_all = np.hypot(xx - cx, yy - cy)
    bins = ((ang_all + math.pi) / (2 * math.pi) * NA).astype(int) % NA
    rin = np.full(NA, np.nan); rout = np.full(NA, np.nan)
    br = bins[ringm]; rrv = r_all[ringm]
    for b in range(NA):
        s = br == b
        if s.sum() == 0:
            continue
        rin[b] = rrv[s].min(); rout[b] = rrv[s].max()
    ok = ~np.isnan(rin)
    th = (np.arange(NA) + .5) / NA * 2 * math.pi - math.pi
    sweep = rout - rin
    # band alpha per angle, sampled on the FITTED ellipse band (so angles with
    # no classified red still get a measurement - that is the honest coverage)
    rad_e = Aax * Bax / np.sqrt((Bax * np.cos(th)) ** 2 + (Aax * np.sin(th)) ** 2)
    halfband = float(np.nanmedian(sweep)) / 2.0
    band_alpha = np.zeros(NA); band_peak = np.zeros(NA)
    for b in range(NA):
        rs = np.linspace(rad_e[b] - halfband, rad_e[b] + halfband, 13)
        pxs = np.clip(np.round(cx + rs * math.cos(th[b])).astype(int), 0, W - 1)
        pys = np.clip(np.round(cy + rs * math.sin(th[b])).astype(int), 0, H - 1)
        v = alpha_red[pys, pxs]
        band_alpha[b] = float(v.mean()); band_peak[b] = float(v.max())
    cov = {}
    for thr, key in ((.10, 'peak10'), (.25, 'peak25'), (.50, 'peak50')):
        pres = band_peak >= thr
        runs = []; cur = 0
        for v in np.concatenate([pres, pres]):
            if not v:
                cur += 1
            else:
                if cur:
                    runs.append(cur)
                cur = 0
        if cur:
            runs.append(cur)
        runs = [min(x, NA) for x in runs]
        cov[key] = dict(coverage=round(float(pres.mean()), 4),
                        longest_gap_deg=round((max(runs) if runs else 0) * 360. / NA, 2),
                        n_gaps=int(round(len(runs) / 2.0)) if runs else 0,
                        gaps_deg=[round(x * 360. / NA, 1) for x in sorted(runs, reverse=True)[:8]])
    sv = sweep[ok]
    # striation / kasure inside the swept envelope
    rin_f = np.nan_to_num(rin, nan=1e9)[bins]; rout_f = np.nan_to_num(rout, nan=-1e9)[bins]
    env = (r_all >= rin_f) & (r_all <= rout_f) & zone & (er > .60) & (er < 1.45)
    al = alpha_red[env]
    holes = env & (alpha_red < .25)
    labh, comph = R.label(holes)
    hs = [c for c in comph if c['n'] >= 1]
    hdim = []
    for c in hs:
        w_ = c['x1'] - c['x0'] + 1; h_ = c['y1'] - c['y0'] + 1
        hdim.append((max(w_, h_), min(w_, h_), c['n']))
    OUT['ring'] = dict(
        centre_f=[round(float(fxv(cx)), 5), round(float(fyv(cy)), 5)],
        centre_mm=[round(mmx(cx), 3), round(mmy(cy), 3)],
        mid_axis_w_mm=round(p2mm(2 * Aax), 3), mid_axis_h_mm=round(p2mm(2 * Bax), 3),
        mid_axis_w_f=round(float(2 * Aax / WPX), 5), mid_axis_h_f=round(float(2 * Bax / HPX), 5),
        axis_ratio_h_over_w=round(float(Bax / Aax), 4),
        ink_box=boxof(ringm, "ring_ink"),
        ring_ink_mm2=round(a2mm2(int(ringm.sum())), 2),
        stroke_median_mm=round(p2mm(float(np.median(sv))), 3),
        stroke_mean_mm=round(p2mm(float(sv.mean())), 3),
        stroke_p05_mm=round(p2mm(float(np.percentile(sv, 5))), 3),
        stroke_p95_mm=round(p2mm(float(np.percentile(sv, 95))), 3),
        stroke_max_mm=round(p2mm(float(sv.max())), 3),
        stroke_cv=round(float(sv.std() / sv.mean()), 4),
        angular_coverage=cov,
        band_alpha_mean=round(float(band_alpha.mean()), 4),
        band_alpha_std=round(float(band_alpha.std()), 4),
        band_alpha_p05=round(float(np.percentile(band_alpha, 5)), 4),
        band_alpha_p95=round(float(np.percentile(band_alpha, 95)), 4),
        envelope_mm2=round(a2mm2(int(env.sum())), 2),
        paper_through_frac=round(float((al < .25).mean()), 4),
        alpha_in_band_mean=round(float(al.mean()), 4),
        alpha_in_band_std=round(float(al.std()), 4),
        hole_count=len(hs),
        hole_area_frac=round(float(sum(c['n'] for c in hs)) / max(1, int(env.sum())), 4),
        hole_median_long_mm=round(p2mm(float(np.median([d[0] for d in hdim]))) if hdim else 0, 4),
        hole_median_short_mm=round(p2mm(float(np.median([d[1] for d in hdim]))) if hdim else 0, 4),
        hole_median_elongation=round(float(np.median([d[0] / max(1, d[1]) for d in hdim])) if hdim else 0, 3),
        n_red_components_in_annulus=0,
    )
    lab, comps = R.label(R.dilate(ringm, 1))
    OUT['ring']['n_red_components_in_annulus'] = len([c for c in comps if c['n'] > 12])
    OUT['ring']['component_mm2'] = [round(a2mm2(int((ringm & (lab == c['label'])).sum())), 2)
                                    for c in comps[:8]]
    # thickness as a function of angle, in 24 sectors (for "does a brush move?")
    sect = []
    for s in range(24):
        lo = int(s * NA / 24); hi = int((s + 1) * NA / 24)
        sl = sweep[lo:hi]; sl = sl[~np.isnan(sl)]
        ba = band_alpha[lo:hi]
        deg = (s + .5) * 15.0
        sect.append(dict(deg_from_east_cw=round(deg, 1),
                         stroke_mm=round(p2mm(float(np.median(sl))), 2) if len(sl) else 0.0,
                         alpha=round(float(ba.mean()), 3)))
    OUT['ring']['sectors'] = sect

    # ------------------------------------------------------------ HERO GLYPH
    inner = (er < 1.55)
    gz = np.zeros((H, W), bool)
    gz[int(YT + .23 * HPX):int(YT + .73 * HPX), int(fl):int(fr)] = True
    gb = black & gz & inner
    lab, comps = R.label(R.dilate(gb, 2))
    main_lbl = comps[0]['label']
    glyph = gb & (lab == main_lbl)
    others = [dict(mm2=round(a2mm2(int((gb & (lab == c['label'])).sum())), 2),
                   **{k: v for k, v in boxof(gb & (lab == c['label'])).items()
                      if k in ('x0_mm', 'x1_mm', 'y0_mm', 'y1_mm', 'cx_mm', 'cy_mm')})
              for c in comps[1:6] if a2mm2(int((gb & (lab == c['label'])).sum())) > .5]
    gbox = boxof(glyph, "centre_glyph")
    gbox['w_over_h'] = round(gbox['w_mm'] / gbox['h_mm'], 4)
    # component structure at NATIVE connectivity (no dilation)
    lab0, comps0 = R.label(glyph)
    gbox['native_components'] = [round(a2mm2(c['n']), 2) for c in comps0[:8]]
    gbox['n_native_components_over_15mm2'] = len([c for c in comps0 if a2mm2(c['n']) > 15])
    gbox['stray_nearby'] = others
    # stroke width ladder: distance transform maxima
    OUT['centre_glyph'] = gbox

    # clearances: hero glyph to each neighbour, nearest-ink distance
    def near_dist(m1, m2):
        y1, x1 = np.nonzero(m1); y2, x2 = np.nonzero(m2)
        if len(x1) == 0 or len(x2) == 0:
            return None
        step1 = max(1, len(x1) // 4000); step2 = max(1, len(x2) // 4000)
        x1 = x1[::step1]; y1 = y1[::step1]; x2 = x2[::step2]; y2 = y2[::step2]
        best = 1e9
        for i in range(0, len(x1), 64):
            dxs = (x1[i:i + 64][:, None] - x2[None, :]) / WPX * CARD_W
            dys = (y1[i:i + 64][:, None] - y2[None, :]) / HPX * CARD_H
            d = np.sqrt(dxs * dxs + dys * dys).min()
            best = min(best, float(d))
        return round(best, 3)

    def zmask(x0f, x1f, y0f, y1f, cls):
        z = np.zeros((H, W), bool)
        z[int(YT + y0f * HPX):int(YT + y1f * HPX), int(XL + x0f * WPX):int(XL + x1f * WPX)] = True
        return cls & z

    nbr = dict(
        ring=ringm,
        flame_emblem=zmask(.24, .76, .08, .29, black),
        col_TL=zmask(.03, .30, .02, .38, black),
        col_TR=zmask(.68, .97, .02, .38, black),
        col_BR=zmask(.68, .99, .60, .84, black),
        col_BC=zmask(.35, .65, .68, .94, black),
        rule_left=zmask(.0, .09, .10, .90, red),
        rule_right=zmask(.91, 1., .10, .90, red),
    )
    cl = {}
    for k, m in nbr.items():
        cl[k] = near_dist(glyph, m & ~glyph)
    OUT['hero_clearance_mm'] = cl
    # and the pair the brief calls out: col_BR (焼尽) to the hero
    OUT['hero_to_BR_column_mm'] = cl['col_BR']
    OUT['col_BR_box'] = boxof(nbr['col_BR'], "col_BR")

    with open(os.path.join(HERE, "rg_s3b_ring_glyph.json"), "w", encoding="utf-8") as fh:
        json.dump(OUT, fh, indent=1, ensure_ascii=False)

    vis = a.copy()
    vis[ringm] = [1, 0, 1]
    vis[glyph] = [0, .4, 1]
    ee = np.abs(er - 1.0) < .01
    vis[ee] = [0, 1, 0]
    R.save_debug(vis, "s3b_ring_fit", scale=2)
    print(json.dumps(OUT, indent=1, ensure_ascii=False))


main()
