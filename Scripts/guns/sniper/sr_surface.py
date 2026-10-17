"""SR01 surfacing rules (plain Python; imported by the W2 UV, bake, paint, recolour, render and gate steps): the SMG's
smg_surface interface (SETS / SLOT_SET / TILE_OF_SET / CLASS_CODE / face_class / CYL frames / MAG_PARTS) with the
sniper's sets, texel classes (SR01_BUILD_PLAN 7), finishes (spec materials, CRAFT_STUDY 3) and wear causes.

Frames: M = the spec's measurement frame (mm); B = M - Grip (Blender). Paths: W2 scratch = scratch/w2.
Also serves the scope attachment (sets Scope_Body / Scope_Lens) when SR01_SURFACE_TARGET=scope.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from sr_common import D, GRIP, ROOT, WORK, PARTS_COLL, BLEND, dims  # noqa: E402,F401
import sr_motion as MO  # noqa: E402

TARGET = os.environ.get("SR01_SURFACE_TARGET", "gun")          # gun | scope
SCRATCH = WORK / "scratch" / ("w2" if TARGET == "gun" else "w2_scope")
SCRATCH.mkdir(parents=True, exist_ok=True)
SCOPE_BLEND = ROOT / "Assets" / "Guns" / "Att_Scope_LongRange.blend"
SCOPE_COLL = "SM_Att_Scope_LongRange_Parts"
TEX = ROOT / "Exports" / "Guns" / "SR01" / "Textures"
COLL = PARTS_COLL if TARGET == "gun" else SCOPE_COLL
WBLEND = BLEND if TARGET == "gun" else SCOPE_BLEND
STEM = "T_SR01" if TARGET == "gun" else "T_Att_Scope_LongRange"

GRIP_M = tuple(float(v) for v in GRIP)
BORE_Z_B = 0.0 - GRIP_M[2]

# ---------------------------------------------------------------- texel classes, sets
BANDS = {k: tuple(float(x) for x in v["range"]) for k, v in D["textures"]["texel_classes_px_per_cm"].items()}
RATIO = {k: 0.5 * (v[0] + v[1]) for k, v in BANDS.items()}


def _set(slot, sizes, fill, classes):
    return {"slot": slot, "sizes": sizes, "fill_min": fill,
            "gap_px": {256: 2, 512: 2, 1024: 2, 2048: 4, 4096: 8}, "cell_px": {256: 1, 512: 1, 1024: 1, 2048: 2, 4096: 4},
            "classes": {c: RATIO[c] for c in classes}, "bands": {c: BANDS[c] for c in classes}}


if TARGET == "gun":
    # the packer picks each size (spec textures.rule: smallest power of two holding the floors at the fill minimum;
    # the AR-01's x2.3 estimate lesson: Metal ~2048, Chassis ~4096 expected, nothing assumed)
    SETS = {"Metal": _set("M_SR01_Metal", (1024, 2048, 4096), 0.70, "BCDE"),
            "Chassis": _set("M_SR01_Chassis", (2048, 4096), 0.65, "BCE"),
            "Mag": _set("M_SR01_Mag", (512, 1024, 2048), 0.65, "CE")}
    SET_INDEX = {"Metal": 0, "Chassis": 1, "Mag": 2}
    TILE_OF_SET = {"Metal": 0.0, "Chassis": 1.0, "Mag": -1.0}          # spec textures.slots SM_SR01
else:
    # (W2) the scope sets sit at the density ceiling at 2048 / 512 (1024 / 256 cannot hold the class floors): fill
    # measured 0.49 / 0.51, so the fill minimum is 0.45 here (declared in gates/uv_bake_paint.json)
    SETS = {"Scope_Body": _set("M_Att_Scope_Body", (1024, 2048, 4096), 0.45, "ACE"),
            "Scope_Lens": _set("M_Att_Scope_Lens", (256, 512), 0.45, "AE")}
    SET_INDEX = {"Scope_Body": 0, "Scope_Lens": 1}
    TILE_OF_SET = {"Scope_Body": 0.0, "Scope_Lens": 1.0}
SLOT_SET = {v["slot"]: k for k, v in SETS.items()}
DENSITY_CEIL = 1.25
CLASS_CODE = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
CODE_CLASS = {v: k for k, v in CLASS_CODE.items()}
MAG_PARTS = ("magazine", "magazine_floorplate") if TARGET == "gun" else ()

# ---------------------------------------------------------------- UV frames (gunlib.uvchart cyl_frame per part)
# round parts: a cylinder chart about their own axis (origin B mm, axis, seam reference); the rest the box frame
_HUB = MO.HUB


def cyl_frames():
    out = {}
    if TARGET == "gun":
        for n in ("barrel", "muzzle_device", "receiver", "bolt"):
            out[n] = ((0.0 - GRIP_M[0], 0.0 - GRIP_M[1], BORE_Z_B), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        for side, sg in (("l", 1.0), ("r", -1.0)):
            o = (0.0 - GRIP_M[0], sg * MO.LEG_Y - GRIP_M[1], float(_HUB[2]) - GRIP_M[2])
            for n in (f"bipod_ext_{side}", f"bipod_foot_{side}"):
                out[n] = (o, (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    else:
        out["scope_body"] = ((0.0 - GRIP_M[0], 0.0 - GRIP_M[1], 57.6 - GRIP_M[2]), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    return out


CYL = cyl_frames()

# ---------------------------------------------------------------- texel class of a face (plan 7)
X_WELL = (414.1, 503.6)            # magazine well
X_FOREND = 560.0                   # forend from the inlet's end
X_GUARD = (330.0, 410.0)


def face_class(part, set_name, P_M, n, visible):
    """A scope eyepiece; B comb, riser top, action bed, receiver, bolt, knob, safety, grip top, rail; C forend, well,
    guard, mag, release, bipod; D barrel, compensator; E hidden (no ray in any configuration)."""
    if not visible:
        return "E"
    x, y, z = P_M
    if TARGET != "gun":
        if set_name == "Scope_Lens":
            return "A"
        return "A" if part == "scope_body" and x < 300.0 else "C"        # the eyepiece end (rear) at the eye
    if set_name == "Metal":
        if part in ("receiver", "rail", "rail_screws", "bolt", "bolt_handle", "safety"):
            return "B"
        if part in ("barrel", "muzzle_device"):
            return "D"
        return "C"
    if set_name == "Chassis":
        if part == "cheek_riser":
            return "B" if z > 20.0 else "C"                               # comb / riser top
        if part == "chassis":
            if x < X_WELL[0] and z > -20.0:
                return "B"                                                # action bed (behind the well, top)
            return "C"                                                    # forend, well, guard
        if part == "grip":
            return "B" if z > -90.0 else "C"                              # grip top
        return "C"
    return "C"


# ---------------------------------------------------------------- finishes (spec materials; CRAFT_STUDY 3)
# Separate value AND roughness per material family (the SMG close-up lesson: not one charcoal for every dark part)
FIN = {
    # OD Cerakote over aluminium: the sheet's 89/89/78 (L5 calibrates the rendered value); ceramic orange peel
    "od": {"metal": 0, "srgb": (84, 85, 72), "rough": (0.56, 0.68), "rub_srgb": (120, 120, 106)},
    # bare / anodized aluminium under a chip: the hard anodize (dark grey) first, bright aluminium only at the crest
    "od_chip_anod": {"metal": 0, "srgb": (58, 58, 57), "rough": 0.45},
    "al_bare": {"metal": 1, "srgb": (200, 201, 203), "rough": (0.32, 0.45)},
    # matte hard-anodized black aluminium (rail, bipod body and legs): a cool, faintly blue-grey satin
    # (W2 judge fix round: "every black one charcoal") a cool blue-grey satin with a sheen: lighter, bluer, smoother
    # (L5, the sheet wins) near-neutral: the fix round's blue tint read sat +0.10 on the bipod (sheet neutral)
    "anod": {"metal": 0, "srgb": (58, 58, 60), "rough": (0.34, 0.44), "wear_srgb": (176, 178, 182)},
    # manganese phosphate steel (a dielectric coat): warmer, dead-flat crystalline charcoal (dry / oiled split)
    # (fix round) a warmer, dead-flat crystalline grey (rougher than every other dark family)
    "phos": {"metal": 0, "srgb": (62, 60, 56), "rough": (0.76, 0.86), "oiled": (0.62, 0.70),
             "bare_srgb": (192, 192, 190), "bare_rough": (0.34, 0.46)},
    # (W2 L5) the compensator: the sheet's darkest steel (43 vs the barrel's 51): its own sooty black phosphate
    "phos_device": {"metal": 0, "srgb": (36, 36, 37), "rough": (0.72, 0.82), "oiled": (0.62, 0.70)},
    # the barrel: a deeper, blued-black phosphate with a finer grain
    "phos_barrel": {"metal": 0, "srgb": (47, 47, 47), "rough": (0.66, 0.76), "oiled": (0.52, 0.60)},
    # polished bolt body + lugs (bare steel, spec bare_steel_polished): linear 0.53-0.56, rough 0.15-0.30
    # (W2 look) 0.16-0.26 read as mirror chrome under the studio rig: a honed satin bolt, 0.24-0.36
    # (W4 review C8) satin, not plated: both judges read the 0.24-0.36 polish as mirror chrome
    # (W4b) still chrome at 0.32-0.44 under the strip lights (both judges): a bead-blasted satin steel, lathe bands
    "bolt_polish": {"metal": 1, "lin": (0.36, 0.40), "rough": (0.48, 0.60)},
    # polished inner legs (hard chrome-like steel)
    # (W4b) "shiny chrome bands that look pasted": a satin hard-chrome
    "leg_polish": {"metal": 1, "lin": (0.46, 0.50), "rough": (0.38, 0.48)},
    # polymer grip (black, satin moulded skin with its own panel texture)
    "polymer": {"metal": 0, "srgb": (44, 44, 46), "rough": (0.56, 0.66), "rough_hand": 0.46},
    # rubber (pad, feet): soft matte, a hair lighter and bluer than the polymer, very rough
    "rubber": {"metal": 0, "srgb": (38, 38, 40), "rough": (0.88, 0.96)},
    # scope: matte anodized black body (a step darker / smoother than the rail), opaque glossy lens
    # (fix round) a deeper gloss-black anodize (the scope's own sheen, not the rail's satin)
    # (W4 review C1) matte type III anodize (study 0.45-0.65): at 0.24-0.34 the tube read as polished chrome
    "scope_anod": {"metal": 0, "srgb": (30, 30, 33), "rough": (0.46, 0.56), "wear_srgb": (170, 172, 176)},
    # (W4b) multi-coated glass in the opaque-glossy slot (Q6): a green-black centre, a violet / amber coating ring, a
    # convex normal (the environment curves across it like a real objective)
    # (scope finish, FINAL_JUDGES 6 / 11: read pure black) a three-phase coat (violet / amber / green) climbing toward
    # the rim, a faint inner coat ring, the centre a deep green-black instead of flat black
    "lens": {"metal": 0, "srgb": (26, 36, 33), "rough": (0.02, 0.04),
             "coat_srgb": ((86, 50, 128), (132, 94, 36), (48, 108, 76)), "coat_ring": (0.45, 0.98, 0.78),
             "inner_ring": (0.42, 0.06, 0.35), "convex_R_mm": 70.0},
    "soot": {"metal": 0, "lin": 0.0130, "rough": (0.85, 0.95)},
    "grime": {"metal": 0, "srgb": (36, 35, 33), "rough": 0.85},
}
PART_FINISH = {
    "chassis": "od", "butt": "od", "pad_plate": "od", "cheek_riser": "od",
    "butt_pad": "rubber", "grip": "polymer",
    "bipod_clamp": "anod", "bipod_swivel": "anod", "bipod_leg_l": "anod", "bipod_leg_r": "anod", "rail": "anod",
    "bipod_foot_l": "rubber", "bipod_foot_r": "rubber",
    "bipod_ext_l": "leg_polish", "bipod_ext_r": "leg_polish",
    "bolt": "bolt_polish", "barrel": "phos_barrel", "muzzle_device": "phos_device",
    "magazine": "phos", "magazine_floorplate": "polymer",
    "scope_body": "scope_anod", "scope_lens_objective": "lens", "scope_lens_ocular": "lens",
}
REFINISHABLE = ("od",)
BOLT_SHROUD_X = 372.0         # the bolt's rear shroud (X < 372, trace bolt_shroud) is phosphate, not polished (spec)
KNOB = {"centre_M": (367.9, -67.6, -33.6), "r": 12.4, "pitch_mm": 1.3, "depth_mm": 0.06}   # checkered ball        # Masks A = 1 only here (the user colour never tints rubber, polymer or metal)


def finish_of(part):
    if part in PART_FINISH:
        return PART_FINISH[part]
    if TARGET != "gun":
        return "scope_anod"
    return "phos"


# ---------------------------------------------------------------- wear by cause (frame M centres, mm)
# chips through the OD to anodize / bare aluminium: handling (the firing hand at the grip / tang, the support hand
# under the forend, the cheek on the comb), struck edges (butt toe / heel, forend front, guard bottom), the mag well
# lip (insertion), where the folded bipod feet ride against the forend underside, and where the sling / rest
# contacts the forend sides
CHIP_ZONES = [
    {"what": "magazine well lip (insertion)", "center_M": (459.0, 0.0, -88.0), "radius": 50.0, "w": 1.0},
    {"what": "forend front face and lower edges (rests, barricades)", "center_M": (835.0, 0.0, -20.0), "radius": 36.0,
     "w": 0.95},
    {"what": "forend underside where the folded feet ride", "center_M": (905.0, 0.0, -39.0), "radius": 40.0, "w": 0.6},
    {"what": "forend belly (support hand / bag rest)", "center_M": (640.0, 0.0, -38.0), "radius": 60.0, "w": 0.55},
    {"what": "butt toe (set down on it)", "center_M": (75.0, 0.0, -150.0), "radius": 34.0, "w": 1.0},
    {"what": "butt heel and the pad plate corners", "center_M": (70.0, 0.0, 10.0), "radius": 30.0, "w": 0.75},
    {"what": "trigger guard bottom", "center_M": (370.0, 0.0, -100.0), "radius": 30.0, "w": 0.8},
    {"what": "tang / action-bed rear under the thumb", "center_M": (300.0, 0.0, -10.0), "radius": 24.0, "w": 0.6},
    {"what": "comb / riser top edges (cheek weld, riser in and out)", "center_M": (125.0, 0.0, 31.0), "radius": 60.0,
     "w": 0.8},
    {"what": "grip area of the chassis (tang sides, grip seat, the thumb)", "center_M": (300.0, 0.0, -50.0),
     "radius": 32.0, "w": 0.75},
    {"what": "bolt-knob side of the action bed (the knob strikes it)", "center_M": (370.0, -30.0, -12.0),
     "radius": 22.0, "w": 0.7, "side": -1},
]
CHIP_BASE = 0.04              # (W4b: wear only where it is caused) outside the zones: rare tiny chips on the sharpest exposed edges only
POLISH = [                    # paint / polymer burnished smooth where hands slide (roughness down, no colour step)
    {"what": "grip (firing hand)", "center_M": (300.0, 0.0, -110.0), "radius": 50.0, "w": 0.9},
    {"what": "forend sides (support hand)", "center_M": (650.0, 0.0, -15.0), "radius": 70.0, "w": 0.55},
    {"what": "comb top (cheek)", "center_M": (130.0, 20.0, 31.0), "radius": 45.0, "w": 0.6},
    {"what": "safety", "center_M": (360.0, -20.0, -10.0), "radius": 12.0, "w": 0.8},
]
STEEL_BRIGHT = [              # phosphate rubbed to bare steel at real contact edges
    {"what": "muzzle device front rim", "center_M": (1100.0, 0.0, 0.0), "radius": 18.0, "w": 1.0},
    {"what": "bolt handle stem / ball crown", "center_M": (368.0, -55.0, -27.0), "radius": 14.0, "w": 0.6},
    {"what": "trigger face", "center_M": (366.0, 0.0, -75.0), "radius": 12.0, "w": 0.8},
    {"what": "release paddle face", "center_M": (410.0, 0.0, -100.0), "radius": 12.0, "w": 0.7},
    {"what": "safety lever tip", "center_M": (360.0, -20.0, -3.0), "radius": 8.0, "w": 0.6},
    {"what": "magazine body lips and spine (insertion)", "center_M": (460.0, 0.0, -25.0), "radius": 50.0, "w": 0.6,
     "part": "mag"},
    {"what": "magazine floor edges (drops)", "center_M": (460.0, 0.0, -128.0), "radius": 50.0, "w": 0.7, "part": "mag"},
]
STEEL_BASE = 0.15
ANOD_WEAR = [                 # anodize worn to bright aluminium (rare: rail edges, clamp jaw corners, leg collars)
    {"what": "rail tooth crests (optics on and off)", "center_M": (470.0, 0.0, 30.0), "radius": 90.0, "w": 0.35},
    {"what": "leg collars and lock buttons", "center_M": (887.0, 0.0, -62.0), "radius": 25.0, "w": 0.6},
    {"what": "clamp jaw corners", "center_M": (780.0, 0.0, -42.0), "radius": 40.0, "w": 0.4},
    {"what": "scope turret caps and ring tops", "center_M": (420.0, 0.0, 95.0), "radius": 60.0, "w": 0.5},
]
SOOT = [{"what": "muzzle device exit and baffle", "center_M": (1095.0, 0.0, 0.0), "radius": 16.0, "w": 1.0},
        {"what": "bore mouth", "center_M": (1052.0, 0.0, 0.0), "radius": 8.0, "w": 0.9}]
# grip texture panel (own polymer texture: a fine raised pyramid / pebble on the sides below the tang)
GRIP_PANEL = {"z": (-150.0, -70.0), "abs_ny_min": 0.6, "pitch": 0.9, "height": (0.08, 0.13),
              "stipple_cell": 0.75, "stipple_depth": (0.10, 0.16)}       # (W4b) a hot-iron stipple, not pyramids
# (W4b) socket heads: hex recess across flats as a fraction of the head diameter (ISO 4762: 3 / 7 on M4)
HEX = {"parts": ("fasteners", "rail_screws"), "af_frac": 0.43, "depth_mm": 0.35}
# (W4b) generic turret markings (numbers / ticks only): clicks per turn, a long tick every 5th, numerals at long ticks
TURRET_MARKS = {"scope_turret_elev": {"ticks": 40, "numbers": True}, "scope_turret_wind": {"ticks": 40, "numbers": True},
                "scope_focus": {"ticks": 24, "numbers": False}}
# (scope finish) generic power-ring numerals in the 8 scallop gaps (scallops at 0 / 45 / ... deg about the bore, 0 =
# +Y, 90 = top; the bottom gap left blank), a tick at each on the ring's rear band, the fixed index on the eyepiece,
# a diopter tick scale by the eyecup; numbers and ticks only (frame M mm, sr_scope.body stations)
POWER_MARKS = {"numbers": ("5", "6", "8", "10", "15", "20", "25"),
               "gap_deg": (-67.5, -22.5, 22.5, 67.5, 112.5, 157.5, 202.5), "ring_r_min": 22.0,
               "num_x": 363.0, "num_h_mm": 2.6, "tick_x": (351.4, 354.6), "index_x": (345.0, 349.6),
               "diopter_x": (285.4, 287.6, 289.2), "diopter_n": 4, "diopter_step_deg": 6.0}
# generic markings allowed (user 2026-10-13): S / F at the safety, rail slot numbers; never a maker / model / serial
# W3 Part 0: the S / F stamp sits on the visible outer face (Y -27) just under the safety pocket (pocket Z -22.5..1.0,
# floor at Y -17); at Z -8 it fell inside the pocket and painted 0 texels
MARKINGS = {"safety_S_F": {"center_M": (360.0, -27.0, -26.6), "height_mm": 3.0},
            "rail_numbers": {"every": 2, "height_mm": 2.2}}
