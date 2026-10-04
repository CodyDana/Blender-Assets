"""t7 (2026-10-03): the pinhole camera fitted to the user's photo (t4/ref_profile.json, t4/trace_ref_profile.py) as a
small importable module (system Python + numpy), in the drum's DESIGN frame (taiko_uv: real = DRUM_SCALE x design).

Photo frame (units of the crown radius Rc = taiko_uv.BODY_RC, 0.547 design): X right, Y away from the camera, Z up the
drum axis, origin at the drum's centre. The drum stands on its -X head (+X head up).

t7 VIEW SIDE: the camera looks at the +Y ring handle (lathe angle th = 0 faces the camera). The ring hangs toward the
drum's -Z (its lying-down "down"), which from this side is the photo's LEFT, as the photo's ring hangs left of its
pivot (t4-t6 looked at the -Y handle, where the ring hung to the right). A design point (x, y, z) (axis x, lathe
angle th: y = r cos th, z = r sin th) sits at photo (z, -y, x) / Rc: th = 0 faces the camera, th = -pi/2 (-Z, the
lathe's UV seam) is the LEFT silhouette, th = +pi/2 the right. render_t7 places the standing drum the same way.

VIEW_TH: the photo faces its ring hardware (plate centre about 1 deg right of the drum's front). Ours hangs its ring
from a plate centred PHI = 5.68 deg above the equator (build_taiko.ring_solve: the vertical ring then rests on the
washer rim), and the photo's plate centre traces 0.80 deg right of its front, so the camera faces our lathe angle
VIEW_TH = 5.68 - 0.80 = 4.88 deg: every design point is turned by
-VIEW_TH about the axis before the mapping (and the rays back), and render_t7 turns the standing drum the same way.
"""
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
_cf = json.loads((Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/props/taiko/t4/ref_profile.json"))
                 .read_text(encoding="utf-8"))["camera_fit"]
F = _cf["focal_px"]
DH = _cf["horizontal_distance_in_crown_radii"]
HC = _cf["camera_height_above_drum_centre_in_crown_radii"]
PITCH = math.radians(_cf["pitch_down_deg"])
ROLL = math.radians(_cf["roll_deg"])
# t7: the judge compares in compose's frame, our render scaled / moved so the two head outlines (ellipses fitted to the
# top 60 px of each silhouette) coincide. With the fit's roll and the lens shift in the right units (t4-t6 render_t*
# divided the shift by the frame height 1224, Blender reads it in units of the sensor-fit width 1024: those renders sat
# 16.3 px high, which compose's head alignment hid), that frame is this camera moved (+1.29, -6.30) px (scale 1.00).
# ALIGN_PX moves the principal point by that much here and in render_t7, so the renders, the trace, the ear fit and
# compose's overlay all share the judge's frame.
ALIGN_PX = (1.29, -6.30)
CX, CY = _cf["principal_x_px"] + ALIGN_PX[0], 512.0 + ALIGN_PX[1]
RC = 0.547                     # design units per photo unit (taiko_uv.BODY_RC)
VIEW_TH = math.radians(4.88)   # the lathe angle that faces the camera (see above)
_CV, _SV = math.cos(VIEW_TH), math.sin(VIEW_TH)


def _rot(P, sgn):
    """turn design points by sgn * VIEW_TH about the axis (x)"""
    P = np.atleast_2d(np.asarray(P, float))
    y, z = P[:, 1], P[:, 2]
    return np.c_[P[:, 0], _CV * y - sgn * _SV * z, sgn * _SV * y + _CV * z]
C = np.array([0.0, -DH, HC])


def basis():
    fwd = np.array([0.0, math.cos(PITCH), -math.sin(PITCH)])
    right = np.array([1.0, 0.0, 0.0])
    up = np.cross(right, fwd)
    cr, sr = math.cos(ROLL), math.sin(ROLL)
    return fwd, cr * right + sr * up, -sr * right + cr * up


FWD, RIGHT, UP = basis()


def project_photo(P):
    """photo-frame points (N, 3) in Rc -> pixels (N, 2)"""
    P = np.atleast_2d(np.asarray(P, float))
    rel = P - C
    zc = rel @ FWD
    return np.c_[CX + F * (rel @ RIGHT) / zc, CY - F * (rel @ UP) / zc]


def depth_photo(P):
    P = np.atleast_2d(np.asarray(P, float))
    return (P - C) @ FWD


def design_to_photo(P):
    """design-frame points (N, 3) (x axis, y, z) -> photo frame (Rc units)"""
    P = _rot(P, -1)
    return np.c_[P[:, 2], -P[:, 1], P[:, 0]] / RC


def photo_to_design(Q):
    Q = np.atleast_2d(np.asarray(Q, float))
    return _rot(np.c_[Q[:, 2], -Q[:, 1], Q[:, 0]] * RC, 1)


def project_design(P):
    return project_photo(design_to_photo(P))


def depth_design(P):
    return depth_photo(design_to_photo(P))


def cyl(x, r, th):
    """design points on the axis x at radius r, lathe angle th (broadcast)"""
    x, r, th = np.broadcast_arrays(np.atleast_1d(x), np.atleast_1d(r), np.atleast_1d(th))
    return np.c_[x, r * np.cos(th), r * np.sin(th)]


def ray_design(u, v):
    """the viewing ray through pixel (u, v): origin and unit direction in the design frame"""
    d = FWD + RIGHT * (u - CX) / F - UP * (v - CY) / F
    d = d / np.linalg.norm(d)
    return photo_to_design(C)[0], _rot(np.array([d[2], -d[1], d[0]]), 1)[0]


def hit_revolution(u, v, rfun, x_lo, x_hi, front=True, n=6000):
    """first (front=True) intersection of the pixel's ray with the surface of revolution r = rfun(x) (design units)
    for x in x_lo..x_hi; returns (x, r, th) or None"""
    o, d = ray_design(u, v)
    t = np.linspace(2.0, 8.0, n)
    P = o[None, :] + t[:, None] * d[None, :]
    rr = np.hypot(P[:, 1], P[:, 2])
    xs = P[:, 0]
    ok = (xs >= x_lo) & (xs <= x_hi)
    f = rr - rfun(xs)
    idx = np.where(ok[:-1] & ok[1:] & (np.sign(f[:-1]) != np.sign(f[1:])))[0]
    if not len(idx):
        return None
    i = idx[0] if front else idx[-1]
    a = f[i] / (f[i] - f[i + 1])
    Q = P[i] + (P[i + 1] - P[i]) * a
    return float(Q[0]), float(math.hypot(Q[1], Q[2])), float(math.atan2(Q[2], Q[1]))


def contour_th(r, side):
    """lathe angle of the silhouette (contour generator) of a cylinder of radius r (slope ignored): photo point
    (r sin th, -r cos th, x) / RC, normal (sin th, -cos th, 0): (P - C) . n = r / RC - DH cos th = 0. side -1 = the
    photo's left (th < 0), +1 = right"""
    c = r / (RC * DH)
    th = math.acos(max(-1.0, min(1.0, c)))
    return (-th if side < 0 else th) + VIEW_TH


def invert_silhouette(u, v, side, x0=0.5, r0=0.65):
    """silhouette pixel -> (x, r) of its contour point (slope ignored), design units"""
    from scipy.optimize import least_squares

    def g(q):
        x, r = q
        return project_design(cyl(x, r, contour_th(r, side)))[0] - np.array([u, v])
    sol = least_squares(g, [x0, r0], bounds=([-1.0, 0.3], [1.0, 1.2]))
    return sol.x
