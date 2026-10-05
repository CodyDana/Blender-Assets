"""Write WorkFiles/guns/rifle/rifle_spec.json: THE build spec for Assault Rifle AR-01 (SK_AR01 / SM_AR01 / SM_AR01_Mag).

    py -3 -B WorkFiles/guns/rifle/tools/make_spec.py

Merges the three study outputs into one consistent spec:
  rifle_measured.json + trace/*.json   (measurement role: dimensions, outlines)      -> wins on dimensions
  craft_parts.json / CRAFT_STUDY.md    (craft role: what each part is, how to build)  -> wins on construction
  rifle_interface.json / RIFLE_BUILD_PLAN.md (tech role: frames, sockets, budgets)   -> wins on frames / sockets / budgets
  GUN_BUILDING_STUDY.md (repo-root line standard, rev 2) overrides the tech plan where it decides (asset set, socket
  names, finishes and slots, budgets, layout), as its section 11 says.
Every conflict and its resolution is listed in spec["resolutions"]. Derived numbers (grip axis, Grip origin, sockets,
dust-cover crown, magazine floor plate, bounds) are computed here from the traced outlines, so they cannot drift from
the trace. Needs numpy only. ROOT comes from this file's location (works in a worktree and after the merge).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
RIFLE = HERE.parents[1]                      # WorkFiles/guns/rifle
ROOT = HERE.parents[4]                       # repo root
TRACE = RIFLE / "trace"
OUT = RIFLE / "rifle_spec.json"

MEAS = json.loads((RIFLE / "rifle_measured.json").read_text())
LEFT = json.loads((TRACE / "LEFT_outline.json").read_text())
TOP = json.loads((TRACE / "TOP_outline.json").read_text())
D = MEAS["dimensions"]
TV = MEAS["top_view"]


def r1(v, n=1):
    if isinstance(v, (list, tuple, np.ndarray)):
        return [r1(x, n) for x in v]
    return round(float(v), n)


# ------------------------------------------------------------------------------------------------ geometry helpers
def rings(key, part=None, outer_only=True):
    src = LEFT["parts"][part] if part else LEFT[key]
    return [np.array(r["mm"]) for r in src if (r["kind"] == "outer" or not outer_only)]


def main_ring(part):
    rr = [(abs(r["area_px"]), np.array(r["mm"])) for r in LEFT["parts"][part] if r["kind"] == "outer"]
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


SIL_NOMAG = rings("rifle_without_magazine")

# ---- dust cover crown (the measured 46.9 "top" came from a 20 px sliver ring at the rear-sight junction)
crown = np.array([cross_z(SIL_NOMAG, X)[-1] for X in np.arange(275, 446, 5)])
CROWN_Z = float(np.median(crown))
DC_REAR = [[float(X), float(cross_z(SIL_NOMAG, X)[-1])] for X in (241.5, 245, 250, 255, 260, 265, 270)]

# ---- pistol grip axis: midline of the traced grip between Z -64 and -116 (below the top flare, above the heel). With the
# grip's dark front strap now traced (check C2) the flare reaches Z ~-62; from -64 down the front and rear edges are
# parallel (22.45 / 22.26 deg), so the midline is not biased by the flare
grip = rings(None, "pistol_grip")
rows = []
for Z in np.arange(-64, -117, -2.0):
    x = cross_x(grip, Z)
    rows.append((Z, x[0], x[-1]))
R = np.array(rows)
k_axis, c_axis = np.polyfit(R[:, 0], (R[:, 1] + R[:, 2]) / 2, 1)          # X = k Z + c
GRIP_RAKE = math.degrees(math.atan(k_axis))
GRIP_TOP_Z = D["pistol_grip"]["Z"][1]                                    # receiver / grip junction (-35.9)
JUNCTION = np.array([k_axis * GRIP_TOP_Z + c_axis, GRIP_TOP_Z])
AXIS_DOWN = -np.array([k_axis, 1.0]) / math.hypot(k_axis, 1.0)          # unit, pointing down the grip toward the butt
# Grip depth down the axis from the junction. GUN_BUILDING_STUDY 5.1 set 40 mm provisionally for H1 to fix. Form fix
# round 1 (2026-10-04) sets it from the locked MH_PlayerDefault fit body's right hand (rifle_h1.py): in a power grasp
# the index->pinky knuckle line runs along the grip axis with the thumb-index web at the junction, so the on-axis
# point under the palm centre is the palm centre's projection on that line: 45.9 mm (the 55.2 mm web->palm-centre
# distance includes the palm's 30.7 mm offset behind the axis). The posed H1 at the rig stage records hand_offset.
GRIP_DEPTH = 46.0
G = JUNCTION + GRIP_DEPTH * AXIS_DOWN                                   # Grip origin in the M frame (X, Z)
GRIP_WIDTH_PERP = float(np.median((R[:, 2] - R[:, 1]) * math.cos(math.atan(k_axis))))

# ---- trigger face (finger contact = most rearward point of the forward-facing concave edge)
trig = rings(None, "trigger")
tf = min(((cross_x(trig, Z)[-1], Z) for Z in np.arange(-38, -52, -0.5)), key=lambda t: t[0])
TRIGGER_FACE = np.array(tf)

# ---- butt plate rear face (centre and tilt)
bp = rings(None, "butt_plate")
face = np.array([[cross_x(bp, Z)[0], Z] for Z in np.arange(-8, -100, -2.0)])
kf, cf = np.polyfit(face[:, 1], face[:, 0], 1)                           # X = kf Z + cf
BUTT_Z_C = (D["butt_plate"]["Z"][0] + D["butt_plate"]["Z"][1]) / 2
BUTT_C = np.array([cross_x(bp, BUTT_Z_C)[0], BUTT_Z_C])
BUTT_TILT = math.degrees(math.atan(-kf))                                 # + = toe forward of the heel

# ---- magazine: concentric arcs, floor plate corners from the trace
MAG = D["magazine"]
CF = MAG["concentric_fit"]
MC = np.array(CF["centre_XZ"])
R_IN, R_OUT = CF["R_front_concave"], CF["R_rear_convex"]
magring = np.array(LEFT["magazine"][0]["mm"])
d = magring - MC
rad = np.hypot(d[:, 0], d[:, 1])
ang = np.degrees(np.arctan2(d[:, 1], d[:, 0]))                          # ~ -170 at the top rear ... -130 at the floor
on_out = np.abs(rad - R_OUT) < 2.0
on_in = np.abs(rad - R_IN) < 2.0
A_TOP = float(np.degrees(np.arctan2(MAG["top_Z_receiver_cut"]["mm"] - MC[1], -math.sqrt(((R_IN + R_OUT) / 2) ** 2 - (MAG["top_Z_receiver_cut"]["mm"] - MC[1]) ** 2))))
A_BOT_OUT = float(ang[on_out].max())
A_BOT_IN = float(ang[on_in].max())


def x_on_arc(r, z):
    return MC[0] - math.sqrt(r ** 2 - (z - MC[1]) ** 2)


def arc_pt(r, a):
    return MC + r * np.array([math.cos(math.radians(a)), math.sin(math.radians(a))])


_xr, _xf = x_on_arc(R_OUT, -25.0), x_on_arc(R_IN, -25.0)
TOP_PLATE_X = [round(_xr + 0.08 * (_xf - _xr), 1), round(_xr + 0.80 * (_xf - _xr), 1)]
FLOOR_REAR = arc_pt(R_OUT, A_BOT_OUT)
FLOOR_FRONT = arc_pt(R_IN, A_BOT_IN)
R_MID = (R_IN + R_OUT) / 2
A_MID = (A_TOP + (A_BOT_OUT + A_BOT_IN) / 2) / 2
MAG_MID = arc_pt(R_MID, A_MID)
MAG_BASE = (FLOOR_REAR + FLOOR_FRONT) / 2
fp_dir = FLOOR_FRONT - FLOOR_REAR
FLOOR_NORMAL = np.array([fp_dir[1], -fp_dir[0]]) / np.hypot(*fp_dir)    # outward (down-forward)
if FLOOR_NORMAL[1] > 0:
    FLOOR_NORMAL = -FLOOR_NORMAL
# magazine thickness: NOT measurable on the sheet. The front close-up c5 reads ~18-20 (its width/height ratio x the
# side view's height), but the close-ups are not drawn to one scale: c7 shows wood on both sides of the butt plate
# where TOP shows the plate skirt flush with the stock, so the c7/TOP ratio (0.64) is a drawing inconsistency and
# does not carry over to c5 (check C5). 28.0 is the real-pattern double-stack norm (28-30); confirm it on the
# camera-solved 3/4 view (spine width against the 41.5 receiver) in the blockout stage before freezing.
# Form fix round 2 (R32): 26.0, the physical minimum closest to the sheet (the 3/4 panel prefers ~24, c5 reads 18-20).
MAG_T_C5 = MAG["thickness_from_front_closeup"]["mm"]
CASE_HEAD_D = 11.35                                   # cartridge case head diameter of the pattern (mm)
MAG_T_INSIDE_MIN = CASE_HEAD_D * (1 + math.sin(math.radians(60)))   # staggered double stack: 21.18 inside
MAG_T = 26.0

# ---- magazine pivot (front-lug hook) and reload path
REC_BOT = D["receiver"]["bottom_Z"]["mm"]                                # -28.8
HOOK_Z = -16.0                                                          # inside the well, under the carrier (fit stage sets it)
x_front_at_hook = MC[0] - math.sqrt(R_IN ** 2 - (HOOK_Z - MC[1]) ** 2)
HOOK = np.array([round(x_front_at_hook + 4.0, 1), HOOK_Z])              # lug tip 4 mm ahead of the front spine
ROCK = 18.0
INSERT_D = 8.0
rr = math.radians(ROCK)
INSERT = HOOK + INSERT_D * np.array([math.sin(rr), -math.cos(rr)])

# ---- sights
NOTCH_X = D["rear_sight"]["notch_X_est"]["mm"] + 1.2                    # notch plate face, 1.2 mm ahead of the leaf's rear end
# the leaf (and its notch plate) overhangs the dust cover's front end (c2; check fix): the block itself starts at the
# dust cover front, so the block box is [cover front, trace front], the leaf box starts at the trace's rear end
RS_BLOCK_X = [D["dust_cover"]["X"][1], D["rear_sight"]["block_X"][1]]
NOTCH_Z = D["rear_sight"]["leaf_top_Z"]["mm"] - 2.5                     # U-notch 2.5 deep (below sheet resolution: norm)
POST_X = D["front_sight_block"]["hood_centre_X"]["mm"]
POST_Z = NOTCH_Z - 0.5                                                  # 100 m zero: line ~1.4 mrad down toward the muzzle
SIGHT_PITCH = math.degrees(math.atan2(POST_Z - NOTCH_Z, POST_X - NOTCH_X))
# R48 (form realism round): the eye line runs over the notch TOP (the shoulders, leaf top) to the post tip -- the
# real-pattern sight picture, post tip level with the notch top and centred in it. The line through the notch
# BOTTOM puts the tip on the notch floor, so the post is hidden behind the leaf (the 'broken sight line').
NOTCH_TOP_Z = D["rear_sight"]["leaf_top_Z"]["mm"]
EYE_PITCH = math.degrees(math.atan2(POST_Z - NOTCH_TOP_Z, POST_X - NOTCH_X))

# ---- brake cut
BR = D["muzzle_brake"]
TAN = math.tan(math.radians(BR["front_face_angle_from_vertical_deg"]))
BR_ZB, BR_ZT = BR["Z"]
BR_TOP_FRONT_X = 880.0 - (BR_ZT - BR_ZB) * TAN
MUZZLE_X = 880.0 - (0.0 - BR_ZB) * TAN                                  # bore axis meets the cut plane

# ---- widths (TOP authority) and other decided numbers
W_COVER = TV["receiver_body_width_plain_section"]["mm"]                 # 43.5: the dust cover is the widest from above
W_RECEIVER = round(W_COVER - 2.0, 1)                                    # walls under the 1.0 mm cover skirts
HALF_W = W_RECEIVER / 2
BARREL_D = 15.0
ROD_D = 4.0
GAS_D = D["gas_tube"]["diameter_exposed"]["mm"]
GAS_Z = D["gas_tube"]["axis_Z"]["mm"]
UPPER_HG_X = D["handguard_upper"]["X"]                                  # cleaned trace (the old 487.1 start was a sliver ring)
assert abs(UPPER_HG_X[0] - 534.0) < 1.0, UPPER_HG_X
# grip section width (unseen on the sheet). Form fix round 1: 31.0, inside the documented real AK grip widths
# (IMI Defense AK47/AK74 grip 30 mm, FAB Defense Gradus AK grip 36 mm); 30.0 put the rounded-oblong girth on the
# band's lower edge (W 30 / straps R 10 = 122 mm). The camera-solved 3/4 view cannot separate 28-32 (zone IoU
# 0.903-0.908).
GRIP_WIDTH_Y = 31.5                     # R31 (30 -> 31), R33 (31 -> 31.5)
CH_TIP_Y = -35.2                                                        # TOP image-down knob extreme (gun right)

# ---- frames: M (measurement) -> B (Blender build, origin Grip) -> Unreal cm
GX, GZ = float(G[0]), float(G[1])


def to_b(x, y, z):
    return [round(x - GX, 2), round(y, 2), round(z - GZ, 2)]


def to_ue(b):
    return [round(b[0] / 10, 3) + 0.0, round(-b[1] / 10, 3) + 0.0, round(b[2] / 10, 3) + 0.0]


def sock(name, bone, m, rot=None, use="", src="", plan_name=None):
    b = to_b(*m)
    out = {"socket": name, "bone": bone, "M_mm": r1(m, 2), "blender_mm": b, "unreal_cm": to_ue(b),
           "unreal_rotation_deg": rot or {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}, "use": use, "source": src}
    if plan_name:
        out["plan_name"] = plan_name
    return out


def msock(name, m, rot=None, use="", src="", plan_name=None):
    """magazine socket in the mag frame (origin = hook, axes = rifle axes when seated)."""
    b = [round(m[0] - HOOK[0], 2), round(m[1], 2), round(m[2] - HOOK[1], 2)]
    out = {"socket": name, "M_mm_seated": r1(m, 2), "mag_mm": b, "unreal_cm": to_ue(b),
           "unreal_rotation_deg": rot or {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}, "use": use, "source": src}
    if plan_name:
        out["plan_name"] = plan_name
    return out


# ---- bounds (sphere radius about the box centre; Unreal uses box extents + sphere)
def bounds_r(x0, x1, y0, y1, z0, z1):
    return math.sqrt(((x1 - x0) / 2) ** 2 + ((y1 - y0) / 2) ** 2 + ((z1 - z0) / 2) ** 2)


R_RIFLE = bounds_r(0, 880, CH_TIP_Y, W_COVER / 2, D["overall"]["bottom_Z_without_mag"]["mm"], D["overall"]["top_Z"]["mm"])
R_RIFLE_MAG = bounds_r(0, 880, CH_TIP_Y, W_COVER / 2, D["overall"]["bottom_Z_with_mag"]["mm"], D["overall"]["top_Z"]["mm"])
R_MAG = bounds_r(MAG["X"][0], MAG["X"][1] + 4, -MAG_T / 2, MAG_T / 2, MAG["Z"][0], HOOK_Z + 4)
SS_RIFLE = [1.0, 0.30, 0.12, 0.04]
SS_MAG = [1.0] + [round(s * R_MAG / R_RIFLE, 4) for s in SS_RIFLE[1:]]

TR = "trace/LEFT_outline.json"
# cleaned per-part trace mask areas (sheet px); L2 gates parts under L2_AREA_PX on contour distance, not IoU (check C3)
L2_AREA_PX = 400.0
PART_AREA_PX = {nm: round(sum(r["area_px"] for r in rr if r["kind"] == "outer"), 1) for nm, rr in LEFT["parts"].items()
                if rr and nm != "unassigned"}
THIN_PARTS = sorted((nm for nm, a in PART_AREA_PX.items() if a < L2_AREA_PX), key=lambda n: PART_AREA_PX[n])


def tref(part):
    return {"file": TR, "key": f"parts.{part}", "view": "LEFT-labelled panel (= true RIGHT side)", "frame": "M"}


# ================================================================================================== parts
F_LAC = "black_lacquer_steel"
F_BLUE = "bluing_small_parts"
F_WOOD = "walnut_shellac"
F_MAG = "black_lacquer_mag"
F_BUTT = "butt_plate_lacquer_worn"
SLOT_METAL, SLOT_FURN, SLOT_MAG = "M_AR01_Metal", "M_AR01_Furniture", "M_AR01_Mag"

rec = D["receiver"]
dc = D["dust_cover"]
rs = D["rear_sight"]
lh = D["handguard_lower"]
uh = D["handguard_upper"]
gb = D["gas_tube"]["gas_block"]
fsb = D["front_sight_block"]
pg = D["pistol_grip"]
st = D["stock"]
bpl = D["butt_plate"]
tg = D["trigger_guard"]

# handguard side slots (check C1), +-1 mm: LEFT pixel columns, both panels
HG_SLOTS_X = [[543.0, 571.0], [595.0, 623.0]]
# receiver wall / trigger-guard top flange ledge seam behind the well (pixel columns, LEFT panel; check C9): a lit
# ledge line that rises toward the front; the flange's dark band below it reaches Z -34.8 (the grip top is -36.0)
LEDGE_Z = [[255.0, -32.5], [300.0, -31.3], [360.0, -29.5]]
FLANGE = {"X": [252.0, 370.0], "Z_top": "ledge_seam_XZ (-32.5 at X 255 rising to -29.5 at X 360)", "Z_bottom": -34.8,
          "note": "flat strap under the receiver from behind the grip junction to the catch housing (real pattern: the "
                  "guard's long top plate, riveted); guard rivets at Z -25 belong to the receiver list"}

RIVETS_RIGHT = [  # (X, Z) read off scratch/gz_recv.png (LEFT-labelled panel = true right side), +-2 mm
    [260.0, -4.0], [250.0, -25.0], [313.0, -25.0], [350.0, -25.0], [379.0, -21.0], [413.0, -19.0],
    [457.0, -1.5], [472.0, -1.5], [475.0, -18.0]]
RIVETS_LEFT = [   # read off scratch/gzR_recv.png (RIGHT-labelled panel = true left side), shifted into LEFT's frame by the
    # local offset of the nearest common feature (selector pivot +4.6, dimple +10.3, front rivets +12.5), +-3 mm
    [258.0, -7.0], [254.0, -28.0], [318.0, -26.0], [346.0, -26.0], [381.0, -22.0], [409.0, -19.5],
    [457.0, -2.0], [475.0, -3.5], [475.0, -21.0]]

parts = []


def part(**kw):
    kw.setdefault("asset", "SK_AR01 + SM_AR01")
    parts.append(kw)


part(id="receiver", display="Receiver (stamped shell, front trunnion)", bone="body", process="S-bend (1.0 mm sheet) + "
     "M-chamfer (front trunnion faces)", joint={"type": "fixed", "parent": None},
     slot=SLOT_METAL, finish=F_LAC, texel_class="B rear / C front",
     box_M={"X": [rec["side_plate_rear_X"]["mm"], rec["X"][1]], "Z": [LEDGE_Z[0][1], rec["side_top_Z"]["mm"]],
            "Y": [-HALF_W, HALF_W]},
     dims={"length_incl_rear_trunnion": rec["length"]["mm"], "side_wall_height": rec["height_side_plate"]["mm"],
           "outer_width_walls": W_RECEIVER, "bottom_Z": rec["bottom_Z"]["mm"],
           "bottom_Z_note": "-28.8 is the wall bottom AHEAD of the magazine well (X 432-485). Behind the well (X ~252-370) "
                            "the wall runs down to the ledge seam (ledge_seam_XZ), below which the trigger guard's top "
                            "flange shows (trigger_guard.dims.top_flange); the traced key parts.receiver includes that band",
           "ledge_seam_XZ": LEDGE_Z, "side_top_seam_Z": rec["side_top_Z"]["mm"],
           "bore_above_bottom": D["heights"]["bore_above_receiver_bottom"]["mm"],
           "front_face_X": rec["X"][1], "lower_handguard_cup_X": [483.0, rec["X"][1]]},
     construction="U-channel of 1.0 mm sheet: flat vertical walls, flat bottom, open top closed by the dust cover. "
     "Solid outer form with real 1.0 mm wall reveals at every opening (ejection port, magazine well, rear tang joint). "
     "Bottom corners R 1.5 with a thin ledge line where the bottom plate meets the walls. The front trunnion region "
     "(X 452-485) ends in a thin steel cup (X 483-485.3) that receives the lower handguard.",
     features=[
         {"name": "ejection_port", "side": "right", "X": [338.0, 452.0], "Z": [3.0, 17.0], "conf": "low-medium (+-3 mm; "
          "blurred)", "note": "through the wall and the cover skirt; 1 mm wall reveal; dark interior; the carrier fills the "
          "front 2/3 (X 378-450); must also clear the full bolt travel (B3)"},
         {"name": "magazine_well", "X": [round(MAG["X"][0] - 0.9, 1), round(HOOK[0] + 3.0, 1)], "width_Y": MAG_T + 1.0,
          "depth_above_bottom": round(HOOK_Z + 4 - REC_BOT, 1), "note": "fitted to the exported mag (lateral 0.2-0.6 mm, lug "
          "recess 0.1-0.4); front lug recess at the front wall, catch notch at the rear; interior reload-visible (class E)"},
         {"name": "side_dimple", "side": "both", "centre_XZ": [397.0, -17.0], "size": [18.0, 11.0], "depth": 1.0,
          "note": "pressed oval, 1 mm soft fillet; right reads (395,-17), left (395,-19.5) after the RIGHT-panel shift"},
         {"name": "pressed_groove", "side": "left", "X": [420.0, 460.0], "Z": -20.0, "width": 3.0, "depth": 0.8,
          "conf": "low", "note": "only on the RIGHT-labelled panel (true left), ahead of the dimple; build as drawn"},
         {"name": "rivets_right", "side": "right", "XZ": RIVETS_RIGHT, "head": "domed 4.5 dia, 1.0 proud (norm: < 4 sheet "
          "px)", "conf": "+-2 mm"},
         {"name": "rivets_left", "side": "left", "XZ": RIVETS_LEFT, "head": "domed 4.5 dia, 1.0 proud", "conf": "+-3 mm"},
         {"name": "pin_right", "side": "right", "XZ": [388.0, -8.0], "head": "flush pin 3.5 dia, inset ring"},
         {"name": "pin_left", "side": "left", "XZ": [372.0, 11.0], "head": "flush pin 3.5 dia (under the cover skirt)"}],
     wear="edge abrasion on the bottom edge and front/rear corners; bright rivet crowns; fine scratches on the flats; "
          "scratch fan into the mag well; thumb arc under the selector (right)",
     trace=tref("receiver"), side_profile_M=profile("receiver"), authority="LEFT-labelled panel (true right) for the "
     "outline and right-side features; RIGHT-labelled panel for left-side features; TOP for width",
     confidence="high (outline), medium (features)", sources=["measure", "craft 2.1", "zoom readings in this merge"])

part(id="rear_trunnion", display="Rear trunnion / stock tang block", bone="body", process="M-chamfer",
     joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_LAC, texel_class="B",
     box_M={"X": [rec["X"][0], rec["side_plate_rear_X"]["mm"]], "Z": rec["rear_cap_Z"], "Y": [-HALF_W, HALF_W]},
     dims={"length": round(rec["side_plate_rear_X"]["mm"] - rec["X"][0], 1)},
     construction="Short steel block at the receiver rear, slightly taller than the stock wrist, vertical rear face into "
     "which the stock seats; two rivet heads on its side region belong to the receiver list.",
     features=[], wear="corner edge wear", trace={"file": TR, "key": "parts.receiver (X < 240.9)", "frame": "M"},
     authority="LEFT-labelled panel", confidence="medium", sources=["measure", "craft rear_tang_block"])

part(id="dust_cover", display="Dust cover", bone="body", process="S-bend (1.0 mm sheet)",
     joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05], "note": "removable in reality; no bone (gun study 2.2)"},
     slot=SLOT_METAL, finish=F_LAC, texel_class="B",
     box_M={"X": dc["X"], "Z": [rec["side_top_Z"]["mm"], round(CROWN_Z, 1)], "Y": [-W_COVER / 2, W_COVER / 2]},
     dims={"length": dc["length"]["mm"], "crown_Z": round(CROWN_Z, 1), "outer_width": W_COVER,
           "crown_radius": round(W_COVER / 2, 2), "skirt_bottom_Z": rec["side_top_Z"]["mm"],
           "height_crown_to_skirt": round(CROWN_Z - rec["side_top_Z"]["mm"], 1), "front_end_top_Z_under_sight_block": 36.2,
           "rear_profile_XZ": r1(DC_REAR, 1)},
     construction="Smooth stamped cover: semicircular crown (radius = half width) on straight vertical skirts that sit "
     "outside the receiver walls. NO transverse ribs (none in any panel). Lengthwise shoulder line where crown meets "
     "skirt. Rear: rounded top-rear corner (profile in dims.rear_profile_XZ) with a rectangular hole for the recoil "
     "spring guide button. Front: tucks under a groove in the rear sight block's rear face. Right skirt cut out over "
     "the ejection port. Crisp 1 mm skirt edge with a shadow gap to the receiver.",
     features=[{"name": "skirt_cutout_right", "X": [338.0, 452.0], "note": "matches the ejection port"}],
     wear="strongest on the skirt edge and the rear corner; lengthwise highlight band on the crown",
     trace=tref("dust_cover"), side_profile_M=profile("dust_cover"), authority="LEFT-labelled panel; TOP for width",
     confidence="high", sources=["measure (crown corrected)", "craft 2.2"])

part(id="recoil_spring_button", display="Recoil spring guide button", bone="body", process="M-round",
     joint={"type": "butt", "parent": "dust_cover", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_LAC, texel_class="B",
     box_M={"X": [243.0, 251.0], "Z": [round(CROWN_Z - 4, 1), round(CROWN_Z - 1, 1)], "Y": [-3.0, 3.0]},
     dims={"size": [8.0, 6.0], "proud": 3.0},
     construction="Small rectangular tab with a rounded top through the hole at the dust cover rear, top centre.",
     features=[], wear="bright top edge", trace=None, authority="TOP + c1", confidence="low (c1 loop-like, TOP squared "
     "tab: TOP wins)", sources=["craft"])

part(id="bolt_carrier", display="Bolt carrier with charging handle", bone="bolt", process="M-chamfer",
     joint={"type": "sliding", "parent": "receiver", "clearance_mm": [0.15, 0.40], "axis": "-X", "travel_mm": 100.0,
            "note": "travel nominal (real-pattern stroke; unseen): the build sets it so the handle stops 3 mm before the "
                    "port's rear wall and the B3 sweep is clean"},
     slot=SLOT_METAL, finish=F_BLUE, texel_class="B",
     box_M={"X": [378.0, 458.0], "Z": [3.0, 22.0], "Y": [CH_TIP_Y, -HALF_W + 2.0]},
     dims={"carrier_visible_X": [378.0, 450.0], "carrier_face_inset_from_wall": 2.0,
           "charging_handle": {"X": [444.0, 458.0], "Z": [11.0, 22.0], "tip_Y": CH_TIP_Y,
                               "proud_of_wall": round(-CH_TIP_Y - HALF_W, 1)}},
     construction="Flat steel carrier block visible in the forward 2/3 of the port with a lengthwise highlight; the "
     "charging handle is a short rectangular tab (flat top, rounded outer corners) at the port's front end, drawn as a "
     "tab, NOT the classic round knob. Bolt face visible through the port at rest (dark).",
     features=[], wear="polished bare metal on the carrier flank and handle face (sliding)",
     trace=None, authority="LEFT-labelled panel (X, Z), TOP (protrusion; TOP draws it 25 mm further forward, side wins on X)",
     confidence="medium", sources=["craft 2.3", "zoom gz_port", "TOP lateral feature image-down X 470-482"])

part(id="selector", display="Selector lever (right side)", bone="selector", process="S-cut (3 mm plate) + M-round boss",
     joint={"type": "hinge", "parent": "receiver", "clearance_mm": [0.10, 0.30], "axis": "Y (transverse) through the boss",
            "pivot_M": [282.8, -7.8], "positions_deg": {"safe (as drawn)": 0.0, "auto": 16.0, "semi": 32.0},
            "note": "front tab moves down; angles nominal, set by the build so the tab clears the port edge"},
     slot=SLOT_METAL, finish=F_BLUE, texel_class="B",
     box_M={"X": D["face_features"]["selector_lever"]["X"], "Z": D["face_features"]["selector_lever"]["Z"],
            "Y": [-(HALF_W + 4.5), -HALF_W]},
     dims={"boss_dia": 13.4, "boss_proud": 3.0, "plate_thickness": 3.0, "plate_standoff": 1.5, "length": 80.8,
           "depth_at_pivot": 14.0, "depth_at_front": 8.0, "tab_bend_out_deg": 25.0},
     construction="Domed round pivot boss with a central pin face; flat stamped lever plate tapering to the front with "
     "a pressed stiffening ridge along its length; the front end steps up and bends outward into a finger tab just "
     "under the port's lower edge. Posed up (safe). No selector markings (letters omitted; two plain detent dimples at "
     "most).", features=[{"name": "face_outline_M", "XZ": D["face_features"]["selector_lever"]["outline_mm"]},
                        {"name": "pivot_outline_M", "XZ": D["face_features"]["selector_pivot"]["outline_mm"]}],
     wear="edges and tab bright, ridge crest worn; thumb arc on the receiver",
     trace={"file": TR, "key": "face_features.selector_lever / selector_pivot", "frame": "M"},
     authority="LEFT-labelled panel (it IS the right side) + c1", confidence="high (shape)",
     sources=["measure face outline", "craft 2.4"], left_side_copy="NOT built by default: the RIGHT-labelled panel (true "
     "left) also draws this lever; the user decides (open question 1)")

part(id="rear_sight_block", display="Rear sight block", bone="body", process="M-chamfer",
     joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_LAC, texel_class="B",
     box_M={"X": RS_BLOCK_X, "Z": [rec["side_top_Z"]["mm"], 42.0], "Y": [-W_COVER / 2, W_COVER / 2]},
     dims={"length": round(RS_BLOCK_X[1] - RS_BLOCK_X[0], 1), "base_width": W_COVER, "leaf_bed_width": 20.0,
           "note": "trace key parts.rear_sight = block + leaf; the leaf overhangs the dust cover front to X "
                   + str(rs["block_X"][0]) + " (c2)"},
     construction="Steel block on the front trunnion, vertical front face (receives the gas tube rear cap); the rear "
     "upper part steps down to the dust cover crown with a groove that seats the cover's front edge; two low curved "
     "cam rails along the top sides carry the leaf. Traced see-through gap under the leaf (X 466-488, Z 35-41).",
     features=[{"name": "gap_under_leaf", "X": [465.8, 487.5], "Z": [34.8, 40.9]}],
     wear="corner edge wear", trace=tref("rear_sight"), side_profile_M=profile("rear_sight"),
     authority="LEFT-labelled panel + c2 + TOP", confidence="high", sources=["measure", "craft 2.5"])

part(id="handguard_retainer_lever", display="Handguard retainer lever (right) / boss (left)", bone="body",
     process="S-cut + M-round", joint={"type": "butt", "parent": "rear_sight_block", "gap_mm": [0.01, 0.05]},
     slot=SLOT_METAL, finish=F_BLUE, texel_class="B",
     box_M={"X": [463.0, 481.0], "Z": [24.0, 41.0], "Y": [-(W_COVER / 2 + 3.0), W_COVER / 2 + 2.0]},
     dims={"arm_length": 22.0, "arm_angle_deg": 45.0, "boss_dia": 6.0},
     construction="Right side: flat steel arm at 45 deg on the block side, pivot boss at the top front, rounded lower-rear "
     "end with a hole. Left side: the round boss only (as the RIGHT-labelled panel shows).",
     features=[], wear="edge wear", trace=None, authority="LEFT-labelled panel (right), RIGHT-labelled panel (left)",
     confidence="low-medium", sources=["craft 2.5", "zoom gz_port"])

part(id="rear_sight_leaf", display="Rear sight leaf, slider and notch", bone="sight_rear", process="M-chamfer",
     joint={"type": "hinge", "parent": "rear_sight_block", "clearance_mm": [0.10, 0.30], "axis": "Y at the leaf's front hinge",
            "pivot_M": [504.0, 41.0], "range_deg": [0.0, 6.0]},
     slot=SLOT_METAL, finish=F_BLUE, texel_class="A",
     box_M={"X": rs["leaf_X_span_top_3mm"], "Z": [40.0, rs["leaf_top_Z"]["mm"]], "Y": [-6.0, 6.0]},
     dims={"leaf_length": round(rs["leaf_X_span_top_3mm"][1] - rs["leaf_X_span_top_3mm"][0], 1), "leaf_width": 12.0,
           "notch_plate_top_Z": rs["leaf_top_Z"]["mm"], "notch_bottom_Z": NOTCH_Z, "notch_X": round(NOTCH_X, 1),
           "notch_width": 2.0, "notch_depth": 2.5, "slider_X": [457.5, 465.5], "slider_top_Z": 48.5,
           "rear_overhang_over_dust_cover": round(D["dust_cover"]["X"][1] - rs["leaf_X_span_top_3mm"][0], 1)},
     construction="Flat leaf hinged at the block front lying rearward, raised centre strip, NO graduations or numerals "
     "(no-markings rule; default: no ticks). Its rear end overhangs the dust cover's front end (c2, traced) and carries "
     "a tall transverse notch plate with a square-bottomed U-notch (lit top, side ears in c2). Slider box (the dark "
     "raised block at X 457.5-465.5 in the side view) riding on the leaf just ahead of the notch plate, with two spring "
     "catches on its sides.", features=[],
     wear="slider catches and notch edges bright", trace={"file": TR, "key": "parts.rear_sight (top 3 mm)", "frame": "M"},
     authority="c2 + TOP + LEFT-labelled panel", confidence="medium", sources=["measure", "craft 2.5"])

part(id="gas_tube_rear_cap", display="Gas tube rear cap", bone="body", process="M-chamfer",
     joint={"type": "butt", "parent": "rear_sight_block", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_LAC,
     texel_class="C", box_M={"X": D["gas_tube_rear_cap"]["X"], "Z": D["gas_tube_rear_cap"]["Z"], "Y": [-16.0, 16.0]},
     dims={"length": round(D["gas_tube_rear_cap"]["X"][1] - D["gas_tube_rear_cap"]["X"][0], 1)},
     construction="Steel cap ring between the rear sight block and the upper handguard; enters the block's front recess.",
     features=[], wear="rim edge wear", trace=tref("gas_tube_rear_cap"), side_profile_M=profile("gas_tube_rear_cap"),
     authority="LEFT-labelled panel", confidence="high", sources=["measure", "craft 2.11"])

part(id="upper_handguard", display="Upper handguard (wood)", bone="body", process="W-round",
     joint={"type": "butt", "parent": "gas_tube", "gap_mm": [0.01, 0.05]}, slot=SLOT_FURN, finish=F_WOOD, texel_class="C",
     box_M={"X": UPPER_HG_X, "Z": uh["Z"], "Y": [-15.5, 15.5]},
     dims={"length": round(UPPER_HG_X[1] - UPPER_HG_X[0], 1), "height_median": uh["height_median"]["mm"], "width": 31.0},
     construction="Wood shell over the gas tube: half-round top with short vertical sides; small gap line to the lower "
     "handguard; grain along the bore. Width unseen (hidden in TOP between the lower guard's sides): 31 from the craft "
     "reading. Two long slots cut up into its LOWER edge on each side (features.lower_edge_slots): pure black in the "
     "sheet, so modelled as blind pockets with a dark (AO/cavity) interior.",
     features=[{"name": "lower_edge_slots", "per_side": 2, "both_sides": True, "X": HG_SLOTS_X, "Z": [13.1, 16.6],
                "depth_up_from_seam": 3.5, "pocket_depth_Y": 3.0, "corner_R": 1.0,
                "measured": "LEFT pixel columns: dark Z ~16.4-11.5 at X 545-569 and 596-620 (elsewhere only the 1-2 mm "
                            "joint line at Z 12.7-13.9); RIGHT panel: the same 26 mm slots, shifted +9 with its "
                            "forward-drawn mid section", "gate": "L3 feature positions <= 2 sheet px"}],
     wear="top highlight, rounded end edges",
     trace=tref("handguard_upper"), side_profile_M=profile("handguard_upper"), authority="LEFT-labelled panel",
     confidence="high (profile), medium (width)", sources=["measure (length corrected)", "craft 2.11"])

part(id="lower_handguard", display="Lower handguard (wood)", bone="body", process="W-round",
     joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]}, slot=SLOT_FURN, finish=F_WOOD, texel_class="C",
     box_M={"X": lh["X"], "Z": lh["Z"], "Y": [-TV["handguard_width"]["mm"] / 2, TV["handguard_width"]["mm"] / 2]},
     dims={"length": lh["length"]["mm"], "height_max_rear": lh["height_max"]["mm"], "height_median": lh["height_median"]["mm"],
           "width": TV["handguard_width"]["mm"], "top_edge_Z": lh["Z"][1]},
     construction="Wood U-section (rounded bottom, slightly swelling sides), hollow barrel channel visible only at the "
     "ends; straight top edge, shallow convex belly. Under the upper guard's two side slots its top edge dips about "
     "1.5 mm (bevelled), deepest at each slot's front wall (Z ~10.5), so the slot opening reads Z ~10.5-16.6. Rear sits "
     "in the receiver's cup; front in the front band. (The craft notes' 'finger scallops at 10-30 / 45-65 %' were "
     "about 42 mm too far back: replaced by the measured stations.)",
     features=[{"name": "top_edge_dips", "per_side": 2, "both_sides": True, "X": HG_SLOTS_X, "depth": 1.5,
                "front_wall_bottom_Z": 10.5, "bevel": 0.5, "pairs_with": "upper_handguard.lower_edge_slots",
                "gate": "L3 feature positions <= 2 sheet px"}],
     wear="support-hand wear on the belly and left side; rounded end edges", trace=tref("handguard_lower"),
     side_profile_M=profile("handguard_lower"), authority="LEFT-labelled panel; TOP for width",
     confidence="high (profile), medium-high (slots, measured on both panels)", sources=["measure", "craft 2.10", "check C1"])

part(id="handguard_front_band", display="Handguard front band (ferrule)", bone="body", process="S-bend",
     joint={"type": "butt", "parent": "lower_handguard", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_LAC,
     texel_class="C", box_M={"X": D["handguard_front_band"]["X"], "Z": D["handguard_front_band"]["Z"],
                             "Y": [-(TV["handguard_width"]["mm"] / 2 + 0.6), TV["handguard_width"]["mm"] / 2 + 0.6]},
     dims={"length": D["handguard_front_band"]["length"]["mm"], "proud_of_wood": 0.6},
     construction="Steel ferrule cups over both handguard fronts, slightly proud of the wood, rolled rim; the cleaning rod "
     "emerges below it.", features=[], wear="rim edge wear", trace=tref("handguard_front_band"),
     side_profile_M=profile("handguard_front_band"), authority="LEFT-labelled panel", confidence="high",
     sources=["measure", "craft"])

part(id="gas_tube", display="Gas tube", bone="body", process="M-chamfer",
     joint={"type": "butt", "parent": "gas_block", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_LAC, texel_class="D",
     box_M={"X": [D["gas_tube_rear_cap"]["X"][0], gb["X"][0] + 10.0], "Z": [round(GAS_Z - GAS_D / 2, 1), round(GAS_Z + GAS_D / 2, 1)],
            "Y": [-GAS_D / 2, GAS_D / 2]},
     dims={"dia": GAS_D, "axis_Z": GAS_Z, "exposed_X": [646.9, gb["X"][0]], "exposed_length": D["gas_tube"]["exposed_length"]["mm"]},
     construction="Steel tube; exposed between the front band and the gas block, hidden under the upper handguard back to "
     "the rear cap. Three short oval vent slots (6 x 3) per side near its front (X 662-680).",
     features=[{"name": "vent_slots", "per_side": 3, "X": [662.0, 680.0], "size": [6.0, 3.0], "conf": "low"}],
     wear="slot edges, top highlight; soot gradient from the vents", trace=tref("gas_tube"),
     authority="LEFT-labelled panel", confidence="high (tube), low (vents)", sources=["measure", "craft 2.11"])

part(id="gas_block", display="Gas block", bone="body", process="M-chamfer",
     joint={"type": "butt", "parent": "barrel", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_LAC, texel_class="D",
     box_M={"X": gb["X"], "Z": gb["Z"], "Y": [-10.8, 10.8]},
     dims={"length": gb["length"]["mm"], "top_Z": gb["top_Z"]["mm"], "lug_bottom_Z": gb["bottom_Z_incl_lug"]["mm"],
           "width": 21.5, "sweep_deg": 45.0, "barrel_collar_dia": 20.0, "lug_X": [713.0, 722.0]},
     construction="Short collar around the gas tube front, sweeping down at 45 deg as a flat-sided arm to a barrel collar; "
     "round pin boss on the arm side; small lug under the barrel collar (rod guide).",
     features=[], wear="corner and collar edge wear; soot", trace=tref("gas_block"), side_profile_M=profile("gas_block"),
     authority="LEFT-labelled panel; TOP for width (21.5 at X 687-707)", confidence="high", sources=["measure", "craft 2.12"])

part(id="barrel", display="Barrel", bone="body", process="M-chamfer (turned)",
     joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_LAC, texel_class="D",
     box_M={"X": [433.8, D["barrel"]["muzzle_end_X"]["mm"]], "Z": [-BARREL_D / 2, BARREL_D / 2], "Y": [-BARREL_D / 2, BARREL_D / 2]},
     dims={"length": 415.0, "chamber_face_X": 433.8, "crown_X": D["barrel"]["muzzle_end_X"]["mm"], "dia": BARREL_D,
           "exposed_from_receiver_face": D["barrel"]["receiver_face_to_muzzle"]["mm"],
           "visible_X": [[646.9, 681.0], [737.0, fsb["X"][0]]], "bore_dia": 7.62, "bore_depth_visible_min": 16.0},
     construction="Plain turned steel tube, essentially straight; 48 sides at LOD0. The crown sits under the brake's rear "
     "collar; the bore is modelled at least 2 calibres deep with a chamfered crown and darkening (G11).",
     features=[], wear="soft lengthwise highlight, light scratches", trace=tref("barrel"), authority="LEFT-labelled panel",
     confidence="high (form), medium (dia: LEFT 14.8-15.0, RIGHT 15.5, TOP 16.7)", sources=["measure", "craft 2.12"])

part(id="cleaning_rod", display="Cleaning rod", bone="body", process="M-round (turned)",
     joint={"type": "butt", "parent": "front_sight_block", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_BLUE,
     texel_class="D", box_M={"X": [647.0, 812.0], "Z": [round(D["cleaning_rod"]["axis_Z"]["mm"] - ROD_D / 2, 1),
                                                       round(D["cleaning_rod"]["axis_Z"]["mm"] + ROD_D / 2, 1)], "Y": [-ROD_D / 2, ROD_D / 2]},
     dims={"dia": ROD_D, "axis_Z": D["cleaning_rod"]["axis_Z"]["mm"], "head": "flat T-head seated in the FSB lug"},
     construction="Steel rod from under the front band to the front sight block lug, through the gas block lug.",
     features=[], wear="polished highlights", trace=tref("cleaning_rod"), authority="LEFT-labelled panel + c3",
     confidence="high", sources=["measure", "craft 2.12"])

part(id="front_sight_block", display="Front sight block (base, collar, lug)", bone="body", process="M-chamfer",
     joint={"type": "butt", "parent": "barrel", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_LAC, texel_class="D",
     box_M={"X": fsb["X"], "Z": [fsb["bottom_Z_incl_rod_lug"]["mm"], 20.0], "Y": [-TV["front_sight_block_max_width"]["mm"] / 2,
                                                                                  TV["front_sight_block_max_width"]["mm"] / 2]},
     dims={"length": fsb["length_incl_front_collar"]["mm"], "base_width_max": TV["front_sight_block_max_width"]["mm"],
           "front_collar_X": [840.0, fsb["X"][1]], "front_collar_dia": 17.4, "lug_bottom_Z": fsb["bottom_Z_incl_rod_lug"]["mm"]},
     construction="Barrel collar with a cross pin (round head ~4) on the side, a small detent plunger at its top front "
     "retaining the brake, and a lug underneath for the cleaning rod head; front collar X 840-848.8.", features=[],
     wear="collar rims bright", trace=tref("front_sight_block"), side_profile_M=profile("front_sight_block"),
     authority="LEFT-labelled panel + c3; TOP for width", confidence="high", sources=["measure", "craft 2.13"])

part(id="front_sight_ears_post", display="Front sight ears, drum and post", bone="body", process="M-round",
     joint={"type": "butt", "parent": "front_sight_block", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_LAC,
     texel_class="A", box_M={"X": [812.0, 835.0], "Z": [8.0, fsb["hood_top_Z"]["mm"]], "Y": [-10.7, 10.7]},
     dims={"ear_top_Z": fsb["hood_top_Z"]["mm"], "ear_top_X": fsb["hood_top_X_span"], "hood_centre_X": POST_X,
           "ear_thickness": 2.5, "outer_width": 21.4, "post_tip_Z": POST_Z, "post_dia": 2.0, "drum_dia": 8.0,
           "window": {"X": [813.7, 827.2], "Z": [11.8, 21.6], "shape": "triangular, see-through (traced hole)"},
           "top_hole": {"XZ": [824.7, 29.9], "boss_ring_dia": 6.0, "hole_dia": 3.5, "boss_proud": 0.4,
                        "note": "raised ring with a dark centre (pixel dump: ring ~5 px, centre ~3 px at sheet "
                                "(702, 71.5)); c3's mark on it is left off (no markings)"}},
     construction="Two thin steel plates on the collar's edges: vertical front edge, rear edge raked about 20 deg, flat top "
     "with rounded corners, a triangular lightening window in the lower half (the traced see-through hole) and a small "
     "raised round boss with a hole in the upper half (dims.top_hole). Between them a round windage drum carrying a thin post 4.4 below the ear tops.",
     features=[], wear="ear edges strongly worn bright", trace=tref("front_sight_block"),
     authority="c3 + LEFT-labelled panel; TOP for width (21.4 at X 825)", confidence="high (ears), medium (post: hidden)",
     sources=["measure", "craft 2.13"])

part(id="muzzle_brake", display="Slant muzzle brake", bone="muzzle_device", process="M-chamfer (turned)",
     joint={"type": "fixed", "parent": "barrel", "note": "own bone; hidden when a suppressor mounts at MuzzleSeat"},
     slot=SLOT_METAL, finish=F_LAC, texel_class="D",
     box_M={"X": BR["X"], "Z": BR["Z"], "Y": [-TV["muzzle_brake_width"]["mm"] / 2, TV["muzzle_brake_width"]["mm"] / 2]},
     dims={"length": BR["length"]["mm"], "dia": TV["muzzle_brake_width"]["mm"], "height_side": BR["height"]["mm"],
           "cut_angle_from_vertical_deg": BR["front_face_angle_from_vertical_deg"], "bottom_lip_front_X": 880.0,
           "top_front_X": round(BR_TOP_FRONT_X, 1), "bore_dia": 7.62},
     construction="Cylinder screwed onto the barrel (thin seam ring at the FSB face). The front is cut by one slanted "
     "plane removing the TOP front, lower lip longer; the cut exposes the bore as an elongated oval with a rounded worn "
     "rim; a soft scallop on one side of the cut face (low confidence).", features=[],
     wear="rim and slant edge bright; soot inside the cut", trace=tref("muzzle_brake"),
     side_profile_M=profile("muzzle_brake"), authority="LEFT-labelled panel + c3; TOP for width",
     confidence="high (slant), low (scallop)", sources=["measure", "craft 2.14"])

part(id="trigger", display="Trigger", bone="trigger", process="C-fillet",
     joint={"type": "hinge", "parent": "receiver", "clearance_mm": [0.10, 0.30], "axis": "Y", "pivot_M": [318.0, -20.0],
            "range_deg": [0.0, 12.0], "note": "pivot hidden (nominal)"},
     slot=SLOT_METAL, finish=F_BLUE, texel_class="C", box_M={"X": D["trigger"]["X"], "Z": [-57.8, -34.5], "Y": [-3.0, 3.0]},
     dims={"blade_width": 6.0, "face_M": r1(TRIGGER_FACE, 1), "tip_Z": D["trigger"]["bottom_Z"]["mm"]},
     construction="Curved blade, forward-concave hook, about 23 mm visible below the receiver.", features=[],
     wear="finger face polished bright", trace=tref("trigger"), side_profile_M=profile("trigger"),
     authority="LEFT-labelled panel + c1/c6", confidence="high", sources=["measure", "craft 2.6"])

part(id="trigger_guard", display="Trigger guard", bone="body", process="S-bend (3 mm strap)",
     joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_LAC, texel_class="C",
     box_M={"X": tg["X"], "Z": [tg["bottom_Z"]["mm"], -34.5], "Y": [-5.0, 5.0]},
     dims={"length": tg["length"]["mm"], "bottom_Z": tg["bottom_Z"]["mm"], "drop_below_receiver": tg["drop_below_receiver_bottom"]["mm"],
           "strap_bottom_Z_columns": {"X 310": -68.0, "X 330": -66.8, "X 345": -64.7},
           "strap_width_Y": 10.0, "strap_thickness": 3.5, "rear_leg_X": [299.5, 303.2], "front_leg_X": [350.6, 355.2],
           "top_flange": FLANGE},
     construction="Steel strap: rear leg (X 299.5-303.2) down from the receiver, a rounded rear corner into a flat "
     "bottom run that rises slightly toward the front (Z -68.0 at X 310 to -64.7 at X 345), a near-square front corner "
     "rising into the catch housing. It does NOT reach back under the grip: the dark sliver at X 284-298 is the grip's "
     "front strap (check C2). Above the opening, its long flat top flange runs under the receiver (dims.top_flange).",
     features=[{"name": "opening", "see_through": True, "note": "traced hole"}], wear="edge wear on the bottom run",
     trace=tref("trigger_guard"), side_profile_M=profile("trigger_guard"), authority="LEFT-labelled panel + c1/c6",
     confidence="high", sources=["measure", "craft 2.6"])

part(id="mag_catch", display="Magazine catch", bone="mag_release", process="S-cut + M-round pin",
     joint={"type": "hinge", "parent": "receiver", "clearance_mm": [0.10, 0.30], "axis": "Y at the pin",
            "pivot_M": [362.0, -50.0], "range_deg": [0.0, 10.0]},
     slot=SLOT_METAL, finish=F_BLUE, texel_class="C", box_M={"X": D["mag_catch"]["X"], "Z": D["mag_catch"]["Z"], "Y": [-5.0, 5.0]},
     dims={"paddle_width_Y": 10.0, "tab_X": [360.2, 363.9], "tip_Z": D["mag_catch"]["bottom_Z"]["mm"]},
     construction="Flat paddle in front of the guard, pinned at mid-height (round pin head), lower tip a short tab below "
     "the guard; top merges into a small housing at the magazine's rear.", features=[], wear="tip edges bright",
     trace=tref("mag_catch"), side_profile_M=profile("mag_catch"), authority="LEFT-labelled panel + c1",
     confidence="high", sources=["measure", "craft 2.6"])

part(id="pistol_grip", display="Pistol grip (wood) with checkered panels", bone="body", process="W-round",
     joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]}, slot=SLOT_FURN, finish=F_WOOD, texel_class="B top / C",
     box_M={"X": pg["X"], "Z": pg["Z"], "Y": [-GRIP_WIDTH_Y / 2, GRIP_WIDTH_Y / 2]},
     dims={"height_below_receiver": round(pg["Z"][1] - pg["Z"][0], 1), "axis_rake_deg_from_vertical": round(GRIP_RAKE, 2),
           "axis_line_M": f"X = {k_axis:.4f} * Z + {c_axis:.2f} (midline, Z -64..-116)",
           "edge_rakes_deg": {"front": pg["front_edge_rake_from_vertical_deg"], "rear": pg["rear_edge_rake_from_vertical_deg"]},
           "width_perp_to_axis": round(GRIP_WIDTH_PERP, 1), "width_Y": GRIP_WIDTH_Y,
           "junction_M": r1(JUNCTION, 2), "length_along_axis": pg["length_along_axis"]["mm"],
           "strap_R_front": 9.0, "strap_R_back": 13.5},
     construction="Wood grip, the traced profile: wider flare at the receiver, front-bottom toe is the lowest point, "
     "rounded rear heel. Section a rounded oblong (31.5 wide: unseen; real AK grips 30-36, R31 / R33 in resolutions), flatter sides where the "
     "checkering sits, straps R 8-10 (front strap R 9; back strap R 13.5, the palm swell: R33). Checkered panel per side: border = real geometry (0.6 recess, 0.3 bevel), "
     "diamonds in the normal map baked from a modelled pyramid tile (pitch 1.2-1.5, elongated along the axis); a "
     "real-pyramid LOD0 option for first person. Bottom: plain flat end with a small chamfer, no cap or screw.",
     features=[{"name": "checker_panel", "both_sides": True, "from_top_fraction": [0.25, 0.88], "inset_front": 4.0,
                "width_fraction": 0.40, "corner_R": 3.0, "note": "c1 (true right) and c6 (true left, mirrored) agree"}],
     wear="firing-hand wear on the straps and toe (finish worn, oil-darkened); scratches on the upper sides; grime in cells",
     trace=tref("pistol_grip"), side_profile_M=profile("pistol_grip"), authority="LEFT-labelled panel + c1 + c6",
     confidence="high (profile), medium (section)", sources=["measure", "craft 2.7"])

part(id="buttstock", display="Buttstock (wood)", bone="body", process="W-round",
     joint={"type": "butt", "parent": "rear_trunnion", "gap_mm": [0.01, 0.05]}, slot=SLOT_FURN, finish=F_WOOD, texel_class="B comb / C",
     box_M={"X": st["X_wood"], "Z": [st["toe_Z"]["mm"], st["comb_nose"]["Z"]["mm"]], "Y": [-19.15, 19.15]},
     dims={"length_butt_to_receiver": st["length_butt_to_receiver"]["mm"], "heel_Z": st["heel_Z"]["mm"],
           "toe_Z": st["toe_Z"]["mm"], "comb_nose_XZ": [st["comb_nose"]["X"], st["comb_nose"]["Z"]["mm"]],
           "wrist_low_XZ": [st["wrist_low_point"]["X"], st["wrist_low_point"]["Z"]["mm"]],
           "comb_slope_deg": st["comb_line_slope_deg"], "bottom_slope_deg": st["bottom_line_slope_deg"],
           "width_by_X_TOP": TV["stock_width_by_X"], "profile_top_M": st["profile_top_mm"], "profile_bottom_M": st["profile_bottom_mm"]},
     construction="Solid wood (no laminate). Straight bottom line from the toe rising to the tang; comb nearly level "
     "rising to the comb nose, a short concave step down to the wrist, wrist top rising into the tang. Section a "
     "rounded rectangle (edges R 6-8), sides slightly convex; width per TOP. Top tang screw head at X 219 (TOP). "
     "Left wrist (RIGHT-labelled panel): a pointed, rearward-V inlet outline (25 x 20) with two small screw heads.",
     features=[{"name": "tang_screw_top", "X": 219.0, "head_dia": 6.0},
               {"name": "wrist_inlet_left", "side": "left", "size": [25.0, 20.0], "screws": 2}],
     wear="cheek-weld polish on the left comb; dents on toe and heel; a round ding on the right side near X 100 and a "
          "C-shaped mark on the left near X 30-40 (as drawn)",
     trace=tref("stock"), side_profile_M=profile("stock"), authority="LEFT-labelled panel; TOP for widths",
     confidence="high (profile), medium (section)", sources=["measure", "craft 2.8"])

part(id="butt_plate", display="Butt plate with 2 screws", bone="body", process="S-bend",
     joint={"type": "butt", "parent": "buttstock", "gap_mm": [0.01, 0.05]}, slot=SLOT_METAL, finish=F_BUTT, texel_class="C",
     box_M={"X": bpl["X"], "Z": bpl["Z"], "Y": [-TV["butt_plate_width"]["mm"] / 2, TV["butt_plate_width"]["mm"] / 2]},
     dims={"height": bpl["height"]["mm"], "width": TV["butt_plate_width"]["mm"], "band_thickness_side": bpl["thickness_side_view"]["mm"],
           "rear_face_tilt_deg_toe_forward": round(BUTT_TILT, 2), "rear_face_centre_M": r1(BUTT_C, 2),
           "screws_Z": [-10.0, -87.5], "screw_head_dia": 7.0,
           "screw_slot": "cross (X) slot, both screws, as c7 draws them (10x zoom: crossed slots in a dark ring)",
           "counterbore_ring": {"dia": 8.5, "depth": 0.6, "note": "the visible dark ring round each head"},
           "screw_fraction_c7": [0.066, 0.82]},
     construction="Steel plate over the whole butt end, stadium outline following the stock section, face slightly "
     "convex, wraparound skirt (the 12 mm band in the side view), rim rounded about 1 mm. Two countersunk screws on "
     "the centre line (c7 fractions 0.066 / 0.82), each a cross-slotted head in a visible counterbore ring (c7). "
     "No trap door.",
     features=[], wear="face densely covered in bright scratches; rim edges bright; toe/heel corners bare",
     trace=tref("butt_plate"), side_profile_M=profile("butt_plate"), authority="LEFT-labelled panel + c7; TOP for width",
     confidence="high", sources=["measure", "craft 2.9"])

part(id="sling_swivel_rear", display="Rear sling swivel", bone="body", process="M-round (loop) + S-cut base",
     joint={"type": "hinge", "parent": "buttstock", "clearance_mm": [0.10, 0.30], "note": "static at rest; no bone"},
     slot=SLOT_METAL, finish=F_BLUE, texel_class="C",
     box_M={"X": D["sling_swivel_rear"]["X"], "Z": D["sling_swivel_rear"]["Z"], "Y": [-6.0, 6.0]},
     dims={"loop_size": 12.0, "wire_dia": 2.5},
     construction="Small steel loop on a short base plate screwed to the stock's bottom line.", features=[],
     wear="loop worn bright", trace=tref("sling_swivel_rear"), side_profile_M=profile("sling_swivel_rear"),
     authority="LEFT-labelled panel", confidence="medium", sources=["measure", "craft"])

# -------------------------------------------------------------------------------------------- magazine (SM_AR01_Mag)
MAGT = "SM_AR01_Mag (on the magazine bone's Mag socket)"
part(id="magazine_body", asset=MAGT, display="Magazine body", bone="magazine (attach only)", process="S-bend (two halves)",
     joint={"type": "seated_mag", "parent": "receiver", "clearance_mm": {"lateral": [0.2, 0.6], "top_stop": [0.1, 0.5],
                                                                          "lug": [0.1, 0.4]}},
     slot=SLOT_MAG, finish=F_MAG, texel_class="C",
     box_M={"X": [MAG["X"][0], MAG["X"][1]], "Z": [MAG["Z"][0], HOOK_Z + 4.0], "Y": [-MAG_T / 2, MAG_T / 2]},
     dims={"arc_centre_M": MC.tolist(), "R_front_concave": R_IN, "R_rear_convex": R_OUT,
           "width_front_to_rear": MAG["width_front_to_rear_radial"]["mm"], "thickness_Y": MAG_T,
           "visible_top_Z": MAG["top_Z_receiver_cut"]["mm"], "lips_top_Z": HOOK_Z + 4.0,
           "angles_deg_about_centre": {"top_mid": round(A_TOP, 2), "floor_rear": round(A_BOT_OUT, 2), "floor_front": round(A_BOT_IN, 2)},
           "sweep_deg": MAG["arc_sweep_deg"], "length_along_centre_arc": MAG["length_along_centre_arc"]["mm"],
           "floor_rear_corner_M": r1(FLOOR_REAR, 1), "floor_front_corner_M": r1(FLOOR_FRONT, 1)},
     construction="Two stamped halves welded at front and rear spines; rectangular section with rounded spine edges; "
     "front and rear edges are concentric arcs (the curve bends forward). Spines (c5): a centre channel with two raised "
     "lengthwise lines. The part hidden in the well is fitted to the exported rifle (saya method).", features=[],
     wear="spine edges and floor-plate rim bright; insertion streaks on the spines",
     trace={"file": TR, "key": "magazine", "frame": "M", "note": "LEFT-labelled panel, mag in place"},
     authority="LEFT-labelled panel (in place); c4 mirrored (it is a true-left view) + c5 for surface",
     confidence="high (form)", sources=["measure", "craft 2.15"])

part(id="magazine_ribs", asset=MAGT, display="Magazine pressed ribs", bone="magazine (attach only)", process="S-bend",
     joint={"type": "integral", "parent": "magazine_body"}, slot=SLOT_MAG, finish=F_MAG, texel_class="C",
     box_M=None, dims={"ribs_per_side": 4, "rib_centres_fraction_from_rear_edge": [0.17, 0.34, 0.51, 0.66],
                       "front_rib_fraction": 0.79, "rib_width": 2.5, "rib_proud": 1.0,
                       "top_tips_Z_seated": -38.5, "top_tips_tol": 1.5, "top_tips_below_lips": 26.5,
                       "bottom_ends": "on the floor-plate band's upper line, 16 +-2 above the floor plate (perpendicular "
                                      "to it), read on the LEFT side view",
                       "ends": "rounded tips"},
     construction="Four raised pressed ribs per side parallel to the curve plus a narrower rib along the front edge, "
                  "real geometry (G-rule), round crowns.", features=[], wear="crests worn to bare steel (the strongest cue)",
     trace=None, authority="c4 (mirrored) + crest positions measured on the side view (0.18/0.34/0.52/0.68/0.76)",
     confidence="high (count)", sources=["measure ribs_side_view", "craft", "merge reading of c4"])

part(id="magazine_top_plates", asset=MAGT, display="Magazine top reinforcing plates", bone="magazine (attach only)",
     process="S-bend", joint={"type": "integral", "parent": "magazine_body"}, slot=SLOT_MAG, finish=F_MAG, texel_class="C",
     box_M={"Z": [-38.0, -12.0], "X_at_Z-25": TOP_PLATE_X, "Y": [-(MAG_T / 2 + 0.8), MAG_T / 2 + 0.8]},
     dims={"Z_seated": [-38.0, -12.0], "width_fraction_from_rear_edge": [0.08, 0.80], "X_at_Z-25": TOP_PLATE_X,
           "proud": 0.8, "note": "from the lips down to the rib tips; toward the rear of the width as c4 shows; mostly "
                                 "hidden in the well when seated (only Z -30.9..-38 shows)"},
     construction="Flat smooth plate on each side above the ribs (c4).", features=[], wear="plate edges bright",
     trace=None, authority="c4", confidence="medium", sources=["craft"])

part(id="magazine_lugs", asset=MAGT, display="Front locking lug (pivot) and rear catch lug", bone="magazine (attach only)",
     process="M-chamfer", joint={"type": "integral", "parent": "magazine_body"}, slot=SLOT_MAG, finish=F_MAG,
     texel_class="E", box_M=None, dims={"front_hook_M": r1(HOOK, 1), "rear_lug_X": [MAG["X"][0] - 2.0, MAG["X"][0] + 6.0]},
     construction="Front: a hooked tab at the top front; its hook point is the mag origin (rock pivot). Rear: a small "
                  "block at the top rear that latches on the catch.", features=[], wear="edges bright",
     trace=None, authority="c4 + c5", confidence="medium (hidden when seated; fit stage sets the exact hook)",
     sources=["craft", "plan 2.3"])

part(id="magazine_lips_follower", asset=MAGT, display="Feed lips and follower (empty)", bone="magazine (attach only)",
     process="S-bend", joint={"type": "integral", "parent": "magazine_body"}, slot=SLOT_MAG, finish=F_MAG, texel_class="E",
     box_M=None, dims={"lips_top_Z": HOOK_Z + 4.0},
     construction="Lips folded inward at the top, plain dark follower; no cartridge (the sheet shows none).",
     features=[], wear="lip edges bright", trace=None, authority="c5", confidence="medium", sources=["craft"])

part(id="magazine_floor_plate", asset=MAGT, display="Floor plate", bone="magazine (attach only)", process="S-bend",
     joint={"type": "butt", "parent": "magazine_body", "gap_mm": [0.01, 0.05]}, slot=SLOT_MAG, finish=F_MAG, texel_class="C",
     box_M=None, dims={"corner_to_corner": MAG["floor_plate_corner_to_corner"]["mm"], "lip_proud": 1.5,
                       "rear_corner_M": r1(FLOOR_REAR, 1), "front_corner_M": r1(FLOOR_FRONT, 1),
                       "outward_normal_M": r1(FLOOR_NORMAL, 4)},
     construction="Separate flat plate in rails at the bottom, lip proud all round, rounded front edge; a transverse "
                  "reinforcing band just above it (c4).", features=[], wear="rim strongly worn bright (drops)",
     trace={"file": TR, "key": "magazine (bottom)", "frame": "M"}, authority="LEFT-labelled panel + c4 + c5",
     confidence="high", sources=["measure", "craft"])

# ================================================================================================== detail pass
# Detail pass (2026-10-05): each detailed part was rebuilt from its own close-up (Scripts/guns/rifle/parts/<module>.py)
# and its builder filed a spec proposal (WorkFiles/guns/rifle/review/detail/<part>/spec_proposal.json). The justified
# ones are applied here as built (the part modules already build these values); deferred ones are listed in R35-R44
# and open_questions. Keys the build reads (rivet XZ lists, grip rake / width / junction, profiles, frames, sockets
# except the magazine Base) are unchanged.
DP_SRC = "review/detail/{}/spec_proposal.json"
_P = {p["id"]: p for p in parts}


def dp(pid, src, dims=None, construction=None, box=None, note=None, feature=None):
    p = _P[pid]
    if dims:
        p["dims"].update(dims)
    if construction:
        p.setdefault("construction_form_stage", p["construction"])
        p["construction"] = construction
    if box:
        p["box_M"] = box
    if feature:
        p["features"].append(feature)
    p.setdefault("detail_pass", []).append({"source": DP_SRC.format(src), "note": note or "applied as built"})


dp("selector", "selector",
   box={"X": [274.66, 354.71], "Z": [-16.01, 7.4], "Y": [-26.89, -18.0]},
   dims={"boss_dia": 10.64, "washer_collar_dia": 10.64, "head_dia": 7.59, "head_height": 1.52, "washer_proud": 0.8,
         "round_end_dia": 16.26, "plate_thickness": 2.0, "plate_standoff": 1.25, "tab_bend_out_deg": 12.0,
         "depth_at_pivot": 16.3, "depth_at_front": 10.6, "boss_proud": 2.32,
         "c1_pose_deg_front_down": 13.25, "c1_scale_vs_side": 1.10},
   construction="Solid 2.0 mm stamped lever plate on the c1-traced outline (round rear end, straight bottom, stepped "
                "hump, long falling top edge, rounded paddle nose), crisp bevelled edges, no edge groove; c1's long "
                "wedge between the top edge and the diagonal line is a tilted valley whose 40 deg crease wall faces up "
                "(the bright diagonal line). Nose tab bent out 12 deg with a small flat pin. Pivot: a raised washer "
                "ring (0.8 proud) and a flat-faced chamfered head with a small centre boss (no slot: c1 shows none). "
                "Posed up (safe) at rest; c1 draws it 13.25 deg front-down (review renders at the c1 camera pose it "
                "there). No selector markings.",
   note="selector rounds 1-2 as built; integration round: edge groove removed, dome -> flat chamfered head with a "
        "centre boss in a raised washer, ringed nose dome -> flat pin (round-2 blind judge tells)")
dp("rear_sight_leaf", "rear_sight",
   dims={"leaf_width": 17.0, "slider_body_width": 20.0, "catch_reach_width": 26.8, "slider_skirt_X": [452.6, 457.5],
         "slider_skirt_top_Z": 45.3, "skirt_and_catch_bottom_Z": 40.8, "slider_floor_from_X": 458.8,
         "teeth": {"count_per_rail": 11, "pitch": 2.8, "top_Z": 45.1}, "centre_slot": {"width": 5.6, "X": [466.8, 497.8]},
         "notch_blade_width": 13.2},
   construction="Ladder leaf: base plate 17 wide (Z 40.6-42.3) with two flat-topped rails (16 wide outer, top 44.4) "
                "split by a deep centre slot 5.6 wide (X 466.8-497.8); fine sawtooth serrations (11, pitch 2.8, to Z "
                "45.1) along each rail's slot-side edge; notch blade 13.2 wide on the rails' rear end, top 48.0, U notch "
                "2.0 wide to Z 45.5; slider with a raised rounded roof over X 457.5-465.5, a lower rear skirt back to "
                "the notch blade and side clamps reaching 26.8 across. No numerals or tick marks (teeth are form, not "
                "markings).", note="rear_sight rounds 1-2 as built")
dp("rear_sight_block", "rear_sight",
   construction="Contoured casting: the full-width vertical side face stops at a swooping top edge (Z 34.0-34.8 over "
                "the rear, an S-rise from X ~481 into the full-height front housing at X 511.5); above it a straight "
                "5.6 mm chamfer band rolls in to a narrow deck / cam walls (Y +-10.8) beside the leaf; the housing "
                "carries a transverse rounded bar (r 3.3 at X 510.8, Y +-15.5); two small domed screw heads on the "
                "side face; the traced see-through slit under the leaf (X 465.8-487.5, Z 38.7-40.9) with its slanted "
                "slot; the slider sits in a stepped pocket (body width, then the catches from their bottom) so no "
                "see-through slit joins the traced one (integration round).",
   note="rear_sight round 2 as built; integration round: stepped slider pocket (L3 gap-under-the-leaf bbox)")
dp("handguard_retainer_lever", "rear_sight",
   construction="Right side: slim stamped slotted link 1.6 thick (boss r 3.3, end r 2.9, open slot r 1.3 at 27-80 % "
                "of the length) from a prominent pivot pin (collar r 3.5 x 1.1 + domed head, 2.35 proud of the link) "
                "at the block's top front to a small domed screw head at the lower end. Left side: the round boss only.",
   note="rear_sight round 2 as built")
dp("front_sight_ears_post", "front_sight",
   dims={"ear_thickness": 3.8, "drum_dia": 5.6,
         "ear_rims": "every ear outline / window edge rolled R 1.5 (outer faces) / 1.2 (inner) / 0.9 (window floor); "
                     "top corners R 3.0 front, 3.5 rear",
         "window": {"X": [813.4, 827.2], "Z": [12.2, 21.8], "shape": "rounded trapezoid, rear side raked with the ear, "
                    "corner radii 1.6 / 2.2 / 2.6 / 2.0, rolled 1.5 rim"},
         "top_hole": {"XZ": [824.7, 29.9], "boss_dia": 7.4, "hole_dia": 0.0, "rim_proud": 0.32, "rim_width": 0.4,
                      "face_proud": 0.18, "scribed_groove": "0.36 wide x 0.22 deep, from the boss's lower rear edge "
                      "toward the rake", "note": "c3: a flush disc outlined by a thin ring (no through hole)"},
         "inner_faces": "blind hole dia 4.0 x 2.0 deep at (829.4, 43.4), round-ended slot 2.4 x 7.0 x 1.4 deep "
                        "(X 829.3-831.7, Z 27.5-34.5), drum counterbore r 3.3 x 0.9 (both ears' inner faces only)"},
   construction="Two thick ears (3.8) cast in one with the base, every outline and window edge rolled; rounded "
                "trapezoid window; a flush boss disc with a thin raised ring rim and a scribed groove on the outer "
                "faces; blind hole and slot on the inner faces; windage drum r 2.8 between them carrying the post.",
   note="front_sight rounds 1-2 as built (integration: rims 2 segments, budget)")
dp("front_sight_block", "front_sight",
   construction="Cast block: a loft of rounded-box sections X 806.1-837.0 (|Y| 11.0, Z -10.3..11.3, top shoulders "
                "R 5.0, flanks bulging 1.2, round lower half R 9.0: reads as a round sleeve band, c3), rear rim R 2.2, "
                "front shoulder R 1.6; ears cast in one; a ring collar r 9.7 (X 836.6-839.6) then a NARROW collar "
                "r 8.7 to the brake's rear face X 848.78, so the brake steps up from it (c3: sleeve band -> narrow ring "
                "-> brake); cross pin dia 4.0 at X 830.5 Z -5.0 with domed heads; c3's stepped, notched cleaning-rod "
                "lug; detent plunger at X 841.2.",
   note="front_sight round 2 as built; integration round: rounder base (R 5.0 / 9.0, was 3.2 / 7.0) and the front "
        "collar r 10.1 -> 8.7 (the brake read long with a seam: judge tells on c3)")
dp("cleaning_rod", "front_sight", box={"X": [641.0, 815.5], "Z": [-14.1, -10.1], "Y": [-2.0, 2.0]},
   dims={"head_box": "X 811.0-815.5, Y +-2.5, Z axis +-2.6 (inside the lug, hidden)"}, note="as built")
dp("muzzle_brake", "muzzle_brake", box={"X": [848.82, 880.0], "Z": [-10.1, 11.15], "Y": [-10.1, 10.1]},
   dims={"body_r": [9.6, 9.85], "flare": "R(x) = 9.6 + 0.25 ((x - 848.82) / 31.18) ^ 1.5",
         "rim_ring": {"r": 10.1, "length_behind_face": 3.4, "ramp": 0.35, "note": "the widest point (key dia 20.2)"},
         "face": "flat band, outer round 0.6 (top) .. 2.0 (chin) along the face, inner round 0.5",
         "cut_angle_from_vertical_deg": 37.5, "cut_X_at_Z0": 873.1, "chamber_r": 7.1, "chamber_floor_X": 858.5,
         "slot_side": "right (-Y) only", "slot_Z": [-5.9, 7.2], "slot_rear_X": "862.0 - 0.20 Z",
         "slot_front_X": "870.0 - 0.55 Z", "slot_edge_round": 0.35,
         "knob": {"X": [847.4, 852.4], "top_Z": 11.15, "Y": [-2.6, 2.6], "note": "detent knob at the junction, rooted "
                  "in the brake, its rear part 0.03 above the FSB's narrow collar (r 8.7)"}},
   construction="One turned body screwed onto the barrel, rear face X 848.82 (r 9.6, chamfer 0.35), flaring to r 9.85, "
                "then a raised rim ring r 10.1 over the last 3.4 mm behind the face (c3: a thick rim band standing "
                "proud). The front is cut by one slanted plane (37.5 deg from vertical, X 873.1 at Z 0) removing the "
                "TOP front: a FLAT face band (wall 3.0) with small rounds, a long chin round; plain chamber bore r 7.1 "
                "with its floor at X 858.5 (c3: a flat-floored oval mouth with a visible inner wall). ONE long rounded "
                "oblong slot through the RIGHT wall ending close to the rim band (web 1.6 / 3.2 / 4.5 at Z 7 / 0 / -6). "
                "A small domed detent knob at the junction. Body measured without the knob: length 31.2, dia 20.2 (L4).",
   note="muzzle_brake round 2 as built, then the integration round: bullnose -> flat face band + raised rim ring, cone "
        "-> plain bore with a nearer floor, wider slot nearer the rim, max radius 10.1 and the chin's front X 880.0 "
        "(L4 key dims), knob lowered onto the narrowed collar")
dp("pistol_grip", "grip",
   dims={"strap_R_front": 9.0, "strap_R_front_on_block": "4.0 above Z -50, smoothstep to 9.0 by Z -68",
         "strap_R_back": 9.0, "side_crown": 0.35, "bottom_round": 2.5, "flange_break": 0.5,
         "guard_leg_slot_half_width_Y": 5.05},
   construction="Wood grip on the traced side profile reshaped to c6 (parts/grip_shape.py: square top-back corner, "
                "straight block face under the guard with a soft shoulder R 8 / 16, squarer heel R 4, round toe nose), "
                "inside the side-view per-part gate. Section a rounded oblong 31.5 wide with flatter sides, front "
                "strap R 9 (R 4 on the top block), back strap R 9; bottom flat with a 2.5 round. Checkered panel per "
                "side: the quadrilateral measured on c6 (features.checker_panel), border = real geometry (0.75 recess, "
                "0.15 bevel, 0.7 flat band); the cells are a normal map baked from modelled ridges (two groove "
                "families: A 46 deg / 1.61 mm continuous ridges, B -49 deg / 1.72 mm shallow notches).",
   note="grip rounds 1-2 as built (H1 girth 129.7, width 31.09 pass); back strap R 13.5 -> 9 (supersedes R33's back "
        "strap); integration round: front strap back to R 9 (round 2 had 7; the solved 3/4 view contradicted it and the "
        "3/4 IoU fell below the exception floor)")
for f in _P["pistol_grip"]["features"]:
    if f.get("name") == "checker_panel":
        f.update({"corners_ts_mm": {"front_top": [16.12, 10.97], "rear_top": [27.86, -7.06], "rear_bottom": [87.99, -4.12],
                                    "front_bottom": [87.59, 15.19]},
                  "frame": "t down the 22.35 deg axis from the junction (280.67, -36.0), s toward the front strap",
                  "corner_R": 0.8, "recess": 0.75, "border_bevel": 0.15, "border_band": 0.7,
                  "cells": "A 46.0 deg from vertical (down toward the rear) / 1.61 mm, B -49.0 deg / 1.72 mm"})
dp("trigger", "trigger_guard", dims={"blade_width_mid": 5.2, "tip_height": 1.3},
   construction="Curved blade re-traced from c1 / c6 inside the side trace: one concave flare from the slot, a "
                "slender blade tapering to a fine 1.3 mm tip, the top-front curving forward (hook); rolled rear edge "
                "0.4, rounded finger face.",
   note="trigger_guard round 2, then the integration round: slimmer lower blade, finer tip, more forward hook "
        "(round-2 judges on c1 and c6)")
dp("trigger_guard", "trigger_guard",
   construction="Stamped U loop lofted from a strip section (rolled outer edge 0.8, centre groove, open inner channel) "
                "on the traced outline (outer R 10 / 9.5, inner R 8 / 5.5); front leg straight up into the flange with "
                "a thin strap under a front tab from X 345.7; the mag catch housing cheeks reach the catch paddle's top "
                "(Z -53.87), the pin a flat round head on a washer.",
   note="trigger_guard round 2 as built; the side-view label convention (cheeks -> mag_catch label above Z -54.5) "
        "updated in rifle_silhouette.py")
dp("butt_plate", "butt_plate",
   dims={"end_outline": "c7 lozenge (two-sided power curve with a bow term, widest row at 40 % of the height), mapped on "
                        "the TOP width 36.9", "rim": "one rounded band 1.6 (3 segments) into the skirt",
         "face_crown": 0.6, "screw_head_dia": 7.0, "screw_head": "flat, flush (0.12 below the face), cut X slots 0.75 "
         "wide x 0.9 deep", "counterbore_ring": {"dia": 8.5, "countersink_deg": 45, "head_gap": 0.05}},
   construction="Steel plate over the butt end, c7's lozenge outline at the TOP width, face slightly convex (0.6 "
                "crown), wraparound skirt (the 12 mm side band); the face rolls into the skirt with one rounded band "
                "(no raised inner lip); two flush flat screw heads with cut X slots in 45 deg countersinks.",
   note="butt_plate rounds 1-2 as built; integration round: the round-2 raised lip removed (judge: an extra inner "
        "border), rim band 1.6 rounded, heads flat with a 0.05 gap (judge: 'domed bosses in a recessed ring'). "
        "BP-1 (stock end section) and BP-5 (plate width: c7 vs TOP) deferred: R41")
dp("magazine_ribs", "magazine",
   dims={"rib_half_widths": [1.55, 1.7, 1.7, 1.5], "rib_width": 3.25, "rib_proud": 1.0,
         "ends": "pressed ends tapering over 3x the half width", "bottom_ends_above_floor": 14.5,
         "front_rib_fraction": 0.76,
         "front_panel": "front panel 0.45 proud from u 0.745 forward (its crisp rear edge is the side view's 0.76 "
                        "line) plus a front spine fold 0.5 proud at u 0.905 (round 2: 0.9; 3/4 view), full length; a raised rear strip"},
   construction="Four flat-topped pressed ribs per side at u 0.17 / 0.34 / 0.51 / 0.66 (rounded shoulders, ~45 deg "
                "flanks, 1.0 proud), narrow, with tapered pressed ends; a front panel and a front spine fold instead of "
                "a narrow front rib; real geometry.",
   note="magazine round 2 as built; integration round: ribs narrower (x0.75), ends tapered, bottom ends 14.5 above the "
        "floor plate (inside the spec's 16 +- 2)")
dp("magazine_top_plates", "magazine",
   box={"Z": [-36.0, -13.5], "X_at_Z-25": [372.2, 414.5], "Y": [-13.3, 13.3]},
   dims={"Z_seated": [-36.0, -13.5], "width_fraction_from_rear_edge": [0.05, 0.735], "proud": 0.9,
         "neck": "the body narrows to 12.4 per side above a line just under the plate, so the plate and front block "
                 "stand 0.9 proud yet end at Y 13.3 inside the 13.5 well liner"},
   note="magazine round 2 as built")
dp("magazine_floor_plate", "magazine",
   dims={"thickness": 5.0, "rear_bottom_corner_R": 3.5, "floor_line_offset_outward": 0.86, "front_turn_up": 3.0,
         "bottom_step": "1.0 out over the front 55 %", "rim": "folded rim 1.9 / +0.5 over a narrower lower part",
         "bottom_panel": "recessed panel with a detent button"},
   note="magazine round 2 as built (lowest point kept at -183.224); Base socket moved 1.4 mm outward along the normal")
dp("dust_cover", "receiver_right",
   dims={"skirt_vertical_to_Z": 21.2, "crease_Z": 22.2, "crease_depth": 1.3, "crown": "elliptical, half width 21.5, "
         "rise 10.7, to Z 32.7", "studs": {"X": [271.0, 311.0, 373.0, 422.0], "dia": 4.8, "proud": [1.0, 1.2]},
         "skirt_cutout_top_Z_built": 19.2},
   construction="Stamped cover: vertical skirts to Z 21.2, a deep lengthwise crease at Z 22.2, an elliptical crown to "
                "Z 32.7; four domed studs on the crown centre line; rear end as traced; the right skirt cut out over "
                "the port (top Z 19.2, held by the L3 port-corner gate; 21.5 proposed: open question).",
   note="receiver_right round 2 as built")
dp("bolt_carrier", "receiver_right",
   dims={"charging_handle": {"X": [444.0, 458.0], "Z": [8.0, 17.0], "tip_Y": -35.2, "stem_Z": [8.6, 11.85]},
         "flank_flat_to_Z": 20.0, "flank_recess": {"below_Z": 9.5, "floor_Y": -8.5, "X": [345.0, 443.0]}},
   note="receiver_right round 2 as built; integration round: recess floor at Y -8.5 (was -4.0: it opened into the "
        "chamber pocket and showed the barrel through the port)")
dp("receiver", "receiver_right",
   dims={"rivet_head": "flat-topped button 5.1 dia, 1.0 proud (the selector sweep limits the height)",
         "rivet_350_-25": "a wire retainer clip whose eye sits at (350, -25) (c1), not a rivet; L3 reads 'rivet or clip eye'"},
   feature={"name": "teardrop_cutout_right", "XZ_top_centre": [372.0, 1.8], "size": [9.5, 9.1],
            "construction": "through cutout 1.3 inside a 0.6 deep pressed rim (c1)"},
   note="receiver_right rounds 1-2 as built; side dimple kept at the spec centre (L3)")
# ------------------------------------------------------------------------------- detail pass round 2b (2026-10-05)
# Second detail loop (r2b): every builder re-ran its round 2 on the integrated build; the proposals' round-2b blocks are
# applied here as built. Deferred items stay in R36 / R40 / R41 / R43 (open_questions). R45 lists what changed.
DP2 = "review/detail/{}/spec_proposal.json (round 2b)"


def dp2(pid, src, **kw):
    dp(pid, src, **kw)
    _P[pid]["detail_pass"][-1]["source"] = DP2.format(src)
    for k in [k for k, v in _P[pid]["dims"].items() if v is None]:      # None = superseded key: drop it
        del _P[pid]["dims"][k]


dp2("selector", "selector",
    dims={"plate_thickness": "2.0 main plate on a 0.9 skirt (outline step 1.1 wide)", "washer_collar_dia": 10.64,
          "washer_proud": 1.2, "head_dia": 7.6, "head_height": 1.84, "head": "domed bolt head on a straight skirt, no slot (R47)",
          "rib": {"proud": 0.20, "front_scale": 0.55, "flanks_deg": [15, 33]},
          "nose_pin": {"ring_r": 2.2, "ring_proud": 0.24, "pin_r": 0.68}, "edge_bevel": 0.20},
    construction="One solid 2.0 mm stamped plate: the c1-traced outer outline inset 1.1 mm at full thickness on a 0.9 "
                 "mm skirt filling the outer outline (c1's outer line, dark band and inner line); a low rounded rib "
                 "(0.20 proud) along c1's crease whose upward flank is the bright band, the wedge above it a solid face "
                 "rising to the top edge (no lip). Nose tab a true semicircle round the pin, full thickness, bent out 12 "
                 "deg, a thin raised ring round a small flat pin. Pivot: raised washer collar r 5.32 x 1.2 with a crisp "
                 "shoulder and a domed bolt head r 3.80 x 1.84 (no slot; R47). 0.20 mm crisp bevels on plate and skirt. No markings.",
    note="selector r2b (second loop) as built; supersedes the integration round's valley pocket / centre boss")
dp2("trigger", "trigger_guard",
    dims={"blade": "profiled extrusion: 0.8 mm concave finger face with 0.15 edge breaks round the tip, 0.45 rear roll",
          "tip_width": 2.0, "c1_rows_scale_Z": 0.914},
    construction="Trigger re-traced from c1's rows scaled into the side opening (x0.914 in Z): broad sloped shoulder, "
                 "crisp knee, blunt ~2 mm tip; built as a profiled extrusion (concave finger face, edge breaks carried "
                 "round the tip, rolled rear edge) instead of bevel-modifier rounds.",
    note="trigger_guard r2b: side L2 trigger IoU 0.895 -> 0.946")
dp2("trigger_guard", "trigger_guard",
    dims={"loop_section": "two rounded beads either side of a V groove", "corner_segments": 8,
          "inner_R": {"rear": 6.0, "front": 8.0}, "outer_R_front": 11.0, "bottom_bar_extra_depth": 0.3,
          "catch_tab_full_width_to_Z": -33.2},
    construction="Stamped U loop lofted from a strip section (two rounded beads either side of a V groove, 8-segment "
                 "corners) on the traced outline (inner R rear 6 / front 8 as c1, outer front R 11); front leg into the "
                 "flange with a thin front tab full width down to Z -33.2, recessed below; catch housing cheeks to the "
                 "paddle top (Z -53.87), pin heads r 1.7 set low (0.14 proud, no washer; R47).",
    note="trigger_guard r2b as built (inner radii were swapped in round 2)")
dp2("front_sight_ears_post", "front_sight",
    dims={"ear_thickness": 4.8, "ear_outer_face_Y": 10.0, "ear_inner_gap": 10.4, "drum_dia": 4.0,
          "ear_rims": "R 2.0 outer faces, R 1.4 inner, R 1.1 window floor / ear-to-floor fillets, down to Z 8.0; top "
                      "corners R 4.0, rear knee R 8.0 (2 bevel segments)",
          "window": {"X": [813.4, 827.2], "Z": [12.2, 21.8], "shape": "rounded trapezoid, larger corner radii, rolled "
                     "rim"},
          "top_hole": {"XZ": [824.7, 29.9], "boss_dia": 8.4, "hole_dia": 0.0, "rim_proud": 0.62, "rim_width": 0.4,
                       "face_proud": 0.45, "scribed_groove": "0.45 wide x 0.3 deep, longer sagging curve"},
          "inner_faces": "blind hole dia 4.8 x 2.0 deep at (829.4, 43.4), round-ended slot 2.4 x 7.0 x 1.4 deep, drum "
                         "counterbore r 2.4 x 0.9"},
    construction="Two thick ears (4.8) cast in one with the base, landing 1.0 inside the base flanks (a ledge, R47), every "
                 "outline and window edge rolled; rounded trapezoid window; raised boss plug (dia 8.4, R47) with a ring "
                 "rim and a scribed curve on the outer faces; blind hole and slot on the inner faces; windage drum r 2.0 "
                 "carrying the post.",
    note="front_sight r2b as built; ear proportion (c3 ~0.75 as wide) still deferred: R36")
dp2("front_sight_block", "front_sight",
    dims={"base_section": "superellipse, exponent 3.5 above Z 0.5, 2.4 below",
          "cross_pin_heads": {"dia": 5.2, "proud": 0.42, "head": "flat, square to the flank"},
          "rod_lug": "one rounded body X 809.9-830.2 (half width 3.6, bottom Z -15.7, corners R 2.5), notch X "
                     "830.9-832.5, round rod-end knob X 833.1-837.5"},
    construction="Cast block: a loft of superellipse sections X 806.1-837.0 (|Y| 11.0, Z -10.3..11.3; square on top "
                 "where the ears land, round below), rear rim R 2.2, front shoulder R 1.6; ring collar r 9.7 (X "
                 "836.6-839.6) then a narrow collar r 8.7 to X 848.78; cross pin dia 4.0 at X 830.5 Z -5.0 with flat "
                 "heads dia 5.2, 0.42 proud; a rounded cleaning-rod lug with a notch and a round rod-end knob.",
    note="front_sight r2b as built")
dp2("muzzle_brake", "muzzle_brake", box={"X": [848.82, 880.0], "Z": [-10.1, 11.0], "Y": [-10.1, 10.1]},
    dims={"shank_r": 8.7, "shank_X": [848.82, 853.0], "step_groove": {"width": 0.75, "depth": 0.32},
          "body_r": [10.0, 10.1], "body_X": [853.0, 867.0], "face_angle_deg": 37.5, "cut_X_at_Z0": 872.786,
          "chamber_r": 6.4, "chamber_inner_round": 0.6, "chamber_floor_X": 858.5, "slot_side": "right (-Y) only", "slot_Z": [-7.7, 6.8],
          "slot_outline": "parts/muzzle_brake.py SLOT_TRACE (closed spline back-projected from c3's edges)",
          "slot_edge_round": 0.4, "rim_ring": None,
          "detent_block": {"X": [847.2, 853.4], "top_Z": 11.0, "Y": [-2.3, 2.3], "pin_XZ": [850.2, 9.95]},
          "flare": None, "knob": None},
    construction="One turned part: rear shank r 8.7 (X 848.82-853.0, the FSB collar's radius) ending in a groove (0.75 "
                 "x 0.32) and a step up to a straight body r 10.0 -> 10.1. The front is cut by one plane 37.5 deg from "
                 "vertical (X 872.786 at Z 0) removing the top front: a flat face band with small rounds round a plain "
                 "chamber r 6.4 (R47) (floor X 858.5). ONE slot through the right (-Y) wall, a closed spline through c3's own "
                 "edges (round top Z 6.8, upright rear edge into a long rounded diagonal, flat floor Z -7.7, front edge "
                 "leaning with the rim, ~1.4 web at the top), outer edge rounded 0.4. A rounded detent block straddles "
                 "the junction with transverse pin ends. Body measured without the block: length 31.2, dia 20.2 (L4).",
    note="muzzle_brake r2b as built: the integration round's raised rim ring and flared body are gone (R45)")
dp2("rear_sight_leaf", "rear_sight",
    dims={"rail_top_Z": 44.7,
          "teeth": {"count_per_rail": 11, "pitch": 2.8, "depth": 1.5,
                    "form": "sawtooth V-grooves across a 2.6 mm strip along each rail's OUTER edge"},
          "centre_slot": {"width": 5.6, "X": [466.8, 497.8], "through": True},
          "notch_block": {"width": 20.0, "lobes": 2, "notch_width": 2.0, "notch_bottom_Z": 45.5,
                          "shoulders": "inner +-7.2 to Z 48.0, outer to 46.7", "bottom_Z": 41.2, "front_X": 452.4}},
    construction="Ladder leaf: base plate 17 wide with two flat-topped rails (top 44.7) split by a through centre slot "
                 "5.6 wide; ratchet teeth = 11 sawtooth V-grooves (pitch 2.8, 1.5 deep) along each rail's outer edge; "
                 "rear notch block as wide as the slider (20) with two lobes either side of the 2.0 U notch and stepped "
                 "shoulders, wrapping down over the leaf to the slider skirt (0.2 gap). No numerals or tick marks.",
    note="rear_sight r2b as built")
dp2("rear_sight_block", "rear_sight",
    dims={"deck_half_width": 13.0,
          "shoulder_band": "half elliptical roll / half chamfer behind a 0.9 ledge along the side face's top S-edge",
          "housing_front_corner_R": 4.0, "rear_corner_R": 3.5,
          "slot": "short upright slot 1.2 wide down to Z 36.0 (replaces the slanted slot)"},
    construction="Contoured casting: the side face stops at a swooping S top edge with a 0.9 mm ledge, above it a "
                 "rolled band to a deck +-13; the front housing's vertical corners rounded R 4 and its top-front corner "
                 "an arc (the rounded hood); rear vertical corners R 3.5 and a rounded rear lip; transverse rounded bar "
                 "r 3.3 at X 510.8; two domed screw heads; a short upright slot down to Z 36.0; the slider in a stepped "
                 "pocket.",
    note="rear_sight r2b as built")
dp2("handguard_retainer_lever", "rear_sight",
    dims={"boss_r": 3.9, "end_r": 3.5, "slot_r": 1.65, "slot_span": [0.27, 0.8], "pin_collar_r": 3.6,
          "angle_XZ_deg": 45.0},
    note="rear_sight r2b: link broadened (the 3/4 view draws it ~1.5x wider); position and angle kept (side view)")
dp2("dust_cover", "receiver_right",
    dims={"skirt_bottom_Z_ahead_of_step": 9.6,
          "skirt_cutout": "lifted to Z 12.3 at X 334-337, rising to Z 19.2 at X 372-378.5"},
    note="receiver_right r2b as built; cutout top 19.2 (21.5 still R40)")
dp2("receiver", "receiver_right",
    dims={"rivet_head": "low dome 5.1 dia, 1.0 proud (10 segments right, 8 left)",
          "pin_right_head": "hollow ring r 0.95-1.75, 0.45 proud (R47; r2b had a dome)", "side_dimple_right_depth": 1.5,
          "retainer_clip": "hairpin wire loop ~11.6 x 2.6 with its eye at (350, -25)",
          "rear_vertical_edges_R": 1.5},
    feature={"name": "ejection_port_rear_band", "X": ["skirt step line", 336.5], "Z": [3.0, 9.2],
             "construction": "the visible slot starts at the cover's skirt step as a low band (wall top cut to Z 9.2 "
                             "under the 9.6 skirt edge) above the selector lever's top edge; full-height port from X "
                             "336.5"},
    note="receiver_right r2b as built; the teardrop cutout's top centre moves to (372, 2.3) with a 0.9 lip and a dark "
         "interior (carrier recess to its bottom, right rail gap X 361-383)")
for f in _P["receiver"]["features"]:
    if f.get("name") == "teardrop_cutout_right":
        f.update({"XZ_top_centre": [372.0, 2.3], "lip": 0.9, "interior": "dark: carrier recess to its bottom"})
dp2("pistol_grip", "grip",
    dims={"strap_R_front": 9.0, "strap_R_back": 9.0, "strap_R_front_on_block": 7.0, "side_crown": 1.2,
          "heel_fillet_R": 8.0, "top_rim_round": 1.2,
          "base": {"flare_per_side": 2.0, "flare_height": 12.0, "roll_under_R": 5.0, "roll_segments": 7,
                   "cap": "flat", "note": "lofted rings turning to the bottom line below Z -92.8 (no bottom boolean)"},
          "bottom_round": None},
    construction="Wood grip on the traced side profile reshaped to c6 (grip_shape.py), section a rounded oblong 31.5 "
                 "wide with rounder sides (crown 1.2), straps R 9 (R 7 on the top block); the base is lofted: the "
                 "rings turn parallel to the bottom line, flare 2.0 per side over the last 12 mm and roll under on a "
                 "5 mm quarter circle to a flat cap; heel fillet R 8; top rim rounded 1.2 under the receiver. Checkered "
                 "panel per side (features.checker_panel), border real geometry; cells a normal map baked from "
                 "modelled gable-crested ridges sitting 0.25 below the border; the recess wall rounded 0.4 (2 segments) and a 0.35 band (R47).",
    note="grip r2b as built: H1 girth 124.7")
for f in _P["pistol_grip"]["features"]:
    if f.get("name") == "checker_panel":
        f.update({"cells": "A 46.0 deg / 1.61 mm gable-crested ridges (profile 0 / 0.72 / 1.0 / 0.72 at 0 / 0.1 / 0.5 "
                           "/ 0.9 of the pitch), crowns 0.50 above the recess floor (0.25 under the border); B -49.0 "
                           "deg / 1.72 mm shallow notches to 0.43"})
dp2("magazine_top_plates", "magazine",
    box={"Z": [-36.8, -12.4], "Y": [-13.3, 13.3]},
    dims={"Z_seated": [-36.8, -12.4],
          "proud": {"centre": 1.3, "corners": 0.8, "form": "domed cap rounding over toward the lip curl, edges "
                    "rounded 0.75"},
          "neck": "body necked to 12.0 per side, neck line 0.35 under the plate with a steep 0.6-tall chamfer"},
    note="magazine r2b as built")
dp2("magazine_ribs", "magazine",
    dims={"rib_half_widths": [1.3, 1.4, 1.4, 1.25], "ends": "round (U) pressed ends, crest fading over 3.0 mm", "bottom_ends_above_floor": 14.0,
          "top_tips": "1.35 under the plate's lower edge (L3 reading -39.19)",
          "front_bead": {"u": 0.915, "half_width": 1.35, "proud_over_panel": 0.5, "Z_top": -38.6}},
    note="magazine r2b as built: the front spine fold is now a raised bead")
dp2("magazine_floor_plate", "magazine",
    dims={"bottom_rear_swell": "0.55 out over 9 mm from the rear corner, then a 0.45 step to the 1.0 level"},
    note="magazine r2b as built (L2 0.9688); band spot welds removed (budget)")
dp2("magazine_lugs", "magazine",
    dims={"front_knobs": "two rounded pin heads r 1.3 at Z -19.6 / -23.6 standing to Y +-13.25 (inside the reload "
                         "envelope)",
          "rear_lug_built": "rounded block from X 368.55, Z -39.6..-36.4, Y +-5.5, under the guard tang, 0.26 in front "
                            "of the catch at rest"},
    note="magazine r2b as built; the higher c4 rear knob and the chunky front lug still need the liner changes (R43)")
dp2("butt_plate", "butt_plate",
    dims={"end_outline": "c7's end shapes fitted at the plate's own width (distance from the tip and half width in "
                         "plate widths, END_FIT concave model); section sampled densely, simplified at 0.05 mm",
          "heel_top_raise": 0.75, "face_crown": 0.25,
          "screw_head": "flat, 7.0 dia, 0.5 slots at angles re-measured on c7",
          "counterbore_ring": {"dia": 8.5, "form": "straight counterbore, 3.5 deep (no countersink)"}},
    note="butt_plate r2b as built; width (BP-5) and the stock end section (BP-1) still R41")
# magazine Base socket: the round-2 floor plate steps out 1.0 over its front half and its floor line sits 0.86 outward
MAG_BASE_SOCK = MAG_BASE + 1.4 * FLOOR_NORMAL

# ================================================================================================== sockets
GM = [GX, 0.0, GZ]
SH_X = round((lh["X"][0] + lh["X"][1]) / 2, 1)
SH_Z = round(cross_z(rings(None, "handguard_lower"), SH_X)[0], 1)          # underside of the lower handguard
rifle_sockets = [
    sock("Grip", "body", GM, use=f"origin; attach to the character's weapon_r ({GRIP_DEPTH:g} mm down the grip axis, set from the fit body's hand in form fix round 1; the posed H1 at the rig stage records hand_offset)",
         src=f"computed: grip axis midline + {GRIP_DEPTH:g} mm from the junction (H1 early: palm centre projected on the knuckle line)"),
    sock("SupportHand", "body", [SH_X, 0.0, SH_Z], use="hand_l two-bone IK target. PROVISIONAL: H1 replaces it with the "
         "measured hand_l bone frame in the support-hand pose (off-axis, left of and below the handguard, with rotation); "
         "until then it sits ON the handguard underside (no hand-in-wood) and the sidecar records the hand offset",
         src="lower handguard centre X; Z = the traced underside there", plan_name="OffHand"),
    sock("Trigger", "trigger", [float(TRIGGER_FACE[0]), 0.0, float(TRIGGER_FACE[1])], use="index finger target",
         src="trace: trigger front-face concavity"),
    sock("Muzzle", "muzzle_device", [round(MUZZLE_X, 2), 0.0, 0.0], use="flash, smoke, tracer; +X out of the bore",
         src="bore axis x brake cut plane"),
    sock("MuzzleSeat", "body", [D["barrel"]["muzzle_end_X"]["mm"], 0.0, 0.0], use="device / suppressor seat",
         src="brake rear face = barrel shoulder"),
    sock("Sight", "sight_rear", [round(NOTCH_X, 2), 0.0, NOTCH_TOP_Z],
         rot={"roll": 0.0, "pitch": round(EYE_PITCH, 4), "yaw": 0.0},
         use="ADS: at the notch TOP centre (level with the shoulders), +X through the front post tip: the eye on this "
             "line sees the post tip level with the notch top and centred in it (gate B4); eye relief is game data "
             "(0.25 m standard)",
         src=f"R48: notch top Z = leaf top {NOTCH_TOP_Z}; post tip at X {POST_X}, Z {POST_Z}",
         plan_name="ADS (+SightRear; SightFront dropped)"),
    sock("Mag", "magazine", [float(HOOK[0]), 0.0, float(HOOK[1])], use="SM_AR01_Mag attaches here with zero relative transform",
         src="front-lug hook point (provisional +-5 mm; the fit stage sets it)", plan_name="MagWell"),
    sock("MagRockStart", "body", [float(HOOK[0]), 0.0, float(HOOK[1])], rot={"roll": 0.0, "pitch": ROCK, "yaw": 0.0},
         use="start of the rock (lug hooked); pure rotation about the lug to Mag", src="plan 2.3; angle set by the fit stage"),
    sock("MagInsertStart", "body", [round(float(INSERT[0]), 2), 0.0, round(float(INSERT[1]), 2)],
         rot={"roll": 0.0, "pitch": ROCK, "yaw": 0.0}, use="before the lug enters its recess (8 mm along the tilted -Z)",
         src="plan 2.3"),
    sock("ShellEject", "body", [395.0, -HALF_W, 10.0], rot={"roll": 0.0, "pitch": 20.0, "yaw": 80.0},
         use="casing spawn; +X = throw direction (right, slightly forward and up). On body, not bolt: on the bolt it "
         "would travel 100 mm back into the receiver (X 295, behind the port's rear wall at 338) mid-cycle",
         src="port centre", plan_name="EjectPort"),
    sock("ChargingHandle", "bolt", [451.0, -30.0, 16.5], use="hand target for the charge; travel along -X", src="handle tab"),
    sock("Selector", "selector", [351.0, -(HALF_W + 3.0), 4.0], use="thumb target on the lever tab", src="lever face outline"),
    sock("MagRelease", "mag_release", [362.0, 0.0, -66.0], use="finger target on the catch tab", src="trace"),
    sock("Shoulder", "body", [float(BUTT_C[0]), 0.0, float(BUTT_C[1])], rot={"roll": 0.0, "pitch": round(BUTT_TILT, 3), "yaw": 0.0},
         use="butt plate centre, +X = plate normal reversed (TP aim offsets)", src="trace: butt plate rear face"),
    sock("SlingRear", "body", [round(sum(D["sling_swivel_rear"]["X"]) / 2, 2), 0.0, round(sum(D["sling_swivel_rear"]["Z"]) / 2, 2)],
         use="sling / back carry", src="trace: swivel centre"),
    sock("CenterOfMass", "body", [420.0, 0.0, -10.0], use="physics CoM offset (README); COMPUTED by the build",
         src="nominal estimate; the build computes it from part volumes x densities, scaled to 3.1 kg"),
    sock("Holster", "body", [420.0, 0.0, -10.0], use="stowed hang point; = CenterOfMass until the game sets it",
         src="gun study 5.3 / 11.4"),
]
mag_sockets = [
    msock("Mag", [float(HOOK[0]), 0.0, float(HOOK[1])], use="origin = front-lug hook = the rifle's Mag socket when seated",
          src="hook point", plan_name="Attach"),
    msock("HandReload", [round(float(MAG_MID[0]), 2), MAG_T / 2, round(float(MAG_MID[1]), 2)],
          use="left palm on the body (left face); hand_l relative = inverse", src="mid-arc point on the left face"),
    msock("Feed", [round((MAG["X"][0] + HOOK[0]) / 2, 2), 0.0, HOOK_Z + 4.0], use="top centre of the lips", src="lips top"),
    msock("Base", [round(float(MAG_BASE_SOCK[0]), 2), 0.0, round(float(MAG_BASE_SOCK[1]), 2)],
          rot={"roll": 0.0, "pitch": round(math.degrees(math.atan2(FLOOR_NORMAL[1], FLOOR_NORMAL[0])), 3), "yaw": 0.0},
          use="floor plate centre, +X = outward normal; impact FX / ground contact", src="floor plate corners from the trace, 1.4 mm out along the normal (detail-pass floor plate, R42)"),
    msock("CenterOfMass", [round(float(MAG_MID[0]), 2), 0.0, round(float(MAG_MID[1]), 2)],
          use="physics CoM (empty); COMPUTED by the build", src="nominal = mid-arc"),
]

# ================================================================================================== spec
spec = {
    "meta": {
        "name": "Assault Rifle AR-01", "code": "AR01", "version": "1.2", "date": "2026-10-05",
        "assets": {"skeletal": "SK_AR01 (+ _LOD1..3, SK_AR01_Skeleton, PHYS_AR01, clips A_AR01_*)",
                   "static_twin": "SM_AR01 (mag merged by default, gun study Q3)", "magazine": "SM_AR01_Mag"},
        "units": "millimetres (Blender builds in metres: / 1000; Unreal cm: / 10)",
        "authority": "This file + RIFLE_DESIGN_SHEET.png are the build reference. Every builder, measurer and fit script "
                     "reads numbers from here; nothing nominal remains except the values flagged 'provisional' (set by "
                     "the named stage) and 'computed' (by the build).",
        "generator": "WorkFiles/guns/rifle/tools/make_spec.py (re-run after any change to the trace or a decision)",
        "inputs": ["rifle_measured.json", "trace/LEFT_outline.json", "trace/RIGHT_outline.json", "trace/TOP_outline.json",
                   "craft_parts.json", "CRAFT_STUDY.md", "rifle_interface.json", "RIFLE_BUILD_PLAN.md",
                   "GUN_BUILDING_STUDY.md (repo root, line standard rev 2)"],
        "ip": "Generic names only (no real-pattern or maker names in any asset name or buyer text); no logos, stamps, "
              "serials, numerals, selector letters or leaf graduations. The game build matches the sheet; Fab design "
              "deltas are listed in fab_original_changes and are NOT applied.",
        "reference": "References/Guns/Rifle/rifle_sheetAB.webp (1536x1024, AI-generated by the user)",
    },
    "sheet_panels": {
        "LEFT-labelled (top-left, muzzle right)": "TRUE RIGHT side: selector, ejection port, carrier, charging handle and "
            "retainer lever as on the real pattern. Authority for all X/Z dimensions and right-side features.",
        "RIGHT-labelled (top-right, muzzle left)": "TRUE LEFT side (plain dust cover, no port) but it ALSO draws the selector "
            "lever (generator copy) and an extra pressed groove ahead of the dimple. Cross-check only; source of left-side "
            "features. Its middle section is drawn 12-16 mm further forward.",
        "TOP": "from above, muzzle right, image-up = gun left; authority for widths only; its side bumps (a plate on the left "
               "at X 353-462) are not real; the right-side knob at X 470-482 is the charging handle drawn 25 mm too far forward.",
        "3/4 FRONT RIGHT": "correct as labelled (front-right: muzzle right and near).",
        "c1 RECEIVER AND SELECTOR (RIGHT)": "correct (true right).",
        "c2 DUST COVER AND REAR SIGHT (TOP LEFT)": "surface detail.",
        "c3 FRONT SIGHT AND MUZZLE (SIDE)": "surface detail, right side.",
        "c4 MAGAZINE (LEFT)": "correct (true left: front edge on the left); mirror it to compare with the side view.",
        "c5 MAGAZINE (FRONT)": "front spine (centre channel, two raised lines). Thickness NOT measurable here (reads ~18-20; R5).",
        "c6 PISTOL GRIP AND TRIGGER (LEFT)": "correct (true left); its checker panel agrees with c1 once mirrored.",
        "c7 BUTT PLATE (END)": "plate shape and cross-slotted screws in counterbore rings; not to scale (wood drawn beside the plate, unlike TOP).",
        "note": "The measurement and craft notes called the LEFT-labelled panel the gun's left and read the controls as "
                "'mirrored onto the left'. Handed features prove it is the right side; the tech plan and the gun study "
                "say the same. Only the selector copy (and groove) on the true-left panel is a generator fault.",
    },
    "frames": {
        "M": {"name": "measurement / spec frame (all part dimensions in this file)",
              "axes": "+X toward the muzzle along the bore, +Z up, +Y = gun LEFT (right-handed)",
              "origin": "X = 0 at the rearmost point of the butt plate; Z = 0 on the bore axis; Y = 0 on the mid-plane",
              "scale": "LEFT-labelled panel at 0.82248 px/mm (1.2158 mm/px), overall length 880.0 set by us"},
        "B": {"name": "Blender build frame (gun study 5.1)", "axes": "+X muzzle, +Z up, -Y = gun RIGHT (same axes as M)",
              "origin": "Grip", "Grip_in_M": r1([GX, 0.0, GZ], 3), "transform": "B = M - Grip_in_M (pure translation)",
              "bore_axis_in_B": f"Y = 0, Z = {round(-GZ, 3)} (parallel to X)",
              "blender_front_view": "from -Y shows the right side, muzzle to screen right = the LEFT-labelled panel"},
        "unreal": {"mapping": "Unreal cm = (Bx, -By, Bz) / 10 (helpers.ue_socket_transform / ue_component_transform)",
                   "axes": "+X forward, +Y right, +Z up"},
        "mag": {"origin": "front-lug hook point", "axes": "identical to the rifle's Mag socket frame when seated",
                "transform_from_M_seated": f"mag = M - ({HOOK[0]}, 0, {HOOK[1]})"},
    },
    "scale": {
        "overall_length": 880.0, "barrel_length": 415.0, "mass_kg": {"rifle_no_mag": 3.1, "mag_empty": 0.33, "mag_loaded_30": 0.82},
        "why": "real fixed-stock stamped-receiver 7.62x39 pattern and the prompt; at 880 the sheet's sight radius is 368.5 "
               "(real ~378, -2.5 %) and receiver face to muzzle 363.5 (fits 415 with 51.5 in the trunnion). Ruler unusable "
               "(labels 0..90 then '90' again; implies 108.5 or 97.7 cm).",
        "uncertainty": "+-1.5 % global (scale choice) on top of each measurement's own +-",
        "length_of_pull": round(float(TRIGGER_FACE[0] - BUTT_C[0]), 1),
        "length_of_pull_note": "short vs the real ~340-350: the sheet draws a slightly short stock; kept as drawn",
    },
    "key_dimensions": {
        "overall_length": 880.0, "overall_height_with_mag": D["overall"]["height_with_magazine"]["mm"],
        "overall_height_without_mag": D["overall"]["height_without_magazine"]["mm"],
        "barrel_length": 415.0, "barrel_exposed_from_receiver_face": D["barrel"]["receiver_face_to_muzzle"]["mm"],
        "barrel_dia": BARREL_D, "bore_dia": 7.62,
        "receiver_length": rec["length"]["mm"], "receiver_width_walls": W_RECEIVER, "dust_cover_width": W_COVER,
        "receiver_bottom_Z": rec["bottom_Z"]["mm"], "dust_cover_crown_Z": round(CROWN_Z, 1),
        "receiver_height_incl_cover": round(CROWN_Z - rec["bottom_Z"]["mm"], 1),
        "rear_sight_leaf_top_Z": rs["leaf_top_Z"]["mm"], "front_sight_ear_top_Z": fsb["hood_top_Z"]["mm"],
        "sight_line": {"notch_M": [round(NOTCH_X, 2), 0.0, NOTCH_Z], "post_tip_M": [POST_X, 0.0, POST_Z],
                       "radius": round(POST_X - NOTCH_X, 1), "pitch_deg": round(SIGHT_PITCH, 4),
                       "height_above_bore_at_notch": NOTCH_Z,
                       "eye_line": {"from_M": [round(NOTCH_X, 2), 0.0, NOTCH_TOP_Z], "to_M": [POST_X, 0.0, POST_Z],
                                    "pitch_deg": round(EYE_PITCH, 4),
                                    "note": "R48: the Sight socket's line (notch top centre -> post tip)"}},
        "grip": {"origin_M": r1([GX, 0.0, GZ], 2), "axis_rake_deg": round(GRIP_RAKE, 2), "bottom_Z": pg["Z"][0]},
        "stock_length": st["length_butt_to_receiver"]["mm"], "butt_height": bpl["height"]["mm"], "butt_width": TV["butt_plate_width"]["mm"],
        "handguard_lower_length": lh["length"]["mm"], "handguard_upper_length": round(UPPER_HG_X[1] - UPPER_HG_X[0], 1),
        "magazine": {"R_front": R_IN, "R_rear": R_OUT, "width": MAG["width_front_to_rear_radial"]["mm"], "thickness": MAG_T,
                     "arc_length": MAG["length_along_centre_arc"]["mm"], "bottom_Z": D["overall"]["bottom_Z_with_mag"]["mm"],
                     "bottom_Z_note": "from the traced SILHOUETTE (lowest point -183.224), like the overall height; the separately traced magazine ring reads the same edge at -183.376 (0.13 px lower), which round 0 used (R30)"},
        "muzzle_brake": {"length": BR["length"]["mm"], "dia": TV["muzzle_brake_width"]["mm"],
                         "cut_deg": BR["front_face_angle_from_vertical_deg"]},
    },
    "stations_X": {
        "butt_plate_rear (heel)": 0.0, "stock_wood_rear": st["X_wood"][0], "sling_swivel_rear": 72.6,
        "comb_nose": st["comb_nose"]["X"], "wrist_low": st["wrist_low_point"]["X"], "receiver_rear (trunnion)": rec["X"][0],
        "dust_cover_rear": dc["X"][0], "grip_top_front": pg["X"][1], "selector_pivot": 282.8, "trigger_face": round(float(TRIGGER_FACE[0]), 1),
        "ejection_port": [338.0, 452.0], "mag_catch": D["mag_catch"]["X"], "magazine_top": [MAG["X"][0], 428.4],
        "chamber_face": 433.8, "dust_cover_front": dc["X"][1], "rear_sight_block": RS_BLOCK_X, "rear_leaf_rear_end": rs["block_X"][0],
        "rear_notch": round(NOTCH_X, 1),
        "receiver_front_face": rec["X"][1], "lower_handguard": lh["X"], "upper_handguard": UPPER_HG_X,
        "front_band": D["handguard_front_band"]["X"], "gas_block": gb["X"], "front_sight_block": fsb["X"],
        "front_post": POST_X, "barrel_crown / brake rear": D["barrel"]["muzzle_end_X"]["mm"], "muzzle": 880.0,
    },
    "parts": parts,
    "fastener_rule": "count and position from the sheet (lists in each part); sizes from norms when the head spans < 4 "
                     "sheet px (rivets 4.5 dia domed 1.0 proud, pins 3.5, screws 6-7 heads), recorded with the source; "
                     "random slot clocking; no 'M'+number size notation",
    "bones": {
        "root": "armature object at Grip, identity (no bone named root)",
        "table": [
            {"bone": "body", "parent": None, "parts": "all fixed parts", "head_M": r1([GX, 0, GZ], 2)},
            {"bone": "bolt", "parent": "body", "parts": "bolt_carrier (+ charging handle)", "motion": "translate -X, 100 mm nominal"},
            {"bone": "trigger", "parent": "body", "head_M": [318.0, 0.0, -20.0], "motion": "rotate about Y, 0-12 deg"},
            {"bone": "selector", "parent": "body", "head_M": [282.8, -(HALF_W + 1.5), -7.8], "motion": "rotate about Y (transverse pin), 0/16/32 deg"},
            {"bone": "mag_release", "parent": "body", "head_M": [362.0, 0.0, -50.0], "motion": "rotate about Y, 0-10 deg"},
            {"bone": "magazine", "parent": "body", "head_M": r1([HOOK[0], 0, HOOK[1]], 2), "motion": "attach only, no weighted vertices"},
            {"bone": "sight_rear", "parent": "body", "head_M": [504.0, 0.0, 41.0], "motion": "rotate about Y, 0-6 deg"},
            {"bone": "muzzle_device", "parent": "body", "head_M": [D["barrel"]["muzzle_end_X"]["mm"], 0.0, 0.0], "motion": "none (hide)"},
        ],
        "count": 8,
        "note": "rest rotation = root's; GUN_BUILDING_STUDY 5.2 says 'a selector turns about X on every gun', but this "
                "lever (and an AR selector) pivots on a transverse pin: about Y. Flagged to the gun-study owner.",
    },
    "sockets": {
        "standard": "GUN_BUILDING_STUDY 5.3 names (plan names kept as plan_name); positions computed from the trace",
        "rifle": rifle_sockets, "mag": mag_sockets,
        "omitted": {"SlingFront": "not shown on the sheet (gas block left side shows no loop)",
                    "Rail_*": "no rail on the game rifle (Fab delta only)", "Stock": "fixed stock"},
        "gates": {"B4": "Muzzle on the bore <= 0.5 mm / 0.05 deg; sight picture at 55 deg ADS FOV, eye 0.25 m behind Sight on "
                        "its line, 2560x1440, occlusion-aware: the post tip level with the notch top and centred in "
                        "the notch within 0.2 mm (both axes, at the notch), the post visible in the notch (R48)", "B5": "sidecar = build within 0.001 mm / 0.001 deg"},
    },
    "materials": {
        "finishes": {
            F_LAC: {"metallic": 0, "base_srgb": "#353535", "base_linear": 0.036, "roughness": [0.40, 0.55],
                    "wears_to": "bare_steel in sharp chips", "parts": "receiver, cover, sights, barrel, gas parts, FSB, brake, guard, bands"},
            F_BLUE: {"metallic": 1, "base_srgb": "#787878", "base_linear": 0.19, "roughness": [0.30, 0.55],
                     "parts": "carrier, selector, trigger, catch, leaf, retainer lever, rod, swivel, pins"},
            F_MAG: {"metallic": 0, "base_srgb": "#313131", "base_linear": 0.031, "roughness": [0.45, 0.60]},
            F_BUTT: {"metallic": 0, "base_srgb": "#3F3F3F", "base_linear": 0.05, "roughness": 0.50,
                     "note": "lacquer densely scratched to bare steel (more bare than anywhere else)"},
            "bare_steel": {"metallic": 1, "base_srgb": "#C3C3C1", "base_linear": 0.54, "roughness": [0.25, 0.40],
                           "sliding_polished": [0.15, 0.25]},
            F_WOOD: {"metallic": 0, "base_srgb": "#6B3C27", "grain_dark_srgb": "#482C1B", "figure_light_srgb": "#965F46",
                     "handling_wear_srgb": "#87573F", "checker_cells_srgb": "#4E2E1E", "roughness": [0.42, 0.60],
                     "grain": "stock along its axis; handguards along the bore; grip along its raked axis; solid wood"},
            "grime": {"metallic": 0, "base_srgb": "#2A2826", "roughness": 0.80},
            "soot": {"metallic": 0, "base_linear": 0.025, "roughness": [0.80, 0.95], "where": "brake cut, gas vents, port"},
        },
        "sheet_samples_srgb": {"receiver_side": [60, 60, 62], "magazine": [53, 52, 51], "butt_plate": [78, 77, 77],
                               "stock": [107, 60, 39], "backdrop": [126, 126, 126],
                               "note": "lit values, not albedo: hue and relative value only (craft); absolute values from "
                                       "the gun study 3.3; calibrate against sheet crops under matched light (gate L5)"},
        "slots": {"SK_AR01 / SM_AR01": [{"index": 0, "slot": SLOT_METAL, "master": "M_Fabric_Master, Metal From ORM ON"},
                                        {"index": 1, "slot": SLOT_FURN, "master": "M_Fabric_Master, Metal From ORM OFF"}],
                  "SM_AR01_Mag": [{"index": 0, "slot": SLOT_MAG, "master": "M_Fabric_Master, Metal From ORM ON"}],
                  "note": "dark finishes are safe under the MFO brightness trap (gun study 5.9)"},
        "wear_level": "moderate (the sheet's own): hard edge wear, subtle surface wear, no rust, no cracks",
    },
    "textures": {
        "sets": {"Metal": "T_AR01_Metal_{BC,ORM,N} 2048 (DECIDED): class A at 90 px/cm, class B at 60 px/cm (the bottom "
                          "of B = the hip-view need of 61; ADS on the dust cover at 0.30-0.35 m wants 70-82, so it reads "
                          "~15-25 % softer there), C 35, D 26, fill 70-78 %. See metal_budget. Fallback, only if the L7 "
                          "first-person crops show the receiver or cover soft: 4096 at A 100 / B 80, accepting ~25 % fill "
                          "and ~36 MB more for BC+ORM+N, with a third-person LOD bias of 1; this is also the Fab 4K option "
                          "(gun study Q13)", "Furniture": "T_AR01_Furniture_{BC,ORM,N} 2048 + Detail16 2048",
                 "Mag": "T_AR01_Mag_{BC,ORM,N} 2048", "Masks": "T_AR01_Masks (R edge, G handling, B cavity, A refinishable)"},
        "texel_classes_px_per_cm": {"A": [80, 100], "B": [60, 80], "C": [30, 40], "D": [25, 30], "E": [8, 15]},
        "metal_budget": {
            "rough_areas_cm2": {"A (leaf, notch plate, slider, ears)": 40, "B (rear receiver sides X 225-340, dust cover, "
                                "rear sight block, selector, carrier + handle)": 430, "C (front receiver sides, receiver "
                                "bottom, guard + flange, catch, trigger, butt plate, rear trunnion)": 330,
                                "D (barrel, gas tube, gas block, FSB, brake, rod, cap, band)": 240},
            "texels_at_class_mid_A90_B70_C35_D28": "0.32 + 2.11 + 0.40 + 0.19 = 3.0 M: over the 2.9 M that 2048 holds at "
                                                   "70 % fill (the check's 3.6 M counted the whole receiver side as B)",
            "texels_as_decided_A90_B60_C35_D26": "0.32 + 1.55 + 0.40 + 0.16 = 2.4 M = 58 % of 2048 squared: the packer "
                                                 "raises B toward 65 until the fill reaches 70-78 %",
            "first_person_need": "98 px/cm at the notch at 0.25 m, 55 deg ADS, 1440p (class A is met)",
            "decided_by": "check C13 (2026-10-04); the user may pick the 4096 fallback instead"},
        "uv0": "SK: every slot in 0..1; SM twin: Metal u 0..1, Furniture u 1..2, merged mag u -1..0; no mirrored or stacked islands",
        "maps": "BC sRGB; ORM linear (AO / rough / metal); N DirectX; full mips; TEXTUREGROUP_Weapon / WeaponNormalMap",
    },
    "budgets_triangles": {
        "rifle": {"lod0_target": [30000, 45000], "lod0_ceiling": 50000, "lod1": "~45 %", "lod2": "~15 %", "lod3": [1500, 2500],
                  "start_allocation_lod0": 27500, "note": "the plan's per-part table (RIFLE_BUILD_PLAN 3.2) is the floor allocation"},
        "mag": {"lod0_target": 4500, "lod0_ceiling": 7000, "lod1": 1750, "lod2": 580, "lod3": [200, 300]},
    },
    "lods": {
        "count": 4, "rifle_screen_sizes_start": SS_RIFLE, "mag_screen_sizes_derived": SS_MAG,
        "bounds_radius_m": {"rifle_no_mag": round(R_RIFLE / 1000, 4), "rifle_with_mag": round(R_RIFLE_MAG / 1000, 4),
                            "mag": round(R_MAG / 1000, 4), "note": "box half-diagonal from the spec; re-derived from Unreal's bounds"},
        "rule": "size_mag = size_rifle x r_mag / r_rifle; LOD-pop gate fixes the rifle sizes (mean <= 1 px, max <= 3 px at 1440p)",
        "first_person": "ForcedLodModel = 1 on every FP component", "nanite": False,
    },
    "collision_static_twin": {
        "rifle": ["UCX_SM_AR01_LOD0_00 receiver + cover + rear sight + selector + handle",
                  "UCX_SM_AR01_LOD0_01 fore-end (handguards, barrel, gas tube to the gas block)",
                  "UCX_SM_AR01_LOD0_02 gas block + exposed barrel + rod to the FSB",
                  "UCX_SM_AR01_LOD0_03 FSB + ears + brake", "UCX_SM_AR01_LOD0_04 pistol grip + trigger guard",
                  "UCX_SM_AR01_LOD0_05 stock + butt plate", "UCX_SM_AR01_LOD0_06 merged magazine (twin only, if merged)"],
        "mag": ["UCX_SM_AR01_Mag_LOD0_00 upper half of the curve", "UCX_SM_AR01_Mag_LOD0_01 lower half"],
        "method": "dense surface samples (<= 1 mm), dilated 0.2 mm, neighbours overlap 3 mm, <= 32 verts each",
    },
    "gates_look": {
        "numbering": "GUN_BUILDING_STUDY 7.3 everywhere: L1 blockout, L2 form, L3 contour + features, L4 dimensions, L5 "
                     "colour, L6 fake checklist, L7 blind tests. RIFLE_BUILD_PLAN section 9 uses the same numbers.",
        "L1": "blockout IoU vs the traced authority view: >= 0.95 side, >= 0.92 top; < 0.90 = change the method",
        "L2": "form IoU: authority side >= 0.96, top >= 0.93; true-left side vs the RIGHT-labelled panel >= 0.88 (the "
              "sheet's own self-IoU 0.893 - 0.01); per part on its authority view see L2_parts; 3/4 FRONT RIGHT view "
              "(camera solved from the sheet panel): silhouette IoU >= 0.93 and P95 contour <= 3 sheet px; magazine vs c4 "
              "(mirrored) and c5 with an own-scale fit (shape only; close-ups are not to scale): IoU >= 0.96 / 0.94",
        "L2_parts": {"area_threshold_px": L2_AREA_PX,
                     "large_parts": "cleaned trace mask >= threshold: part IoU >= 0.95",
                     "thin_or_small_parts": "below the threshold, IoU is noise-limited (a perfect 3 px strap scores ~0.7-0.8 "
                                            "with the trace's 0.25 px median / 0.5 px P90 edge error): gate on contour "
                                            "distance against the cleaned part contour, P95 <= 1.0 sheet px and max <= 2 px",
                     "thin_parts_now": THIN_PARTS, "areas_px": PART_AREA_PX,
                     "also_thin": "features without their own trace key (front sight ears and post, rear leaf, selector, "
                                  "carrier handle, retainer lever) are gated by L3 feature positions"},
        "L3": "P95 contour <= 2 sheet px (side views); feature positions <= 2 sheet px for every entry in L3_features (side "
              "views) or 1 mm on close-ups; angles <= 1 deg",
        "L3_features": [
            {"feature": "ejection port corners", "M": "X 338 / 452, Z 3 / 17", "part": "receiver"},
            {"feature": "side dimple centre", "M": [397.0, -17.0], "part": "receiver"},
            {"feature": "right rivets (9)", "M": "receiver features.rivets_right", "part": "receiver"},
            {"feature": "trigger-guard flange ledge seam", "M": "receiver dims.ledge_seam_XZ", "part": "trigger_guard"},
            {"feature": "selector pivot", "M": [282.8, -7.8], "part": "selector"},
            {"feature": "leaf rear end / notch plate", "M": [round(float(rs["leaf_X_span_top_3mm"][0]), 1), rs["leaf_top_Z"]["mm"]],
             "part": "rear_sight_leaf"},
            {"feature": "rear sight slider", "M": "X 457.5-465.5, top Z 48.5", "part": "rear_sight_leaf"},
            {"feature": "gap under the leaf", "M": "X 465.8-487.5, Z 34.8-40.9", "part": "rear_sight_block"},
            {"feature": "handguard side slot 1 ends", "M": "X 543 / 571, Z 10.5-16.6", "part": "upper + lower handguard"},
            {"feature": "handguard side slot 2 ends", "M": "X 595 / 623, Z 10.5-16.6", "part": "upper + lower handguard"},
            {"feature": "gas tube vent slots", "M": "X 662-680", "part": "gas_tube", "note": "low confidence: 3 px"},
            {"feature": "front sight ear window", "M": "X 813.7-827.2, Z 11.8-21.6", "part": "front_sight_ears_post"},
            {"feature": "front sight ear boss + hole", "M": [824.7, 29.9], "part": "front_sight_ears_post"},
            {"feature": "trigger-guard opening", "M": "traced hole", "part": "trigger_guard"},
            {"feature": "magazine rib top tips", "M": "Z -38.5", "part": "magazine_ribs"},
            {"feature": "butt-plate screws (c7, close-up rule 1 mm)", "M": "Z -10 / -87.5", "part": "butt_plate"}],
        "L4": "dimensions measured on the build vs this spec <= 0.05 mm. A consistency check, not a likeness test: the same "
              "numbers drive both, so anything larger is a build bug (gun study 7.3). Likeness is L1-L3 and L7",
        "L5": "colour: crop-matched hue, R/B and median luma within the stone S16 tolerances (gun study 7.3; materials "
              "finishes calibrated against sheet crops under matched light)",
        "L6": "fake checklist G1-G20 reviewed with evidence images; 0 major (gun study 3.6)",
        "L7": "design judge on >= 12 image pairs (sheet crop vs our render, matched camera, light and scale): 2 sides, top, "
              "3/4, the 7 close-ups re-rendered at matched cameras, 1 seated mag/well crop. Correct picks <= 8/12 (or "
              "<= 12/20) and no confident design tell; stop and show the user if the first 4 pairs are all picked for a "
              "design reason. Realism judge per gun study 7.3 (2 judges, 4 views, at most 1 single-judge fake call). The "
              "close-ups have no separate gate: they are pairs in this set",
        "excluded_zones": "left-side selector copy and groove (if the user keeps the real pattern); TOP side bumps; "
                          "RIGHT-labelled panel's 12-16 mm mid-section shift",
    },
    "layout": {
        "standard": "GUN_BUILDING_STUDY 4.7 / 11.8 (Q20 default); this block is the one place builders copy paths from",
        "sources": ["Assets/Guns/AR01.blend (rifle)", "Assets/Guns/AR01_Mag.blend (magazine, fitted to the exported rifle bytes)"],
        "exports": "Exports/Guns/AR01/: SK_AR01*.fbx, SK_AR01.skeletal.json, A_AR01_*.fbx, SM_AR01.fbx + SM_AR01.sockets.json, "
                   "SM_AR01_Mag.fbx + SM_AR01_Mag.sockets.json, Physics/, Textures/ (+ Recolour/), README.md, MATERIALS_README.md",
        "scripts": "Scripts/guns/rifle/ (build_rifle.py staged, lock asserted at the top; rifle_parts.py; run_rifle.sh); shared "
                   "code moves to Scripts/guns/gunlib/ only when the SMG needs it; ROOT = Path(__file__).resolve().parents[3]",
        "work": "WorkFiles/guns/rifle/ (spec, reports, UnrealCheck/); scratch/ and build/ are not committed",
        "renders": "Renders/Guns/AR01/, showcase/<Product_Name>/ + an ASSET_LIST.md row",
        "locks": {"asset": "AR01 (Scripts/pipeline/lock.py)", "library": "GunLib", "shared_exports": "GunShared",
                  "materials": "PackMaterials (Scripts/unreal/materials/np_lock.py, build via run_build.sh)"},
        "unreal_check_path": "/Game/GunCheck/AR01_<run>",
    },
    "unseen_plain": [
        "receiver underside between grip and well: the guard's top flange as a flat plate, two guard rivets", "inside the port: carrier face, dark cavity",
        "magazine well: 25-30 deep dark cavity, front lug recess, rear catch notch", "bore and brake interior: dark, plain",
        "magazine internals: lips + follower, no rounds", "magazine rear spine: as the front spine",
        "grip bottom: plain flat end, small chamfer", "handguard insides: plain dark channel at the ends",
        "underside of the rear sight block, gas block, FSB: plain continuation", "butt plate: no trap",
        "front post: hidden in the hood on the sheet; post on a drum, tip 4.4 below the ears",
        "dust cover rear button: small squared tab (TOP)"],
}

# ------------------------------------------------------------------------------------- resolutions (merge log)
spec["resolutions"] = [
    {"id": "R1", "topic": "Which panel is which side",
     "conflict": "measure + craft: the LEFT-labelled panel is the gun's left with right-side controls mirrored onto it; "
                 "tech plan: it is the right side",
     "resolution": "LEFT-labelled panel = TRUE RIGHT side (muzzle right with the selector, port and handle visible is "
                   "geometrically a right-side view; it agrees with c1, the 3/4 front-right view and the TOP knob). "
                   "The RIGHT-labelled panel = true left with one generator fault: the copied selector (+ a groove).",
     "rule": "tech on frames; checked by geometry in this merge"},
    {"id": "R2", "topic": "Dust cover height", "conflict": "measure 46.9 above the bore (75.7 total); craft +33",
     "resolution": f"crown at Z {round(CROWN_Z, 1)} (median of the traced silhouette over X 275-445). The 46.9 came from a "
                   "20 px sliver ring at the rear-sight junction; the check showed it is the rear sight leaf's overhang, "
                   "now reassigned in the trace (R19). Receiver height incl. cover = "
                   f"{round(CROWN_Z - rec['bottom_Z']['mm'], 1)}.", "rule": "measurement wins (its own trace, corrected)"},
    {"id": "R3", "topic": "Upper handguard length", "conflict": "measure 153.8 (X 487.1-640.9); craft X 528-644",
     "resolution": "X 534.0-640.9 = 106.9 (the main traced ring); the 487.1 start came from a 12 px sliver ring, now "
                   "removed from the trace itself (R19)",
     "rule": "measurement wins (corrected)"},
    {"id": "R4", "topic": "Magazine radii", "conflict": "craft R 210 / 150 about (580, -10); measure concentric R 239.0 / 180.8 about (604.8, 3.3)",
     "resolution": "measure (rms 0.56 mm fit on sub-pixel edges)", "rule": "measurement wins on dimensions"},
    {"id": "R5", "topic": "Magazine thickness", "conflict": f"front close-up c5 reads {MAG_T_C5} (18-20); real ~28-30; craft ~29",
     "resolution": f"SUPERSEDED by R32 ({MAG_T}). Round-0 text: NOT measurable on the sheet (c5 reads about 18-20); the real-pattern double-stack norm is "
                   "28-30, and 28 was chosen. The earlier derivation (17.9 x 1.557 from the c7/TOP butt-plate ratio) is "
                   "withdrawn: c7 draws wood on both sides of the plate where TOP shows the plate flush with the stock, so "
                   "that ratio is a drawing inconsistency, not a uniform close-up scale (check C5). Confirm on the "
                   "camera-solved 3/4 view (spine width against the 41.5 receiver) in the blockout stage before freezing",
     "rule": "real-pattern norm where the sheet cannot be measured; the user may override"},
    {"id": "R6", "topic": "Barrel diameter", "conflict": "LEFT 14.8 (15.0 behind the gas block), RIGHT 15.5, TOP 16.7; measure suggests 15.5",
     "resolution": "15.0: LEFT is the authority for heights; TOP's 16.7 is excluded (its shading inflates thin rounds, as "
                   "the 1.128 barrel ratio shows); within 0.6 px of every side reading", "rule": "measurement authority table"},
    {"id": "R7", "topic": "Cleaning rod diameter", "conflict": "measure 3.4 +-0.7 (2.8 px); craft ~5; real ~6",
     "resolution": "4.0 (upper edge of the sheet reading; a thin dark line on grey reads thin); invent nothing bigger",
     "rule": "measurement wins, rounded within its uncertainty"},
    {"id": "R8", "topic": "Part X stations", "conflict": "craft readings +-4 mm (e.g. receiver 240-483, grip 246-299, FSB 808-840, brake 840-880)",
     "resolution": "all X/Z from the LEFT trace (receiver 225.2/240.9-485.3, grip 226.5-300.5, FSB "
                   f"{fsb['X'][0]}-848.8, brake 848.8-880)",
     "rule": "measurement wins on dimensions"},
    {"id": "R9", "topic": "Grip rake", "conflict": "measure edges 23.6 / 19.1 (axis 21.4); craft 22 / 13",
     "resolution": f"the build uses the traced profile; the Grip origin uses the midline axis fitted over Z -64..-116 (front and rear edges parallel there; the range moved from -60 after the check traced the grip front strap): "
                   f"{round(GRIP_RAKE, 2)} deg", "rule": "measurement"},
    {"id": "R10", "topic": "Construction details", "conflict": "none of substance",
     "resolution": "craft wins on every construction note (smooth cover, tab handle, ribs, checkering method, brake cut, "
                   "ears with windows); measurement supplies their numbers and positions (the craft scallop fractions "
                   "were replaced by measured slots, R20)", "rule": "craft wins on construction"},
    {"id": "R11", "topic": "Checker panel position", "conflict": "craft: front half in c6, rear half in c1 ('mirrored')",
     "resolution": "c1 is a true right view and c6 a true left view; mirrored, they agree (no inconsistency)", "rule": "R1"},
    {"id": "R12", "topic": "Assets and rig", "conflict": "tech plan: two static meshes (skeletal as open Q1); gun study: SK + SM twin + mag, AR-01 is the rig pilot",
     "resolution": "gun study (repo-root line standard; its section 11 targets this plan). Bones: body, bolt, trigger, "
                   "selector, mag_release, magazine, sight_rear, muzzle_device", "rule": "line standard over the plan"},
    {"id": "R13", "topic": "Socket names", "conflict": "plan OffHand / EjectPort / MagWell / ADS / SightFront / mag Attach",
     "resolution": "gun study 5.3: SupportHand / ShellEject / Mag / Sight (front post carried by Sight's +X) / mag Mag; "
                   "MuzzleSeat and Holster added; plan names kept as plan_name", "rule": "line standard"},
    {"id": "R14", "topic": "Finishes and slots", "conflict": "craft: blued steel metallic 1 at #3C3C3E; plan: M_Steel_Master + Steel Tint; gun study: black lacquer metallic 0, bluing only for small parts, M_Fabric_Master + MFO",
     "resolution": "gun study values (metallic 1 below sRGB ~110 is non-physical); craft's sampled hues and relative values "
                   "kept for calibration; slots M_AR01_Metal / M_AR01_Furniture / M_AR01_Mag", "rule": "line standard (physically valid)"},
    {"id": "R15", "topic": "Budgets, LODs, textures", "conflict": "plan 26-32k, 3 LODs, steel 4096; gun study 30-45k, LOD3 now, Metal sized by texel class",
     "resolution": "gun study; the plan's per-part table stays as the floor allocation", "rule": "line standard"},
    {"id": "R16", "topic": "Charging handle X", "conflict": "side view X 444-458; TOP knob X 470-482",
     "resolution": "side view X (LEFT authority for X), TOP protrusion (Y -35.2)", "rule": "authority table"},
    {"id": "R17", "topic": "Rear sight retainer lever", "conflict": "arm on one panel, boss on the other (read as an inconsistency)",
     "resolution": "not an inconsistency once R1 is applied: arm on the right, boss on the left, as drawn", "rule": "R1"},
    {"id": "R18", "topic": "Layout and names", "conflict": "plan Exports/AR01, Scripts/Guns/AR01, Assets/AR01; gun study Exports/Guns/AR01, Scripts/guns/rifle, Assets/Guns/AR01.blend",
     "resolution": "gun study 11.8 (Q20 default)", "rule": "line standard"},
]

spec["resolutions"] += [
    {"id": "R19", "topic": "Per-part trace masks (check C2)", "conflict": "part keys held slivers cut off by the hand-placed "
     "region boundaries: dust_cover 2 extra contours (X 448.6-454.8), handguard_upper 1 (X 487.1-515.2), barrel 2 (the FSB "
     "rear edge X 806-810 up to Z 17.4, and a 2 px piece in the gas block), trigger_guard a grip-edge sliver (X 286-298.5) "
     "and a trigger piece; the spec cited these keys as the outline authority",
     "resolution": "trace_reference.py now drops part contours under 40 px (except a part's largest) and relabels detached "
                   "pieces under 40 px to the nearest other part (the magazine cut excepted), and three region boundaries "
                   "were corrected on gridded zooms: the rear sight leaf overhangs the dust cover front to X "
                   f"{rs['leaf_X_span_top_3mm'][0]} (c2 shows it), the front sight block starts at the dark seam X "
                   f"{fsb['X'][0]} (not 809.7), and the grip's dark front strap is grip. Every part box was re-checked against "
                   "the silhouette on overlays", "rule": "measurement (its own trace, cleaned)"},
    {"id": "R20", "topic": "Handguard features (check C1)", "conflict": "craft: two finger scallops per side at 10-30 % and "
     "45-65 % of the lower guard (X 499.7-531.1, 554.6-586.0); measurement notes: two long slots on the upper guard",
     "resolution": "measured stations X 543-571 and 595-623 on both panels: slots 3.5 mm up into the upper guard's lower edge "
                   "plus a 1.5 mm bevelled dip in the lower guard's top edge (opening Z ~10.5-16.6); both in L3_features",
     "rule": "measurement wins on positions"},
    {"id": "R21", "topic": "Trigger guard (check C2)", "conflict": "bottom -73.7, drop 44.9, box from X 286.0",
     "resolution": f"bottom {tg['bottom_Z']['mm']} (pixel columns: -68.0 / -66.8 / -64.7 at X 310 / 330 / 345), drop "
                   f"{tg['drop_below_receiver_bottom']['mm']}, box X {tg['X'][0]}-{tg['X'][1]}: the old numbers came from the "
                   "grip's front strap labelled as guard", "rule": "measurement (cleaned)"},
    {"id": "R22", "topic": "Sight line (follows R19)", "conflict": "notch at X 458.0 (radius 367.3) from a leaf rear end cut "
     "at the dust-cover region boundary",
     "resolution": f"the leaf's rear end is X {rs['leaf_X_span_top_3mm'][0]}, so the notch is X {round(NOTCH_X, 1)} and the "
                   f"radius {round(POST_X - NOTCH_X, 1)} (real ~378: -0.7 %, was -2.8 %); the slider is the raised block at "
                   "X 457.5-465.5. Sight, Grip-relative sockets and the design sheet are regenerated",
     "rule": "measurement"},
    {"id": "R23", "topic": "Receiver bottom band (check C9)", "conflict": "receiver bottom -28.8 vs its own traced profile "
     "-34.5..-36 from X 252 to 370",
     "resolution": "-28.8 is the wall bottom ahead of the well; behind it the trigger guard's top flange (X 252-370, ledge "
                   "seam -32.5 rising to -29.5, bottom -34.8) is now explicit", "rule": "measurement"},
    {"id": "R24", "topic": "Butt-plate screws (check C4)", "conflict": "default single slot (craft: 'period-plausible')",
     "resolution": "cross (X) slots in a visible counterbore ring, as c7 draws both heads; open question closed (the single "
                   "slot stays a Fab option)", "rule": "invent nothing the reference does not show"},
    {"id": "R25", "topic": "Magazine ribs and top plates (check C6)", "conflict": "rib tips 'about 25 below the visible "
     "top' (Z ~-56); top plates without a position",
     "resolution": "rib tips at seated Z -38.5 +-1.5 (26.5 below the lips), bottom ends 16 +-2 above the floor plate; top "
                   f"plates seated Z -38..-12, width fraction 0.08-0.80 from the rear (X {TOP_PLATE_X} at Z -25)",
     "rule": "measurement"},
    {"id": "R26", "topic": "Sockets (checks C7, C8)", "conflict": "ShellEject on the bolt (travels into the receiver); "
     "SupportHand on the mid-plane 3 mm inside the wood",
     "resolution": f"ShellEject on body; SupportHand on the handguard underside (Z {SH_Z}) and PROVISIONAL until H1 sets the "
                   "measured hand_l frame", "rule": "tech"},
    {"id": "R27", "topic": "Front sight ear hole (check C10)", "conflict": "plain 3 mm hole at (822, 33)",
     "resolution": "raised ring 6 with a 3.5 hole at (824.7, 29.9) (pixel dump); c3's mark left off", "rule": "measurement"},
    {"id": "R28", "topic": "Gates (checks C3, C12)", "conflict": "per-part IoU 0.95 unreachable for 3-6 px parts; L-number "
     "clash between the spec, the plan and the gun study; no 3/4 number; close-ups without a criterion",
     "resolution": f"per-part IoU only for masks >= {int(L2_AREA_PX)} px, contour distance below; gun-study L-numbers "
                   "everywhere; 3/4 gate IoU >= 0.93 + P95 <= 3 px; close-ups are L7 pairs; L4 kept as a build-bug check",
     "rule": "line standard"},
    {"id": "R29", "topic": "Metal texture size (check C13)", "conflict": "'2048 likely' did not fit the classes at 70 % fill",
     "resolution": "Metal 2048 with class B at 60 px/cm (A 90): ~2.4 M texels; 4096 fallback recorded (textures.sets)",
     "rule": "decided here; the user may choose the fallback"},
    {"id": "R30", "topic": "Magazine bottom vs overall height (form fix round 1)", "conflict": "key overall_height_with_mag 232.6 (front sight top 49.4 to the traced silhouette's lowest point -183.2) but magazine.bottom_Z -183.4 (the magazine ring's lowest point -183.376): 49.4 + 183.4 = 232.8, so no model could meet both within the L4 0.05 mm",
     "resolution": "both read the same traced edge 0.15 mm (0.13 px) apart; the silhouette is the outline authority for every overall number, so magazine.bottom_Z = -183.2 and the build sets its floor line from the silhouette's lowest point (rifle_parts2._floor_line)", "rule": "one outline for all overall dimensions"},
    {"id": "R31", "topic": "Grip origin depth (H1 early, form fix round 1)", "conflict": "provisional 40 mm (study 5.1)",
     "resolution": f"{GRIP_DEPTH:g} mm: the fit body's palm centre projected on the knuckle line from the web (45.9 mm); B-frame coordinates (sockets, bore height) are regenerated from it. Grip section width 30 -> 31 (documented real AK grips 30-36 mm; at 30 the rounded-oblong girth sat on the real-world band's lower edge)", "rule": "H1 (gun study 7)"},
    {"id": "R32", "topic": "Magazine thickness (form fix round 2; supersedes R5)",
     "conflict": "spec 28.0 (real-pattern norm) vs the camera-solved 3/4 panel's preference ~24 (parabola peak 23.6 on "
                 "the magazine-zone IoU sweep 18-34 mm) and close-up c5's 18-20",
     "resolution": f"{MAG_T}: a staggered double stack of {CASE_HEAD_D} mm case heads needs d x (1 + sin 60 deg) = "
                   f"{MAG_T_INSIDE_MIN:.1f} mm inside, plus two ~1.0 mm walls and the pressed ribs' depth, so about 25-26 mm "
                   "is the physical minimum; 26 is the closest physically real value to the sheet. The magazine well "
                   "opening and liner follow (opening = thickness + 1.0, liner walls 1.0); the remaining 3/4 magazine "
                   "residual (the panel's ~24) is the documented physical-minimum residual of the L2 3/4 gate",
     "rule": "physical minimum wins over a drawing that is thinner than a real magazine can be"},
    {"id": "R33", "topic": "Grip back strap radius (form fix round 2)",
     "conflict": "straps R 8-10 (craft) at width 31 / R 10 leave a 3.2-3.6 px residual on the grip's back strap in the "
                 "camera-solved 3/4 view; width 30 / R 10 also removes it but drops the section girth below the H1 band "
                 "(122.0 for this depth); back strap R 11 at width 31 leaves 3.16 px (it flickers with the camera re-solve)",
     "resolution": "width 31.5 (inside the documented 30-36), front strap R 9 (inside the spec's 8-10), back strap "
                   "R 13.5 (the palm swell; real grips are rounder at the back than at the front): the back-strap residual "
                   "drops to 2.8 px (sweep at the solved camera; R 12 / R 12.5 / R 13 leave 3.0-3.16 px, R 11 3.16 px) and "
                   "the H1 girth stays inside its band (about 122.5 against the 122.06 lower edge for this depth; round 1: "
                   "123.5 at 31 / R 10). The grip's front-strap 3/4 residual grows slightly (core 114 -> 136 px) and stays "
                   "a 3/4-panel contradiction",
     "rule": "3/4 panel for the unseen section, inside the H1 band"},
    {"id": "R34", "topic": "Gas block, buttstock and front sight widths vs the 3/4 panel (form fix round 2)",
     "conflict": "round 1 flagged three 3/4 residuals as 'a width the TOP allows would fit', testing our half width "
                 "+-2.45 mm (2 TOP px)",
     "resolution": "kept. Re-tested against the TOP trace itself: the widths that remove the 3/4 residuals push the TOP "
                   "width error past the 2 px tolerance (gas block +8 % -> TOP P95 2.43 px, region still 5.1 px; stock "
                   "-6 % -> 2.16 px, region still 5.0 px; front sight base: no width from -5 % to +25 % brings it below "
                   "3.6 px) and lower the TOP L2 IoU (gas block +7 %: -0.0022; stock -3 %: -0.0018) that passes at "
                   "0.931 against 0.93. Inside the TOP-allowed range the three regions are 3/4-panel contradictions; "
                   "the exception test now uses that range (rifle_q34.py, TOP width error P95 <= 2 px at the part's own "
                   "width stations) instead of a fixed +-2.45 mm",
     "rule": "TOP is the width authority"},
]

spec["resolutions"] += [
    {"id": "R35", "topic": "Detail pass: part shapes from their own close-ups (2026-10-05)",
     "conflict": "the form stage derived small parts from the side outlines; a blind judge picked our crops on design",
     "resolution": "each detailed part (selector, trigger guard + trigger, front sight, muzzle brake, rear sight, "
                   "receiver right side, grip, magazine, butt plate) is built from its close-up for its 3D shape; the "
                   "side views and the spec keep scale / position (every stage-2 gate re-run on the integrated build). "
                   "The builders' spec proposals are applied as built (parts[*].detail_pass lists them)",
     "rule": "close-up = shape authority; side views = scale / position authority"},
    {"id": "R36", "topic": "Close-up proportions that contradict the side views (front sight ears, brake length, "
                           "magazine curve, butt plate width)",
     "conflict": "c3 draws the ears ~0.7-0.8 as wide front-to-back and the brake ~35 % shorter for its height; c4 / c5 "
                 "draw the magazine 21-38 % longer for its width and more curved; c7 draws the plate 0.65x the TOP width",
     "resolution": "the side / TOP views stay the authority (L2 per part, L4 key dims). The close-up-proportion "
                   "variants were built and measured (front sight FS_EAR_SX 0.78: L2 0.865 < 0.95) and are NOT shipped; "
                   "the user decides (open_questions)",
     "rule": "the gates' authority table; a blind judge on the close-up crops can still see these proportions"},
    {"id": "R37", "topic": "Muzzle brake body vs key dims after the detail rounds",
     "conflict": "round 2 flared the body to r 10.5 and moved the chin to X 879.63 (L4 overall_length 879.6, brake "
                 "length 32.4 and dia 21.6 including the knob vs 880.0 / 31.2 / 20.2)",
     "resolution": "the widest point is a raised rim ring r 10.1 (c3: a proud rim band), body r 9.6-9.85, cut plane "
                   "X 873.1 at Z 0 so the chin's front is X 880.0; L4 measures the BODY (the detent knob, which the "
                   "side views do not show, is excluded: rifle_measure.py)",
     "rule": "measurement wins on dimensions"},
    {"id": "R38", "topic": "Detent latch owner and the front collar",
     "conflict": "front sight and muzzle brake builders both claimed the c3 latch; the FSB front collar r 10.1 "
                 "equalled the brake and read as part of a long brake with a seam",
     "resolution": "the muzzle brake owns the knob; the FSB front collar is r 8.7 (c3: sleeve band -> narrow ring -> "
                   "brake) and the knob sits 0.03 above it", "rule": "c3; one owner per feature"},
    {"id": "R39", "topic": "Side-view label convention for the catch housing",
     "conflict": "rifle_silhouette gave guard faces above Z -52 (the round-1 cheek bottom) to the mag_catch label",
     "resolution": "-54.5: the cheeks reach the paddle top (Z -53.87) since round 2 (trigger_guard proposal); "
                   "forward of X 355.3 the guard has no loop faces, so only cheek faces move",
     "rule": "trace label convention"},
    {"id": "R40", "topic": "Ejection port opening top and the charging handle height",
     "conflict": "receiver_right proposes the skirt cutout top at Z ~21.5 (c2, q34, the side panel at 16x) and the "
                 "handle at Z ~4-15; the LEFT trace's L3 port corner says Z 17 (tol 2.43)",
     "resolution": "built at Z 19.2 (inside the L3 tolerance) and the handle at Z 8-17 (the selector lever under its "
                   "path limits it); 21.5 stays a proposal (open_questions)", "rule": "L3 trace position"},
    {"id": "R41", "topic": "Butt plate width and the stock end section (BP-1, BP-5)",
     "conflict": "c7 draws the plate ~0.65x the stock width with wood beside it; TOP shows a flush steel cap 36.5-36.9",
     "resolution": "TOP kept (width 36.9, L4 butt_width); the stock end section following the plate lozenge (BP-1) "
                   "is deferred to the stock's next pass", "rule": "TOP is the width authority"},
    {"id": "R42", "topic": "Magazine floor plate and Base socket",
     "conflict": "the LEFT trace's floor face runs ~2.7 mm outside the spec line (56 vs 50.6 deg)",
     "resolution": "spec corners kept; the plate is 5.0 thick with a R 3.5 rear corner, a 1.0 step over the front 55 % "
                   "and its floor line 0.86 outward (L2 0.9678); the Base socket moves 1.4 mm out along the normal",
     "rule": "spec corners (sockets) + side-view L2"},
    {"id": "R43", "topic": "Magazine rear lug and front-lug recess",
     "conflict": "c4 draws a rear lug and a chunky front lug; the well liner (0.5 mm behind the body) and the guard's "
                 "front tang (0.2 mm) leave no room, the reload path limits the front lug",
     "resolution": "deferred to the fit stage (M4): a rear-liner slot + raised catch nose and a front-liner recess "
                   "first, then the lugs", "rule": "reload path (M-gates) first"},
    {"id": "R44", "topic": "LOD0 triangle ceiling after the detail pass",
     "conflict": "integrated detail parts took the rifle to 53.8k (ceiling 50k) and the magazine to 7.96k (7k)",
     "resolution": "unseen or redundant density removed: the barrel's chamber cuts (inside the carrier pocket), lower "
                   "handguard stations on its straight run, upper handguard stations on its profile knots and a 24-point "
                   "arc, front sight rims 2 segments, rivets 8 segments, an 8-gon swivel wire, trigger outline DP 0.03, "
                   "the selector's groove, flush butt screws (16 segments), magazine rib ends at the round-end ring count",
     "rule": "B8 ceiling"},
]

spec["resolutions"] += [
    {"id": "R45", "topic": "Detail pass round 2b (second detail loop) integrated (2026-10-05)",
     "conflict": "every part builder re-ran round 2 on the integrated build (r2b) and filed round-2b proposals; the "
                 "integration round's muzzle-brake rim ring (R37) and several construction texts no longer describe "
                 "the parts",
     "resolution": "the round-2b proposals are applied as built (parts[*].detail_pass, source '... (round 2b)'): "
                   "selector solid stepped plate + rib + button head in a washer; trigger profiled blade; guard bead "
                   "section and c1 radii; front sight 4.8 ears, flat pin heads, rounded rod lug; muzzle brake shank + "
                   "groove + step, straight body r 10.0-10.1 (no rim ring: supersedes R37's construction, its key dims "
                   "hold), c3-traced slot, detent block; rear sight outer-edge ratchet teeth, two-lobed notch block, "
                   "rolled block band, broader link; receiver port rear band, domed rivets / pin, deeper right dimple, "
                   "hairpin clip; grip lofted flared base, rounder sides, gable-crested checker cells; magazine domed "
                   "top plate, U rib ends, front bead, front knobs, rear lug, swelled floor plate; butt plate c7 ends "
                   "at the width scale, straight counterbores, heel top flush with the stock. Deferred items keep "
                   "their entries: R36 (close-up proportions), R40 (port top), R41 (butt plate width), R43 (liner "
                   "changes for the higher rear knob / chunky front lug)",
     "rule": "close-up = shape authority; side views = scale / position authority (R35)"},
    {"id": "R46", "topic": "Butt plate height after the heel raise",
     "conflict": "the round-2b plate's heel top was raised 0.75 to meet the stock's traced top line (c7 shows no wood "
                 "above the plate); the plate's Z bounds measure 110.52 against the measured 109.8",
     "resolution": "butt_height 110.5: inside the measurement's own uncertainty (109.8 +- 0.7); the traced stock top "
                   "line at the heel (Z 0.43-0.47) and c7 decide where the plate's top sits",
     "rule": "measurement within its uncertainty; c7 for the shape"},
]
spec["resolutions"] += [
    {"id": "R47", "topic": "Integration round after r2b: focused attempts on the r2b judges' design tells",
     "conflict": "the r2b blind judges still picked every part confidently; several tells sit inside the authority "
                 "table (fixable), the rest are close-up proportions (R36 / R41), the port top (R40) or contradict an "
                 "earlier round's judge",
     "resolution": "fixed as real geometry: selector domed bolt head (1.84 high) in a 1.2 thick washer with a crisp "
                   "shoulder; front sight ears land 1.0 inside the base flanks (a visible ledge) and the ear boss is a "
                   "raised plug (rim 0.62 / face 0.45 proud); muzzle brake chamber r 7.1 -> 6.4 with a 0.6 inner round "
                   "(thick flat annular face); rear sight block: the short upright slot (a lit shard in c2: 'torn "
                   "crease') became a rounded scallop r 2.1 cut after the bevels (L3 gap bbox unchanged); right receiver "
                   "pin at (388, -8) a hollow ring (c1: a small ring round a dark hole); mag catch pin heads low and "
                   "flush-set (no washer); grip checker border softened (0.4 x 2 round, field band 0.35); magazine ribs "
                   "x0.8 narrower, crest ramp 3.0, bottom ends 14.0 above the floor plate (spec 16 +- 2); butt plate "
                   "face crown 0.6 -> 0.25; grip base lifted onto the key bottom Z (L4)",
     "rule": "R35 authority table; unchanged where a fix needs R36 / R40 / R41"},
]
spec["key_dimensions"]["butt_height"] = 110.5
spec["key_dimensions"]["butt_height_note"] = "R46: 109.8 +- 0.7 measured; 110.5 with the heel top flush with the stock"

# ------------------------------------------------------------------------------- form realism round (2026-10-05, R48)
# Two realism judges on the rough-look form: fake in the first-person, ADS and hero views, real at 3 m. Every reason
# they gave was fixed as real geometry in the part modules / generators (Scripts/guns/rifle/parts/*, rifle_parts2.py);
# the values below are as built.
DP3 = "form realism round (R48): {}"


def dp3(pid, src, **kw):
    dp(pid, src, **kw)
    _P[pid]["detail_pass"][-1]["source"] = DP3.format(src)
    for k in [k for k, v in _P[pid]["dims"].items() if v is None]:
        del _P[pid]["dims"][k]


dp3("dust_cover", "parts/receiver_right_cover.py",
    dims={"skirt_vertical_to_Z": 22.26, "crease_Z": None, "crease_depth": None, "studs": None,
          "crown": "gentle top arc R 48 (rise ~2.9 over +-16.5) on R 8 shoulders, tangent-continuous, to Z 32.7",
          "sheet_thickness": 0.98,
          "rear_end": "formed hood: the section above the lip line Z 11.6 scaled by the traced centreline rear "
                      "profile; lip end ~1 mm tall at X ~240 (Z 11.6-12.6, over the receiver top 11.0)",
          "edge_break": "0.3 on cut edges only (skirt bottoms, lip, front end, port cutout, button hole)"},
    construction="Pressed 0.98 mm sheet: outer loft (vertical skirts to Z 22.26, R 8 shoulders, gentle R 48 top arc "
                 "through the crown Z 32.7) minus the same construction one sheet thickness in; the rear end a formed "
                 "hood whose centreline follows the traced rear profile (steep lip, ramp, roll into the crown) with the "
                 "shoulders and skirt tops on proportionally lower copies of it; open below the lip line Z 11.6 and "
                 "behind X 241 under it; the spring-guide button through a hole in the lip's slope; the right skirt "
                 "cut out over the port (top Z 19.2). No studs, no ribs (sheet and real pattern). Crisp 0.3 breaks on "
                 "the cut edges, smooth lofted faces.",
    note="realism: invented crown studs removed; half-cylinder / flat rear face / shading seam replaced by a pressed "
         "sheet with a gentle crown and a formed rear lip")
dp3("selector", "parts/selector.py",
    dims={"plate_thickness": 2.0, "washer_proud": 0.5, "head_height": 0.9, "rib": None, "edge_bevel": 0.3,
          "top_edge_Z": 8.0, "crease_step": 0.35,
          "head": "low button head (axle end) on a low washer",
          "slot_closed": "upper edge Z 8.0 over the slot band (wall cut Z 3-9.2): 1.6 mm left under the skirt edge 9.6"},
    construction="One flat stamped blade 2.0 mm on c1's outline mapped to the side view, its upper edge raised from the "
                 "step forward to Z 8.0 (closes most of the charging-handle slot on safe; clears the handle stem 8.6 / "
                 "knob 8.2 over the full bolt travel), crisp 0.3 breaks; c1's crease a 0.35 pressed step; the nose tab "
                 "bent out 12 deg about c1's bend line with a small flat pin; a low washer 0.5 and button head 0.9 on "
                 "the pivot. No markings.",
    note="realism: short stubby paddle sitting high -> a long thin stamped blade closing most of the slot")
dp3("trigger_guard", "parts/trigger_guard.py",
    dims={"loop_section": "stamped channel: flat web 10 wide outside, R 1.0 bends, flat 1.0 flanges (the side band), "
                          "0.25 flange-end breaks, channel open toward the trigger, web 1.6",
          "strap_thickness": 1.0},
    note="realism: wire-thin rounded beads -> a stamped strip channel with flat faces and crisp edges")
dp3("buttstock", "rifle_parts2.py",
    dims={"section": "swelling oval: w(x) f(v); f = the butt plate's end-view profile at the butt (X <= 24), a "
                     "two-sided superellipse forward of X 70 (exponent 3.3 -> 2.9 at X 150 -> 2.45 at the wrist, widest "
                     "row 0.42 -> 0.5 from the top), blended between",
          "edges": "no round-over along the stock (the oval is smooth); 1.6 x 2 only on the inlet / tang seats"},
    construction="Wood stock lofted from swelling oval sections on the traced top / bottom lines and the TOP-traced "
                 "width: the butt end follows the butt plate's own lozenge (slimmer, rounder butt), convex sides that "
                 "taper and swell toward a rounded comb crest and toe line, rounder toward the wrist.",
    note="realism: flat-sided slab, boxy butt, faceted comb, uniform round-over -> swelling oval sections")
dp3("magazine_ribs", "parts/magazine.py",
    dims={"rib_half_widths": [2.0, 2.15, 2.15, 1.95], "rib_proud": 0.95,
          "profile": "pressed-out swell: crest to 0.15 hw, 0.72 h at 0.55 hw, 0.24 h at 0.82 hw, 0.1 fillet dip"},
    note="realism: ribs read as incised lines -> broad rounded pressed-out ribs")
dp3("pistol_grip", "parts/grip.py + parts/grip_checker.py",
    dims={"checker_pitch": 1.8, "checker_border": "recess 0.75 with a crisp 0.25 x 1 cut wall",
          "checker_cut_depth": 0.70},
    note="realism: checkering read as a decal -> 1.8 mm diamonds cut 0.70 into a 0.75 recess with a crisp border")
dp3("rear_sight_leaf", "parts/rear_sight.py",
    dims={"slider_top_Z": 47.6, "slider_top_Z_traced": 48.5},
    note="B4: the slider's roof (traced 48.5, inside the trace's noise) formed the visible notch top 0.58 mm above the "
         "real one from the ADS eye; built 0.4 under the notch top (real pattern: the slider sits below the notch)")
dp3("receiver", "parts/receiver_right.py",
    dims={"rear_vertical_edges": "0.6 roll (was 1.5)"},
    note="realism: crisp stamped / machined edges (0.3-0.6) on steel")
spec["resolutions"] += [
    {"id": "R48", "topic": "Form realism round (2026-10-05): the realism judges' reasons fixed as real geometry",
     "conflict": "both realism judges read the rough-look form as fake in the first-person (35 cm), ADS and hero views "
                 "(real at 3 m): invented domed studs on the dust cover; the cover a thick half cylinder with a flat "
                 "sharp rear face and a shading seam; no front post in the ADS notch; the stock a flat-sided slab with "
                 "a boxy butt, faceted comb and a uniform round-over; the selector a short stubby paddle; the trigger "
                 "guard wire-thin; the magazine ribs incised lines; the grip checkering a decal; uniform soft bevels",
     "resolution": "SIGHT: the Sight socket moved from the notch bottom to the notch TOP centre (Z 48.0), pitch -0.4579 "
                   "toward the post tip: an eye on the old line saw the tip exactly on the notch floor (post hidden "
                   "behind the leaf); the rear sight slider's roof (traced 48.5) lowered to 47.6 (it formed a false, "
                   "higher notch top). New gate B4 (rifle_b4.py, occlusion-aware raster at 2560x1440 x8): post tip "
                   "level with the notch top and centred within 0.2 mm, visible in the notch. COVER: pressed 0.98 "
                   "sheet, gentle crown, formed rear hood / lip, no studs, cut-edge-only breaks. STOCK: swelling oval "
                   "sections (butt = the plate's lozenge). SELECTOR: flat 2.0 blade, top raised to Z 8.0 (closes most "
                   "of the slot), low pivot hardware. GUARD: stamped channel strip. MAG RIBS: broad pressed-out swells. "
                   "CHECKERING: pitch 1.8, crisp cut border. EDGES: 0.3-0.6 on steel (receiver rear roll 1.5 -> 0.6, "
                   "cover / selector 0.3), soft only on wood. Silhouette / proportion gates re-run (gates/form.json).",
     "rule": "real pattern + main views (user decision 2026-10-05); the side / top / 3-4 gates keep passing"},
]

# ------------------------------------------------------------------------------- realism round 2 (2026-10-05, R49)
# The two realism judges on the round-1 rebuild (hero 3/4 and first-person 35 cm): reasons checked one by one against
# the real stamped-receiver pattern and the sheet's main views; the real flaws are fixed as geometry, the rest rejected
# with the reason (R49). Values as built.
DP4 = "realism round 2 (R49): {}"


def dp4(pid, src, **kw):
    dp(pid, src, **kw)
    _P[pid]["detail_pass"][-1]["source"] = DP4.format(src)
    for k in [k for k, v in _P[pid]["dims"].items() if v is None]:
        del _P[pid]["dims"][k]


dp4("dust_cover", "parts/receiver_right_cover.py",
    dims={"skirt_vertical_to_Z": 26.03, "crown_radius": None,
          "crown": "flatter top arc R 90 (rise ~1.8 over +-17.7) on R 5 shoulders, tangent-continuous, to Z 32.7",
          "cross_ribs": {"X": [296.0, 322.0, 348.0, 374.0, 400.0, 426.0], "top_width": 5.0, "floor_width": 3.2,
                         "depth": 0.8, "pressed": "IN (the main views' top line stays smooth at the crown 32.7)",
                         "extent": "across the top arc, fading over the shoulder to 0 at the vertical wall "
                                   "(smoothstep in the shoulder angle); flanks ~42 deg (crisp)"},
          "lengthwise_rib": "the shoulder line (top of the vertical skirt, Z 26.03)"},
    construction="Pressed 0.98 mm sheet: outer loft (vertical skirts to Z 26.03, R 5 shoulders, flat R 90 top arc "
                 "through the crown Z 32.7) with six transverse stiffening ribs pressed 0.8 into the top (X 296-426, "
                 "pitch 26, stopping at the vertical wall) minus the same construction one sheet thickness in (cavity "
                 "smooth: 0.18 under a rib floor, never seen); the rear end a formed hood whose centreline follows the traced rear profile; open below the "
                 "lip line Z 11.6 and behind X 241 under it; the spring-guide button through a hole in the lip's slope; "
                 "the right skirt cut out over the port (top Z 19.2). Crisp 0.3 breaks on the cut edges.",
    note="realism 2: soft inflated lid (R 8 shoulders, 2.9 crown) -> tight U stamping (R 5, R 90 top); smooth hump -> "
         "the stamped pattern's cross ribs (the receiver's oval dimple is that pattern's; its thin cover has "
         "lengthwise and transverse ribs; the sheet's 3/4 draws transverse lines near X ~316 / ~377)")
dp4("rear_trunnion", "rifle_parts.py + rifle_parts2.rear_tang",
    dims={"upper_tang": {"object": "rear_tang", "X": [208.0, 225.22], "half_width": 9.5, "rear_end": "round (R 9.5)",
                         "proud_of_wood": 0.25, "inlet_depth": 1.35, "thickness": 1.6, "edge_break": 0.3,
                         "screw_X": 219.0, "gap_to_trunnion_face": 0.02}},
    construction="Short steel block at the receiver rear (stepped: the wrist's width back of X ~233.5, the receiver's "
                 "ahead, as the TOP panel measures 34-35.6 then 43-45), vertical rear face into which the stock seats; "
                 "its UPPER TANG a conformal 1.6 mm strap over the wrist's top (X 208-225.2, round rear end) inletted "
                 "flush (0.25 proud), the slotted tang screw through its round end.",
    note="realism 2: no tang (a bare screw head on the wood) -> the stamped pattern's upper tang with the screw on it "
         "(the sheet's TOP panel draws the strap-shaped patch round the screw)")
dp4("buttstock", "rifle_parts2.py",
    dims={"tang_seat": "conformal inlet under the rear tang (outline + 0.02, depth 1.37)",
          "tang_screw": "slotted head r 3.0 on the tang (slot 0.9 wide; object stock_hardware)"},
    note="realism 2: the tang seat and the slotted tang screw on the tang. Rounder sections (exponents 2.8 / 2.55 / "
         "2.35) were tried for 'a flat-sided slab' and dropped: the 3/4 gate's stock-top residual then read 'a width the "
         "TOP allows would fit' (unexplained); round 1's swelling oval stays, the plan taper 38.3 -> 31.9 is the TOP trace")
dp4("handguard_front_band", "rifle_parts2.front_band",
    dims={"pieces": "two: gas-tube collar (upper, from Z 13.45) and lower ferrule (to Z 12.75); 0.7 seam at the "
                    "handguards' joint line", "proud_of_wood": 0.6},
    construction="Two sheet-steel pieces at the handguards' front (X 639.6-647.1): a collar round the upper guard's "
                 "front on the gas tube, and a U ferrule round the lower guard's front with the barrel and "
                 "cleaning-rod holes; outer outlines = the guards' sections + 0.6, split at the joint line.",
    note="realism 2: one band framing both guards -> collar + ferrule (real pattern; the sheet's LEFT and 3/4 draw "
         "the two pieces with a seam)")
dp4("lower_handguard", "rifle_parts2.lower_hg_section",
    dims={"section_fillets": "R 1.5 on the two top corners only (was every vertex: the belly arc's 15 deg vertices "
                             "each took a 0.2 mm 3-segment fillet; 52 -> 22 points, same shape)"},
    note="budget only (no visible change)")
spec["resolutions"] += [
    {"id": "R49", "topic": "Realism round 2 (2026-10-05): hero 3/4 and first-person reasons checked against the real "
                           "pattern and the main views",
     "conflict": "the judges still called the hero 3/4 and the first-person 35 cm views fake: cover a soft inflated lid "
                 "without cross ribs; no upper tang (screw on the wood); one band framing both handguards; stock a "
                 "flat slab; comb bump; straight grip with a decal-like panel; stubby selector; blocky receiver rear",
     "resolution": "FIXED (geometry): cover section R 8 / crown 2.9 -> R 5 shoulders + R 90 top (rise 1.8), six crisp "
                   "transverse ribs pressed 0.8 in (X 296-426; pressed out they stood above the traced top line, broke "
                   "L4 and the 3/4 exception); rear trunnion upper tang (conformal strap X 208-225.2, slotted screw on "
                   "it, stock inletted); front band split into the gas-tube collar and the lower ferrule. REJECTED (with "
                   "reason): flat-sided stock (plan taper 38.3 -> 31.9 is the TOP trace; rounder sections were tried "
                   "and broke the 3/4 exception); comb bump (the LEFT, "
                   "RIGHT and 3/4 panels all draw the comb nose at X 157.5 dropping to the wrist low at 181.5; traced, "
                   "side IoU authority); grip shape (traced side outline, per-part IoU; the real pattern's grip is a "
                   "straight, near-uniform stick with a flared base, as built); checker panel size (c6's panel, as "
                   "built; its light 'decal' read is the review look's plain wood shader -- the texture stage paints "
                   "the cut cells #4E2E1E); selector (80.8 mm, the traced main-view outline and c1, 2.0 mm blade "
                   "closing the slot to Z 8.0); stepped receiver rear (the TOP panel measures the wrist-wide block "
                   "34-35.6 back of X 233 and 43-45 ahead: the real stepped trunnion); cover surface lumps and wood "
                   "colour (rough-look placeholder material).",
     "rule": "real pattern + main views (user decision 2026-10-05); the side / top / 3-4 gates keep passing"},
]

spec["fab_original_changes"] = {
    "status": "NOT applied; the user decides. The game build matches the sheet.",
    "items": [
        "Muzzle: an original device (round two-port brake, or a cylinder with 3 short side slots) instead of the slant cut",
        "Dust cover: two lengthwise stiffening ribs and a stepped rear end (or a 1913-profile rail on top, gun study Q7)",
        "Receiver: own rivet layout (fewer rivets) and a rectangular recess or long pressed rib instead of the oval dimple",
        "Stock: straight comb without the nose step and wrist dip, or an inset cheek panel",
        "Butt plate: rubber pad with 3 horizontal ribs, no screws",
        "Handguards: one long palm swell with three shallow flutes instead of the two side slots; flat-sided band with one screw",
        "Grip: horizontal-groove or hex-stipple panel instead of diamond checkering, subtle finger swell",
        "Gas block: squared front instead of the 45 deg sweep; round gas-tube vents in a 2-2 pattern",
        "Front sight: closed round hood, or ears with round windows",
        "Rear sight: own leaf and slider profile",
        "Magazine: own rib layout (two wide ribs + one cross-rib, or 3 ribs + a waffle panel) and a stepped floor-plate lip",
        "Selector: shorter, wider lever with a hooked tab (or keep an ambidextrous left lever: not on the real pattern)",
        "Trigger guard: squared front",
    ],
    "advice": "four or five together (brake, dust cover, handguard, grip texture, stock) make the silhouette and close-ups "
              "read as the user's own while keeping the classic wooden-rifle feel; none changes frames, sockets or slots",
}

spec["open_questions"] = [
    "Left receiver side: build the real pattern (plain, as default) or copy the RIGHT-labelled panel literally (a second "
    "selector lever on the left)? The pressed groove ahead of the left dimple is built either way (it is drawn).",
    "Grip checkering on the first-person LOD0: normal map only (default) or real pyramids (~3.6k tris per side)?",
    "Fab version: which of the 13 original changes to apply (none applied now)?",
    "SM_AR01 and the magazine: your request named SM_AR01 as the rifle with a separate magazine mesh. The gun study's "
    "default (Q3) also merges a copy of the magazine into the SM_AR01 static twin (for world pickups and drops) while "
    "SM_AR01_Mag stays separate for the reload. Keep the merged copy (default) or ship SM_AR01 without a magazine?",
    "Gun-study defaults carried here (change the build if answered differently): rig pilot SK + SM twin + mag (Q2), black "
    "lacquer finish, Exports/Guns/AR01 (Q20); Metal texture 2048 (R29) or the 4096 fallback.",
]

spec["open_questions"] += [
    "Detail pass (R36): the generated close-ups draw some parts at proportions the side views contradict (front sight "
    "ears ~0.75 as wide, brake ~35 % shorter, magazine longer and more curved, butt plate 0.65x wide). Keep the side "
    "views as the authority (default; a judge on close-up crops can still pick these), or let each close-up govern its "
    "own part and re-gate L2 / L4 for it?",
    "Ejection port opening top Z 21.5 (receiver_right proposal, R40) instead of the built 19.2: needs the L3 port-corner "
    "entry changed (the LEFT trace reads 17).",
    "Butt plate: stock end section following the plate (BP-1) in the stock's next pass?",
]

spec["counts"] = {"parts": len(parts), "parts_rifle": sum(1 for p in parts if not p["asset"].startswith("SM_AR01_Mag")),
                  "parts_mag": sum(1 for p in parts if p["asset"].startswith("SM_AR01_Mag")),
                  "rifle_sockets": len(rifle_sockets), "mag_sockets": len(mag_sockets), "bones": 8,
                  "rivets": len(RIVETS_RIGHT) + len(RIVETS_LEFT)}


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
    if isinstance(o, float):
        return round(o, 4)
    return o


OUT.write_text(json.dumps(clean(spec), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)}: {spec['counts']}")
print(f"Grip M = ({GX:.2f}, {GZ:.2f}); rake {GRIP_RAKE:.2f}; crown {CROWN_Z:.2f}; trigger face {TRIGGER_FACE}; "
      f"butt centre {BUTT_C} tilt {BUTT_TILT:.2f}; hook {HOOK}; insert {INSERT}; mag T {MAG_T}; "
      f"floor rear {FLOOR_REAR} front {FLOOR_FRONT}; A_TOP {A_TOP:.2f} A_BOT {A_BOT_OUT:.2f}/{A_BOT_IN:.2f}; "
      f"R rifle {R_RIFLE:.1f} mag {R_MAG:.1f}; SS mag {SS_MAG}; muzzle X {MUZZLE_X:.2f}; sight pitch {SIGHT_PITCH:.4f}")
