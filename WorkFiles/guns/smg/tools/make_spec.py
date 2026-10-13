"""Write WorkFiles/guns/smg/smg_spec.json: THE build spec for Compact SMG SM-01 (SK_SMG01 / SM_SMG01 / SM_SMG01_Mag).

    py -3 -B WorkFiles/guns/smg/tools/make_spec.py

Merges the three study outputs into one consistent spec (same method as the AR-01's rifle/tools/make_spec.py):
  smg_measured.json + trace/*.json        (measurement role)  -> wins on silhouette dimensions and positions
  craft_parts.json / CRAFT_STUDY.md       (craft role)        -> wins on small-part construction (real-pattern rulings
                                                                 RP1-RP22), finishes and wear
  smg_interface.json / SMG_BUILD_PLAN.md  (tech role)         -> wins on frames, bones, sockets, slots, budgets, LODs,
                                                                 gates and stage order
Where one role's number came from a reading error, the merge re-read the sheet (8-10x zooms in scratch/merge/) and says so
in spec["resolutions"]. Derived numbers (bore height, grip axis, Grip origin, magazine frame, sockets, rail slot lattice,
fold geometry, bounds) are computed here from the traced outlines so they cannot drift from the trace.
Needs numpy only. ROOT comes from this file's location (works in a worktree and after the merge).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
SMG = HERE.parents[1]                        # WorkFiles/guns/smg
ROOT = HERE.parents[4]                       # repo root
TRACE = SMG / "trace"
OUT = SMG / "smg_spec.json"

MEAS = json.loads((SMG / "smg_measured.json").read_text(encoding="utf-8"))
CRAFT = json.loads((SMG / "craft_parts.json").read_text(encoding="utf-8"))
PLAN = json.loads((SMG / "smg_interface.json").read_text(encoding="utf-8"))
LEFT = json.loads((TRACE / "LEFT_outline.json").read_text(encoding="utf-8"))
RIGHT = json.loads((TRACE / "RIGHT_outline.json").read_text(encoding="utf-8"))
TOP = json.loads((TRACE / "TOP_outline.json").read_text(encoding="utf-8"))
D = MEAS["dimensions_LEFT"]
TV = MEAS["top_view"]
RF = MEAS["right_side_features"]
BOX = D["part_boxes_mm_X0_X1_Z0_Z1"]
# ---- SCALE (orchestrator ruling 2026-10-09, resolution R26): the trace is measured at OVERALL mm (625; it was 690). Every
# number below that was READ OFF THE SHEET in mm at the 690 scale is written sc(value_at_690); numbers that are real-pattern
# or line-standard values (rail profile, clearances, wall thicknesses, pin and bore norms, sight hardware) stay absolute.
OVERALL = float(MEAS["scale"]["overall_length_mm_chosen"])
S = OVERALL / 690.0


def sc(v, n=2):
    """A sheet read in mm at the 690 scale -> the ruled scale (lists recurse)."""
    if isinstance(v, (list, tuple)):
        return [sc(x, n) for x in v]
    return round(float(v) * S, n) + 0.0


def r1(v, n=1):
    if isinstance(v, (list, tuple, np.ndarray)):
        return [r1(x, n) for x in v]
    return round(float(v), n) + 0.0


# ------------------------------------------------------------------------------------------------ geometry helpers
def rings_of(src, outer_only=True):
    return [np.array(r["mm"], float) for r in src if (r["kind"] == "outer" or not outer_only)]


def main_ring(part):
    rr = [(abs(r["area_px"]), np.array(r["mm"], float)) for r in LEFT["parts"][part] if r["kind"] == "outer"]
    return max(rr, key=lambda t: t[0])[1]


def cross_z(rr, X):
    out = []
    for P in rr:
        Q = np.roll(P, -1, 0)
        for a, b in zip(P, Q):
            if (a[0] - X) * (b[0] - X) < 0:
                out.append(a[1] + (b[1] - a[1]) * (X - a[0]) / (b[0] - a[0]))
    return sorted(out)


def cross_x(rr, Z):
    out = []
    for P in rr:
        Q = np.roll(P, -1, 0)
        for a, b in zip(P, Q):
            if (a[1] - Z) * (b[1] - Z) < 0:
                out.append(a[0] + (b[0] - a[0]) * (Z - a[1]) / (b[1] - a[1]))
    return sorted(out)


def dp_simplify(P, tol):
    """Douglas-Peucker on a closed ring (same algorithm as tools/refimg.py)."""
    n = len(P)
    if n < 5:
        return P
    i1 = int(np.argmax(np.hypot(*(P - P[0]).T)))
    keep = np.zeros(n + 1, bool)
    Q = np.vstack([P, P[:1]])
    keep[[0, i1, n]] = True
    stack = [(0, i1), (i1, n)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        A, B = Q[a], Q[b]
        ab = B - A
        nn = np.hypot(*ab)
        seg = Q[a + 1:b]
        d = np.hypot(*(seg - A).T) if nn == 0 else np.abs(ab[0] * (seg[:, 1] - A[1]) - ab[1] * (seg[:, 0] - A[0])) / nn
        k = int(np.argmax(d))
        if d[k] > tol:
            m = a + 1 + k
            keep[m] = True
            stack += [(a, m), (m, b)]
    return Q[:-1][keep[:-1]]


def profile(part, tol=0.3):
    return r1(dp_simplify(main_ring(part), tol), 2)


def area_px(part):
    return round(sum(abs(r["area_px"]) for r in LEFT["parts"][part] if r["kind"] == "outer"), 1)


SIL_L = rings_of(LEFT["silhouette"])
SIL_R = rings_of(RIGHT["silhouette"])
SIL_T = rings_of(TOP["silhouette"])
WPROF = np.array(TOP["width_profile_mm_X_Yleft_Yright"], float)     # X, Y left (+), Y right (-)


def top_width(x0, x1):
    m = (WPROF[:, 0] >= x0) & (WPROF[:, 0] <= x1)
    return r1(np.median(WPROF[m, 1]), 1), r1(np.median(WPROF[m, 2]), 1)


# ================================================================================================ derived numbers
# ---- bore height. The measurer set Z = 0 on the muzzle device / barrel centre line using a median "outer diameter"
# of 20.8 mm. Its own silhouette rings say the device is 25.3-25.7 tall at X 656-685 (the 20.8 came from a sliver
# where a see-through slot splits the ring). Centre of the OUTER crossings over the exposed barrel + device:
cent_L, cent_R, dia_L = [], [], []
for X in np.arange(sc(632.0), sc(686.0), sc(2.0, 4)):
    zl, zr = cross_z(SIL_L, X), cross_z(SIL_R, X)
    if len(zl) >= 2:
        cent_L.append((zl[0] + zl[-1]) / 2)
        if X >= sc(656.0):
            dia_L.append(zl[-1] - zl[0])
    if len(zr) >= 2:
        cent_R.append((zr[0] + zr[-1]) / 2)
BORE_Z = round(float(np.median(cent_L)), 2)
BORE_Z_RIGHT = round(float(np.median(cent_R)), 2)
DEVICE_OD = round(float(np.median(dia_L)), 1)
DEVICE_W_TOP = TV["muzzle_device_width"]["mm"]

# ---- pistol grip axis: midline of the traced grip between Z -70 and -140 (below the beaver-tail flare, above the heel)
grip_r = rings_of(LEFT["parts"]["grip"])
rows = []
for Z in np.arange(sc(-70.0), sc(-141.0), sc(-2.0, 4)):
    x = cross_x(grip_r, Z)
    if len(x) >= 2:
        rows.append((Z, x[0], x[-1]))
GR = np.array(rows)
k_axis, c_axis = np.polyfit(GR[:, 0], (GR[:, 1] + GR[:, 2]) / 2, 1)          # X = k Z + c
GRIP_RAKE = round(math.degrees(math.atan(k_axis)), 2)                        # bottom behind the top = +
JZ = D["reference_points"]["grip_junction_web_Z"]                            # web line (grip front meets the guard)
J = np.array([k_axis * JZ + c_axis, JZ])
u_dn = np.array([-k_axis, -1.0]) / math.hypot(k_axis, 1.0)
GRIP_DEPTH = 46.0                                                            # plan (AR-01 H1 value; hand anatomy: absolute)
G = J + GRIP_DEPTH * u_dn
GX, GZ = round(float(G[0]), 2), round(float(G[1]), 2)
GRIP_WIDTH_FOREAFT = r1(np.median(GR[:, 2] - GR[:, 1]) * math.cos(math.atan(k_axis)), 1)

# ---- receiver widths (TOP; the merge's check shows TOP round parts agree with the side views within 3 %)
W_REC_L, W_REC_R = TV["receiver_body_Y_left_right"]
W_REC = TV["receiver_body_width_plain"]["mm"]
FRONT_L, FRONT_R = top_width(sc(560), sc(584))
HINGE_L, HINGE_R = top_width(sc(275), sc(292))
LATCH_Y_L = top_width(sc(258), sc(272))[0]                     # latch housing's left face (TOP over the stock knuckle zone)
LATCH_BUTTON_PROUD = 1.0

# ---- charging handle (merge re-read at 8x, scratch/merge/zL_knob.png; TOP agrees on the knob size)
KNOB_D = sc(18.5)
KNOB_C = (sc(549.3), sc(21.0))
KNOB_TIP_Y = round(W_REC_L + TV["lateral_features_gun_left_(+Y,image-down)"][2]["beyond_body_mm"], 1)   # 52.4
KNOB_CY = round(KNOB_TIP_Y - KNOB_D / 2, 2)
ARM_ROD = {"X": sc([514.0, 539.7]), "Z": sc([16.3, 24.3])}
ARM_BLOCK = {"X": sc([501.5, 514.0]), "Z": sc([13.0, 24.7]), "proud_of_wall": sc(3.3)}
CH_TRAVEL = round(75.0 * S, 1)       # the real ~75 mm (craft RP5, from the 85 mm photo slot) scales with the gun (R26)
SLOT_H = sc(6.5)
SLOT_Z = [round(KNOB_C[1] - SLOT_H / 2, 2), round(KNOB_C[1] + SLOT_H / 2, 2)]
NECK_D = sc(6.0)
SLOT_X = [round(KNOB_C[0] - CH_TRAVEL - NECK_D / 2 - 0.25, 2), round(KNOB_C[0] + NECK_D / 2 + 0.25, 2)]
# lock (check fix C4): the real pattern's lever pivots on a roll pin in the slide (axis parallel to X) and the slide does
# not rotate. The pin sits in the slide's upper inboard corner so that every point of the outer arm (Y 34.2, Z 13.0-24.7)
# moves OUTWARD over the 15 deg lock (an axis at the slide centre Y 20, Z 21 drove the arm 1.24 mm through the wall)
W_IN_L = round(W_REC_L - 3.5, 1)                                  # left wall inner face (wall 3.5 at the slot)
SLIDE = {"Y": sc([14.0, 26.0]), "Z": sc([17.5, 29.5]), "note": "%.1f x %.1f steel slide in a moulded guide above the bolt; does not rotate" % (sc(12.0, 1), sc(12.0, 1))}
LOCK_PIN = (sc(22.0), sc(27.0))                                          # (Y, Z), roll pin dia 3.0 through the slide
LOCK_DEG = 15.0
ARM_Y_IN = round(W_REC_L + 0.2, 2)                                # arm inner face, 0.2 off the wall


def lock_rot(y, z, deg=LOCK_DEG):
    """(Y, Z) of a lever point after the lock rotation about +X through LOCK_PIN (Blender R_x, + = knob up)."""
    t = math.radians(deg)
    a, b = y - LOCK_PIN[0], z - LOCK_PIN[1]
    return LOCK_PIN[0] + a * math.cos(t) - b * math.sin(t), LOCK_PIN[1] + a * math.sin(t) + b * math.cos(t)


_arm_pts = [(ARM_Y_IN, z) for z in (ARM_BLOCK["Z"][0], ARM_ROD["Z"][0], ARM_ROD["Z"][1], ARM_BLOCK["Z"][1])]
ARM_MIN_DY = round(min(lock_rot(y, z, d)[0] - y for y, z in _arm_pts for d in np.linspace(0.5, LOCK_DEG, 30)), 3)
KNOB_RISE = round(lock_rot(KNOB_CY, KNOB_C[1])[1] - KNOB_C[1], 2)
NECK_RISE_IN = round(lock_rot(W_IN_L, KNOB_C[1])[1] - KNOB_C[1], 2)        # neck centre at the wall's inner face
NECK_RISE_OUT = round(lock_rot(W_REC_L, KNOB_C[1])[1] - KNOB_C[1], 2)      # ... and at its outer face
NOTCH_RISE = round(math.ceil((NECK_RISE_OUT + 0.4) * 2) / 2, 1)            # notch above the slot top, ramped

# ---- bolt / barrel (measurer's feed geometry; craft's X 485 would put the chamber over the magazine)
MAG = D["magazine"]
FE, RE = MAG["front_edge_line"], MAG["rear_edge_line"]
BREECH_X = sc(503.0, 1)
BOLT_REST_FACE_X = BREECH_X
BOLT_BACK_FACE_X = BREECH_X - CH_TRAVEL
CROWN_X = sc(659.0, 1)                                      # inside the device's thread collar (device seat 644.1 + 15)
BARREL_LEN = CROWN_X - BREECH_X

# ---- magazine frame: axis = midline of the traced front and rear edges; origin = where it crosses the well lip line
k_mag = (FE["dX_dZ"] + RE["dX_dZ"]) / 2
c_mag = (FE["X_at_Z0"] + RE["X_at_Z0"]) / 2
MAG_RAKE = round(math.degrees(math.atan(-k_mag)), 2)          # + = floor plate forward of the top
# R35 (W1b fix round): the traced front-to-back (front edge = the spine rib's crest) is body + rib; the body is the
# traced width minus the rib, its rear face on the traced rear edge, so the frame axis (the body's midline) sits half a
# rib behind the traced midline (perpendicular shift d moves the line's X-intercept by d * sqrt(1 + k^2))
MAG_RIB = 0.8
c_mag -= (MAG_RIB / 2.0) * math.hypot(k_mag, 1.0)
lf, lr = D["mag_well"]["lip_lower_edge_front_XZ"], D["mag_well"]["lip_lower_edge_rear_XZ"]
s_lip = (lr[1] - lf[1]) / (lr[0] - lf[0])
Zm = -78.0
for _ in range(30):
    Xm = k_mag * Zm + c_mag
    Zm = lf[1] + (Xm - lf[0]) * s_lip
MAG_O = np.array([k_mag * Zm + c_mag, 0.0, Zm])
U_UP = np.array([k_mag, 0.0, 1.0]) / math.hypot(k_mag, 1.0)                    # mag +Z (up the insertion axis)
U_FW = np.array([U_UP[2], 0.0, -U_UP[0]])                                      # mag +X (forward, perpendicular)
MAG_T = 27.0                                                                   # thickness (R14, re-decided by R26 at
#                                                                                625: the 3/4 read 27.8 +-5.2, real minimum 27)
MAG_FA_TRACED = MAG["width_front_to_back_perpendicular_to_axis"]["mm"]         # 42.2 at 625 (the rib's crest incl.)
MAG_FA = round(MAG_FA_TRACED - MAG_RIB, 2)                                     # R35: the body (41.4)
# R30 (W1b): the bolt's underside (bolt box Z) and the magazine's RAKED top face: the top face is perpendicular to the
# mag axis, so its front edge stands (fore-aft / 2) x sin(rake) above the centre; the whole top (incl. the lips) stays
# 0.5 under the bolt's underside (the bolt strips the top round over it; no cartridge is modelled)
BOLT_Z = [round(BORE_Z - sc(13.0), 1), round(BORE_Z + sc(15.0), 1)]
MAG_TOP_Z = round(BOLT_Z[0] - 0.5 - (MAG_FA / 2.0) * math.sin(math.radians(abs(MAG_RAKE))), 2)   # centre of the top
MAG_TOP_ALONG = (MAG_TOP_Z - MAG_O[2]) / U_UP[2]
MAG_FLOOR_ALONG = (MAG["floor_bottom_Z"]["mm"] - MAG_O[2]) / U_UP[2]
INSERT_START_ALONG = -(MAG_TOP_ALONG + 10.0)
MAG_LEN = MAG_TOP_ALONG - MAG_FLOOR_ALONG
THETA_MAG_Y = -math.degrees(math.atan2(-U_UP[0], U_UP[2]))                     # Blender rot about Y of the Mag frame
# Blender: rotation about +Y by t maps +Z to (sin t, 0, cos t); we need (U_UP[0], U_UP[2]) -> t = atan2(U_UP[0], U_UP[2])
THETA_MAG_Y = math.degrees(math.atan2(U_UP[0], U_UP[2]))


def mag_local(p):
    v = np.array(p, float) - MAG_O
    return [round(float(v @ U_FW), 2) + 0.0, round(float(v[1]), 2) + 0.0, round(float(v @ U_UP), 2) + 0.0]


def mag_world(xl, yl, zl):
    return MAG_O + xl * U_FW + np.array([0, yl, 0]) + zl * U_UP


# ---- magazine release paddle (check fix C1). The trace's old 'mag_release' box (X 449-462) was the magwell's rear
# corner; the lever is DRAWN inside the guard's front leg (trace parts.mag_release, pin head
# face_features.mag_release_pin_head). Mechanics: the magwell's rear wall (4.0 + 0.3 to the magazine) stands between
# the magazine and the paddle, so the paddle hangs in an open slot behind that wall, ahead of the guard's front leg, with
# its pin in a clevis of the lower (real-pattern layout). Its nose reaches the notch through the catch window.
MAG_REAR = lambda Z: RE["dX_dZ"] * Z + RE["X_at_Z0"]               # traced magazine rear face (straight-body fit)
MW_WALL, MW_CLR = sc(4.0, 1), 0.3                                 # C1 wall, scaled with the sheet (R26)
WALL_OUT = lambda Z: MAG_REAR(Z) - MW_CLR - MW_WALL                 # magwell rear wall, outer face
PAD_DRAWN = BOX["mag_release"]                                      # drawn lever X0, X1, Z0, Z1
PAD_PIN_DRAWN = D["face_features"]["mag_release_pin_head"]["centre_XZ"]
PAD_REL = -11.0                                                     # lower end forward, nose rearward (R_y: - = fwd)
PAD_DEPTH, PAD_WIDTH, PAD_PIN_D, PAD_BOSS_D = 3.0, 9.0, 2.0, 4.0     # depth 3.0 at 625 (R26: guard leg)
# R31: magwell outer width from the 3/4 view (front-face ratio magwell lip / magazine, independent of the view angle)
MW_RATIO = D["mag_well"]["outer_width_estimate_from_3q"]["mm"] / MAG["thickness_estimate_from_3q"]["mm"]
MW_OUT_LIP = round(MAG_T * MW_RATIO, 1)
MW_OUT_BODY = round(MW_OUT_LIP - 4.0, 1)
PAD_TOP_Z, PAD_BOT_Z = PAD_DRAWN[3], PAD_DRAWN[2]
LIP_REAR_Z = D["mag_well"]["lip_lower_edge_rear_XZ"][1]
NOTCH_Z, PAD_ENGAGE, NOTCH_DEPTH = sc(-44.0), 1.5, 2.5


def _rotY(px, pz, cx, cz, deg):
    t = math.radians(deg)
    a, b = px - cx, pz - cz
    return cx + a * math.cos(t) + b * math.sin(t), cz - a * math.sin(t) + b * math.cos(t)


def _pad_front_ok(xf, piv):
    for Z in np.linspace(PAD_TOP_Z, LIP_REAR_Z, 40):                                  # static: 0.3 to the wall
        if WALL_OUT(Z) - xf < 0.3 - 1e-9:
            return False
    for deg in np.linspace(0.0, PAD_REL, 23):                                         # swing: 0.10 to the wall
        for Z in np.linspace(piv[1], LIP_REAR_Z, 40):
            x2, z2 = _rotY(xf, Z, piv[0], piv[1], deg)
            if z2 >= LIP_REAR_Z and WALL_OUT(z2) - x2 < 0.10 - 1e-9:
                return False
    return True


_xf = math.floor(WALL_OUT(PAD_TOP_Z) * 10) / 10
while True:
    _piv = (round(min(PAD_PIN_DRAWN[0], _xf - PAD_DEPTH / 2), 2), PAD_PIN_DRAWN[1])
    if _pad_front_ok(_xf, _piv) and _piv[0] + PAD_BOSS_D / 2 + 0.3 <= WALL_OUT(_piv[1]):
        break
    _xf = round(_xf - 0.1, 1)
PAD_FRONT_X = _xf
PAD_PIVOT = _piv
PAD_REAR_X = round(PAD_FRONT_X - PAD_DEPTH, 2)
PAD_NOSE = (round(MAG_REAR(NOTCH_Z) + PAD_ENGAGE, 2), NOTCH_Z)                       # nose tip, seated
PAD_NOSE_TRAVEL = round(PAD_NOSE[0] - _rotY(PAD_NOSE[0], PAD_NOSE[1], *PAD_PIVOT, PAD_REL)[0], 2)
PAD_SHIFT_FRONT = round(PAD_FRONT_X - PAD_DRAWN[1], 1)                              # built vs drawn (declared)
GUARD_OPENING_FRONT_X = round(PAD_DRAWN[0] - 0.6, 1)                                # drawn leg rear edge (1/2 px)
GUARD_LEG = round(PAD_REAR_X - 0.3 - GUARD_OPENING_FRONT_X, 2)


# ---- magazine side ladder (merge re-read, scratch/merge/zL_mag.png)
LADDER = {"channel_top_Z": sc(-97.9), "channel_bottom_Z": sc(-237.4), "tie_Z": sc([-143.4, -178.7, -214.5]),
          "channel_width": sc(12.5), "rib_between": sc(3.0), "depth": 1.0}

# ---- top rail slot lattice (MIL-STD-1913 pitch in the drawn toothed zone; resolution R9)
PITCH = 10.01
SLOT_W = 5.24
TOOTH_L = PITCH - SLOT_W
tr = D["rails"]["top"]
t0, t1 = tr["teeth_runs_X"][0][0], tr["teeth_runs_X"][-2][1]                    # 350.3 .. 556.8 (the last run is the sight)
n_teeth = int(round((t1 - t0 + SLOT_W) / PITCH))
span = n_teeth * PITCH - SLOT_W
tooth0 = (t0 + t1) / 2 - span / 2
lattice0 = tooth0 + TOOTH_L + SLOT_W / 2 - PITCH                               # slot just behind the first tooth
REAR_BASE = D["sights"]["sight_rear"]["base_X_span_above_rail"]
FRONT_BASE = D["sights"]["sight_front"]["base_X_span_above_rail"]
rear_c = (REAR_BASE[0] + REAR_BASE[1]) / 2
front_c = (FRONT_BASE[0] + FRONT_BASE[1]) / 2
k_rear = round((rear_c - lattice0) / PITCH)
k_front = round((front_c - lattice0) / PITCH)
SLOT0_X = lattice0 + k_rear * PITCH                                            # rearmost cut slot = rear sight lug
idx = lambda x: int(round((x - SLOT0_X) / PITCH))
TOOTHED_SLOTS = list(range(idx(lattice0), idx(lattice0) + n_teeth + 1))         # slots around the drawn teeth
FRONT_LUG = idx(lattice0 + k_front * PITCH)
CUT_SLOTS = [0] + TOOTHED_SLOTS + [FRONT_LUG]
SLOT_X_LIST = [round(SLOT0_X + k * PITCH, 2) for k in CUT_SLOTS]
RAIL_TOP_Z = tr["tooth_top_Z"]["mm"]
RAIL_UNDER_Z = tr["underside_Z_seam"]["mm"]

TOPF_X0 = sc(283.5, 1)                         # R32: the D rim's rear end (end_block.dims.top_frame X0)
lrl = D["rails"]["bottom"]
# check fix C8: 7 slots centred on the rail (end webs ~5.4 mm); round(76.2 / 10.01) = 8 left 0.45 mm end walls
LR_END_WEB_MIN = 3.0
LR_N = int((lrl["length"]["mm"] - SLOT_W - 2 * LR_END_WEB_MIN) // PITCH) + 1          # 7 slots on 76.2 mm
LR_C = (lrl["X"][0] + lrl["X"][1]) / 2
LR_SLOTS_X = [round(LR_C + PITCH * (k - (LR_N - 1) / 2), 2) for k in range(LR_N)]
LR_Z = lrl["tooth_bottom_Z"]["mm"]

# ---- sights (merge re-read, scratch/merge/zL_rear.png / zL_front.png): aperture centre and post tip on one line
# check fix C9: the sight line is anchored on the drawn aperture ring (panel px (320.7, 130.5), rows 129-132; Z_M 76.0
# +-0.6); the earlier 73.0 matched the dark band in the front sight, which hides the post in a side view
APERTURE = (sc(330.0, 1), sc(76.0, 1))
POST_TIP = (D["sights"]["sight_front"]["head_centre_X"]["mm"], APERTURE[1])
SIGHT_RADIUS = round(POST_TIP[0] - APERTURE[0], 1)
# check fix C6: the rear leaf folds FORWARD, so its pin sits at the leaf's front-lower corner (a pin at the leaf's rear
# face swung the head 7.9 mm into the rail). Pin dia 3.0 in a U-channel base whose floor is 2.0 above the rail top.
REAR_HEAD_X = D["sights"]["sight_rear"]["head_X_span_1to6mm_below_top"]
REAR_PIVOT = (round(REAR_HEAD_X[1] - 0.5, 1), round(RAIL_TOP_Z + 2.0 + 1.5, 1))
FRONT_PIVOT = (round(front_c, 1), round(RAIL_TOP_Z + 4.0, 1))
FRONT_HEAD_X = D["sights"]["sight_front"]["head_X_span_1to6mm_below_top"]
REAR_FOLDED_TOP = round(REAR_PIVOT[1] + (REAR_PIVOT[0] - REAR_HEAD_X[0]), 1)      # +90 about Y: (dx, dz) -> (dz, -dx)
FRONT_FOLDED_Z = [round(FRONT_PIVOT[1] + (FRONT_HEAD_X[0] - FRONT_PIVOT[0]), 1),  # -90 about Y: (dx, dz) -> (-dz, dx)
                  round(FRONT_PIVOT[1] + (FRONT_HEAD_X[1] - FRONT_PIVOT[0]), 1)]
B4C_REAR = round(REAR_FOLDED_TOP + 0.3, 1)
B4C_FRONT = round(FRONT_FOLDED_Z[1] + 0.3, 1)

# ---- trigger (check fix C5/C7): the axle is the drawn head on both side views (LEFT (402.2, -40.2), RIGHT (404.7,
# -39.6): panel drift); the pull rotates the blade's lower end REARWARD = + about Y (Blender R_y), as the AR-01's 0..+12
TRIG_PIVOT = tuple(D["face_features"]["trigger_axle_head"]["centre_XZ"])
TRIG_PULL = 13.0

# ---- selector (one shaft; LEFT is the authority for X; RIGHT drifts 5.5 mm = panel drift)
SEL = D["selector_left"]
SEL_P = SEL["pivot_XZ"]
SEL_TIP = SEL["lever_tip_XZ"]
phi_bind = math.degrees(math.atan2(SEL_TIP[1] - SEL_P[1], SEL_TIP[0] - SEL_P[0]))       # in the XZ plane from +X
# check fix C11: these detents are a DESIGN CALL, not real-pattern figures. The saved manual figures (scratch/realref/
# craft img62/65/68) show SAFE with the blade ~25 deg below forward and SEMI / AUTO both ~15-20 deg below rearward
# (indistinguishable at 72 x 48 px); the sheet's pose (blade 71.6 deg below rearward) matches neither and is taken as
# SEMI by choice, SAFE at 45 deg below forward and AUTO 45 deg further rearward (open question Q16)
PHI_SAFE = -45.0                                                                        # blade 45 deg below forward
PHI_AUTO = phi_bind - 45.0                                                              # 45 deg further rearward
# Blender rotation about +Y by t changes the XZ-plane angle by -t
SEL_ROT = {"SEMI (bind = sheet pose)": 0.0, "SAFE": round(-(PHI_SAFE - phi_bind), 1),
           "AUTO": round(-(PHI_AUTO - phi_bind), 1)}

# ---- stock and fold
ST = D["stock"]
HINGE_X = ST["hinge_axis_estimate"]["X"]["mm"]                                          # 272.4
PAD = ST["butt_pad"]
PAD_W = sc(58.0, 1)                                      # craft read of the pad's top face; the TOP trace 67.3 is oblique
FRAME_W = sc(29.5, 1)                                    # top strut width (TOP, top face only)
CATCH = RF["boss_front_of_port"]
CATCH_PROUD = 3.0                                  # real moulded catch boss (absolute)
R_WALL = W_REC_R                                   # -34.9
PAD_CLEAR = 1.0
FOLD_MID_Y = round(R_WALL - CATCH_PROUD - PAD_CLEAR - PAD_W / 2, 2)                     # folded stock mid-plane
HINGE_Y = round(FOLD_MID_Y / 2, 2)                                                       # 180 deg rigid fold
KNUCKLE_OD = sc(12.0, 1)                           # the drawn knuckle stack (TOP) scales with the sheet
KNUCKLE_PROUD_R = round(-(HINGE_Y - KNUCKLE_OD / 2) + R_WALL, 1)                       # beyond the right wall (+ = out)
FOLD_REAR_X = round(HINGE_X - KNUCKLE_OD / 2, 1)
FOLDED_LEN = round(OVERALL - FOLD_REAR_X, 1)


def fold_pt(x, y):
    """stock point (extended, M) -> folded (M): +180 deg about the vertical axis at (HINGE_X, HINGE_Y)."""
    return (2 * HINGE_X - x, 2 * HINGE_Y - y)


# ---- folded retention (check fix C3): nothing on the folded stock reached the port catch (pad inner face Y -38.9, catch
# outer face -37.9, frame inner face -53.15). A moulded lug on the rear upright's RIGHT face (extended frame), just ahead
# of the pad, reaches past the catch's hooked lip when folded; the catch lip overhangs rearward over the lug's barb.
# Folded frame, Y negative = outboard (right). The catch body is X CATCH, Y R_WALL..R_WALL-3.0; its hooked lip runs along
# its REAR edge, flush with its outer face, overhanging rearward; the lug's barb sits in the pocket under the lip.
LIP_OVER, LIP_T = 1.5, 1.5
LIP_X = [round(CATCH["X"][0] - LIP_OVER, 2), CATCH["X"][0]]
LIP_Y = [round(R_WALL - CATCH_PROUD, 2), round(R_WALL - CATCH_PROUD + LIP_T, 2)]          # -37.9 .. -36.4
POCKET_Y = [LIP_Y[1], R_WALL]                                                             # -36.4 .. -34.9
LUG_TIP_Y_F = round(R_WALL - 0.3, 2)                                                      # 0.3 off the wall
LUG_BODY_X_F = [round(LIP_X[0] - 0.3 - 6.0, 2), round(LIP_X[0] - 0.3, 2)]                 # behind the lip, 6 long
BARB_X_F = [LUG_BODY_X_F[1], round(CATCH["X"][0] - 0.2, 2)]                               # forward under the lip
BARB_Y_F = [round(LIP_Y[1] + 0.3, 2), LUG_TIP_Y_F]                                        # 0.3 under the lip
F3_ENGAGE_X = round(BARB_X_F[1] - LIP_X[0], 2)                                            # barb length under the lip
LUG_Z = [round(max(CATCH["Z"][0] + 2.0, ST["parts_X_Z"]["stock_rear_upright"][2]), 1),
         round(min(CATCH["Z"][1] - 2.0, ST["parts_X_Z"]["stock_rear_upright"][3]) - 1.0, 1)]
_ext = lambda xs: sorted(round(fold_pt(x, 0)[0], 2) for x in xs)
_exty = lambda ys: sorted(round(2 * HINGE_Y - y, 2) for y in ys)
LUG = {"on": "stock_frame rear upright, RIGHT face (extended frame), just ahead of the butt pad; moulded with the frame",
       "Z": LUG_Z, "root_Y_ext": round(-FRAME_W / 2, 2),
       "body_X_ext": _ext(LUG_BODY_X_F), "tip_Y_ext": _exty([LUG_TIP_Y_F])[0],
       "barb_X_ext": _ext(BARB_X_F), "barb_Y_ext": _exty(BARB_Y_F), "barb_ramp_deg": 35,
       "folded": {"body_X": LUG_BODY_X_F, "tip_Y": LUG_TIP_Y_F, "barb_X": BARB_X_F, "barb_Y": BARB_Y_F},
       "proud_of_pad_side_ext": round(-(_exty([LUG_TIP_Y_F])[0] + PAD_W / 2), 2),
       "engagement_X_under_lip": F3_ENGAGE_X, "release": "the user pulls the stock outboard; the lug flexes (polymer) "
       "and the barb's 35 deg rear ramp lifts it over the lip"}
CATCH_LIP = {"edge": "rear edge of the catch (faces the folded upright)", "X": LIP_X, "Y": LIP_Y, "pocket_Y": POCKET_Y,
             "overhang_X": LIP_OVER, "thickness_Y": LIP_T}

# ---- extended-stock latch (check fix C14): a necked push-button bolt in the stock's upper hinge band engages a lug that
# projects rearward from the end block's left rear ABOVE the drawn see-through gap (X 272.4, Z -12.8..+14.2)
LATCH_AXIS_XZ = (round(HINGE_X - sc(6.0), 1), sc(18.5, 1))
LATCH = {"lug": {"on": "end block, left rear, moulded; projects rearward into a recess in the stock's upper band",
                 "X": [round(HINGE_X - sc(8.4), 1), round(BOX["hinge_block"][0], 1)], "Y": [sc(22.0, 1), round(sc(22.0, 1) + 6.0, 1)],
                 "Z": [sc(15.0, 1), sc(22.0, 1)],
                 "bore": {"axis": "Y", "dia": 4.3, "centre_XZ": list(LATCH_AXIS_XZ)},
                 "exit_slot": {"width_Z": 2.8, "from": "the bore centre rearward to the lug's rear end",
                               "why": "folding moves the stock rearward relative to the lug at the latch"}},
         "bolt": {"axis": "Y through (%.1f, %.1f)" % LATCH_AXIS_XZ, "dia": 4.0, "neck_dia": 2.5, "neck_length": 6.4,
                  "travel": 2.0, "spring": "pushes the bolt +Y (out, toward the button)",
                  "latched": "full diameter 2.0 mm into the lug's bore (the neck sits outboard of the lug)",
                  "pressed": "button in 2.0: the neck spans the lug's 6.0 thickness, the stock folds"},
         "button": {"shape": "vertical oval", "size": [7.0, 16.0], "proud": LATCH_BUTTON_PROUD, "stroke": 2.0,
                    "face_Y": round(LATCH_Y_L + LATCH_BUTTON_PROUD, 1)},
         "housing_left_face_Y": LATCH_Y_L, "engagement_latched": 2.0}


# ---- bounds (half-diagonal of the box, extended, mm)
def bounds_r(x0, x1, y0, y1, z0, z1):
    return math.sqrt(((x1 - x0) / 2) ** 2 + ((y1 - y0) / 2) ** 2 + ((z1 - z0) / 2) ** 2)


Y_MIN = min(TV["lateral_features_gun_right_(-Y,image-up)"][0]["Y_extreme"], HINGE_Y - KNUCKLE_OD / 2)
Y_MAX = KNUCKLE_TIP = KNOB_TIP_Y
OV = D["overall"]
R_GUN = bounds_r(0, OVERALL, Y_MIN, Y_MAX, OV["bottom_Z_without_mag"]["mm"], OV["top_Z"]["mm"])
R_GUN_MAG = bounds_r(0, OVERALL, Y_MIN, Y_MAX, OV["bottom_Z_with_mag"]["mm"], OV["top_Z"]["mm"])
MAG_PTS = [mag_world(sx * MAG_FA / 2, sy * MAG_T / 2, z) for sx in (-1, 1) for sy in (-1, 1)
           for z in (MAG_FLOOR_ALONG, MAG_TOP_ALONG)]
MP = np.array(MAG_PTS)
R_MAG = bounds_r(MP[:, 0].min(), MP[:, 0].max(), MP[:, 1].min(), MP[:, 1].max(), MP[:, 2].min(), MP[:, 2].max())
# check fix C10: the folded envelope comes from EVERY stock-bone part (frame, pad, stock-side knuckle, latch housing and
# button, lug); the latch housing (Y up to HINGE_L) folds furthest out, not the pad
STOCK_BONE_Y_MAX = {"stock_frame": FRAME_W / 2, "butt_pad": PAD_W / 2,
                    "latch_housing_and_button": LATCH_Y_L + LATCH_BUTTON_PROUD,
                    "stock_knuckle": HINGE_Y + KNUCKLE_OD / 2, "retention_lug": -FRAME_W / 2}
FOLD_Y_MIN_BY = {k: round(2 * HINGE_Y - v, 1) for k, v in STOCK_BONE_Y_MAX.items()}
FOLD_Y_MIN = min(FOLD_Y_MIN_BY.values())
FOLD_Y_MIN_PART = min(FOLD_Y_MIN_BY, key=FOLD_Y_MIN_BY.get)
R_FOLDED = bounds_r(FOLD_REAR_X, OVERALL, FOLD_Y_MIN, Y_MAX, OV["bottom_Z_without_mag"]["mm"], OV["top_Z"]["mm"])
SS_GUN = [1.0, 0.25, 0.10, 0.033]
SS_MAG = [1.0] + [round(s * R_MAG / R_GUN, 4) for s in SS_GUN[1:]]


# ---- frames: M (measurement) -> B (Blender build, origin Grip) -> Unreal cm
def to_b(x, y, z):
    return [round(x - GX, 2) + 0.0, round(y, 2) + 0.0, round(z - GZ, 2) + 0.0]


def to_ue(b):
    return [round(b[0] / 10, 3) + 0.0, round(-b[1] / 10, 3) + 0.0, round(b[2] / 10, 3) + 0.0]


def rot(roll=0.0, pitch=0.0, yaw=0.0, blender=None):
    return {"blender_euler_xyz_deg": blender or [0.0, 0.0, 0.0], "unreal": {"roll": roll, "pitch": pitch, "yaw": yaw}}


def sock(name, bone, m, r=None, use="", src="", state="final"):
    b = to_b(*m)
    return {"socket": name, "bone": bone, "M_mm": r1(m, 2), "blender_mm": b, "unreal_cm": to_ue(b),
            "rotation": r or rot(), "use": use, "source": src, "state": state}


def msock(name, local, r=None, use="", src="", state="final"):
    return {"socket": name, "mag_mm": [round(v, 2) + 0.0 for v in local],
            "M_mm_seated": r1(mag_world(*local), 2), "unreal_cm": to_ue(list(local)),
            "rotation": r or rot(), "use": use, "source": src, "state": state}


# ================================================================================================ sockets
mw = rings_of(LEFT["parts"]["mag_well"])
MW_FRONT_AT_60 = cross_x(mw, sc(-60.0))[-1]
PORT = RF["ejection_port"]
mag_pitch_ue = round(-THETA_MAG_Y, 2)
GUN_SOCKETS = [
    sock("Grip", "body", (GX, 0.0, GZ), use="origin; attach to the character's weapon_r. 46 mm down the grip axis "
         "from the web line (plan / AR-01 H1 value); H1 early confirms or moves it and the sidecar records hand_offset",
         src=f"computed: grip-axis midline (trace parts.grip, Z -70..-140, rake {GRIP_RAKE} deg) + 46 mm from the "
             f"junction at the web line Z {JZ}"),
    sock("SupportHand", "body", (round(MW_FRONT_AT_60, 2), 0.0, sc(-60.0)), use="hand_l two-bone IK target: off-hand palm "
         "on the magwell front (study 5.3 SMG default); PROVISIONAL until H1 (may move to the lower rail)",
         src="trace parts.mag_well front edge at Z %.1f" % sc(-60.0), state="provisional (H1)"),
    sock("Trigger", "trigger", (sc(409.4), 0.0, sc(-77.9)), use="index finger target", src="trace: trigger finger face at its "
         "lower third (measure face_profile)"),
    sock("Muzzle", "muzzle_device", (OVERALL, 0.0, BORE_Z), use="flash, smoke, tracer; on the bore within 0.5 mm / 0.05 deg",
         src=f"device tip X {OVERALL}; bore Z from the outer silhouette centre (resolution R2)"),
    sock("MuzzleSeat", "body", (D["barrel"]["device_seat_X"]["mm"], 0.0, BORE_Z), use="suppressor / device seat",
         src="measure barrel.device_seat_X"),
    sock("Sight", "sight_rear", (APERTURE[0], 0.0, APERTURE[1]), use="ADS: aperture centre, +X toward the front post tip "
         "(sight line parallel to the bore)", src="the drawn aperture ring, panel px (320.7, 130.5) (check fix C9)"),
    sock("SightFront", "sight_front", (POST_TIP[0], 0.0, POST_TIP[1]), use="front post tip (folded-state check, review "
         "camera)", src="measure head_centre_X; tip Z = aperture centre Z (B4)"),
    sock("Mag", "magazine", tuple(MAG_O), r=rot(pitch=mag_pitch_ue, blender=[0.0, round(THETA_MAG_Y, 3), 0.0]),
         use="SM_SMG01_Mag attaches with zero relative transform; +Z up the insertion axis (tilted with the "
         f"{MAG_RAKE} deg rake), +X forward", src="mag axis = midline of the traced front/rear edges; origin on the "
         "traced well-lip line"),
    sock("MagInsertStart", "body", tuple(mag_world(0, 0, INSERT_START_ALONG)),
         r=rot(pitch=mag_pitch_ue, blender=[0.0, round(THETA_MAG_Y, 3), 0.0]),
         use=f"straight reload path start: Mag moved {abs(INSERT_START_ALONG):.1f} mm along its -Z (insert depth "
             f"{MAG_TOP_ALONG:.1f} + 10)", src="computed"),
    sock("ShellEject", "body", ((PORT["X"][0] + PORT["X"][1]) / 2, R_WALL, (PORT["Z"][0] + PORT["Z"][1]) / 2),
         r=rot(pitch=10.0, yaw=75.0, blender=[0.0, -10.0, -75.0]),
         use="casing spawn; +X = throw: to the right, 15 deg forward of square, 10 deg up (real blowback ports throw "
             "right and slightly forward). Stock folded: the throw cone meets the folded stock (B3b: 29 stock / pad "
             "vertices inside it; Q5 open), so spawned casings ignore the gun's own collision (W4 tech review)",
         src="RIGHT trace ejection_port centre on the right wall"),
    sock("ChargingHandle", "charging_handle", (KNOB_C[0], KNOB_CY, KNOB_C[1]), use="hand target (knob centre)",
         src="merge re-read (zL_knob.png) + TOP knob protrusion"),
    sock("Selector", "selector", (sc(357.7), round(W_REC_L + 2.5, 1), sc(-45.6)), use="thumb target: left lever tab, 4 mm in "
         "from the tip", src="measure selector_left tip"),
    sock("MagRelease", "mag_release", (PAD_REAR_X, 0.0, round(PAD_BOT_Z + 6.0, 2)), use="finger target: the paddle's "
         "rear face 6 mm above its bottom (the trigger finger pushes it forward)", src="mag_release dims (check fix C1)"),
    sock("Rail_Top", "body", (SLOT0_X, 0.0, RAIL_TOP_Z), use="attachments: slot 0 centre (rearmost cut slot, under the "
         "rear sight's lug) on the rail-top plane, +X along the slots, +Z up; mounts snap at k x 10.01",
         src="rail lattice (resolution R9)"),
    sock("Rail_Bottom", "body", (LR_SLOTS_X[0], 0.0, LR_Z), r=rot(roll=180.0, blender=[180.0, 0.0, 0.0]),
         use="lower rail slot 0 centre, +X along the slots, +Z out of the rail (down)", src="lower rail lattice"),
    sock("Stock", "body", (D["stock"]["parts_X_Z"]["hinge_block"][0], 0.0, BORE_Z), use="modular stocks: the receiver's "
         "rear (hinge) face", src="trace parts.hinge_block rear"),
    sock("Shoulder", "stock", (0.0, 0.0, round((PAD["Z"][0] + PAD["Z"][1]) / 2, 2)), use="TP aim offsets; butt-pad centre, "
         "+X = pad normal reversed; follows the fold", src="trace parts.butt_pad"),
    sock("SlingFront", "body", (D["barrel"]["receiver_front_face_X"]["mm"], sc(24.0), sc(31.0)), use="sling: the front-left "
         "eyelet hole on the receiver front face (3/4 view)", src="craft RP17 + merge read of the 3/4 (zQ_front.png)"),
    sock("SlingRear", "stock", (sc(40.1), 0.0, sc(-65.5)), r=rot(), use="sling: the lower through-hole of the stock's rear "
         "upright (axis Y)", src="merge re-read (zL_butt.png)"),
    sock("CenterOfMass", "body", (sc(440.0), 0.0, sc(-15.0)), use="physics CoM (stock extended, mag out); the folded CoM is "
         "reported in the sidecar", src="PROVISIONAL estimate; computed by the form stage from part volumes x densities "
         "(polymer 1.4, steel 7.85 g/cm3) scaled to 2.5 kg", state="computed at W1"),
    sock("Holster", "body", (sc(440.0), 0.0, sc(-15.0)), use="= CenterOfMass until the game sets it", src="= CenterOfMass",
         state="computed at W1"),
]
MAG_SOCKETS = [
    msock("Mag", [0.0, 0.0, 0.0], use="origin: centre of the well-entry opening when seated (the seating pivot)",
          src="computed"),
    msock("HandReload", [0.0, MAG_T / 2, sc(-90.0, 1)], use="left palm on the body", src="mid-exposed body, left face"),
    msock("Feed", [0.0, 0.0, round(MAG_TOP_ALONG, 2)], use="top centre of the feed lips", src=f"lips top Z {MAG_TOP_Z} (R30) "
          "seated (below the bolt path)"),
    msock("Base", [0.0, 0.0, round(MAG_FLOOR_ALONG, 2)], r=rot(pitch=-90.0, blender=[0.0, 90.0, 0.0]),
          use="floor-plate centre, +X = outward normal (down the mag axis); impact FX", src="trace floor plate"),
    msock("CenterOfMass", [0.0, 0.0, round((MAG_TOP_ALONG + MAG_FLOOR_ALONG) / 2, 1)], use="physics", src="PROVISIONAL "
          "(the empty polymer body's centroid); computed at W3", state="computed at W3"),
]

# ================================================================================================ fasteners (C7)
FFL, FFR = D["face_features"], RF
PINS = [
    {"name": "front support bolt", "side": "left", "XZ": FFL["pin_front_takedown"]["centre_XZ"], "dia": sc(7.7, 1),
     "note": "the RIGHT draws nothing there (the port catch's front)"},
    {"name": "trigger-housing pin behind the magwell", "side": "both", "XZ": FFL["pin_lower_rear_of_magwell"]["centre_XZ"],
     "XZ_RIGHT": FFR["pin_lower_rear_of_magwell"]["centre_XZ"], "dia": sc(7.8, 1), "head": "ring"},
    {"name": "small head above it", "side": "both", "XZ": FFL["head_above_rear_pin"]["centre_XZ"],
     "XZ_RIGHT": FFR["head_above_rear_pin"]["centre_XZ"], "dia": 3.5},
    {"name": "trigger axle", "side": "both", "XZ": FFL["trigger_axle_head"]["centre_XZ"],
     "XZ_RIGHT": FFR["trigger_axle_head"]["centre_XZ"], "dia": sc(5.2, 1), "note": "= the trigger bone's pivot"},
    {"name": "seam boss pin", "side": "left", "XZ": FFL["seam_boss_pin"]["centre_XZ"], "dia": 3.0,
     "note": "inside the LEFT seam boss (lower_receiver.features seam_boss)"},
    {"name": "seam head upper (right)", "side": "right", "XZ": FFR["seam_head_upper"]["centre_XZ"], "dia": 3.5},
    {"name": "seam head lower (right)", "side": "right", "XZ": FFR["seam_head_lower"]["centre_XZ"], "dia": 3.5},
    {"name": "head behind the right selector hub", "side": "right", "XZ": FFR["head_behind_selector"]["centre_XZ"],
     "dia": 3.5},
    {"name": "end-block head", "side": "both", "XZ": FFL["head_end_block"]["centre_XZ"],
     "XZ_RIGHT": FFR["head_end_block"]["centre_XZ"], "dia": 4.0},
    {"name": "rear locking pin", "side": "both", "XZ": FFL["pin_hinge_block"]["centre_XZ"], "dia": sc(6.6, 1),
     "XZ_RIGHT": FFR["locking_pin_end"]["centre_XZ"], "head": "left: round head; right: square-ish plain end %.1f" % sc(4.7, 1)},
    {"name": "mag release pin", "side": "both", "XZ": list(PAD_PIVOT), "dia": PAD_PIN_D,
     "note": "in the clevis ears; drawn on the LEFT at %s (the RIGHT's lever area is too dark to read)" % PAD_PIN_DRAWN},
    {"name": "selector shaft ends", "side": "both", "XZ": SEL_P, "dia": 5.0, "note": "in the hubs"}]

# ================================================================================================ parts
SLOT_METAL, SLOT_FURN, SLOT_MAG = "M_SMG01_Metal", "M_SMG01_Furniture", "M_SMG01_Mag"
F_POLY, F_STIP, F_MAGP, F_RUB, F_STEEL, F_BOLT = ("polymer_black", "grip_stipple", "polymer_mag", "rubber_pad",
                                                 "phosphate_steel", "bolt_steel")
TRL = "trace/LEFT_outline.json"
TRR = "trace/RIGHT_outline.json"


def tref(*keys, view="LEFT", file=TRL):
    return {"file": file, "keys": [f"parts.{k}" for k in keys], "view": view, "frame": "M",
            "area_px": {k: area_px(k) for k in keys} if file == TRL else None}


def boxM(key, y=None):
    b = BOX[key]
    out = {"X": [b[0], b[1]], "Z": [b[2], b[3]]}
    if y is not None:
        out["Y"] = y
    return out


parts = []


def part(**kw):
    kw.setdefault("asset", "SK_SMG01 + SM_SMG01")
    kw.setdefault("features", [])
    parts.append(kw)


part(id="upper_receiver", display="Upper receiver (fibre-reinforced polymer shell, incl. the slotted fore-end)",
     bone="body", process="P-round (polymer moulding)", joint={"type": "fixed", "parent": None}, slot=SLOT_FURN,
     finish=F_POLY, texel_class="B rear (behind the magwell) / C fore-end / E inside",
     box_M={"X": [D["receiver"]["X"][0], D["receiver"]["X"][1]], "Z": [BOX["receiver_upper"][2], RAIL_UNDER_Z],
            "Y": [W_REC_R, W_REC_L]},
     dims={"length": D["receiver"]["length_front_face_to_rear_end"]["mm"],
           "top_under_rail_Z": RAIL_UNDER_Z, "upper_lower_seam_Z": D["receiver"]["upper_lower_seam_Z"]["mm"],
           "fore_end_bottom_Z_above_lower_rail": D["receiver"]["front_body_bottom_Z_above_lower_rail"]["mm"],
           "width_plain_X393_512": W_REC, "width_Y_left_right": [W_REC_L, W_REC_R],
           "width_fore_end_X560_584": [FRONT_L, FRONT_R], "front_face_X": D["barrel"]["receiver_front_face_X"]["mm"],
           "wall": [3.0, 3.5], "side_ledge_step": {"Z": sc([12.0, 15.0], 1), "step": [0.5, 0.8],
                                                 "note": "full-length moulded shoulder on both sides; upper band set in"},
           "front_left_corner": "vertical chamfered corner between the front face and the left side (3/4 view)",
           "edge_R": [0.6, 2.0], "draft_deg": [1.0, 2.0]},
     construction="One polymer box shell (upper) with flat vertical sides, a flat top under the rail and a near-vertical "
     "front face (1-2 deg draft, R 2 edge). Wall 3.0-3.5 mm; every opening shows that wall (vents, port, charging slot, "
     "bore opening, eyelet). INSIDE (modelled at form): two steel L-section bolt guide rails 3 x 4 mm along the inner "
     "walls at bolt height from the breech face back over the travel + 10 mm; the charging-slide guide above the "
     "barrel; the barrel seat boss with a transverse roll-pin bore; the support-bolt bosses at the magwell front; the "
     "two receiver-side hinge knuckles at the right rear (see stock_hinge). Parting witness on the side-wall edge rounds "
     "(texture only). Ejector circles only on hidden faces. No sink (none drawn).",
     features=[
         {"name": "forward_long_vent_left", "side": "left", "X": D["face_features"]["front_upper_slot"]["X"],
          "Z": D["face_features"]["front_upper_slot"]["Z"], "shape": "stadium through-vent, 3 mm wall, 1 deg draft, "
          "0.4 mm outer break", "ruling": "RP4", "conf": "+-1.2 mm (measure)"},
         {"name": "forward_long_vent_right", "side": "right", "X": sc([530.1, 595.8], 1), "Z": sc([25.0, 33.9], 1),
          "shape": "as left", "ruling": "RP4", "conf": "+-1.5 mm (merge read of the RIGHT panel, zR_slot.png; the "
          "measurer did not trace it)"},
         {"name": "lower_vents_left", "side": "left", "X": sc([[543.1, 570.1], [578.3, 605.4]], 1), "Z_centre": sc(-3.4, 1),
          "height": sc(8.7, 1), "shape": "stadium through-vents (the barrel shows through)", "conf": "+-1.2 (dark-feature "
          "boxes + 0.6 mm lip)"},
         {"name": "lower_vents_right", "side": "right", "X": sc([[540.1, 568.3], [576.5, 603.5]], 1), "Z_centre": sc(-0.1, 1),
          "height": sc(8.7, 1), "shape": "as left", "conf": "+-1.2 (RIGHT frame)"},
         {"name": "charging_slot", "side": "left", "X": SLOT_X, "Z": SLOT_Z, "rear_lock_notch": {"rise_above_slot_top": NOTCH_RISE,
          "width": 7.0, "bottom": "full round", "ramp": "follows the neck's arc about the lock pin (rise %.2f at the "
          "wall's inner face, %.2f at its outer face)" % (NECK_RISE_IN, NECK_RISE_OUT)}, "ruling": "RP3", "note": "through the left wall; covered by the "
          "handle's arm at rest except X %.1f-%.1f behind the arm's rear block (a small visible change, C-Q1)" % (SLOT_X[0], ARM_BLOCK["X"][0])},
         {"name": "front_sling_eyelet", "side": "front face, upper left", "centre_YZ": sc([24.0, 31.0], 1), "dia": 6.0,
          "axis": "X, 11 mm deep into the solid corner boss, then out into the vent cavity (a sling hook passes in)",
          "sleeve": "steel, 0.6 mm proud", "ruling": "RP17"},
         {"name": "barrel_collar_counterbore", "side": "front face", "dia": round(D["barrel"]["front_collar_diameter"]["mm"] + 0.6, 1), "note": "the steel collar ring sits in it"},
         {"name": "front_takedown_pin", "side": "left", "XZ": D["face_features"]["pin_front_takedown"]["centre_XZ"],
          "head": "flush steel ring dia %.1f, 0.15 proud" % sc(7.7, 1), "ruling": "RP18 (support bolt head)"}],
     wear="whitening on the vertical corners, the front-face rim and the fore-end lower edge; support-hand polish on "
          "the fore-end belly and left side; fine fore-aft scratches; vent lips whitened",
     trace=tref("receiver_upper", "handguard_area"),
     side_profile_M=[profile("receiver_upper"), profile("handguard_area")],
     authority="LEFT (outline, left features); RIGHT (right features); TOP (width)", confidence="high (outline), medium "
     "(seams, vents)", sources=["measure", "craft upper_receiver + forearm_vents", "merge reads"])

part(id="lower_receiver", display="Lower receiver (trigger housing; one moulding with the magwell, guard, grip and end "
     "block)", bone="body", process="P-round", joint={"type": "seam", "parent": "upper_receiver", "gap_mm": [0.3, 0.5],
     "depth_mm": 0.6}, slot=SLOT_FURN, finish=F_POLY, texel_class="B",
     box_M={**boxM("receiver_lower"), "Y": [W_REC_R, W_REC_L]},
     dims={"seam_Z": D["receiver"]["upper_lower_seam_Z"]["mm"], "front_tab_top_Z": D["receiver"]["lower_front_tab_top_Z"]["mm"],
           "width": W_REC, "width_note": "the lower is not seen from the top; its trigger-housing sides are set in 0.8 per side under "
           "the upper's (the split reads as a step, R43); the end block keeps its own spec width"},
     construction="One polymer moulding: trigger housing, integral magwell, integral trigger guard, integral pistol grip "
     "and the integrated backplate (the end block). Front hooked lugs engage the upper's support bolts; the rear is held "
     "by one removable locking pin through the end block. Selector seat bosses (1.0 mm proud, round) on both sides. "
     "Design seam 0.3-0.5 mm wide, 0.6 deep along the drawn upper/lower line (V-tongue at the front, as traced); the "
     "housing's sides 0.8 under the upper's, the magwell flaring out of the housing on a 35 deg funnel (R43).",
     features=[{"name": "pin_behind_magwell", "side": "both (through pin)",
                "XZ": D["face_features"]["pin_lower_rear_of_magwell"]["centre_XZ"],
                "XZ_RIGHT": RF["pin_lower_rear_of_magwell"]["centre_XZ"], "head": "flush steel ring dia %.1f" % sc(7.8, 1)},
               {"name": "selector_seats", "side": "both", "XZ": SEL_P, "dia": round(SEL["ring_diameter"]["mm"] + 2.0, 1), "proud": 1.0},
               {"name": "oblong_recess", "side": "left", "X": D["face_features"]["recess_oblong"]["X"],
                "Z": D["face_features"]["recess_oblong"]["Z"], "shape": "stadium pocket %.1f x %.1f, 0.8 deep, R 0.3 " % (sc(11.8, 1), sc(4.0, 1)) +
                "rim (drawn on the LEFT only; the RIGHT shows nothing there)"},
               {"name": "seam_boss", "side": "left", "XZ": D["face_features"]["seam_boss_ring"]["centre_XZ"],
                "dia": sc(16.4, 1), "proud": 1.0, "note": "round boss straddling the upper/lower seam behind and above the "
                "selector hub (LEFT), one moulded pad with the selector seat (R 3.0 waist fillets, the seat's height, "
                "R43); the seam steps around it; its pin head at "
                + str(D["face_features"]["seam_boss_pin"]["centre_XZ"]) + " (RIGHT: two plain heads instead, see "
                "pins_fasteners)"}],
     wear="thumb-arc polish around the selector seat; edge whitening",
     trace=tref("receiver_lower"), side_profile_M=profile("receiver_lower"), authority="LEFT", confidence="high",
     sources=["measure", "craft lower_receiver", "RP19"])

part(id="magwell", display="Magazine well (integral with the lower)", bone="body", process="P-round",
     joint={"type": "integral", "parent": "lower_receiver"}, slot=SLOT_FURN, finish=F_POLY,
     texel_class="C outside / E inside (seen with the mag out)",
     box_M={**boxM("mag_well"), "Y": [-MW_OUT_LIP / 2.0, MW_OUT_LIP / 2.0]},
     dims={"front_face_X": D["mag_well"]["front_face_X"]["mm"], "lip_lower_edge_front_XZ": lf,
           "lip_lower_edge_rear_XZ": lr, "lip_slope_deg": D["mag_well"]["lip_slope_deg"],
           "outer_width_body": MW_OUT_BODY, "outer_width_lip": MW_OUT_LIP,
           "outer_width_rule": "R31: the 3/4 view's magwell-lip / magazine front-face width ratio (%.3f, view-angle "
                               "free) x the magazine thickness; the body is the lip minus the 2 x 2.0 flare" % MW_RATIO,
           "inner_width": round(MAG_T + 0.6, 1),
           "inner_foreaft": round(MAG_FA + 0.6, 1), "wall": MW_WALL, "flare_per_side": [1.5, 2.0],
           "flare_height": sc([8.0, 10.0], 1), "top_shelf_above_seated_mag": [1.0, 2.0], "inner_draft_deg": 1.0,
           "rear_wall": {"inner_face": "magazine rear face + %.1f" % MW_CLR, "thickness": MW_WALL,
                         "outer_face_line_XZ": "X = %.4f Z + %.2f (parallel to the magazine's rear face)" % (
                             RE["dX_dZ"], RE["X_at_Z0"] - MW_CLR - MW_WALL),
                         "outer_face_X_at_paddle_top_and_lip": [round(WALL_OUT(PAD_TOP_Z), 2),
                                                                round(WALL_OUT(LIP_REAR_Z), 2)],
                         "drawn_rear_line": "the sheet's magwell rear line (X ~%.0f at Z %.0f) is kept as a 0.3 mm " % (sc(452), sc(-60)) +
                                            "moulded step on the outer face; the wall itself follows the magazine"},
           "catch_window": {"in": "rear wall", "Z": [round(NOTCH_Z - 6.0, 1), round(NOTCH_Z + 4.0, 1)],
                            "width_Y": round(PAD_WIDTH - 2.0, 1), "note": "the paddle's nose passes through it to the notch"},
           "axis_rake_deg": MAG_RAKE},
     construction="Box around the magazine following its rake; the outer front face continues the diagonal step from "
     "the fore-end (traced). The drawn lip band is the insertion flare: the mouth widens 1.5-2.0 mm per side over its "
     "lowest 8-10 mm with an R 1.5 rolled lip. Inner walls 1 deg draft opening downward; 0.3 mm per side to the "
     "magazine. NO guide ribs (the magazine's ladder is recessed, RP21). Catch window in the rear wall for the paddle "
     "nose; hard top shelf (feed-ramp ledge) above the seated magazine. Outer width: 3/4 view reads %.1f +-%.1f at the "
     "lip; built %.1f at the lip, %.1f above (inner + 2 x the %.1f wall; + 2 x 2.0 flare), checked by the 3/4 L2 gate." % (
         sc(48.9, 1), sc(7.3, 1), MAG_T + 0.6 + 2 * MW_WALL + 4.0, MAG_T + 0.6 + 2 * MW_WALL, MW_WALL),
     wear="insertion scratch fan into the mouth; lip whitening; support-hand polish on the front face",
     trace=tref("mag_well"), side_profile_M=profile("mag_well"), authority="LEFT (outline; the old trace key "
     "'mag_release' box X 449-462 is now part of mag_well: check fix C1), 3/4 (width)",
     confidence="high (outline), low (width)", ruling="RP21", sources=["measure", "craft magwell", "RP21"])

part(id="trigger_guard", display="Trigger guard (integral polymer loop)", bone="body", process="P-round",
     joint={"type": "integral", "parent": "lower_receiver"}, slot=SLOT_FURN, finish=F_POLY, texel_class="C",
     box_M={**boxM("trigger_guard"), "Y": sc([-6.0, 6.0], 1)},
     dims={"length": D["trigger_guard"]["length"]["mm"], "bottom_Z": D["trigger_guard"]["bottom_Z"]["mm"],
           "opening": sc([62.2, 35.4], 1), "bar_width_Y": sc(12.0, 1), "inner_corner_R": [6.0, 8.0], "edge_R": [1.5, 2.0],
           "front_leg": {"X": [GUARD_OPENING_FRONT_X, round(PAD_REAR_X - 0.3, 2)], "thickness_X": GUARD_LEG,
                         "note": "behind the paddle slot; the opening's front edge as drawn"},
           "paddle_clevis": {"Z": [round(PAD_TOP_Z, 1), round(PAD_PIVOT[1] - 4.0, 1)], "ear_thickness_Y": 2.0,
                             "width_Y": round(PAD_WIDTH + 2 * 0.3 + 2 * 2.0, 1),
                             "note": "two ears of the lower straddle the paddle's top and carry its pin; below them the "
                                     "paddle is open on both sides (visible in both side views)"}},
     construction="Heavy integral loop (no seam): bottom bar and legs as traced, large rectangular opening with R 6-8 "
     "corners (gloved finger).", ruling="RP12", wear="bottom whitening; inside front polished by the finger",
     trace=tref("trigger_guard"), side_profile_M=profile("trigger_guard", 0.2), authority="LEFT", confidence="high",
     sources=["measure", "craft trigger_guard"])

part(id="pistol_grip", display="Pistol grip (integral) + grip cover", bone="body", process="P-round",
     joint={"type": "integral", "parent": "lower_receiver"}, slot=SLOT_FURN, finish=F_POLY + " + " + F_STIP,
     texel_class="B", box_M={**boxM("grip"), "Y": [-16.0, 16.0]},
     dims={"axis_rake_deg_from_vertical": GRIP_RAKE, "foreaft_perpendicular_median": GRIP_WIDTH_FOREAFT,
           "width_Y": 32.0, "width_note": "unseen on the sheet: real polymer SMG grips 31-33 (craft norm; absolute, R26)",
           "bottom_Z": D["grip"]["bottom_Z"]["mm"], "front_strap_R": sc([9.0, 10.0], 1), "back_strap_R": sc([12.0, 14.0], 1),
           "base_lip_proud": 3.0, "cover_height": sc(9.0, 1), "cover_seam": [0.3, 0.5],
           "stipple_panel": {"top_inset_frac": 0.20, "bottom_inset_frac": 0.12, "strap_inset": 5.0,
                             "border_step": [0.5, 0.6], "border_break": 0.3,
                             "stipple": "normal map only: pebbles 0.5-0.8 pitch, 0.1-0.15 tall"}},
     construction="Integral grip: rounded-oblong section, beaver-tail web at the top rear, flared base lip; the lowest "
     "~9 mm is the separate grip cover (real part) with a 0.3 x 0.5 seam and a flat plain bottom (R 1 rim). Stipple "
     "panel on both sides: the border in geometry, the stipple in the normal map.", ruling="RP13",
     wear="front/back strap and web polished; stipple crowns polished; base lip whitened",
     trace=tref("grip"), side_profile_M=profile("grip"), authority="LEFT", confidence="high (outline), medium (width)",
     sources=["measure", "craft pistol_grip"])

part(id="end_block", display="End block (the lower's integrated backplate; receiver hinge block)", bone="body",
     process="P-round", joint={"type": "integral", "parent": "lower_receiver", "seam_front_mm": [0.3, 0.5]},
     slot=SLOT_FURN, finish=F_POLY, texel_class="B", box_M={**boxM("hinge_block"), "Y": [HINGE_R, HINGE_L]},
     dims={"length": ST["hinge_block_length"]["mm"], "locking_pin": {"XZ": D["face_features"]["pin_hinge_block"]["centre_XZ"],
           "dia": sc(6.6, 1), "side": "left head (flush steel, 0.5 chamfer); right: square-ish plain end %.1f x %.1f at " % (sc(4.7, 1), sc(4.7, 1)) +
           str(RF["locking_pin_end"]["centre_XZ"]) + " (RIGHT read)"},
           "top_frame": {"X": sc([283.5, 310.4], 1), "Y": sc([-19.0, 19.0], 1), "window_X": sc([289.4, 304.6], 1),
                         "window_Y": sc([-14.0, 14.0], 1),
                         "shape": "raised D-shaped rim (round end to the rear) on top of the end block and the rail's "
                                  "rear plain zone, around a rectangular recess 2.0 deep (dark, not see-through)",
                         "source": "TOP (scratch/checker/z_top_rear.png; panel px x 336-359, y 257-292); Y centred "
                                   "(TOP reads -24.0..+17.5 with the panel's slight obliquity)"},
           "latch_lug": LATCH["lug"]},
     construction="Tall block from the lower to the receiver top (buffer and recoil-spring support inside). Its rear "
     "face carries the receiver-side hinge knuckles at the right rear corner and, at the left rear above the drawn "
     "see-through gap, the latch lug (bore along Y, exit slot rearward). On top: the D-shaped frame drawn in TOP.",
     ruling="RP20", wear="corner whitening", trace=tref("hinge_block"), side_profile_M=profile("hinge_block"),
     authority="LEFT", confidence="high", sources=["measure", "craft", "RP18"])

part(id="charging_handle", display="Charging handle (non-reciprocating cocking lever: knob, arm, slide)",
     bone="charging_handle", process="M-round (knob), M-chamfer (arm, slide)",
     joint={"type": "sliding", "parent": "body", "clearance_mm": [0.15, 0.40]}, slot=SLOT_METAL, finish=F_STEEL,
     texel_class="B", box_M={"X": [ARM_BLOCK["X"][0], round(KNOB_C[0] + KNOB_D / 2, 1)], "Z": [ARM_BLOCK["Z"][0],
     round(KNOB_C[1] + KNOB_D / 2, 1)], "Y": [W_REC_L, KNOB_TIP_Y]},
     dims={"knob_dia": KNOB_D, "knob_centre_XZ": KNOB_C, "knob_centre_Y": KNOB_CY, "knob_tip_Y": KNOB_TIP_Y,
           "neck_dia": NECK_D, "arm_rod": ARM_ROD, "arm_rear_block": ARM_BLOCK, "arm_clearance_to_wall": 0.2,
           "travel_minus_X": CH_TRAVEL, "lock_rotation_about_X_deg": [0.0, LOCK_DEG],
           "lock_axis": {"YZ": list(LOCK_PIN), "what": "roll pin dia 3.0 through the slide's upper inboard corner, "
                         "parallel to X; the lever pivots on it, the slide does NOT rotate (real pattern)",
                         "why": "with this axis every point of the outer arm moves outward over the lock (min %+.3f mm); "
                                "the old axis (Y 20, Z 21) drove the arm's upper inner edge 1.24 mm through the wall"
                                % ARM_MIN_DY},
           "lock_motion": {"knob_rise": KNOB_RISE, "neck_rise_at_wall_inner_face": NECK_RISE_IN,
                           "neck_rise_at_wall_outer_face": NECK_RISE_OUT, "notch_rise_above_slot_top": NOTCH_RISE,
                           "arm_min_outward_motion": ARM_MIN_DY},
           "slide": SLIDE, "wall_inner_face_Y": W_IN_L, "slot": {"X": SLOT_X, "Z": SLOT_Z}},
     construction="Ball knob on a dia 6 neck through the slot in the left wall; the drawn rod and rear block behind it "
     "are the lever's outer arm, riding 0.2 mm off the wall (the TOP shows the block %.1f mm proud, so no recess) and " % ARM_BLOCK["proud_of_wall"] +
     "moving with the knob. Inside: a steel slide in a moulded guide above the barrel with a hook that pushes the "
     "bolt's charging lug; its own return spring (not modelled). At rest the knob is at the FRONT of its slot; pulled "
     "%.1f mm back, the lever pivots %.0f deg about the roll pin in the slide (Y %.1f, Z %.1f; the slide itself does not "
     "rotate) so the neck rises %.1f mm into the lock notch at the slot's rear and the knob %.1f mm; the outer arm swings "
     "outward, away from the wall. When fired, the bolt leaves the slide behind." % (
         CH_TRAVEL, LOCK_DEG, LOCK_PIN[0], LOCK_PIN[1], NECK_RISE_IN, KNOB_RISE),
     ruling="RP3", wear="polished knob crown with a bright rim; polished slot lips along the travel",
     trace={"file": TRL, "keys": ["face_features.charging_handle_knob", "face_features.charging_handle_rod",
            "face_features.charging_handle_rear_block"], "view": "LEFT", "frame": "M",
            "note": "the measurer's hand outlines under-read the knob (12.9) and rod (3.2 tall); L3 uses this part's dims"},
     authority="LEFT + TOP (knob size and protrusion); real pattern (construction)", confidence="medium",
     sources=["measure", "craft charging_handle", "merge re-read zL_knob.png"])

part(id="bolt", display="Bolt (blowback block, visible through the port)", bone="bolt", process="M-chamfer",
     joint={"type": "sliding", "parent": "body", "clearance_mm": [0.15, 0.40]}, slot=SLOT_METAL, finish=F_BOLT,
     texel_class="B (port-visible right face) / E", box_M={"X": [round(BOLT_REST_FACE_X - sc(110.0, 1), 1), BOLT_REST_FACE_X],
     "Z": BOLT_Z, "Y": sc([-13.0, 13.0], 1)},
     dims={"face_X_rest": BOLT_REST_FACE_X, "face_X_back": BOLT_BACK_FACE_X, "travel": CH_TRAVEL, "width": sc(26.0, 1),
           "length": sc(110.0, 1), "case_head_boss_dia": 12.0, "firing_pin_hole_dia": 1.5,
           "extractor": {"size": sc([5.0, 25.0], 1), "hook_over_face": 1.0, "side": "right"},
           "thumb_recess": {"size": sc([16.0, 9.0], 1), "depth": 1.5, "side": "right", "centre_X_rest": sc(481.0, 1),
                            "note": "centred in the port at rest (port X %.1f-%.1f)" % tuple(RF["ejection_port"]["X"])},
           "guide_grooves": "both lower edges, 0.2 mm per side on the receiver rails", "chamfer": 0.4},
     construction="Heavy rectangular steel block; the upper section overhangs rearward with the recoil-spring guide bore "
     "at the top front; bolt face with the case-head boss and firing-pin hole; extractor claw inset in the right face; "
     "the real thumb recess (oval scallop) on the right face; charging lug on the top front; guide grooves riding the "
     "receiver's steel rails. Milling passes in roughness only.", ruling="RP5",
     wear="sliding polish on the flanks (bare steel); soot at the face", trace=None,
     authority="RIGHT (port) + real pattern", confidence="medium", sources=["craft bolt", "measure (breech X)"])

part(id="ejection_port_and_catch", display="Ejection port (right) and the integral stock catch", bone="body",
     process="P-round", joint={"type": "integral", "parent": "upper_receiver"}, slot=SLOT_FURN, finish=F_POLY,
     texel_class="B / E inside", box_M={"X": [PORT["X"][0], CATCH["X"][1]], "Z": [CATCH["Z"][0], PORT["Z"][1]],
     "Y": [R_WALL - CATCH_PROUD, R_WALL]},
     dims={"port_X": PORT["X"], "port_Z": PORT["Z"], "port_corner_R": 2.0, "rear_edge_deflector_chamfer_deg": 45,
           "catch_X": CATCH["X"], "catch_Z": CATCH["Z"], "catch_proud": CATCH_PROUD, "catch_lip": CATCH_LIP,
           "engages": "the stock's retention lug (stock_frame.dims.retention_lug), folded"},
     construction="Port through the right wall only, wall reveal shown, dark interior (bolt, breech, feed lips; class E). "
     "The drawn vertical boss in front of the port (the measurer's Q5) is the real pattern's integral stock catch: "
     "moulded with the upper, 3 mm proud. Its rear edge carries a hooked lip (overhang 1.5 rearward, 1.5 thick, flush with "
     "the outer face); folded, the barb of the stock's retention lug sits in the pocket under that lip (engagement "
     "%.1f mm in X, gate F3). The small drawn lever shape on it stays as moulded relief." % F3_ENGAGE_X, ruling="RP6",
     wear="polished catch lip; light soot at the port's rear edge",
     trace={"file": TRR, "keys": ["face_features.ejection_port", "face_features.boss_front_of_port"], "view": "RIGHT",
            "frame": "M (RIGHT's own)"}, authority="RIGHT", confidence="high (port), medium (catch)",
     sources=["measure RIGHT", "craft ejection_port_and_stock_catch"])

part(id="barrel", display="Barrel (+ collar ring at the receiver face)", bone="body", process="M-chamfer",
     joint={"type": "fixed", "parent": "upper_receiver", "pin": "transverse roll pin (hidden)"}, slot=SLOT_METAL,
     finish=F_STEEL, texel_class="D exposed / E inside",
     box_M={"X": [BREECH_X, CROWN_X], "Z": [round(BORE_Z - sc(12.4), 1), round(BORE_Z + sc(12.4), 1)], "Y": sc([-12.4, 12.4], 1)},
     dims={"breech_X": BREECH_X, "crown_X": CROWN_X, "length": BARREL_LEN, "bore_dia": 11.4,
           "bore_depth_visible_min": 22.8, "exposed_X": D["barrel"]["exposed_X"],
           "collar_ring": {"X": [D["barrel"]["exposed_X"][0], sc(632.4, 1)], "dia": D["barrel"]["front_collar_diameter"]["mm"]},
           "neck": {"X": [sc(632.4, 1), D["barrel"]["device_seat_X"]["mm"]], "dia": D["barrel"]["neck_diameter"]["mm"]},
           "hidden_od": sc(17.7, 1)},
     construction="Phosphated steel barrel pinned in the upper. Visible: the collar ring seated in the receiver face, "
     "then the neck (thread collar) to the device seat. Bore .45-class, dark, >= 2 calibres deep from the device front; "
     "polygonal rifling as texture only. Hidden length %.0f mm (sheet feed geometry, open question Q2)." % BARREL_LEN,
     wear="edge brightening on the collar ring", trace=tref("barrel"), side_profile_M=profile("barrel", 0.2),
     authority="LEFT", confidence="high (visible), medium (hidden length)", sources=["measure", "craft barrel", "merge"])

part(id="muzzle_device", display="Muzzle device (6-slot cage flash hider + jam-nut collar)", bone="muzzle_device",
     process="M-chamfer", joint={"type": "fixed", "parent": "barrel"}, slot=SLOT_METAL, finish=F_STEEL, texel_class="D",
     box_M={"X": [D["barrel"]["device_seat_X"]["mm"], OVERALL], "Z": [round(BORE_Z - DEVICE_OD / 2, 1),
            round(BORE_Z + DEVICE_OD / 2, 1)], "Y": [-DEVICE_OD / 2, DEVICE_OD / 2]},
     dims={"length": D["muzzle_device"]["length"]["mm"], "od": DEVICE_OD, "od_TOP": DEVICE_W_TOP,
           "cage_X": [sc(652.2, 1), OVERALL], "rear_collar_X": [D["barrel"]["device_seat_X"]["mm"], sc(652.2, 1)],
           "groove_ring_width": sc(2.0, 1), "slots": {"count": 6, "spacing_deg": 60, "one_centred_on_each_side": True,
           "width": sc(4.0, 1), "length": sc(26.0, 1), "ends": "round"}, "front_rim_length": sc(5.0, 1), "front_chamfer_out": 0.6,
           "bore_chamfer": 1.0, "inner_dia": 13.5, "wrench_flats": "two 3 mm flats on the underside of the collar only"},
     construction="Slotted cage, open front, six through-slots at 60 deg with one centred on each side (3 slots in the "
     "side views, 2 from the top, matching the sheet), solid front rim, rear collar with the drawn groove ring. Seams "
     "read at 8x (scratch/merge/zL_muzzle.png).", ruling="RP16", wear="soot gradient from each slot and the crown; "
     "bright front rim", trace=tref("muzzle_device"), side_profile_M=profile("muzzle_device", 0.2),
     authority="LEFT + TOP (agree within 3 %)", confidence="high", sources=["measure (outline)", "craft", "merge"])

part(id="top_rail", display="Top rail (1913 profile, gunlib.rail_1913)", bone="body", process="M-chamfer",
     joint={"type": "butt", "parent": "upper_receiver", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_STEEL,
     texel_class="B for X < 400 (rear, seen at ADS) / C forward (check fix C15; class A is the sights only)",
     box_M={"X": [TOPF_X0, tr["X"][1]], "Z": [RAIL_UNDER_Z, RAIL_TOP_Z], "Y": sc([-17.5, 17.5], 1)},
     dims={"length": round(tr["X"][1] - TOPF_X0, 1), "rear_end_X": TOPF_X0,
           "rear_end_rule": "R32: the end block's TOP-drawn D-shaped rim is the rail's machined rear end (round in plan, "
                            "with the drawn rectangular pocket 2.0 deep in its rear relief flat); the rail starts at the "
                            "D's rear end and sits on the end block's top there", "top_Z": RAIL_TOP_Z, "underside_Z": RAIL_UNDER_Z,
           "height": round(RAIL_TOP_Z - RAIL_UNDER_Z, 1), "dovetail_width": 21.2, "flank_deg": 45,
           "base_flange": {"width": sc(35.0, 1), "height": 4.0, "note": "TOP band (RP14)"},
           "slot_width": SLOT_W, "slot_pitch": PITCH, "slot_depth": 3.0, "slot_depth_drawn": tr["slot_depth_side_view"]["mm"],
           "lattice_slot0_X": round(SLOT0_X, 2), "cut_slot_indices": CUT_SLOTS, "cut_slot_centres_X": SLOT_X_LIST,
           "teeth_drawn": tr["n_teeth_visible_total"] - 1, "teeth_built": n_teeth,
           "toothed_zone_X": [round(tooth0 - SLOT_W, 2), round(tooth0 + span + SLOT_W, 2)],
           "plain_zones": {"rear_X": [TOPF_X0, round(REAR_BASE[0], 1)],
                           "front_relief_X": [round(tooth0 + span + SLOT_W, 2), round(FRONT_BASE[0], 1)],
                           "rule": "as drawn: the rail top is at the slot-floor level there (a milled relief flat); "
                                   "the dovetail flanks continue"},
           "screws": {"count": 2, "head": "low button head dia 4.8 (inside the 5.24 slot: no tooth notch)",
                      "head_dia": 4.8, "in_slots": [CUT_SLOTS[3], CUT_SLOTS[-3]], "head_below_slot_floor": 0.3,
                      "note": "check fix C13: 8.5 mm heads would cut 1.6 mm into each neighbouring tooth flank"},
           "chamfer": [0.3, 0.5]},
     construction="Separate steel rail from gunlib.rail_1913 on a base flange, screwed to the moulded hard points with "
     "two counterbored low button-head screws (dia 4.8) in two slot floors. Slots only where the sheet draws teeth "
     "(standard pitch: "
     f"{n_teeth} teeth for the {tr['n_teeth_visible_total'] - 1} drawn), plus one hidden lug slot under each sight base.",
     ruling="RP14", wear="bright slot edges and flank crests; grime in the slot roots", trace=tref("top_rail"),
     side_profile_M=profile("top_rail", 0.2), authority="LEFT (length, height, toothed zone); standard (profile)",
     confidence="high", sources=["measure", "craft top_rail", "plan section 5", "line standard 5.4"])

part(id="lower_rail", display="Lower rail (short 1913 section, facing down)", bone="body", process="M-chamfer",
     joint={"type": "butt", "parent": "upper_receiver", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_STEEL,
     texel_class="C", box_M={"X": lrl["X"], "Z": [LR_Z, lrl["top_Z_seam"]["mm"]], "Y": [-12.0, 12.0]},
     dims={"length": lrl["length"]["mm"], "bottom_Z": LR_Z, "top_seam_Z": lrl["top_Z_seam"]["mm"], "slots": LR_N,
           "slot_centres_X": LR_SLOTS_X, "slots_drawn": lrl["n_teeth_visible"], "profile": "as the top rail",
           "screws": 2},
     construction="Short rail from the same module, %d slots at the standard pitch centred on the measured length "
     "(end webs %.1f mm; check fix C8: 8 slots left 0.45 mm end walls)." % (LR_N, LR_SLOTS_X[0] - SLOT_W / 2 - lrl["X"][0]),
     ruling="RP14", wear="as the top rail; support-hand polish", trace=tref("lower_rail"),
     side_profile_M=profile("lower_rail", 0.2), authority="LEFT", confidence="high", sources=["measure", "craft"])

part(id="sight_rear", display="Rear flip sight (rail clamp, diopter aperture)", bone="sight_rear",
     process="M-chamfer (base) + M-round (ears)", joint={"type": "hinge", "parent": "body", "clearance_mm": [0.10, 0.30]},
     slot=SLOT_METAL, finish=F_STEEL, texel_class="A",
     box_M={"X": D["sights"]["sight_rear"]["X"], "Z": [RAIL_TOP_Z - 6.0, D["sights"]["sight_rear"]["top_Z"]["mm"]],
            "Y": [-14.0, round(W_REC_L + sc(6.5), 1)]},
     dims={"base_X": REAR_BASE, "leaf_head_X": D["sights"]["sight_rear"]["head_X_span_1to6mm_below_top"],
           "top_Z": D["sights"]["sight_rear"]["top_Z"]["mm"], "aperture_centre_XZ": APERTURE, "aperture_dia": 2.0,
           "aperture_disc_dia": 10.0, "eye_side_countersink_deg": 45, "pivot_XZ": REAR_PIVOT, "pivot_pin_dia": 3.0,
           "pivot_rule": "the leaf's front-lower corner (it folds forward); base = U-channel, floor 2.0 above the "
                         "rail top, the leaf between its cheeks",
           "fold": "forward (about Y)", "fold_rotation_Y_deg": 90.0, "folded_max_Z": REAR_FOLDED_TOP,
           "folded_max_Z_over_rail_top": round(REAR_FOLDED_TOP - RAIL_TOP_Z, 1),
           "lug_slot": 0, "cross_bolt_head": "left, XZ (%.1f, %.1f)" % (sc(329.3), sc(48.9)),
           "windage_drum": {"side": "LEFT", "X": sc([312.1, 355.3], 1), "proud_of_body": sc(6.5, 1),
                            "note": "TOP lateral feature + 3/4 view (left side) show it on the left; plain, knurl in the "
                                    "normal map, no ticks"}},
     construction="Rail-clamp base (a U-channel) with its recoil lug in slot 0 and a transverse cross-bolt (head left, "
     "captive jaw/nut right); rectangular leaf with two protective ears framing a round aperture disc, pinned at its "
     "front-lower corner between the channel's cheeks so it folds forward over the rail (folded top Z %.1f = rail top "
     "+ %.1f); spring detent on a transverse pin (no release button: none drawn)." % (
         REAR_FOLDED_TOP, REAR_FOLDED_TOP - RAIL_TOP_Z), ruling="RP15", wear="bright ear edges",
     trace=tref("sight_rear"), side_profile_M=profile("sight_rear", 0.2), authority="LEFT (+TOP drum)",
     confidence="medium-high", sources=["measure", "craft rear_flip_sight", "merge re-read zL_rear.png"])

part(id="sight_front", display="Front flip sight (rail clamp, post between ears)", bone="sight_front",
     process="M-chamfer (base) + M-round (ears)", joint={"type": "hinge", "parent": "body", "clearance_mm": [0.10, 0.30]},
     slot=SLOT_METAL, finish=F_STEEL, texel_class="A",
     box_M={"X": D["sights"]["sight_front"]["X"], "Z": [RAIL_TOP_Z - 6.0, D["sights"]["sight_front"]["top_Z"]["mm"]],
            "Y": [-16.2, 14.0]},                     # R40: the TOP panel's knob (to Y -46.3) is not built
     dims={"base_X": FRONT_BASE, "head_X": D["sights"]["sight_front"]["head_X_span_1to6mm_below_top"],
           "ear_top_Z": D["sights"]["sight_front"]["top_Z"]["mm"], "post_tip_XZ": POST_TIP, "post_width": 1.85,
           "ear_thickness": [2.5, 3.0], "pivot_XZ": FRONT_PIVOT, "fold": "rearward (about Y)",
           "fold_rotation_Y_deg": -90.0, "folded_Z": FRONT_FOLDED_Z, "folded_max_Z": FRONT_FOLDED_Z[1],
           "folded_note": "the folded head's lowest point (Z %.1f) lies over the front relief flat (slot-floor level "
                          "%.1f)" % (FRONT_FOLDED_Z[0], RAIL_TOP_Z - 3.0), "lug_slot": FRONT_LUG,
           "clamp_knob_right": {"X": TV["lateral_features_gun_right_(-Y,image-up)"][0]["X"],
                                "Y_extreme": TV["lateral_features_gun_right_(-Y,image-up)"][0]["Y_extreme"],
                                "note": "TOP shows the clamp's nut end on the right as a round knob, %.1f mm proud; "
                                        "R40: not built (RIGHT and 3/4 draw none; real pattern); its X span sets the "
                                        "cross-bolt / captive nut X and the cheeks' lower rear step" % sc(16.0, 1)}},
     construction="Rail-clamp base (lug in a hidden slot, cross-bolt head left, captive hex nut right, R40); "
     "leaf with two ears and a square post between them, tip flat with a 0.2 mm break, the tip on the sight line "
     f"(Z {POST_TIP[1]}, {round(D['sights']['sight_front']['top_Z']['mm'] - POST_TIP[1], 1)} mm under the ear tops); "
     "spring detent, no button.", ruling="RP15", wear="bright ear tops",
     trace=tref("sight_front"), side_profile_M=profile("sight_front", 0.2), authority="LEFT + RIGHT (3/4 ears; the TOP knob not built, R40)",
     confidence="medium-high", sources=["measure", "craft front_flip_sight", "merge"])

part(id="selector", display="Selector (ambidextrous: one shaft, two teardrop levers)", bone="selector",
     process="M-chamfer (steel plate)", joint={"type": "hinge", "parent": "body", "clearance_mm": [0.10, 0.30]},
     slot=SLOT_METAL, finish=F_STEEL, texel_class="B",
     box_M={"X": sc([353.1, 373.7], 1), "Z": sc([-50.8, -18.1], 1), "Y": [round(W_REC_R - 5.0, 1), round(W_REC_L + 5.0, 1)]},
     dims={"pivot_XZ": SEL_P, "hub_dia": SEL["ring_diameter"]["mm"], "hub_dia_right": SEL["ring_diameter"]["mm"],
           "blade_tip_XZ_left": SEL_TIP, "blade_root_width": sc(12.0, 1), "blade_tip_width": sc(6.0, 1), "tip_R": sc(3.0, 1),
           "plate": [2.5, 3.0], "seat_boss_proud": 1.0, "edge_R": 0.8, "thumb_ledge": 0.5,
           "index_groove": [0.5, 0.3], "positions_rot_Y_deg_from_bind": SEL_ROT,
           "bind_blade_angle_deg_from_plusX": round(phi_bind, 1),
           "right_lever": "outline from the RIGHT trace (face_features.selector_lever), same hub size"},
     construction="Teardrop steel levers on both ends of one transverse shaft (one part, one bone); index line = an "
     "unpainted groove across the hub. No red dot, no pictograms, no letters. Positions SAFE / SEMI / AUTO (no burst).",
     ruling="RP7", wear="bright blade tip and hub rim; thumb-arc polish on the housing",
     trace={"file": TRL, "keys": ["face_features.selector_pivot_ring", "face_features.selector_lever"], "view": "LEFT",
            "frame": "M", "right": "trace/RIGHT_outline.json face_features.selector_*"},
     authority="LEFT (X, shape), RIGHT (right lever)", confidence="medium", sources=["measure", "craft selector"])

part(id="trigger", display="Trigger", bone="trigger", process="C-fillet", joint={"type": "hinge", "parent": "body",
     "clearance_mm": [0.10, 0.30]}, slot=SLOT_METAL, finish=F_STEEL, texel_class="C",
     box_M={**boxM("trigger"), "Y": [-3.0, 3.0]},
     dims={"width": 6.0, "face_crown_R": 8.0, "pivot_XZ": list(TRIG_PIVOT), "pull_rot_Y_deg": TRIG_PULL,
           "pivot_source": "the drawn axle head on both side views (LEFT %s, RIGHT %s)" % (
               TRIG_PIVOT, RF["trigger_axle_head"]["centre_XZ"]),
           "pull_sign": "+ about Y (Blender R_y moves points below the pivot toward -X = rearward); AR-01 ships 0..+12",
           "finger_face_XZ": [sc(409.4, 1), sc(-77.9, 1)], "reach_backstrap_to_face": D["trigger_reach_to_blade_front_face"]["mm"]},
     construction="Curved steel blade, smooth crowned face, hanging from a transverse axle at the drawn head (flush pin "
     "heads both sides, about %.0f mm above the blade's top). Pull" % sc(14.0) + " = +%.0f deg about Y: the lower end moves rearward."
     % TRIG_PULL, ruling="RP11", wear="bright face",
     trace=tref("trigger"), side_profile_M=profile("trigger", 0.15), authority="LEFT", confidence="high",
     sources=["measure", "craft trigger"])

part(id="mag_release", display="Magazine release paddle (centred, ambidextrous)", bone="mag_release",
     process="M-chamfer", joint={"type": "hinge", "parent": "body", "clearance_mm": [0.10, 0.30]}, slot=SLOT_METAL,
     finish=F_STEEL, texel_class="C",
     box_M={"X": [PAD_REAR_X, PAD_FRONT_X], "Z": [PAD_BOT_Z, PAD_TOP_Z], "Y": [-PAD_WIDTH / 2, PAD_WIDTH / 2],
            "nose_to": list(PAD_NOSE)},
     dims={"width_Y": PAD_WIDTH, "depth_X": PAD_DEPTH, "front_face_X": PAD_FRONT_X, "rear_face_X": PAD_REAR_X,
           "top_Z": PAD_TOP_Z, "bottom_Z": PAD_BOT_Z, "pivot_XZ": list(PAD_PIVOT), "pin_dia": PAD_PIN_D,
           "pivot_boss_dia": PAD_BOSS_D, "pad_R": 3.0, "release_rot_Y_deg": PAD_REL,
           "nose_tip_XZ_seated": list(PAD_NOSE), "nose_engagement": PAD_ENGAGE,
           "nose_travel_at_release": PAD_NOSE_TRAVEL, "notch_on_mag_rear_Z_seated": NOTCH_Z,
           "notch_depth": NOTCH_DEPTH,
           "drawn_lever": {"X": PAD_DRAWN[:2], "Z": PAD_DRAWN[2:], "pin_head_XZ": PAD_PIN_DRAWN,
                           "trace": "parts.mag_release (the lever drawn inside the guard's front leg)"},
           "declared_deviation": {"front_face_vs_drawn": PAD_SHIFT_FRONT,
                                  "pivot_vs_drawn_pin_head": round(PAD_PIVOT[0] - PAD_PIN_DRAWN[0], 2),
                                  "why": "the magwell's %.1f rear wall (+0.3 to the magazine)" % MW_WALL + " and the release swing "
                                         "(>= 0.10 to the wall down to the lip) set the paddle's front face; the "
                                         "sheet draws the lever over the wall's position (an AI-sheet contradiction "
                                         "on a small part: the real pattern decides construction)",
                                  "L3": "the pin head <= 2 px and the paddle's top and bottom Z <= 2 px are gated; the "
                                        "fore-aft faces are checked against these dims (+-0.05), not the drawn outline",
                                  "L2": "trace key parts.mag_release: built paddle inside the drawn lever's X-Z box "
                                        "extended by the declared shift; the per-part contour rule is waived"}},
     construction="One centred steel paddle (%.1f wide, %.1f deep) hanging in an open slot between the magwell's rear "
     "wall and the trigger guard's front leg, its pin (dia %.1f) carried by a two-ear clevis of the lower at the drawn "
     "pin head (%.1f, %.1f). Its upper nose runs up through the catch window in the magwell's rear wall into the notch "
     "in the magazine's rear face (tip X %.1f at Z %.1f, engagement %.1f). Pushed FORWARD (%.0f deg about Y: the lower "
     "end forward) the nose swings %.1f mm rearward, out of the notch. The paddle is seen below the clevis on both "
     "sides, %.1f mm behind the drawn lever's front edge (declared)." % (
         PAD_WIDTH, PAD_DEPTH, PAD_PIN_D, PAD_PIVOT[0], PAD_PIVOT[1], PAD_NOSE[0], PAD_NOSE[1], PAD_ENGAGE, PAD_REL,
         PAD_NOSE_TRAVEL, -PAD_SHIFT_FRONT), ruling="RP8",
     wear="bright pad face", trace=tref("mag_release"), side_profile_M=profile("mag_release", 0.15),
     authority="LEFT (drawn lever + pin head; re-traced, check fix C1); real pattern (mechanism, fore-aft position)",
     confidence="medium", sources=["measure", "craft", "check C1"])

part(id="stock_hinge", display="Stock hinge (right-rear corner axle) and latch housing (left)",
     bone="stock (stock-side knuckle, latch housing, button) / body (receiver knuckles, axle)",
     process="M-chamfer (axle, bushings), P-round (housings)", joint={"type": "hinge", "parent": "body",
     "clearance_mm": [0.10, 0.30]}, slot=SLOT_FURN + " (housings) + " + SLOT_METAL + " (axle)", finish=F_POLY + " + " + F_STEEL,
     texel_class="B", box_M={**boxM("stock_hinge_knuckle"), "Y": [round(HINGE_Y - KNUCKLE_OD / 2, 1),
                                                                   round(LATCH_Y_L + LATCH_BUTTON_PROUD, 1)]},
     dims={"axis_X": HINGE_X, "axis_Y": HINGE_Y, "axis": "vertical (+Z)", "axle_dia": 6.0, "knuckle_od": KNUCKLE_OD,
           "knuckles": "two receiver-side (top, bottom; steel bushings) + one stock-side centre knuckle",
           "knuckle_proud_of_right_wall_TOP": KNUCKLE_PROUD_R,
           "latch": LATCH,
           "fold_rot_Z_deg": 180.0, "fold_direction": "toward the gun's right (+Z rotation, CCW seen from above)",
           "stock_knuckle_X": BOX["stock_hinge_knuckle"][:2], "gap_line_X": HINGE_X},
     construction="Corner hinge at the RIGHT rear (real pattern: folds to the right). The axle sits at Y "
     f"{HINGE_Y} ({round(HINGE_Y - R_WALL, 2)} mm inside the right wall's plane, resolution R19): the knuckle stack "
     f"stands ~{KNUCKLE_PROUD_R:.0f} mm proud of the right side in the TOP view, inside the drawn side-view outline. "
     "The stock-side arm doglegs from the knuckle to the stock mid-plane. "
     "LEFT: the drawn cylindrical boss is the latch housing with the oval release button; its drawn split lines are the "
     "button outline and the knuckle splits. The latch: a necked dia 4.0 bolt along Y at (%.1f, %.1f), sprung outward, "
     "sits 2.0 mm into the bore of the end block's rearward lug (above the see-through gap); pressing the button 2.0 "
     "brings the dia 2.5 neck into the lug and it leaves through the lug's rearward exit slot as the stock folds "
     "(gate F6)." % LATCH_AXIS_XZ, ruling="RP1, RP2",
     wear="button face polished; knuckle edges whitened; grime in the splits",
     trace=tref("stock_hinge_knuckle"), side_profile_M=profile("stock_hinge_knuckle"), authority="LEFT (outline); real "
     "pattern (construction)", confidence="medium", sources=["measure", "craft stock_hinge_and_latch", "merge R19"])

part(id="stock_frame", display="Skeleton stock frame (one-piece moulding)", bone="stock", process="P-round",
     joint={"type": "hinge child", "parent": "stock_hinge"}, slot=SLOT_FURN, finish=F_POLY, texel_class="B (top strut, "
     "neck) / C", box_M={"X": [ST["parts_X_Z"]["stock_rear_upright"][0], ST["parts_X_Z"]["stock_neck"][1]],
     "Z": [ST["parts_X_Z"]["stock_lower_strut"][2], ST["parts_X_Z"]["stock_top_strut"][3]],
     "Y": [-FRAME_W / 2, FRAME_W / 2]},
     dims={"top_strut": ST["struts"]["stock_top_strut"], "lower_strut": ST["struts"]["stock_lower_strut"],
           "web": ST["stock_web"], "rear_upright": ST["stock_rear_upright"], "neck": ST["stock_neck"],
           "width_Y": FRAME_W, "width_note": "top face of the top strut in TOP; TOP is oblique at the stock (the lower "
           "strut shows beside the top strut), so the traced 35-45 mm is not a width",
           "windows": "the two traced see-through holes (LEFT silhouette holes)", "opening_border_step": [0.8, 1.0],
           "opening_border_inset": 1.5, "opening_inner_R": 1.5, "draft_deg_each_way": 1.0,
           "through_holes": [{"XZ": sc([40.1, 9.5], 1), "dia": sc(6.0, 1), "use": "plain"},
                             {"XZ": sc([40.1, -65.5], 1), "dia": sc(6.0, 1), "use": "SlingRear"}],
           "neck_slot": {"X": sc([188.9, 219.4], 1), "Z": sc([-4.7, 0.0], 1), "note": "drawn dark slot = the locking-pin storage "
                         "hole (real pattern), built as drawn"},
           "retention_lug": LUG},
     construction="One-piece polymer frame symmetric about its mid-plane (parting witness around the middle, texture "
     "only): top strut, lower strut, slanted web, rear upright and the solid neck to the hinge, all as traced; solid "
     "struts with flat faces (both faces seen when folded); raised borders around the openings. No cheek piece (not "
     "drawn). Folded retention (check fix C3): a moulded lug on the rear upright's right face just ahead of the pad "
     "(X %.1f-%.1f, Z %.1f..%.1f, tip Y %.1f = %.1f proud of the pad's side) whose barb snaps under the port catch's "
     "rear lip when folded; not drawn on the sheet (open question Q17)." % (
         LUG["body_X_ext"][0], LUG["body_X_ext"][1], LUG_Z[0], LUG_Z[1], LUG["tip_Y_ext"], LUG["proud_of_pad_side_ext"]), wear="cheek-weld polish on the top strut (left); whitening on the outer corners and the toe",
     trace=tref("stock_top_strut", "stock_lower_strut", "stock_neck", "stock_web", "stock_rear_upright"),
     side_profile_M=[profile(k) for k in ("stock_top_strut", "stock_lower_strut", "stock_neck", "stock_web",
                                          "stock_rear_upright")],
     authority="LEFT (outline), TOP (top-strut width)", confidence="high (outline), medium (width)",
     sources=["measure", "craft stock_frame", "merge"])

part(id="butt_pad", display="Butt pad (rubber, ribbed rear face)", bone="stock", process="P-round (rubber)",
     joint={"type": "seam", "parent": "stock_frame", "gap_mm": [0.2, 0.4]}, slot=SLOT_FURN, finish=F_RUB,
     texel_class="C", box_M={"X": PAD["X"], "Z": PAD["Z"], "Y": [-PAD_W / 2, PAD_W / 2]},
     dims={"thickness_X": PAD["thickness_side"]["mm"], "height": PAD["height"]["mm"], "width": PAD_W,
           "width_note": "craft read 55-59 of the pad's top face; TOP trace 67.3 includes the oblique side",
           "ribs": "rear face, as geometry: count and ends from the LEFT trace (the silhouette shows them); depth 1.2, "
                   "R 0.6 crests", "wrap_lip": 2.0, "edge_R": [3.0, 4.0]},
     construction="Rubber pad wrapping the rear upright with a 2 mm lip; horizontal ribs on the rear face as geometry.",
     wear="dust in the rib roots; toe and heel scuffs", trace=tref("butt_pad"), side_profile_M=profile("butt_pad", 0.2),
     authority="LEFT", confidence="high (outline), medium (width)", sources=["measure", "craft butt_pad"])

part(id="magazine_body", asset="SM_SMG01_Mag (+ merged in SM_SMG01)", display="Magazine body (straight double stack, "
     "solid polymer)", bone="magazine", process="P-round", joint={"type": "seated", "parent": "magwell"},
     slot=SLOT_MAG, finish=F_MAGP, texel_class="C / E inside",
     box_M={"X": MAG["X"], "Z": [MAG["Z"][0], MAG_TOP_Z], "Y": [-MAG_T / 2, MAG_T / 2]},
     dims={"frame": "mag frame (origin = Mag socket; +Z up the insertion axis)", "rake_deg": MAG_RAKE,
           "foreaft": MAG_FA, "thickness": MAG_T, "length_along_axis": round(MAG_LEN, 1),
           "exposed_along_axis": MAG["exposed_length_along_axis"]["mm"], "top_along_axis": round(MAG_TOP_ALONG, 2),
           "floor_along_axis": round(MAG_FLOOR_ALONG, 2), "corner_R": {"front": 3.0, "rear": 2.5},
           "ladder": LADDER, "front_spine_rib": {"width": sc(6.0, 1), "proud": MAG_RIB},
           "foreaft_traced_incl_rib": MAG_FA_TRACED,
           "catch_notch": {"size": [8.0, 4.0], "depth": 2.5, "Z_seated": NOTCH_Z, "bearing_face": "square, top"},
           "feed_lips": {"wall": 2.0, "single_feed_taper_height": sc(30.0, 1), "front_top_stepped_higher": True},
           "follower": "dark polymer, visible between the lips; no cartridge", "inner_draft_deg": 0.25,
           "mass_empty_kg": 0.17},
     construction="Straight polymer housing, double stack tapering to a single-feed top. Two parallel recessed channels "
     "per side crossed by flush ties (the ladder; geometry, re-read at 4x), a raised front spine rib with the parting "
     "line on its crest, a plain rear spine with the catch notch. Solid (no witness panels: the sheet and the prompt).",
     ruling="RP10", wear="insertion streaks on the upper 40 mm; polished spine crest and lips; whitened floor-plate "
     "corners; dust in the ladder floors", trace=tref("magazine"), side_profile_M=profile("magazine", 0.2),
     authority="LEFT (outline, rake, ladder); 3/4 (thickness, +-6)", confidence="high (side), low (thickness)",
     sources=["measure", "craft magazine", "merge"])

part(id="magazine_floor_plate", asset="SM_SMG01_Mag (+ merged in SM_SMG01)", display="Magazine floor plate",
     bone="magazine", process="P-round", joint={"type": "slide-on", "parent": "magazine_body", "gap_mm": [0.2, 0.4]},
     slot=SLOT_MAG, finish=F_MAGP, texel_class="C",
     box_M={"X": [MAG["floor_plate"]["profile_Z_Xrear_Xfront"][-1][1], MAG["floor_plate"]["profile_Z_Xrear_Xfront"][-1][2]],
            "Z": [MAG["floor_bottom_Z"]["mm"], MAG["floor_plate"]["profile_Z_Xrear_Xfront"][-1][0]],
            "Y": [-MAG_T / 2 - 1.0, MAG_T / 2 + 1.0]},
     dims={"length": MAG["floor_plate"]["max_length_X"]["mm"], "height": sc(7.5, 1), "lip_proud": [1.0, 2.0], "front_R": 4.0,
           "locking_tab_hole_dia": 8.0, "profile_Z_Xrear_Xfront": MAG["floor_plate"]["profile_Z_Xrear_Xfront"]},
     construction="Separate cap sliding on from the rear on rails moulded into the housing's bottom flange; the locking "
     "plate's dark tab shows flush in a dia 8 hole on the bottom face (unseen face).", ruling="RP10",
     wear="corner whitening (drops); Base impact zone", trace=None, authority="LEFT", confidence="medium",
     sources=["measure floor_plate", "craft"])

part(id="pins_fasteners", display="Pins and fastener heads (count and position from the trace only)", bone="body",
     process="M-chamfer", joint={"type": "fixed", "parent": "body"}, slot=SLOT_METAL, finish=F_STEEL, texel_class="C",
     box_M=None, dims={"list": PINS, "count_left": sum(1 for q in PINS if q["side"] in ("left", "both")),
         "count_right": sum(1 for q in PINS if q["side"] in ("right", "both")),
         "head_rule": "flush steel inset rings, 0.3 mm chamfer, 0.1-0.2 mm proud or sunk as each sheet head reads; "
                      "sizes written in mm; LEFT positions for 'both' parts, RIGHT positions as read on the RIGHT "
                      "panel (RIGHT drift up to ~2.5 mm is panel drift, the through-part is built at the LEFT position)"},
     construction="Steel flush heads at every head the two side views draw (check fix C7: re-read at 10x on both "
     "panels; the old 'pin behind the magwell' position was 8 mm off, on plain wall).",
     ruling="RP18", wear="rims brightened, grime around", trace=None, authority="LEFT / RIGHT", confidence="medium",
     sources=["measure face_features", "craft"])

# ================================================================================================ rulings (merged)
RULINGS = []
for r in CRAFT["rulings"]:
    RULINGS.append(dict(r))
RULING_OVERRIDES = {
    "RP3": "Knob at rest where drawn (merge read: dia %.1f, centre (%.1f, %.1f)); slot X %.1f-%.1f behind it, lock "
           "notch at its rear; the arm rides 0.2 mm off the wall (no recess: TOP shows the block %.1f proud)." % (
               KNOB_D, KNOB_C[0], KNOB_C[1], SLOT_X[0], SLOT_X[1], ARM_BLOCK["proud_of_wall"]),
    "RP5": "Bolt face at rest X %.1f (the measurer's feed geometry; the craft's X 485 sits over the magazine's top "
           "round), travel %.1f to X %.1f (the real ~75 scaled with the gun, R26)." % (BOLT_REST_FACE_X, CH_TRAVEL, BOLT_BACK_FACE_X),
    "RP7": "Hub %.1f on BOTH sides (both traces draw the same size; the craft's 10 %% smaller right lever is dropped); "
           "positions as rotations about Y from the bind pose: %s." % (SEL["ring_diameter"]["mm"], SEL_ROT),
    "RP2": "As ruled, with the axle at Y %.1f (1 mm inside the right wall plane, knuckles ~%.0f mm proud in TOP) so the "
           "rigid 180 deg fold clears the right side (resolution R19)." % (HINGE_Y, KNUCKLE_PROUD_R),
    "RP10": "Thickness %.1f (resolutions R14, R26); ladder channels %.1f wide x 2 with a %.1f rib, ties at Z %s (the craft's "
            "4.5 mm channels were a misread)." % (MAG_T, LADDER["channel_width"], LADDER["rib_between"], LADDER["tie_Z"]),
    "RP15": "Fold directions as ruled; the rear windage drum is on the LEFT (TOP + 3/4), not the right; the front "
            "sight's clamp knob stands %.1f mm proud on the right (TOP)." % sc(16.0, 1),
    "RP14": "Slots only where the sheet draws teeth (%d slots, %d teeth) + one hidden lug slot under each sight; "
            "the drawn flats stay (the craft's ~29 slots over X 308-607 overruled)." % (len(TOOTHED_SLOTS), n_teeth),
    "RP16": "Device OD %.1f (the trace's outer edges; TOP %.1f)." % (DEVICE_OD, DEVICE_W_TOP),
}
for r in RULINGS:
    rid = r.get("id")
    if rid in RULING_OVERRIDES:
        r["merge_adjustment"] = RULING_OVERRIDES[rid]

# ================================================================================================ resolutions
RES = [
    {"id": "R1", "topic": "Scale", "conflict": "measure 0.85114 px/mm on the sub-pixel LEFT trace (587.3 px); craft "
     "1.1795 mm/px from a 585 px threshold silhouette; both 690 mm; the ruler reads 86.8 cm",
     "resolution": "690.0 mm overall at the measurer's per-view scales (LEFT 0.85114, RIGHT 0.85196, TOP 0.84613 px/mm). "
     "Every craft station (+-3.5 mm) is replaced by the trace. The sheet is chunkier than the real pattern (trigger "
     "reach 90.5 vs ~70, height 338 vs 280-326, width 68.8 vs 61-63.5); the silhouette gates keep the sheet; H1 decides "
     "whether the user's Q1 (625 mm) is needed", "rule": "measurement wins (silhouette)"},
    {"id": "R2", "topic": "Bore height and muzzle device diameter", "conflict": "measure: device dia 20.8, Z = 0 on its "
     "centre, and 'TOP inflates round parts by 26 %'; craft: OD ~24, TOP round parts read the same as the side",
     "resolution": f"The measurer's own LEFT silhouette is {DEVICE_OD} mm tall over the cage (X 656-685) and the TOP "
     f"{DEVICE_W_TOP}: they agree within 3 %; the 20.8 median was split by a see-through slot sliver. The bore axis "
     f"is the centre of the outer edges over X 632-685: Z_M = {BORE_Z} (RIGHT {BORE_Z_RIGHT}). Frame M keeps the "
     "measurer's Z (every trace stays valid); the bore is the line Y 0, Z_M " + str(BORE_Z) + ". TOP widths are "
     "therefore usable as drawn (the +-15 % caveat is withdrawn), except at the stock (R18)",
     "rule": "measurement wins, corrected on its own trace"},
    {"id": "R3", "topic": "Which panel is which side", "conflict": "none: all three roles agree",
     "resolution": "Labels are true: LEFT = left (knob), RIGHT = right (port, catch), TOP has the muzzle image-left with "
     "the gun's left image-down; 3/4 FRONT (LEFT) shows the left. No mirrored panel", "rule": "agreed"},
    {"id": "R4", "topic": "Grip origin depth", "conflict": "measure 40 mm (study 5.1 provisional); plan 46 mm (the "
     "AR-01's H1 value)", "resolution": f"46 mm down the traced grip-axis midline (rake {GRIP_RAKE} deg) from the web "
     f"line Z {JZ}: Grip_M = ({GX}, 0, {GZ}); H1 early may move it", "rule": "plan wins (frames)"},
    {"id": "R5", "topic": "Charging handle size and position", "conflict": "measure knob dia 12.9 at (548.3, 24.5), rod "
     "3.2 tall; craft ball ~18 at (551, 19.5)", "resolution": f"8x re-read: ball {KNOB_D} at ({KNOB_C[0]}, {KNOB_C[1]}), "
     f"rod Z {ARM_ROD['Z']}, rear block Z {ARM_BLOCK['Z']}; the TOP agrees (knob 19.2 long in X, 18.4 proud). The "
     "measurer's hand circles under-read", "rule": "silhouette authority (LEFT + TOP), re-read"},
    {"id": "R6", "topic": "Charging handle construction (plan R4 vs craft RP3)", "conflict": "plan: slot cut for the "
     "travel, 'confirm' the rest position; craft: real lever rests at the front of a channel behind it, travel 75, "
     "lock indent", "resolution": "RP3 with the merge numbers: slot X %.1f-%.1f, Z %.2f-%.2f; the arm rides on the "
     "wall (TOP: block 3.3 proud), so no recess; visible change limited to X 470-501.5 behind the block. User check "
     "C-Q1 = open question Q3" % (SLOT_X[0], SLOT_X[1], SLOT_Z[0], SLOT_Z[1]), "rule": "craft wins (small-part construction)"},
    {"id": "R7", "topic": "Right-side upper slot (plan R18 / plan Q1)", "conflict": "plan default: a plain wall "
     "(AI-mirrored handle slot); craft RP4: build it as a vent", "resolution": "Built as a moulded through-vent, X "
     "530.1-595.8, Z 25.0-33.9 (merge read). It is not a mirror: the right slot is longer and starts 29 mm further back "
     "than the left one. Plan Q1 closed", "rule": "craft (+ sheet) wins"},
    {"id": "R8", "topic": "Hidden barrel and breech", "conflict": "measure: breech X ~503 (barrel ~150); craft: "
     "200 mm barrel, breech X ~485 'inside the port'; plan: real 200", "resolution": f"Breech X {BREECH_X}: the chamber "
     "must sit ahead of the magazine's top round (mag front wall reaches X 493 at the receiver); X 485 is over the "
     f"round. Crown X {CROWN_X} inside the device collar: barrel {BARREL_LEN:.0f} mm. Nothing visible changes. Real "
     "200 mm only with the port and magazine moved (silhouette); open question Q2", "rule": "measurement wins (feed "
     "geometry), mechanism check"},
    {"id": "R9", "topic": "Top rail slots", "conflict": "measure: 19-20 drawn teeth at 11.05 pitch, flats behind the "
     "rear sight and X 557-595; craft: ~29 slots X 308-607; plan: round(length/10.01)", "resolution": f"Standard "
     f"10.01 pitch in the drawn toothed zone only: {n_teeth} teeth, slots {TOOTHED_SLOTS[0]}-{TOOTHED_SLOTS[-1]} "
     f"(X {SLOT_X_LIST[1]}-{SLOT_X_LIST[-2]}), plus hidden lug slots 0 (rear sight, X {SLOT_X_LIST[0]}) and "
     f"{FRONT_LUG} (front sight, X {SLOT_X_LIST[-1]}); the drawn flats are built (relief flats at slot-floor level). "
     "Slot depth 3.0 (standard), not the drawn 6.0; L3 exempts the notch depth. Lower rail 7 slots (76.2 mm)",
     "rule": "measurement (zone, length), line standard (profile, pitch)"},
    {"id": "R10", "topic": "Selector", "conflict": "craft: right lever 10 % smaller, hub 20, SAFE '110 deg' from "
     "SEMI; measure: both hubs 20.7, pivots 5.5 mm apart; plan: rest = safe", "resolution": f"One shaft at the LEFT "
     f"pivot {SEL_P} (the RIGHT's +5.5 mm is panel drift); hubs 20.7 both sides; bind pose = the sheet = SEMI; rotations "
     f"about Y from bind: {SEL_ROT} (SAFE = blade 45 deg below forward, AUTO = 45 deg further rearward); clips that "
     "move the bolt hold AUTO; other clips keep the bind (SEMI, also a firing position). The detents are a DESIGN CALL "
     "(check C11): the manual figures show SAFE ~25 deg below forward and SEMI/AUTO ~15-20 deg below rearward, which "
     "the sheet's pose matches neither; open question Q16", "rule": "measurement (shape), design call (positions), "
     "plan (clip rule)"},
    {"id": "R11", "topic": "Stock catch / folded retention (plan R10 vs craft RP2/RP6; measure Q5)", "conflict":
     "plan: a hook over a stud; measure: an unexplained boss in front of the port (keep or drop?); craft: the boss is "
     "the integral catch", "resolution": "The traced boss X 511.3-527.9 is the integral stock catch, 3.0 proud, with a "
     "hooked lip on its rear edge; folded, the barb of a moulded lug on the stock's rear upright sits under that lip "
     "(check fix C3: the pad alone never reached the catch), engagement %.1f (gate F3); no stud. Measure Q5 closed"
     % F3_ENGAGE_X, "rule": "craft wins (construction), measure (outline), check C3 (engagement part)"},
    {"id": "R12", "topic": "Magwell internals (plan R17, mag budget 'guide ribs'; craft RP21)", "conflict": "plan: two "
     "guide channels for mag guide ribs; craft: no ribs (the ladder is recessed)", "resolution": "No guide ribs or "
     "channels; M3's rib-in-channel row is dropped; the flare, 1 deg draft, catch window and top shelf stay",
     "rule": "craft wins"},
    {"id": "R13", "topic": "Magazine section and ladder", "conflict": "craft 42 fore-aft, channels 4.5 wide; measure "
     "46.7, rake -7.42", "resolution": f"Fore-aft {MAG_FA}, rake {MAG_RAKE} deg (bottom forward; refit on the straight "
     f"body Z -240..-90, check fix C2: the old 7.42 took in the lip cut and the floor plate), exposed "
     f"{MAG['exposed_length_along_axis']['mm']} along the axis; ladder re-read at 4x: two 12.5 mm channels, 3 mm rib, "
     f"ends Z {LADDER['channel_top_Z']} / {LADDER['channel_bottom_Z']}, ties Z {LADDER['tie_Z']}", "rule": "measurement wins"},
    {"id": "R14", "topic": "Magazine thickness", "conflict": "measure 30.7 +-5.7 (3/4), default 30; craft ~27 (real "
     "norm); AR-01 R32 precedent", "resolution": "29.0: inside the 3/4 read's 1 sigma and above the real minimum "
     "(22.4 stack + 2 x 2.3 walls = 27) with room for the 1.0 mm ladder recess; the 3/4 L2 gate re-checks 27-31 at "
     "blockout (open question Q8)", "rule": "measurement band, craft floor"},
    {"id": "R15", "topic": "Muzzle device stations", "conflict": "measure X 644.1-690 incl. the collar; craft cage "
     "651-690, jam nut 632-651 OD 17.7, collar ring OD 26 at 620-632", "resolution": "8x re-read: cage X 652.2-690, "
     f"collar + groove X 644.1-652.2, neck X 632.4-644.1 (dia 22.6), collar ring X 621.9-632.4 (dia 24.8); OD "
     f"{DEVICE_OD}", "rule": "measurement wins (+ re-read)"},
    {"id": "R16", "topic": "Port, catch, magwell, guard, grip, pad, stock stations", "conflict": "craft stations "
     "(port X 453-515 Z -2..22, guard bottom -100, magwell 452-512 to -79, pad 0-28 x 107, top strut +4.7..+16.5) vs "
     "the trace", "resolution": "Every outline and station from the trace (port 449.1-512.6 x 2.5-26.1; guard bottom "
     "-121.4; magwell 449.1-539.2 with the lip line; pad 0-31 x 113.3; strut profiles)", "rule": "measurement wins"},
    {"id": "R17", "topic": "Sight line and sight hardware", "conflict": "neither study gave the aperture height; "
     "craft put the windage drum on the right", "resolution": f"Aperture centre ({APERTURE[0]}, {APERTURE[1]}): the drawn "
     f"ring at 10x (check fix C9; the earlier 73.0 was the front sight's dark band); the post tip on the same line (sight line parallel to the bore, {APERTURE[1] - BORE_Z:.1f} above it), "
     f"{D['sights']['sight_front']['top_Z']['mm'] - POST_TIP[1]:.1f} below the ear tops; sight radius {SIGHT_RADIUS}. "
     "Drum on the LEFT (TOP lateral feature X 312-355 + the 3/4 left view); the front clamp knob on the right (TOP, "
     "16 mm proud)", "rule": "silhouette authority (TOP, 3/4)"},
    {"id": "R18", "topic": "Stock and butt-pad widths", "conflict": "measure TOP stock 35-45, pad 67.3; craft strut "
     "29.5, pad 55-59", "resolution": f"TOP is oblique at the stock (both struts and the pad's side show; the measurer "
     f"notes it). Frame {FRAME_W} (top face of the top strut), pad {PAD_W}. The TOP L2 gate is computed on X >= 245 "
     "with the stock checked by these two widths instead", "rule": "craft read (the trace's number is not a width)"},
    {"id": "R19", "topic": "Fold geometry (new)", "conflict": "no role computed it: a rigid 180 deg fold about an axis "
     "inside the drawn outline (TOP shows no knuckle beyond the right side) puts the folded pad 13 mm INSIDE the receiver",
     "resolution": f"Axle at Y {HINGE_Y} (X {HINGE_X}): the folded stock's mid-plane lands at Y {FOLD_MID_Y}, the pad's "
     f"inner face {PAD_CLEAR} mm outboard of the 3 mm port catch; the knuckle stack stands ~{KNUCKLE_PROUD_R:.0f} mm "
     "proud of the right wall in TOP (as on the real pattern's right-side hinge). Side views unchanged. Open question Q6 "
     "(alternative: a fold angle under 180 deg with the stock splayed, or a joggled arm)", "rule": "real pattern "
     "(construction) inside the main-view silhouette; user decides"},
    {"id": "R20", "topic": "Folded length", "conflict": "craft gate 450 +-15 (real); measure 417.6 to the hinge gap; "
     "plan ~443", "resolution": f"Folded rearmost point = the hinge knuckles at X {FOLD_REAR_X}: folded length "
     f"{FOLDED_LEN} mm on the sheet's proportions; gate F2 = {FOLDED_LEN} +-3 (build check), the real 450 reported",
     "rule": "measurement (silhouette) wins over the real figure"},
    {"id": "R21", "topic": "Materials values", "conflict": "plan ranges (polymer 40-55 / 0.50-0.70, steel 50-70); craft "
     "sheet-sampled values", "resolution": "craft values (sheet-calibrated, real finishes); plan slots, masters and "
     "recolour group unchanged; L5 calibrates under matched light", "rule": "craft (look), plan (slots)"},
    {"id": "R22", "topic": "Bones, sockets, budgets, LODs, gates, stage order", "conflict": "none of substance (the "
     "craft's added gates are merged)", "resolution": "plan contract kept; numbers filled from this merge; craft gates "
     "added as F1-F5", "rule": "plan wins"},
    {"id": "R23", "topic": "Selector rotation axis", "conflict": "GUN_BUILDING_STUDY 5.2/U2 says a selector turns "
     "about X; the plan and the shipped AR-01 turn it about Y (transverse shaft)", "resolution": "about Y (the AR-01's "
     "shipped behaviour, required for the shared ABP); the study text is a known wording slip", "rule": "plan wins"},
    {"id": "R24", "topic": "Bolt catch (plan R9/Q7; craft RP9)", "conflict": "none", "resolution": "not built, no "
     "bolt_catch bone; the internal hold-open (not modelled) holds the bolt after the last round with the charging "
     "handle forward; ReloadEmpty releases it with a full charging-handle pull and release. Plan Q7 closed",
     "rule": "agreed"},
    {"id": "R25", "topic": "Stock fold side (plan R10/Q2)", "conflict": "none: craft RP1 (manual) = right, TOP agrees",
     "resolution": "folds to the right; plan Q2 closed", "rule": "agreed"},
    {"id": "R26", "topic": "Scale (open question Q1): orchestrator ruling 2026-10-09", "conflict": "the W0 merge built "
     "the sheet at the real pattern's 690 mm; there the sheet's grip / trigger group is 13-29 % larger than real "
     "(trigger reach 90.5 vs ~70, side rail pitch 11.05, receiver width 68.8 vs 61-63.5)",
     "resolution": "SCALE = %.0f mm overall with the stock extended (factor %.6f on every sheet proportion): at ~625 the "
     "side-view rail pitch is exactly 10.01 and the receiver width matches the real 61 mm, so the sheet was evidently "
     "drawn at ~625. All silhouette proportions stay exactly the sheet's. Implemented in the measurement "
     "(tools/trace_reference.py OVERALL_MM = 625, its mm windows scaled with it) and here (every number read off the "
     "sheet in mm at 690 is written sc(v)); line-standard and real-pattern hardware stays absolute: the 1913 rail "
     "profile, every clearance row, wall thicknesses (3.0-3.5 receiver, 4.0 magwell rear wall), the .45-class bore "
     "(11.4) and case head (12.0), pin / screw norms (< 4 sheet px), the sight aperture (2.0) and disc (10), the paddle "
     "(9.0 wide; 3.0 deep at 625 so the guard's front leg keeps 2 mm of polymer), the latch bolt (4.0 / 2.5), the grip width (32, unseen, real norm) and the Grip depth (46, hand). "
     "Derived at 625: bolt and charging travel %.1f (the real ~75 scaled with the gun; still > the .45 round's 32.4 + "
     "feed), magazine thickness %.1f (the 3/4 read is 27.8 +-5.2 at 625; the real minimum 27, so R14's 29 becomes 27), "
     "trigger reach %.1f, length of pull %.1f, folded length %.1f. The text of R1-R25 records the W0 merge at 690; "
     "every number the build reads (parts, sockets, bones, gates, fold) is regenerated at 625" % (
         OVERALL, S, CH_TRAVEL, MAG_T, D["trigger_reach_to_blade_front_face"]["mm"], sc(409.4, 1), FOLDED_LEN),
     "rule": "orchestrator ruling (binding); plan Q1 closed"},
    {"id": "R27", "topic": "Selector detents (open question Q16): orchestrator ruling 2026-10-09",
     "conflict": "design call (sheet pose = SEMI, SAFE 45 deg below forward, AUTO 45 deg further rearward) vs the "
     "manual's figures (SAFE ~25 deg below forward, SEMI / AUTO ~15-20 deg below rearward)",
     "resolution": "the study's design call: bind = the sheet pose = SEMI; rotations about Y from bind %s; Q16 closed" % SEL_ROT,
     "rule": "orchestrator ruling (binding)"},
    {"id": "R28", "topic": "Folded-stock retention (open question Q17): orchestrator ruling 2026-10-09",
     "conflict": "a moulded lug on the rear upright's right face (not drawn) vs a joggled stock arm (changes TOP)",
     "resolution": "the moulded lug (stock_frame.dims.retention_lug: barb under the port catch's rear lip, engagement "
     "%.1f in X); side views unchanged; Q17 closed" % F3_ENGAGE_X, "rule": "orchestrator ruling (binding)"},
    {"id": "R29", "topic": "Every other open question (Q2-Q15)", "conflict": "none", "resolution": "the plan's default, "
     "as listed in open_questions (orchestrator ruling 2026-10-09 (4))", "rule": "orchestrator ruling (binding)"},
    {"id": "R30", "topic": "Magazine top vs the bolt (W1b form build)", "conflict": "the W0 top Z (feed lips, seated) "
     "was a centre value; with the 8.27 deg rake the top face's front edge stood %.1f mm higher, into the bolt's path "
     "(bolt underside Z %.1f)" % ((MAG_FA / 2.0) * math.sin(math.radians(abs(MAG_RAKE))), BOLT_Z[0]),
     "resolution": "the magazine's top centre at Z %.2f, so its whole raked top (incl. the lips) stays 0.5 under the "
     "bolt; the top shelf (M2 overtravel 1.0-2.0) is the bolt rails' lower flanges over the mag's side walls (outside "
     "the bolt's width); Feed, MagInsertStart and the mag length follow" % MAG_TOP_Z,
     "rule": "mechanism check (form stage), numbers regenerated here"},
    {"id": "R31", "topic": "Magwell outer width (W1b form build)", "conflict": "W0 built the well from the magazine + "
     "walls (34.8 / 38.8 at 625); the 3/4 view reads %.1f +-%.1f at the lip" % (
         D["mag_well"]["outer_width_estimate_from_3q"]["mm"], D["mag_well"]["outer_width_estimate_from_3q"]["unc_mm"]),
     "resolution": "lip %.1f / body %.1f: the 3/4 view's magwell-lip / magazine front-face ratio (%.3f, the same view "
     "angle for both faces, so the ratio carries no camera error) x the magazine thickness %.1f; checked by the camera-"
     "solved 3/4 L2 gate" % (MW_OUT_LIP, MW_OUT_BODY, MW_RATIO, MAG_T), "rule": "measurement (3/4 ratio)"},
    {"id": "R32", "topic": "Top rail rear end and the end block's D-frame (W1b form build)", "conflict": "the trace's "
     "top_rail key starts at the end block's front seam (X %.1f) while the TOP draws a raised D-shaped rim with a "
     "rectangular pocket over X %.1f-%.1f, across that seam" % (tr["X"][0], TOPF_X0, sc(310.4, 1)),
     "resolution": "the D rim is the steel rail's machined rear end: the rail starts at X %.1f (round in plan, R 8 "
     "corners), sits on the end block's top behind the seam, and carries the drawn pocket (2.0 deep) in its rear "
     "relief flat; the side silhouette is unchanged (same top Z)" % TOPF_X0, "rule": "TOP authority (widths), side "
     "silhouette kept"},
    {"id": "R33", "topic": "L2 per part: measurement conventions (W1b fix round, orchestrator: re-derive the thresholds "
     "for the parts the sight-fold spec resizes, fix real mismatches)",
     "conflict": "at 0.94 px/mm the per-part rule judged the trace's label boundaries inside one moulding (triangle "
     "centroids put whole triangles across them), the declared deviations (paddle C1, the sights' fold B4c, the rail "
     "notch depth R9, real through-slots) and ribbons whose IoU a half-pixel trace edge moves by more than 0.05 (guard, "
     "rails: the plan's own thin examples, trigger 5.8 px and paddle 6.5 px, are thin by width, not area)",
     "resolution": "smg_silhouette.py: integral mouldings split PER PIXEL by the trace's own label map (nearest allowed "
     "label; the lower's fixed hinge knuckles may take stock_hinge_knuckle); what the fore-end vents show takes the "
     "vent's moulding label (the sheet draws them dark); the rail's top band under the sights' feet takes the trace's "
     "sight label where the trace has one; toothed rails compared with the notches closed (R9); the trigger below the "
     "housing's bottom line - 2.5 px (the trace labels the housing's edge band 'trigger'; the same band is left out of "
     "receiver_lower); the muzzle device hole-filled; the pixels the trace labels mag_release (+1 px) left out of every "
     "other part (declared C1); thin = area < 400 px OR mean width (2 area / perimeter) < 7 px -> contour rule P95 <= 1 "
     "px, max <= 2 px; the flip sights: IoU >= fold ceiling - 0.05, the ceiling = the trace minus the leaf pixels the "
     "fold rule makes impossible (a leaf point folded about its pin must land inside the B4c band and clear the base "
     "top + 0.15 outside the pocket), 0.05 being the plan's own tolerance under a perfect match",
     "rule": "measurement method (W1b fix round)"},
    {"id": "R34", "topic": "L2 side IoU and L3 contour: the declared deviations measured alike in both masks",
     "conflict": "the side IoU / contour counted the rail notch depth (R9: the line standard's 3.0, drawn 5.4), the "
     "muzzle device's real through-slots (daylight through the bore; the sheet draws dark slots and one 1 px slit), the "
     "stock's two drawn-dark through-holes and the paddle's fore-aft faces (declared C1) as outline errors",
     "resolution": "smg_silhouette.side_conventions on ours AND the trace: the rail notch bands closed along X, the "
     "muzzle interior closed and filled, our see-through stock holes without a traced counterpart filled; the L3 contour "
     "also without the paddle zone (+2 px); the RIGHT ceiling (the LEFT trace against the RIGHT panel) recomputed with "
     "the same conventions; the raw values are reported beside every gate value",
     "rule": "measurement method (W1b fix round)"},
    {"id": "R35", "topic": "Magazine body vs the traced front-to-back (W1b fix round)",
     "conflict": "the traced %.1f front-to-back is measured to the front spine rib's crest; the build added the %.1f rib "
     "on top of a %.1f body, so both side panels read our magazine's front edge 1-2 px forward of theirs" % (
         MAG_FA_TRACED, MAG_RIB, MAG_FA_TRACED),
     "resolution": "body %.1f + spine rib %.1f = the traced %.1f; the body's rear face stays on the traced rear edge "
     "(the catch notch, the rear wall line and the paddle are unchanged); the mag frame's axis is the body's midline, "
     "%.1f behind the traced midline; the well's cavity, the inner fore-aft and every mag socket follow" % (
         MAG_FA, MAG_RIB, MAG_FA_TRACED, MAG_RIB / 2.0),
     "rule": "measurement (both side panels) + RP10 (the rib)"},
    {"id": "R36", "topic": "Magazine insertion: the mouth's lead-in and the catch's travel (W1b fix round, M2 / M4)",
     "conflict": "a 1.6 mm per side mouth flare left a 1.7-1.9 mm visible seam at the well's lower edge (M2 <= 0.6); "
     "the static-catch M4 allowance ('last 6 mm only') cannot hold for any real catch: the nose rides the magazine's "
     "rear face from its top edge to the notch (26 mm here) on a spring",
     "resolution": "the well's mouth a 0.25 per side lead-in over 2.5 mm along the slanted lip (seam 0.55 at the edge); "
     "the insertion guide is the outer flare band (2.0 per side) and the magazine's tapered top. M4 evaluates the real "
     "pattern's spring-loaded catch (gunlib 0.2.2 magfit_check catch_spring): at every 0.5 mm step the smallest catch "
     "rotation toward release that clears the magazine must exist inside the travel, the nose may move <= 0.5 x tan 60 "
     "= 0.87 mm per step (a ramp: the nose's 41 deg underside meets the magazine's top rear edge; a square shoulder "
     "would need the whole engagement in one step), 0 intersections with the rest of the gun, and the catch is back at "
     "rest with the magazine seated (the snap); M4b / M5 (released) stay 0",
     "rule": "real pattern (paddle catches: spring-loaded, cammed by the magazine) + mechanism check"},
    {"id": "R37", "topic": "W1b fix-round geometry (generators)",
     "conflict": "form gates L2 / L3 / UD1 near misses",
     "resolution": "the master side outline cleaned without corner-cutting bias (smg_geom.clean_ring_true: Gaussian "
     "sigma 1.0 mm with corners pinned, straight runs snapped, 0.05 sagitta; IoU 0.9932 against the trace vs 0.9857 for "
     "DP 0.9 + Chaikin; the see-through holes keep the DP + Chaikin clean-up); the guard opening also cut through the "
     "DRAWN trigger blade's region (+0.6, up to 0.3 into the housing band) so no polymer sliver is left beside the "
     "built blade; the top rail's front end chamfered as both side panels draw it; the barrel's face flange (dia 26.4, "
     "3.6 long) as drawn; the seam's horizontal run on the drawn line's upper edge (row 210.5: the trace gives the line to "
     "the lower); the butt pad's wrap lip removed (the sheet draws the pad ending at the seam); the stock head traced "
     "entire (top rising to Z 31, bottom under the neck); the rear sight base's raised rear (Z 51.2) and centre block "
     "(Z 58.1) behind the leaf as drawn; the front sight ears' side profile as drawn (76.0 over their rear 0.8, 72.4 "
     "forward); UD1: the trigger tongue's sweep as one hull cutter (concentric arcs), the paddle slot's face 0.1 into "
     "the wall (coplanar strip), a sliver flip / collapse pass after the repair (no triangle under 0.0125 mm2)",
     "rule": "sheet authority (LEFT) + UD gates"},
    {"id": "R38", "topic": "L2 3/4 FRONT (LEFT): the camera solve and the exception rule (W1b fix round)",
     "conflict": "the landmark + soft-IoU solve stopped at IoU 0.89 / contour P95 12 px; the plan allows the AR-01's "
     "documented exception only for regions proven to be 3/4-panel contradictions",
     "resolution": "smg_q34.solve_best: four objectives from the landmark camera (soft IoU without the magazine zone, the "
     "symmetric chamfer, soft IoU of the whole gun, soft IoU of the body alone), the best by the gate's own hole-filled "
     "IoU; the panel's consistency recorded (body-only landmark RMS, the grip / magazine landmarks under the body camera, "
     "each half fitted alone). Gate: IoU >= 0.93 and P95 <= 3 px; else pass only if the solved IoU >= 0.915 (the "
     "AR-01's floor) AND with the proven contradictions (smg_q34_exception: the parts pass the side view and no width "
     "the authorities allow removes the region; R26 magazine-thickness regions) left out the rest meets the bar. Below "
     "the floor no region is excused and the panel goes to the user (Q11: regenerate the 3/4 panel or rule on it)",
     "rule": "measurement method (orchestrator: solve the camera properly; the exception only with evidence)"},
    {"id": "R39", "topic": "L2 3/4 FRONT (LEFT): reported only for the SMG (orchestrator ruling 2026-10-10)",
     "conflict": "no rigid camera fits the AI 3/4 panel: best camera-solved IoU 0.90 (R38 floor 0.915 not met); the "
     "grip / magazine landmarks sit 16-19 px off any camera that fits the body, while the LEFT and RIGHT panels agree "
     "with each other at 0.95 (the panel is internally inconsistent, not the build)",
     "resolution": "the side (LEFT / RIGHT) and TOP views are the exact-match authority; the 3/4 panel is a look "
     "reference. The two 3/4 rows (camera-solved IoU, contour P95) are still measured and recorded every stage, marked "
     "'reported' and not blocking (gates/form.json status pass)",
     "rule": "orchestrator ruling (W1 start state, 2026-10-10)"},
    {"id": "R40", "topic": "Front sight: the TOP panel's right-side 'clamp knob' (W1 realism round 1)",
     "conflict": "the TOP panel draws a 12 x 15 mm protrusion on the right at the front sight base (built in W1 as a "
     "stalk + cap knob to Y -46.3); every close-up realism judge read it as a second charging handle / a stray "
     "plunger; the RIGHT side view (authority) draws only a small screw head on the base's face where an end-on 11.8 "
     "mm knob would show, the 3/4 view draws nothing beyond the base, and real rail-clamp flip sights carry no stalk",
     "resolution": "not built: the cross-bolt ends in the captive hex nut the rear sight carries (flats up, flush on the "
     "base's right face); the side panels' taller base block over the knob's X span (535.3-547.1) is the cheeks' lower "
     "rear step (top Z 13.2 in the rail frame); TOP L2 stays >= 0.93 without it",
     "rule": "authority views (RIGHT + 3/4 agree against the TOP panel) + real pattern + realism judges"},
    {"id": "R41", "topic": "Traced outlines as geometry: fairing (W1 realism round 1)",
     "conflict": "the close-up judges read the trace's pixel residue as torn / chipped geometry: clean_ring_true's "
     "corner pins blended back to the raw stairs (zig-zags on the magwell lip, the receiver's lower front, the stock "
     "arm's lumpy top), clean_ring's DP 0.3 kept sub-pixel steps on small parts (the trigger's stepped tip, the guard's "
     "notched rim)",
     "resolution": "smg_geom.fair_ring for every traced ring (master outline, holes, part rings): true corners pinned "
     "(DP 0.75 polyline turns >= 40 deg next to a segment >= 1.5 mm), each raw run between corners Gaussian-smoothed "
     "(sigma 1.5 mm, ends held), straight stretches (DP segment >= 5 mm) snapped onto their least-squares line, no "
     "edge under 0.2 mm; the lower rail's rear-end stair notch replaced by its straight step (MASTER_SPANS). Measured: "
     "LEFT 0.9814 -> 0.983, L3 P95 2.0 (unchanged), 23 / 23 parts",
     "rule": "sheet authority (unchanged silhouette within the gates) + realism judges"},
    {"id": "R42", "topic": "W1 realism round 1: part construction fixes",
     "conflict": "judged fake at 35 cm: the trigger's stepped tip, the guard's broken rim (two traced holes and the "
     "drawn blade's relief cut separately), the lower's hooked flap round the lower rail's rear end, an unchamfered "
     "magwell flare band under a round (a cornice), the stock head unrounded with a square step from the arm",
     "resolution": "trigger: one centripetal Catmull-Rom curve through control points read at the trace stairs' middles "
     "(finger face 370.9 / -66.5, forward-curled tip 378.2 / -80.7, root flaring to 360.2-374.0 at the opening's top), "
     "no housing band; guard: ONE opening (the traced hole minus the blade's run, its top held at the drawn -51.3 across "
     "the blade's root, 45 deg corners kept) cut before the rounds (rim R 1.05), the loop = the opening grown 8 mm to "
     "the front leg (X 402.2) + the drawn foot spliced in; the lower rail butts the lower's flat face (X 484.2, 0.3 "
     "gap) instead of tucking into a pocket; the flare band's 45 deg top chamfer runs (its predicate missed the "
     "built top by 1.2 mm); the stock's head, hinge leaf and latch boss rounded with the frame (R 1.0) and the neck "
     "flaring into the head in plan; the upper's seam edges and the shoulder set-in round the front chamfer kept off "
     "the rounds (UD)",
     "rule": "real pattern + realism judges, inside the sheet's side / top gates"},
    {"id": "R43", "topic": "W1 realism round 2: construction fixes (the last shape round before texturing)",
     "conflict": "judged fake at 35 cm: the drawn upper / lower split read as decorative panel lines on one flush "
     "plane; the seam boss, 0.2 lower than the selector seat and half under the lever's hub, read as a loose second "
     "disc; the magwell a block stacked under a 10 mm shelf of the full-width housing; the guard a crisp octagonal "
     "stamping butting the grip; the stock top's bend and the tang behind the grip faceted (fair_ring's corner clusters "
     "between long flats); a 0.5 trough across the stock top where the head met the neck; the hinge leaf a pasted "
     "box; the charging knob a full sphere on the slot; radial shading streaks on the receiver's front face",
     "resolution": "the trigger housing set in 0.8 per side under the upper (end block at its spec width; pins centred "
     "below the seam seat on the set-in face); the LEFT seat and seam boss one pad (two circles, R 3.0 waist fillets, "
     "1.0 over the upper's face, 0.6 top round; the upper's pocket 0.22 round it); the housing zone cut by a 35 deg "
     "funnel through its set-in faces at Z -49.6 with a skirt beside the well (X 0.4 inside the rear wall .. the front "
     "face), so the well flares out of the housing; the guard opening's corners at the spec's inner R 6 (after a 0.2 "
     "simplification so the arcs fit), the master outline's guard corners and the bar / grip notch smoothed (sigma "
     "1.5-2.0), the rear bar flaring into the grip (half width 9.0 -> 5.45 below Z -74); MASTER_CURVES: the stock top "
     "X 181-233.7 and the tang X 253-294.9 re-smoothed (sigma 3.0, 1.0 mm chords); the stock head's top / bottom on "
     "the outline with a 0.5 ramp crossing the neck's eased end once (X 221.5-224), its plan flare 11 long; the "
     "leaf's front end a 45 deg gusset (material removed only); the knob a flattened ball (Y semi-axis 6.9, crown flat "
     "dia 7.0) over an R 2.4 cove and a dia 8.0 stem 2.0 off the shoulder band (dia 16.76, centre and tip Y 47.5 "
     "kept); the receiver's front face above the barrel's flange one plane (X 563.3) up to its traced top chamfer "
     "(11.7 deg, meeting at Z 20.68) instead of the trace's zig-zag strips that fanned streaks round the eyelet "
     "(smg_geom.MASTER_POLYS); every large flat region shaded with its plane normal (smg_parts._flatten_planar)",
     "rule": "real pattern + realism judges, inside the sheet's side / top gates"},
    {"id": "R44", "topic": "W4 review fixes (craft + tech review, 2 realism judges on the final textures)",
     "conflict": "realism: every view judged fake (one flat clay material, steel = polymer, no micro-texture, no wear "
     "logic, firefly specks); craft: vent / channel ends 25.7 deg facets, the knob a speckled blob, bare steel as 196 "
     "isolated flecks (0.07 %), the polymer's normal map flat (2.3 % of texels), the steel LIGHTER than the polymer "
     "(base 50-52 vs 46-49, against the sheet's device 40 / rail 49 vs receiver 63), soot invisible on phosphate, no "
     "drum knurl, trace noise in the stock window and the pad's rib profile, the housing's tongue 3.1 mm proud of the "
     "fore-end at the V, the twin's LOD sizes at the box half-diagonal",
     "resolution": "phosphate base sRGB (40, 41, 42), rough 0.62-0.76 dry / 0.52-0.62 oiled (the craft table's 48-54 "
     "contradicted its own 'steel darker' rule; the sheet's crops decide); soot at the PBR floor (lin 0.013, sRGB 30); "
     "bare steel as continuous 0.25-0.8 mm lines on the sharp convex crests (curvature x exposure x handling, <= 1.2 mm "
     "from the edge, clusters >= 14 texels, <= 1.6 mm wide); the knob a satin crown with a bright rim; the polymer's "
     "moulded texture in the normal map at the texel scale the maps carry (0.6 mm grain + 1.8 mm peel; the study's "
     "0.05-0.15 mm sits under a texel and shows only as roughness), albedo mottle, continuous whitening bands, fore-aft "
     "scratches; drum knurl 0.55 pitch in Metal_N; Masks G on the metal; stadium ends 24 segments per semicircle "
     "(7.5 deg) and a G3o gate on opening loops (chord error <= 0.035 mm; 7.5 deg at r >= 5); the guard / grip cover "
     "rounds finer; stock windows DP 1.0 + true radii; the pad's rear face flat with open ribs at the one pitch 3.2; "
     "the housing set in 0.8 under the upper's plan incl. its 45 deg fore-end step; the follower 1.0 under the lips "
     "(lips rolled R 1.2); the static twin's and the magazine's LOD sizes at Unreal's static-mesh sphere radius "
     "(max |v - box centre|); texel classes: shipped medians up to 1.25 x the band top (W2 B9 rule), the measured "
     "medians written into the sidecar beside the bands",
     "rule": "realism judges + real pattern, inside the sheet's side / top gates; the sheet's crops for colour"},
    {"id": "R45", "topic": "W4 resume: why the realism judges saw 'one flat clay' (measured), and the fix",
     "conflict": "both realism judges called every close view one flat matte clay although the maps exist. Measured: "
     "the maps reach the review renders (FBX UV0, BC sRGB / ORM + N Non-Color, DirectX green flipped, BC-emission "
     "renders show the paint), but the paint was near-uniform at render scale: even after the first W4 fix pass "
     "(polymer BC std 3.9 levels; W3 shipped 2.3) the maps sat only 1.8-3.5 sRGB levels (mean over the object) off a "
     "constant per-set clay material in the 7 close-ups, and the review rigs' flat grey world left a dark rough finish "
     "nothing to reflect (no sheen, no edge highlights)",
     "resolution": "paint: real-scale roughness variation on the polymer (sheen fields at ~30 mm and ~8 mm, about "
     "0.25 / 0.22 x fbm; 0.45 / 0.25 was tried and read as camouflage clouds at hero distance), recess dust on the polymer x 1.8, a settled dust film on up-facing faces (lighter, drier, "
     "wiped off in the handling zones), the phosphate's mottle x 1.8 and its sheen field; albedo mottle stays at the "
     "craft table's +-4 levels. Renders: the realism views lit by a photographic studio rig (Blender's bundled studio "
     "HDRI, neutral, for light and reflections + softboxes; the camera sees the same grey backdrop), with the L5 "
     "calibration rig's versions kept beside them; the review set and the colour test stay on L5. Measured after: the maps "
     "3.28 / 3.37 levels (rough / studio rig, mean of the 7 close-ups) off the clay, x 1.23 over the first pass "
     "(review/diag/maps_vs_clay.json)",
     "rule": "realism judges; measurement (maps vs clay)"},
    {"id": "R46", "topic": "W4b close-up realism pass r1: the R45 clouds, the exposure, the seam, the glints, one material",
     "conflict": "both realism judges failed all 12 close views of the R45 set: 'large, soft, cloudy grey / white "
     "blotches' (procedural noise / concrete) on the receiver and stock, 'one mid-grey value with one roughness' (steel "
     "= polymer), a centre seam down the receiver rear face and the stock head (ADS), white specks on the rail teeth and "
     "the sight drum, 'mid-grey clay, not black polymer'. Measured: the R45 sheen fields (+-0.12 roughness at 30 / 8 mm) "
     "and albedo fields (+-22 % / +-25 % at 9 / 25 mm) were the clouds; the studio rig (studio.exr 0.6 + k 0.3) lit the "
     "receiver to 1.92 x the L5 calibration's exposure; the seam was the painted mid-plane parting line on the lower "
     "receiver's rear face and the stock head (not UV: one island across Y 0); polymer 0.58-0.66 and phosphate 0.62-0.76 "
     "roughness overlapped; bare steel at 0.42-0.55 glinted",
     "resolution": "paint: the clouds to a trace (sheen 0.05 / 0.05, albedo 0.10 / 0.06, per-texel speckle 0.14); the "
     "variation moved to where real wear puts it: a handling rub on every exposed convex edge (0.2-0.7 mm, up to +35 % "
     "linear, rough -0.10), dust as a grey-beige deposit in the deep recesses and against inside corners (no fbm "
     "patches), the hand-polish blended in (its switch drew a disc); polymer a satin 0.50-0.58 (hand 0.44) with its "
     "moulded grain at 12 / 20 um, phosphate a dead-flat crystalline charcoal 0.66-0.78 (oiled 0.56-0.66) with a +-4 um "
     "crystal grain in the normal map, its base (45, 46, 47) (R44 (40, 41, 42)) so the L5 render's receiver / steel "
     "ratio stays at the sheet's (G20 1.537 vs 1.453: at (40, 41, 42) / 0.70-0.82 it read 1.635), still under the "
     "polymer's albedo; the stipple 0.72-0.82 and x 1.24 (L5 grip); bare steel 0.50-0.62 and fewer bare dashes on the "
     "top rail (the rest rubbed phosphate); the parting line only on the grip / guard / magwell straps, the grip cover, "
     "the magazine and the stock's struts. Renders: the realism rig is the bundled interior.exr (CC0) at 0.45 + "
     "softboxes k 0.12, its exposure within 1.3 x the L5 calibration (review/closeup_r1, gates/closeup_r1.json)",
     "rule": "realism judges; reference photos (realref/craft); measurement (closeup K1-K5)"},
    {"id": "R47", "topic": "W4b close-up realism pass r2: the banded stock head, one value / no sheen, no visible wear, "
     "slivers on the sights",
     "conflict": "both realism judges failed every r1 close view: the FP / ADS foreground stock head 'a smooth slanted "
     "sheet like a bent ribbon, banded, with soft streaks'; 'one flat charcoal value with one roughness, steel = "
     "polymer'; 'no edge wear, finger polish or holster rub'; 'white hairline glints on random edges of the rear sight'; "
     "vent walls 'flat grey, no depth darkening'. Measured: the stock head's curved top (and every curved prism surface: "
     "the strut bends, the grip, the pad top) was FLATTENED by smg_parts._flatten_planar into 3-6 deg planar bands "
     "(area-weighted shading / geometric spread 0.11 on the curved regions; clay renders show the bands); the r1 rig left "
     "a rough black finish nothing in its mirror direction (no sheen to tell 0.55 from 0.80); r1's edge rub (+6 sRGB "
     "levels) and specks never reached a render (a multiplied albedo step on black is swamped by the 4 % specular); the "
     "sights' 1-3 px bare-steel dashes were the slivers; r1's recess dust (30 % to sRGB 94) lit the vent walls",
     "resolution": "geometry: curved regions (deviation field R^2 >= 0.8, span >= 1.5 deg, >= 3 faces) keep smooth "
     "shading (corner-angle weighted normals), only true flats are flattened (W1 onward rebuilt; shading / geometric "
     "spread 0.27 -> 0.98 on the 22 curved regions); paint: polymer satin 0.47-0.55 (hand 0.41; magazine 0.48-0.58; "
     "0.40-0.48 failed L5 grip and G20), the phosphate base (46, 47, 48), the stipple x 1.34 (L5 grip), the orange peel "
     "to a trace + a 0.25 mm spark grain, wear MIXED toward a "
     "worn grey (edge rub to sRGB 100 at the crest 0.35-1.0 mm wide, rough -0.22; scuffs to 96; the sheet's specks to "
     "112; worn phosphate edges to 100), handling smudges +-0.07 rough at 3 mm, dust on floors only (12 %), recess walls "
     "darkened x (1 - 0.28 cav), no bare steel on the sights / selector, the knob rim a rubbed ring; renders: the "
     "product rig (smg_review_export.STUDIO: mirror-placed softboxes for the side and top faces, edge strips, weak key, "
     "interior HDRI 0.15, backdrop sRGB 150), no denoiser at 1024 samples (review/closeup_r2, gates/closeup_r2.json)",
     "rule": "realism judges; the sheet's 3/4 view (specks, edge scuffs, satin sheen); measurement (closeup r2 K1-K6)"},
]

# ================================================================================================ gates
GATES = {
    "numbering": "GUN_BUILDING_STUDY 7 + SMG_BUILD_PLAN 14 + craft F-gates; thresholds below are binding",
    "spec": {"S0": "this file: 0 missing fields per part (process, slot, finish, texel class, bone, joint, authority, "
                   "box or dims), 0 unresolved values; validator output in spec['S0']"},
    "look": {
        "L1": "blockout IoU: LEFT >= 0.95, RIGHT >= 0.95, TOP (X >= %.0f) >= 0.92; < 0.90 = stop and change the method" % sc(245),
        "L2": "form IoU: LEFT >= 0.96, RIGHT >= 0.96 (labels consistent: both sides are authority views), TOP (X >= %.0f) " % sc(245) +
              ">= 0.93, 3/4 FRONT (LEFT) camera-solved IoU >= 0.93 and contour P95 <= 3 px (reported only, R39); per "
              "part (LEFT trace keys) IoU >= 0.95 where area >= 400 px and mean width (2 area / perimeter) >= 7 px, "
              "else contour P95 <= 1 px / max <= 2 px; the fold-resized sight leaves IoU >= their fold ceiling - 0.05; "
              "measurement conventions R33 (per part) and R34 (side IoU and L3 contour)",
        "L2_thin_rule": "area < 400 px or mean width < 7 px (R33)",
        "L2_thin_parts": sorted(k for k in LEFT["parts"] if area_px(k) < 400.0),
        "L2_part_areas_px": {k: area_px(k) for k in LEFT["parts"]},
        "L2_TOP_exclusion_X": sc(245, 1), "L2_TOP_exclusion": "X < %.0f (oblique stock)" % sc(245) + " is replaced by the widths in R18 (+-1 mm)",
        "L3": "side contour P95 <= 2 sheet px; feature positions <= 2 sheet px for: vents (4 per side + the 2 long "
              "vents), port corners, catch, knob centre, arm block, selector hub, trigger face, the paddle's pin head "
              "and top/bottom Z (its fore-aft faces are a declared deviation: mag_release.dims.declared_deviation), "
              "every pins_fasteners head (%d LEFT + %d RIGHT), the oblong recess, the seam boss, the end-block TOP "
              "frame, sight heads, aperture, rail ends + toothed-zone ends, stock windows and holes, butt-pad ends, "
              "mag ladder ties, floor plate; angles (grip rake, mag rake, lower strut) <= 1 deg; rail notch depth "
              "exempt (R9)" % (sum(1 for q in PINS if q["side"] in ("left", "both")),
                               sum(1 for q in PINS if q["side"] in ("right", "both"))),
        "L4": "measured vs spec <= 0.05 mm",
        "L5": "colour: crop-matched hue, R/B and median luma (stone S16 tolerances) under the physical light; the "
              "polymer/steel luminance ratio 1.3-1.5 holds",
        "L6": "fake checklist G1-G20, 0 major (polymer tells first: G8, G19, G15)",
        "L7": "blind design judge >= 12 pairs (reported, not blocking); realism: 2 judges x 4 views (FP 35 cm, ADS, TP "
              "3 m, hero 3/4) + a folded-stock hero: at most 1 single-judge fake call",
        "L8": "early realism review at form, rough look, per part group (receiver + rails, sights, grip + lower, stock + "
              "hinge, front end, magazine): 2 judges with the real-pattern photos beside. PASS per group = at most 1 "
              "single-judge fake call; a group with 2 single-judge calls is fixed and re-judged once; DECISIVE FAIL = "
              "both judges call the same group fake (or a re-judge fails): stop and show the user"},
    "blender": {
        "B1": "skeleton: root object identity; 11 bones (no bolt_catch); every bone deforms but magazine; rest = root's",
        "B2": "rigid skin qa_skeletal(max_influences=1)",
        "B3": "sweeps LOD0-1, 0 intersections, joints inside their 3.7 rows: bolt 0..%.1f (-X), charging handle 0..%.1f + " % (CH_TRAVEL, CH_TRAVEL) +
              "lock 0..15 deg about the lever's roll pin (Y %.1f, Z %.1f; pusher-lug contact 0.0-0.05, no "
              "penetration), trigger 0..+%.0f deg, selector over SAFE..AUTO (both levers), paddle 0..%.0f deg, stock "
              "0..180 deg (step min(1 deg, 0.10/r_max) ~0.023 deg at r 250 mm, or 0.25 deg steps each proving >= 0.55 "
              "mm outside the latch and catch zones), sights 0..+-90 deg; declared allowances only: sight detents <= 0.3 "
              "mm in the last 2 deg, the catch lip over the lug's barb <= %.1f mm in the last 3 deg (snap); LOD2-3 < 1 "
              "px at the switch distance" % (LOCK_PIN[0], LOCK_PIN[1], TRIG_PULL, PAD_REL, F3_ENGAGE_X + 0.2),
        "B3b": "folded state: 0 intersections with the selector, port catch (except the engagement), grip, magwell; "
               "casing throw cone (ShellEject +X, 15 deg half-angle, 150 mm) reported against the folded stock (Q5)",
        "B4": f"sockets on their bones; Muzzle on the bore (Z_M {BORE_Z}) <= 0.5 mm / 0.05 deg; sight picture at ADS "
              "55 deg, 2560 x 1440, eye 0.25 m behind Sight: post tip at the aperture centre <= 0.5 px, nothing "
              "occludes the post, post visible >= 1 mm; from the blockout on, every stage, every LOD (S2)",
        "B4b": "same at the cheek-weld eye point (80-100 mm behind the aperture), reported",
        "B4c": f"sights folded: rear <= Z_M {B4C_REAR} (rail top + {B4C_REAR - RAIL_TOP_Z:.1f}: a 12.6 mm head folding "
               f"forward about its front-lower pin), front <= Z_M {B4C_FRONT}; nothing below the rail top (check fix C6)",
        "B5": "sidecar = build values within 0.001 mm / 0.001 deg",
        "B6": "twin qa_check --budget 55000 on the exported bytes", "B6a": "joined-twin topology from form: 0 "
              "coincident, 0 non-manifold, 0 UV0 overlaps once UVs exist",
        "B7": "closed manifold parts; flat-face deviation < 1 deg; facet <= 7.5 deg at LOD0; bevels = spec +-0.05 and "
              ">= 0.1 mm",
        "B8": "budgets (section budgets_triangles) and LOD-pop mean <= 1 px, max <= 3 px, both stock states",
        "B9": "textures: classes +-15 % (P5-median), fill >= 70 % Metal / 65 % others, metallic 0/1, BC ranges",
        "B10": "names: tokenised gun deny list on every name and shipped text (no ump, hk, heckler, koch ...)",
        "B11": "bounds extension: every LOD0-3 vertex at every clip frame, both stock states, sights up/down inside "
               "the bind AABB + extension; the folded envelope from EVERY stock-bone part (spec fold.folded_min_Y_by_part: "
               "the latch housing and button fold furthest out, check fix C10)",
        "G5": "0 static intersections LOD0-1; butt gaps >= 0.01 mm; LOD2-3 < 1 px",
        "H1_early": "W1: PASS = trigger reach <= 80 mm AND grip girth <= real polymer SMG grips + 10 %%; Grip depth "
                    "within 1 mm of the fit body's palm; SupportHand reachable <= 1.5 mm; length of pull (sheet %.1f "
                    "vs real 350-370) and cheek-weld eye height reported. At 625 (R26) the sheet's reach reads %.1f; a "
                    "FAIL does not stop the build: it is reported to the user with the numbers" % (sc(409.4, 1), D["trigger_reach_to_blade_front_face"]["mm"]),
        "H1_full": "W3: MH_PlayerDefault posed fit, 0 hand-gun intersections at rest and clip extremes incl. stock "
                   "folded and mag out; records hand_offset",
        "UD1": "gunlib.tspace.unreal_drops(ob) == 0 on every part object at LOD0-3, the joined twin and each SK LOD; "
               "min triangle area >= 0.01 mm2",
        "UD2": "0 edges < 0.05 mm; 0 triangles with height < 0.02 mm over their longest edge; 0 bevel strips < 0.1 mm",
        "UD3": "W2 on: tspace.collapsed(me, 'UV0', unreal=True) == 0 on every export mesh LOD0-3; float32_zero_corners "
               "== 0; edge_on_corners == 0",
        "UD4": "W2 on: authored UV1 in 0..1, 0 overlap at 64 and 128 px with 2 px padding, every LOD"},
    "form_craft": {
        "F1": "selector sweep SAFE..AUTO: swept minimum to the grip, guard and housing >= 0.10 mm",
        "F2": f"folded length {FOLDED_LEN} +-3 mm (build check); real 450 reported",
        "F3": "stock folded: the lug's barb under the port catch's rear lip, engagement >= 1.0 mm in X (spec %.1f) "
              "and barb-to-lip gap 0.2-0.4 in Y; 0 intersections when seated; swept minimum over the fold >= 0.10 mm "
              "outside the declared snap allowance" % F3_ENGAGE_X,
        "F4": "charging handle sweep (translate %.1f, then the lock" % CH_TRAVEL + " 0..15 deg about the lever's roll pin, the slide not "
              "rotating): the neck clear of the slot and notch by 0.15-0.40 mm; the outer arm >= 0.10 mm off the wall "
              "at every frame (spec: every arm point moves outward, min %+.2f)" % ARM_MIN_DY,
        "F6": "stock latch (extended): the bolt's full diameter >= 1.5 mm into the end-block lug's bore when released "
              "(spec 2.0); 0 with the button pressed 2.0 (the neck spans the lug); the fold sweep with the button "
              "pressed clears the lug's exit slot by >= 0.10",
        "F7": "charging-handle lock: at 15 deg the neck seated in the rear notch >= 2.0 mm above the slot top (spec "
              "%.2f at the wall's inner face); the knob rises %.1f mm" % (NECK_RISE_IN, KNOB_RISE),
        "F5": "magazine catch sweep 0..release with the mag seated: 0 intersections except the nose leaving the notch; "
              "bolt thumb recess visible in the port at rest (render check)"},
    "magazine": {
        "M1": "seated, co-visible LOD pairs (k,k) and (k,k+-1): 0 intersections LOD0-1; LOD2-3 < 1 px",
        "M2": "seat: nose to the notch bearing face 0.0-0.3; overtravel to the top shelf 1.0-2.0; seam <= 0.6 (the "
              "well's mouth a 0.25 lead-in over 2.5 mm, R36)",
        "M3": "lateral 0.2-0.6 per side; fore-aft 0.2-0.6; catch engagement >= 1.5",
        "M4": "insert path MagInsertStart -> Mag in 0.5 mm steps with the real pattern's spring-loaded catch (R36): 0 "
              "gun intersections; at every step a clearing catch angle inside 0..release; the nose moves <= 0.87 mm "
              "per 0.5 mm step (a ramp, not a shoulder); the catch back at rest with the magazine seated",
        "M4b": "the same with mag_release at -11 deg: 0 intersections",
        "M5": "removal with the release pressed: 0 intersections; M5b (info) removal at rest collides",
        "M6": "sockets from the exported sidecars vs the fit <= 0.001 mm / 0.001 deg", "M7": "gun bytes = shipped sha256",
        "M8": "(info) the Reload clip's magazine path below MagInsertStart reported",
        "M9": "Unreal: mag at Mag <= 0.001 cm; seated fit on read-back geometry", "M10": "twin's merged mag = "
              "SM_SMG01_Mag at every LOD (equal triangles, vertices within 0.001 mm)"},
    "unreal": PLAN["gates"]["unreal"] | {
        "U2b": "ABP_Gun_LongGun (authored on SK_AR01_Skeleton) drives SK_SMG01 and SK_AR01 via Compatible Skeletons "
               "within 0.01 cm / 0.01 deg, through NORMALIZED inputs mapped by each gun's sidecar abp_angle_table: "
               "bolt 0..1, trigger pull 0..1 (both triggers move their lower end rearward), selector detent index "
               "(SAFE/SEMI/AUTO reach each gun's own angles), mag_release 0..1 (each paddle/catch moves its release "
               "way); missing bones raise no error (check fix C5)"},
    "pack": PLAN["gates"]["pack"],
}

# ================================================================================================ clips (check C11, C12)
CLIP_TEXT = {
    "A_SMG01_Selector.fbx": "SEMI (bind) -> SAFE -> SEMI -> AUTO -> SEMI: starts and ends at the bind pose",
    "A_SMG01_StockFold.fbx": "button pressed (latch bolt in 2.0, the neck spans the end-block lug), stock 0 -> 180 deg "
                             "about Z; the lug's barb snaps under the port catch's rear lip; button released",
    "A_SMG01_StockUnfold.fbx": "the stock pulled outboard (the lug flexes, the barb ramps over the catch lip), 180 -> 0 "
                               "deg; the latch bolt's ramp rides over the end-block lug and snaps into its bore",
    "A_SMG01_ReloadEmpty.fbx": "starts with the bolt held open by the internal hold-open (not modelled; no bolt_catch "
                               "bone, R24) and the charging handle FORWARD; paddle press, mag out, new mag in; then "
                               "the charging handle pulled fully back (%.1f) and released:" % CH_TRAVEL + " the hold-open lets go and the "
                               "bolt runs forward with the handle",
    "A_SMG01_Fire.fbx": "trigger pull 0 -> +%.0f deg; bolt 0 -> travel -> 0; the charging handle does not move" % TRIG_PULL,
    "A_SMG01_Reload.fbx": "paddle 0 -> %.0f deg (nose out of the notch); magazine straight down along -Z, drop, new "
                          "mag up the path, paddle back, nose snaps into the notch" % PAD_REL}
CLIPS = []
for c in PLAN["clips"]["list"]:
    c = dict(c)
    if c["file"] in CLIP_TEXT:
        c["motion"] = CLIP_TEXT[c["file"]]
    CLIPS.append(c)

# ================================================================================================ textures, budgets (C15)
TEXTURES = json.loads(json.dumps(PLAN["textures"]))
TEXTURES["class_assignment"]["A"] = "rear diopter (leaf, ears, aperture disc), front post + ears (the sights only)"
TEXTURES["class_assignment"]["B"] = ("bolt, charging handle, selector, top rail X < 400 (seen at ADS); polymer rear "
                                     "receiver behind the magwell, grip top, stock comb + hinge")
TEXTURES["class_assignment"]["C"] = ("top rail X >= 400, lower rail, trigger, paddle; polymer front receiver, magwell, "
                                     "guard, stock frame; the magazine")
TEXTURES["estimate_correction"] = "every set x2.3 (the AR-01's packer needed 2.3x its estimate); the packer decides"
TEXTURES["sets"]["Metal"]["rough_need_texels"] = ("~1.0 M at estimate (sights A ~40 cm2 at 90; rail B ~53 cm2 at 70 + "
                                                 "C ~107 cm2 at 35; bolt/handle/selector B; paddle/trigger C; barrel/"
                                                 "device D), ~2.4 M x2.3")
TEXTURES["sets"]["Metal"]["expected"] = "2048 likely (holds 2.94 M at 70 %); 4096 if the packer needs it"
TEXTURES["sets"]["Furniture"]["rough_need_texels"] = "~3.1 M at estimate, ~7.1 M x2.3"
TEXTURES["sets"]["Furniture"]["expected"] = "4096 (holds ~10.9 M at 65 %)"
TEXTURES["sets"]["Mag"]["rough_need_texels"] = "~0.35 M at estimate, ~0.8 M x2.3"
TEXTURES["sets"]["Mag"]["expected"] = "1024 at the estimate (0.68 M at 65 %); 2048 if the x2.3 factor holds"
BUDGETS = json.loads(json.dumps(PLAN["budgets_triangles"]))
_old_rail = BUDGETS["gun"]["per_part_lod0"]["top_rail"]
BUDGETS["gun"]["per_part_lod0"]["top_rail"] = 3500
BUDGETS["gun"]["per_part_lod0"] = {("hinge_block_knuckles_pin_latch_lug" if k == "hinge_block_knuckles_pin_detent_stud"
                                    else k): v for k, v in BUDGETS["gun"]["per_part_lod0"].items()}
BUDGETS["gun"]["floor_allocation_lod0"] += 3500 - _old_rail
BUDGETS["gun"]["top_rail_note"] = ("24 chamfered slots at ~140 triangles each + flanks and ends: 3,500 (check fix C15; "
                                   "the plan's 2,800 was 20-30 % low)")

# ================================================================================================ spec assembly
spec = {
    "meta": {
        "name": "Compact SMG SM-01", "code": "SMG01", "version": "1.2", "date": "2026-10-09",
        "revision": "1.2: orchestrator rulings R26-R29 (scale 625 mm, selector design call, retention lug, plan defaults); "
                    "1.1: checker findings C1-C16 verified and fixed (spec check_findings; SMG_STUDY.md section 12)",
        "assets": {"skeletal": "SK_SMG01 (+ _LOD1..3, SK_SMG01_Skeleton, PHYS_SMG01, clips A_SMG01_*)",
                   "static_twin": "SM_SMG01 (stock extended, mag merged)", "magazine": "SM_SMG01_Mag"},
        "units": "millimetres (Blender builds in metres: / 1000; Unreal cm: / 10)",
        "authority": "This file + SMG_DESIGN_SHEET.png are the build reference; SMG_BUILD_PLAN.md is the process. "
                     "Values marked 'provisional' or 'computed at Wn' are set by that stage; nothing else is nominal.",
        "generator": "WorkFiles/guns/smg/tools/make_spec.py (re-run after any change to the trace or a decision)",
        "inputs": ["smg_measured.json", "trace/LEFT_outline.json", "trace/RIGHT_outline.json", "trace/TOP_outline.json",
                   "craft_parts.json", "CRAFT_STUDY.md", "smg_interface.json", "SMG_BUILD_PLAN.md",
                   "GUN_BUILDING_STUDY.md", "merge zooms in scratch/merge/ (local)"],
        "roles": {"measurement": "silhouette dimensions and positions", "craft": "small-part construction, finishes, "
                  "wear (rulings RP1-RP22)", "plan": "frames, bones, sockets, slots, budgets, LODs, gates, stages"},
        "ip": "Generic names only; no real-pattern or maker names in any asset name or buyer text; no markings (no "
              "logo, serial, calibre, selector letters, dots or pictograms). The game build matches the sheet; Fab "
              "design changes are listed, NOT applied.",
        "reference": "References/Guns/SMG/smg_sheetA.webp (1254x1254, AI-generated by the user; Sheet A only)"},
    "sheet_panels": {
        "LEFT": {"box_sheet_px": MEAS["panels_sheet_px_x0_y0_x1_y1_inclusive"]["LEFT"], "is": "true left side, muzzle "
                 "image-left", "authority": "X lengths, Z heights, positions, left features"},
        "RIGHT": {"box_sheet_px": MEAS["panels_sheet_px_x0_y0_x1_y1_inclusive"]["RIGHT"], "is": "true right side, "
                  "muzzle image-right (traced mirrored)", "authority": "right features (port, catch, right vents, right "
                  "selector lever)"},
        "TOP": {"box_sheet_px": MEAS["panels_sheet_px_x0_y0_x1_y1_inclusive"]["TOP"], "is": "from above, muzzle "
                "image-left, gun left = image-down", "authority": "widths (X >= 245); oblique at the stock"},
        "Q34": {"box_sheet_px": MEAS["panels_sheet_px_x0_y0_x1_y1_inclusive"]["Q34_FRONT_LEFT"], "is": "3/4 front "
                "view of the LEFT side", "authority": "magazine thickness, magwell width, front face (eyelet), front "
                "sight ears (camera-solved L2)"},
        "ruler": f"wrong: reads {MEAS['scale']['sheet_ruler']['implied_overall_length_cm_LEFT']} cm for the {OVERALL / 10:.1f} cm gun"},
    "frames": {
        "M": {"name": "measurement / spec frame (all part dimensions and trace outlines)",
              "axes": "+X toward the muzzle along the bore, +Z up, +Y = gun LEFT (right-handed)",
              "origin": "X = 0 at the rearmost point of the butt pad (stock extended); Z = 0 = the measurer's datum "
                        f"(the bore axis is at Z_M {BORE_Z}, resolution R2); Y = 0 on the mid-plane",
              "scale": "LEFT %.5f px/mm (%.4f mm/px); RIGHT %.5f; TOP %.5f; overall length %.1f (orchestrator ruling, R26)" % (
                  MEAS["scale"]["px_per_mm"]["LEFT"], MEAS["scale"]["mm_per_px"]["LEFT"], MEAS["scale"]["px_per_mm"]["RIGHT"],
                  MEAS["scale"]["px_per_mm"]["TOP"], OVERALL)},
        "B": {"name": "Blender build frame (GUN_BUILDING_STUDY 5.1)", "axes": "+X muzzle, +Z up, -Y = gun RIGHT "
              "(same axes as M)", "origin": "Grip", "Grip_in_M": [GX, 0.0, GZ], "transform": "B = M - Grip_in_M (pure "
              "translation)", "bore_axis_in_B": f"Y = 0, Z = {round(BORE_Z - GZ, 2)} (parallel to X)",
              "blender_front_view": "from -Y shows the right side, muzzle to screen right = the RIGHT panel"},
        "unreal": {"mapping": "Unreal cm = (Bx, -By, Bz) / 10", "axes": "+X forward, +Y right, +Z up",
                   "rotation_note": "Blender rotation about +Y by t = Unreal pitch -t; about +Z by t = Unreal yaw -t"},
        "mag": {"origin": "the Mag socket (well-entry centre on the traced lip line)", "Mag_in_M": r1(MAG_O, 2),
                "axes": f"+Z up the insertion axis = M rotated {THETA_MAG_Y:.3f} deg about +Y; +X forward perpendicular; "
                        "+Y = gun left", "z_axis_in_M": r1(U_UP, 5), "x_axis_in_M": r1(U_FW, 5)}},
    "scale": {"overall_length": OVERALL, "ruling": "R26 (orchestrator 2026-10-09): 625 mm, not 690; one uniform scale on every "
              "sheet proportion (factor %.6f vs the W0 merge); line-standard and real-pattern hardware stay absolute" % S,
              "factor_vs_690": round(S, 6), "folded_length_sheet": FOLDED_LEN, "folded_length_real": 450.0,
              "barrel_length": BARREL_LEN, "barrel_length_real": 200.0, "mass_kg": 2.5,
              "mass_note": "line standard (manual 2.26 without magazine; C-Q4 default 2.5)",
              "sheet_vs_real": MEAS["scale"]["real_anchor_ratios_sheet_over_real"],
              "scale_ruling": MEAS["scale"]["scale_ruling"]},
    "key_dimensions": {
        "overall_length": OVERALL, "height_with_mag": OV["height_with_magazine"]["mm"],
        "height_without_mag": OV["height_without_magazine"]["mm"], "top_Z": OV["top_Z"]["mm"],
        "bore_Z_M": BORE_Z, "sight_line_Z_M": APERTURE[1], "sight_height_over_bore": round(APERTURE[1] - BORE_Z, 1),
        "sight_radius": SIGHT_RADIUS, "rail_top_Z": RAIL_TOP_Z, "receiver_length": D["receiver"]["length_front_face_to_rear_end"]["mm"],
        "receiver_width": W_REC, "fore_end_width": round(FRONT_L - FRONT_R, 1), "max_width_incl_knob": round(KNOB_TIP_Y - Y_MIN, 1),
        "grip": {"origin_M": [GX, 0.0, GZ], "axis_rake_deg": GRIP_RAKE, "junction_M": r1(J, 2), "bottom_Z": D["grip"]["bottom_Z"]["mm"],
                 "trigger_reach": D["trigger_reach_to_blade_front_face"]["mm"]},
        "magazine": {"rake_deg": MAG_RAKE, "foreaft": MAG_FA, "thickness": MAG_T, "length_along_axis": round(MAG_LEN, 1),
                     "exposed": MAG["exposed_length_along_axis"]["mm"]},
        "muzzle_device": {"X": [D["barrel"]["device_seat_X"]["mm"], OVERALL], "od": DEVICE_OD},
        "stock": {"hinge_axis_XY": [HINGE_X, HINGE_Y], "length_hinge_to_butt": ST["length_hinge_gap_to_butt_rear"]["mm"],
                  "pad": [PAD["thickness_side"]["mm"], PAD["height"]["mm"], PAD_W]},
        "length_of_pull": sc(409.4, 1), "length_of_pull_note": "butt rear to the trigger face along the bore "
                                                                          "(real ~350-370; reported at H1)"},
    "stations_X": {
        "butt_pad_rear": 0.0, "butt_pad_front": PAD["X"][1], "stock_web": ST["stock_web"]["X"],
        "stock_neck": ST["parts_X_Z"]["stock_neck"][:2], "stock_knuckle": BOX["stock_hinge_knuckle"][:2],
        "hinge_axis": HINGE_X, "end_block": BOX["hinge_block"][:2], "receiver_rear": D["receiver"]["X"][0],
        "rear_sight_base": REAR_BASE, "aperture": APERTURE[0], "rail_slot0": round(SLOT0_X, 2), "grip_top": BOX["grip"][:2],
        "selector_pivot": SEL_P[0], "trigger_face": sc(409.4, 1), "trigger_guard": BOX["trigger_guard"][:2],
        "mag_release": BOX["mag_release"][:2], "ejection_port": PORT["X"], "magazine": MAG["X"],
        "bolt_face_back": BOLT_BACK_FACE_X, "breech_bolt_face_rest": BREECH_X, "stock_catch": CATCH["X"],
        "charging_slot": SLOT_X, "charging_knob": KNOB_C[0], "magwell_front_face": D["mag_well"]["front_face_X"]["mm"],
        "lower_rail": lrl["X"], "forward_vent_left": D["face_features"]["front_upper_slot"]["X"],
        "front_sight_base": FRONT_BASE, "front_post": POST_TIP[0], "receiver_front_face": D["barrel"]["receiver_front_face_X"]["mm"],
        "device_seat": D["barrel"]["device_seat_X"]["mm"], "crown": CROWN_X, "muzzle": OVERALL},
    "parts": parts,
    "fastener_rule": "count and position from the sheet only (pins_fasteners + per-part features); sizes from norms "
                     "where a head spans < 4 sheet px; written in mm, never 'M' + number",
    "real_pattern_rulings": {"source": "CRAFT_STUDY.md section 4 (RP1-RP22), with this merge's adjustments",
                             "items": RULINGS,
                             "plan_rulings_answered": "plan R1-R20: R4 -> RP3; R5 -> RP5 (%.1f mm at 625);" % CH_TRAVEL + " R9 -> RP9 (no catch); "
                             "R10 -> RP1/RP2 (right, port catch); R12 -> RP15; R16/R17 -> RP10/RP21 (no guide ribs); "
                             "R18 -> RP4 (vent); the rest confirmed"},
    "bones": {
        "root": "armature OBJECT 'root' at Grip, identity (no bone named root)",
        "count": 11, "rest_rotation": "identity (root's) for every bone", "same_bones_every_lod": True,
        "compatible_skeleton": PLAN["bones"]["compatible_skeleton"],
        "table": [
            {"bone": "body", "parent": None, "head_M": [GX, 0.0, GZ], "motion": "fixed; the physics body"},
            {"bone": "bolt", "parent": "body", "head_M": [BOLT_REST_FACE_X, 0.0, BORE_Z], "motion": "translate -X",
             "limits_mm": [0.0, CH_TRAVEL], "joint": "sliding 0.15-0.40"},
            {"bone": "charging_handle", "parent": "body", "head_M": [KNOB_C[0], KNOB_CY, KNOB_C[1]],
             "motion": "translate -X 0..%.1f; at full travel rotate about X 0..+15 deg (lock)" % CH_TRAVEL,
             "lock_axis_M": [None, LOCK_PIN[0], LOCK_PIN[1]],
             "joint": "sliding 0.15-0.40", "note": "the lock rotation is keyed about the lever's roll pin in the slide "
             "(Y %.1f, Z %.1f) by the rig (the slide does not rotate); the bone head stays at the knob for the socket"
             % LOCK_PIN},
            {"bone": "trigger", "parent": "body", "head_M": [TRIG_PIVOT[0], 0.0, TRIG_PIVOT[1]], "motion": "rotate about "
             "Y (+ = pull: lower end rearward)", "limits_deg": [0.0, TRIG_PULL], "joint": "hinge 0.10-0.30"},
            {"bone": "selector", "parent": "body", "head_M": [SEL_P[0], 0.0, SEL_P[1]], "motion": "rotate about Y",
             "positions_deg": SEL_ROT, "joint": "hinge 0.10-0.30"},
            {"bone": "mag_release", "parent": "body", "head_M": [PAD_PIVOT[0], 0.0, PAD_PIVOT[1]], "motion": "rotate "
             "about Y (- = release: lower end forward, nose rearward)", "limits_deg": [0.0, PAD_REL],
             "joint": "hinge 0.10-0.30"},
            {"bone": "magazine", "parent": "body", "head_M": r1(MAG_O, 2), "motion": "attach only, no weighted "
             "vertices; head = Mag socket", "joint": "seated-mag row"},
            {"bone": "stock", "parent": "body", "head_M": [HINGE_X, HINGE_Y, BORE_Z], "motion": "rotate about Z",
             "limits_deg": [0.0, 180.0], "joint": "hinge 0.10-0.30"},
            {"bone": "sight_rear", "parent": "body", "head_M": [REAR_PIVOT[0], 0.0, REAR_PIVOT[1]],
             "motion": "rotate about Y (folds forward)", "limits_deg": [0.0, 90.0], "joint": "hinge 0.10-0.30"},
            {"bone": "sight_front", "parent": "body", "head_M": [FRONT_PIVOT[0], 0.0, FRONT_PIVOT[1]],
             "motion": "rotate about Y (folds rearward)", "limits_deg": [0.0, -90.0], "joint": "hinge 0.10-0.30"},
            {"bone": "muzzle_device", "parent": "body", "head_M": [D["barrel"]["device_seat_X"]["mm"], 0.0, BORE_Z],
             "motion": "none (hidden when a suppressor mounts)"}],
        "note": "head_M in frame M; the builder writes B = M - Grip. The trigger pivot is the drawn axle head; the "
                "paddle pivot is the drawn pin head moved back by the wall rule (declared). Form (B3, F5) may move "
                "either by <= 1 mm",
        "abp_inputs": {"rule": "check fix C5: the shared ABP drives normalized inputs (trigger_pull 0..1, selector "
                               "detent index, mag_release 0..1, bolt 0..1); the skeletal sidecar's gun.abp_angle_table "
                               "maps them to each gun's own angles, so sign and detent differences never reach the ABP",
                       "SMG01": {"trigger_pull": [0.0, TRIG_PULL], "selector_detents_deg": SEL_ROT,
                                 "selector_detent_order": ["SAFE", "SEMI (bind = sheet pose)", "AUTO"],
                                 "mag_release": [0.0, PAD_REL], "bolt_mm": [0.0, CH_TRAVEL]},
                       "AR01_shipped": {"trigger_pull": [0.0, 12.0], "selector_detents_deg": [0.0, 16.0, 32.0],
                                        "mag_release": [0.0, 10.0],
                                        "source": "Scripts/guns/rifle/rifle_rig.py ranges; confirm the detent order "
                                                  "from SK_AR01.skeletal.json before W5"}}},
    "joints_clearance_mm": {k: v for k, v in PLAN["joints_clearance_mm"].items() if k != "seated_mag"} | {
        "seated_mag": {"lateral": [0.2, 0.6], "foreaft": [0.2, 0.6]},
        "declared_allowances": [a for a in PLAN["joints_clearance_mm"]["declared_allowances"]
                                if "stud" not in a["where"]] + [
            {"where": "port catch lip over the stock lug's barb (snap, polymer flex)", "max_mm": round(F3_ENGAGE_X + 0.2, 2),
             "only": "last <= 3 deg of the fold and the first <= 3 deg of the unfold"}]},
    "sockets": {"standard": "GUN_BUILDING_STUDY 5.3; PascalCase; bones in SK_SMG01.skeletal.json; Empties + "
                            ".sockets.json on SM_SMG01", "gun": GUN_SOCKETS, "mag": MAG_SOCKETS,
                "gun_count": len(GUN_SOCKETS), "mag_count": len(MAG_SOCKETS),
                "reload_path": "MagInsertStart -> (lerp along the mag's -Z, rotation constant) -> Mag; removal in "
                               "reverse with mag_release at -11 deg",
                "rail_slots": {"Rail_Top": {"cut": CUT_SLOTS, "occupied_by_sights": [0, FRONT_LUG],
                                            "free_for_attachments": TOOTHED_SLOTS},
                               "Rail_Bottom": {"cut": list(range(LR_N))}},
                "gates": "S1 sidecar = build values; B4 sockets on bones; M6 mag sockets"},
    "rails": {"module": PLAN["rails"]["module"], "profile_mm": PLAN["rails"]["profile_mm"] | {"height": round(RAIL_TOP_Z - RAIL_UNDER_Z, 1)},
              "top": {"X": tr["X"], "cut_slots": CUT_SLOTS, "slot_centres_X": SLOT_X_LIST},
              "bottom": {"X": lrl["X"], "slot_centres_X": LR_SLOTS_X}, "snap_rule": PLAN["rails"]["snap_rule"],
              "lod": PLAN["rails"]["lod"], "tests": PLAN["rails"]["tests"]},
    "fold": {"axis_M": [HINGE_X, HINGE_Y], "angle_deg": 180.0, "direction": "+Z (toward the gun's right)",
             "folded_mid_plane_Y": FOLD_MID_Y, "folded_pad_X": r1(sorted([fold_pt(0, 0)[0], fold_pt(PAD["X"][1], 0)[0]]), 1),
             "folded_rearmost_X": FOLD_REAR_X, "folded_length": FOLDED_LEN, "folded_min_Y": FOLD_Y_MIN,
             "folded_min_Y_part": FOLD_Y_MIN_PART, "folded_min_Y_by_part": FOLD_Y_MIN_BY,
             "retention": "the stock lug's barb under the port catch's rear lip (R11 + check fix C3), engagement %.1f "
                          "in X" % F3_ENGAGE_X, "retention_lug": LUG, "catch_lip": CATCH_LIP,
             "release": "extended: the left button (stock_hinge latch, gate F6); folded: pull the stock outboard",
             "known_overlap": "the folded top strut crosses the ejection port in the side view (C-Q3 = open question Q5)"},
    "materials": {
        "finishes": {
            "polymer_black": CRAFT["materials"]["polymer_black"],
            "grip_stipple": CRAFT["materials"]["grip_stipple"],
            "polymer_mag": CRAFT["materials"]["polymer_mag"],
            "rubber_pad": CRAFT["materials"]["rubber"],
            "phosphate_steel": dict(CRAFT["materials"]["phosphate_steel"], base_srgb=[40, 41, 42],
                                    base_linear=[0.021, 0.023], roughness_dry=[0.62, 0.76], roughness_oiled=[0.52, 0.62],
                                    craft_table_base_srgb=CRAFT["materials"]["phosphate_steel"].get("base_srgb"),
                                    ruling="R44: the steel darker than the polymer, as the sheet's crops show"),
            "bare_steel_wear": CRAFT["materials"]["bare_steel"],
            "bolt_steel": {"base": "phosphate_steel", "flanks_and_face": "bare_steel_wear (sliding 0.15-0.25)"},
            "soot": dict(CRAFT["materials"]["soot"], base_linear_painted=0.013,
                         ruling="R44: at the PBR floor (sRGB 30), visibly under the darkened phosphate")},
        "sheet_samples_srgb": CRAFT["materials"]["sheet_samples_srgb_median"],
        "wear_logic": CRAFT["wear_logic"],
        "slots": PLAN["materials"]["slots"], "recolour": PLAN["materials"]["recolour"],
        "sidecar_materials_block": PLAN["materials"]["sidecar_materials_block"],
        "wear_level": "moderate, as the sheet (white specks and edge scuffs); polymer never shows metal"},
    "textures": TEXTURES,
    "budgets_triangles": BUDGETS,
    "lods": {"count": 4, "gun_screen_sizes_start": SS_GUN, "mag_screen_sizes_derived": SS_MAG,
             "bounds_radius_m": {"gun_extended_no_mag": round(R_GUN / 1000, 4), "gun_extended_with_mag":
                                 round(R_GUN_MAG / 1000, 4), "gun_folded_no_mag": round(R_FOLDED / 1000, 4),
                                 "mag": round(R_MAG / 1000, 4)},
             "rule": PLAN["lods"]["rule"], "bounds_extension": PLAN["lods"]["bounds_extension"],
             "first_person": "ForcedLodModel = 1 on every FP component", "nanite": False},
    "collision": PLAN["collision"],
    "clips": {"rule": "start and end at the bind pose (selector SEMI, the sheet pose) unless stated; clips that move "
                      "the bolt hold the selector at AUTO first to last frame; review tools pose from absolute matrices",
              "list": CLIPS, "optional": PLAN["clips"]["optional"],
              "values": {"bolt_travel": CH_TRAVEL, "charging_travel": CH_TRAVEL, "charging_lock_deg": 15.0,
                         "trigger_pull_deg": TRIG_PULL, "selector_deg": SEL_ROT, "mag_release_deg": PAD_REL,
                         "stock_fold_deg": 180.0, "sight_rear_fold_deg": 90.0, "sight_front_fold_deg": -90.0,
                         "rate_rpm": 600, "selector_clip": "SEMI -> SAFE -> SEMI -> AUTO -> SEMI"}},
    "gates": GATES,
    "workflows": PLAN["workflows"],
    "gunlib_additions_W1a": PLAN["gunlib_additions_W1a"],
    "sidecar_gun_block": PLAN["sidecar_gun_block"] | {
        "grip_axis_deg": GRIP_RAKE, "rail_slots": {"Rail_Top": {"cut": len(CUT_SLOTS), "sights": [0, FRONT_LUG]},
                                                   "Rail_Bottom": {"cut": LR_N}},
        "stock_states": {"extended_deg": 0.0, "folded_deg": 180.0},
        "abp_angle_table": {"trigger_pull": [0.0, TRIG_PULL], "selector_detents_deg": SEL_ROT,
                            "mag_release": [0.0, PAD_REL], "bolt_mm": [0.0, CH_TRAVEL],
                            "rule": "the shared ABP drives 0..1 / detent index; this table maps to angles (U2b)"}},
    "layout": PLAN["layout"], "names": PLAN["names"],
    "unseen_plain": CRAFT["unseen_plain"],
    "inconsistencies_in_sheet": CRAFT["inconsistencies"],
    "realref": CRAFT["realref"] | {"use": "local reference only (scratch, gitignored): manual figures are copyrighted, "
                                          "one Wikimedia image is CC BY-SA; never commit or ship them"},
    "resolutions": RES,
    "fab_original_changes": {"status": "NOT applied; the user decides. The game build matches the sheet.",
                             "items": CRAFT["fab_original_changes"],
                             "advice": "any five of vents, stock, grip, muzzle, magazine move the read clearly away from "
                                       "the real pattern while keeping the boxy polymer SMG feel"},
}

OPEN_Q = [
    {"id": "Q2", "question": f"Hidden barrel: {BARREL_LEN:.0f} mm (sheet feed geometry) instead of the real 200 mm?",
     "default": "follow the sheet (nothing visible changes)", "from": "measure Q2"},
    {"id": "Q3", "question": "Charging handle: knob where drawn with a real 75 mm slot behind it (visible only X 470-501 "
     "behind the arm), the drawn front slots as vents?", "default": "yes", "from": "craft C-Q1"},
    {"id": "Q4", "question": "Selector index groove: paint it white (the sheet shows a light line) or leave it plain?",
     "default": "plain groove, no paint, no dots or pictograms", "from": "craft C-Q2"},
    {"id": "Q5", "question": "Folded, the stock's top strut crosses the ejection port (the real gun fires folded). "
     "Accept (folded = carry/no-fire in the game) or raise the strut (changes the side silhouette)?",
     "default": "accept as drawn", "from": "craft C-Q3"},
    {"id": "Q6", "question": f"Hinge: put the axle at the right-rear corner so the knuckles stand ~{KNUCKLE_PROUD_R:.0f} "
     "mm proud of the right side in the top view (needed for the stock to fold flat along the right side; the sheet's "
     "TOP shows no protrusion), or keep the axle inside the outline and fold to a splayed angle?",
     "default": "corner axle, knuckles proud (real-pattern construction; side views unchanged)", "from": "merge R19"},
    {"id": "Q7", "question": "Physics mass 2.5 kg (line standard) or 2.26 kg (manual, without magazine)?",
     "default": "2.5 kg", "from": "craft C-Q4"},
    {"id": "Q8", "question": "Magazine thickness 29 mm (3/4 view 31 +-6, real minimum 27)?", "default": "29; the 3/4 "
     "L2 gate re-checks 27-31 at blockout", "from": "measure Q4 / craft"},
    {"id": "Q9", "question": "Top rail: the standard 10.01 pitch in the drawn toothed zone (21 teeth where the sheet "
     "draws 19)?", "default": "yes (line standard)", "from": "measure Q3"},
    {"id": "Q10", "question": "Keep the merged magazine in SM_SMG01?", "default": "yes", "from": "plan Q3"},
    {"id": "Q11", "question": "Also ship a folded static SM_SMG01_Folded?", "default": "no", "from": "plan Q4"},
    {"id": "Q12", "question": "Ship A_SMG01_SightFlip as an 8th clip?", "default": "yes", "from": "plan Q5"},
    {"id": "Q13", "question": "Lightmap UV: authored UV1 with Generate Lightmap UVs off on the statics?",
     "default": "yes (UD4 + U8)", "from": "plan Q6"},
    {"id": "Q14", "question": "Folded-stock physics: one body with the extended shapes?", "default": "yes; U7 reports a "
     "folded drop", "from": "plan Q8"},
    {"id": "Q15", "question": "Fab design changes (craft list of 10)?", "default": "listed, not applied", "from": "plan Q9"},
]
spec["open_questions"] = OPEN_Q
spec["open_questions_rule"] = ("orchestrator ruling 2026-10-09 (R29): the build follows each listed default; Q1, Q16 and "
                               "Q17 were ruled (R26-R28) and moved to closed_questions")
spec["check_findings"] = {
    "source": "SMG checker, 2026-10-09 (scratch/checker/, local); each finding verified on the sheet before fixing",
    "items": [
        {"id": "C1", "area": "magazine release paddle", "verdict": "fixed",
         "resolution": "trace: the old box X 449-462 relabelled mag_well; the drawn lever inside the guard's front leg "
                       "traced as mag_release (X %.1f-%.1f, Z %.1f..%.1f, pin head %s). Built: pivot %s, paddle X "
                       "%.2f-%.2f behind the %.1f rear wall (+0.3), nose tip %s (engagement 1.5, travel %.1f at -11 deg); "
                       "the %.1f mm fore-aft shift vs the drawn lever is declared" % (
                           PAD_DRAWN[0], PAD_DRAWN[1], PAD_DRAWN[2], PAD_DRAWN[3], PAD_PIN_DRAWN, list(PAD_PIVOT),
                           PAD_REAR_X, PAD_FRONT_X, MW_WALL, list(PAD_NOSE), PAD_NOSE_TRAVEL, PAD_SHIFT_FRONT)},
        {"id": "C2", "area": "magazine rake", "verdict": "fixed",
         "resolution": "edge fit on the straight body (Z0+14 .. Z1-14): rake %.2f deg (was 7.42); Mag, MagInsertStart, "
                       "magwell axis and mag frame regenerated" % MAG_RAKE},
        {"id": "C3", "area": "folded-stock retention", "verdict": "fixed (option A)",
         "resolution": "a lug on the rear upright's right face, barb under the catch's rear lip, engagement %.1f; Q17"
                       % F3_ENGAGE_X},
        {"id": "C4", "area": "charging-handle lock axis", "verdict": "fixed (real-pattern variant)",
         "resolution": "lever pivots on a roll pin in the slide at (Y %.1f, Z %.1f); slide does not rotate; arm min "
                       "outward motion %+.3f; neck rise %.2f / knob %.2f; F4 restated, F7 added" % (
                           LOCK_PIN[0], LOCK_PIN[1], ARM_MIN_DY, NECK_RISE_IN, KNOB_RISE)},
        {"id": "C5", "area": "trigger sign, ABP", "verdict": "fixed",
         "resolution": "trigger 0..+%.0f; normalized ABP inputs + sidecar abp_angle_table; U2b covers trigger, "
                       "selector detents and release" % TRIG_PULL},
        {"id": "C6", "area": "rear flip sight fold", "verdict": "fixed (B4c recomputed, not 13.5)",
         "resolution": "pivot %s at the leaf's front-lower corner; folded top %.1f; B4c rear <= %.1f, front <= %.1f"
                       % (list(REAR_PIVOT), REAR_FOLDED_TOP, B4C_REAR, B4C_FRONT)},
        {"id": "C7", "area": "drawn fasteners and features", "verdict": "fixed",
         "resolution": "%d fastener rows (LEFT + RIGHT read), oblong recess, seam boss, TOP end-block frame; trigger "
                       "pivot on the drawn axle head %s" % (len(PINS), list(TRIG_PIVOT))},
        {"id": "C8", "area": "lower rail", "verdict": "fixed", "resolution": "%d slots, centres %s" % (LR_N, LR_SLOTS_X)},
        {"id": "C9", "area": "sight line", "verdict": "fixed",
         "resolution": "aperture (%.1f, %.1f), post tip on the line, %.1f above the bore" % (
             APERTURE[0], APERTURE[1], APERTURE[1] - BORE_Z)},
        {"id": "C10", "area": "folded envelope", "verdict": "fixed",
         "resolution": "folded_min_Y %.1f (%s)" % (FOLD_Y_MIN, FOLD_Y_MIN_PART)},
        {"id": "C11", "area": "selector detents", "verdict": "fixed (declared a design call; Q16)",
         "resolution": "clip text one sequence from and to the bind pose"},
        {"id": "C12", "area": "stale clip text", "verdict": "fixed", "resolution": "StockFold/Unfold, ReloadEmpty, "
         "Selector, Fire, Reload rewritten; S0 text-consistency check added"},
        {"id": "C13", "area": "rail screws", "verdict": "fixed", "resolution": "low button heads dia 4.8 in the slots"},
        {"id": "C14", "area": "stock latch", "verdict": "fixed", "resolution": "end-block lug above the gap, necked "
         "bolt dia 4.0 / neck 2.5, stroke 2.0, engagement 2.0; F6"},
        {"id": "C15", "area": "texel classes, budgets", "verdict": "fixed",
         "resolution": "rail B (X < 400) / C; sights A; x2.3 on every set; rail floor 3,500"},
        {"id": "C16", "area": "gates without numbers", "verdict": "fixed", "resolution": "L8 and H1 numbers; F6, F7"}]}
spec["closed_questions"] = [
    {"id": "plan Q1 (right-side slot)", "closed_by": "R7: built as a vent"},
    {"id": "plan Q2 (fold side)", "closed_by": "R25: right"},
    {"id": "plan Q7 (bolt_catch)", "closed_by": "R24: not built"},
    {"id": "measure Q5 (boss in front of the port)", "closed_by": "R11: the integral stock catch"},
    {"id": "measure Q6 (charging-handle path)", "closed_by": "R6 / RP3"},
    {"id": "Q1 (scale 690 or ~625)", "closed_by": "R26: 625 mm (orchestrator ruling 2026-10-09)"},
    {"id": "Q16 (selector detents)", "closed_by": "R27: the design call, sheet pose = SEMI (orchestrator ruling)"},
    {"id": "Q17 (folded-stock retention)", "closed_by": "R28: the moulded lug, X %.1f-%.1f, %.1f mm proud of the pad's "
     "side (orchestrator ruling)" % (LUG["body_X_ext"][0], LUG["body_X_ext"][1], LUG["proud_of_pad_side_ext"])}]


# ================================================================================================ S0 validator
REQ = ("id", "display", "bone", "process", "joint", "slot", "finish", "texel_class", "construction", "authority",
       "confidence", "sources")
missing = []
for p in parts:
    for k in REQ:
        if p.get(k) in (None, "", []):
            missing.append(f"{p['id']}.{k}")
    if not p.get("box_M") and not p.get("dims"):
        missing.append(f"{p['id']}.box_M|dims")
for s in GUN_SOCKETS + MAG_SOCKETS:
    if any(v is None for v in s.get("M_mm", s.get("M_mm_seated", []))):
        missing.append(f"socket {s['socket']}")
# text and number consistency (check fix C12): stale mechanism words in the sections the build reads, and numbers
# that must agree across parts / bones / clips / sockets / gates
import re  # noqa: E402
LIVE = {k: spec[k] for k in ("parts", "bones", "clips", "gates", "fold", "sockets", "joints_clearance_mm")}
live_txt = json.dumps(clean_txt := LIVE, default=str).lower()
STALE = [r"\bstud\b", r"bolt_catch under", r"safe -> semi -> auto -> safe", r"selector rest = safe", r"\bslap", r"0\.\.-13",
         r"slide centre \(y \+?20", r"pins \(3\)", r"read at form", r"whole length\)"]
incons = [f"stale text /{pat}/" for pat in STALE if re.search(pat, live_txt)]
P_ = {q["id"]: q for q in parts}
B_ = {b["bone"]: b for b in spec["bones"]["table"]}
S_ = {q["socket"]: q for q in GUN_SOCKETS}
checks = {
    "trigger pull: part = bone = clip": P_["trigger"]["dims"]["pull_rot_Y_deg"] == B_["trigger"]["limits_deg"][1]
    == spec["clips"]["values"]["trigger_pull_deg"] > 0,
    "paddle pivot: part = bone": P_["mag_release"]["dims"]["pivot_XZ"] == [B_["mag_release"]["head_M"][0],
                                                                         B_["mag_release"]["head_M"][2]],
    "paddle release: part = bone = clip": P_["mag_release"]["dims"]["release_rot_Y_deg"]
    == B_["mag_release"]["limits_deg"][1] == spec["clips"]["values"]["mag_release_deg"] < 0,
    "lower rail count": P_["lower_rail"]["dims"]["slots"] == len(LR_SLOTS_X) == LR_N
    and f"{LR_N} slots" in P_["lower_rail"]["construction"],
    "selector clip starts and ends at SEMI": spec["clips"]["values"]["selector_clip"].split(" -> ")[0].startswith("SEMI")
    and spec["clips"]["values"]["selector_clip"].split(" -> ")[-1].startswith("SEMI"),
    "sight sockets on the aperture line": S_["Sight"]["M_mm"][2] == S_["SightFront"]["M_mm"][2] == APERTURE[1],
    "rear sight folded <= B4c": P_["sight_rear"]["dims"]["folded_max_Z"] <= B4C_REAR,
    "paddle >= 0.3 behind the wall": WALL_OUT(PAD_TOP_Z) - PAD_FRONT_X >= 0.3 - 1e-9,
    "paddle nose clears the notch": PAD_NOSE_TRAVEL >= PAD_ENGAGE + 0.3,
    "charging arm moves outward": ARM_MIN_DY >= 0.0,
    "neck seated >= 2.0": NECK_RISE_IN >= 2.0,
    "lug engagement >= 1.0": F3_ENGAGE_X >= 1.0,
    "fold min Y covers every stock-bone part": FOLD_Y_MIN == min(FOLD_Y_MIN_BY.values()),
    "lower rail end webs >= 3.0": LR_SLOTS_X[0] - SLOT_W / 2 - lrl["X"][0] >= 3.0,
}
incons += [k for k, ok in checks.items() if not ok]
spec["S0"] = {"missing_fields": missing, "inconsistencies": incons,
              "consistency_checks": {k: bool(v) for k, v in checks.items()},
              "status": "PASS" if not missing and not incons else "FAIL",
              "provisional": [s["socket"] for s in GUN_SOCKETS + MAG_SOCKETS if s["state"] != "final"],
              "real_figures_within_5pct": {"overall": f"{OVERALL:.0f} vs the real pattern's 690 (R26 ruling)", "barrel": f"{BARREL_LEN:.0f} vs 200 (Q2, sheet)",
                                           "folded": f"{FOLDED_LEN} vs 450 (R20, sheet)"}}
spec["counts"] = {"parts": len(parts), "gun_sockets": len(GUN_SOCKETS), "mag_sockets": len(MAG_SOCKETS),
                  "bones": 11, "rulings": len(RULINGS), "resolutions": len(RES), "open_questions": len(OPEN_Q),
                  "top_rail_cut_slots": len(CUT_SLOTS), "lower_rail_slots": LR_N}


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating,)):
        return round(float(o), 4)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, float):
        return round(o, 4) + 0.0
    return o


OUT.write_text(json.dumps(clean(spec), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)}: {len(parts)} parts, {len(GUN_SOCKETS)}+{len(MAG_SOCKETS)} sockets, "
      f"{len(RES)} resolutions, S0 {spec['S0']['status']}")
print(f"bore Z_M {BORE_Z} (RIGHT {BORE_Z_RIGHT}), device OD {DEVICE_OD}; grip rake {GRIP_RAKE}, Grip_M ({GX}, {GZ}); "
      f"mag O {r1(MAG_O, 2)} rake {MAG_RAKE} theta {THETA_MAG_Y:.3f}, top {MAG_TOP_ALONG:.1f} floor {MAG_FLOOR_ALONG:.1f}")
print(f"rail teeth {n_teeth}, toothed slots {TOOTHED_SLOTS[0]}..{TOOTHED_SLOTS[-1]}, front lug {FRONT_LUG}, X {SLOT_X_LIST}")
print(f"hinge Y {HINGE_Y}, fold mid {FOLD_MID_Y}, knuckle proud {KNUCKLE_PROUD_R}, folded length {FOLDED_LEN}; "
      f"selector {SEL_ROT}; R gun {R_GUN:.1f} mag {R_MAG:.1f} folded {R_FOLDED:.1f}; SS mag {SS_MAG}")
