"""SMG01 B3 moving groups (gunlib.drivers.b3; pivots in frame B, mm). SMG_BUILD_PLAN 14.2 B3:

  bolt              -X 0..67.9 (blowback: the charging handle stays forward, non-reciprocating)
  charging          handle + slide + bolt -X 0..67.9 (the slide's hook pushes the bolt's lug)
  charging_lock     the lever 0..+15 deg about the slide's roll pin at full travel (the slide does not rotate)
  trigger           0..+13 deg about Y at the axle
  selector          -63.4 (SAFE) .. +45 (AUTO) about Y, both levers
  mag_release       0..-11 deg about Y at its pin (the magazine seated)
  stock_button      the latch button + bolt -Y 0..2.0
  stock_fold        0..180 deg about Z at the hinge axle, the button pressed (pre-pose -2.0 Y); 0.25 deg steps that
                    each prove >= r_max x 0.25 deg / 2, fine 0.02 deg steps in the latch zone (0..2 deg) and the snap
                    zone (177..180 deg); declared allowance: the port catch's lip over the lug's barb (<= 1.5 mm, last
                    3 deg)
  sight_rear        0..+90 deg about Y at its pin (folds forward); detent allowance <= 0.3 mm in the last 2 deg
  sight_front       0..-90 deg about Y at its pin (folds rearward); the same allowance
"""
from __future__ import annotations

import numpy as np

from smg_common import GRIP, dims
from gunlib.parts import hinge as HG
from gunlib.parts import sights_flip as SF

CH = dims("charging_handle")
BO = dims("bolt")
TRG = dims("trigger")
SE = dims("selector")
MR = dims("mag_release")
SH = dims("stock_hinge")
SR = dims("sight_rear")
SFR = dims("sight_front")


def B(p):
    return np.asarray(p, float) - np.asarray(GRIP, float)


def T(dx=0.0, dy=0.0, dz=0.0):
    M = np.eye(4)
    M[:3, 3] = (dx, dy, dz)
    return M


STOCK_PARTS = ["stock_frame", "stock_latch_button", "stock_latch_bolt", "butt_pad"]


def groups(G, rec, cfg):
    travel = float(CH["travel_minus_X"])
    out = {}
    out["bolt"] = {"parts": ["bolt"], "kind": "slide", "axis": [-1.0, 0.0, 0.0], "range": [0.0, float(BO["travel"])],
                   "row": "sliding"}
    out["charging"] = {"parts": ["charging_handle", "charging_slide", "bolt"], "kind": "slide",
                       "axis": [-1.0, 0.0, 0.0], "range": [0.0, travel], "row": "sliding"}
    pin = CH["lock_axis"]["YZ"]
    back = T(-travel)
    out["charging_lock"] = {"parts": ["charging_handle"], "kind": "rot",
                            "pivot": B((480.0 - travel, pin[0], pin[1])), "axis": [1.0, 0.0, 0.0],
                            "range": [0.0, float(CH["lock_rotation_about_X_deg"][1])], "row": "hinge",
                            "pre": {"charging_handle": back, "charging_slide": back, "bolt": back}}
    tp = TRG["pivot_XZ"]
    out["trigger"] = {"parts": ["trigger"], "kind": "rot", "pivot": B((tp[0], 0.0, tp[1])), "axis": [0.0, 1.0, 0.0],
                      "range": [0.0, float(TRG["pull_rot_Y_deg"])], "row": "hinge"}
    sp = SE["pivot_XZ"]
    pos = SE["positions_rot_Y_deg_from_bind"]
    out["selector"] = {"parts": ["selector"], "kind": "rot", "pivot": B((sp[0], 0.0, sp[1])), "axis": [0.0, 1.0, 0.0],
                       "range": [float(pos["SAFE"]), float(pos["AUTO"])], "row": "hinge"}
    mp = MR["pivot_XZ"]
    out["mag_release"] = {"parts": ["mag_release"], "kind": "rot", "pivot": B((mp[0], 0.0, mp[1])),
                          "axis": [0.0, 1.0, 0.0], "range": [0.0, float(MR["release_rot_Y_deg"])], "row": "hinge"}
    from parts.stock import STROKE as stroke          # 2.5 (declared; spec 2.0: the shoulders need it)
    out["stock_button"] = {"parts": ["stock_latch_button", "stock_latch_bolt"], "kind": "slide",
                           "axis": [0.0, -1.0, 0.0], "range": [0.0, stroke], "row": "sliding"}
    pressed = T(dy=-stroke)
    ax = (float(SH["axis_X"]), float(SH["axis_Y"]), 0.0)
    out["stock_fold"] = HG.sweep_group(STOCK_PARTS, B(ax), (0.0, 0.0, 1.0), (0.0, float(SH["fold_rot_Z_deg"])),
                                       row="hinge", step=0.25, fine=[(0.0, 2.0, 0.02), (177.0, 180.0, 0.02)],
                                       allowances=[{"with": ["upper_receiver"], "window": [177.0, 180.0],
                                                    "max_depth_mm": 1.5,
                                                    "why": "the port catch's lip over the stock lug's barb (snap, "
                                                           "polymer flex)"}],
                                       coarse_proof=True)
    out["stock_fold"]["pre"] = {"stock_latch_button": pressed, "stock_latch_bolt": pressed}
    out["stock_fold"]["sample_mm"] = 1.0
    out["stock_fold"]["coarse_proof"] = "radius"
    for name, d, parts in (("sight_rear", SR, ["sight_rear_leaf"]), ("sight_front", SFR, ["sight_front_leaf"])):
        px, pz = d["pivot_XZ"]
        fold = float(d.get("fold_rotation_Y_deg"))
        out[name] = SF.fold_sweep_group(parts, B((px, 0.0, pz)), fold, with_parts=[f"{name}_base"])
    return out
