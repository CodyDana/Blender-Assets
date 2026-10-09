"""AR-01 surfacing rules (plain Python, imported by the UV, bake, paint and game stages).

Sets, texel classes, per-part UV frames and the finish of every part. Numbers: rifle_spec.json (materials, textures),
GUN_BUILDING_STUDY 3.3 / 3.4 / 5.8, and the user's decision (4) of 2026-10-04: ADS-sharp metal, class A 80-100 px/cm
on the ADS-visible parts (rear sight, dust cover top, front sight, receiver top) and class B 60-80 everywhere else on
the metal; the Metal set goes to 4096 if 2048 cannot hold that at >= 70 % fill.
"""
from __future__ import annotations

import math

# ---------------------------------------------------------------- sets (UV0 atlases) and material slots
SETS = {
    "Metal": {"slot": "M_AR01_Metal", "sizes": (2048, 4096), "fill_min": 0.70, "gap_px": {2048: 4, 4096: 8},
              "cell_px": {2048: 2, 4096: 4},
              "classes": {"A": 100.0, "B": 80.0, "E": 12.0},          # packing ratios (px/cm at scale 1)
              "bands": {"A": (80.0, 100.0), "B": (60.0, 80.0), "E": (8.0, 15.0)}},
    "Furniture": {"slot": "M_AR01_Furniture", "sizes": (2048,), "fill_min": 0.65, "gap_px": {2048: 4},
                  "cell_px": {2048: 2},
                  "classes": {"B": 70.0, "C": 35.0, "E": 12.0},
                  "bands": {"B": (60.0, 80.0), "C": (30.0, 40.0), "E": (8.0, 15.0)}},
    # Mag: the smallest of 1024 / 2048 that holds class C at >= 65 % fill (plan 5.3 named 2048, which puts C at
    # ~93 px/cm, 2.3x the band top: outside the stage-3 gate "per-class density within +-25 %"; 1024 gives ~47)
    "Mag": {"slot": "M_AR01_Mag", "sizes": (1024, 2048), "fill_min": 0.65, "gap_px": {1024: 2, 2048: 4},
            "cell_px": {1024: 1, 2048: 2},
            "classes": {"C": 35.0, "E": 12.0},
            "bands": {"C": (30.0, 40.0), "E": (8.0, 15.0)}},
}
SLOT_SET = {v["slot"]: k for k, v in SETS.items()}
# density ceiling (stage-3 gate: per-class density within +-25 % of the class band): the packer's scale is capped so
# no class median exceeds 1.25 x its band top (a bigger set than the floors need otherwise over-fills its classes)
DENSITY_CEIL = 1.25
CLASS_CODE = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
CODE_CLASS = {v: k for k, v in CLASS_CODE.items()}

GRIP_M = (263.18, 0.0, -78.54)           # frame B = M - Grip (spec frames.B)
BORE_Z_B = 78.54

# ---------------------------------------------------------------- UV frames (gunlib.uvchart)
# round parts: cylinder charts about their X axis (centre from the part's own bounds in YZ); the grip: a box frame
# raked with its axis (22.35 deg from vertical, top toward the muzzle); everything else: the gun frame
CYL_PARTS = ("barrel", "gas_tube", "cleaning_rod", "gas_piston", "muzzle_brake")
# the curved magazine: a cylinder frame about its arc centre (spec magazine dims arc_centre_M (604.8, 3.3), axis Y), the
# seam opposite the magazine; front / rear faces unwrap to straight strips, the sides to annulus strips (polar caps)
MAG_ARC_PARTS = ("magazine", "magazine_floor_plate")
MAG_ARC_C_M = (604.8, 0.0, 3.3)
MAG_ARC_U0 = (-0.866, 0.0, -0.5)          # toward the magazine (mid angle about -150 deg in XZ)
GRIP_RAKE_DEG = 22.35
FRAME_ROT_Y = {"pistol_grip": -GRIP_RAKE_DEG}

# ---------------------------------------------------------------- texel classes per face (rules; hidden faces -> E)
A_PARTS = ("rear_sight_block", "rear_sight_leaf", "rear_sight_slider", "front_sight_block", "front_sight_post")
A_TOP_PARTS = ("dust_cover", "recoil_spring_button")          # their up-facing faces (n_z >= 0.55: the +Z chart)
A_RECEIVER_TOP = ("receiver", "rear_trunnion", "receiver_rails")   # up-facing faces at or above the bore line - 5


def face_class(part, set_name, z_M, n_z, visible):
    """Texel class of one face (z_M: face centre height in frame M, mm; n_z: normal Z)."""
    if not visible:
        return "E"
    if set_name == "Metal":
        if part in A_PARTS:
            return "A"
        if part in A_TOP_PARTS and n_z >= 0.55:
            return "A"
        if part in A_RECEIVER_TOP and n_z >= 0.55 and z_M >= -5.0:
            return "A"
        if part == "rivets" and z_M >= 25.0:                  # the dust-cover crown studs
            return "A"
        return "B"
    if set_name == "Furniture":
        if part == "pistol_grip" and z_M >= -62.0:            # grip top (the web of the hand, seen in first person)
            return "B"
        if part == "buttstock" and n_z >= 0.35:               # comb and wrist top (cheek weld, first person)
            return "B"
        return "C"
    return "C"


# ---------------------------------------------------------------- LOD3 (blockout) part -> set
LOD3_WOOD = ("upper_handguard", "lower_handguard", "pistol_grip", "buttstock")
LOD3_MAG = ("magazine",)


def lod3_set(base):
    if base in LOD3_WOOD:
        return "Furniture"
    if base in LOD3_MAG:
        return "Mag"
    return "Metal"


# ---------------------------------------------------------------- finishes (rifle_spec materials.finishes)
def srgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


FIN = {
    "lacquer": {"metal": 0, "srgb": srgb("#353535"), "rough": (0.40, 0.55)},
    "lacquer_mag": {"metal": 0, "srgb": srgb("#313131"), "rough": (0.45, 0.60)},
    "lacquer_worn": {"metal": 0, "srgb": srgb("#383838"), "rough": (0.50, 0.50),
                     "note": "spec #3F3F3F; L5 (the plate's band reads 51 in the sheet's side view) -> #383838, 7 levels "
                             "darker, inside the +-12 finish check"},
    "lacquer_cover": {"metal": 0, "srgb": srgb("#474747"), "spec_srgb": srgb("#3F3F3F"), "rough": (0.48, 0.62),
                      "note": "the dust cover: spec lacquer_worn #3F3F3F (the most rubbed pressed sheet on the gun); "
                              "L5 (the sheet's cover reads 89 against the receiver's 63 under one light) -> #474747, "
                              "8 levels lighter, inside the +-12 finish check against the spec value"},
    # realism-fix round 2026-10-07 (review: the stamped selector / trigger / catch flashed chrome): satin bluing on the
    # small stamped parts, 0.45-0.55 (spec range 0.30-0.55, its upper half)
    "bluing": {"metal": 1, "srgb": srgb("#787878"), "rough": (0.45, 0.55)},
    "bare": {"metal": 1, "srgb": srgb("#C3C3C1"), "rough": (0.25, 0.40), "sliding": (0.15, 0.25)},
    "walnut": {"metal": 0, "srgb": srgb("#6B3C27"), "grain_dark": srgb("#482C1B"), "figure_light": srgb("#965F46"),
               "handling": srgb("#87573F"), "checker": srgb("#4E2E1E"), "rough": (0.42, 0.60)},
    "grime": {"metal": 0, "srgb": srgb("#2A2826"), "rough": 0.80},
    "soot": {"metal": 0, "lin": 0.025, "rough": (0.80, 0.95)},
}

# part -> (finish, wear profile). Wear: edge = chip wear to bare steel on convex edges (moderate, the sheet's own);
# 'slide' = polished bare on sliding faces; 'scratched' = the butt plate's dense scratches
PART_FINISH = {
    "receiver": "lacquer", "rear_trunnion": "lacquer", "rear_tang": "lacquer", "dust_cover": "lacquer_cover", "receiver_rails": "bluing",
    "recoil_spring_button": "bluing", "rivets": "lacquer", "bolt_carrier": "bluing", "rear_sight_block": "lacquer",
    "rear_sight_leaf": "bluing", "rear_sight_slider": "bluing", "handguard_retainer": "bluing",
    "gas_tube_rear_cap": "lacquer", "handguard_front_band": "lacquer", "gas_tube": "lacquer", "gas_piston": "bare",
    "gas_block": "lacquer", "barrel": "lacquer", "cleaning_rod": "bluing", "front_sight_block": "lacquer",
    "front_sight_post": "bluing", "muzzle_brake": "lacquer", "trigger": "bluing", "trigger_guard": "lacquer",
    "mag_catch": "bluing", "butt_plate": "lacquer_worn", "butt_screws": "bluing", "sling_swivel_base": "lacquer",
    "sling_swivel_loop": "bluing", "stock_hardware": "bluing", "selector": "bluing",
    "upper_handguard": "walnut", "lower_handguard": "walnut", "pistol_grip": "walnut", "buttstock": "walnut",
    "magazine": "lacquer_mag", "magazine_floor_plate": "lacquer_mag",
}

# per-part wood value (one stain hue; the sheet draws the upper handguard lighter and the grip slightly darker than the
# stock: side-panel medians 146 / 100 / 108 at R)
WOOD_VALUE = {"upper_handguard": 1.12, "lower_handguard": 1.04, "pistol_grip": 0.97, "buttstock": 1.0}
# wood grain axis per part (frame B unit vectors): along the bore for the handguards, along the raked axis for the
# grip, along the stock's comb line for the stock
_a = math.radians(GRIP_RAKE_DEG)
GRAIN_AXIS = {"upper_handguard": (1.0, 0.0, 0.0), "lower_handguard": (1.0, 0.0, 0.0),
              "pistol_grip": (math.sin(_a), 0.0, math.cos(_a)), "buttstock": (0.985, 0.0, 0.174)}

# handling zones (gun study 3.4 G channel): firing hand on the grip straps, support hand on the lower handguard's belly
# and left side, cheek weld on the comb's left, thumb travel on the selector's arc; positions frame M (mm)
HANDLING = [
    {"part": "pistol_grip", "center_M": (268.0, 0.0, -70.0), "radius": 40.0, "w": 0.9},
    {"part": "lower_handguard", "center_M": (562.0, 8.0, -24.0), "radius": 45.0, "w": 0.8},
    {"part": "upper_handguard", "center_M": (590.0, 6.0, 30.0), "radius": 35.0, "w": 0.35},
    {"part": "buttstock", "center_M": (150.0, 14.0, 8.0), "radius": 55.0, "w": 0.6},
]
HOT_PARTS = ("gas_block", "barrel", "gas_tube", "front_sight_block", "muzzle_brake", "handguard_front_band")
# soot (heat and gas): brake cut, gas block vents, port; frame M centres and radii (mm)
SOOT = [{"center_M": (870.0, 0.0, 0.0), "radius": 16.0, "w": 1.0},
        {"center_M": (700.0, 0.0, 24.0), "radius": 14.0, "w": 0.6},
        {"center_M": (395.0, -20.0, 10.0), "radius": 22.0, "w": 0.35}]

# ---------------------------------------------------------------- metal wear placement (stage 3 on the r4 geometry)
# Chip wear to bare steel is NOT uniform: it follows where hands, slings, the ground and the magazine change wear a
# stamped-receiver rifle, and where the sheet draws its bright worn edges (the brake rim, the front sight ears, the
# receiver's lower edges round the magazine well, the dust cover's shoulders, the charging handle and selector tab,
# the guard's bottom, the magazine's spine / ribs / floor plate, the butt plate rim). Edge wear propensity =
# WEAR_BASE + (1 - WEAR_BASE) x the strongest zone falloff (frame M centres, mm).
WEAR_BASE = 0.30
METAL_WEAR = [
    {"what": "brake rim and slant cut (the muzzle end; the base collar sees base wear only)",
     "center_M": (876.0, 0.0, 0.0), "radius": 20.0, "w": 1.0},
    {"what": "front sight ears / post", "center_M": (826.0, 0.0, 38.0), "radius": 17.0, "w": 0.95},
    {"what": "front sight block base, rod lug", "center_M": (815.0, 0.0, -14.0), "radius": 22.0, "w": 0.55},
    {"what": "gas block corners", "center_M": (700.0, 0.0, 22.0), "radius": 24.0, "w": 0.45},
    {"what": "front band / handguard retainer", "center_M": (640.0, 0.0, 0.0), "radius": 20.0, "w": 0.5},
    {"what": "receiver lower edges round the magazine well", "center_M": (430.0, 0.0, -30.0), "radius": 48.0, "w": 0.85},
    {"what": "rear sight block and leaf edges", "center_M": (450.0, 0.0, 40.0), "radius": 26.0, "w": 0.6},
    # stage-7 fix round (craft review: the knob read as a chrome ball, 79 % bare): bare only at its tip / edges
    {"what": "charging handle", "center_M": (452.0, -40.0, 14.0), "radius": 12.0, "w": 0.6},
    {"what": "dust cover shoulders", "center_M": (330.0, 0.0, 28.0), "radius": 70.0, "w": 0.45},
    # (stage-7 fix round: at r 22 / w 0.95 the rub spread into a uniform light-grey halo round the button hole in
    # first person; the thumb wears the button and the hole's rim, not a disc of the cover)
    {"what": "dust cover rear lip and the recoil spring button (thumb)", "center_M": (247.0, 0.0, 22.0),
     "radius": 12.0, "w": 0.6},
    {"what": "receiver flanks under the firing hand / cheek", "center_M": (320.0, 0.0, -10.0), "radius": 55.0, "w": 0.55},
    {"what": "selector tab (thumb)", "center_M": (362.0, -24.0, -6.0), "radius": 20.0, "w": 1.0},
    {"what": "trigger guard bottom", "center_M": (335.0, 0.0, -60.0), "radius": 30.0, "w": 0.75},
    {"what": "magazine floor plate and toe", "center_M": (478.0, 0.0, -160.0), "radius": 48.0, "w": 0.95},
    {"what": "magazine spine and rib crests", "center_M": (472.0, 0.0, -88.0), "radius": 70.0, "w": 0.55},
    {"what": "butt plate rim", "center_M": (4.0, 0.0, -40.0), "radius": 85.0, "w": 0.85},
]
# scuff direction per part (frame M unit vectors): along the bore for the receiver, cover, barrel and gas parts (rubbed
# in and out of a rack / sling); the magazine down its curve (pulled from pouches)
# STAGE-7 FIX ROUND (realism judges: 'even white streaks along every rib and edge: the classic look of an automatic
# edge-wear generator; real wear clusters at the feed lips, the front lug, the floor plate edges and the spine contact
# points'; craft / tech: white chips and dashed lines along the magazine's spine): the magazine's own wear zones (frame
# M, seated). They REPLACE the rifle's METAL_WEAR on the magazine's lacquer; outside them no chip and only a faint rub
MAG_WEAR = [
    {"what": "feed lips and the top block (cartridges, loading)", "center_M": (395.0, 0.0, -14.0), "radius": 22.0,
     "w": 1.0},
    {"what": "front locking lug (rocked onto the trunnion every reload)", "center_M": (424.0, 0.0, -20.0),
     "radius": 9.0, "w": 0.9},
    {"what": "rear lug on the catch", "center_M": (370.0, 0.0, -37.0), "radius": 9.0, "w": 0.9},
    {"what": "spines at the well's lower edge", "center_M": (428.0, 0.0, -33.0), "radius": 10.0, "w": 0.6},
    {"what": "rear spine at the well's lower edge", "center_M": (369.0, 0.0, -33.0), "radius": 8.0, "w": 0.6},
    {"what": "floor plate and its edges (dropped, slapped, rested on)", "center_M": (475.0, 0.0, -162.0),
     "radius": 26.0, "w": 0.95},
]
SCUFF_AXIS = {"magazine": (0.45, 0.0, -0.89), "magazine_floor_plate": (1.0, 0.0, 0.0),
              "butt_plate": (0.0, 0.0, 1.0), "trigger_guard": (1.0, 0.0, 0.0)}
# how scuffed each lacquered part is (x the shared scuff field; the sheet's dust cover is the most rubbed surface)
SCUFF_W = {"dust_cover": 0.45, "receiver": 1.0, "magazine": 1.1, "barrel": 0.9, "gas_block": 0.9, "gas_tube": 0.9,
           "front_sight_block": 1.0, "muzzle_brake": 1.0, "rear_trunnion": 0.8, "rear_tang": 0.8,
           "handguard_front_band": 0.9, "trigger_guard": 0.9, "rear_sight_block": 0.8}
# wood handling damage density per part (dents, scratches; the sheet's grip is the most dinged)
DENT_W = {"pistol_grip": 1.6, "buttstock": 1.0, "lower_handguard": 1.2, "upper_handguard": 0.9}
