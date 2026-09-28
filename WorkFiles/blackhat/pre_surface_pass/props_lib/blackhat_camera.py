#!/usr/bin/env python
"""props_lib.blackhat_camera - the reference camera of REFERENCE_SPEC 1, in the build frame.

numpy only.  The metrology (WorkFiles/blackhat/reference_metrology/bh_cam.py) fitted a pinhole
camera in its own frame: the rim-outline circle of radius 1 (R) at z = 0, the hat axis +Z,
the camera on -Y at distance d and elevation e looking at the rim centre, image right = +X,
principal point (u0, v0), focal f px, roll (content rotated clockwise for roll < 0 here, the
fit's sign).  This module carries that camera into the build frame:

    world_mm = Rz(PSI + 90) . (R x metrology) + (0, 0, z_off)

(theta 0, the camera-facing rim point, is metrology -Y; world azimuth = theta + PSI).  The
numbers are REFERENCE_SPEC 1's; the build never reads the reference pixels.
"""
from __future__ import annotations

import math

import numpy as np

from .blackhat_spec import BLACK_HAT, BlackHatSpec, PSI_DEG


def _basis(e, roll):
    F = np.array([0.0, math.cos(e), -math.sin(e)])
    Rv = np.array([1.0, 0.0, 0.0])
    U = np.array([0.0, math.sin(e), math.cos(e)])
    c, s = math.cos(roll), math.sin(roll)
    return F, c * Rv - s * U, s * Rv + c * U


class RefCamera:
    def __init__(self, spec: BlackHatSpec = BLACK_HAT, z_off_R: float = None):
        c = spec.camera
        self.spec = spec
        self.R = spec.R
        self.z_off_R = c.z_offset_R if z_off_R is None else z_off_R
        self.z_off_mm = self.z_off_R * self.R
        self.e = math.radians(c.elevation_deg)
        self.roll = math.radians(c.roll_deg)
        self.d = c.distance_R
        self.f = c.f_px
        self.u0, self.v0 = c.u0, c.v0
        self.res = c.res
        a = math.radians(PSI_DEG + 90.0)
        self.Rz = np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
        F, Rr, Ur = _basis(self.e, self.roll)
        self.F_m, self.R_m, self.U_m = F, Rr, Ur
        self.F, self.Rt, self.Up = self.Rz @ F, self.Rz @ Rr, self.Rz @ Ur
        self.C = self.Rz @ (-self.d * F) * self.R + np.array([0.0, 0.0, self.z_off_mm])

    # ------------------------------------------------------------------ projection (px, index-centred)
    def project(self, P):
        P = np.asarray(P, np.float64)
        Q = P - self.C
        x, y, z = Q @ self.Rt, Q @ self.Up, Q @ self.F
        return np.stack([self.u0 + self.f * x / z, self.v0 - self.f * y / z], -1)

    def ray(self, px, py):
        x = (px - self.u0) / self.f
        y = -(py - self.v0) / self.f
        d = self.F + x * self.Rt + y * self.Up
        return self.C.copy(), d / np.linalg.norm(d)

    # ------------------------------------------------------------------ Blender camera numbers
    def blender(self):
        w, h = self.res
        lens = self.f * 36.0 / w
        # metrology pixel coordinates are index-centred (a pixel's centre at its index); Blender's
        # continuous frame puts that centre at index + 0.5.  A positive Blender shift moves the
        # frame window right / up, i.e. the principal point LEFT / DOWN in the image
        shift_x = (0.5 * w - (self.u0 + 0.5)) / w
        shift_y = ((self.v0 + 0.5) - 0.5 * h) / w
        M = np.stack([self.Rt, self.Up, -self.F], 1)          # columns: camera X, Y, Z in world
        return {"location_mm": self.C.tolist(), "matrix3": M.tolist(), "lens_mm": lens, "sensor_mm": 36.0,
                "shift_x": shift_x, "shift_y": shift_y, "res": [w, h]}


__all__ = ["RefCamera"]
