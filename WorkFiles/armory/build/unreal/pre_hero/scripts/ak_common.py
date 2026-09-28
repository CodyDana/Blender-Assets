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
"""
import json
import math
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
    want = {"POWER", "PRESET_SCALE", "SUN", "FOG", "SUN_ANGLE_DEG", "EXPOSURE", "LOOK", "SKY", "BLOOM"}
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
PRESET = "golden"
POWER_W = dict(RC["POWER"])                         # Blender watts per role ("glow": per metre of plinth perimeter)
GOLDEN_SCALE = dict(RC["PRESET_SCALE"][PRESET])     # the golden preset's role scales
SUN_W_M2 = float(RC["SUN"][PRESET])                 # f2: 60 W/m2 (x the light's power_scale: the window fill 0.85)
SUN_ANGLE_DEG = float(RC["SUN_ANGLE_DEG"])          # f1: 0.5 deg disc
BLENDER_EXPOSURE_EV = float(RC["EXPOSURE"][PRESET])  # f1: +2.4 EV with AgX Very High Contrast
BLENDER_LOOK = RC["LOOK"]
FOG_DENSITY_PER_M = float(RC["FOG"][PRESET])        # Blender haze extinction per metre; Unreal FogDensity = per_m * 10
SKY_FILL = RC["SKY"][PRESET]                        # (colour, strength) of the Blender world for non-camera rays

# Unreal-only role scales on top of the Blender golden preset (tuned against the Blender golden renders; BUILD_NOTES,
# Unreal rebuild). 1.0 = radiance parity with Blender.
# lantern: the paper panes are opaque in Blender, so the lantern point light only escapes through the open top; in
# Unreal the lanterns cast no shadow (budget), so the light reaches the floor and walls unblocked. 0.2 leaves roughly
# the open-top share (measured round 1: hot floor pools round every lantern in C1 / C10).
UE_ROLE_SCALE = {"lantern": 0.2}
UE_SPEC_OFF_ROLES = {"lantern"}
# Unreal-only: the plan's shadow budget is at most 12 shadow-casting local lights (ARMORY_PLAN section on lights).
# Blender shadows 12 case lights and the 4 rear-alcove spots (f2); in Unreal the alcove spots light an empty rack
# fixture against its own back board, so they give up their shadows and the 12 case lights keep theirs.
UE_SHADOW_OFF_ROLES = {"alcove"}
# Unreal-only post-process grade on the level's unbound PPV (key = FPostProcessSettings property; ak_level sets its
# override_ flag too). Blender blooms lightly (render_armory.py BLOOM: threshold 2.0, strength 0.2); Unreal's default
# bloom (0.675 on everything) veils the dark room.
UE_PP = {"bloom_intensity": 0.3,
         # round 1: Unreal's filmic curve keeps the 2800 K sun saturated where AgX rolls it toward cream (CG sunlit gravel
         # display (0.70, 0.47, 0.18) against Blender's (0.63, 0.51, 0.37))
         "color_saturation": (0.85, 0.85, 0.85, 1.0)}
# (tried and dropped: film_toe 0.3 against the default 0.55 lifted C1 p10 only 0.016 -> 0.039 and darkened every mid-tone)
# Unreal-only sky: SkyAtmosphere's physical sky for a 6000 lux sun reads dim teal (CG_Garden sky display (0.38, 0.44,
# 0.43)) where the Blender golden world is cream (0.81, 0.77, 0.72); its linearised ratio per channel is about
# (5.2, 3.5, 3.1). The factor also scales the real-time sky light (the shade fill the Blender world gives).
UE_SKY = {"sky_luminance_factor": (5.0, 3.5, 3.0)}
SPOT_BLEND = 0.5                 # default when a spot has no "blend"
SPOT_SOFT_M = 0.04
FOG_ANISO = 0.35
FOG_ALBEDO = (1.0, 0.93, 0.85)
SKY_SCATTER = 0.0                # Blender: the world does not scatter in the haze
# Manual exposure bias (EV). Analytic radiance parity: exposure multiplier 2^bias = 2^EV_blender / K.
# The tuned bias is what the capture sweep measured to give the Blender golden C1's mean and median display luminance
# (capture_stats.json "sweep"; BUILD_NOTES). History: -3.34 (fix1, Blender EV +0.8 AgX MHC), -3.94 (look2, EV +0.2).
EXPOSURE_BIAS_ANALYTIC = BLENDER_EXPOSURE_EV - math.log2(K_LUX)
EXPOSURE_BIAS = -1.80            # Unreal rebuild: TUNED over ALL the review views, not C1 alone.
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
    """Blender watts of a layout.json local light in the golden preset (render_armory.py: POWER x perimeter for the
    under-glow x preset scale x the light's own power_scale), times the Unreal-only role scale."""
    role = L["role"]
    p = POWER_W[role] * (L["perimeter"] if role == "glow" else 1.0)
    return p * GOLDEN_SCALE.get(role, 1.0) * float(L.get("power_scale", 1.0)) * UE_ROLE_SCALE.get(role, 1.0)


def sun_lux(L):
    """Directional light illuminance: K x the golden sun strength x the light's power_scale (the window fill 0.85)."""
    return K_LUX * SUN_W_M2 * float(L.get("power_scale", 1.0))


def light_shadows(L):
    return bool(L.get("shadows", False)) and L.get("role") not in UE_SHADOW_OFF_ROLES


def is_interior_piece(piece):
    """The Blender Assembly collection (room kit) = SM_AK_ pieces; SM_AKX_ are AssemblyExterior."""
    return piece.startswith("SM_AK_")


def camera_exposure_offset(cam):
    """A camera's own review exposure relative to the golden room exposure (exterior stage: CG_Garden -2.8 vs +2.4)."""
    ev = cam.get("exposure_ev", {}).get(PRESET)
    return 0.0 if ev is None else float(ev) - BLENDER_EXPOSURE_EV


def light_candela(L):
    """Unreal candela for a layout.json light (golden preset)."""
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
    if p.startswith(("Threshold", "EntryMat")):
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


def n_meshes():
    """look2: the kit size is whatever the pipeline exported (was a constant 35)."""
    return len(list(EXPORTS.glob("SM_AK*.fbx")))   # exterior stage: SM_AK_* room kit + SM_AKX_* exterior


def n_textures():
    return len(engine_textures())


def engine_textures():
    """Exterior stage: the material maps Unreal imports (T_AK_* + T_AKX_*, suffix BC / N / ORM). Generator-only
    intermediates such as T_AK_Emblem (the emblem mask the BC / N / ORM maps are derived from) are not imported."""
    return sorted(p for p in TEXTURES.glob("T_AK*.png") if p.stem.rsplit("_", 1)[1] in ("BC", "N", "ORM"))


def tex_stem(tex):
    """Texture set name -> texture asset stem prefix (exterior sets are named AKX_*: T_AKX_<set>)."""
    return f"T_{tex}" if tex.startswith("AKX_") else f"T_AK_{tex}"


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
