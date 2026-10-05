"""Pinhole camera solve for a perspective sheet panel (plain Python).

1. Landmarks: 2D panel px <-> 3D gun points (frame M, mm) give an initial camera by nonlinear least squares
   (rotation vector, camera centre, focal length; principal point at the panel centre, square pixels).
2. Silhouette refinement: the 7 parameters are refined to maximise the soft IoU between the rasterised model and the
   panel's foreground mask (optionally inside a validity mask).

Camera convention (OpenCV, right-handed): x_cam = R (P - C) with x right, y down, z forward; image
u = cx + f * x_cam / z_cam, v = cy + f * y_cam / z_cam.
"""
from __future__ import annotations

import math
from typing import Dict, Sequence

import numpy as np
from scipy.optimize import least_squares, minimize

from . import compare as C


def rodrigues(r):
    r = np.asarray(r, float)
    th = np.linalg.norm(r)
    if th < 1e-12:
        return np.eye(3)
    k = r / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


def look_at(cam, target, up=(0, 0, 1)):
    """Rotation matrix whose rows are the camera axes (x right, y down, z forward) for a camera at cam looking at
    target."""
    z = np.asarray(target, float) - np.asarray(cam, float)
    z /= np.linalg.norm(z)
    x = np.cross(z, up)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return np.vstack([x, y, z])


def mat_to_rvec(R):
    th = math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2)))
    if th < 1e-9:
        return np.zeros(3)
    w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / (2 * math.sin(th))
    return w * th


class Camera:
    def __init__(self, rvec, centre, f, cx, cy):
        self.rvec = np.asarray(rvec, float)
        self.C = np.asarray(centre, float)
        self.f = float(f)
        self.cx, self.cy = float(cx), float(cy)

    @property
    def R(self):
        return rodrigues(self.rvec)

    def project(self, P):
        X = (np.asarray(P, float) - self.C) @ self.R.T
        z = np.maximum(X[:, 2], 1e-6)
        return np.c_[self.cx + self.f * X[:, 0] / z, self.cy + self.f * X[:, 1] / z]

    def depth(self, P):
        return ((np.asarray(P, float) - self.C) @ self.R.T)[:, 2]

    def params(self):
        return np.r_[self.rvec, self.C, self.f]

    @staticmethod
    def from_params(p, cx, cy):
        return Camera(p[:3], p[3:6], p[6], cx, cy)

    def to_dict(self):
        R = self.R
        return {"rvec": self.rvec.tolist(), "centre_M_mm": self.C.tolist(), "f_px": self.f, "cx": self.cx,
                "cy": self.cy, "R_rows_cam_axes_in_M": R.tolist(),
                "forward_M": R[2].tolist(), "fov_h_deg_for_width": None}


def solve_landmarks(pts2, pts3, cx, cy, init_cam, init_target, f0=1500.0):
    pts2 = np.asarray(pts2, float)
    pts3 = np.asarray(pts3, float)
    R0 = look_at(init_cam, init_target)
    p0 = np.r_[mat_to_rvec(R0), init_cam, f0]

    def res(p):
        return (Camera.from_params(p, cx, cy).project(pts3) - pts2).ravel()

    best = None
    for scale in (1.0, 0.6, 1.6, 2.5):
        q0 = p0.copy()
        q0[3:6] = init_target + (np.asarray(init_cam) - init_target) * scale
        q0[6] = f0 * scale
        q0[:3] = mat_to_rvec(look_at(q0[3:6], init_target))
        r = least_squares(res, q0, method="lm", max_nfev=20000)
        if best is None or r.cost < best.cost:
            best = r
    cam = Camera.from_params(best.x, cx, cy)
    err = np.linalg.norm(cam.project(pts3) - pts2, axis=1)
    return cam, err


def refine_silhouette(cam, V, T, target, valid=None, iters=1500, ss=2, free_principal=True):
    """Nelder-Mead on the soft IoU (rotation vector, centre, focal and, optionally, the principal point), started
    with an explicit simplex (the raster cost is flat below a pixel, so default tiny steps never move)."""
    tgt = target.astype(float)
    p0 = np.r_[cam.params(), cam.cx, cam.cy]
    scale = np.r_[0.01, 0.01, 0.01, 15.0, 15.0, 15.0, 30.0, 3.0, 3.0]
    n = 9 if free_principal else 7

    def unpack(q):
        qq = np.zeros(9)
        qq[:n] = q
        p = p0 + qq * scale
        return Camera(p[:3], p[3:6], p[6], p[7], p[8])

    def cost(q):
        c = unpack(q)
        if np.any(c.depth(V[::50]) <= 1.0):
            return 1.0
        cov = C.raster_tris(c.project(V), T, target.shape, ss=ss)
        inter = np.minimum(cov, tgt)
        uni = np.maximum(cov, tgt)
        if valid is not None:
            inter, uni = inter[valid], uni[valid]
        return 1.0 - float(inter.sum() / max(uni.sum(), 1e-9))

    x = np.zeros(n)
    best = None
    for step in (1.5, 0.5):
        sim = np.vstack([x] + [x + np.eye(n)[i] * step for i in range(n)])
        best = minimize(cost, x, method="Nelder-Mead",
                        options={"maxiter": iters, "xatol": 1e-2, "fatol": 1e-6, "adaptive": True,
                                 "initial_simplex": sim})
        x = best.x
    return unpack(best.x), 1.0 - best.fun
