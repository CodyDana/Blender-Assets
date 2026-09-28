"""Trace pilot v2 - small shared helpers (numpy only)."""
import numpy as np
import tp_geom2d as G


def bilinear(F, px, py):
    """sample a full-image field F at ref px coords (pixel centres at +0.5)."""
    x = px - 0.5; y = py - 0.5
    x0 = np.clip(np.floor(x).astype(int), 0, F.shape[1] - 2); y0 = np.clip(np.floor(y).astype(int), 0, F.shape[0] - 2)
    fx = np.clip(x - x0, 0, 1); fy = np.clip(y - y0, 0, 1)
    return (F[y0, x0] * (1 - fx) * (1 - fy) + F[y0, x0 + 1] * fx * (1 - fy) + F[y0 + 1, x0] * (1 - fx) * fy
            + F[y0 + 1, x0 + 1] * fx * fy)


def petal_poly(cx, cy, phi, d0, d1, w, q, e, n=160):
    s = np.linspace(0, 1, n)
    hw = w / 2 * (2 * np.sqrt(np.clip(s * (1 - s), 0, None))) ** q * (1 + e * (s - 0.5))
    u = d0 + s * (d1 - d0)
    Q = np.vstack([np.c_[u, hw], np.c_[u[::-1], -hw[::-1]][1:-1]])
    cu, su = np.cos(phi), np.sin(phi)
    return np.c_[cx + Q[:, 0] * cu - Q[:, 1] * su, cy + Q[:, 0] * su + Q[:, 1] * cu]


def sdist_grid(poly, X, Y):
    """signed distance (+ inside) from grid points X, Y (ref px) to a closed polygon."""
    P = G.resample_closed(np.asarray(poly, float), 0.25)
    x = X.ravel(); y = Y.ravel()
    a = P; b = np.roll(P, -1, 0)
    d = np.full(x.shape, 1e9)
    for k in range(0, len(a), 96):
        A = a[k:k + 96]; B = b[k:k + 96]; AB = B - A
        apx = x[:, None] - A[None, :, 0]; apy = y[:, None] - A[None, :, 1]
        t = np.clip((apx * AB[None, :, 0] + apy * AB[None, :, 1]) / ((AB ** 2).sum(1)[None] + 1e-12), 0, 1)
        dx = apx - t * AB[None, :, 0]; dy = apy - t * AB[None, :, 1]
        d = np.minimum(d, np.sqrt(dx * dx + dy * dy).min(1))
    ins = G.pip(x, y, P)
    return np.where(ins, d, -d).reshape(X.shape)
