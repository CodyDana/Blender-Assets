"""Saya (scabbard) for the basic katana: every number and form rule, read from WorkFiles/katana/katana_spec.json
(the authority, section "saya" / "sheathed" / "sockets") through katana_spec (read-only import).

Pure Python + numpy (no bpy). Units: millimetres.

Frames
    sword frame  origin = the katana's Grip socket, +Z along the tsuka axis toward the blade, +X mune, -Y omote
    saya frame   = sword frame - (0, 0, 138.3): origin = BeltMount (the kurikata station on the mouth's tangent axis),
                 axes = the SEATED sword's axes, so Holster has zero rotation (spec saya.frame)
    arc coords   (s, rho, y) about the blade's mune arc centre C = (CX, CZ):
                 s   = R * atan2(z - CZ, CX - x)          station along the mune arc from the machi (0) toward the tip
                 rho = |(x, z) - C| - R                   radial offset from the blade's mune (0) toward the edge (+)
                 a draw is a pure rotation about C, i.e. a translation in s (spec sheathed.draw)
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

import katana_spec as K

ROOT = K.ROOT
SP = K.SP
SY = SP["saya"]
NAME = "SM_Katana_Saya"
KATANA_FBX = ROOT / "Exports" / "Katana" / "SM_Katana.fbx"
KATANA_SIDECAR = ROOT / "Exports" / "Katana" / "SM_Katana.sockets.json"
KATANA_FBX_SHA = "114c79f43f6654669c06f0684bb52a0a5aff5cae3799c1de2eab4a771e420cf7"   # finaliser re-export 2026-10-03 (katana_interface.json)

R, CX, CZ = K.R, K.CX, K.CZ
Z_OFF = -SP["sockets"]["saya_mm"]["Holster"][2]          # 138.3: sword z of the saya frame origin
RS = SY["mune_outer_radius"]                              # 3658.6
RHO_MUNE = RS - R                                         # -4.5: the saya's outer mune line in arc coords
S_MO = SY["s_mouth"]                                      # 0.3 (the koiguchi face)
S_EN = SY["s_end"]                                        # 722.09 (kojiri end)
S_KG1 = SY["koiguchi"]["s"][1]                            # 20.3 (koiguchi / body seam)
S_KJ0 = SY["kojiri"]["s"][0]                              # 694.09 (body / kojiri seam)
SEAM_W, SEAM_D = SY["koiguchi"]["seam_groove"]            # 0.3 wide x 0.2 deep
MOUTH_ROUND = 0.4
KOJIRI_ROUND = 4.0
SE_N = 2.4                                                # outer section superellipse exponent
S_CAV_END = K.S_TIP + 10.0                                # 716.09: cavity ends 10 mm past the tip
# cavity clearances (spec saya.cavity.rule): edge 1.0, sides 1.0, mune 0.5; habaki pocket 0.1 all round.
CLR_EDGE, CLR_SIDE, CLR_MUNE = 1.0, 1.0, 0.5
CLR_HABAKI = 0.11      # spec 0.1; +0.01 so the discretised loft never measures under the 0.1 gate
HABAKI_TOP_Z = SP["habaki"]["z"][1]                        # 86.0
S_POCKET_END = 28.5    # "the pocket runs from the mouth to 0.5 below the habaki top" (habaki top spans s 27.75..28.0)
KURI = SY["kurikata"]
LOD_SCREEN_SIZES = (1.0, 0.35, 0.15)                      # KATANA_BUILD_PLAN.md 2.3 (same as SM_Katana)
SLOT_NAMES = ["M_Katana_Saya_Lacquer", "M_Katana_Saya_Fittings"]   # KATANA_BUILD_PLAN.md 5.2 (plan governs slots)
SLOT_LACQUER, SLOT_FIT = 0, 1
TEX_STEM = "T_Katana_Saya"
ATLAS = 2048

# per-LOD resolution
OUTER_N = {0: 48, 1: 28, 2: 16}          # outer ring vertices
BODY_STEP = {0: 40.0, 1: 80.0, 2: 120.0}  # body stations (the arc sagitta over 40 mm is 0.05 mm)
CAV_DIRS = {0: 32, 1: 16, 2: 12}          # cavity support-polygon directions
EDGE_STEP = 0.5                           # sword edge samples (Snow Flower lesson)


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------------------------------------- arc frame
def arc_to_xyz(s, rho, y):
    a = np.asarray(s, float) / R
    r = R + np.asarray(rho, float)
    return np.stack(np.broadcast_arrays(CX - r * np.cos(a), np.asarray(y, float), CZ + r * np.sin(a)), -1)


def xyz_to_arc(P):
    P = np.asarray(P, float)
    dx, dz = CX - P[..., 0], P[..., 2] - CZ
    s = R * np.arctan2(dz, dx)
    rho = np.hypot(dx, dz) - R
    return s, rho, P[..., 1]


def tangent(s):
    a = s / R
    return np.array([math.sin(a), 0.0, math.cos(a)])


def radial(s):
    """+rho direction (toward the edge) at station s."""
    a = s / R
    return np.array([-math.cos(a), 0.0, math.sin(a)])


# ---------------------------------------------------------------------------------------------- outer form
def dims(s):
    """(depth D along rho, width W along y) of the outer section at station s (linear in s, spec)."""
    t = (s - S_MO) / (S_EN - S_MO)
    return (lerp(SY["depth_x"]["mouth"], SY["depth_x"]["kojiri_end"], t),
            lerp(SY["width_y"]["mouth"], SY["width_y"]["kojiri_end"], t))


def centre_rho(s):
    return RHO_MUNE + dims(s)[0] / 2


def se_point(a, b, n, th):
    c, s_ = math.cos(th), math.sin(th)
    return a * math.copysign(abs(c) ** (2.0 / n), c), b * math.copysign(abs(s_) ** (2.0 / n), s_)


_FRAC_CACHE = {}


def equal_arc_params(a, b, n, N, phase=math.pi):
    """N superellipse parameters at equal arclength fractions, starting at ``phase`` (pi = the mune side, where the
    UV seam sits). Fractions are measured on a 2048-point reference ring of the same aspect, so every LOD's vertices
    sit at the same fractions of the same curve."""
    key = (round(a / b, 4), n, N, phase)
    if key in _FRAC_CACHE:
        return _FRAC_CACHE[key]
    th = phase + np.linspace(0.0, 2 * math.pi, 4097)
    pts = np.array([se_point(a, b, n, t) for t in th])
    L = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    tgt = np.arange(N) / N * L[-1]
    out = np.interp(tgt, L, th)
    _FRAC_CACHE[key] = out
    return out


def outer_ring(s, N, shrink=0.0):
    """Outer section ring at s as (rho, y) points (N, 2), vertex 0 on the mune side, then toward the ura (+y)...
    Order: phase pi (mune) -> +3pi/2 (y-) ... i.e. counter-clockwise in (rho, y) starting at the mune."""
    D, W = dims(s)
    a, b = D / 2 - shrink, W / 2 - shrink
    th = equal_arc_params(D / 2, W / 2, SE_N, N)
    pts = np.array([se_point(a, b, SE_N, t) for t in th])
    pts[:, 0] += centre_rho(s)
    return pts


def outer_perimeter(s):
    D, W = dims(s)
    th = np.linspace(0, 2 * math.pi, 1025)
    pts = np.array([se_point(D / 2, W / 2, SE_N, t) for t in th])
    return float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())


def outer_half_y(s, rho):
    """|y| of the outer surface at station s and radial position rho (0 outside)."""
    D, W = dims(s)
    x = abs(rho - centre_rho(s)) / (D / 2)
    if x >= 1:
        return 0.0
    return W / 2 * (1 - x ** SE_N) ** (1 / SE_N)


# ---------------------------------------------------------------------------------------------- sockets
def sockets_saya_mm():
    S = SP["sockets"]
    d = dict(S["saya_mm"])
    d["DrawPivot"] = S["saya_mm_extra"]["DrawPivot"]
    return {k: tuple(float(v) for v in vals) for k, vals in d.items()}


def to_saya(P):
    P = np.array(P, float)
    P[..., 2] -= Z_OFF
    return P
