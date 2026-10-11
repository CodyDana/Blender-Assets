"""The moving steel parts and the fasteners (spec bolt, charging_handle, selector, trigger, mag_release,
pins_fasteners, stock_hinge axle; rulings RP3, RP5, RP7, RP8, RP11, RP18).

Real pattern (steel, M-chamfer / C-fillet):
- bolt: a heavy rectangular block, its upper section overhanging rearward (the recoil-spring guide bore in it, blind
  from the rear), the face with the case-head boss and firing-pin hole, the extractor inset in the right face with its
  claw over the face, the oval thumb scallop on the right face (centred in the port at rest), the charging lug on the
  top front (left), guide grooves along both lower edges riding the receiver's steel rails;
- charging handle (non-reciprocating, left): the lever = ball knob, neck through the wall slot, the outer arm (rod +
  rear block) riding 0.2 off the shoulder band, the tongue inside the slide pocket with its eye on the roll pin
  (Y 19.93, Z 24.46, parallel to X); the slide (10.9 x 10.9, does not rotate) with its hook in front of the bolt's lug,
  the pocket (the tongue's 0..15 deg lock swing + 0.3) and the roll pin;
- selector: one shaft (dia 5.0) with a teardrop lever on each end (hub dia 18.7, blade 10.9 -> 5.4, tip R 2.7), the
  index groove across the hub, the thumb ledge at the tip; the right lever mirrors the left (the RIGHT trace reads the
  same bind angle, -108.3 deg);
- trigger: the traced blade (6.0 wide, crowned face by its R 1.2 rounds) and its tongue round the axle; the axle
  (dia 4.7) with flush heads both sides;
- mag release: the centred paddle (9.0 x 3.0, R 3 lower corners across Y), its pivot boss (dia 4.0) and the nose up
  through the catch window to the notch (tip X 409.33, Z -39.86); the pin (dia 2.0) in the clevis ears;
- pins: flush steel heads at every drawn head (the ring heads with their centre recess), the rear locking pin's round
  head (left) and square end (right); the hinge axle (dia 6.0) through the knuckle stack with chamfered ends.
"""
from __future__ import annotations

import math

import numpy as np

from gunlib import geo2d as G
from gunlib.mesh import Mesh, box, cylinder, prism, revolve, ellipsoid
from gunlib.parts import PartDef
from gunlib.parts import hardware as HW
from gunlib.parts import hinge as HG

import smg_geom as SG
from smg_common import dims, feature, BORE_Z
from . import METAL, GAP, Comp, pcyl
from .receiver import (slide_geom, rail_geom, face_y, wall_line_x, mag_rear_x, Z_BODY_BOT, X_EBF, EB_Y, Z_LEDGE,
                       LEDGE, pin_face_y)
from .lower import trigger_profile

BO = dims("bolt")
CH = dims("charging_handle")
SE = dims("selector")
TRG = dims("trigger")
MR = dims("mag_release")
MW = dims("magwell")
TG = dims("trigger_guard")
SH = dims("stock_hinge")
PF = dims("pins_fasteners")
LOF = {f["name"]: f for f in [feature("lower_receiver", n) for n in ("selector_seats", "seam_boss")]}

HINGE_C = 0.15                                   # hinge row clearance (0.10-0.30) on pivots / bores


def hull(P):
    """Convex hull (monotone chain), counter-clockwise."""
    P = sorted(map(tuple, np.asarray(P, float)))
    if len(P) < 3:
        return np.array(P)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 1e-12:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 1e-12:
            up.pop()
        up.append(p)
    return np.array(lo[:-1] + up[:-1])


def circle(cx, cy, r, n=32):
    t = np.linspace(0.0, 2 * math.pi, n, endpoint=False)
    return np.c_[cx + r * np.cos(t), cy + r * np.sin(t)]


def rot2(P, c, deg):
    t = math.radians(deg)
    P = np.asarray(P, float) - c
    return np.c_[P[:, 0] * math.cos(t) - P[:, 1] * math.sin(t), P[:, 0] * math.sin(t) + P[:, 1] * math.cos(t)] + c


# ------------------------------------------------------------------------------------------------ bolt
def bolt():
    x_face = float(BO["face_X_rest"])                   # 455.6
    x_main = x_face - 1.0                               # the main face; the case-head boss stands to x_face
    x_rear = x_face - float(BO["length"])               # 356.0
    # the underside sits on the rails' shelf (rail_geom z_bot + 0.12, under the lips' top by the 0.2 groove clearance):
    # the spec box's Z -10.1 hangs 1 mm under the shelf and leaves the seated magazine only 0.5 mm of overtravel
    # (M2 asks 1.0-2.0); invisible (the port shows Z >= 2.3), declared
    zb, zt = rail_geom()["z_bot"] + 0.12, 15.3
    hw = BO["width"] / 2.0                              # 11.8
    x_low0 = 380.0                                      # the lower section's rear (the upper overhangs rearward)
    z_split = -1.0
    prof = np.array([[x_rear, z_split], [x_low0, z_split], [x_low0, zb], [x_main, zb], [x_main, zt], [x_rear, zt]])
    body = prism(prof, -hw, hw, "XZ")
    rg = rail_geom()
    cuts = []
    # guide grooves: the rails' lips (Y 10.3..12.05, Z z_bot..lip_top) + 0.2 per side
    g_y0 = rg["lip"][0] - 0.2
    g_z0, g_z1 = rg["z_bot"] - 0.2, rg["lip_top"] + 0.2
    for s in (1.0, -1.0):
        cuts.append(box(x_rear - 1.0, x_face + 1.0, min(s * g_y0, s * (hw + 1.0)), max(s * g_y0, s * (hw + 1.0)),
                        g_z0, g_z1))
    bz = BORE_Z
    cuts.append(cylinder((x_face - 4.0, 0.0, bz), (x_face + 1.0, 0.0, bz), BO["firing_pin_hole_dia"] / 2.0, 16))
    # recoil-spring guide bore, blind from the rear face of the overhang
    cuts.append(cylinder((x_rear - 1.0, 0.0, 9.0), (x_rear + 62.0, 0.0, 9.0), 3.6, 32))
    # extractor pocket in the right face
    ex_l, ex_h = BO["extractor"]["size"][1], BO["extractor"]["size"][0]
    cuts.append(box(x_face - ex_l - 0.15, x_main + 1.0, -hw - 1.0, -hw + 1.35, bz - ex_h / 2.0 - 0.15,
                    bz + ex_h / 2.0 + 0.15))
    # the thumb scallop (oval, 1.5 deep) in the right face
    tr = BO["thumb_recess"]
    cuts.append(ellipsoid((tr["centre_X_rest"], -hw, 8.6), tr["size"][0] / 2.0, tr["depth"], tr["size"][1] / 2.0, 32, 12))
    sg = slide_geom()
    lug = box(sg["lug"]["X"][0], sg["lug"]["X"][1], hw - 0.5, sg["lug"]["Y"][1], sg["lug"]["Z"][0], sg["lug"]["Z"][1])
    # the case-head boss stands 0.15 short of the breech face at rest (the sliding row's lower bound: headspace gap)
    boss = pcyl((x_main - 0.5, 0.0, bz), (x_face - 0.15, 0.0, bz), BO["case_head_boss_dia"] / 2.0, 48)
    extr = box(x_face - ex_l, x_main - 0.02, -hw + 0.02, -hw + 1.33, bz - ex_h / 2.0, bz + ex_h / 2.0)
    claw = box(x_main - 0.02, x_face - 0.15, -hw + 0.02, -6.3, bz - 1.4, bz + 1.4)
    c = float(BO["chamfer"])
    return Comp("bolt", [(body, [(c, 1, 30.0)], cuts), (lug, [(0.3, 1, 30.0)]), (boss, [(0.3, 1, 30.0)]),
                         (extr, [(0.2, 1, 30.0)]), (claw, [(0.2, 1, 30.0)])],
                bone="bolt", cls="M-chamfer", slot=METAL, spec_id="bolt",
                joint={"type": "sliding", "parent": "body", "clearance_mm": [0.15, 0.4]})


# ------------------------------------------------------------------------------------------------ charging handle
PIN_YZ = np.array(CH["lock_axis"]["YZ"], float)       # (19.93, 24.46)
KNOB_C = np.array([CH["knob_centre_XZ"][0], CH["knob_centre_Y"], CH["knob_centre_XZ"][1]])
NECK_R = CH["neck_dia"] / 2.0
EYE_R = 2.3                    # 0.21 under the guide channel's roof
TONGUE_X = (KNOB_C[0] - 2.75, KNOB_C[0] + 2.75)
WALL_FACE_UP = SG.Y_L - LEDGE                          # the shoulder band's face (the arm rides above Z_LEDGE)


def tongue_yz():
    """The tongue's YZ outline: the eye round the pin and the pad the neck rises from."""
    pad = np.array([[20.7, 16.5], [23.3, 16.5], [23.3, 21.5], [20.7, 21.5]])
    return hull(np.vstack([circle(PIN_YZ[0], PIN_YZ[1], EYE_R, 24), pad]))


# (W1 realism round 2) the knob as a turned steel cocking knob on its neck (craft study 2.3: 'ball ~18 on a short round
# neck, dia ~8, ~6 long'), not a full sphere sitting on the slot: the judges read the ball on the rod as a CG primitive.
# Kept: the drawn dia 16.76 (LEFT / RIGHT circle), its centre X / Z and the tip Y 47.5 (TOP). The ball is a flattened
# sphere (Y semi-axis 6.9) whose crown is cut by a flat (dia ~7) rounded R 0.8; its underside runs through an R 2.4
# cove into a dia 8.0 stem that starts 2.0 outside the shoulder band (the dia 5.43 neck through the slot shows there).
KNOB_R = CH["knob_dia"] / 2.0                          # 8.38
KNOB_TIP = float(CH["knob_tip_Y"])                     # 47.5
KNOB_AY = 6.9                                          # the ball's semi-axis along Y
KNOB_FLAT_R = 3.5
KNOB_CY = KNOB_TIP - KNOB_AY * math.sqrt(1.0 - (KNOB_FLAT_R / KNOB_R) ** 2)   # the flat at the tip
KNOB_STEM_R = 4.0
KNOB_STEM_Y0 = WALL_FACE_UP + 2.0


def knob_profile():
    """(t = Y, r) open profile from the stem's base on the axis to the crown flat's centre (revolved about the knob's
    axis, parallel to Y): a polygon with the true ellipse between the stem and the crown, its two corners filleted."""
    R, AY, CY = KNOB_R, KNOB_AY, KNOB_CY
    yS = CY - AY * math.sqrt(1.0 - (KNOB_STEM_R / R) ** 2)          # where the stem's cylinder meets the ball
    phS = math.pi - math.asin(KNOB_STEM_R / R)
    phT = math.asin(KNOB_FLAT_R / R)
    ell = [(CY + AY * math.cos(p), R * math.sin(p)) for p in np.linspace(phS, phT, 18)]
    corner_S, corner_T = np.array(ell[0]), np.array(ell[-1])
    ell = [q for q in ell[1:-1] if np.linalg.norm(np.array(q) - corner_S) > 3.0 and
           np.linalg.norm(np.array(q) - corner_T) > 1.2]
    P = np.array([(KNOB_STEM_Y0, 0.0), (KNOB_STEM_Y0, KNOB_STEM_R), (yS, KNOB_STEM_R)] + ell +
                 [(KNOB_TIP, KNOB_FLAT_R), (KNOB_TIP, 0.0)], float)
    radii = [0.0, 0.4, 2.4] + [0.0] * len(ell) + [0.8, 0.0]
    Q = G.fillet(P, 1.0, 4, min_turn_deg=5.0, radii=radii)
    # back to an open profile from the stem base on the axis to the crown centre on the axis
    i0 = int(np.argmin(np.hypot(Q[:, 0] - KNOB_STEM_Y0, Q[:, 1])))
    Q = np.roll(Q, -i0, axis=0)
    i1 = int(np.argmin(np.hypot(Q[:, 0] - KNOB_TIP, Q[:, 1])))
    Q = Q[:i1 + 1]
    if Q[1, 1] < Q[0, 1] - 1e-9 or Q[1, 0] > KNOB_TIP:              # walked the wrong way round: reverse
        Q = np.vstack([Q[:1], Q[1:][::-1]])
    out = [Q[0]]
    for q in Q[1:]:
        if np.linalg.norm(q - out[-1]) > 0.05:
            out.append(q)
    return [(float(a), float(b)) for a, b in out]


def charging_handle():
    kz = KNOB_C[2]
    knob = revolve(knob_profile(), (KNOB_C[0], 0.0, kz), (0.0, 1.0, 0.0), 32)
    neck = pcyl((KNOB_C[0], 21.5, kz), (KNOB_C[0], KNOB_STEM_Y0 + 0.5, kz), NECK_R, 32)
    tongue = prism(tongue_yz(), TONGUE_X[0], TONGUE_X[1], "YZ")
    y0 = WALL_FACE_UP + 0.2
    rb = CH["arm_rear_block"]
    yb = WALL_FACE_UP + float(rb["proud_of_wall"])
    # the rear block follows the moulded shoulder: 0.2 off the band above the step, 0.2 off the body face below it
    z_step = Z_LEDGE + 0.6
    block = box(rb["X"][0], rb["X"][1] + 0.5, y0, yb, z_step, rb["Z"][1])
    block_lo = box(rb["X"][0], rb["X"][1] + 0.5, SG.Y_L + 0.2, yb, rb["Z"][0], z_step + 0.5)
    ar = CH["arm_rod"]
    rod = box(ar["X"][0], KNOB_C[0] - 3.0, y0, yb, ar["Z"][0], ar["Z"][1])
    eye_bore = cylinder((TONGUE_X[0] - 1.0, PIN_YZ[0], PIN_YZ[1]), (TONGUE_X[1] + 1.0, PIN_YZ[0], PIN_YZ[1]),
                        1.5 + HINGE_C, 24)
    return Comp("charging_handle", [(knob, []), (neck, [(0.2, 1, 50.0)]), (tongue, [(0.3, 1, 30.0)]),
                                    (block, [(0.9, 2, 30.0)]), (block_lo, [(0.6, 2, 30.0)]),
                                    (rod, [(1.2, 2, 30.0)])],
                cutters=[eye_bore], bone="charging_handle", cls="M-round", slot=METAL, spec_id="charging_handle",
                joint={"type": "sliding", "parent": "body", "clearance_mm": [0.15, 0.4],
                       "lock": {"axis_M": [None, float(PIN_YZ[0]), float(PIN_YZ[1])], "deg": [0.0, 15.0]}})


def charging_slide():
    sg = slide_geom()
    body = box(sg["X"][0], sg["X"][1], sg["Y"][0], sg["Y"][1], sg["Z"][0], sg["Z"][1])
    hk = sg["hook"]
    hook = box(hk["X"][0], hk["X"][1], hk["Y"][0] + 0.3, hk["Y"][1], hk["Z"][0], sg["Z"][0] + 0.5)   # 0.3 in: no coplanar union
    # the pocket: the tongue and the neck root swept 0..15 deg about the pin, + 0.3, opening at the outboard face
    neck_root = np.array([[21.0, KNOB_C[2] - NECK_R], [25.5, KNOB_C[2] - NECK_R], [25.5, KNOB_C[2] + NECK_R],
                          [21.0, KNOB_C[2] + NECK_R]])
    sw = [rot2(np.vstack([tongue_yz(), neck_root]), PIN_YZ, a) for a in (0.0, 5.0, 10.0, 15.0)]
    sw = [rot2(np.vstack([tongue_yz(), neck_root]), PIN_YZ, a) for a in np.linspace(0.0, 15.0, 7)]
    pocket = G.offset(G.ccw(hull(np.vstack(sw))), 0.4)
    # open through the slide's underside (the pocket's floor would sit 0.15 over the bottom face: a sliver wall)
    pocket = np.c_[pocket[:, 0], np.where(pocket[:, 1] < sg["Z"][0] + 0.8, sg["Z"][0] - 1.5, pocket[:, 1])]
    pk = prism(pocket, TONGUE_X[0] - 0.3, TONGUE_X[1] + 0.3, "YZ")
    pin = pcyl((sg["X"][0] + 0.6, PIN_YZ[0], PIN_YZ[1]), (sg["X"][1] - 0.6, PIN_YZ[0], PIN_YZ[1]), 1.5, 24)
    return Comp("charging_slide", [(body, [(0.3, 1, 30.0)], [pk]), (hook, [(0.3, 1, 30.0)]), (pin, [(0.2, 1, 50.0)])],
                bone="charging_handle", cls="M-chamfer", slot=METAL, spec_id="charging_handle",
                joint={"type": "sliding", "parent": "body", "clearance_mm": [0.15, 0.4]})


# ------------------------------------------------------------------------------------------------ selector
def selector():
    pv = np.array(SE["pivot_XZ"], float)
    ang = math.radians(float(SE["bind_blade_angle_deg_from_plusX"]))
    u = np.array([math.cos(ang), math.sin(ang)])
    tip = np.array(SE["blade_tip_XZ_left"], float)
    L = float(np.linalg.norm(tip - pv))
    r_hub = SE["hub_dia"] / 2.0
    r_tip = float(SE["tip_R"])
    tc = pv + u * (L - r_tip)
    outline = hull(np.vstack([circle(pv[0], pv[1], r_hub, 40), circle(tc[0], tc[1], r_tip, 12)]))
    plate = 2.75
    hub_t = 3.25
    seat = 0.5 * LOF["selector_seats"]["dia"]
    pieces = []
    cuts = []
    for s in (1.0, -1.0):
        y_in = s * (abs(face_y(s, pv[0], pv[1])) + float(SE["seat_boss_proud"]) + HINGE_C)
        y_pl = y_in + s * plate
        y_hub = y_in + s * hub_t
        pieces.append((prism(outline, min(y_in, y_pl), max(y_in, y_pl), "XZ"), [(0.8, 2, 30.0)]))
        pieces.append((pcyl((pv[0], y_in + s * 0.4, pv[1]), (pv[0], y_hub, pv[1]), r_hub - 0.9, 48), [(0.5, 2, 30.0)]))
        # the thumb ledge: a 0.5 raised pad across the tip
        ledge = hull(np.vstack([circle(tc[0], tc[1], r_tip - 0.5, 16), circle(*(tc - u * 2.2), r_tip - 0.5, 16)]))
        pieces.append((prism(ledge, min(y_pl - s * 0.5, y_pl + s * 0.5), max(y_pl - s * 0.5, y_pl + s * 0.5), "XZ"),
                       [(0.3, 1, 30.0)]))
        # the index groove across the hub (0.5 wide, 0.3 deep, along the blade)
        a0 = pv - u * (r_hub - 1.6)
        a1 = pv + u * (r_hub - 1.6)
        nrm = np.array([-u[1], u[0]]) * 0.25
        gp = np.array([a0 - nrm, a1 - nrm, a1 + nrm, a0 + nrm])
        cuts.append(prism(gp, min(y_hub - s * 0.3, y_hub + s * 1.0), max(y_hub - s * 0.3, y_hub + s * 1.0), "XZ"))
        # the shaft end: a 0.3 ring groove of dia 5.0 in the hub face (the shaft reads through the hub)
        r_sh = 2.5
        from gunlib.parts.sights_flip import revolve_loop
        cuts.append(revolve_loop([(-0.3, r_sh - 0.15), (-0.3, r_sh + 0.15), (1.0, r_sh + 0.15), (1.0, r_sh - 0.15)],
                                 (pv[0], y_hub, pv[1]), (0.0, s, 0.0), 32))
    yl = abs(face_y(1.0, pv[0], pv[1])) + float(SE["seat_boss_proud"]) + HINGE_C + 0.5
    yr = -(abs(face_y(-1.0, pv[0], pv[1])) + float(SE["seat_boss_proud"]) + HINGE_C + 0.5)
    shaft = pcyl((pv[0], yr, pv[1]), (pv[0], yl, pv[1]), 2.5, 32)
    pieces.append((shaft, []))
    return Comp("selector", pieces, cutters=cuts, bone="selector", cls="M-chamfer", slot=METAL, spec_id="selector",
                joint={"type": "hinge", "parent": "body", "clearance_mm": [0.1, 0.3],
                       "positions_deg": SE["positions_rot_Y_deg_from_bind"]})


# ------------------------------------------------------------------------------------------------ trigger
def trigger():
    blade, tongue = trigger_profile()
    w = TRG["width"] / 2.0
    ax, az = TRG["pivot_XZ"]
    axle_r = _pin("trigger axle")["dia"] / 2.0
    bore = cylinder((ax, -w - 1.0, az), (ax, w + 1.0, az), axle_r + HINGE_C, 32)
    return Comp("trigger", [(prism(G.ccw(blade), -w, w, "XZ"), [(1.2, 3, 30.0)]),
                            (prism(G.ccw(tongue), -w + 0.5, w - 0.5, "XZ"), [(0.3, 1, 30.0)])],
                cutters=[bore], bone="trigger", cls="C-fillet", slot=METAL, spec_id="trigger",
                joint={"type": "hinge", "parent": "body", "clearance_mm": [0.1, 0.3]})


def _pin(name):
    return [q for q in PF["list"] if q["name"] == name][0]


def flush_head(d, xz, side, yface, proud=0.15, depth=2.4, ring=False):
    m = HW.flush_pin(d, depth, proud=proud, chamfer=0.3, nseg=24 if d >= 5.0 else 16)
    if ring and d >= 5.0:
        # the ring head: a 0.4 deep centre recess leaves the drawn steel ring (wall 1.2)
        rr = d / 2.0 - 1.2
        rec = revolve([(proud - 0.4, 0.0), (proud - 0.4, rr), (proud + 1.0, rr), (proud + 1.0, 0.0)], (0, 0, 0),
                      (0, 0, 1), 32)
        return HW.place(m, (xz[0], yface, xz[1]), (0, side, 0)), HW.place(rec, (xz[0], yface, xz[1]), (0, side, 0))
    return HW.place(m, (xz[0], yface, xz[1]), (0, side, 0)), None


def trigger_axle():
    q = _pin("trigger axle")
    r = q["dia"] / 2.0
    ax, az = q["XZ"]
    yl = pin_face_y(1.0, ax, az) + 0.15
    yr = pin_face_y(-1.0, ax, az) - 0.15
    m = HG.pin((ax, 0.0, az), (0.0, 1.0, 0.0), yr, yl, r, chamfer=0.3, nseg=32)
    return PartDef("trigger_axle", [m], bone="body", cls="M-chamfer", slot=METAL, recipe=[],
                   joint={"type": "fixed", "parent": "lower_receiver"}, spec_id="pins_fasteners")


# ------------------------------------------------------------------------------------------------ mag release
def mag_release():
    x0, x1 = float(MR["rear_face_X"]), float(MR["front_face_X"])
    zt, zb = float(MR["top_Z"]), float(MR["bottom_Z"])
    hw = MR["width_Y"] / 2.0
    pad_r = float(MR["pad_R"])
    yz = G.rounded_rect(-hw, hw, zb, zt + 0.0, 0.0)
    # the lower corners across Y rounded R pad_R (the finger pad)
    yz = np.vstack([G.arc(hw - pad_r, zb + pad_r, pad_r, -90.0, 0.0, 6), [[hw, zt], [-hw, zt]],
                    G.arc(-hw + pad_r, zb + pad_r, pad_r, 180.0, 270.0, 6)])
    paddle = prism(G.ccw(yz), x0, x1, "YZ")
    px, pz = MR["pivot_XZ"]
    boss = pcyl((px, -hw, pz), (px, hw, pz), MR["pivot_boss_dia"] / 2.0, 32)
    tip_x, tip_z = MR["nose_tip_XZ_seated"]
    tip_z -= 0.2                       # the nose's top 0.2 under the notch's bearing face at rest (M2 0.0-0.3)
    tip_x += 0.15                      # engagement 1.5 measured past the tip's 0.3 break (M3 >= 1.5)
    ch = 0.8                           # the top-front corner chamfered: releasing (-11 deg) the nose lifts 0.14 at exit
    wl = wall_line_x
    nose = np.array([[x0 + 0.2, zt - 0.6], [x1 - 0.2, zt - 0.6], [wl(-46.2) + 0.1, -46.2], [wl(-45.6) + 0.2, -45.6],
                     [tip_x, -41.6], [tip_x, tip_z - ch], [tip_x - ch, tip_z], [wl(tip_z) + 1.0, tip_z],
                     [403.6, -45.6], [x0 + 0.2, -50.0]])
    nose_m = prism(G.ccw(nose), -3.2, 3.2, "XZ")
    pin_bore = cylinder((px, -hw - 1.0, pz), (px, hw + 1.0, pz), MR["pin_dia"] / 2.0 + HINGE_C, 24)
    # the pad's lower front corner rounded R 2.0 in the side view: released (-11 deg) it swings 3.6 forward and stops
    # short of the magwell's lower rear edge (0.06 square)
    rc = 2.0
    arc_ = [(x1 - rc + rc * math.cos(a), zb + rc + rc * math.sin(a)) for a in np.radians(np.linspace(0.0, -90.0, 7))]
    corner = np.array([(x1 + 1.0, zb - 1.0), (x1 + 1.0, zb + rc)] + arc_[::1] + [(x1 - rc, zb - 1.0)])
    corner_cut = prism(G.ccw(corner), -hw - 1.0, hw + 1.0, "XZ")
    return Comp("mag_release", [(paddle, [(0.4, 1, 30.0)]), (boss, [(0.3, 1, 30.0)]), (nose_m, [(0.3, 1, 30.0)])],
                cutters=[pin_bore, corner_cut], bone="mag_release", cls="M-chamfer", slot=METAL, spec_id="mag_release",
                joint={"type": "hinge", "parent": "body", "clearance_mm": [0.1, 0.3]})


def mag_release_pin():
    px, pz = MR["pivot_XZ"]
    pw = MR["width_Y"] / 2.0
    y_out = pw + 0.3 + float(TG["paddle_clevis"]["ear_thickness_Y"])
    m = HG.pin((px, 0.0, pz), (0.0, 1.0, 0.0), -y_out - 0.1, y_out + 0.1, MR["pin_dia"] / 2.0, chamfer=0.25, nseg=24)
    return PartDef("mag_release_pin", [m], bone="body", cls="M-chamfer", slot=METAL, recipe=[],
                   joint={"type": "fixed", "parent": "lower_receiver"}, spec_id="pins_fasteners")


# ------------------------------------------------------------------------------------------------ pins, axle
def pins_fasteners():
    m = Mesh()
    cuts = []
    for q in PF["list"]:
        nm = q["name"]
        if nm in ("trigger axle", "mag release pin", "selector shaft ends"):
            continue
        sides = []
        if q["side"] in ("left", "both"):
            sides.append((1.0, q["XZ"]))
        if q["side"] in ("right", "both"):
            sides.append((-1.0, q.get("XZ_RIGHT", q["XZ"])))
        for s, xz in sides:
            if nm == "seam boss pin":
                # (W1 realism round 2) on the selector pad's boss lobe (2.4 thick there): a 1.8 deep pin
                from .lower import PAD_TOP_L
                head, rec = flush_head(q["dia"], xz, s, PAD_TOP_L, depth=1.8)
                m.extend(head)
                continue
            yf = pin_face_y(s, xz[0], xz[1])
            if nm == "rear locking pin" and s > 0:
                head = HW.place(revolve([(-2.4, 0.0), (-2.4, 3.0), (0.4, 3.0), (0.9, 2.6), (1.2, 1.6), (1.3, 0.0)],
                                        (0, 0, 0), (0, 0, 1), 32), (xz[0], yf, xz[1]), (0, s, 0))
                m.extend(head)
                continue
            if nm == "rear locking pin" and s < 0:
                head, _ = flush_head(q["dia"], xz, s, yf, proud=0.15)
                m.extend(head)
                sq = HW.place(box(-2.15, 2.15, -2.15, 2.15, 0.0, 0.45), (xz[0], yf, xz[1]), (0, s, 0))
                m.extend(sq)
                continue
            head, rec = flush_head(q["dia"], xz, s, yf, ring=q.get("head") == "ring" or q["dia"] >= 7.0)
            m.extend(head)
            if rec is not None:
                cuts.append(rec)
    return PartDef("pins_fasteners", [m], bone="body", cls="M-chamfer", slot=METAL, cutters=cuts, recipe=[],
                   joint={"type": "fixed", "parent": "body"}, spec_id="pins_fasteners")


def hinge_axle():
    ax, ay = SH["axis_X"], SH["axis_Y"]
    r = SH["axle_dia"] / 2.0
    m = HG.pin((ax, ay, 0.0), (0.0, 0.0, 1.0), -22.0 + 0.1, 30.0 - 0.1, r, chamfer=0.4, nseg=48)
    return PartDef("hinge_axle", [m], bone="body", cls="M-chamfer", slot=METAL, recipe=[],
                   joint={"type": "fixed", "parent": "lower_receiver"}, spec_id="stock_hinge")


def build_all():
    return [bolt(), charging_handle(), charging_slide(), selector(), trigger(), trigger_axle(), mag_release(),
            mag_release_pin(), pins_fasteners(), hinge_axle()]
