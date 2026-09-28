"""Camera + hat silhouette model shared by the fits.
World: hat axis +Z, rim tube centre circle radius 1 at z=0, apex (0,0,H). Camera looks at the rim centre (0,0,0)
from azimuth -Y (camera sits at -Y), elevation e above the rim plane, distance d. Image: u right, v down, px.
"""
import numpy as np

def cam_basis(e, roll):
    F = np.array([0.0, np.cos(e), -np.sin(e)])
    Rv = np.array([1.0, 0.0, 0.0])
    U = np.array([0.0, np.sin(e), np.cos(e)])
    c, s = np.cos(roll), np.sin(roll)
    # roll: positive = image content rotates clockwise (right side goes down)
    Rr = c * Rv - s * U; Ur = s * Rv + c * U
    return F, Rr, Ur

def project(P, e, d, f, u0, v0, roll):
    """P: (...,3) world -> (...,2) px. f in px. d=inf -> orthographic with scale f (px per unit)."""
    F, Rv, U = cam_basis(e, roll)
    if np.isinf(d):
        x = P @ Rv; y = P @ U
        return np.stack([u0 + f * x, v0 - f * y], -1)
    C = -d * F
    Q = P - C
    x = Q @ Rv; y = Q @ U; z = Q @ F
    return np.stack([u0 + f * x / z, v0 - f * y / z], -1)

def hull(pts):
    """monotone chain; returns (lower_in_image_sense, upper) as arrays sorted by x.
    'upper' = min v (top outline), 'lower' = max v (bottom outline)."""
    p = pts[np.lexsort((pts[:, 1], pts[:, 0]))]
    def half(seq):
        out = []
        for q in seq:
            while len(out) >= 2:
                o, a = out[-2], out[-1]
                cr = (a[0] - o[0]) * (q[1] - o[1]) - (a[1] - o[1]) * (q[0] - o[0])
                if cr <= 0: out.pop()
                else: break
            out.append(q)
        return np.array(out)
    h1 = half(p)            # cross>0 kept: with v down this is the bottom (max v) chain
    h2 = half(p[::-1])[::-1]
    # decide which is top (smaller v on average)
    if h1[:, 1].mean() < h2[:, 1].mean():
        return h2, h1
    return h1, h2

def tube_points(rt, H, nth=720, nps=16, zc=0.0, extra=None):
    th = np.linspace(0, 2 * np.pi, nth, endpoint=False)
    ps = np.linspace(0, 2 * np.pi, nps, endpoint=False)
    T, S = np.meshgrid(th, ps)
    r = 1 + rt * np.cos(S); z = zc + rt * np.sin(S)
    P = np.stack([r * np.cos(T), r * np.sin(T), z], -1).reshape(-1, 3)
    P = np.vstack([P, [[0, 0, H]]])
    if extra is not None: P = np.vstack([P, extra])
    return P

def outlines(params, d, xs_top, xs_bot):
    H, rt, e, f, u0, v0, roll = params
    P = tube_points(rt, H)
    uv = project(P, e, d, f, u0, v0, roll)
    bot, top = hull(uv)
    yt = np.interp(xs_top, top[:, 0], top[:, 1], left=np.nan, right=np.nan)
    yb = np.interp(xs_bot, bot[:, 0], bot[:, 1], left=np.nan, right=np.nan)
    return yt, yb, top, bot

def lm(fun, p0, iters=60, eps=None, lam=1e-3, verbose=False):
    p = np.array(p0, float)
    eps = eps if eps is not None else np.maximum(np.abs(p) * 1e-4, 1e-6)
    r = fun(p); cost = r @ r
    for it in range(iters):
        J = np.empty((r.size, p.size))
        for i in range(p.size):
            dp = np.zeros_like(p); dp[i] = eps[i]
            J[:, i] = (fun(p + dp) - r) / eps[i]
        A = J.T @ J; g = J.T @ r
        improved = False
        for _ in range(12):
            step = np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-12), -g)
            pn = p + step; rn = fun(pn); cn = rn @ rn
            if cn < cost:
                p, r, cost = pn, rn, cn; lam = max(lam / 3, 1e-9); improved = True; break
            lam *= 4
        if verbose: print(it, cost, p)
        if not improved or np.max(np.abs(step) / (np.abs(p) + 1e-9)) < 1e-7: break
    return p, r, J
