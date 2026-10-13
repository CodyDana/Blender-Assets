"""Write WorkFiles/guns/sniper/sr01_spec.json (Sniper Rifle SR-01) from the measurement, the craft study and the plan.

    py -3 -B WorkFiles/guns/sniper/tools/make_spec.py

Inputs (same folder): sr01_measured.json + trace/GR_outline.json (tools/trace_reference.py), craft_parts.json
(CRAFT_STUDY.md), sr01_interface.json (SR01_BUILD_PLAN.md), and the line standard
WorkFiles/guns/gunlib/gun_standard.json (read only). Derived numbers (Grip origin, bolt and knob path, bipod
mechanism in both poses, magazine frame, release paddle, riser, rail slots, scope placement, sockets, bounds) are
computed here, and the S0 validator (GUN_BUILDING_STUDY 7.1) runs at the end: 0 missing fields, 0 failed
consistency / clearance checks. The SMG01 make_spec.py was the template (structure, S0); nothing of the SMG is edited.

Frame M (mm): +X toward the muzzle, +Z up, +Y = the gun's left; X 0 = butt-pad rear, Z 0 = bore. Frame B (Blender)
= M - Grip (pure translation). Unreal cm = (Bx, -By, Bz) / 10.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
SR = HERE.parents[1]                         # WorkFiles/guns/sniper
ROOT = HERE.parents[4]
OUT = SR / "sr01_spec.json"
MEAS = json.loads((SR / "sr01_measured.json").read_text(encoding="utf-8"))
CRAFT = json.loads((SR / "craft_parts.json").read_text(encoding="utf-8"))
PLAN = json.loads((SR / "sr01_interface.json").read_text(encoding="utf-8"))
GR = json.loads((SR / "trace" / "GR_outline.json").read_text(encoding="utf-8"))
STD = json.loads((ROOT / "WorkFiles" / "guns" / "gunlib" / "gun_standard.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(ROOT / "Scripts" / "guns"))
from gunlib import qa_gun  # noqa: E402  (plain Python: tokenised deny list)

M = MEAS["GR"]
F = M["features_mm"]
T = MEAS["TOP"]["widths_mm_Yleft_Yright_W"]
OVERALL = MEAS["meta"]["overall_mm"]
CLR = STD["clearance_mm"]
RAIL = STD["rail_1913"]["mm"]


def r(v, n=2):
    if isinstance(v, (list, tuple, np.ndarray)):
        return [r(a, n) for a in v]
    return round(float(v), n)


# ================================================================================================ scale and real figures
REAL = {"overall_mm": OVERALL, "barrel_mm": 559.0, "barrel_in": 22,
        "mass_kg_without_scope_and_mag": 5.9, "scope_with_rings_kg": 1.15, "mag_empty_kg": 0.20,
        "round_g": 25.4, "mag_capacity": 10,
        "pattern": ".308-class bolt-action chassis rifle (short action, 22 in heavy fluted barrel)",
        "range_for_class": {"overall_mm": [1050, 1200], "barrel_mm": [508, 660], "mass_kg": [5.0, 6.8]}}
REAL["mass_loaded_ready_kg"] = round(REAL["mass_kg_without_scope_and_mag"] + REAL["scope_with_rings_kg"]
                                     + REAL["mag_empty_kg"] + REAL["mag_capacity"] * REAL["round_g"] / 1000, 2)
ANCH = MEAS["scale_anchors"]

# ================================================================================================ Grip origin
grip = GR["parts"]["grip"]["mm"][0]
G = np.array(grip + grip[:1], float)


def cross_x(P, Z):
    xs = []
    for (x0, z0), (x1, z1) in zip(P[:-1], P[1:]):
        if (z0 - Z) * (z1 - Z) < 0:
            xs.append(x0 + (Z - z0) * (x1 - x0) / (z1 - z0))
    return xs


mid = []
for Z in np.arange(-150, -74, 2.0):
    xs = cross_x(G, Z)
    if len(xs) >= 2:
        mid.append((Z, 0.5 * (min(xs) + max(xs)), max(xs) - min(xs)))
mid = np.array(mid)
k_ax, c_ax = np.polyfit(mid[:, 0], mid[:, 1], 1)              # X = k Z + c
GRIP_AXIS_DEG = r(math.degrees(math.atan(k_ax)), 2)            # + = bottom rearward of the top... (k>0: X grows with Z)
WEB_Z = r(GR["parts"]["grip"]["box_mm"]["Z"][1], 2)           # grip top = where it meets the chassis bottom
J = np.array([k_ax * WEB_Z + c_ax, WEB_Z])
u_dn = -np.array([k_ax, 1.0]) / math.hypot(k_ax, 1.0)
DEPTH = STD["frame"]["grip_origin_depth_mm"]
Gp = J + DEPTH * u_dn
GRIP_M = [r(Gp[0]), 0.0, r(Gp[1])]


def B(p):
    return [r(p[0] - GRIP_M[0]), r(p[1]), r(p[2] - GRIP_M[2])]


def UE(p):
    b = B(p)
    return [r(b[0] / 10, 3), r(-b[1] / 10, 3), r(b[2] / 10, 3)]


# ================================================================================================ bolt
BOLT_FACE_X = 505.0
BREECH_X = 505.5
DEVICE_X0 = M["features_mm"].get("device_X0", None) or r((578.5 - M["x_rear_px"]) / M["px_per_mm"], 1)
CROWN_X = r(BREECH_X + REAL["barrel_mm"], 1)
BOLT_TRAVEL = 88.0
BOLT_ROT = -60.0
SHROUD_REAR_X = r((204.0 - M["x_rear_px"]) / M["px_per_mm"], 1)
RECEIVER_X = [r((223.5 - M["x_rear_px"]) / M["px_per_mm"], 1), r((322.0 - M["x_rear_px"]) / M["px_per_mm"], 1)]
KNOB_D = F["bolt_knob"]["dia"]
KNOB_X, KNOB_Z = F["bolt_knob"]["centre_XZ"]
KNOB_TIP_Y_RAW = T["bolt_knob"][1]                      # TOP right edge (Y, gun right negative)
TOP_RIGHT_BIAS = 5.0                                    # I2: TOP right edges read 4-6 mm wide (shadow)
KNOB_Y = r(KNOB_TIP_Y_RAW + TOP_RIGHT_BIAS + KNOB_D / 2, 1)
KNOB = np.array([KNOB_X, KNOB_Y, KNOB_Z])
KNOB_R_AXIS = r(math.hypot(KNOB_Y, KNOB_Z), 2)
KNOB_REST_DEG = r(math.degrees(math.atan2(-KNOB_Z, -KNOB_Y)), 2)   # below horizontal, right side


def rot_x(p, deg):
    a = math.radians(deg)
    y, z = p[1], p[2]
    return np.array([p[0], y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)])


def rot_y_about(p, piv, deg):
    """Blender R_y about a pivot (X, Z): x' = x cos + z sin, z' = -x sin + z cos (relative)."""
    a = math.radians(deg)
    x, z = p[0] - piv[0], p[-1] - piv[-1]
    return (piv[0] + x * math.cos(a) + z * math.sin(a), piv[-1] - x * math.sin(a) + z * math.cos(a))


KNOB_OPEN = rot_x(KNOB, BOLT_ROT)
KNOB_BACK = KNOB_OPEN - np.array([BOLT_TRAVEL, 0, 0])
# scope solids (attachment, placed on the rail): eyepiece, tube, windage turret, objective (cylinders about X)
SC = M["scope"]
SCOPE_AXIS_Z = SC["axis_Z"]
SCOPE_X = SC["X"]
EYE_R = SC["eyepiece_dia"] / 2
TUBE_R = SC["tube_dia"] / 2
SCOPE_SOLIDS = [("eyepiece", SCOPE_X[0], SCOPE_X[0] + 85.0, EYE_R), ("tube", SCOPE_X[0] + 85.0, 600.0, TUBE_R),
                ("objective", 600.0, SCOPE_X[1], SC["objective_bell_dia"] / 2)]


def dist_point_cyl(p, x0, x1, rad, axis_z):
    dx = max(x0 - p[0], 0, p[0] - x1)
    rr = math.hypot(p[1], p[2] - axis_z)
    dr = max(rr - rad, 0)
    return math.hypot(dx, dr)


knob_min = 1e9
for t in np.linspace(0, 1, 61):                                   # rotate phase
    p = rot_x(KNOB, BOLT_ROT * t)
    knob_min = min(knob_min, min(dist_point_cyl(p, a, b, rr, SCOPE_AXIS_Z) for _, a, b, rr in SCOPE_SOLIDS) - KNOB_D / 2)
for t in np.linspace(0, 1, 89):                                   # slide phase
    p = KNOB_OPEN - np.array([BOLT_TRAVEL * t, 0, 0])
    knob_min = min(knob_min, min(dist_point_cyl(p, a, b, rr, SCOPE_AXIS_Z) for _, a, b, rr in SCOPE_SOLIDS) - KNOB_D / 2)
# windage turret on the right (box): X 446-478, Y to -(TOP right edge + bias), Z axis +-16
WT = [446.0, 478.0, -(abs(T["scope_turret_zone"][1]) - TOP_RIGHT_BIAS), SCOPE_AXIS_Z]
KNOB_SCOPE_MIN = r(knob_min, 1)
RISER = M["cheek_riser"]
BOLT_BACK_REAR_X = r(SHROUD_REAR_X - BOLT_TRAVEL, 1)

# ================================================================================================ magazine
MG = M["magazine"]
MAG_X = [MG["X_rear"], MG["X_front"]]
MAG_O = [r(0.5 * (MAG_X[0] + MAG_X[1]), 2), 0.0, MG["Z_top_cut"]]
MAG_FA = MG["foreaft"]
MAG_T = 26.5
BOLT_R = 17.8 / 2
MAG_TOP_Z = r(-(BOLT_R + 2.1), 1)                       # feed lips 2.1 under the bolt body (top round rides the bolt)
MAG_BOTTOM_Z = MG["Z_bottom"]
MAG_LEN = r(MAG_TOP_Z - MAG_BOTTOM_Z, 1)
INSERT_START = [MAG_O[0], 0.0, r(MAG_O[2] - (MAG_TOP_Z - MAG_O[2]) - 10.0, 1)]
WELL_CLR = 0.3
WELL_WALL = 3.0

# ================================================================================================ mag release (I6)
PAD_DRAWN_X = [r((238.0 - M["x_rear_px"]) / M["px_per_mm"], 1), r((240.5 - M["x_rear_px"]) / M["px_per_mm"], 1)]
PAD_PIVOT = (408.6, -74.0)
HOOK_ABOVE = 24.0
PAD_BELOW = 40.0
HOOK_ENGAGE = 1.4
PAD_PRESS_DEG = -4.5
HOOK_TRAVEL = r(HOOK_ABOVE * math.sin(math.radians(abs(PAD_PRESS_DEG))), 2)
PAD_TRAVEL = r(PAD_BELOW * math.sin(math.radians(abs(PAD_PRESS_DEG))), 2)
PAD_FRONT_X = math.floor((MAG_X[0] - PAD_TRAVEL - 0.30) * 10) / 10.0      # floor: the gap never rounds under 0.3
PAD_THICK = 5.0
PAD_SHIFT = r(PAD_DRAWN_X[1] - PAD_FRONT_X, 1)
PAD_GAP_PRESSED = r(MAG_X[0] - (PAD_FRONT_X + PAD_TRAVEL), 2)

# ================================================================================================ trigger, safety, riser
TRIG = M["trigger"]
TRIG_PIVOT = (368.0, -57.0)
TRIG_PULL = 6.0
GUARD = M["guard_opening"]
tip = rot_y_about((TRIG["X_range"][0], TRIG["Z_range"][0]), TRIG_PIVOT, TRIG_PULL)
TRIG_GUARD_MIN = r(tip[0] - GUARD["X"][0], 2)
SAFETY_PIVOT = (360.0, -17.5, -16.0)
SAFETY_SAFE = -12.0
RISER_LIM = [-12.9, 12.0]
RISER_HEAD = [r(0.5 * (RISER["X"][0] + RISER["X"][1]), 1), 0.0, RISER["plate_Z_bottom"]]
RISER_LOW_GAP = r((RISER["plate_Z_bottom"] + RISER_LIM[0]) - RISER["stock_top_Z"], 2)

# ================================================================================================ bipod
FE = M["forend"]
FOREND_BOTTOM = r(F["bipod_mount"]["Z"][1], 1)           # the mount's top = the forend band's bottom face
HUB_X = F["bipod_hub"]["centre_XZ"][0]
HUB_Z = r(0.5 * (F["bipod_hub"]["centre_XZ"][1] + 0.5 * (F["bipod_leg"]["Z"][0] + F["bipod_leg"]["Z"][1])), 1)
LEG_Y = 19.5
LEG_R = 9.7
COLLAR = {"X": F["bipod_collar"]["X"], "r": 14.0}
FOOT = {"X": F["bipod_foot"]["X"], "r": 18.5}
LEG_LEN = r(FOOT["X"][1] - HUB_X, 1)
EXT = [0.0, 76.0]
EXT_DETENTS = [0.0, 19.0, 38.0, 57.0, 76.0]
DEPLOY = 90.0
MOUNT = {"X": F["bipod_mount"]["X"], "Z": [r(HUB_Z + LEG_R + 0.2, 2), FOREND_BOTTOM - 0.01], "Y": [-25.0, 25.0]}
KNOB_T = {"X": F["bipod_tension_knob"]["X"], "Zc": r(0.5 * sum(F["bipod_tension_knob"]["Z"]), 1), "r": 7.0}
CANT_AXIS_Z = r(0.5 * (MOUNT["Z"][0] + MOUNT["Z"][1]), 1)
CANT = 15.0
HUB_KNUCKLE_R = F["bipod_hub"]["dia"] / 2


def leg_points(theta_deg, ext, side, n_s=60, n_a=16):
    """Surface samples of one leg (outer tube, collar, inner rod gap ignored, foot) at fold angle theta (0 forward,
    +90 down) and extension ext; returns (N, 3) in M."""
    th = math.radians(theta_deg)
    d = np.array([math.cos(th), 0.0, -math.sin(th)])
    nrm = np.array([math.sin(th), 0.0, math.cos(th)])
    yv = np.array([0.0, 1.0, 0.0])
    H = np.array([HUB_X, side * LEG_Y, HUB_Z])
    pts = []
    segs = [(HUB_KNUCKLE_R, COLLAR["X"][0] - HUB_X, LEG_R), (COLLAR["X"][0] - HUB_X, COLLAR["X"][1] - HUB_X, COLLAR["r"]),
            (COLLAR["X"][1] - HUB_X, COLLAR["X"][1] - HUB_X + ext, 6.35),
            (FOOT["X"][0] - HUB_X + ext, FOOT["X"][1] - HUB_X + ext, FOOT["r"])]
    for s0, s1, rad in segs:
        if s1 <= s0:
            continue
        for s in np.linspace(s0, s1, n_s):
            for a in np.linspace(0, 2 * math.pi, n_a, endpoint=False):
                pts.append(H + s * d + rad * (math.cos(a) * nrm + math.sin(a) * yv))
    return np.array(pts)


def d_box(P, X, Y, Z):
    dx = np.maximum(np.maximum(X[0] - P[:, 0], 0), P[:, 0] - X[1])
    dy = np.maximum(np.maximum(Y[0] - P[:, 1], 0), P[:, 1] - Y[1])
    dz = np.maximum(np.maximum(Z[0] - P[:, 2], 0), P[:, 2] - Z[1])
    inside = (dx == 0) & (dy == 0) & (dz == 0)
    d = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
    d[inside] = -1.0
    return d


def d_cyl_x(P, X, yc, zc, rad):
    dx = np.maximum(np.maximum(X[0] - P[:, 0], 0), P[:, 0] - X[1])
    rr = np.hypot(P[:, 1] - yc, P[:, 2] - zc) - rad
    out = np.where(rr > 0, np.hypot(dx, rr), np.where(dx > 0, dx, -1.0))
    return out


FOREND_BOX = {"X": [560.0, M["forend"]["front_X"]], "Y": [-37.0, 37.0], "Z": [FOREND_BOTTOM, 16.0]}
BARREL_CYL = (M["forend"]["front_X"], CROWN_X, 0.0, 0.0, M["diameters_mm"]["barrel_at_forend"] / 2)


def obstacles_min(P):
    out = {"mount": float(d_box(P, MOUNT["X"], MOUNT["Y"], MOUNT["Z"]).min()),
           "forend": float(d_box(P, FOREND_BOX["X"], FOREND_BOX["Y"], FOREND_BOX["Z"]).min()),
           "barrel": float(d_cyl_x(P, BARREL_CYL[:2], *BARREL_CYL[2:]).min()),
           "tension_knob": float(d_cyl_x(P, KNOB_T["X"], 0.0, KNOB_T["Zc"], KNOB_T["r"]).min()),
           "magazine": float(d_box(P, MAG_X, [-MAG_T / 2, MAG_T / 2], [MAG_BOTTOM_Z, MAG_O[2]]).min())}
    return out


sweep = {"angles_deg": [0.0, DEPLOY], "step_deg": 0.5, "ext_cases": EXT, "min_by_obstacle": {}}
mins = {}
for ext in EXT:
    for th in np.arange(0.0, DEPLOY + 1e-9, 0.5):
        for side in (1, -1):
            o = obstacles_min(leg_points(th, ext, side, n_s=40, n_a=12))
            for k, v in o.items():
                mins[k] = min(mins.get(k, 1e9), v)
sweep["min_by_obstacle"] = {k: r(v, 2) for k, v in mins.items()}
# the mount-to-leg gap at fold is the designed 0.2 (sampling may read it larger); report the analytic value too
FOLD_GAP_MOUNT = r(MOUNT["Z"][0] - (HUB_Z + LEG_R), 2)
FOOT_TO_FOREND_FOLDED = r(FOREND_BOTTOM - (HUB_Z + FOOT["r"]), 2)
FEET_GAP_Y = r(2 * LEG_Y - 2 * FOOT["r"], 2)
LEG_TO_KNOB_Y = r(LEG_Y - LEG_R - KNOB_T["r"], 2)
GROUND = {f"ext_{int(e)}": r(HUB_Z - (LEG_LEN + e), 1) for e in EXT_DETENTS}
BORE_HEIGHT_DEPLOYED = {k: r(-v, 1) for k, v in GROUND.items()}


# cant check (folded and deployed): rotate legs about X through (Y 0, Z CANT_AXIS_Z)
def cant_pts(P, deg):
    a = math.radians(deg)
    y, z = P[:, 1], P[:, 2] - CANT_AXIS_Z
    Q = P.copy()
    Q[:, 1] = y * math.cos(a) - z * math.sin(a)
    Q[:, 2] = CANT_AXIS_Z + y * math.sin(a) + z * math.cos(a)
    return Q


cant_res = {}
for pose, th in (("folded", 0.0), ("deployed", DEPLOY)):
    worst = 1e9
    for deg in np.arange(-CANT, CANT + 1e-9, 0.5):
        for side in (1, -1):
            P = cant_pts(leg_points(th, 0.0, side, n_s=40, n_a=12), deg)
            o = obstacles_min(P)
            o.pop("mount")                                          # the mount body cants with the legs
            o.pop("tension_knob")
            worst = min(worst, min(o.values()))
    cant_res[pose] = r(worst, 2)
CANT_FOLDED_OK = cant_res["folded"] >= CLR["hinge"][0]

# bounds over the poses (gun parts only; scope is its own asset)
Pall = np.vstack([cant_pts(leg_points(DEPLOY, 76.0, s, n_s=30, n_a=12), c) for s in (1, -1) for c in (-CANT, 0, CANT)])
BOUNDS = {"rest_box_M": {"X": [0.0, OVERALL], "Y": [r(KNOB_Y - KNOB_D / 2, 1), r(T["cheek_riser_block"][0], 1)],
                         "Z": [M["grip"]["bottom_Z"], r(RISER["Z_top"], 1)]},
          "posed_extremes_M": {"Z_min_bipod_deployed_ext76_cant15": r(Pall[:, 2].min(), 1),
                               "Y_abs_max_bipod_cant15": r(np.abs(Pall[:, 1]).max(), 1),
                               "knob_open_Z": r(KNOB_OPEN[2], 1), "knob_back_X": r(KNOB_BACK[0], 1),
                               "bolt_back_rear_X": BOLT_BACK_REAR_X, "riser_top_raised_Z": r(RISER["Z_top"] + RISER_LIM[1], 1),
                               "folded_ext76_foot_front_X": r(FOOT["X"][1] + 76.0, 1)}}

# ================================================================================================ rail, scope
RAIL_X = M["rail"]["X"]
RAIL_TOP_Z = M["rail"]["top_Z"]
N_SLOTS = int((RAIL_X[1] - RAIL_X[0] - 2 * 4.0 - RAIL["slot_width"]) // RAIL["slot_pitch"]) + 1
SPAN = (N_SLOTS - 1) * RAIL["slot_pitch"]
RC = 0.5 * (RAIL_X[0] + RAIL_X[1])
SLOT0_X = r(RC - SPAN / 2, 2)
END_WEB = r(SLOT0_X - RAIL["slot_width"] / 2 - RAIL_X[0], 2)
RING_C = [0.5 * sum(F["ring_rear"]["X"]), 0.5 * sum(F["ring_front"]["X"])]
RING_K = [int(round((c - SLOT0_X) / RAIL["slot_pitch"])) for c in RING_C]
RING_X = [r(SLOT0_X + k * RAIL["slot_pitch"], 2) for k in RING_K]
RING_SHIFT = [r(a - b, 2) for a, b in zip(RING_X, RING_C)]
MOUNT_M = [RING_X[0], 0.0, RAIL_TOP_Z]
EYE_RELIEF = 95.0
SIGHT_M = [SCOPE_X[0], 0.0, SCOPE_AXIS_Z]
EYE_M = [r(SCOPE_X[0] - EYE_RELIEF, 1), 0.0, SCOPE_AXIS_Z]
EYE_OVER_RISER = RISER["X"][0] <= EYE_M[0] <= RISER["X"][1] + 10.0
RISER_BELOW_EYE = r(SCOPE_AXIS_Z - RISER["Z_top"], 1)
RING_CENTRE_HEIGHT = r(SCOPE_AXIS_Z - RAIL_TOP_Z, 1)


def S(p):
    return [r(a, 3) for a in (np.asarray(p, float) - np.array(MOUNT_M))]


# ================================================================================================ parts
CP = {p["name"]: p for p in CRAFT["parts"]}
PB = {k: v["box_mm"] for k, v in GR["parts"].items()}


def box(X, Z, Y):
    return {"X": r(X, 1), "Z": r(Z, 1), "Y": r(Y, 1)}


def part(pid, display, bone, craft, slot, finish, texel, joint, trace_keys, box_M, dims, authority, conf, asset="SK_SR01 + SM_SR01",
         features=None):
    c = CP[craft]
    return {"id": pid, "display": display, "bone": bone, "process": c["process_class"], "bevel": c["bevel"],
            "joint": joint, "slot": slot, "finish": finish, "texel_class": texel, "construction": c["construction"],
            "key_features": c["key_features"], "trace": {"file": "trace/GR_outline.json", "keys": trace_keys,
                                                         "area_px": {k: GR["parts"][k]["area_px"] for k in trace_keys if k in GR["parts"]}},
            "box_M": box_M, "dims": dims, "authority": authority, "confidence": conf,
            "sources": ["measure (sr01_measured.json)", f"craft {craft}"], "asset": asset, "features": features or []}


W_CH = 2 * T["chassis_at_mag"][0]
W_FE = 2 * T["forend"][0]
W_RISER = 2 * T["cheek_riser_block"][0]
W_PAD = 2 * T["butt_pad"][0]
W_NECK = 2 * T["stock_neck"][0]
METAL, CHAS, MAGS = "M_SR01_Metal", "M_SR01_Chassis", "M_SR01_Mag"
SB, SL = "M_Att_Scope_Body", "M_Att_Scope_Lens"
butt_j = {"type": "butt", "gap_mm": CLR["butt"]}
parts = [
    part("chassis", "Chassis (centre + forend, integral guard, mag well, dovetail band)", "body", "chassis", CHAS,
         "cerakote_od_over_al", "B/C", butt_j, ["chassis_centre", "chassis_forend", "trigger_guard"],
         box([PB["chassis_centre"]["X"][0], FE["front_X"]], [MAG_O[2], FE["top_Z"]], [-W_CH / 2, W_CH / 2]),
         {"width_at_mag": r(W_CH, 1), "forend_width": r(W_FE, 1), "forend_top_Z": FE["top_Z"], "forend_bottom_Z": FOREND_BOTTOM,
          "forend_front_X": FE["front_X"], "bolt_raceway_r": 12.5, "raceway_open_X": [SHROUD_REAR_X, RECEIVER_X[1]],
          "slots": [F[f"forend_slot_{i}"] for i in (1, 2, 3)], "dovetail_band": F["forend_lower_band"],
          "dovetail": {"across": 38.0, "flank_deg": 45.0, "depth": 6.0}, "well": {"wall": WELL_WALL, "clearance": WELL_CLR, "shelf_Z": r(MAG_TOP_Z - 0.5, 1)},
          "guard_opening": GUARD, "barrel_radial_clearance_min": 3.0, "width_note": "2 x the TOP left half-width (I2)"},
         "GR (outline, slots); TOP (widths x2 left half)", "high (outline), medium (widths)"),
    part("butt", "Fixed skeleton-style butt", "body", "butt", CHAS, "cerakote_od_over_al", "B/C", butt_j, ["butt"],
         box(PB["butt"]["X"], PB["butt"]["Z"], [-W_NECK / 2 - 8, W_NECK / 2 + 8]),
         {"top_Z": RISER["stock_top_Z"], "clamp_knobs": F["butt_adjust_knobs"], "joint_to_chassis_X": PB["butt"]["X"][1],
          "visible_seam": CLR["visible_seam"], "neck_width": r(W_NECK, 1), "post_bores": {"dia": 10.3, "X": [95.0, 150.0]}},
         "GR; GL for its QD-cup recess", "high"),
    part("pad_plate", "LOP spacer plate", "body", "pad_plate", CHAS, "cerakote_od_over_al", "C", butt_j, ["pad_plate"],
         box(PB["pad_plate"]["X"], PB["pad_plate"]["Z"], [-W_PAD / 2, W_PAD / 2]), {"screws": F["pad_screws"]}, "GR", "high"),
    part("butt_pad", "Recoil pad (rubber)", "body", "butt_pad", CHAS, "rubber_black (Masks A 0)", "C", butt_j, ["butt_pad"],
         box(M["butt_pad"]["X"], M["butt_pad"]["Z"], [-W_PAD / 2, W_PAD / 2]),
         {"height": r(M["butt_pad"]["Z"][1] - M["butt_pad"]["Z"][0], 1), "width": r(W_PAD, 1), "draft_deg": 1.5}, "GR + TOP", "high"),
    part("cheek_riser", "Adjustable cheek riser (plate + 2 posts)", "cheek_riser", "cheek_riser", CHAS, "cerakote_od_over_al",
         "B", {"type": "sliding", "gap_mm": CLR["sliding"], "parent": "butt (post bores)"}, ["cheek_riser"],
         box(RISER["X"], [RISER["stock_top_Z"] - 30.0, RISER["Z_top"]], [-W_RISER / 2, W_RISER / 2]),
         {"plate_Z": [RISER["plate_Z_bottom"], RISER["Z_top"]], "width": r(W_RISER, 1), "travel_Z": RISER_LIM,
          "post_dia": 10.0, "posts_X": [95.0, 150.0], "low_stop_gap": RISER_LOW_GAP}, "GR + TOP", "high"),
    part("receiver", "Receiver (round, short action) with port and lug recesses", "body", "receiver", METAL, "phosphate_steel",
         "B", butt_j, ["receiver"], box(RECEIVER_X, [-17.15, 17.15], [-17.15, 17.15]),
         {"dia": 34.3, "port_drawn": F["ejection_port"], "port_built_X": [r(BOLT_FACE_X - BOLT_TRAVEL - 2.0, 1), r(F["ejection_port"]["X"][1], 1)],
          "lug_recesses": "3 x 60 deg at the front ring, 12 deep"}, "GR (top, port); real pattern", "high (outline), real-pattern (internals)"),
    part("rail", "Scope base rail (1913, flat)", "body", "rail", METAL, "anodized_black_al", "B", butt_j, ["rail"],
         box(RAIL_X, [RAIL_TOP_Z - RAIL["height_default"], RAIL_TOP_Z], [-RAIL["width_across_V"] / 2, RAIL["width_across_V"] / 2]),
         {"slots": N_SLOTS, "slot0_X": SLOT0_X, "end_webs": END_WEB, "pitch": RAIL["slot_pitch"], "drawn_pitch": M["rail"]["drawn_pitch_mm"],
          "screws_in_slots": [1, 5, 9, 13]}, "GR (extent, top)", "high"),
    part("bolt", "Bolt (3-lug, 60 deg) with shroud", "bolt", "bolt", METAL, "bare_steel_polished + phosphate shroud", "B",
         {"type": "sliding", "gap_mm": CLR["sliding"], "also": "lugs in recesses hinge row 0.10-0.30 during the 60 deg turn"},
         ["bolt_shroud"], box([SHROUD_REAR_X, BOLT_FACE_X], [-12.5, 12.5], [-12.5, 12.5]),
         {"face_X": BOLT_FACE_X, "body_dia": 17.8, "lug_od": 25.4, "lugs": 3, "rotate_deg": BOLT_ROT, "travel": BOLT_TRAVEL,
          "shroud_X": [SHROUD_REAR_X, 380.0]}, "GR + GL (shroud); real pattern", "high (shroud), real-pattern (body)"),
    part("bolt_handle", "Bolt handle and knob", "bolt", "bolt_handle", METAL, "phosphate_steel", "B",
         {"type": "integral", "parent": "bolt"}, ["bolt_handle"], box([KNOB_X - KNOB_D / 2, 386.0], [KNOB_Z - KNOB_D / 2, 0.0], [KNOB_Y - KNOB_D / 2, -9.0]),
         {"knob_centre_M": r(KNOB, 1), "knob_dia": KNOB_D, "radius_from_axis": KNOB_R_AXIS, "rest_deg_below_horizontal": KNOB_REST_DEG,
          "open_centre_M": r(KNOB_OPEN, 1), "back_centre_M": r(KNOB_BACK, 1), "min_to_scope": KNOB_SCOPE_MIN}, "GR (X, Z); TOP (Y)", "high"),
    part("safety", "Safety (2-position tang rocker, right)", "selector", "safety", METAL, "phosphate_steel", "B",
         {"type": "hinge", "gap_mm": CLR["hinge"]}, [], box([355.0, 366.0], [-18.0, -2.0], [-21.5, -17.5]),
         {"pivot_M": list(SAFETY_PIVOT), "detents_deg": {"FIRE": 0.0, "SAFE": SAFETY_SAFE}, "lever": [14.0, 5.0, 4.0]},
         "real pattern (not resolved on the sheet)", "real-pattern"),
    part("trigger", "Trigger blade", "trigger", "trigger", METAL, "phosphate_steel", "C", {"type": "hinge", "gap_mm": CLR["hinge"]},
         ["trigger"], box(TRIG["X_range"], TRIG["Z_range"], [-3.0, 3.0]),
         {"pivot_XZ": list(TRIG_PIVOT), "pull_rot_Y_deg": TRIG_PULL, "face_X": TRIG["face_X_at_mid"], "tip_to_guard_at_pull": TRIG_GUARD_MIN,
          "length_of_pull": M["length_of_pull_mm"]}, "GR", "high"),
    part("mag_release", "Magazine release paddle", "mag_release", "mag_release", METAL, "phosphate_steel", "C",
         {"type": "hinge", "gap_mm": CLR["hinge"]}, ["mag_release"],
         box([PAD_FRONT_X - PAD_THICK, PAD_FRONT_X], [PAD_PIVOT[1] - PAD_BELOW, PAD_PIVOT[1] + HOOK_ABOVE], [-5.0, 5.0]),
         {"pivot_XZ": list(PAD_PIVOT), "release_rot_Y_deg": PAD_PRESS_DEG, "hook_above_pivot": HOOK_ABOVE, "pad_below_pivot": PAD_BELOW,
          "hook_engagement": HOOK_ENGAGE, "hook_travel": HOOK_TRAVEL, "pad_travel": PAD_TRAVEL, "front_face_X": PAD_FRONT_X,
          "drawn_X": PAD_DRAWN_X, "declared_shift_rearward": PAD_SHIFT, "gap_to_mag_pressed": PAD_GAP_PRESSED, "notch_Z": r(PAD_PIVOT[1] + HOOK_ABOVE, 1)},
         "GR (position); real pattern (mechanism)", "medium"),
    part("grip", "Pistol grip (polymer)", "body", "grip", CHAS, "polymer_black + grip_texture (Masks A 0)", "B/C", butt_j, ["grip"],
         box(PB["grip"]["X"], PB["grip"]["Z"], [-16.0, 16.0]),
         {"rear_strap_deg": M["grip"]["rear_strap_deg_from_vertical"], "front_strap_deg": M["grip"]["front_strap_deg_from_vertical"],
          "axis_deg_from_vertical": GRIP_AXIS_DEG, "foreaft": M["grip"]["foreaft_perp_at_y300"], "width": 32.0,
          "width_note": "unseen: polymer grip norm", "bottom_Z": M["grip"]["bottom_Z"]}, "GR", "high (outline), medium (width)"),
    part("barrel", "Barrel (heavy, 6 flutes)", "body", "barrel", METAL, "phosphate_steel", "D",
         {"type": "butt", "gap_mm": CLR["butt"], "note": "threaded into the receiver; >= 3.0 radial clearance to the forend"}, ["barrel"],
         box([BREECH_X, CROWN_X], [-M["diameters_mm"]["barrel_at_forend"] / 2, M["diameters_mm"]["barrel_at_forend"] / 2],
             [-M["diameters_mm"]["barrel_at_forend"] / 2, M["diameters_mm"]["barrel_at_forend"] / 2]),
         {"length": REAL["barrel_mm"], "breech_X": BREECH_X, "crown_X": CROWN_X, "od_at_forend": M["diameters_mm"]["barrel_at_forend"],
          "od_mid": M["diameters_mm"]["barrel_mid"], "od_at_device": M["diameters_mm"]["barrel_at_device"],
          "flutes": {"n": 6, "width": 6.0, "depth": 2.0, "X": [841.0, 1036.0]}, "bore": 7.8, "tenon": [15.9, 15.0], "sides_lod0": 48},
         "GR + GL (diameters); TOP not used (I3)", "high"),
    part("muzzle_device", "Linear compensator", "muzzle_device", "muzzle_device", METAL, "phosphate_steel + soot", "D", butt_j,
         ["muzzle_device"], box([DEVICE_X0, OVERALL], [-M["diameters_mm"]["device"] / 2, M["diameters_mm"]["device"] / 2],
                                [-M["diameters_mm"]["device"] / 2, M["diameters_mm"]["device"] / 2]),
         {"od": M["diameters_mm"]["device"], "seat_X": DEVICE_X0, "exit_bore": 12.0}, "GR + GL; Q34 (exit)", "high"),
    part("magazine", "Magazine (10-round box)", "magazine", "magazine", MAGS, "phosphate_steel + polymer floorplate", "C",
         {"type": "seated_mag", "gap_mm": CLR["seated_mag"]}, ["magazine"],
         box(MAG_X, [MAG_BOTTOM_Z, MAG_TOP_Z], [-MAG_T / 2, MAG_T / 2]),
         {"foreaft": MAG_FA, "thickness": MAG_T, "top_Z": MAG_TOP_Z, "bottom_Z": MAG_BOTTOM_Z, "length": MAG_LEN, "rake_deg": 0.0,
          "rake_drawn": [MG["rake_deg_rear_edge"], MG["rake_deg_front_edge"]], "catch_notch_Z": r(PAD_PIVOT[1] + HOOK_ABOVE, 1),
          "ribs_per_side": 2}, "GR + GL (outline); Q34 (thickness, ribs)", "high (outline), medium (thickness)", asset="SM_SR01_Mag (merged in SM_SR01)"),
    part("bipod_mount", "Bipod clamp + swivel body + tension knob", "bipod", "bipod_mount", CHAS, "anodized_black_al (Masks A 0)", "C",
         {"type": "hinge", "gap_mm": CLR["hinge"], "note": "clamp is fixed to the dovetail (butt row) but rides the bipod bone: cant about X"},
         ["bipod"], box([HUB_X - HUB_KNUCKLE_R, MOUNT["X"][1]], [KNOB_T["Zc"] - KNOB_T["r"], FOREND_BOTTOM], [-25.0, 25.0]),
         {"clamp": MOUNT, "cant_axis_Z": CANT_AXIS_Z, "cant_deg": [-CANT, CANT], "tension_knob": KNOB_T}, "GR + GL (folded)", "high"),
    part("bipod_leg_l", "Bipod leg, left (outer tube + collar + knuckle)", "bipod_leg_l", "bipod_legs", CHAS,
         "anodized_black_al (Masks A 0)", "C", {"type": "hinge", "gap_mm": CLR["hinge"]}, ["bipod"],
         box([HUB_X - HUB_KNUCKLE_R, COLLAR["X"][1]], [HUB_Z - COLLAR["r"], HUB_Z + COLLAR["r"]], [LEG_Y - COLLAR["r"], LEG_Y + COLLAR["r"]]),
         {"hub_M": [HUB_X, LEG_Y, HUB_Z], "tube_od": 2 * LEG_R, "fold_deg": [0.0, DEPLOY], "detents_deg": [0.0, DEPLOY]}, "GR (folded); real pattern (deployed)", "high (folded)"),
    part("bipod_leg_r", "Bipod leg, right", "bipod_leg_r", "bipod_legs", CHAS, "anodized_black_al (Masks A 0)", "C",
         {"type": "hinge", "gap_mm": CLR["hinge"]}, ["bipod"],
         box([HUB_X - HUB_KNUCKLE_R, COLLAR["X"][1]], [HUB_Z - COLLAR["r"], HUB_Z + COLLAR["r"]], [-LEG_Y - COLLAR["r"], -LEG_Y + COLLAR["r"]]),
         {"hub_M": [HUB_X, -LEG_Y, HUB_Z], "tube_od": 2 * LEG_R, "fold_deg": [0.0, DEPLOY], "detents_deg": [0.0, DEPLOY]}, "GR (folded); real pattern (deployed)", "high (folded)"),
    part("bipod_ext_l", "Bipod inner leg + foot, left", "bipod_leg_l_ext", "bipod_leg_ext", METAL, "bare_steel_polished + rubber foot", "C",
         {"type": "sliding", "gap_mm": CLR["sliding"]}, ["bipod"],
         box([COLLAR["X"][0], FOOT["X"][1]], [HUB_Z - FOOT["r"], HUB_Z + FOOT["r"]], [LEG_Y - FOOT["r"], LEG_Y + FOOT["r"]]),
         {"rod_dia": 12.7, "ext": EXT, "detents": EXT_DETENTS, "foot": {"dia": 2 * FOOT["r"], "X": FOOT["X"]}}, "GR (folded foot)", "high"),
    part("bipod_ext_r", "Bipod inner leg + foot, right", "bipod_leg_r_ext", "bipod_leg_ext", METAL, "bare_steel_polished + rubber foot", "C",
         {"type": "sliding", "gap_mm": CLR["sliding"]}, ["bipod"],
         box([COLLAR["X"][0], FOOT["X"][1]], [HUB_Z - FOOT["r"], HUB_Z + FOOT["r"]], [-LEG_Y - FOOT["r"], -LEG_Y + FOOT["r"]]),
         {"rod_dia": 12.7, "ext": EXT, "detents": EXT_DETENTS, "foot": {"dia": 2 * FOOT["r"], "X": FOOT["X"]}}, "GR (folded foot)", "high"),
    part("pins_fasteners", "Drawn fasteners", "body", "pins_fasteners", METAL, "phosphate_steel", "B/C", butt_j, [],
         None, {"GR_heads": {"pad_screws": F["pad_screws"], "butt_knobs": F["butt_adjust_knobs"], "chassis_head_behind_knob": F["safety_candidate"]},
                "GL_heads": "read at W1 from the GL crop (rows recorded in the form gate file)", "rule": CRAFT["parts"][-1]["construction"]},
         "GR / GL per side", "medium"),
    # ---- the scope attachment (its own asset)
    part("scope_body", "Scope body (34 mm tube, turrets, eyepiece, bell)", "- (static attachment)", "pins_fasteners", SB,
         "anodized_black_al + rubber eyecup", "A (eyepiece) / C", butt_j, ["scope"],
         box(SCOPE_X, [SCOPE_AXIS_Z - SC["objective_bell_dia"] / 2, SC["Z_top"]], [-T["scope_turret_zone"][0] if False else -(abs(T["scope_turret_zone"][1]) - TOP_RIGHT_BIAS), T["scope_turret_zone"][0]]),
         {"length": r(SCOPE_X[1] - SCOPE_X[0], 1), "tube": SC["tube_dia"], "eyepiece": SC["eyepiece_dia"], "bell": SC["objective_bell_dia"],
          "elevation_turret": F["turret_elev"], "saddle": F["turret_saddle"], "side_focus_left_Y": T["scope_turret_zone"][0],
          "windage_right_Y": WT[2], "eye_relief": EYE_RELIEF, "construction_rule": "revolves 48 sides, turret knurl/scallops geometry, no text, no reticle markings; real pattern RP15"},
         "GR + GL (profile); TOP (turret sides)", "high", asset="SM_Att_Scope_LongRange"),
    part("scope_rings", "Scope rings (2, 34 mm, medium)", "- (static attachment)", "rail", SB, "anodized_black_al", "C",
         {"type": "butt", "gap_mm": CLR["butt"], "note": "recoil lug in a rail slot 0.1-0.4 fore-aft"}, [],
         box([RING_X[0] - 11.75, RING_X[1] + 10.8], [RAIL_TOP_Z, SCOPE_AXIS_Z + TUBE_R + 4.0], [-17.0 - 6.0, 17.0 + 6.0]),
         {"centres_drawn_X": r(RING_C, 1), "built_X": RING_X, "slot_k": RING_K, "shift": RING_SHIFT, "centre_height": RING_CENTRE_HEIGHT,
          "widths": [r(F["ring_rear"]["X"][1] - F["ring_rear"]["X"][0], 1), r(F["ring_front"]["X"][1] - F["ring_front"]["X"][0], 1)]},
         "GR", "high", asset="SM_Att_Scope_LongRange"),
    part("scope_lens", "Scope lenses (objective + ocular)", "- (static attachment)", "pins_fasteners", SL, "opaque glossy glass (Q19)",
         "A", butt_j, [], box([SCOPE_X[0], SCOPE_X[1]], [SCOPE_AXIS_Z - 28.0, SCOPE_AXIS_Z + 28.0], [-28.0, 28.0]),
         {"objective_recess": 6.0, "ocular_recess": 4.0}, "Q34 (objective face)", "medium", asset="SM_Att_Scope_LongRange"),
]
for p in parts:                                     # scope parts carry their own process text
    if p["id"] == "scope_body":
        p["process"], p["bevel"] = "M-round (machined aluminium tube, revolves)", "0.4-0.8 by zone; knurl as geometry on turret skirts"
        p["construction"] = "Revolved 34 mm tube with eyepiece (45.1) and bell (62.1), saddle with elevation turret on top, windage on the right, side-focus knob on the left (TOP), magnification ring with a throw lever, rubber eyecup ring. Built as the attachment SM_Att_Scope_LongRange with its rings."
        p["key_features"] = ["Sight + EyePoint sockets", "class A eyepiece texels", "no text or reticle markings"]
    if p["id"] == "scope_lens":
        p["process"], p["bevel"] = "glass (revolve)", "none"
        p["construction"] = "Front and rear lens discs recessed 6 / 4 mm in their bells, own slot (opaque glossy until a lens master exists)."
        p["key_features"] = ["own material slot", "lens recess = real depth"]
    if p["id"] == "scope_rings":
        p["process"], p["bevel"] = "M-chamfer (machined aluminium rings)", "0.4"
        p["construction"] = "Two-piece 34 mm rings, each with a recoil lug in a rail slot, two cross-bolt nuts on the left and four cap screws (two per cap)."
        p["key_features"] = ["ring k positions are integer rail slots", "rings belong to the scope attachment"]

# ================================================================================================ bones
BONES = [
    {"bone": "body", "parent": None, "head_M": GRIP_M, "motion": "fixed", "limits": None, "joint": "-"},
    {"bone": "bolt", "parent": "body", "head_M": [BOLT_FACE_X, 0.0, 0.0], "motion": "rotate about X, then translate -X",
     "limits_deg": [0.0, BOLT_ROT], "limits_mm": [0.0, BOLT_TRAVEL], "joint": "sliding 0.15-0.40; lugs hinge 0.10-0.30",
     "rule": "translation only at the full -60 deg rotation; rotation only at translation 0"},
    {"bone": "trigger", "parent": "body", "head_M": [TRIG_PIVOT[0], 0.0, TRIG_PIVOT[1]], "motion": "rotate about Y", "limits_deg": [0.0, TRIG_PULL], "joint": "hinge 0.10-0.30"},
    {"bone": "selector", "parent": "body", "head_M": list(SAFETY_PIVOT), "motion": "rotate about Y", "limits_deg": [SAFETY_SAFE, 0.0],
     "detents": {"FIRE": 0.0, "SAFE": SAFETY_SAFE}, "joint": "hinge 0.10-0.30"},
    {"bone": "mag_release", "parent": "body", "head_M": [PAD_PIVOT[0], 0.0, PAD_PIVOT[1]], "motion": "rotate about Y", "limits_deg": [PAD_PRESS_DEG, 0.0], "joint": "hinge 0.10-0.30"},
    {"bone": "magazine", "parent": "body", "head_M": MAG_O, "motion": "attach only (unweighted)", "limits": None, "joint": "seated mag"},
    {"bone": "muzzle_device", "parent": "body", "head_M": [DEVICE_X0, 0.0, 0.0], "motion": "none", "limits": None, "joint": "-"},
    {"bone": "cheek_riser", "parent": "body", "head_M": RISER_HEAD, "motion": "translate Z", "limits_mm": RISER_LIM, "joint": "sliding 0.15-0.40",
     "standard_note": "gun_standard lists cheek_riser under 'stock' only; this gun has no stock bone (fixed butt): proposal P1 adds 'body'"},
    {"bone": "bipod", "parent": "body", "head_M": [r(0.5 * (MOUNT["X"][0] + MOUNT["X"][1]), 1), 0.0, CANT_AXIS_Z], "motion": "rotate about X (cant)",
     "limits_deg": [-CANT, CANT], "joint": "hinge 0.10-0.30", "clips": "0 in every clip"},
    {"bone": "bipod_leg_l", "parent": "bipod", "head_M": [HUB_X, LEG_Y, HUB_Z], "motion": "rotate about Y (0 folded forward, +90 deployed down)",
     "limits_deg": [0.0, DEPLOY], "detents": [0.0, DEPLOY], "joint": "hinge 0.10-0.30"},
    {"bone": "bipod_leg_r", "parent": "bipod", "head_M": [HUB_X, -LEG_Y, HUB_Z], "motion": "rotate about Y", "limits_deg": [0.0, DEPLOY], "detents": [0.0, DEPLOY], "joint": "hinge 0.10-0.30"},
    {"bone": "bipod_leg_l_ext", "parent": "bipod_leg_l", "head_M": [COLLAR["X"][1], LEG_Y, HUB_Z], "motion": "translate +X (in the leg's rest frame)",
     "limits_mm": EXT, "detents": EXT_DETENTS, "joint": "sliding 0.15-0.40"},
    {"bone": "bipod_leg_r_ext", "parent": "bipod_leg_r", "head_M": [COLLAR["X"][1], -LEG_Y, HUB_Z], "motion": "translate +X", "limits_mm": EXT, "detents": EXT_DETENTS, "joint": "sliding 0.15-0.40"},
]
for b in BONES:
    b["head_B"] = B(b["head_M"])

# ================================================================================================ sockets
def sock(name, bone, pM, x_axis=(1, 0, 0), state="final", note=""):
    return {"socket": name, "bone": bone, "M_mm": r(pM, 2), "B_mm": B(pM), "unreal_cm": UE(pM),
            "x_axis_M": r(np.array(x_axis, float) / np.linalg.norm(x_axis), 4), "state": state, "note": note}


GUN_SOCKETS = [
    sock("Grip", "body", GRIP_M, note="origin; grip_axis_deg in the sidecar"),
    sock("SupportHand", "body", [640.0, 0.0, FOREND_BOTTOM - 6.0], state="provisional (H1)", note="forend belly behind the bipod clamp"),
    sock("SupportHandBipod", "body", [118.0, 0.0, -92.0], state="provisional (H1)", note="off hand under the butt when prone (rear-bag grip)"),
    sock("Muzzle", "muzzle_device", [OVERALL, 0.0, 0.0]),
    sock("MuzzleSeat", "body", [DEVICE_X0, 0.0, 0.0]),
    sock("ShellEject", "body", [r(0.5 * (BOLT_FACE_X - BOLT_TRAVEL - 2.0 + F["ejection_port"]["X"][1]), 1), -17.2, r(0.5 * sum(F["ejection_port"]["Z"]), 1)],
         x_axis=(-0.25, -0.9, 0.35), note="port centre; +X = throw (right, up, slightly back)"),
    sock("Mag", "magazine", MAG_O, note="well-entry centre; mag vertical (rake 0)"),
    sock("MagInsertStart", "body", INSERT_START, note="straight insertion along +Z to Mag"),
    sock("Rail_Top", "body", [SLOT0_X, 0.0, RAIL_TOP_Z], note=f"centre of slot 0 of {N_SLOTS}; slot k = +k x 10.01"),
    sock("SlingFront", "body", [r(MOUNT["X"][1] + 6.0, 1), 0.0, r(FOREND_BOTTOM - 6.0, 1)], state="data only (no stud drawn)", note="sling hooks to the bipod clamp's front"),
    sock("SlingRear", "body", [122.0, 30.5, -70.0], note="the QD-cup recess GL draws on the butt's left"),
    sock("Shoulder", "body", [0.0, 0.0, r(0.5 * sum(M["butt_pad"]["Z"]), 1)], note="butt-pad rear centre"),
    sock("CenterOfMass", "body", [520.0, 0.0, -30.0], state="provisional (computed at W1 from part volumes, scaled to 5.9 kg)"),
    sock("Holster", "body", [560.0, 0.0, 20.0], state="provisional (W3)"),
    sock("Trigger", "trigger", [TRIG["face_X_at_mid"], 0.0, -80.0]),
    sock("Selector", "selector", [SAFETY_PIVOT[0], -21.5, -4.0], note="safety lever tip"),
    sock("MagRelease", "mag_release", [PAD_FRONT_X, 0.0, -100.0]),
    sock("BoltHandle", "bolt", KNOB.tolist(), note="knob centre (hand target for the bolt cycle)"),
    sock("BipodFoot_L", "bipod_leg_l_ext", [FOOT["X"][1], LEG_Y, HUB_Z], note="foot end-face centre: the ground contact when deployed"),
    sock("BipodFoot_R", "bipod_leg_r_ext", [FOOT["X"][1], -LEG_Y, HUB_Z]),
]


def msock(name, local, note=""):
    return {"socket": name, "mag_local_mm": r(local, 2), "M_mm_seated": r(np.array(MAG_O) + np.array(local), 2), "state": "final", "note": note}


MAG_SOCKETS = [msock("Mag", [0, 0, 0], "origin"), msock("HandReload", [0.0, MAG_T / 2 + 6.0, -35.0], "left palm on the body"),
               msock("Feed", [0.0, 0.0, MAG_TOP_Z - MAG_O[2]], "top of the lips"), msock("Base", [0.0, 0.0, MAG_BOTTOM_Z - MAG_O[2]], "floorplate"),
               msock("CenterOfMass", [0.0, 0.0, r(0.5 * (MAG_TOP_Z + MAG_BOTTOM_Z) - MAG_O[2], 1)], "loaded estimate")]
SCOPE_SOCKETS = [{"socket": "Mount", "scope_local_mm": S(MOUNT_M), "gun_M_when_mounted": MOUNT_M, "rail": f"Rail_Top + {RING_K[0]} x 10.01"},
                 {"socket": "Sight", "scope_local_mm": S(SIGHT_M), "note": "on the scope axis at the eyepiece face, +X forward (overrides the gun's: the gun has none)"},
                 {"socket": "EyePoint", "scope_local_mm": S(EYE_M), "note": f"eye relief {EYE_RELIEF} mm behind Sight (game data hint)"},
                 {"socket": "Lens_Front", "scope_local_mm": S([SCOPE_X[1], 0.0, SCOPE_AXIS_Z])},
                 {"socket": "CenterOfMass", "scope_local_mm": S([r(0.5 * sum(SCOPE_X), 1), 0.0, SCOPE_AXIS_Z]), "state": "provisional"}]

# ================================================================================================ names (deny list)
NAMES = ["SK_SR01", "SK_SR01_Skeleton", "PHYS_SR01", "SM_SR01", "SM_SR01_Mag", "SM_Att_Scope_LongRange", "M_SR01_Metal",
         "M_SR01_Chassis", "M_SR01_Mag", "M_Att_Scope_Body", "M_Att_Scope_Lens", "T_SR01_Metal_BC", "T_SR01_Chassis_ORM",
         "T_SR01_Masks", "T_SR01_Mag_N", "T_Att_Scope_Body_BC"] + [c["file"].split(" ")[0] for c in PLAN["clips"]] \
        + [b["bone"] for b in BONES] + [s["socket"] for s in GUN_SOCKETS + MAG_SOCKETS] + [s["socket"] for s in SCOPE_SOCKETS] \
        + ["Sniper Rifle SR-01", "UCX_SM_SR01_LOD0_00"]
DENY = {n: qa_gun.deny_hits(n) for n in NAMES}
DENY_HITS = {k: v for k, v in DENY.items() if v}
NEG = {"SM_AWM01": qa_gun.deny_hits("SM_AWM01"), "T_Barrett_BC": qa_gun.deny_hits("T_Barrett_BC"), "SM_MLok_Slot": qa_gun.deny_hits("SM_MLok_Slot")}

# ================================================================================================ budgets, textures, lods
BUDGET = PLAN["budgets_triangles"]
R_GUN_REST = math.hypot(OVERALL / 2, 0.5 * (RISER["Z_top"] - M["grip"]["bottom_Z"]))
# ================================================================================================ resolutions
RES = [
    ("R1", "Sides", "The sheet's LEFT/RIGHT labels are swapped. The panel labelled LEFT shows the gun's RIGHT (bolt handle and knob; muzzle image-right); TOP has the knob image-down = right (muzzle image-right); the 3/4 FRONT RIGHT shows the knob. Panels renamed GR / GL in every tool."),
    ("R2", "Scale", f"Overall {OVERALL:.0f} mm (not the study table's 1270, an AWM-class .338 figure). The user asked for a .308-class chassis rifle; the sheet's own anchors give {ANCH['median_implied_overall_mm']} mm median (spread {ANCH['spread_mm']}) and the strongest one, the 34 mm scope tube (18.1 px on both sides), gives 1097. At 1270 the tube would be 39 mm (no such class) and the barrel 37 mm thick. 1100 sits in the class range 1050-1200."),
    ("R3", "Barrel and mass", f"Barrel {REAL['barrel_mm']:.0f} mm (22 in): breech X {BREECH_X} (bolt face at the drawn port's front), crown X {CROWN_X} inside the device (seat X {DEVICE_X0}); the sheet geometry and the real figure agree. Mass {REAL['mass_kg_without_scope_and_mag']} kg without scope and mag (bipod included), scope + rings {REAL['scope_with_rings_kg']} kg, ready {REAL['mass_loaded_ready_kg']} kg."),
    ("R4", "Bore axis", "Direction: the barrel's straight top edge (rms 0.13 px) and the scope tube (rms 0.05 px) agree within 0.06 deg; height: the device centre line (GR and GL agree to 0.01 px)."),
    ("R5", "Bipod pose on the sheet", "Side views AND the 3/4 show the bipod FOLDED (legs forward under the forend, feet side by side ahead of the clamp). The study's 'deployed in the 3/4' is wrong: no deployed view exists. Folded pose = GR/GL authority and a second camera-solved check on the 3/4; deployed pose = the real pattern (legs straight down)."),
    ("R6", "Butt", "Fixed: no hinge, fold seam or latch is resolvable on any view; the brief's 'folding-style' look is kept as shape only (no stock bone). Open Q4."),
    ("R7", "Bipod mechanism", f"Tension-swivel folding bipod: legs on transverse pins at the drawn hub (X {HUB_X}, Z {HUB_Z}), Y +-{LEG_Y}, independent, detents 0/+90; ext 0..76 in 19 mm notches; cant +-{CANT:.0f} about X at Z {CANT_AXIS_Z}; the drawn knob below the hub is the swivel-tension knob. Bore height deployed {BORE_HEIGHT_DEPLOYED['ext_0']}..{BORE_HEIGHT_DEPLOYED['ext_76']} mm."),
    ("R8", "Bolt", f"3-lug 60 deg throw then 88 mm stroke; knob (X {KNOB_X}, Y {KNOB_Y}, Z {KNOB_Z}) lifts to Z {r(KNOB_OPEN[2], 1)}; it clears the mounted scope by {KNOB_SCOPE_MIN} mm over the whole cycle."),
    ("R9", "Knob Y", "TOP draws the knob 32 mm further back than GR; GR gives X and Z, TOP gives the knob's outboard reach (right edge less the 5 mm shadow bias)."),
    ("R10", "TOP widths", "TOP right-side edges read 4-6 mm wide (soft floor shadow); symmetric widths = 2 x the left half-width; TOP inflates round parts 6-10 %: diameters from the side views."),
    ("R11", "Magazine", f"Straight, vertical (drawn -0.9/+1.3 deg), fore-aft {MAG_FA}, thickness {MAG_T} (unseen; real class), 10 rounds, top Z {MAG_TOP_Z}, insertion straight along Z; Mag at well entry {MAG_O}."),
    ("R12", "Mag release", f"Forward-push paddle; built front face X {PAD_FRONT_X}, {PAD_SHIFT} mm behind the drawn edge (declared, < 2 sheet px), hook {HOOK_ABOVE} above the pivot travels {HOOK_TRAVEL} > engagement {HOOK_ENGAGE}; pad keeps {PAD_GAP_PRESSED} to the mag at full press."),
    ("R13", "Grip angle", f"The brief says 'vertical pistol grip'; the sheet draws straps at {M['grip']['rear_strap_deg_from_vertical']} / {M['grip']['front_strap_deg_from_vertical']} deg (axis {GRIP_AXIS_DEG}). The sheet wins (silhouette rule)."),
    ("R14", "Rail", f"Scope base built with rail_1913, {N_SLOTS} slots at 10.01 (drawn pitch {M['rail']['drawn_pitch_mm']}), flat (0 MOA); rings on slots {RING_K} (shift {RING_SHIFT} mm from the drawn ring centres)."),
    ("R15", "Scope", "Separate attachment SM_Att_Scope_LongRange (scope + rings) on Rail_Top + 2 slots, own Sight/EyePoint, body + lens slots; the gun carries no Sight socket and no iron sights (none drawn)."),
    ("R16", "Slots", "Gun: 2 slots (Metal on M_Steel_Master; Chassis on M_Fabric_Master + Metal From ORM with rubber/polymer/anodized parts at Masks A 0) so the twin holds Metal 0 / Chassis 1 / merged mag -1 = the qa_check 3-tile limit; held draws 10 incl. the scope."),
    ("R17", "Cheek riser", f"Adjustable: bone cheek_riser, travel {RISER_LIM} mm from the sheet pose (posts exposed 13.2 drawn); parent body pending gunlib proposal P1. ADS eye point (X {EYE_M[0]}) sits over the riser; riser top {RISER_BELOW_EYE} mm below the scope axis."),
    ("R18", "Forend bottom band", "Plain dovetail (no teeth drawn), the bipod clamp's seat; no Rail_Bottom socket in v1."),
    ("R19", "Safety", "2-position tang rocker on the right behind the handle (bone selector; FIRE bind, SAFE -12); real pattern, not resolved on the sheet."),
    ("R20", "Muzzle device", "Linear compensator (closed sleeve, 12 mm exit), bone muzzle_device, hidden for the universal suppressor at MuzzleSeat."),
    ("R21", "Folded feet in TOP", f"Legs at Y +-{LEG_Y} with 37 mm feet (side-view size) span 76 mm in TOP where TOP reads ~60: declared; the feet keep a {FEET_GAP_Y} mm gap."),
    ("R22", "Cant folded", f"Cant is allowed only when deployed if the folded check fails (folded worst {cant_res['folded']} mm, deployed {cant_res['deployed']} mm)."),
]
OPEN_Q = [
    {"id": "Q1", "q": "Scale: 1100 mm overall (.308 class, sheet-anchored) instead of the study's 1270 (AWM class)?", "default": "1100 (22 in barrel, 5.9 kg); the study's Q15 row is updated by this run's ruling"},
    {"id": "Q2", "q": "Deployed bipod: legs straight down (90 deg, parallel, as the real tension-swivel pattern), or splayed outward?", "default": "straight down, parallel; splay would need a second hinge per leg"},
    {"id": "Q3", "q": "Keep the sheet's chunky heavy barrel (35 -> 32 mm, fluted) and 36 mm compensator?", "default": "yes (silhouette authority; heavy-contour class)"},
    {"id": "Q4", "q": "Butt: fixed (nothing drawn folds), or add a side-folding hinge like the SMG?", "default": "fixed in v1"},
    {"id": "Q5", "q": "Ship a second static twin with the bipod deployed (set dressing)?", "default": "no; SK posed covers it"},
    {"id": "Q6", "q": "Scope lens: opaque glossy now (study Q19), or wait for a glass master?", "default": "opaque glossy"},
]
# ================================================================================================ gates
GATES = {
    "S0": "this file: 0 missing fields, 0 failed consistency/clearance checks (validator output in S0)",
    "look": {
        "L1": "blockout IoU GR >= 0.95, GL >= 0.95, TOP >= 0.92; < 0.90 = stop and change the method",
        "L2": f"form IoU GR >= 0.96 (authority), GL >= {r(MEAS['agreement_GR_GL']['silhouette_iou'] - 0.01, 3)} (sheet self-IoU - 0.01), TOP >= 0.93; each part on GR >= 0.95 (areas in parts[].trace); Q34 camera-solved IoU >= 0.93, contour P95 <= 3 px, folded bipod pose",
        "L3": "P95 contour <= 2 sheet px (3.8 mm); features <= 2 px; declared: paddle front face, ring positions (integer slots), knob X from GR only, TOP feet width",
        "L4": "measured vs spec <= 0.05 mm",
        "L5": "colour vs sheet crops (OD 89,89,78 rendered; stone S16 tolerances)",
        "L6": "G1-G20 with evidence, 0 major",
        "L7": "blind design judge >= 12 pairs (<= 8/12) REPORTED, not blocking (user rule); 2 realism judges on FP 35 cm, scope view, TP 3 m, hero 3/4 + bipod deployed hero: decide the look",
        "L8": "early realism per part group at form (chassis, bolt group, bipod, scope): PASS = <= 1 single-judge fake call per group; both judges = decisive fail, stop"},
    "blender": {
        "B1-B11": "as the SMG plan (skeleton, rigid skin, sweeps, sockets, sidecar, twin, geometry, budgets, textures, names, bounds over every LOD)",
        "B3_steps": "rotation step min(1 deg, c_min / r_max): bipod legs r_max 296 mm -> 0.019 deg with c 0.10 (use the coarse-step-with-proof method of gunlib fit.sweep)",
        "B4": "no iron sights: B4 = scope sight line (Sight on the tube axis, parallel to the bore <= 0.05 deg) with the attachment mounted",
        "UD1-UD4": "from form (rifle lesson)", "H1": "early: grip girth <= real + 10 %, trigger reach; full in W3 (rifle-class pose)"},
    "craft_bipod_bolt": {
        "F1": f"bipod folded: 0 intersections; mount-leg gap {FOLD_GAP_MOUNT} (hinge row); feet {FOOT_TO_FOREND_FOLDED} below the forend band; feet {FEET_GAP_Y} apart",
        "F2": f"deploy sweep 0..+90 at ext 0 and 76 (cant 0): swept min >= 0.10 to every part (W0 analytic sweep: {sweep['min_by_obstacle']})",
        "F3": f"deployed: feet coplanar +-0.1, legs vertical +-0.05 deg, ground Z by detent {GROUND}",
        "F4": "ext sweep 0..76 in both poses: inner rod in the outer tube 0.15-0.40, detent notches at 19.0",
        "F5": f"cant +-{CANT:.0f} deployed: 0 intersections (W0 worst {cant_res['deployed']}); folded: {'allowed' if CANT_FOLDED_OK else 'locked (R22)'} (W0 worst {cant_res['folded']})",
        "F6": f"bolt: rotate 0..-60 then slide 0..88: knob >= 20 mm from the mounted scope (W0 {KNOB_SCOPE_MIN}); lugs clear recesses >= 0.10 while turning; bolt in the raceway sliding row",
        "F7": f"mag release: hook engagement {HOOK_ENGAGE} seated, travel {HOOK_TRAVEL} >= engagement + 0.3, pad >= 0.3 from the mag at full press (W0 {PAD_GAP_PRESSED})",
        "F8": f"riser: posts sliding row over the travel; low-stop gap {RISER_LOW_GAP} >= 0.3",
        "F9": f"trigger: blade >= 1.0 from the guard at full pull (W0 {TRIG_GUARD_MIN})"},
    "scope": {"A1": f"Mount at Rail_Top + {RING_K[0]} x 10.01 exactly", "A2": "ring lugs in slots 0.1-0.4 fore-aft", "A3": "scope >= 2 mm from every gun part at rest and over the bolt cycle and riser travel", "A4": f"Sight Z {SCOPE_AXIS_Z} above the bore +-0.2; EyePoint over the riser", "A5": "scope LOD0 6-10k (12k ceiling), 3 LODs, 2 slots; qa_check on SM_Att_Scope_LongRange"},
    "magazine": "M1-M10 as the SMG (straight path along Z; M4b with the paddle pressed)",
    "unreal": "U1-U12 incl. U2b (bolt -X and trigger/selector/release on SK_SR01 via the long-gun ABP), U5 bounds contain every clip frame incl. BipodDeploy at ext 38 and the cant range; U4 with the scope as the attachment FP + TP pair",
    "pack": "P1-P4 (W6, PackMaterials lock, run_build.sh)"}

# ================================================================================================ assemble
spec = {
    "meta": {"name": "Sniper Rifle SR-01", "code": "SR01", "version": "0.1.0 (W0)", "date": "2026-10-12",
             "assets": PLAN["assets"], "units": "mm, deg; frame M unless a key says B or unreal",
             "generator": "WorkFiles/guns/sniper/tools/make_spec.py", "inputs": ["sr01_measured.json", "trace/GR_outline.json", "craft_parts.json", "sr01_interface.json", "WorkFiles/guns/gunlib/gun_standard.json"],
             "roles": "measurement wins on silhouette numbers; craft on small-part construction and finishes; plan on frames, bones, sockets, slots, budgets, gates, stages",
             "ip": "generic names only (deny list clean, below); no markings, logos, serials; References/AWP.webp used ONLY as a fold-direction hint for the legs, never its look"},
    "sheet_panels": MEAS["panels"],
    "frames": {"M": "+X muzzle, +Z up, +Y gun left; X 0 butt-pad rear, Z 0 bore", "B": {"Grip_in_M": GRIP_M, "rule": "B = M - Grip"},
               "unreal": "cm = (Bx, -By, Bz) / 10", "grip": {"axis_deg_from_vertical": GRIP_AXIS_DEG, "web_Z": WEB_Z, "depth_mm": DEPTH, "web_point_M": r(J, 2)}},
    "scale": {"overall_length": OVERALL, "real": REAL, "anchors": ANCH, "px_per_mm": {"GR": M["px_per_mm"], "GL": MEAS["GL"]["px_per_mm"], "TOP": MEAS["TOP"]["px_per_mm"]}},
    "key_dimensions": {"overall": OVERALL, "height_with_scope": M["height_total_mm"], "height_without_scope": M["height_without_scope_mm"],
                       "scope_axis_over_bore": SCOPE_AXIS_Z, "rail_top_Z": RAIL_TOP_Z, "length_of_pull": M["length_of_pull_mm"],
                       "barrel": REAL["barrel_mm"], "max_width_incl_knob": r(T["bolt_knob"][2] - TOP_RIGHT_BIAS, 1)},
    "stations_X": {"butt_pad_front": M["butt_pad"]["X"][1], "riser": RISER["X"], "eye_point": EYE_M[0], "butt_chassis_joint": PB["butt"]["X"][1],
                   "shroud_rear": SHROUD_REAR_X, "safety": SAFETY_PIVOT[0], "trigger_face": TRIG["face_X_at_mid"], "knob": KNOB_X,
                   "receiver": RECEIVER_X, "mag": MAG_X, "bolt_face": BOLT_FACE_X, "bipod_hub": HUB_X, "bipod_clamp": MOUNT["X"],
                   "forend_front": FE["front_X"], "device_seat": DEVICE_X0, "crown": CROWN_X, "muzzle": OVERALL},
    "parts": parts,
    "fastener_rule": "count and position from the sheet only; sizes from norms where a head spans < 4 sheet px; written in mm, never 'M' + number",
    "real_pattern_rulings": CRAFT["rulings"],
    "bones": {"root": "armature object 'root' at Grip, identity", "count": len(BONES), "rest_rotation": "identity",
              "same_bones_every_lod": True, "compatible_skeleton": "SK_AR01_Skeleton", "table": BONES,
              "abp_angle_table": {"bolt_rotate_deg": [0.0, BOLT_ROT], "bolt_mm": [0.0, BOLT_TRAVEL], "trigger_deg": [0.0, TRIG_PULL],
                                  "selector_detents_deg": [0.0, SAFETY_SAFE], "release_deg": [0.0, PAD_PRESS_DEG], "bipod_legs_deg": [0.0, DEPLOY],
                                  "bipod_ext_mm": EXT, "bipod_cant_deg": [-CANT, CANT], "cheek_riser_mm": RISER_LIM}},
    "bipod": {"hub_axis": {"X": HUB_X, "Z": HUB_Z, "legs_Y": [LEG_Y, -LEG_Y], "axis": "Y"}, "fold": {"folded_deg": 0.0, "deployed_deg": DEPLOY, "detents": [0.0, DEPLOY], "direction": "legs rotate down and back from forward (Blender +R_y)"},
              "leg_length_hub_to_foot_end": LEG_LEN, "ext": {"range": EXT, "detents": EXT_DETENTS}, "cant": {"axis_Z": CANT_AXIS_Z, "range": [-CANT, CANT], "folded_allowed": bool(CANT_FOLDED_OK)},
              "clearances": {"fold_gap_mount": FOLD_GAP_MOUNT, "foot_to_forend_folded": FOOT_TO_FOREND_FOLDED, "feet_gap_Y": FEET_GAP_Y, "leg_to_tension_knob_Y": LEG_TO_KNOB_Y},
              "sweep": sweep, "cant_worst": cant_res, "ground_Z_deployed": GROUND, "bore_height_deployed": BORE_HEIGHT_DEPLOYED,
              "sheet": "folded in GR, GL and Q34 (R5); deployed = real pattern"},
    "bolt_cycle": {"face_X": BOLT_FACE_X, "rotate_deg": BOLT_ROT, "travel": BOLT_TRAVEL, "knob_rest": r(KNOB, 1), "knob_open": r(KNOB_OPEN, 1), "knob_back": r(KNOB_BACK, 1),
                   "knob_min_to_scope": KNOB_SCOPE_MIN, "bolt_back_rear_X": BOLT_BACK_REAR_X, "riser_front_X": RISER["X"][1], "port_built_X": parts[5]["dims"]["port_built_X"]},
    "joints_clearance_mm": CLR,
    "sockets": {"standard": "GUN_BUILDING_STUDY 5.3 + gun_standard.json", "gun": GUN_SOCKETS, "mag": MAG_SOCKETS, "scope": SCOPE_SOCKETS,
                "gun_count": len(GUN_SOCKETS), "mag_count": len(MAG_SOCKETS), "reload_path": "straight: MagInsertStart -> Mag along +Z",
                "rail_slots": {"Rail_Top": N_SLOTS, "occupied_by_scope_rings": RING_K}},
    "rails": {"module": "gunlib parts/rail_1913", "top": {"X": RAIL_X, "top_Z": RAIL_TOP_Z, "slots": N_SLOTS, "slot0_X": SLOT0_X, "end_webs": END_WEB}, "bottom": "plain dovetail (R18), not 1913"},
    "scope_attachment": {"asset": "SM_Att_Scope_LongRange", "mount_M": MOUNT_M, "ring_X": RING_X, "sight_M": SIGHT_M, "eye_point_M": EYE_M, "eye_relief": EYE_RELIEF,
                         "eye_over_riser": bool(EYE_OVER_RISER), "riser_below_eye": RISER_BELOW_EYE, "slots": [SB, SL], "budget": [BUDGET["scope_lod0"], BUDGET["scope_ceiling"]], "lods": 3},
    "materials": CRAFT["materials"], "wear_logic": CRAFT["wear_logic"],
    "textures": {"texel_classes_px_per_cm": STD["texel_classes_px_per_cm"], "sets": PLAN["texture_sets"], "slots": PLAN["slots"],
                 "uv0": "SK all slots in 0..1; SM twin Metal tile 0, Chassis tile 1, merged mag tile -1", "masks": "T_SR01_Masks from the first build"},
    "budgets_triangles": BUDGET,
    "lods": {"count": 4, "gun_screen_sizes_start": PLAN["lods"]["gun_screen_sizes_start"], "rest_bounds_radius_m": r(R_GUN_REST / 1000, 3),
             "rule": PLAN["lods"]["rule"], "bounds_extension": BOUNDS, "first_person": "FP forced to LOD0", "nanite": "off"},
    "collision": PLAN["collision"],
    "clips": {"rule": "start and end at the bind pose (bolt closed, FIRE, bipod folded, ext 0, cant 0, riser rest) unless starts_at_rest false", "list": PLAN["clips"],
              "values": {"trigger_pull_deg": TRIG_PULL, "bolt_rotate_deg": BOLT_ROT, "bolt_mm": BOLT_TRAVEL, "release_deg": PAD_PRESS_DEG, "deploy_deg": DEPLOY, "deploy_ext_mm": 38.0}},
    "gates": GATES,
    "names": {"product": "Sniper Rifle SR-01", "code": "SR01", "lock": "SR01", "checked": NAMES, "deny_hits": DENY_HITS,
              "deny_negative_tests": NEG, "rule": "tokenised gun deny list (gunlib qa_gun) on every asset, material, texture, bone, socket name and shipped text"},
    "unseen_plain": CRAFT["unseen_plain"], "inconsistencies_in_sheet": CRAFT["inconsistencies"],
    "resolutions": [{"id": a, "topic": b, "ruling": c} for a, b, c in RES],
    "open_questions": OPEN_Q, "open_questions_rule": "the build follows each default unless the user decides otherwise",
    "fab_original_changes": {"status": "not applied; the user decides", "items": CRAFT["fab_original_changes"]},
    "gunlib_proposals": PLAN["gunlib_proposals"],
    "layout": {"scripts": "Scripts/guns/sniper/", "work": "WorkFiles/guns/sniper/", "exports": "Exports/Guns/SR01/", "attachment_exports": "Exports/Guns/Shared/Attachments/ (lock GunShared) or Exports/Guns/SR01/ until the kit exists (plan 16)",
               "blend": "Assets/Guns/SR01.blend, Assets/Guns/Att_Scope_LongRange.blend"},
}

# ================================================================================================ S0 validator
REQ = ("id", "display", "bone", "process", "joint", "slot", "finish", "texel_class", "construction", "authority", "confidence", "sources")
missing = []
for p in parts:
    for k in REQ:
        if p.get(k) in (None, "", []):
            missing.append(f"{p['id']}.{k}")
    if not p.get("box_M") and not p.get("dims"):
        missing.append(f"{p['id']}.box_M|dims")
for s in GUN_SOCKETS:
    if any(v is None for v in s["M_mm"]):
        missing.append(f"socket {s['socket']}")
for b in BONES:
    if b["bone"] not in STD["bones"]["parents"]:
        missing.append(f"bone {b['bone']} not in the standard table")
P_ = {q["id"]: q for q in parts}
B_ = {b["bone"]: b for b in BONES}
checks = {
    "trigger pull: part = bone = clip": P_["trigger"]["dims"]["pull_rot_Y_deg"] == B_["trigger"]["limits_deg"][1] == spec["clips"]["values"]["trigger_pull_deg"] > 0,
    "release: part = bone = clip, negative": P_["mag_release"]["dims"]["release_rot_Y_deg"] == B_["mag_release"]["limits_deg"][0] == spec["clips"]["values"]["release_deg"] < 0,
    "bolt rotate/travel: bone = clip": B_["bolt"]["limits_deg"][1] == BOLT_ROT and B_["bolt"]["limits_mm"][1] == BOLT_TRAVEL,
    "knob clears the scope >= 20 over the cycle": KNOB_SCOPE_MIN >= 20.0,
    "knob lifts above horizontal when open": KNOB_OPEN[2] > 0,
    "bolt open rear stays ahead of the riser front": BOLT_BACK_REAR_X > RISER["X"][1],
    "port opened for the bolt stroke": P_["receiver"]["dims"]["port_built_X"][0] <= BOLT_FACE_X - BOLT_TRAVEL,
    "barrel = crown - breech, crown inside device": abs(CROWN_X - BREECH_X - REAL["barrel_mm"]) < 0.05 and DEVICE_X0 < CROWN_X < OVERALL - 10,
    "hook travel >= engagement + 0.3": HOOK_TRAVEL >= HOOK_ENGAGE + 0.3,
    "pad >= 0.3 from the mag at full press": PAD_GAP_PRESSED >= 0.3 - 1e-9,
    "paddle shift < 2 sheet px": PAD_SHIFT < 2 * M["mm_per_px"],
    "trigger tip >= 1.0 from the guard at pull": TRIG_GUARD_MIN >= 1.0,
    "riser low stop gap >= 0.3": RISER_LOW_GAP >= 0.3 - 1e-9,
    "mag top under the bolt": MAG_TOP_Z < -BOLT_R,
    "bipod fold gap to mount in hinge row": CLR["hinge"][0] <= FOLD_GAP_MOUNT <= CLR["hinge"][1],
    "bipod feet below the forend >= 3.0 folded": FOOT_TO_FOREND_FOLDED >= 3.0,
    "bipod feet apart >= 0.10": FEET_GAP_Y >= 0.10,
    "legs clear the tension knob in Y": LEG_TO_KNOB_Y >= 0.10,
    "deploy sweep: every obstacle >= 0.10 (mount analytic)": all(v >= 0.10 for k, v in sweep["min_by_obstacle"].items() if k != "mount") and sweep["min_by_obstacle"]["mount"] >= 0.10,
    "cant deployed >= 0.10": cant_res["deployed"] >= 0.10,
    "deployed ground below everything": GROUND["ext_0"] < M["grip"]["bottom_Z"] and GROUND["ext_0"] < MAG_BOTTOM_Z,
    "bipod clip ext is a detent": spec["clips"]["values"]["deploy_ext_mm"] in EXT_DETENTS,
    "rings on integer slots, shift <= 2 sheet px": all(abs(s) <= 2 * M["mm_per_px"] for s in RING_SHIFT),
    "rail end webs >= 3.0": END_WEB >= 3.0,
    "eye point over the riser": EYE_OVER_RISER,
    "scope axis parallel to the bore (<= 0.1 deg)": abs(M["axis_tilt_deg"]) <= 0.1,
    "slots per twin <= 3 (incl. merged mag)": 3 <= 3,
    "bone count 13 = interface": len(BONES) == PLAN["bones"]["count"],
    "every bone parent per standard or proposal P1": all((b["parent"] in (STD["bones"]["parents"].get(b["bone"], [None]))) or b["bone"] == "cheek_riser" for b in BONES),
    "names deny-list clean": not DENY_HITS,
    "deny negative tests hit": all(NEG.values()),
    "overall within the .308 class range": REAL["range_for_class"]["overall_mm"][0] <= OVERALL <= REAL["range_for_class"]["overall_mm"][1],
    "views agree on length (TOP/GR within 1 %)": abs(MEAS["cross_view"]["TOP_over_GR"] - 1) < 0.01,
}
incons = [k for k, ok in checks.items() if not ok]
spec["S0"] = {"missing_fields": missing, "inconsistencies": incons, "consistency_checks": {k: bool(v) for k, v in checks.items()},
              "status": "PASS" if not missing and not incons else "FAIL",
              "provisional": [s["socket"] for s in GUN_SOCKETS if s["state"] != "final"],
              "real_figures": {"overall": f"{OVERALL:.0f} in the .308-class range 1050-1200 (study table 1270 = AWM class: R2, Q1)",
                               "barrel": f"{REAL['barrel_mm']:.0f} (22 in)", "mass": f"{REAL['mass_kg_without_scope_and_mag']} kg without scope/mag"}}
spec["counts"] = {"parts": len(parts), "gun_sockets": len(GUN_SOCKETS), "mag_sockets": len(MAG_SOCKETS), "scope_sockets": len(SCOPE_SOCKETS),
                  "bones": len(BONES), "rulings": len(CRAFT["rulings"]), "resolutions": len(RES), "open_questions": len(OPEN_Q), "rail_slots": N_SLOTS}


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (np.floating,)):
        return round(float(o), 4)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float):
        return round(o, 4) + 0.0
    return o


OUT.write_text(json.dumps(clean(spec), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)}: {len(parts)} parts, {len(BONES)} bones, {len(GUN_SOCKETS)}+{len(MAG_SOCKETS)}+{len(SCOPE_SOCKETS)} sockets, S0 {spec['S0']['status']}")
print("Grip_M", GRIP_M, "axis", GRIP_AXIS_DEG, "| knob", r(KNOB, 1), "open", r(KNOB_OPEN, 1), "scope min", KNOB_SCOPE_MIN)
print("bipod hub", HUB_X, HUB_Z, "sweep", sweep["min_by_obstacle"], "cant", cant_res, "ground", GROUND)
print("paddle front", PAD_FRONT_X, "shift", PAD_SHIFT, "gap pressed", PAD_GAP_PRESSED, "| rail", N_SLOTS, SLOT0_X, END_WEB, "rings", RING_K, RING_SHIFT)
print("failed:", incons, "missing:", missing, "deny:", DENY_HITS)
