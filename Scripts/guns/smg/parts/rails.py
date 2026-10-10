"""Top rail, lower rail and the rail screws (spec top_rail / lower_rail, RP14; gunlib.parts.rail_1913, true 1913 profile).

Top rail: X from the D-frame's rear (the end block's TOP-drawn D rim is the rail's machined rear end: the side view
shows the rail band from the end block's top on; spec end_block.dims.top_frame) to the front, 26 slot positions at
10.01 from slot 0 (the rear sight's lug) to slot 25 (the front sight's lug); cut only where the sheet draws teeth plus
the two lug slots; relief flats at slot-floor level where the sheet draws flats (rear plain zone, front relief); a base
flange (TOP band) under the dovetail. Two low button-head screws (dia 4.8 heads, 0.3 under the slot floor) in two slot
floors (check fix C13). Lower rail: 6 slots centred, facing down, two screws.
"""
from __future__ import annotations

import numpy as np

from gunlib.mesh import Mesh, cylinder, box
from gunlib.parts import PartDef
from gunlib.parts import rail_1913 as RL
from gunlib.parts import hardware as HW

from smg_common import dims, box as sbox
from . import METAL, GAP

TR = dims("top_rail")
LR = dims("lower_rail")
EB = dims("end_block")
PITCH = RL.PITCH


def top_rail_geometry():
    """(x0, M4, layout kwargs, record) of the top rail."""
    x0 = float(EB["top_frame"]["X"][0])                 # 256.8: the D rim's rear end
    z0 = float(TR["underside_Z"])
    H = round(float(TR["top_Z"]) - z0, 3)
    s0 = float(TR["lattice_slot0_X"])
    cut = list(TR["cut_slot_indices"])
    n = max(cut) + 1
    x1 = float(sbox("top_rail")["X"][1])
    pad_rear = s0 - RL.SLOT_W / 2.0 - x0
    pad_front = x1 - (s0 + (n - 1) * PITCH + RL.SLOT_W / 2.0)
    flats = [(0.0, float(TR["plain_zones"]["rear_X"][1]) - x0),
             (float(TR["plain_zones"]["front_relief_X"][0]) - x0, float(TR["plain_zones"]["front_relief_X"][1]) - x0)]
    bw = float(TR["base_flange"]["width"])
    sd = round(H - 3.0, 3)                               # 3.0 flange: the 1913 neck (5.77 under the top) must fit above
    kw = dict(n_slots=n, pad_rear=pad_rear, pad_front=pad_front, height=H, cut=cut, flats=flats, base_width=bw,
              shoulder_depth=sd)
    M4 = RL.placement((x0, 0.0, z0))
    return x0, z0, H, M4, kw


def lower_rail_geometry():
    x0, x1 = (float(v) for v in sbox("lower_rail")["X"])
    ztop = float(LR["top_seam_Z"])                       # mounting face (the fore-end's underside)
    H = round(ztop - float(LR["bottom_Z"]), 3)
    c = [float(v) for v in LR["slot_centres_X"]]
    n = len(c)
    pad_rear = c[0] - RL.SLOT_W / 2.0 - x0
    pad_front = x1 - (c[-1] + RL.SLOT_W / 2.0)
    kw = dict(n_slots=n, pad_rear=pad_rear, pad_front=pad_front, height=H)
    M4 = RL.placement((x0, 0.0, ztop - GAP), z_axis=(0.0, 0.0, -1.0))
    return M4, kw


def top_rail():
    x0, z0, H, M4, kw = top_rail_geometry()
    # mounting face GAP above the receiver top / end block (butt joint)
    M4 = RL.placement((x0, 0.0, z0 + GAP))
    p, rec = RL.part("top_rail", M4, slot=METAL, chamfer_mm=0.3, spec_id="top_rail",
                     joint={"type": "butt", "parent": "upper_receiver", "gap_mm": [0.01, 0.05]}, **kw)
    # the D-frame pocket in the rear plain zone (spec end_block.top_frame window, 2.0 deep) and the screw counterbores
    tf = EB["top_frame"]
    floor = z0 + GAP + rec["floor_z"]
    wx, wy = tf["window_X"], tf["window_Y"]
    from gunlib.geo2d import rounded_rect
    from gunlib.mesh import prism
    pocket = prism(rounded_rect(wx[0], wx[1], wy[0], wy[1], 2.0, 4), floor - 2.0, floor + 1.0, "XY")
    cuts = [pocket]
    for k in TR["screws"]["in_slots"]:
        xc = float(TR["lattice_slot0_X"]) + k * PITCH
        cuts.append(cylinder((xc, 0, floor - 1.75), (xc, 0, floor + 1.0), 2.55, 32))       # counterbore dia 5.1
        cuts.append(cylinder((xc, 0, z0 - 1.0), (xc, 0, floor - 1.6), 1.35, 24))           # the screw's hole
    # the front end's chamfer as both side panels draw it (W1b fix round): from the top at X 556.0 down to Z 39.3 at
    # the end face (a machined end bevel; the last slot's front wall ends at 548.6)
    x1 = float(sbox("top_rail")["X"][1])
    zt = z0 + GAP + H
    cuts.append(prism(np.array([[556.0, zt + 2.0], [556.0, zt], [x1 + 0.05, 39.3], [x1 + 2.0, 39.3], [x1 + 2.0, zt + 2.0]]),
                      -20.0, 20.0, "XZ"))
    p.post_cutters = cuts
    p.post_recipe = []
    # the D's round rear end in plan (TOP: "round end to the rear"): the rail's rear corners rounded R 8 in plan
    from gunlib.geo2d import arc
    hw = float(TR["base_flange"]["width"]) / 2.0 + 1.0
    R = 8.0
    xa = x0 + R
    plan = np.vstack([arc(xa, -hw + R, R, 270.0, 180.0, 9), arc(xa, hw - R, R, 180.0, 90.0, 9),
                      [[x0 + 400.0, hw], [x0 + 400.0, -hw]]])
    p.section_intersect_pre = [prism(plan, z0 - 5.0, z0 + H + 5.0, "XY")]
    return [p], rec


def lower_rail():
    M4, kw = lower_rail_geometry()
    p, rec = RL.part("lower_rail", M4, slot=METAL, chamfer_mm=0.3, spec_id="lower_rail",
                     joint={"type": "butt", "parent": "upper_receiver", "gap_mm": [0.01, 0.05]}, **kw)
    return [p], rec


def rail_screws():
    """Low button-head cap screws (heads dia 4.8, 0.3 under the slot floor) in the top rail's slots 4 and 20 and the
    lower rail's slots 1 and 4: ISO 7380 proportions on a 2.5 mm screw (head 4.75, height 1.38, socket 1.5)."""
    x0, z0, H, M4, kw = top_rail_geometry()
    floor = z0 + GAP + H - RL.D_VBOT
    m = Mesh()
    d = 2.5
    for k in TR["screws"]["in_slots"]:
        xc = float(TR["lattice_slot0_X"]) + k * PITCH
        head = HW.button_head(d, shank_len=4.0, nseg=36)
        m.extend(HW.place(head, (xc, 0.0, floor - 0.3 - 0.55 * d - 0.02 - 0.0), (0, 0, 1)).translated((0, 0, 0)))
    M4l, kwl = lower_rail_geometry()
    c = [float(v) for v in LR["slot_centres_X"]]
    Hl = kwl["height"]
    floor_l = float(LR["top_seam_Z"]) - GAP - (Hl - RL.D_VBOT)
    for k in (1, len(c) - 2):
        head = HW.button_head(d, shank_len=4.0, nseg=36)
        m.extend(HW.place(head, (c[k], 0.0, floor_l + 0.3 + 0.55 * d + 0.02), (0, 0, -1)))
    return [PartDef("rail_screws", [m], bone="body", cls="M-chamfer", slot=METAL, recipe=[],
                    joint={"type": "fixed", "parent": "top_rail"}, spec_id="top_rail")]
