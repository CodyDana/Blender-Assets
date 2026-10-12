"""The magazine (spec magazine_body, magazine_floor_plate; ruling RP10, R30), built with gunlib.parts.mag_box in the
mag frame and placed by the spec's frames.mag.

Real pattern (moulded polymer, straight double stack): one closed housing shell (outer rings, the top rim, the feed
lips turned in over the follower, the cavity), two parallel recessed channels per side crossed by flush ties (the
ladder, 1.0 deep), the raised front spine rib (its crest carries the mould's parting line) below the well, a plain
rear spine with the catch notch (square bearing face on top, the paddle's nose sits under it, Z -39.86 seated), the
follower seen between the lips, the slide-on floor plate (proud lip, the locking tab's dia 8 hole in its bottom face).
"""
from __future__ import annotations

import numpy as np

from gunlib.parts import mag_box as MB

from smg_common import dims, D as SPECD
from . import MAGS

MAGD = dims("magazine_body")
FP = dims("magazine_floor_plate")
_mf = SPECD["frames"]["mag"]
M4 = MB.placement(_mf["Mag_in_M"], _mf["z_axis_in_M"], _mf["x_axis_in_M"])
MAG_O = np.array(_mf["Mag_in_M"], float)
MAG_Z = np.array(_mf["z_axis_in_M"], float)
MAG_X = np.array(_mf["x_axis_in_M"], float)

LENGTH = float(MAGD["foreaft"])              # 42.2
THICK = float(MAGD["thickness"])             # 27.0
WALL = 2.6                                    # notch depth 2.5 leaves 0.1 (gunlib check)
Z_TOP = float(MAGD["top_along_axis"])        # 58.07
PLATE_H = float(FP["height"])                # 6.8
FOLLOWER_DEPTH = 1.0                          # under the lips' underside (gunlib default 6.0)


def _trace_floor():
    """The traced magazine's lowest point along the mag axis (LEFT panel): the floor plate's bottom. The spec's
    floor_along_axis (-160.57) sits 2.3 below the traced plate and below box_M's Z -230 (declared; the trace decides)."""
    import smg_geom as SG
    r = SG.part_ring("magazine", 0.3)
    O, Z = MAG_O[[0, 2]], MAG_Z[[0, 2]]
    return float(np.round(((r - O) @ Z).min(), 2))


Z_FLOOR = _trace_floor()                     # ~ -158.3
Z_BOT = Z_FLOOR + PLATE_H                    # the housing's bottom (the plate below it)


def z_local(Z_M, x_local):
    """Mag-frame z of a point on a face at x_local whose gun Z is Z_M (Y = 0)."""
    return (Z_M - MAG_O[2] - x_local * MAG_X[2]) / MAG_Z[2]


def build_all():
    lad = MAGD["ladder"]
    cw, rib = float(lad["channel_width"]), float(lad["rib_between"])
    # the two channels per side, centred fore-aft: [-(rib/2 + cw), -rib/2] and [rib/2, rib/2 + cw]
    z0 = z_local(lad["channel_bottom_Z"], 0.0)
    z1 = z_local(lad["channel_top_Z"], 0.0)
    ties = [z_local(t, 0.0) for t in lad["tie_Z"]]
    notch_top = z_local(MAGD["catch_notch"]["Z_seated"], -LENGTH / 2.0)
    nt = MAGD["catch_notch"]
    # (W4 review fixes, craft 2.14) the lips rolled (outer top edge R 1.2, a 0.9 vertical tip face, so they read folded
    # inward, not a flat rim round a trapezoid) and the follower raised to 1.0 under the lips' underside (3.0 under the
    # lip tips; was 6.0 / 8.0: lost in the black cavity in mag_top_3x)
    lips = {"opening": 10.0, "x_front": LENGTH / 2.0 - WALL - 8.0, "x_rear": -LENGTH / 2.0, "height": 2.0,
            "flare": 3.0, "roll": 1.2, "roll_seg": 3, "tip": 0.9}
    parts, rec = MB.magazine(LENGTH, THICK, Z_BOT, Z_TOP, wall=WALL, r_front=MAGD["corner_R"]["front"],
                             r_rear=MAGD["corner_R"]["rear"], lips=lips,
                             notch={"z_top": notch_top, "width": nt["size"][0], "height": nt["size"][1],
                                    "depth": nt["depth"]},
                             ladder=None,
                             spine={"z0": Z_BOT + 1.5, "z1": -1.0, "width": MAGD["front_spine_rib"]["width"],
                                    "proud": MAGD["front_spine_rib"]["proud"]},
                             plate={"thickness": PLATE_H, "overhang": 1.2, "tab_hole": (-4.0, 0.0,
                                                                                         FP["locking_tab_hole_dia"])},
                             follower_depth=FOLLOWER_DEPTH, M4=M4, slot=MAGS, prefix="magazine")
    body, fol, plate = parts
    for x0, x1 in ((-rib / 2.0 - cw, -rib / 2.0), (rib / 2.0, rib / 2.0 + cw)):
        # (W4, G3o) the recess corners at 5 segments (18 deg, chord error 0.012 mm; were 3: 30 deg, 0.047 mm)
        for c in MB.ladder_cutters(x0, x1, z0, z1, float(lad["depth"]), THICK / 2.0, ties, tie_w=3.0, r=1.0, seg=5):
            body.cutters.append(c.transformed(M4))
    fol.name = "magazine_follower"
    plate.name = "magazine_floor_plate"
    return [body, fol, plate]
