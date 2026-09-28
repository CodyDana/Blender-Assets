# -*- coding: utf-8 -*-
"""Measurement primitives: exact EDT, connected components, morphology,
radial power spectra. Pure numpy, runs inside Blender's Python.
"""
import numpy as np

INF = 1e20


def _edt1d(f):
    n = f.shape[0]
    d = np.empty(n)
    v = np.zeros(n, dtype=np.int64)
    z = np.empty(n + 1)
    k = 0
    v[0] = 0
    z[0] = -INF
    z[1] = INF
    for q in range(1, n):
        fq = f[q]
        s = ((fq + q * q) - (f[v[k]] + v[k] * v[k])) / (2.0 * q - 2.0 * v[k])
        while s <= z[k]:
            k -= 1
            s = ((fq + q * q) - (f[v[k]] + v[k] * v[k])) / (2.0 * q - 2.0 * v[k])
        k += 1
        v[k] = q
        z[k] = s
        z[k + 1] = INF
    k = 0
    for q in range(n):
        while z[k + 1] < q:
            k += 1
        dq = q - v[k]
        d[q] = dq * dq + f[v[k]]
    return d


def _edt1d_batch(f):
    """Felzenszwalb-Huttenlocher lower envelope, vectorised over lanes.
    f: (n, L) squared-distance seed. Returns (n, L)."""
    n, L = f.shape
    d = np.empty((n, L))
    v = np.zeros((n, L), dtype=np.int64)
    z = np.empty((n + 1, L))
    k = np.zeros(L, dtype=np.int64)
    lanes = np.arange(L)
    z[0] = -INF
    z[1] = INF
    with np.errstate(divide="ignore", invalid="ignore"):
        for q in range(1, n):
            fq = f[q]
            qq = float(q * q)
            while True:
                vk = v[k, lanes]
                den = 2.0 * q - 2.0 * vk
                s = ((fq + qq) - (f[vk, lanes] + vk * vk)) / den
                bad = s <= z[k, lanes]
                if not bad.any():
                    break
                k[bad] -= 1
            k += 1
            v[k, lanes] = q
            z[k, lanes] = s
            z[k + 1, lanes] = INF
        k[:] = 0
        for q in range(n):
            while True:
                mv = z[k + 1, lanes] < q
                if not mv.any():
                    break
                k[mv] += 1
            vk = v[k, lanes]
            dq = (q - vk).astype(np.float64)
            d[q] = dq * dq + f[vk, lanes]
    return d


def edt(mask):
    """Exact Euclidean distance (px) from every pixel to the nearest False pixel.
    True pixels get their distance to the outside; False pixels get 0."""
    m = np.asarray(mask, bool)
    if not m.any():
        return np.zeros(m.shape)
    if m.all():
        # no zero anywhere: distance is to the array border+1 (never used here)
        return np.full(m.shape, INF ** 0.5)
    f = np.where(m, INF, 0.0)
    out = _edt1d_batch(f)                      # along axis 0, lanes = columns
    out = _edt1d_batch(np.ascontiguousarray(out.T)).T   # along axis 1
    return np.sqrt(np.maximum(out, 0.0))


def dist_outside(mask):
    """Distance from every pixel to the nearest True pixel (0 inside the mask)."""
    return edt(~np.asarray(mask, bool))


def dilate(mask, r):
    if r <= 0:
        return np.asarray(mask, bool).copy()
    return dist_outside(mask) <= r


def erode(mask, r):
    if r <= 0:
        return np.asarray(mask, bool).copy()
    return edt(mask) > r


def closing(mask, r):
    return erode(dilate(mask, r), r)


def opening(mask, r):
    return dilate(erode(mask, r), r)


class Find:
    __slots__ = ("p",)

    def __init__(self):
        self.p = [0]

    def new(self):
        self.p.append(len(self.p))
        return len(self.p) - 1

    def find(self, a):
        p = self.p
        while p[a] != a:
            p[a] = p[p[a]]
            a = p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if ra < rb:
                self.p[rb] = ra
            else:
                self.p[ra] = rb


def label_cc(mask):
    """8-connected labelling by row runs + union-find.
    Returns (labels int32 (0=background), n_labels)."""
    m = np.asarray(mask, bool)
    H, W = m.shape
    uf = Find()
    rows = []
    prev = []
    for y in range(H):
        row = m[y].astype(np.int8)
        d = np.diff(np.concatenate(([0], row, [0])))
        starts = np.flatnonzero(d == 1)
        ends = np.flatnonzero(d == -1)
        cur = []
        j = 0
        for s, e in zip(starts, ends):
            lab = uf.new()
            # 8-connectivity: previous-row runs overlapping [s-1, e+1)
            while j < len(prev) and prev[j][1] < s:
                j += 1
            jj = j
            while jj < len(prev) and prev[jj][0] <= e:
                uf.union(lab, prev[jj][2])
                jj += 1
            cur.append((s, e, lab))
        rows.append(cur)
        prev = cur
    remap = {}
    labels = np.zeros((H, W), np.int32)
    nxt = 1
    for y, cur in enumerate(rows):
        for s, e, lab in cur:
            r = uf.find(lab)
            v = remap.get(r)
            if v is None:
                v = nxt
                remap[r] = v
                nxt += 1
            labels[y, s:e] = v
    return labels, nxt - 1


def cc_stats(labels, n, px_per_unit_x=1.0, px_per_unit_y=1.0):
    """Per-component area, bbox, centroid, second moments -> elongation, angle."""
    if n == 0:
        return []
    flat = labels.ravel()
    H, W = labels.shape
    ys, xs = np.divmod(np.arange(flat.size), W)
    sel = flat > 0
    lab = flat[sel]
    ys = ys[sel].astype(np.float64)
    xs = xs[sel].astype(np.float64)
    area = np.bincount(lab, minlength=n + 1).astype(np.float64)
    sx = np.bincount(lab, weights=xs, minlength=n + 1)
    sy = np.bincount(lab, weights=ys, minlength=n + 1)
    sxx = np.bincount(lab, weights=xs * xs, minlength=n + 1)
    syy = np.bincount(lab, weights=ys * ys, minlength=n + 1)
    sxy = np.bincount(lab, weights=xs * ys, minlength=n + 1)
    mnx = np.full(n + 1, np.inf)
    mxx = np.full(n + 1, -np.inf)
    mny = np.full(n + 1, np.inf)
    mxy = np.full(n + 1, -np.inf)
    np.minimum.at(mnx, lab, xs)
    np.maximum.at(mxx, lab, xs)
    np.minimum.at(mny, lab, ys)
    np.maximum.at(mxy, lab, ys)
    out = []
    for i in range(1, n + 1):
        a = area[i]
        if a <= 0:
            continue
        cx, cy = sx[i] / a, sy[i] / a
        mxx2 = sxx[i] / a - cx * cx
        myy2 = syy[i] / a - cy * cy
        mxy2 = sxy[i] / a - cx * cy
        tr = mxx2 + myy2
        det = mxx2 * myy2 - mxy2 * mxy2
        disc = max(tr * tr / 4.0 - det, 0.0)
        l1 = tr / 2.0 + np.sqrt(disc)
        l2 = tr / 2.0 - np.sqrt(disc)
        maj = 2.0 * np.sqrt(max(l1, 0.0))
        mnr = 2.0 * np.sqrt(max(l2, 0.0))
        ang = 0.5 * np.degrees(np.arctan2(2.0 * mxy2, mxx2 - myy2))
        out.append({
            "label": i, "area_px": float(a),
            "cx_px": float(cx), "cy_px": float(cy),
            "bbox_px": [float(mnx[i]), float(mny[i]), float(mxx[i]), float(mxy[i])],
            "major_px": float(maj), "minor_px": float(mnr),
            "elongation": float(maj / mnr) if mnr > 1e-6 else float("inf"),
            "angle_deg": float(ang),
            "equiv_diam_px": float(2.0 * np.sqrt(a / np.pi)),
        })
    return out


def radial_power(img, detrend=True):
    """Radially averaged power spectrum of a 2-D patch.
    Returns (freq_cycles_per_px, power). freq[0] is skipped."""
    a = np.asarray(img, float)
    if detrend:
        a = a - a.mean()
    h, w = a.shape
    wy = np.hanning(h)[:, None]
    wx = np.hanning(w)[None, :]
    a = a * (wy * wx)
    F = np.fft.fftshift(np.fft.fft2(a))
    P = (np.abs(F) ** 2) / (h * w)
    ky = (np.arange(h) - h // 2) / float(h)
    kx = (np.arange(w) - w // 2) / float(w)
    KX, KY = np.meshgrid(kx, ky)
    R = np.sqrt(KX ** 2 + KY ** 2)
    nb = int(min(h, w) // 2)
    edges = np.linspace(0, 0.5, nb + 1)
    idx = np.clip(np.digitize(R.ravel(), edges) - 1, 0, nb - 1)
    cnt = np.bincount(idx, minlength=nb)
    tot = np.bincount(idx, weights=P.ravel(), minlength=nb)
    with np.errstate(invalid="ignore", divide="ignore"):
        prof = tot / np.maximum(cnt, 1)
    centres = 0.5 * (edges[:-1] + edges[1:])
    return centres[1:], prof[1:], (P, KX, KY, R)


def angular_power(P, KX, KY, R, f_lo, f_hi, nbins=18):
    """Power vs orientation inside an annulus -> anisotropy."""
    m = (R >= f_lo) & (R < f_hi)
    th = (np.degrees(np.arctan2(KY[m], KX[m])) % 180.0)
    p = P[m]
    edges = np.linspace(0, 180, nbins + 1)
    idx = np.clip(np.digitize(th, edges) - 1, 0, nbins - 1)
    cnt = np.bincount(idx, minlength=nbins)
    tot = np.bincount(idx, weights=p, minlength=nbins)
    prof = tot / np.maximum(cnt, 1)
    return 0.5 * (edges[:-1] + edges[1:]), prof


def boxblur(a, r):
    """Separable box blur with reflect padding; r in px (half-width)."""
    if r < 1:
        return np.asarray(a, float).copy()
    a = np.asarray(a, float)
    k = 2 * int(r) + 1
    pad = int(r)
    b = np.pad(a, ((pad, pad), (0, 0)), mode="reflect")
    c = np.cumsum(b, axis=0)
    c = np.vstack([np.zeros((1, a.shape[1])), c])
    a = (c[k:, :] - c[:-k, :]) / k
    b = np.pad(a, ((0, 0), (pad, pad)), mode="reflect")
    c = np.cumsum(b, axis=1)
    c = np.hstack([np.zeros((a.shape[0], 1)), c])
    return (c[:, k:] - c[:, :-k]) / k


def masked_blur(a, mask, r):
    """Box blur of `a` using only mask pixels (normalised by the mask blur)."""
    m = np.asarray(mask, float)
    num = boxblur(np.asarray(a, float) * m, r)
    den = boxblur(m, r)
    return num / np.maximum(den, 1e-6), den


def pct(a, qs=(0.1, 1, 5, 25, 50, 75, 95, 99, 99.9)):
    a = np.asarray(a, float).ravel()
    if a.size == 0:
        return {str(q): None for q in qs}
    return {("p%g" % q): round(float(np.percentile(a, q)), 6) for q in qs}


def stats(a):
    a = np.asarray(a, float).ravel()
    if a.size == 0:
        return {"n": 0}
    d = {"n": int(a.size), "mean": round(float(a.mean()), 6),
         "std": round(float(a.std()), 6), "min": round(float(a.min()), 6),
         "max": round(float(a.max()), 6)}
    d.update(pct(a))
    return d
