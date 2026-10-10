"""Upper and lower receiver mouldings, the grip cover and the bolt rails (spec upper_receiver, lower_receiver, magwell,
trigger_guard, pistol_grip, end_block, ejection_port_and_catch; rulings RP1-RP6, RP12, RP13, RP19-RP21; R30-R32).

Construction (glass-filled polymer, P-round class; side actions form the flat sides, so the side faces carry no draft,
the openings' walls do; craft study 2.1):
- the side silhouette is the trace's own (the LEFT gun_without_magazine outline, Douglas-Peucker 0.3 mm), split into the
  upper and the lower along the drawn seam (the horizontal seam, the lower's front tab, the V tongue, the magwell front
  face) with a 0.4 mm design seam (RP19);
- the plan widths are the spec's (TOP): the upper's body / fore-end with the 45 deg step and the chamfered front corners;
  the lower's full-width trigger housing and end block, the narrower magwell (R31) with its insertion flare band, the
  integral guard loop and the grip (a loft of rounded sections perpendicular to the grip axis, RP13);
- the moulded shoulder (a 0.6 mm set-in upper band at Z 12.25, both sides), R 1.4 outer edge rounds, 0.35 breaks on the
  opening lips, a 0.4 break on the seam edges;
- every opening is a real through-cut with its wall (vents, port, charging slot + lock notch, eyelet), its walls drafted
  1 deg (wider outside);
- the internals the moving parts touch (task rule): the shell cavity, the bolt rail seats, the charging slide's guide
  block (channel, hook slot, neck slot), the barrel trunnion and front wall bore, the magwell cavity (0.3 per side, the
  mouth flare), the catch window, the paddle slot and its clevis ears, the trigger slot, the selector shaft and trigger
  axle bores, the lower-rail pocket, the port catch with its hooked lip (the folded stock's lug snaps under it), the
  receiver-side hinge knuckles and the latch lug on the end block.
"""
from __future__ import annotations

import math

import numpy as np

from gunlib import geo2d as G
from gunlib.mesh import Mesh, box, cylinder, loft, prism
from gunlib.parts import mag_box as MB
from gunlib.parts import hardware as HW
from gunlib.parts import hinge as HG

import smg_geom as SG
from smg_common import dims, box as sbox, feature, D as SPECD, BORE_Z
from smg_parts import Ops
from . import FURN, METAL, GAP, Comp

UP = dims("upper_receiver")
LO = dims("lower_receiver")
MW = dims("magwell")
TG = dims("trigger_guard")
PG = dims("pistol_grip")
EB = dims("end_block")
EP = dims("ejection_port_and_catch")
CH = dims("charging_handle")
BO = dims("bolt")
BA = dims("barrel")
MR = dims("mag_release")
SE = dims("selector")
TRG = dims("trigger")
MAGD = dims("magazine_body")
LR = dims("lower_rail")
TR = dims("top_rail")
SH = dims("stock_hinge")

WALL = 3.2
Z_TOP = float(UP["top_under_rail_Z"])                   # 36.1 (the rail's underside)
Z_FB = float(LR["top_seam_Z"])                          # -27.5 (the fore-end bottom = the lower rail's mounting face)
X_LRF = float(sbox("lower_rail")["X"][1])               # 553.6
X_LR0 = float(sbox("lower_rail")["X"][0])               # 484.5
X_FF = float(UP["front_face_X"])                        # 563.3
X_RAIL0 = float(TR["rear_end_X"])                       # 256.8 (R32)
Z_LEDGE = 0.5 * sum(UP["side_ledge_step"]["Z"])         # 12.25
LEDGE = 0.6
SEAM = SG.seam_polyline()
H = SG.SEAM_GAP / 2.0
X_EBF = SG.END_BLOCK_FRONT_X
X_EBR = SG.END_BLOCK_REAR_X
Z_BODY_BOT = float(SG.L([(219.0, 241.5)])[0, 1])        # the trigger housing's bottom (guard top), ~-49.1
DRAFT = math.tan(math.radians(1.0))
_mf = SPECD["frames"]["mag"]
MAG_O, MAG_X, MAG_Z = (np.array(_mf[k], float) for k in ("Mag_in_M", "x_axis_in_M", "z_axis_in_M"))
MAG_Y = np.cross(MAG_Z, MAG_X)
EB_Y = tuple(sbox("end_block")["Y"])                    # (-29.6, 30.4)


def mag_M(xl, yl, zl):
    return MAG_O + xl * MAG_X + yl * MAG_Y + zl * MAG_Z


def mag_M4():
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = MAG_X, MAG_Y, MAG_Z, MAG_O
    return M


def wall_line_x(z):
    """The magwell rear wall's outer face (spec magwell.dims.rear_wall.outer_face_line_XZ)."""
    s = MW["rear_wall"]["outer_face_line_XZ"]
    k, c = [float(v) for v in s.split("(")[0].replace("X =", "").replace("Z +", "").split()]
    return k * z + c


def mag_rear_x(z):
    return wall_line_x(z) + MW["wall"] + 0.3


# ------------------------------------------------------------------------------------------------ regions (XZ)
def face_line():
    return SEAM[5], SEAM[7]                             # the magwell front face (upper / lower boundary at the front)


def region_upper():
    up = SG.offset_polyline(SEAM, +H)
    xi = SG.line_x_at_z(up[5], up[7], Z_FB)
    pts = [(X_EBF + H, Z_TOP), (X_EBF + H, float(up[0, 1]))] + [tuple(p) for p in up[1:6]]
    pts += [(xi, Z_FB), (X_LRF + GAP, Z_FB), (X_LRF + GAP, -60.0), (X_FF + 0.5, -60.0), (X_FF + 0.5, Z_TOP)]
    return SG.polygon_from(pts)


def region_lower():
    lo = SG.offset_polyline(SEAM, -H)
    pts = [(X_EBR + 0.2, 60.0), (X_RAIL0 - GAP, 60.0), (X_RAIL0 - GAP, Z_TOP), (X_EBF - H, Z_TOP),
           (X_EBF - H, float(lo[0, 1]))] + [tuple(p) for p in lo[1:]]
    pts += [(float(lo[-1, 0]) + 2.0, -130.0), (X_EBR + 0.2, -130.0)]
    return SG.polygon_from(pts)


def master_prism():
    return prism(SG.master_outer(0.45), -60.0, 60.0, "XZ")


def stadium_xz(x0, x1, zc, h, n=8):
    r = h / 2.0
    pts = list(G.arc(x1 - r, zc, r, -90.0, 90.0, n)) + list(G.arc(x0 + r, zc, r, 90.0, 270.0, n))
    return np.array(pts, float)


def wall_cut(outline_xz, y_face, inward, depth_in=None, draft=True):
    """A cutter through a side wall whose outer face is at y_face (inward = -1 for a +Y (left) face, +1 for a -Y
    (right) face): the opening's outline at the inner end, grown by the 1 deg draft at the outer face (wider outside),
    running 1 mm beyond the face."""
    d = WALL + 1.5 if depth_in is None else depth_in
    P = G.ccw(np.asarray(outline_xz, float))
    Po = G.offset(P, DRAFT * (d + 1.0)) if draft else P
    y_out = y_face - inward * 1.0
    y_in = y_face + inward * d
    r_out = np.c_[Po[:, 0], np.full(len(Po), y_out), Po[:, 1]]
    r_in = np.c_[P[:, 0], np.full(len(P), y_in), P[:, 1]]
    return loft([r_in, r_out]) if inward < 0 else loft([r_out, r_in])


def side_strip(chain, inset, z0, z1, x_ext=8.0):
    """A cutter that sets a side face in by ``inset`` over Z z0..z1: the side's plan chain (rear -> front, the face
    points) shifted inward by inset, back along the chain shifted outward by 6."""
    C = np.asarray(chain, float)
    s = np.sign(C[:, 1].mean())
    inner = C - np.array([0.0, s * inset])
    outer = C + np.array([0.0, s * 6.0])
    inner[0, 0] -= x_ext
    outer[0, 0] -= x_ext
    return prism(np.vstack([inner, outer[::-1]]), z0, z1, "XY")


# ------------------------------------------------------------------------------------------------ shared internals
def slide_geom():
    """The charging slide's box (M) at rest, its travel, the hook and the bolt's charging lug (spec charging_handle)."""
    sl = CH["slide"]
    return {"X": (449.0, 503.0), "Y": tuple(sl["Y"]), "Z": tuple(sl["Z"]), "travel": float(CH["travel_minus_X"]),
            "hook": {"X": (449.2, 452.5), "Y": (12.68, 14.8), "Z": (8.6, sl["Z"][0] + 0.5)},
            "lug": {"X": (444.0, 449.0), "Y": (BO["width"] / 2.0 - 0.5, 14.3), "Z": (8.9, 12.5)},
            "guide_floor_Z": 12.8}


def rail_geom():
    """Bolt guide rails (steel L-sections at the bolt's lower edges) = the magazine's top shelf (R30): their undersides
    stand 1.5 mm (along the mag axis) over the magazine's raked top front edge, over the mag's side walls."""
    fa = MAGD["foreaft"] / 2.0
    front_top = mag_M(fa, 0.0, MAGD["top_along_axis"])
    zb = round(float(front_top[2]) + 1.5 * float(MAG_Z[2]), 2)
    hw = BO["width"] / 2.0                                  # 11.8
    return {"z_bot": zb, "web": (hw + 0.25, hw + 1.75), "lip": (hw - 1.5, hw + 0.25), "lip_top": -7.35,
            "web_top": -2.0, "X": (BO["face_X_back"] - BO["length"] - 2.0, BO["face_X_rest"] - 0.25)}


def pin_holes(host):
    """Flush pin heads (pins_fasteners) seated in each host: (name, side +1 left / -1 right, XZ, dia)."""
    out = []
    for q in dims("pins_fasteners")["list"]:
        nm = q["name"]
        if nm in ("trigger axle", "mag release pin", "selector shaft ends", "seam boss pin"):
            continue
        sides = []
        if q["side"] in ("left", "both"):
            sides.append((1.0, q["XZ"]))
        if q["side"] in ("right", "both"):
            sides.append((-1.0, q.get("XZ_RIGHT", q["XZ"])))
        for s, xz in sides:
            # a head whose ring (+0.2) crosses the seam is cut in both hosts (the seam steps round it)
            r = q["dia"] / 2.0 + 0.2
            zs = seam_lower_z(xz[0])
            in_upper = xz[0] > X_EBF and xz[1] + r > zs + H
            in_lower = xz[0] <= X_EBF or xz[1] - r < zs - H
            if (host == "upper" and in_upper) or (host == "lower" and in_lower):
                out.append((nm, s, xz, q["dia"]))
    return out


def seam_lower_z(x):
    S = SEAM
    zs = []
    for a, b in zip(S[:6], S[1:7]):
        if min(a[0], b[0]) <= x <= max(a[0], b[0]) and abs(b[0] - a[0]) > 1e-6:
            zs.append(a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))
    return min(zs) if zs else float(S[0, 1])


def face_y(side, x, z):
    """The side face's Y at (x, z) for a pin / boss seat (+1 left, -1 right): body, fore-end, the shoulder band, the
    end block."""
    if x < X_EBF:
        return EB_Y[1] if side > 0 else EB_Y[0]
    fore = x > SG.FORE_END_STEP_X
    y = (SG.F_L if fore else SG.Y_L) if side > 0 else (SG.F_R if fore else SG.Y_R)
    if z > Z_LEDGE and z > seam_lower_z(x):
        y -= side * LEDGE
    return y


# ------------------------------------------------------------------------------------------------ upper receiver
def upper_receiver():
    base = master_prism()
    reg = prism(region_upper(), -60.0, 60.0, "XZ")
    plan_pts = SG.top_outline_upper(X_EBF + H - 1.0)
    plan = prism(plan_pts, -100.0, 100.0, "XY")
    # the moulded shoulder: the band above Z_LEDGE set in by LEDGE on both sides, up to the front corner chamfers
    s = SG.FORE_END_STEP_X
    # (r1) the set-in runs on round the chamfered front corner to the front face: ending at the chamfer's start it
    # left a 0.01 mm2 corner triangle where the ledge step, the chamfer and the round met (UD1)
    xf_, c_ = SG.FRONT_FACE_X, SG.FRONT_CHAMFER
    right_chain = [(X_EBF - 2.0, SG.Y_R), (s - (SG.F_R - SG.Y_R), SG.Y_R), (s, SG.F_R), (xf_ - c_, SG.F_R),
                   (xf_, SG.F_R + c_), (xf_ + 3.0, SG.F_R + c_)]
    left_chain = [(X_EBF - 2.0, SG.Y_L), (s - (SG.Y_L - SG.F_L), SG.Y_L), (s, SG.F_L), (xf_ - c_, SG.F_L),
                  (xf_, SG.F_L - c_), (xf_ + 3.0, SG.F_L - c_)]
    strips = [side_strip(right_chain, LEDGE, Z_LEDGE, Z_TOP + 5.0), side_strip(left_chain, LEDGE, Z_LEDGE, Z_TOP + 5.0)]
    seam_z = float(SEAM[0, 1]) + H

    up_seam = SG.offset_polyline(SEAM, +H)

    def near_up_seam(x, z, tol=1.3):
        q = np.array([x, z])
        for a, b in zip(up_seam[:-1], up_seam[1:]):
            ab = b - a
            t = np.clip((q - a) @ ab / max(ab @ ab, 1e-12), 0.0, 1.0)
            if np.linalg.norm(a + t * ab - q) < tol:
                return True
        return False

    def outer_round(mid, d, n1, n2, dih, convex):
        if not convex or dih < 35.0:
            return 0.0
        if mid[2] < seam_z + 1.2 and mid[0] < SG.FORE_END_STEP_X + 3.0:
            return 0.0                                           # the seam edges (their own break)
        if near_up_seam(mid[0], mid[2]):
            return 0.0                                           # (r1) the whole seam incl. the V's upper corners: a
            #                                                      round ending part-way up the V left 0.003 mm2 corner
            #                                                      patches the UD repair could not collapse
        if abs(mid[2] - Z_LEDGE) < 0.8:
            return 0.0                                           # the shoulder's step edge
        if abs(mid[2] - Z_FB) < 0.8 and X_LR0 - 1.0 < mid[0] < X_LRF + 1.0:
            return 0.0                                           # the lower rail's seat
        if mid[0] < X_EBF + H + 0.8:
            return 0.0                                           # the rear face against the end block (seam)
        if mid[2] > Z_TOP - 0.8 and abs(mid[1]) < float(TR["base_flange"]["width"]) / 2.0 + 1.0:
            return 0.0                                           # under the rail
        return 1.0

    x_run = float(SEAM[1, 0]) - 0.5                              # the horizontal seam run ends there

    def seam_break(mid, d, n1, n2, dih, convex):
        if not convex or not (60.0 <= dih <= 120.0):
            return 0.0
        if (abs(mid[2] - seam_z) < 0.6 and mid[0] < x_run) or abs(mid[2] - Z_LEDGE) < 0.8 or mid[0] < X_EBF + H + 0.8:
            return 1.0
        return 0.0

    # ---- the shell's cavity (open at the bottom over the lower, closed fore-end bottom wall, front wall 6 thick)
    xa = SG.line_x_at_z(SEAM[5], SEAM[7], Z_FB)
    cav_xz = SG.polygon_from([(X_EBF - 6.0, -75.0), (X_EBF - 6.0, Z_TOP - WALL), (X_FF - 6.0, Z_TOP - WALL),
                              (X_FF - 6.0, Z_FB + WALL), (xa + WALL, Z_FB + WALL),
                              (SG.line_x_at_z(SEAM[5], SEAM[7], -75.0) + WALL, -75.0)])
    cav_xz2 = np.array([(x, min(z, Z_TOP - WALL - 0.3)) for x, z in cav_xz])      # 0.3 lower: no coplanar top
    cav_fore = prism(cav_xz2, SG.F_R + WALL, SG.F_L - WALL, "XZ")
    cav_body = prism(G.clip_x(cav_xz, None, SG.FORE_END_STEP_X - 1.5), SG.Y_R + WALL, SG.Y_L - WALL, "XZ")
    # ---- internals (united after the cavity cut)
    rg = rail_geom()
    seats = [box(rg["X"][0], rg["X"][1], rg["web"][1] + GAP, SG.Y_L - WALL + 0.3, rg["z_bot"], rg["web_top"]),
             box(rg["X"][0], rg["X"][1], SG.Y_R + WALL - 0.3, -(rg["web"][1] + GAP), rg["z_bot"], rg["web_top"])]
    sg = slide_geom()
    guide = box(376.0, 506.0, 12.0, SG.Y_L - WALL + 0.3, sg["guide_floor_Z"], Z_TOP - WALL + 0.3)
    # the moulded guide runs on to the front wall inside the fore-end (the sheet's long vents show it, not daylight)
    guide_f = box(505.0, X_FF - 5.8, 12.0, SG.F_L - WALL + 0.3, sg["guide_floor_Z"], Z_TOP - WALL + 0.3)
    trunnion = box(BA["breech_X"] + GAP, 470.0, SG.Y_R + WALL - 0.3, SG.Y_L - WALL + 0.3, BORE_Z - 10.5, BORE_Z + 9.3)
    # the port catch (right, integral): 3 mm proud in front of the port, its hooked lip along its rear edge
    cx_, cz_ = EP["catch_X"], EP["catch_Z"]
    lip = EP["catch_lip"]
    # one plan (XY) outline: the body proud of the wall and the hooked lip along its rear edge, flush with its outer face
    yo, yi = SG.Y_R - EP["catch_proud"], SG.Y_R + 1.2
    catch_plan = np.array([[lip["X"][0], yo], [cx_[1], yo], [cx_[1], yi], [cx_[0], yi], [cx_[0], lip["Y"][1]],
                           [lip["X"][0], lip["Y"][1]]])
    catch_body = prism(catch_plan, cz_[0], cz_[1], "XY")
    catch_lip = None
    # ---- openings
    vl = feature("upper_receiver", "forward_long_vent_left")
    vr = feature("upper_receiver", "forward_long_vent_right")
    lvl = feature("upper_receiver", "lower_vents_left")
    lvr = feature("upper_receiver", "lower_vents_right")
    cuts = [wall_cut(stadium_xz(vl["X"][0], vl["X"][1], 0.5 * sum(vl["Z"]), vl["Z"][1] - vl["Z"][0]), SG.F_L, -1),
            wall_cut(stadium_xz(vr["X"][0], vr["X"][1], 0.5 * sum(vr["Z"]), vr["Z"][1] - vr["Z"][0]), SG.Y_R, +1,
                     depth_in=(SG.F_R + WALL) - SG.Y_R + 1.0)]
    for x0, x1 in lvl["X"]:
        cuts.append(wall_cut(stadium_xz(x0, x1, lvl["Z_centre"], lvl["height"]), SG.F_L, -1))
    for x0, x1 in lvr["X"]:
        cuts.append(wall_cut(stadium_xz(x0, x1, lvr["Z_centre"], lvr["height"]), SG.F_R, +1))
    px, pz = EP["port_X"], EP["port_Z"]
    cuts.append(wall_cut(G.rounded_rect(px[0], px[1], pz[0], pz[1], EP["port_corner_R"], 4), SG.Y_R, +1,
                         depth_in=WALL + 12.0))
    # the port's 45 deg deflector chamfer along its rear edge (2.0)
    cuts.append(prism(np.array([[px[0] - 3.0, SG.Y_R - 1.0], [px[0] + 0.5, SG.Y_R - 1.0], [px[0] + 0.5, SG.Y_R + 2.5]]),
                      pz[0] + 2.2, pz[1] - 2.2, "XY"))
    cs = feature("upper_receiver", "charging_slot")
    sx, sz = cs["X"], cs["Z"]
    rise = cs["rear_lock_notch"]["rise_above_slot_top"]
    nw = cs["rear_lock_notch"]["width"]
    slot = np.vstack([[[sx[0], sz[0]], [sx[1], sz[0]], [sx[1], sz[1]], [sx[0] + nw, sz[1]]],
                      G.arc(sx[0] + nw / 2.0, sz[1] + rise - nw / 2.0, nw / 2.0, 0.0, 180.0, 7)[:-1],
                      [[sx[0], sz[1] + rise - nw / 2.0]]])
    cuts.append(wall_cut(slot, SG.Y_L, -1, depth_in=SG.Y_L - sg["Y"][1] + 0.6, draft=False))
    c = 0.25
    cuts.append(box(sg["X"][0] - sg["travel"] - c - 1.0, sg["X"][1] + c, sg["Y"][0] - c, sg["Y"][1] + c,
                    sg["Z"][0] - c, sg["Z"][1] + c))
    cuts.append(box(sg["X"][0] - sg["travel"] - 1.5, 453.5, sg["hook"]["Y"][0] - 0.3, sg["hook"]["Y"][1] + 0.3, 11.9,
                    sg["Z"][0] + 0.4))
    bz = BORE_Z
    cuts.append(cylinder((X_FF - 20.0, 0.0, bz), (X_FF + 1.0, 0.0, bz), BA["hidden_od"] / 2.0 + 0.03, 64))
    cuts.append(cylinder((X_FF - 3.0, 0.0, bz), (X_FF + 1.0, 0.0, bz),
                         feature("upper_receiver", "barrel_collar_counterbore")["dia"] / 2.0, 64))
    cuts.append(cylinder((BA["breech_X"] - 1.0, 0.0, bz), (470.5, 0.0, bz), BA["hidden_od"] / 2.0 + 0.03, 64))
    ey = feature("upper_receiver", "front_sling_eyelet")
    eyz = ey["centre_YZ"]
    cuts.append(cylinder((X_FF - 11.0, eyz[0], eyz[1]), (X_FF + 1.0, eyz[0], eyz[1]), ey["dia"] / 2.0 + 0.6 + GAP, 32))
    sb = feature("lower_receiver", "seam_boss")
    cuts.append(cylinder((sb["XZ"][0], SG.Y_L - WALL - 1.0, sb["XZ"][1]), (sb["XZ"][0], SG.Y_L + 2.0, sb["XZ"][1]),
                         sb["dia"] / 2.0 + 0.2, 48))
    # the lower's selector seat bosses (dia 20.7) reach 1.3 above the seam: the upper's lower edge steps round them
    sp_, seat_r = SE["pivot_XZ"], float(feature("lower_receiver", "selector_seats")["dia"]) / 2.0 + 0.25
    for s_ in (1.0, -1.0):
        yf_ = face_y(s_, sp_[0], sp_[1])
        cuts.append(cylinder((sp_[0], yf_ - s_ * 1.2, sp_[1]), (sp_[0], yf_ + s_ * 3.0, sp_[1]), seat_r, 64))
    for name, side, xz, d in pin_holes("upper"):
        yf = face_y(side, xz[0], xz[1])
        cuts.append(HW.place(HW.pin_hole_cutter(d, 2.6, 0.15), (xz[0], yf, xz[1]), (0, side, 0)))
    for k in TR["screws"]["in_slots"]:                       # the rail screws' threaded inserts (blind, hidden)
        pass

    faces = [SG.Y_L, SG.Y_R, SG.F_L, SG.F_R, SG.Y_L - LEDGE, SG.Y_R + LEDGE, SG.F_L - LEDGE, SG.F_R + LEDGE,
             SG.Y_R - EP["catch_proud"]]

    def lip_break(mid, d, n1, n2, dih, convex):
        if not convex or not (60.0 <= dih <= 120.0):
            return 0.0
        on_face = any(abs(mid[1] - f) < 0.06 for f in faces)
        return 1.0 if on_face and mid[2] > seam_z + 1.0 and mid[0] > X_EBF + 1.0 else 0.0

    ops = [("intersect", [reg]), ("intersect", [plan]), ("diff", strips),
           ("bevel_wc", (1.4, 2, outer_round)), ("bevel_wc", (0.4, 1, seam_break)),
           ("diff", [cav_body]), ("diff", [cav_fore]),
           ("union", seats + [guide, guide_f, trunnion, catch_body]),
           ("diff", cuts),
           ("bevel_wc", (0.35, 1, lip_break))]
    return Ops("upper_receiver", base, ops, bone="body", cls="P-round", slot=FURN, spec_id="upper_receiver",
               joint={"type": "fixed", "parent": None})


def bolt_rails():
    rg = rail_geom()
    m = Mesh()
    for s in (1.0, -1.0):
        w0, w1 = rg["web"]
        l0, l1 = rg["lip"]
        sec = np.array([[l0, rg["z_bot"]], [w1, rg["z_bot"]], [w1, rg["web_top"]], [w0, rg["web_top"]],
                        [w0, rg["lip_top"]], [l0, rg["lip_top"]]])
        sec = sec * np.array([s, 1.0])
        m.extend(prism(sec, rg["X"][0], rg["X"][1], "YZ"))
    from gunlib.parts import PartDef
    return PartDef("bolt_rails", [m], bone="body", cls="M-chamfer", slot=METAL, recipe=[(0.3, 1, 50.0)],
                   joint={"type": "fixed", "parent": "upper_receiver"}, spec_id="upper_receiver")


def build_all():
    from . import lower
    return [upper_receiver(), bolt_rails()] + lower.build_all()
