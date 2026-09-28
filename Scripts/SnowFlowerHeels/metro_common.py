"""Shared numpy helpers for reference metrology (no scipy)."""
import numpy as np, collections
def shift(m, dy, dx, fill=False):
    o = np.full_like(m, fill); H, W = m.shape[:2]
    ys, yd = (slice(0, H-dy), slice(dy, H)) if dy >= 0 else (slice(-dy, H), slice(0, H+dy))
    xs, xd = (slice(0, W-dx), slice(dx, W)) if dx >= 0 else (slice(-dx, W), slice(0, W+dx))
    o[yd, xd] = m[ys, xs]; return o
def dilate(m, r=1):
    o = m.copy()
    for dy in range(-r, r+1):
        for dx in range(-r, r+1):
            if dy*dy+dx*dx <= r*r: o |= shift(m, dy, dx)
    return o
def erode(m, r=1): return ~dilate(~m, r)
def boxmean(a, r):
    k = 2*r+1; p = np.pad(a, r, mode='edge').astype(np.float64)
    c = p.cumsum(0).cumsum(1); c = np.pad(c, ((1,0),(1,0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k*k)
def label(m):
    H, W = m.shape; lab = np.zeros((H, W), np.int32); n = 0; sizes = [0]
    for y0, x0 in zip(*np.nonzero(m)):
        if lab[y0, x0]: continue
        n += 1; q = collections.deque([(y0, x0)]); lab[y0, x0] = n; c = 0
        while q:
            y, x = q.popleft(); c += 1
            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                yy, xx = y+dy, x+dx
                if 0 <= yy < H and 0 <= xx < W and m[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n; q.append((yy, xx))
        sizes.append(c)
    return lab, np.array(sizes)
def fill_holes(m):
    lab, s = label(~m); border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    return ~np.isin(lab, list(border))
def trace_boundary(m):
    """Moore-neighbour trace of the outer boundary of the single blob in m; returns Nx2 (x,y)."""
    ys, xs = np.nonzero(m); i = np.lexsort((xs, ys))[0]; start = (ys[i], xs[i])
    nb = [(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1)]
    pts = [start]; cur = start; d = 6
    H, W = m.shape
    for _ in range(200000):
        for k in range(8):
            dd = (d + k) % 8; y, x = cur[0]+nb[dd][0], cur[1]+nb[dd][1]
            if 0 <= y < H and 0 <= x < W and m[y, x]:
                cur = (y, x); d = (dd + 6) % 8; break
        if cur == start: break
        pts.append(cur)
    p = np.array(pts)[:, ::-1].astype(float); return p
def rdp(p, eps):
    if len(p) < 3: return p
    a, b = p[0], p[-1]; ab = b - a; L = np.hypot(*ab)
    d = np.abs(np.cross(ab, p - a)) / L if L > 0 else np.hypot(*(p - a).T)
    i = int(np.argmax(d))
    if d[i] > eps: return np.vstack([rdp(p[:i+1], eps)[:-1], rdp(p[i:], eps)])
    return np.vstack([a, b])
def draw_poly(img, pts, col, closed=False, w=1):
    pts = np.asarray(pts, float); H, W = img.shape[:2]
    segs = list(zip(pts[:-1], pts[1:])) + ([(pts[-1], pts[0])] if closed else [])
    for p, q in segs:
        n = int(max(abs(q-p)) * 2) + 1
        for t in np.linspace(0, 1, n):
            x, y = p + (q-p)*t
            for oy in range(-(w//2), w//2+1):
                for ox in range(-(w//2), w//2+1):
                    yy, xx = int(round(y))+oy, int(round(x))+ox
                    if 0 <= yy < H and 0 <= xx < W: img[yy, xx] = col
