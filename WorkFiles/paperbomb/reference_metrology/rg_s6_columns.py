# -*- coding: utf-8 -*-
"""STAGE 6 - the four columns, split at the necks, and the flame's stroke ladder.
METROLOGY ONLY.  The glyphs in a column TOUCH (leading ~0.3 mm), so a split on
empty rows returns one blob; this splits on the row-ink valleys instead.
"""
import json
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

    fl = XL + S3['rules']['L']['inset_px']; fr = XR - 1 - S3['rules']['R']['inset_px']

    def zm(x0f, x1f, y0f, y1f):
        z = np.zeros((H, W), bool)
        z[int(YT + y0f * HPX):int(YT + y1f * HPX), int(XL + x0f * WPX):int(XL + x1f * WPX)] = True
        return z

    rule_band = np.zeros((H, W), bool)
    for cen_, vert in ((fl, True), (fr, True),):
        x = int(round(cen_)); rule_band[:, max(0, x - 2):x + 3] = True

    CDEF = dict(
        col_TL_hidonjutsu=(.04, .28, .015, .36, 3),
        col_TR_bakuenjin=(.70, .96, .015, .36, 3),
        col_BR_shoujin=(.70, .96, .625, .83, 2),
        col_BC_shungou=(.36, .64, .68, .93, 2),
    )
    cols = {}
    for nm, (x0f, x1f, y0f, y1f, nglyph) in CDEF.items():
        m = black & zm(x0f, x1f, y0f, y1f) & ~rule_band
        lab, comps = R.label(R.dilate(m, 1))
        keep = np.zeros((H, W), bool)
        for c in comps:
            if a2mm2(int((m & (lab == c['label'])).sum())) > 2.0:
                keep |= m & (lab == c['label'])
        ys = np.flatnonzero(keep.any(1))
        y0, y1 = int(ys[0]), int(ys[-1])
        rowsum = keep[y0:y1 + 1].sum(1).astype(float)
        # valleys: pick the nglyph-1 deepest local minima, at least 6 px apart
        # the column is evenly set, so cut k lives near k/nglyph of its height;
        # search a +-12 % window there for the row with the least ink.
        L = len(rowsum)
        cuts = []
        for k in range(1, nglyph):
            c0 = int(k * L / nglyph)
            wlo = max(1, c0 - int(.12 * L)); whi = min(L - 1, c0 + int(.12 * L))
            cuts.append(int(wlo + np.argmin(rowsum[wlo:whi])))
        cuts.sort()
        bounds = [0] + cuts + [len(rowsum)]
        glyphs = []
        for k in range(len(bounds) - 1):
            g = keep.copy()
            g[:y0 + bounds[k]] = False
            g[y0 + bounds[k + 1]:] = False
            if a2mm2(int(g.sum())) < 5.0:
                continue
            b = boxof(g, nm + "_%d" % k)
            b['em_mm'] = round(max(b['w_mm'], b['h_mm']), 3)
            b['neck_ink_px'] = int(rowsum[bounds[k + 1]]) if k + 1 < len(bounds) - 1 else None
            glyphs.append(b)
        whole = boxof(keep, nm)
        pitches = [round(glyphs[i + 1]['cy_mm'] - glyphs[i]['cy_mm'], 3) for i in range(len(glyphs) - 1)]
        cols[nm] = dict(
            whole=whole, n_glyphs=len(glyphs), glyphs=glyphs,
            axis_x_mm=round(float(np.mean([g['cx_mm'] for g in glyphs])), 3),
            axis_x_f=round(float(np.mean([g['cx_f'] for g in glyphs])), 5),
            em_mean_mm=round(float(np.mean([g['em_mm'] for g in glyphs])), 3),
            em_min_mm=round(float(min(g['em_mm'] for g in glyphs)), 3),
            em_max_mm=round(float(max(g['em_mm'] for g in glyphs)), 3),
            cell_w_mean_mm=round(float(np.mean([g['w_mm'] for g in glyphs])), 3),
            cell_w_f=round(float(np.mean([g['w_f'] for g in glyphs])), 5),
            pitch_mm=pitches,
            pitch_mean_mm=round(float(np.mean(pitches)), 3) if pitches else None,
            clear_of_own_rule_mm=(round(whole['x0_mm'] - mmx(fl), 3) if 'TL' in nm
                                  else round(mmx(fr) - whole['x1_mm'], 3) if 'BC' not in nm
                                  else None),
        )
    OUT['columns'] = cols

    # ----------------------------------------------------- flame stroke ladder
    fm = black & zm(.28, .72, .09, .28)
    lab, comps = R.label(R.dilate(fm, 1))
    keep = np.zeros((H, W), bool)
    for c in comps:
        s = fm & (lab == c['label'])
        if a2mm2(int(s.sum())) >= 3.0:
            keep |= s
    ys = np.flatnonzero(keep.any(1))
    ladder = []
    for frac in (.10, .20, .30, .40, .50, .60, .70, .80, .90):
        y = int(ys[0] + frac * (ys[-1] - ys[0]))
        idx = np.flatnonzero(keep[y])
        if len(idx) == 0:
            ladder.append([round(frac, 2), []]); continue
        runs = []; cur = 1
        for i in range(1, len(idx)):
            if idx[i] == idx[i - 1] + 1:
                cur += 1
            else:
                runs.append(cur); cur = 1
        runs.append(cur)
        ladder.append([round(frac, 2), [round(p2mm(r), 2) for r in runs]])
    OUT['flame_run_ladder'] = ladder
    # spiral heart: the lowest/central part, its turns
    heart = keep & zm(.40, .60, .155, .27)
    OUT['flame_heart'] = boxof(heart, "flame_heart")
    # vertical scan through the heart's centre: alternating ink/paper = turns
    hb = OUT['flame_heart']
    if hb.get('present'):
        xcen = int(round(XL + ((hb['cx_mm'] / CARD_W)) * WPX))
        col = keep[:, xcen]
        ysh = np.flatnonzero(col)
        seq = []
        if len(ysh):
            cur = col[ysh[0]]; run = 0
            for y in range(ysh[0], ysh[-1] + 1):
                if col[y] == cur:
                    run += 1
                else:
                    seq.append([bool(cur), round(p2mm(run), 2)]); cur = col[y]; run = 1
            seq.append([bool(cur), round(p2mm(run), 2)])
        OUT['flame_heart_vertical_scan'] = seq
    # enclosed voids at n>=1
    filled = R.fill_holes(keep)
    eye = filled & ~keep
    labe, compe = R.label(eye)
    OUT['flame_enclosed_voids'] = [dict(mm2=round(a2mm2(c['n']), 3),
                                        cx_mm=round(mmx(c['cx']), 2), cy_mm=round(mmy(c['cy']), 2),
                                        w_mm=round(p2mm(c['x1'] - c['x0'] + 1), 2),
                                        h_mm=round(p2mm(c['y1'] - c['y0'] + 1), 2))
                                   for c in compe[:6]]
    # stray specks anywhere in the emblem zone (the delta report mentions two)
    small = [c for c in comps if 0 < a2mm2(int((fm & (lab == c['label'])).sum())) < 3.0]
    OUT['flame_specks_under_3mm2'] = [round(a2mm2(int((fm & (lab == c['label'])).sum())), 3)
                                      for c in small]

    with open(os.path.join(HERE, "rg_s6_columns.json"), "w", encoding="utf-8") as fh:
        json.dump(OUT, fh, indent=1, ensure_ascii=False)
    for nm, c in cols.items():
        print(nm, 'axis', c['axis_x_mm'], c['axis_x_f'], 'n', c['n_glyphs'], 'em',
              c['em_min_mm'], c['em_mean_mm'], c['em_max_mm'], 'cellw', c['cell_w_mean_mm'],
              'pitch', c['pitch_mm'], 'clear', c['clear_of_own_rule_mm'])
        w = c['whole']
        print('   whole x%.2f-%.2f y%.2f-%.2f w%.2f h%.2f area%.1f' %
              (w['x0_mm'], w['x1_mm'], w['y0_mm'], w['y1_mm'], w['w_mm'], w['h_mm'], w['area_mm2']))
        for g in c['glyphs']:
            print('     %-22s %6.1f mm2 x%.2f-%.2f y%.2f-%.2f w%.2f h%.2f em%.2f c(%.2f,%.2f)' %
                  (g['name'], g['area_mm2'], g['x0_mm'], g['x1_mm'], g['y0_mm'], g['y1_mm'],
                   g['w_mm'], g['h_mm'], g['em_mm'], g['cx_mm'], g['cy_mm']))
    print('LADDER', json.dumps(OUT['flame_run_ladder']))
    print('HEART', json.dumps(OUT['flame_heart']))
    print('HEARTSCAN', json.dumps(OUT.get('flame_heart_vertical_scan')))
    print('VOIDS', json.dumps(OUT['flame_enclosed_voids']))
    print('SPECKS', json.dumps(OUT['flame_specks_under_3mm2']))


main()
