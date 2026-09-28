# Shared helpers for the roppo contour study (method B). Pure numpy + zlib PNG writer.
import numpy as np, zlib, struct
from collections import deque

def write_png(path, arr):
    """arr: HxW (gray) or HxWx3 uint8 or float 0..1, top-origin rows."""
    a = np.asarray(arr)
    if a.dtype != np.uint8:
        a = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    H, W, C = a.shape
    raw = b''.join(b'\x00' + a[y].tobytes() for y in range(H))
    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b'')
    open(path, 'wb').write(png)

def features(a):
    L = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    mx = a.max(-1); mn = a.min(-1)
    S = (mx - mn) / np.maximum(mx, 1e-6)
    return L, S

def otsu(v, bins=256, rng=(0, 1)):
    h, e = np.histogram(v.ravel(), bins=bins, range=rng)
    c = (e[:-1] + e[1:]) / 2
    w0 = np.cumsum(h); w1 = w0[-1] - w0
    m0 = np.cumsum(h * c) / np.maximum(w0, 1)
    m1 = ((h * c).sum() - np.cumsum(h * c)) / np.maximum(w1, 1)
    var = w0 * w1 * (m0 - m1) ** 2
    return float(c[np.argmax(var)])

def gauss_blur(img, sigma):
    r = int(3 * sigma + 0.5)
    x = np.arange(-r, r + 1)
    k = np.exp(-x ** 2 / (2 * sigma ** 2)); k /= k.sum()
    p = np.pad(img, r, mode='edge')
    t = sum(k[i] * p[:, i:i + img.shape[1]] for i in range(2 * r + 1))
    t = t[r:-r, :] if r else t
    p2 = np.pad(t, ((r, r), (0, 0)), mode='edge') if r else t
    out = sum(k[i] * p2[i:i + img.shape[0], :] for i in range(2 * r + 1))
    return out

def sobel(img):
    p = np.pad(img, 1, mode='edge')
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2])
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:])
    return gx / 8, gy / 8

def label(mask, conn=4):
    """Connected-component labelling (BFS). Returns labels (0 = not in mask), count, sizes list."""
    H, W = mask.shape
    lab = np.zeros((H, W), np.int32)
    m = mask.ravel(); lf = lab.ravel()
    if conn == 4:
        nb = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    else:
        nb = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    n = 0; sizes = [0]
    idx = np.flatnonzero(m)
    for s in idx:
        if lf[s]:
            continue
        n += 1; lf[s] = n; q = deque([s]); cnt = 0
        while q:
            p = q.popleft(); cnt += 1
            y, x = divmod(p, W)
            for dy, dx in nb:
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W:
                    pp = yy * W + xx
                    if m[pp] and not lf[pp]:
                        lf[pp] = n; q.append(pp)
        sizes.append(cnt)
    return lab, n, sizes

def dilate(m, r=1):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy * dy + dx * dx <= r * r:
                out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out

def erode(m, r=1):
    return ~dilate(~m, r)

def moore_trace(mask, start=None):
    """Moore-neighbour boundary trace of the 8-connected region containing start (a boundary pixel,
    topmost-leftmost by default). Returns Nx2 array of (x, y) pixel centres, clockwise in image coords."""
    H, W = mask.shape
    m = np.pad(mask, 1)
    if start is None:
        ys, xs = np.nonzero(m)
        i = np.lexsort((xs, ys))[0]
        start = (ys[i], xs[i])
    else:
        start = (start[0] + 1, start[1] + 1)
    # neighbours clockwise starting from west (image coords, y down)
    nb = [(0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1)]
    b = start
    c_dir = 0  # we came from west (pixel to the west is background for the topmost-leftmost)
    contour = [b]
    prev_dir = 0
    first_move = None
    while True:
        found = False
        for k in range(8):
            d = (prev_dir + k) % 8
            y, x = b[0] + nb[d][0], b[1] + nb[d][1]
            if m[y, x]:
                found = True
                break
        if not found:
            break
        nbp = (y, x)
        # backtrack direction: start search from the neighbour after the one pointing back to b, rotated
        prev_dir = (d + 5) % 8  # (d+4) points back; start one step clockwise past background
        if first_move is None:
            first_move = (b, nbp)
        elif (b, nbp) == first_move:
            break
        b = nbp
        contour.append(b)
        if len(contour) > 4 * H * W:
            break
    c = np.array(contour[:-1] if len(contour) > 1 and contour[-1] == contour[0] else contour)
    return np.stack([c[:, 1] - 1, c[:, 0] - 1], 1).astype(float)

def douglas_peucker(pts, eps, closed=True):
    pts = np.asarray(pts, float)
    if closed:
        # split at the two farthest points
        d = np.linalg.norm(pts - pts[0], axis=1); i = int(np.argmax(d))
        a = _dp(pts[:i + 1], eps); b = _dp(np.vstack([pts[i:], pts[:1]]), eps)
        idx = list(a) + [i + j for j in b[1:-1]]
        return np.array(idx)
    return _dp(pts, eps)

def _dp(pts, eps):
    n = len(pts)
    keep = np.zeros(n, bool); keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        s, e = stack.pop()
        if e <= s + 1:
            continue
        p0, p1 = pts[s], pts[e]
        v = p1 - p0; L = np.hypot(*v)
        seg = pts[s + 1:e]
        if L < 1e-9:
            d = np.linalg.norm(seg - p0, axis=1)
        else:
            d = np.abs(v[0] * (seg[:, 1] - p0[1]) - v[1] * (seg[:, 0] - p0[0])) / L
        k = int(np.argmax(d))
        if d[k] > eps:
            m = s + 1 + k; keep[m] = True
            stack += [(s, m), (m, e)]
    return np.flatnonzero(keep)

def fit_line(pts):
    """Total least squares line. Returns centroid, unit direction, rms residual, max residual."""
    p = np.asarray(pts, float); c = p.mean(0)
    u, s, vt = np.linalg.svd(p - c, full_matrices=False)
    d = vt[0]; nrm = vt[1]
    r = (p - c) @ nrm
    return c, d, float(np.sqrt((r ** 2).mean())), float(np.abs(r).max())

def fit_circle(pts):
    """Algebraic (Kasa) circle fit followed by a few Gauss-Newton (geometric) iterations."""
    p = np.asarray(pts, float)
    x, y = p[:, 0], p[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0], sol[1]; r = np.sqrt(sol[2] + cx ** 2 + cy ** 2)
    alg = (cx, cy, r)
    for _ in range(50):
        dx, dy = x - cx, y - cy; d = np.hypot(dx, dy)
        J = np.c_[-dx / d, -dy / d, -np.ones(len(x))]
        res = d - r
        step, *_ = np.linalg.lstsq(J, -res, rcond=None)
        cx, cy, r = cx + step[0], cy + step[1], r + step[2]
        if np.abs(step).max() < 1e-7:
            break
    res = np.hypot(x - cx, y - cy) - r
    return dict(cx=float(cx), cy=float(cy), r=float(r), rms=float(np.sqrt((res ** 2).mean())),
                maxres=float(np.abs(res).max()), alg=[float(v) for v in alg])

def line_intersect(c1, d1, c2, d2):
    A = np.array([d1, -d2]).T
    t = np.linalg.solve(A, c2 - c1)
    return c1 + t[0] * d1
