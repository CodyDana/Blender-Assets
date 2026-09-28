"""Reference camera for view A (orthographic), in the right shoe's local frame (mm).

Parameters: az (deg, camera azimuth from +u toward -v, i.e. from the toe toward the lateral side), el (deg above the
floor), s (px per mm), tx, ty (px, reference canvas 1254 x 1254), roll (deg, image rotation).
project(p) -> (x, y) reference pixels (y down). ray(x, y) -> (origin far on the camera side, direction into the scene).
"""
from __future__ import annotations

import json
import math

import numpy as np


class Cam:
    def __init__(self, az=48.0, el=22.0, s=3.6, tx=0.0, ty=0.0, roll=0.0):
        self.az, self.el, self.s, self.tx, self.ty, self.roll = az, el, s, tx, ty, roll

    def params(self):
        return np.array([self.az, self.el, self.s, self.tx, self.ty, self.roll])

    @classmethod
    def from_params(cls, p):
        return cls(*[float(x) for x in p])

    def basis(self):
        a, e = math.radians(self.az), math.radians(self.el)
        cdir = np.array([math.cos(e) * math.cos(a), -math.cos(e) * math.sin(a), math.sin(e)])  # toward the camera
        fwd = -cdir
        right = np.cross(fwd, [0.0, 0.0, 1.0])
        right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        r = math.radians(self.roll)
        right2 = math.cos(r) * right + math.sin(r) * up
        up2 = -math.sin(r) * right + math.cos(r) * up
        return cdir, right2, up2

    def project(self, p):
        p = np.asarray(p, dtype=float)
        _, right, up = self.basis()
        x = self.s * (p @ right) + self.tx
        y = -self.s * (p @ up) + self.ty
        return np.stack([x, y], axis=-1)

    def depth(self, p):
        """Larger = nearer the camera."""
        cdir, _, _ = self.basis()
        return np.asarray(p, dtype=float) @ cdir

    def ray(self, xy, back=2000.0):
        xy = np.asarray(xy, dtype=float)
        cdir, right, up = self.basis()
        a = (xy[..., 0:1] - self.tx) / self.s
        b = -(xy[..., 1:2] - self.ty) / self.s
        o = a * right + b * up + cdir * back
        d = np.broadcast_to(-cdir, o.shape)
        return o, d

    def to_json(self):
        return {"az": self.az, "el": self.el, "s": self.s, "tx": self.tx, "ty": self.ty, "roll": self.roll}


def fit(landmarks, init: Cam, fixed=(), weights=None, iters=200):
    """landmarks: list of (xyz_local_mm, (px, py)). Least squares by damped Gauss-Newton on the free params."""
    P = np.array([l[0] for l in landmarks], dtype=float)
    Q = np.array([l[1] for l in landmarks], dtype=float)
    Wt = np.ones(len(P)) if weights is None else np.asarray(weights, dtype=float)
    names = ["az", "el", "s", "tx", "ty", "roll"]
    free = [i for i, n in enumerate(names) if n not in fixed]
    x = init.params()

    def resid(xx):
        c = Cam.from_params(xx)
        return ((c.project(P) - Q) * np.sqrt(Wt)[:, None]).ravel()
    lam = 1e-2
    r = resid(x)
    for _ in range(iters):
        J = np.zeros((len(r), len(free)))
        for k, i in enumerate(free):
            h = 1e-4 * max(1.0, abs(x[i]))
            xp = x.copy()
            xp[i] += h
            J[:, k] = (resid(xp) - r) / h
        A = J.T @ J + lam * np.eye(len(free))
        step = np.linalg.solve(A, -J.T @ r)
        xn = x.copy()
        xn[free] += step
        rn = resid(xn)
        if (rn ** 2).sum() < (r ** 2).sum():
            x, r = xn, rn
            lam *= 0.5
            if np.abs(step).max() < 1e-7:
                break
        else:
            lam *= 4.0
    c = Cam.from_params(x)
    per = np.linalg.norm(c.project(P) - Q, axis=1)
    return c, per


def seg_dist(q, poly):
    """Distance from 2D points q (N,2) to a 2D polyline (M,2)."""
    a = poly[:-1][None]
    b = poly[1:][None]
    p = np.asarray(q, dtype=float)[:, None]
    ab = b - a
    t = np.clip(((p - a) * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-12), 0, 1)
    d = np.linalg.norm(p - (a + ab * t[..., None]), axis=-1)
    return d.min(1)


def fit_general(init: Cam, points=(), curves=(), fixed=("roll",), iters=300):
    """points: [(xyz, (px,py), weight)]; curves: [(img_pts (K,2), curve3d (M,3), weight)] - image points must lie on
    the projected 3D curve. Damped Gauss-Newton."""
    names = ["az", "el", "s", "tx", "ty", "roll"]
    free = [i for i, n in enumerate(names) if n not in fixed]
    x = init.params()

    def resid(xx):
        c = Cam.from_params(xx)
        r = []
        for xyz, px, w in points:
            r.extend(((c.project(np.array(xyz, dtype=float)) - np.array(px)) * math.sqrt(w)).tolist())
        for img, cur, w in curves:
            r.extend((seg_dist(np.asarray(img, dtype=float), c.project(np.asarray(cur, dtype=float))) * math.sqrt(w)).tolist())
        return np.array(r)
    lam = 1e-2
    r = resid(x)
    for _ in range(iters):
        J = np.zeros((len(r), len(free)))
        for k, i in enumerate(free):
            h = 1e-4 * max(1.0, abs(x[i]))
            xp = x.copy()
            xp[i] += h
            J[:, k] = (resid(xp) - r) / h
        step = np.linalg.solve(J.T @ J + lam * np.eye(len(free)), -J.T @ r)
        xn = x.copy()
        xn[free] += step
        rn = resid(xn)
        if (rn ** 2).sum() < (r ** 2).sum():
            x, r = xn, rn
            lam *= 0.5
            if np.abs(step).max() < 1e-7:
                break
        else:
            lam *= 4.0
    return Cam.from_params(x), r
