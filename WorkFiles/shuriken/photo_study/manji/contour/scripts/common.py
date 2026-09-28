import numpy as np, zlib, struct, os
BASE = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour"

def write_png(path, arr):
    """arr: HxW (gray) or HxWx3 uint8 or float 0..1, top-origin rows."""
    a = np.asarray(arr)
    if a.dtype != np.uint8:
        a = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    if a.ndim == 2:
        ctype, ch = 0, 1
        a = a[:, :, None]
    else:
        ch = a.shape[2]; ctype = {3: 2, 4: 6}[ch]
    h, w = a.shape[:2]
    raw = np.concatenate([np.zeros((h, 1), np.uint8), a.reshape(h, w * ch)], axis=1).tobytes()
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)

def label_runs(mask, conn8=True):
    """Connected components via row runs + union-find. Returns label image (0=bg) and count."""
    h, w = mask.shape
    parent = []
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    runs_prev = []
    all_runs = []  # (row, start, end_excl, id)
    for y in range(h):
        row = mask[y].astype(np.int8)
        d = np.diff(np.concatenate([[0], row, [0]]))
        starts = np.nonzero(d == 1)[0]; ends = np.nonzero(d == -1)[0]
        runs_cur = []
        j = 0
        for s, e in zip(starts.tolist(), ends.tolist()):
            rid = len(parent); parent.append(rid)
            lo, hi = (s - 1, e + 1) if conn8 else (s, e)
            # advance j over prev runs
            while j < len(runs_prev) and runs_prev[j][1] <= lo:
                j += 1
            k = j
            while k < len(runs_prev) and runs_prev[k][0] < hi:
                a, b = find(rid), find(runs_prev[k][2])
                if a != b:
                    parent[max(a, b)] = min(a, b)
                k += 1
            runs_cur.append((s, e, rid))
            all_runs.append((y, s, e, rid))
        runs_prev = runs_cur
    lab = np.zeros((h, w), np.int32)
    roots = {}
    for (y, s, e, rid) in all_runs:
        r = find(rid)
        if r not in roots:
            roots[r] = len(roots) + 1
        lab[y, s:e] = roots[r]
    return lab, len(roots)

def otsu(values, nbins=512):
    v = values.ravel()
    hist, edges = np.histogram(v, bins=nbins)
    p = hist.astype(np.float64) / hist.sum()
    centers = 0.5 * (edges[:-1] + edges[1:])
    w0 = np.cumsum(p); w1 = 1 - w0
    m0 = np.cumsum(p * centers); mt = m0[-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        sb = (mt * w0 - m0) ** 2 / (w0 * w1)
    sb[~np.isfinite(sb)] = 0
    return centers[np.argmax(sb)]

def gauss_blur(a, sigma):
    r = max(1, int(3 * sigma + 0.5))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    p = np.pad(a, ((r, r), (r, r)), mode="edge")
    t = np.zeros((p.shape[0], a.shape[1]), np.float32)
    for i, kv in enumerate(k):
        t += kv * p[:, i:i + a.shape[1]]
    o = np.zeros(a.shape, np.float32)
    for i, kv in enumerate(k):
        o += kv * t[i:i + a.shape[0], :]
    return o

def box_mean(a, r):
    p = np.pad(a, ((r + 1, r), (r + 1, r)), mode="edge").astype(np.float64)
    c = p.cumsum(0).cumsum(1)
    n = 2 * r + 1
    s = c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]
    return (s / (n * n)).astype(np.float32)

# Moore-neighbour contour tracing (8-connectivity), clockwise in image coords (x right, y down)
_NB = [(-1, 0), (-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1)]  # (dx,dy) W, NW, N, NE, E, SE, S, SW
def moore_trace(mask, start=None):
    h, w = mask.shape
    m = np.zeros((h + 2, w + 2), bool); m[1:-1, 1:-1] = mask
    if start is None:
        ys, xs = np.nonzero(m)
        i = np.lexsort((xs, ys))[0]   # topmost, then leftmost
        sy, sx = int(ys[i]), int(xs[i])
    else:
        sx, sy = start[0] + 1, start[1] + 1
    # backtrack pixel is the west neighbour (outside, since start is leftmost of top row)
    cx, cy = sx, sy
    bdir = 0  # index into _NB of the backtrack position relative to current
    contour = [(cx, cy)]
    first_move = None
    for _ in range(10 * (h + w) * 10):
        found = False
        for k in range(1, 9):
            d = (bdir + k) % 8
            nx, ny = cx + _NB[d][0], cy + _NB[d][1]
            if m[ny, nx]:
                # new backtrack: the neighbour checked just before d, expressed relative to the new pixel
                pd = (bdir + k - 1) % 8
                px_, py_ = cx + _NB[pd][0], cy + _NB[pd][1]
                cx, cy = nx, ny
                dx, dy = px_ - cx, py_ - cy
                bdir = _NB.index((dx, dy))
                found = True
                break
        if not found:
            break
        if first_move is None:
            first_move = (cx, cy)
        elif (cx, cy) == first_move and contour[-1] == (sx, sy):
            contour.pop()
            break
        contour.append((cx, cy))
    return np.array(contour, np.float64) - 1.0

def douglas_peucker(pts, eps, closed=True):
    pts = np.asarray(pts, np.float64)
    if closed:
        # split at the two mutually farthest points (approximate)
        d0 = np.hypot(*(pts - pts[0]).T); i1 = int(np.argmax(d0))
        d1 = np.hypot(*(pts - pts[i1]).T); i2 = int(np.argmax(d1))
        a, b = sorted((i1, i2))
        k1 = _dp_open(pts[a:b + 1], eps)
        k2 = _dp_open(np.concatenate([pts[b:], pts[:a + 1]]), eps)
        idx = [a + i for i in k1] + [(b + i) % len(pts) for i in k2[1:-1]]
        return sorted(set(idx))
    return _dp_open(pts, eps)

def _dp_open(pts, eps):
    n = len(pts); keep = np.zeros(n, bool); keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1: continue
        p, q = pts[i], pts[j]; seg = pts[i + 1:j]
        v = q - p; L = np.hypot(*v)
        if L < 1e-9:
            d = np.hypot(*(seg - p).T)
        else:
            d = np.abs(v[0] * (seg[:, 1] - p[1]) - v[1] * (seg[:, 0] - p[0])) / L
        k = int(np.argmax(d))
        if d[k] > eps:
            keep[i + 1 + k] = True
            stack.append((i, i + 1 + k)); stack.append((i + 1 + k, j))
    return np.nonzero(keep)[0].tolist()

def bilinear(img, x, y):
    h, w = img.shape[:2]
    x = np.clip(x, 0, w - 1.001); y = np.clip(y, 0, h - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    if img.ndim == 3:
        fx = fx[..., None]; fy = fy[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)

def fill_polygon(poly, h, w):
    """even-odd scanline fill of a closed polygon (N,2) at pixel centres."""
    m = np.zeros((h, w), bool)
    x = poly[:, 0]; y = poly[:, 1]
    x2 = np.roll(x, -1); y2 = np.roll(y, -1)
    for row in range(h):
        yc = row
        c = ((y <= yc) & (y2 > yc)) | ((y2 <= yc) & (y > yc))
        if not c.any(): continue
        xi = x[c] + (yc - y[c]) * (x2[c] - x[c]) / (y2[c] - y[c])
        xi.sort()
        for a, b in zip(xi[0::2], xi[1::2]):
            lo = int(np.ceil(a)); hi = int(np.floor(b))
            if hi >= lo: m[row, max(lo, 0):min(hi + 1, w)] = True
    return m
