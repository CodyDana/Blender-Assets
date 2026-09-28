import numpy as np, zlib, struct
ROOT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/"

def load():
    return np.load(ROOT + "juji_rgb.npy")

def write_png(path, arr):
    """arr: HxW (gray) or HxWx3 float [0,1] or uint8, top-origin."""
    a = np.asarray(arr)
    if a.dtype != np.uint8:
        a = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    if a.ndim == 2:
        a = np.stack([a]*3, -1)
    h, w, _ = a.shape
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)

def hsv(rgb):
    mx = rgb.max(-1); mn = rgb.min(-1)
    s = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
    return mx, s

def otsu(vals, nbins=256):
    vals = vals.ravel()
    lo, hi = vals.min(), vals.max()
    hist, edges = np.histogram(vals, bins=nbins, range=(lo, hi))
    p = hist.astype(float) / hist.sum()
    omega = np.cumsum(p); mu = np.cumsum(p * (edges[:-1] + edges[1:]) / 2)
    mt = mu[-1]
    sb = (mt * omega - mu) ** 2 / np.maximum(omega * (1 - omega), 1e-12)
    k = np.nanargmax(sb)
    return (edges[k] + edges[k+1]) / 2

def shift(m, dy, dx, fill=False):
    out = np.full_like(m, fill)
    h, w = m.shape
    ys = slice(max(dy, 0), h + min(dy, 0)); yd = slice(max(-dy, 0), h + min(-dy, 0))
    xs = slice(max(dx, 0), w + min(dx, 0)); xd = slice(max(-dx, 0), w + min(-dx, 0))
    out[ys, xs] = m[yd, xd]
    return out

def disk_offsets(r):
    return [(dy, dx) for dy in range(-r, r+1) for dx in range(-r, r+1) if dy*dy + dx*dx <= r*r]

def dilate(m, r):
    out = m.copy()
    for dy, dx in disk_offsets(r):
        out |= shift(m, dy, dx, False)
    return out

def erode(m, r):
    out = m.copy()
    for dy, dx in disk_offsets(r):
        out &= shift(m, dy, dx, True)
    return out

def label(m):
    """4-connected labelling, iterative union-find via numpy scanning (simple BFS in python for moderate sizes)."""
    h, w = m.shape
    lab = np.zeros((h, w), np.int32)
    cur = 0
    ys, xs = np.nonzero(m)
    from collections import deque
    for y0, x0 in zip(ys, xs):
        if lab[y0, x0]:
            continue
        cur += 1
        lab[y0, x0] = cur
        dq = deque([(y0, x0)])
        while dq:
            y, x = dq.popleft()
            for ny, nx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = cur
                    dq.append((ny, nx))
    return lab, cur
