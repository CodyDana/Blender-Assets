import numpy as np

def moore_trace(mask):
    """Moore-neighbour boundary tracing (8-connected), stop when the first move repeats.
    Returns Nx2 array of (x, y) pixel coords."""
    h, w = mask.shape
    m = np.zeros((h + 2, w + 2), bool); m[1:-1, 1:-1] = mask
    ys, xs = np.nonzero(m)
    i = np.lexsort((xs, ys))[0]
    start = (int(ys[i]), int(xs[i]))
    # neighbours clockwise (image coords, y down) starting from west: (dy, dx)
    nb = [(0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1)]
    cur = start; back = 0  # backtrack pixel is west of start (background, since start is top-left-most)
    contour = [cur]
    first_move = None
    while True:
        found = False
        for k in range(1, 9):
            d = (back + k) % 8
            ny, nx = cur[0] + nb[d][0], cur[1] + nb[d][1]
            if m[ny, nx]:
                prev = (back + k - 1) % 8
                py, px = cur[0] + nb[prev][0], cur[1] + nb[prev][1]
                nxt = (ny, nx)
                back = nb.index((py - ny, px - nx))
                found = True
                break
        if not found:
            break
        if first_move is None:
            first_move = (cur, nxt)
        elif (cur, nxt) == first_move:
            break
        cur = nxt
        contour.append(cur)
        if len(contour) > 40 * (h + w):
            raise RuntimeError("trace runaway")
    c = np.array(contour[:-1], float)
    return np.stack([c[:, 1] - 1, c[:, 0] - 1], 1)

def signed_area(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)

def smooth_closed(P, sig):
    r = int(3 * sig + 0.5)
    k = np.exp(-np.arange(-r, r + 1) ** 2 / (2 * sig ** 2)); k /= k.sum()
    out = np.zeros_like(P)
    for i, kv in zip(range(-r, r + 1), k):
        out += kv * np.roll(P, -i, 0)
    return out

def resample_closed(P, step=1.0):
    Q = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.arange(0, s[-1], step)
    return np.stack([np.interp(t, s, Q[:, 0]), np.interp(t, s, Q[:, 1])], 1)

def bilinear(img, x, y):
    h, w = img.shape[:2]
    x = np.clip(x, 0, w - 1.001); y = np.clip(y, 0, h - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    if img.ndim == 3:
        fx = fx[..., None]; fy = fy[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)

def dp_simplify(P, eps):
    """Douglas-Peucker on an open polyline; returns indices kept."""
    keep = np.zeros(len(P), bool); keep[0] = keep[-1] = True
    stack = [(0, len(P) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        A, B = P[a], P[b]
        d = B - A; L = np.hypot(*d)
        seg = P[a + 1:b] - A
        if L < 1e-9:
            dist = np.hypot(seg[:, 0], seg[:, 1])
        else:
            dist = np.abs(d[0] * seg[:, 1] - d[1] * seg[:, 0]) / L
        i = int(np.argmax(dist))
        if dist[i] > eps:
            k = a + 1 + i; keep[k] = True
            stack += [(a, k), (k, b)]
    return np.nonzero(keep)[0]

def dp_closed(P, eps):
    c = P.mean(0); i0 = int(np.argmax(np.linalg.norm(P - c, axis=1)))
    i1 = int(np.argmax(np.linalg.norm(P - P[i0], axis=1)))
    a, b = sorted([i0, i1])
    k1 = dp_simplify(P[a:b + 1], eps) + a
    Q = np.vstack([P[b:], P[:a + 1]])
    k2 = (dp_simplify(Q, eps) + b) % len(P)
    return np.unique(np.concatenate([k1, k2]))

def fit_line(P):
    """Total least squares line: centroid, unit direction, rms residual."""
    c = P.mean(0); U, S, Vt = np.linalg.svd(P - c)
    d = Vt[0]; nrm = Vt[1]
    r = (P - c) @ nrm
    return c, d, float(np.sqrt(np.mean(r ** 2)))

def fit_circle(P):
    """Algebraic (Kasa) circle fit refined with Gauss-Newton geometric iterations."""
    x, y = P[:, 0], P[:, 1]
    A = np.stack([x, y, np.ones_like(x)], 1); b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2; R = np.sqrt(sol[2] + cx ** 2 + cy ** 2)
    for _ in range(30):
        dx, dy = x - cx, y - cy; r = np.hypot(dx, dy)
        J = np.stack([-dx / r, -dy / r, -np.ones_like(r)], 1)
        res = r - R
        step, *_ = np.linalg.lstsq(J, -res, rcond=None)
        cx, cy, R = cx + step[0], cy + step[1], R + step[2]
        if np.abs(step).max() < 1e-7:
            break
    rr = np.hypot(x - cx, y - cy) - R
    return np.array([cx, cy]), float(R), float(np.sqrt(np.mean(rr ** 2)))

def poly_fill(P, h, w):
    """Even-odd rasterisation of closed polygon P (x,y) at pixel centres."""
    mask = np.zeros((h, w), bool)
    x0, y0 = P[:, 0], P[:, 1]; x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    for yy in range(h):
        cond = ((y0 <= yy) & (y1 > yy)) | ((y1 <= yy) & (y0 > yy))
        if not cond.any():
            continue
        xi = x0[cond] + (yy - y0[cond]) * (x1[cond] - x0[cond]) / (y1[cond] - y0[cond])
        xi = np.sort(xi)
        for a, b in zip(xi[::2], xi[1::2]):
            ia = int(np.ceil(a)); ib = int(np.floor(b))
            if ib >= ia:
                mask[yy, max(ia, 0):min(ib + 1, w)] = True
    return mask

def line_poly_intersections(P, origin, direction):
    """Signed parameters t where the line origin + t*direction crosses closed polygon P."""
    n = np.array([-direction[1], direction[0]])
    A = P; B = np.roll(P, -1, 0)
    da = (A - origin) @ n; db = (B - origin) @ n
    cross = (da * db < 0) | (da == 0)
    f = da[cross] / (da[cross] - db[cross])
    X = A[cross] + f[:, None] * (B[cross] - A[cross])
    return np.sort((X - origin) @ direction)
