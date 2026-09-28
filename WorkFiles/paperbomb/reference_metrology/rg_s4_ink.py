# -*- coding: utf-8 -*-
"""STAGE 4 - colour, ink density, halo, grain, ageing, the reds, the chain,
the seals, the columns, the flame. METROLOGY ONLY.

Resolution honesty: the real-glyph reference is 300 x 653 and its tag is
274.19 x 635.67 px, i.e. 3.917 px/mm.  One pixel is 0.255 mm and Nyquist is
1.96 cycles/mm, so nothing finer than a 0.51 mm cell is resolvable here.  Rows
that fall below that are marked and the high-resolution guide is used ONLY to
describe their character, never to set a position, size, weight or colour.
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
S3B = json.load(open(os.path.join(HERE, "rg_s3b_ring_glyph.json"), encoding="utf-8"))
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


def s2l(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


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


def chamfer(mask):
    big = 1e9
    d = np.where(mask, 0.0, big)
    aa, bb = 1.0, 1.41421356
    Hh, Ww = d.shape
    for y in range(Hh):
        row = d[y]
        if y:
            up = d[y - 1]
            row = np.minimum(row, up + aa)
            row = np.minimum(row, np.concatenate(([big], up[:-1])) + bb)
            row = np.minimum(row, np.concatenate((up[1:], [big])) + bb)
        for x in range(1, Ww):
            if row[x] > row[x - 1] + aa:
                row[x] = row[x - 1] + aa
        d[y] = row
    for y in range(Hh - 1, -1, -1):
        row = d[y]
        if y < Hh - 1:
            dn = d[y + 1]
            row = np.minimum(row, dn + aa)
            row = np.minimum(row, np.concatenate(([big], dn[:-1])) + bb)
            row = np.minimum(row, np.concatenate((dn[1:], [big])) + bb)
        for x in range(Ww - 2, -1, -1):
            if row[x] > row[x + 1] + aa:
                row[x] = row[x + 1] + aa
        d[y] = row
    return d


def boxblur(img, r):
    k = 2 * r + 1
    p = np.pad(img, ((r, r), (r, r)), mode='reflect')
    cs = np.cumsum(np.cumsum(p, 0), 1)
    cs = np.pad(cs, ((1, 0), (1, 0)))
    H2, W2 = img.shape
    return (cs[k:k + H2, k:k + W2] - cs[0:H2, k:k + W2]
            - cs[k:k + H2, 0:W2] + cs[0:H2, 0:W2]) / (k * k)


def main():
    a, _ = R.read_stored(R.RG)
    H, W = a.shape[:2]
    lu = R.luma(a)
    rex = a[..., 0] - .5 * (a[..., 1] + a[..., 2])
    hue, sat, val = R.hsv(a)
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
    paper_sel0 = tag & (rex < .22) & (lu > .80)
    paper_rex = float(np.median(rex[paper_sel0])); paper_lu = float(np.median(lu[paper_sel0]))
    red_rex = float(np.percentile(rex[tag], 99.5))
    dk = lu[tag]; ink_lu = float(np.median(dk[dk < np.percentile(dk, 6)]))
    thr_red = .5 * (paper_rex + red_rex); thr_ink = .5 * (paper_lu + ink_lu)
    red = tag & (rex > thr_red); black = tag & (lu < thr_ink) & ~red
    ink = red | black
    alpha_red = np.clip((rex - paper_rex) / (red_rex - paper_rex), 0, 1)

    fl = XL + S3['rules']['L']['inset_px']; fr = XR - 1 - S3['rules']['R']['inset_px']
    ft = YT + S3['rules']['T']['inset_px']; fb = YB - 1 - S3['rules']['B']['inset_px']

    # ------------------------------------------------------------ PAPER COLOUR
    clean = tag & ~R.dilate(ink, 3)
    # central 70 % so the edge vignette does not bias the base colour
    cen = np.zeros((H, W), bool)
    cen[int(YT + .12 * HPX):int(YT + .88 * HPX), int(XL + .12 * WPX):int(XL + .88 * WPX)] = True
    base = clean & cen
    prgb = np.array([float(np.median(a[..., c][base])) for c in range(3)])
    ph, ps, pv = R.hsv(prgb[None, None, :])
    lin = s2l(prgb)
    OUT['paper'] = dict(
        stored_rgb=[round(v, 4) for v in prgb],
        hex='#%02X%02X%02X' % tuple(int(round(v * 255)) for v in prgb),
        hue_deg=round(float(ph[0, 0]), 2), sat=round(float(ps[0, 0]), 4), val=round(float(pv[0, 0]), 4),
        linear_rgb=[round(float(v), 4) for v in lin],
        linear_luma=round(float(.2126 * lin[0] + .7152 * lin[1] + .0722 * lin[2]), 4),
        stored_luma=round(float(np.median(lu[base])), 4),
        n_samples=int(base.sum()),
        spatial_p05=round(float(np.percentile(lu[base], 5)), 4),
        spatial_p95=round(float(np.percentile(lu[base], 95)), 4),
    )

    # ------------------------------------------------------------ EDGE AGEING
    dist_edge = chamfer(~tag)          # px inside the tag from the boundary
    prof = []
    for d0 in range(0, 40, 1):
        sel = clean & (dist_edge >= d0) & (dist_edge < d0 + 1)
        if sel.sum() > 30:
            prof.append((round(p2mm(d0 + .5), 3), round(float(np.median(lu[sel])), 4), int(sel.sum())))
    plateau = float(np.median([p[1] for p in prof if p[0] > 12]))
    depth = [p for p in prof if p[0] < 1.0]
    d0v = depth[0][1] if depth else prof[0][1]
    reach = None
    for mm_, v, _ in prof:
        if v >= plateau - .05 * (plateau - d0v):
            reach = mm_; break
    per_side = {}
    for nm, sl in (('L', (slice(int(YT + .25 * HPX), int(YT + .75 * HPX)), slice(0, int(XL + .12 * WPX)))),
                   ('R', (slice(int(YT + .25 * HPX), int(YT + .75 * HPX)), slice(int(XR - .12 * WPX), W))),
                   ('T', (slice(0, int(YT + .07 * HPX)), slice(int(XL + .25 * WPX), int(XL + .75 * WPX)))),
                   ('B', (slice(int(YB - .07 * HPX), H), slice(int(XL + .25 * WPX), int(XL + .75 * WPX))))):
        m = clean[sl] & (dist_edge[sl] < 4)
        if m.sum() > 20:
            per_side[nm] = round(float(np.median(lu[sl][m])), 4)
    OUT['edge_ageing'] = dict(
        profile_mm_luma=prof[:26], plateau_luma=round(plateau, 4),
        edge_luma=round(d0v, 4),
        depth_pct=round(100 * (plateau - d0v) / plateau, 2),
        reach_95pct_mm=reach,
        per_side_edge_luma=per_side,
        side_spread_pts=round(100 * (max(per_side.values()) - min(per_side.values())), 2) if per_side else None,
    )

    # ---------------------------------------------------------------- GRAIN
    lo = boxblur(lu, 4)
    hp = (lu - lo)
    g = hp[base]
    amp = float(g.std()) / max(paper_lu, 1e-6)
    # autocorrelation along x and y on paper-only rows/cols
    def acorr(axis):
        vals = []
        if axis == 0:
            for y in range(int(YT + .15 * HPX), int(YT + .85 * HPX), 3):
                row = np.where(base[y], hp[y], np.nan)
                if np.isfinite(row).sum() < 60:
                    continue
                r0 = row[np.isfinite(row)]
                r0 = r0 - r0.mean()
                d = float((r0 * r0).mean())
                if d <= 0:
                    continue
                vals.append([float((r0[:-k] * r0[k:]).mean()) / d for k in range(1, 9)])
        else:
            for x in range(int(XL + .15 * WPX), int(XL + .85 * WPX), 3):
                col = np.where(base[:, x], hp[:, x], np.nan)
                if np.isfinite(col).sum() < 60:
                    continue
                c0 = col[np.isfinite(col)]
                c0 = c0 - c0.mean()
                d = float((c0 * c0).mean())
                if d <= 0:
                    continue
                vals.append([float((c0[:-k] * c0[k:]).mean()) / d for k in range(1, 9)])
        return np.array(vals).mean(0) if vals else np.zeros(8)
    ax = acorr(0); ay = acorr(1)

    def corrlen(ac):
        prev = 1.0
        for k, v in enumerate(ac, start=1):
            if v < math.e ** -1:
                t = (prev - math.e ** -1) / max(prev - v, 1e-9)
                return (k - 1 + t)
            prev = v
        return float(len(ac))
    lx = corrlen(ax); ly = corrlen(ay)
    OUT['grain'] = dict(
        amplitude_frac_of_paper=round(amp, 4),
        amplitude_pct=round(100 * amp, 2),
        highpass_radius_px=4,
        acorr_x=[round(float(v), 4) for v in ax],
        acorr_y=[round(float(v), 4) for v in ay],
        corr_len_x_px=round(lx, 3), corr_len_y_px=round(ly, 3),
        corr_len_x_mm=round(p2mm(lx), 4), corr_len_y_mm=round(p2mm(ly), 4),
        anisotropy=round(max(lx, ly) / max(1e-6, min(lx, ly)), 3),
        nyquist_cell_mm=round(2.0 / PPMM, 4),
        note="cell at or below 2 px is NOT resolvable in this file",
    )
    # mottle: power in the 1-3 mm and 3-10 mm bands
    b1 = boxblur(lu, 2); b2 = boxblur(lu, 6); b3 = boxblur(lu, 18)
    OUT['mottle'] = dict(
        band_1_3mm_pct=round(100 * float((b1 - b2)[base].std()) / paper_lu, 3),
        band_3_10mm_pct=round(100 * float((b2 - b3)[base].std()) / paper_lu, 3),
    )

    # ------------------------------------------------------------- THE REDS
    def redstat(m, nm):
        m = m & red
        if m.sum() < 8:
            return dict(name=nm, present=False)
        core = m & (alpha_red > .80)
        if core.sum() < 6:
            core = m
        rgb = np.array([float(np.median(a[..., c][core])) for c in range(3)])
        hh, ss, vv = R.hsv(rgb[None, None, :])
        return dict(name=nm, n_px=int(m.sum()), core_px=int(core.sum()),
                    stored_rgb=[round(float(v), 4) for v in rgb],
                    hex='#%02X%02X%02X' % tuple(int(round(v * 255)) for v in rgb),
                    hue_deg=round(float(hh[0, 0]), 2), sat=round(float(ss[0, 0]), 4),
                    val=round(float(vv[0, 0]), 4),
                    val_p10=round(float(np.percentile(val[core], 10)), 4),
                    val_p90=round(float(np.percentile(val[core], 90)), 4),
                    area_mm2=round(a2mm2(int(m.sum())), 2))

    def zm(x0f, x1f, y0f, y1f):
        z = np.zeros((H, W), bool)
        z[int(YT + y0f * HPX):int(YT + y1f * HPX), int(XL + x0f * WPX):int(XL + x1f * WPX)] = True
        return z
    rule_band = np.zeros((H, W), bool)
    for cen_, vert in ((fl, True), (fr, True), (ft, False), (fb, False)):
        if vert:
            x = int(round(cen_)); rule_band[:, max(0, x - 2):x + 3] = True
        else:
            y = int(round(cen_)); rule_band[max(0, y - 2):y + 3, :] = True
    rule_band &= ~zm(0, .16, 0, .06) & ~zm(.84, 1, 0, .06)
    ringzone = zm(.05, .95, .25, .68)
    reds = dict(
        border_rule=redstat(rule_band & ~zm(.40, .60, .90, 1.0), "border_rule"),
        ring=redstat(ringzone & ~rule_band, "ring"),
        seal_big=redstat(zm(.02, .40, .72, .96) & ~rule_band, "seal_big"),
        seal_small=redstat(zm(.68, .99, .80, .98) & ~rule_band, "seal_small"),
        lozenges=redstat(zm(.44, .56, .66, 1.0) & ~rule_band, "lozenges"),
        corner_ornaments=redstat((zm(0, .16, 0, .06) | zm(.84, 1, 0, .06) |
                                  zm(0, .16, .95, 1) | zm(.84, 1, .95, 1)), "corner_ornaments"),
    )
    present = [v for v in reds.values() if v.get('present', True) and 'val' in v]
    OUT['reds'] = reds
    OUT['red_spread'] = dict(
        hue_spread_deg=round(max(v['hue_deg'] for v in present) - min(v['hue_deg'] for v in present), 3),
        sat_spread=round(max(v['sat'] for v in present) - min(v['sat'] for v in present), 4),
        val_spread=round(max(v['val'] for v in present) - min(v['val'] for v in present), 4),
        heaviest=min(present, key=lambda v: v['val'])['name'],
        lightest=max(present, key=lambda v: v['val'])['name'],
        by_val=[[v['name'], v['val']] for v in sorted(present, key=lambda v: v['val'])],
    )

    # ---------------------------------------------------------- BLACK INK CORE
    bcore = black & (lu < np.percentile(lu[black], 30))
    brgb = np.array([float(np.median(a[..., c][bcore])) for c in range(3)])
    blin = s2l(brgb)
    OUT['black_ink'] = dict(
        stored_rgb=[round(float(v), 4) for v in brgb],
        hex='#%02X%02X%02X' % tuple(int(round(v * 255)) for v in brgb),
        linear_luma=round(float(.2126 * blin[0] + .7152 * blin[1] + .0722 * blin[2]), 5),
        stored_luma_p01=round(float(np.percentile(lu[black], 1)), 4),
        stored_luma_median=round(float(np.median(lu[black])), 4),
        stored_luma_min=round(float(lu[black].min()), 4),
        contrast_ratio_paper_over_ink=round(
            float((.2126 * s2l(prgb)[0] + .7152 * s2l(prgb)[1] + .0722 * s2l(prgb)[2]) /
                  max(1e-6, .2126 * blin[0] + .7152 * blin[1] + .0722 * blin[2])), 1),
    )

    # ------------------------------------------------------------------ HALO
    # luma recovery as a function of distance OUTSIDE solid black ink, away
    # from any other ink.  1 px = 0.2553 mm, so this row is sampling-limited.
    solid = black & R.erode(black, 2)
    dsolid = chamfer(solid)
    away = ~R.dilate(red, 3) & tag & ~black
    halo = []
    for d0 in range(1, 12):
        sel = away & (dsolid >= d0) & (dsolid < d0 + 1) & (dist_edge > 20)
        if sel.sum() > 40:
            halo.append([round(p2mm(d0), 3), round(float(np.median(lu[sel])), 4), int(sel.sum())])
    far = float(np.median([h[1] for h in halo[-3:]])) if len(halo) >= 3 else paper_lu
    reach_h = None
    for mm_, v, _ in halo:
        if v >= far - .05 * (far - halo[0][1]):
            reach_h = mm_; break
    OUT['ink_halo'] = dict(profile_mm_luma=halo, far_luma=round(far, 4),
                           first_ring_luma=round(halo[0][1], 4) if halo else None,
                           reach_95pct_mm=reach_h,
                           sampling_floor_mm=round(p2mm(1.0), 4),
                           note="one pixel is 0.255 mm; a halo below that cannot be separated "
                                "from the file's own resampling blur")
    # edge sharpness: 10-90 transition width across black stroke edges
    prof2 = []
    for d0 in range(0, 6):
        sel = tag & (dsolid >= d0) & (dsolid < d0 + 1) & ~red
        if sel.sum() > 40:
            prof2.append((d0, float(np.median(lu[sel]))))
    OUT['ink_edge_profile'] = [[p[0], round(p[1], 4)] for p in prof2]

    # -------------------------------------------------------- CENTRELINE CHAIN
    xc = XL + .5 * WPX
    halfw = 3.2 / CARD_W * WPX
    strip = np.zeros((H, W), bool)
    strip[int(YT + .655 * HPX):H, int(xc - halfw):int(xc + halfw)] = True
    ch = ink & strip
    lab, comps = R.label(R.dilate(ch, 1))
    chain = []
    for c in comps:
        sel = ch & (lab == c['label'])
        if a2mm2(int(sel.sum())) < .25:
            continue
        b = boxof(sel, "chain")
        b['red_mm2'] = round(a2mm2(int((sel & red).sum())), 3)
        b['black_mm2'] = round(a2mm2(int((sel & black).sum())), 3)
        b['kind'] = 'black' if (sel & black).sum() > (sel & red).sum() else 'red'
        chain.append(b)
    chain = [b for b in chain if b['w_mm'] < 9 and b['h_mm'] < 22]
    chain.sort(key=lambda b: b['cy_mm'])
    OUT['centreline_chain'] = chain

    # ------------------------------------------------------- LEAF-PAIR QUESTION
    # V1 put two tapered leaves at fy 0.838, fx 0.460 / 0.543.  Is there ANY
    # separate ornament there in the real-glyph file?
    probe = zm(.40, .61, .80, .875)
    OUT['leaf_pair_probe'] = dict(
        zone_mm=[round(mmx(XL + .40 * WPX), 2), round(mmx(XL + .61 * WPX), 2),
                 round(mmy(YT + .80 * HPX), 2), round(mmy(YT + .875 * HPX), 2)],
        ink_mm2=round(a2mm2(int((ink & probe).sum())), 3),
        black_mm2=round(a2mm2(int((black & probe).sum())), 3),
        red_mm2=round(a2mm2(int((red & probe).sum())), 3),
        n_components=len([c for c in R.label(R.dilate(ink & probe, 1))[1] if c['n'] > 4]),
        note="ink here belongs to the lower-centre column glyph; see s3 named.col_BC",
    )

    # ------------------------------------------------------------------ SEALS
    def seal(x0f, x1f, y0f, y1f, nm):
        z = zm(x0f, x1f, y0f, y1f)
        m = ink & z
        lab2, c2 = R.label(R.dilate(m, 2))
        main = m & (lab2 == c2[0]['label'])
        b = boxof(main, nm)
        ys, xs = np.nonzero(main)
        x0, x1 = xs.min(), xs.max(); y0, y1 = ys.min(), ys.max()
        sub = (slice(y0, y1 + 1), slice(x0, x1 + 1))
        rr = red[sub]; pp = ~ink[sub]
        b['red_fill_frac'] = round(float(rr.mean()), 4)
        b['paper_frac_inside_box'] = round(float(pp.mean()), 4)
        # inner 60 % of the box
        iy0 = y0 + int(.2 * (y1 - y0)); iy1 = y1 - int(.2 * (y1 - y0))
        ix0 = x0 + int(.2 * (x1 - x0)); ix1 = x1 - int(.2 * (x1 - x0))
        b['inner60_red_frac'] = round(float(red[iy0:iy1, ix0:ix1].mean()), 4)
        b['inner60_paper_frac'] = round(float((~ink)[iy0:iy1, ix0:ix1].mean()), 4)
        b['device_is_reversed_out'] = bool(b['inner60_red_frac'] > .5)
        # frame rule width: red run length crossing the left border at mid height
        ym = (y0 + y1) // 2
        row = red[ym, x0:x1 + 1]
        runs = []; cur = 0
        for v in row:
            if v:
                cur += 1
            else:
                if cur:
                    runs.append(cur)
                cur = 0
        if cur:
            runs.append(cur)
        b['mid_row_red_runs_mm'] = [round(p2mm(r), 3) for r in runs[:8]]
        xmid = (x0 + x1) // 2
        col = red[y0:y1 + 1, xmid]
        runs = []; cur = 0
        for v in col:
            if v:
                cur += 1
            else:
                if cur:
                    runs.append(cur)
                cur = 0
        if cur:
            runs.append(cur)
        b['mid_col_red_runs_mm'] = [round(p2mm(r), 3) for r in runs[:8]]
        return b
    OUT['seal_big'] = seal(.02, .40, .72, .96, "seal_big")
    OUT['seal_small'] = seal(.66, 1.0, .80, .98, "seal_small")

    # ------------------------------------------------------------- HERO vs 焼
    hero_zone = zm(.05, .96, .30, .66)
    gb = black & hero_zone
    lab, comps = R.label(R.dilate(gb, 2))
    hero = gb & (lab == comps[0]['label'])
    sho = black & zm(.70, .96, .62, .74)
    lab2, c2 = R.label(R.dilate(sho, 1))
    sho = sho & (lab2 == c2[0]['label'])

    def near(m1, m2):
        y1, x1 = np.nonzero(m1); y2, x2 = np.nonzero(m2)
        best = 1e9
        for i in range(0, len(x1), 128):
            dxs = (x1[i:i + 128][:, None] - x2[None, :]) / WPX * CARD_W
            dys = (y1[i:i + 128][:, None] - y2[None, :]) / HPX * CARD_H
            best = min(best, float(np.sqrt(dxs * dxs + dys * dys).min()))
        return round(best, 3)
    OUT['hero_to_sho_mm'] = near(hero, sho)
    OUT['sho_box'] = boxof(sho, "sho_glyph")
    OUT['hero_box'] = boxof(hero, "hero")

    with open(os.path.join(HERE, "rg_s4_ink.json"), "w", encoding="utf-8") as fh:
        json.dump(OUT, fh, indent=1, ensure_ascii=False)
    print(json.dumps(OUT, indent=1, ensure_ascii=False))


main()
