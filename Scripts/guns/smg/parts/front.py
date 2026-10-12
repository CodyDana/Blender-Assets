"""Barrel and muzzle device (spec barrel, muzzle_device; ruling RP16).

Real pattern (phosphated steel, lathe work, M-chamfer):
- the barrel: hidden length from the breech (X 455.6) through the trunnion and the front wall's bore (OD 16), the
  collar ring (dia 22.5) seated 3 mm deep in the receiver face's counterbore (dia 23.1), the neck (dia 20.4) out to the
  device seat (X 583.4), a thread tenon inside the device's rear collar, the recessed crown (X 596.9) inside the cage;
  the bore (dia 11.4) runs through;
- the muzzle device: a rear collar (dia 23.1) with its drawn groove ring and two wrench flats on the underside, a
  slotted cage with six through-slots at 60 deg (one centred on each side, so the side views show three and the top
  two), the solid front rim with its outer and bore chamfers, open front.
Every revolved solid is a closed (t, r) loop about the bore axis (no boolean for the bore: no cap slivers).
"""
from __future__ import annotations

import math

import numpy as np

from gunlib.mesh import Mesh, prism
from gunlib.parts import PartDef
from gunlib.parts.sights_flip import revolve_loop

from smg_common import dims, D as SPECD, BORE_Z
from . import METAL, GAP

BA = dims("barrel")
MD = dims("muzzle_device")
UP = dims("upper_receiver")
X_FF = float(UP["front_face_X"])                     # 563.3
AXIS_O = (0.0, 0.0, BORE_Z)
AXIS = (1.0, 0.0, 0.0)
CB_DEPTH = 3.0                                      # the receiver face's counterbore depth (receiver.py)
R_BORE = BA["bore_dia"] / 2.0                       # 5.7
R_HID = BA["hidden_od"] / 2.0                       # 8.0
R_COL = BA["collar_ring"]["dia"] / 2.0              # 11.25
R_NECK = BA["neck"]["dia"] / 2.0                    # 10.2
R_TEN = 7.9                                         # the thread tenon inside the device's rear collar (hidden)
X_SEAT = float(MD["rear_collar_X"][0])              # 583.4 (the device's rear face = the neck's shoulder)
X_CROWN = float(BA["crown_X"])                      # 596.9
R_DEV = MD["od"] / 2.0                              # 11.55
R_DEV_IN = MD["inner_dia"] / 2.0                    # 6.75
X_MUZ = float(SPECD["parts"][[p["id"] for p in SPECD["parts"]].index("muzzle_device")]["box_M"]["X"][1])   # 625.0
NSEG = 64
# the barrel at 64 sides (W4 tried the plan's 48 for budget; kept 64, the W3 geometry)
NSEG_BARREL = 64


def barrel():
    """One closed loop: outside rear -> front, then the bore back (breech and crown chamfered)."""
    xb = float(BA["breech_X"])
    xc0 = X_FF - CB_DEPTH + GAP                      # the collar's rear face sits on the counterbore floor
    xc1 = float(BA["collar_ring"]["X"][1])           # 572.8
    c = 0.4
    # (W1b fix round, L2 per part) the face flange both side panels and the 3/4 draw against the receiver face: a ring
    # dia 26.4 over the first 3.6 mm in front of the face (the collar ring seated in the counterbore behind it)
    xf0, xf1, R_FL = X_FF + GAP, X_FF + 3.6, 13.2
    from gunlib import lod as _lod
    if _lod.LEVEL >= 2:
        xb = xc0 - 4.0       # (W3) LOD2+: the barrel's 100 mm inside the receiver is never seen (hidden surface removed)
    # (W4 review fixes) the chamber mouth: with the bolt back the port shows the breech face's upper half (the bore
    # centre Z 1.87 is just under the port's lower edge, Z 2.3); the 0.6 chamfer is kept (1.0 was tried: its sloped
    # faces under the barrel's cylinder chart pulled class D's density P5 under B9's 0.85 x median) and painted as the
    # rounds' rubbed bright cone with a bare rim (smg_paint). The feed ramp sits under the bore, below the port's edge:
    # never seen, not modelled
    loop = [(xb, R_BORE + 0.6), (xb, R_HID - c), (xb + c, R_HID),
            (xc0, R_HID), (xc0, R_COL - c), (xc0 + c, R_COL), (xf0, R_COL), (xf0, R_FL - c), (xf0 + c, R_FL),
            (xf1 - c, R_FL), (xf1, R_FL - c), (xf1, R_COL), (xc1 - c, R_COL), (xc1, R_COL - c),
            (xc1, R_NECK), (X_SEAT - GAP - 0.3, R_NECK), (X_SEAT - GAP, R_NECK - 0.3),
            (X_SEAT - GAP, R_TEN), (X_CROWN - 0.3, R_TEN), (X_CROWN, R_TEN - 0.3),
            (X_CROWN, R_BORE + 0.8), (X_CROWN - 0.8, R_BORE),          # the recessed crown's 45 deg bore chamfer
            (xb + 0.6, R_BORE)]                                      # breech chamfer (the feed ramp is not modelled)
    m = revolve_loop([(t, r) for t, r in loop], AXIS_O, AXIS, NSEG_BARREL)
    return PartDef("barrel", [m], bone="body", cls="M-chamfer", slot=METAL, recipe=[],
                   joint={"type": "fixed", "parent": "upper_receiver", "pin": "transverse roll pin (hidden)"},
                   spec_id="barrel")


def rot_about_bore(angle_deg):
    """4x4: rotation about the bore axis taking +Z toward +Y by angle_deg (0 = top, 90 = gun left, 180 = bottom)."""
    t = math.radians(angle_deg)
    R = np.eye(4)
    R[1, 1], R[1, 2], R[2, 1], R[2, 2] = math.cos(t), math.sin(t), -math.sin(t), math.cos(t)
    T0, T1 = np.eye(4), np.eye(4)
    T0[2, 3], T1[2, 3] = -BORE_Z, BORE_Z
    return T1 @ R @ T0


def _slot_cutter(angle_deg, x0, x1, w):
    """A through-slot with round ends, centred at angle_deg about the bore axis, from x0 to x1."""
    r = w / 2.0
    a = np.radians(np.linspace(-90.0, 90.0, 9))
    st = np.vstack([np.c_[x1 - r + r * np.cos(a), r * np.sin(a)],
                    np.c_[x0 + r - r * np.cos(a), -r * np.sin(a)]])
    m = prism(st, BORE_Z + R_DEV_IN - 1.5, BORE_Z + R_DEV + 1.0, "XY")     # radial through the wall at the top
    return m.transformed(rot_about_bore(angle_deg))


def muzzle_device():
    sl = MD["slots"]
    x0c, x1c = float(MD["rear_collar_X"][0]), float(MD["rear_collar_X"][1])     # 583.4, 590.8
    g = float(MD["groove_ring_width"])
    gx1 = x1c - 0.9                                   # the drawn groove ring just behind the cage (0.5 deep)
    gx0 = gx1 - g
    c_out = float(MD["front_chamfer_out"])
    c_in = float(MD["bore_chamfer"])
    xt = X_CROWN + 0.9                                # the threaded counterbore's end, 0.9 past the crown (clear of the slots' rear rounds)
    loop = [(x0c, R_TEN + 0.1), (x0c, R_DEV - 0.4), (x0c + 0.4, R_DEV), (gx0 - 0.25, R_DEV), (gx0, R_DEV - 0.25),
            (gx0 + 0.25, R_DEV - 0.5), (gx1 - 0.25, R_DEV - 0.5), (gx1, R_DEV - 0.25), (gx1 + 0.25, R_DEV),
            (X_MUZ - c_out, R_DEV), (X_MUZ, R_DEV - c_out), (X_MUZ, R_DEV_IN + c_in), (X_MUZ - c_in, R_DEV_IN),
            (xt, R_DEV_IN), (xt, R_TEN + 0.1)]      # thread clearance 0.1
    m = revolve_loop(loop, AXIS_O, AXIS, NSEG)
    # six slots at 60 deg, one centred on each side (+-Y): 30, 90, 150, 210, 270, 330 deg from +Z
    front_rim = float(MD["front_rim_length"])
    sx1 = X_MUZ - front_rim
    sx0 = sx1 - float(sl["length"])
    cuts = [_slot_cutter(a, sx0, sx1, float(sl["width"])) for a in (30.0, 90.0, 150.0, 210.0, 270.0, 330.0)]
    from gunlib import lod as _lod
    if _lod.LEVEL >= 2:
        cuts = []        # (W3) LOD2+: the slots are 3 mm-class, 0.6 px at the LOD2 switch (the painted soot stays)
    # two wrench flats on the collar's underside (0.5 deep, at +-35 deg off -Z), behind the groove
    flats = []
    for a in (180.0 - 35.0, 180.0 + 35.0):
        d = R_DEV - 0.5
        blk = prism(np.array([[x0c - 1.0, -6.0], [gx0 - 0.6, -6.0], [gx0 - 0.6, 6.0], [x0c - 1.0, 6.0]]),
                    BORE_Z + d, BORE_Z + d + 5.0, "XY")
        flats.append(blk.transformed(rot_about_bore(a)))
    return PartDef("muzzle_device", [m], bone="muzzle_device", cls="M-chamfer", slot=METAL,
                   cutters=cuts + flats, recipe=[(0.3, 1, 50.0)],
                   joint={"type": "fixed", "parent": "barrel"}, spec_id="muzzle_device")


def build_all():
    return [barrel(), muzzle_device()]
