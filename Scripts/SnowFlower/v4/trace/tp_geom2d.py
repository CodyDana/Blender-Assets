"""2D helpers (numpy only): point-in-polygon, polygon raster, flood fill, distance transform, marching squares,
contour simplify/smooth.  Coordinates: (col, row) = (x, y) in reference pixels, pixel centres at integer+0.5? No:
pixel (r, c) centre = (c + 0.5, r + 0.5) in 'ref px' continuous coords, matching the spec's integer rows ~ centres."""
import numpy as np

def pip(px, py, poly):
    """vectorised crossing-number point-in-polygon. px, py arrays; poly (N,2)."""
    poly = np.asarray(poly, float)
    x0, y0 = poly[:, 0], poly[:, 1]
    x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    inside = np.zeros(np.shape(px), bool)
    for a, b, c, d in zip(x0, y0, x1, y1):
        cond = ((b > py) != (d > py))
        with np.errstate(divide='ignore', invalid='ignore'):
            xi = a + (py - b) * (c - a) / (d - b)
        inside ^= cond & (px < xi)
    return inside

def grid(r0, r1, c0, c1, s=1):
    """pixel-centre coords of a (r1-r0)*s x (c1-c0)*s grid in ref px (col, row)."""
    ys = r0 + (np.arange((r1 - r0) * s) + 0.5) / s
    xs = c0 + (np.arange((c1 - c0) * s) + 0.5) / s
    return np.meshgrid(xs, ys)

def dilate(m, r=1):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r: continue
            out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out

def erode(m, r=1):
    return ~dilate(~m, r)

def flood(seed, allowed):
    cur = seed & allowed
    while True:
        nxt = dilate(cur, 1) & allowed
        if nxt.sum() == cur.sum(): return nxt
        cur = nxt

def label(m):
    """4-connected components (simple union by BFS; fine for small images)."""
    H, W = m.shape
    lab = np.zeros((H, W), int); n = 0
    for y in range(H):
        for x in range(W):
            if m[y, x] and lab[y, x] == 0:
                n += 1; st = [(y, x)]; lab[y, x] = n
                while st:
                    a, b = st.pop()
                    for c, d in ((a+1, b), (a-1, b), (a, b+1), (a, b-1)):
                        if 0 <= c < H and 0 <= d < W and m[c, d] and lab[c, d] == 0:
                            lab[c, d] = n; st.append((c, d))
    return lab, n

def edt(mask):
    """Euclidean distance (px) from each True pixel to the nearest False pixel (brute-force-ish via two-pass
    separable exact EDT, Felzenszwalb)."""
    INF = 1e12
    f = np.where(mask, INF, 0.0)
    def dt1(f):
        n = len(f); d = np.zeros(n); v = np.zeros(n, int); z = np.zeros(n + 1)
        k = 0; v[0] = 0; z[0] = -INF; z[1] = INF
        for q in range(1, n):
            s = ((f[q] + q*q) - (f[v[k]] + v[k]*v[k])) / (2*q - 2*v[k])
            while s <= z[k]:
                k -= 1
                s = ((f[q] + q*q) - (f[v[k]] + v[k]*v[k])) / (2*q - 2*v[k])
            k += 1; v[k] = q; z[k] = s; z[k+1] = INF
        k = 0
        for q in range(n):
            while z[k+1] < q: k += 1
            d[q] = (q - v[k])**2 + f[v[k]]
        return d
    g = np.array([dt1(col) for col in f.T]).T
    h = np.array([dt1(row) for row in g])
    return np.sqrt(h)

def marching_squares(f, iso):
    """Closed/open iso-contours of field f at level iso, as lists of (x, y) arrays in field index coords
    (x = column index, y = row index, at sample positions).  Field is padded so all contours close."""
    F = np.pad(f, 1, constant_values=min(f.min(), iso) - 1.0)
    H, W = F.shape
    segs = {}
    def interp(p, q, fp, fq):
        t = (iso - fp) / (fq - fp)
        return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))
    edges = []
    for y in range(H - 1):
        for x in range(W - 1):
            v = [F[y, x], F[y, x+1], F[y+1, x+1], F[y+1, x]]
            idx = sum((1 << i) for i in range(4) if v[i] > iso)
            if idx == 0 or idx == 15: continue
            P = [(x, y), (x+1, y), (x+1, y+1), (x, y+1)]
            E = {}
            for e, (i, j) in enumerate(((0, 1), (1, 2), (2, 3), (3, 0))):
                if (v[i] > iso) != (v[j] > iso):
                    E[e] = interp(P[i], P[j], v[i], v[j])
            ks = list(E.keys())
            if len(ks) == 2:
                edges.append((E[ks[0]], E[ks[1]]))
            else:
                c = sum(v) / 4 > iso
                if (idx == 5) == c:
                    edges.append((E[0], E[1])); edges.append((E[2], E[3]))
                else:
                    edges.append((E[0], E[3])); edges.append((E[1], E[2]))
    # chain
    from collections import defaultdict
    key = lambda p: (round(p[0], 6), round(p[1], 6))
    adj = defaultdict(list)
    for a, b in edges:
        adj[key(a)].append(key(b)); adj[key(b)].append(key(a))
    seen = set(); loops = []
    for s in list(adj.keys()):
        if s in seen: continue
        loop = [s]; seen.add(s); prev = None; cur = s
        while True:
            nb = [n for n in adj[cur] if n != prev and n not in seen]
            if not nb:
                break
            prev, cur = cur, nb[0]; seen.add(cur); loop.append(cur)
        arr = np.array(loop, float) - 1.0
        if len(arr) >= 4: loops.append(arr)
    return loops

def signed_area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)

def resample_closed(p, step):
    q = np.vstack([p, p[:1]])
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))]
    n = max(int(d[-1] / step), 8)
    t = np.linspace(0, d[-1], n, endpoint=False)
    return np.c_[np.interp(t, d, q[:, 0]), np.interp(t, d, q[:, 1])]

def smooth_closed(p, it=2, lam=0.5):
    for _ in range(it):
        p = p + lam * (0.5 * (np.roll(p, 1, 0) + np.roll(p, -1, 0)) - p)
    return p

def gauss(a, s):
    if s <= 0: return a
    r = int(3 * s + 1); x = np.arange(-r, r + 1); k = np.exp(-x*x / (2*s*s)); k /= k.sum()
    b = np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode='edge'), k, 'valid'), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode='edge'), k, 'valid'), 1, b)
