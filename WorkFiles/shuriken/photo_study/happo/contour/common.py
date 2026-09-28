# shared helpers for method B scripts (numpy only)
import numpy as np, os
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour"

def bil(A, x, y):
    H, W = A.shape[:2]
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
    return (A[y0, x0] * (1 - fx) * (1 - fy) + A[y0, x0 + 1] * fx * (1 - fy) + A[y0 + 1, x0] * (1 - fx) * fy + A[y0 + 1, x0 + 1] * fx * fy)

def smooth1d(p, sigma, dt):
    gk = np.exp(-0.5 * (np.arange(-4 * sigma, 4 * sigma + 1e-9, dt) / sigma) ** 2); gk /= gk.sum()
    return np.convolve(np.pad(p, len(gk) // 2, mode='edge'), gk, mode='valid')

def peaks(d, TS, thr, sign=1):
    s = sign * d; DT = TS[1] - TS[0]
    idx = np.nonzero((s[1:-1] > s[:-2]) & (s[1:-1] >= s[2:]) & (s[1:-1] > thr))[0] + 1
    out = []
    for i in idx:
        a, b, c = s[i - 1], s[i], s[i + 1]
        den = a - 2 * b + c
        off = 0.5 * (a - c) / den if den != 0 else 0
        hm = s[i] / 2; j0 = i; j1 = i
        while j0 > 0 and s[j0] > hm: j0 -= 1
        while j1 < len(s) - 1 and s[j1] > hm: j1 += 1
        out.append(dict(t=float(TS[i] + off * DT), g=float(s[i]), fwhm=float((j1 - j0) * DT)))
    return out

def fit_line(P):
    m = P.mean(0)
    _, s, vt = np.linalg.svd(P - m, full_matrices=False)
    dv = vt[0]; nv = np.array([-dv[1], dv[0]])
    return m, dv, (P - m) @ nv

def robust_line(P):
    keep = np.ones(len(P), bool)
    for _ in range(8):
        m, dv, _ = fit_line(P[keep])
        r_all = (P - m) @ np.array([-dv[1], dv[0]])
        s = 1.4826 * np.median(np.abs(r_all[keep] - np.median(r_all[keep])))
        nk = np.abs(r_all - np.median(r_all[keep])) < max(3 * s, 1.0)
        if (nk == keep).all(): break
        keep = nk
    m, dv, res = fit_line(P[keep])
    return m, dv, keep, res

def intersect(p1, d1, p2, d2):
    A = np.array([[d1[0], -d2[0]], [d1[1], -d2[1]]])
    s, _ = np.linalg.solve(A, np.array(p2) - np.array(p1))
    return np.array(p1) + s * np.array(d1)

def circle_fit(P):
    # algebraic (Kasa) fit followed by a few Gauss-Newton geometric iterations
    x, y = P[:, 0], P[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    b = x * x + y * y
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = c[0], c[1]; r = np.sqrt(c[2] + cx * cx + cy * cy)
    for _ in range(20):
        dx = x - cx; dy = y - cy; di = np.hypot(dx, dy)
        J = np.c_[-dx / di, -dy / di, -np.ones(len(x))]
        res = di - r
        step, *_ = np.linalg.lstsq(J, -res, rcond=None)
        cx += step[0]; cy += step[1]; r += step[2]
        if np.abs(step).max() < 1e-6: break
    res = np.hypot(x - cx, y - cy) - r
    return np.array([cx, cy]), float(r), res

def angle_between(d1, d2):
    c = np.clip(np.dot(d1, d2) / np.linalg.norm(d1) / np.linalg.norm(d2), -1, 1)
    return float(np.degrees(np.arccos(c)))
