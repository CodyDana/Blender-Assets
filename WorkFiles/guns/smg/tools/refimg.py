"""Image helpers for tracing the AR-01 reference sheet (numpy + scipy + Pillow only).

- find_panels: exact panel boxes on the white sheet by pixel analysis
- background model: robust 2D polynomial fit to the neutral grey studio backdrop
- soft foreground field and binary mask
- marching squares (sub-pixel iso-contours, consistently oriented) + Douglas-Peucker
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi


# ----------------------------------------------------------------------------------------------- panels
def _runs(flags):
    out, s = [], None
    for i, f in enumerate(flags):
        if f and s is None:
            s = i
        elif not f and s is not None:
            out.append((s, i - 1))
            s = None
    if s is not None:
        out.append((s, len(flags) - 1))
    return out


def find_panels(rgb, white=232, min_len=60):
    """Return panel boxes (x0, y0, x1, y1), inclusive pixel bounds, ordered by row then column.

    The sheet is white with grey photo panels; captions are dark text on white and never fill half a row/column.
    1) panel-row bands = runs of rows that are > 50 % non-white; 2) inside each band, panel columns = runs of columns
    that are > 50 % non-white; 3) each panel's own top/bottom = the run of rows (> 50 % non-white over that panel's
    columns) that overlaps the band centre."""
    g = rgb.astype(float).min(axis=2)
    H, W = g.shape
    nonwhite = g < white
    rows = [r for r in _runs(nonwhite.mean(axis=1) > 0.5) if r[1] - r[0] + 1 >= min_len]
    panels = []
    for (y0, y1) in rows:
        band = nonwhite[y0:y1 + 1]
        cols = [c for c in _runs(band.mean(axis=0) > 0.5) if c[1] - c[0] + 1 >= min_len]
        for (x0, x1) in cols:
            yc = (y0 + y1) // 2
            rr = _runs(nonwhite[:, x0:x1 + 1].mean(axis=1) > 0.5)
            yy0, yy1 = next((a, b) for a, b in rr if a <= yc <= b)
            panels.append((int(x0), int(yy0), int(x1), int(yy1)))
    return panels


# ----------------------------------------------------------------------------------------------- background
def fit_background(L, S, deg=4, exclude=None, iters=5):
    """Robust 2D polynomial fit of the neutral backdrop luminance. Returns (model image, residual sd)."""
    H, W = L.shape
    yy, xx = np.mgrid[0:H, 0:W]
    xn = xx / (W - 1) * 2 - 1
    yn = yy / (H - 1) * 2 - 1
    terms = [xn ** i * yn ** j for i in range(deg + 1) for j in range(deg + 1 - i)]
    A = np.stack([t.ravel() for t in terms], 1)
    ok = (S < 6) & (L > 90)
    if exclude is not None:
        ok &= ~exclude
    ok = ok.ravel()
    c, sd = None, 0.0
    for _ in range(iters):
        c, *_ = np.linalg.lstsq(A[ok], L.ravel()[ok], rcond=None)
        r = L.ravel() - A @ c
        sd = float(np.std(r[ok]))
        ok = ok & (np.abs(r) < max(2.5 * sd, 4.0))
    return (A @ c).reshape(H, W), sd


def soft_field(L, S, bg, dl=40.0, ds=24.0, db=24.0):
    """Foreground strength: 0.5 on the edge criterion (luminance drop dl below the backdrop, chroma ds, or a specular
    highlight db brighter than the backdrop), in [0, 1]. Steel is dark and neutral, wood is chromatic; the backdrop is
    neutral grey (chroma ~0-3, smooth to ~2 levels sd around the fitted model)."""
    f = np.maximum(np.maximum((bg - L) / dl, S / ds), (L - bg) / db) * 0.5
    return np.clip(f, 0.0, 1.0)


def drop_small(m, min_obj):
    lab, n = ndi.label(m)
    if not n:
        return m
    sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = np.zeros(n + 1, bool)
    keep[1:] = sizes >= min_obj
    return keep[lab]


def largest_component(m):
    lab, n = ndi.label(m)
    if n == 0:
        return m
    sizes = ndi.sum(m, lab, range(1, n + 1))
    return lab == (1 + int(np.argmax(sizes)))


def holes_of(m):
    """Label map of enclosed background regions (holes) of mask m."""
    filled = ndi.binary_fill_holes(m)
    lab, n = ndi.label(filled & ~m)
    return lab, n


# ----------------------------------------------------------------------------------------------- contours
def marching_squares(F, level=0.5):
    """Sub-pixel iso-contours of F at `level`. Returns closed rings as (N, 2) arrays of (x, y) pixel-centre coords.
    Outer boundaries have positive signed_area() (computed in x, -y), holes negative."""
    F = np.pad(F.astype(float), 1, constant_values=level - 1.0)
    H, W = F.shape
    B = F > level

    def interp(p, q):
        (y0, x0), (y1, x1) = p, q
        a, b = F[y0, x0], F[y1, x1]
        t = 0.5 if a == b else (level - a) / (b - a)
        return (x0 + t * (x1 - x0) - 1.0, y0 + t * (y1 - y0) - 1.0)

    nxt, pts = {}, {}
    table = {1: [('B', 'L')], 2: [('R', 'B')], 3: [('R', 'L')], 4: [('T', 'R')], 6: [('T', 'B')], 7: [('T', 'L')],
             8: [('L', 'T')], 9: [('B', 'T')], 11: [('R', 'T')], 12: [('L', 'R')], 13: [('B', 'R')], 14: [('L', 'B')]}
    for i in range(H - 1):
        code = B[i, :-1] * 8 + B[i, 1:] * 4 + B[i + 1, 1:] * 2 + B[i + 1, :-1] * 1
        for j in np.nonzero((code != 0) & (code != 15))[0]:
            c = int(code[j])
            E = {'T': ('h', i, j), 'R': ('v', i, j + 1), 'B': ('h', i + 1, j), 'L': ('v', i, j)}
            ept = {'T': ((i, j), (i, j + 1)), 'R': ((i, j + 1), (i + 1, j + 1)),
                   'B': ((i + 1, j), (i + 1, j + 1)), 'L': ((i, j), (i + 1, j))}
            if c in (5, 10):
                centre = F[i:i + 2, j:j + 2].mean() > level
                if c == 5:
                    segs = [('T', 'R'), ('B', 'L')] if not centre else [('T', 'L'), ('B', 'R')]
                else:
                    segs = [('L', 'T'), ('R', 'B')] if not centre else [('R', 'T'), ('L', 'B')]
            else:
                segs = table[c]
            for a, b in segs:
                nxt[E[a]] = E[b]
                for k in (a, b):
                    if E[k] not in pts:
                        pts[E[k]] = interp(*ept[k])
    polys, seen = [], set()
    for start in list(nxt.keys()):
        if start in seen:
            continue
        ring, e = [], start
        while e not in seen and e in nxt:
            seen.add(e)
            ring.append(pts[e])
            e = nxt[e]
        if len(ring) >= 3:
            polys.append(np.array(ring))
    return polys


def signed_area(P):
    x, y = P[:, 0], -P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def dp_simplify(P, tol):
    """Douglas-Peucker on a closed ring (iterative, no recursion limit issues)."""
    n = len(P)
    if n < 5:
        return P
    i1 = int(np.argmax(np.hypot(*(P - P[0]).T)))
    keep = np.zeros(n + 1, bool)
    Q = np.vstack([P, P[:1]])
    keep[[0, i1, n]] = True
    stack = [(0, i1), (i1, n)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        A, Bp = Q[a], Q[b]
        ab = Bp - A
        nn = np.hypot(*ab)
        seg = Q[a + 1:b]
        if nn == 0:
            d = np.hypot(*(seg - A).T)
        else:
            d = np.abs(ab[0] * (seg[:, 1] - A[1]) - ab[1] * (seg[:, 0] - A[0])) / nn
        k = int(np.argmax(d))
        if d[k] > tol:
            m = a + 1 + k
            keep[m] = True
            stack += [(a, m), (m, b)]
    return Q[:-1][keep[:-1]]


def poly_coverage(polys, shape, ss=4):
    """Fractional coverage in [0,1] of the union of polygons (pixel-centre coords), supersampled."""
    H, W = shape
    im = Image.new('L', (W * ss, H * ss), 0)
    d = ImageDraw.Draw(im)
    for P in polys:
        d.polygon([((x + 0.5) * ss, (y + 0.5) * ss) for x, y in P], fill=255)
    return np.asarray(im.resize((W, H), Image.BOX)).astype(float) / 255.0


def rings_to_mask(rings, shape, ss=4):
    """Rasterise outer rings minus hole rings (sign of area) to a boolean mask."""
    outer = [r for r in rings if signed_area(r) > 0]
    holes = [r for r in rings if signed_area(r) < 0]
    m = poly_coverage(outer, shape, ss) > 0.5
    if holes:
        m &= ~(poly_coverage(holes, shape, ss) > 0.5)
    return m


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 1.0


def fit_circle(x, y):
    A = np.c_[x, y, np.ones(len(x))]
    b = -(x * x + y * y)
    c = np.linalg.lstsq(A, b, rcond=None)[0]
    cx, cy = -c[0] / 2, -c[1] / 2
    r = float(np.sqrt(cx * cx + cy * cy - c[2]))
    res = np.hypot(x - cx, y - cy) - r
    return float(cx), float(cy), r, float(np.sqrt(np.mean(res ** 2)))


def fit_line(x, y):
    """Least-squares y = a*x + b; returns a, b, rms."""
    a, b = np.polyfit(x, y, 1)
    return float(a), float(b), float(np.sqrt(np.mean((y - (a * x + b)) ** 2)))


def crossings_along(F, x, y0, direction, level=0.5, maxlen=60):
    """Walk a column of F from row y0 (inside, F > level) in direction (+1 down, -1 up); return sub-pixel row of the
    first level crossing (pixel-centre coords), or None."""
    xi = int(round(x))
    y = int(round(y0))
    H = F.shape[0]
    if F[y, xi] <= level:
        return None
    for _ in range(maxlen):
        yn = y + direction
        if yn < 0 or yn >= H:
            return None
        if F[yn, xi] <= level:
            a, b = F[y, xi], F[yn, xi]
            t = (a - level) / (a - b)
            return y + direction * t
        y = yn
    return None


def crossings_row(F, y, x0, direction, level=0.5, maxlen=120):
    yi = int(round(y))
    x = int(round(x0))
    W = F.shape[1]
    if F[yi, x] <= level:
        return None
    for _ in range(maxlen):
        xn = x + direction
        if xn < 0 or xn >= W:
            return None
        if F[yi, xn] <= level:
            a, b = F[yi, x], F[yi, xn]
            t = (a - level) / (a - b)
            return x + direction * t
        x = xn
    return None
