"""2D polygon tools (numpy only; usable inside and outside Blender).

Polygons are (N, 2) float arrays, closed implicitly (last point != first). Orientation: counter-clockwise = positive
signed area in the (a, b) plane (for a side view a = X, b = Z).
"""
from __future__ import annotations

import math
from typing import List, Sequence

import numpy as np

from . import lod as _lod


def arr(P) -> np.ndarray:
    P = np.asarray(P, float)
    if len(P) > 1 and np.allclose(P[0], P[-1]):
        P = P[:-1]
    return P


def area(P) -> float:
    P = arr(P)
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def ccw(P) -> np.ndarray:
    P = arr(P)
    return P if area(P) > 0 else P[::-1].copy()


def dedupe(P, tol=1e-6) -> np.ndarray:
    P = arr(P)
    keep = [0]
    for i in range(1, len(P)):
        if np.linalg.norm(P[i] - P[keep[-1]]) > tol:
            keep.append(i)
    Q = P[keep]
    if len(Q) > 2 and np.linalg.norm(Q[0] - Q[-1]) <= tol:
        Q = Q[:-1]
    return Q


def dp_simplify(P, tol) -> np.ndarray:
    """Douglas-Peucker on a closed ring."""
    P = arr(P)
    n = len(P)
    if n < 5:
        return P
    i1 = int(np.argmax(np.hypot(*(P - P[0]).T)))
    keep = np.zeros(n + 1, bool)
    Q = np.vstack([P, P[:1]])
    keep[[0, i1, n]] = True
    stack = [(0, i1), (i1, n)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        A, B = Q[a], Q[b]
        ab = B - A
        nn = np.hypot(*ab)
        seg = Q[a + 1:b]
        d = np.hypot(*(seg - A).T) if nn == 0 else np.abs(ab[0] * (seg[:, 1] - A[1]) - ab[1] * (seg[:, 0] - A[0])) / nn
        k = int(np.argmax(d))
        if d[k] > tol:
            m = a + 1 + k
            keep[m] = True
            stack += [(a, m), (m, b)]
    return Q[:-1][keep[:-1]]


def resample(P, step, closed=True) -> np.ndarray:
    P = arr(P)
    Q = np.vstack([P, P[:1]]) if closed else P
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    n = max(int(round(d[-1] / step)), 3)
    t = np.linspace(0, d[-1], n, endpoint=not closed)
    return np.c_[np.interp(t, d, Q[:, 0]), np.interp(t, d, Q[:, 1])]


def smooth(P, sigma_pts=2.0, iters=1) -> np.ndarray:
    """Periodic Gaussian smoothing of a (dense, evenly resampled) closed ring."""
    P = arr(P).copy()
    n = len(P)
    r = int(3 * sigma_pts) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_pts) ** 2)
    k /= k.sum()
    for _ in range(iters):
        Q = np.zeros_like(P)
        for j, w in zip(range(-r, r + 1), k):
            Q += w * np.roll(P, -j, axis=0)
        P = Q
    return P


def fillet(P, radius, seg=4, min_turn_deg=12.0, radii=None) -> np.ndarray:
    """Round every corner of a closed polygon with an arc (tangent length clamped to 45 % of the shorter edge).
    ``radii``: optional per-vertex radius list (0 = keep sharp)."""
    P = arr(P)
    n = len(P)
    seg = _lod.count(seg, 1)
    out = []
    for i in range(n):
        r = radius if radii is None else radii[i]
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        u = a - b
        v = c - b
        lu, lv = np.linalg.norm(u), np.linalg.norm(v)
        if r <= 0 or lu < 1e-9 or lv < 1e-9:
            out.append(b)
            continue
        u /= lu
        v /= lv
        cosang = float(np.clip(u @ v, -1, 1))
        ang = math.acos(cosang)                      # interior angle between the two edges
        turn = math.pi - ang
        if math.degrees(turn) < min_turn_deg:
            out.append(b)
            continue
        t = r / math.tan(ang / 2)
        tmax = 0.45 * min(lu, lv)
        if t > tmax:
            t = tmax
            r = t * math.tan(ang / 2)
        p0 = b + u * t
        p1 = b + v * t
        bis = (u + v)
        bis /= np.linalg.norm(bis)
        ctr = b + bis * (r / math.sin(ang / 2))
        a0 = math.atan2(*(p0 - ctr)[::-1])
        a1 = math.atan2(*(p1 - ctr)[::-1])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        for k in range(seg + 1):
            th = a0 + da * k / seg
            out.append(ctr + r * np.array([math.cos(th), math.sin(th)]))
    return dedupe(np.array(out))


def offset(P, d, miter_limit=3.0) -> np.ndarray:
    """Offset a closed CCW polygon by d (positive = outward). Mitered joins (fine for convex-ish small offsets)."""
    P = ccw(P)
    n = len(P)
    out = []
    for i in range(n):
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        e0 = b - a
        e1 = c - b
        n0 = np.array([e0[1], -e0[0]]) / max(np.linalg.norm(e0), 1e-12)
        n1 = np.array([e1[1], -e1[0]]) / max(np.linalg.norm(e1), 1e-12)
        m = n0 + n1
        lm = np.linalg.norm(m)
        if lm < 1e-9:
            out.append(b + n0 * d)
            continue
        m /= lm
        s = d / max(float(m @ n0), 1.0 / miter_limit)
        out.append(b + m * s)
    return np.array(out)


def point_in_poly(pt, P) -> bool:
    x, y = pt
    P = arr(P)
    inside = False
    j = len(P) - 1
    for i in range(len(P)):
        xi, yi = P[i]
        xj, yj = P[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-300) + xi:
            inside = not inside
        j = i
    return inside


def arc(cx, cy, r, a0_deg, a1_deg, n) -> np.ndarray:
    n = _lod.arc_points(n)
    t = np.radians(np.linspace(a0_deg, a1_deg, n))
    return np.c_[cx + r * np.cos(t), cy + r * np.sin(t)]


def rounded_rect(a0, a1, b0, b1, r, seg=4) -> np.ndarray:
    r = min(r, 0.49 * (a1 - a0), 0.49 * (b1 - b0))
    if r <= 0:
        return np.array([[a0, b0], [a1, b0], [a1, b1], [a0, b1]], float)
    pts = []
    for (cx, cy, s) in ((a1 - r, b0 + r, -90), (a1 - r, b1 - r, 0), (a0 + r, b1 - r, 90), (a0 + r, b0 + r, 180)):
        pts.append(arc(cx, cy, r, s, s + 90, seg + 1))
    return dedupe(np.vstack(pts))


def superellipse(a, b, n_exp=4.0, npts=48, ca=0.0, cb=0.0) -> np.ndarray:
    npts = _lod.ring(npts)
    t = np.linspace(0, 2 * math.pi, npts, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    x = a * np.sign(c) * np.abs(c) ** (2.0 / n_exp)
    y = b * np.sign(s) * np.abs(s) ** (2.0 / n_exp)
    return np.c_[ca + x, cb + y]


def polyline_interp(pts, x):
    """Piecewise-linear y(x) through pts sorted by x (clamped)."""
    pts = np.asarray(pts, float)
    o = np.argsort(pts[:, 0])
    return np.interp(x, pts[o, 0], pts[o, 1])


def rot(P, deg, about=(0.0, 0.0)) -> np.ndarray:
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    P = np.asarray(P, float) - about
    return np.c_[c * P[:, 0] - s * P[:, 1], s * P[:, 0] + c * P[:, 1]] + about


def clip_x(P, x0=None, x1=None) -> np.ndarray:
    """Sutherland-Hodgman clip of a closed polygon to x >= x0 and/or x <= x1."""
    P = arr(P)

    def clip(P, keep, inter):
        out = []
        n = len(P)
        for i in range(n):
            a, b = P[i - 1], P[i]
            ka, kb = keep(a), keep(b)
            if kb:
                if not ka:
                    out.append(inter(a, b))
                out.append(b)
            elif ka:
                out.append(inter(a, b))
        return np.array(out) if out else np.zeros((0, 2))

    def ix(xc):
        return lambda a, b: a + (b - a) * ((xc - a[0]) / (b[0] - a[0]))

    if x0 is not None:
        P = clip(P, lambda p: p[0] >= x0, ix(x0))
    if x1 is not None and len(P):
        P = clip(P, lambda p: p[0] <= x1, ix(x1))
    return P


def clip_y(P, y0=None, y1=None) -> np.ndarray:
    P = arr(P)
    Q = clip_x(P[:, ::-1], y0, y1)
    return Q[:, ::-1] if len(Q) else Q


def chaikin(P, iters=2) -> np.ndarray:
    P = arr(P)
    for _ in range(iters):
        Q = np.roll(P, -1, axis=0)
        out = np.empty((2 * len(P), 2))
        out[0::2] = 0.75 * P + 0.25 * Q
        out[1::2] = 0.25 * P + 0.75 * Q
        P = out
    return P


def clean_hard(P, tol=0.55, fillet_r=0.0, seg=3) -> np.ndarray:
    """Trace polygon -> crisp outline: Douglas-Peucker removes the pixel stair noise and keeps corners; optional
    fillet on every corner."""
    Q = ccw(dp_simplify(arr(P), tol))
    if fillet_r > 0:
        Q = fillet(Q, fillet_r, seg)
    return Q


def clean_smooth(P, step=0.6, sigma_mm=1.6, corner_deg=40.0) -> np.ndarray:
    """Trace polygon -> smooth outline for curved (wood) parts: resample, Gaussian smoothing; vertices where the
    DP-simplified ring turns more than corner_deg are pinned (crisp corners kept)."""
    P = ccw(arr(P))
    core = dp_simplify(P, 0.6)
    pins = []
    for i in range(len(core)):
        a, b, c = core[i - 1], core[i], core[(i + 1) % len(core)]
        u, v = b - a, c - b
        t = math.degrees(abs(math.atan2(u[0] * v[1] - u[1] * v[0], u @ v)))
        if t > corner_deg:
            pins.append(b)
    R = resample(P, step)
    S = smooth(R, sigma_mm / step)
    if pins:
        # snap: the resampled point nearest each pin is replaced by the pin, with a blend over +-3 points
        for p in pins:
            k = int(np.argmin(np.linalg.norm(R - p, axis=1)))
            for j in range(-3, 4):
                w = 1.0 - abs(j) / 4.0
                S[(k + j) % len(S)] = w * R[(k + j) % len(R)] + (1 - w) * S[(k + j) % len(S)]
            S[k] = p
    return ccw(S)
