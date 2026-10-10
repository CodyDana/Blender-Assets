"""Stage 1 blockout: the primary volumes straight from the traced LEFT part outlines at the ruled scale (frame M, mm).

Each traced part ring (Douglas-Peucker 0.35 mm) is extruded across its spec width (TOP authority: the receiver body
and fore-end widths, the stock frame / pad widths, the magwell, guard, grip, end block); round parts are cylinders;
the magazine is the traced magazine ring at the spec thickness; the charging knob is a ball on its neck. The flip
sights are the form stage's own generators (gate B4 runs on the blockout). No bevels, no booleans: this stage proves
the volumes and the scale (gate L1).
"""
from __future__ import annotations

import numpy as np

from gunlib import geo2d as G
from gunlib import mesh as MS
from smg_common import dims, box, D as SPECD, trace
import smg_geom as SG

# trace part key -> (object name, Y range)
WIDTH = {
    "receiver_upper": ("upper_receiver", (SG.Y_R, SG.Y_L)),
    "handguard_area": ("upper_fore_end", (SG.F_R, SG.F_L)),
    "receiver_lower": ("lower_receiver", (SG.Y_R, SG.Y_L)),
    "mag_well": ("magwell", tuple(box("magwell")["Y"])),
    "trigger_guard": ("trigger_guard", tuple(box("trigger_guard")["Y"])),
    "grip": ("pistol_grip", tuple(box("pistol_grip")["Y"])),
    "hinge_block": ("end_block", tuple(box("end_block")["Y"])),
    "stock_hinge_knuckle": ("stock_hinge", (-26.0, float(box("stock_hinge")["Y"][1]))),
    "stock_neck": ("stock_neck", tuple(box("stock_frame")["Y"])),
    "stock_top_strut": ("stock_top_strut", tuple(box("stock_frame")["Y"])),
    "stock_lower_strut": ("stock_lower_strut", tuple(box("stock_frame")["Y"])),
    "stock_web": ("stock_web", tuple(box("stock_frame")["Y"])),
    "stock_rear_upright": ("stock_rear_upright", tuple(box("stock_frame")["Y"])),
    "butt_pad": ("butt_pad", tuple(box("butt_pad")["Y"])),
    "top_rail": ("top_rail", tuple(box("top_rail")["Y"])),
    "lower_rail": ("lower_rail", (-10.6, 10.6)),
    "trigger": ("trigger", tuple(box("trigger")["Y"])),
    "mag_release": ("mag_release", tuple(box("mag_release")["Y"])),
    "magazine": ("magazine", tuple(box("magazine_body")["Y"])),
}


def parts(tol=0.35):
    out = {}
    j = trace("LEFT")
    for key, (name, (y0, y1)) in WIDTH.items():
        rr = [r for r in j["parts"][key] if r["kind"] == "outer" and abs(r["area_px"]) > 4]
        holes = [np.array(r["mm"], float) for r in j["parts"][key] if r["kind"] == "hole"]
        m = MS.Mesh()
        for r in rr:
            P = G.ccw(G.dp_simplify(np.array(r["mm"], float), tol))
            if len(P) >= 3:
                m.extend(MS.prism(P, y0, y1, "XZ"))
        out[name] = m
    bz = SPECD["key_dimensions"]["bore_Z_M"]
    b = dims("barrel")
    out["barrel"] = MS.cylinder((b["exposed_X"][0] - 6.0, 0, bz), (b["neck"]["X"][1], 0, bz), b["collar_ring"]["dia"] / 2,
                                32)
    md = dims("muzzle_device")
    out["muzzle_device"] = MS.cylinder((md["rear_collar_X"][0], 0, bz), (md["cage_X"][1], 0, bz), md["od"] / 2, 32)
    ch = dims("charging_handle")
    kx, kz = ch["knob_centre_XZ"]
    out["charging_handle"] = MS.ellipsoid((kx, ch["knob_centre_Y"], kz), ch["knob_dia"] / 2, ch["knob_dia"] / 2,
                                          ch["knob_dia"] / 2, 32, 16).extend(
        MS.cylinder((kx, SG.Y_L - 1.0, kz), (kx, ch["knob_centre_Y"], kz), ch["neck_dia"] / 2, 24))
    sd = dims("selector")
    sx, sz = sd["pivot_XZ"]
    out["selector"] = MS.cylinder((sx, SG.Y_R - 2.5, sz), (sx, SG.Y_L + 2.5, sz), sd["hub_dia"] / 2, 32)
    return out
