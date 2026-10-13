"""SR01 motions (plain Python): 4x4 matrices in frame M (mm) for every bone's motion, the poses the gates, renders and
(W3) the rig use. Blender conventions: R_y(+a) swings +X toward -Z (a forward-folded bipod leg goes DOWN at +90);
R_x(a) turns +Y toward +Z (the bolt opens at -60: the knob on the right swings up).
"""
from __future__ import annotations

import math

import numpy as np

from sr_common import D, dims

BOLT_TRAVEL = float(D["bolt_cycle"]["travel"])          # 88
BOLT_ROT = float(D["bolt_cycle"]["rotate_deg"])         # -60
TRIGGER_PIVOT = np.array([368.0, 0.0, -57.0])
SAFETY_PIVOT = np.array(dims("safety")["pivot_M"], float)
RELEASE_PIVOT = np.array([408.6, 0.0, -74.0])
HUB = np.array([719.6, 0.0, -62.3])
CANT_Z = float(D["bipod"]["cant"]["axis_Z"])            # -46.0
LEG_Y = 19.5
# user 2026-10-13: the legs SPLAY when deployed (tension-swivel pattern). Each leg pin is rolled about the leg's own
# axis (X through the hub) by SPLAY, outboard-down, so a 90 deg swing ends with the leg leaning SPLAY out sideways;
# folded (0 deg) the leg is unchanged along the forend. 12 deg: the middle of the 10-15 deg spread of fixed-splay
# swivel bipods; it gives a 2.0x wider stance than parallel legs at ext 0 and keeps the deployed legs inside the
# +-15 deg cant (the downhill leg never passes vertical by more than 3 deg)
SPLAY = 12.0
RISER = tuple(dims("cheek_riser")["travel_Z"])          # (-12.9, 12.0)


def T(d):
    M = np.eye(4)
    M[:3, 3] = d
    return M


def R(axis, deg, pivot=(0.0, 0.0, 0.0)):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    if axis == "x":
        r = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    elif axis == "y":
        r = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    else:
        r = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    M = np.eye(4)
    M[:3, :3] = r
    p = np.asarray(pivot, float)
    return T(p) @ M @ T(-p)


def bolt(rot=0.0, slide=0.0):
    """rotate about the bore (X axis through Z 0) then slide -X (sequenced: slide only at full rotation)."""
    return T((-slide, 0.0, 0.0)) @ R("x", rot)


def bolt_cycle_param(u):
    """u in [0, 1]: 0..0.4 rotate 0 -> -60, 0.4..1 slide 0 -> 88 (the compound path the B3 sweep walks)."""
    if u <= 0.4:
        return bolt(BOLT_ROT * u / 0.4, 0.0)
    return bolt(BOLT_ROT, BOLT_TRAVEL * (u - 0.4) / 0.6)


def trigger(deg):
    return R("y", deg, TRIGGER_PIVOT)


def selector(deg):
    return R("y", deg, SAFETY_PIVOT)


def mag_release(deg):
    return R("y", deg, RELEASE_PIVOT)


def riser(dz):
    return T((0.0, 0.0, dz))


def cant(deg):
    return R("x", deg, (0.0, 0.0, CANT_Z))


def leg_roll(side):
    """the leg frame's roll about its own axis (X through the hub): the pin axis Y goes to (0, cos s, +-sin s)."""
    y = LEG_Y if side == "l" else -LEG_Y
    return R("x", SPLAY if side == "l" else -SPLAY, (0.0, y, HUB[2]))


def pin_axis(side):
    return leg_roll(side)[:3, :3] @ np.array([0.0, 1.0, 0.0])


def leg(side, fold_deg, cant_deg=0.0):
    """swing about the angled pin: roll . R_y(fold) . roll^-1 (the leg meshes are already built rolled)."""
    y = LEG_Y if side == "l" else -LEG_Y
    Rr = leg_roll(side)
    return cant(cant_deg) @ Rr @ R("y", fold_deg, (HUB[0], y, HUB[2])) @ np.linalg.inv(Rr)


def leg_ext(side, fold_deg, ext, cant_deg=0.0):
    return leg(side, fold_deg, cant_deg) @ T((ext, 0.0, 0.0))


def magazine(drop):
    """straight path: the magazine drops -Z by ``drop`` mm from the seat."""
    return T((0.0, 0.0, -drop))
