# -*- coding: utf-8 -*-
"""STAGE 5 - columns, flame, seals, chain split, and the corrected colour rows.
METROLOGY ONLY.  Also measures the HIGH-RESOLUTION guide for SUB-PIXEL CHARACTER
ONLY (grain cell, stroke-edge roughness, kasure hole shape) - never for a
position, size, weight, colour or shape, which all come from the real-glyph file.
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
    num = bs(img * wgt); den = bs(wgt)
    return num / np.maximum(den, 1e-6)


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


def classify(a, poly):
    H, W = a.shape[:2]
    lu = R.luma(a)
    rex = a[..., 0] - .5 * (a[..., 1] + a[..., 2])
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
    dk = lu[tag]; i_lu = float(np.median(dk[dk < np.percentile(dk, 6)]))
    red = tag & (rex > .5 * (p_rex + r_rex))
    black = tag & (lu < .5 * (p_lu + i_lu)) & ~red
    return dict(tag=tag, lu=lu, rex=rex, red=red, black=black, ink=red | black,
                p_rex=p_rex, p_lu=p_lu, r_rex=r_rex, i_lu=i_lu,
                alpha_red=np.clip((rex - p_rex) / (r_rex - p_rex), 0, 1))


def split_column(mask, minrun=1):
    """Split a vertical column of glyphs on empty rows."""
    rows = mask.any(1)
    ys = np.flatnonzero(rows)
    if len(ys) == 0:
        return []
    segs = []; s = ys[0]; prev = ys[0]
    for y in ys[1:]:
        if y - prev > minrun:
            segs.append((s, prev)); s = y
        prev = y
    segs.append((s, prev))
    return segs


def main():
    a, _ = R.read_stored(R.RG)
    H, W = a.shape[:2]
    poly = np.array(S1['octagon_vertices_px'], float)
    C = classify(a, poly)
    tag, lu, red, black, ink = C['tag'], C['lu'], C['red'], C['black'], C['ink']
    alpha_red = C['alpha_red']
    fl = XL + S3['rules']['L']['inset_px']; fr = XR - 1 - S3['rules']['R']['inset_px']
    ft = YT + S3['rules']['T']['inset_px']; fb = YB - 1 - S3['rules']['B']['inset_px']

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

    # ------------------------------------------------------------- COLUMNS
    cols = {}
    CDEF = dict(
        col_TL_hidonjutsu=(.04, .28, .015, .36),
        col_TR_bakuenjin=(.70, .96, .015, .36),
        col_BR_shoujin=(.70, .96, .61, .83),
        col_BC_shungou=(.36, .64, .68, .93),
    )
    for nm, (x0f, x1f, y0f, y1f) in CDEF.items():
        m = black & zm(x0f, x1f, y0f, y1f) & ~rule_band
        lab, comps = R.label(R.dilate(m, 1))
        keep = np.zeros((H, W), bool)
        for c in comps:
            if a2mm2(int((m & (lab == c['label'])).sum())) > 2.0:
                keep |= m & (lab == c['label'])
        segs = split_column(keep)
        glyphs = []
        for (ya, yb) in segs:
            g = keep.copy(); g[:ya] = False; g[yb + 1:] = False
            if a2mm2(int(g.sum())) < 6.0:
                continue
            b = boxof(g, nm)
            b['em_mm'] = round(max(b['w_mm'], b['h_mm']), 3)
            glyphs.append(b)
        whole = boxof(keep, nm)
        pitches = [round(glyphs[i + 1]['cy_mm'] - glyphs[i]['cy_mm'], 3) for i in range(len(glyphs) - 1)]
        leads = [round(glyphs[i + 1]['y0_mm'] - glyphs[i]['y1_mm'], 3) for i in range(len(glyphs) - 1)]
        cols[nm] = dict(
            whole=whole, n_glyphs=len(glyphs), glyphs=glyphs,
            axis_x_mm=round(float(np.mean([g['cx_mm'] for g in glyphs])), 3) if glyphs else None,
            axis_x_f=round(float(np.mean([g['cx_f'] for g in glyphs])), 5) if glyphs else None,
            em_mean_mm=round(float(np.mean([g['em_mm'] for g in glyphs])), 3) if glyphs else None,
            em_min_mm=round(float(min(g['em_mm'] for g in glyphs)), 3) if glyphs else None,
            em_max_mm=round(float(max(g['em_mm'] for g in glyphs)), 3) if glyphs else None,
            cell_w_mean_mm=round(float(np.mean([g['w_mm'] for g in glyphs])), 3) if glyphs else None,
            pitch_mm=pitches, leading_mm=leads,
            clear_of_own_rule_mm=None,
        )
        if nm.startswith('col_TL') or nm.startswith('col_BC'):
            cols[nm]['clear_of_own_rule_mm'] = round(whole['x0_mm'] - mmx(fl), 3)
        else:
            cols[nm]['clear_of_own_rule_mm'] = round(mmx(fr) - whole['x1_mm'], 3)
    OUT['columns'] = cols

    # --------------------------------------------------------------- FLAME
    fm = black & zm(.28, .72, .09, .28)
    lab, comps = R.label(R.dilate(fm, 1))
    parts = []
    keep = np.zeros((H, W), bool)
    for c in comps:
        s = fm & (lab == c['label'])
        if a2mm2(int(s.sum())) < 3.0:
            continue
        keep |= s
        parts.append(boxof(s, "flame_part"))
    fb_ = boxof(keep, "flame_emblem")
    fb_['n_parts'] = len(parts)
    fb_['parts'] = parts
    fb_['w_over_h'] = round(fb_['w_mm'] / fb_['h_mm'], 4)
    fb_['fill_of_box'] = round(fb_['area_mm2'] / (fb_['w_mm'] * fb_['h_mm']), 4)
    # the spiral heart: enclosed paper inside the emblem
    filled = R.fill_holes(keep)
    eye = filled & ~keep
    labe, compe = R.label(eye)
    eyes = [dict(mm2=round(a2mm2(c['n']), 3), **{k: v for k, v in boxof(eye & (labe == c['label'])).items()
                                                 if k in ('w_mm', 'h_mm', 'cx_mm', 'cy_mm')})
            for c in compe if c['n'] >= 2]
    fb_['enclosed_paper_voids'] = eyes[:6]
    fb_['heart_is_solid'] = bool(len([e for e in eyes if e['mm2'] > 1.0]) <= 2)
    # tongue widths: horizontal ink runs across the emblem, per row
    ys, xs = np.nonzero(keep)
    runw = []
    for y in range(ys.min(), ys.max() + 1):
        row = keep[y]
        idx = np.flatnonzero(row)
        if len(idx) == 0:
            continue
        runs = []; cur = 1
        for i in range(1, len(idx)):
            if idx[i] == idx[i - 1] + 1:
                cur += 1
            else:
                runs.append(cur); cur = 1
        runs.append(cur)
        runw.append((y, [round(p2mm(r), 2) for r in runs]))
    mid = runw[len(runw) // 3]
    fb_['run_widths_mm_at_upper_third'] = mid[1]
    fb_['max_runs_per_row'] = max(len(r[1]) for r in runw)
    OUT['flame_emblem'] = fb_

    # ---------------------------------------------------------------- SEALS
    def seal_iso(x0f, x1f, y0f, y1f, nm):
        z = zm(x0f, x1f, y0f, y1f) & ~rule_band
        m = ink & z
        lab2, c2 = R.label(R.dilate(m, 2))
        main = m & (lab2 == c2[0]['label'])
        b = boxof(main, nm)
        ys_, xs_ = np.nonzero(main)
        x0, x1 = int(xs_.min()), int(xs_.max()); y0, y1 = int(ys_.min()), int(ys_.max())
        sub = (slice(y0, y1 + 1), slice(x0, x1 + 1))
        b['red_fill_frac'] = round(float(red[sub].mean()), 4)
        iy0 = y0 + int(.22 * (y1 - y0)); iy1 = y1 - int(.22 * (y1 - y0))
        ix0 = x0 + int(.22 * (x1 - x0)); ix1 = x1 - int(.22 * (x1 - x0))
        b['inner56_red_frac'] = round(float(red[iy0:iy1, ix0:ix1].mean()), 4)
        b['device_reversed_out'] = bool(b['inner56_red_frac'] > .5)
        ym = (y0 + y1) // 2; xmid = (x0 + x1) // 2

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
        b['row_scan_red_runs_mm'] = runs_of(red[ym, x0:x1 + 1])
        b['col_scan_red_runs_mm'] = runs_of(red[y0:y1 + 1, xmid])
        b['row_scan_gaps_mm'] = runs_of(~red[ym, x0:x1 + 1])
        # frame rule thickness = first red run from each side at mid height
        rr = runs_of(red[ym, x0:x1 + 1])
        b['frame_rule_mm'] = rr[0] if rr else None
        return b
    OUT['seal_big'] = seal_iso(.04, .38, .73, .95, "seal_big")
    OUT['seal_small'] = seal_iso(.74, .99, .82, .97, "seal_small")

    # ------------------------------------------------------- CHAIN, SPLIT BY CLASS
    xc = XL + .5 * WPX
    halfw = 3.4 / CARD_W * WPX
    strip = np.zeros((H, W), bool)
    strip[int(YT + .655 * HPX):H, int(xc - halfw):int(xc + halfw)] = True
    items = []
    for cls, nm in ((red, 'red'), (black, 'black')):
        m = cls & strip
        lab, comps = R.label(R.dilate(m, 1))
        for c in comps:
            s = m & (lab == c['label'])
            if a2mm2(int(s.sum())) < .25:
                continue
            b = boxof(s, nm)
            b['kind'] = nm
            if b['h_mm'] < 12 and b['w_mm'] < 8:
                items.append(b)
    items.sort(key=lambda b: b['cy_mm'])
    OUT['centreline_chain'] = items

    # ---------------------------------------------------- CORRECTED COLOUR ROWS
    clean = tag & ~R.dilate(ink, 3)
    cen = zm(.12, .88, .10, .90)
    base = clean & cen
    p_lu = float(np.median(lu[base]))
    dist_edge = chamfer(~tag)
    deep = ~R.dilate(ink, 9)
    prof = []
    for d0 in range(0, 46):
        sel = clean & deep & (dist_edge >= d0) & (dist_edge < d0 + 1)
        if sel.sum() > 25:
            prof.append([round(p2mm(d0 + .5), 3), round(float(np.median(lu[sel])), 4), int(sel.sum())])
    plateau = p_lu
    e0 = prof[0][1]
    reach = None
    for mm_, v, _ in prof:
        if v >= plateau - .05 * (plateau - e0):
            reach = mm_; break
    OUT['edge_ageing'] = dict(profile_mm_luma=prof[:30], plateau_luma=round(plateau, 4),
                              edge_luma=round(e0, 4),
                              depth_pct=round(100 * (plateau - e0) / plateau, 2),
                              reach_95pct_mm=reach,
                              reach_note="distance inboard at which the paper recovers 95 % of the edge step")
    # mottle with INK-AWARE blurs
    w = clean.astype(float)
    b1 = wblur(lu * clean, w, 2); b2 = wblur(lu * clean, w, 6); b3 = wblur(lu * clean, w, 18)
    OUT['mottle'] = dict(
        band_1_3mm_pct=round(100 * float((b1 - b2)[base].std()) / p_lu, 3),
        band_3_10mm_pct=round(100 * float((b2 - b3)[base].std()) / p_lu, 3),
    )
    # halo measured from the BLACK BOUNDARY outward
    dblk = chamfer(black)
    away = tag & ~black & ~R.dilate(red, 3)
    halo = []
    for d0 in range(1, 14):
        sel = away & (dblk >= d0) & (dblk < d0 + 1) & (dist_edge > 16)
        if sel.sum() > 40:
            halo.append([round(p2mm(d0), 3), round(float(np.median(lu[sel])), 4), int(sel.sum())])
    far = float(np.median([h[1] for h in halo[-4:]])) if len(halo) >= 4 else p_lu
    reach_h = None
    for mm_, v, _ in halo:
        if v >= far - .05 * (far - halo[0][1]):
            reach_h = mm_; break
    OUT['ink_halo'] = dict(profile_mm_luma=halo, far_luma=round(far, 4),
                           reach_95pct_mm=reach_h, sampling_floor_mm=round(p2mm(1.), 4))
    # red weight: mean luma over each element's red (laid-on weight, not hue)
    def wt(m, nm):
        m = m & red
        if m.sum() < 8:
            return None
        return dict(name=nm, mean_luma=round(float(lu[m].mean()), 4),
                    median_luma=round(float(np.median(lu[m])), 4),
                    solid_frac=round(float((alpha_red[m] > .9).mean()), 4),
                    mean_alpha=round(float(alpha_red[m].mean()), 4))
    rb = rule_band & ~zm(0, .16, 0, .06) & ~zm(.84, 1, 0, .06) & ~zm(0, .16, .94, 1) & ~zm(.84, 1, .94, 1)
    OUT['red_weight'] = [x for x in (
        wt(rb, 'border_rule'), wt(zm(.05, .95, .25, .68) & ~rule_band, 'ring'),
        wt(zm(.04, .38, .73, .95) & ~rule_band, 'seal_big'),
        wt(zm(.74, .99, .82, .97) & ~rule_band, 'seal_small'),
        wt(strip, 'lozenges'),
        wt((zm(0, .16, 0, .07) | zm(.84, 1, 0, .07) | zm(0, .16, .93, 1) | zm(.84, 1, .93, 1)),
           'corner_ornaments')) if x]

    # ================= HIGH-RESOLUTION GUIDE: SUB-PIXEL CHARACTER ONLY ========
    hr, _ = R.read_stored(R.HR)
    Hh, Wh = hr.shape[:2]
    hlu = R.luma(hr)
    hrex = hr[..., 0] - .5 * (hr[..., 1] + hr[..., 2])
    warm = R.warmth(hr)
    corners = np.concatenate([warm[:8, :8].ravel(), warm[:8, -8:].ravel(),
                              warm[-8:, :8].ravel(), warm[-8:, -8:].ravel()])
    lo = float(np.median(corners))
    core = warm[int(.06 * Hh):int(.94 * Hh), int(.10 * Wh):int(.90 * Wh)]
    hi = float(np.median(core[core > lo + .05]))
    hm = warm > lo + .5 * (hi - lo)
    hm = R.fill_holes(R.open_(R.close_(hm, 2), 2))
    labh, ch = R.label(hm)
    hm = R.fill_holes(labh == ch[0]['label'])
    hys = np.flatnonzero(hm.any(1)); hxs = np.flatnonzero(hm.any(0))
    hppmm = (hxs[-1] - hxs[0] + 1) / CARD_W
    hink = hm & (hlu < .5)
    hred = hm & (hrex > .35)
    hclean = hm & ~R.dilate(hink | hred, 4)
    hcen = np.zeros((Hh, Wh), bool)
    hcen[int(hys[0] + .12 * len(hys)):int(hys[0] + .88 * len(hys)),
         int(hxs[0] + .12 * len(hxs)):int(hxs[0] + .88 * len(hxs))] = True
    hbase = hclean & hcen
    hlo = wblur(hlu * hclean, hclean.astype(float), 8)
    hhp = hlu - hlo
    hp_lu = float(np.median(hlu[hbase]))
    hamp = float(hhp[hbase].std()) / hp_lu

    def hacorr(axis, n=10):
        vals = []
        rng = range(int(hys[0] + .15 * len(hys)), int(hys[0] + .85 * len(hys)), 7) if axis == 0 \
            else range(int(hxs[0] + .15 * len(hxs)), int(hxs[0] + .85 * len(hxs)), 7)
        for t in rng:
            line = hhp[t] if axis == 0 else hhp[:, t]
            msk = hbase[t] if axis == 0 else hbase[:, t]
            v = line[msk]
            if len(v) < 120:
                continue
            v = v - v.mean(); d = float((v * v).mean())
            if d <= 0:
                continue
            vals.append([float((v[:-k] * v[k:]).mean()) / d for k in range(1, n + 1)])
        return np.array(vals).mean(0) if vals else np.zeros(n)
    hax = hacorr(0); hay = hacorr(1)

    def clen(ac):
        prev = 1.0
        for k, v in enumerate(ac, start=1):
            if v < math.e ** -1:
                return k - 1 + (prev - math.e ** -1) / max(prev - v, 1e-9)
            prev = v
        return float(len(ac))
    OUT['HR_subpixel_character'] = dict(
        _authority="CHARACTER ONLY - never a position, size, weight, colour or shape",
        ppmm=round(float(hppmm), 3),
        grain_amplitude_pct=round(100 * hamp, 2),
        grain_cell_x_mm=round(clen(hax) / hppmm, 4),
        grain_cell_y_mm=round(clen(hay) / hppmm, 4),
        grain_anisotropy=round(max(clen(hax), clen(hay)) / max(1e-6, min(clen(hax), clen(hay))), 3),
        acorr_x=[round(float(v), 4) for v in hax],
        acorr_y=[round(float(v), 4) for v in hay],
    )
    # kasure hole shape inside the ring, on HR - SHAPE ONLY
    rz = np.zeros((Hh, Wh), bool)
    rz[int(hys[0] + .24 * len(hys)):int(hys[0] + .67 * len(hys)),
       int(hxs[0] + .06 * len(hxs)):int(hxs[0] + .94 * len(hxs))] = True
    ralpha = np.clip((hrex - float(np.median(hrex[hbase]))) /
                     (float(np.percentile(hrex[hm], 99.5)) - float(np.median(hrex[hbase]))), 0, 1)
    rmask = rz & (ralpha > .5)
    env = R.close_(rmask, 6)
    holes = env & ~rmask
    labo, compo = R.label(holes)
    dims = []
    for c in compo:
        if c['n'] < 3:
            continue
        w_ = c['x1'] - c['x0'] + 1; h_ = c['y1'] - c['y0'] + 1
        dims.append((max(w_, h_) / hppmm, min(w_, h_) / hppmm, c['n'] / (hppmm ** 2)))
    if dims:
        OUT['HR_subpixel_character'].update(
            kasure_hole_count=len(dims),
            kasure_hole_median_long_mm=round(float(np.median([d[0] for d in dims])), 4),
            kasure_hole_median_short_mm=round(float(np.median([d[1] for d in dims])), 4),
            kasure_hole_median_elongation=round(float(np.median([d[0] / max(d[1], 1e-6) for d in dims])), 3),
            kasure_hole_area_frac=round(float(sum(d[2] for d in dims)) /
                                        max(1e-6, float(env.sum()) / (hppmm ** 2)), 4))
    # stroke-edge roughness on HR: deviation of a black stroke edge from its local line
    hdist = chamfer(hink)
    edge = (hdist > 0) & (hdist <= 1)
    OUT['HR_subpixel_character']['ink_edge_ramp_px'] = None
    ramp = []
    for d0 in range(0, 6):
        sel = hm & (hdist >= d0) & (hdist < d0 + 1)
        if sel.sum() > 200:
            ramp.append([d0, round(float(np.median(hlu[sel])), 4)])
    OUT['HR_subpixel_character']['ink_edge_ramp'] = ramp
    OUT['HR_subpixel_character']['ink_edge_ramp_mm_per_px'] = round(1.0 / hppmm, 4)

    with open(os.path.join(HERE, "rg_s5_detail.json"), "w", encoding="utf-8") as fh:
        json.dump(OUT, fh, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in OUT.items() if k != 'columns'}, indent=1, ensure_ascii=False)[:9000])


main()
