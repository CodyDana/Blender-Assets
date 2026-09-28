# Method B helpers: Otsu, flood fill, Moore neighbour tracing, Douglas-Peucker,
# least-squares line fit, algebraic (Kasa) + geometric circle fit.  numpy only.
import numpy as np
from collections import deque

def otsu(values, bins=256, rng=None):
    v = np.asarray(values, float).ravel()
    if rng is None: rng = (v.min(), v.max())
    h, e = np.histogram(v, bins=bins, range=rng)
    c = 0.5 * (e[:-1] + e[1:])
    w0 = np.cumsum(h); w1 = w0[-1] - w0
    m0 = np.cumsum(h * c); mt = m0[-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        mu0 = m0 / w0; mu1 = (mt - m0) / w1
        sb = w0 * w1 * (mu0 - mu1) ** 2
    sb = np.nan_to_num(sb)
    k = int(np.argmax(sb))
    return float(e[k + 1])

def flood(mask, seeds):
    """4-connected flood fill of True pixels in mask starting from seeds (list of (y,x))."""
    H, W = mask.shape
    out = np.zeros_like(mask, bool)
    q = deque()
    for (y, x) in seeds:
        if mask[y, x] and not out[y, x]:
            out[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W and mask[yy, xx] and not out[yy, xx]:
                out[yy, xx] = True; q.append((yy, xx))
    return out

def label(mask):
    H, W = mask.shape
    lab = np.zeros(mask.shape, np.int32); n = 0
    ys, xs = np.nonzero(mask)
    for y, x in zip(ys, xs):
        if lab[y, x]: continue
        n += 1; lab[y, x] = n; q = deque([(y, x)])
        while q:
            cy, cx = q.popleft()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = cy + dy, cx + dx
                if 0 <= yy < H and 0 <= xx < W and mask[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n; q.append((yy, xx))
    return lab, n

def binary_open(m, r):
    return dilate(erode(m, r), r)
def binary_close(m, r):
    return erode(dilate(m, r), r)
def dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy * dy + dx * dx > r * r: continue
            out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out
def erode(m, r):
    return ~dilate(~m, r)

# Moore neighbour tracing (clockwise in image coords, y down), Jacob's stopping criterion.
_NB = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]  # N,NE,E,SE,S,SW,W,NW
def moore_trace(mask):
    H, W = mask.shape
    m = np.zeros((H + 2, W + 2), bool); m[1:-1, 1:-1] = mask
    ys, xs = np.nonzero(m)
    i = np.lexsort((xs, ys))[0]           # top-most, then left-most pixel
    start = (ys[i], xs[i])
    back = (start[0], start[1] - 1)        # came from the west (background)
    contour = [start]
    cur = start
    b = back
    start_back = back
    for _ in range(10 * (H + W) * 4):
        # index of backtrack pixel relative to cur
        d = (b[0] - cur[0], b[1] - cur[1])
        k = _NB.index(d)
        found = False
        for j in range(1, 9):
            kk = (k + j) % 8
            ny, nx = cur[0] + _NB[kk][0], cur[1] + _NB[kk][1]
            if m[ny, nx]:
                pk = (k + j - 1) % 8
                b = (cur[0] + _NB[pk][0], cur[1] + _NB[pk][1])
                cur = (ny, nx); found = True
                break
        if not found:
            break
        if cur == start and b == start_back:
            break
        contour.append(cur)
    c = np.array(contour, float) - 1.0     # back to image coords (y, x)
    if len(c) > 1 and (c[-1] == c[0]).all():
        c = c[:-1]
    return c[:, ::-1]                      # return (x, y)

def douglas_peucker(pts, eps):
    pts = np.asarray(pts, float)
    n = len(pts)
    keep = np.zeros(n, bool); keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1: continue
        a, b = pts[i], pts[j]
        ab = b - a; L = np.hypot(*ab)
        seg = pts[i + 1:j] - a
        if L == 0:
            d = np.hypot(seg[:, 0], seg[:, 1])
        else:
            d = np.abs(ab[0] * seg[:, 1] - ab[1] * seg[:, 0]) / L
        k = int(np.argmax(d))
        if d[k] > eps:
            keep[i + 1 + k] = True
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return pts[keep], np.nonzero(keep)[0]

def fit_line(pts):
    """Total least squares line. Returns (point, unit direction, rms, max_abs)."""
    p = np.asarray(pts, float); c = p.mean(0)
    u, s, vt = np.linalg.svd(p - c)
    d = vt[0]; nrm = np.array([-d[1], d[0]])
    r = (p - c) @ nrm
    return c, d, float(np.sqrt((r ** 2).mean())), float(np.abs(r).max())

def fit_circle(pts, refine=True):
    """Kasa algebraic fit then Gauss-Newton geometric refinement. Returns (cx, cy, R, rms, residuals)."""
    p = np.asarray(pts, float); x, y = p[:, 0], p[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones_like(x)]
    b = x * x + y * y
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0], sol[1]; R = np.sqrt(sol[2] + cx * cx + cy * cy)
    if refine:
        for _ in range(50):
            dx, dy = x - cx, y - cy; di = np.hypot(dx, dy)
            r = di - R
            J = np.c_[-dx / di, -dy / di, -np.ones_like(di)]
            step, *_ = np.linalg.lstsq(J, -r, rcond=None)
            cx += step[0]; cy += step[1]; R += step[2]
            if np.abs(step).max() < 1e-9: break
    res = np.hypot(x - cx, y - cy) - R
    return float(cx), float(cy), float(R), float(np.sqrt((res ** 2).mean())), res

def line_intersect(p1, d1, p2, d2):
    A = np.array([d1, -d2]).T
    t = np.linalg.solve(A, p2 - p1)
    return p1 + t[0] * d1

def circle_circle(c1, r1, c2, r2):
    c1 = np.asarray(c1, float); c2 = np.asarray(c2, float)
    d = np.hypot(*(c2 - c1))
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = np.sqrt(max(r1 * r1 - a * a, 0.0))
    m = c1 + a * (c2 - c1) / d
    perp = np.array([-(c2 - c1)[1], (c2 - c1)[0]]) / d
    return m + h * perp, m - h * perp

def bilinear(img, x, y):
    H, W = img.shape
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)
