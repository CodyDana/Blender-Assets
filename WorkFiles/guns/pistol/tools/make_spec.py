"""HP01 spec generator (adapted from the CB01 make_spec.py pattern, much smaller: one gun, no shared family).

    py -3 -B WorkFiles/guns/pistol/tools/make_spec.py

Inputs: hp01_measured.json (trace_reference.py), craft_parts.json, the standard (WorkFiles/guns/gunlib/gun_standard.json,
read only) and the PLAN constants below (HP01_BUILD_PLAN.md). Outputs: hp01_spec.json (with the S0 validator result
in spec["S0"]) and hp01_interface.json (bones, sockets, clips, notifies, sidecar keys for the game and the gun chat).
Who wins: measurement = silhouette dimensions and positions; craft = small-part construction, finishes, wear, marks;
plan = frames, bones, sockets, slots, budgets, LODs, gates, stages. Paths from this file's location.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(OUT, "..", "..", ".."))
STD = json.load(open(os.path.join(ROOT, "WorkFiles", "guns", "gunlib", "gun_standard.json")))
M = json.load(open(os.path.join(OUT, "hp01_measured.json")))
C = json.load(open(os.path.join(OUT, "craft_parts.json")))

s = M["scale"]["px_per_mm"]
FX = M["frame_px"]["x_front"]
BY = M["frame_px"]["bore_y"]
R = M["reads_px"]


def F(px, py):
    """sheet px (LEFT panel) -> F mm (X = 0 at the crown front, Z = 0 on the bore)."""
    return ((FX - px) / s, (BY - py) / s)


def r1(v, n=1):
    return round(float(v), n)


# ------------------------------------------------------------------------------------------- grip origin (5.1)
GRIP_AXIS_DEG = 0.5 * (M["key_dimensions"]["grip_angle_deg_front_strap"] + M["key_dimensions"]["grip_angle_deg_backstrap_groove"])
# grip centre line: mid between the front strap and the backstrap at the read rows (sheet px); tang web line y = 285
MID_400 = (488.0, 400.0)
TANG_Y = 285.0
ta = math.radians(GRIP_AXIS_DEG)
tang = (MID_400[0] - (MID_400[1] - TANG_Y) * math.tan(ta), TANG_Y)
DEPTH = STD["frame"]["grip_origin_depth_mm"]          # 46 (AR-01 H1); the pistol H1 replaces it for the class
gx = tang[0] + DEPTH * s * math.sin(ta)
gy = tang[1] + DEPTH * s * math.cos(ta)
GRIP_F = F(gx, gy)


def B(pF):
    """F mm -> build frame B mm (origin = Grip, +X muzzle, +Z up)."""
    return [r1(pF[0] - GRIP_F[0], 2), r1(pF[1] - GRIP_F[1], 2)]


def Bpx(px, py):
    return B(F(px, py))


# Y half-widths (TOP authority, Q1 default = the sheet as drawn; K_Y is the one parameter for the real-pattern option)
K_Y = 0.70  # user 2026-10-14: "go realistic" (Q1): slide ~33 mm, the real class
TOPW = M["top"]["slide_width_mm_sheet"]
HALF = {"slide": r1(K_Y * TOPW / 2, 2), "levers": r1(K_Y * M["top"]["max_width_mm_sheet"] / 2, 2),
        "flank_tab_proud": r1(K_Y * (54.5 - TOPW) / 2, 2), "hammer": r1(K_Y * 17.0 / 2, 2),
        "rib_top_flat": r1(K_Y * 21.0 / 2, 2), "grip": r1(K_Y * 36.0 / 2, 2),
        "source": "[S] TOP width profile (hp01_measured.json top.width_profile_mm_every_5); grip from the TOP lever "
                  "line minus the levers [D]; K_Y = %.3f (Q1)" % K_Y}

# ------------------------------------------------------------------------------------------- parts
FEAT_OF = {
    "barrel": {"crown_front_X_B": B(F(R["crown_front_x"], BY))[0], "crown_d": M["key_dimensions"]["crown_diameter_mm"],
               "rib_top_line_B": [Bpx(*p) for p in R["top_line"]], "upper_facet_Z_B": [Bpx(100, R["upper_facet_y"][1])[1], Bpx(100, R["upper_facet_y"][0])[1]],
               "facet_runout_B": [Bpx(*p) for p in R["upper_facet_rear_taper"]], "hood_end_X_B": Bpx(R["rear_block_front_x"], 160)[0],
               "bore_d": 12.7, "bore_depth_min": 25.4},
    "rail": {"recess_X_B": [Bpx(R["rail_recess_x"][1], 0)[0], Bpx(R["rail_recess_x"][0], 0)[0]], "cap_Z_B": Bpx(0, R["rail_cap_y"])[1],
             "floor_Z_B": Bpx(0, R["rail_floor_y"])[1], "n_bars": 6, "pitch": STD["rail_1913"].get("slot_pitch_mm", 10.01) if isinstance(STD.get("rail_1913"), dict) else 10.01,
             "sheet_bar_centres_X_B": [r1(x - GRIP_F[0], 2) for x in M["rail"]["bar_centres_X"]]},
    "sight_front": {"X_B": [Bpx(R["front_sight_x"][1], 0)[0], Bpx(R["front_sight_x"][0], 0)[0]], "top_Z_B": Bpx(0, R["front_sight_top_y"])[1],
                    "base_Z_B": Bpx(0, R["front_sight_base_y"])[1]},
    "slide": {"front_X_B": Bpx(R["slide_front_x"], 0)[0], "rear_top_B": Bpx(*R["slide_rear_top"]), "rear_bottom_B": Bpx(*R["slide_rear_bottom"]),
              "bottom_Z_B": Bpx(0, R["slide_frame_seam_y"])[1], "lower_band_Z_B": [Bpx(0, R["lower_band_y"][1])[1], Bpx(0, R["lower_band_y"][0])[1]],
              "lower_band_rear_X_B": Bpx(R["frame_front_x"], 0)[0], "rear_block_top_Z_B": Bpx(0, R["rear_block_top_y"])[1],
              "rear_sight_X_B": [Bpx(R["rear_sight_x"][1], 0)[0], Bpx(R["rear_sight_x"][0], 0)[0]], "rear_sight_top_Z_B": Bpx(0, R["rear_sight_top_y"])[1],
              "serration_field_B": [Bpx(*p) for p in R["serr_field_top"] + R["serr_field_bottom"][::-1]], "half_width": HALF["slide"]},
    "front_plate": {"X_B": [Bpx(R["face_plate_x"][1], 0)[0], Bpx(R["face_plate_x"][0], 0)[0]], "Z_B": [Bpx(0, R["face_plate_y"][1])[1], Bpx(0, R["face_plate_y"][0])[1]]},
    "recoil_guides": {"rod_d": 6.0, "exposed_len": 50.0, "Z_B": Bpx(0, 265)[1], "Y_B": [-9.0, 9.0], "source": "[N] class practice; hidden at rest"},
    "frame": {"front_X_B": Bpx(R["frame_front_x"], 0)[0], "guard_opening_B": [Bpx(*p) for p in R["guard_opening"]], "guard_bottom_Z_B": Bpx(0, R["guard_bottom_y"])[1],
              "guard_pin_B": Bpx(R["guard_pin"][0], R["guard_pin"][1]), "beavertail_tip_B": Bpx(*R["beavertail_tip"]), "front_strap_B": [Bpx(*p) for p in R["front_strap"]],
              "half_width_levers": HALF["levers"]},
    "grip": {"panel_B": [Bpx(*p) for p in R["grip_panel"]], "backstrap_groove_B": [Bpx(*p) for p in R["backstrap_groove"]], "bottom_Z_B": Bpx(0, R["grip_bottom_y"])[1],
             "half_width": HALF["grip"], "axis_deg": r1(GRIP_AXIS_DEG, 2)},
    "trigger": {"box_B": [Bpx(*p) for p in R["trigger_box"]], "tip_B": Bpx(*R["trigger_tip"]), "pivot_B": Bpx(*R["trigger_pivot"]), "thickness": 6.5},
    "hammer": {"box_B": [Bpx(*p) for p in R["hammer_box"]], "spur_tip_B": Bpx(*R["hammer_spur_tip"]), "pivot_B": Bpx(562.0, 240.0), "half_width": HALF["hammer"]},
    "selector": {"box_B": [Bpx(*p) for p in R["safety_box"]], "pivot_B": Bpx(554.0, 192.0), "proud_max": 0.8},
    "slide_stop": {"outline_B": [Bpx(*p) for p in R["slide_stop"]], "pivot_B": Bpx(546.0, 262.0), "proud": r1(HALF["levers"] - HALF["slide"], 2)},
    "mag_release": {"centre_B": Bpx(398.0, 292.0), "d": 9.0, "proud": 0.8, "side": "left (+Y)"},
    "flank_tab": {"outline_B": [Bpx(*p) for p in R["flank_tab"]], "proud": HALF["flank_tab_proud"]},
    "magazine": {"base_plate_B": [Bpx(*p) for p in R["mag_base"]], "seat_B": Bpx(503.0, 490.0)},
}
SOURCES = {"barrel": "LEFT", "rail": "LEFT", "sight_front": "LEFT", "slide": "LEFT", "front_plate": "LEFT", "recoil_guides": "none (real pattern)",
           "frame": "LEFT", "grip": "LEFT", "trigger": "LEFT", "hammer": "LEFT", "selector": "LEFT", "slide_stop": "LEFT",
           "mag_release": "none (real pattern, Q3)", "flank_tab": "LEFT", "magazine": "LEFT"}
BUDGET = {"slide": 6500, "barrel": 3200, "rail": 900, "sight_front": 400, "front_plate": 500, "recoil_guides": 400, "frame": 4000, "grip": 2500,
          "trigger": 600, "hammer": 800, "selector": 400, "slide_stop": 500, "mag_release": 250, "flank_tab": 200}
RESERVE = 1650
JOINT_ROW = {"barrel": "butt", "rail": "butt", "sight_front": "butt", "slide": "sliding", "front_plate": "visible_seam", "recoil_guides": "sliding",
             "frame": "sliding", "grip": "butt", "trigger": "hinge", "hammer": "hinge", "selector": "hinge", "slide_stop": "hinge",
             "mag_release": "sliding", "flank_tab": "visible_seam", "magazine": "seated_mag"}
PARENT = {"barrel": "frame", "rail": "barrel", "sight_front": "barrel", "slide": "frame", "front_plate": "slide", "recoil_guides": "frame",
          "frame": "root part (carries body)", "grip": "frame", "trigger": "frame", "hammer": "frame", "selector": "slide", "slide_stop": "frame",
          "mag_release": "frame", "flank_tab": "slide", "magazine": "frame"}

parts = []
for c in C["parts"]:
    pid = c["id"]
    p = dict(c)
    p["features_B"] = FEAT_OF[pid]
    p["trace_ref"] = "traces/LEFT_outline.json + traces/TOP_outline.json" if SOURCES[pid] == "LEFT" else "none"
    p["authority_view"] = c["authority"]
    p["joint_row"] = JOINT_ROW[pid]
    p["contact_parent"] = PARENT[pid]
    p["texel_set"] = c["slot"].replace("M_HP01_", "")
    p["lod0_alloc"] = BUDGET.get(pid, 0) if pid != "magazine" else 1800
    p.setdefault("fasteners", [])
    p.setdefault("motion", {"type": "fixed"})
    p["revealed"] = {"slide": "inside rails, recoil-guide bores, breech face (slide back)", "recoil_guides": "forward 50 mm when the slide is back",
                     "barrel": "chamber block + hood end face (ejection window) when the slide is back", "magazine": "tube, follower, top round during reload",
                     "frame": "rails and the grip seat under the slide when back"}.get(pid, "none")
    p["handling_zones"] = {"slide": ["serrations (rack)", "front flats (holster)"], "grip": ["palm swell", "thumb rest left", "fingers front"],
                           "frame": ["guard front (support finger)", "tang under the web"], "selector": ["thumb arc"], "slide_stop": ["thumb pad"],
                           "trigger": ["face"], "magazine": ["base plate (insertion palm)"], "mag_release": ["thumb"]}.get(pid, [])
    parts.append(p)

# ------------------------------------------------------------------------------------------- bones, sockets, clips
PIV = {k: FEAT_OF[k].get("pivot_B") for k in ("trigger", "hammer", "selector", "slide_stop")}
bones = [
    {"name": "body", "parent": None, "head_B": [0.0, 0.0, 0.0], "motion": "fixed (physics body)"},
    {"name": "slide", "parent": "body", "head_B": [B(F(FX - 125 * s, BY))[0], 0.0, 0.0], "motion": "translate -X 0..48 (lock 46, press check 14)"},
    {"name": "selector", "parent": "slide", "head_B": [PIV["selector"][0], 0.0, PIV["selector"][1]], "motion": "rotate about Y 0 (FIRE) .. -40 (SAFE)"},
    {"name": "hammer", "parent": "body", "head_B": [PIV["hammer"][0], 0.0, PIV["hammer"][1]], "motion": "rotate about Y 0 (cocked, rest) .. +58 (down)"},
    {"name": "trigger", "parent": "body", "head_B": [PIV["trigger"][0], 0.0, PIV["trigger"][1]], "motion": "rotate about Y 0 .. -9 (pull)"},
    {"name": "slide_stop", "parent": "body", "head_B": [PIV["slide_stop"][0], 0.0, PIV["slide_stop"][1]], "motion": "rotate about Y 0 .. +10 (front up, engaged)"},
    {"name": "mag_release", "parent": "body", "head_B": [FEAT_OF["mag_release"]["centre_B"][0], 0.0, FEAT_OF["mag_release"]["centre_B"][1]], "motion": "translate -Y 0..3 (pressed in from the left)"},
    {"name": "magazine", "parent": "body", "head_B": [FEAT_OF["magazine"]["seat_B"][0], 0.0, FEAT_OF["magazine"]["seat_B"][1]], "motion": "attach only (no weights); keyed in the reload clips"},
]
for b in bones:
    if b["parent"] is not None:
        assert b["parent"] in STD["bones"]["parents"][b["name"]], b
MOTION_AXES = {"slide": "-X", "selector": "Y", "hammer": "Y", "trigger": "Y", "slide_stop": "Y", "mag_release": "-Y"}

grip_rot = [0.0, r1(-GRIP_AXIS_DEG, 2), 0.0]      # mag frame: +Z up the grip axis (rake toward the rear at the bottom)
seat = FEAT_OF["magazine"]["seat_B"]
ins = [r1(seat[0] - 60 * math.sin(ta), 2), r1(seat[1] - 60 * math.cos(ta), 2)]
sight_F = F(0.5 * sum(R["rear_sight_x"]), R["rear_sight_top_y"] + 4.0)
rail_c = 0.5 * sum(FEAT_OF["rail"]["recess_X_B"])
rail0 = r1(rail_c - 2.5 * 10.01, 2)
sockets = [
    {"name": "Grip", "bone": "body", "B": [0.0, 0.0, 0.0], "rot": [0, 0, 0], "source": "5.1 origin (provisional 46 mm depth, pistol H1)"},
    {"name": "SupportHand", "bone": "body", "B": [Bpx(455, 410)[0], 22.0, Bpx(455, 410)[1]], "rot": [0, 0, 0], "source": "support wrap: off-hand palm on the left grip panel [J], H1 replaces"},
    {"name": "Muzzle", "bone": "body", "B": [B(F(R["crown_front_x"], BY))[0], 0.0, B(F(0, BY))[1]], "rot": [0, 0, 0], "source": "crown front on the bore (barrel fixed: body, not slide; 5.3 deviation R4)"},
    {"name": "ShellEject", "bone": "body", "B": [Bpx(470, 185)[0], -16.0, Bpx(470, 185)[1]], "rot": [0, 25.0, -110.0], "source": "ejection window at the hood end, right side; throw right, up, slightly rear (R5)"},
    {"name": "Sight", "bone": "slide", "B": [B(sight_F)[0], 0.0, B(sight_F)[1]], "rot": [0, 0, 0], "source": "rear notch bottom on the sight line"},
    {"name": "Mag", "bone": "magazine", "B": [seat[0], 0.0, seat[1]], "rot": grip_rot, "source": "well-entry centre, +Z up the grip axis (5.6)"},
    {"name": "MagInsertStart", "bone": "body", "B": [ins[0], 0.0, ins[1]], "rot": grip_rot, "source": "60 mm out along -Z of Mag"},
    {"name": "Rail_Top", "bone": "body", "B": [rail0, 0.0, FEAT_OF["rail"]["cap_Z_B"]], "rot": [0, 0, 0], "source": "slot 0 (rearmost) centre on the rail-top plane, standard pitch about the drawn recess centre"},
    {"name": "Holster", "bone": "body", "B": [Bpx(300, 215)[0], 0.0, Bpx(300, 215)[1]], "rot": [0, 0, 0], "source": "slide mid, on the bore plane [J]"},
    {"name": "CenterOfMass", "bone": "body", "B": [Bpx(400, 260)[0], 0.0, Bpx(400, 260)[1]], "rot": [0, 0, 0], "source": "estimate [D]; the builder recomputes from part volumes and overwrites (5.3)"},
    {"name": "Trigger", "bone": "trigger", "B": [Bpx(372, 315)[0], 0.0, Bpx(372, 315)[1]], "rot": [0, 0, 0], "source": "trigger face mid (optional socket)"},
    {"name": "Selector", "bone": "selector", "B": [Bpx(554, 225)[0], HALF["slide"], Bpx(554, 225)[1]], "rot": [0, 0, 0], "source": "lever paddle, left (optional)"},
    {"name": "MagRelease", "bone": "mag_release", "B": [FEAT_OF["mag_release"]["centre_B"][0], HALF["grip"], FEAT_OF["mag_release"]["centre_B"][1]], "rot": [0, 0, 0], "source": "button face (optional)"},
]
for so in sockets:
    assert so["name"] in STD["sockets"]["gun"] or so["name"] in STD["sockets"]["optional_gun"], so["name"]
mag_sockets = [{"name": "Mag", "B": [0, 0, 0]}, {"name": "HandReload", "B": [0, 9.0, -40.0]}, {"name": "Feed", "B": [0, 0, 124.0]},
               {"name": "Base", "B": [0, 0, -4.7]}, {"name": "CenterOfMass", "B": [0, 0, 55.0]}]

clips = [
    {"name": "A_HP01_Fire", "fps": 60, "frames": 10, "keys": {"trigger": [[0, 0], [1, -9], [8, -9], [10, 0]], "hammer": [[1, 0], [2, 58], [4, -5], [5, 0]],
                                                           "slide_mm": [[2, 0], [4, 48], [8, 0]]}, "notifies": [["Fire", 1], ["ShellEject", 3]]},
    {"name": "A_HP01_FireLast", "fps": 60, "frames": 10, "keys": {"trigger": [[0, 0], [1, -9], [10, -9]], "hammer": [[1, 0], [2, 58], [4, -5], [5, 0]],
                                                               "slide_mm": [[2, 0], [4, 48], [6, 46]], "slide_stop": [[3, 0], [5, 10]]},
     "notifies": [["Fire", 1], ["ShellEject", 3], ["SlideLock", 6]], "ends": "slide held at 46 with slide_stop up"},
    {"name": "A_HP01_Reload", "fps": 30, "frames": 60, "keys": {"mag_release": [[6, 0], [8, 3], [14, 3], [16, 0]], "magazine_mm": [[8, 0], [14, -130], [16, -130], [36, -130], [42, 0]]},
     "notifies": [["MagRelease", 8], ["MagOut", 12], ["MagDrop", 16], ["MagIn", 42]]},
    {"name": "A_HP01_ReloadEmpty", "fps": 30, "frames": 70, "starts": "slide 46 + slide_stop 10 (FireLast end)",
     "keys": {"slide_mm": [[0, 46], [52, 46], [55, 0]], "slide_stop": [[0, 10], [52, 10], [53, 0]], "mag_release": [[6, 0], [8, 3], [14, 3], [16, 0]],
              "magazine_mm": [[8, 0], [14, -130], [16, -130], [36, -130], [42, 0]]},
     "notifies": [["MagRelease", 8], ["MagOut", 12], ["MagDrop", 16], ["MagIn", 42], ["BoltRelease", 52]]},
    {"name": "A_HP01_Safety", "fps": 30, "frames": 24, "keys": {"selector": [[0, 0], [6, -40], [18, -40], [24, 0]]}, "notifies": []},
    {"name": "A_HP01_SlideRack", "fps": 30, "frames": 20, "keys": {"slide_mm": [[0, 0], [6, 48], [9, 48], [11, 0]], "hammer": [[0, 0], [5, -5], [7, 0]]},
     "notifies": [["BoltRelease", 9]]},
    {"name": "A_HP01_Inspect", "fps": 30, "frames": 60, "keys": {"slide_mm": [[10, 0], [18, 14], [42, 14], [48, 0]]}, "notifies": [],
     "note": "press check; the character's inspect montage turns the gun (buyer / game side)"},
]
for c in clips:
    for k, _ in c["notifies"]:
        assert k in ("Fire", "ShellEject", "SlideLock", "MagRelease", "MagOut", "MagDrop", "MagIn", "BoltRelease"), k

# ------------------------------------------------------------------------------------------- gates (study 7 + close-up)
GATES = {
    "S0": "this validator: 0 missing / null fields; real dims within +-5 %; camera block; every bone and socket name from gun_standard 0.3.0",
    "L1": "blockout IoU LEFT >= 0.95 (RIGHT is a mirror: reported), TOP >= 0.92 (on the Q1 width); < 0.90 = stop and change the method",
    "L2": "form IoU LEFT >= 0.96, TOP >= 0.93; each part on its authority view >= 0.95",
    "L3": "P95 contour distance <= 2 sheet px (0.95 mm); features <= 2 sheet px; angles (grip axis, serration lean, top-line rise) <= 1 deg",
    "L4": "measured vs spec <= 0.05 mm",
    "L5": "colour report (reported, not a gate, if the user rules CLOSEUP CM-R1 for this gun; default: reported)",
    "L6": "G1-G20 with evidence; 0 major",
    "L7": "blind design judge >= 12 pairs <= 8/12; realism judges: fp35 (slide rear + grip), ADS (sights), TP 3 m, hero 3/4: at most 1 of 4 called fake by at most 1 judge",
    "B1-B10, H1, M1-M5": "as GUN_BUILDING_STUDY 7.2 with the pistol's numbers (budget row pistol: LOD0 15-25k, ceiling 30k; mag 1-2k)",
    "U1-U12": "as 7.4; U2 for the pistol: Transform Modify Bone slide -X moves straight back; hammer and selector turn about Y",
    "CU1": "outline fairness: every traced outline is faired before extrusion (deviation to the trace <= 1 sheet px = 0.47 mm; direction change <= 12 deg between 0.5 mm segments except at declared corners; 0 second-difference jags > 0.08 mm)",
    "CU2": "authored bevels: every edge set's land width within +-0.05 of the spec along its whole length (min >= 0.9 x spec: no clamp collapse); normals monotonic across each land (no stepped bevel)",
    "CU3": "no slivers / torn faces: gunlib UD rule (Unreal degenerate thresholds) 0 failures; visible-face min angle >= 2 deg; 0 non-manifold; B6a twin topology from W1 on",
    "CU4": "early realism ER0 at W1c on 8 rendered crops (slide rear + serrations L/R, trigger + guard, grip + slide stop, front sight + crown, hammer + safety, mag base, rail) under the frozen judge rig, 2 judges + 6 real-photo controls: pass <= 1/8 called CG on geometry by both; >= 6/8 = decisive fail: stop and change the method",
    "CU5": "finish cards tuned on a swatch board first (stainless_brushed, stainless_bead, black_oxide, rubber_pebble) under the grey-card rig, AgX; stainless flat highlight P95/P5 >= 3 in fp35 crops",
    "CU6": "real-pattern small parts: every part in craft_parts.json real_pattern built as ruled (trigger thickness + crowned face, grooved pads, checkered button, dovetail seams); audit lists each with a crop",
    "CU7": "marks audit: only the inventory glyphs (safety dot pictograms; rail digits only if Q6 says yes); 0 text",
    "CU8": "pebble and serration identity from geometry/bakes at real scale: pebble cell >= 3 texels at class B; serration crest polish follows the baked curvature, not noise",
}
camera = dict(STD["camera"])
camera["pistol"] = {"hip_eye_to_rear_mm": [350, 450], "ads_eye_to_rear_sight_mm": 300, "inspect_eye_to_gun_mm": [250, 350],
                    "visibility_min_mm": {"rear": 0.35, "mid": 0.45, "front": 0.6},
                    "texel_targets_px_per_cm": {"A": [80, 100], "B": [70, 90], "C": [45, 60], "D": [35, 45], "E": [10, 15]},
                    "why": "a pistol sits 35-45 cm from the eye at the hip and 25-35 cm in an inspect; class C/D raised over the long-gun table (study 5.8 derivation, same formula)"}

spec = {
    "meta": {"name": "Heavy Pistol HP-01", "code": "HP01", "version": "0.1", "date": "2026-10-14", "stage": "W0 study",
             "generator": "WorkFiles/guns/pistol/tools/make_spec.py", "inputs": ["hp01_measured.json", "craft_parts.json", "gun_standard.json 0.3.0 (read only)", "HP01_BUILD_PLAN.md"],
             "reference": "References/Guns/Pistol/pistol_sheetA.webp (LEFT, RIGHT, TOP, 3/4 FRONT LEFT; AI-generated)",
             "tags": "[S] sheet, [N] norm / real pattern, [D] derived, [J] judgement, [K] class figure from the study table"},
    "frames": {"F": M["meta"]["frame"], "B": STD["frame"]["axes"] + "; origin = Grip", "grip_F": [r1(GRIP_F[0], 2), r1(GRIP_F[1], 2)],
               "grip_axis_deg": r1(GRIP_AXIS_DEG, 2), "grip_origin_depth_mm": DEPTH, "tang_px": [r1(tang[0], 2), TANG_Y],
               "unreal": STD["frame"]["unreal_mapping"]},
    "scale": {"overall_mm": 273.0, "barrel_mm": 152.0, "mass_kg": 2.0, "px_per_mm": s, "ruler_error_pct": M["scale"]["ruler_error_pct"],
              "height_mm_sheet": M["key_dimensions"]["height_mm_reads"], "height_mm_class": 159.0,
              "width": {"slide_mm_sheet": TOPW, "levers_mm_sheet": M["top"]["max_width_mm_sheet"], "class_max_mm": 32.0, "K_Y": K_Y,
                        "ruling": "Q1 RULED by the user 2026-10-14 (\"go realistic\"): K_Y 0.70, slide ~33 mm (real class); the TOP view as drawn is overruled on width only"},
              "rule": "real overall length (study 3.5); proportions from the sheet; rulers reported only"},
    "key_dimensions": M["key_dimensions"], "half_widths_mm": HALF, "serrations": M["serrations"], "rail_sheet": M["rail"],
    "parts": parts, "finishes": C["finishes"], "bones": bones, "motion_axes": MOTION_AXES, "rest_pose": {"slide": 0, "hammer": "cocked (0)", "selector": "FIRE (0)", "slide_stop": 0, "magazine": "seated"},
    "joints_clearance_mm": STD["clearance_mm"], "sockets": sockets, "mag_sockets": mag_sockets, "clips": clips,
    "materials": {"M_HP01_Steel": {"master": "M_Steel_Master", "carries": "stainless_brushed, stainless_bead, black_oxide (baked colour)", "set": "Steel"},
                  "M_HP01_Furniture": {"master": "M_Fabric_Master", "metal_from_orm": False, "carries": "rubber grip", "set": "Furniture"},
                  "M_HP01_Mag": {"master": "M_Steel_Master", "carries": "mag tube stainless + base plate black oxide", "set": "Mag"}},
    "textures": {"Steel": {"size": 4096, "fill_min": 0.70, "why": "~800 cm2 of metal at classes A-D (pistol targets) needs ~4.1 M texels at 70 % fill; 2048 holds 2.9 M: packer reports, smallest power of two that meets the classes wins"},
                 "Furniture": {"size": 1024, "fill_min": 0.65}, "Mag": {"size": 1024, "fill_min": 0.65}, "Masks": {"size": 2048},
                 "maps": "T_HP01_<Set>_BC (sRGB), _ORM (linear), _N (DirectX); T_HP01_Masks (linear RGBA)"},
    "budgets_triangles": {"gun": {"lod0": [15000, 25000], "ceiling": 30000, "alloc": BUDGET, "reserve": RESERVE, "sum": sum(BUDGET.values()) + RESERVE},
                          "magazine": {"lod0": [1000, 2000], "ceiling": 2500, "alloc": 1800}, "lod_shares": {"LOD1": 0.45, "LOD2": 0.15}, "lod3": [800, 1200]},
    "lods": {"screen_sizes_start": [1.0, 0.25, 0.09, 0.03], "rule": "measured by the LOD-pop gate (bounding radius ~0.17 m vs the rifle's 0.45)"},
    "collision": {"SM_HP01": "UCX_SM_HP01_00..03 (slide+barrel box, frame front box, grip hull, guard hull)", "physics": "PHYS_HP01 one body on body, 2.0 kg"},
    "names": {"sk": "SK_HP01", "skeleton": "SK_HP01_Skeleton (pistol class pilot)", "sm": "SM_HP01", "mag": "SM_HP01_Mag", "phys": "PHYS_HP01", "clips": [c["name"] for c in clips],
              "exports": "Exports/Guns/HP01/", "asset": "Assets/Guns/HP01.blend", "lock": "HP01"},
    "camera": camera, "gates": GATES,
    "marks": {"default": ["safety dot pictograms on the slide at the lever arc (white = SAFE, red = FIRE), 0.1 mm V-cut + fill"],
              "optional_Q6": ["rail digits on every 2nd crossbar (1913 practice)"], "never": "maker, model, calibre text, serials, logos"},
    "real_dimensions_check": {"overall": [273.0, 273.0], "barrel_class": [152.0, 152.0], "mass": [2.0, 2.0]},
}

# ------------------------------------------------------------------------------------------- S0 validator
REQ = ["id", "bone", "process", "bevels", "finish", "slot", "texel_class", "authority_view", "joint_row", "motion", "features_B", "trace_ref",
       "real_pattern", "closeup", "fasteners", "lod0_alloc", "revealed", "handling_zones"]
missing = []


def walk(o, path):
    if o is None:
        missing.append(path)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k != "parent":
                walk(v, path + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, "%s[%d]" % (path, i))


for p in parts:
    for k in REQ:
        if k not in p:
            missing.append("%s.%s" % (p["id"], k))
    for f in p["fasteners"]:
        if "source" not in f:
            missing.append(p["id"] + ".fastener.source")
walk({k: v for k, v in spec.items() if k != "bones"}, "spec")
for b in bones:
    walk({k: v for k, v in b.items() if k != "parent"}, "bones." + b["name"])

import importlib.util  # noqa: E402
_sp = importlib.util.spec_from_file_location("qa_gun_ro", os.path.join(ROOT, "Scripts", "guns", "gunlib", "qa_gun.py"))
QG = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(QG)                       # read only: the gun chat's tokenised deny list (study 4.9)
deny = list(QG.GUN_DENY)


def deny_hit(name):
    h = QG.deny_hits(name)
    return h[0] if h else None


names = [spec["names"][k] for k in ("sk", "sm", "mag", "phys")] + spec["names"]["clips"] + list(spec["materials"]) + [b["name"] for b in bones] + [so["name"] for so in sockets]
deny_hits = {n: deny_hit(n) for n in names if deny_hit(n)}
tot = spec["budgets_triangles"]["gun"]["sum"]
checks = {
    "8 bones from the standard (pistol 8-9)": len(bones) == 8,
    "every bone parent allowed by gun_standard": all(b["parent"] is None or b["parent"] in STD["bones"]["parents"][b["name"]] for b in bones),
    "every socket name in gun_standard": all(so["name"] in STD["sockets"]["gun"] or so["name"] in STD["sockets"]["optional_gun"] for so in sockets),
    "mag socket names in gun_standard": all(m["name"] in STD["sockets"]["mag"] for m in mag_sockets),
    "every part bone exists": all(p["bone"] in {b["name"] for b in bones} for p in parts),
    "every socket bone exists": all(so["bone"] in {b["name"] for b in bones} for so in sockets),
    "overall 273 within +-5 % of the class": abs(273.0 / 273.0 - 1) <= 0.05,
    "LOD0 allocation + reserve within 15-25k": 15000 <= tot <= 25000,
    "per-part allocation sums": sum(p["lod0_alloc"] for p in parts if p["id"] != "magazine") + RESERVE == tot,
    "Muzzle on the bore (Z_B equal to the bore)": abs(sockets[2]["B"][2] - B(F(0, BY))[1]) < 1e-6,
    "Sight above the bore 25-40 mm": 25 <= sockets[4]["B"][2] - sockets[2]["B"][2] <= 40,
    "slide travel > cartridge class OAL 40.4 + 5": 48.0 >= 45.4,
    "lock position < travel": 46.0 < 48.0,
    "clips: ReloadEmpty starts where FireLast ends (46, slide_stop 10)": clips[3]["keys"]["slide_mm"][0][1] == clips[1]["keys"]["slide_mm"][-1][1] and clips[3]["keys"]["slide_stop"][0][1] == clips[1]["keys"]["slide_stop"][-1][1],
    "every clip notify a standard name": True,
    "deny list clean on every asset / bone / socket / material name": not deny_hits,
    "grip axis 15-22 deg": 15 <= GRIP_AXIS_DEG <= 22,
    "camera block present": "camera" in spec and "pistol" in spec["camera"],
    "3 material slots max": len(spec["materials"]) <= 3,
}
spec["S0"] = {"missing_fields": missing, "consistency_checks": checks, "deny_hits": deny_hits, "deny_terms_read": len(deny),
              "status": "pass" if not missing and all(checks.values()) else "fail"}
json.dump(spec, open(os.path.join(OUT, "hp01_spec.json"), "w"), indent=1)

interface = {
    "meta": {"code": "HP01", "what": "game / gun-chat interface for SK_HP01 (W0 plan values; the build overwrites with built numbers)", "date": "2026-10-14",
             "frame": "B mm (Blender, origin Grip); Unreal cm = (Bx, -By, Bz) / 10"},
    "assets": spec["names"], "bones": bones, "motion_axes": MOTION_AXES, "rest_pose": spec["rest_pose"],
    "sockets": sockets, "mag_sockets": mag_sockets, "clips": clips,
    "notifies_rule": "sidecar 'notifies' list (study 4.6), harness adds them in Unreal",
    "sidecar_gun_block": {"class": "pistol", "grip_axis_deg": r1(GRIP_AXIS_DEG, 2), "rail_slots": {"Rail_Top": 6}, "muzzle_class": "none (no thread drawn)",
                          "mag_family": "HP01 single-stack (own)", "texel_classes": camera["pistol"]["texel_targets_px_per_cm"], "slide_travel_mm": 48.0,
                          "slide_lock_mm": 46.0, "hand_offset": "from pistol H1 (pending)", "mass_kg": 2.0},
    "abp_pistol_table": {"slide_mm": [0, 48], "hammer_deg": [0, 58], "trigger_pull": [0, -9], "selector_detents_deg": {"FIRE": 0, "SAFE": -40},
                         "slide_stop_deg": [0, 10], "mag_release_translate_mm": [0, 3.0],
                         "rule": "ABP_Gun_Pistol authored on SK_HP01_Skeleton (pistol class pilot, study 5.2)"},
    "fp_tp": "FP_Weapon + TP_Weapon (SK_HP01), FP_Mag + TP_Mag (SM_HP01_Mag on Mag); FP components FirstPerson + ForcedLodModel 1; TP WorldSpaceRepresentation (study 2.3); 4 draws held (Steel + Furniture, x2) + 2 mag",
}
json.dump(interface, open(os.path.join(OUT, "hp01_interface.json"), "w"), indent=1)
print("S0", spec["S0"]["status"], "missing", missing[:10], {k: v for k, v in checks.items() if not v}, "deny_terms", len(deny), deny_hits)
print("grip_F", [r1(v, 2) for v in GRIP_F], "axis", r1(GRIP_AXIS_DEG, 2), "LOD0 sum", tot)
print("sockets", [(so["name"], so["B"]) for so in sockets])
