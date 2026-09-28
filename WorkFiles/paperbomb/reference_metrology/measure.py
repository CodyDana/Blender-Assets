# -*- coding: utf-8 -*-
"""PaperBomb LAYOUT metrology - measures V1, V2 and our shipped base colour.
MEASUREMENT ONLY. Emits numbers; writes no artwork a build could consume.
Canonical space: 980 x 2184 px = 70.0 x 156.0 mm at 14 px/mm, origin at the
TAG's top-left virtual corner, x right, y down."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import lib_metro as L
import lib_tag as T

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"
BCP = r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png"
OUTD = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/reference_metrology"
DBG = os.path.join(OUTD, "debug")
CW, CH, PPMM = T.CW, T.CH, T.PPMM


def mm(px):      return px / PPMM
def fx(px):      return px / CW
def fy(px):      return px / CH
def pair_x(px):  return dict(px=round(float(px), 2), fW=round(float(px) / CW, 5), mm=round(float(px) / PPMM, 3))
def pair_y(px):  return dict(px=round(float(px), 2), fH=round(float(px) / CH, 5), mm=round(float(px) / PPMM, 3))


def box(x0, x1, y0, y1):
    return dict(x0=pair_x(x0), x1=pair_x(x1), y0=pair_y(y0), y1=pair_y(y1),
                w=pair_x(x1 - x0 + 1), h=pair_y(y1 - y0 + 1))


# ------------------------------------------------------------- classification
def classify(rgb):
    lu = L.lum(rgb)
    gb = 0.5 * (rgb[..., 1] + rgb[..., 2])
    ratio = rgb[..., 0] / np.maximum(gb, 0.02)
    paper_lum = float(np.percentile(lu, 60))
    ink_lum = float(np.percentile(lu[lu < np.percentile(lu, 12)], 50))
    thr_ink = 0.5 * (paper_lum + ink_lum)
    red = ratio > 1.55
    ink = (lu < thr_ink) | red
    black = ink & ~red
    return dict(red=red, black=black, ink=ink, lum=lu, ratio=ratio,
                paper_lum=paper_lum, ink_lum=ink_lum, thr_ink=thr_ink)


def runs(row):
    d = np.diff(row.astype(np.int8))
    s = list(np.nonzero(d == 1)[0] + 1); e = list(np.nonzero(d == -1)[0] + 1)
    if row[0]: s.insert(0, 0)
    if row[-1]: e.append(len(row))
    return list(zip(s, e))


# ----------------------------------------------------------------- outline
def fit_tls(pts):
    p = np.asarray(pts, float)
    c = p.mean(0)
    u, s, vt = np.linalg.svd(p - c)
    d = vt[0]                      # direction
    n = np.array([-d[1], d[0]])    # normal
    res = (p - c) @ n
    return c, d, n, float(np.sqrt((res ** 2).mean())), float(np.abs(res).max())


def measure_outline(q, sw, sh):
    """q from lib_tag.fit_quad on the NATIVE image. sw/sh = native tag W/H px."""
    kx = CW / sw; ky = CH / sh        # native px -> canonical px
    o = {}
    o['source_tag_px'] = dict(W=round(sw, 3), H=round(sh, 3), aspect=round(sw / sh, 5))
    o['aspect_vs_card'] = round(sw / sh / (70.0 / 156.0) - 1.0, 5)
    # rotation / keystone
    tilt_l = math.degrees(math.atan(q['aL'])); tilt_r = math.degrees(math.atan(q['aR']))
    tilt_t = math.degrees(math.atan(q['aT'])); tilt_b = math.degrees(math.atan(q['aB']))
    wt = q['TR'][0] - q['TL'][0]; wb = q['BR'][0] - q['BL'][0]
    hl = q['BL'][1] - q['TL'][1]; hr = q['BR'][1] - q['TR'][1]
    o['rectification'] = dict(
        left_edge_deg_from_vertical=round(tilt_l, 4),
        right_edge_deg_from_vertical=round(tilt_r, 4),
        top_edge_deg_from_horizontal=round(tilt_t, 4),
        bottom_edge_deg_from_horizontal=round(tilt_b, 4),
        mean_rotation_deg=round((tilt_t + tilt_b) / 2 - (tilt_l + tilt_r) / 2, 4),
        keystone_top_vs_bottom_width_pct=round(100 * (wb - wt) / wt, 3),
        keystone_left_vs_right_height_pct=round(100 * (hr - hl) / hl, 3),
        applied="perspective warp of the fitted edge quad to a 980x2184 rectangle")
    # edge irregularity
    irr = {}
    for k, r, scale in (('left', q['resL'], kx), ('right', q['resR'], kx),
                        ('top', q['resT'], ky), ('bottom', q['resB'], ky)):
        r = np.asarray(r, float) * scale
        rms = float(np.sqrt((r ** 2).mean()))
        nick = int((np.abs(r) > max(3 * rms, 1.0)).sum())
        irr[k] = dict(rms_px=round(rms, 3), rms_mm=round(mm(rms), 4),
                      max_dev_px=round(float(np.abs(r).max()), 3),
                      max_dev_mm=round(mm(float(np.abs(r).max())), 4),
                      n_outliers_gt3rms=nick, n_samples=int(r.size))
    o['edge_irregularity'] = irr
    # corner clips, in native px then converted
    clips = {}
    left, right, top, bot = q['left'], q['right'], q['top'], q['bot']
    lineL = lambda y: q['aL'] * y + q['bL']
    lineR = lambda y: q['aR'] * y + q['bR'] - 1.0
    lineT = lambda x: q['aT'] * x + q['bT']
    lineB = lambda x: q['aB'] * x + q['bB'] - 1.0
    ys = np.arange(len(left), dtype=float); xs = np.arange(len(top), dtype=float)
    cy0, cy1 = q['yspan']; cx0, cx1 = q['xspan']
    span_y = int(0.22 * (cy1 - cy0)); span_x = int(0.42 * (cx1 - cx0))
    for name, (hprof, hline, hrange, hsign), (vprof, vline, vrange, vsign) in (
        ('TL', (top, lineT, range(cx0, cx0 + span_x), +1), (left, lineL, range(cy0, cy0 + span_y), +1)),
        ('TR', (top, lineT, range(cx1, cx1 - span_x, -1), +1), (right, lineR, range(cy0, cy0 + span_y), -1)),
        ('BL', (bot, lineB, range(cx0, cx0 + span_x), -1), (left, lineL, range(cy1, cy1 - span_y, -1), +1)),
        ('BR', (bot, lineB, range(cx1, cx1 - span_x, -1), -1), (right, lineR, range(cy1, cy1 - span_y, -1), -1)),
    ):
        pts = []
        for x in hrange:
            v = hprof[x]
            if not np.isnan(v) and hsign * (v - hline(x)) > 1.5:
                pts.append((x, v))
        for y in vrange:
            v = vprof[y]
            if not np.isnan(v) and vsign * (v - vline(y)) > 1.5:
                pts.append((v, y))
        if len(pts) < 6:
            clips[name] = dict(note="no clip detected")
            continue
        c, d, n, rms, mx = fit_tls(pts)
        # intersect fitted clip line with the two edge lines
        def isect_with(av, bv, horiz):
            if horiz:      # y = av*x + bv
                den = d[1] - av * d[0]
                t = (av * c[0] + bv - c[1]) / den if abs(den) > 1e-12 else 0.0
            else:          # x = av*y + bv
                den = d[0] - av * d[1]
                t = (av * c[1] + bv - c[0]) / den if abs(den) > 1e-12 else 0.0
            return c + t * d
        Ph = isect_with(q['aT'] if 'T' in name else q['aB'],
                        q['bT'] if 'T' in name else q['bB'] - 1.0, True)
        Pv = isect_with(q['aL'] if 'L' in name else q['aR'],
                        q['bL'] if 'L' in name else q['bR'] - 1.0, False)
        corner = np.array(q[name], float)
        # convert to canonical
        Phc = np.array([Ph[0] * kx, Ph[1] * ky]) - np.array([q['TL'][0] * kx, q['TL'][1] * ky])
        Pvc = np.array([Pv[0] * kx, Pv[1] * ky]) - np.array([q['TL'][0] * kx, q['TL'][1] * ky])
        cut_h = abs(Ph[0] - corner[0]) * kx     # along the horizontal edge
        cut_v = abs(Pv[1] - corner[1]) * ky     # along the vertical edge
        chord = math.hypot(Phc[0] - Pvc[0], Phc[1] - Pvc[1])
        ang = math.degrees(math.atan2(cut_v, cut_h))   # from the horizontal edge
        clips[name] = dict(
            cut_along_top_or_bottom_edge=pair_x(cut_h),
            cut_along_side_edge=pair_y(cut_v),
            chord_len_px=round(chord, 2), chord_len_mm=round(mm(chord), 3),
            chord_angle_deg_from_horizontal_edge=round(ang, 3),
            straightness_rms_px=round(rms * (kx + ky) / 2, 3),
            straightness_max_dev_px=round(mx * (kx + ky) / 2, 3),
            n_boundary_samples=len(pts))
    o['corner_clips'] = clips
    cl = [clips[k] for k in ('TL', 'TR', 'BL', 'BR') if 'chord_len_mm' in clips[k]]
    if len(cl) == 4:
        ch = [c['chord_len_mm'] for c in cl]
        o['corner_clip_symmetry'] = dict(
            chords_mm=ch, mean_mm=round(float(np.mean(ch)), 3),
            spread_mm=round(float(max(ch) - min(ch)), 3),
            spread_pct=round(100 * (max(ch) - min(ch)) / float(np.mean(ch)), 2),
            angles_deg=[c['chord_angle_deg_from_horizontal_edge'] for c in cl])
    return o


# ------------------------------------------------------------- border rules
def measure_rules(red, ink):
    out = {}
    for side in ('left', 'right', 'top', 'bottom'):
        vert = side in ('left', 'right')
        n_along = CH if vert else CW
        lim = int(0.16 * CW) if vert else int(0.10 * CH)
        cen, wid, at = [], [], []
        for i in range(0, n_along, 2):
            if side == 'left':   line = red[i, :lim]
            elif side == 'right': line = red[i, CW - lim:][::-1]
            elif side == 'top':   line = red[:lim, i]
            else:                 line = red[CH - lim:, i][::-1]
            r = runs(line)
            if not r:
                continue
            a, b = r[0]
            if a > (0.13 * CW if vert else 0.085 * CH):
                continue
            cen.append((a + b) / 2.0); wid.append(b - a); at.append(i)
        if len(cen) < 20:
            out[side] = dict(note='rule not found'); continue
        cen = np.array(cen); wid = np.array(wid); at = np.array(at)
        # trim the corner-flourish ends: keep the central 80% of the span
        lo, hi = int(0.12 * n_along), int(0.88 * n_along)
        sel = (at >= lo) & (at <= hi)
        c2, w2, a2 = cen[sel], wid[sel], at[sel]
        med = float(np.median(c2))
        core = np.abs(c2 - med) < 0.30 * PPMM * 6
        c2, w2, a2 = c2[core], w2[core], a2[core]
        # wobble: deviation from a straight least-squares line along the rule
        A = np.stack([a2.astype(float), np.ones_like(a2, float)], 1)
        sol, *_ = np.linalg.lstsq(A, c2, rcond=None)
        dev = c2 - A @ sol
        pos = pair_x if vert else pair_y
        out[side] = dict(
            inset_from_edge=pos(med),
            inset_p10=pos(float(np.percentile(c2, 10))), inset_p90=pos(float(np.percentile(c2, 90))),
            stroke_w_med=pos(float(np.median(w2))),
            stroke_w_p10=pos(float(np.percentile(w2, 10))),
            stroke_w_p90=pos(float(np.percentile(w2, 90))),
            stroke_w_max=pos(float(w2.max())),
            stroke_w_min=pos(float(w2.min())),
            stroke_w_ratio_p90_p10=round(float(np.percentile(w2, 90) / max(np.percentile(w2, 10), 0.5)), 2),
            wobble_rms=pos(float(np.sqrt((dev ** 2).mean()))),
            wobble_max=pos(float(np.abs(dev).max())),
            drift_over_length=pos(float(sol[0] * (a2.max() - a2.min()))),
            coverage_frac=round(len(at[sel]) / max(1, len(range(lo, hi, 2))), 3),
            extent_start=(pair_y if vert else pair_x)(float(at.min())),
            extent_end=(pair_y if vert else pair_x)(float(at.max())),
            extent_len=(pair_y if vert else pair_x)(float(at.max() - at.min())),
            n_samples=int(len(c2)))
        # second rule?
        c3, w3 = [], []
        for i in range(lo, hi, 2):
            if side == 'left':   line = red[i, :lim]
            elif side == 'right': line = red[i, CW - lim:][::-1]
            elif side == 'top':   line = red[:lim, i]
            else:                 line = red[CH - lim:, i][::-1]
            r = runs(line)
            if len(r) > 1:
                a, b = r[1]
                if a < (0.14 * CW if vert else 0.09 * CH):
                    c3.append((a + b) / 2.0); w3.append(b - a)
        if len(c3) > 0.35 * len(range(lo, hi, 2)):
            c3 = np.array(c3); w3 = np.array(w3)
            out[side]['second_rule'] = dict(
                inset_from_edge=pos(float(np.median(c3))),
                stroke_w_med=pos(float(np.median(w3))),
                gap_to_outer_rule=pos(float(np.median(c3) - med)),
                present_frac=round(len(c3) / len(range(lo, hi, 2)), 3))
        else:
            out[side]['second_rule'] = None
    return out


# ------------------------------------------------- clusters + element naming
def cluster(mask, rad, min_px):
    d = L.dilate(mask, rad)
    lab, _ = L.label_components(d)
    ids = np.unique(lab[mask])
    out = []
    for i in ids:
        if i == 0: continue
        sel = mask & (lab == i)
        ys, xs = np.nonzero(sel)
        if len(xs) < min_px: continue
        out.append(dict(n=int(len(xs)), x0=int(xs.min()), x1=int(xs.max()),
                        y0=int(ys.min()), y1=int(ys.max()),
                        cx=float(xs.mean()), cy=float(ys.mean()), mask=sel))
    out.sort(key=lambda d: -d['n'])
    return out


def elem(c_list):
    xs0 = min(c['x0'] for c in c_list); xs1 = max(c['x1'] for c in c_list)
    ys0 = min(c['y0'] for c in c_list); ys1 = max(c['y1'] for c in c_list)
    n = sum(c['n'] for c in c_list)
    cx = sum(c['cx'] * c['n'] for c in c_list) / n
    cy = sum(c['cy'] * c['n'] for c in c_list) / n
    d = box(xs0, xs1, ys0, ys1)
    d.update(centroid_x=pair_x(cx), centroid_y=pair_y(cy),
             ink_px=int(n), ink_mm2=round(n / (PPMM * PPMM), 3),
             fill_of_bbox=round(n / float((xs1 - xs0 + 1) * (ys1 - ys0 + 1)), 4),
             n_parts=len(c_list))
    return d


def ring_geom(m):
    ys, xs = np.nonzero(m)
    cx, cy = xs.mean(), ys.mean()
    ang = np.arctan2(ys - cy, xs - cx)
    rad = np.hypot(xs - cx, ys - cy)
    nb = 180
    bi = ((ang + math.pi) / (2 * math.pi) * nb).astype(int) % nb
    ro = np.full(nb, np.nan); ri = np.full(nb, np.nan)
    for b in range(nb):
        s = rad[bi == b]
        if len(s) > 3:
            ro[b] = np.percentile(s, 99); ri[b] = np.percentile(s, 1)
    ok = ~np.isnan(ro)
    th = (np.arange(nb) + 0.5) / nb * 2 * math.pi - math.pi
    # ellipse: r_out ~ a + b*cos(2*theta)
    A = np.stack([np.ones(ok.sum()), np.cos(2 * th[ok]), np.sin(2 * th[ok])], 1)
    sol, *_ = np.linalg.lstsq(A, ro[ok], rcond=None)
    thick = ro[ok] - ri[ok]
    return dict(
        centre_x=pair_x(cx), centre_y=pair_y(cy),
        outer_r_med=pair_x(float(np.nanmedian(ro))),
        outer_r_min=pair_x(float(np.nanmin(ro))), outer_r_max=pair_x(float(np.nanmax(ro))),
        inner_r_med=pair_x(float(np.nanmedian(ri))),
        thickness_med=pair_x(float(np.median(thick))),
        thickness_p10=pair_x(float(np.percentile(thick, 10))),
        thickness_p90=pair_x(float(np.percentile(thick, 90))),
        thickness_max=pair_x(float(thick.max())),
        angular_coverage=round(float(ok.mean()), 3),
        ellipse_mean_r_px=round(float(sol[0]), 2),
        ellipse_cos2_amp_px=round(float(math.hypot(sol[1], sol[2])), 2),
        ellipse_ecc_pct=round(100 * float(math.hypot(sol[1], sol[2])) / float(sol[0]), 2),
        ellipse_major_axis_deg=round(math.degrees(0.5 * math.atan2(sol[2], sol[1])), 2),
        ink_frac_of_annulus=round(float(m.sum()) /
                                  max(1.0, math.pi * (np.nanmedian(ro) ** 2 - np.nanmedian(ri) ** 2)), 3))


def measure_source(name, path, ours=False):
    a = L.load_stored(path)
    m = T.tag_mask_ours(a, 940) if ours else T.tag_mask_ref(a)
    q = T.fit_quad(m)
    sw = q['TR'][0] - q['TL'][0]; sh = q['BL'][1] - q['TL'][1]
    rect, _ = T.rectify(a, q)
    cls = classify(rect)
    red, black, ink = cls['red'], cls['black'], cls['ink']
    R = dict(source=os.path.basename(path), image_px=[int(a.shape[1]), int(a.shape[0])])
    R['ink_levels_stored_srgb'] = dict(
        paper_lum_p60=round(cls['paper_lum'], 4), ink_lum_p50_of_darkest=round(cls['ink_lum'], 4),
        threshold_used=round(cls['thr_ink'], 4),
        paper_rgb=[round(float(v), 4) for v in rect[~ink].reshape(-1, 3).mean(0)],
        black_rgb=[round(float(v), 4) for v in rect[black].reshape(-1, 3).mean(0)],
        red_rgb=[round(float(v), 4) for v in rect[red].reshape(-1, 3).mean(0)],
        red_coverage_pct=round(float(red.mean()) * 100, 3),
        black_coverage_pct=round(float(black.mean()) * 100, 3),
        total_ink_coverage_pct=round(float(ink.mean()) * 100, 3))
    R['outline'] = measure_outline(q, sw, sh)
    R['border_rules'] = measure_rules(red, ink)

    # ---- build a rule mask so it can be removed from the element search
    rule = np.zeros_like(red)
    for side in ('left', 'right', 'top', 'bottom'):
        d = R['border_rules'][side]
        if 'inset_from_edge' not in d: continue
        c = d['inset_from_edge']['px']; hw = max(4.0, d['stroke_w_max']['px'])
        if side == 'left':   rule[:, max(0, int(c - hw)):int(c + hw)] = True
        elif side == 'right': rule[:, CW - int(c + hw):CW - max(0, int(c - hw))] = True
        elif side == 'top':   rule[max(0, int(c - hw)):int(c + hw), :] = True
        else:                 rule[CH - int(c + hw):CH - max(0, int(c - hw)), :] = True
    inner = ~rule

    rad = max(1, int(round(1.1 * PPMM)))
    minpx = int(0.6 * PPMM * PPMM)
    bcl = cluster(black & inner, rad, minpx)
    rcl = cluster(red & inner, max(1, int(0.45 * PPMM)), minpx)

    print(f"\n===== {name}: black clusters =====")
    for c in bcl[:22]:
        print("  n=%7d bbox x[%4d,%4d] y[%4d,%4d] c=(%6.1f,%7.1f) fx[%.3f,%.3f] fy[%.3f,%.3f]"
              % (c['n'], c['x0'], c['x1'], c['y0'], c['y1'], c['cx'], c['cy'],
                 c['x0']/CW, c['x1']/CW, c['y0']/CH, c['y1']/CH))
    print(f"===== {name}: red clusters =====")
    for c in rcl[:22]:
        print("  n=%7d bbox x[%4d,%4d] y[%4d,%4d] c=(%6.1f,%7.1f) fx[%.3f,%.3f] fy[%.3f,%.3f] fill=%.2f"
              % (c['n'], c['x0'], c['x1'], c['y0'], c['y1'], c['cx'], c['cy'],
                 c['x0']/CW, c['x1']/CW, c['y0']/CH, c['y1']/CH,
                 c['n']/float((c['x1']-c['x0']+1)*(c['y1']-c['y0']+1))))

    # ---------------- element assignment ----------------
    big = [c for c in bcl if c['n'] > 6 * PPMM * PPMM]
    small = [c for c in bcl if c['n'] <= 6 * PPMM * PPMM]
    E = {}
    def pick(lst, pred):
        return [c for c in lst if pred(c['cx'] / CW, c['cy'] / CH, c)]
    centre = pick(big, lambda x, y, c: 0.28 < x < 0.72 and 0.32 < y < 0.72 and c['n'] > 40 * PPMM * PPMM)
    if centre: E['centre_char_bao'] = elem([max(centre, key=lambda c: c['n'])])
    used = {id(max(centre, key=lambda c: c['n']))} if centre else set()
    flame = pick(big, lambda x, y, c: 0.30 < x < 0.70 and 0.08 < y < 0.31 and id(c) not in used)
    if flame: E['flame_emblem'] = elem(flame)
    for key, pred in (
        ('col_upper_left_hi_ton_jutsu', lambda x, y: x < 0.38 and y < 0.55),
        ('col_upper_right_baku_en_jin', lambda x, y: x > 0.62 and y < 0.55),
        ('col_lower_right_shou_jin',    lambda x, y: x > 0.60 and y >= 0.55),
        ('col_lower_centre_shun_gou',   lambda x, y: 0.38 <= x <= 0.62 and y >= 0.55)):
        sel = [c for c in big if pred(c['cx'] / CW, c['cy'] / CH) and id(c) not in used]
        if sel: E[key] = elem(sel)
    # red elements
    ringc = [c for c in rcl if (c['x1'] - c['x0']) > 0.45 * CW and 0.25 < c['cy'] / CH < 0.62]
    if ringc:
        rc = max(ringc, key=lambda c: c['n'])
        E['red_ring'] = elem([rc]); E['red_ring']['geometry'] = ring_geom(rc['mask'])
    seals = [c for c in rcl if c['n'] > 25 * PPMM * PPMM and c['cy'] / CH > 0.55
             and c['n'] / float((c['x1']-c['x0']+1)*(c['y1']-c['y0']+1)) > 0.25]
    for c in seals:
        k = 'seal_box_large_left' if c['cx'] / CW < 0.5 else 'seal_box_small_right'
        E[k] = elem([c])
    R['elements'] = {k: {kk: vv for kk, vv in v.items() if kk != 'geometry'} | (
        {'geometry': v['geometry']} if 'geometry' in v else {}) for k, v in E.items()}

    # ---------------- corner flourishes ----------------
    fl = {}
    bx, by = int(0.28 * CW), int(0.125 * CH)
    for nm2, sx, sy in (('TL', slice(0, bx), slice(0, by)), ('TR', slice(CW - bx, CW), slice(0, by)),
                        ('BL', slice(0, bx), slice(CH - by, CH)), ('BR', slice(CW - bx, CW), slice(CH - by, CH))):
        sub = (red | (black & (cls['lum'] < 0.30)))[sy, sx]
        lab, comps = L.label_components(sub)
        if not comps: continue
        c = comps[0]
        ys, xs = np.nonzero(lab == c['label'])
        ox = sx.start; oy = sy.start
        X0, X1 = xs.min() + ox, xs.max() + ox
        Y0, Y1 = ys.min() + oy, ys.max() + oy
        # arm lengths measured from the corner-most extreme of the blob
        rl = R['border_rules']
        armh = (X1 - X0 + 1); armv = (Y1 - Y0 + 1)
        # stroke width = median run length across the blob, perpendicular
        wr = []
        for yy in range(ys.min(), ys.max() + 1, 2):
            rr = runs((lab == c['label'])[yy])
            wr += [b - a for a, b in rr]
        fl[nm2] = dict(bbox=box(X0, X1, Y0, Y1), ink_px=int(c['n']),
                       ink_mm2=round(c['n'] / (PPMM * PPMM), 3),
                       arm_h=pair_x(armh), arm_v=pair_y(armv),
                       stroke_w_med=pair_x(float(np.median(wr))),
                       stroke_w_p90=pair_x(float(np.percentile(wr, 90))),
                       reach_beyond_rule_x=pair_x(float(
                           (rl['left']['inset_from_edge']['px'] - X0) if 'L' in nm2
                           else (X1 - (CW - rl['right']['inset_from_edge']['px'])))),
                       reach_beyond_rule_y=pair_y(float(
                           (rl['top']['inset_from_edge']['px'] - Y0) if 'T' in nm2
                           else (Y1 - (CH - rl['bottom']['inset_from_edge']['px'])))))
    R['corner_flourishes'] = fl

    # ---------------- diamond / lozenge ornaments ----------------
    dia = []
    for colour, msk in (('red', red), ('black', black)):
        cl2 = cluster(msk, 2, int(0.35 * PPMM * PPMM))
        for c in cl2:
            w = c['x1'] - c['x0'] + 1; h = c['y1'] - c['y0'] + 1
            area = w * h
            fill = c['n'] / float(area)
            if not (0.25 * PPMM < w < 6.5 * PPMM and 0.4 * PPMM < h < 11 * PPMM):
                continue
            if fill < 0.34 or fill > 0.80:
                continue
            if h < w:
                continue
            dia.append(dict(colour=colour, cx=pair_x(c['cx']), cy=pair_y(c['cy']),
                            w=pair_x(w), h=pair_y(h), fill=round(fill, 3),
                            ink_mm2=round(c['n'] / (PPMM * PPMM), 3),
                            aspect_w_over_h=round(w / float(h), 3)))
    dia.sort(key=lambda d: (d['cy']['px'], d['cx']['px']))
    R['diamonds'] = dia
    R['diamond_count'] = len(dia)

    # ---------------- composition / optical centring ----------------
    content = ink & inner
    ys, xs = np.nonzero(content)
    R['composition'] = dict(
        content_bbox=box(int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())),
        content_centroid_x=pair_x(float(xs.mean())), content_centroid_y=pair_y(float(ys.mean())),
        offset_from_tag_centre_x=pair_x(float(xs.mean()) - CW / 2),
        offset_from_tag_centre_y=pair_y(float(ys.mean()) - CH / 2),
        bbox_centre_offset_x=pair_x((float(xs.min()) + float(xs.max())) / 2 - CW / 2),
        bbox_centre_offset_y=pair_y((float(ys.min()) + float(ys.max())) / 2 - CH / 2),
        margin_left=pair_x(float(xs.min())), margin_right=pair_x(CW - float(xs.max())),
        margin_top=pair_y(float(ys.min())), margin_bottom=pair_y(CH - float(ys.max())))
    # column mass balance
    colmass = content.sum(0).astype(float)
    R['composition']['ink_column_balance_left_minus_right_pct'] = round(
        100 * (colmass[:CW // 2].sum() - colmass[CW // 2:].sum()) / colmass.sum(), 2)
    rowmass = content.sum(1).astype(float)
    R['composition']['ink_row_balance_top_minus_bottom_pct'] = round(
        100 * (rowmass[:CH // 2].sum() - rowmass[CH // 2:].sum()) / rowmass.sum(), 2)

    # debug overlay with measured boxes
    ov = rect.copy()
    def rect_outline(x0, x1, y0, y1, col, t=3):
        x0 = max(0, int(x0)); x1 = min(CW - 1, int(x1)); y0 = max(0, int(y0)); y1 = min(CH - 1, int(y1))
        ov[y0:y0+t, x0:x1] = col; ov[y1-t:y1, x0:x1] = col
        ov[y0:y1, x0:x0+t] = col; ov[y0:y1, x1-t:x1] = col
    for k, v in E.items():
        rect_outline(v['x0']['px'], v['x1']['px'], v['y0']['px'], v['y1']['px'], np.array([0.0, 0.85, 0.1]))
    for k, v in fl.items():
        b = v['bbox']
        rect_outline(b['x0']['px'], b['x1']['px'], b['y0']['px'], b['y1']['px'], np.array([0.0, 0.4, 1.0]))
    for d in dia:
        rect_outline(d['cx']['px'] - d['w']['px']/2, d['cx']['px'] + d['w']['px']/2,
                     d['cy']['px'] - d['h']['px']/2, d['cy']['px'] + d['h']['px']/2,
                     np.array([1.0, 0.0, 1.0]), 2)
    L.save_debug_png(ov[::2, ::2], os.path.join(DBG, f"DEBUG_NEVER_SHIP_boxes_{name}.png"))
    return R


out = {}
out['_note'] = ("LAYOUT metrology of the PaperBomb reference. Numbers only - no artwork is "
                "derived from the guide images. Canonical space 980x2184 px = 70.0x156.0 mm "
                "(14 px/mm), origin at the TAG's top-left virtual corner, x right, y down. "
                "All colour values are STORED (file) values, i.e. sRGB-encoded 0..1, not linear.")
out['V1'] = measure_source('V1', os.path.join(REF, 'paperbomb_guide.png'))
out['V2'] = measure_source('V2', os.path.join(REF, 'paperbomb_guide_v2_real_glyphs.png'))
out['OURS'] = measure_source('OURS', BCP, ours=True)
with open(os.path.join(OUTD, 'layout.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print("\nWROTE layout.json")
