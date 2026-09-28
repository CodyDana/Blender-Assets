# -*- coding: utf-8 -*-
"""PaperBomb LAYOUT metrology (final pass).  MEASUREMENT ONLY - emits numbers.
No artwork is derived from the guide images; debug overlays are marked NEVER SHIP.
Canonical space: 980 x 2184 px = 70.0 x 156.0 mm at 14 px/mm, origin at the TAG's
top-left virtual corner, x right, y down.  Colours quoted are STORED file values
(sRGB-encoded 0..1), NOT linear."""
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

def mm(p):      return float(p) / PPMM
def px_x(p):    return dict(px=round(float(p), 2), fW=round(float(p) / CW, 5), mm=round(float(p) / PPMM, 3))
def px_y(p):    return dict(px=round(float(p), 2), fH=round(float(p) / CH, 5), mm=round(float(p) / PPMM, 3))
def box(x0, x1, y0, y1):
    return dict(x0=px_x(x0), x1=px_x(x1), y0=px_y(y0), y1=px_y(y1),
                w=px_x(x1 - x0 + 1), h=px_y(y1 - y0 + 1),
                cx=px_x((x0 + x1) / 2.0), cy=px_y((y0 + y1) / 2.0))

def classify(rgb):
    lu = L.lum(rgb)
    gb = 0.5 * (rgb[..., 1] + rgb[..., 2])
    ratio = rgb[..., 0] / np.maximum(gb, 0.02)
    paper_lum = float(np.percentile(lu, 60))
    ink_lum = float(np.percentile(lu[lu < np.percentile(lu, 12)], 50))
    thr = 0.5 * (paper_lum + ink_lum)
    red = ratio > 1.55
    ink = (lu < thr) | red
    return dict(red=red, black=ink & ~red, ink=ink, lum=lu,
                paper_lum=paper_lum, ink_lum=ink_lum, thr_ink=thr)

def runs(row):
    d = np.diff(row.astype(np.int8))
    s = list(np.nonzero(d == 1)[0] + 1); e = list(np.nonzero(d == -1)[0] + 1)
    if row[0]: s.insert(0, 0)
    if row[-1]: e.append(len(row))
    return list(zip(s, e))

def fit_tls(pts):
    p = np.asarray(pts, float); c = p.mean(0)
    _, _, vt = np.linalg.svd(p - c)
    d = vt[0]; n = np.array([-d[1], d[0]]); r = (p - c) @ n
    return c, d, float(np.sqrt((r ** 2).mean())), float(np.abs(r).max())

# ------------------------------------------------------------------- outline
def measure_outline(q, qm, sw, sh):
    kx, ky = CW / sw, CH / sh
    o = dict(source_tag_px=dict(W=round(sw, 3), H=round(sh, 3), aspect_W_over_H=round(sw / sh, 5)),
             card_aspect=round(70.0 / 156.0, 5),
             aspect_error_vs_card_pct=round(100 * (sw / sh / (70.0 / 156.0) - 1.0), 3),
             px_per_mm_of_source=dict(x=round(sw / 70.0, 3), y=round(sh / 156.0, 3)))
    tl, tr = math.degrees(math.atan(q['aL'])), math.degrees(math.atan(q['aR']))
    tt, tb = math.degrees(math.atan(q['aT'])), math.degrees(math.atan(q['aB']))
    wt = q['TR'][0] - q['TL'][0]; wb = q['BR'][0] - q['BL'][0]
    hl = q['BL'][1] - q['TL'][1]; hr = q['BR'][1] - q['TR'][1]
    o['rectification_applied'] = dict(
        left_edge_deg_off_vertical=round(tl, 4), right_edge_deg_off_vertical=round(tr, 4),
        top_edge_deg_off_horizontal=round(tt, 4), bottom_edge_deg_off_horizontal=round(tb, 4),
        net_rotation_deg=round(((tt + tb) / 2 - (tl + tr) / 2) / 1.0, 4),
        keystone_bottom_minus_top_width_pct=round(100 * (wb - wt) / wt, 3),
        keystone_right_minus_left_height_pct=round(100 * (hr - hl) / hl, 3),
        method="4 edge lines least-squares fitted to the outline, intersected for virtual "
               "corners, then a perspective warp of that quad onto 980x2184")
    irr = {}
    for k, r, s in (('left', q['resL'], kx), ('right', q['resR'], kx),
                    ('top', q['resT'], ky), ('bottom', q['resB'], ky)):
        r = np.asarray(r, float) * s
        rms = float(np.sqrt((r ** 2).mean())); mx = float(np.abs(r).max())
        irr[k] = dict(rms_px=round(rms, 3), rms_mm=round(mm(rms), 4),
                      max_dev_px=round(mx, 3), max_dev_mm=round(mm(mx), 4),
                      n_nicks_gt_3rms=int((np.abs(r) > max(3 * rms, 1.0)).sum()),
                      n_samples=int(r.size))
    o['edge_irregularity'] = irr
    o['subpixel_edge_refinement_px'] = q.get('refinement', {})
    clips = {}
    q = qm      # corner clips are measured against the binary-mask edge fit
    lineL = lambda y: q['aL'] * y + q['bL']
    lineR = lambda y: q['aR'] * y + q['bR'] - 1.0
    lineT = lambda x: q['aT'] * x + q['bT']
    lineB = lambda x: q['aB'] * x + q['bB'] - 1.0
    cy0, cy1 = q['yspan']; cx0, cx1 = q['xspan']
    sy = int(0.22 * (cy1 - cy0)); sx = int(0.42 * (cx1 - cx0))
    for nm, (hp, hl_, hr_, hs), (vp, vl_, vr_, vs) in (
        ('TL', (q['top'], lineT, range(cx0, cx0 + sx), +1), (q['left'], lineL, range(cy0, cy0 + sy), +1)),
        ('TR', (q['top'], lineT, range(cx1, cx1 - sx, -1), +1), (q['right'], lineR, range(cy0, cy0 + sy), -1)),
        ('BL', (q['bot'], lineB, range(cx0, cx0 + sx), -1), (q['left'], lineL, range(cy1, cy1 - sy, -1), +1)),
        ('BR', (q['bot'], lineB, range(cx1, cx1 - sx, -1), -1), (q['right'], lineR, range(cy1, cy1 - sy, -1), -1))):
        # walk CONTIGUOUSLY outward from the corner; stop at 3 consecutive
        # samples that sit on the straight edge, so distant nicks cannot leak in
        capH = 0.35 * (cy1 - cy0); capV = 0.45 * (cx1 - cx0)
        pts = []; below = 0; n_h = 0
        for x in hr_:
            v = hp[x]
            if np.isnan(v): continue
            dev = hs * (v - hl_(x))
            if dev > 1.0:
                below = 0; n_h += 1
                if dev < capH: pts.append((x, v))   # skip degenerate grazing columns
            else:
                below += 1
                if below >= 3: break
        below = 0; n_v = 0
        for y in vr_:
            v = vp[y]
            if np.isnan(v): continue
            dev = vs * (v - vl_(y))
            if dev > 1.0:
                below = 0; n_v += 1
                if dev < capV: pts.append((v, y))
            else:
                below += 1
                if below >= 3: break
        if len(pts) < 6:
            clips[nm] = dict(note="no clip detected"); continue
        c, d, rms, mx = fit_tls(pts)
        def isect(av, bv, horiz):
            if horiz:
                den = d[1] - av * d[0]; t = (av * c[0] + bv - c[1]) / den if abs(den) > 1e-12 else 0.0
            else:
                den = d[0] - av * d[1]; t = (av * c[1] + bv - c[0]) / den if abs(den) > 1e-12 else 0.0
            return c + t * d
        Ph = isect(q['aT'] if 'T' in nm else q['aB'], q['bT'] if 'T' in nm else q['bB'] - 1.0, True)
        Pv = isect(q['aL'] if 'L' in nm else q['aR'], q['bL'] if 'L' in nm else q['bR'] - 1.0, False)
        cor = np.array(q[nm], float)
        cut_h = abs(Ph[0] - cor[0]) * kx
        cut_v = abs(Pv[1] - cor[1]) * ky
        chord = math.hypot(cut_h, cut_v)
        clips[nm] = dict(cut_along_horizontal_edge=px_x(cut_h), cut_along_vertical_edge=px_y(cut_v),
                         cut_h_by_departure=px_x(n_h * kx), cut_v_by_departure=px_y(n_v * ky),
                         chord_len_px=round(chord, 2), chord_len_mm=round(mm(chord), 3),
                         chord_angle_deg_from_horizontal=round(math.degrees(math.atan2(cut_v, cut_h)), 3),
                         straightness_rms_px=round(rms * (kx + ky) / 2, 3),
                         straightness_max_dev_px=round(mx * (kx + ky) / 2, 3),
                         shape="straight bevel" if rms * (kx + ky) / 2 < 1.5 else "curved / irregular",
                         n_samples=len(pts))
    o['corner_clips'] = clips
    ok = [clips[k] for k in ('TL', 'TR', 'BL', 'BR') if 'chord_len_mm' in clips[k]]
    if len(ok) == 4:
        ch = [c['chord_len_mm'] for c in ok]
        o['corner_clip_symmetry'] = dict(
            chords_mm_TL_TR_BL_BR=ch, mean_mm=round(float(np.mean(ch)), 3),
            spread_mm=round(float(max(ch) - min(ch)), 3),
            spread_pct_of_mean=round(100 * (max(ch) - min(ch)) / float(np.mean(ch)), 2),
            angles_deg_TL_TR_BL_BR=[c['chord_angle_deg_from_horizontal'] for c in ok],
            cut_h_mm=[c['cut_along_horizontal_edge']['mm'] for c in ok],
            cut_v_mm=[c['cut_along_vertical_edge']['mm'] for c in ok])
    return o

# ------------------------------------------------------------- border rules
def measure_rules(red):
    out = {}; rule_mask = np.zeros_like(red)
    for side in ('left', 'right', 'top', 'bottom'):
        vert = side in ('left', 'right')
        n_along = CH if vert else CW
        lim = int(0.17 * CW) if vert else int(0.11 * CH)
        lo, hi = int(0.12 * n_along), int(0.72 * n_along) if vert else int(0.88 * n_along)
        if not vert: lo = int(0.12 * n_along)
        allruns = []   # (pos_along, centre, width, a, b)
        for i in range(0, n_along):
            if side == 'left':    line = red[i, :lim]
            elif side == 'right': line = red[i, CW - lim:][::-1]
            elif side == 'top':   line = red[:lim, i]
            else:                 line = red[CH - lim:, i][::-1]
            for a, b in runs(line):
                allruns.append((i, (a + b) / 2.0, b - a, a, b))
        # rules are THIN: reject fat runs (ring / seal / glyph intrusions)
        MAXW = 2.4 * PPMM
        sel = [r for r in allruns if lo <= r[0] <= hi and r[2] <= MAXW]
        nscan = max(1, hi - lo + 1)
        hist = np.zeros(lim + 2)
        for r in sel:
            hist[int(round(r[1]))] += 1
        k = np.ones(5) / 5.0
        sm = np.convolve(hist, k, mode='same')
        peaks = []
        for i in range(1, lim):
            if sm[i] >= sm[i - 1] and sm[i] > sm[i + 1] and hist[max(0, i - 4):i + 5].sum() >= 0.18 * nscan:
                if peaks and i - peaks[-1] < 0.55 * PPMM:
                    if sm[i] > sm[peaks[-1]]: peaks[-1] = i
                else:
                    peaks.append(i)
        glist = []
        for p in peaks:
            tol = 0.55 * PPMM
            members = [r for r in sel if abs(r[1] - p) <= tol]
            if len(members) < 0.18 * nscan: continue
            c0, c1 = p - tol, p + tol
            w = np.array([r[2] for r in members], float)
            cc = np.array([r[1] for r in members], float)
            aa = np.array([r[0] for r in members], float)
            A = np.stack([aa, np.ones_like(aa)], 1)
            sol, *_ = np.linalg.lstsq(A, cc, rcond=None)
            dev = cc - A @ sol
            P = px_x if vert else px_y
            Q = px_y if vert else px_x
            # breaks along the rule
            fullr = [r for r in allruns if c0 <= r[1] <= c1 and r[2] <= MAXW]
            pr = np.zeros(n_along, bool); pr[[int(r[0]) for r in fullr]] = True
            idx = np.nonzero(pr)[0]
            gaps = np.diff(idx)
            glist.append(dict(
                inset_from_tag_edge=P(float(np.median(cc))),
                inset_p5=P(float(np.percentile(cc, 5))), inset_p95=P(float(np.percentile(cc, 95))),
                stroke_w_med=P(float(np.median(w))), stroke_w_p10=P(float(np.percentile(w, 10))),
                stroke_w_p90=P(float(np.percentile(w, 90))), stroke_w_min=P(float(w.min())),
                stroke_w_max=P(float(w.max())),
                stroke_w_p90_over_p10=round(float(np.percentile(w, 90) / max(np.percentile(w, 10), 0.5)), 2),
                wobble_rms=P(float(np.sqrt((dev ** 2).mean()))), wobble_max=P(float(np.abs(dev).max())),
                straightness="straight" if np.sqrt((dev ** 2).mean()) < 0.10 * PPMM else "brush-wobbled",
                drift_end_to_end=P(float(sol[0] * (aa.max() - aa.min()))),
                coverage_frac_of_scanned=round(len(set(int(r[0]) for r in members)) / float(nscan), 3),
                extent_start=Q(float(idx.min())), extent_end=Q(float(idx.max())),
                extent_len=Q(float(idx.max() - idx.min() + 1)),
                n_breaks=int((gaps > 2).sum()),
                longest_break=Q(float(gaps.max() - 1)) if len(gaps) else Q(0.0)))
            for r in fullr:
                i, _, _, a, b = r
                if side == 'left':    rule_mask[int(i), int(a):int(b)] = True
                elif side == 'right': rule_mask[int(i), CW - int(b):CW - int(a)] = True
                elif side == 'top':   rule_mask[int(a):int(b), int(i)] = True
                else:                 rule_mask[CH - int(b):CH - int(a), int(i)] = True
        glist.sort(key=lambda d: d['inset_from_tag_edge']['px'])
        real = [g for g in glist if g['coverage_frac_of_scanned'] >= 0.45]
        other = [g for g in glist if g['coverage_frac_of_scanned'] < 0.45]
        out[side] = dict(n_rules=len(real), rules=real,
                         other_red_lines_in_band=other,
                         scan_window=dict(from_frac=round(lo / n_along, 3), to_frac=round(hi / n_along, 3)))
        if len(real) >= 2:
            out[side]['gap_between_rule1_and_rule2'] = (px_x if vert else px_y)(
                real[1]['inset_from_tag_edge']['px'] - real[0]['inset_from_tag_edge']['px'])
    return out, rule_mask

# --------------------------------------------------------------- clustering
def cluster(mask, rad, min_px):
    d = L.dilate(mask, rad) if rad else mask
    lab, _ = L.label_components(d)
    out = []
    for i in np.unique(lab[mask]):
        if i == 0: continue
        sel = mask & (lab == i)
        ys, xs = np.nonzero(sel)
        if len(xs) < min_px: continue
        out.append(dict(n=int(len(xs)), x0=int(xs.min()), x1=int(xs.max()),
                        y0=int(ys.min()), y1=int(ys.max()),
                        cx=float(xs.mean()), cy=float(ys.mean()), mask=sel))
    out.sort(key=lambda d: -d['n'])
    return out

def elem(cs):
    x0 = min(c['x0'] for c in cs); x1 = max(c['x1'] for c in cs)
    y0 = min(c['y0'] for c in cs); y1 = max(c['y1'] for c in cs)
    n = sum(c['n'] for c in cs)
    d = box(x0, x1, y0, y1)
    d.update(centroid_x=px_x(sum(c['cx'] * c['n'] for c in cs) / n),
             centroid_y=px_y(sum(c['cy'] * c['n'] for c in cs) / n),
             ink_px=int(n), ink_mm2=round(n / (PPMM * PPMM), 2),
             fill_of_bbox=round(n / float((x1 - x0 + 1) * (y1 - y0 + 1)), 4), n_parts=len(cs))
    return d

def ring_geom(m):
    ys, xs = np.nonzero(m)
    cx, cy = xs.mean(), ys.mean()
    nb = 180
    th = (np.arange(nb) + 0.5) / nb * 2 * math.pi - math.pi
    # iteratively re-centre on the mid-ring radius so gaps/splatter don't drag it
    for _ in range(8):
        ang = np.arctan2(ys - cy, xs - cx); rad = np.hypot(xs - cx, ys - cy)
        bi = ((ang + math.pi) / (2 * math.pi) * nb).astype(int) % nb
        rmid = np.full(nb, np.nan)
        for b in range(nb):
            s = rad[bi == b]
            if len(s) > 4:
                rmid[b] = 0.5 * (np.percentile(s, 98) + np.percentile(s, 2))
        ok = ~np.isnan(rmid)
        A = np.stack([np.ones(ok.sum()), np.cos(th[ok]), np.sin(th[ok])], 1)
        sol, *_ = np.linalg.lstsq(A, rmid[ok], rcond=None)
        cx += sol[1]; cy += sol[2]
        if abs(sol[1]) < 0.02 and abs(sol[2]) < 0.02:
            break
    ang = np.arctan2(ys - cy, xs - cx); rad = np.hypot(xs - cx, ys - cy)
    bi = ((ang + math.pi) / (2 * math.pi) * nb).astype(int) % nb
    ro = np.full(nb, np.nan); ri = np.full(nb, np.nan); cov = np.zeros(nb, bool)
    for b in range(nb):
        s = rad[bi == b]
        if len(s) > 4:
            ro[b] = np.percentile(s, 98); ri[b] = np.percentile(s, 2); cov[b] = True
    A = np.stack([np.ones(cov.sum()), np.cos(2 * th[cov]), np.sin(2 * th[cov])], 1)
    sol, *_ = np.linalg.lstsq(A, ro[cov], rcond=None)
    th_ = ro[cov] - ri[cov]
    return dict(centre_x=px_x(cx), centre_y=px_y(cy),
                centre_fit_method="iterative mid-ring re-centring (8 passes, 180 angular bins)",
                outer_r_med=px_x(float(np.nanmedian(ro))), outer_r_min=px_x(float(np.nanmin(ro))),
                outer_r_max=px_x(float(np.nanmax(ro))),
                outer_r_p10=px_x(float(np.nanpercentile(ro, 10))),
                outer_r_p25=px_x(float(np.nanpercentile(ro, 25))),
                outer_r_p75=px_x(float(np.nanpercentile(ro, 75))),
                outer_r_p90=px_x(float(np.nanpercentile(ro, 90))),
                outer_r_rms_raggedness=px_x(float(np.nanstd(ro))),
                inner_r_med=px_x(float(np.nanmedian(ri))),
                outer_diameter=px_x(2 * float(np.nanmedian(ro))),
                thickness_med=px_x(float(np.median(th_))), thickness_p10=px_x(float(np.percentile(th_, 10))),
                thickness_p90=px_x(float(np.percentile(th_, 90))), thickness_max=px_x(float(th_.max())),
                thickness_p90_over_p10=round(float(np.percentile(th_, 90) / max(np.percentile(th_, 10), .5)), 2),
                angular_coverage=round(float(cov.mean()), 3),
                ellipse_mean_r_px=round(float(sol[0]), 2),
                ellipse_cos2_amp_px=round(float(math.hypot(sol[1], sol[2])), 2),
                ellipse_ellipticity_pct=round(100 * math.hypot(sol[1], sol[2]) / float(sol[0]), 2),
                ellipse_major_axis_deg=round(math.degrees(0.5 * math.atan2(sol[2], sol[1])), 2),
                ink_fill_of_annulus=round(float(m.sum()) / max(1.0, math.pi *
                                    (float(np.nanmedian(ro)) ** 2 - float(np.nanmedian(ri)) ** 2)), 3))

# ------------------------------------------------------------------ measure
def measure_source(name, path, ours=False):
    a = L.load_stored(path)
    m = T.tag_mask_ours(a, 940) if ours else T.tag_mask_ref(a)
    qm = T.fit_quad(m)
    q = T.refine_edges(a, qm)
    sw = q['TR'][0] - q['TL'][0]; sh = q['BL'][1] - q['TL'][1]
    print(f"[{name}] mask quad W={qm['TR'][0]-qm['TL'][0]:.3f} H={qm['BL'][1]-qm['TL'][1]:.3f} "
          f"asp={(qm['TR'][0]-qm['TL'][0])/(qm['BL'][1]-qm['TL'][1]):.5f}  -> refined "
          f"W={sw:.3f} H={sh:.3f} asp={sw/sh:.5f}   shifts={q.get('refinement')}")
    rect, _ = T.rectify(a, q)
    c = classify(rect)
    red, black, ink = c['red'], c['black'], c['ink']
    R = dict(source_file=os.path.basename(path), image_px=[int(a.shape[1]), int(a.shape[0])])
    R['ink_levels_stored_srgb'] = dict(
        paper_lum_p60=round(c['paper_lum'], 4), darkest_ink_lum=round(c['ink_lum'], 4),
        ink_threshold=round(c['thr_ink'], 4),
        paper_mean_rgb=[round(float(v), 4) for v in rect[~ink].reshape(-1, 3).mean(0)],
        black_mean_rgb=[round(float(v), 4) for v in rect[black].reshape(-1, 3).mean(0)],
        red_mean_rgb=[round(float(v), 4) for v in rect[red].reshape(-1, 3).mean(0)],
        black_p5_lum=round(float(np.percentile(c['lum'][black], 5)), 4),
        red_coverage_pct=round(float(red.mean()) * 100, 3),
        black_coverage_pct=round(float(black.mean()) * 100, 3),
        total_ink_pct=round(float(ink.mean()) * 100, 3))
    R['outline'] = measure_outline(q, qm, sw, sh)
    R['border_rules'], rule_mask = measure_rules(red)

    rad = max(1, int(round(0.70 * PPMM))); minpx = int(0.6 * PPMM * PPMM)
    bcl = cluster(black, rad, minpx)
    red_nr = red & ~L.dilate(rule_mask, 1)
    rcl = cluster(red_nr, max(1, int(0.5 * PPMM)), minpx)
    print(f"\n===== {name} black clusters ({len(bcl)}) =====")
    for cc in bcl[:26]:
        print("  n=%7d x[%4d,%4d] y[%4d,%4d] c=(%6.1f,%7.1f) fx[%.3f,%.3f] fy[%.3f,%.3f]" %
              (cc['n'], cc['x0'], cc['x1'], cc['y0'], cc['y1'], cc['cx'], cc['cy'],
               cc['x0']/CW, cc['x1']/CW, cc['y0']/CH, cc['y1']/CH))
    print(f"===== {name} red clusters (rules removed) =====")
    for cc in rcl[:20]:
        print("  n=%7d x[%4d,%4d] y[%4d,%4d] c=(%6.1f,%7.1f) fx[%.3f,%.3f] fy[%.3f,%.3f] fill=%.2f" %
              (cc['n'], cc['x0'], cc['x1'], cc['y0'], cc['y1'], cc['cx'], cc['cy'],
               cc['x0']/CW, cc['x1']/CW, cc['y0']/CH, cc['y1']/CH,
               cc['n']/float((cc['x1']-cc['x0']+1)*(cc['y1']-cc['y0']+1))))

    E = {}
    # seals: largest red body inside a dedicated lower-left / lower-right band
    seal_boxes = []
    for k, xa, xb, ya, yb in (('seal_box_large_left', 0.05, 0.52, 0.735, 0.955),
                              ('seal_box_small_right', 0.58, 0.97, 0.745, 0.955)):
        bandm = np.zeros_like(red)
        bandm[int(ya*CH):int(yb*CH), int(xa*CW):int(xb*CW)] = True
        sm = red_nr & bandm
        cls_ = cluster(sm, 3, int(1.5 * PPMM * PPMM))
        if not cls_: continue
        cc = cls_[0]
        # merge the outer border ring / inner panel: anything CONTAINED in the
        # largest body's bbox grown by 4 mm (keeps corner ornaments out)
        pad = 4.0 * PPMM
        grp = [cc]
        for _ in range(3):
            gx0 = min(z['x0'] for z in grp) - pad; gx1 = max(z['x1'] for z in grp) + pad
            gy0 = min(z['y0'] for z in grp) - pad; gy1 = max(z['y1'] for z in grp) + pad
            add = [z for z in cls_ if z not in grp and gx0 <= z['x0'] and z['x1'] <= gx1
                   and gy0 <= z['y0'] and z['y1'] <= gy1]
            if not add: break
            grp += add
        msk = np.zeros_like(red)
        for z in grp: msk |= z['mask']
        ys2, xs2 = np.nonzero(msk)
        cc = dict(n=int(msk.sum()), x0=int(xs2.min()), x1=int(xs2.max()),
                  y0=int(ys2.min()), y1=int(ys2.max()),
                  cx=float(xs2.mean()), cy=float(ys2.mean()), mask=msk)
        E[k] = elem([cc]); E[k]['n_red_parts'] = len(grp)
        seal_boxes.append((cc['x0'], cc['x1'], cc['y0'], cc['y1']))
        sub = cc['mask'][cc['y0']:cc['y1']+1, cc['x0']:cc['x1']+1]
        E[k]['knockout_frac_of_bbox'] = round(1.0 - float(sub.mean()), 4)
        wr = [b - a for yy in range(0, sub.shape[0]) for a, b in runs(sub[yy])]
        thin = [w for w in wr if w < 0.30 * sub.shape[1]]
        E[k]['border_stroke_w_med'] = px_x(float(np.median(thin)) if thin else 0.0)
        E[k]['border_stroke_w_p90'] = px_x(float(np.percentile(thin, 90)) if thin else 0.0)
        E[k]['style'] = 'solid filled panel' if sub.mean() > 0.5 else 'outline box'
    # ring: all non-rule red in the central band, minus the seal boxes
    band = np.zeros_like(red)
    band[int(0.20*CH):int(0.76*CH), int(0.06*CW):int(0.94*CW)] = True
    for (x0, x1, y0, y1) in seal_boxes:
        band[max(0, y0-6):y1+7, max(0, x0-6):x1+7] = False
    rm = red_nr & band
    rcl2 = cluster(rm, max(1, int(1.6 * PPMM)), int(1.0 * PPMM * PPMM))
    if rcl2:
        wide = [cc for cc in rcl2 if (cc['x1']-cc['x0']) > 0.30 * CW or cc['n'] > 8 * PPMM * PPMM]
        if not wide: wide = rcl2[:1]
        rmask = np.zeros_like(rm)
        for cc in wide: rmask |= cc['mask']
        E['red_ring'] = elem([dict(n=int(rmask.sum()), x0=int(np.nonzero(rmask.any(0))[0].min()),
                                   x1=int(np.nonzero(rmask.any(0))[0].max()),
                                   y0=int(np.nonzero(rmask.any(1))[0].min()),
                                   y1=int(np.nonzero(rmask.any(1))[0].max()),
                                   cx=float(np.nonzero(rmask)[1].mean()),
                                   cy=float(np.nonzero(rmask)[0].mean()))])
        E['red_ring']['geometry'] = ring_geom(rmask)
        E['red_ring']['n_arcs'] = len(wide)

    # ---- black elements, assigned by zone, with the ring used to keep the
    # centre character's detached strokes out of the column buckets
    G = E.get('red_ring', {}).get('geometry')
    RCX = G['centre_x']['px'] if G else CW / 2.0
    RCY = G['centre_y']['px'] if G else CH * 0.49
    ROUT = G['outer_r_med']['px'] if G else 0.42 * CW
    def in_ring(cc, k=0.85):
        return math.hypot(cc['cx'] - RCX, cc['cy'] - RCY) < k * ROUT
    big = [cc for cc in bcl if cc['n'] > 4 * PPMM * PPMM]
    SMALL = 300 * PPMM * PPMM      # a glyph is < 300 mm2, the centre character > 700
    used = set()
    fl = [cc for cc in big if 0.28 < cc['cx']/CW < 0.72 and 0.05 < cc['cy']/CH < 0.30
          and cc['n'] < SMALL]
    for cc in fl: used.add(id(cc))
    if fl: E['flame_emblem'] = elem(fl)
    for key, pred in (('col_upper_left_hi_ton_jutsu', lambda x, y: x < 0.36 and y < 0.56),
                      ('col_upper_right_baku_en_jin', lambda x, y: x > 0.64 and y < 0.56),
                      ('col_lower_right_shou_jin', lambda x, y: x > 0.64 and 0.56 <= y < 0.90),
                      ('col_lower_centre_shun_gou', lambda x, y: 0.38 <= x <= 0.62 and y >= 0.68)):
        s = [cc for cc in big if pred(cc['cx']/CW, cc['cy']/CH) and id(cc) not in used
             and cc['n'] < SMALL and not in_ring(cc)]
        if s:
            for cc in s: used.add(id(cc))
            E[key] = elem(s)
            E[key]['parts'] = [dict(bbox=box(z['x0'], z['x1'], z['y0'], z['y1']),
                                    ink_mm2=round(z['n']/(PPMM*PPMM), 2))
                               for z in sorted(s, key=lambda z: z['y0'])]
    core = [cc for cc in big if id(cc) not in used and 0.12 < cc['cx']/CW < 0.88
            and 0.25 < cc['cy']/CH < 0.80 and cc['n'] >= SMALL]
    if core:
        for cc in core: used.add(id(cc))
        pad = 3.0 * PPMM
        for _ in range(3):
            bx0 = min(z['x0'] for z in core); bx1 = max(z['x1'] for z in core)
            by0 = min(z['y0'] for z in core); by1 = max(z['y1'] for z in core)
            add = [cc for cc in big if id(cc) not in used and
                   cc['x0'] <= bx1 + pad and cc['x1'] >= bx0 - pad and
                   cc['y0'] <= by1 + pad and cc['y1'] >= by0 - pad and in_ring(cc, 1.25)]
            if not add: break
            for cc in add: used.add(id(cc)); core.append(cc)
        E['centre_char_bao'] = elem(core)
        E['centre_char_bao']['n_merged_clusters'] = len(core)
    R['elements'] = E

    # corner flourishes (red + very dark ink inside the corner boxes)
    FL = {}
    bx, by = int(0.30 * CW), int(0.13 * CH)
    for nm, sx, sy in (('TL', slice(0, bx), slice(0, by)), ('TR', slice(CW-bx, CW), slice(0, by)),
                       ('BL', slice(0, bx), slice(CH-by, CH)), ('BR', slice(CW-bx, CW), slice(CH-by, CH))):
        keep = np.zeros_like(red)
        keep[sy, sx] = True
        sub_full = (red | (black & (c['lum'] < 0.30))) & keep
        orn = sub_full & ~L.dilate(rule_mask, 1)          # ornament = corner ink minus the rules
        lab, comps = L.label_components(orn)
        comps = [z for z in comps if z['n'] >= 0.4 * PPMM * PPMM]
        if not comps: continue
        sel = np.isin(lab, [z['label'] for z in comps])
        ys, xs = np.nonzero(sel)
        X0, X1, Y0, Y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        wr = [b - a for yy in range(Y0, Y1+1) for a, b in runs(sel[yy])]
        wc = [b - a for xx in range(X0, X1+1) for a, b in runs(sel[:, xx])]
        r1 = R['border_rules']
        def inset(side):
            rr = r1[side]['rules']
            return rr[0]['inset_from_tag_edge']['px'] if rr else float('nan')
        # corner reference = intersection of the two rule centre lines
        RX = inset('left') if 'L' in nm else CW - inset('right')
        RY = inset('top') if 'T' in nm else CH - inset('bottom')
        dist = np.hypot(xs - RX, ys - RY)
        FL[nm] = dict(bbox=box(X0, X1, Y0, Y1), ink_px=int(sel.sum()),
                      ink_mm2=round(float(sel.sum())/(PPMM*PPMM), 3), n_parts=len(comps),
                      arm_len_horizontal=px_x(X1-X0+1), arm_len_vertical=px_y(Y1-Y0+1),
                      stroke_w_med_h=px_x(float(np.median(wr))), stroke_w_p90_h=px_x(float(np.percentile(wr, 90))),
                      stroke_w_med_v=px_y(float(np.median(wc))),
                      rule_corner_x=px_x(RX), rule_corner_y=px_y(RY),
                      reach_from_rule_corner_max=px_x(float(dist.max())),
                      reach_from_rule_corner_p90=px_x(float(np.percentile(dist, 90))),
                      run_along_horiz_rule=px_x(float((X1 - RX) if 'L' in nm else (RX - X0))),
                      run_along_vert_rule=px_y(float((Y1 - RY) if 'T' in nm else (RY - Y0))),
                      outboard_of_side_rule=px_x(float(RX - X0 if 'L' in nm else X1 - RX)),
                      outboard_of_horiz_rule=px_y(float(RY - Y0 if 'T' in nm else Y1 - RY)))
    R['corner_flourishes'] = FL

    # diamond / lozenge ornaments
    dia = []
    for colour, msk in (('red', red & ~L.dilate(rule_mask, 1)), ('black', black)):
        for cc in cluster(msk, 2, int(0.30 * PPMM * PPMM)):
            w = cc['x1']-cc['x0']+1; h = cc['y1']-cc['y0']+1
            fill = cc['n']/float(w*h)
            if not (0.3*PPMM < w < 7*PPMM and 0.5*PPMM < h < 13*PPMM): continue
            if h < 0.9*w or fill < 0.34 or fill > 0.82: continue
            inside_elem = any(
                v['x0']['px'] - 2 <= cc['x0'] and cc['x1'] <= v['x1']['px'] + 2 and
                v['y0']['px'] - 2 <= cc['y0'] and cc['y1'] <= v['y1']['px'] + 2
                for k2, v in E.items()
                if k2 in ('flame_emblem', 'seal_box_large_left', 'seal_box_small_right'))
            if inside_elem:
                continue
            sub = cc['mask'][cc['y0']:cc['y1']+1, cc['x0']:cc['x1']+1]
            prof = sub.sum(1)
            waist = int(np.argmax(prof))
            r1b = R['border_rules']
            def near_rule():
                for s2, ax in (('left', cc['cx']), ('right', CW - cc['cx']),
                               ('top', cc['cy']), ('bottom', CH - cc['cy'])):
                    rr = r1b[s2]['rules']
                    if rr and abs(ax - rr[0]['inset_from_tag_edge']['px']) < 0.6 * PPMM:
                        return s2
                return None
            dia.append(dict(colour=colour, on_rule=near_rule(),
                            cx=px_x(cc['cx']), cy=px_y(cc['cy']),
                            w=px_x(w), h=px_y(h), fill=round(fill, 3),
                            ink_mm2=round(cc['n']/(PPMM*PPMM), 3),
                            w_over_h=round(w/float(h), 3),
                            widest_row_frac_of_height=round(waist/float(h), 3),
                            on_centreline=bool(abs(cc['cx'] - CW/2) < 0.03*CW)))
    dia.sort(key=lambda d: (d['cy']['px'], d['cx']['px']))
    # beads sitting ON a rule show up as local width bulges, not separate blobs
    beads = []
    for side in ('left', 'right', 'top', 'bottom'):
        rr = R['border_rules'][side]['rules']
        if not rr: continue
        vert = side in ('left', 'right')
        n_along = CH if vert else CW
        c0 = rr[0]['inset_from_tag_edge']['px']
        half = max(3.0, 3.0 * rr[0]['stroke_w_med']['px'])
        w = np.zeros(n_along)
        for i in range(n_along):
            if side == 'left':    line = red[i, :int(c0 + half)]
            elif side == 'right': line = red[i, CW - int(c0 + half):][::-1]
            elif side == 'top':   line = red[:int(c0 + half), i]
            else:                 line = red[CH - int(c0 + half):, i][::-1]
            rs = [(a, b) for a, b in runs(line) if abs((a + b) / 2 - c0) <= half]
            w[i] = max([b - a for a, b in rs], default=0)
        med = float(np.median(w[w > 0])) if (w > 0).any() else 0
        thr_w = max(med * 2.0, med + 0.25 * PPMM)
        i = 0
        while i < n_along:
            if w[i] > thr_w:
                j = i
                while j < n_along and w[j] > thr_w: j += 1
                if 0.5 * PPMM < (j - i) < 8 * PPMM:
                    P = px_y if vert else px_x
                    beads.append(dict(on_rule=side, pos_along_rule=P((i + j) / 2.0),
                                      length_along_rule=P(float(j - i)),
                                      max_width=(px_x if vert else px_y)(float(w[i:j].max())),
                                      width_over_rule_med=round(float(w[i:j].max()) / max(med, .5), 2)))
                i = j
            else:
                i += 1
    R['diamonds'] = dict(count=len(dia), on_vertical_centreline=sum(1 for d in dia if d['on_centreline']),
                         items=dia, rule_median_stroke_note="beads_on_rules are local width bulges "
                         "along a border rule (>2x its median stroke width)",
                         beads_on_rules=beads, beads_count=len(beads))

    # clear space + composition
    content = ink & ~L.dilate(rule_mask, 2)
    ys, xs = np.nonzero(content)
    comp = dict(content_bbox=box(int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())),
                content_centroid_x=px_x(float(xs.mean())), content_centroid_y=px_y(float(ys.mean())),
                centroid_offset_from_tag_centre_x=px_x(float(xs.mean()) - CW/2),
                centroid_offset_from_tag_centre_y=px_y(float(ys.mean()) - CH/2),
                bbox_centre_offset_x=px_x((float(xs.min())+float(xs.max()))/2 - CW/2),
                bbox_centre_offset_y=px_y((float(ys.min())+float(ys.max()))/2 - CH/2),
                margin_left=px_x(float(xs.min())), margin_right=px_x(CW - float(xs.max())),
                margin_top=px_y(float(ys.min())), margin_bottom=px_y(CH - float(ys.max())))
    cm = content.sum(0).astype(float); rw = content.sum(1).astype(float)
    comp['ink_balance_left_minus_right_pct'] = round(100*(cm[:CW//2].sum()-cm[CW//2:].sum())/cm.sum(), 2)
    comp['ink_balance_top_minus_bottom_pct'] = round(100*(rw[:CH//2].sum()-rw[CH//2:].sum())/rw.sum(), 2)
    R['composition'] = comp

    gaps = {}
    def gap(a_key, b_key, axis, mode):
        if a_key not in E or b_key not in E: return
        A, B = E[a_key], E[b_key]
        if axis == 'y':
            v = B['y0']['px'] - A['y1']['px'] if mode == 'ab' else A['y0']['px'] - B['y1']['px']
            gaps[f"{a_key}__to__{b_key}_vertical"] = px_y(v)
        else:
            v = B['x0']['px'] - A['x1']['px'] if mode == 'ab' else A['x0']['px'] - B['x1']['px']
            gaps[f"{a_key}__to__{b_key}_horizontal"] = px_x(v)
    gap('flame_emblem', 'red_ring', 'y', 'ab')
    gap('red_ring', 'col_lower_centre_shun_gou', 'y', 'ab')
    r1 = R['border_rules']
    if r1['left']['rules'] and 'red_ring' in E:
        gaps['ring_left_to_left_rule'] = px_x(E['red_ring']['x0']['px'] - r1['left']['rules'][0]['inset_from_tag_edge']['px'])
        gaps['ring_right_to_right_rule'] = px_x((CW - r1['right']['rules'][0]['inset_from_tag_edge']['px']) - E['red_ring']['x1']['px'])
    for k in ('col_upper_left_hi_ton_jutsu', 'col_upper_right_baku_en_jin',
              'col_lower_right_shou_jin', 'seal_box_large_left', 'seal_box_small_right',
              'flame_emblem', 'centre_char_bao'):
        if k in E and r1['left']['rules'] and r1['right']['rules']:
            gaps[k + '_to_left_rule'] = px_x(E[k]['x0']['px'] - r1['left']['rules'][0]['inset_from_tag_edge']['px'])
            gaps[k + '_to_right_rule'] = px_x((CW - r1['right']['rules'][0]['inset_from_tag_edge']['px']) - E[k]['x1']['px'])
    if 'centre_char_bao' in E and 'red_ring' in E:
        g = E['red_ring']['geometry']
        cc_ = E['centre_char_bao']
        gaps['bao_bbox_diag_over_ring_outer_diameter'] = round(
            math.hypot(cc_['w']['px'], cc_['h']['px']) / g['outer_diameter']['px'], 4)
        gaps['bao_width_over_ring_outer_diameter'] = round(cc_['w']['px'] / g['outer_diameter']['px'], 4)
        gaps['bao_centroid_minus_ring_centre_x'] = px_x(cc_['centroid_x']['px'] - g['centre_x']['px'])
        gaps['bao_centroid_minus_ring_centre_y'] = px_y(cc_['centroid_y']['px'] - g['centre_y']['px'])
    R['clear_space'] = gaps

    ov = rect.copy()
    def outline_rect(x0, x1, y0, y1, col, t=3):
        x0 = max(0, int(x0)); x1 = min(CW-1, int(x1)); y0 = max(0, int(y0)); y1 = min(CH-1, int(y1))
        ov[y0:y0+t, x0:x1] = col; ov[max(y0,y1-t):y1, x0:x1] = col
        ov[y0:y1, x0:x0+t] = col; ov[y0:y1, max(x0,x1-t):x1] = col
    for k, v in E.items():
        outline_rect(v['x0']['px'], v['x1']['px'], v['y0']['px'], v['y1']['px'], np.array([0., .85, .1]))
    for k, v in FL.items():
        b = v['bbox']; outline_rect(b['x0']['px'], b['x1']['px'], b['y0']['px'], b['y1']['px'], np.array([0., .4, 1.]))
    for d in dia:
        outline_rect(d['cx']['px']-d['w']['px']/2, d['cx']['px']+d['w']['px']/2,
                     d['cy']['px']-d['h']['px']/2, d['cy']['px']+d['h']['px']/2, np.array([1., 0., 1.]), 2)
    L.save_debug_png(ov[::2, ::2], os.path.join(DBG, f"DEBUG_NEVER_SHIP_boxes_{name}.png"))
    for k in list(E):
        E[k].pop('mask', None)
    return R

out = dict(_note=("PaperBomb LAYOUT metrology. Numbers only; no artwork derived from the guides. "
                  "Canonical space 980x2184 px = 70.0 x 156.0 mm (14 px/mm), origin at the TAG's "
                  "top-left virtual corner, x right, y down. fW = fraction of tag width, "
                  "fH = fraction of tag height, mm = millimetres on the 70.0 x 156.0 mm card. "
                  "Colour values are STORED (file/sRGB-encoded) 0..1 values, not linear."))
out['V1'] = measure_source('V1', os.path.join(REF, 'paperbomb_guide.png'))
out['V2'] = measure_source('V2', os.path.join(REF, 'paperbomb_guide_v2_real_glyphs.png'))
out['OURS'] = measure_source('OURS', BCP, ours=True)
with open(os.path.join(OUTD, 'layout.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print("\nWROTE layout.json")
