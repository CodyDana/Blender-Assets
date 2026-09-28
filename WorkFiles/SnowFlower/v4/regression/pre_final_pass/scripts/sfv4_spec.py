"""Snow Flower v4 - every design number in one place (millimetres, v4 model frame).

MODEL FRAME (the shipped mesh)
    origin  = SOCKET Grip: the primary-hand centre on the grip axis, 46 mm below the collar
    +Z      = toward the blade tip (the pommel is at -Z)
    +X      = the blade SPINE side (the tip sweeps toward +X); -X = the cutting edge
    -Y      = the "front" face (the face the sheet's FRONT VIEW shows); +Y = back
    Seen in the sheet's front view (pommel up, tip down) +X is on the viewer's LEFT.

SOURCE OF THE NUMBERS
    Sheet = References/SnowFlower/SnowFlower_user_reference.png, front view, measured by
    WorkFiles/SnowFlower/v4/sword_ref/sw_ref_profile.py (per-row silhouette, lum<0.93 or sat>0.06)
    at 1.04257 mm/px (overall length 1256.3 mm, pommel top row 10 -> tip row 1215, kept from
    revision 3 because the sheet has no scale; the user has not confirmed it).
    z_model = (sheet_row - 10) * 1.04257 - 216.3
"""
from __future__ import annotations

import math

import numpy as np

MM_PER_PX = 1256.3 / 1205.0
OVERALL_MM = 1256.3
Z_POMMEL_TOP = -216.3
Z_TIP = OVERALL_MM + Z_POMMEL_TOP          # 1040.0


def z_of_row(row: float) -> float:
    return (row - 10.0) * MM_PER_PX + Z_POMMEL_TOP


# --------------------------------------------------------------------------- blade
Z_BLADE_ROOT = 96.0      # hidden inside the guard hub
Z_BLADE_SEAT = 104.0     # hub bottom face (the blade leaves the guard body here)
Z_PENDANT_TIP = 128.5    # lowest point of the front/back pendant leaves = sheath mouth plane
BLADE_LEN = Z_TIP - Z_BLADE_SEAT

#: sheet spine line (the straight back of the blade, measured x = +22.4 mm from the grip axis,
#: rows 380-660) and the sheet's measured sweep of 18.8 mm at the tip, starting at z ~680.
SPINE_X0 = 22.4
SHEET_SWEEP_MM = 18.8
#: DESIGN DECISION (documented in SWORD_V4_REPORT.md): the v4 spine sweeps HALF of the sheet's
#: 18.8 mm so that the straight reference sheath can hold the blade with a small (~3-4 mm/side)
#: widening of its lower body. Shape and start of the sweep follow the sheet exactly.
SWEEP_SCALE = 0.5
SWEEP_MM = SHEET_SWEEP_MM * SWEEP_SCALE
SWEEP_Z0 = 680.0
SWEEP_POWER = 1.9

#: blade width (spine to edge) along z, from the sheet front view (smoothed; the top capped at
#: 53.5 mm because the sheet rows under the pendant leaves include the leaves).
WIDTH_TABLE = [(Z_BLADE_ROOT, 53.5), (126.0, 53.5), (200.0, 52.0), (300.0, 50.0), (400.0, 48.0),
               (500.0, 45.9), (600.0, 43.8), (700.0, 42.2), (780.0, 40.8), (830.0, 39.0),
               (880.0, 36.4), (920.0, 33.2), (960.0, 27.0), (990.0, 21.5), (1010.0, 16.5),
               (1025.0, 10.5), (1035.0, 5.0), (Z_TIP, 0.0)]

#: blade thickness at the spine: 6.2 mm at the seat to 2.3 mm at 92 %, closing to the point
#: (revision 3's steel: 6 -> 2 mm; the sheet's side view (23 mm) is not credible).
T_SEAT = 6.2
T_LOW = 2.3


def blade_t(z):
    return np.clip((np.asarray(z, float) - Z_BLADE_SEAT) / BLADE_LEN, 0.0, 1.0)


def spine_x(z):
    z = np.asarray(z, float)
    tau = np.clip((z - SWEEP_Z0) / (Z_TIP - SWEEP_Z0), 0.0, 1.0)
    return SPINE_X0 + SWEEP_MM * tau ** SWEEP_POWER


def width(z):
    zs, ws = zip(*WIDTH_TABLE)
    return np.interp(np.asarray(z, float), zs, ws)


def edge_x(z):
    return spine_x(z) - width(z)


def thickness(z):
    t = blade_t(z)
    base = T_SEAT - (T_SEAT - T_LOW) * np.minimum(t, 0.92) / 0.92
    tipclose = 1.0 - 0.55 * np.clip((t - 0.92) / 0.08, 0.0, 1.0) ** 1.5
    return base * tipclose


#: cross-section, lateral s from the spine (0) to the edge (1) -> half-thickness as a fraction
#: of the spine thickness T. Sheet front view: a WIDE polished band on the spine side
#: (s 0.02-0.28), the recessed dark channel that holds the relief (s 0.30-0.78) and a narrow
#: bright land + edge bevel (s 0.80-1.0).
SECTION = [  # (s, half-thickness / T, region)
    (0.000, 0.40, "spine"), (0.012, 0.50, "spine"), (0.020, 0.50, "bevel"),
    (0.150, 0.485, "bevel"), (0.280, 0.465, "bevel"), (0.300, 0.36, "channel"),
    (0.420, 0.345, "channel"), (0.540, 0.34, "channel"), (0.660, 0.345, "channel"),
    (0.780, 0.36, "channel"), (0.800, 0.43, "land"), (0.860, 0.40, "land"),
    (0.930, 0.19, "edge"), (1.000, 0.02, "edge")]
CHANNEL_S = (0.30, 0.78)
CHANNEL_FLOOR = 0.34


def section_half(s, T):
    ss, hs, _ = zip(*SECTION)
    return np.interp(s, ss, hs) * T


def blade_point(z, s, side):
    """Surface point of the steel at height z, lateral fraction s (0 spine..1 edge), side -1 front / +1 back."""
    x = spine_x(z) - s * width(z)
    return float(x), float(side * section_half(s, thickness(z))), float(z)


# --------------------------------------------------------------------------- hilt
Z_COLLAR_BOT = 44.0
Z_COLLAR_TOP = 62.0
Z_GRIP_TOP = 46.0            # wrap runs under the collar
Z_GRIP_BOT = -183.3          # top of the pommel ring
GRIP_A = (17.0, 20.5)        # half-width in X at the pommel end -> at the collar (sheet 34 -> 41 mm)
GRIP_B = (15.75, 18.0)       # half-depth in Y (sheet side view 31.5 -> 36 mm, audit 33 -> 40)
WRAP_THICK = 1.3             # cord height over the core
WRAP_TURNS = 10.5            # ~10-11 diamond crossings visible from the front (sheet / audit)

POMMEL_R = 21.0              # sheet 42-44 mm across the bezel
Z_POMMEL_RING = (-189.3, -183.3)
Z_POMMEL_BODY = (Z_POMMEL_TOP, -189.3)

# --------------------------------------------------------------------------- guard
GUARD_HALF_SPAN = 58.0       # sheet 113-115 px at rows 294-303 -> 118-120 mm incl. rim halo
GUARD_Z = (56.0, 112.0)      # hub
GUARD_BLOSSOM_Z = 83.0
GUARD_BLOSSOM_R = 18.5       # ~37 mm across: the sheet's guard blossom spans ~0.30 of the guard
GUARD_DEPTH_HALF = 30.0      # side view 57-66 mm at the wing line

# --------------------------------------------------------------------------- sockets (model frame, mm)
SOCKETS = {
    "Grip": (0.0, 0.0, 0.0),
    "OffHand": (0.0, 0.0, -95.0),
    "BladeBase": (None, 0.0, Z_PENDANT_TIP),   # x filled with the blade centre line at that z
    "BladeTip": (None, 0.0, Z_TIP),
}


def blade_centre_x(z):
    return float(spine_x(z) - 0.5 * width(z))


def socket_positions():
    out = {}
    for name, (x, y, z) in SOCKETS.items():
        if x is None:
            x = float(spine_x(z)) if name == "BladeTip" else blade_centre_x(z)
        out[name] = (x, y, z)
    return out


# --------------------------------------------------------------------------- textures
STEEL_MAP = 4096
WRAP_MAP = 2048
PAD_PX = 16

LOD_SCREEN_SIZES = (1.0, 0.5, 0.25)
