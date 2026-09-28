# -*- coding: utf-8 -*-
"""Tag detection + rectification shared by the measurement passes."""
import numpy as np
import lib_metro as L

CARD_W_MM = 70.0
CARD_H_MM = 156.0
PPMM = 14.0                      # canonical resolution
CW = int(round(CARD_W_MM * PPMM))   # 980
CH = int(round(CARD_H_MM * PPMM))   # 2184


def tag_mask_ref(a):
    """Reference images: cream tag on near-white ground."""
    rgb = a[..., :3]
    m = (L.lum(rgb) < 0.965) | (L.sat(rgb) > 0.045)
    return _largest_filled(m)


def tag_mask_ours(a, xmax):
    """Our BC atlas: cream tag on brown padding. Restrict to the front island."""
    rgb = a[:, :xmax, :3]
    m = L.lum(rgb) > 0.69
    m = _largest_filled(m)
    full = np.zeros(a.shape[:2], bool)
    full[:, :xmax] = m
    return full


def _largest_filled(m):
    m = L.open_(L.close_(m, 2), 2)
    lab, comps = L.label_components(m)
    m = (lab == comps[0]['label'])
    inv = ~m
    lab2, comps2 = L.label_components(inv)
    bgl = next((c['label'] for c in comps2 if c['x0'] == 0 and c['y0'] == 0), comps2[0]['label'])
    return ~(lab2 == bgl)


def edge_profiles(m):
    h, w = m.shape
    left = np.full(h, np.nan); right = np.full(h, np.nan)
    top = np.full(w, np.nan); bot = np.full(w, np.nan)
    for y in range(h):
        xs = np.nonzero(m[y])[0]
        if len(xs) > 8:
            left[y] = xs[0]; right[y] = xs[-1]
    for x in range(w):
        ys = np.nonzero(m[:, x])[0]
        if len(ys) > 8:
            top[x] = ys[0]; bot[x] = ys[-1]
    return left, right, top, bot


def fit_quad(m):
    """Fit the four straight edges; return dict with line params + corners
    (continuous image coords) and edge residual stats."""
    left, right, top, bot = edge_profiles(m)
    yv = np.nonzero(~np.isnan(left))[0]; y0, y1 = yv[0], yv[-1]; H0 = y1 - y0 + 1
    xv = np.nonzero(~np.isnan(top))[0]; x0, x1 = xv[0], xv[-1]; W0 = x1 - x0 + 1
    lo, hi = y0 + int(.20 * H0), y0 + int(.80 * H0)
    yy = np.arange(lo, hi + 1, dtype=float)
    aL, bL, rL, resL = L.fit_line(left[lo:hi + 1], yy)
    aR, bR, rR, resR = L.fit_line(right[lo:hi + 1], yy)
    xlo, xhi = x0 + int(.25 * W0), x0 + int(.75 * W0)
    xx = np.arange(xlo, xhi + 1, dtype=float)
    aT, bT, rT, resT = L.fit_line(top[xlo:xhi + 1], xx)
    aB, bB, rB, resB = L.fit_line(bot[xlo:xhi + 1], xx)
    bR += 1.0   # outer boundary of the right-most pixel
    bB += 1.0

    def isect(av, bv, ah, bh):
        y = (ah * bv + bh) / (1 - ah * av)
        return (av * y + bv, y)
    q = dict(
        aL=aL, bL=bL, aR=aR, bR=bR, aT=aT, bT=bT, aB=aB, bB=bB,
        rmsL=rL, rmsR=rR, rmsT=rT, rmsB=rB,
        resL=resL, resR=resR, resT=resT, resB=resB,
        yspan=(int(y0), int(y1)), xspan=(int(x0), int(x1)),
        left=left, right=right, top=top, bot=bot)
    q['TL'] = isect(aL, bL, aT, bT); q['TR'] = isect(aR, bR, aT, bT)
    q['BL'] = isect(aL, bL, aB, bB); q['BR'] = isect(aR, bR, aB, bB)
    return q


def refine_edges(a, q):
    """Sub-pixel edge location: per scanline, find the 50% luminance crossing
    between the ground outside the tag and the paper just inside it, then refit
    the four edge lines.  Returns a NEW q with refined a*/b* and corners, plus a
    record of how far each refined edge moved from the binary-mask edge."""
    lu = L.lum(a[..., :3])
    h, w = lu.shape
    out = dict(q)
    rec = {}

    def cross(prof_out, prof_in, samples):
        """samples: list of (coord, value) ordered OUTSIDE -> INSIDE."""
        tgt = 0.5 * (prof_out + prof_in)
        rising = prof_in < prof_out
        for i in range(1, len(samples)):
            c0, v0 = samples[i - 1]; c1, v1 = samples[i]
            if (rising and v0 >= tgt > v1) or ((not rising) and v0 <= tgt < v1):
                if v1 == v0:
                    return c1
                return c0 + (v0 - tgt) / (v0 - v1) * (c1 - c0)
        return None

    y0, y1 = q['yspan']; x0, x1 = q['xspan']
    H0 = y1 - y0 + 1; W0 = x1 - x0 + 1
    OUT, SPAN = 12, 4
    bg_global = float(np.median(np.concatenate([
        lu[:6, :6].ravel(), lu[:6, -6:].ravel(), lu[-6:, :6].ravel(), lu[-6:, -6:].ravel()])))

    for side in ('left', 'right', 'top', 'bottom'):
        vert = side in ('left', 'right')
        if vert:
            rng = range(y0 + int(.20 * H0), y0 + int(.80 * H0))
            base = (lambda y: q['aL'] * y + q['bL']) if side == 'left' else (lambda y: q['aR'] * y + q['bR'] - 1.0)
        else:
            rng = range(x0 + int(.25 * W0), x0 + int(.75 * W0))
            base = (lambda x: q['aT'] * x + q['bT']) if side == 'top' else (lambda x: q['aB'] * x + q['bB'] - 1.0)
        sgn = +1 if side in ('left', 'top') else -1   # inside is at +sgn
        pos, at = [], []
        lim = w if vert else h
        for t in rng:
            e = base(t)
            ei = int(round(e))
            # sample OUTSIDE -> INSIDE, clipped to the image
            coords = [ei - sgn * k for k in range(OUT, -OUT - 1, -1)]
            coords = [k for k in coords if 0 <= k < lim]
            if len(coords) < 8:
                continue
            vals = [float(lu[t, k]) if vert else float(lu[k, t]) for k in coords]
            samp = list(zip(coords, vals))
            outs = [v for k, v in samp if sgn * (k - ei) <= -SPAN]
            ins = [v for k, v in samp if sgn * (k - ei) >= SPAN]
            if len(ins) < 3:
                continue
            vi = float(np.median(ins))
            vo = float(np.median(outs)) if len(outs) >= 3 else bg_global
            if abs(vo - vi) < 0.02:
                continue
            c = cross(vo, vi, samp)
            if c is not None and abs(c - e) < 8:
                pos.append(c); at.append(t)
        if len(pos) < 20:
            rec[side] = dict(note='refinement failed, kept mask edge'); continue
        pos = np.array(pos); at = np.array(at, float)
        A = np.stack([at, np.ones_like(at)], 1)
        sol, *_ = np.linalg.lstsq(A, pos, rcond=None)
        res = pos - A @ sol
        old = np.array([base(t) for t in at])
        rec[side] = dict(shift_px=round(float((pos - old).mean()), 3),
                         rms_px=round(float(np.sqrt((res ** 2).mean())), 3),
                         n=int(len(pos)))
        # continuous coords: a 50% crossing at index c sits at continuous c+0.5
        if side == 'left':   out['aL'], out['bL'] = float(sol[0]), float(sol[1]) + 0.5
        elif side == 'right': out['aR'], out['bR'] = float(sol[0]), float(sol[1]) + 0.5
        elif side == 'top':   out['aT'], out['bT'] = float(sol[0]), float(sol[1]) + 0.5
        else:                 out['aB'], out['bB'] = float(sol[0]), float(sol[1]) + 0.5
        out['res' + side[0].upper()] = res

    def isect(av, bv, ah, bh):
        y = (ah * bv + bh) / (1 - ah * av)
        return (av * y + bv, y)
    out['TL'] = isect(out['aL'], out['bL'], out['aT'], out['bT'])
    out['TR'] = isect(out['aR'], out['bR'], out['aT'], out['bT'])
    out['BL'] = isect(out['aL'], out['bL'], out['aB'], out['bB'])
    out['BR'] = isect(out['aR'], out['bR'], out['aB'], out['bB'])
    out['refinement'] = rec
    return out


def rectify(a, q, cw=CW, ch=CH):
    src = np.array([q['TL'], q['TR'], q['BR'], q['BL']], float)
    dst = np.array([[0, 0], [cw, 0], [cw, ch], [0, ch]], float)
    Hm = L.homography(src, dst)
    Hi = np.linalg.inv(Hm)
    return L.warp(a[..., :3], Hi, cw, ch), Hm


def classify(rgb):
    """Per-image adaptive paper / red / black separation (stored values)."""
    lu = L.lum(rgb)
    rex = rgb[..., 0] - 0.5 * (rgb[..., 1] + rgb[..., 2])
    paper_lum = float(np.percentile(lu, 60))
    ink_lum = float(np.percentile(lu[lu < np.percentile(lu, 12)], 50))
    thr_ink = 0.5 * (paper_lum + ink_lum)
    paper_rex = float(np.median(rex[lu > paper_lum - 0.05]))
    red_rex = float(np.percentile(rex, 99))
    thr_red = 0.5 * (paper_rex + red_rex)
    red = rex > thr_red
    black = (lu < thr_ink) & ~red
    return dict(red=red, black=black, lum=lu, rex=rex,
                paper_lum=paper_lum, ink_lum=ink_lum, thr_ink=thr_ink,
                paper_rex=paper_rex, red_rex=red_rex, thr_red=thr_red)


def clusters(mask, rad, min_area):
    """Dilate by rad px, label, then report ORIGINAL-ink stats per cluster."""
    d = L.dilate(mask, rad)
    lab, _ = L.label_components(d)
    out = []
    ids = np.unique(lab[mask])
    for i in ids:
        if i == 0:
            continue
        sel = mask & (lab == i)
        ys, xs = np.nonzero(sel)
        if len(xs) < min_area:
            continue
        out.append(dict(n=int(len(xs)), x0=int(xs.min()), x1=int(xs.max()),
                        y0=int(ys.min()), y1=int(ys.max()),
                        cx=float(xs.mean()), cy=float(ys.mean())))
    out.sort(key=lambda d: -d['n'])
    return out
