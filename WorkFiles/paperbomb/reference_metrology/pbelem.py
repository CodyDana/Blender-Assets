# -*- coding: utf-8 -*-
"""Element extraction + typography/stroke/ring/flame/seal metrology."""
import math, os
import numpy as np
import pbmetro as P
import pbtag as T

CARD_W_MM = T.CARD_W_MM
CARD_H_MM = T.CARD_H_MM


# --------------------------------------------------------------------------
def comps(mask, min_area, close_r=1):
    m = P.close(mask, close_r) if close_r else mask
    lab, n = P.label_cc(m)
    st = [s for s in P.cc_stats(lab, n) if s and s['area'] >= min_area]
    for s in st:
        s['mask'] = (lab == s['label']) & mask
    st.sort(key=lambda s: -s['area'])
    return st


def union(mlist, shape):
    out = np.zeros(shape, dtype=bool)
    for m in mlist:
        out |= m
    return out


def bbox_of(mask):
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    return int(cols[0]), int(rows[0]), int(cols[-1] + 1), int(rows[-1] + 1)


def mass_box(mask, keep=0.90):
    """Box holding the central `keep` fraction of ink mass on each axis - the
    'visual weight' box, immune to one long flick."""
    cx = mask.sum(axis=0).astype(np.float64)
    cy = mask.sum(axis=1).astype(np.float64)
    lo = (1.0 - keep) / 2.0

    def span(p):
        c = np.cumsum(p) / max(p.sum(), 1)
        a = int(np.searchsorted(c, lo))
        b = int(np.searchsorted(c, 1.0 - lo))
        return a, min(b + 1, len(p))
    x0, x1 = span(cx)
    y0, y1 = span(cy)
    return x0, y0, x1, y1


# --------------------------------------------------------------------------
def fit_ring(tg, red, field):
    """Fit the red ring: centre, radii, thickness/coverage/laps per angle."""
    H, W = red.shape
    ys, xs = np.mgrid[0:H, 0:W]
    xmm = xs / W * CARD_W_MM
    ymm = ys / H * CARD_H_MM
    sel = red & (xmm > field[0]) & (xmm < field[2]) & (ymm > field[1]) & (ymm < field[3])
    if sel.sum() < 200:
        return None
    py, px = np.nonzero(sel)
    cx, cy = px.mean(), py.mean()
    mx = my = None
    el = None
    # iterate on the midline
    for _ in range(6):
        ang = np.arctan2((py - cy) / H * CARD_H_MM, (px - cx) / W * CARD_W_MM)
        rad = np.hypot((px - cx) / W * CARD_W_MM, (py - cy) / H * CARD_H_MM)
        nb = 360
        b = ((ang + math.pi) / (2 * math.pi) * nb).astype(int) % nb
        mid = np.full(nb, np.nan)
        for i in range(nb):
            r = rad[b == i]
            if len(r) > 3:
                mid[i] = np.median(r)
        ok = np.isfinite(mid)
        th = (np.arange(nb)[ok] + 0.5) / nb * 2 * math.pi - math.pi
        mx = cx + mid[ok] / CARD_W_MM * W * np.cos(th)
        my = cy + mid[ok] / CARD_H_MM * H * np.sin(th)
        el2 = P.fit_ellipse(mx, my)
        if not el2:
            break
        el = el2
        ncx, ncy = el['cx'], el['cy']
        if abs(ncx - cx) < 0.05 and abs(ncy - cy) < 0.05:
            cx, cy = ncx, ncy
            break
        cx, cy = ncx, ncy

    nb = 720
    ang = np.arctan2((py - cy) / H * CARD_H_MM, (px - cx) / W * CARD_W_MM)
    rad = np.hypot((px - cx) / W * CARD_W_MM, (py - cy) / H * CARD_H_MM)
    b = ((ang + math.pi) / (2 * math.pi) * nb).astype(int) % nb
    prof = []
    order = np.argsort(b)
    bs = b[order]
    rs = rad[order]
    starts = np.searchsorted(bs, np.arange(nb), 'left')
    ends = np.searchsorted(bs, np.arange(nb), 'right')
    step_mm = 0.5 * (CARD_W_MM / W + CARD_H_MM / H)
    # ellipse radius as a function of angle, for the normalised radius rho
    sa = el['semi_major_px'] if el else 1.0
    sb = el['semi_minor_px'] if el else 1.0
    th0 = math.radians(el['major_axis_deg']) if el else 0.0
    sa_mm = sa * 0.5 * (CARD_W_MM / W + CARD_H_MM / H)
    sb_mm = sb * 0.5 * (CARD_W_MM / W + CARD_H_MM / H)

    def r_ell(a):
        u = math.cos(a - th0) / sa_mm
        v = math.sin(a - th0) / sb_mm
        return 1.0 / math.sqrt(u * u + v * v)

    rho_all = []
    for i in range(nb):
        r = rs[starts[i]:ends[i]]
        a = (i + 0.5) / nb * 2 * math.pi - math.pi
        re = r_ell(a)
        if len(r) == 0:
            prof.append(dict(deg=(i + 0.5) / nb * 360.0 - 180.0, n=0, r_in=None, r_out=None, core_thick=0.0,
                             thick=0.0, ink_thick=0.0, ink=0.0, runs=0, cover=0.0, r_ell=re))
            continue
        r_in, r_out = float(r.min()), float(r.max())
        nbins = int((r_out - r_in) / step_mm) + 2
        bins = np.zeros(nbins, dtype=bool)
        idx = np.clip(((r - r_in) / step_mm).astype(int), 0, nbins - 1)
        bins[idx] = True
        occ = int(bins.sum())
        bb = bins.copy()                       # bridge dry-brush speckle up to 2 px
        for k in (1, 2):
            bb[:-k] |= bins[k:]
            bb[k:] |= bins[:-k]
        dd = np.diff(np.concatenate(([0], bb.astype(np.int8), [0])))
        nruns = int((dd == 1).sum())
        rho_all.append(r / re)
        core = float(np.percentile(r, 95) - np.percentile(r, 5)) if len(r) > 6 else r_out - r_in
        prof.append(dict(deg=(i + 0.5) / nb * 360.0 - 180.0, n=int(len(r)),
                         r_in=r_in, r_out=r_out, thick=r_out - r_in, core_thick=core,
                         ink_thick=occ * step_mm,
                         ink=float(len(r)) * step_mm * step_mm,
                         runs=nruns, r_ell=re,
                         cover=float(occ) / max(nbins - 1, 1)))
    rho_all = np.concatenate(rho_all) if rho_all else np.array([])
    if mx is not None:
        el2 = P.fit_ellipse(mx, my)
        if el2:
            el = el2
    if el is None:                                   # fall back to a circle fit
        fcx, fcy, fr, frms = P.fit_circle(mx if mx is not None else px.astype(float),
                                          my if my is not None else py.astype(float))
        el = dict(cx=fcx, cy=fcy, semi_major_px=fr, semi_minor_px=fr,
                  major_axis_deg=0.0, eccentricity=0.0, axis_ratio=1.0,
                  fallback='circle')
    # radial occupancy histogram in ellipse-normalised radius: one lap = one
    # hump, three concentric laps = three humps separated by clean troughs
    hist = bands = None
    if len(rho_all):
        edges = np.linspace(0.70, 1.30, 121)
        h, _ = np.histogram(rho_all, bins=edges)
        h = h.astype(np.float64) / max(h.max(), 1)
        sm = np.convolve(h, np.ones(5) / 5.0, mode='same')
        peaks = []
        for i in range(2, len(sm) - 2):
            if sm[i] >= sm[i - 1] and sm[i] > sm[i + 1] and sm[i] > 0.22:
                peaks.append(i)
        # merge peaks not separated by a deep enough trough
        keep = []
        for i in peaks:
            if not keep:
                keep.append(i); continue
            trough = sm[keep[-1]:i + 1].min()
            if trough < 0.55 * min(sm[keep[-1]], sm[i]):
                keep.append(i)
            elif sm[i] > sm[keep[-1]]:
                keep[-1] = i
        hist = dict(edges=[round(float(v), 4) for v in edges],
                    occupancy=[round(float(v), 4) for v in sm],
                    n_radial_modes=len(keep),
                    mode_rho=[round(float(0.5 * (edges[i] + edges[i + 1])), 4) for i in keep],
                    mode_height=[round(float(sm[i]), 4) for i in keep],
                    fwhm_rho=None)
        if keep:
            i = keep[int(np.argmax([sm[j] for j in keep]))]
            half = sm[i] * 0.5
            a = i
            while a > 0 and sm[a] > half:
                a -= 1
            bq = i
            while bq < len(sm) - 1 and sm[bq] > half:
                bq += 1
            hist['fwhm_rho'] = round(float(edges[bq] - edges[a]), 4)
    return dict(cx=cx, cy=cy, prof=prof, ellipse=el, sel=sel, radial_hist=hist,
                n_px=int(sel.sum()), step_mm=step_mm)


# --------------------------------------------------------------------------
def column_cells(tg, mask, min_gap_mm=0.55, min_run_mm=1.2, axis='v'):
    """Split a column's ink into glyph cells by projection profile."""
    x0, y0, x1, y1 = bbox_of(mask)
    sub = mask[y0:y1, x0:x1]
    if axis == 'v':
        mg = max(1, int(round(min_gap_mm * tg.H / CARD_H_MM)))
        mr = max(2, int(round(min_run_mm * tg.H / CARD_H_MM)))
        segs, prof = P.split_profile(sub, 0, mg, mr)
        cells = []
        for (a, b) in segs:
            cm = np.zeros_like(mask)
            cm[y0 + a:y0 + b, x0:x1] = sub[a:b]
            cells.append(cm)
    else:
        mg = max(1, int(round(min_gap_mm * tg.W / CARD_W_MM)))
        mr = max(2, int(round(min_run_mm * tg.W / CARD_W_MM)))
        segs, prof = P.split_profile(sub, 1, mg, mr)
        cells = []
        for (a, b) in segs:
            cm = np.zeros_like(mask)
            cm[y0:y1, x0 + a:x0 + b] = sub[:, a:b]
            cells.append(cm)
    return cells, prof


def describe_glyph(tg, m, name, px_mm_x=None, px_mm_y=None):
    x0, y0, x1, y1 = bbox_of(m)
    b = tg.box(x0, y0, x1, y1)
    mx0, my0, mx1, my1 = mass_box(m, 0.90)
    mb = tg.box(mx0, my0, mx1, my1)
    ys, xs = np.nonzero(m)
    sub = m[y0:y1, x0:x1]
    sm = P.stroke_metrics(sub, tg.px_per_mm)
    tp = P.taper_profile(sub)
    d = dict(name=name, bbox=b, mass_box_90=mb,
             ink_area_px=int(m.sum()),
             ink_area_mm2=round(float(m.sum()) / (tg.px_per_mm_x * tg.px_per_mm_y), 3),
             fill_of_bbox=round(float(m.sum()) / max((x1 - x0) * (y1 - y0), 1), 4),
             ink_centroid=tg.pt(float(xs.mean()), float(ys.mean())),
             w_over_h=b['w_over_h'], mass_w_over_h=mb['w_over_h'])
    if sm:
        # anisotropic px/mm: vertical strokes are measured across x, horizontal across y
        sm['vstroke_median_mm_x'] = round(sm['vstroke_median_px'] / tg.px_per_mm_x, 4)
        sm['hstroke_median_mm_y'] = round(sm['hstroke_median_px'] / tg.px_per_mm_y, 4)
        d['stroke'] = sm
    if tp:
        d['taper'] = tp
    return d


def describe_column(tg, mlist, name, expect=None):
    m = union([s['mask'] for s in mlist], (tg.H, tg.W)) if mlist and isinstance(mlist[0], dict) \
        else union(mlist, (tg.H, tg.W))
    if m.sum() == 0:
        return None
    x0, y0, x1, y1 = bbox_of(m)
    cells, prof = column_cells(tg, m)
    split_mode = 'gap'
    if expect and len(cells) != expect:
        # forced n-way split at the lightest rows (glyph cells that touch)
        sub = m[y0:y1, x0:x1]
        rowp = sub.sum(axis=1).astype(np.float64)
        min_seg = max(2, int(0.55 * len(rowp) / expect))
        segs = P.split_into_n(rowp, expect, min_seg)
        cells = []
        for (a, b) in segs:
            cm = np.zeros_like(m)
            cm[y0 + a:y0 + b, x0:x1] = sub[a:b]
            cells.append(cm)
        split_mode = f'forced-{expect}way'
    cells = [c for c in cells if c.sum() > 4]
    gl = [describe_glyph(tg, c, f"{name}[{i}]") for i, c in enumerate(cells)]
    centres = [(g['bbox']['cx_mm'], g['bbox']['cy_mm']) for g in gl]
    adv = []
    gaps = []
    for i in range(len(gl) - 1):
        adv.append(round(centres[i + 1][1] - centres[i][1], 3))
        gaps.append(round(gl[i + 1]['bbox']['y0_mm'] - gl[i]['bbox']['y1_mm'], 3))
    lean = None
    if len(centres) >= 2:
        cy = np.array([c[1] for c in centres])
        cx = np.array([c[0] for c in centres])
        a, bq, rms = P.fit_line_x_of_y(cy, cx)
        lean = dict(axis_x_at_top_mm=round(float(a * cy.min() + bq), 3),
                    axis_x_at_bottom_mm=round(float(a * cy.max() + bq), 3),
                    lean_deg_from_vertical=round(math.degrees(math.atan(a)), 3),
                    axis_rms_mm=round(rms, 3),
                    axis_mean_x_mm=round(float(cx.mean()), 3))
    return dict(name=name, n_cells=len(cells), split_mode=split_mode,
                bbox=tg.box(x0, y0, x1, y1),
                row_profile_px=[int(v) for v in
                                m[y0:y1, x0:x1].sum(axis=1)[::max(1, (y1 - y0) // 60)]],
                glyphs=gl, advance_mm=adv, gap_mm=gaps, axis=lean,
                ink_area_mm2=round(float(m.sum()) / (tg.px_per_mm_x * tg.px_per_mm_y), 3),
                mask=m)


# --------------------------------------------------------------------------
def seal_metrics2(tg, red, paperish, box_mm, name, exclude_x=None, frame_zone=None):
    """Seal box: outer/inner frame from red-density profiles, corner treatment,
    fill character, and the device inside."""
    H, W = red.shape
    ys, xs = np.mgrid[0:H, 0:W]
    xmm = xs / W * CARD_W_MM
    ymm = ys / H * CARD_H_MM
    win = (xmm >= box_mm[0]) & (xmm <= box_mm[2]) & (ymm >= box_mm[1]) & (ymm <= box_mm[3])
    if exclude_x:
        win &= ~((xmm > exclude_x[0]) & (xmm < exclude_x[1]))
    if frame_zone is not None:
        win &= ~frame_zone
    m = red & win
    if m.sum() < 50:
        return None
    cs = comps(m, max(20, int(0.00002 * W * H)), 2)
    if not cs:
        return None
    big = cs[0]['mask'].copy()
    parts = [cs[0]]
    bx0, by0, bx1, by1 = cs[0]['x0'], cs[0]['y0'], cs[0]['x1'], cs[0]['y1']
    pad = int(round(3.0 * tg.px_per_mm))          # the outline can sit OUTSIDE the block
    for c in cs[1:]:
        if (c['x0'] >= bx0 - pad and c['x1'] <= bx1 + pad and
                c['y0'] >= by0 - pad and c['y1'] <= by1 + pad):
            big |= c['mask']
            parts.append(c)
    x0, y0, x1, y1 = bbox_of(big)
    sub = big[y0:y1, x0:x1]
    h, w = sub.shape
    rowf = sub.mean(axis=1)
    colf = sub.mean(axis=0)

    def rule_run(a, thr=0.5):
        """(offset, width) of the first run of lines that are mostly inked."""
        on = a >= thr
        i = 0
        while i < len(on) and not on[i]:
            i += 1
        if i == len(on):
            return 0, 0
        j = i
        while j < len(on) and on[j]:
            j += 1
        return i, j - i

    t_off, t = rule_run(rowf)
    b_off, b = rule_run(rowf[::-1])
    l_off, l = rule_run(colf)
    r_off, r = rule_run(colf[::-1])
    t += t_off
    b += b_off
    l += l_off
    r += r_off
    out = dict(name=name,
               outer_bbox=tg.box(x0, y0, x1, y1),
               frame_stroke_mm=dict(top=round(tg.mmy(t), 3), bottom=round(tg.mmy(b), 3),
                                    left=round(tg.mmx(l), 3), right=round(tg.mmx(r), 3)),
               frame_stroke_px=dict(top=t, bottom=b, left=l, right=r),
               red_fill_of_outer_bbox=round(float(sub.mean()), 4),
               row_red_fraction=[round(float(v), 3) for v in rowf[::max(1, h // 40)]],
               col_red_fraction=[round(float(v), 3) for v in colf[::max(1, w // 24)]])
    # structure: the seal's separate red pieces, biggest first
    out['pieces'] = [dict(area_mm2=round(c['area'] / (tg.px_per_mm_x * tg.px_per_mm_y), 3),
                          bbox=tg.box(c['x0'], c['y0'], c['x1'], c['y1']),
                          fill_of_bbox=round(c['area'] / max((c['x1'] - c['x0']) *
                                                             (c['y1'] - c['y0']), 1), 4))
                     for c in parts[:6]]
    # an outline piece is a low-fill rectangle; its rule thickness follows from
    # ink area = 2*s*(W+H) - 4*s^2
    for p in out['pieces']:
        Wm, Hm, A = p['bbox']['w_mm'], p['bbox']['h_mm'], p['area_mm2']
        if p['fill_of_bbox'] < 0.45 and Wm > 2 and Hm > 2:
            disc = (Wm + Hm) ** 2 - 4.0 * A
            p['implied_rule_thickness_mm'] = (round((Wm + Hm - math.sqrt(max(disc, 0))) / 4.0, 3)
                                              if disc >= 0 else None)
            p['role'] = 'outline rectangle'
        elif p['fill_of_bbox'] >= 0.45:
            p['role'] = 'solid block or glyph'
    # mid-line run structure (frame, gap, block, gap, frame)
    midy, midx = h // 2, w // 2
    rr = P.runs_along(sub[midy:midy + 1, :], 1)
    cc = P.runs_along(sub[:, midx:midx + 1], 0)
    out['mid_row_run_widths_mm'] = [round(float(v) / tg.px_per_mm_x, 3) for v in rr]
    out['mid_col_run_widths_mm'] = [round(float(v) / tg.px_per_mm_y, 3) for v in cc]
    cb = sub[int(0.2 * h):int(0.8 * h), int(0.2 * w):int(0.8 * w)]
    out['central_60pct_red_fill'] = round(float(cb.mean()), 4) if cb.size else None
    if t + b < h - 2 and l + r < w - 2:
        inner = sub[t:h - b, l:w - r]
        out['inner_bbox'] = tg.box(x0 + l, y0 + t, x1 - r, y1 - b)
        out['inner_red_fill'] = round(float(inner.mean()), 4)
        out['solid_or_outline'] = ('solid (inner area is inked)' if inner.mean() > 0.55
                                   else 'outline (inner area is mostly bare)'
                                   if inner.mean() < 0.25 else 'part-filled')
        # mottle: how broken is the fill?
        lab, n = P.label_cc(~inner)
        st = [s for s in P.cc_stats(lab, n) if s]
        out['n_holes_in_fill'] = len(st)
        out['hole_area_frac'] = round(float((~inner).mean()), 4)
        if st:
            areas = sorted([s['area'] for s in st], reverse=True)
            out['largest_hole_mm2'] = round(areas[0] / (tg.px_per_mm_x * tg.px_per_mm_y), 3)
            out['median_hole_mm2'] = round(float(np.median(areas)) /
                                           (tg.px_per_mm_x * tg.px_per_mm_y), 4)
    # corner treatment: fill of a frame-stroke-sized square at each corner, and
    # whether a rule overshoots past the corner (hand-drawn) or stops square
    cw = max(2, int(round(0.5 * (t + b + l + r) / 2.0)))
    corners = {}
    for tag, (ax, ay) in (('tl', (0, 0)), ('tr', (w - cw, 0)),
                          ('bl', (0, h - cw)), ('br', (w - cw, h - cw))):
        corners[tag] = round(float(sub[ay:ay + cw, ax:ax + cw].mean()), 3)
    out['corner_fill'] = corners
    out['corner_treatment'] = ('closed square corners' if min(corners.values()) > 0.8
                               else 'broken / open corners' if min(corners.values()) < 0.45
                               else 'partly broken corners')
    # the device inside: paper islands enclosed by the seal's INKED block, so
    # the bare gap between an outline and the block is not counted as artwork
    blocks = [c for c in parts
              if c['area'] / max((c['x1'] - c['x0']) * (c['y1'] - c['y0']), 1) >= 0.45
              and (c['x1'] - c['x0']) * (c['y1'] - c['y0']) > 0.25 * (x1 - x0) * (y1 - y0)]
    devwin = np.zeros_like(sub)
    if blocks:
        bb = max(blocks, key=lambda c: c['area'])
        devwin[bb['y0'] - y0:bb['y1'] - y0, bb['x0'] - x0:bb['x1'] - x0] = True
        out['device_search'] = 'inside the solid block ' + str(
            tg.box(bb['x0'], bb['y0'], bb['x1'], bb['y1'])['w_mm'])
    else:
        devwin[:] = True
        out['device_search'] = 'whole seal (no distinct solid block found)'
    dev = paperish[y0:y1, x0:x1] & _filled(sub) & devwin
    labd, nd = P.label_cc(dev)
    sd = [s for s in P.cc_stats(labd, nd) if s and s['area'] > max(6, 0.02 * tg.px_per_mm ** 2)]
    sd.sort(key=lambda s: -s['area'])
    out['n_device_islands'] = len(sd)
    if sd:
        dm = np.zeros_like(dev)
        for s in sd[:20]:
            dm |= (labd == s['label'])
        dx0, dy0, dx1, dy1 = bbox_of(dm)
        out['device_bbox'] = tg.box(x0 + dx0, y0 + dy0, x0 + dx1, y0 + dy1)
        out['device_area_mm2'] = round(float(dm.sum()) / (tg.px_per_mm_x * tg.px_per_mm_y), 3)
        out['device_frac_of_seal'] = round(float(dm.sum()) / max(float(big.sum()), 1.0), 4)
        sm = P.stroke_metrics(dm[dy0:dy1, dx0:dx1], tg.px_per_mm)
        if sm:
            out['device_stroke'] = sm
        out['device_islands'] = [dict(
            bbox=tg.box(x0 + s['x0'], y0 + s['y0'], x0 + s['x1'], y0 + s['y1']),
            area_mm2=round(s['area'] / (tg.px_per_mm_x * tg.px_per_mm_y), 3)) for s in sd[:8]]
    out['mask'] = big
    return out


def _filled(sub):
    """Everything enclosed by the seal's red outline (holes filled)."""
    inv = ~sub
    lab, n = P.label_cc(inv)
    edge = set(np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])))
    edge.discard(0)
    return ~np.isin(lab, list(edge))


def seal_metrics(tg, red, paperish, box_mm, name):
    """Measure a seal: outer/inner frame, stroke width, fill, inner device."""
    H, W = red.shape
    ys, xs = np.mgrid[0:H, 0:W]
    xmm = xs / W * CARD_W_MM
    ymm = ys / H * CARD_H_MM
    win = (xmm >= box_mm[0]) & (xmm <= box_mm[2]) & (ymm >= box_mm[1]) & (ymm <= box_mm[3])
    m = red & win
    if m.sum() < 50:
        return None
    cs = comps(m, max(20, int(0.00002 * W * H)), 2)
    if not cs:
        return None
    big = cs[0]['mask']
    for c in cs[1:]:
        if c['area'] > 0.25 * cs[0]['area']:
            big = big | c['mask']
    x0, y0, x1, y1 = bbox_of(big)
    out = dict(name=name, outer_bbox=tg.box(x0, y0, x1, y1))
    # frame stroke: rows/cols through the middle
    midy = (y0 + y1) // 2
    midx = (x0 + x1) // 2
    rowrun = P.runs_along(big[midy:midy + 1, x0:x1], 1)
    colrun = P.runs_along(big[y0:y1, midx:midx + 1], 0)
    out['mid_row_runs_px'] = [float(v) for v in rowrun]
    out['mid_col_runs_px'] = [float(v) for v in colrun]
    # solid vs outline: fill ratio
    fill = float(big.sum()) / max((x1 - x0) * (y1 - y0), 1)
    out['fill_of_bbox'] = round(fill, 4)
    # interior: the hole(s) inside the red
    inner = win & ~big
    lab, n = P.label_cc(inner)
    st = [s for s in P.cc_stats(lab, n) if s]
    st = [s for s in st if s['x0'] > x0 and s['x1'] < x1 and s['y0'] > y0 and s['y1'] < y1]
    st.sort(key=lambda s: -s['area'])
    out['n_interior_holes'] = len(st)
    if st:
        s = st[0]
        out['inner_bbox'] = tg.box(s['x0'], s['y0'], s['x1'], s['y1'])
        out['frame_stroke_mm'] = dict(
            left=round(tg.mmx(s['x0'] - x0), 3), right=round(tg.mmx(x1 - s['x1']), 3),
            top=round(tg.mmy(s['y0'] - y0), 3), bottom=round(tg.mmy(y1 - s['y1']), 3))
    # corner treatment: is the red continuous around the corners?
    cw = max(2, int(round(1.2 * tg.px_per_mm)))
    corners = {}
    for tagc, (ax, ay) in (('tl', (x0, y0)), ('tr', (x1 - cw, y0)),
                           ('bl', (x0, y1 - cw)), ('br', (x1 - cw, y1 - cw))):
        patch = big[ay:ay + cw, ax:ax + cw]
        corners[tagc] = round(float(patch.mean()), 3)
    out['corner_fill'] = corners
    # fill texture of the solid area (mottle) - measured on the red mask density
    interior = big[y0 + cw:y1 - cw, x0 + cw:x1 - cw]
    if interior.size:
        out['interior_red_fill'] = round(float(interior.mean()), 4)
        # device inside: paper-coloured islands within the solid red
        dev = paperish[y0:y1, x0:x1]
        labd, nd = P.label_cc(dev)
        sd = [s for s in P.cc_stats(labd, nd) if s and s['area'] > 8]
        sd = [s for s in sd if s['x0'] > 1 and s['y0'] > 1 and s['x1'] < (x1 - x0 - 1) and s['y1'] < (y1 - y0 - 1)]
        sd.sort(key=lambda s: -s['area'])
        out['n_device_islands'] = len(sd)
        if sd:
            dm = np.zeros_like(dev)
            for s in sd[:12]:
                dm |= (labd == s['label'])
            dx0, dy0, dx1, dy1 = bbox_of(dm)
            out['device_bbox'] = tg.box(x0 + dx0, y0 + dy0, x0 + dx1, y0 + dy1)
            out['device_area_mm2'] = round(float(dm.sum()) / (tg.px_per_mm_x * tg.px_per_mm_y), 3)
            sm = P.stroke_metrics(dm[dy0:dy1, dx0:dx1], tg.px_per_mm)
            if sm:
                out['device_stroke'] = sm
            out['device_frac_of_inner'] = round(
                float(dm.sum()) / max(float(big.sum()), 1.0), 4)
    out['mask'] = big
    return out
