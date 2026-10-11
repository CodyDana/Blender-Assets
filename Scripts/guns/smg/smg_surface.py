"""SMG01 surfacing rules (plain Python; imported by the W2 UV, bake, paint, recolour, render and gate steps).

Sets, texel classes, UV frames, finishes and wear placement for the Compact SMG SM-01. Numbers: smg_spec.json
(textures.texel_classes_px_per_cm / class_assignment / sets, materials.finishes / wear_logic, parts[].texel_class /
wear), SMG_BUILD_PLAN 9, GUN_BUILDING_STUDY 3.3 / 3.4 / 5.8, and the AR-01's stage-3 lessons (RIFLE_REPORT 10):
bake margin 0, the magazine's AO alone, same-side edge masks, analytic wear.

Frames: M = the spec's measurement frame (mm, X from the butt-pad rear, Z up, +Y = the gun's left); B = M - Grip
(the Blender frame; part meshes are in B metres, the UV code works in B mm).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from smg_common import D, GRIP, BORE_Z, dims  # noqa: E402

GRIP_M = tuple(float(v) for v in GRIP)
BORE_Z_B = BORE_Z - GRIP_M[2]

# ---------------------------------------------------------------- sets (UV0 atlases) and material slots
# packing ratios (px/cm at scale 1) = the middle of each class band (spec textures.texel_classes_px_per_cm); every set
# is the smallest power of two that holds its classes' floors at the fill minimum (spec textures.rule; the packer
# decides, with the AR-01's x2.3 estimate lesson: no size is assumed)
BANDS = {k: tuple(float(x) for x in v) for k, v in D["textures"]["texel_classes_px_per_cm"].items()}
RATIO = {k: 0.5 * (v[0] + v[1]) for k, v in BANDS.items()}
SETS = {
    "Metal": {"slot": "M_SMG01_Metal", "sizes": (2048, 4096), "fill_min": 0.70, "gap_px": {2048: 4, 4096: 8},
              "cell_px": {2048: 2, 4096: 4}, "classes": {c: RATIO[c] for c in "ABCDE"},
              "bands": {c: BANDS[c] for c in "ABCDE"}},
    "Furniture": {"slot": "M_SMG01_Furniture", "sizes": (2048, 4096), "fill_min": 0.65, "gap_px": {2048: 4, 4096: 8},
                  "cell_px": {2048: 2, 4096: 4}, "classes": {c: RATIO[c] for c in "BCE"},
                  "bands": {c: BANDS[c] for c in "BCE"}},
    "Mag": {"slot": "M_SMG01_Mag", "sizes": (1024, 2048), "fill_min": 0.65, "gap_px": {1024: 2, 2048: 4},
            "cell_px": {1024: 1, 2048: 2}, "classes": {c: RATIO[c] for c in "CE"},
            "bands": {c: BANDS[c] for c in "CE"}},
}
SLOT_SET = {v["slot"]: k for k, v in SETS.items()}
SET_INDEX = {"Metal": 0, "Furniture": 1, "Mag": 2}
# the static twin's U tile per set (study 5.8, spec textures.uv0): Metal 0..1, Furniture 1..2, the merged mag -1..0
TILE_OF_SET = {"Metal": 0.0, "Furniture": 1.0, "Mag": -1.0}
DENSITY_CEIL = 1.25          # no class median above 1.25 x its band top (the AR-01's stage-3 density rule)
CLASS_CODE = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
CODE_CLASS = {v: k for k, v in CLASS_CODE.items()}
MAG_PARTS = ("magazine", "magazine_follower", "magazine_floor_plate")
STOCK_PARTS = ("stock_frame", "stock_latch_button", "stock_latch_bolt", "butt_pad")

# ---------------------------------------------------------------- UV frames (gunlib.uvchart)
# round parts: cylinder charts about their own axis; everything else the gun's box frame. The grip is part of the
# one-piece lower: its straps (21.9 deg rake) project onto the X / Z charts at cos(21.9) = 0.93 (inside the +-15 %
# class uniformity), so no raked frame is needed
CYL_X = ("barrel", "muzzle_device")
_SH = dims("stock_hinge")
HINGE_AXIS_B = (float(_SH["axis_X"]) - GRIP_M[0], float(_SH["axis_Y"]) - GRIP_M[1])
CYL_Z = ("hinge_axle",)

# ---------------------------------------------------------------- stations (frame M, mm; spec stations_X)
ST = D["stations_X"]
X_MAG_REAR = float(ST["magazine"][0])            # 413.3: "behind the magwell" (texel class B on the receiver)
X_GUARD = tuple(float(v) for v in ST["trigger_guard"])
_TR, _LR = dims("top_rail"), dims("lower_rail")
RAIL_TOP_Z = float(_TR["top_Z"])                 # 45.4: the top rail's tooth tops (frame M)
RAIL_LOW_Z = float(_LR["bottom_Z"])              # the lower rail's tooth tops (it faces down)
RAIL_SLOT_D = 3.0                                 # MIL-STD-1913 slot depth (gunlib rail_1913 SLOT_D)
X_RAIL_B = 400.0                                  # top rail: class B for X < 400 (seen at ADS), C forward
SIGHT_PARTS = ("sight_rear_base", "sight_rear_leaf", "sight_rear_pin", "sight_front_base", "sight_front_leaf",
               "sight_front_pin")


def face_class(part, set_name, P_M, n, visible):
    """Texel class of one face (P_M: face centre, frame M mm; n: normal) by the spec's class_assignment and the parts'
    texel_class rows. Faces no ray reaches in any configuration (UV step's visibility) are class E."""
    if not visible:
        return "E"
    x, y, z = P_M
    if set_name == "Metal":
        if part in SIGHT_PARTS:
            return "A"                                    # the sights only (spec class A, check fix C15)
        if part in ("bolt", "charging_handle", "charging_slide", "selector", "hinge_axle", "stock_latch_bolt"):
            return "B"
        if part in ("top_rail", "rail_screws"):
            return "B" if x < X_RAIL_B else "C"
        if part in ("barrel", "muzzle_device"):
            return "D"
        return "C"                                        # lower rail, trigger, paddle, pins, axles, bolt rails
    if set_name == "Furniture":
        if part == "upper_receiver":
            return "B" if x < X_MAG_REAR else "C"         # rear (behind the magwell) B / fore-end C
        if part == "lower_receiver":
            # the magwell (C outside) and the trigger guard (C); the rest of the lower (grip, end block, housing) B
            if x >= 400.0 and z < -15.0:
                return "C"
            if X_GUARD[0] + 21.0 <= x <= X_GUARD[1] and z < -40.0:
                return "C"
            return "B"
        if part == "grip_cover":
            return "B"
        if part == "stock_frame":
            # top strut (cheek weld) and the neck to the hinge B; the rest C
            if x >= 170.0 or z >= 18.0:
                return "B"
            return "C"
        if part == "stock_latch_button":
            return "B"
        return "C"                                        # butt pad
    return "C"                                            # magazine


# ---------------------------------------------------------------- finishes (spec materials.finishes)
FIN = {
    # polymer (46, 47, 49): spec (46, 47, 50) one blue level down by L5 (the sheet's shadowed polymer reads neutral;
    # the spec's B - R +4 made the trigger guard's shadowed leg 0.056 saturated in sRGB, tolerance 0.05)
    "polymer": {"metal": 0, "srgb": (46, 47, 49), "spec_srgb": (46, 47, 50), "rough": (0.58, 0.66), "rough_hand": 0.52},
    "stipple": {"metal": 0, "srgb": (46, 47, 49), "rough": (0.78, 0.88)},
    "polymer_mag": {"metal": 0, "srgb": (41, 42, 45), "rough": (0.55, 0.65)},
    "rubber": {"metal": 0, "srgb": (42, 42, 44), "rough": (0.82, 0.92)},
    "phosphate": {"metal": 0, "srgb": (50, 51, 52), "rough": (0.66, 0.80), "oiled": (0.55, 0.65)},
    # worn steel at the spec's bare value but micro-scratched: rough 0.42-0.55 (spec 0.25-0.40; the AR-01's realism
    # rounds moved it to 0.50-0.62: at 0.25-0.40 every chip flashed as a white mirror fleck under the review lights);
    # the bolt's sliding flanks keep the spec's polished 0.15-0.25
    "bare": {"metal": 1, "srgb": (190, 190, 188), "rough": (0.42, 0.55), "spec_rough": (0.25, 0.40),
             "sliding": (0.15, 0.25)},
    "soot": {"metal": 0, "lin": 0.025, "rough": (0.85, 0.95)},
    "grime": {"metal": 0, "srgb": (34, 33, 32), "rough": 0.85},
}
PART_FINISH = {
    "upper_receiver": "polymer", "lower_receiver": "polymer", "grip_cover": "polymer", "stock_frame": "polymer",
    "stock_latch_button": "polymer", "butt_pad": "rubber",
    "magazine": "polymer_mag", "magazine_floor_plate": "polymer_mag", "magazine_follower": "polymer_mag",
}
POLYMER_FIN = ("polymer", "stipple", "polymer_mag", "rubber")


def finish_of(part):
    return PART_FINISH.get(part, "phosphate")


# ---------------------------------------------------------------- stipple panel (spec pistol_grip.dims.stipple_panel)
_PG = dims("pistol_grip")
GRIP_W = float(_PG["width_Y"])
STIPPLE_FLOOR_Y = GRIP_W / 2.0 - float(sum(_PG["stipple_panel"]["border_step"])) / 2.0     # 15.45: the panel floor
STIPPLE_PITCH = (0.5, 0.8)
STIPPLE_HEIGHT = (0.10, 0.15)

# ---------------------------------------------------------------- wear placement (spec wear_logic + parts[].wear)
# Polymer never shows metal: it POLISHES (lower roughness, base -2 levels) where hands slide and WHITENS (base +15..+35
# levels, roughness +0.05, 0.3-1.0 mm bands) where struck or abraded. Steel (phosphate, a dielectric coat) wears to
# bare steel on the bright edges named by the spec. Zones: frame M centres (mm), radius, weight; 'side' limits a zone
# to the gun's left (+1) or right (-1) half.
POLISH = [
    {"what": "grip front / back strap and the web (firing hand)", "center_M": (318.0, 0.0, -96.0), "radius": 46.0,
     "w": 0.9},
    {"what": "grip web under the tang", "center_M": (300.0, 0.0, -50.0), "radius": 18.0, "w": 0.8},
    {"what": "fore-end belly + left side (support hand; right-handed: the left more)", "center_M": (520.0, 18.0, -15.0),
     "radius": 45.0, "w": 0.8, "side": 1},
    {"what": "fore-end right side (support-hand fingers)", "center_M": (520.0, -18.0, -15.0), "radius": 38.0,
     "w": 0.45, "side": -1},
    {"what": "magwell flare and front face (support hand at the well)", "center_M": (466.0, 0.0, -50.0),
     "radius": 28.0, "w": 0.75},
    {"what": "stock top strut, cheek-weld zone (left)", "center_M": (165.0, 14.0, 24.0), "radius": 50.0, "w": 0.6,
     "side": 1},
    {"what": "selector thumb arc (left lever, the right-hand thumb)", "center_M": (329.2, 31.0, -31.0),
     "radius": 20.0, "w": 0.85, "side": 1},
    {"what": "selector arc (right lever, index finger)", "center_M": (329.2, -31.0, -31.0), "radius": 16.0,
     "w": 0.45, "side": -1},
    {"what": "trigger guard inside front (finger)", "center_M": (392.0, 0.0, -62.0), "radius": 12.0, "w": 0.55},
    {"what": "stock latch button face (thumb, left)", "center_M": (241.5, 29.0, 16.7), "radius": 9.0, "w": 0.8},
    {"what": "port catch lip", "center_M": (470.0, -31.0, 10.0), "radius": 8.0, "w": 0.6, "side": -1},
    {"what": "magazine spine crest and the upper 40 mm (insertion)", "center_M": (452.0, 0.0, -50.0), "radius": 30.0,
     "w": 0.5, "part": "mag"},
]
WHITEN = [
    {"what": "receiver vertical corners (rear)", "center_M": (268.0, 0.0, 20.0), "radius": 40.0, "w": 0.7},
    {"what": "receiver front-face rim", "center_M": (563.0, 0.0, 10.0), "radius": 36.0, "w": 1.0},
    {"what": "fore-end lower edge", "center_M": (525.0, 0.0, -28.0), "radius": 42.0, "w": 0.85},
    {"what": "vent and port lips (left vents / right port)", "center_M": (500.0, 0.0, 10.0), "radius": 50.0, "w": 0.45},
    {"what": "magwell lip (insertion)", "center_M": (445.0, 0.0, -66.0), "radius": 34.0, "w": 0.9},
    {"what": "trigger guard bottom", "center_M": (370.0, 0.0, -86.0), "radius": 30.0, "w": 0.8},
    {"what": "grip base lip", "center_M": (330.0, 0.0, -150.0), "radius": 30.0, "w": 0.85},
    {"what": "stock outer corners: butt toe", "center_M": (14.0, 0.0, -76.0), "radius": 26.0, "w": 1.0},
    {"what": "stock outer corners: butt heel", "center_M": (14.0, 0.0, 20.0), "radius": 24.0, "w": 0.9},
    {"what": "stock hinge knuckle edges", "center_M": (246.8, -31.0, 0.0), "radius": 34.0, "w": 0.6},
    {"what": "end block corners", "center_M": (257.0, 0.0, 0.0), "radius": 40.0, "w": 0.55},
    {"what": "magazine floor plate corners (drops)", "center_M": (452.0, 0.0, -228.0), "radius": 30.0, "w": 1.0,
     "part": "mag"},
    {"what": "magazine feed lips", "center_M": (430.0, 0.0, -24.0), "radius": 18.0, "w": 0.6, "part": "mag"},
]
WHITEN_BASE = 0.22           # outside the zones, only the strongest sharp corners whiten (faint)
STEEL_BRIGHT = [
    {"what": "rail slot edges and flank crests (top rail rear, the hands and optics on and off)",
     "center_M": (330.0, 0.0, 41.0), "radius": 60.0, "w": 0.55},
    {"what": "top rail forward / lower rail (support hand)", "center_M": (510.0, 0.0, 0.0), "radius": 60.0, "w": 0.45},
    {"what": "rear sight ear edges", "center_M": (298.9, 0.0, 68.0), "radius": 13.0, "w": 0.9},
    {"what": "front sight ear tops", "center_M": (542.2, 0.0, 70.0), "radius": 12.0, "w": 0.95},
    {"what": "muzzle device front rim and slots", "center_M": (622.0, 0.0, 1.7), "radius": 18.0, "w": 1.0},
    {"what": "charging knob crown", "center_M": (497.6, 46.0, 19.0), "radius": 9.0, "w": 0.9},
    {"what": "selector blade tips and hub rims", "center_M": (329.2, 0.0, -31.0), "radius": 22.0, "w": 0.85},
    {"what": "trigger face", "center_M": (370.8, 0.0, -60.0), "radius": 12.0, "w": 0.9},
    {"what": "mag release paddle face", "center_M": (405.0, 0.0, -55.0), "radius": 10.0, "w": 0.75},
    {"what": "barrel collar ring", "center_M": (566.0, 0.0, 1.7), "radius": 8.0, "w": 0.6},
    {"what": "hinge axle ends, latch bolt", "center_M": (246.8, -31.0, 0.0), "radius": 32.0, "w": 0.55},
]
STEEL_BASE = 0.25
# soot (spec: device slots and crown; light at the port's rear edge); frame M centres, radii, weights
SOOT = [{"what": "muzzle device slots and crown", "center_M": (612.0, 0.0, 1.7), "radius": 20.0, "w": 1.0},
        {"what": "bore mouth", "center_M": (597.0, 0.0, 1.7), "radius": 7.0, "w": 0.9},
        {"what": "port rear edge (right)", "center_M": (408.0, -31.0, 8.0), "radius": 12.0, "w": 0.35}]
# sliding polish (bare steel, rough 0.15-0.25): the bolt's flanks where they ride the rails
BOLT_SLIDE = {"part": "bolt", "normal_y_min": 0.75}
