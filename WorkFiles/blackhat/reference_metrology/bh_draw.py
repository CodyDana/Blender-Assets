"""Tiny raster drawing helpers (numpy) for labelled debug overlays."""
import numpy as np
def line(img, x0, y0, x1, y1, col, k=1, w=1):
    n = int(max(abs(x1 - x0), abs(y1 - y0)) * k * 2) + 2
    xs = np.linspace(x0, x1, n) * k; ys = np.linspace(y0, y1, n) * k
    H, W = img.shape[:2]
    for dx in range(-(w // 2), w // 2 + 1):
        for dy in range(-(w // 2), w // 2 + 1):
            xi = np.round(xs + dx).astype(int); yi = np.round(ys + dy).astype(int)
            ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
            img[yi[ok], xi[ok]] = col
def dot(img, x, y, col, k=1, r=3):
    H, W = img.shape[:2]; cx, cy = x * k, y * k
    yy, xx = np.mgrid[max(0, int(cy - r)):min(H, int(cy + r) + 1), max(0, int(cx - r)):min(W, int(cx + r) + 1)]
    m = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    img[yy[m], xx[m]] = col
def ring(img, x, y, col, k=1, r=6):
    t = np.linspace(0, 2 * np.pi, 80)
    for a, b in zip(t[:-1], t[1:]):
        line(img, (x + r / k * np.cos(a)), (y + r / k * np.sin(a)), (x + r / k * np.cos(b)), (y + r / k * np.sin(b)), col, k)
def polyline(img, pts, col, k=1, w=1):
    for a, b in zip(pts[:-1], pts[1:]): line(img, a[0], a[1], b[0], b[1], col, k, w)
