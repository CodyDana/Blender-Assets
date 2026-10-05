"""Pinhole-camera silhouette rasteriser and contour comparison (numpy + PIL; plain Python).

Used by the LOD-pop gate (GUN_BUILDING_STUDY 7.2 B8: silhouettes of LOD k and k+1 at the switch distance, 2560 x 1440,
90 deg horizontal FOV, 4 headings; mean contour difference <= 1 px, max <= 3 px) and the sight-picture gate (B4 / S2).
Triangles in mm; the camera in the same frame.
"""
from __future__ import annotations

import math

import numpy as np


class Camera:
    def __init__(self, eye, target=None, forward=None, up=(0.0, 0.0, 1.0), hfov_deg=90.0, W=2560, H=1440):
        self.eye = np.asarray(eye, float)
        f = np.asarray(forward, float) if forward is not None else np.asarray(target, float) - self.eye
        f = f / np.linalg.norm(f)
        r = np.cross(f, np.asarray(up, float))
        if np.linalg.norm(r) < 1e-9:
            r = np.cross(f, np.array([0.0, 1.0, 0.0]))
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        self.f, self.r, self.u = f, r, u
        self.W, self.H = W, H
        self.fx = (W / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)

    def project(self, P):
        d = np.asarray(P, float) - self.eye
        z = d @ self.f
        x = d @ self.r
        y = d @ self.u
        sx = self.W / 2.0 + self.fx * x / z
        sy = self.H / 2.0 - self.fx * y / z
        return np.c_[sx, sy], z


def raster_mask(cam: Camera, V, T, ss=2, window=None):
    """Coverage mask (pixel centres) of triangles at ss x supersampling; window = (x0, y0, x1, y1) in pixels (crop).
    Returns (mask, (x0, y0) of the window)."""
    S, z = cam.project(V)
    if window is None:
        x0, y0, x1, y1 = 0, 0, cam.W, cam.H
    else:
        x0, y0, x1, y1 = window
    w, h = (x1 - x0) * ss, (y1 - y0) * ss
    M = np.zeros((h, w), bool)
    P = (S - np.array([x0, y0])) * ss
    tri = P[T]
    zt = z[T]
    ok = np.all(zt > 1.0, axis=1)
    tri = tri[ok]
    lo = np.floor(tri.min(1) - 0.5).astype(int)
    hi = np.ceil(tri.max(1) + 0.5).astype(int)
    keep = (hi[:, 0] > 0) & (hi[:, 1] > 0) & (lo[:, 0] < w) & (lo[:, 1] < h)
    for t, a, b in zip(tri[keep], lo[keep], hi[keep]):
        xa, ya = max(a[0], 0), max(a[1], 0)
        xb, yb = min(b[0], w), min(b[1], h)
        if xb <= xa or yb <= ya:
            continue
        X, Y = np.meshgrid(np.arange(xa, xb) + 0.5, np.arange(ya, yb) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = t
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12:
            continue
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / d
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / d
        l3 = 1 - l1 - l2
        M[ya:yb, xa:xb] |= (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
    return M, (x0, y0)


def boundary(M):
    e = M.copy()
    e[1:, :] &= M[:-1, :]
    e[:-1, :] &= M[1:, :]
    e[:, 1:] &= M[:, :-1]
    e[:, :-1] &= M[:, 1:]
    e[0, :] = e[-1, :] = False
    e[:, 0] = e[:, -1] = False
    return M & ~e


def contour_distance(A, B, ss=1, chunk=800):
    """Symmetric contour distance between two masks (in output pixels: divided by ss): (mean, max, p99, xor_px)."""
    pa = np.argwhere(boundary(A)).astype(np.float32)
    pb = np.argwhere(boundary(B)).astype(np.float32)
    if not len(pa) or not len(pb):
        return float("inf"), float("inf"), float("inf"), int((A ^ B).sum())

    def nn(P, Q):
        out = np.empty(len(P), np.float32)
        for s in range(0, len(P), chunk):
            d = ((P[s:s + chunk, None, :] - Q[None, :, :]) ** 2).sum(-1)
            out[s:s + chunk] = np.sqrt(d.min(1))
        return out
    da, db = nn(pa, pb), nn(pb, pa)
    d = np.r_[da, db] / ss
    return float(d.mean()), float(d.max()), float(np.percentile(d, 99)), int((A ^ B).sum() / (ss * ss))
