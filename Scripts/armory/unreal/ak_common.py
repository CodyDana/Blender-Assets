"""Shared constants and conversions for the ArmoryLab Unreal assembly (lean build: the room and EMPTY cases).

Imported by the Unreal-side scripts (ak_import / ak_materials / ak_level / ak_verify / ak_capture) and by the plain
Python helpers. Nothing here imports `unreal`, so it can be unit-checked outside the engine.

Blender frame (layout.json): metres, X across 0-12, Y along the axis 0-16 (entrance at Y 0), Z up.
Unreal frame: centimetres, left-handed. Conversion (layout.json "units", checked by the bounds gate in ak_level/ak_verify):
    UE location = (x*100, -y*100, z*100),  UE yaw = -rot_z (degrees).

Photometric conversion (measured, WorkFiles/armory/build/unreal/blender_units_probe.json): in Cycles a white Lambertian
plane under a sun of strength S has radiance S/pi, a P-watt point light gives irradiance P/(4 pi d^2), a P-watt area light
has on-axis intensity P/pi, and emission strength s is radiance s. Unreal: a directional light of E lux on a white
Lambertian surface gives scene radiance E/pi, candela is luminous intensity (on-axis for a rect light: lm = pi cd), and
emissive colour is scene radiance. So ONE factor K (lux per Blender W/m2) keeps every ratio of the Blender review renders:
    sun lux = K S,  point / spot cd = K P / (4 pi)  (a Blender spot's power is that of a point radiating in all directions),
    rect cd = K P / pi,  emissive = K s colour,  exposure multiplier = 2^EV_blender / K  (Unreal manual exposure = 2^bias).

PRESET (night + genkan, 2026-09-28): the lighting preset the whole Unreal stage builds, read from the environment variable
AK_PRESET: "night" (the DEFAULT, as render_armory.py) or "golden" (golden hour, exactly the hero-round level). Every
Unreal step is its own process, so set it for the whole run:  AK_PRESET=golden bash run_armory_unreal.sh
Night (render_armory.py MOON / PRESET_SCALE["night"] / PRESET_KELVIN / NIGHT_EMIT / CAM_EXPOSURE): ONE directional light,
the dim cool moon (it drives the SkyAtmosphere, forward shading priority 1; the golden sun and the window fill are not
spawned), a dark-blue physical sky at low sky-light intensity, no height fog and no volumetric fog (no shafts), the
practicals at the night role multipliers (downlights 3500 K), the far-scenery cards dimmed and cooled, the night
exposure bias. ak_verify checks whichever preset the level was built with (the same AK_PRESET).
"""
import json
import math
import os
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
LAYOUT = ROOT / "WorkFiles" / "armory" / "build" / "layout.json"
EXPORTS = ROOT / "Exports" / "ArmoryKit"
TEXTURES = EXPORTS / "Textures"
OUT = ROOT / "WorkFiles" / "armory" / "build" / "unreal"
CAPTURES = OUT / "captures"
BLENDER_BOUNDS = OUT / "blender_bounds.json"

PROJECT_DIR = Path(r"C:\Users\Cody\Documents\Unreal Projects\ArmoryLab")
UPROJECT = PROJECT_DIR / "ArmoryLab.uproject"

MESH_DEST = "/Game/ArmoryKit/Meshes"
TEX_DEST = "/Game/ArmoryKit/Textures"
MAT_DEST = "/Game/ArmoryKit/Materials"
LEVEL = "/Game/Armory/Maps/L_Armory"
MANAGED_TAG = "AK_Managed"      # every actor ak_level spawns; a re-run destroys exactly these and nothing else

# ------------------------------------------------------------------------------------------------ light / exposure
K_LUX = 100.0                    # lux per Blender W/m2 (Blender sun strength S -> K*S lux)
RENDER_SCRIPT = ROOT / "Scripts" / "armory" / "render_armory.py"


def _render_constants():
    """Unreal rebuild (2026-09-27): the Blender review powers, preset scales, sun strength, haze, sun disc and exposure
    are READ from render_armory.py (its module-level literals, via ast; it imports bpy, so it cannot be imported here),
    so the Unreal light table follows every Blender round without a hand-copied table going stale."""
    import ast
    want = {"POWER", "PRESET_SCALE", "SUN", "FOG", "SUN_ANGLE_DEG", "EXPOSURE", "LOOK", "SKY", "BLOOM",
            "MOON", "PRESET_KELVIN", "NIGHT_EMIT", "NIGHT_SKY_CAM", "CAM_EXPOSURE"}   # night: the moon + night tables
    out = {}
    tree = ast.parse(RENDER_SCRIPT.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in want:
                out[name] = ast.literal_eval(node.value)
    missing = want - set(out)
    if missing:
        raise RuntimeError(f"render_armory.py lacks {sorted(missing)}")
    return out


RC = _render_constants()
PRESETS = ("night", "golden")
PRESET = os.environ.get("AK_PRESET", "night").strip().lower() or "night"   # night + genkan (2026-09-28): night default
if PRESET not in PRESETS:
    raise RuntimeError(f"AK_PRESET={PRESET!r}: expected one of {PRESETS}")
NIGHT = PRESET == "night"
POWER_W = dict(RC["POWER"])                         # Blender watts per role ("glow": per metre of plinth perimeter)
ROLE_SCALE = dict(RC["PRESET_SCALE"][PRESET])       # the active preset's role scales (night table / golden)
GOLDEN_SCALE = ROLE_SCALE                           # (old name, kept for the helper scripts)
ROLE_KELVIN = dict(RC["PRESET_KELVIN"].get(PRESET, {}))   # night: absolute colour temperature per role (downlights 3500 K)
MOON = RC["MOON"].get(PRESET)                       # night: the moon replaces the golden sun, the window fill is off
SUN_W_M2 = float(RC["SUN"][PRESET])                 # golden 90 W/m2 (x power_scale: window fill 0.85); night: the moon 0.5 (r20 look; was 3)
SUN_ANGLE_DEG = float(RC["SUN_ANGLE_DEG"])          # f1: 0.5 deg disc
BLENDER_EXPOSURE_EV = float(RC["EXPOSURE"][PRESET])  # golden +2.4 EV, night +1.1 EV (AgX Very High Contrast)
BLENDER_LOOK = RC["LOOK"]
FOG_DENSITY_PER_M = float(RC["FOG"][PRESET])        # Blender haze extinction per metre; Unreal FogDensity = per_m * 10
SKY_FILL = RC["SKY"][PRESET]                        # (colour, strength) of the Blender world for non-camera rays

# Unreal-only role scales on top of the Blender golden preset (tuned against the Blender golden renders; BUILD_NOTES,
# Unreal rebuild). 1.0 = radiance parity with Blender.
# lantern: the paper panes are opaque in Blender, so the lantern point light only escapes through the open top; in
# Unreal the lanterns cast no shadow (budget), so the light reaches the floor and walls unblocked. 0.2 leaves roughly
# the open-top share (measured round 1: hot floor pools round every lantern in C1 / C10).
UE_ROLE_SCALE_BY_PRESET = {
    "golden": {"lantern": 0.2},
    # night (tuned on the night C1 against the Blender night C1 at 1448 x 1086, BUILD_NOTES "Unreal: night + genkan"):
    # glow 0.25: the under-glow rects (1.8 x 1.3 m, 7.5 cm over the floor, pointing down) are Lambertian in Unreal where
    # Blender narrows them to a 160 deg spread; at night x3.0 the spill in front of every plinth read a clipped white pool
    # (display L 0.63 against 0.26); 0.3 gave 0.31, 0.25 gave 0.28 (with the -2.68 bias). panel 0.6: the wall-niche
    # returns read hot orange (niche_back L 0.38 against 0.26, together with M_AK_HNicheSide below)
    # glow round (2026-09-28, user: brighter under-glow): glow 0.25 -> 1.0 together with the amber colour and the barn
    # doors below (C1 1448 x 1086 against night_live2, display L: pool in front of the front plinth 0.43 -> 0.61
    # (Blender 0.51), saturation 0.54 -> 0.89; tried: 2000 K doors 6 cm x0.5 (the doors cut the pool to a line, 0.22),
    # 2000 K 3 cm x1.0 (0.56), 1800 K 2 cm x0.8 (0.55, orange with no yellow), 1900 K 2 cm x0.9 (0.58, mid pool 0.43 < 0.46))
    "night": {"lantern": 0.2, "glow": 1.0, "panel": 0.6},
}
UE_ROLE_SCALE = dict(UE_ROLE_SCALE_BY_PRESET[PRESET])
# Unreal-only under-glow shape and colour (glow round, 2026-09-28; user: "please make the lights below the showcase boxes
# glow brighter"; BUILD_NOTES "Unreal: brighter under-glow"). In Cycles the amber floor streak in front of every plinth
# comes from the hot emissive strips (M_AK_HAmberHot, M_AK_HKickGlow) lighting and mirroring in the glossy floor; the
# 4200 K glow rect only adds a soft warm-white spill. Unreal's emissives light nothing, so the rect alone made a wide
# cream pool. Here the rect carries the strips' amber (UE_ROLE_KELVIN) and straight barn doors (UE_ROLE_BARN_DOOR_CM,
# the rect hangs 7.5 cm over the floor) keep its light in a tight band beside the plinth, so it can run brighter
# without spreading into a clipped white pool.
UE_ROLE_KELVIN_BY_PRESET = {"golden": {}, "night": {"glow": 2000}}
UE_ROLE_KELVIN = dict(UE_ROLE_KELVIN_BY_PRESET[PRESET])
UE_ROLE_BARN_DOOR_CM_BY_PRESET = {"golden": {}, "night": {"glow": 2.0}}
UE_ROLE_BARN_DOOR_CM = dict(UE_ROLE_BARN_DOOR_CM_BY_PRESET[PRESET])
# diagnostics only (hero round): AK_ROLE_SCALE='{"wash": 0}' switches a role off for a test level + capture; the verify
# gate then fails the light intensities on purpose, so a real run never sets it
if __import__("os").environ.get("AK_ROLE_SCALE"):
    UE_ROLE_SCALE.update(json.loads(__import__("os").environ["AK_ROLE_SCALE"]))
UE_SPEC_OFF_ROLES = {"lantern"}
# Unreal-only: the plan's shadow budget is at most 12 shadow-casting local lights (ARMORY_PLAN section on lights).
# Blender shadows 12 case lights and the 4 rear-alcove spots (f2); in Unreal the alcove spots light an empty rack
# fixture against its own back board, so they give up their shadows and the 12 case lights keep theirs.
UE_SHADOW_OFF_ROLES = {"alcove"}
# r19 b (2026-09-30): the rear tall pairs added G4 / G5 (CaseLight_13 / 14, appended after the hero so the other
# numbers hold), 14 shadowed case lights against the budget of 12. Unreal-only, like the alcove spots: the two NEAR
# talls (empty growth slots, tucked straight behind the scroll / hat cases, their feet hidden from C1) give up their
# shadows; the other 12 case lights keep theirs. Blender still shadows all 14.
UE_SHADOW_OFF_LIGHTS = {"CaseLight_13", "CaseLight_14"}
# Unreal-only post-process grade on the level's unbound PPV (key = FPostProcessSettings property; ak_level sets its
# override_ flag too). Blender blooms lightly (render_armory.py BLOOM: threshold 2.0, strength 0.2); Unreal's default
# bloom (0.675 on everything) veils the dark room.
UE_PP = {"bloom_intensity": 0.3,
         # round 1: Unreal's filmic curve keeps the 2800 K sun saturated where AgX rolls it toward cream (CG sunlit gravel
         # display (0.70, 0.47, 0.18) against Blender's (0.63, 0.51, 0.37))
         "color_saturation": (0.85, 0.85, 0.85, 1.0)}
if PRESET == "night":
    # night: no warm sun to desaturate (saturation 1.0: the practicals' amber is the look; at 0.85 the LED lines and the
    # glow pools read cream-white against Blender's amber); film_toe 0.4 (default 0.55): most of the night frame sits in
    # the toe, where Unreal crushed the moonlit / downlit floor (floor_lo50 L 0.068 against 0.109 at 0.55; 0.082 at 0.4)
    UE_PP = dict(UE_PP, color_saturation=(1.0, 1.0, 1.0, 1.0), film_toe=0.4)
# (tried and dropped: film_toe 0.3 against the default 0.55 lifted C1 p10 only 0.016 -> 0.039 and darkened every mid-tone)
# Unreal-only sky: SkyAtmosphere's physical sky for a 6000 lux sun reads dim teal (CG_Garden sky display (0.38, 0.44,
# 0.43)) where the Blender golden world is cream (0.81, 0.77, 0.72); its linearised ratio per channel is about
# (5.2, 3.5, 3.1). The factor also scales the real-time sky light (the shade fill the Blender world gives).
UE_SKY_BY_PRESET = {"golden": {"sky_luminance_factor": (5.0, 3.5, 3.0)},
                    # night: the moon (300 lux, 38 deg up) is the atmosphere light; its physical sky is a DAYTIME blue
                    # scaled down and tinted to render_armory NIGHT_SKY_CAM's blue-black (tuned on the CG_Garden sky,
                    # display sRGB, Blender (0.011, 0.050, 0.105)): (1.0, 1.1, 1.9) gave a bright day sky, (0.08, 0.09,
                    # 0.16) (0.011, 0.036, 0.201), (0.08, 0.18, 0.04) (0.012, 0.123, 0.033), (0.06, 0.11, 0.10)
                    # (0.008, 0.057, 0.124)
                    # r20 look (user: "lower the moon brightness by a lot so its darker outside"): the moon 300 -> 50
                    # lux already darkens the physical sky (and the captured sky light) x1/6; Blender's camera sky went
                    # x0.3 (NIGHT_SKY_CAM 1.0 -> 0.3), so the factor rises x1.8 to keep parity: (0.06, 0.11, 0.10) ->
                    "night": {"sky_luminance_factor": (0.108, 0.198, 0.18)}}
UE_SKY = UE_SKY_BY_PRESET[PRESET]
# the real-time sky light (the shade fill of the Blender world's diffuse rays): golden 1.0; night 0.25 (Blender's diffuse
# fill SKY["night"] is about a fifth of its camera sky where golden's is about half)
SKYLIGHT_INTENSITY = {"golden": 1.0, "night": 0.25}[PRESET]
SPOT_BLEND = 0.5                 # default when a spot has no "blend"
SPOT_SOFT_M = 0.04
FOG_ANISO = 0.35
FOG_ALBEDO = (1.0, 0.93, 0.85)
SKY_SCATTER = 0.0                # Blender: the world does not scatter in the haze
# Manual exposure bias (EV). Analytic radiance parity: exposure multiplier 2^bias = 2^EV_blender / K.
# The tuned bias is what the capture sweep measured to give the Blender golden C1's mean and median display luminance
# (capture_stats.json "sweep"; BUILD_NOTES). History: -3.34 (fix1, Blender EV +0.8 AgX MHC), -3.94 (look2, EV +0.2).
EXPOSURE_BIAS_ANALYTIC = BLENDER_EXPOSURE_EV - math.log2(K_LUX)
# per preset; night started from the golden tuning moved by the Blender night - golden EV (+1.1 - +2.4 = -1.3): -2.88
# (every room view within 0.035 of Blender's mean, but hot glow pools and emissives over a dark floor); with the night
# role scales, overrides and film toe it is -2.68: C1 whole-frame mean 0.129 / 0.129 (BUILD_NOTES "Unreal: night + genkan")
EXPOSURE_BIAS_BY_PRESET = {"golden": -1.58, "night": -2.68}
EXPOSURE_BIAS = EXPOSURE_BIAS_BY_PRESET[PRESET]
EXPOSURE_BIAS_GOLDEN = -1.58     # hero round (2026-09-28): -1.80 -> -1.58, re-tuned over the 7 room views against the
# hero_live Blender renders: at -1.80 the per-view mean errors (Unreal - Blender) were C1 -0.027, C3 +0.019, C4 -0.027,
# C5 -0.041, C10 +0.029, CW -0.042, CX -0.066; their median -0.027 over the measured slope (~0.12 mean per EV) is +0.22 EV
# (CG_Garden keeps its own camera offset on top). Previous: Unreal rebuild, TUNED over ALL the review views, not C1 alone.
# Start -1.74 (look2's -3.94 moved by the Blender +0.2 -> +2.4 EV). The C1 sweep (48 frames per bias, capture_stats.json
# "sweep") against the Blender golden C1 (mean 0.295, p50 0.202) is best at -2.24 (0.275 / 0.209), but that leaves C3, CW
# and CX 0.07-0.11 darker than Blender. At -1.74 the per-view errors (Unreal - Blender) are, mean: C1 +0.039, C3 -0.041,
# C5 +0.007, C10 +0.073, CW -0.017, CX -0.011, CG +0.034; p50: +0.092, -0.050, -0.022, +0.079, -0.065, -0.001, +0.049.
# Their medians (+0.007 / -0.001) over the measured slope (about 0.12 mean per EV) give -1.80.
MAX_SHADOWED_LOCAL = 12
# UE 5.8 rect lights deliver TWICE the nominal candela on axis: RectLightSceneProxy.cpp divides the colour by
# 0.5 * SourceWidth * SourceHeight. Measured (ak_capture.py AK_LADDER=1, capture.json "light_units"): a 1000 cd point
# light 2 m over a 0.18 grey Lambertian quad gives 1.035x the expected 14.3 nits, a 10 x 10 cm rect light of 1000 cd
# gives 2.07x. So a rect light is set to half the Blender-equivalent candela.
RECT_CANDELA_SCALE = 0.5
# f2: the window fill sun lights, and is shadowed by, the room only (Blender light + shadow linking to the Assembly
# collection). Unreal: lighting channel 1. The room kit (SM_AK_) is on channels 0 + 1, the exterior (SM_AKX_) on 0.
INTERIOR_CHANNEL = 1


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexcol(h):
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255.0) for i in (1, 3, 5))


def kelvin_rgb(k):
    """Tanner Helland's blackbody fit, exactly as render_armory.py uses it (treated as linear RGB there)."""
    t = k / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(max(0.0, min(255.0, c)) / 255.0 for c in (r, g, b))


def light_watts(L):
    """Blender watts of a layout.json local light in the active preset (render_armory.py: POWER x perimeter for the
    under-glow x preset scale x the light's own power_scale), times the Unreal-only role scale."""
    role = L["role"]
    p = POWER_W[role] * (L["perimeter"] if role == "glow" else 1.0)
    return p * ROLE_SCALE.get(role, 1.0) * float(L.get("power_scale", 1.0)) * UE_ROLE_SCALE.get(role, 1.0)


def light_kelvin(L):
    """render_armory.py: PRESET_KELVIN[preset][role] replaces layout.json's kelvin (night downlights 3500 K); then the
    Unreal-only UE_ROLE_KELVIN (night under-glow: a saturated amber, see there)."""
    return UE_ROLE_KELVIN.get(L.get("role"), ROLE_KELVIN.get(L.get("role"), L["kelvin"]))


def light_barn_door_cm(L):
    """Unreal barn-door length (cm, doors straight: angle 0) for a rect light: the Unreal-only UE_ROLE_BARN_DOOR_CM
    (night under-glow) or, for a layout light with its own spread_deg (the hero table's), the length that puts the
    half-spread cone's edge ray from the rect centre at the door tip; else 0 (no doors)."""
    if L["role"] in UE_ROLE_BARN_DOOR_CM:
        return float(UE_ROLE_BARN_DOOR_CM[L["role"]])
    if "spread_deg" in L:
        w, h = L["size"]
        return min(w, h) * 100.0 / 2.0 / math.tan(math.radians(float(L["spread_deg"]) / 2.0))
    return 0.0


def sun_lux(L):
    """Directional light illuminance: K x the golden sun strength x the light's power_scale (the window fill 0.85)."""
    return K_LUX * SUN_W_M2 * float(L.get("power_scale", 1.0))


def moon_travel_dir(moon):
    """render_armory.py main(): the moon's travel direction (Blender frame) from its elevation and heading (degrees from
    +X toward -Y, layout.json's convention)."""
    el, az = math.radians(moon["elev_deg"]), math.radians(moon["heading_deg"])
    return [math.cos(el) * math.cos(az), -math.cos(el) * math.sin(az), -math.sin(el)]


def directional_specs(layout=None):
    """The directional lights of the active preset, as ak_level spawns them and ak_verify checks them. Golden: the
    layout.json suns (the real sun: atmosphere light, channel 0, scatters, forward shading priority 1; the f2 window fill:
    channel 1 only, no atmosphere, no scatter, priority 0). Night: ONE light, the moon (render_armory MOON: the golden
    sun re-aimed and dimmed, the window fill off): atmosphere light, channel 0, no volumetric scattering (no shafts),
    priority 1 (a single directional light: the multiple-directional-lights warning cannot come back)."""
    suns = [L for L in (layout or load_layout())["lights"] if L["type"] == "sun"]
    if MOON is not None:
        return [{"name": "Moon", "travel_dir": [round(v, 6) for v in moon_travel_dir(MOON)], "lux": K_LUX * SUN_W_M2,
                 "kelvin": MOON["kelvin"], "angle_deg": float(MOON.get("angle_deg", SUN_ANGLE_DEG)), "interior": False,
                 "atmosphere": True, "scatter": 0.0, "volumetric_shadow": False, "priority": 1,
                 "replaces": [L["name"] for L in suns]}]
    out = []
    for L in suns:
        interior = L.get("link") == "interior"
        out.append({"name": L["name"], "travel_dir": list(L["travel_dir"]), "lux": sun_lux(L), "kelvin": L["kelvin"],
                    "angle_deg": SUN_ANGLE_DEG, "interior": interior, "atmosphere": not interior,
                    "scatter": 0.0 if interior else 1.0, "volumetric_shadow": not interior,
                    "priority": 0 if interior else 1})
    return out


def light_shadows(L):
    return (bool(L.get("shadows", False)) and L.get("role") not in UE_SHADOW_OFF_ROLES
            and L.get("name") not in UE_SHADOW_OFF_LIGHTS)


# ------------------------------------------------------------------------------------------------ performance (2026-10-02)
# ArmoryLab performance, hall variant (BUILD_NOTES "ArmoryLab performance (hall variant)", measured with ak_perf.ps1).
# Unreal-only, every preset. Blender has no equivalent (its lights have no cut-off and no channels), so nothing here
# changes the Blender renders.
# 1 The case lights (12 of them cast the level's only local shadows) light and shadow ONLY lighting channel 1: the room
#   kit (SM_AK_ on channels 0 + 1) and the items. The hall shell (SM_DKH_, channel 0) and the armory's hidden exterior
#   then stay out of their 12 cube virtual shadow maps: the shell's ~170 actors (15 of its 32 pieces non-Nanite) were
#   about half of the ~1030 shadow-depth draws per frame. Nothing the case lights can reach changes: the shell stands
#   outside the room's walls and ceiling. The hall variant's 8 floor tiles (placed by the shell tool, SM_AK_ pieces)
#   are put on channels 0 + 1 by ak_hallperf.py, the post-shell step.
UE_CHANNEL1_ONLY_ROLES = {"case"}
# 2 Attenuation radius (cm), per role; every light keeps 2000 for now. Measured 2026-10-02: shorter radii (glow 600,
#   panel 800, lantern 600, down 1200) cut the deferred "Lights" pass but darkened C1 by 11 % (Unreal's window
#   (1 - (d / r)^4)^2 is close to 1 only for d < 0.3 r), so they are NOT applied; the table is the hook if a later
#   round wants to trade look for GPU time (re-measure with ak_perf.ps1 and compare the C1 / C10 shots).
UE_ATTEN_CM_DEFAULT = 2000.0
UE_ATTEN_CM_BY_ROLE = {}


def light_atten_cm(L):
    return float(UE_ATTEN_CM_BY_ROLE.get(L.get("role"), UE_ATTEN_CM_DEFAULT))


def light_channels(L):
    """(channel0, channel1) of a local light."""
    return (False, True) if L.get("role") in UE_CHANNEL1_ONLY_ROLES else (True, False)


def is_interior_piece(piece):
    """The Blender Assembly collection (room kit) = SM_AK_ pieces; SM_AKX_ are AssemblyExterior."""
    return piece.startswith("SM_AK_")


def camera_exposure_offset(cam):
    """A camera's own review exposure relative to the room exposure of the preset, as render_armory.py picks it:
    CAM_EXPOSURE[preset] first (night: CG_Garden +0.3 vs +1.1), then layout.json exposure_ev (golden: CG -2.8 vs +2.4)."""
    ev = RC["CAM_EXPOSURE"].get(PRESET, {}).get(cam["name"], cam.get("exposure_ev", {}).get(PRESET))
    return 0.0 if ev is None else float(ev) - BLENDER_EXPOSURE_EV


def light_candela(L):
    """Unreal candela for a layout.json light (active preset)."""
    p = light_watts(L)
    if L["type"] == "rect":
        return K_LUX * p / math.pi * RECT_CANDELA_SCALE
    return K_LUX * p / (4.0 * math.pi)      # point and spot


# ------------------------------------------------------------------------------------------------ transforms
def loc_cm(v):
    x, y, z = v
    return (x * 100.0, -y * 100.0, z * 100.0)


def yaw_deg(rot_z):
    return -float(rot_z)


def bbox_bl_to_ue(bmin, bmax):
    """Blender AABB (m) -> Unreal AABB (cm): Y flips, so min/max swap on Y."""
    return ([bmin[0] * 100.0, -bmax[1] * 100.0, bmin[2] * 100.0],
            [bmax[0] * 100.0, -bmin[1] * 100.0, bmax[2] * 100.0])


def dir_bl_to_ue(d):
    return (d[0], -d[1], d[2])


def pitch_yaw_of(d):
    """Unreal pitch / yaw (degrees) whose forward vector is d (Unreal frame)."""
    x, y, z = d
    n = math.sqrt(x * x + y * y + z * z)
    return math.degrees(math.asin(z / n)), math.degrees(math.atan2(y, x))


def hfov_deg(lens_mm, sensor_mm=36.0):
    """Horizontal FOV: Blender sensor fit AUTO with a 36 mm sensor on a landscape frame fits the width."""
    return math.degrees(2.0 * math.atan(sensor_mm / 2.0 / lens_mm))


# ------------------------------------------------------------------------------------------------ piece classes
def folder_of(piece):
    if piece.startswith("SM_AKX_"):   # exterior stage: the garden, the roof and the scenery
        p = piece.replace("SM_AKX_", "")
        if p.startswith(("Roof", "Foundation", "Facade")):
            return "Exterior/Building"
        if p.startswith(("TreeLine", "Hills", "Mountains", "Ground_Field")):
            return "Exterior/Scenery"
        if p.startswith(("Pine", "Maple")):
            return "Exterior/Trees"
        if p.startswith(("Wall", "Gate")):
            return "Exterior/Enclosure"
        return "Exterior/Garden"
    p = piece.replace("SM_AK_", "")
    if p.startswith("Case_"):
        return "Casework/Cases"
    if p.startswith("WallPanel"):
        return "Casework/WallPanels"
    if p.startswith("CornerRack"):
        return "Casework/CornerRacks"
    if p.startswith("PaintingPanel"):
        return "Casework/Painting"
    if p.startswith("Lantern"):
        return "Casework/Lanterns"
    if p.startswith(("Floor", "Ext_Ground")):
        return "Architecture/Floor"
    if p.startswith("Ceiling"):
        return "Architecture/Ceiling"
    if p.startswith(("Platform", "Steps")):
        return "Architecture/Platform"
    if p.startswith(("Threshold", "EntryMat", "StepBeam", "GenkanFloor")):   # genkan (2026-09-28)
        return "Architecture/Entry"
    if p.startswith(("Window",)):
        return "Architecture/Windows"
    if p.startswith(("Post", "Corner")):
        return "Architecture/Posts"
    return "Architecture/Walls"


def wall_side(inst):
    """Which wall a wall piece belongs to (Blender placement rule in build_armory_kit.layout())."""
    r = float(inst["rot_z"])
    return {0.0: "South", 180.0: "North", -90.0: "West", 90.0: "East"}.get(r, "")


def layout_pieces(layout=None):
    """Hero round (2026-09-28): the kit is what layout.json lists ("pieces"), not whatever FBX sits in the export folder
    (a stale SM_AK_Entrance_6.fbx from the pre-hero build is still there and is NOT part of the kit)."""
    return sorted((layout or load_layout())["pieces"])


def n_meshes():
    """look2: the kit size is whatever the pipeline exported (was a constant 35); hero round: layout.json "pieces"."""
    return len(layout_pieces())


def texture_kinds(params):
    """The maps a Blender material samples (build_armory_kit.build_material): an emissive picture (emit_image) reads its
    BC map only; every other texture set reads BC + ORM + N."""
    return ("BC",) if params.get("emit_image") else ("BC", "ORM", "N")


def layout_textures(layout=None):
    """{texture asset stem: kind} for every map a layout.json material uses (T_AK_* / T_AK_H* / T_AKX_*)."""
    out = {}
    for _name, m in (layout or load_layout())["materials"].items():
        if m.get("texture"):
            for kind in texture_kinds(m["params"]):
                out[f"{tex_stem(m['texture'])}_{kind}"] = kind
    return out


def n_textures():
    return len(engine_textures())


def engine_textures():
    """The material maps Unreal imports. Hero round: exactly the maps the layout.json materials use (generic: T_AK_*,
    T_AK_H* and T_AKX_*), not every BC / N / ORM in the folder (the folder also holds maps of retired sets, and the
    N / ORM maps of the emissive pictures that only read BC). Generator-only intermediates such as T_AK_Emblem are not
    imported. A map layout.json needs but the exports lack still appears here, so the import step fails on it."""
    return sorted(TEXTURES / f"{stem}.png" for stem in layout_textures())


def tex_stem(tex):
    """Texture set name -> texture asset stem prefix (exterior sets are named AKX_*: T_AKX_<set>)."""
    return f"T_{tex}" if tex.startswith("AKX_") else f"T_AK_{tex}"


# ------------------------------------------------------------------------------------------------ materials
# Hero round: the Blender material table (build_armory_kit.MATERIALS incl. every hero module's M_AK_H* and hero_shared's
# overrides of kit materials) travels in layout.json "materials"; the Unreal instance spec is computed HERE (not in the
# unreal-only ak_materials), so ak_verify checks every instance against layout.json itself.
# Unreal-only overrides on top of the Blender values, measured on C1 against the Blender golden render (BUILD_NOTES).
# Hero round: look3's plank tint 0.62 and painting tint 0.70 were tuned for the old T_AK_Plank / T_AK_Painting sets;
# hero_shared now puts M_AK_Plank on the HPlank set at Blender tint 1.8 and the painting is M_AK_HPaintingTall, so the
# table was re-derived on the hero C1 (BUILD_NOTES "Unreal: hero pieces").
UE_OVERRIDES = {
    # the HPlank floor at Blender tint 1.8 read light grey oak (C1 floor_shade L 0.58 vs 0.36, floor_lo50 0.48 vs 0.30);
    # at bias -1.80: 0.9 went slightly dark, 1.0 matched the shaded boards (lo50 0.31 / 0.30, shadow_left 0.38 / 0.39);
    # the -1.58 bias (x1.165) then asks for 1.0 / 1.165 = 0.86
    # r20 look (2026-10-01, user: the floor reads grey): the dark walnut now lives in T_AK_HPlank_BC and the Blender tint
    # is 1.0 (was 1.8); the Unreal / Blender albedo ratio stays 0.86 / 1.8 = 0.478, so the instance keeps the measured
    # parity. A scalar (grey) Tint, so the hue and saturation are the map's: albedo sRGB (45, 27, 18), HSV 20 / 0.61 / 0.18 (was (53, 44, 38), 25 / 0.29 / 0.21)
    "M_AK_Plank": {"tint": 0.48},
    # the unlit painting paper read bright (painting_centre L 0.57 vs 0.42): emission 0.1 -> 0.05 gave 0.42 / 0.42 at
    # bias -1.80; / 1.165 for the -1.58 bias
    "M_AK_HPaintingTall": {"emit": 0.043},
    # the lantern washi read bright (lantern_paper L 0.83 vs 0.74): 0.28 -> 0.17 gave 0.77 / 0.74 at bias -1.80 (0.2:
    # 0.79); / 1.165 for the -1.58 bias
    "M_AK_HWashi": {"emit": 0.146},
    # the platform deck (#6E5A48, coat 0.3) read pale cream in EVERY view (C1 platform_deck sRGB (0.74, 0.59, 0.45) vs
    # (0.51, 0.31, 0.12); C10 (0.68, 0.57, 0.46) vs (0.50, 0.31, 0.14)); not the wash, the lanterns, the downlights or
    # the coat (diagnostic captures, BUILD_NOTES). The per-channel linear ratio gives #4D2D12 (C1 (0.58, 0.27, 0.08)),
    # rebalanced to #493015 (C1 (0.55, 0.29, 0.09) at bias -1.80), x 1 / 1.165 linear for the -1.58 bias: #432D11
    "M_AK_HDeck": {"color": "#432D11"},
}
# night + genkan (2026-09-28): Unreal-only overrides for the NIGHT preset only, merged over UE_OVERRIDES (tuned on the
# night C1 against the Blender night C1; BUILD_NOTES "Unreal: night + genkan"). Golden keeps UE_OVERRIDES alone.
UE_OVERRIDES_NIGHT = {
    # the washi lantern paper read bright (lantern_paper L 0.57 against 0.49 at -2.88): 0.146 -> 0.11 (0.50 / 0.49)
    "M_AK_HWashi": {"emit": 0.11},
    # the plinth kick line (M_AK_HAmberHot line over the M_AK_HKickGlow picture) read cream-white, L 0.68 (0.84, 0.65,
    # 0.48) against amber L 0.37 (0.64, 0.33, 0.03): Unreal's filmic shoulder whitens it; 22 -> 6 and 3.15 -> 1.2 give
    # L 0.46 (0.66, 0.42, 0.24) (still paler: the tonemapper)
    # glow round (user: brighter under-glow): HAmberHot 6 -> 12 (the hidden down-facing strip; Lumen emissive bounce
    # under the overhang), HKickGlow 1.2 -> 2.0 with an amber Emissive Tint (1.0, 0.8, 0.6) so its white-hot core stays
    # amber in the filmic shoulder: kick band L 0.34 -> 0.42 (Blender 0.41), saturation 0.94
    "M_AK_HAmberHot": {"emit": 12.0},
    "M_AK_HKickGlow": {"emit": 2.0, "emit_tint": (1.0, 0.8, 0.6)},
    # the platform deck: the golden override #432D11 read dark red at night (L 0.13 (0.30, 0.10, 0.01) against 0.27
    # (0.40, 0.25, 0.12)); Blender's #6E5A48 read 0.43; #534337 gives 0.28 (0.42, 0.25, 0.14)
    "M_AK_HDeck": {"color": "#534337"},
    # the wall niches read hot orange (niche_back L 0.38 against 0.26): the washi backs 0.02 -> 0.012, the side
    # returns 0.035 -> 0.015 (with panel x0.6 above): 0.30
    "M_AK_HNicheWashi": {"emit": 0.012},
    "M_AK_HNicheWashi190": {"emit": 0.012},
    "M_AK_HNicheSide": {"emit": 0.015},
    # the rear-alcove screens by the painting read hot beside it: 0.9 -> 0.6
    "M_AK_HAlcovePanel": {"emit": 0.6},
    # the case-frame LED lines read white (Blender amber): 1.2 -> 0.6
    "M_AK_HLedStrip": {"emit": 0.6},
    # the case decks caught a cool sheen of the 6400 K case lights (case_deck L 0.15 (0.17, 0.14, 0.11) against 0.08
    # (0.12, 0.07, 0.03)): #0A0908 rough 0.35 -> #060504 rough 0.8: 0.07 (0.09, 0.06, 0.04)
    "M_AK_HDeckSuede": {"color": "#060504", "rough": 0.8},
    # the moonlit gravel read bright warm cream in CG_Garden (L 0.45 against 0.32; Unreal's filmic keeps the beige that
    # AgX greys, as in golden): tint 0.6 gives 0.36
    "M_AKX_Gravel": {"tint": 0.6},
}
if PRESET == "night":
    UE_OVERRIDES = {k: dict(UE_OVERRIDES.get(k, {}), **UE_OVERRIDES_NIGHT.get(k, {}))
                    for k in set(UE_OVERRIDES) | set(UE_OVERRIDES_NIGHT)}
# Museum anti-reflective glass. Blender: fully transparent plus a mirror at refl x Fresnel (IOR 1.5; f2 default 0.02).
# Unreal thin translucent pane: specular 0.1 (F0 0.008) under a small opacity rising at grazing, at refl 0.02; a material
# with its own "refl" (hero_shared M_AK_HCaseGlass 0.035) scales Specular and Edge Opacity by refl / 0.02.
GLASS = {"Base Colour": (0.012, 0.013, 0.013), "Opacity": 0.02, "Edge Opacity": 0.06, "Roughness": 0.02, "Specular": 0.1}
GLASS_REFL = 0.02


def blender_materials(layout=None):
    """{name: (texture set or None, params with UE_OVERRIDES applied)} from layout.json. Night: the painted far-scenery
    cards (render_armory NIGHT_EMIT) get their emission scaled and an "emit_tint" (render_armory dim_scenery())."""
    out = {k: (v["texture"], dict(v["params"])) for k, v in (layout or load_layout())["materials"].items()}
    for k, o in UE_OVERRIDES.items():
        if k in out:
            out[k] = (out[k][0], dict(out[k][1], **o))
    if NIGHT:
        ne = RC["NIGHT_EMIT"]
        for k, f in ne["scale"].items():
            if k in out and "emit" in out[k][1]:
                p = dict(out[k][1])
                p["emit"] = float(p["emit"]) * float(f)
                p["emit_tint"] = tuple(float(c) for c in ne["tint"])
                out[k] = (out[k][0], p)
    return out


def material_spec(tex, p):
    """-> (master, scalars, vectors, textures, notes) for a Blender material (layout.json texture + params)."""
    notes = []
    if p.get("emit_image"):
        master = "M_AK_EmissiveTexMasked_Master" if p.get("alpha") else "M_AK_EmissiveTex_Master"
        return master, {"Emissive Intensity": p["emit"] * K_LUX, "Base Colour Scale": 0.0 if p.get("unlit") else 1.0}, \
            {"Emissive Tint": tuple(p.get("emit_tint", (1.0, 1.0, 1.0)))}, {"Base Colour Map": f"{tex_stem(tex)}_BC"}, notes
    if tex:
        st = tex_stem(tex)
        t = {"Base Colour Map": f"{st}_BC", "ORM Map": f"{st}_ORM", "Normal Map": f"{st}_N"}
        s = float(p.get("tint", 1.0))
        if p.get("translucent"):   # Unreal rebuild: leaf cards on the two-sided foliage master
            return "M_AK_Foliage_Master", {"UV Scale": 1.0, "Edge Fade": 1.0 if p.get("edge_fade") else 0.0,
                                           "Translucency": float(p["translucent"])}, {"Tint": (s, s, s)}, t, notes
        if p.get("alpha"):   # exterior stage: masked two-sided cards
            return "M_AK_TexturedMasked_Master", {"UV Scale": 1.0, "Edge Fade": 1.0 if p.get("edge_fade") else 0.0}, \
                {"Tint": (s, s, s)}, t, notes
        if p.get("two_sided"):   # hero round: an opaque two-sided cloth (M_AK_HBannerSatin): no mask, no alpha test
            return "M_AK_TexturedTwoSided_Master", {"UV Scale": 1.0}, {"Tint": (s, s, s)}, t, notes
        return "M_AK_Textured_Master", {"UV Scale": 1.0}, {"Tint": (s, s, s)}, t, notes
    if p.get("glass"):
        k = float(p.get("refl", GLASS_REFL)) / GLASS_REFL
        sc = {"Opacity": GLASS["Opacity"], "Edge Opacity": min(1.0, GLASS["Edge Opacity"] * k),
              "Roughness": GLASS["Roughness"], "Specular": min(1.0, GLASS["Specular"] * k)}
        tint = hexcol(p["tint"]) if "tint" in p else (1.0, 1.0, 1.0)
        if min(tint) < 0.999:   # Blender's see-through colour; the surface-lit translucent pane has no transmission tint
            notes.append(f"glass tint {p['tint']} is not reproduced (clear pane)")
        return "M_AK_Glass_Master", sc, {"Base Colour": GLASS["Base Colour"]}, {}, notes
    if "emit" in p:
        return "M_AK_Emissive_Master", {"Roughness": 0.8, "Emissive Intensity": p["emit"] * K_LUX}, \
            {"Base Colour": hexcol(p["color"]), "Emissive Colour": hexcol(p.get("emit_color", p["color"]))}, {}, notes
    sc = {"Roughness": p.get("rough", 0.5), "Metallic": p.get("metal", 0.0), "Specular": 0.5}
    if p.get("coat", 0.0) <= 0.0:   # no coat in Blender: plain default-lit master (cheaper, no coat layer at all)
        return "M_AK_FlatNoCoat_Master", sc, {"Base Colour": hexcol(p["color"])}, {}, notes
    sc.update({"Clear Coat": p["coat"], "Clear Coat Roughness": 0.05})
    return "M_AK_Flat_Master", sc, {"Base Colour": hexcol(p["color"])}, {}, notes


def player_start(layout):
    """Exterior stage: the PlayerStart comes from layout.json (in the courtyard on the path, facing the entrance).
    Returns (UE location cm, UE yaw). Falls back to the old spot just inside the door."""
    ps = layout.get("player_start", {"loc": [6.0, 0.9, 0.0], "rot_z": 90.0})
    x, y, _z = loc_cm(ps["loc"])
    return (x, y, 95.0), yaw_deg(ps["rot_z"])


def load_layout():
    return json.loads(LAYOUT.read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")
