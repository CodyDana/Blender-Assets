# -*- coding: utf-8 -*-
"""pbmetro - image metrology helpers for the paper-bomb reference study.

Runs inside Blender 5.2's Python (numpy 2.x).  MEASUREMENT ONLY: this module
loads reference images to produce NUMBERS.  It never writes any pixel data
derived from a reference image.  Debug output is drawn from measured numbers
onto a blank canvas.

Colour convention: images are loaded with colorspace 'Non-Color' so that
image.pixels yields the STORED (sRGB-encoded) 8-bit values scaled to 0..1.
Every value this module reports is a STORED value unless the name says linear.
"""
import math
import numpy as np

INF = 1e12


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------
def load_stored(path):
    """Load a PNG as top-down float32 HxWxC of STORED (sRGB-encoded) values."""
    import bpy
    img = bpy.data.images.load(path, check_existing=False)
    try:
        img.colorspace_settings.name = 'Non-Color'
    except Exception:
        pass
    w, h = img.size
    ch = img.channels
    buf = np.empty(w * h * ch, dtype=np.float32)
    img.pixels.foreach_get(buf)
    a = buf.reshape(h, w, ch)[::-1].copy()      # Blender is bottom-up
    bpy.data.images.remove(img)
    return a


def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def luma_stored(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


# --------------------------------------------------------------------------
# morphology (numpy shift based, structuring element = square or disk)
# --------------------------------------------------------------------------
def _shift_or(m, dy, dx):
    out = np.zeros_like(m)
    h, w = m.shape
    ys0, ys1 = max(0, dy), min(h, h + dy)
    xs0, xs1 = max(0, dx), min(w, w + dx)
    out[ys0:ys1, xs0:xs1] = m[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def dilate(m, r=1, disk=True):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy == 0 and dx == 0:
                continue
            if disk and dy * dy + dx * dx > r * r + 0.01:
                continue
            out |= _shift_or(m, dy, dx)
    return out


def erode(m, r=1, disk=True):
    return ~dilate(~m, r, disk)


def close(m, r=1):
    return erode(dilate(m, r), r)


def open_(m, r=1):
    return dilate(erode(m, r), r)


# --------------------------------------------------------------------------
# exact Euclidean distance transform (Felzenszwalb & Huttenlocher, vectorised
# over lines; the inner loop walks positions, numpy walks the lines)
# --------------------------------------------------------------------------
def _dt1d(f):
    """squared-distance transform along axis 1 of f (m, n)."""
    m, n = f.shape
    if n == 1:
        return f.copy()
    v = np.zeros((m, n), dtype=np.int64)
    z = np.empty((m, n + 1), dtype=np.float64)
    z[:, 0] = -INF
    z[:, 1] = INF
    k = np.zeros(m, dtype=np.int64)
    rows = np.arange(m)
    for q in range(1, n):
        fq = f[:, q]
        while True:
            vk = v[rows, k]
            s = ((fq + q * q) - (f[rows, vk] + vk * vk)) / (2.0 * q - 2.0 * vk)
            bad = (s <= z[rows, k]) & (k > 0)
            if not bad.any():
                break
            k[bad] -= 1
        k += 1
        v[rows, k] = q
        z[rows, k] = s
        z[rows, k + 1] = INF
    out = np.empty((m, n), dtype=np.float64)
    k[:] = 0
    for q in range(n):
        while True:
            adv = z[rows, k + 1] < q
            if not adv.any():
                break
            k[adv] += 1
        vk = v[rows, k]
        out[:, q] = (q - vk) ** 2 + f[rows, vk]
    return out


def edt(mask):
    """Euclidean distance (px) from each True pixel to the nearest False pixel.

    The array is treated as bounded by background on all four sides.
    """
    f = np.where(mask, INF, 0.0)
    d = _dt1d(f)                       # along x
    d = _dt1d(d.T.copy()).T            # along y
    np.minimum(d, INF, out=d)
    return np.sqrt(np.maximum(d, 0.0))


# --------------------------------------------------------------------------
# connected components (run-length + union-find, 8-connected)
# --------------------------------------------------------------------------
def label_cc(mask):
    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    parent = [0]

    def find(x):
        r = x
        while parent[r] != r:
            r = parent[r]
        while parent[x] != r:
            parent[x], x = r, parent[x]
        return r

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    prev = []                      # list of (start, end, label)
    nxt_label = 1
    for y in range(h):
        row = mask[y]
        if not row.any():
            prev = []
            continue
        d = np.diff(row.astype(np.int8))
        starts = np.flatnonzero(d == 1) + 1
        ends = np.flatnonzero(d == -1) + 1
        if row[0]:
            starts = np.concatenate(([0], starts))
        if row[-1]:
            ends = np.concatenate((ends, [w]))
        cur = []
        j = 0
        for s, e in zip(starts, ends):
            lab = 0
            while j < len(prev) and prev[j][1] < s:        # 8-conn: touch ok
                j += 1
            jj = j
            while jj < len(prev) and prev[jj][0] <= e:
                pl = prev[jj][2]
                lab = pl if lab == 0 else lab
                union(lab, pl)
                jj += 1
            if lab == 0:
                lab = nxt_label
                parent.append(nxt_label)
                nxt_label += 1
            labels[y, s:e] = lab
            cur.append((s, e, lab))
        prev = cur

    if nxt_label == 1:
        return labels, 0
    roots = np.array([find(i) for i in range(nxt_label)], dtype=np.int32)
    uniq, remap = np.unique(roots, return_inverse=True)
    remap = remap.astype(np.int32)
    remap[0] = 0
    if uniq[0] == 0:
        pass
    else:
        remap += 1
    out = remap[labels]
    return out, int(out.max())


def cc_stats(labels, n):
    """Return list of dicts with area/bbox/centroid per label (1..n)."""
    if n == 0:
        return []
    flat = labels.ravel()
    area = np.bincount(flat, minlength=n + 1)
    h, w = labels.shape
    ys, xs = np.mgrid[0:h, 0:w]
    sy = np.bincount(flat, weights=ys.ravel(), minlength=n + 1)
    sx = np.bincount(flat, weights=xs.ravel(), minlength=n + 1)
    out = []
    for i in range(1, n + 1):
        if area[i] == 0:
            out.append(None)
            continue
        m = labels == i
        rows = np.flatnonzero(m.any(axis=1))
        cols = np.flatnonzero(m.any(axis=0))
        out.append(dict(label=i, area=int(area[i]),
                        x0=int(cols[0]), x1=int(cols[-1] + 1),
                        y0=int(rows[0]), y1=int(rows[-1] + 1),
                        cx=float(sx[i] / area[i]), cy=float(sy[i] / area[i])))
    return out


# --------------------------------------------------------------------------
# stroke width
# --------------------------------------------------------------------------
def ridge_mask(dist):
    """Pixels that are a local max of the distance transform (the stroke spine)."""
    m = dist > 0.75
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        sh = np.full_like(dist, -1.0)
        h, w = dist.shape
        ys0, ys1 = max(0, dy), min(h, h + dy)
        xs0, xs1 = max(0, dx), min(w, w + dx)
        sh[ys0:ys1, xs0:xs1] = dist[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
        m &= dist >= sh - 1e-6
    return m


def perimeter_px(mask):
    """4-neighbour boundary edge count (a good ribbon perimeter estimate)."""
    p = 0
    p += int((mask[:, 1:] & ~mask[:, :-1]).sum())
    p += int((mask[:, :-1] & ~mask[:, 1:]).sum())
    p += int((mask[1:, :] & ~mask[:-1, :]).sum())
    p += int((mask[:-1, :] & ~mask[1:, :]).sum())
    p += int(mask[:, 0].sum()) + int(mask[:, -1].sum())
    p += int(mask[0, :].sum()) + int(mask[-1, :].sum())
    return p


def runs_along(mask, axis):
    """Lengths of all True runs along the given axis (1 = rows -> vertical-stroke
    widths; 0 = columns -> horizontal-stroke widths)."""
    m = mask if axis == 1 else mask.T
    pad = np.zeros((m.shape[0], 1), dtype=bool)
    mm = np.concatenate([pad, m, pad], axis=1).astype(np.int8)
    d = np.diff(mm, axis=1)
    ys, xs = np.nonzero(d == 1)
    ys2, xe = np.nonzero(d == -1)
    return (xe - xs).astype(np.float64)


def stroke_metrics(mask, px_per_mm, tag_frac_px=None):
    """Full stroke-width report for one binary element."""
    if mask.sum() < 8:
        return None
    dist = edt(np.pad(mask, 1))[1:-1, 1:-1]
    ridge = ridge_mask(dist)
    rv = dist[ridge] * 2.0                      # spine distance -> full width
    area = float(mask.sum())
    per = perimeter_px(mask)
    ribbon_w = 2.0 * area / per if per else float('nan')
    rl_v = runs_along(mask, 1)                  # widths of vertical strokes
    rl_h = runs_along(mask, 0)                  # widths of horizontal strokes
    rl_v = rl_v[rl_v >= 2]
    rl_h = rl_h[rl_h >= 2]

    def q(a, p):
        return float(np.percentile(a, p)) if len(a) else float('nan')

    out = dict(
        area_px=area,
        perimeter_px=per,
        stroke_max_px=float(dist.max() * 2.0),
        stroke_mean_ridge_px=float(rv.mean()) if len(rv) else float('nan'),
        stroke_median_ridge_px=q(rv, 50),
        stroke_p05_ridge_px=q(rv, 5),
        stroke_p95_ridge_px=q(rv, 95),
        stroke_min_ridge_px=float(rv.min()) if len(rv) else float('nan'),
        stroke_ribbon_mean_px=ribbon_w,
        vstroke_median_px=q(rl_v, 50), vstroke_p10_px=q(rl_v, 10), vstroke_p90_px=q(rl_v, 90),
        hstroke_median_px=q(rl_h, 50), hstroke_p10_px=q(rl_h, 10), hstroke_p90_px=q(rl_h, 90),
    )
    # edge roughness: how much of the outline survives smoothing at a fixed
    # PHYSICAL radius (0.25 mm), so images of different resolution compare
    r = max(1, int(round(0.25 * px_per_mm)))
    sm_mask = open_(close(mask, r), r)
    per_s = perimeter_px(sm_mask)
    xor = int(np.count_nonzero(mask ^ sm_mask))
    out['smooth_radius_px'] = r
    out['perimeter_over_smoothed'] = round(per / max(per_s, 1), 4)
    out['edge_deviation_mm'] = round((xor / max(per, 1)) / px_per_mm, 4)
    out['isoperimetric_ratio'] = round(per / max(2.0 * math.sqrt(math.pi * area), 1e-6), 4)
    out['thick_thin_ratio'] = (out['stroke_p95_ridge_px'] / out['stroke_p05_ridge_px']
                               if out['stroke_p05_ridge_px'] > 0 else float('nan'))
    out['thick_thin_ratio_maxmin'] = (out['stroke_max_px'] / out['stroke_min_ridge_px']
                                      if out['stroke_min_ridge_px'] > 0 else float('nan'))
    for k in list(out.keys()):
        if k.endswith('_px') and k not in ('area_px', 'perimeter_px'):
            out[k[:-3] + '_mm'] = round(out[k] / px_per_mm, 4)
    return out


# --------------------------------------------------------------------------
# taper: how the stroke width behaves at the two ends of an element
# --------------------------------------------------------------------------
def taper_profile(mask, n=12):
    """Width profile along the element's principal axis, n buckets, in px."""
    ys, xs = np.nonzero(mask)
    if len(ys) < 20:
        return None
    x = xs - xs.mean()
    y = ys - ys.mean()
    cov = np.cov(np.vstack([x, y]))
    w_, v_ = np.linalg.eigh(cov)
    ax = v_[:, np.argmax(w_)]                   # principal direction (x, y)
    t = x * ax[0] + y * ax[1]
    s = -x * ax[1] + y * ax[0]
    lo, hi = t.min(), t.max()
    edges = np.linspace(lo, hi, n + 1)
    prof = []
    for i in range(n):
        sel = (t >= edges[i]) & (t <= edges[i + 1])
        prof.append(float(np.ptp(s[sel])) if sel.sum() > 2 else 0.0)
    return dict(axis_deg=float(math.degrees(math.atan2(ax[1], ax[0]))),
                length_px=float(hi - lo), profile_px=[round(p, 2) for p in prof])


# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------
def fit_line_x_of_y(ys, xs):
    """x = a*y + b, returns a, b, rms."""
    A = np.vstack([ys, np.ones_like(ys)]).T
    sol, *_ = np.linalg.lstsq(A, xs, rcond=None)
    res = xs - (A @ sol)
    return float(sol[0]), float(sol[1]), float(np.sqrt((res ** 2).mean()))


def fit_circle(x, y):
    """Algebraic (Kasa) circle fit -> cx, cy, r, rms residual."""
    A = np.vstack([x, y, np.ones_like(x)]).T
    b = x * x + y * y
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx = sol[0] / 2.0
    cy = sol[1] / 2.0
    r = math.sqrt(max(sol[2] + cx * cx + cy * cy, 0.0))
    rr = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    return float(cx), float(cy), float(r), float(np.sqrt(((rr - r) ** 2).mean()))


def fit_ellipse(x, y):
    """Direct conic fit -> dict(cx, cy, a, b, theta_deg, ecc)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    mx, my = x.mean(), y.mean()
    sc = max(np.std(x), np.std(y))
    xs, ys = (x - mx) / sc, (y - my) / sc
    D = np.vstack([xs * xs, xs * ys, ys * ys, xs, ys, np.ones_like(xs)]).T
    _, _, V = np.linalg.svd(D, full_matrices=False)
    a, b, c, d, e, f = V[-1]
    if a + c < 0:                                  # fix the global sign
        a, b, c, d, e, f = -a, -b, -c, -d, -e, -f
    M = np.array([[a, b / 2], [b / 2, c]])
    try:
        cen = np.linalg.solve(2 * M, [-d, -e])
    except np.linalg.LinAlgError:
        return None
    x0, y0 = cen
    num = a * x0 * x0 + b * x0 * y0 + c * y0 * y0 - f
    ev, evec = np.linalg.eigh(M)
    if np.any(ev <= 0) or num <= 0:
        return None
    axes = np.sqrt(num / ev)
    order = np.argsort(-axes)
    axes = axes[order]
    evec = evec[:, order]
    th = math.degrees(math.atan2(evec[1, 0], evec[0, 0]))
    A_, B_ = float(axes[0] * sc), float(axes[1] * sc)
    ecc = math.sqrt(max(1.0 - (B_ / A_) ** 2, 0.0))
    return dict(cx=float(x0 * sc + mx), cy=float(y0 * sc + my),
                semi_major_px=A_, semi_minor_px=B_,
                major_axis_deg=th, eccentricity=ecc,
                axis_ratio=float(B_ / A_))


def warp_bilinear(img, H, out_w, out_h):
    """Sample img with the inverse homography H (3x3 mapping out -> in)."""
    yy, xx = np.mgrid[0:out_h, 0:out_w]
    ones = np.ones_like(xx, dtype=np.float64)
    P = np.stack([xx + 0.5, yy + 0.5, ones], axis=-1)
    Q = P @ H.T
    sx = Q[..., 0] / Q[..., 2] - 0.5
    sy = Q[..., 1] / Q[..., 2] - 0.5
    h, w = img.shape[:2]
    x0 = np.floor(sx).astype(np.int64)
    y0 = np.floor(sy).astype(np.int64)
    fx = (sx - x0)[..., None]
    fy = (sy - y0)[..., None]
    x0c = np.clip(x0, 0, w - 1)
    x1c = np.clip(x0 + 1, 0, w - 1)
    y0c = np.clip(y0, 0, h - 1)
    y1c = np.clip(y0 + 1, 0, h - 1)
    a = img[y0c, x0c].astype(np.float64)
    b = img[y0c, x1c].astype(np.float64)
    c = img[y1c, x0c].astype(np.float64)
    d = img[y1c, x1c].astype(np.float64)
    top = a * (1 - fx) + b * fx
    bot = c * (1 - fx) + d * fx
    return (top * (1 - fy) + bot * fy).astype(np.float32)


def homography(src, dst):
    """src, dst: 4x2 point lists. Returns H mapping dst -> src (for warping)."""
    A = []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    A = np.array(A, dtype=np.float64)
    _, _, V = np.linalg.svd(A)
    H = V[-1].reshape(3, 3)
    return H / H[2, 2]


# --------------------------------------------------------------------------
# projection-profile splitting (for cutting a column into glyph cells)
# --------------------------------------------------------------------------
def split_into_n(prof, n, min_seg):
    """Cut a 1-D ink profile into exactly n segments at the n-1 lightest places.

    CJK column glyphs often touch, so a pure gap split under-counts; this picks
    the deepest valleys subject to a minimum cell size (dynamic programme).
    """
    L = len(prof)
    if n <= 1 or L < n * min_seg:
        return [(0, L)]
    p = np.asarray(prof, dtype=np.float64)
    if len(p) > 4:
        p = np.convolve(p, np.ones(3) / 3.0, mode='same')
    INFV = 1e18
    # dp[k][i] = best cost of cutting the first i samples into k segments
    dp = np.full((n, L + 1), INFV)
    back = np.zeros((n, L + 1), dtype=np.int64)
    for i in range(min_seg, L + 1):
        dp[0, i] = 0.0
    for k in range(1, n):
        for i in range(min_seg * (k + 1), L + 1):
            lo = min_seg * k
            hi = i - min_seg + 1
            if hi <= lo:
                continue
            js = np.arange(lo, hi)
            cost = dp[k - 1, js] + p[js - 1] + p[np.minimum(js, L - 1)]
            m = int(np.argmin(cost))
            if cost[m] < dp[k, i]:
                dp[k, i] = cost[m]
                back[k, i] = js[m]
    cuts = []
    i = L
    for k in range(n - 1, 0, -1):
        j = int(back[k, i])
        cuts.append(j)
        i = j
    cuts = sorted(cuts)
    segs = []
    prev = 0
    for c in cuts:
        segs.append((prev, c))
        prev = c
    segs.append((prev, L))
    return segs


def split_profile(mask, axis, min_gap=1, min_run=3):
    """Split a mask into runs of non-empty lines along `axis`.

    axis=0 -> scan rows (vertical stacking); axis=1 -> scan columns.
    Returns list of (start, end) index pairs, plus the raw profile.
    """
    prof = mask.sum(axis=1 if axis == 0 else 0)
    occ = prof > 0
    segs = []
    i = 0
    n = len(occ)
    while i < n:
        if occ[i]:
            j = i
            gap = 0
            k = i
            while k < n:
                if occ[k]:
                    j = k
                    gap = 0
                else:
                    gap += 1
                    if gap > min_gap:
                        break
                k += 1
            if j - i + 1 >= min_run:
                segs.append((int(i), int(j + 1)))
            i = k
        else:
            i += 1
    return segs, prof.astype(np.int64)
